"""Offline maintained conformance checks using independently authored fictional examples."""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from publicai.contracts import CAPABILITY_IDS, Discovery, load_discovery
from publicai.runtime import TOOL_NAMES, ResponseEnvelope, SnapshotRuntime, create_server


def check_conformance(discovery_path: Path | None = None) -> list[str]:
    """Check fixed expected behavior and each package's real MCP tool contracts.

    Args:
        discovery_path: Optional generated inventory to check alongside the maintained fixture.

    Returns:
        Diagnostic failures; an empty list means every check passed.
    """
    fixture_path = Path(__file__).parent / "fixtures" / "representative.json"
    fixture = load_discovery(fixture_path)
    failures = _fixture_checks(fixture)
    candidate = load_discovery(discovery_path) if discovery_path else fixture
    failures.extend(asyncio.run(_mcp_checks(fixture, candidate)))
    return failures


def _fixture_checks(discovery: Discovery) -> list[str]:
    """Use explicit expectations based on the fictional source text, not extraction output."""
    failures = []
    runtime = SnapshotRuntime(discovery, today=date(2026, 10, 1))
    if runtime.query("office_hours", office="unknown").outcome != "unknown_filter":
        failures.append("Unknown office filters must be explicit.")
    if (
        runtime.query("office_hours", office=" KANZLEI ").data.entries[0].hours[0].value
        != "Montag 09:00–11:00"
    ):
        failures.append("Office labels must match after case and whitespace normalization.")
    unzoned = runtime.query("garbage_collection")
    if unzoned.outcome != "needs_input" or unzoned.data.entries:
        failures.append("Zone-dependent dates must not be returned without a zone.")
    if unzoned.available_choices.get("zone") != ["Nord", "Süd"]:
        failures.append("Missing zone choices.")
    waste = runtime.query("garbage_collection", zone="Nord")
    if [item.value for item in waste.data.entries[0].dates] != [
        date(2026, 10, 1),
        date(2026, 10, 30),
    ]:
        failures.append("Default inclusive 30-day interval lost boundary dates.")
    complete_empty = runtime.query(
        "garbage_collection", zone="Nord", date_from="2026-10-02", date_to="2026-10-03"
    )
    if complete_empty.outcome != "no_matching_dates":
        failures.append("Explicitly covered empty intervals must return no_matching_dates.")
    incomplete = runtime.query(
        "garbage_collection", zone="Nord", date_from="2026-11-01", date_to="2026-11-02"
    )
    if (
        incomplete.outcome != "information_unavailable"
        or not incomplete.data.entries[0].instructions
    ):
        failures.append("Uncovered intervals must retain guidance without claiming no collection.")
    moving = runtime.query("move_in")
    if moving.data.entries[0].requirements[0].conditions[0].value != "Bei Zuzug aus dem Ausland.":
        failures.append("Conditional requirements lost their conditions.")
    if moving.snapshot.status != "undated":
        failures.append("Undated snapshots must not be labelled current.")
    expired = SnapshotRuntime(discovery, today=date(2027, 1, 1)).query(
        "garbage_collection", zone="Nord"
    )
    if expired.snapshot.status != "expired":
        failures.append("Expired validity must be explicit.")
    for start, end in [("2026-10-03", "2026-10-02"), ("2026-10-01", "2026-12-30")]:
        try:
            runtime.query("garbage_collection", zone="Nord", date_from=start, date_to=end)
        except ValueError:
            pass
        else:
            failures.append("Invalid or oversized date ranges must be tool errors.")
    return failures


async def _mcp_checks(fixture: Discovery, candidate: Discovery) -> list[str]:
    """Exercise actual SDK tool registration, JSON schemas and structured tool calls."""
    failures = []
    expected_signatures = {
        "get_office_hours": {"office"},
        "get_garbage_collection": {"waste_type", "zone", "date_from", "date_to"},
        "get_recycling_info": {"material"},
        "get_move_in_requirements": set(),
        "get_move_out_requirements": set(),
        "get_problem_reporting_info": {"category"},
    }
    expected_envelope = {
        "municipality",
        "capability",
        "coverage",
        "outcome",
        "data",
        "evidence",
        "retrieved_at",
        "snapshot",
        "limitations",
        "available_choices",
    }
    expected_server = create_server(fixture)
    server = create_server(candidate)
    expected = {tool.name: tool for tool in await expected_server.list_tools()}
    actual = {tool.name: tool for tool in await server.list_tools()}
    if set(actual) != set(expected_signatures):
        failures.append("Package does not expose exactly the six standard tools.")
        return failures
    for capability in CAPABILITY_IDS:
        name = TOOL_NAMES[capability]
        tool = actual[name]
        if (
            set(tool.input_schema.get("properties", {})) != expected_signatures[name]
            or tool.input_schema.get("required")
            or set((tool.output_schema or {}).get("properties", {})) != expected_envelope
        ):
            failures.append(f"Tool signature differs from the fixed catalogue: {name}.")
        if (
            tool.input_schema != expected[name].input_schema
            or tool.output_schema != expected[name].output_schema
        ):
            failures.append(f"Tool schema differs from the maintained contract: {name}.")
        if not tool.annotations or (
            tool.annotations.read_only_hint is not True
            or tool.annotations.destructive_hint is not False
            or tool.annotations.idempotent_hint is not True
            or tool.annotations.open_world_hint is not False
        ):
            failures.append(f"Tool read-only/offline annotations missing: {name}.")
        result = await server.call_tool(name, {})
        if result.is_error or not result.structured_content or not result.content:
            failures.append(f"Tool has no successful structured and readable response: {name}.")
            continue
        envelope = ResponseEnvelope.model_validate(result.structured_content)
        if (
            envelope.capability != capability
            or envelope.snapshot.discovery_id != candidate.discovery_id
        ):
            failures.append(f"Tool response has incorrect snapshot identity: {name}.")
        if not envelope.evidence or "Build-time snapshot" not in result.content[0].text:
            failures.append(f"Tool response lacks evidence or an explicit snapshot label: {name}.")
    return failures


def main() -> None:
    """Run the maintained checks and emit diagnostics exclusively to stderr."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", type=Path)
    args = parser.parse_args()
    try:
        failures = check_conformance(args.discovery)
    except (OSError, ValueError) as error:
        print(f"Conformance could not complete: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print("Shared conformance checks passed.", file=sys.stderr)


if __name__ == "__main__":
    main()
