"""Core domain models for the Public AI Challenge pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field


class ScoutedServiceRecord(BaseModel):
    """Normalized service record identified during municipality scouting."""

    name: str = Field(description="The service identifier or name.")
    description: str = Field(default="", description="The service description.")
    urls: list[str] = Field(
        default_factory=list,
        description="Source URLs associated with this service.",
    )
    available: bool = Field(
        default=True,
        description="Whether the service was observed as available.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional scouting metadata (e.g. source role, interaction type).",
    )


class ScoutResult(BaseModel):
    """Normalized result of the scouting phase for a municipality."""

    municipality_name: str
    canton: str
    official_url: str
    services: list[ScoutedServiceRecord] = Field(default_factory=list)
    raw_discovery: Any | None = Field(
        default=None,
        description="Optional reference to the original pipeline-specific discovery object.",
    )


class ServiceInventoryRecord(BaseModel):
    """Normalized synthesized content and structured inventory for a service."""

    service_name: str
    markdown_content: str
    inventory_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured JSON data adhering to mmp-service-inventory schema.",
    )
    source_urls: list[str] = Field(default_factory=list)
    inventory_path: str | Path | None = Field(
        default=None,
        description="Filesystem path where the inventory JSON was written.",
    )
    markdown_path: str | Path | None = Field(
        default=None,
        description="Filesystem path where the markdown documentation was written.",
    )


class JudgeFinding(BaseModel):
    """Finding for a specific claim or field evaluated by the Judge."""

    field: str
    verdict: str  # "pass", "fail", "withheld"
    reason: str
    service_id: str | None = None
    is_injection: bool = False


class JudgeReport(BaseModel):
    """Normalized evaluation report produced by the Judge quality gate."""

    municipality: str
    build_id: str
    passed: bool
    blocked: bool
    block_reason: str | None = None
    coverage_ratio: float = 1.0
    findings: list[JudgeFinding] = Field(default_factory=list)
    withheld_fields: list[dict[str, str]] = Field(default_factory=list)
    raw_result: Any | None = Field(
        default=None,
        description="Original phase3 BuildJudgeResult object if available.",
    )
