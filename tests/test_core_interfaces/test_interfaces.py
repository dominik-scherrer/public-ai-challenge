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
from public_ai_challenge.phase1_scout.adapter import FinalScoutAdapter
from public_ai_challenge.phase2_synthesis.adapter import FinalSynthesisAdapter
from public_ai_challenge.phase4_mcp.adapter import McpServerGemeindeAdapter
from public_ai_challenge.phase3_judge.adapter import JudgePipelineAdapter


def test_protocol_conformance():
    """Verify that all phase adapters satisfy their respective Protocol interfaces."""
    assert issubclass(FinalScoutAdapter, ScoutProtocol)
    assert issubclass(FinalSynthesisAdapter, SynthesisProtocol)
    assert issubclass(McpServerGemeindeAdapter, McpServerProtocol)
    assert issubclass(JudgePipelineAdapter, JudgeProtocol)
