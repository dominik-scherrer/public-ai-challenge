"""The Reference Client's turn logic: Citizen message -> MCP calls -> UI blocks.

The browser keeps the conversation; this backend holds no state between
requests (ADR-0005 applies to the client too: nothing is logged).

Why not native tool calling: Apertus on Public AI does not support the OpenAI
``tools`` parameter (OQ-2). Instead the model gets the compact
``list_services`` output — exactly what OQ-2 proposes — and answers with one
JSON plan; this backend then performs the MCP calls itself. The model never
states facts about a Service: facts come only from ``get_service`` and are
rendered by the Service Card with their sources.

Situation details (children, a separation, the move date) stay here and in
the browser. They are passed to the Service Card through the MCP Apps host
context, never as tool arguments to the MMP server.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from typing import Any

from mcp.client import Client

from mmp.llm import ChatModel

PLANNER = """Du bist der Assistent der Gemeinde {name} (BFS {bfs}) für Einwohnerinnen und Einwohner.
Heute ist {today}. Du kennst NUR die Dienstleistungen in der Liste unten (aus dem MMP-Server).

Dienstleistungen von {name}:
{services}

Andere Gemeinden mit MMP-Inventar: {others}

Aufgabe: Lies das Gespräch und antworte NUR mit JSON:
{{
  "reply": "1–2 Sätze auf Deutsch (Sie-Form). Nenne höchstens die Titel der gewählten Dienstleistungen. KEINE Fakten wie Fristen, Gebühren, Unterlagen, Adressen oder Zeiten – die zeigt die Service Card mit Quelle.",
  "service_ids": ["ids aus der Liste, die zur Situation passen, dringendste zuerst; [] wenn keine passt"],
  "situation": {{
    "move_date": "YYYY-MM-DD oder null",
    "adults": "Zahl oder null", "children": "Zahl oder null",
    "nationality": "swiss | foreign | null",
    "moving": "in | out | within | null",
    "previous_municipality": "Name der bisherigen Wohngemeinde oder null"
  }},
  "gap_topic": "null, oder wenn die Frage von keiner Dienstleistung beantwortet wird: ein kurzes, abstraktes Thema OHNE persönliche Angaben (z. B. 'Umzugskostenbeitrag für Alleinerziehende')",
  "gap_service_id": "null oder id der Stelle aus der Liste, die am ehesten zuständig ist"
}}
Regeln: Erfinde keine Dienstleistungen. Wenn nichts passt, rate nicht: setze gap_topic.
Übernimm nur Angaben, die die Person selbst gemacht hat; sonst null."""

MATCHER = """Eine Person hat ihre Situation beschrieben (Gespräch unten). Die Gemeinde verlangt einige Unterlagen nur unter einer Bedingung.
Entscheide für jede bedingte Unterlage, ob die Person die Bedingung SELBST erwähnt hat. Im Zweifel: nicht zutreffend.
Unterlagen:
{docs}

