from __future__ import annotations

import json
import logging
import os

from .contracts import (
    Availability,
    Handling,
    HandlingType,
    InteractionType,
    ReconResult,
    ScoutFinding,
    ScoutStrategy,
    ServiceIndex,
    ServiceInterpretation,
    StrategyMode,
)
from .runtime import PageIR

logger = logging.getLogger(__name__)


def heuristic_strategy(
    recon: ReconResult,
    index: ServiceIndex,
) -> ScoutStrategy:
    if recon.internal_links <= 80 and not recon.service_directory_candidates:
        return ScoutStrategy(
            mode=StrategyMode.BROAD_SMALL_SITE,
            reason="Small/shallow site without a clear service directory.",
            roots=[recon.entrypoint],
            max_pages=25,
            max_depth=2,
            target_services=[service.id for service in index.services],
        )
    return ScoutStrategy(
        mode=StrategyMode.TARGETED,
        reason="Larger or structured site; target indexed services rather than broad crawling.",
        roots=[recon.entrypoint],
        max_pages=30,
        max_depth=1,
        target_services=[service.id for service in index.services],
    )


async def choose_strategy(
    recon: ReconResult,
    index: ServiceIndex,
    use_agent: bool,
) -> ScoutStrategy:
    if not use_agent:
        return heuristic_strategy(recon, index)

    model = os.getenv("SCOUT_MODEL")
    if not model:
        return heuristic_strategy(recon, index)

    try:
        from pydantic_ai import Agent
    except ImportError:
        return heuristic_strategy(recon, index)

    agent = Agent(
        model,
        output_type=ScoutStrategy,
        system_prompt=(
            "You choose a bounded scouting strategy for a Swiss municipality. "
            "Allowed modes are broad_small_site and targeted. "
            "Use broad_small_site for small/shallow sites where broad crawling is economical. "
            "Use targeted for larger/structured sites. "
            "Keep max_pages <= 40 and max_depth <= 2. "
            "The runtime, not you, enforces networking and crawl policy."
        ),
    )
    prompt = json.dumps({
        "recon": recon.model_dump(mode="json"),
        "service_index": [
            {"id": service.id, "labels": service.labels}
            for service in index.services
        ],
    }, ensure_ascii=False)
    try:
        result = await agent.run(prompt)
        return result.output
    except Exception as exc:
        logger.warning(
            "Agent strategy selection failed (%s: %s); falling back to heuristic",
            type(exc).__name__,
            exc,
        )
        return heuristic_strategy(recon, index)


def heuristic_interpret(
    finding: ScoutFinding,
    page: PageIR,
) -> ServiceInterpretation:
    haystack = f"{page.url} {page.text[:4000]}".lower()
    external = any(not bool(link["internal"]) for link in page.links)

    if page.forms:
        handling_type = HandlingType.HTML_FORM
        interaction = InteractionType.REQUEST
        summary = "The municipality exposes this service through an HTML form or request endpoint."
    elif page.documents:
        handling_type = HandlingType.PDF
        interaction = InteractionType.INFORMATION
        summary = "The municipality exposes this service through a municipal information page with linked official documents."
    elif external and any(term in haystack for term in ("eumzug", "portal", "online")):
        handling_type = HandlingType.EXTERNAL_HANDOFF
        interaction = InteractionType.WAYFINDING
        summary = "The municipality provides local guidance and routes the citizen to an external official service."
    else:
        handling_type = HandlingType.STATIC_PAGE
        interaction = InteractionType.INFORMATION
        summary = "The municipality provides this service primarily as information on an official web page."

    return ServiceInterpretation(
        service_id=finding.service_id,
        local_name=finding.local_name,
        index_relation=finding.index_relation,
        availability=Availability.SUPPORTED,
        handling=Handling(
            type=handling_type,
            interaction=interaction,
            summary=summary,
            live=False,
        ),
        confidence=finding.confidence,
        limitations=[],
    )


async def inspect_service(
    finding: ScoutFinding,
    page: PageIR,
    use_agent: bool,
) -> ServiceInterpretation:
    if not use_agent:
        return heuristic_interpret(finding, page)

    model = os.getenv("SCOUT_MODEL")
    if not model:
        return heuristic_interpret(finding, page)

    try:
        from pydantic_ai import Agent
    except ImportError:
        return heuristic_interpret(finding, page)

    agent = Agent(
        model,
        output_type=ServiceInterpretation,
        system_prompt=(
            "You semantically interpret how a Swiss municipality handles one public service. "
            "Use only the supplied page evidence. Do not invent URLs or source facts. "
            "Describe the local handling pattern, not a universal procedure. "
            "not_observed is not the same as unavailable. "
            "Return concise, factory-useful output."
        ),
    )
    prompt = json.dumps({
        "finding": finding.model_dump(mode="json"),
        "page": {
            "url": page.url,
            "title": page.title,
            "headings": page.headings[:30],
            "text": page.text[:12000],
            "forms": page.forms,
            "documents": page.documents,
            "links": page.links[:60],
        },
    }, ensure_ascii=False)
    try:
        result = await agent.run(prompt)
        return result.output
    except Exception as exc:
        logger.warning(
            "Agent service inspection failed (%s: %s); falling back to heuristic",
            type(exc).__name__,
            exc,
        )
        return heuristic_interpret(finding, page)
