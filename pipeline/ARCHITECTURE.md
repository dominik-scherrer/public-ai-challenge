# Architecture — Adaptive Municipal Service Ingestion

## 1. Goal

Transform an official municipal entry point into structured, typed, provenance-preserving service records while minimizing unnecessary crawling and expensive model use.

Input:

```text
https://municipality.example.ch/
```

Output:

```text
service[]
authority[]
jurisdiction[]
procedure[]
source[]
evidence[]
```

The pipeline must work across large city portals, small municipality CMS sites, multilingual websites, external eGovernment portals, PDFs, departmental pages and mixed municipal/tourism content.

## 2. Architecture

```text
MUNICIPALITY
    │
    ▼
CONTEXT ENRICHMENT
BFS/canton/language context
    │
    ▼
CHEAP RECONNAISSANCE
homepage / robots / sitemap / nav / hreflang / portal links
    │
    ▼
PLANNER / SEMANTIC COMPILER
large model only when useful
    │
    ▼
CrawlPlan IR
    │
    ▼
DETERMINISTIC RUNTIME
HTTP first → browser fallback → interactive fallback
    │
    ├── source snapshot
    └── PageIR
            │
            ▼
SMALL CONSTRAINED MODEL
classify / extract / rank links
            │
            ▼
ClaimIR
            │
            ▼
VALIDATOR / COMPILER
schema / provenance / normalization / conflicts
            │
      ┌─────┴─────┐
      │           │
 confident      ambiguous
      │           │
      ▼           ▼
    STORE      LARGE MODEL
```

## 3. Source snapshot before interpretation

Never let an extractor directly create the only stored representation.

Always preserve:

```text
SOURCE SNAPSHOT
    ↓
PageIR
    ↓
OBSERVATIONS
    ↓
ClaimIR
    ↓
SERVICE RECORD
```

This allows re-running improved extractors without re-fetching, auditing changed interpretations, comparing versions over time and reproducing tests.

## 4. Fetch escalation

A headless browser is not the baseline.

### Tier 1 — HTTP

Prefer direct HTTP when it yields useful source content.

Use it for:

- static HTML
- sitemaps
- PDFs
- JSON/API endpoints
- canonical metadata
- most traditional municipal CMS pages

### Tier 2 — Headless browser

Escalate when:

- the HTTP response is a JavaScript shell
- meaningful content appears only after rendering
- navigation or content depends on client-side state
- a service directory requires browser execution

### Tier 3 — Agentic browser

Escalate only when a real interaction is necessary:

- multi-step portal navigation
- menus/forms that cannot be represented by stable selectors
- dynamic transaction flows needed for discovery

The fetcher records which tier was used and why.

## 5. Agentic boundary

Agentic orchestration is justified where the pipeline must choose among known actions.

Good model tasks:

- classify the municipality/site
- choose FULL / SECTION / DIRECTORY / DISCOVERY
- choose relevant language variants
- rank evidence-bearing links
- compile extraction rules
- resolve hard multilingual equivalence
- decide whether uncertainty warrants escalation

Bad model tasks:

- unconstrained browsing
- unlimited crawling
- ignoring deterministic URL/domain policy
- inventing service facts
- replacing schema validation
- deciding freshness from intuition

## 6. Semantic compiler boundary

The large model should emit typed intermediate representations rather than directly performing the entire crawl.

Example:

```json
{
  "schema": "municipal-crawl-plan/v1",
  "strategy": "directory_crawl",
  "roots": [{"url": "...", "role": "service_directory"}],
  "languages": ["de"],
  "fetch_policy": {
    "prefer": "http",
    "browser_fallback": true
  },
  "budget": {
    "max_pages": 250,
    "max_depth": 4
  },
  "stop": {
    "directory_exhausted": true,
    "novelty_window": 20
  }
}
```

Software validates and executes this plan.

## 7. Small-model execution

The small model receives bounded inputs and strict output schemas.

Example page classification:

```json
{
  "page_role": "service",
  "service_probability": 0.94,
  "follow_candidates": []
}
```

Example field extraction:

```json
{
  "claims": [
    {
      "field": "fees[0].raw",
      "value": "CHF 30",
      "evidence_span": [182, 188]
    }
  ]
}
```

Deterministic code then parses currency/amount, validates schema and attaches provenance.

## 8. Compile successful behavior into rules

Unknown sites may initially require model help. Repeated crawls should become cheaper.

```text
model discovers structure
        ↓
typed selector/extraction plan
        ↓
validated
        ↓
cached site adapter
        ↓
future crawl without large model
```

This is a core design goal: **discover with intelligence, formalize, replay cheaply.**

## 9. Strategy selection signals

Population is only a hint.

Strategy depends on:

```text
population
+ estimated site size
+ sitemap availability
+ service directory
+ search
+ eGov portal presence
+ language structure
+ branching factor
+ content density
+ browser requirement
+ observed crawl cost
```

Website evidence overrides demographic expectations.
