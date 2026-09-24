# Scout MVP-1 Build Plan

## Goal

Prove one real end-to-end Scout run:

```text
Municipality URL
+ Service Index
→ recon
→ typed strategy
→ deterministic acquisition
→ indexed-service discovery
→ semantic inspection
→ MunicipalityDiscovery JSON
```

MVP-1 is complete when Binn can produce a valid `municipality-discovery/v1` artifact and the artifact is useful to the downstream MCP Factory without re-scouting the website.

## Package slices

### Slice A — contracts

Implement typed Pydantic models for:

- municipality identity
- Service Index
- recon result
- Scout strategy
- source references
- Scout findings
- service handling
- municipality service
- catalog suggestions
- coverage
- final MunicipalityDiscovery

Acceptance:

- fixtures round-trip through Pydantic validation
- `not_observed` is distinct from `unavailable`

### Slice B — deterministic runtime

Implement:

- public HTTP(S) URL validation
- URL normalization
- redirects
- HTML fetch
- simple PageIR
- bounded broad crawl
- targeted crawl from homepage links
- source IDs and retrieval timestamps

Acceptance:

- no model required
- request budget is enforced
- same URL is not processed twice
- source metadata survives into findings

### Slice C — Service Index

Start with five concepts:

1. waste collection
2. move in
3. office hours
4. forms
5. building application

The index includes German discovery synonyms.

Scout may emit `possible_new` findings for source-backed services that do not match the index.

### Slice D — PydanticAI agents

Two agents only:

#### Strategy Agent

Input:

- ReconResult
- Service Index summary

Output:

- ScoutStrategy

MVP strategies:

- `broad_small_site`
- `targeted`

#### Inspector Agent

Input:

- ScoutFinding
- bounded source/page evidence
- matching Service Index entry if available

Output:

- ServiceInterpretation

The model may interpret:

- local service name
- index relation
- availability
- handling type
- interaction type
- semantic handling summary
- confidence
- limitations

The model may not invent or rewrite source URLs. Provenance remains deterministic.

### Slice E — orchestrator

Sequence:

```text
recon
→ choose strategy
→ execute strategy
→ discover candidates
→ inspect candidates
→ add not_observed entries
→ compile coverage
→ validate MunicipalityDiscovery
→ write artifacts
```

Artifacts:

```text
discovery.json
sources.jsonl
crawl-report.json
```

## Iteration sequence

1. Binn — prove broad scouting + possible-new service detection
2. Ausserberg — prove factory usefulness
3. Dübendorf — add service-directory strategy
4. Bosco/Gurin — improve mixed-content precision
5. Zürich — add true large-city targeted strategy

## Deliberately deferred

- Pydantic Graph orchestration
- browser fallback
- sitemap parser
- PDF content extraction
- multilingual equivalence
- nationwide Service Index
- automatic Service Index mutation
- MCP generation

Pydantic Graph comes after the vertical slice works. The state machine is already explicit enough to migrate without changing contracts.

## Definition of done

```bash
cd pipeline/scout
uv sync
uv run scout https://www.binn.ch/ --municipality Binn --canton VS --out runs/binn
```

must produce a schema-valid `runs/binn/discovery.json`.
