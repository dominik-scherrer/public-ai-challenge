"""Bounded public HTML and linked JSON discovery on the authorized municipality host."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import re
import socket
import ssl
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
from types import TracebackType
from typing import Literal, Self
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpcore
import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from publicai.contracts import validate_url as validate_handoff_url

ALLOWED_HOST = "www.ausserberg.ch"
USER_AGENT = "PublicAIMunicipalityDiscovery/0.1"
Resolver = Callable[[str, int], Awaitable[list[str]]]
_CONTACT_WORDS = re.compile(r"kontakt|contact|impressum|kanzlei", re.I)
_SERVICE_WORDS = re.compile(
    r"kontakt|contact|impressum|kanzlei|schalter|abfall|kehricht|recycl|entsorg|zuzug|wegzug|"
    r"umzug|anmeld|abmeld|mangel|schaden|meldung|offnung|oeffnung",
    re.I,
)
_PRIVATE_JSON_KEY = re.compile(
    r"token|password|passwort|secret|credential|session|cookie|authorization|apikey|"
    r"csrf|^form|form$|formfields|formdata|formvalues|submission|submitted|"
    r"resident|citizen|person|user|benutzer|"
    r"firstname|lastname|vorname|nachname|birth|geburts",
    re.I,
)
_MAX_JSON_DEPTH = 16
_MAX_JSON_NODES = 10000
_MAX_HTML_DEPTH = 128


class CrawlSettings(BaseModel):
    """Operator limits; the host restriction is deliberately not configurable."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    max_requests: int = Field(default=100, ge=1, le=1000)
    concurrency: int = Field(default=2, ge=1, le=2)
    run_timeout: float = Field(default=600, gt=0, le=3600)
    request_timeout: float = Field(default=10, gt=0, le=60)
    max_redirects: int = Field(default=5, ge=0, le=10)
    max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=5 * 1024 * 1024)


class Link(BaseModel):
    """An observed destination; external and document links remain handoffs."""

    url: str
    label: str
    kind: Literal["html", "pdf", "calendar", "external", "contact", "structured"]


class FormField(BaseModel):
    """Visible form labels without submitted or prepopulated values."""

    label: str
    required: bool = False


class FetchedPage(BaseModel):
    """Retained public evidence, with a hash of exactly the retained text."""

    url: str
    title: str
    text: str
    retrieved_at: datetime
    sha256: str
    links: list[Link] = Field(default_factory=list)
    form_fields: list[FormField] = Field(default_factory=list)
    authentication_required: bool = False


class CrawlFailure(BaseModel):
    """A diagnostic that excludes credentials and query-string values."""

    url: str
    reason: str
    detail: str


