"""Evidence and version boundary regression tests using fictional content."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from publicai.contracts import Discovery, packaging_issues


@pytest.fixture
def discovery_payload() -> dict:
    """Read deliberately fictional examples, never live municipal findings."""
    path = Path(__file__).parents[2] / "src/publicai/fixtures/representative.json"
    return json.loads(path.read_text())


def test_all_six_supported_examples_pass(discovery_payload: dict) -> None:
    discovery = Discovery.model_validate(discovery_payload)
    assert len(discovery.capabilities) == 6
    assert packaging_issues(discovery) == []
    assert Discovery.model_validate_json(discovery.model_dump_json()) == discovery


@pytest.mark.parametrize("mutation", ["version", "hash", "excerpt", "source", "identity", "host"])
def test_invalid_evidence_is_rejected(discovery_payload: dict, mutation: str) -> None:
    if mutation == "version":
        discovery_payload["contract_version"] = "99"
    elif mutation == "hash":
        discovery_payload["sources"][0]["sha256"] = "0" * 64
    elif mutation == "excerpt":
        discovery_payload["identity"]["contact"]["evidence"][0]["excerpt"] = "invented quote"
    elif mutation == "source":
        discovery_payload["identity"]["contact"]["evidence"][0]["source_id"] = "missing"
    elif mutation == "identity":
        discovery_payload["identity"]["name"]["value"] = "Different municipality"
    else:
        discovery_payload["sources"][0]["url"] = "https://example.org/"
    with pytest.raises(ValidationError):
        Discovery.model_validate(discovery_payload)


def test_supported_coverage_requires_minimum(discovery_payload: dict) -> None:
    discovery_payload["capabilities"]["office_hours"]["entries"][0]["hours"] = []
    with pytest.raises(ValidationError, match="coverage"):
        Discovery.model_validate(discovery_payload)
    discovery_payload["capabilities"]["office_hours"]["coverage"] = "partial"
    Discovery.model_validate(discovery_payload)


def test_handoff_and_unavailable_examples(discovery_payload: dict) -> None:
    capability = discovery_payload["capabilities"]["move_in"]
    capability["entries"] = []
    capability["coverage"] = "handoff_only"
    discovery_payload["capabilities"]["move_out"] = {
        "coverage": "unavailable",
        "missing_reasons": ["not_found"],
    }
    discovery = Discovery.model_validate(discovery_payload)
    assert discovery.capabilities["move_in"].coverage == "handoff_only"
    assert discovery.capabilities["move_out"].coverage == "unavailable"


def test_conflicting_fact_cannot_be_returned_definitively(discovery_payload: dict) -> None:
    capability = discovery_payload["capabilities"]["office_hours"]
    disputed = capability["entries"][0]["hours"][0]
    capability["coverage"] = "partial"
    capability["conflicts"] = [{"field": "hours", "claims": [disputed, disputed]}]
    with pytest.raises(ValidationError, match="disputed"):
        Discovery.model_validate(discovery_payload)


def test_external_handoff_must_be_linked_by_retained_source(discovery_payload: dict) -> None:
    for source in discovery_payload["sources"]:
        source["links"] = []
    with pytest.raises(ValidationError, match="linked"):
        Discovery.model_validate(discovery_payload)


def test_pending_review_blocks_packaging_only(discovery_payload: dict) -> None:
    discovery_payload["review"]["status"] = "pending"
    discovery = Discovery.model_validate(discovery_payload)
    assert "Semantic review must pass before packaging." in packaging_issues(discovery)


def test_identity_cannot_relabel_one_page_as_two_sources(discovery_payload: dict) -> None:
    discovery_payload["sources"][1]["url"] = discovery_payload["sources"][0]["url"]
    with pytest.raises(ValidationError, match="distinct"):
        Discovery.model_validate(discovery_payload)


def test_unversioned_inventory_is_not_silently_interpreted(discovery_payload: dict) -> None:
    del discovery_payload["contract_version"]
    with pytest.raises(ValidationError, match="contract_version"):
        Discovery.model_validate(discovery_payload)
