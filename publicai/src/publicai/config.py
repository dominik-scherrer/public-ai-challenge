"""Validated operator settings; website permissions are deliberately not configurable."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from publicai.crawler import CrawlSettings


class ModelSettings(BaseModel):
    """Bound model requests independently from website request budgets."""

    model_config = ConfigDict(extra="forbid")
    provider: Literal["openai"] = "openai"
    discovery_model: str = "gpt-6-sol"
    review_model: str = "gpt-6-luna"
    temperature: float | None = Field(default=None, ge=0, le=2)
    reasoning_effort: Literal["low", "medium", "high"] = "low"
    max_tokens: int = Field(default=32000, ge=512, le=64000)
    timeout: float = Field(default=120, gt=0, le=300)
    retries: int = Field(default=2, ge=0, le=3)
    request_limit: int = Field(default=24, ge=1, le=100)
    tool_calls_limit: int = Field(default=80, ge=1, le=200)
    total_tokens_limit: int = Field(default=250000, ge=1000, le=1000000)


class TelemetrySettings(BaseModel):
    """Explicit opt-in for metadata-only telemetry."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    send_to_logfire: bool = False
    service_name: str = "municipality-factory"


class Settings(BaseModel):
    """Factory settings loaded from an operator-controlled YAML file."""

    model_config = ConfigDict(extra="forbid")
    model: ModelSettings = Field(default_factory=ModelSettings)
    web_search_enabled: bool = False
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    crawl: CrawlSettings = Field(default_factory=CrawlSettings)
    run_timeout: float = Field(default=600, gt=0, le=600)


def load_settings(path: Path | None = None) -> Settings:
    """Load a small YAML document, rejecting misspelled or unsafe settings."""
    if path is None:
        path = Path("config.yaml")
        if not path.exists():
            return Settings()
    if path.stat().st_size > 65536:
        raise ValueError("Configuration exceeds 64 KiB")
    return Settings.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
