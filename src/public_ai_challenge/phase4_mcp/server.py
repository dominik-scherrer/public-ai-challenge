"""MCP Server implementation serving synthesized municipal resources and inventory data."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from mcp.server.mcpserver import MCPServer

logger = logging.getLogger(__name__)

# Alias for backwards compatibility with spec naming
FastMCP = MCPServer


# [C_GMP_02_01] [SP_GMP_02_03] create_mcp_server
def create_mcp_server(
    output_dir: Path | str = "output",
    server_name: str = "Gemeinde-MCP",
) -> MCPServer:
    """Create and configure an MCP server with municipal resources and inventory query tools.

    - Registers Markdown documents under URI 'gemeinde://services/{name}'
    - Exposes query tools for structured service inventory data
    - Implements cross-service tools: list_services, search_services, get_service
    """
    out_path = Path(output_dir)
    server = MCPServer(server_name)

    # In-memory storage for loaded resources and inventories
    markdown_registry: Dict[str, str] = {}
    inventory_registry: Dict[str, Dict[str, Any]] = {}

    if out_path.exists():
        # Load all markdown documentation files
        for md_file in out_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                markdown_registry[md_file.stem] = content
            except Exception as e:
                logger.error("Failed to read markdown file %s: %s", md_file, e)

        # Load all service inventory JSON files
        for inv_file in out_path.glob("*_inventory.json"):
            try:
                data = json.loads(inv_file.read_text(encoding="utf-8"))
                # Base service name by stripping '_inventory'
                service_stem = inv_file.stem.removesuffix("_inventory")
                inventory_registry[service_stem] = data
            except Exception as e:
                logger.error("Failed to read inventory file %s: %s", inv_file, e)

    # [SP_GMP_05_05] [SP_GMP_05_06] Dynamic resource handler
    @server.resource("gemeinde://services/{name}")
    def get_service_resource(name: str) -> str:
        """Return the synthesized Markdown documentation for a municipal service."""
        if name in markdown_registry:
            return markdown_registry[name]
        md_file = out_path / f"{name}.md"
        if md_file.exists():
            return md_file.read_text(encoding="utf-8")
        return f"# Service Not Found\n\nNo documentation found for service '{name}'."

    # Register individual concrete resources so they show in list_resources
    for service_name, content in markdown_registry.items():
        def _make_concrete(svc_content: str, svc_name: str):
            @server.resource(
                f"gemeinde://services/{svc_name}",
                name=f"Service: {svc_name}",
                description=f"Synthesized official documentation for {svc_name}",
                mime_type="text/markdown",
            )
            def _concrete_res() -> str:
                return svc_content

        _make_concrete(content, service_name)

    # [SP_GMP_05_09] Cross-service tool: list_services
    @server.tool(name="list_services", description="List all municipal services available on this server.")
    def list_services() -> List[str]:
        """Return list of service identifiers available on this municipality server."""
        services = sorted(set(list(markdown_registry.keys()) + list(inventory_registry.keys())))
        return services

    # [SP_GMP_05_07] Query tool: get_service
    @server.tool(name="get_service", description="Retrieve structured inventory data for a specific service.")
    def get_service(service_name: str) -> Dict[str, Any]:
        """Get the full structured inventory data for the named service."""
        if service_name in inventory_registry:
            return inventory_registry[service_name]
        return {
            "error": "service_not_found",
            "service_name": service_name,
            "message": f"Service '{service_name}' was not found in municipal inventory.",
        }

    # Cross-service tool: search_services
    @server.tool(name="search_services", description="Search municipal services by keyword or phrase.")
    def search_services(query: str) -> List[Dict[str, Any]]:
        """Search across service titles, summaries, and categories."""
        q = query.lower().strip()
        matches: list[dict[str, Any]] = []

        for name, data in inventory_registry.items():
            title = str(data.get("title", "")).lower()
            summary = str(data.get("summary", "")).lower()
            category = str(data.get("category", "")).lower()
            desc = str(data.get("description", "")).lower()

            if q in title or q in summary or q in category or q in desc or q in name.lower():
                matches.append({
                    "service_name": name,
                    "title": data.get("title", name),
                    "summary": data.get("summary", ""),
                    "category": data.get("category", ""),
                    "status": data.get("status", "supported"),
                })
        return matches

    return server


def main() -> None:
    """CLI entrypoint to start the Gemeinde MCP Server."""
    parser = argparse.ArgumentParser(description="Start the Gemeinde MCP Server.")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Path to directory containing synthesized markdown and inventory files (default: output)",
    )
    parser.add_argument(
        "--name",
        default="Gemeinde-MCP",
        help="Server name identifier (default: Gemeinde-MCP)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    args = parser.parse_args()

    server = create_mcp_server(output_dir=args.output_dir, server_name=args.name)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
