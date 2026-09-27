"""Service Inventory generation module."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic_ai import Agent

from .agents import _safe_service_name, data_extraction_agent
from .models import ExtractedData, ScoutedService, ServiceInventory, ServiceProcessingDeps

logger = logging.getLogger(__name__)


# [C_GMP_03_01] [SP_GMP_02_02] generate_inventory
async def generate_inventory(
    service: ScoutedService,
    markdown_content: str,
    source_contents: list[bytes],
    deps: ServiceProcessingDeps,
    output_dir: Path | str = "output",
    agent: Agent[ServiceProcessingDeps, ExtractedData] | None = None,
) -> ServiceInventory:
    """Generate structured Service Inventory JSON for a service.

    Extracts typed service data using LLM analysis and writes the resulting JSON
    inventory file complying with mmp-service-inventory/v0 schema.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_service_name(service.name)
    inv_file = out_path / f"{safe_name}_inventory.json"

    # [SP_GMP_05_02] Unavailable service minimal inventory
    if not service.available or not markdown_content.strip():
        minimal_inventory = {
            "schema": "mmp-service-inventory/v0",
            "service_name": service.name,
            "status": "unavailable",
            "available": False,
        }
        inv_file.write_text(json.dumps(minimal_inventory, indent=2), encoding="utf-8")
        return ServiceInventory(file_path=str(inv_file), data=minimal_inventory)

    active_agent = agent or data_extraction_agent
    sources_summary = "\n\n".join(
        f"Raw Source excerpt {i+1}:\n{content[:1500].decode('utf-8', errors='ignore')}"
        for i, content in enumerate(source_contents[:3])
    )
    prompt = (
        f"Service Name: {service.name}\n"
        f"Service Description: {service.description}\n\n"
        f"Synthesized Markdown:\n{markdown_content}\n\n"
        f"Sources Sample:\n{sources_summary}"
    )

    try:
        result = await active_agent.run(prompt, deps=deps, model=deps.model_name)
        extracted: ExtractedData = result.output
        inventory_data = extracted.json_data
    except Exception as e:
        logger.error("Failed to generate inventory for %s after retries: %s", service.name, e)
        # [SP_GMP_EDGE_02] Fallback minimal inventory on failure
        inventory_data = {
            "schema": "mmp-service-inventory/v0",
            "service_name": service.name,
            "status": "extraction_failed",
            "available": service.available,
            "error": str(e),
        }

    inv_file.write_text(json.dumps(inventory_data, indent=2), encoding="utf-8")
    return ServiceInventory(file_path=str(inv_file), data=inventory_data)
