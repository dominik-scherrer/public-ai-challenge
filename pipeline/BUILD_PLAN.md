# Build Plan — Scout MVP

## Goal

Build one working Scout pipeline:

```text
Municipality URL
+
Service Index
→ adaptive scouting
→ semantic service inspection
→ MunicipalityDiscovery JSON
```

The MCP Factory is a downstream workstream.

## Phase 1 — Contracts first

Implement Pydantic models for:

- `ServiceIndex`
- `ServiceIndexEntry`
- `ScoutStrategy`
- `ScoutFinding`
- `SourceRef`
- `Handling`
- `MunicipalityService`
- `CatalogSuggestion`
- `CoverageSummary`
- `MunicipalityDiscovery`

The first stable boundary is:

```text
municipality-discovery/v1
```

## Phase 2 — Service Index

Create:

```text
pipeline/scout/catalog/services.json
```

Start with the currently agreed factory capabilities/services.

Each index entry should contain:

- stable ID
- multilingual labels/synonyms
- optional discovery hints
- status/version metadata

Scout can propose new or variant services, but the index changes only through review.

## Phase 3 — deterministic acquisition tools

Reuse existing crawler work where useful.

Implement narrow tools/interfaces for:

- fetch URL
- parse page
- discover links
- normalize URL
- snapshot source
- inspect sitemap
- inspect navigation
- classify source/resource type

No LLM should own request policy.

## Phase 4 — Recon + Strategy agent

Build the first PydanticAI reasoning step.

Input:

- municipality URL
- cheap reconnaissance
- Service Index metadata

Output:

```text
ScoutStrategy
```

Acceptance:

- Binn → broad-small-site style strategy
- Dübendorf → service-directory style strategy
- Zürich → targeted-large-city style strategy
- Bosco/Gurin → mixed-content strategy

The exact labels can evolve; the behavioral difference is what matters.

## Phase 5 — Scout Step 1: discover

Execute the strategy.

For indexed services:

```text
find candidate sources
→ classify relevance
→ retain official resources
→ mark unresolved where necessary
```

Also collect possible new/variant service candidates.

Output:

```text
ScoutFindings[]
```

## Phase 6 — Scout Step 2: understand

For each finding/source bundle, use semantic reasoning to compile:

- local service name
- index relation
- availability
- handling type
- interaction type
- semantic handling summary
- source roles
- live/static status
- external system/handoff where applicable
- limitations / gaps

The model should summarize how the municipality handles the service, not attempt universal deep normalization.

## Phase 7 — Compile + validate

Deterministically compile findings into:

```text
MunicipalityDiscovery
```

Validate:

- every supported service has sources
- every URL is valid
- every handling enum is legal
- not-observed remains distinct from unavailable
- new-service suggestions have evidence
- crawl strategy and stop reason are preserved

## Phase 8 — First municipality loop

Recommended first loop:

1. **Binn** — small/broad discovery
2. **Ausserberg** — reference product workflow
3. **Dübendorf** — structured service catalogue
4. **Bosco/Gurin** — mixed-content precision
5. **Zürich** — large-city targeted discovery

The goal is not merely coverage.

Each run should improve:

- Service Index
- strategy selection
- semantic handling types
- discovery prompts
- source roles
- factory assumptions

## MVP acceptance

Scout MVP succeeds when:

- one command accepts municipality URL + identity
- Recon chooses a typed strategy
- indexed services are explicitly checked
- new candidates can be proposed
- discovered services include authoritative source bundles
- the LLM produces a useful semantic handling description
- final output validates as `MunicipalityDiscovery`
- deterministic mode can still fetch/snapshot/validate without model ownership of crawl policy
- the MCP Factory can consume the JSON without rediscovering the municipality website

## Defer

Do not prioritize yet:

- perfect national ontology
- full field-level normalization of every service
- universal eCH-0070 mapping
- transactions
- deep PDF interpretation unless needed for the first factory proof
- complex UI
- nationwide crawling
- autonomous browser wandering

## Primary experiment

> **Can one adaptive Scout agent understand very different municipal websites well enough to compile each into the same stable municipality contract for an MCP Factory?**