class CrawlError(ValueError):
    """A destination, resource, or request that cannot be safely inspected."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason


def validate_url(url: str) -> str:
    """Canonicalize an authorized fetch URL, rejecting session-bearing URLs."""
    if not url or re.search(r"[\x00-\x20\x7f\\]", url):
        raise CrawlError("blocked", "URL contains whitespace or unsafe characters")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as error:
        raise CrawlError("blocked", "Malformed URL") from error
    if parts.scheme not in {"http", "https"} or parts.hostname != ALLOWED_HOST:
        raise CrawlError("blocked", "Only the authorized municipality host may be fetched")
    if parts.username is not None or parts.password is not None:
        raise CrawlError("blocked", "URL credentials are forbidden")
    if port not in {None, 443 if parts.scheme == "https" else 80}:
        raise CrawlError("blocked", "Only default HTTP(S) ports are allowed")
    decoded_path = unquote(parts.path)
    if parts.query or ";" in decoded_path or re.search(r"[\x00-\x20\x7f\\]", decoded_path):
        raise CrawlError("blocked", "Query strings and unsafe path parameters are forbidden")
    return urlunsplit((parts.scheme, ALLOWED_HOST, parts.path or "/", "", ""))


async def resolve_addresses(host: str, port: int) -> list[str]:
    """Resolve DNS without blocking the event loop."""
    results = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(str(result[4][0]) for result in results))


async def _public_addresses(resolver: Resolver, host: str, port: int) -> list[str]:
    """Reject mixed public/private DNS answers and transition addresses."""
    addresses = await resolver(host, port)
    if not addresses:
        raise CrawlError("blocked", "The host has no public DNS address")
    for address in addresses:
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError as error:
            raise CrawlError("blocked", "DNS returned an invalid public address") from error
        if (
            not parsed.is_global
            or parsed.is_multicast
            or (
                isinstance(parsed, ipaddress.IPv6Address)
                and (
                    parsed.ipv4_mapped is not None
                    or parsed.sixtofour is not None
                    or parsed.teredo is not None
                )
            )
        ):
            raise CrawlError("blocked", "All resolved addresses must be public network addresses")
    return addresses


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    """Resolve, validate, and connect to a numeric IP in one network boundary.

    httpcore still performs TLS with the original hostname, preserving certificate
    verification and SNI. The socket backend never re-resolves that hostname.
    """

    def __init__(
        self,
        resolver: Resolver = resolve_addresses,
        backend: httpcore.AsyncNetworkBackend | None = None,
    ) -> None:
        self._resolver = resolver
        self._backend = backend or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Pin the exact validated numeric address used by the socket."""
        if host != ALLOWED_HOST or port not in {80, 443}:
            raise CrawlError("blocked", "Unauthorized network destination")
        addresses = await _public_addresses(self._resolver, host, port)
        return await self._backend.connect_tcp(
            addresses[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        """Never permit local sockets."""
        raise CrawlError("blocked", "Local sockets are forbidden")

    async def sleep(self, seconds: float) -> None:
        """Implement the network backend scheduling contract."""
        await asyncio.sleep(seconds)


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.response.aiter_stream():
            yield chunk

    async def aclose(self) -> None:
        await self.response.aclose()


class _PinnedTransport(httpx.AsyncBaseTransport):
    """Use the public httpcore pool API with our constrained network backend."""

    def __init__(self, resolver: Resolver, concurrency: int) -> None:
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=concurrency,
            max_keepalive_connections=0,
            network_backend=PublicNetworkBackend(resolver),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.pool.handle_async_request(
            httpcore.Request(
                method=request.method,
                url=httpcore.URL(
                    scheme=request.url.raw_scheme,
                    host=request.url.raw_host,
                    port=request.url.port,
                    target=request.url.raw_path,
                ),
                headers=request.headers.raw,
                content=request.stream,
                extensions=request.extensions,
            )
        )
        return httpx.Response(
            response.status,
            headers=response.headers,
            stream=_ResponseStream(response),
            extensions=response.extensions,
        )

    async def aclose(self) -> None:
        await self.pool.aclose()


def _link(
    url: str,
    label: str,
    base: str,
    document_kind: Literal["pdf", "calendar"] | None = None,
) -> Link | None:
    """Keep safe public handoffs while dropping session and credential values."""
    if re.search(r"[\x00-\x20\x7f\\]", url):
        return None
    try:
        absolute = urljoin(base, url)
        parts = urlsplit(absolute)
    except ValueError:
        return None
    if parts.scheme in {"mailto", "tel"}:
        contact = unquote(parts.path)
        if (
            not contact
            or len(contact) > 320
            or parts.netloc
            or parts.fragment
            or re.search(r"[\x00-\x20\x7f\\]", contact)
            or (parts.scheme == "mailto" and not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", contact))
            or (parts.scheme == "tel" and not re.fullmatch(r"\+?[0-9().-]+", contact))
        ):
            return None
        return Link(url=absolute.split("?", 1)[0], label=label[:300], kind="contact")
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username is not None or parts.password is not None:
        return None
    if re.search(r"[\x00-\x1f\x7f\\;]", unquote(parts.path)):
        return None
    absolute = urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, ""))
    try:
        validate_handoff_url(absolute)
    except ValueError:
        # A malformed observed link must not invalidate otherwise usable evidence.
        return None
    suffix = parts.path.lower()
    if suffix.endswith((".webp", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js")):
        return None
    if document_kind == "pdf" or suffix.endswith(".pdf") or label.casefold().endswith(".pdf"):
        kind = "pdf"
    elif document_kind == "calendar" or suffix.endswith((".ics", ".ical")):
        kind = "calendar"
    elif parts.hostname != ALLOWED_HOST:
        kind = "external"
    elif suffix.endswith(".json"):
        kind = "structured"
    else:
        kind = "html"
    return Link(url=absolute, label=label[:300], kind=kind)


class _PublicHTML(HTMLParser):
    """Extract rendered text and labels without executing or retaining scripts."""

    _OMIT = {"script", "style", "template", "noscript", "svg", "textarea", "select"}
    _VOID = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.text: list[str] = []
        self.title: list[str] = []
        self.links: list[Link] = []
        self.labels: dict[str, list[str]] = {}
        self.fields: list[tuple[str, bool]] = []
        self.authentication_required = False
        self.stack: list[tuple[str, bool, bool]] = []
        self._anchor: tuple[str, list[str]] | None = None
        self._anchor_document: Literal["pdf", "calendar"] | None = None
        self._label: str | None = None

    @property
    def omitted(self) -> bool:
        return any(hidden for _, hidden, _ in self.stack)

    @property
    def navigation(self) -> bool:
        return any(navigation for _, _, navigation in self.stack)

    def _record_field(self, values: dict[str, str | None]) -> None:
        identifier = values.get("id") or self._label
        if identifier:
            self.fields.append(
                (identifier, "required" in values or values.get("aria-required") == "true")
            )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        explicitly_hidden = (
            "hidden" in values
            or values.get("aria-hidden") == "true"
            or bool(
                re.search(
                    r"display\s*:\s*none|visibility\s*:\s*hidden", values.get("style") or "", re.I
                )
            )
        )
        if (
            tag in {"textarea", "select"}
            and not explicitly_hidden
            and not self.omitted
            and not self.navigation
        ):
            self._record_field(values)
        hidden = tag in self._OMIT or explicitly_hidden
        navigation = tag in {"nav", "header"} or values.get("role") in {"navigation", "menu"}
        if tag not in self._VOID:
            if len(self.stack) >= _MAX_HTML_DEPTH:
                raise CrawlError("crawl_limit", "HTML exceeds the nesting limit")
            self.stack.append((tag, hidden, navigation))
        if self.omitted or hidden:
            return
        if self._anchor and {"fa-file-pdf", "fa-file-pdf-o"}.intersection(
            (values.get("class") or "").split()
        ):
            self._anchor_document = "pdf"
        if tag == "a":
            self._anchor = (values.get("href") or "", [])
            media_type = (values.get("type") or "").lower()
            download_name = (values.get("download") or "").lower()
            self._anchor_document = (
                "pdf"
                if media_type == "application/pdf" or download_name.endswith(".pdf")
                else "calendar"
                if media_type == "text/calendar"
                else None
            )
        elif self.navigation:
            return
        elif tag == "label":
            self._label = values.get("for") or f"wrapped-{len(self.labels)}"
            self.labels[self._label] = []
        elif tag == "input":
            input_type = (values.get("type") or "text").lower()
            if input_type == "password":
                self.authentication_required = True
            elif input_type not in {"hidden", "submit", "button", "reset", "image"}:
                self._record_field(values)
        elif tag == "form" and re.search(r"login|signin", values.get("action") or "", re.I):
            self.authentication_required = True

    def handle_endtag(self, tag: str) -> None:
        if not self.omitted:
            if tag == "a" and self._anchor is not None:
                destination = _link(
                    self._anchor[0],
                    " ".join(self._anchor[1]),
                    self.base,
                    self._anchor_document,
                )
                if destination is not None and (
                    not self.navigation
                    or _SERVICE_WORDS.search(destination.url + " " + destination.label)
                ):
                    self.links.append(destination)
                self._anchor = None
                self._anchor_document = None
            elif tag == "label":
                self._label = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.omitted:
            return
        value = " ".join(data.split())
        if not value:
            return
        if any(tag == "title" for tag, _, _ in self.stack):
            self.title.append(value)
        if any(tag == "head" for tag, _, _ in self.stack):
            return
        if not self.navigation:
            self.text.append(value)
        if self._anchor:
            self._anchor[1].append(value)
        if self._label is not None:
            self.labels[self._label].append(value)


def extract_html(url: str, html: str, retrieved_at: datetime | None = None) -> FetchedPage:
    """Retain public text, visible field labels, and official link destinations."""
    parser = _PublicHTML(url)
    parser.feed(html)
    parser.close()
    text = "\n".join(parser.text)
    fields = [
        FormField(label=" ".join(parser.labels[identifier]), required=required)
        for identifier, required in parser.fields
        if parser.labels.get(identifier)
    ]
    links = list({(link.url, link.label): link for link in parser.links}.values())
    if not (text.strip() or links or fields or parser.authentication_required):
        raise CrawlError("inaccessible", "HTML contains no retainable public evidence")
    return FetchedPage(
        url=url,
        title=" ".join(parser.title),
        text=text,
        retrieved_at=retrieved_at or datetime.now(UTC),
        sha256=sha256(text.encode()).hexdigest(),
        links=links,
        form_fields=fields,
        authentication_required=parser.authentication_required,
    )


def _unique_json_object(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
    """Reject ambiguous duplicate keys instead of silently choosing one claim."""
    result: dict[str, JsonValue] = {}
    for key, value in pairs:
        if key in result:
            raise CrawlError("blocked", "JSON contains ambiguous duplicate keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    """Reject nonstandard nonfinite numeric literals."""
    raise CrawlError("blocked", "JSON contains a nonfinite numeric value")


def _public_json_page(url: str, title: str, body: bytes, max_bytes: int) -> FetchedPage:
    """Retain bounded public JSON, omitting recognizable private/form fields.

    Filtering is conservative data minimization, not a guarantee that arbitrary
    municipal JSON has no personal information. The normal evidence review and
    final excerpt minimization still apply. Embedded URLs remain untrusted data.
    """
    try:
        data = json.loads(
            body, object_pairs_hook=_unique_json_object, parse_constant=_reject_json_constant
        )
    except (ValueError, UnicodeDecodeError, RecursionError) as error:
        raise CrawlError("blocked", "Public JSON is invalid or excessively nested") from error
    if not isinstance(data, (dict, list)):
        raise CrawlError("blocked", "Public JSON must contain an object or array")
    nodes = 0

    def retain(value: JsonValue, depth: int = 0) -> JsonValue:
        nonlocal nodes
        nodes += 1
        if depth > _MAX_JSON_DEPTH or nodes > _MAX_JSON_NODES:
            raise CrawlError("crawl_limit", "Public JSON exceeds structural limits")
        if isinstance(value, dict):
            form_field = "value" in value and ("name" in value or "label" in value)
            return {
                key: retain(child, depth + 1)
                for key, child in value.items()
                if not _PRIVATE_JSON_KEY.search(re.sub(r"[^a-zA-Z]", "", key))
                and not (form_field and key.casefold() in {"value", "default", "defaultvalue"})
            }
        if isinstance(value, list):
            return [retain(child, depth + 1) for child in value]
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            try:
                validate_handoff_url(value)
            except ValueError:
                return None
        return value

    retained = retain(data)
    if not retained:
        raise CrawlError("blocked", "Public JSON has no retainable service content")
    try:
        text = json.dumps(retained, ensure_ascii=False, indent=2, allow_nan=False)
    except ValueError as error:
        raise CrawlError("blocked", "Public JSON contains invalid numeric data") from error
    if len(text.encode()) > max_bytes:
        raise CrawlError("crawl_limit", "Retained public JSON exceeds the byte limit")
    return FetchedPage(
        url=url,
        title=f"Linked public JSON: {title[:900]}",
        text=text,
        retrieved_at=datetime.now(UTC),
        sha256=sha256(text.encode()).hexdigest(),
    )


class SafeCrawler:
    """A GET-only session with robots, body, time, concurrency, and request limits."""

    def __init__(
        self,
        settings: CrawlSettings | None = None,
        *,
        resolver: Resolver | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or CrawlSettings()
        self.failures: list[CrawlFailure] = []
        self.request_count = 0
        self.pages: dict[str, FetchedPage] = {}
        self.discovered_urls: list[str] = []
        self._resolver = resolver or resolve_addresses
        self._client = httpx.AsyncClient(
            transport=transport or _PinnedTransport(self._resolver, self.settings.concurrency),
            trust_env=False,
            follow_redirects=False,
            timeout=self.settings.request_timeout,
        )
        self._robots: dict[str, RobotFileParser] = {}
        self._robots_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.settings.concurrency)
        self._started = time.monotonic()

    async def __aenter__(self) -> Self:
        await self._client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.__aexit__(exc_type, exc, traceback)

    def _remaining(self) -> float:
        remaining = self.settings.run_timeout - (time.monotonic() - self._started)
        if remaining <= 0 or self.request_count >= self.settings.max_requests:
            raise CrawlError("crawl_limit", "The discovery request or time budget is exhausted")
        return remaining

    def _record(self, url: str, error: CrawlError) -> None:
        try:
            safe_url = validate_url(url)
        except CrawlError:
            safe_url = "<blocked-url>"
        self.failures.append(CrawlFailure(url=safe_url, reason=error.reason, detail=str(error)))

    async def _one_request(self, url: str) -> tuple[int, httpx.Headers, bytes]:
        async with self._semaphore:
            timeout = min(self._remaining(), self.settings.request_timeout)
            parts = urlsplit(url)
            try:
                async with asyncio.timeout(timeout):
                    await _public_addresses(
                        self._resolver, ALLOWED_HOST, 443 if parts.scheme == "https" else 80
                    )
                    self._remaining()
                    self.request_count += 1
                    # A fresh Request bypasses the client's cookie jar entirely.
                    request = httpx.Request(
                        "GET",
                        url,
                        headers={
                            "User-Agent": USER_AGENT,
                            "Accept": (
                                "text/html,application/xhtml+xml,application/json,"
                                "text/plain,application/xml"
                            ),
                            "Accept-Encoding": "identity",
                        },
                    )
                    response = await self._client.send(request, stream=True)
                    try:
                        encoding = response.headers.get("content-encoding", "identity").lower()
                        if encoding not in {"", "identity"}:
                            raise CrawlError("blocked", "Compressed responses are not inspected")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            if len(body) + len(chunk) > self.settings.max_bytes:
                                raise CrawlError("crawl_limit", "Response exceeds the byte limit")
                            body.extend(chunk)
                        return response.status_code, response.headers, bytes(body)
                    finally:
                        await response.aclose()
            except (TimeoutError, httpx.TimeoutException, httpcore.TimeoutException) as error:
                raise CrawlError("crawl_limit", "Request or run time limit exceeded") from error
            except (
                OSError,
                httpx.HTTPError,
                httpcore.NetworkError,
                httpcore.ProtocolError,
            ) as error:
                raise CrawlError("blocked", "Public HTTP request failed") from error

    async def _ensure_robots(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self._robots_lock:
            if origin not in self._robots:
                _, status, _, body = await self._read(origin + "/robots.txt", skip_robots=True)
                parser = RobotFileParser(origin + "/robots.txt")
                if status in {404, 410}:
                    parser.parse(["User-agent: *", "Disallow:"])
                elif status in {401, 403}:
                    parser.parse(["User-agent: *", "Disallow: /"])
                elif status == 200:
                    parser.parse(body.decode("utf-8", errors="replace").splitlines())
                else:
                    raise CrawlError("blocked", "Robots rules could not be established")
                self._robots[origin] = parser
            return self._robots[origin]

    async def _read(
        self,
        url: str,
        *,
        skip_robots: bool = False,
    ) -> tuple[str, int, httpx.Headers, bytes]:
        current = validate_url(url)
        for redirects in range(self.settings.max_redirects + 1):
            suffix = unquote(urlsplit(current).path).lower()
            if suffix.endswith((".pdf", ".ics", ".ical")):
                reason = "pdf_uninspected" if suffix.endswith(".pdf") else "blocked"
                raise CrawlError(reason, "Document and calendar destinations are link-only")
            if not skip_robots:
                robots = await self._ensure_robots(current)
                if not robots.can_fetch(USER_AGENT, current):
                    raise CrawlError("blocked", "The site's robots rules disallow this page")
            status, headers, body = await self._one_request(current)
            if status in {301, 302, 303, 307, 308}:
                if redirects >= self.settings.max_redirects:
                    raise CrawlError("crawl_limit", "Redirect limit exceeded")
                if "location" not in headers:
                    raise CrawlError("blocked", "Redirect has no destination")
                current = validate_url(urljoin(current, headers["location"]))
                continue
            return current, status, headers, body
        raise CrawlError("crawl_limit", "Redirect limit exceeded")

    async def fetch(self, url: str) -> FetchedPage:
        """Inspect public HTML or previously linked JSON through the same safe boundary."""
        try:
            normalized = validate_url(url)
            if normalized in self.pages:
                return self.pages[normalized]
            observed_link = next(
                (
                    link
                    for page in self.pages.values()
                    for link in page.links
                    if link.url == normalized
                ),
                None,
            )
            if urlsplit(normalized).path.lower().endswith(".json") and observed_link is None:
                raise CrawlError("blocked", "JSON must be linked by an already inspected HTML page")
            final_url, status, headers, body = await self._read(normalized)
            if status != 200:
                raise CrawlError(
                    "blocked" if status in {401, 403} else "not_found", f"HTTP status {status}"
                )
            content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type == "application/json" or content_type.endswith("+json"):
                if observed_link is None:
                    raise CrawlError(
                        "blocked", "JSON must be linked by an already inspected HTML page"
                    )
                page = _public_json_page(
                    final_url,
                    observed_link.label or "Municipal data",
                    body,
                    self.settings.max_bytes,
                )
            elif content_type in {"text/html", "application/xhtml+xml"}:
                page = extract_html(final_url, body.decode("utf-8", errors="replace"))
            else:
                reason = "pdf_uninspected" if content_type == "application/pdf" else "blocked"
                raise CrawlError(
                    reason, "Only public HTML and explicitly linked JSON are inspected"
                )
            self.pages[normalized] = page
            self.pages[final_url] = page
            return page
        except CrawlError as error:
            self._record(url, error)
            raise

    async def seed(self, url: str) -> list[FetchedPage]:
        """Inspect the homepage, bounded sitemaps, and up to four contact candidates."""
        homepage = await self.fetch(url)
        robots = await self._ensure_robots(homepage.url)
        sitemap_urls = (robots.site_maps() or [])[:3]
        if not sitemap_urls:
            sitemap_urls = [urljoin(homepage.url, "/sitemap.xml")]
        candidates = [
            link.url
            for link in homepage.links
            if link.kind == "html" and _SERVICE_WORDS.search(link.url + " " + link.label)
        ]
        for sitemap_url in sitemap_urls:
            try:
                _, status, _, body = await self._read(sitemap_url)
                if status != 200:
                    raise CrawlError("not_found", f"Sitemap HTTP status {status}")
                if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
                    raise CrawlError("blocked", "Sitemap document declarations are forbidden")
                root = ElementTree.fromstring(body)
                for element in root.iter():
                    if element.tag.rsplit("}", 1)[-1] == "loc" and element.text:
                        candidate = validate_url(element.text.strip())
                        if _SERVICE_WORDS.search(candidate) and not candidate.endswith(".xml"):
                            candidates.append(candidate)
            except ElementTree.ParseError:
                self._record(sitemap_url, CrawlError("blocked", "Sitemap XML is invalid"))
            except CrawlError as error:
                self._record(sitemap_url, error)
        self.discovered_urls = list(dict.fromkeys(candidates))
        contacts = sorted(
            (
                candidate
                for candidate in self.discovered_urls
                if _CONTACT_WORDS.search(urlsplit(candidate).path.rsplit("/", 1)[-1])
            ),
            key=lambda candidate: (
                0
                if "impressum" in candidate
                else 1
                if "standort" in candidate
                else 2
                if "kanzlei" in candidate
                else 3,
                len(candidate),
            ),
        )[:2]
        for candidate in contacts:
            try:
                await self.fetch(candidate)
            except CrawlError:
                # fetch retains the diagnostic; another contact may still be available.
                continue
        return list({page.url: page for page in self.pages.values()}.values())
