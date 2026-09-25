"""Six read-only municipal MCP tools over a validated, offline build-time snapshot."""

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from publicai.contracts import (
    CAPABILITY_IDS,
    CapabilityId,
    Coverage,
    Discovery,
    EvidenceRef,
    Fact,
    ServiceEntry,
    StrictModel,
    evidence_refs,
    load_discovery,
)

TOOL_NAMES = {
    "office_hours": "get_office_hours",
    "garbage_collection": "get_garbage_collection",
    "recycling": "get_recycling_info",
    "move_in": "get_move_in_requirements",
    "move_out": "get_move_out_requirements",
    "problem_reporting": "get_problem_reporting_info",
}
type Outcome = Literal[
    "ok", "needs_input", "unknown_filter", "no_matching_dates", "information_unavailable"
]
type TextFilter = Annotated[str, Field(max_length=200)]


class ResultData(StrictModel):
    """Definitive discovered facts and official destinations relevant to a query."""

    entries: list[ServiceEntry] = Field(default_factory=list)
    handoffs: list[Fact] = Field(default_factory=list)


class SnapshotValidity(StrictModel):
    """Snapshot identity and explicit published validity, without freshness inference."""

    discovery_id: str
    created_at: datetime
    status: Literal["undated", "published_period", "expired"]
    valid_from: date | None = None
    valid_to: date | None = None
    requested_from: date | None = None
    requested_to: date | None = None
    interval_covered: bool | None = None
    timezone: Literal["Europe/Zurich"] = "Europe/Zurich"


class Citation(StrictModel):
    """A citation expanded with the retained source's URL and retrieval timestamp."""

    source_id: str
    url: str
    excerpt: str
    retrieved_at: datetime
    sha256: str


class ResponseEnvelope(StrictModel):
    """Identical output contract across all six tools and all generated packages."""

    municipality: str
    capability: CapabilityId
    coverage: Coverage
    outcome: Outcome
    data: ResultData
    evidence: list[Citation]
    retrieved_at: list[datetime]
    snapshot: SnapshotValidity
    limitations: list[str]
    available_choices: dict[str, list[str]] = Field(default_factory=dict)


class _JsonFormatter(logging.Formatter):
    """Keep transport diagnostics machine-readable and separate from protocol stdout."""

    def format(self, record: logging.LogRecord) -> str:
        event = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, ensure_ascii=False)


