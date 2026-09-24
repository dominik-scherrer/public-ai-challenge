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

from model_adapter import ModelConfig, OpenAICompatibleClassifier

USER_AGENT = "AgentScrap/0.1 (+Swiss public municipal service discovery)"

SERVICE_HINTS = (
    "anmeldung", "abmeldung", "umzug", "wohnsitz", "bescheinigung", "ausweis",
    "identitätskarte", "gesuch", "bewilligung", "formular", "bestellung",
    "beantragen", "register", "patent", "meldepflicht", "gebühr", "gebuehr",
    "abfall", "kehricht", "recycling", "entsorgung", "sammelstelle",
    "baugesuch", "baubewilligung", "reservation", "miete", "vermietung",
    "attestation", "demande", "permis", "inscription", "certificat",
    "richiesta", "permesso", "certificato", "iscrizione", "servizio",
    "dienstleistung", "online-schalter", "guichet", "sportello",
)

NOISE_HINTS = (
    "news", "medien", "aktuelles", "politik", "gemeinderat", "veranstaltung",
    "tourismus", "hotel", "restaurant", "verein", "association", "manifestation",
    "turismo", "albergo", "wetter", "weather", "webcam", "ferienwohnung",
)

NOISE_PATH_HINTS = (
    "/aktuelles/", "/news/", "/medien/", "/wetter", "/weather", "/webcam",
    "/tourismus", "/tourism", "/hotel", "/restaurant", "/veranstaltung",
    "/events", "/politik/", "/gemeinderat/",
)

TRACKING_QUERY_PREFIXES = ("utm_", "pk_", "mc_")
TRACKING_QUERY_KEYS = {"fbclid", "gclid"}

TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("residence_registration", ("anmeldung", "abmeldung", "umzug", "zuzug", "wegzug", "einwohner")),
    ("residence_certificate", ("wohnsitzbestätigung", "wohnsitzbescheinigung", "heimatausweis", "attestation de domicile")),
    ("waste_collection", ("abfall", "kehricht", "recycling", "entsorgung", "sammelstelle")),
    ("building_application", ("baugesuch", "baubewilligung", "bauen", "planung")),
    ("facility_rental", ("reservation", "reservierung", "vermietung", "miete", "gemeindesaal", "mehrzweckhalle")),
    ("identity_document", ("identitätskarte", "identitaetskarte", "pass", "passport")),
    ("forms", ("formular", "formulare", "gesuch", "antrag")),
    ("permit", ("bewilligung", "patent", "permis", "permesso")),
    ("municipal_contact", ("kontakt", "öffnungszeiten", "oeffnungszeiten", "verwaltung", "gemeindekanzlei")),
    ("regulations", ("reglement", "verordnung", "gesetz", "regolamento")),
    ("official_notices", ("amtliche veröffentlich", "amtliche veroeffentlich", "publikation", "anzeiger")),
]

