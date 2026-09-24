# Agent Scrap MVP

Agent Scrap is the discovery-side agent for the municipal grounding pipeline.

Its job is intentionally narrow:

> **Find real municipal services, preserve the authoritative sources, bundle related source material, and emit observations that can ground the MCP tool hypotheses.**

It does **not** normalize all service details and it does **not** build the MCP runtime.

## Architecture

```text
municipality URL
→ bounded HTTP crawl
→ PageIR
→ deterministic heuristic classification
→ optional bounded model classification
→ source bundling
→ ServiceLead[]
→ tool-observations.json
```

Python owns state, crawl policy, deduplication and provenance. The model is optional and bounded to page classification.

## Run

From the repository root:

```bash
python3 pipeline/agent_scrap/agent.py \
  https://www.binn.ch/ \
  --municipality Binn \
  --canton VS \
  --max-pages 20 \
  --max-depth 2 \
  --model-mode off \
  --out /tmp/agent-scrap-binn
```

### Model modes

- `off` — deterministic baseline only
- `candidate` — use the model only for plausible service pages
- `always` — model-classify every fetched HTML page

Without model configuration, Agent Scrap still works fully in deterministic mode.

Optional OpenAI-compatible configuration:

```bash
export PUBLIC_AI_BASE_URL='https://provider.example/v1'
export PUBLIC_AI_API_KEY='...'
export PUBLIC_AI_MODEL='model-name'
```

or set `PUBLIC_AI_ENDPOINT` directly.

## Output

```text
<run>/
├── crawl-report.json
├── sources.jsonl
├── service-leads.jsonl
├── tool-observations.json
├── failures.jsonl
├── snapshots/
└── pages/
```

### Service Lead

A Service Lead contains:

- local official label
- service type hint
- municipality/canton
- primary source
- related forms/PDFs/contact pages
- discovery confidence/evidence

It deliberately does not require normalized fees, eligibility, requirements or process data.

### Tool observations

`tool-observations.json` uses the grounding-loop contract:

```text
agent-scrap-tool-observations/v1
```

The output can be fed into the grounding matrix from the tool-grounding workstream.

Agent Scrap is conservative: it only emits a supported observation when the discovery shape gives enough evidence for the tool hypothesis. Absence is not treated as negative evidence.

## MVP behavior

Implemented:

- public HTTP(S) validation
- redirect validation
- URL normalization
- final/canonical URL deduplication
- bounded crawl queue
- service/noise prioritization
- source snapshots
- PageIR
- service lead generation
- related form/PDF/contact source bundling
- optional OpenAI-compatible classifier
- graceful model fallback
- tool grounding observations

Not yet implemented:

- robots/sitemap parser
- PDF text extraction
- browser fallback
- multi-page semantic grouping beyond directly linked sources
- learned CMS adapters
- multilingual equivalence
- application of observations to the grounding matrix in-process

## Tests

```bash
python3 -m unittest discover -s pipeline/agent_scrap/tests -v
```

The MVP test suite covers URL normalization, service detection, tourism/noise rejection, source bundling, grounding observations, model fallback and redirect deduplication.
