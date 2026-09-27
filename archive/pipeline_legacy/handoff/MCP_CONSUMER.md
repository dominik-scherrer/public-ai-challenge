# MCP Consumer Guide

This folder is the contract between the ingestion workstream and the MCP/runtime workstream.

## Short version

Do **not** integrate against crawler internals.

Use:

```text
pipeline/handoff/delivery-2026-09-24/<municipality>/inventory.json
```

as the primary input for the MCP runtime.

The current first delivery contains:

- Ausserberg
- Binn
- Biel/Bienne
- Zürich
- Lausanne
- Lugano
- Ilanz/Glion
- Bosco/Gurin

Each municipality folder contains:

```text
inventory.json
documents.jsonl
build-report.json
```

## What the MCP side can assume

Each `inventory.json` follows:

```text
mmp-service-inventory/v0
```

and exposes **semantic capabilities**, not concrete MCP tool names.

Patrick's live `minigmeind` server currently exposes a broader domain-specific tool surface (moving, forms, permits, waste, facilities, finance, reporting, etc.). The inventory intentionally does not mirror those names.

The MCP implementation should treat the inventory as **canonical data** and map its capability tags to the current tool contracts.

See [MCP_CAPABILITY_MATRIX.md](MCP_CAPABILITY_MATRIX.md) for the live tool → required data mapping.

## What is inside

### inventory.json

Primary runtime input.

Contains:

- municipality identity
- build metadata
- source languages
- normalized service records
- service IDs
- categories
- summaries
- delivery modes
- official source references
- completeness state
- trust/conflict state
- source metadata

### documents.jsonl

Sidecar for document-oriented retrieval.

This is intentionally sparse in the first seed batch. It is the place for:

- PDFs
- regulations
- forms
- document excerpts
- page/section references

The MCP `search_documents` implementation can use this file independently from the structured service inventory.

### build-report.json

Quality and handoff state.

Use this to determine whether a municipality should be exposed, hidden, or labelled partial.

Important fields:

- `handoff_ready`
- `coverage`
- counts
- warnings

Example: Biel/Bienne is deliberately present as an empty partial build because the official site could not be reliably retrieved in the first seed run. The gap is explicit instead of being silently filled from weaker sources.

## Why the boundary exists

The ingestion pipeline has richer internal representations:

```text
raw source
→ SourceSnapshot
→ PageIR
→ ClaimIR
→ validated service record
```

Those are useful for crawling, provenance and debugging, but they should not become MCP runtime dependencies.

The runtime should consume a stable Service Inventory so that we can change:

- crawler implementation
- extraction model
- planning strategy
- source parsing
- validation logic

without forcing changes in the MCP server.

This is the main collaboration boundary:

```text
SCRAPING / INGESTION
        ↓
Service Inventory
        ↓
MCP RUNTIME
        ↓
ChatGPT / Claude / Open WebUI / clients
```

## First delivery status

The current batch is a **source-backed seed delivery**, not a claim of exhaustive municipal coverage.

It exists to unblock MCP integration now.

The native crawler can later replace the seed inventories with fuller generated inventories while keeping the same contract.

### Current counts

| Municipality | Services | Sources | Handoff ready |
|---|---:|---:|---|
| Ausserberg | 6 | 6 | yes |
| Binn | 3 | 3 | yes |
| Biel/Bienne | 0 | 0 | no |
| Zürich | 3 | 3 | yes |
| Lausanne | 3 | 3 | yes |
| Lugano | 3 | 3 | yes |
| Ilanz/Glion | 5 | 3 | yes |
| Bosco/Gurin | 3 | 1 | yes |

## Recommended MCP integration order

Start with **Ausserberg**.

Why:

- it is the product/MCP reference municipality in the MVP plan
- it includes different service shapes
- it has municipal forms, information, requests and external routing
- it is good for exercising all four MCP tools

Then test:

1. Binn — sparse municipality
2. Ilanz/Glion — smaller multilingual / federated services
3. Lugano — eGovernment service portal
4. Lausanne — French service model
5. Zürich — large mature portal
6. Bosco/Gurin — noisy/sparse small municipality
7. Biel/Bienne — once retrieval is fixed

## Runtime mapping

Patrick's MCP owns the public tool surface.

Examples:

```text
list_services
  ← capability: service_catalog

get_move_in_requirements
  ← capability: residence_registration
  ← requirements + documents + authority + channel + evidence

get_office_hours
  ← capability: office_hours
  ← typed office/hours data + evidence

get_building_application_requirements
  ← capability: building_application
  ← requirements + authority + official handoff + evidence
```

The mapping belongs in the MCP/runtime layer, not in the crawler.

Do not invent missing attributes.

If `completeness.<field> == "unknown"`, return that as unavailable/unknown instead of generating a value.

## Compiler for future batches

Future crawler output can be converted with:

```bash
python pipeline/handoff/compile_inventory.py \
  --input <crawler-output-folder> \
  --out <handoff-folder> \
  --municipality <name> \
  --canton <code> \
  --official-url <url> \
  --language <lang>
```

Expected crawler inputs:

```text
sources.jsonl
services.jsonl
```

The compiler validates source references and emits the same runtime contract.

## Ownership

### Ingestion workstream owns

- discovery
- crawling
- source snapshots
- extraction
- provenance
- normalization
- completeness
- conflict detection
- producing the Service Inventory

### MCP workstream owns

- loading inventories
- search/indexing
- MCP tool contracts
- runtime response shape
- endpoint hosting
- host/client compatibility
- presenting source links and unknown fields correctly

The MCP side should not need to understand how a municipality was crawled.
