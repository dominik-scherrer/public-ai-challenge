# Architecture — Adaptive Municipal Service Ingestion

## 1. Goal

Transform an official municipal entry point into structured, typed, provenance-preserving service records.

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

The pipeline should work across:

- very large city portals
- small municipality CMS sites
- multilingual websites
- external eGovernment portals
- service directories
- departmental pages
- PDFs and linked forms
- mixed municipal / tourism / association content

## 2. Pipeline

```text
URL
 │
 ▼
1. CONTEXT ENRICHMENT
   municipality metadata
   population
   language context
   canton / BFS identity
 │
 ▼
2. RECONNAISSANCE
   homepage
   robots.txt
   sitemap
   navigation
   language variants
   search
   service directory
   eGov portal links
 │
 ▼
3. ORCHESTRATION
   estimate scale
   choose crawl strategy
   choose languages
   set page / token budgets
   set stop rules
 │
 ▼
4. FETCH
   HTML / PDF / API / linked documents
 │
 ▼
5. SNAPSHOT
   URL
   retrieval timestamp
   response metadata
   content hash
   raw content
 │
 ▼
6. CLEAN + STRUCTURE
   remove navigation noise
   retain headings, links, tables, forms, metadata
 │
 ▼
7. CLASSIFY
   service page?
   department?
   form?
   transaction endpoint?
   PDF?
   tourism/commercial?
 │
 ▼
8. EXTRACT OBSERVATIONS
   raw facts with exact evidence
 │
 ▼
9. NORMALIZE
   map observations into canonical service concepts
 │
 ▼
10. VALIDATE
   schema
   jurisdiction
   source authority
   duplicates
   multilingual equivalence
 │
 ▼
11. GAP ANALYSIS
   what is missing?
   is targeted follow-up justified?
 │
 ├─ yes → bounded follow-up crawl
 └─ no  → stop
 │
 ▼
12. PUBLISH
   canonical service records
   provenance graph
   MCP-ready index
```

## 3. Source snapshot before interpretation

Never let an extractor directly create the only stored representation.

Always store:

```text
SOURCE SNAPSHOT
    ↓
OBSERVATIONS
    ↓
TYPED CLAIMS
    ↓
SERVICE RECORD
```

This allows:

- re-running improved extractors without re-fetching
- auditing changed interpretations
- comparing versions over time
- checking model mistakes against raw evidence
- reproducible tests

## 4. Agentic boundary

Agentic orchestration is justified where the pipeline must choose among known actions.

Good agentic tasks:

- classify the municipality website
- choose crawl strategy
- identify relevant language variants
- detect likely service directories
- rank candidate links for missing evidence
- decide whether a follow-up fetch is justified
- pair multilingual pages representing the same service

Bad agentic tasks:

- unconstrained browsing
- unlimited crawling
- deciding whether a URL may be fetched outside deterministic rules
- inventing service facts
- silently changing jurisdiction
- deciding freshness from intuition
- replacing deterministic validation

## 5. Bounded orchestration loop

```text
municipality profile
        +
reconnaissance result
        ↓
crawl planner
        ↓
known strategy
        ↓
observations
        ↓
coverage analysis
        ↓
┌───────────────┐
│ enough?       │
├───────┬───────┤
│ yes   │ no    │
▼       ▼
stop    targeted follow-up
```

Every iteration records:

- strategy
- reason
- budget
- URLs examined
- URLs retained
- languages attempted
- coverage gaps
- stop reason

## 6. Important principle

Population size is a hint, not the strategy.

Actual strategy depends on:

```text
population
+ estimated website size
+ sitemap availability
+ site search
+ service directory
+ eGov portal presence
+ language structure
+ observed branching factor
+ content density
+ crawl cost
```

Website structure overrides population when evidence disagrees.
