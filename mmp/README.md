# mmp/ — Model Municipality Protocol MVP

An end-to-end implementation of the accepted architecture in `docs/architecture/`: a **Build** turns a municipality website into a Judge-gated **Service Inventory** (data, not code). **One shared MMP server** serves every inventory by BFS number. The **Reference Client** is a chat that acts as an MCP client and an MCP Apps host, and renders the **Service Card**.

The demo is the "Umzug nach Seewil" journey from the design canvas, played on real municipalities from the research report: moving from **Dübendorf (BFS 191)** to **Wettingen (BFS 4045)** after a separation, with two children.

```
municipality website ─▶ Build ─────────────────────────────────▶ data/inventories/<bfs>.json
                        crawl │ extract │ provenance │ eCH-0070 │ Judge (pipeline/judge)
                                                                         │
Reference Client (chat) ◀── MCP Streamable HTTP ──▶ shared MMP server ◀──┘
  └─ Service Card (ui:// MCP App, sandboxed iframe)     list_services · find_service · get_service
                                                         report_gap · send_feedback · list_municipalities
```

## Run it

```bash
cd mmp
uv sync
cp ../.env.example ../.env      # add PUBLIC_AI_API_KEY (see below)
uv run mmp dev                  # MMP server on :8765/mcp + Reference Client on http://127.0.0.1:8080
```

Open http://127.0.0.1:8080 and type (or click "Umzug nach Wettingen"):

> Ich ziehe nach einer Trennung mit meinen zwei Kindern per 1. November von Dübendorf nach Wettingen. Was muss ich alles erledigen?

Without a key the client runs in a clearly labelled **rule-based demo mode**, so the UI can be developed and tested offline. With `PUBLIC_AI_API_KEY` it uses Apertus via the Public AI Inference Utility (`https://api.publicai.co/v1`).

Other commands:

```bash
uv run mmp serve                       # only the MMP server (connect Claude/ChatGPT/Open WebUI to http://127.0.0.1:8765/mcp)
uv run mmp chat --mcp-url <url>        # only the client, against any MMP server
uv run mmp build wettingen             # a real Build: crawl + extract (needs a model) + Judge + publish
uv run mmp build wettingen --capture data/captures/wettingen --extraction data/extractions/wettingen.json
uv run mmp seed                        # rebuild the committed demo inventories (Judge runs fully if a key is set)
uv run mmp ech0070-import BEIL1_d&f_eCH-0070_V4.2.0_Leistungsinventar.xlsx
uv run pytest                          # 14 tests, no key or network needed
```

## Screens (from the design canvas)

| # | Screen | Where |
|---|---|---|
| 1 | Question: municipality header, sovereignty badge, greeting, suggestion chips | `client/static` |
| 2 | Overview: matched Services with tier, eCH-0070 ID or "nicht zugeordnet", deadline computed from the move date; "not yet verified" banner; the move-out at the **previous municipality**, fetched from its own inventory | `client/orchestrator.py` + `static/app.js` |
| 3 | Service Card: deadline, "Mitbringen – für Sie", "Zusätzlich – für Ihre 2 Kinder" with *"Hinzugefügt, weil Sie eine Trennung erwähnt haben"*, fee, counter hours, source links, withheld attributes, print checklist, feedback | `server/ui/service_card.html` (MCP App) |
| 4 | Handoff: only stated facts prepared (date, household size, previous municipality). The Citizen opens eUmzug / the online counter and submits there | Service Card, handoff view |
| 5 | Gap: honest "no information", responsible office (call / e-mail), consented anonymous Gap Report with editable topic | `static/app.js` → `report_gap` |

## How the ADRs show up in code

