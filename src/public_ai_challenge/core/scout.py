"""Core abstractions for Phase 1: Scout."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field

class ScoutedServiceRecord(BaseModel):
    name: str = Field(description="The service identifier or name.")
    description: str = Field(default="", description="The service description.")
    urls: list[str] = Field(default_factory=list, description="Source URLs associated with this service.")
    available: bool = Field(default=True, description="Whether the service was observed as available.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional scouting metadata (e.g. source role, interaction type).")

class ScoutResult(BaseModel):
    municipality_name: str
    canton: str
    official_url: str
    services: list[ScoutedServiceRecord] = Field(default_factory=list)
    raw_discovery: Any | None = Field(default=None, description="Optional reference to the original pipeline-specific discovery object.")

@runtime_checkable
class ScoutProtocol(Protocol):
    async def scout(self, url: str, municipality: str, canton: str, output_dir: Path | str | None = None) -> ScoutResult:
        ...
