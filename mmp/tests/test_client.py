"""Reference Client turn logic, with the rule-based stand-in model."""

from mmp.client.orchestrator import Orchestrator, RuleModel, prefill_values
from mmp.server.app import create_server
from mmp.server.store import InventoryStore

SEEWIL = "Ich ziehe nach einer Trennung mit meinen zwei Kindern per 1. November von Dübendorf nach Wettingen. Was muss ich alles erledigen?"


async def test_move_in_journey(built):
    orch = Orchestrator(create_server(InventoryStore(built)), RuleModel())
    result = await orch.turn(4045, [{"role": "user", "content": SEEWIL}])
    kinds = [b["type"] for b in result["blocks"]]
    assert kinds == ["overview", "previous", "app"]
    overview = result["blocks"][0]
    assert overview["items"][0]["id"] == "zuzug_anmelden"
    assert "15. November" in overview["items"][0]["subtitle"]
    previous = result["blocks"][1]
    assert previous["bfs"] == 191 and previous["item"]["id"] == "wegzug_abmelden"
    card = result["blocks"][2]
    assert card["context"]["matched_documents"][0]["id"] == "sorgerechtsentscheid"
    assert card["context"]["prefill"]["household_size"].startswith("3")
    # the situation never travels to the MMP server as a tool argument
    assert set(card["arguments"]) == {"bfs", "service_id"}


async def test_gap_is_reported_not_guessed(built):
    orch = Orchestrator(create_server(InventoryStore(built)), RuleModel())
    result = await orch.turn(4045, [{"role": "user", "content": "Gibt es einen Zuschuss für ein E-Bike?"}])
    gap = result["blocks"][0]
    assert gap["type"] == "gap" and gap["topic"]
    assert gap["contact"]["phone"] == "056 437 71 11"


def test_prefill_only_stated_facts():
    assert prefill_values({"move_date": None, "adults": None, "children": 2}) == {"children": "2"}


class StubModel:
    """Replays a plan shaped like Apertus' first real answers (2026-09-24)."""

    label = "stub"

    def __init__(self, plan):
        self.plan = plan

    def complete_json(self, system, messages):
        return self.plan


async def test_model_text_never_reaches_the_citizen(built):
    plan = {"reply": "Die Gemeinde übernimmt keine Umzugskosten.", "covered": True, "service_ids": ["zuzug_anmelden"],
            "situation": {"move_date": "2026-11-01", "adults": 1, "children": 2, "separated": True, "divorced": False}}
    result = await Orchestrator(create_server(InventoryStore(built)), StubModel(plan)).turn(4045, [{"role": "user", "content": SEEWIL}])
    assert "Umzugskosten" not in result["reply"]
    assert result["reply"].startswith("Für Ihren Zuzug per 1. November")


async def test_separation_is_not_divorce(built):
    plan = {"covered": True, "service_ids": ["zuzug_anmelden"], "situation": {"separated": True, "children": 2, "adults": 1}}
    result = await Orchestrator(create_server(InventoryStore(built)), StubModel(plan)).turn(4045, [{"role": "user", "content": SEEWIL}])
    card = next(b for b in result["blocks"] if b["type"] == "app")
    assert [m["id"] for m in card["context"]["matched_documents"]] == ["sorgerechtsentscheid"]


async def test_responsible_office_is_a_gap_not_an_answer(built):
    plan = {"covered": False, "service_ids": ["soziale_dienste"], "situation": {}, "gap_topic": "Umzugskostenbeitrag für Alleinerziehende"}
    result = await Orchestrator(create_server(InventoryStore(built)), StubModel(plan)).turn(
        4045, [{"role": "user", "content": "Übernimmt die Gemeinde Umzugskosten für Alleinerziehende?"}]
    )
    assert [b["type"] for b in result["blocks"]] == ["gap"]
    assert result["blocks"][0]["contact"]["office"].startswith("Soziale Dienste")
    assert "nichts" in result["reply"]
