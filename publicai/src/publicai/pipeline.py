"""Trusted orchestration from bounded acquisition to reviewed immutable artifacts."""

import asyncio
import hashlib
import json
import logging
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from pydantic_ai import capture_run_messages
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart

from publicai.agents import (
    DiscoveryContext,
    FactoryAgents,
    ReviewValidationError,
    claim_records,
    live_agents,
    usage_limits,
    validate_review,
)
from publicai.builder import render_report
from publicai.config import Settings
from publicai.contracts import (
    Discovery,
    DiscoveryFailure,
    ReviewMetadata,
    evidence_refs,
    facts,
    normalize_whitespace,
)
from publicai.crawler import SafeCrawler, validate_url

logger = logging.getLogger(__name__)


class DiscoveryError(ValueError):
    """A failed discovery with a safe diagnostic artifact."""

    def __init__(self, message: str, diagnostic_path: Path) -> None:
        super().__init__(message)
        self.diagnostic_path = diagnostic_path


def minimize_sources(discovery: Discovery) -> Discovery:
    """Retain only cited public text and relevant links after full-context review.

    Hashes describe the minimized retained text, not the original HTML response.
    All supporting excerpts remain reproducible through whitespace normalization.
    """
    refs = evidence_refs(discovery)
    claim_values = {str(fact.value) for fact in facts(discovery)}
    retained = []
    for source in discovery.sources:
        excerpts = list(
            dict.fromkeys(
                normalize_whitespace(ref.excerpt) for ref in refs if ref.source_id == source.id
            )
        )
        if not excerpts and not source.authentication_observed:
            continue
        original = normalize_whitespace(source.text)
        # Extract from trusted text instead of persisting model-authored replacements.
        text = "\n".join(
            original[original.index(excerpt) : original.index(excerpt) + len(excerpt)]
            for excerpt in excerpts
        )
        if not text:
            text = "Authentication interface observed; no procedural requirements inferred."
        retained.append(
            source.model_copy(
                update={
                    "text": text,
                    "sha256": hashlib.sha256(text.encode()).hexdigest(),
                    "links": [url for url in source.links if url in claim_values],
                }
            )
        )
    return Discovery.model_validate(discovery.model_copy(update={"sources": retained}).model_dump())


