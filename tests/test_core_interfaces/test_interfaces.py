"""Tests verifying core pipeline interfaces and phase adapters."""

import pytest
from pathlib import Path

from public_ai_challenge.core.interfaces import (
    JudgeProtocol,
    McpServerProtocol,
    ScoutProtocol,
    SynthesisProtocol,
)
from public_ai_challenge.core.models import (
    JudgeReport,
    ScoutedServiceRecord,
    ScoutResult,
    ServiceInventoryRecord,
)
from public_ai_challenge.phase1_scout_pipeline.adapter import (
    FileScoutAdapter,
    ScoutPipelineAdapter,
)
from public_ai_challenge.phase2_synthesis_gemeinde.adapter import (
    McpServerGemeindeAdapter,
    SynthesisGemeindeAdapter,
)
from public_ai_challenge.phase3_judge_pipeline.adapter import JudgePipelineAdapter


def test_protocol_conformance():
    """Verify that all phase adapters satisfy their respective Protocol interfaces."""
    assert issubclass(ScoutPipelineAdapter, ScoutProtocol)
    assert issubclass(FileScoutAdapter, ScoutProtocol)
    assert issubclass(SynthesisGemeindeAdapter, SynthesisProtocol)
    assert issubclass(McpServerGemeindeAdapter, McpServerProtocol)
    assert issubclass(JudgePipelineAdapter, JudgeProtocol)


@pytest.mark.asyncio
async def test_file_scout_adapter(tmp_path: Path):
    """Verify FileScoutAdapter correctly loads and parses scouted services."""
    json_file = tmp_path / "mock_scout.json"
    json_file.write_text(
        """[
            {"name": "Test Service", "description": "A test service", "urls": ["https://example.com"], "available": true}
        ]""",
        encoding="utf-8",
    )

    adapter = FileScoutAdapter(json_file)
    result = await adapter.scout(
        url="https://example.com",
        municipality="TestGemeinde",
        canton="VS",
    )

    assert isinstance(result, ScoutResult)
    assert result.municipality_name == "TestGemeinde"
    assert result.canton == "VS"
    assert len(result.services) == 1
    assert result.services[0].name == "Test Service"
    assert result.services[0].available is True


@pytest.mark.asyncio
async def test_judge_pipeline_adapter():
    """Verify JudgePipelineAdapter evaluates service inventory records."""
    adapter = JudgePipelineAdapter(build_floor=0.0)

    records = [
        ServiceInventoryRecord(
            service_name="Test Service",
            markdown_content="# Test Service",
            inventory_data={
                "id": "ch.vs.test.test_service",
                "title": "Test Service",
                "category": "municipal_administration",
                "summary": "Official test service.",
                "fees": [],
            },
            source_urls=["https://example.com"],
        )
    ]

    report = await adapter.evaluate(inventory_records=records, dry_run=True)
    assert isinstance(report, JudgeReport)
    assert report.municipality == "Ausserberg"
    assert report.passed is True
    assert not report.blocked
