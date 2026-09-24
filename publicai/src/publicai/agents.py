"""Two bounded Pydantic AI agents: website discovery and offline evidence review."""

import hashlib
import json
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, TypedDict
from urllib.parse import urlsplit

from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from pydantic import Field, ValidationError
from pydantic_ai import Agent, ModelRetry, RunContext, ToolOutput
from pydantic_ai.capabilities import WebFetch, WebSearch
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from publicai.config import Settings
from publicai.contracts import (
    CONTRACT_VERSION,
    Capability,
    Discovery,
    EvidenceRef,
    Fact,
    LinkedDocument,
    MunicipalityIdentity,
    ObservedFormField,
    SourceSnapshot,
    StrictModel,
)
from publicai.crawler import ALLOWED_HOST, CrawlError, FetchedPage, SafeCrawler

PROMPTS = Path(__file__).with_name("prompts")


class ModelConfigurationError(ValueError):
    """An actionable local configuration error with no sensitive payload."""


class ReviewValidationError(ValueError):
    """A trusted review rejection message without model-authored text or payloads."""


class CapabilityInventory(TypedDict):
    """Fixed keys let the model provider enforce the complete catalogue during generation."""

    office_hours: Capability
    garbage_collection: Capability
    recycling: Capability
    move_in: Capability
    move_out: Capability
    problem_reporting: Capability


class Inventory(StrictModel):
    """Only the municipal claims are model-generated; acquisition metadata is trusted code."""

    identity: MunicipalityIdentity
    capabilities: CapabilityInventory


class ClaimCheck(StrictModel):
    """The review agent's explicit decision on one factual leaf."""

    path: str
    status: Literal["supported", "unsupported", "conflicting"]
    reason: str = ""


class ReviewDecision(StrictModel):
    """Semantic decisions cannot override deterministic validation or missing checks."""

    identity_consistent: bool
    checks: list[ClaimCheck]
    issues: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class DiscoveryContext:
    """State available to the discovery tools, never exposing provider credentials."""

    crawler: SafeCrawler
    official_url: str
    discovery_id: str
    created_at: datetime
    sources: dict[str, SourceSnapshot] = field(default_factory=dict)
    links: dict[str, dict[str, str]] = field(default_factory=dict)
    validation_issues: list[dict[str, Any]] = field(default_factory=list)
    progress: Callable[[str], None] = lambda _: None

    def retain(self, page: FetchedPage) -> SourceSnapshot:
        """Attach trusted fetch metadata and reuse IDs for cached pages."""
        for source in self.sources.values():
            if source.url == page.url:
                return source
        path = urlsplit(page.url).path.rstrip("/")
        kind = "service"
        if not path:
            kind = "homepage"
        elif any(
            word in path.casefold() for word in ("kontakt", "impressum", "kanzlei", "contact")
        ):
            kind = "contact"
        observed_links = [
            f"{link.label or 'Unlabelled link'}: {link.url}"
            for link in page.links
            if urlsplit(link.url).scheme in {"http", "https", "mailto", "tel"}
        ]
        retained_text = page.text
        if observed_links:
            retained_text += "\nObserved link labels and destinations:\n" + "\n".join(
                observed_links
            )
        if page.authentication_required:
            retained_text += (
                "\nAuthentication interface observed; no procedural requirements inferred."
            )
        source_id = f"source-{len(self.sources) + 1}"
        observed_fields = []
        for item in page.form_fields:
            excerpt = f"Observed form label: {item.label}; required marker: {item.required}"
            retained_text += "\n" + excerpt
            observed_fields.append(
                ObservedFormField(
                    label=Fact(
                        value=item.label,
                        evidence=[EvidenceRef(source_id=source_id, excerpt=excerpt)],
                    ),
                    required_marker=item.required,
                )
            )
        documents = []
        for link in page.links:
            if link.kind not in {"pdf", "calendar"}:
                continue
            evidence = [
                EvidenceRef(
                    source_id=source_id, excerpt=f"{link.label or 'Unlabelled link'}: {link.url}"
                )
            ]
            documents.append(
                LinkedDocument(
                    title=Fact(value=link.label, evidence=evidence) if link.label else None,
                    url=Fact(value=link.url, evidence=evidence),
                    kind=link.kind,
                )
            )
        source = SourceSnapshot(
            id=source_id,
            url=page.url,
            title=page.title[:1000],
            text=retained_text,
            retrieved_at=page.retrieved_at,
            sha256=hashlib.sha256(retained_text.encode()).hexdigest(),
            kind=kind,
            documents=documents,
            form_fields=observed_fields,
            authentication_observed=page.authentication_required,
            links=[
                link.url for link in page.links if urlsplit(link.url).scheme in {"http", "https"}
            ],
        )
        self.sources[source.id] = source
        for link in page.links:
            self.links[link.url] = {"url": link.url, "label": link.label, "kind": link.kind}
        return source

    def inventory(self, candidate: Inventory) -> Discovery:
        """Validate the candidate against only sources actually retained by tools."""
        return Discovery(
            contract_version=CONTRACT_VERSION,
            discovery_id=self.discovery_id,
            created_at=self.created_at,
            official_url=self.official_url,
            identity=candidate.identity,
            capabilities=candidate.capabilities,
            sources=list(self.sources.values()),
        )


