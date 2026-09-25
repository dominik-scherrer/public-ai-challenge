from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from model_adapter import ModelConfig, OpenAICompatibleModel


USER_AGENT = "SwissGroundingMCP-Hackathon/0.1 (+public municipal service research)"

SERVICE_HINTS = (
    "anmeldung", "abmeldung", "umzug", "wohnsitz", "bescheinigung", "ausweis",
    "identitätskarte", "gesuch", "bewilligung", "formular", "bestellung",
    "beantragen", "register", "attestation", "demande", "permis", "inscription",
    "certificat", "richiesta", "permesso", "certificato", "iscrizione",
    "servizio", "dienstleistung", "online-schalter", "guichet", "sportello",
)

NOISE_HINTS = (
    "news", "medien", "politik", "gemeinderat", "veranstaltung", "event",
    "tourismus", "hotel", "restaurant", "verein", "association", "manifestation",
    "turismo", "albergo",
)


@dataclass
class SourceSnapshot:
    source_id: str
    url: str
    canonical_url: str | None
    retrieved_at: str
    status: int
    content_type: str
    language: str | None
    last_modified: str | None
    etag: str | None
    sha256: str
    fetch_tier: str = "http"


@dataclass
class CrawlReport:
    municipality: str
    canton: str
    entrypoint: str
    started_at: str
    completed_at: str | None
    pages_fetched: int
    pages_failed: int
    services_found: int
    truncated: bool
    stop_reason: str | None
    model_mode: str


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class MunicipalHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.links: list[dict[str, Any]] = []
        self.documents: list[str] = []
        self.forms: list[str] = []
        self.language: str | None = None
        self.canonical_url: str | None = None
        self._stack: list[str] = []
        self._current_link: dict[str, Any] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)

        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

        if tag == "html":
            self.language = attrs.get("lang")
        elif tag == "link":
            rel = (attrs.get("rel") or "").lower()
            href = attrs.get("href")
            if href and "canonical" in rel:
                self.canonical_url = urllib.parse.urljoin(self.base_url, href)
        elif tag == "a":
            href = attrs.get("href")
            if href:
                self._current_link = {
                    "url": urllib.parse.urljoin(self.base_url, href),
                    "text": "",
                }
        elif tag == "form":
            action = attrs.get("action")
            if action:
                self.forms.append(urllib.parse.urljoin(self.base_url, action))

    def handle_endtag(self, tag: str):
        if tag == "a" and self._current_link:
            self._current_link["text"] = _clean_space(self._current_link["text"])
            self.links.append(self._current_link)
            path = urllib.parse.urlsplit(self._current_link["url"]).path.lower()
            if path.endswith(".pdf"):
                self.documents.append(self._current_link["url"])
            self._current_link = None

        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str):
        if self._skip_depth:
            return

        text = _clean_space(data)
        if not text:
            return

        self.text_parts.append(text)
        if self._current_link is not None:
            self._current_link["text"] += " " + text

        if self._stack:
            tag = self._stack[-1]
            if tag == "title":
                self.title_parts.append(text)
            elif tag in {"h1", "h2", "h3"}:
                self.headings.append(text)

    def page_ir(self, url: str, source_ref: str) -> dict[str, Any]:
        host = urllib.parse.urlsplit(url).netloc.lower()
        links = []
        seen = set()

        for link in self.links:
            candidate = _strip_fragment(link["url"])
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)

            parsed = urllib.parse.urlsplit(candidate)
            if parsed.scheme.lower() not in {"http", "https"}:
                continue

            links.append(
                {
                    "url": candidate,
                    "text": link["text"],
                    "internal": parsed.netloc.lower() == host,
                }
            )

        return {
            "schema": "page-ir/v0",
            "url": url,
            "title": _clean_space(" ".join(self.title_parts)) or None,
            "language": self.language,
            "headings": self.headings[:100],
            "main_text": _clean_space(" ".join(self.text_parts)),
            "links": links,
            "forms": list(dict.fromkeys(self.forms)),
            "documents": list(dict.fromkeys(self.documents)),
            "source_ref": source_ref,
        }


def validate_public_http_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")

    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("local hostnames are not allowed")

    try:
        infos = socket.getaddrinfo(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
        )
    except socket.gaierror as exc:
        raise ValueError(f"cannot resolve host: {host}") from exc

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ValueError(f"non-public destination rejected: {address}")


