import json
from pathlib import Path
import httpx
from pydantic_ai.models.test import TestModel
import pytest

from public_ai_challenge.gemeinde_mcp.agents import process_service_content, synthesis_agent
from public_ai_challenge.gemeinde_mcp.models import ScoutedService, ServiceProcessingDeps


@pytest.mark.anyio
async def test_process_unavailable_service(tmp_path: Path):
    """Test SP_GMP_05_02: Unavailable service generates unavailable markdown and minimal inventory."""
    service = ScoutedService(
        name="Bauberatung",
        description="Building consultation service currently unavailable online.",
        urls=[],
        available=False,
    )
    deps = ServiceProcessingDeps(http_client=httpx.AsyncClient(), model_name="test")

    synthesized, raw_contents = await process_service_content(service, deps, output_dir=tmp_path)

    assert synthesized.service_name == "Bauberatung"
    assert "currently unavailable" in synthesized.markdown.lower()
    assert len(raw_contents) == 0

    md_file = tmp_path / "Bauberatung.md"
    assert md_file.exists()
    assert "unavailable" in md_file.read_text(encoding="utf-8").lower()

    inventory_file = tmp_path / "Bauberatung_inventory.json"
    assert inventory_file.exists()
    inv_data = json.loads(inventory_file.read_text(encoding="utf-8"))
    assert inv_data["status"] == "unavailable"
    assert inv_data["available"] is False


@pytest.mark.anyio
async def test_process_service_fetch_failure_fallback(tmp_path: Path):
    """Test SP_GMP_EDGE_01: Network failure on all URLs falls back to unavailable behavior."""
    service = ScoutedService(
        name="Wohnsitz",
        description="Move registration",
        urls=["https://invalid.domain.local/move"],
        available=True,
    )

    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(failing_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        deps = ServiceProcessingDeps(http_client=client, model_name="test")
        synthesized, raw_contents = await process_service_content(service, deps, output_dir=tmp_path)

        assert "could not be retrieved" in synthesized.markdown.lower()
        assert len(raw_contents) == 0
        md_file = tmp_path / "Wohnsitz.md"
        assert md_file.exists()


@pytest.mark.anyio
async def test_process_available_service_synthesis(tmp_path: Path):
    """Test SP_GMP_05_01: Available service synthesized markdown is cohesive and saves fragments."""
    service = ScoutedService(
        name="Miete_Gemeindeanlagen",
        description="Facility rental",
        urls=["https://ausserberg.ch/anlage"],
        available=True,
    )

    html_content = b"""
    <main>
        <h1>Miete Gemeindeanlagen Ausserberg</h1>
        <p>Die Mehrzweckhalle kann gemietet werden. Kosten betragen 200 CHF pro Tag.</p>
    </main>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html_content, headers={"content-type": "text/html"})

    transport = httpx.MockTransport(handler)
    test_output_data = {
        "service_name": "Miete_Gemeindeanlagen",
        "markdown": "# Miete Gemeindeanlagen Ausserberg\n\nDie Mehrzweckhalle kann gemietet werden. Kosten: 200 CHF pro Tag.",
        "source_urls": ["https://ausserberg.ch/anlage"],
    }

    test_model = TestModel(custom_output_args=test_output_data)

    with synthesis_agent.override(model=test_model):
        async with httpx.AsyncClient(transport=transport) as client:
            deps = ServiceProcessingDeps(http_client=client, model_name="test")
            synthesized, raw_contents = await process_service_content(
                service, deps, output_dir=tmp_path
            )

            assert synthesized.service_name == "Miete_Gemeindeanlagen"
            assert "Miete Gemeindeanlagen Ausserberg" in synthesized.markdown
            assert "<main>" not in synthesized.markdown
            assert "<p>" not in synthesized.markdown
            assert len(raw_contents) == 1

            # Verify fragment saved
            fragments = list((tmp_path / "fragments").glob("*.md"))
            assert len(fragments) == 1
            assert "Miete Gemeindeanlagen Ausserberg" in fragments[0].read_text(encoding="utf-8")

            # Verify synthesized output file saved
            out_md = tmp_path / "Miete_Gemeindeanlagen.md"
            assert out_md.exists()
            assert "# Miete Gemeindeanlagen Ausserberg" in out_md.read_text(encoding="utf-8")