TOOL_RULES = {
    "residence_registration": ["get_move_in_requirements"],
    "residence_certificate": ["list_services"],
    "waste_collection": ["garbage_collection"],
    "building_application": ["get_building_application_requirements"],
    "facility_rental": ["list_facilities"],
    "identity_document": ["get_id_requirements"],
    "forms": ["list_forms"],
    "municipal_contact": ["find_responsible_office"],
    "regulations": ["search_regulations"],
    "official_notices": ["list_official_notices"],
}


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
class ScrapReport:
    run_id: str
    municipality: str
    canton: str
    entrypoint: str
    started_at: str
    completed_at: str
    pages_fetched: int
    pages_failed: int
    service_leads_found: int
    truncated: bool
    stop_reason: str
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
        self.links: list[dict[str, str]] = []
        self.forms: list[str] = []
        self.documents: list[str] = []
        self.language: str | None = None
        self.canonical_url: str | None = None
        self._stack: list[str] = []
        self._current_link: dict[str, str] | None = None
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs):
        attrs = dict(attrs)
        self._stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "html":
            self.language = attrs.get("lang")
        elif tag == "link":
            if "canonical" in (attrs.get("rel") or "").lower() and attrs.get("href"):
                self.canonical_url = normalize_url(
                    urllib.parse.urljoin(self.base_url, attrs["href"])
                )
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
            self._current_link["text"] = clean_space(self._current_link["text"])
            self.links.append(self._current_link)
            if urllib.parse.urlsplit(self._current_link["url"]).path.lower().endswith(".pdf"):
                self.documents.append(normalize_url(self._current_link["url"]))
            self._current_link = None
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        text = clean_space(data)
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
        url = normalize_url(url)
        host = urllib.parse.urlsplit(url).netloc.lower()
        links = []
        seen = set()
        for link in self.links:
            candidate = normalize_url(link["url"])
            if candidate in seen:
                continue
            seen.add(candidate)
            parsed = urllib.parse.urlsplit(candidate)
            if parsed.scheme not in {"http", "https"}:
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
            "title": clean_space(" ".join(self.title_parts)) or None,
            "language": self.language,
            "headings": self.headings[:100],
            "main_text": clean_space(" ".join(self.text_parts)),
            "links": links,
            "forms": list(dict.fromkeys(self.forms)),
            "documents": list(dict.fromkeys(self.documents)),
            "source_ref": source_ref,
        }


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, "")
        )
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    netloc = (
        f"{hostname}:{port}"
        if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443))
        else hostname
    )
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    query = urllib.parse.urlencode(
        [
            (k, v)
            for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_QUERY_KEYS
            and not any(k.lower().startswith(p) for p in TRACKING_QUERY_PREFIXES)
        ],
        doseq=True,
    )
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def validate_public_http_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("public http(s) URL required")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("local hostname rejected")
    try:
        infos = socket.getaddrinfo(
            host, parsed.port or (443 if parsed.scheme == "https" else 80)
        )
    except socket.gaierror as exc:
        raise ValueError(f"cannot resolve host: {host}") from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError(f"non-public destination rejected: {info[4][0]}")


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
        return (
            SourceSnapshot(
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
            ),
            body,
        )


def parse_html(snapshot: SourceSnapshot, body: bytes) -> dict[str, Any]:
    parser = MunicipalHTMLParser(snapshot.url)
    parser.feed(body.decode("utf-8", errors="replace"))
    page = parser.page_ir(snapshot.url, snapshot.source_id)
    snapshot.canonical_url = parser.canonical_url
    snapshot.language = parser.language
    return page


def service_score(page: dict[str, Any]) -> float:
    strong = " ".join(
        [
            page.get("title") or "",
            " ".join(page.get("headings") or []),
            page.get("url") or "",
        ]
    ).lower()
    body = (page.get("main_text") or "").lower()
    positive = sum(1 for hint in SERVICE_HINTS if hint in strong)
    negative = sum(1 for hint in NOISE_HINTS if hint in strong)
    score = 0.12 + min(0.66, 0.20 * positive) - min(0.55, 0.22 * negative)
    if page.get("forms"):
        score += 0.16
    if page.get("documents"):
        score += 0.08
    if any(
        hint in body
        for hint in ("gesuch", "antrag", "formular", "gebühr", "gebuehr", "beantragen", "bestellen")
    ):
        score += 0.08
    if url_has_noise(page.get("url") or "") and positive == 0:
        score -= 0.25
    return max(0.0, min(1.0, score))


def infer_service_type(page: dict[str, Any]) -> str:
    haystack = " ".join(
        [
            page.get("title") or "",
            " ".join(page.get("headings") or []),
            page.get("url") or "",
            (page.get("main_text") or "")[:3000],
        ]
    ).lower()
    for service_type, terms in TYPE_RULES:
        if any(term in haystack for term in terms):
            return service_type
    return "unknown"


def source_role(url: str, text: str = "") -> str:
    haystack = f"{url} {text}".lower()
    path = urllib.parse.urlsplit(url).path.lower()
    if path.endswith(".pdf"):
        if any(x in haystack for x in ("kalender", "calendar", "abfuhr", "collect")):
            return "calendar_pdf"
        if any(x in haystack for x in ("formular", "gesuch", "antrag", "application")):
            return "application_pdf"
        if any(x in haystack for x in ("reglement", "verordnung", "gesetz", "regolamento")):
            return "regulation_pdf"
        return "information_pdf"
    if any(x in haystack for x in ("formular", "gesuch", "antrag", "apply", "application")):
        return "form"
    if any(x in haystack for x in ("kontakt", "verwaltung", "amt", "office")):
        return "contact_page"
    return "related_page"


