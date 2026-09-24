from __future__ import annotations

import urllib.parse
from collections import Counter

from .contracts import IndexRelation, ScoutFinding, ServiceIndex
from .runtime import PageIR, is_news_item


GENERIC_SERVICE_SIGNALS = (
    "anmeldung", "abmeldung", "gesuch", "bewilligung", "formular",
    "bestellen", "beantragen", "patent", "gebühr", "gebuehr",
    "dienstleistung", "online-schalter",
)


def _site_wide_headings(pages: list[PageIR]) -> set[str]:
    """Headings repeated on most pages are navigation/widgets (e.g. 'Webcam'), not page content."""
    if len(pages) < 3:
        return set()
    counts = Counter(heading for page in pages for heading in set(page.headings))
    return {heading for heading, count in counts.items() if count > len(pages) / 2}


def _page_name(page: PageIR, site_wide: set[str]) -> str | None:
    """'Strahlerpatente | Gemeinde Binn | …' → 'Strahlerpatente'."""
    if page.title:
        name = page.title.split("|")[0].strip()
        if name:
            return name
    own = [heading for heading in page.headings if heading not in site_wide]
    return own[0] if own else None


def _haystack(page: PageIR, site_wide: set[str]) -> str:
    # Page-specific evidence only. Body text starts with the site navigation on many
    # municipal CMSs, and parent path sections (/verwaltung/…) are shared by many
    # pages, so matching either makes every page look like every service.
    slug = urllib.parse.unquote(urllib.parse.urlsplit(page.url).path).rstrip("/").rsplit("/", 1)[-1]
    return " ".join([
        _page_name(page, site_wide) or "",
        " ".join(heading for heading in page.headings if heading not in site_wide),
        slug,
    ]).lower()


def discover_findings(
    pages: list[PageIR],
    index: ServiceIndex,
) -> list[ScoutFinding]:
    site_wide = _site_wide_headings(pages)
    candidates = [page for page in pages if not is_news_item(page.url)]
    haystacks = {page.source_id: _haystack(page, site_wide) for page in candidates}

    # Score every (index entry, page) pair, then assign greedily so one page
    # satisfies at most one index entry and each entry gets its best page.
    scored: list[tuple[int, int, str, PageIR]] = []
    for order, page in enumerate(candidates):
        for entry in index.services:
            terms = [
                term.lower()
                for values in entry.labels.values()
                for term in values
            ] + [hint.lower() for hint in entry.hints]
            score = sum(1 for term in terms if term in haystacks[page.source_id])
            if score:
                scored.append((score, -order, entry.id, page))

    findings: list[ScoutFinding] = []
    matched_pages: set[str] = set()
    matched_entries: set[str] = set()
    for score, _, entry_id, page in sorted(scored, key=lambda item: item[:2], reverse=True):
        if entry_id in matched_entries or page.source_id in matched_pages:
            continue
        matched_entries.add(entry_id)
        matched_pages.add(page.source_id)
        findings.append(ScoutFinding(
            service_id=entry_id,
            local_name=_page_name(page, site_wide) or entry_id,
            index_relation=IndexRelation.INDEXED,
            source_ids=[page.source_id],
            confidence=min(0.95, 0.55 + score * 0.1),
            evidence_excerpt=page.text[:300] or None,
        ))

    seen_names: set[str] = set()
    for page in candidates:
        if page.source_id in matched_pages:
            continue
        name = _page_name(page, site_wide) or "Unknown service"
        signal_count = sum(1 for signal in GENERIC_SERVICE_SIGNALS if signal in haystacks[page.source_id])
        if signal_count >= 1 and name.lower() not in seen_names:
            seen_names.add(name.lower())
            findings.append(ScoutFinding(
                service_id=None,
                local_name=name,
                index_relation=IndexRelation.POSSIBLE_NEW,
                source_ids=[page.source_id],
                confidence=min(0.9, 0.5 + signal_count * 0.08),
                evidence_excerpt=page.text[:300] or None,
            ))

    return findings
