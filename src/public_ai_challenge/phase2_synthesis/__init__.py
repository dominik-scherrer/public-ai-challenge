"""Gemeinde MCP Pipeline package."""

from .agents import data_extraction_agent, process_service_content, synthesis_agent
from .data_generator import generate_inventory
from .extraction import (
    convert_to_markdown,
    extract_html_to_markdown,
    extract_pdf_to_markdown,
    fetch_content,
)
from .models import (
    ExtractedData,
    ScoutedService,
    ServiceInventory,
    ServiceProcessingDeps,
    ServiceResource,
    SynthesizedContent,
)
from .pipeline import run_pipeline
from public_ai_challenge.phase4_mcp.server import FastMCP, create_mcp_server

__all__ = [
    "ScoutedService",
    "ServiceInventory",
    "ServiceProcessingDeps",
    "SynthesizedContent",
    "ExtractedData",
    "ServiceResource",
    "fetch_content",
    "extract_html_to_markdown",
    "extract_pdf_to_markdown",
    "convert_to_markdown",
    "synthesis_agent",
    "data_extraction_agent",
    "process_service_content",
    "generate_inventory",
    "FastMCP",
    "create_mcp_server",
    "run_pipeline",
]
