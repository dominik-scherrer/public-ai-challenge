"""Configuration boundaries do not widen the network policy."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from publicai.config import Settings, load_settings


def test_defaults_use_direct_openai_and_disable_telemetry() -> None:
    settings = Settings()
    assert settings.model.provider == "openai"
    assert settings.telemetry.enabled is False


def test_unknown_config_cannot_add_allowed_hosts(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("allowed_hosts: [evil.example]\n")
    with pytest.raises(ValidationError):
        load_settings(path)


def test_missing_explicit_config_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_settings(tmp_path / "missing.yaml")
