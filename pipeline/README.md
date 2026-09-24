# Pipeline = Scout

The `pipeline/` workstream is now the **Scout agent**.

Scout receives a municipality URL and a versioned Service Index, dynamically explores the municipality, semantically understands how its services are implemented, and compiles one validated municipality JSON artifact for the MCP Factory.

> **Scout converts heterogeneous municipal reality into a stable machine-readable municipality contract.**

## Boundary

```text
Municipality URL
      +
Service Index
      ↓
┌────────────────────────────┐
│ SCOUT STEP 1 — DISCOVER    │
│                            │
│ recon municipality         │
│ choose scouting strategy   │
│ find indexed services      │
│ notice new/variant services│
└─────────────┬──────────────┘
              ↓
        ScoutFindings[]
              ↓
┌────────────────────────────┐
│ SCOUT STEP 2 — COMPILE     │
│                            │
│ inspect service sources    │
│ understand local handling  │
│ preserve provenance        │
│ validate typed output      │
└─────────────┬──────────────┘
              ↓
   MunicipalityDiscovery JSON
              ↓
         MCP FACTORY
```

Scout does **not** generate the MCP server.

## Why AI matters

Municipal services are semantically similar but implemented heterogeneously.

The same service may appear as:

- a static page
- a structured service page
- a PDF or downloadable form
- an HTML form
- an external official portal
- a live feed
- a structured API
- a combination of several sources

Scout uses model reasoning to understand that local implementation and compress it into a stable typed representation.

Example:

```json
{
  "service_id": "waste_collection",
  "local_name": "Abfallentsorgung",
  "availability": "supported",
  "handling": {
    "type": "mixed",
    "interaction": "information",
    "summary": "The municipality publishes general waste guidance locally and provides the collection schedule as an official PDF.",
    "live": false
  },
  "sources": [
    {"url": "...", "role": "service_page"},
    {"url": "...", "role": "calendar_pdf"}
  ]
}
```

## Why Scout is agentic

There is no universal municipal crawl plan.

Scout first performs reconnaissance, then selects a bounded strategy such as:

- `broad_small_site`
- `service_directory`
- `targeted_large_city`
- `mixed_content`
- `custom`

Examples:

- **Binn** → broad small-site scouting
- **Dübendorf** → structured service-directory scouting
- **Zürich** → targeted large-city scouting
- **Bosco/Gurin** → broad scouting with aggressive municipal/noise discrimination

The model chooses the strategy; deterministic runtime enforces legal actions, budgets, URLs and stop rules.

## Service Index

Scout receives a versioned index of service concepts to actively investigate.

The index provides:

- stable service ID
- labels/synonyms
- optional discovery hints
- expected service family

Scout must also detect:

- `possible_new`
- `possible_variant`

These are proposals for later index evolution, not automatic changes.

## Scout output

The primary handoff is:

```text
municipality-discovery/v1
```

It contains:

- municipality identity
- run/build metadata
- Service Index version
- Scout strategy and reason
- service records
- local service names
- availability / coverage
- handling description
- source/resource bundle
- evidence / provenance
- index relation
- new-service suggestions
- discovery failures
- coverage summary

See `SERVICE_MODEL.md`.

## Framework

The target implementation uses:

- **Pydantic models** for all contracts
- **PydanticAI agents** for semantic planning and inspection
- typed graph/state orchestration for the two Scout stages
- ordinary Python for deterministic runtime operations

The LLM never owns network policy, crawl limits or provenance truth.

## Runtime principle

Use the cheapest sufficient acquisition method:

```text
HTTP
 ↓ insufficient
headless browser
 ↓ genuine interaction required
interactive/agentic browser
```

Browser escalation is an acquisition detail, not the Scout architecture.

## Core documents

- `ARCHITECTURE.md` — two-step Scout architecture
- `SERVICE_MODEL.md` — MunicipalityDiscovery contract
- `BUILD_PLAN.md` — implementation sequence
- `SEMANTIC_COMPILER.md` — semantic compression of heterogeneous services
- `CRAWL_STRATEGIES.md` — scouting strategies
- `TOOLING_AND_RUNTIME.md` — deterministic/agent framework split
- `PROVENANCE_AND_TRUST.md` — evidence boundary
- `MUNICIPALITY_BENCHMARK.md` — municipality stress cases
- `EVALS.md` — Scout evaluation

## Repository layout

The active implementation is intentionally small:

```text
pipeline/
├── README.md + architecture docs   # current Scout design
├── scout/                          # active executable Scout
├── observatory/                    # current Scout architecture/build view
└── legacy/                         # superseded experiments and contracts
```

Only the root Scout documents, `scout/`, and `observatory/` describe the current architecture.

`legacy/` is historical evidence. Its old Service Inventory, crawler prototype, baseline schemas and commands are **not current interfaces** and must not be used as the Factory contract. The current downstream boundary is `municipality-discovery/v1`.

## Core claim

> **The common standard is not how Swiss municipalities implement services. The common standard is the typed contract Scout compiles from that heterogeneity.**
