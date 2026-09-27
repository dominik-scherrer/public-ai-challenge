"""End-to-End Pipeline runner and CLI for Gemeinde MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv
import httpx

load_dotenv()

from .agents import process_service_content
from .data_generator import generate_inventory
from .models import ScoutedService, ServiceProcessingDeps
from public_ai_challenge.phase4_mcp.server import FastMCP, create_mcp_server

logger = logging.getLogger(__name__)


# [C_GMP_02_02] [SP_GMP_05_08] run_pipeline
async def run_pipeline(
    input_path: Path | str = "input/scouted_services.json",
    output_dir: Path | str = "output",
    model_name: str = "openai:gpt-4o",
    http_client: httpx.AsyncClient | None = None,
) -> FastMCP:
    """Run the complete end-to-end Gemeinde MCP pipeline.

    1. Loads and validates scouted services from input JSON.
    2. Sequentially processes each service: fetching URLs, synthesizing Markdown.
    3. Generates structured Service Inventory JSON conforming to mmp-service-inventory/v0.
    4. Initializes and configures the FastMCP/MCPServer with all generated resources and tools.
    """
    in_file = Path(input_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_file.exists():
        raise FileNotFoundError(f"Input file '{input_path}' not found.")

    with open(in_file, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list):
        raise ValueError("Input file must contain a JSON list of scouted services.")

    services: List[ScoutedService] = [ScoutedService.model_validate(item) for item in raw_data]
    logger.info("Loaded %d scouted services from %s", len(services), in_file)

    async def _execute_with_client(client: httpx.AsyncClient) -> FastMCP:
        deps = ServiceProcessingDeps(http_client=client, model_name=model_name)

        for service in services:
            logger.info("Processing service '%s' (available=%s)...", service.name, service.available)
            # Stage 2 -> Content Extraction & Synthesis
            synthesized, raw_contents = await process_service_content(
                service, deps, output_dir=out_dir
            )

            # Stage 3 -> Inventory Generation
            await generate_inventory(
                service,
                synthesized.markdown,
                raw_contents,
                deps,
                output_dir=out_dir,
            )

        # Stage 4 -> MCP Server initialization
        server = create_mcp_server(output_dir=out_dir)
        return server

    if http_client is not None:
        return await _execute_with_client(http_client)
    else:
        async with httpx.AsyncClient() as client:
            return await _execute_with_client(client)


def main() -> None:
    """CLI entry point for the Gemeinde MCP pipeline."""
    parser = argparse.ArgumentParser(description="Run the Gemeinde MCP Pipeline.")
    parser.add_argument(
        "--input",
        "-i",
        default="input/scouted_services.json",
        help="Path to scouted services JSON file (default: input/scouted_services.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="output",
        help="Path to output directory (default: output)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="openai:gpt-4o",
        help="Language model identifier (default: openai:gpt-4o)",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the MCP server immediately upon pipeline completion",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default="stdio",
        help="MCP server transport mode if --serve is specified (default: stdio)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    server = asyncio.run(
        run_pipeline(
            input_path=args.input,
            output_dir=args.output,
            model_name=args.model,
        )
    )

    if args.serve:
        logger.info("Starting MCP server with transport '%s'...", args.transport)
        server.run(transport=args.transport)


if __name__ == "__main__":
    main()