async def discover_with_agents(
    url: str,
    out: Path,
    settings: Settings,
    agents: FactoryAgents,
    crawler: SafeCrawler,
    progress: Callable[[str], None] = lambda _: None,
) -> Path:
    """Run injected agents and crawler; publish only a validated reviewed discovery.

    Invalid model output, failed identity checks and incomplete semantic reviews
    leave diagnostic artifacts, never a completed discovery or server package.
    """
    discovery_id = f"discovery-{uuid4().hex}"
    out.mkdir(parents=True, exist_ok=True)
    staging = out / f".staging-{discovery_id}"
    staging.mkdir()
    context = DiscoveryContext(crawler, url, discovery_id, datetime.now(UTC), progress=progress)
    decision = None
    started = monotonic()
    messages = []
    stage = "acquisition"

    try:
        url = validate_url(url)
        context.official_url = url
        async with asyncio.timeout(settings.run_timeout):
            progress("Inspecting homepage, robots rules, sitemap and contact pages")
            pages = await crawler.seed(url)
            for page in pages:
                context.retain(page)
            for candidate in crawler.discovered_urls:
                context.links.setdefault(candidate, {"url": candidate, "label": "", "kind": "html"})
            progress("Discovery agent: extracting the six evidence-backed capabilities")
            stage = "discovery"
            with capture_run_messages() as messages:
                result = await agents.discoverer.run(
                    "Discover the six municipal capabilities at " + url + ".\n"
                    "Initial inspected source evidence:\n"
                    + json.dumps(
                        [source.model_dump(mode="json") for source in context.sources.values()],
                        ensure_ascii=False,
                    ),
                    deps=context,
                    usage_limits=usage_limits(settings),
                )
            discovery = context.inventory(result.output)
            # Facts and fetch failures come through separate trust boundaries.
            discovery.failures = [
                DiscoveryFailure(**failure.model_dump()) for failure in crawler.failures
            ]
            claims = claim_records(result.output.model_dump(mode="json"))
            progress(f"Review agent: checking {len(claims)} claims against retained evidence")
            stage = "review"
            review_result = await agents.reviewer.run(
                "Review this inventory and every listed claim path.\n"
                + json.dumps(
                    {
                        "inventory": result.output.model_dump(mode="json"),
                        "claims": claims,
                        "sources": [
                            {"id": source.id, "url": source.url, "kind": source.kind}
                            for source in context.sources.values()
                        ],
                    },
                    ensure_ascii=False,
                ),
                deps=context.sources,
                usage_limits=usage_limits(settings),
            )
            decision = review_result.output
            validate_review(decision, claims)
            discovery.review = ReviewMetadata(
                status="passed", agent="municipality_evidence_review", checked_at=datetime.now(UTC)
            )
            stage = "publication"
            # Revalidate after trusted metadata additions before publishing.
            discovery = minimize_sources(Discovery.model_validate(discovery.model_dump()))
            (staging / "discovery.json").write_text(
                discovery.model_dump_json(indent=2), encoding="utf-8"
            )
            (staging / "review.json").write_text(
                decision.model_dump_json(indent=2), encoding="utf-8"
            )
            metrics = {
                "duration_seconds": round(monotonic() - started, 3),
                "website_requests": crawler.request_count,
                "agents": {
                    name: {
                        "model_requests": run.usage.requests,
                        "tool_calls": run.usage.tool_calls,
                        "input_tokens": run.usage.input_tokens,
                        "output_tokens": run.usage.output_tokens,
                    }
                    for name, run in (("discovery", result), ("review", review_result))
                },
            }
            (staging / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            (staging / "report.md").write_text(render_report(discovery), encoding="utf-8")
            destination = out / discovery_id
            staging.rename(destination)
            logger.info("discovery_completed")
            return destination / "discovery.json"
    except Exception as error:
        # Exception strings from SDKs may include provider payloads; never persist them.
        diagnostic = out / f"diagnostic-{discovery_id}"
        diagnostic.mkdir()
        payload = {
            "status": "failed",
            "discovery_id": discovery_id,
            "error_type": type(error).__name__,
            "stage": stage,
            "message": str(error)
            if isinstance(error, ReviewValidationError)
            else "Discovery failed validation, acquisition, model execution, or review.",
            "request_count": crawler.request_count,
            "failures": [failure.model_dump() for failure in crawler.failures],
            "validation_issues": context.validation_issues,
            "model_responses": [
                {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                    "finish_reason": message.finish_reason,
                }
                for message in messages
                if isinstance(message, ModelResponse)
            ],
            "schema_retry_history": [
                {key: issue[key] for key in ("loc", "type", "msg") if key in issue}
                for message in messages
                if isinstance(message, ModelRequest)
                for part in message.parts
                if isinstance(part, RetryPromptPart) and isinstance(part.content, list)
                for issue in part.content
            ],
        }
        diagnostic_path = diagnostic / "diagnostic.json"
        diagnostic_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if decision is not None:
            (diagnostic / "review.json").write_text(
                decision.model_dump_json(indent=2), encoding="utf-8"
            )
        logger.error("discovery_failed", extra={"error_type": type(error).__name__})
        raise DiscoveryError(payload["message"], diagnostic_path) from error
    finally:
        if staging.exists():
            shutil.rmtree(staging)


async def discover(
    url: str, out: Path, settings: Settings, progress: Callable[[str], None] = lambda _: None
) -> Path:
    """Connect configured models and the restricted crawler for a live discovery."""
    validate_url(url)
    async with live_agents(settings) as agents, SafeCrawler(settings.crawl) as crawler:
        return await discover_with_agents(url, out, settings, agents, crawler, progress)