def build_service_lead(
    page: dict[str, Any],
    municipality: str,
    canton: str,
    confidence: float,
    service_type_hint: str | None = None,
    title_override: str | None = None,
) -> dict[str, Any] | None:
    if confidence < 0.48:
        return None
    title = title_override or (
        page["headings"][0] if page.get("headings") else page.get("title")
    )
    if not title:
        return None

    stable = hashlib.sha256(
        f"{municipality}|{page['url']}|{title}".encode()
    ).hexdigest()[:16]

    sources = [
        {
            "source_ref": page["source_ref"],
            "url": page["url"],
            "role": "service_page",
        }
    ]
    seen_urls = {page["url"]}

    for url in page.get("documents", []):
        if url not in seen_urls:
            sources.append({"source_ref": None, "url": url, "role": source_role(url)})
            seen_urls.add(url)

    for url in page.get("forms", []):
        if url not in seen_urls:
            sources.append({"source_ref": None, "url": url, "role": "form"})
            seen_urls.add(url)

    for link in sorted(page.get("links", []), key=link_priority, reverse=True)[:8]:
        role = source_role(link["url"], link.get("text", ""))
        if (
            role
            in {"form", "contact_page", "application_pdf", "calendar_pdf", "regulation_pdf"}
            and link["url"] not in seen_urls
        ):
            sources.append(
                {"source_ref": None, "url": link["url"], "role": role}
            )
            seen_urls.add(link["url"])

    return {
        "schema": "service-lead/v1",
        "service_lead_id": "lead_" + stable,
        "labels": {page.get("language") or "und": title},
        "service_type_hint": service_type_hint or infer_service_type(page),
        "authority": {
            "country": "CH",
            "canton": canton,
            "municipality": municipality,
            "department": None,
        },
        "sources": sources,
        "discovery": {
            "confidence": round(confidence, 3),
            "method": "heuristic-v1",
            "evidence": [{"source_ref": page["source_ref"], "text": title}],
        },
        "status": "candidate",
    }


