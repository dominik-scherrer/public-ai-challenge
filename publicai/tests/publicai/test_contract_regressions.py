"""Independent publication-boundary and fixed-protocol regression checks."""

import copy
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from publicai.contracts import Discovery
from publicai.runtime import SnapshotRuntime, create_server


def test_recycling_point_must_be_in_structured_location_field() -> None:
    from publicai.contracts import Capability, EvidenceRef, Fact, ServiceEntry, classify_coverage

    evidence = [EvidenceRef(source_id="source-1", excerpt="Glas: Sammelstelle Testplatz")]
    point = Fact(value="Sammelstelle Testplatz", evidence=evidence)
    entry = ServiceEntry(
        id="glass",
        label=point,
        materials=[Fact(value="Glas", evidence=evidence)],
    )
    capability = Capability(coverage="partial", entries=[entry])
    assert classify_coverage("recycling", capability) == "partial"
    entry.locations = [point]
    assert classify_coverage("recycling", capability) == "supported"


@pytest.fixture
def payload() -> dict[str, Any]:
    """Load an independently authored, explicitly fictional inventory."""
    source = Path(__file__).parents[2] / "src/publicai/fixtures/representative.json"
    return json.loads(source.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "source_url",
    [
        "https://www.ausserberg.ch/?session=private-value",
        "https://www.ausserberg.ch/unsafe%0apath",
        "https://www.ausserberg.ch/unsafe\\path",
        "https://www.ausserberg.ch/route;session=private-value",
        "https://www.ausserberg.ch:80/",
    ],
)
def test_imported_sources_cannot_bypass_crawler_url_policy(
    payload: dict[str, Any], source_url: str
) -> None:
    """An imported artifact cannot publish source URLs the crawler forbids retaining."""
    payload["sources"][0]["url"] = source_url

    with pytest.raises(ValidationError):
        Discovery.model_validate(payload)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://[::1]/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost/private",
        "http://0x7f.0.0.1/admin",
        "http://%31%32%37.0.0.1/admin",
        "http://[ff02::1]/admin",
        "http://[2002:7f00:1::]/admin",
        "https://portal.example.test/registration?session=private-value",
        "https://portal.example.test/unsafe%0apath",
    ],
)
def test_official_handoffs_exclude_local_and_session_bearing_urls(
    payload: dict[str, Any], url: str
) -> None:
    """Retained evidence is not permission to recommend private or credential-bearing URLs."""
    source = payload["sources"][1]
    source["text"] += "\n" + url
    source["sha256"] = hashlib.sha256(source["text"].encode()).hexdigest()
    source["links"].append(url)
    payload["capabilities"]["move_in"]["handoffs"] = [
        {"value": url, "evidence": [{"source_id": source["id"], "excerpt": url}]}
    ]

    with pytest.raises(ValidationError):
        Discovery.model_validate(payload)


def test_identity_requires_two_distinct_page_urls(payload: dict[str, Any]) -> None:
    """Duplicating one page with another ID is not homepage/contact corroboration."""
    payload["sources"][1]["url"] = payload["sources"][0]["url"]

    with pytest.raises(ValidationError):
        Discovery.model_validate(payload)


def test_homepage_kind_cannot_be_assigned_to_an_arbitrary_service_page(
    payload: dict[str, Any],
) -> None:
    """A source label must not let an imported inventory skip the homepage identity check."""
    payload["sources"][0]["url"] = "https://www.ausserberg.ch/some-service"

    with pytest.raises(ValidationError):
        Discovery.model_validate(payload)


def test_known_zone_entries_require_a_zone_even_if_agent_omits_flag(
    payload: dict[str, Any],
) -> None:
    """A defaulted model flag must not turn zone-specific dates into general answers."""
    payload["capabilities"]["garbage_collection"]["zone_required"] = False
    runtime = SnapshotRuntime(Discovery.model_validate(payload), today=date(2026, 10, 1))

    result = runtime.query("garbage_collection")

    assert result.outcome == "needs_input"
    assert result.available_choices["zone"] == ["Nord", "Süd"]
    assert not result.data.entries


def test_conflicting_claim_cannot_return_with_whitespace_reformatting(
    payload: dict[str, Any],
) -> None:
    """Formatting variations cannot reintroduce a known disputed fact as definitive."""
    capability = payload["capabilities"]["office_hours"]
    original = copy.deepcopy(capability["entries"][0]["hours"][0])
    capability["coverage"] = "partial"
    capability["conflicts"] = [{"field": "hours", "claims": [original, original]}]
    capability["entries"][0]["hours"][0]["value"] = "Montag   09:00–11:00"

    with pytest.raises(ValidationError, match="disputed"):
        Discovery.model_validate(payload)


def test_missing_zone_returns_guidance_without_any_dated_entries(
    payload: dict[str, Any],
) -> None:
    """General entries must not leak unfiltered dates while a required zone is missing."""
    capability = payload["capabilities"]["garbage_collection"]
    general = copy.deepcopy(capability["entries"][0])
    general["id"] = "general-guidance"
    general["zone"] = None
    capability["entries"].append(general)
    runtime = SnapshotRuntime(Discovery.model_validate(payload), today=date(2026, 10, 1))

    result = runtime.query("garbage_collection", date_from="2026-10-01", date_to="2026-10-01")

    assert result.outcome == "needs_input"
    assert len(result.data.entries) == 1
    assert result.data.entries[0].instructions
    assert result.data.entries[0].dates == []


@pytest.mark.asyncio
async def test_six_protocol_signatures_match_the_literal_catalogue(
    payload: dict[str, Any],
) -> None:
    """Expected public contracts must not be derived from the implementation's mapping."""
    expected = {
        "get_office_hours": {"office"},
        "get_garbage_collection": {"waste_type", "zone", "date_from", "date_to"},
        "get_recycling_info": {"material"},
        "get_move_in_requirements": set(),
        "get_move_out_requirements": set(),
        "get_problem_reporting_info": {"category"},
    }
    tools = await create_server(Discovery.model_validate(payload)).list_tools()

    assert {tool.name for tool in tools} == set(expected)
    for tool in tools:
        assert set(tool.input_schema["properties"]) == expected[tool.name]
        assert not tool.input_schema.get("required")
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.idempotent_hint is True
        assert tool.annotations.open_world_hint is False
        assert set(tool.output_schema["properties"]) == {
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
