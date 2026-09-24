# Message to MCP person

**Scraping calling MCP 👋**

I have a first handoff ready from the ingestion/scraping side.

The important thing: you do **not** need to integrate against my crawler or PageIR. I added a stable handoff contract under:

```text
pipeline/handoff/
```

For the first batch, use:

```text
pipeline/handoff/delivery-2026-09-24/
```

Each municipality has:

```text
inventory.json
documents.jsonl
build-report.json
```

The main file for you is `inventory.json` (`mmp-service-inventory/v0`).

It is shaped for the four planned MCP tools:

- `list_services`
- `find_service`
- `get_service`
- `search_documents`

I would start with **Ausserberg** because it has the richest mix of service types and is already our reference municipality.

The current batch also includes Binn, Zürich, Lausanne, Lugano, Ilanz/Glion and Bosco/Gurin. Biel/Bienne is intentionally included as an explicit empty/partial build because the official site retrieval failed in this first pass.

One important caveat: this first delivery is a **source-backed seed batch**, not yet the full native crawler output. I did that deliberately so you can already build against the interface. As the crawler improves, I can replace these inventories without you having to change your MCP integration.

Docs:

```text
pipeline/handoff/MCP_CONSUMER.md
pipeline/handoff/WHY_THIS_HANDOFF.md
pipeline/handoff/README.md
```

So the contract between us is basically:

```text
scraping / ingestion
→ Service Inventory
→ MCP runtime
```

If that shape works for your runtime, I’ll treat it as the stable boundary and keep feeding newer batches into it.