def build_tool_observations(
    run_id: str,
    municipality: str,
    canton: str,
    leads: list[dict[str, Any]],
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    if leads:
        observations.append(
            {
                "tool_id": "list_services",
                "service_lead_id": leads[0]["service_lead_id"],
                "result": "supported",
                "source_refs": [leads[0]["sources"][0]["source_ref"]],
                "notes": "At least one source-backed municipal service lead was discovered.",
                "proposed_change": None,
            }
        )

    for lead in leads:
        service_type = lead.get("service_type_hint", "unknown")
        refs = [
            source["source_ref"]
            for source in lead.get("sources", [])
            if source.get("source_ref")
        ]
        roles = {source.get("role") for source in lead.get("sources", [])}

        for tool_id in TOOL_RULES.get(service_type, []):
            key = (tool_id, lead["service_lead_id"])
            if key in seen:
                continue
            seen.add(key)
            observations.append(
                {
                    "tool_id": tool_id,
                    "service_lead_id": lead["service_lead_id"],
                    "result": "supported",
                    "source_refs": refs,
                    "notes": (
                        f"Agent Scrap discovered a {service_type} service lead "
                        "with authoritative source material."
                    ),
                    "proposed_change": None,
                }
            )

        if "form" in roles or "application_pdf" in roles:
            key = ("list_forms", lead["service_lead_id"])
            if key not in seen:
                seen.add(key)
                observations.append(
                    {
                        "tool_id": "list_forms",
                        "service_lead_id": lead["service_lead_id"],
                        "result": "supported",
                        "source_refs": refs,
                        "notes": "A form/application source was discovered in the service bundle.",
                        "proposed_change": None,
                    }
                )

        if service_type == "waste_collection" and "calendar_pdf" in roles:
            observations.append(
                {
                    "tool_id": "next_waste_collection",
                    "service_lead_id": lead["service_lead_id"],
                    "result": "supported",
                    "source_refs": refs,
                    "notes": "Waste service bundle includes a collection-calendar source.",
                    "proposed_change": None,
                }
            )

    return {
        "schema": "agent-scrap-tool-observations/v1",
        "run_id": run_id,
        "municipality": municipality,
        "canton": canton,
        "observations": observations,
    }


class AgentScrap:
    def __init__(
        self,
        max_pages: int = 20,
        max_depth: int = 2,
        delay_seconds: float = 0.2,
        model=None,
    ):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay_seconds = delay_seconds
        self.model = model

    def classify(
        self,
        page: dict[str, Any],
        municipality: str,
        canton: str,
        model_mode: str,
    ) -> tuple[float, str | None, str | None]:
        baseline = service_score(page)
        if (
            self.model is None
            or model_mode == "off"
            or (model_mode == "candidate" and baseline < 0.24)
        ):
            return baseline, None, None
        try:
            result = self.model.classify(page, municipality, canton)
        except Exception:
            return baseline, None, None
        if not result.get("is_service"):
            return (
                min(baseline, float(result.get("confidence", 0))),
                result.get("service_type_hint"),
                result.get("title"),
            )
        return (
            max(baseline, float(result.get("confidence", 0))),
            result.get("service_type_hint"),
            result.get("title"),
        )

    def run(
        self,
        entrypoint: str,
        municipality: str,
        canton: str,
        out_dir: Path,
        model_mode: str = "off",
    ) -> ScrapReport:
        entrypoint = normalize_url(entrypoint)
        validate_public_http_url(entrypoint)

        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "snapshots").mkdir(exist_ok=True)
        (out_dir / "pages").mkdir(exist_ok=True)

        started = datetime.now(timezone.utc)
        run_id = f"{slug(municipality)}-{started.strftime('%Y%m%dT%H%M%SZ')}"
        queue: list[tuple[str, int, int]] = [(entrypoint, 0, 0)]
        requested_seen: set[str] = set()
        processed_final: set[str] = set()
        processed_canonical: set[str] = set()
        allowed_hosts = {urllib.parse.urlsplit(entrypoint).netloc.lower()}

        sources: list[dict[str, Any]] = []
        leads: list[dict[str, Any]] = []
        failures: list[dict[str, str]] = []

        while queue and len(sources) < self.max_pages:
            queue.sort(key=lambda item: (item[2], -item[1]), reverse=True)
            url, depth, _priority = queue.pop(0)
            url = normalize_url(url)
            if url in requested_seen:
                continue
            requested_seen.add(url)

            try:
                snapshot, body = fetch(url)
                final_url = normalize_url(snapshot.url)
                snapshot.url = final_url
                allowed_hosts.add(urllib.parse.urlsplit(final_url).netloc.lower())

                if final_url in processed_final:
                    continue

                if snapshot.content_type not in {"text/html", "application/xhtml+xml"}:
                    processed_final.add(final_url)
                    sources.append(source_row(snapshot, municipality))
                    (
                        out_dir / "snapshots" / f"{snapshot.source_id}.bin"
                    ).write_bytes(body)
                    continue

                page = parse_html(snapshot, body)
                canonical = (
                    normalize_url(snapshot.canonical_url)
                    if snapshot.canonical_url
                    else None
                )
                identity = canonical or final_url

                if identity in processed_canonical:
                    processed_final.add(final_url)
                    continue

                processed_final.add(final_url)
                processed_canonical.add(identity)
                sources.append(source_row(snapshot, municipality))

                (
                    out_dir / "snapshots" / f"{snapshot.source_id}.html"
                ).write_bytes(body)
                (
                    out_dir / "pages" / f"{snapshot.source_id}.json"
                ).write_text(
                    json.dumps(page, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                score, type_hint, title_override = self.classify(
                    page, municipality, canton, model_mode
                )
                lead = build_service_lead(
                    page,
                    municipality,
                    canton,
                    score,
                    type_hint,
                    title_override,
                )
                if lead:
                    leads.append(lead)

                if depth < self.max_depth:
                    queued = {queued_url for queued_url, _, _ in queue}
                    for link in page["links"]:
                        link_url = normalize_url(link["url"])
                        if (
                            not link["internal"]
                            or urllib.parse.urlsplit(link_url).netloc.lower()
                            not in allowed_hosts
                            or obvious_noise(link)
                            or link_url in requested_seen
                            or link_url in queued
                        ):
                            continue
                        queue.append(
                            (link_url, depth + 1, link_priority(link))
                        )
                        queued.add(link_url)

            except Exception as exc:
                failures.append(
                    {"url": url, "error": f"{type(exc).__name__}: {exc}"}
                )

            if self.delay_seconds:
                time.sleep(self.delay_seconds)

        leads = dedupe_leads(leads)
        completed = datetime.now(timezone.utc)
        truncated = bool(queue)

        report = ScrapReport(
            run_id=run_id,
            municipality=municipality,
            canton=canton,
            entrypoint=entrypoint,
            started_at=started.isoformat(timespec="seconds"),
            completed_at=completed.isoformat(timespec="seconds"),
            pages_fetched=len(sources),
            pages_failed=len(failures),
            service_leads_found=len(leads),
            truncated=truncated,
            stop_reason="page_budget_reached" if truncated else "queue_exhausted",
            model_mode=model_mode,
        )

        write_jsonl(out_dir / "sources.jsonl", sources)
        write_jsonl(out_dir / "service-leads.jsonl", leads)
        write_jsonl(out_dir / "failures.jsonl", failures)

        (out_dir / "tool-observations.json").write_text(
            json.dumps(
                build_tool_observations(run_id, municipality, canton, leads),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (out_dir / "crawl-report.json").write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        return report


def dedupe_leads(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for lead in leads:
        label = next(iter(lead.get("labels", {}).values()), "").strip().lower()
        primary = lead.get("sources", [{}])[0].get("url", "")
        key = (label, normalize_url(primary))
        if key not in seen:
            seen.add(key)
            out.append(lead)
    return out


def source_row(
    snapshot: SourceSnapshot, municipality: str
) -> dict[str, Any]:
    return {
        **asdict(snapshot),
        "classification": "official",
        "source_type": "municipality_website",
        "publisher": {
            "name": municipality,
            "authority_level": "municipality",
        },
    }


def link_priority(link: dict[str, Any]) -> int:
    haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
    score = (
        sum(5 for hint in SERVICE_HINTS if hint in haystack)
        - sum(7 for hint in NOISE_HINTS if hint in haystack)
    )
    if url_has_noise(link.get("url", "")):
        score -= 12
    if urllib.parse.urlsplit(link.get("url", "")).path.lower().endswith(".pdf"):
        score += 2
    return score


def obvious_noise(link: dict[str, Any]) -> bool:
    haystack = f"{link.get('text', '')} {link.get('url', '')}".lower()
    has_service_signal = any(hint in haystack for hint in SERVICE_HINTS)
    return (
        url_has_noise(link.get("url", ""))
        or any(hint in haystack for hint in NOISE_HINTS)
    ) and not has_service_signal


def url_has_noise(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return any(hint in path for hint in NOISE_PATH_HINTS)


def clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Agent Scrap MVP — discover municipal services and authoritative sources"
        )
    )
    parser.add_argument("url")
    parser.add_argument("--municipality", required=True)
    parser.add_argument("--canton", required=True)
    parser.add_argument("--out", default="pipeline/agent_scrap/output")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument(
        "--model-mode",
        choices=["off", "candidate", "always"],
        default="off",
    )
    args = parser.parse_args()

    config = ModelConfig.from_env()
    model = OpenAICompatibleClassifier(config) if config else None

    report = AgentScrap(
        args.max_pages,
        args.max_depth,
        args.delay,
        model=model,
    ).run(
        args.url,
        args.municipality,
        args.canton,
        Path(args.out),
        args.model_mode,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
