import json
from pathlib import Path
import pytest

from public_ai_challenge.phase2_synthesis_gemeinde.server import create_mcp_server


@pytest.fixture
def mock_output_dir(tmp_path: Path) -> Path:
    # Service 1
    (tmp_path / "Anmeldung_Wohnsitz.md").write_text(
        "# Anmeldung Wohnsitz\n\nOfficial move-in instructions.", encoding="utf-8"
    )
    inv1 = {
        "schema": "mmp-service-inventory/v0",
        "title": "Anmeldung Wohnsitz",
        "category": "residence_registration",
        "summary": "Online move-in registration.",
        "fees": [{"amount": 20, "currency": "CHF"}],
    }
    (tmp_path / "Anmeldung_Wohnsitz_inventory.json").write_text(
        json.dumps(inv1), encoding="utf-8"
    )

    # Service 2
    (tmp_path / "Miete_Gemeindeanlagen.md").write_text(
        "# Miete Gemeindeanlagen\n\nRental details.", encoding="utf-8"
    )
    inv2 = {
        "schema": "mmp-service-inventory/v0",
        "title": "Miete Gemeindeanlagen",
        "category": "facility_rental",
        "summary": "Community hall rental.",
    }
    (tmp_path / "Miete_Gemeindeanlagen_inventory.json").write_text(
        json.dumps(inv2), encoding="utf-8"
    )

    # Service 3 (unavailable)
    (tmp_path / "Bauberatung.md").write_text(
        "# Bauberatung\n\nThis service is unavailable.", encoding="utf-8"
    )
    inv3 = {
        "schema": "mmp-service-inventory/v0",
        "title": "Bauberatung",
        "status": "unavailable",
        "available": False,
    }
    (tmp_path / "Bauberatung_inventory.json").write_text(
        json.dumps(inv3), encoding="utf-8"
    )

    return tmp_path


@pytest.mark.anyio
async def test_mcp_server_resources(mock_output_dir: Path):
    """Test SP_GMP_05_05 & SP_GMP_05_06: Resources registered and reading returns correct content."""
    server = create_mcp_server(output_dir=mock_output_dir, server_name="Test-Server")

    # Read specific service resource
    res = await server.read_resource("gemeinde://services/Anmeldung_Wohnsitz")
    assert len(res) == 1
    assert "Official move-in instructions." in res[0].content

    res2 = await server.read_resource("gemeinde://services/Miete_Gemeindeanlagen")
    assert len(res2) == 1
    assert "Rental details." in res2[0].content


@pytest.mark.anyio
async def test_mcp_server_list_services_tool(mock_output_dir: Path):
    """Test SP_GMP_05_09: list_services tool returns all loaded services."""
    server = create_mcp_server(output_dir=mock_output_dir)

    result = await server.call_tool("list_services", {})
    assert result.is_error is False
    assert "Anmeldung_Wohnsitz" in result.structured_content["result"]
    assert "Miete_Gemeindeanlagen" in result.structured_content["result"]
    assert "Bauberatung" in result.structured_content["result"]


@pytest.mark.anyio
async def test_mcp_server_get_service_tool(mock_output_dir: Path):
    """Test SP_GMP_05_07: get_service returns structured inventory data."""
    server = create_mcp_server(output_dir=mock_output_dir)

    result = await server.call_tool("get_service", {"service_name": "Anmeldung_Wohnsitz"})
    assert result.is_error is False
    data = result.structured_content["result"]
    assert data["title"] == "Anmeldung Wohnsitz"
    assert data["category"] == "residence_registration"
    assert data["fees"][0]["amount"] == 20

    # Non-existent service returns error dictionary
    result_err = await server.call_tool("get_service", {"service_name": "unknown_svc"})
    assert "error" in result_err.structured_content["result"]


@pytest.mark.anyio
async def test_mcp_server_search_services_tool(mock_output_dir: Path):
    """Test search_services across titles and categories."""
    server = create_mcp_server(output_dir=mock_output_dir)

    search_res = await server.call_tool("search_services", {"query": "rental"})
    assert search_res.is_error is False
    matches = search_res.structured_content["result"]
    assert len(matches) == 1
    assert matches[0]["service_name"] == "Miete_Gemeindeanlagen"
