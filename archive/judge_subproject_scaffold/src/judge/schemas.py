"""Data model for the Judge.

Plain dataclasses on purpose: pydantic isn't a repo dependency yet (Scout's
PR #13 may add it), and this module needs to be importable without waiting
on that merge. Revisit once pydantic lands on main.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    """A judge's decision on one claim. No numeric score — see docs/architecture/adr/0004."""

    PASS = "pass"
    FAIL = "fail"
    WITHHELD = "withheld"  # not judged wrong — judged *unsupported*, so it never renders


@dataclass(frozen=True)
class Claim:
    """One attribute of one service, as extracted, with whatever evidence backs it.

    This is the Judge's internal unit of work. It is deliberately narrower
    than the full Service Inventory record (see pipeline/SERVICE_MODEL.md /
    pipeline/PROVENANCE_AND_TRUST.md) so the Judge doesn't have to track
    every schema revision the ingestion side makes — see adapters.py.
    """

    service_id: str
    municipality: str
    field: str  # e.g. "fees[0].amount", "requirements", "summary"
    value: Any
    source_refs: tuple[str, ...] = ()
    evidence_text: str | None = None  # exact supporting quote, if any was captured
    is_free_text: bool = False  # True for fields a citizen-facing LLM might render verbatim


@dataclass
class ProvenanceVerdict:
    claim: Claim
    verdict: Verdict
    reason: str
    model: str | None = None  # None when withheld without calling a model (no evidence)


@dataclass
class InjectionFinding:
    claim: Claim
    flagged: bool
    category: str  # "instruction_injection" | "foreign_domain_link" | "payment_details" | "none"
    reason: str
    detector: str  # "deterministic" | "<model name>"


@dataclass
class ServiceJudgeResult:
    service_id: str
    kept_fields: list[str] = field(default_factory=list)
    withheld_fields: list[dict[str, str]] = field(default_factory=list)  # [{field, reason}]
    injection_flags: list[InjectionFinding] = field(default_factory=list)

    @property
    def blocked_by_injection(self) -> bool:
        return any(f.flagged for f in self.injection_flags)


@dataclass
class CoverageResult:
    mapped: list[str]
    unmapped_reference: list[str]
    extra_categories: list[str]  # produced by the Build but not in the reference list
    ratio: float  # len(mapped) / len(reference_categories), 0.0 if reference is empty


@dataclass
class BuildJudgeResult:
    build_id: str
    municipality: str
    services: list[ServiceJudgeResult]
    coverage: CoverageResult
    build_floor: float
    blocked: bool
    block_reason: str | None = None
