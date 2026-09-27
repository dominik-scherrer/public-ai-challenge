"""Data structures and models for Gemeinde MCP Pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field, model_validator


# [C_GMP_02_01] [SP_GMP_01_01] ScoutedService
class ScoutedService(BaseModel):
    """Represents a service identified during scouting of a municipality website."""

    name: str = Field(description="The service identifier.")
    description: str = Field(description="The service description.")
    urls: list[str] = Field(
        default_factory=list,
        description="URLs associated with the service (required if available is true).",
    )
    available: bool = Field(description="Indicates if the service is available.")

    @model_validator(mode="after")
    def validate_available_urls(self) -> ScoutedService:
        if self.available:
            if not self.urls or not any(u.strip() for u in self.urls):
                raise ValueError("If available is true, urls must contain at least one valid URL.")
        return self


# [C_GMP_02_01] [SP_GMP_01_02] ServiceInventory
class ServiceInventory(BaseModel):
    """Represents a generated JSON service inventory document conforming to mmp-service-inventory/v0."""

    file_path: str = Field(description="Path to the generated JSON inventory.")
    data: dict[str, Any] = Field(
        description="Contains structured service attributes, contacts, procedures, and evidence."
    )


# [C_GMP_03_01] [SP_GMP_01_03] ServiceProcessingDeps
@dataclass
class ServiceProcessingDeps:
    """Shared dependencies for fetching and LLM calls."""

    http_client: httpx.AsyncClient
    model_name: str = "openai:gpt-4o"


# [C_GMP_02_01] [SP_GMP_01_04] SynthesizedContent
class SynthesizedContent(BaseModel):
    """Represents unified Markdown content synthesized from scraped source fragments."""

    service_name: str = Field(description="Name of the service matching ScoutedService.")
    markdown: str = Field(description="Unified Markdown document.")
    source_urls: list[str] = Field(
        default_factory=list, description="URLs used for synthesis."
    )


# [C_GMP_02_01] [SP_GMP_01_05] ExtractedData
class ExtractedData(BaseModel):
    """Represents the structured inventory data extracted by LLM for a service."""

    service_name: str = Field(description="Name of the service matching ScoutedService.")
    json_data: dict[str, Any] = Field(description="The extracted Service Inventory data.")


# [C_GMP_02_01] [SP_GMP_01_06] ServiceResource
class ServiceResource(BaseModel):
    """Represents a service exposed as an MCP resource."""

    name: str = Field(description="The service identifier.")
    markdown_content: str = Field(description="The Markdown content.")
    tools_module: str | None = Field(
        default=None, description="Path to generated tools module (if applicable)."
    )