@dataclass(frozen=True, slots=True)
class FactoryAgents:
    """Separate agents with distinct dependencies and permissions."""

    discoverer: Agent[DiscoveryContext, Inventory]
    reviewer: Agent[dict[str, SourceSnapshot], ReviewDecision]


def claim_records(value: Any, prefix: str = "") -> dict[str, dict[str, Any]]:
    """Enumerate fact paths independently so the reviewer cannot omit difficult claims."""
    if isinstance(value, dict):
        if "value" in value and "evidence" in value:
            return {prefix: value}
        records = {}
        for key, child in value.items():
            path = f"{prefix}.{key}".strip(".")
            if key in {
                "coverage",
                "zone_required",
                "limitations",
                "missing_reasons",
                "delivery_shapes",
            }:
                records[path] = {"value": child, "evidence": [], "kind": "coverage_or_gap_metadata"}
            elif key == "not_offered_evidence" and child:
                records[path] = {"value": "Service explicitly not offered", "evidence": child}
            else:
                records.update(claim_records(child, path))
        return records
    if isinstance(value, list):
        return {
            path: claim
            for index, child in enumerate(value)
            for path, claim in claim_records(child, f"{prefix}.{index}").items()
        }
    return {}


def validate_review(decision: ReviewDecision, claims: dict[str, dict[str, Any]]) -> None:
    """Require complete affirmative review; do not silently repair a failed review."""
    paths = [check.path for check in decision.checks]
    if len(paths) != len(set(paths)) or set(paths) != set(claims):
        raise ReviewValidationError("Semantic review must check every claim exactly once.")
    if not decision.identity_consistent:
        raise ReviewValidationError("Semantic review found inconsistent municipality identity.")
    if any(
        check.status == "unsupported"
        or (check.status == "conflicting" and ".conflicts." not in check.path)
        for check in decision.checks
    ):
        raise ReviewValidationError(
            "Semantic review found unsupported or conflicting claims. "
            "See review.json beside the diagnostic for claim paths and reasons."
        )
    if decision.issues:
        raise ReviewValidationError(
            "Semantic review reported blocking issues. "
            "See review.json beside the diagnostic for details."
        )


