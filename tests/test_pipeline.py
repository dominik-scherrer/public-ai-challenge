import json
from pathlib import Path
import httpx
from pydantic_ai.models.test import TestModel
import pytest

from public_ai_challenge.gemeinde_mcp.agents import (
    data_extraction_agent,
    synthesis_agent,
)
from public_ai_challenge.gemeinde_mcp.pipeline import run_pipeline


@pytest.mark.anyio
async def test_end_to_end_pipeline(tmp_path: Path):
    """Test SP_GMP_05_08 & SP_GMP_05_09: End-to-end pipeline execution from input JSON to running MCP server."""
    # Create input JSON with 2 services
    input_file = tmp_path / "input_services.json"
    services_data = [
        {
            "name": "Wohnsitz_Anmeldung",
            "description": "Move-in registration",
            "urls": ["https://ausserberg.ch/wohnsitz"],
            "available": True,
        },
        {
            "name": "Sonderbewilligung",
            "description": "Special permit offline",
            "urls": [],
            "available": False,
        },
    ]
    input_file.write_text(json.dumps(services_data), encoding="utf-8")

    out_dir = tmp_path / "output"

    html_content = b"<main><h1>Wohnsitz Anmeldung</h1><p>Bitte Formular ausfuellen.</p></main>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html_content, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)

    synth_output = {
        "service_name": "Wohnsitz_Anmeldung",
        "markdown": "# Wohnsitz Anmeldung\n\nBitte Formular ausfuellen.",
        "source_urls": ["https://ausserberg.ch/wohnsitz"],
    }
    inv_output = {
        "service_name": "Wohnsitz_Anmeldung",
        "json_data": {
            "schema": "mmp-service-inventory/v0",
            "title": "Wohnsitz Anmeldung",
            "category": "residence_registration",
            "summary": "Online move-in registration form.",
            "requirements": ["Ausweis"],
        },
    }

    synth_model = TestModel(custom_output_args=synth_output)
    inv_model = TestModel(custom_output_args=inv_output)

    with synthesis_agent.override(model=synth_model), data_extraction_agent.override(model=inv_model):
        async with httpx.AsyncClient(transport=transport) as client:
            server = await run_pipeline(
                input_path=input_file,
                output_dir=out_dir,
                model_name="test",
                http_client=client,
            )

            # Check generated files
            assert (out_dir / "Wohnsitz_Anmeldung.md").exists()
            assert (out_dir / "Wohnsitz_Anmeldung_inventory.json").exists()
            assert (out_dir / "Sonderbewilligung.md").exists()
            assert (out_dir / "Sonderbewilligung_inventory.json").exists()

            # Verify MCP server resources
            res = await server.read_resource("gemeinde://services/Wohnsitz_Anmeldung")
            assert len(res) == 1
            assert "Bitte Formular ausfuellen" in res[0].content

            # Verify MCP server tools
            tool_res = await server.call_tool("list_services", {})
            assert tool_res.is_error is False
            assert "Wohnsitz_Anmeldung" in tool_res.structured_content["result"]
            assert "Sonderbewilligung" in tool_res.structured_content["result"]

            get_res = await server.call_tool("get_service", {"service_name": "Wohnsitz_Anmeldung"})
            assert get_res.is_error is False
            assert get_res.structured_content["result"]["title"] == "Wohnsitz Anmeldung"
