# Scout Evaluation Plan

## 1. What we evaluate

Scout should be evaluated as a two-stage agent:

```text
Step 1: did it scout the municipality intelligently?
Step 2: did it understand and compile the local service reality correctly?
```

A high-quality Scout run must do both.

## 2. Step 1 — adaptive scouting metrics

### Discovery recall

Against a manually checked reference set:

> How many real municipal services did Scout find?

### Discovery precision

Of the candidates Scout retained:

> How many are actually municipal public services?

Especially important for mixed-content municipalities.

### Strategy quality

Did the chosen strategy fit the municipality?

Evaluate:

- unnecessary pages fetched
- useful service/source yield
- missed obvious structural shortcut
- excessive broad crawling
- failure to switch strategy when reconnaissance contradicted expectations

### Crawl efficiency

Track:

```text
requests
pages fetched
pages retained
service candidates
indexed services resolved
model calls
tokens
elapsed time
```

Useful ratios:

```text
services / 100 requests
useful sources / 100 requests
indexed services resolved / model call
```

## 3. Step 2 — semantic compilation metrics

### Service Index match accuracy

For each discovered service:

- correct indexed service
- correct variant
- correct possible-new suggestion
- false match

### Handling accuracy

Does `handling` correctly capture how the municipality implements the service?

Check:

- handling type
- interaction type
- live/static status
- external-system presence
- source roles
- semantic summary

### Semantic summary usefulness

The handling summary should let the MCP Factory understand the implementation without reopening the whole website.

Test question:

> Could a downstream builder choose an implementation pattern from the municipality JSON and source bundle?

### Availability accuracy

Distinguish correctly:

- supported
- partial
- handoff_only
- unavailable
- not_observed

Especially penalize converting `not_observed` into `unavailable`.

### Catalog suggestion quality

For `possible_new` / `variant` suggestions:

- source-backed?
- genuinely outside the current index?
- useful enough to review?
- duplicate of existing concept?

## 4. Provenance

Every supported/partial/handoff service should answer:

```text
Which sources support this?
Who publishes them?
When were they retrieved?
Which source is primary?
Which statements are semantic interpretations?
```

The semantic handling summary is inferred.

The source bundle is evidence.

## 5. Benchmark municipalities

### Binn

Primary question:

> Can Scout efficiently achieve broad coverage on a tiny municipality?

Focus:

- recall
- unusual local services
- sensible `possible_new` suggestions
- low orchestration overhead

### Ausserberg

Primary question:

> Can Scout produce a municipality artifact useful to the actual product/factory scenarios?

Focus:

- forms
- official handoffs
- administrative pages
- contact/service responsibility
- factory usefulness

### Dübendorf

Primary question:

> Can Scout recognize and exploit a structured service catalogue?

Focus:

- strategy selection
- directory yield
- reusable structural hints
- request efficiency

### Bosco/Gurin

Primary question:

> Can Scout separate municipal capabilities from tourism/community noise?

Focus:

- precision
- authority classification
- false positive rate

### Zürich

Primary question:

> Can Scout resolve indexed services on a very large site without attempting a broad crawl?

Focus:

- targeted strategy
- requests avoided
- service resolution
- portal/API/handoff interpretation

## 6. End-to-end Factory readiness metric

The most important integration metric:

> Can the MCP Factory consume `MunicipalityDiscovery` without rediscovering the municipality website?

Score each service:

- `factory_ready`
- `needs_targeted_source_followup`
- `needs_rescout`
- `unusable`

This becomes the clearest measure of whether the Scout/Factory boundary works.

## 7. Failure modes worth demonstrating

- tiny site with weak information architecture
- large site where broad crawl would explode
- structured service directory
- tourism page resembling municipal content
- official external service portal
- service represented by HTML + PDF + contact page
- possible new local service
- ambiguous indexed-service mapping
- inaccessible source
- dynamic/JS-only page
- conflicting official sources
- model output failing validation
- crawl budget exhausted before coverage target

## 8. Demo claim

The strongest demo is not:

> “The crawler found pages.”

It is:

> **The same Scout agent chose different strategies for different municipalities, semantically understood their heterogeneous service implementations, and compiled them into one stable municipality contract for the MCP Factory.**
