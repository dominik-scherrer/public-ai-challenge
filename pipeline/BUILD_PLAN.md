# Build Plan — Discovery First, MCP Compilation Second

## Goal

Prove:

```text
municipality URL
→ discover municipal services
→ group authoritative source bundles
→ Service Leads
→ hand off to Agent 2
→ compile local MCP capabilities
```

Agent 1 does not need to fully normalize service attributes.

## Phase 1 — Make discovery reliable

Current prototype priorities:

1. URL normalization + redirect/canonical deduplication
2. crawl prioritization and noise filtering
3. service-vs-noise classification
4. source-role classification
5. related-source grouping
6. provenance-preserving Service Lead output
7. graceful optional-model fallback

Success means:

> given a municipality, we find the meaningful service surfaces and hand off the right sources.

## Phase 2 — Minimal Service Lead schema

Implement a small contract:

```text
id
labels
service_type_hint
authority
source refs + roles
discovery evidence/confidence
crawl provenance
```

Do not add fee/eligibility/process fields to Agent 1 unless Agent 2 proves they are required for routing.

## Phase 3 — Source bundle grouping

For each likely service:

```text
service page
+ form
+ PDF
+ department/contact page
+ external official handoff
```

Group related sources without deeply interpreting them.

## Phase 4 — Agent 2 prototype

Give a Service Lead to a planning model and ask it to produce:

```text
mcp-capability-plan/v1
```

The plan should state:

- useful MCP capability/tools
- inputs
- source strategy
- handoffs
- limitations

## Phase 5 — MCP builder/runtime

Validate the capability plan and bind it to the allowed sources.

The builder—not the model—owns:

- runtime safety
- source boundaries
- schema validation
- packaging
- tool contract tests

## First discovery batch

The first batch should stress **different service-discovery shapes**, not multilingual normalization.

### Batch A — four complementary discovery cases

1. **Ausserberg VS — reference workflow / PDFs + administrative pages**
   - already used by the MVP plan
   - gives continuity with Patrick's reference scenarios
   - tests service + document + handoff discovery

2. **Binn VS — tiny site / broad crawl**
   - small enough to approach near-complete discovery
   - good deterministic baseline
   - already exposes useful edge cases such as Strahlerpatente

3. **Dübendorf ZH — structured i-web service catalogue**
   - tests a reusable CMS pattern
   - high value because one adapter may generalize to many municipalities
   - easier than starting with Zürich-scale complexity

4. **Bosco/Gurin TI — noisy mixed municipal/tourism site**
   - precision stress test
   - verifies that service discovery does not become generic local-content scraping

### Batch B — after the basic discovery contract works

5. **Airolo TI or Lugano TI** — Italian portal/form patterns
6. **Biel/Bienne BE** — multilingual service/source grouping
7. **Zürich ZH** — selective discovery at large scale
8. **Lausanne VD / Ilanz-Glion GR** — additional language/structure tests

The exact later set can change; Batch A should stay focused on distinct discovery architectures.

## Acceptance criteria for Batch A

- each real Service Lead points to at least one authoritative source
- obvious non-services are excluded
- source bundles preserve links to PDFs/forms/handoffs
- no final URL is processed repeatedly
- crawl strategy and stop reason are visible
- Binn can approach broad coverage without complex orchestration
- Dübendorf demonstrates a reusable structured-directory pattern
- Bosco/Gurin demonstrates precision under noisy content
- Ausserberg demonstrates compatibility with the team's MVP reference scenarios

## Defer from Agent 1

- universal fee normalization
- universal eligibility schema
- full eCH-0070 mapping
- perfect multilingual entity resolution
- national canonical service ontology
- generating final MCP code directly from raw pages

These may exist downstream if they prove useful.

## Core experiment

> **Can a lightweight discovery agent reliably produce enough service/source structure that a second agent can build a useful local MCP without a universal normalized municipal dataset?**
