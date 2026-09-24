"""Gemeinde MCP Pipeline package."""

from .agents import process_service_content, synthesis_agent
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
    "process_service_content",
]
