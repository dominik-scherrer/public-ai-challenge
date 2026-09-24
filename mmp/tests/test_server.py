"""The shared MMP server: BFS addressing, Service Card, consented channels only."""

import pytest
from mcp.client import Client

from mmp.server.app import SERVICE_CARD_URI, create_server
from mmp.server.store import InventoryStore


@pytest.fixture()
def server(built):
    return create_server(InventoryStore(built))


async def test_tools_and_card(server):
    async with Client(server) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
        assert {"list_services", "find_service", "get_service", "report_gap"} <= set(tools)
        assert tools["get_service"].meta["ui"]["resourceUri"] == SERVICE_CARD_URI
        res = await c.read_resource(SERVICE_CARD_URI)
        assert res.contents[0].mime_type == "text/html;profile=mcp-app"
        assert "ui/initialize" in res.contents[0].text

        listing = await c.call_tool("list_services", {"bfs": 4045})
        assert {s["id"] for s in listing.structured_content["services"]} >= {"zuzug_anmelden", "kehricht"}

        found = await c.call_tool("find_service", {"bfs": 4045, "query": "Kehrichtsäcke"})
        assert found.structured_content["services"][0]["id"] == "kehricht"

        card = await c.call_tool("get_service", {"bfs": 191, "service_id": "wegzug_abmelden"})
        assert card.structured_content["service"]["fees"][0]["amount"] in ("0", 0, "0.0")
        assert "Quelle: https://www.duebendorf.ch" in card.content[0].text

        missing = await c.call_tool("get_service", {"bfs": 9999, "service_id": "x"})
        assert missing.is_error


async def test_gap_report_rejects_personal_data(server, tmp_path, monkeypatch):
    import mmp.server.operator_inbox as inbox

    monkeypatch.setattr(inbox.record_gap, "__kwdefaults__", {"directory": tmp_path})
    async with Client(server) as c:
        bad = await c.call_tool("report_gap", {"bfs": 4045, "topic": "Ich bin alleinerziehend, 079 123 45 67"})
        assert bad.is_error
        ok = await c.call_tool("report_gap", {"bfs": 4045, "topic": "Umzugskostenbeitrag für Alleinerziehende"})
        assert not ok.is_error
    assert "Umzugskostenbeitrag" in (tmp_path / "gap-reports.jsonl").read_text(encoding="utf-8")
