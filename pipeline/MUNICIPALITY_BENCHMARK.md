# Municipality Discovery Benchmark

## Goal

Benchmark **service discovery and authoritative-source handoff**, not full service normalization.

The important question is:

> Can Agent 1 find the services a municipality exposes and package the right authoritative sources for Agent 2?

## Batch A — first implementation benchmark

| Municipality | Discovery shape | Why it belongs in Batch A |
|---|---|---|
| **Ausserberg VS** | administrative pages + PDFs/forms/handoffs | aligns discovery work with the project's existing MVP reference scenarios |
| **Binn VS** | tiny traditional site | broad-crawl baseline; near-complete discovery should be feasible |
| **Dübendorf ZH** | structured i-web `/dienstleistungen/` catalogue | tests a reusable CMS pattern with potentially high national leverage |
| **Bosco/Gurin TI** | municipality + tourism + associations mixed together | precision/noise stress test |

These four test fundamentally different discovery problems without requiring Agent 1 to solve national normalization first.

## Why the batch changed

The previous benchmark emphasized:

- municipality size
- multilingual normalization
- cross-language identity
- portal maturity

Those remain useful later, but the new Agent 1 boundary is narrower.

For Agent 1, the highest-value early questions are:

1. Can we find services?
2. Can we avoid noise?
3. Can we group the right source pages/documents?
4. Can we recognize reusable site structures?
5. Can we hand the result to Agent 2 with provenance intact?

## Batch A cases

### Ausserberg — reference integration case

Test:

- existing MVP reference scenarios
- administrative service pages
- PDF/form discovery
- official handoff URLs
- service-source grouping

This connects the discovery pipeline directly to the team's agreed demo/MVP material.

### Binn — completeness baseline

Likely strategy:

```text
FULL_CRAWL
```

Test:

- tiny site
- low page budget
- service-vs-general-information classification
- broad coverage
- unusual local service names such as Strahlerpatente

### Dübendorf — reusable structured CMS

Likely strategy:

```text
DIRECTORY_CRAWL
→ site adapter
```

Test:

- `/dienstleistungen/` structure
- predictable service pages
- selector/rule compilation
- whether one adapter can generalize to other i-web municipalities

This matters more for scaling than proving Zürich immediately.

### Bosco/Gurin — noisy precision case

Likely strategy:

```text
FULL_CRAWL
+ aggressive service/noise classification
```

Test separation of:

- municipal administration
- tourism
- lodging
- associations
- culture/events
- local commerce

## Batch B — complexity after discovery works

Candidates:

| Municipality | Main later test |
|---|---|
| Airolo TI | custom Italian form/service portal |
| Biel/Bienne BE | multilingual source grouping |
| Zürich ZH | bounded discovery on a very large site |
| Lausanne VD | French service catalogue |
| Ilanz/Glion GR | small multilingual/decentralized administration |
| Lugano TI | richer eGovernment portal |

Batch B is where language parity, large-scale selective crawling and portal complexity become primary.

## Metrics

Agent 1 should be evaluated on:

### Service discovery precision

Of emitted Service Leads, how many are real municipal services?

### Discovery recall

Against a manually checked reference set, how many relevant services were found?

### Source-bundle quality

Does the lead include the source material Agent 2 actually needs?

### Authority precision

Are sources genuinely official/responsible?

### Crawl efficiency

```text
pages fetched
service leads emitted
useful source links retained
noise pages processed
model calls
```

### Downstream usefulness

Most important new metric:

> Can Agent 2 build a useful MCP capability from the Service Lead without having to rediscover the municipality website from scratch?

## Benchmark principle

- **Binn** tests coverage.
- **Bosco/Gurin** tests precision.
- **Dübendorf** tests repeatability/scaling.
- **Ausserberg** tests integration with the team's actual MVP story.

That is a stronger first batch for the revised architecture.
