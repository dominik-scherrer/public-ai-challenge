"""Core abstractions for Phase 4: MCP Serving."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from .synthesis import ServiceInventoryRecord

@runtime_checkable
class McpServerProtocol(Protocol):
    def create_server(self, inventory_records: list[ServiceInventoryRecord], output_dir: Path | str, server_name: str = "Gemeinde-MMP-Server") -> Any:
        ...