| ADR | Where |
|---|---|
| 0001 eCH-0070 | `schema.Ech0070`, `build/ech0070.py`. Maps **only** against the official list once imported. Until then everything is `unmapped` (no IDs typed from memory). |
| 0002 sovereignty in the client | The badge says "bleibt in der Schweiz" only if the operator sets `MMP_CHAT_SOVEREIGN=true`; otherwise it names the model and warns. Chat uses `PUBLIC_AI_*`; the Build may use any model. |
| 0003 data, not code | A Build writes JSON. `server/app.py` is the one generic server for every BFS number. |
| 0004 the Judge is the only gate | `build/judge_bridge.py` runs the team's `pipeline/judge` (`judge_claims` + new v1 adapter) and applies withheld attributes and the Build Floor. Without a judge model it says `not_run` everywhere, never "passed". |
| 0005 stateless, no query logs | No access logs. The browser holds the conversation. Situation details reach the Service Card via MCP Apps host context, **never** as tool arguments. Gap Reports reject personal data server-side. 90-day retention. |
| 0006 reference client + own MCP Apps host | Simplified per team decision: a small chat (not the Open WebUI fork) with its own MCP Apps host (`static/app.js`: sandboxed iframe, `ui/initialize`, `tool-input`/`tool-result`, `open-link`, `tools/call`, `size-changed`). |
| 0007 typed data + injection check | `schema.py` (amounts, days, document items, conditions); `build/provenance.py` (quote literally in source, value in quote, link on official domain or allow-list); the Judge's injection check on top. |

## Deliberate decisions to review (flagged, not silently settled)

1. **Handoff allow-list** (`data/handoff_allowlist.yml`): contains only `eumzug.swiss`. Wettingen and Dübendorf send move registrations there. ADR-0007 anticipated this list. Every addition is a team decision. Example of it working: Wettingen's `kitarechner.ch` link is withheld.
2. **Extra tools** `list_municipalities` and `send_feedback`, beyond the four in the ADRs: the first is for addressing the previous municipality, the second is the Feedback channel from ADR-0005, called from inside the Service Card.
3. **Prefill is prepare-and-copy**, not injection into the municipality's form. Cross-site forms can't be pre-filled without a municipality API (the Transaction tier, out of scope).
4. **No native tool calling.** Apertus on Public AI doesn't support the OpenAI `tools` parameter (OQ-2, litellm#21124). The client gives the model the compact `list_services` output and asks for one JSON plan; the backend makes the MCP calls. The model never states Service facts. Those come only from `get_service`.
5. **Judge fix:** `judge/injection.py` and `judge/pipeline.py` used `lstrip("www.")`, which strips *characters*. `wettingen.ch` became `ettingen.ch`, so every own-domain link was flagged as foreign. Changed to `removeprefix`.

## Demo data — what it is and isn't

- `data/captures/<slug>/*.txt`: the visible text of 9 official pages of wettingen.ch, schule-wettingen.ch and duebendorf.ch, captured in a browser on 2026-09-24. The build host's network couldn't reach those sites. Trimmed to the main content; staff names and third-party institution lists were removed.
- `data/extractions/<slug>.json`: the extraction step done by hand (by Claude), standing in for the build model until a key is configured. It goes through the same deterministic provenance gate as model output: every quote is checked literally against the capture.
- `data/inventories/`: the published result. `judge.status = "not_run"` because no judge model was available. The card says "Judge-Prüfung ausstehend". Run `uv run mmp seed` with `OPENAI_API_KEY` / `PUBLIC_AI_*` set to judge them for real, and `uv run mmp build <slug>` to replace captures with a real crawl.
- BFS numbers are only filled in `data/municipalities.yml` where they were checked against a source. The others are `null` until verified.

## Not done yet

- A real LLM run: extraction, Judge ensemble, Apertus planning quality (OQ-2) are untested against the live endpoint. Only against a local OpenAI-compatible fake.
- eCH-0070 import is written against the published XLSX but untested against the real file (column detection may need a tweak).
- The Open WebUI fork (ADR-0006) is replaced by this lightweight client for the MVP.
