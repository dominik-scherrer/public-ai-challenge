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


USER_AGENT = "SwissGroundingMCP-Hackathon/0.2 (+public municipal service research)"

SERVICE_HINTS = (
    "anmeldung", "abmeldung", "umzug", "wohnsitz", "bescheinigung", "ausweis",
    "identitätskarte", "gesuch", "bewilligung", "formular", "bestellung",
    "beantragen", "register", "patent", "meldepflicht", "gebühr", "gebuehr",
    "attestation", "demande", "permis", "inscription", "certificat",
    "richiesta", "permesso", "certificato", "iscrizione", "servizio",
    "dienstleistung", "online-schalter", "guichet", "sportello",
)

ACTION_HINTS = (
    "beantragen", "bestellen", "anmelden", "abmelden", "melden", "einreichen",
    "gesuch einreichen", "antrag stellen", "bewilligung", "patent", "formular",
    "gebühr", "gebuehr", "kosten", "unterlagen", "voraussetzungen",
    "zuständig", "zustaendig", "schalter", "kontakt", "download",
    "demander", "commander", "inscription", "formulaire", "frais",
    "richiedere", "ordinare", "modulo", "tassa",
)

NOISE_HINTS = (
    "news", "medien", "aktuelles", "politik", "gemeinderat", "veranstaltung",
    "event", "tourismus", "hotel", "restaurant", "verein", "association",
    "manifestation", "turismo", "albergo", "wetter", "weather", "webcam",
    "immobilien", "liegenschaft", "ferienwohnung", "unterkunft",
)

NOISE_PATH_HINTS = (
    "/aktuelles/", "/news/", "/medien/", "/wetter", "/weather", "/webcam",
    "/tourismus", "/tourism", "/hotel", "/restaurant", "/veranstaltung",
    "/events", "/politik/", "/gemeinderat/", "/immobilien", "/liegenschaft",
)

TRACKING_QUERY_PREFIXES = ("utm_", "pk_", "mc_")
TRACKING_QUERY_KEYS = {"fbclid", "gclid"}


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
                self.canonical_url = normalize_url(urllib.parse.urljoin(self.base_url, href))
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
                self.forms.append(normalize_url(urllib.parse.urljoin(self.base_url, action)))

    def handle_endtag(self, tag: str):
        if tag == "a" and self._current_link:
            self._current_link["text"] = _clean_space(self._current_link["text"])
            self.links.append(self._current_link)
            path = urllib.parse.urlsplit(self._current_link["url"]).path.lower()
            if path.endswith(".pdf"):
                self.documents.append(normalize_url(self._current_link["url"]))
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
        normalized_url = normalize_url(url)
        host = urllib.parse.urlsplit(normalized_url).netloc.lower()
        links = []
        seen = set()

        for link in self.links:
            candidate = normalize_url(link["url"])
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
            "url": normalized_url,
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
    url = normalize_url(url)
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
        final_url = normalize_url(response.geturl())
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
    title_headings_url = " ".join(
        [
            page.get("title") or "",
            " ".join(page.get("headings") or []),
            page.get("url") or "",
        ]
    ).lower()
    body = (page.get("main_text") or "").lower()

    strong_positive = sum(1 for hint in SERVICE_HINTS if hint in title_headings_url)
    body_positive = sum(1 for hint in ACTION_HINTS if hint in body)
    negative = sum(1 for hint in NOISE_HINTS if hint in title_headings_url)

    score = 0.14 + min(0.60, 0.20 * strong_positive) + min(0.24, 0.04 * body_positive)

    if page.get("forms"):
        score += 0.18
    if page.get("documents"):
        score += 0.08
    if re.search(r"(?:chf|fr\.?)[\s\xa0]*\d", body):
        score += 0.08
    if any(term in body for term in ("online-schalter", "online schalter", "e-government", "egov")):
        score += 0.08

    score -= min(0.55, 0.22 * negative)
    if _url_has_noise(page.get("url") or "") and strong_positive == 0:
        score -= 0.25

    return max(0.0, min(1.0, score))


def heuristic_extract(
    page: dict[str, Any],
    municipality: str,
    canton: str,
) -> dict[str, Any]:
    score = heuristic_score(page)
    title = page["headings"][0] if page.get("headings") else page.get("title")
    text = page.get("main_text", "")
    quote = text[:500] if score >= 0.40 and text else None

    return {
        "page_role": "service" if score >= 0.48 else ("department" if score >= 0.32 else "other"),
        "is_service": score >= 0.48,
        "confidence": round(score, 3),
        "concept": None,
        "title": title,
        "summary": text[:700] if score >= 0.48 else None,
        "evidence_quote": quote,
        "follow_urls": [],
        "extractor": "heuristic-v1",
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
        and (model_mode == "always" or baseline["confidence"] >= 0.24)
    )

    if not should_call:
        return baseline

    try:
        result = _validated_model_extraction(
            model.extract_service(page, municipality, canton)
        )
    except Exception as exc:
        fallback = dict(baseline)
        fallback["model_error"] = f"{type(exc).__name__}: {exc}"
        fallback["model_fallback"] = True
        return fallback

    result["extractor"] = "event-api"

    quote = result.get("evidence_quote")
    if quote and quote not in page.get("main_text", ""):
        result["evidence_quote"] = None
        result["evidence_warning"] = "non-verbatim model quote discarded"

    return result


