"""Core abstractions for Phase 3: Judge."""
from __future__ import annotations
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from .scout import ScoutResult
from .synthesis import ServiceInventoryRecord

class JudgeFinding(BaseModel):
    field: str
    verdict: str
    reason: str
    service_id: str | None = None
    is_injection: bool = False

class JudgeReport(BaseModel):
    municipality: str
    build_id: str
    passed: bool
    blocked: bool
    block_reason: str | None = None
    coverage_ratio: float = 1.0
    findings: list[JudgeFinding] = Field(default_factory=list)
    withheld_fields: list[dict[str, str]] = Field(default_factory=list)
    raw_result: Any | None = Field(default=None, description="Original phase3 BuildJudgeResult object if available.")

@runtime_checkable
class JudgeProtocol(Protocol):
    async def evaluate(self, inventory_records: list[ServiceInventoryRecord], scout_result: ScoutResult | None = None, dry_run: bool = False) -> JudgeReport:
        ...
