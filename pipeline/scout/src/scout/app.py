from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

from .agents import choose_strategy, inspect_service
from .catalog import all_terms, load_service_index
from .contracts import (
    Availability,
    BuildInfo,
    CatalogSuggestion,
    CoverageSummary,
    DiscoveryFailure,
    Handling,
    HandlingType,
    IndexRelation,
    InformationCoverage,
    InteractionType,
    Municipality,
    MunicipalityDiscovery,
    MunicipalityService,
    SourceRef,
    SourceRole,
)
from .discovery import discover_findings
from .runtime import execute_strategy, recon


def source_role_for(page) -> SourceRole:
    return SourceRole.MUNICIPAL_SERVICE_PAGE


def linked_source_role(url: str, kind: str) -> SourceRole:
    path = urllib.parse.urlsplit(url).path.lower()
    haystack = url.lower()
    if kind == "form":
        return SourceRole.FORM
    if path.endswith(".pdf"):
        if any(term in haystack for term in ("kalender", "calendar", "abfuhr")):
            return SourceRole.CALENDAR_PDF
        if any(term in haystack for term in ("formular", "gesuch", "antrag")):
            return SourceRole.APPLICATION_PDF
        if any(term in haystack for term in ("reglement", "verordnung", "gesetz")):
            return SourceRole.REGULATION_PDF
        return SourceRole.INFORMATION_PDF
    return SourceRole.OFFICIAL_HANDOFF


def _parent_domain(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


# Cantonal and federal authorities are official handoff targets for municipal
# services (e.g. Binn's building permits route to www.vs.ch).
CANTON_CODES = (
    "ag", "ai", "ar", "be", "bl", "bs", "fr", "ge", "gl", "gr", "ju", "lu", "ne",
    "nw", "ow", "sg", "sh", "so", "sz", "tg", "ti", "ur", "vd", "vs", "zg", "zh",
)
GOVERNMENT_DOMAINS = {f"{code}.ch" for code in CANTON_CODES} | {"admin.ch", "ch.ch"}


def _is_government(url: str) -> bool:
    return _parent_domain(url) in GOVERNMENT_DOMAINS


def compile_source_bundle(page) -> list[SourceRef]:
    sources = [
        SourceRef(
            source_id=page.source_id,
            url=page.url,
            role=source_role_for(page),
            retrieved_at=page.retrieved_at,
        )
    ]
    seen = {page.url}

    for kind, urls in (("form", page.forms), ("document", page.documents)):
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            source_id = "ref_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            sources.append(
                SourceRef(
                    source_id=source_id,
                    url=url,
                    role=linked_source_role(url, kind),
                    retrieved_at=None,
                    discovered_from=page.source_id,
                )
            )

    page_parent_domain = _parent_domain(page.url)
    for link in page.links:
        if link["internal"] or link["url"] in seen:
            continue
        text = str(link.get("text") or "").lower()
        url = str(link["url"])
        sibling_official = (
            page_parent_domain
            and _parent_domain(url) == page_parent_domain
        ) or _is_government(url)
        semantic_handoff = any(
            term in f"{text} {url.lower()}"
            for term in (
                "portal", "portail", "portale", "online", "eumzug", "egov",
                "antrag", "gesuch", "kauf", "bestellen",
            )
        )
        if sibling_official or semantic_handoff:
            seen.add(url)
            source_id = "ref_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            sources.append(
                SourceRef(
                    source_id=source_id,
                    url=url,
                    role=SourceRole.OFFICIAL_HANDOFF,
                    retrieved_at=None,
                    discovered_from=page.source_id,
                )
            )

    return sources


