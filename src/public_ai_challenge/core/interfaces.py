"""Abstract interfaces (Protocols) for the main phases of the pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .models import JudgeReport, ScoutResult, ServiceInventoryRecord


@runtime_checkable
class ScoutProtocol(Protocol):
    """Interface for Phase 1: Municipality Website Discovery & Scouting."""

    async def scout(
        self,
        url: str,
        municipality: str,
        canton: str,
        output_dir: Path | str | None = None,
    ) -> ScoutResult:
        """Discover municipal services from official web presence."""
        ...


@runtime_checkable
class SynthesisProtocol(Protocol):
    """Interface for Phase 2: Content Synthesis & Service Inventory Extraction."""

    async def synthesize(
        self,
        scout_result: ScoutResult,
        output_dir: Path | str,
    ) -> list[ServiceInventoryRecord]:
        """Synthesize markdown and extract structured service inventory data."""
        ...


@runtime_checkable
class JudgeProtocol(Protocol):
    """Interface for Phase 3: Provenance, Injection, and Coverage Quality Gate."""

    async def evaluate(
        self,
        inventory_records: list[ServiceInventoryRecord],
        scout_result: ScoutResult | None = None,
        dry_run: bool = False,
    ) -> JudgeReport:
        """Evaluate synthesized inventories against provenance, safety, and coverage."""
        ...


@runtime_checkable
class McpServerProtocol(Protocol):
    """Interface for Phase 4: Serving Verified Services via Model Context Protocol."""

    def create_server(
        self,
        inventory_records: list[ServiceInventoryRecord],
        output_dir: Path | str,
        server_name: str = "Gemeinde-MMP-Server",
    ) -> Any:
        """Create and configure an MCP server hosting the verified services."""
        ...