class SnapshotRuntime:
    """Query a validated snapshot without models, networking or mutable service state."""

    def __init__(self, discovery: Discovery, *, today: date | None = None) -> None:
        self.discovery = discovery
        self._today = today

    def query(
        self,
        capability_id: CapabilityId,
        *,
        office: str | None = None,
        waste_type: str | None = None,
        zone: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        material: str | None = None,
        category: str | None = None,
    ) -> ResponseEnvelope:
        """Apply exact optional filters and return only retained evidence-backed facts."""
        if capability_id not in CAPABILITY_IDS:
            raise ValueError("Unknown capability.")
        today = self._today or datetime.now(ZoneInfo("Europe/Zurich")).date()
        capability = self.discovery.capabilities[capability_id]
        entries = list(capability.entries)
        limitations = [
            "Build-time snapshot; rebuilding is the only update mechanism. No live verification.",
            *capability.limitations,
            *[f"Discovery gap: {reason}." for reason in capability.missing_reasons],
        ]
        if capability.conflicts:
            limitations.append("Conflicting claims were omitted from definitive answers.")
        if capability_id in {"move_in", "move_out"}:
            limitations.append("Published requirements and conditions may not be exhaustive.")
        snapshot = SnapshotValidity(
            discovery_id=self.discovery.discovery_id,
            created_at=self.discovery.created_at,
            status="undated",
            valid_from=capability.valid_from.value if capability.valid_from else None,
            valid_to=capability.valid_to.value if capability.valid_to else None,
        )
        if snapshot.valid_from or snapshot.valid_to:
            snapshot.status = (
                "expired" if snapshot.valid_to and snapshot.valid_to < today else "published_period"
            )
        else:
            limitations.append(
                "No published validity period; retrieval time does not establish currency."
            )
        choices: dict[str, list[str]] = {}
        outcome: Outcome = (
            "ok" if capability.coverage != "unavailable" else "information_unavailable"
        )
        if capability_id == "garbage_collection":
            start, end = date_window(today, date_from, date_to)
            snapshot.requested_from, snapshot.requested_to = start, end
            snapshot.interval_covered = bool(
                snapshot.valid_from
                and snapshot.valid_to
                and snapshot.valid_from <= start
                and end <= snapshot.valid_to
            )
        filters = {
            "office_hours": ("office", office),
            "garbage_collection": ("waste_type", waste_type),
            "recycling": ("material", material),
            "problem_reporting": ("category", category),
        }
        if capability_id in filters:
            filter_name, filter_value = filters[capability_id]
            if filter_value and filter_value.strip():
                available = {entry.label.value for entry in entries}
                if filter_name == "material":
                    available.update(entry.id for entry in entries)
                    available.update(item.value for entry in entries for item in entry.materials)
                choices[filter_name] = sorted(available)
                entries = [
                    entry for entry in entries if matches_entry(entry, filter_value, filter_name)
                ]
                if not entries:
                    outcome = "unknown_filter"
        if capability_id == "garbage_collection" and outcome != "unknown_filter":
            choices["zone"] = sorted({entry.zone.value for entry in entries if entry.zone})
            if zone and zone.strip():
                wanted = zone.strip().casefold()
                known = {value.casefold() for value in choices["zone"]}
                if wanted not in known:
                    outcome, entries = "unknown_filter", []
                else:
                    entries = [
                        entry
                        for entry in entries
                        if entry.zone is None or entry.zone.value.casefold() == wanted
                    ]
            elif capability.zone_required or any(entry.zone for entry in entries):
                outcome = "needs_input"
                entries = [
                    entry.model_copy(update={"dates": []})
                    for entry in entries
                    if entry.zone is None
                ]
                limitations.append(
                    "A collection zone is required; no address-to-zone mapping is inferred."
                )
                if not choices["zone"]:
                    limitations.append(
                        "Zone choices were not discovered; "
                        "consult the official service destination."
                    )
            if outcome == "ok":
                entries = [
                    entry.model_copy(
                        update={
                            "dates": [item for item in entry.dates if start <= item.value <= end]
                        }
                    )
                    for entry in entries
                ]
                if not snapshot.interval_covered:
                    outcome = "information_unavailable"
                    limitations.append(
                        "Date coverage is unknown or incomplete for the requested interval; "
                        "general guidance remains available."
                    )
                elif not any(entry.dates for entry in entries):
                    outcome = "no_matching_dates"
        data = ResultData(entries=entries, handoffs=capability.handoffs)
        refs = evidence_refs(data) + evidence_refs(self.discovery.identity.name)
        refs += evidence_refs(capability.valid_from) + evidence_refs(capability.valid_to)
        citations = self._citations(refs)
        return ResponseEnvelope(
            municipality=self.discovery.identity.name.value,
            capability=capability_id,
            coverage=capability.coverage,
            outcome=outcome,
            data=data,
            evidence=citations,
            retrieved_at=sorted({citation.retrieved_at for citation in citations}),
            snapshot=snapshot,
            limitations=limitations,
            available_choices=choices,
        )

    def _citations(self, refs: list[EvidenceRef]) -> list[Citation]:
        """Expand citations from trusted retained source metadata and remove duplicates."""
        sources = {source.id: source for source in self.discovery.sources}
        unique = {(ref.source_id, ref.excerpt): ref for ref in refs}
        return [
            Citation(
                source_id=ref.source_id,
                url=sources[ref.source_id].url,
                excerpt=ref.excerpt,
                retrieved_at=sources[ref.source_id].retrieved_at,
                sha256=sources[ref.source_id].sha256,
            )
            for ref in unique.values()
        ]


def matches_entry(entry: ServiceEntry, value: str, filter_name: str) -> bool:
    """Match identifiers and observed labels exactly, ignoring case and whitespace."""
    labels = [entry.id, entry.label.value]
    if filter_name == "material":
        labels.extend(item.value for item in entry.materials)
    return value.strip().casefold() in {label.strip().casefold() for label in labels}


def date_window(today: date, start_value: str | None, end_value: str | None) -> tuple[date, date]:
    """Resolve inclusive ISO date defaults and reject ranges above 90 calendar days."""
    for value in (start_value, end_value):
        if value is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Dates must use ISO calendar format YYYY-MM-DD.")
    start = date.fromisoformat(start_value) if start_value else today
    try:
        end = date.fromisoformat(end_value) if end_value else start + timedelta(days=29)
    except OverflowError as error:
        raise ValueError("Date range exceeds the supported calendar.") from error
    if not 1 <= (end - start).days + 1 <= 90:
        raise ValueError(
            "Date range must be ordered and contain at most 90 inclusive calendar days."
        )
    return start, end


