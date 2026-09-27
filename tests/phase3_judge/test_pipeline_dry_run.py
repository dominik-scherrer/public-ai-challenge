"""End-to-end pipeline test with --dry-run: no API key needed, no network calls.

Runs the real Ausserberg seed delivery through run_judge(). Because that
data currently has no evidence text (see test_adapters.py), every claim
should come back withheld, and coverage against the placeholder reference
list should be computable either way.
"""

from pathlib import Path

from public_ai_challenge.phase3_judge.pipeline import run_judge

_h1 = Path(__file__).resolve().parents[2] / "archive" / "pipeline_legacy" / "handoff" / "delivery-2026-09-24"
_h2 = Path(__file__).resolve().parents[2] / "pipeline" / "legacy" / "handoff" / "delivery-2026-09-24"
_handoff = _h1 if _h1.exists() else _h2
AUSSERBERG = _handoff / "ausserberg" / "inventory.json"


def test_dry_run_withholds_everything_without_evidence():
    result = run_judge(AUSSERBERG, dry_run=True)
    assert result.services, "expected at least one service result"
    for service in result.services:
        assert service.kept_fields == [], (
            f"{service.service_id}: dry-run must never pass a claim, "
            f"got kept_fields={service.kept_fields}"
        )


def test_dry_run_never_calls_a_model():
    """--dry-run must work with no OPENAI_API_KEY at all -- this is the point of the flag."""
    import os

    had_key = os.environ.pop("OPENAI_API_KEY", None)
    try:
        run_judge(AUSSERBERG, dry_run=True)  # must not raise
    finally:
        if had_key is not None:
            os.environ["OPENAI_API_KEY"] = had_key


def test_coverage_is_computed_against_reference_list():
    result = run_judge(AUSSERBERG, dry_run=True)
    assert 0.0 <= result.coverage.ratio <= 1.0
    assert isinstance(result.blocked, bool)
