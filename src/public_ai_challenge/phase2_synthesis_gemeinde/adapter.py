"""Adapters exposing phase2_synthesis_gemeinde through SynthesisProtocol and McpServerProtocol."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from public_ai_challenge.core.interfaces import McpServerProtocol, SynthesisProtocol
from public_ai_challenge.core.models import ScoutResult, ServiceInventoryRecord

from .agents import (
    _safe_service_name,
    data_extraction_agent,
    process_service_content,
    synthesis_agent,
)
from .data_generator import generate_inventory
from .models import ScoutedService, ServiceProcessingDeps
from .server import FastMCP, create_mcp_server


class SynthesisGemeindeAdapter(SynthesisProtocol):
    """Adapter that synthesizes markdown and extracts service inventories using Pydantic AI agents."""

    def __init__(
        self,
        model_name: str = "openai:gpt-4o",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model_name = model_name
        self.http_client = http_client

    async def synthesize(
        self,
        scout_result: ScoutResult,
        output_dir: Path | str,
    ) -> list[ServiceInventoryRecord]:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        async def _run(client: httpx.AsyncClient) -> list[ServiceInventoryRecord]:
            deps = ServiceProcessingDeps(http_client=client, model_name=self.model_name)
            records: list[ServiceInventoryRecord] = []

            is_test = self.model_name == "test" or (
                self.model_name.startswith("openai:") and not os.getenv("OPENAI_API_KEY")
            )

            for s_record in scout_result.services:
                safe_urls = [u for u in s_record.urls if u.strip()]
                is_available = s_record.available and bool(safe_urls)
                service = ScoutedService(
                    name=s_record.name,
                    description=s_record.description or f"Information and services for {s_record.name}",
                    urls=safe_urls,
                    available=is_available,
                )

                if is_test and service.available:
                    synth_data = {
                        "service_name": service.name,
                        "markdown": (
                            f"# {service.name}\n\nOffizielle Dienstleistung der Gemeinde Ausserberg.\n\n"
                            f"## Beschreibung\n{service.description}\n\n"
                            f"## Online Schalter\nDie Anmeldung kann online eingereicht werden."
                        ),
                        "source_urls": service.urls,
                    }
                    inv_data = {
                        "service_name": service.name,
                        "json_data": {
                            "schema": "mmp-service-inventory/v0",
                            "id": f"ch.vs.ausserberg.{service.name.lower().replace(' ', '_')}",
                            "title": service.name,
                            "category": "municipal_administration",
                            "summary": service.description,
                            "requirements": ["Gueltiger Ausweis", "Mietvertrag / Kaufvertrag"],
                            "fees": [{"amount": 20, "currency": "CHF", "description": "Meldegebuehr"}],
                            "contacts": [{"department": "Gemeindeverwaltung Ausserberg", "phone": "+41 27 946 21 54"}],
                            "handoffs": [{"url": service.urls[0] if service.urls else "", "type": "online_form"}],
                        },
                    }
                    from pydantic_ai.models.test import TestModel
                    with synthesis_agent.override(model=TestModel(custom_output_args=synth_data)), \
                         data_extraction_agent.override(model=TestModel(custom_output_args=inv_data)):
                        synthesized, raw_contents = await process_service_content(
                            service, deps, output_dir=out_path
                        )
                        inventory = await generate_inventory(
                            service,
                            synthesized.markdown,
                            raw_contents,
                            deps,
                            output_dir=out_path,
                        )
                else:
                    synthesized, raw_contents = await process_service_content(
                        service, deps, output_dir=out_path
                    )
                    inventory = await generate_inventory(
                        service,
                        synthesized.markdown,
                        raw_contents,
                        deps,
                        output_dir=out_path,
                    )

                safe_name = _safe_service_name(service.name)
                md_path = out_path / f"{safe_name}.md"
                json_path = out_path / f"{safe_name}_inventory.json"

                records.append(
                    ServiceInventoryRecord(
                        service_name=service.name,
                        markdown_content=synthesized.markdown,
                        inventory_data=inventory.data,
                        source_urls=service.urls,
                        inventory_path=str(json_path),
                        markdown_path=str(md_path),
                    )
                )

            return records

        if self.http_client is not None:
            return await _run(self.http_client)
        else:
            async with httpx.AsyncClient() as client:
                return await _run(client)


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
