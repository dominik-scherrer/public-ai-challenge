"""Core domain models and interfaces for the Public AI Challenge pipeline."""
from .scout import ScoutedServiceRecord, ScoutResult, ScoutProtocol
from .synthesis import ServiceInventoryRecord, SynthesisProtocol
from .judge import JudgeFinding, JudgeReport, JudgeProtocol
from .mcp import McpServerProtocol

__all__ = [
    "ScoutedServiceRecord", "ScoutResult", "ScoutProtocol",
    "ServiceInventoryRecord", "SynthesisProtocol",
    "JudgeFinding", "JudgeReport", "JudgeProtocol",
    "McpServerProtocol"
]