def tool_result(result: ResponseEnvelope) -> CallToolResult:
    """Return structured data alongside concise source-language readable guidance."""
    lines = [
        f"{result.municipality}: {result.capability}",
        f"Coverage: {result.coverage}; outcome: {result.outcome}.",
        f"Build-time snapshot {result.snapshot.discovery_id} "
        f"({result.snapshot.created_at.isoformat()}); validity: {result.snapshot.status}.",
    ]
    for entry in result.data.entries:
        lines.append(f"\n{entry.label.value}" + (f" — {entry.zone.value}" if entry.zone else ""))
        for field in (
            entry.hours,
            entry.instructions,
            entry.contacts,
            entry.locations,
            entry.materials,
        ):
            lines.extend(f"- {fact.value}" for fact in field)
        if entry.purpose:
            lines.append(f"- {entry.purpose.value}")
        for requirement in entry.requirements:
            conditions = "; ".join(item.value for item in requirement.conditions)
            lines.append(f"- {requirement.text.value}" + (f" ({conditions})" if conditions else ""))
        lines.extend(
            f"- Published collection date: {item.value.isoformat()}" for item in entry.dates
        )
    lines.extend(f"Official destination: {handoff.value}" for handoff in result.data.handoffs)
    lines.extend(
        f"{name} choices: {', '.join(values)}" for name, values in result.available_choices.items()
    )
    lines.extend(result.limitations)
    lines.extend(
        f"Source: {citation.url} (retrieved {citation.retrieved_at.isoformat()})"
        for citation in result.evidence
    )
    return CallToolResult(
        content=[TextContent(type="text", text="\n".join(lines))],
        structured_content=result.model_dump(mode="json"),
    )


def create_server(discovery: Discovery) -> MCPServer:
    """Create the fixed tool surface; this function never performs outbound I/O."""
    runtime = SnapshotRuntime(discovery)
    server = MCPServer(
        name=f"Municipality snapshot: {discovery.identity.name.value}",
        instructions=(
            "Read-only build-time municipal snapshot. Cite evidence and preserve limitations; "
            "never describe undated information as current."
        ),
    )
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )

    @server.tool(annotations=annotations)
    def get_office_hours(
        office: TextFilter | None = None,
    ) -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return hours and contacts; optionally match an exact office label or id."""
        return tool_result(runtime.query("office_hours", office=office))

    @server.tool(annotations=annotations)
    def get_garbage_collection(
        waste_type: TextFilter | None = None,
        zone: TextFilter | None = None,
        date_from: TextFilter | None = None,
        date_to: TextFilter | None = None,
    ) -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return waste guidance and published dates.

        ISO date boundaries are inclusive; the default is 30 days and the maximum is 90.
        """
        return tool_result(
            runtime.query(
                "garbage_collection",
                waste_type=waste_type,
                zone=zone,
                date_from=date_from,
                date_to=date_to,
            )
        )

    @server.tool(annotations=annotations)
    def get_recycling_info(
        material: TextFilter | None = None,
    ) -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return disposal routes; optionally match an exact material label or id."""
        return tool_result(runtime.query("recycling", material=material))

    @server.tool(annotations=annotations)
    def get_move_in_requirements() -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return published arrival guidance with all observed conditions, contacts and handoffs."""
        return tool_result(runtime.query("move_in"))

    @server.tool(annotations=annotations)
    def get_move_out_requirements() -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return departure guidance with observed conditions, contacts and handoffs."""
        return tool_result(runtime.query("move_out"))

    @server.tool(annotations=annotations)
    def get_problem_reporting_info(
        category: TextFilter | None = None,
    ) -> Annotated[CallToolResult, ResponseEnvelope]:
        """Return documented reporting channels and purposes; no submissions are performed."""
        return tool_result(runtime.query("problem_reporting", category=category))

    return server


async def check_health(*, port: int = 8000, timeout: float = 3) -> bool:
    """Probe the loopback MCP request loop within a bounded health-check deadline."""
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    if not 1 <= port <= 65535 or timeout <= 0:
        raise ValueError("Health probe requires a valid port and positive timeout.")
    try:
        async with asyncio.timeout(timeout):
            async with create_mcp_http_client() as client:
                # Bound transport cleanup too; the SDK defaults to long SSE reads.
                client.timeout = timeout
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp", http_client=client
                ) as streams:
                    async with ClientSession(*streams, read_timeout_seconds=timeout) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        return {tool.name for tool in result.tools} == set(TOOL_NAMES.values())
    except Exception:
        # Transport task groups may wrap failures; any failed exchange is unhealthy.
        return False


def main() -> None:
    """Launch stdio or loopback HTTP; diagnostics are always written to stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path, required=True)
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument(
        "--check", action="store_true", help="Validate snapshot and tool construction, then exit."
    )
    checks.add_argument(
        "--health-check", action="store_true", help="Probe the running loopback MCP server."
    )
    args = parser.parse_args()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(handlers=[handler], level=logging.WARNING)
    try:
        if args.health_check:
            healthy = asyncio.run(check_health(port=args.port))
            if not healthy:
                logging.getLogger(__name__).error("Loopback MCP health check failed.")
            raise SystemExit(0 if healthy else 1)
        server = create_server(load_discovery(args.discovery))
        if args.check:
            return
        if args.transport == "stdio":
            server.run(transport="stdio")
        else:
            server.run(
                transport="streamable-http",
                host=args.host,
                port=args.port,
                streamable_http_path="/mcp",
            )
    except (OSError, ValueError) as error:
        logging.getLogger(__name__).error(
            "Snapshot server could not start (%s); "
            "validate the discovery artifact and launch options.",
            type(error).__name__,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
