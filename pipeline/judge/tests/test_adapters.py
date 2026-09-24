from pathlib import Path

from judge.adapters import iter_delivered_inventories, load_claims_from_inventory

HANDOFF_DIR = Path(__file__).resolve().parents[3] / "pipeline" / "legacy" / "handoff" / "delivery-2026-09-24"
AUSSERBERG = HANDOFF_DIR / "ausserberg" / "inventory.json"


def test_ausserberg_inventory_exists():
    assert AUSSERBERG.exists(), "expected the Ausserberg seed delivery to still be at this path"


def test_loads_claims_with_service_ids():
    build_id, municipality, claims = load_claims_from_inventory(AUSSERBERG)
    assert build_id
    assert municipality == "Ausserberg"
    assert claims, "expected at least one claim from the Ausserberg inventory"
    assert all(c.service_id.startswith("ch.vs.ausserberg.") for c in claims)


def test_current_seed_data_has_no_evidence_yet():
    """Documents a real, current fact about the data, not a Judge bug.

    See adapters.py's _evidence_text_for docstring: documents.jsonl is
    empty for every delivered municipality right now, so every claim
    should come back with evidence_text=None until the crawler starts
    capturing source quotes. If this test starts failing, it means real
    evidence has landed -- update it, don't just delete it.
    """
    _, _, claims = load_claims_from_inventory(AUSSERBERG)
    assert all(c.evidence_text is None for c in claims)


def test_discovers_all_delivered_municipalities():
    found = list(iter_delivered_inventories(HANDOFF_DIR))
    names = {p.parent.name for p in found}
    assert "ausserberg" in names
    assert len(found) >= 7
