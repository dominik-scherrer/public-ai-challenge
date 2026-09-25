import json
from pathlib import Path
import httpx
from pydantic_ai.models.test import TestModel
import pytest

from public_ai_challenge.phase2_synthesis_gemeinde.agents import (
    data_extraction_agent,
    validate_extracted_data,
)
from public_ai_challenge.phase2_synthesis_gemeinde.data_generator import generate_inventory
from public_ai_challenge.phase2_synthesis_gemeinde.models import (
    ExtractedData,
    ScoutedService,
    ServiceProcessingDeps,
)
from pydantic_ai import ModelRetry


def test_validate_extracted_data_valid():
    """Test SP_GMP_05_10: Output validator accepts valid dictionary and ensures schema."""
    extracted = ExtractedData(
        service_name="Anmeldung",
        json_data={"title": "Anmeldung", "fees": []},
    )
    validated = validate_extracted_data(None, extracted)  # type: ignore
    assert validated.json_data["schema"] == "mmp-service-inventory/v0"


def test_validate_extracted_data_invalid():
    """Test SP_GMP_05_10: Output validator rejects invalid data missing title/name."""
    extracted = ExtractedData(
        service_name="Anmeldung",
        json_data={"other_field": 123},
    )
    with pytest.raises(ModelRetry):
        validate_extracted_data(None, extracted)  # type: ignore


@pytest.mark.anyio
async def test_generate_inventory_available_service(tmp_path: Path):
    """Test SP_GMP_05_03 & SP_GMP_05_04: Generates structured inventory with facts & handoffs."""
    service = ScoutedService(
        name="Anmeldung_Wohnsitz",
        description="Residence registration",
        urls=["https://ausserberg.ch/anmeldung"],
        available=True,
    )
    markdown_content = "# Anmeldung Wohnsitz\n\nGebuehr: 20 CHF. Oeffnungszeiten: Mo-Fr 08:00-11:30."
    source_contents = [b"Raw HTML with form fields and requirements"]

    sample_inventory_data = {
        "schema": "mmp-service-inventory/v0",
        "id": "ch.vs.ausserberg.move_in",
        "title": "Anmeldung Wohnsitz",
        "category": "residence_registration",
        "summary": "Online form for registering move-in.",
        "requirements": ["Heimatschein", "Mietvertrag"],
        "fees": [{"amount": 20, "currency": "CHF"}],
        "office_hours": "Mo-Fr 08:00-11:30",
        "handoffs": [{"url": "https://ausserberg.ch/anmeldung", "type": "online_counter"}],
    }

    test_model = TestModel(
        custom_output_args={
            "service_name": "Anmeldung_Wohnsitz",
            "json_data": sample_inventory_data,
        }
    )

    with data_extraction_agent.override(model=test_model):
        deps = ServiceProcessingDeps(http_client=httpx.AsyncClient(), model_name="test")
        inventory = await generate_inventory(
            service,
            markdown_content,
            source_contents,
            deps,
            output_dir=tmp_path,
        )

        assert inventory.data["title"] == "Anmeldung Wohnsitz"
        assert inventory.data["fees"][0]["amount"] == 20
        assert "Heimatschein" in inventory.data["requirements"]
        assert inventory.data["office_hours"] == "Mo-Fr 08:00-11:30"
        assert len(inventory.data["handoffs"]) == 1

        # Check saved JSON file
        out_file = tmp_path / "Anmeldung_Wohnsitz_inventory.json"
        assert out_file.exists()
        saved = json.loads(out_file.read_text(encoding="utf-8"))
        assert saved["id"] == "ch.vs.ausserberg.move_in"


@pytest.mark.anyio
async def test_generate_inventory_unavailable_service(tmp_path: Path):
    """Test minimal inventory output for unavailable service."""
    service = ScoutedService(
        name="Bauberatung",
        description="In-person only",
        urls=[],
        available=False,
    )
    deps = ServiceProcessingDeps(http_client=httpx.AsyncClient(), model_name="test")
    inventory = await generate_inventory(
        service,
        markdown_content="",
        source_contents=[],
        deps=deps,
        output_dir=tmp_path,
    )

    assert inventory.data["status"] == "unavailable"
    assert inventory.data["available"] is False
    out_file = tmp_path / "Bauberatung_inventory.json"
    assert out_file.exists()
