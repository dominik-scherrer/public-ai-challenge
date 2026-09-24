"""Shared snapshot service behavior independent of model providers."""

import asyncio
import re
import sys
from datetime import date
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from publicai.contracts import Discovery, load_discovery
from publicai.runtime import SnapshotRuntime, create_server, date_window


async def test_health_probe_requires_a_responsive_mcp_server() -> None:
    from publicai.runtime import check_health

    fixture = Path(__file__).parents[2] / "src/publicai/fixtures/representative.json"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "publicai.runtime",
        "--discovery",
        str(fixture),
        "--transport",
        "streamable-http",
        "--port",
        "0",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with asyncio.timeout(10):
            while True:
                line = await process.stderr.readline()
                assert line, "Server exited before opening its listener"
                match = re.search(rb"http://127\.0\.0\.1:(\d+)", line)
                if match:
                    port = int(match[1])
                    break
            assert await check_health(port=port)
    finally:
        if process.returncode is None:
            process.terminate()
        await asyncio.wait_for(process.communicate(), timeout=5)
    assert not await check_health(port=port)


async def test_health_probe_times_out_on_unresponsive_listener() -> None:
    from publicai.runtime import check_health

    writers = []

    def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        writers.append(writer)

    server = await asyncio.start_server(connected, "127.0.0.1", 0)
    try:
        async with asyncio.timeout(2):
            assert not await check_health(port=server.sockets[0].getsockname()[1], timeout=0.05)
    finally:
        server.close()
        for writer in writers:
            writer.close()
            await writer.wait_closed()
        await server.wait_closed()


@pytest.fixture
def discovery() -> Discovery:
    return load_discovery(Path(__file__).parents[2] / "src/publicai/fixtures/representative.json")


@pytest.fixture
def runtime(discovery: Discovery) -> SnapshotRuntime:
    return SnapshotRuntime(discovery, today=date(2026, 10, 1))


def test_unknown_filters_offer_exact_choices(runtime: SnapshotRuntime) -> None:
    result = runtime.query("office_hours", office="Unknown")
    assert result.outcome == "unknown_filter"
    assert "Kanzlei" in result.available_choices["office"]
    assert runtime.query("office_hours", office=" KANZLEI ").outcome == "ok"


def test_missing_zone_returns_only_general_guidance(runtime: SnapshotRuntime) -> None:
    result = runtime.query("garbage_collection")
    assert result.outcome == "needs_input"
    assert result.available_choices["zone"] == ["Nord", "Süd"]
    assert not result.data.entries


def test_collection_boundaries_are_inclusive(runtime: SnapshotRuntime) -> None:
    result = runtime.query("garbage_collection", zone="Nord")
    assert result.outcome == "ok"
    assert [item.value for item in result.data.entries[0].dates] == [
        date(2026, 10, 1),
        date(2026, 10, 30),
    ]


def test_partial_coverage_never_claims_no_dates(runtime: SnapshotRuntime) -> None:
    result = runtime.query(
        "garbage_collection", zone="Nord", date_from="2026-11-01", date_to="2026-11-02"
    )
    assert result.outcome == "information_unavailable"
    assert result.data.entries[0].instructions
    result = runtime.query(
        "garbage_collection", zone="Nord", date_from="2026-10-02", date_to="2026-10-03"
    )
    assert result.outcome == "no_matching_dates"


@pytest.mark.parametrize("start,end", [("2026-10-03", "2026-10-02"), ("2026-10-01", "2026-12-30")])
def test_invalid_date_ranges_are_tool_errors(
    runtime: SnapshotRuntime, start: str, end: str
) -> None:
    with pytest.raises(ValueError):
        runtime.query("garbage_collection", zone="Nord", date_from=start, date_to=end)


def test_conditions_and_expired_validity_are_preserved(discovery: Discovery) -> None:
    runtime = SnapshotRuntime(discovery, today=date(2027, 1, 1))
    moving = runtime.query("move_in")
    assert (
        moving.data.entries[0].requirements[0].conditions[0].value == "Bei Zuzug aus dem Ausland."
    )
    assert moving.snapshot.status == "undated"
    waste = runtime.query("garbage_collection", zone="Nord")
    assert waste.snapshot.status == "expired"


@pytest.mark.asyncio
async def test_mcp_preserves_conditional_guidance_in_text_and_structured_output(
    discovery: Discovery,
) -> None:
    server = create_server(discovery)
    result = await server.call_tool("get_move_in_requirements", {})
    assert not result.is_error
    data = result.structured_content
    requirement = data["data"]["entries"][0]["requirements"][0]
    assert requirement["text"]["value"] == "Ausländerausweis vorlegen."
    assert [item["value"] for item in requirement["conditions"]] == ["Bei Zuzug aus dem Ausland."]
    assert {citation["excerpt"] for citation in data["evidence"]} >= {
        "Ausländerausweis vorlegen.",
        "Bei Zuzug aus dem Ausland.",
        "https://portal.example.test/registration",
    }
    text = result.content[0].text
    assert "Ausländerausweis vorlegen. (Bei Zuzug aus dem Ausland.)" in text
    assert "Official destination: https://portal.example.test/registration" in text
    assert "Build-time snapshot fictional-discovery-1" in text