def fetch(url: str, timeout_seconds: int = 20) -> tuple[SourceSnapshot, bytes]:
    validate_public_http_url(url)

    opener = urllib.request.build_opener(SafeRedirectHandler())
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.5",
        },
    )

    with opener.open(request, timeout=timeout_seconds) as response:
        final_url = response.geturl()
        validate_public_http_url(final_url)
        body = response.read()
        sha = hashlib.sha256(body).hexdigest()

        snapshot = SourceSnapshot(
            source_id="src_" + sha[:16],
            url=final_url,
            canonical_url=None,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            status=getattr(response, "status", 200),
            content_type=response.headers.get_content_type(),
            language=None,
            last_modified=response.headers.get("Last-Modified"),
            etag=response.headers.get("ETag"),
            sha256="sha256:" + sha,
        )
        return snapshot, body


def parse_html(snapshot: SourceSnapshot, body: bytes) -> dict[str, Any]:
    parser = MunicipalHTMLParser(snapshot.url)
    parser.feed(body.decode("utf-8", errors="replace"))
    page = parser.page_ir(snapshot.url, snapshot.source_id)
    snapshot.canonical_url = parser.canonical_url
    snapshot.language = parser.language
    return page


def heuristic_score(page: dict[str, Any]) -> float:
    haystack = " ".join(
        [
            page.get("title") or "",
            " ".join(page.get("headings") or []),
            page.get("url") or "",
        ]
    ).lower()

    positive = sum(1 for hint in SERVICE_HINTS if hint in haystack)
    negative = sum(1 for hint in NOISE_HINTS if hint in haystack)

    score = 0.20 + 0.18 * positive - 0.20 * negative
    if page.get("forms"):
        score += 0.15
    if page.get("documents"):
        score += 0.05

    return max(0.0, min(1.0, score))


def heuristic_extract(
    page: dict[str, Any],
    municipality: str,
    canton: str,
) -> dict[str, Any]:
    score = heuristic_score(page)
    title = page["headings"][0] if page.get("headings") else page.get("title")
    text = page.get("main_text", "")
    quote = text[:500] if score >= 0.45 and text else None

    return {
        "page_role": "service" if score >= 0.55 else ("department" if score >= 0.35 else "other"),
        "is_service": score >= 0.55,
        "confidence": round(score, 3),
        "concept": None,
        "title": title,
        "summary": text[:700] if score >= 0.55 else None,
        "evidence_quote": quote,
        "follow_urls": [],
        "extractor": "heuristic-v0",
    }


def model_extract(
    page: dict[str, Any],
    municipality: str,
    canton: str,
    model: OpenAICompatibleModel | None,
    model_mode: str,
) -> dict[str, Any]:
    baseline = heuristic_extract(page, municipality, canton)

    should_call = (
        model is not None
        and model_mode != "off"
        and (model_mode == "always" or baseline["confidence"] >= 0.28)
    )

    if not should_call:
        return baseline

    result = model.extract_service(page, municipality, canton)
    result["extractor"] = "event-api"

    quote = result.get("evidence_quote")
    if quote and quote not in page.get("main_text", ""):
        result["evidence_quote"] = None
        result["evidence_warning"] = "non-verbatim model quote discarded"

    return result


def build_service(
    extraction: dict[str, Any],
    page: dict[str, Any],
    snapshot: SourceSnapshot,
    municipality: str,
    canton: str,
) -> dict[str, Any] | None:
    if not extraction.get("is_service"):
        return None

    title = extraction.get("title") or page.get("title")
    if not title:
        return None

    stable = hashlib.sha256(
        f"{municipality}|{page['url']}|{title}".encode("utf-8")
    ).hexdigest()[:16]

    quote = extraction.get("evidence_quote")
    field_provenance: dict[str, Any] = {}

    if quote:
        field_provenance["title"] = {
            "classification": (
                "inferred" if extraction.get("extractor") == "event-api" else "observed"
            ),
            "source_refs": [snapshot.source_id],
            "evidence": [{"source_ref": snapshot.source_id, "text": quote}],
            "extractor": extraction.get("extractor"),
        }

    return {
        "service_id": f"svc_{stable}",
        "concept": extraction.get("concept"),
        "labels": {page.get("language") or "und": title},
        "description": extraction.get("summary"),
        "provider": {
            "name": municipality,
            "department": None,
            "authority_level": "municipality",
        },
        "jurisdiction": {
            "country": "CH",
            "canton": canton,
            "municipality": municipality,
        },
        "eligibility": [],
        "requirements": [],
        "documents": page.get("documents", []),
        "fees": [],
        "processing_time": None,
        "channels": {
            "online": bool(page.get("forms")),
            "in_person": None,
            "postal": None,
            "telephone": None,
            "email": None,
        },
        "actions": [
            {"type": "form", "url": url}
            for url in page.get("forms", [])
        ],
        "contacts": [],
        "source_refs": [snapshot.source_id],
        "field_provenance": field_provenance,
        "status": "partial",
        "trust": {
            "authority": "high",
            "directness": "primary",
            "freshness": "unknown",
            "evidence_coverage": 1.0 if field_provenance else 0.0,
            "conflicts": [],
        },
    }


