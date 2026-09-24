# Scout MVP

Scout is the discovery-side agent in the Municipality MCP Factory architecture.

```text
Municipality URL + Service Index
→ Scout
→ MunicipalityDiscovery JSON
→ MCP Factory
```

MVP-1 implements the first executable Scout vertical slice.

## Install

```bash
cd pipeline/scout
uv sync
```

PydanticAI is pinned locally to the Scout package so the rest of the team repository does not need to change dependencies.

## Run without a model

```bash
uv run scout https://www.binn.ch/ \
  --municipality Binn \
  --canton VS \
  --out runs/binn \
  --model-mode off
```

This uses deterministic strategy fallback and deterministic service interpretation.

## Run with PydanticAI

Set a PydanticAI-compatible model string:

```bash
export SCOUT_MODEL='openai:YOUR_MODEL'
export OPENAI_API_KEY='...'
```

Then:

```bash
uv run scout https://www.binn.ch/ \
  --municipality Binn \
  --canton VS \
  --out runs/binn \
  --model-mode agent
```

The model is only used for:

- strategy selection
- semantic service interpretation

Networking, crawl budgets, provenance and artifact writing remain deterministic.

## Output

```text
runs/binn/
├── discovery.json
├── sources.jsonl
└── crawl-report.json
```

## Current MVP strategies

- `broad_small_site`
- `targeted`

The architecture is intentionally ready for later `service_directory` and `mixed_content` strategies.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```