def _validated_model_extraction(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("model output must be an object")
    if not isinstance(value.get("is_service"), bool):
        raise RuntimeError("model output is_service must be boolean")
    if value.get("page_role") not in {
        "service", "department", "form", "egov", "news", "tourism", "politics",
        "contact", "other",
    }:
        raise RuntimeError("model output page_role is invalid")
    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise RuntimeError("model output confidence must be numeric")
    if not 0 <= float(confidence) <= 1:
        raise RuntimeError("model output confidence must be between 0 and 1")
    result = dict(value)
    result["confidence"] = float(confidence)
    for key in ("concept", "title", "summary", "evidence_quote"):
        if result.get(key) is not None and not isinstance(result.get(key), str):
            raise RuntimeError(f"model output {key} must be string or null")
    if not isinstance(result.get("follow_urls", []), list):
        raise RuntimeError("model output follow_urls must be a list")
    result.setdefault("follow_urls", [])
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
    entrypoint = normalize_url(entrypoint)
    validate_public_http_url(entrypoint)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshots").mkdir(exist_ok=True)
    (out_dir / "pages").mkdir(exist_ok=True)

    model_config = ModelConfig.from_env()
    model = OpenAICompatibleModel(model_config) if model_config else None

    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queue: list[tuple[str, int, int]] = [(entrypoint, 0, 0)]
    requested_seen: set[str] = set()
    processed_final: set[str] = set()
    processed_canonical: set[str] = set()
    allowed_hosts = {urllib.parse.urlsplit(entrypoint).netloc.lower()}

    source_rows: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    while queue and len(source_rows) < max_pages:
        queue.sort(key=lambda item: (item[2], -item[1]), reverse=True)
        url, depth, _priority = queue.pop(0)
        url = normalize_url(url)
        if url in requested_seen:
            continue
        requested_seen.add(url)

        try:
            snapshot, body = fetch(url)
            snapshot.url = normalize_url(snapshot.url)
            final_key = snapshot.url
            allowed_hosts.add(urllib.parse.urlsplit(snapshot.url).netloc.lower())

            if final_key in processed_final:
                continue

            if snapshot.content_type not in {"text/html", "application/xhtml+xml"}:
                processed_final.add(final_key)
                source_rows.append(_source_row(snapshot, municipality))
                (out_dir / "snapshots" / f"{snapshot.source_id}.bin").write_bytes(body)
                continue

            page = parse_html(snapshot, body)
            canonical_key = normalize_url(snapshot.canonical_url) if snapshot.canonical_url else None
            identity_key = canonical_key or final_key

            if identity_key in processed_canonical:
                processed_final.add(final_key)
                continue

            processed_final.add(final_key)
            processed_canonical.add(identity_key)
            source_rows.append(_source_row(snapshot, municipality))
            (out_dir / "snapshots" / f"{snapshot.source_id}.html").write_bytes(body)
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
                queued_urls = {queued for queued, _, _ in queue}
                for link in page["links"]:
                    link_url = normalize_url(link["url"])
                    if (
                        not link["internal"]
                        or urllib.parse.urlsplit(link_url).netloc.lower() not in allowed_hosts
                        or _obvious_noise(link)
                        or link_url in requested_seen
                        or link_url in queued_urls
                    ):
                        continue
                    queue.append((link_url, depth + 1, _link_priority(link)))
                    queued_urls.add(link_url)

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


def _source_row(snapshot: SourceSnapshot, municipality: str) -> dict[str, Any]:
    return {
        **asdict(snapshot),
        "classification": "official",
        "source_type": "municipality_website",
        "publisher": {
            "name": municipality,
            "authority_level": "municipality",
        },
    }


def _link_priority(link: dict[str, Any]) -> int:
    text = (link.get("text") or "").lower()
    url = link.get("url") or ""
    haystack = f"{text} {url.lower()}"
    score = sum(5 for hint in SERVICE_HINTS if hint in haystack)
    score += sum(2 for hint in ACTION_HINTS if hint in text)
    if url.lower().endswith(".pdf"):
        score += 3
    if any(token in haystack for token in ("verwaltung", "gemeinde", "schalter", "service", "dienst")):
        score += 2
    score -= sum(7 for hint in NOISE_HINTS if hint in haystack)
    if _url_has_noise(url):
        score -= 12
    return score


def _obvious_noise(link: dict[str, Any]) -> bool:
    haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
    has_service_signal = any(hint in haystack for hint in SERVICE_HINTS)
    return (_url_has_noise(link.get("url") or "") or any(hint in haystack for hint in NOISE_HINTS)) and not has_service_signal


def _url_has_noise(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return any(hint in path for hint in NOISE_PATH_HINTS)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return _strip_fragment(url)

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    query_pairs = []
    for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or any(lowered.startswith(p) for p in TRACKING_QUERY_PREFIXES):
            continue
        query_pairs.append((key, value))
    query = urllib.parse.urlencode(query_pairs, doseq=True)

    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


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
