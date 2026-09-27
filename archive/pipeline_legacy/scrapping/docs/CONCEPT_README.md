# Swiss Grounding MCP — Provenance-Aware Service Ingestion

This package defines the concept for an adaptive ingestion pipeline that turns heterogeneous Swiss municipal websites into structured, provenance-preserving service records suitable for an MCP server.

The core claim:

> **Do not build a generic scraper. Build a provenance-preserving municipal-service compiler with adaptive acquisition strategies.**

The ingestion system should answer not only:

- What service exists?
- What are the requirements, fees, channels and responsible authorities?

But also:

- Where did every claim come from?
- When was it fetched?
- Was it official, observed, derived, inferred or dynamic?
- Which extraction method produced it?
- What evidence supports it?
- How fresh is it?
- How complete was the crawl?
- Why did the system stop crawling?

## System boundary

```text
municipality
    ↓
context enrichment
    ↓
website reconnaissance
    ↓
crawl-plan orchestration
    ↓
bounded scraping strategy
    ↓
source snapshots
    ↓
observations
    ↓
semantic interpretation
    ↓
typed service claims
    ↓
validation / reconciliation
    ↓
service records + provenance
    ↓
MCP-facing knowledge layer
```

The LLM is **not** the scraper and **not** the authority.

Its role is bounded:

- classify source/page types
- select an appropriate crawl strategy
- identify likely service content
- map heterogeneous wording into typed concepts
- decide which evidence gaps justify targeted follow-up

Deterministic software owns:

- HTTP fetching
- crawl budgets
- domain boundaries
- canonicalization
- hashing
- timestamps
- storage
- schema validation
- duplicate handling
- stop conditions
- provenance bookkeeping

## Documents

- `ARCHITECTURE.md` — full pipeline and orchestration model
- `PROVENANCE_AND_TRUST.md` — trust, provenance and evidence model
- `CRAWL_STRATEGIES.md` — adaptive scraper modes and orchestration
- `MUNICIPALITY_BENCHMARK.md` — seven representative test municipalities
- `SERVICE_MODEL.md` — canonical service representation
- `BUILD_PLAN.md` — first vertical slice and implementation sequence
- `EVALS.md` — benchmark and evaluation criteria

## Hackathon fit

The Swiss Grounding MCP challenge values grounding quality, useful Swiss coverage, jurisdiction, freshness, citations, unsupported-query handling, agent efficiency, response size, latency, caching, refresh design, maintainability and MCP contract quality.

This ingestion architecture is intended to make those properties visible and testable rather than implicit.
