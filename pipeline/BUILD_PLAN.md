# Build Plan — First Vertical Slice

## Goal

Prove one end-to-end pipeline:

```text
municipality URL
→ reconnaissance
→ strategy selection
→ fetch
→ source snapshot
→ service extraction
→ provenance
→ targeted follow-up
→ canonical service JSON
```

Do not begin by attempting all seven municipalities.

## Phase 0 — Repository skeleton

Suggested structure:

```text
/
├── docs/
│   └── ingestion/
├── src/
│   ├── context/
│   ├── recon/
│   ├── crawl/
│   ├── snapshot/
│   ├── extract/
│   ├── normalize/
│   ├── provenance/
│   └── orchestrator/
├── schemas/
├── fixtures/
├── evals/
└── tests/
```

## Phase 1 — Deterministic fetch + snapshot

Implement:

- same-domain HTTP fetcher
- redirects
- content type
- canonical URL
- timestamps
- SHA-256
- raw HTML storage
- cache
- basic error representation

Success:

```text
URL → reproducible source snapshot
```

## Phase 2 — Cleaner + structural parser

Extract:

- title
- headings
- main text
- internal links
- external links
- PDFs
- forms
- hreflang
- canonical link
- JSON-LD
- metadata

No LLM required.

## Phase 3 — Page classifier

Input:

```text
structured page representation
```

Output:

```json
{
  "page_type": "service_page",
  "contains_service": true,
  "authority_signal": "official",
  "language": "de",
  "candidate_follow_links": []
}
```

Use strict schema output.

## Phase 4 — Service extractor

Input:

- structured page
- canonical service schema
- source metadata

Output:

- observations
- typed candidate claims
- field-level evidence references

Do not write directly into final storage without validation.

## Phase 5 — Provenance assembler

Every service response must expose:

- source registry
- retrieval times
- hashes
- field evidence
- classifications
- extractor version
- conflicts
- freshness

## Phase 6 — Reconnaissance + strategy planner

Given municipality entry URL:

Inspect cheaply:

- robots.txt
- sitemap
- homepage navigation
- language alternatives
- likely service directory
- eGov links
- rough branching / page scale

Produce:

```json
{
  "strategy": "section_crawl",
  "reason": [...],
  "languages": ["de"],
  "page_budget": 200,
  "candidate_roots": [...]
}
```

## Phase 7 — First adaptive loop

Implement:

```text
crawl
→ extract
→ coverage analysis
→ choose at most N targeted follow-ups
→ crawl
→ stop
```

Start with `N = 3`.

## Phase 8 — Three-municipality proof

First test trio:

1. **Binn** — easiest full-crawl baseline
2. **Biel/Bienne** — multilingual identity test
3. **Zürich** — selective-crawl stress test

This gives three fundamentally different acquisition modes.

Once these work, add:

4. Lugano
5. Lausanne
6. Ilanz/Glion
7. Bosco/Gurin

## First hackathon acceptance criteria

For each first-trio municipality:

- produce at least 10 real municipal service candidates
- every service has source URL + retrieval timestamp
- every non-empty structured field has evidence
- no fabricated fields
- crawl strategy and stop reason recorded
- duplicate multilingual services are detectable
- source snapshot can be reprocessed without refetching
- at least one service uses targeted follow-up evidence

## Do not build yet

Defer:

- vector database
- graph database
- full MCP server
- sophisticated UI
- automatic national crawling
- broad ontology
- complex trust scoring
- continuous schedulers

Prove the ingestion boundary first.
