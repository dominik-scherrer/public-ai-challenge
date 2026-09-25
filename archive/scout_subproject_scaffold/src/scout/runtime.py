from __future__ import annotations

import hashlib
import heapq
import ipaddress
import logging
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

from .contracts import DiscoveryFailure, ReconResult, ScoutStrategy, StrategyMode

logger = logging.getLogger(__name__)

USER_AGENT = "MunicipalityScout/0.1 (+Swiss public-service discovery)"
TRACKING_PREFIXES = ("utm_", "pk_", "mc_")
TRACKING_KEYS = {"fbclid", "gclid"}


@dataclass
class PageIR:
    source_id: str
    url: str
    retrieved_at: datetime
    title: str | None
    language: str | None
    headings: list[str]
    text: str
    links: list[dict[str, str | bool]]
    forms: list[str]
    documents: list[str]


class Parser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: list[str] = []
        self.text: list[str] = []
        self.headings: list[str] = []
        self.links: list[dict[str, str]] = []
        self.forms: list[str] = []
        self.documents: list[str] = []
        self.language: str | None = None
        self._stack: list[str] = []
        self._current_link: dict[str, str] | None = None
        self._skip = 0

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "html":
            self.language = attrs.get("lang")
        elif tag == "a" and attrs.get("href"):
            self._current_link = {
                "url": urllib.parse.urljoin(self.base_url, attrs["href"]),
                "text": "",
            }
        elif tag == "form" and attrs.get("action"):
            self.forms.append(
                normalize_url(urllib.parse.urljoin(self.base_url, attrs["action"]))
            )

    def handle_endtag(self, tag: str):
        if tag == "a" and self._current_link:
            self._current_link["text"] = clean(self._current_link["text"])
            self.links.append(self._current_link)
            if urllib.parse.urlsplit(self._current_link["url"]).path.lower().endswith(".pdf"):
                self.documents.append(normalize_url(self._current_link["url"]))
            self._current_link = None
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str):
        if self._skip:
            return
        value = clean(data)
        if not value:
            return
        self.text.append(value)
        if self._current_link is not None:
            self._current_link["text"] += " " + value
        if self._stack:
            if self._stack[-1] == "title":
                self.title.append(value)
            elif self._stack[-1] in {"h1", "h2", "h3"}:
                self.headings.append(value)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = urllib.parse.urlencode([
        (k, v)
        for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_KEYS
        and not any(k.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)
    ])
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def validate_public_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("public http(s) URL required")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("local hostname rejected")
    infos = socket.getaddrinfo(
        host,
        parsed.port or (443 if parsed.scheme == "https" else 80),
    )
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("non-public destination rejected")


def fetch_page(url: str, timeout: int = 20) -> PageIR:
    url = normalize_url(url)
    validate_public_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = normalize_url(response.geturl())
        validate_public_url(final_url)
        body = response.read()
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unsupported content type: {content_type}")

    parser = Parser(final_url)
    parser.feed(body.decode("utf-8", errors="replace"))
    retrieved_at = datetime.now(UTC)
    source_id = "src_" + hashlib.sha256(body).hexdigest()[:16]
    host = urllib.parse.urlsplit(final_url).netloc.lower()
    links: list[dict[str, str | bool]] = []
    seen = set()
    for link in parser.links:
        candidate = normalize_url(link["url"])
        if candidate in seen:
            continue
        seen.add(candidate)
        parsed = urllib.parse.urlsplit(candidate)
        if parsed.scheme not in {"http", "https"}:
            continue
        links.append({
            "url": candidate,
            "text": link["text"],
            "internal": parsed.netloc.lower() == host,
        })

    return PageIR(
        source_id=source_id,
        url=final_url,
        retrieved_at=retrieved_at,
        title=clean(" ".join(parser.title)) or None,
        language=parser.language,
        headings=parser.headings[:100],
        text=clean(" ".join(parser.text)),
        links=links,
        forms=list(dict.fromkeys(parser.forms)),
        documents=list(dict.fromkeys(parser.documents)),
    )


def recon(entrypoint: str) -> tuple[ReconResult, PageIR]:
    page = fetch_page(entrypoint)
    directory_candidates: list[str] = []
    sampled: list[str] = []
    for link in page.links:
        text = f"{link['text']} {link['url']}".lower()
        if link["internal"] and any(term in text for term in (
            "dienstleistung", "online-schalter", "service", "guichet", "sportello"
        )):
            directory_candidates.append(str(link["url"]))
        if link["internal"] and len(sampled) < 30:
            sampled.append(str(link["text"] or link["url"]))

    result = ReconResult(
        entrypoint=page.url,
        title=page.title,
        language=page.language,
        internal_links=sum(1 for link in page.links if link["internal"]),
        service_directory_candidates=directory_candidates[:10],
        sampled_links=sampled,
    )
    return result, page