async def run_scout(
    url: str,
    municipality: str,
    canton: str,
    out_dir: Path,
    use_agent: bool,
) -> MunicipalityDiscovery:
    index = load_service_index()
    recon_result, root = recon(url)
    strategy = await choose_strategy(recon_result, index, use_agent)
    failures: list[DiscoveryFailure] = []
    pages = execute_strategy(root, strategy, all_terms(index), failures=failures)
    page_by_id = {page.source_id: page for page in pages}

    findings = discover_findings(pages, index)
    services: list[MunicipalityService] = []
    suggestions: list[CatalogSuggestion] = []
    found_index_ids: set[str] = set()

    for finding in findings:
        page = page_by_id[finding.source_ids[0]]
        interpretation = await inspect_service(finding, page, use_agent)
        source_bundle = compile_source_bundle(page)
        services.append(MunicipalityService(
            service_id=interpretation.service_id,
            local_name=interpretation.local_name,
            index_relation=interpretation.index_relation,
            availability=interpretation.availability,
            handling=interpretation.handling,
            sources=source_bundle,
            information=InformationCoverage(
                available=True,
                structured=False,
            ),
            confidence=interpretation.confidence,
            limitations=interpretation.limitations,
        ))
        if interpretation.service_id:
            found_index_ids.add(interpretation.service_id)

        if finding.index_relation == IndexRelation.POSSIBLE_NEW:
            suggestions.append(CatalogSuggestion(
                local_name=finding.local_name,
                proposal="possible_new_service",
                reason="Source-backed service-like capability did not match the current Service Index.",
                source_ids=finding.source_ids,
                confidence=finding.confidence,
            ))

    for entry in index.services:
        if entry.id in found_index_ids:
            continue
        services.append(MunicipalityService(
            service_id=entry.id,
            local_name=entry.labels.get("de", [entry.id])[0],
            index_relation=IndexRelation.INDEXED,
            availability=Availability.NOT_OBSERVED,
            handling=Handling(
                type=HandlingType.UNKNOWN,
                interaction=InteractionType.INFORMATION,
                summary="Scout did not find sufficient source evidence for this indexed service in this run.",
            ),
            sources=[],
            information=InformationCoverage(
                available=False,
                structured=False,
            ),
            confidence=0.0,
            limitations=["Not observed is not evidence that the service is unavailable."],
        ))

    coverage = CoverageSummary(
        indexed_services_checked=len(index.services),
        supported=sum(service.availability == Availability.SUPPORTED for service in services),
        partial=sum(service.availability == Availability.PARTIAL for service in services),
        handoff_only=sum(service.availability == Availability.HANDOFF_ONLY for service in services),
        unavailable=sum(service.availability == Availability.UNAVAILABLE for service in services),
        not_observed=sum(service.availability == Availability.NOT_OBSERVED for service in services),
        new_candidates=len(suggestions),
    )

    now = datetime.now(UTC)
    run_id = f"{municipality.lower().replace(' ', '-')}-{now.strftime('%Y%m%dT%H%M%SZ')}"
    discovery = MunicipalityDiscovery(
        municipality=Municipality(
            name=municipality,
            canton=canton,
            official_url=url,
        ),
        build=BuildInfo(
            run_id=run_id,
            scouted_at=now,
            service_index_version=index.version,
        ),
        strategy=strategy,
        services=services,
        catalog_suggestions=suggestions,
        coverage=coverage,
        failures=failures,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "discovery.json").write_text(
        discovery.model_dump_json(indent=2),
        encoding="utf-8",
    )
    with (out_dir / "sources.jsonl").open("w", encoding="utf-8") as handle:
        for page in pages:
            handle.write(json.dumps({
                "source_id": page.source_id,
                "url": page.url,
                "retrieved_at": page.retrieved_at.isoformat(),
                "title": page.title,
                "language": page.language,
            }, ensure_ascii=False) + "\n")
    (out_dir / "crawl-report.json").write_text(
        json.dumps({
            "run_id": run_id,
            "strategy": strategy.model_dump(mode="json"),
            "pages_fetched": len(pages),
            "failures_encountered": len(failures),
            "findings": len(findings),
            "indexed_services_checked": len(index.services),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return discovery


def main() -> None:
    parser = argparse.ArgumentParser(description="Municipality Scout MVP")
    parser.add_argument("url")
    parser.add_argument("--municipality", required=True)
    parser.add_argument("--canton", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-mode", choices=["off", "agent"], default="off")
    args = parser.parse_args()

    discovery = asyncio.run(run_scout(
        args.url,
        args.municipality,
        args.canton,
        args.out,
        use_agent=args.model_mode == "agent",
    ))
    print(discovery.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
