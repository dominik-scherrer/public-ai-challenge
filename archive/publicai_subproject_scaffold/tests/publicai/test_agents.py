"""Agent permissions and complete claim review are enforceable contracts."""

import pytest
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from publicai.agents import (
    ClaimCheck,
    ReviewDecision,
    claim_records,
    create_agents,
    validate_review,
)
from publicai.config import Settings


@pytest.fixture(autouse=True)
def prevent_real_model_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


def test_missing_claim_review_is_rejected() -> None:
    decision = ReviewDecision(identity_consistent=True, checks=[], issues=[])
    with pytest.raises(ValueError, match="every claim"):
        validate_review(decision, {"identity.name": {"value": "Testdorf"}})


def test_unrelated_excerpt_cannot_be_approved() -> None:
    decision = ReviewDecision(
        identity_consistent=True,
        checks=[ClaimCheck(path="hours", status="unsupported", reason="Unrelated excerpt")],
        issues=[],
    )
    with pytest.raises(ValueError, match="unsupported"):
        validate_review(decision, {"hours": {"value": "Monday"}})


def test_claim_enumeration_includes_conditions() -> None:
    value = {
        "requirements": [
            {
                "text": {"value": "ID", "evidence": []},
                "conditions": [{"value": "from abroad", "evidence": []}],
            }
        ]
    }
    assert set(claim_records(value)) == {"requirements.0.text", "requirements.0.conditions.0"}


async def test_reviewer_exposes_only_retained_source_reader() -> None:
    def respond(messages: object, info: object) -> ModelResponse:
        assert [tool.name for tool in info.function_tools] == ["read_source"]
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {"identity_consistent": False, "checks": [], "issues": ["test"]},
                )
            ]
        )

    agents = create_agents(Settings(), FunctionModel(respond), FunctionModel(respond))
    result = await agents.reviewer.run("Review empty inventory", deps={})
    assert result.output.identity_consistent is False


def test_review_cannot_skip_denial_or_zone_metadata() -> None:
    records = claim_records(
        {
            "capabilities": {
                "garbage_collection": {
                    "zone_required": True,
                    "missing_reasons": ["explicitly_not_offered"],
                    "not_offered_evidence": [{"source_id": "s1", "excerpt": "Contact us"}],
                    "limitations": ["No collection on Fridays"],
                }
            }
        }
    )
    assert set(records) == {
        "capabilities.garbage_collection.zone_required",
        "capabilities.garbage_collection.missing_reasons",
        "capabilities.garbage_collection.not_offered_evidence",
        "capabilities.garbage_collection.limitations",
    }


def test_retained_conflict_alternatives_can_pass_review() -> None:
    path = "capabilities.office_hours.conflicts.0.claims.0"
    decision = ReviewDecision(
        identity_consistent=True,
        checks=[
            ClaimCheck(path=path, status="conflicting", reason="Source really states alternative")
        ],
    )
    validate_review(decision, {path: {"value": "Monday"}})


def test_inventory_schema_requires_six_named_capability_objects() -> None:
    from publicai.agents import Inventory

    schema = Inventory.model_json_schema()["$defs"]["CapabilityInventory"]
    expected = {
        "office_hours",
        "garbage_collection",
        "recycling",
        "move_in",
        "move_out",
        "problem_reporting",
    }
    assert set(schema["properties"]) == expected
    assert set(schema["required"]) == expected
    assert schema["additionalProperties"] is False
