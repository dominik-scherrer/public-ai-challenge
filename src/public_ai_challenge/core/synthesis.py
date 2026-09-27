"""Core abstractions for Phase 2: Synthesis."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel, Field
from .scout import ScoutResult

class ServiceInventoryRecord(BaseModel):
    service_name: str
    markdown_content: str
    inventory_data: dict[str, Any] = Field(default_factory=dict, description="Structured JSON data adhering to mmp-service-inventory schema.")
    source_urls: list[str] = Field(default_factory=list)
    inventory_path: str | Path | None = Field(default=None, description="Filesystem path where the inventory JSON was written.")
    markdown_path: str | Path | None = Field(default=None, description="Filesystem path where the markdown documentation was written.")

@runtime_checkable
class SynthesisProtocol(Protocol):
    async def synthesize(self, scout_result: ScoutResult, output_dir: Path | str) -> list[ServiceInventoryRecord]:
        ...
