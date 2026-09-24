# Swiss Grounding MCP — Provenance-Aware Service Ingestion

This directory defines the ingestion pipeline that turns heterogeneous Swiss municipal websites into structured, provenance-preserving service records suitable for an MCP server.

The core claim:

> **Do not build a generic scraper. Build a provenance-preserving municipal-service compiler with adaptive acquisition strategies.**

The system should answer not only what service exists, but also where every claim came from, when it was fetched, how it was transformed, how fresh it is, and why the crawler stopped.

## System boundary

```text
municipality
    ↓
context enrichment
    ↓
cheap reconnaissance
    ↓
planner / semantic compiler
    ↓
typed CrawlPlan IR
    ↓
deterministic crawl runtime
    ↓
source snapshots + PageIR
    ↓
small-model classification / extraction
    ↓
typed ClaimIR
    ↓
deterministic validation / normalization
    ↓
service records + provenance
    ↓
MCP-facing knowledge layer
```

The LLM is **not** the scraper and **not** the authority.

### Large-model role

Use a capable planner only where the website is unfamiliar or the evidence is ambiguous:

- understand an unfamiliar site structure
- select a crawl strategy
- choose relevant languages
- set budgets and stop rules
- compile site-specific extraction plans
- resolve hard conflicts or multilingual identity questions

### Small-model role

Use a cheaper constrained model, ultimately Apertus, for repetitive typed work:

- page classification
- service-vs-noise classification
- field extraction into strict schemas
- link relevance ranking
- obvious multilingual pairing

### Deterministic runtime role

Software owns:

- HTTP fetching
- browser escalation
- domain boundaries
- crawl budgets
- caching and snapshots
- canonicalization
- hashing and timestamps
- schema validation
- normalization
- duplicate/conflict detection
- stop conditions
- provenance bookkeeping

## Fetch principle

Use the cheapest sufficient tool:

```text
HTTP fetch
   ↓ insufficient / JS shell
headless browser
   ↓ real interaction required
agentic browser
```

A browser is a fallback, not the default.

## Documents

- `ARCHITECTURE.md` — end-to-end pipeline and model/runtime boundaries
- `CRAWL_STRATEGIES.md` — adaptive crawl modes, fetch escalation and stop rules
- `TOOLING_AND_RUNTIME.md` — candidate OSS components and runtime choices
- `SEMANTIC_COMPILER.md` — planner → typed IR → small-model execution design
- `PROVENANCE_AND_TRUST.md` — trust, provenance and evidence model
- `MUNICIPALITY_BENCHMARK.md` — seven representative test municipalities
- `SERVICE_MODEL.md` — canonical service representation
- `BUILD_PLAN.md` — first vertical slice and implementation sequence
- `EVALS.md` — benchmark and evaluation criteria

## Hackathon fit

The Swiss Grounding MCP challenge values grounding quality, useful Swiss coverage, jurisdiction, freshness, citations, unsupported-query handling, agent efficiency, response size, latency, caching, refresh design, maintainability and MCP contract quality.

This pipeline is designed to make those properties explicit and testable rather than implicit.
