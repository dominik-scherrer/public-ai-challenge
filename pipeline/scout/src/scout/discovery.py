from __future__ import annotations

from .contracts import IndexRelation, ScoutFinding, ServiceIndex
from .runtime import PageIR


GENERIC_SERVICE_SIGNALS = (
    "anmeldung", "abmeldung", "gesuch", "bewilligung", "formular",
    "bestellen", "beantragen", "patent", "gebühr", "gebuehr",
    "dienstleistung", "online-schalter",
)


def _haystack(page: PageIR) -> str:
    return " ".join([
        page.title or "",
        " ".join(page.headings),
        page.url,
        page.text[:5000],
    ]).lower()


def discover_findings(
    pages: list[PageIR],
    index: ServiceIndex,
) -> list[ScoutFinding]:
    findings: list[ScoutFinding] = []
    matched_pages: set[str] = set()

    for entry in index.services:
        terms = [
            term.lower()
            for values in entry.labels.values()
            for term in values
        ] + [hint.lower() for hint in entry.hints]

        best: tuple[int, PageIR] | None = None
        for page in pages:
            haystack = _haystack(page)
            score = sum(1 for term in terms if term in haystack)
            if score and (best is None or score > best[0]):
                best = (score, page)

        if best:
            score, page = best
            matched_pages.add(page.source_id)
            findings.append(ScoutFinding(
                service_id=entry.id,
                local_name=page.headings[0] if page.headings else (page.title or entry.id),
                index_relation=IndexRelation.INDEXED,
                source_ids=[page.source_id],
                confidence=min(0.95, 0.55 + score * 0.1),
                evidence_excerpt=page.text[:300] or None,
            ))

    for page in pages:
        if page.source_id in matched_pages:
            continue
        haystack = _haystack(page)
        signal_count = sum(1 for signal in GENERIC_SERVICE_SIGNALS if signal in haystack)
        if signal_count >= 2:
            findings.append(ScoutFinding(
                service_id=None,
                local_name=page.headings[0] if page.headings else (page.title or "Unknown service"),
                index_relation=IndexRelation.POSSIBLE_NEW,
                source_ids=[page.source_id],
                confidence=min(0.9, 0.5 + signal_count * 0.08),
                evidence_excerpt=page.text[:300] or None,
            ))

    return findings