ASSET_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js", ".zip", ".mp4", ".mp3",
)
ADMIN_SIGNALS = (
    "verwaltung", "kanzlei", "schalter", "dienstleistung", "formular",
    "reglement", "bauwesen", "abfall", "kontakt", "gemeindesaal",
    "belegung", "öffnungszeit", "oeffnungszeit", "patent", "gesuch",
    "bewilligung", "anmeld", "gebühr", "gebuehr",
)
NOISE_SIGNALS = (
    "wetter", "webcam", "luftaufnahme", "geschichte", "siedlung",
    "verein", "galerie", "immobilien", "anschlagbrett", "tourismus",
    "dorfleben", "impressum", "datenschutz", "partnergemeinde",
    "museum", "skilift", "skiclub",
)
# Dated news / notice detail pages, e.g. /gemeindeinfos/28082026-baugesuch-...-913
NEWS_ITEM = re.compile(r"/\d{6,8}-|-\d{2,5}$")


def is_asset_url(url: str) -> bool:
    return urllib.parse.urlsplit(url).path.lower().endswith(ASSET_EXTENSIONS)


def is_news_item(url: str) -> bool:
    return bool(NEWS_ITEM.search(urllib.parse.urlsplit(url).path.lower()))


def link_priority(link: dict, terms: list[str]) -> int:
    """Higher is fetched first: indexed-service and admin wording up, noise and news items down."""
    haystack = f"{link['text']} {urllib.parse.unquote(str(link['url']))}".lower()
    score = 3 * sum(1 for term in terms if term in haystack)
    score += 2 * sum(1 for signal in ADMIN_SIGNALS if signal in haystack)
    score -= 3 * sum(1 for signal in NOISE_SIGNALS if signal in haystack)
    if is_news_item(str(link["url"])):
        score -= 6
    return score


def broad_crawl(
    root: PageIR,
    strategy: ScoutStrategy,
    terms_by_service: dict[str, list[str]] | None = None,
    failures: list[DiscoveryFailure] | None = None,
) -> list[PageIR]:
    terms = [term for values in (terms_by_service or {}).values() for term in values]
    pages = [root]
    seen = {root.url}
    seen_bodies = {root.source_id}
    queue: list[tuple[int, int, int, str]] = []
    counter = 0

    def enqueue(page: PageIR, depth: int) -> None:
        nonlocal counter
        for link in page.links:
            url = str(link["url"])
            if not link["internal"] or url in seen or is_asset_url(url):
                continue
            counter += 1
            heapq.heappush(queue, (depth, -link_priority(link, terms), counter, url))

    enqueue(root, 1)
    while queue and len(pages) < strategy.max_pages:
        depth, _, _, url = heapq.heappop(queue)
        url = normalize_url(url)
        if url in seen or depth > strategy.max_depth:
            continue
        seen.add(url)
        try:
            page = fetch_page(url)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            logger.warning("Failed to fetch %s: %s: %s", url, type(exc).__name__, exc)
            if failures is not None:
                failures.append(DiscoveryFailure(url=url, stage="crawl", error=f"{type(exc).__name__}: {exc}"))
            continue
        # Redirects and aliases can land on a page we already have, or leave the
        # municipality's site entirely (e.g. a link that redirects to the canton).
        if (page.url in seen and page.url != url) or page.source_id in seen_bodies:
            continue
        if urllib.parse.urlsplit(page.url).hostname != urllib.parse.urlsplit(root.url).hostname:
            continue
        seen.add(page.url)
        seen_bodies.add(page.source_id)
        pages.append(page)
        if depth < strategy.max_depth:
            enqueue(page, depth + 1)
    return pages


def targeted_crawl(
    root: PageIR,
    strategy: ScoutStrategy,
    terms_by_service: dict[str, list[str]],
    failures: list[DiscoveryFailure] | None = None,
) -> list[PageIR]:
    pages = [root]
    scored: list[tuple[int, str]] = []
    target_ids = set(strategy.target_services) or set(terms_by_service)

    for link in root.links:
        if not link["internal"]:
            continue
        haystack = f"{link['text']} {link['url']}".lower()
        score = sum(
            1
            for service_id in target_ids
            for term in terms_by_service.get(service_id, [])
            if term in haystack
        )
        if score:
            scored.append((score, str(link["url"])))

    for _, url in sorted(scored, reverse=True):
        if len(pages) >= strategy.max_pages:
            break
        try:
            pages.append(fetch_page(url))
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            logger.warning("Failed to fetch %s: %s: %s", url, type(exc).__name__, exc)
            if failures is not None:
                failures.append(DiscoveryFailure(url=url, stage="crawl", error=f"{type(exc).__name__}: {exc}"))
            continue
    return pages


def execute_strategy(
    root: PageIR,
    strategy: ScoutStrategy,
    terms_by_service: dict[str, list[str]],
    failures: list[DiscoveryFailure] | None = None,
) -> list[PageIR]:
    if strategy.mode == StrategyMode.BROAD_SMALL_SITE:
        return broad_crawl(root, strategy, terms_by_service, failures=failures)
    return targeted_crawl(root, strategy, terms_by_service, failures=failures)
