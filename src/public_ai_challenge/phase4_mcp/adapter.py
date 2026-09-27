"""Adapter for Phase 4: Serving Verified Services via FastMCP."""

from __future__ import annotations

from pathlib import Path

from public_ai_challenge.core import McpServerProtocol
from public_ai_challenge.core import ServiceInventoryRecord
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
        out_path.mkdir(parents=True, exist_ok=True)
        import json
        for rec in inventory_records:
            if rec.markdown_content:
                md_path = out_path / f"{rec.service_name}.md"
                md_path.write_text(rec.markdown_content, encoding="utf-8")
                rec.markdown_path = str(md_path)
            if rec.inventory_data is not None:
                inv_path = out_path / f"{rec.service_name}_inventory.json"
                inv_path.write_text(json.dumps(rec.inventory_data, indent=2), encoding="utf-8")
                rec.inventory_path = str(inv_path)
                
        # FastMCP loads markdown and inventory JSON files from output_dir
        return create_mcp_server(output_dir=out_path, server_name=server_name)
