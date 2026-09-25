"""Core interfaces and domain models for Public AI Challenge."""

from .interfaces import (
    JudgeProtocol,
    McpServerProtocol,
    ScoutProtocol,
    SynthesisProtocol,
)
from .models import (
    JudgeFinding,
    JudgeReport,
    ScoutedServiceRecord,
    ScoutResult,
    ServiceInventoryRecord,
)

__all__ = [
    "JudgeProtocol",
    "McpServerProtocol",
    "ScoutProtocol",
    "SynthesisProtocol",
    "JudgeFinding",
    "JudgeReport",
    "ScoutedServiceRecord",
    "ScoutResult",
    "ServiceInventoryRecord",
]
