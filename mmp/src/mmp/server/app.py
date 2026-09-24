"""The one shared, generic MMP server (ADR-0003), stateless (ADR-0005).

Every Municipality is served by this same code, addressed by BFS number; a
Build only swaps the data in ``data/inventories/<bfs>.json``. Speaks
Streamable HTTP (ADR-0006) so any MCP host can connect — the Reference Client,
Claude or ChatGPT (ADR-0002: only the Reference Client is the sovereign path).

Tools (the MMP tool surface):
  list_municipalities    which BFS numbers have a live Service Inventory
  list_services(bfs)     compact list for the model to choose from (OQ-2)
  find_service(bfs, q)   keyword fallback
  get_service(bfs, id)   one Service + its Service Card (MCP Apps, ui://)
  report_gap(bfs, topic) consented Gap Report, abstracted topic only
  send_feedback(...)     consented Feedback, called from the Service Card

No query text is logged or stored. The only runtime record is a counter of
which Service IDs were retrieved (ADR-0005: "which Services are in demand,
never who asked or why").
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path
from typing import Annotated, Any

from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from mmp.schema import Inventory, Service
from mmp.server.operator_inbox import InboxRejected, record_feedback, record_gap
from mmp.server.store import InventoryStore, rank_services

SERVICE_CARD_URI = "ui://mmp/service-card.html"
MCP_APP_MIME = "text/html;profile=mcp-app"
UI_DIR = Path(__file__).parent / "ui"

log = logging.getLogger("mmp.server")
demand = Counter()  # service-id -> retrievals; the only runtime metric

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITES_INBOX = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

Bfs = Annotated[int, Field(description="BFS-Gemeindenummer of the Municipality, e.g. 4045 for Wettingen", ge=1, le=9999)]


def _error(text: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=True)


def _label(inventory: Inventory) -> dict[str, Any]:
    build = inventory.build
    return {
        "build_id": build.id,
        "built_at": build.built_at.isoformat(),
        "method": build.method,
        "extraction": build.extraction,
        "judge": build.judge.status,
        "verified_by_municipality": build.verified_by_municipality,
        "notice": (
            f"Automatisch aus {inventory.municipality.official_domains[0]} erstellt, "
            "noch nicht von der Gemeinde geprüft. Jede Angabe verweist auf ihre Quelle."
            + ("" if build.judge.status == "passed" else " Die inhaltliche Prüfung durch den Judge steht noch aus.")
        ),
    }


def _municipality(inventory: Inventory) -> dict[str, Any]:
    m = inventory.municipality
    return {
        "bfs": m.bfs,
        "name": m.name,
        "canton": m.canton,
        "website": m.website,
        "official_domains": m.official_domains,
        "general_contact": m.general_contact.model_dump(mode="json", exclude_none=True) if m.general_contact else None,
    }


def _compact(service: Service) -> dict[str, Any]:
    return {
        "id": service.id,
        "title": service.title,
        "tier": service.tier,
        "ech0070": service.ech0070.id or "unmapped",
        "categories": service.categories,
        "keywords": service.keywords,
        "deadline_days": service.deadline.days if service.deadline else None,
        "office": service.responsible.office if service.responsible else None,
    }


def service_text(inventory: Inventory, service: Service) -> str:
    """Plain-text rendering for hosts without MCP Apps: every fact with its source."""
    src = {s.id: s for s in inventory.sources}
    lines = [f"{service.title} — {inventory.municipality.name} (BFS {inventory.municipality.bfs})"]
    if service.summary:
        lines.append(service.summary)
    if service.deadline:
        lines.append(f"Frist: {service.deadline.label}")
    if service.responsible:
        r = service.responsible
        lines.append("Zuständig: " + ", ".join(x for x in [r.office, r.address, r.phone, r.email] if x))
    for doc in service.documents:
        cond = f" ({doc.condition})" if doc.condition else ""
        who = {"swiss": " [Schweizer Staatsangehörige]", "foreign": " [ausländische Staatsangehörige]"}.get(doc.audience, "")
        lines.append(f"- Unterlage: {doc.label}{cond}{who}")
    for fee in service.fees:
        amount = "gratis" if fee.amount == 0 else f"CHF {fee.amount:.2f}"
        lines.append(f"- Gebühr: {fee.label}: {amount}{' ' + fee.unit if fee.unit else ''}")
    if service.opening_hours:
        oh = service.opening_hours
        lines.append(f"Öffnungszeiten {oh.office}: " + "; ".join(f"{e.days} {', '.join(e.times)}" for e in oh.entries))
    for handoff in service.handoffs:
        lines.append(f"- Selbst erledigen: {handoff.label}{' → ' + handoff.url if handoff.url else ''}")
    for withheld in service.withheld:
        lines.append(f"- Zurückgehalten ({withheld.field}): bitte bei der Gemeinde nachfragen")
    for sid in service.source_ids:
        if sid in src:
            lines.append(f"Quelle: {src[sid].url} (abgerufen {src[sid].retrieved_at.date().isoformat()})")
    lines.append(_label(inventory)["notice"])
    return "\n".join(lines)


def create_server(store: InventoryStore | None = None) -> MCPServer:
    store = store or InventoryStore()
    server = MCPServer(
        name="MMP — Model Municipality Protocol",
        instructions=(
            "Official information and services of Swiss municipalities, addressed by BFS number. "
            "Only state what a tool returned, cite its source, and say so when nothing was found "
            "instead of guessing. Never submit anything on the citizen's behalf: Handoffs open the "
            "municipality's own counter, where the citizen submits."
        ),
    )

    @server.resource(SERVICE_CARD_URI, name="service-card", title="MMP Service Card", mime_type=MCP_APP_MIME)
    def service_card() -> str:
        """The single standardized view of a Service, identical in every MCP Apps host."""
        return (UI_DIR / "service_card.html").read_text(encoding="utf-8")

    @server.tool(annotations=READ_ONLY)
    def list_municipalities() -> CallToolResult:
        """List Municipalities with a live Service Inventory (BFS number, name, canton, number of Services)."""
        items = [
            {"bfs": inv.municipality.bfs, "name": inv.municipality.name, "canton": inv.municipality.canton, "services": len(inv.services)}
            for inv in store.all()
        ]
        text = "\n".join(f"{i['bfs']}: {i['name']} ({i['canton']}), {i['services']} Services" for i in items) or "Keine Inventare publiziert."
        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content={"municipalities": items})

    @server.tool(annotations=READ_ONLY)
    def list_services(bfs: Bfs) -> CallToolResult:
        """List all Services of one Municipality (id, title, tier, eCH-0070 ID, categories, synonyms).
        Choose the matching Service(s) from this list, then call get_service."""
        inventory = store.get(bfs)
        if inventory is None:
            return _error(f"Für BFS {bfs} ist kein Service Inventory publiziert.")
        items = [_compact(s) for s in inventory.services]
        text = "\n".join(f"{i['id']}: {i['title']} [{i['tier']}] ({', '.join(i['keywords'][:5])})" for i in items)
        return CallToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content={"municipality": _municipality(inventory), "build": _label(inventory), "services": items},
        )

    @server.tool(annotations=READ_ONLY)
    def find_service(bfs: Bfs, query: Annotated[str, Field(max_length=200, description="A few keywords, not the citizen's full message")]) -> CallToolResult:
        """Keyword fallback when list_services is not enough. Returns up to 5 candidate Services."""
        inventory = store.get(bfs)
        if inventory is None:
            return _error(f"Für BFS {bfs} ist kein Service Inventory publiziert.")
        hits = [_compact(s) for _, s in rank_services(inventory, query)]
        text = "\n".join(f"{h['id']}: {h['title']}" for h in hits) or "Kein passender Service gefunden."
        return CallToolResult(content=[TextContent(type="text", text=text)], structured_content={"services": hits})

    @server.tool(annotations=READ_ONLY, meta={"ui": {"resourceUri": SERVICE_CARD_URI, "visibility": ["model", "app"]}})
    def get_service(bfs: Bfs, service_id: Annotated[str, Field(pattern=r"^[a-z0-9_]+$", max_length=80)]) -> CallToolResult:
        """Get one Service with every attribute and its source, rendered as the MMP Service Card."""
        inventory = store.get(bfs)
        if inventory is None:
            return _error(f"Für BFS {bfs} ist kein Service Inventory publiziert.")
        service = inventory.service(service_id)
        if service is None:
            return _error(f"Service '{service_id}' existiert in BFS {bfs} nicht. Nutze list_services.")
        demand[f"{bfs}:{service_id}"] += 1
        sources = [
            {"id": s.id, "url": s.url, "title": s.title, "retrieved_at": s.retrieved_at.isoformat()}
            for s in inventory.sources
            if s.id in service.source_ids
        ]
        return CallToolResult(
            content=[TextContent(type="text", text=service_text(inventory, service))],
            structured_content={
                "municipality": _municipality(inventory),
                "build": _label(inventory),
                "service": service.model_dump(mode="json", exclude_none=True),
                "sources": sources,
            },
        )

    @server.tool(annotations=WRITES_INBOX)
    def report_gap(
        bfs: Bfs,
        topic: Annotated[str, Field(max_length=120, description="Abstracted topic only, e.g. 'Umzugskostenbeitrag für Alleinerziehende' — never the citizen's words or situation")],
    ) -> CallToolResult:
        """Send a Gap Report to the MMP Operator. Only call after the citizen has seen the topic and agreed."""
        if store.get(bfs) is None:
            return _error(f"Für BFS {bfs} ist kein Service Inventory publiziert.")
        try:
            record = record_gap(bfs, topic)
        except InboxRejected as error:
            return _error(str(error))
        return CallToolResult(
            content=[TextContent(type="text", text=f"Danke. Thema «{record['topic']}» anonym gemeldet.")],
            structured_content={"reported": record},
        )

    @server.tool(annotations=WRITES_INBOX)
    def send_feedback(
        bfs: Bfs,
        message: Annotated[str, Field(max_length=600)],
        service_id: Annotated[str | None, Field(pattern=r"^[a-z0-9_]+$", max_length=80)] = None,
    ) -> CallToolResult:
        """Send Feedback to the MMP Operator. Only after the citizen pressed 'send feedback' and approved this exact text."""
        if store.get(bfs) is None:
            return _error(f"Für BFS {bfs} ist kein Service Inventory publiziert.")
        try:
            record = record_feedback(bfs, service_id, message)
        except InboxRejected as error:
            return _error(str(error))
        return CallToolResult(content=[TextContent(type="text", text="Danke für Ihr Feedback.")], structured_content={"sent": True, "date": record["date"]})

    return server


def build_asgi(store: InventoryStore | None = None):
    server = create_server(store)
    return server.streamable_http_app(streamable_http_path="/mcp", stateless_http=True, json_response=True)


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    logging.basicConfig(level=logging.WARNING)
    # access_log=False: request lines carry no arguments for MCP, but we keep no request log at all.
    uvicorn.run(build_asgi(), host=host, port=port, access_log=False, log_level="warning")
