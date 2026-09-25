"""Adapter exposing phase3_judge_pipeline through JudgeProtocol."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any

from public_ai_challenge.core.interfaces import JudgeProtocol
from public_ai_challenge.core.models import JudgeFinding, JudgeReport, ScoutResult, ServiceInventoryRecord

from .pipeline import run_judge
from .schemas import BuildJudgeResult


class JudgePipelineAdapter(JudgeProtocol):
    """Adapter that evaluates Service Inventories using the Judge quality gate."""

    def __init__(self, build_floor: float = 0.5) -> None:
        self.build_floor = build_floor

    async def evaluate(
        self,
        inventory_records: list[ServiceInventoryRecord],
        scout_result: ScoutResult | None = None,
        dry_run: bool = True,
    ) -> JudgeReport:
        municipality_name = scout_result.municipality_name if scout_result else "Ausserberg"
        official_url = scout_result.official_url if scout_result else "https://www.ausserberg.ch"

        # Construct consolidated mmp-service-inventory payload
        services_payload = []
        for rec in inventory_records:
            data = rec.inventory_data
            # Handle possible nested 'json_data' or direct dict
            if "json_data" in data and isinstance(data["json_data"], dict):
                service_dict = dict(data["json_data"])
            else:
                service_dict = dict(data)

            # Ensure minimal required fields for the Judge
            if "id" not in service_dict:
                safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in rec.service_name).lower()
                service_dict["id"] = f"ch.vs.{municipality_name.lower()}.{safe_id}"
            if "title" not in service_dict:
                service_dict["title"] = rec.service_name
            if "summary" not in service_dict:
                service_dict["summary"] = service_dict.get("description", "")
            if "source_refs" not in service_dict:
                service_dict["source_refs"] = rec.source_urls

            services_payload.append(service_dict)

        consolidated = {
            "schema": "mmp-service-inventory/v0",
            "build_id": f"{municipality_name.lower()}-build",
            "municipality": {
                "name": municipality_name,
                "official_url": official_url,
            },
            "services": services_payload,
        }

        # Write to temporary file for the Judge adapter to consume
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as tmp:
            json.dump(consolidated, tmp, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        try:
            build_result: BuildJudgeResult = run_judge(
                tmp_path,
                dry_run=dry_run,
                build_floor=self.build_floor,
            )
            return self.to_judge_report(build_result)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @staticmethod
    def to_judge_report(build_result: BuildJudgeResult) -> JudgeReport:
        findings: list[JudgeFinding] = []
        all_withheld: list[dict[str, str]] = []

        for svc in build_result.services:
            for inj in svc.injection_flags:
                if inj.flagged:
                    findings.append(
                        JudgeFinding(
                            field=inj.claim.field,
                            verdict="fail",
                            reason=f"injection: {inj.reason}",
                            service_id=svc.service_id,
                            is_injection=True,
                        )
                    )
            for w in svc.withheld_fields:
                all_withheld.append(w)
                findings.append(
                    JudgeFinding(
                        field=w.get("field", ""),
                        verdict="withheld",
                        reason=w.get("reason", ""),
                        service_id=svc.service_id,
                        is_injection="injection" in w.get("reason", "").lower(),
                    )
                )

        return JudgeReport(
            municipality=build_result.municipality,
            build_id=build_result.build_id,
            passed=not build_result.blocked,
            blocked=build_result.blocked,
            block_reason=build_result.block_reason,
            coverage_ratio=build_result.coverage.ratio,
            findings=findings,
            withheld_fields=all_withheld,
            raw_result=build_result,
        )