@pytest.mark.parametrize(
    "tool,filter_name,label,identifier,expected_ids",
    [
        ("get_office_hours", "office", "Kanzlei", "kanzlei", ["kanzlei"]),
        (
            "get_garbage_collection",
            "waste_type",
            "Kehricht",
            "kehricht-nord",
            ["kehricht-nord"],
        ),
        ("get_recycling_info", "material", "Glas", "glas", ["glas"]),
        ("get_problem_reporting_info", "category", "Schadenmeldung", "schaden", ["schaden"]),
    ],
)
async def test_mcp_filters_match_exact_labels_and_ids(
    discovery: Discovery,
    tool: str,
    filter_name: str,
    label: str,
    identifier: str,
    expected_ids: list[str],
) -> None:
    """README filters must survive SDK argument forwarding, including rejection of substrings."""
    server = create_server(discovery)
    arguments = (
        {"zone": " nOrD ", "date_from": "2026-10-01", "date_to": "2026-10-30"}
        if filter_name == "waste_type"
        else {}
    )
    for value in (f" {label.upper()} ", identifier):
        result = await server.call_tool(tool, {**arguments, filter_name: value})
        assert not result.is_error
        data = result.structured_content
        assert data["outcome"] == "ok"
        assert [entry["id"] for entry in data["data"]["entries"]] == expected_ids
    for value in (label[:-1], "unknown"):
        result = await server.call_tool(tool, {**arguments, filter_name: value})
        assert not result.is_error
        data = result.structured_content
        assert data["outcome"] == "unknown_filter"
        assert data["data"]["entries"] == []
        assert label in data["available_choices"][filter_name]


def test_date_filtering_does_not_mutate_later_queries(runtime: SnapshotRuntime) -> None:
    """The read-only contract holds across narrow, unzoned, and repeated date queries."""
    narrow = runtime.query(
        "garbage_collection", zone="Nord", date_from="2026-10-30", date_to="2026-10-30"
    )
    assert [item.value for item in narrow.data.entries[0].dates] == [date(2026, 10, 30)]
    assert runtime.query("garbage_collection").outcome == "needs_input"
    south = runtime.query("garbage_collection", zone="Süd")
    assert [entry.id for entry in south.data.entries] == ["kehricht-sued"]
    assert [item.value for item in south.data.entries[0].dates] == [date(2026, 10, 15)]
    for _ in range(2):
        north = runtime.query("garbage_collection", zone="Nord")
        assert [entry.id for entry in north.data.entries] == ["kehricht-nord"]
        assert [item.value for item in north.data.entries[0].dates] == [
            date(2026, 10, 1),
            date(2026, 10, 30),
        ]


@pytest.mark.parametrize(
    "start,end,expected",
    [
        (None, None, (date(2026, 10, 1), date(2026, 10, 30))),
        ("2026-10-15", None, (date(2026, 10, 15), date(2026, 11, 13))),
        (None, "2026-10-05", (date(2026, 10, 1), date(2026, 10, 5))),
        ("2026-10-01", "2026-12-29", (date(2026, 10, 1), date(2026, 12, 29))),
    ],
)
def test_date_defaults_and_ninety_day_inclusive_limit(
    start: str | None, end: str | None, expected: tuple[date, date]
) -> None:
    assert date_window(date(2026, 10, 1), start, end) == expected


def test_undated_collection_keeps_guidance(discovery: Discovery) -> None:
    payload = discovery.model_dump(mode="json")
    waste = payload["capabilities"]["garbage_collection"]
    waste["valid_from"] = waste["valid_to"] = None
    for entry in waste["entries"]:
        entry["dates"] = []
    runtime = SnapshotRuntime(Discovery.model_validate(payload), today=date(2026, 10, 1))
    result = runtime.query("garbage_collection", zone="Nord")
    assert result.outcome == "information_unavailable"
    assert result.coverage == "supported"
    assert result.data.entries[0].instructions
    assert result.snapshot.status == "undated"


@pytest.mark.asyncio
async def test_stdio_transport_negotiates_and_invalid_dates_are_protocol_tool_errors() -> None:
    fixture = Path(__file__).parents[2] / "src/publicai/fixtures/representative.json"
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "publicai.runtime", "--discovery", str(fixture)],
    )
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams, read_timeout_seconds=10) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert len(tools.tools) == 6
            response = await client.call_tool("get_office_hours", {"office": "Kanzlei"})
            assert not response.is_error
            assert response.structured_content["data"]["entries"][0]["hours"][0]["value"] == (
                "Montag 09:00–11:00"
            )
            invalid = await client.call_tool(
                "get_garbage_collection",
                {"date_from": "2026-10-02", "date_to": "2026-10-01"},
            )
            assert invalid.is_error


def test_missing_zone_never_returns_unqualified_collection_dates(discovery: Discovery) -> None:
    payload = discovery.model_dump(mode="json")
    payload["capabilities"]["garbage_collection"]["entries"][0]["zone"] = None
    runtime = SnapshotRuntime(Discovery.model_validate(payload), today=date(2026, 10, 1))
    result = runtime.query("garbage_collection")
    assert result.outcome == "needs_input"
    assert result.data.entries[0].instructions
    assert not result.data.entries[0].dates


def test_unknown_material_offers_discovered_materials_and_collection_point_labels(
    discovery: Discovery,
) -> None:
    payload = discovery.model_dump(mode="json")
    entry = payload["capabilities"]["recycling"]["entries"][0]
    entry["materials"] = [entry["label"]]
    entry["id"] = "sammelstelle-dorfplatz"
    entry["label"] = {
        "value": "Sammelstelle Dorfplatz",
        "evidence": entry["instructions"][0]["evidence"],
    }
    runtime = SnapshotRuntime(Discovery.model_validate(payload))

    result = runtime.query("recycling", material="Unknown")

    assert result.outcome == "unknown_filter"
    assert set(result.available_choices["material"]) == {
        "Glas",
        "Sammelstelle Dorfplatz",
        "sammelstelle-dorfplatz",
    }
    for choice in result.available_choices["material"]:
        assert runtime.query("recycling", material=choice).outcome == "ok"
