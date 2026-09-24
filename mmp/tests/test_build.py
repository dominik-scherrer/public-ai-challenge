"""Build pipeline: provenance gate, allow-list, Judge integration, Build Floor."""

import copy
import json

from mmp.build import judge_bridge
from mmp.build.pages import load_capture_dir
from mmp.build.provenance import ProvenanceChecker, check_service
from mmp.registry import CAPTURE_DIR, EXTRACTION_DIR, handoff_allowlist
from mmp.schema import Inventory


def _checker():
    pages = load_capture_dir(CAPTURE_DIR / "wettingen")
    return ProvenanceChecker(pages, ["wettingen.ch", "schule-wettingen.ch"], list(handoff_allowlist()))


def _draft(service_id):
    data = json.loads((EXTRACTION_DIR / "wettingen.json").read_text(encoding="utf-8"))
    return copy.deepcopy(next(s for s in data["services"] if s["id"] == service_id))


def test_seed_inventories_validate(built):
    inv = Inventory.model_validate(json.loads((built / "4045.json").read_text(encoding="utf-8")))
    assert inv.municipality.bfs == 4045
    zuzug = inv.service("zuzug_anmelden")
    assert zuzug.deadline.days == 14
    assert any(d.id == "sorgerechtsentscheid" and d.condition for d in zuzug.documents)
    assert all(s.ech0070.status == "unmapped" for s in inv.services), "no eCH-0070 list imported, so nothing may be mapped"
    assert inv.build.judge.status == "not_run"


def test_invented_quote_is_withheld():
    draft = _draft("zuzug_anmelden")
    draft["deadline"]["evidence"][0]["quote"] = "Bitte melden Sie sich innert 30 Tagen an."
    service, notes = check_service(draft, _checker())
    assert service.deadline is None
    assert any(w.field == "deadline" and "verbatim" in w.reason for w in service.withheld)


def test_value_not_in_quote_is_withheld():
    draft = _draft("kehricht")
    draft["fees"][1]["amount"] = 12.50  # quote says Fr. 10.00
    service, _ = check_service(draft, _checker())
    assert [f.amount for f in service.fees if f.label.startswith("Kehrichtsäcke 17")] == []
    assert any(w.field == "fees[1]" for w in service.withheld)


def test_foreign_link_withheld_but_allowlisted_eumzug_kept():
    kita, _ = check_service(_draft("kinderbetreuung"), _checker())
    assert all("kitarechner" not in (h.url or "") for h in kita.handoffs)
    assert any("ADR-0007" in w.reason for w in kita.withheld)
    zuzug, _ = check_service(_draft("zuzug_anmelden"), _checker())
    assert any(h.url == "https://ag.eumzug.swiss/" for h in zuzug.handoffs)


def test_unobserved_link_is_withheld():
    draft = _draft("kehricht")
    draft["handoffs"][0]["url"] = "https://www.wettingen.ch/some/invented/path"
    service, _ = check_service(draft, _checker())
    assert service.handoffs == []


def test_judge_full_mode_withholds_what_the_judge_rejects(built, monkeypatch, tmp_path):
    import judge.pipeline as jp

    def fake_ensemble(rubric, **kwargs):
        if rubric.id == "provenance_judge":
            ok = "Sorgerecht" not in str(kwargs["claim_value"])  # pretend the judge rejects one claim
            return [("openai", {"supported": ok, "reason": "test"})]
        return [("openai", {"flagged": False})]

    monkeypatch.setattr(jp, "call_judge_ensemble", fake_ensemble)
    monkeypatch.setattr(judge_bridge, "resolve_judge_models", lambda: ["openai"])
    inv = Inventory.model_validate(json.loads((built / "4045.json").read_text(encoding="utf-8")))
    judged, blocked, _ = judge_bridge.run(inv, mode="full", report_path=tmp_path / "r.json", allowed_domains=("eumzug.swiss",))
    assert not blocked
    assert judged.build.judge.status == "passed"
    zuzug = judged.service("zuzug_anmelden")
    assert all(d.id != "sorgerechtsentscheid" for d in zuzug.documents)
    assert any(w.field == "documents[sorgerechtsentscheid]" for w in zuzug.withheld)
    assert zuzug.deadline is not None


def test_build_floor_blocks_and_keeps_previous(built, tmp_path):
    inv = Inventory.model_validate(json.loads((built / "191.json").read_text(encoding="utf-8")))
    _, blocked, reason = judge_bridge.run(inv, mode="deterministic", report_path=tmp_path / "r.json", allowed_domains=(), build_floor=0.9)
    assert blocked and "Build Floor" in reason
