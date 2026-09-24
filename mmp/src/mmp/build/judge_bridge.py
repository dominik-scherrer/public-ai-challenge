"""Runs the team's Judge (``pipeline/judge``) over a v1 Service Inventory.

The Judge is the only quality gate (ADR-0004). This module does not
re-implement it: it feeds the Judge's own ``judge_claims`` with Claims from
``judge.adapters.load_claims_from_mmp_v1`` and applies the verdicts —
withheld attributes are removed and recorded, a flagged injection drops the
attribute, and coverage below the Build Floor blocks the whole Build.

Two modes:

- ``full``: provenance (LLM entailment) + injection + coverage. Needs a
  judge model (``OPENAI_API_KEY`` and/or ``PUBLIC_AI_*``, see pipeline/judge).
- ``deterministic``: no model available. Injection's deterministic checks and
  coverage run; provenance is *not* claimed. The Build is published with
  ``judge.status = "not_run"`` and every Service Card says so. This is the
  honest fallback, not a pass.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from judge.adapters import load_categories_from_mmp_v1, load_claims_from_mmp_v1
from judge.coverage import compute_coverage, load_reference_categories
from judge.injection import deterministic_check
from judge.llm import resolve_judge_models
from judge.pipeline import DEFAULT_BUILD_FLOOR, _to_jsonable, judge_claims

from mmp.schema import Inventory, JudgeStatus, WithheldAttribute


def _categories(inventory: Inventory) -> list[str]:
    payload = inventory.dump()
    categories = load_categories_from_mmp_v1(payload)
    if any(s.opening_hours for s in inventory.services):
        categories.append("office_hours")
    if inventory.municipality.general_contact or any(s.responsible for s in inventory.services):
        categories.append("municipal_contact")
    return categories


def _remove(inventory: Inventory, service_id: str, field: str, reason: str) -> None:
    service = inventory.service(service_id)
    if service is None:
        return
    if field == "summary":
        service.summary, service.summary_evidence = None, []
    elif field in {"responsible", "deadline", "opening_hours"}:
        setattr(service, field, None)
    elif "[" in field:
        name, key = field[:-1].split("[", 1)
        items = getattr(service, name, None)
        if isinstance(items, list):
            if name == "documents":
                setattr(service, name, [d for d in items if d.id != key])
            elif key.isdigit() and int(key) < len(items):
                items.pop(int(key))
    elif field == "title":
        # A title that fails the injection check makes the whole Service unsafe to show.
        inventory.services = [s for s in inventory.services if s.id != service_id]
        return
    service.withheld.append(WithheldAttribute(field=field, reason=f"Judge: {reason}"))


def run(
    inventory: Inventory,
    *,
    mode: Literal["full", "deterministic"],
    report_path: Path,
    allowed_domains: tuple[str, ...],
    build_floor: float = DEFAULT_BUILD_FLOOR,
) -> tuple[Inventory, bool, str | None]:
    """Returns (judged inventory, blocked, block_reason). Writes the judge report."""
    payload = inventory.dump()
    build_id, municipality, claims = load_claims_from_mmp_v1(payload)
    domain = inventory.municipality.official_domains[0]
    other_domains = tuple(inventory.municipality.official_domains[1:]) + allowed_domains
    categories = _categories(inventory)

    if mode == "full":
        models = resolve_judge_models()
        result = judge_claims(
            claims,
            build_id=build_id,
            municipality=municipality,
            domain=domain,
            categories=categories,
            build_floor=build_floor,
            allowed_domains=other_domains,
        )
        withheld = [(s.service_id, w["field"], w["reason"]) for s in result.services for w in s.withheld_fields]
        report = _to_jsonable(result)
        coverage, blocked, reason = result.coverage.ratio, result.blocked, result.block_reason
        status = JudgeStatus(status="passed", models=models, coverage=coverage)
    else:
        withheld = []
        for claim in claims:
            finding = deterministic_check(claim, domain, other_domains)
            if finding is not None:
                withheld.append((claim.service_id, claim.field, f"{finding.category}: {finding.reason}"))
        cov = compute_coverage(categories, load_reference_categories())
        coverage = cov.ratio
        blocked = coverage < build_floor
        reason = f"Coverage {coverage:.0%} is below the Build Floor of {build_floor:.0%}." if blocked else None
        report = {
            "schema": "mmp-judge-report/v0",
            "build_id": build_id,
            "municipality": municipality,
            "mode": "deterministic-only (no judge model configured; provenance NOT judged)",
            "blocked": blocked,
            "block_reason": reason,
            "build_floor": build_floor,
            "coverage": {"ratio": coverage, "mapped": cov.mapped, "unmapped_reference": cov.unmapped_reference},
            "injection_withheld": [{"service_id": s, "field": f, "reason": r} for s, f, r in withheld],
        }
        status = JudgeStatus(status="not_run", coverage=coverage)

    def _index(item: tuple[str, str, str]) -> int:
        field = item[1]
        key = field[field.find("[") + 1 : -1] if "[" in field else ""
        return int(key) if key.isdigit() else -1

    # highest list index first, so popping one item never shifts another's index
    for service_id, field, reason in sorted(withheld, key=_index, reverse=True):
        _remove(inventory, service_id, field, reason)

    report["judged_at"] = datetime.now(UTC).isoformat()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    status.report = report_path.name
    inventory.build.judge = status
    return inventory, blocked, reason