def create_agents(
    settings: Settings, discovery_model: Model | str, review_model: Model | str
) -> FactoryAgents:
    """Create the two agents with small, eager, task-relevant tool sets."""
    model_settings = {
        "max_tokens": settings.model.max_tokens,
        "timeout": settings.model.timeout,
        "openai_reasoning_effort": settings.model.reasoning_effort,
    }
    if settings.model.temperature is not None:
        model_settings["temperature"] = settings.model.temperature

    async def web_fetch(ctx: RunContext[DiscoveryContext], url: str) -> dict[str, Any]:
        """Inspect public HTML or explicitly linked JSON on www.ausserberg.ch."""
        ctx.deps.progress("Discovery tool: web_fetch")
        try:
            page = await ctx.deps.crawler.fetch(url)
            source = ctx.deps.retain(page)
        except CrawlError as error:
            return {
                "error": error.reason,
                "guidance": "Record this discovery gap; do not bypass it.",
            }
        return {
            "source": source.model_dump(mode="json"),
            "links": [link.model_dump() for link in page.links],
            "form_fields": [item.model_dump() for item in page.form_fields],
            "authentication_required": page.authentication_required,
            "untrusted_evidence": True,
        }

    discoverer = Agent(
        discovery_model,
        name="municipality_discovery",
        deps_type=DiscoveryContext,
        output_type=ToolOutput(Inventory, strict=True),
        instructions=(PROMPTS / "discovery.md").read_text(encoding="utf-8")
        + "\n"
        + (PROMPTS / "catalogue.md").read_text(encoding="utf-8"),
        model_settings=model_settings,
        retries=settings.model.retries,
        capabilities=[
            WebFetch(native=False, local=web_fetch),
            *(
                [WebSearch(allowed_domains=[ALLOWED_HOST], external_web_access=False)]
                if settings.web_search_enabled
                else []
            ),
        ],
    )

    @discoverer.tool
    def list_sources(ctx: RunContext[DiscoveryContext], query: str = "") -> dict[str, Any]:
        """Find known navigation links or inspected sources by literal German keywords."""
        ctx.deps.progress("Discovery tool: list_sources")
        terms = query.casefold().split()
        links = [
            link
            for link in ctx.deps.links.values()
            if not terms
            or any(term in (link["url"] + " " + link["label"]).casefold() for term in terms)
        ]
        return {
            "sources": [
                {
                    "source_id": source.id,
                    "url": source.url,
                    "title": source.title,
                    "kind": source.kind,
                }
                for source in ctx.deps.sources.values()
            ],
            "links": links[:150],
            "requests_used": ctx.deps.crawler.request_count,
        }

    @discoverer.output_validator
    def validate_candidate(ctx: RunContext[DiscoveryContext], output: Inventory) -> Inventory:
        try:
            ctx.deps.inventory(output)
        except ValidationError as error:
            details = [
                {"path": e["loc"], "message": e["msg"]} for e in error.errors(include_input=False)
            ]
            ctx.deps.validation_issues = details
            ctx.deps.progress(
                "Candidate failed deterministic evidence validation; requesting correction"
            )
            raise ModelRetry(
                f"Correct these inventory/evidence errors: {json.dumps(details)}. "
                "Available source IDs and kinds: "
                + json.dumps({sid: source.kind for sid, source in ctx.deps.sources.items()})
            ) from error
        ctx.deps.validation_issues.clear()
        return output

    reviewer = Agent(
        review_model,
        name="municipality_evidence_review",
        deps_type=dict[str, SourceSnapshot],
        output_type=ToolOutput(ReviewDecision, strict=True),
        instructions=(PROMPTS / "review.md").read_text(encoding="utf-8")
        + "\n"
        + (PROMPTS / "catalogue.md").read_text(encoding="utf-8"),
        model_settings=model_settings,
        retries=settings.model.retries,
    )

    @reviewer.tool
    def read_source(ctx: RunContext[dict[str, SourceSnapshot]], source_id: str) -> dict[str, Any]:
        """Read an already retained source by ID; no filesystem or network access."""
        source = ctx.deps.get(source_id)
        if source is None:
            raise ModelRetry("Unknown source ID. Use only source IDs in the supplied claims.")
        return source.model_dump(mode="json")

    return FactoryAgents(discoverer=discoverer, reviewer=reviewer)


def usage_limits(settings: Settings) -> UsageLimits:
    """Bound each agent's model calls, tool calls and total tokens."""
    return UsageLimits(
        request_limit=settings.model.request_limit,
        tool_calls_limit=settings.model.tool_calls_limit,
        total_tokens_limit=settings.model.total_tokens_limit,
    )


@asynccontextmanager
async def live_agents(settings: Settings) -> AsyncIterator[FactoryAgents]:
    """Create and close SDK clients with a fixed provider endpoint."""
    key_name = "OPENAI_API_KEY"
    key = os.getenv(key_name)
    if not key or key.startswith("your_"):
        raise ModelConfigurationError(
            f"{key_name} is missing; configure it in .env or the environment."
        )
    async with AsyncOpenAI(
        api_key=key,
        base_url="https://api.openai.com/v1",
        timeout=settings.model.timeout,
        max_retries=settings.model.retries,
        http_client=DefaultAsyncHttpxClient(trust_env=False, follow_redirects=False),
    ) as client:
        adapter = OpenAIProvider(openai_client=client)
        first = OpenAIResponsesModel(settings.model.discovery_model, provider=adapter)
        second = OpenAIResponsesModel(settings.model.review_model, provider=adapter)
        yield create_agents(settings, first, second)
