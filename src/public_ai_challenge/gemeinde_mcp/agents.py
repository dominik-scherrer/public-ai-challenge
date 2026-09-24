"""PydanticAI agents and content processing for Gemeinde MCP Pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Tuple

from pydantic_ai import Agent, ModelRetry, RunContext

from .extraction import convert_to_markdown, fetch_content
from .models import ExtractedData, ScoutedService, ServiceProcessingDeps, SynthesizedContent

logger = logging.getLogger(__name__)

# [C_GMP_03_01] [SP_GMP_02_01] synthesis_agent
synthesis_agent: Agent[ServiceProcessingDeps, SynthesizedContent] = Agent(
    model="openai:gpt-4o",
    deps_type=ServiceProcessingDeps,
    output_type=SynthesizedContent,
    system_prompt=(
        "You are a documentation specialist. Synthesize the provided Markdown "
        "fragments into a single, cohesive, well-structured Markdown document. "
        "Remove redundancies and organize the information logically. Preserve all "
        "factual details, URLs, contact information, and official references."
    ),
    retries=2,
    defer_model_check=True,
)


def _safe_service_name(name: str) -> str:
    """Generate a filesystem-safe filename stem for a service."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)


# [C_GMP_03_01] [SP_GMP_02_01] process_service_content
async def process_service_content(
    service: ScoutedService,
    deps: ServiceProcessingDeps,
    output_dir: Path | str = "output",
    agent: Agent[ServiceProcessingDeps, SynthesizedContent] | None = None,
) -> Tuple[SynthesizedContent, List[bytes]]:
    """Extract content from service URLs and synthesize a single Markdown document.

    Handles availability checks, URL fetching, fallback for network errors,
    fragment persistence, and synthesized document generation.
    """
    out_path = Path(output_dir)
    fragments_dir = out_path / "fragments"
    out_path.mkdir(parents=True, exist_ok=True)
    fragments_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_service_name(service.name)
    md_file = out_path / f"{safe_name}.md"
    inventory_file = out_path / f"{safe_name}_inventory.json"

    # [SP_GMP_05_02] Unavailable service handling
    if not service.available:
        unavailable_text = (
            f"# {service.name}\n\n"
            "This service is currently unavailable for online interaction."
        )
        md_file.write_text(unavailable_text, encoding="utf-8")
        minimal_inventory = {
            "schema": "mmp-service-inventory/v0",
            "service_name": service.name,
            "status": "unavailable",
            "available": False,
        }
        inventory_file.write_text(json.dumps(minimal_inventory, indent=2), encoding="utf-8")
        return (
            SynthesizedContent(
                service_name=service.name,
                markdown=unavailable_text,
                source_urls=[],
            ),
            [],
        )

    fragments: list[str] = []
    raw_contents: list[bytes] = []
    successful_urls: list[str] = []

    for url in service.urls:
        try:
            content, content_type = await fetch_content(url, deps.http_client)
            md = convert_to_markdown(content, content_type)
            url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
            fragment_file = fragments_dir / f"{safe_name}__{url_hash}.md"
            fragment_file.write_text(md, encoding="utf-8")

            fragments.append(f"### Source: {url}\n\n{md}")
            raw_contents.append(content)
            successful_urls.append(url)
        except Exception as e:
            logger.warning("Error fetching URL '%s' for service '%s': %s", url, service.name, e)
            continue

    # [SP_GMP_EDGE_01] Fallback if all URL fetches fail
    if not fragments:
        unavailable_text = (
            f"# {service.name}\n\n"
            "This service content could not be retrieved from official sources."
        )
        md_file.write_text(unavailable_text, encoding="utf-8")
        minimal_inventory = {
            "schema": "mmp-service-inventory/v0",
            "service_name": service.name,
            "status": "unavailable",
            "available": False,
        }
        inventory_file.write_text(json.dumps(minimal_inventory, indent=2), encoding="utf-8")
        return (
            SynthesizedContent(
                service_name=service.name,
                markdown=unavailable_text,
                source_urls=[],
            ),
            [],
        )

    active_agent = agent or synthesis_agent
    prompt = (
        f"Service: {service.name}\n"
        f"Description: {service.description}\n\n"
        "Source Content Fragments:\n"
        + "\n\n---\n\n".join(fragments)
    )

    result = await active_agent.run(prompt, deps=deps, model=deps.model_name)
    synthesized: SynthesizedContent = result.output

    # Ensure source_urls reflects successful sources if not populated by agent
    if not synthesized.source_urls:
        synthesized.source_urls = successful_urls

    md_file.write_text(synthesized.markdown, encoding="utf-8")
    return synthesized, raw_contents


# [C_GMP_03_01] [SP_GMP_02_02] data_extraction_agent
data_extraction_agent: Agent[ServiceProcessingDeps, ExtractedData] = Agent(
    model="openai:gpt-4o",
    deps_type=ServiceProcessingDeps,
    output_type=ExtractedData,
    system_prompt=(
        "You are an expert municipal service data extractor. "
        "Analyze the provided service description, synthesized markdown, and raw source materials. "
        "Extract structured service attributes conforming to mmp-service-inventory/v0. "
        "Your output must include a dictionary json_data containing:\n"
        "- schema: 'mmp-service-inventory/v0'\n"
        "- id: canonical service id\n"
        "- title: official title of the service\n"
        "- category: service category\n"
        "- summary: brief summary\n"
        "- requirements: list of conditions/prerequisites\n"
        "- fees: list of fees/costs\n"
        "- documents: list of required documents\n"
        "- contacts: list of responsible departments/contacts\n"
        "- handoffs: list of online forms or external portals\n"
        "Ensure all facts are supported by the sources without hallucination."
    ),
    retries=3,
    defer_model_check=True,
)


# [C_GMP_03_01] [SP_GMP_02_02] [SP_GMP_05_10] validate_extracted_data
@data_extraction_agent.output_validator
def validate_extracted_data(
    ctx: RunContext[ServiceProcessingDeps], output: ExtractedData
) -> ExtractedData:
    """Validate that extracted data is a valid dictionary and conforms to schema requirements."""
    if not isinstance(output.json_data, dict) or not output.json_data:
        raise ModelRetry("json_data must be a non-empty dictionary structure.")
    if "title" not in output.json_data and "name" not in output.json_data:
        raise ModelRetry("json_data must contain at least a 'title' or 'name' field.")
    if "schema" not in output.json_data:
        output.json_data["schema"] = "mmp-service-inventory/v0"
    return output