def crawl(
    entrypoint: str,
    municipality: str,
    canton: str,
    out_dir: Path,
    max_pages: int = 20,
    max_depth: int = 2,
    delay_seconds: float = 0.5,
    model_mode: str = "candidate",
) -> CrawlReport:
    validate_public_http_url(entrypoint)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshots").mkdir(exist_ok=True)
    (out_dir / "pages").mkdir(exist_ok=True)

    model_config = ModelConfig.from_env()
    model = OpenAICompatibleModel(model_config) if model_config else None

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queue: list[tuple[str, int]] = [(_strip_fragment(entrypoint), 0)]
    seen: set[str] = set()
    allowed_hosts = {urllib.parse.urlsplit(entrypoint).netloc.lower()}

    source_rows: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    while queue and len(seen) < max_pages:
        url, depth = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)

        try:
            snapshot, body = fetch(url)
            allowed_hosts.add(urllib.parse.urlsplit(snapshot.url).netloc.lower())

            source_rows.append(
                {
                    **asdict(snapshot),
                    "classification": "official",
                    "source_type": "municipality_website",
                    "publisher": {
                        "name": municipality,
                        "authority_level": "municipality",
                    },
                }
            )

            suffix = (
                ".html"
                if snapshot.content_type in {"text/html", "application/xhtml+xml"}
                else ".bin"
            )
            (out_dir / "snapshots" / f"{snapshot.source_id}{suffix}").write_bytes(body)

            if snapshot.content_type not in {"text/html", "application/xhtml+xml"}:
                continue

            page = parse_html(snapshot, body)
            (out_dir / "pages" / f"{snapshot.source_id}.json").write_text(
                json.dumps(page, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            extraction = model_extract(
                page,
                municipality,
                canton,
                model,
                model_mode,
            )
            service = build_service(
                extraction,
                page,
                snapshot,
                municipality,
                canton,
            )
            if service:
                services.append(service)

            if depth < max_depth:
                ranked = sorted(
                    (
                        link
                        for link in page["links"]
                        if link["internal"]
                        and urllib.parse.urlsplit(link["url"]).netloc.lower() in allowed_hosts
                        and not _obvious_noise(link)
                    ),
                    key=_link_priority,
                    reverse=True,
                )

                queued_urls = {queued for queued, _ in queue}
                for link in ranked:
                    if link["url"] not in seen and link["url"] not in queued_urls:
                        queue.append((link["url"], depth + 1))
                        queued_urls.add(link["url"])

        except Exception as exc:
            failures.append(
                {
                    "url": url,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        if delay_seconds:
            time.sleep(delay_seconds)

    truncated = bool(queue)
    completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    _write_jsonl(out_dir / "sources.jsonl", source_rows)
    _write_jsonl(out_dir / "services.jsonl", services)
    _write_jsonl(out_dir / "failures.jsonl", failures)

    report = CrawlReport(
        municipality=municipality,
        canton=canton,
        entrypoint=entrypoint,
        started_at=started_at,
        completed_at=completed_at,
        pages_fetched=len(source_rows),
        pages_failed=len(failures),
        services_found=len(services),
        truncated=truncated,
        stop_reason="page_budget_reached" if truncated else "queue_exhausted",
        model_mode=model_mode if model else "off:no_model_config",
    )

    (out_dir / "crawl-report.json").write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return report


def _link_priority(link: dict[str, Any]) -> int:
    haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
    return (
        sum(3 for hint in SERVICE_HINTS if hint in haystack)
        - sum(4 for hint in NOISE_HINTS if hint in haystack)
    )


def _obvious_noise(link: dict[str, Any]) -> bool:
    haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
    return (
        any(hint in haystack for hint in NOISE_HINTS)
        and not any(hint in haystack for hint in SERVICE_HINTS)
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _strip_fragment(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, "")
    )


def _clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded provenance-aware municipality scraper v0"
    )
    parser.add_argument("url")
    parser.add_argument("--municipality", required=True)
    parser.add_argument("--canton", required=True)
    parser.add_argument("--out", default="pipeline/prototype/output")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument(
        "--model-mode",
        choices=["off", "candidate", "always"],
        default="candidate",
    )
    args = parser.parse_args()

    report = crawl(
        args.url,
        args.municipality,
        args.canton,
        Path(args.out),
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay_seconds=args.delay,
        model_mode=args.model_mode,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
