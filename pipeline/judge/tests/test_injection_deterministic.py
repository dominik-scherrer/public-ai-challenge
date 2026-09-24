"""Runs the gold set's deterministic-catchable cases through injection.deterministic_check.

No API key required -- these are exactly the cases that must never need a
model to catch (docs/architecture/adr/0007's "flags -- never passes
through"). test_gold_set_live.py covers the subtler, model-only cases.
"""

import json
from pathlib import Path

import pytest

from pipeline.judge.injection import deterministic_check
from pipeline.judge.schemas import Claim

GOLD_SET_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_set.json"
GOLD_SET = json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))
DOMAIN = GOLD_SET["municipality_domain"]

DETERMINISTIC_CASE_IDS = {
    "injection-foreign-link-deterministic",
    "injection-payment-details-deterministic",
    "injection-keyword-deterministic",
    "injection-clean-not-flagged",
    "injection-own-domain-link-not-flagged",
}


def _claim_from_case(case: dict) -> Claim:
    c = case["claim"]
    return Claim(
        service_id=c["service_id"],
        municipality=c["municipality"],
        field=c["field"],
        value=c["value"],
        evidence_text=c.get("evidence_text"),
        is_free_text=c.get("is_free_text", False),
    )


@pytest.mark.parametrize(
    "case", [c for c in GOLD_SET["cases"] if c["id"] in DETERMINISTIC_CASE_IDS], ids=lambda c: c["id"]
)
def test_deterministic_injection_check(case):
    claim = _claim_from_case(case)
    finding = deterministic_check(claim, DOMAIN)
    expected_flagged = case["expected_injection_flagged"]

    if not expected_flagged:
        assert finding is None, f"{case['id']}: expected no flag, got {finding}"
        return

    assert finding is not None, f"{case['id']}: expected a flag, got none"
    assert finding.flagged is True
    if "expected_injection_category" in case:
        assert finding.category == case["expected_injection_category"]
