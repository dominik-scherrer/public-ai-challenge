"""Coverage check — how much of the expected service set did this Build produce?

Feeds the Build Floor decision (docs/architecture/adr/0004): "The threshold
below which a whole Build is blocked and the previous Build stays live
(e.g. coverage drops sharply), because it signals a site relaunch rather
than content change."

Deterministic — no LLM involved. See config/reference_categories.yml for
why the reference list is a placeholder.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from public_ai_challenge.phase3_judge.schemas import CoverageResult

_local_cfg = Path(__file__).resolve().parent / "config" / "reference_categories.yml"
DEFAULT_REFERENCE_PATH = _local_cfg if _local_cfg.exists() else Path(__file__).resolve().parent.parent.parent / "config" / "reference_categories.yml"


def load_reference_categories(path: Path = DEFAULT_REFERENCE_PATH) -> list[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(raw.get("categories", []))


def compute_coverage(build_categories: list[str], reference_categories: list[str]) -> CoverageResult:
    build_set = set(build_categories)
    reference_set = set(reference_categories)

    mapped = sorted(build_set & reference_set)
    unmapped_reference = sorted(reference_set - build_set)
    extra_categories = sorted(build_set - reference_set)
    ratio = (len(mapped) / len(reference_set)) if reference_set else 0.0

    return CoverageResult(
        mapped=mapped,
        unmapped_reference=unmapped_reference,
        extra_categories=extra_categories,
        ratio=ratio,
    )
