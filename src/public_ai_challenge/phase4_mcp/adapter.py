"""Adapter for Phase 4: Serving Verified Services via FastMCP."""

from __future__ import annotations

from pathlib import Path

from public_ai_challenge.core.interfaces import McpServerProtocol
from public_ai_challenge.core.models import ServiceInventoryRecord
from public_ai_challenge.phase4_mcp.server import FastMCP, create_mcp_server


class McpServerGemeindeAdapter(McpServerProtocol):
    """Adapter that serves verified service inventories via FastMCP."""

    def create_server(
        self,
        inventory_records: list[ServiceInventoryRecord],
        output_dir: Path | str,
        server_name: str = "Gemeinde-MMP-Server",
    ) -> FastMCP:
        out_path = Path(output_dir)
        # FastMCP loads markdown and inventory JSON files from output_dir
        return create_mcp_server(output_dir=out_path, server_name=server_name)
