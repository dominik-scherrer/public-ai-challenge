# Scraper Prototype v0

First executable slice of the provenance-aware municipal ingestion pipeline.

## What it does

```text
municipality URL
→ safe bounded HTTP crawl
→ raw source snapshots
→ PageIR
→ heuristic candidate detection
→ optional event API extraction
→ partial service records + provenance
```

This prototype intentionally does **not** implement the large-model planner, browser fallback, PDF parsing, multilingual service merging, or final MCP runtime yet.

## Run

From the repository root:

```bash
python pipeline/prototype/scraper.py https://www.binn.ch/ \
  --municipality Binn \
  --canton VS \
  --max-pages 20 \
  --max-depth 2 \
  --out pipeline/prototype/output/binn
```

The crawler is conservative:

- HTTP(S) only
- rejects local/private destinations
- validates redirects
- same-origin traversal only
- bounded page/depth budgets
- delay between requests
- obvious tourism/news noise is deprioritized
- external links remain visible in PageIR but are not crawled

## Event API / Apertus-compatible model

The crawler has a dependency-free OpenAI-compatible adapter.

Use a full endpoint:

```bash
export PUBLIC_AI_ENDPOINT='https://.../v1/chat/completions'
```

or a base URL:

```bash
export PUBLIC_AI_BASE_URL='https://.../v1'
```

Then set:

```bash
export PUBLIC_AI_API_KEY='...'
export PUBLIC_AI_MODEL='...'
```

The exact event API snippet can be mapped here without changing crawler logic. If the event requires custom headers or a slightly different payload, only `model_adapter.py` should change.

Modes:

- `off` — deterministic heuristic only
- `candidate` — model only on plausible service pages
- `always` — model on every HTML page

`candidate` is the intended default.

## Outputs

```text
output/
├── crawl-report.json
├── sources.jsonl
├── services.jsonl
├── failures.jsonl
├── snapshots/
│   └── src_....html
└── pages/
    └── src_....json
```

### Provenance

Each fetched source records:

- URL
- retrieval time
- HTTP metadata
- SHA-256
- fetch tier
- official municipality publisher classification

Every service candidate keeps `source_refs` and field-level evidence where available.

## Tests

```bash
python -m unittest discover -s pipeline/prototype/tests -v
```

Tests use a local fixture and do not access the network.

## Current limitations

- no robots.txt parser yet
- no sitemap discovery
- no PDF text extraction
- no headless-browser fallback
- no full CrawlPlan planner
- no multilingual service deduplication
- main-text extraction still includes some navigation text
- model output is not yet JSON-Schema validated
- no deterministic fee/date/contact extraction yet

These are visible limitations, not hidden assumptions.
