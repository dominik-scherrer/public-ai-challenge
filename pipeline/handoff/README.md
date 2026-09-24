# MCP Inventory Handoff

This directory is the collaboration boundary between the ingestion/scraping workstream and the shared MCP runtime.

## Start here

If you work on the MCP/runtime side, read:

- [MCP_CONSUMER.md](MCP_CONSUMER.md) — what to load, what the runtime can assume, and recommended integration order
- [WHY_THIS_HANDOFF.md](WHY_THIS_HANDOFF.md) — why the boundary is a typed Service Inventory rather than crawler internals
- [MESSAGE_TO_MCP.md](MESSAGE_TO_MCP.md) — short handoff message for the runtime owner

First delivery:

- [delivery-2026-09-24/](delivery-2026-09-24/) — Ausserberg + seven benchmark municipalities

## Contract

The crawler may use any internal representation. The downstream contract is a versioned **Service Inventory** built from:

- `sources.jsonl`
- `services.jsonl`

Compile a municipality batch:

```bash
python pipeline/handoff/compile_inventory.py \
  --input pipeline/scrapping/baseline/ausserberg \
  --out pipeline/handoff/output/ausserberg-v0 \
  --municipality Ausserberg \
  --canton VS \
  --official-url https://www.ausserberg.ch/ \
  --language de
```

Output:

```text
ausserberg-v0/
├── inventory.json
├── documents.jsonl
└── build-report.json
```

`inventory.json` is the primary runtime handoff.

The MCP workstream should integrate against this artifact, **not against crawler internals** such as PageIR, snapshots, or a specific scraping implementation.

## First integration municipality

Use **Ausserberg** first because the repository's MVP plan already defines its user scenarios and it exposes several service shapes: information, forms, municipal requests, documents and external official routing.

Binn, Biel/Bienne and Zürich remain important crawler/architecture stress tests, with Lausanne, Lugano, Ilanz/Glion and Bosco/Gurin extending the language and small-municipality coverage.
