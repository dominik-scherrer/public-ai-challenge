import json
from pathlib import Path
import pytest
import httpx
from pydantic import ValidationError

from public_ai_challenge.phase2_synthesis.models import (
    ScoutedService,
    ServiceInventory,
    ServiceProcessingDeps,
    SynthesizedContent,
    ExtractedData,
    ServiceResource,
)


def test_models_import():
    assert ScoutedService is not None
    assert ServiceInventory is not None
    assert ServiceProcessingDeps is not None
    assert SynthesizedContent is not None
    assert ExtractedData is not None
    assert ServiceResource is not None


def test_scouted_services_json_parsing():
    input_path = Path(__file__).parent / "fixtures" / "scouted_services.json"
    assert input_path.exists()

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    services = [ScoutedService.model_validate(item) for item in data]
    assert len(services) == 3
    assert services[0].name == "Anmeldung Wohnsitz"
    assert services[0].available is True
    assert len(services[0].urls) == 1
    assert services[2].name == "Bauberatung"
    assert services[2].available is False
    assert len(services[2].urls) == 0


def test_scouted_service_invariant_available_without_urls_fails():
    with pytest.raises(ValidationError):
        ScoutedService(
            name="Invalid Service",
            description="Service available without urls",
            available=True,
            urls=[],
        )


def test_synthesized_content_and_extracted_data():
    synth = SynthesizedContent(
        service_name="Anmeldung Wohnsitz",
        markdown="# Anmeldung Wohnsitz\n\nSynthesized content...",
        source_urls=["https://example.com/move-in"],
    )
    assert synth.service_name == "Anmeldung Wohnsitz"
    assert len(synth.source_urls) == 1

    extracted = ExtractedData(
        service_name="Anmeldung Wohnsitz",
        json_data={"schema": "mmp-service-inventory/v0", "title": "Anmeldung Wohnsitz"},
    )
    assert extracted.service_name == "Anmeldung Wohnsitz"
    assert extracted.json_data["schema"] == "mmp-service-inventory/v0"


def test_service_processing_deps():
    client = httpx.AsyncClient()
    deps = ServiceProcessingDeps(http_client=client, model_name="openai:gpt-4o")
    assert deps.http_client is client
    assert deps.model_name == "openai:gpt-4o"
