# Build Plan — First Vertical Slice

## Goal

Prove this end-to-end path:

```text
municipality URL
→ reconnaissance
→ CrawlPlan IR
→ adaptive fetch
→ source snapshot
→ PageIR
→ small-model classification/extraction
→ ClaimIR
→ deterministic validation/provenance
→ targeted follow-up
→ canonical service JSON
```

Do not begin by attempting all seven municipalities.

## Phase 0 — Keep work scoped to pipeline/

All code, schemas, fixtures, baselines and docs for this subsystem stay under this directory.

Suggested structure:

```text
pipeline/
├── docs/                # optional future split; current design docs remain here
├── baseline/
├── schemas/
├── fixtures/
├── src/
│   ├── context/
│   ├── recon/
│   ├── planner/
│   ├── crawl/
│   ├── snapshot/
│   ├── extract/
│   ├── normalize/
│   ├── provenance/
│   └── orchestrator/
├── evals/
└── tests/
```

## Phase 1 — Baseline corpus

Use the research-agent baseline for the seven municipalities before tuning our crawler.

Purpose:

- reference services
- real source weirdness
- multilingual examples
- evidence/provenance examples
- comparison target for our pipeline

Treat service-count targets as soft budgets, not quotas.

## Phase 2 — Deterministic fetch + snapshot

Implement HTTP first:

- redirects
- content type
- canonical URL when observable
- timestamps
- SHA-256
- raw response storage
- cache
- retry/backoff
- basic robots/rate policy
- structured error representation

Success:

```text
URL → reproducible SourceSnapshot
```

## Phase 3 — Cleaner + PageIR

Extract deterministically:

- title
- headings
- main text
- internal/external links
- PDFs
- forms
- hreflang
- canonical link
- JSON-LD
- metadata

Success:

```text
SourceSnapshot → bounded PageIR
```

## Phase 4 — Browser fallback

Add Playwright/Crawl4AI only when HTTP is insufficient.

Record:

- fetch tier
- escalation reason
- rendering/interaction requirement

Do not make every request a browser request.

## Phase 5 — Typed planner

Implement `municipal-crawl-plan/v1`.

Planner receives:

- municipality context
- cheap reconnaissance
- discovered languages
- site scale signals

Planner returns:

- strategy
- roots
- budgets
- fetch policy
- language plan
- link policy
- stop rules

Validate before execution.

## Phase 6 — Small Apertus-compatible classifier

Input: PageIR.

Strict output:

- page role
- service likelihood
- authority signal
- follow-up candidates
- confidence/escalation reason

Start with any available model adapter if needed; keep the interface Apertus-compatible.

## Phase 7 — Service extraction to ClaimIR

Produce evidence-backed candidate claims.

Do not write final service records directly.

Deterministic code handles:

- date/currency parsing
- schema validation
- duplicate/conflict detection
- provenance
- evidence coverage

## Phase 8 — Compile reusable site adapters

When the planner discovers stable structure, emit cached rules/selectors.

Try adapter-first on subsequent runs.

Measure how much large-model work disappears.

## Phase 9 — Three-municipality proof

First trio:

1. **Binn** — full-crawl baseline
2. **Biel/Bienne** — multilingual identity test
3. **Zürich** — selective large-site crawl

Then:

4. Lugano
5. Lausanne
6. Ilanz/Glion
7. Bosco/Gurin

## First hackathon acceptance criteria

For each first-trio municipality:

- real service candidates with exact source references
- every populated structured field has evidence or is explicitly derived
- crawl strategy and stop reason recorded
- HTTP/browser fetch tier visible
- no fabricated fields
- multilingual duplicates detectable
- snapshot reprocessable without refetching
- at least one targeted follow-up
- at least one site adapter/rule compiled and replayed
- model escalation events recorded

## Architectural experiment

Measure:

```text
large-model calls
small-model calls
HTTP vs browser fetches
compiled-rule coverage
pages fetched
services retained
evidence coverage
precision / recall against baseline
```

The strongest proof is not "the agent can browse".

It is:

> **A capable model can compile an unfamiliar public website into a bounded acquisition program that deterministic software and a smaller public model can execute repeatedly.**

## Defer

Do not spend hackathon time on:

- vector database
- graph database
- broad national crawling
- sophisticated UI
- stealth/browser fingerprint work
- complex trust scoring
- continuous scheduler

Prove the ingestion/compiler boundary first.