Antworte NUR mit JSON: {{"matched": [{{"id": "...", "reason": "Hinzugefügt, weil Sie ... erwähnt haben."}}]}}"""


def _conversation(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{'Person' if m['role'] == 'user' else 'Assistent'}: {m['content']}" for m in messages[-12:])


def _int_or_none(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 20 else None


def _date_or_none(value: Any) -> str | None:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError:
        return None


def clean_situation(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    nationality = raw.get("nationality") if raw.get("nationality") in {"swiss", "foreign"} else None
    moving = raw.get("moving") if raw.get("moving") in {"in", "out", "within"} else None
    previous = raw.get("previous_municipality")
    return {
        "move_date": _date_or_none(raw.get("move_date")),
        "adults": _int_or_none(raw.get("adults")),
        "children": _int_or_none(raw.get("children")),
        "nationality": nationality,
        "moving": moving,
        "previous_municipality": previous.strip()[:60] if isinstance(previous, str) and previous.strip() and previous != "null" else None,
    }


def prefill_values(situation: dict[str, Any]) -> dict[str, str]:
    """Only what the Citizen stated (CONTEXT.md: Handoff)."""
    values: dict[str, str] = {}
    if situation.get("move_date"):
        values["move_date"] = date.fromisoformat(situation["move_date"]).strftime("%d.%m.%Y")
    adults, children = situation.get("adults"), situation.get("children")
    if adults is not None and children is not None:
        parts = [f"{adults} erwachsene Person{'en' if adults != 1 else ''}"]
        if children:
            parts.append(f"{children} Kind{'er' if children != 1 else ''}")
        values["household_size"] = f"{adults + children} ({', '.join(parts)})"
    if adults is not None:
        values["adults"] = str(adults)
    if children is not None:
        values["children"] = str(children)
    if situation.get("previous_municipality"):
        values["previous_municipality"] = situation["previous_municipality"]
    return values


class Orchestrator:
    def __init__(self, mcp_url: str, model: ChatModel):
        self.mcp_url = mcp_url
        self.model = model

    async def _call(self, mcp: Client, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await mcp.call_tool(tool, arguments)
        payload = result.model_dump(mode="json", by_alias=True, exclude_none=True)
        return payload

    async def municipalities(self) -> list[dict[str, Any]]:
        async with Client(self.mcp_url) as mcp:
            result = await mcp.call_tool("list_municipalities", {})
            return (result.structured_content or {}).get("municipalities", [])

    async def service_card(self, bfs: int, service_id: str, messages: list[dict[str, str]], situation: dict[str, Any]) -> dict[str, Any]:
        async with Client(self.mcp_url) as mcp:
            return await self._card(mcp, bfs, service_id, messages, situation)

    async def _card(self, mcp: Client, bfs: int, service_id: str, messages, situation) -> dict[str, Any]:
        arguments = {"bfs": bfs, "service_id": service_id}
        result = await self._call(mcp, "get_service", arguments)
        service = (result.get("structuredContent") or {}).get("service", {})
        conditional = [d for d in service.get("documents", []) if d.get("condition")]
        matched: list[dict[str, str]] = []
        if conditional and any(m["role"] == "user" for m in messages):
            docs = "\n".join(f"- id={d['id']}: {d['label']} — nur {d['condition']}" for d in conditional)
            try:
                answer = await asyncio.to_thread(
                    self.model.complete_json, MATCHER.format(docs=docs), [{"role": "user", "content": _conversation(messages)}]
                )
                ids = {d["id"] for d in conditional}
                matched = [
                    {"id": m["id"], "reason": str(m.get("reason", ""))[:160]}
                    for m in answer.get("matched", [])
                    if isinstance(m, dict) and m.get("id") in ids
                ]
            except Exception:  # noqa: BLE001 - a failed match only means "show the condition, not a tick"
                matched = []
        return {
            "type": "app",
            "tool": "get_service",
            "resource_uri": "ui://mmp/service-card.html",
            "arguments": arguments,
            "result": result,
            "context": {"situation": situation, "matched_documents": matched, "prefill": prefill_values(situation)},
        }

    async def turn(self, bfs: int, messages: list[dict[str, str]]) -> dict[str, Any]:
        async with Client(self.mcp_url) as mcp:
            listing = (await self._call(mcp, "list_services", {"bfs": bfs})).get("structuredContent")
            if not listing:
                return {"reply": "Für diese Gemeinde ist noch kein Service Inventory publiziert.", "blocks": []}
            others = (await self._call(mcp, "list_municipalities", {})).get("structuredContent", {}).get("municipalities", [])
            municipality = listing["municipality"]
            services = {s["id"]: s for s in listing["services"]}
            service_lines = "\n".join(
                f"- {s['id']}: {s['title']} [{s['tier']}] Stichworte: {', '.join(s['keywords'])}" for s in listing["services"]
            )
            system = PLANNER.format(
                name=municipality["name"],
                bfs=bfs,
                today=date.today().isoformat(),
                services=service_lines,
                others=", ".join(f"{o['name']} (BFS {o['bfs']})" for o in others if o["bfs"] != bfs) or "keine",
            )
            plan = await asyncio.to_thread(self.model.complete_json, system, [{"role": "user", "content": _conversation(messages)}])

            ids = [i for i in plan.get("service_ids") or [] if i in services][:6]
            situation = clean_situation(plan.get("situation"))
            reply = str(plan.get("reply") or "").strip()[:600]
            blocks: list[dict[str, Any]] = []

            details = {}
            for service_id in ids:
                full = await self._call(mcp, "get_service", {"bfs": bfs, "service_id": service_id})
                details[service_id] = (full.get("structuredContent") or {}).get("service", {})

            if ids:
                blocks.append(
                    {
                        "type": "overview",
                        "bfs": bfs,
                        "notice": listing["build"]["notice"],
                        "items": [_overview_item(services[i], details.get(i, {}), situation) for i in ids],
                    }
                )
                # Previous municipality: the move-out Service there, if MMP serves it.
                previous = situation.get("previous_municipality")
                is_move_in = any("residence_registration" in services[i]["categories"] for i in ids)
                if is_move_in and situation.get("moving") in {"in", None}:
                    prev = next(
                        (o for o in others if previous and o["name"].casefold() == previous.casefold() and o["bfs"] != bfs), None
                    )
                    block: dict[str, Any] = {"type": "previous", "name": previous, "bfs": prev["bfs"] if prev else None, "item": None}
                    if prev:
                        prev_listing = (await self._call(mcp, "list_services", {"bfs": prev["bfs"]})).get("structuredContent") or {}
                        out = next((s for s in prev_listing.get("services", []) if "residence_deregistration" in s["categories"]), None)
                        if out:
                            full = await self._call(mcp, "get_service", {"bfs": prev["bfs"], "service_id": out["id"]})
                            block["item"] = _overview_item(out, (full.get("structuredContent") or {}).get("service", {}), situation)
                            block["item"]["bfs"] = prev["bfs"]
                    blocks.append(block)
                blocks.append(await self._card(mcp, bfs, ids[0], messages, situation))
            else:
                topic = plan.get("gap_topic")
                topic = topic.strip()[:120] if isinstance(topic, str) and topic.strip() and topic != "null" else None
                contact = None
                gap_service = plan.get("gap_service_id")
                if gap_service in services:
                    full = await self._call(mcp, "get_service", {"bfs": bfs, "service_id": gap_service})
                    responsible = ((full.get("structuredContent") or {}).get("service") or {}).get("responsible")
                    if responsible:
                        contact = {k: responsible.get(k) for k in ("office", "phone", "email", "address")}
                if contact is None and municipality.get("general_contact"):
                    gc = municipality["general_contact"]
                    contact = {k: gc.get(k) for k in ("office", "phone", "email", "address")}
                blocks.append(
                    {"type": "gap", "bfs": bfs, "topic": topic, "contact": contact, "domain": municipality["official_domains"][0]}
                )
            return {"reply": reply, "situation": situation, "blocks": blocks}


def _overview_item(compact: dict[str, Any], service: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    subtitle = compact.get("office") or ""
    deadline = service.get("deadline")
    if deadline:
        subtitle = f"Frist: {deadline['label']}"
        if situation.get("move_date") and deadline.get("relative_to") in {"move_in", "move_out"}:
            from datetime import timedelta

            due = date.fromisoformat(situation["move_date"]) + timedelta(days=int(deadline["days"]))
            subtitle = f"Frist: bis {due.day}. {_MONTHS[due.month - 1]} ({deadline['days']} Tage)"
    elif "school_enrolment" in compact.get("categories", []) and situation.get("children"):
        subtitle = f"Für {situation['children']} Kind{'er' if situation['children'] != 1 else ''} · {compact.get('office') or ''}".rstrip(" ·")
    elif service.get("summary"):
        subtitle = service["summary"][:90] + ("…" if len(service["summary"]) > 90 else "")
    return {
        "id": compact["id"],
        "title": compact["title"],
        "tier": compact["tier"],
        "ech0070": compact["ech0070"],
        "subtitle": subtitle,
        "urgent": bool(deadline),
    }


_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]


# ----------------------------------------------------------------------------
# Rule-based stand-in for the model (no key configured). Clearly labelled in
# the UI; exists so the Reference Client can be developed and tested offline.

_NUMBERS = {"ein": 1, "einem": 1, "einer": 1, "eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5}
_MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(_MONTHS)}


class RuleModel:
    label = "Demo-Modus ohne Sprachmodell (regelbasiert)"

    def complete_json(self, system: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        convo = messages[-1]["content"]
        person = "\n".join(line for line in convo.splitlines() if line.startswith("Person:")).lower()
        if system.startswith("Eine Person hat ihre Situation"):
            matched = []
            if re.search(r"trennung|getrennt|geschieden|scheidung", person):
                for doc_id in re.findall(r"id=(\w+):[^\n]*getrennt", system):
                    matched.append({"id": doc_id, "reason": "Hinzugefügt, weil Sie eine Trennung erwähnt haben."})
            return {"matched": matched}

        services = re.findall(r"^- (\w+): (.+?) \[\w+\] Stichworte: (.*)$", system, re.M)
        last = person.splitlines()[-1].removeprefix("person:").strip() if person else ""
        chosen = []
        for sid, title, keywords in services:
            words = [w.strip().lower() for w in keywords.split(",")] + [title.lower()]
            if any(w and w[:6] in last for w in words if len(w) > 3):
                chosen.append(sid)
        moving_in = bool(re.search(r"ziehe .*nach|zuzug|neu in|umzug nach", last))
        if moving_in:
            for sid, title, keywords in services:
                if sid not in chosen and re.search(r"zuzug|anmeld", sid + title.lower()):
                    chosen.insert(0, sid)
        children = None
        m = re.search(r"(\d+|ein|einem|einer|zwei|drei|vier|fünf)\s+(?:meinen\s+|meine\s+)?kinder", person)
        if m:
            children = int(m.group(1)) if m.group(1).isdigit() else _NUMBERS.get(m.group(1))
            if moving_in:
                for sid, title, keywords in services:
                    if sid not in chosen and ("schul" in sid or "kinderbetreuung" in sid):
                        chosen.append(sid)
        if moving_in:
            for sid, title, keywords in services:
                if sid not in chosen and "kehricht" in sid:
                    chosen.append(sid)
        move_date = None
        d = re.search(r"(\d{1,2})\.\s*(" + "|".join(_MONTH_NUM) + r")", person)
        if d:
            today = date.today()
            month = _MONTH_NUM[d.group(2)]
            year = today.year if month >= today.month else today.year + 1
            move_date = date(year, month, int(d.group(1))).isoformat()
        previous = None
        p = re.search(r"(?:von|aus)\s+([A-ZÄÖÜ][\wäöü/-]+)", convo.split("Person:")[-1])
        if p:
            previous = p.group(1)
        adults = 1 if re.search(r"\bich\b", person) and not re.search(r"\bwir\b", person) else None
        situation = {"move_date": move_date, "adults": adults, "children": children, "nationality": None,
                     "moving": "in" if moving_in else None, "previous_municipality": previous}
        if not chosen:
            topic = re.sub(r"^(gibt es|wie|was|wo|wann|kann ich|bekomme ich)\s+", "", last).strip(" ?.")
            topic = re.sub(r"\b(ich|mein\w*|mir|mich)\b", "", topic).strip()[:80] or "Anfrage ohne passende Dienstleistung"
            return {"reply": "Dazu finde ich in den erfassten Angaben keine Dienstleistung. Ich möchte nicht raten.",
                    "service_ids": [], "situation": situation, "gap_topic": topic[:1].upper() + topic[1:], "gap_service_id": None}
        return {"reply": f"Ich habe {len(chosen)} passende Dienstleistung{'en' if len(chosen) != 1 else ''} gefunden. Die dringendste zuerst:",
                "service_ids": chosen, "situation": situation, "gap_topic": None, "gap_service_id": None}


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
