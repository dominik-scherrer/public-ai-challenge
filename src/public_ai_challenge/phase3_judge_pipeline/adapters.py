"""Turn a delivered Service Inventory (mmp-service-inventory/v0) into Claims.

Kept separate from schemas.py on purpose: there are currently at least
three competing shapes in this repo for "a service record" (see the
tensions list in pipeline/observatory/state.json and the status table in
docs/architecture/README.md). Rather than have the Judge commit to one,
it works against the narrow internal Claim type, and this file is the
only place that needs to change when ingestion's schema changes.

Currently handles: pipeline/legacy/handoff/delivery-2026-09-24/*/inventory.json
(schema "mmp-service-inventory/v0").
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from public_ai_challenge.phase3_judge_pipeline.schemas import Claim

# Fields whose value is free text that could plausibly be rendered verbatim
# to a citizen through an MCP tool response — these get the injection check.
FREE_TEXT_FIELDS = {"summary", "title"}

# Fields worth an individual provenance claim when present and non-empty.
# List-valued fields are expanded per-item below.
SCALAR_FIELDS = ("title", "summary")
LIST_FIELDS = ("requirements", "fees", "documents", "contacts", "handoffs")


def _evidence_text_for(service: dict[str, Any], source_refs: list[str]) -> str | None:
    """Look up supporting text for a claim from the service's evidence list.

    The mmp-service-inventory/v0 seed data currently ships `evidence: []`
    for every service (see pipeline/legacy/handoff/*/documents.jsonl, which is
    empty in every delivered municipality) — the crawler hasn't started
    capturing source quotes yet. That means this returns None for
    everything right now, and every claim below gets withheld rather than
    judged. That is the CORRECT behavior per ADR-0004 ("say less rather
    than say something wrong"), not a bug in this adapter — don't "fix"
    it by inventing evidence.
    """
    evidence = service.get("evidence") or []
    for item in evidence:
        if not source_refs or item.get("source_ref") in source_refs:
            text = item.get("text")
            if text:
                return text
    return None


def load_claims_from_inventory(inventory_path: Path) -> tuple[str, str, list[Claim]]:
    """Returns (build_id, municipality_name, claims)."""
    payload = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    build_id = payload.get("build_id", "unknown-build")
    municipality = payload.get("municipality", {}).get("name", "unknown-municipality")

    claims: list[Claim] = []
    for service in payload.get("services", []):
        service_id = service.get("id", "unknown-service")
        source_refs = list(service.get("source_refs", []))

        for scalar_field in SCALAR_FIELDS:
            value = service.get(scalar_field)
            if value in (None, "", [], {}):
                continue
            claims.append(
                Claim(
                    service_id=service_id,
                    municipality=municipality,
                    field=scalar_field,
                    value=value,
                    source_refs=tuple(source_refs),
                    evidence_text=_evidence_text_for(service, source_refs),
                    is_free_text=scalar_field in FREE_TEXT_FIELDS,
                )
            )

        for list_field in LIST_FIELDS:
            items = service.get(list_field) or []
            for i, item in enumerate(items):
                claims.append(
                    Claim(
                        service_id=service_id,
                        municipality=municipality,
                        field=f"{list_field}[{i}]",
                        value=item,
                        source_refs=tuple(source_refs),
                        evidence_text=_evidence_text_for(service, source_refs),
                        is_free_text=False,
                    )
                )

    return build_id, municipality, claims


def load_categories(inventory_path: Path) -> list[str]:
    """Category (or capability) tags present in a Build, for the coverage check."""
    payload = json.loads(Path(inventory_path).read_text(encoding="utf-8"))
    categories: list[str] = []
    for service in payload.get("services", []):
        cat = service.get("category")
        if cat:
            categories.append(cat)
        categories.extend(service.get("capabilities") or [])
    return categories


def iter_delivered_inventories(handoff_dir: Path) -> Iterable[Path]:
    """All inventory.json files under a delivery batch, e.g. pipeline/legacy/handoff/delivery-2026-09-24/."""
    yield from sorted(handoff_dir.glob("*/inventory.json"))
