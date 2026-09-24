"""Validates the actual judge models against the gold set -- the step from
dominik-scherrer/thesis-educational-agent's methodology that must run
before anyone trusts "the Judge is the only quality gate" (ADR-0004) in
production: don't just build a judge, measure it against known-correct
and known-wrong cases first.

Skipped automatically when OPENAI_API_KEY isn't set, so it never blocks
a normal `pytest` run or CI without secrets. Run explicitly with:

    OPENAI_API_KEY=... uv run pytest pipeline/judge/tests/test_gold_set_live.py -v

A failure here means the rubric wording needs work, not necessarily that
the pipeline code is broken -- see pipeline/judge/README.md.
"""

import json
import os
from pathlib import Path

import pytest

from judge.injection import deterministic_check
from judge.pipeline import judge_injection, judge_provenance
from judge.schemas import Claim, Verdict

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set -- skipping live-model gold set validation"
)

GOLD_SET_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_set.json"
GOLD_SET = json.loads(GOLD_SET_PATH.read_text(encoding="utf-8"))
DOMAIN = GOLD_SET["municipality_domain"]


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
    "case",
    [c for c in GOLD_SET["cases"] if "expected_provenance" in c],
    ids=lambda c: c["id"],
)
def test_provenance_judge_against_gold_set(case):
    claim = _claim_from_case(case)
    verdict = judge_provenance(claim, dry_run=False)
    assert verdict.verdict.value == case["expected_provenance"], (
        f"{case['id']}: expected {case['expected_provenance']}, got {verdict.verdict.value} "
        f"(reason: {verdict.reason})"
    )


@pytest.mark.parametrize(
    "case",
    [c for c in GOLD_SET["cases"] if "expected_injection_flagged" in c],
    ids=lambda c: c["id"],
)
def test_injection_judge_against_gold_set(case):
    claim = _claim_from_case(case)
    finding = judge_injection(claim, DOMAIN, dry_run=False)
    assert finding.flagged == case["expected_injection_flagged"], (
        f"{case['id']}: expected flagged={case['expected_injection_flagged']}, "
        f"got {finding.flagged} (reason: {finding.reason})"
    )
