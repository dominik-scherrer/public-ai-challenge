# MCP Inventory Handoff

This directory is the boundary between crawler work and the shared MCP runtime.

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

## Contract

`inventory.json` is the primary runtime handoff. It contains:

- municipality/build metadata
- runtime compatibility
- service records
- official handoff URLs
- source references
- field-level evidence
- completeness
- trust/conflict state
- only the source metadata referenced by published services

`documents.jsonl` is the document/search sidecar for `search_documents`.

`build-report.json` is the quality gate. A batch is not silently promoted: unresolved source references fail compilation, and unchecked evidence/conflicts remain visible as warnings.

The MCP team should integrate against this artifact, **not against crawler internals** such as PageIR, snapshots, or a specific scraping implementation.

## First integration batch

Use **Ausserberg** for the first product/MCP integration because the repository's MVP plan already defines its user scenarios and heterogeneous service shapes. Keep Binn, Biel/Bienne and Zürich as pipeline stress tests.

A useful first Ausserberg inventory is small and evidence-rich: roughly 6–10 services covering residence/moving, office/contact, facility requests, forms/documents and at least one external official handoff.
