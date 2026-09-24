"""The Judge pipeline: Service Inventory in, judge-report.json out.

Usage:
    uv run python -m judge.pipeline \\
        pipeline/legacy/handoff/delivery-2026-09-24/ausserberg/inventory.json

    # deterministic checks only, no API key / cost required:
    uv run python -m judge.pipeline --dry-run \\
        pipeline/legacy/handoff/delivery-2026-09-24/ausserberg/inventory.json

Decision rule for provenance (docs/architecture/adr/0004, "say less rather
than say something wrong"):
  - no evidence captured for the claim            -> WITHHELD, no model called
  - every configured judge model says "supported" -> PASS
  - any model says "not supported", or fails to
    parse / can't be reached                       -> FAIL (fail closed)

A claim is never shown because one judge liked it; it has to survive all
of them. The ensemble is OpenAI + Apertus (see llm.py); if only one is
actually configured, llm.py's resolve_judge_models() prints a loud
warning rather than silently running as a 1-model "ensemble."
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

from judge.adapters import load_categories, load_claims_from_inventory
from judge.coverage import compute_coverage, load_reference_categories
from judge.injection import deterministic_check
from judge.llm import call_judge_ensemble, load_rubric
from judge.schemas import (
    BuildJudgeResult,
    Claim,
    InjectionFinding,
    ProvenanceVerdict,
    ServiceJudgeResult,
    Verdict,
)

DEFAULT_BUILD_FLOOR = 0.5


def _municipality_domain(inventory_path: Path) -> str:
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    url = payload.get("municipality", {}).get("official_url", "")
    return urlparse(url).netloc.removeprefix("www.") if url else ""


def judge_provenance(claim: Claim, *, dry_run: bool) -> ProvenanceVerdict:
    if claim.evidence_text is None:
        return ProvenanceVerdict(
            claim=claim,
            verdict=Verdict.WITHHELD,
            reason="No source evidence captured for this claim yet.",
        )

    if dry_run:
        return ProvenanceVerdict(
            claim=claim,
            verdict=Verdict.WITHHELD,
            reason="--dry-run: evidence exists but judge models were not called.",
        )

    rubric = load_rubric("provenance_judge")
    results = call_judge_ensemble(
        rubric,
        field=claim.field,
        claim_value=claim.value,
        evidence_text=claim.evidence_text,
        municipality=claim.municipality,
    )

    reasons = []
    for label, parsed in results:
        if parsed is None:
            return ProvenanceVerdict(
                claim=claim,
                verdict=Verdict.FAIL,
                reason=f"Judge '{label}' returned no parseable verdict — failing closed.",
                model=label,
            )
        if parsed.get("supported") is not True:
            return ProvenanceVerdict(
                claim=claim,
                verdict=Verdict.FAIL,
                reason=parsed.get("reason", f"Judge '{label}' did not confirm support."),
                model=label,
            )
        reasons.append(parsed.get("reason", ""))

    return ProvenanceVerdict(
        claim=claim,
        verdict=Verdict.PASS,
        reason="; ".join(r for r in reasons if r) or "All configured judges confirmed support.",
        model=",".join(label for label, _ in results),
    )


def judge_injection(claim: Claim, municipality_domain: str, *, dry_run: bool) -> InjectionFinding:
    deterministic = deterministic_check(claim, municipality_domain)
    if deterministic is not None:
        return deterministic

    if not claim.is_free_text or dry_run:
        return InjectionFinding(
            claim=claim, flagged=False, category="none", reason="", detector="deterministic"
        )

    rubric = load_rubric("injection_judge")
    results = call_judge_ensemble(
        rubric,
        field=claim.field,
        text=str(claim.value),
        municipality_domain=municipality_domain,
    )

    # Fail closed across the whole ensemble, not just the first model: any
    # model flagging, or any model failing to return a parseable verdict,
    # is enough to flag. ADR-0007 says injection "flags -- never passes
    # through" -- that bar has to survive a two-model ensemble the same
    # way it survives one, so agreement is required to clear a claim, not
    # to flag it (the inverse of the unanimity rule in judge_provenance).
    detectors = ",".join(label for label, _ in results)
    for label, parsed in results:
        if parsed is None:
            return InjectionFinding(
                claim=claim,
                flagged=True,
                category="instruction_injection",
                reason=f"Judge '{label}' returned no parseable verdict — flagging for review.",
                detector=detectors,
            )
        if parsed.get("flagged"):
            return InjectionFinding(
                claim=claim,
                flagged=True,
                category="instruction_injection",
                reason=parsed.get("reason", f"Judge '{label}' flagged this text."),
                detector=detectors,
            )

    return InjectionFinding(claim=claim, flagged=False, category="none", reason="", detector=detectors)


def run_judge(
    inventory_path: Path,
    *,
    dry_run: bool = False,
    build_floor: float = DEFAULT_BUILD_FLOOR,
    reference_categories: list[str] | None = None,
) -> BuildJudgeResult:
    build_id, municipality, claims = load_claims_from_inventory(inventory_path)
    domain = _municipality_domain(inventory_path)

    services: dict[str, ServiceJudgeResult] = {}
    for claim in claims:
        result = services.setdefault(claim.service_id, ServiceJudgeResult(service_id=claim.service_id))

        provenance = judge_provenance(claim, dry_run=dry_run)
        injection = judge_injection(claim, domain, dry_run=dry_run)
        result.injection_flags.append(injection)

        if injection.flagged:
            result.withheld_fields.append({"field": claim.field, "reason": f"injection: {injection.reason}"})
        elif provenance.verdict == Verdict.PASS:
            result.kept_fields.append(claim.field)
        else:
            result.withheld_fields.append({"field": claim.field, "reason": provenance.reason})

    categories = load_categories(inventory_path)
    reference = reference_categories if reference_categories is not None else load_reference_categories()
    coverage = compute_coverage(categories, reference)

    blocked = coverage.ratio < build_floor
    return BuildJudgeResult(
        build_id=build_id,
        municipality=municipality,
        services=list(services.values()),
        coverage=coverage,
        build_floor=build_floor,
        blocked=blocked,
        block_reason=(
            f"Coverage {coverage.ratio:.0%} is below the Build Floor of {build_floor:.0%}."
            if blocked
            else None
        ),
    )


def _to_jsonable(result: BuildJudgeResult) -> dict:
    def service_to_dict(s: ServiceJudgeResult) -> dict:
        return {
            "service_id": s.service_id,
            "kept_fields": s.kept_fields,
            "withheld_fields": s.withheld_fields,
            "injection_flags": [
                {"field": f.claim.field, "category": f.category, "reason": f.reason, "detector": f.detector}
                for f in s.injection_flags
                if f.flagged
            ],
        }

    return {
        "schema": "mmp-judge-report/v0",
        "build_id": result.build_id,
        "municipality": result.municipality,
        "blocked": result.blocked,
        "block_reason": result.block_reason,
        "build_floor": result.build_floor,
        "coverage": asdict(result.coverage),
        "services": [service_to_dict(s) for s in result.services],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the MMP Judge over a Service Inventory.")
    parser.add_argument("inventory", type=Path, help="Path to an inventory.json")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: judge-report.json next to the inventory)")
    parser.add_argument("--dry-run", action="store_true", help="Run only deterministic checks; withhold everything that needs a model.")
    parser.add_argument("--build-floor", type=float, default=DEFAULT_BUILD_FLOOR)
    args = parser.parse_args()

    result = run_judge(args.inventory, dry_run=args.dry_run, build_floor=args.build_floor)
    out_path = args.out or args.inventory.parent / "judge-report.json"
    out_path.write_text(json.dumps(_to_jsonable(result), indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Judge report written to {out_path}")
    print(f"Coverage: {result.coverage.ratio:.0%} (floor {result.build_floor:.0%}) -> {'BLOCKED' if result.blocked else 'OK'}")
    for s in result.services:
        print(f"  {s.service_id}: kept={len(s.kept_fields)} withheld={len(s.withheld_fields)} injection_flags={sum(1 for f in s.injection_flags if f.flagged)}")
    return 1 if result.blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
