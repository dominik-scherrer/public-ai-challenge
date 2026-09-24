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
