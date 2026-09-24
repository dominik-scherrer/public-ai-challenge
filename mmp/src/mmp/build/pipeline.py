"""One Build: Municipality website -> Judge-gated Service Inventory (ADR-0003/0004).

    pages      crawler (default) or browser capture (--capture)
      |
    extract    LLM -> typed drafts with literal quotes   (or --extraction file)
      |
    provenance deterministic: quote in source? value in quote? link allowed?
      |
    eCH-0070   map to a Leistungs-ID from the official list, else unmapped
      |
    Judge      pipeline/judge: provenance (LLM) + injection + coverage/Build Floor
      |
    publish    data/inventories/<bfs>.json — or keep the previous Build if blocked

Freshness comes from rerunning this, never from patching an inventory by hand.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from judge.llm import apertus_is_configured, openai_is_configured

from mmp.build import ech0070, judge_bridge
from mmp.build.extract import extract_services, load_extraction
from mmp.build.pages import Page, load_capture_dir, pages_from_crawl
from mmp.build.provenance import ProvenanceChecker, check_service
from mmp.llm import OpenAICompatibleModel, build_config
from mmp.registry import INVENTORY_DIR, MunicipalityEntry, find_municipality, handoff_allowlist
from mmp.schema import BuildInfo, Contact, Inventory, JudgeStatus, Municipality, Source


class BuildError(RuntimeError):
    pass


@dataclass
class BuildOutcome:
    bfs: int
    published: bool
    inventory_path: Path
    notes: list[str] = field(default_factory=list)
    block_reason: str | None = None


def crawl_pages(entry: MunicipalityEntry, max_pages: int) -> list[Page]:
    from urllib.parse import urlsplit

    from mmp.build.crawler import CrawlSettings, SafeCrawler

    host = urlsplit(entry.website).hostname or ""

    async def _run():
        async with SafeCrawler(host, CrawlSettings(max_requests=max_pages * 2)) as crawler:
            fetched = await crawler.crawl(entry.website, max_pages=max_pages)
            return fetched, crawler.failures

    fetched, failures = asyncio.run(_run())
    if not fetched:
        reasons = ", ".join(sorted({f.reason for f in failures})) or "unknown"
        raise BuildError(f"Crawler retained no page from {entry.website} ({reasons})")
    return pages_from_crawl(fetched)


def build(
    key: str,
    *,
    capture_dir: Path | None = None,
    extraction_path: Path | None = None,
    judge_mode: str = "auto",
    out_dir: Path = INVENTORY_DIR,
    max_pages: int = 40,
) -> BuildOutcome:
    entry = find_municipality(key)
    if entry is None:
        raise BuildError(f"Unknown municipality '{key}' — add it to data/municipalities.yml")
    if entry.bfs is None:
        raise BuildError(f"{entry.name}: BFS number not verified yet (data/municipalities.yml)")

    notes: list[str] = []
    started = datetime.now(UTC)
    pages = load_capture_dir(capture_dir) if capture_dir else crawl_pages(entry, max_pages)
    method = "browser_capture" if capture_dir else "crawler"
    notes.append(f"{len(pages)} retained page(s) via {method}")

    model = None
    if extraction_path:
        extraction = load_extraction(extraction_path)
    else:
        config = build_config()
        if config is None:
            raise BuildError("No build model configured (MMP_BUILD_*, PUBLIC_AI_* or OPENAI_API_KEY) and no --extraction file")
        model = OpenAICompatibleModel(config)
        extraction = extract_services(model, entry.name, pages)

    allowlist = list(handoff_allowlist())
    checker = ProvenanceChecker(pages, list(entry.official_domains), allowlist)
    services = []
    for draft in extraction.get("services", []):
        service, service_notes = check_service(draft, checker)
        notes.extend(service_notes)
        if service is not None:
            services.append(service)

    general_contact = None
    if extraction.get("general_contact"):
        contact = Contact.model_validate(extraction["general_contact"])
        problem = checker.check_contact(contact)
        if problem:
            notes.append(f"general_contact withheld ({problem})")
        else:
            general_contact = contact

    leistungen = ech0070.load_leistungen()
    if not leistungen:
        notes.append("eCH-0070 list not imported (data/ech0070/leistungen.csv): all Services unmapped")
    for service in services:
        service.ech0070 = ech0070.map_service(service, leistungen, model)

    cited = {e.source_id for s in services for e in _all_evidence(s)}
    if general_contact:
        cited |= {e.source_id for e in general_contact.evidence}
    sources = [
        Source(
            id=p.id,
            url=p.url,
            title=p.title,
            retrieved_at=p.retrieved_at,
            sha256=p.sha256,
            capture_method=p.capture_method,
            text=p.text,
        )
        for p in pages
        if p.id in cited
    ]

    build_id = f"{entry.slug}-{started.strftime('%Y%m%dT%H%M%SZ')}"
    inventory = Inventory(
        municipality=Municipality(
            bfs=entry.bfs,
            name=entry.name,
            canton=entry.canton,
            website=entry.website,
            official_domains=list(entry.official_domains),
            languages=list(entry.languages),
            general_contact=general_contact,
        ),
        build=BuildInfo(
            id=build_id,
            built_at=started,
            method=method,
            extraction=extraction.get("extraction", "unknown"),
            judge=JudgeStatus(status="not_run"),
        ),
        sources=sources,
        services=services,
    )

    if judge_mode == "auto":
        judge_mode = "full" if (openai_is_configured() or apertus_is_configured()) else "deterministic"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / f"{entry.bfs}.judge-report.json"
    inventory, blocked, reason = judge_bridge.run(
        inventory, mode=judge_mode, report_path=report_path, allowed_domains=tuple(allowlist)
    )
    notes.append(f"Judge ({judge_mode}): {inventory.build.judge.status}, coverage {inventory.build.judge.coverage:.0%}")

    target = out_dir / f"{entry.bfs}.json"
    (out_dir / f"{entry.bfs}.build-notes.json").write_text(
        json.dumps({"build_id": build_id, "blocked": blocked, "block_reason": reason, "notes": notes}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if blocked:
        notes.append(f"BLOCKED: {reason} Previous Build stays live." if target.exists() else f"BLOCKED: {reason} Nothing published.")
        return BuildOutcome(entry.bfs, False, target, notes, reason)

    target.write_text(json.dumps(inventory.dump(), indent=2, ensure_ascii=False), encoding="utf-8")
    return BuildOutcome(entry.bfs, True, target, notes)


def _all_evidence(service):
    for attr in (service.responsible, service.deadline, service.opening_hours):
        if attr:
            yield from attr.evidence
    for items in (service.fees, service.documents, service.handoffs):
        for item in items:
            yield from item.evidence
    yield from service.summary_evidence
