# Semantic Compiler — Large Planner, Small Apertus Executor

## 1. Goal

Use the model hierarchy efficiently:

> **large model for unfamiliar architecture and planning; small Apertus model for repetitive constrained execution; deterministic software for authority and validation.**

The model should not own the crawl state or final truth.

## 2. Three layers

### Planner

Large capable model.

Responsibilities:

- understand an unfamiliar municipality/site
- choose acquisition strategy
- set language plan and crawl budget
- identify promising roots
- propose extraction rules
- resolve ambiguous conflicts
- handle exceptions escalated from the small model

Output must be typed IR.

### Executor

Small Apertus model.

Responsibilities:

- classify page role
- service-vs-noise classification
- map text spans to allowed service fields
- rank candidate follow-up links
- perform obvious multilingual equivalence checks

The executor receives only bounded context and enumerated output choices.

### Runtime/compiler

Deterministic code.

Responsibilities:

- fetch
- parse
- validate IR
- enforce URL/domain/budget policy
- execute crawl plan
- normalize dates/currencies/URLs
- hash snapshots
- attach provenance
- detect conflicts
- decide whether confidence thresholds trigger escalation

## 3. CrawlPlan IR

Example:

```json
{
  "schema": "municipal-crawl-plan/v1",
  "target": {
    "municipality": "Zürich",
    "jurisdiction": "CH-ZH-Zurich"
  },
  "strategy": "directory_crawl",
  "roots": [
    {
      "url": "https://...",
      "role": "service_directory"
    }
  ],
  "languages": ["de"],
  "fetch_policy": {
    "prefer": "http",
    "browser_fallback": true,
    "agent_browser": false
  },
  "link_policy": {
    "allow_roles": ["service", "form", "egov", "official_pdf"],
    "deny_roles": ["news", "events", "politics", "tourism"]
  },
  "budget": {
    "max_pages": 250,
    "max_depth": 4,
    "max_targeted_followups_per_service": 3
  },
  "stop": {
    "directory_exhausted": true,
    "novelty_window": 20
  }
}
```

The runtime rejects invalid plans before crawling.

## 4. PageIR

Do not feed raw browser state to the executor when deterministic parsing can reduce it first.

Example:

```json
{
  "url": "...",
  "title": "...",
  "language": "de",
  "headings": ["..."],
  "main_text": "...",
  "links": [
    {"url": "...", "text": "...", "internal": true}
  ],
  "forms": [],
  "documents": [],
  "source_ref": "src_123"
}
```

## 5. Small-model classifier

Input: PageIR + allowed labels.

Output:

```json
{
  "page_role": "service",
  "service_probability": 0.94,
  "authority_signal": "official",
  "follow_candidates": [
    {
      "url": "...",
      "role": "official_pdf",
      "reason_code": "missing_requirements"
    }
  ]
}
```

Prefer enums/reason codes over prose.

## 6. ClaimIR

The executor must extract evidence-backed candidate claims, not final facts.

```json
{
  "claims": [
    {
      "field": "fees[0].raw",
      "value": "CHF 30",
      "source_ref": "src_123",
      "evidence_span": [182, 188],
      "semantic_classification": "official_observation"
    }
  ]
}
```

Then deterministic code derives:

```json
{
  "amount": 30,
  "currency": "CHF",
  "classification": "derived"
}
```

## 7. Confidence and escalation

The executor should not improvise outside its schema.

```text
small model result
      ↓
schema valid?
  no → retry/large model
      ↓
confidence/evidence sufficient?
  yes → continue
  no  → large model
```

Escalation reasons should be typed, for example:

- `ambiguous_service_identity`
- `conflicting_official_sources`
- `unknown_page_structure`
- `language_pair_uncertain`
- `portal_boundary_uncertain`

## 8. Compile once, replay cheaply

The planner may produce reusable site rules:

```json
{
  "adapter": "stadt-zuerich/v1",
  "service_link_selector": "...",
  "exclude_patterns": ["/news/", "/politik/"],
  "language_routes": {"de": "..."},
  "field_rules": {}
}
```

After validation, future crawls should try the adapter first.

Large-model cost should trend toward zero for stable sites.

## 9. Evaluation hypothesis

Primary architectural experiment:

> Can a large model inspect one municipality once and compile enough rules that most subsequent service discovery/extraction is handled by deterministic code plus a small Apertus model?

Measure:

- large-model calls per municipality
- small-model calls per page/service
- percentage of pages handled by HTTP vs browser
- percentage of extraction handled by compiled rules
- escalation rate
- evidence coverage
- precision/recall versus the baseline corpus

## 10. Long-term Apertus path

The architecture should work even if the small model has modest reasoning ability.

Make execution easy by:

- reducing raw HTML to PageIR
- enumerating allowed page roles
- exposing only legal next actions
- using strict schemas
- providing exact evidence spans
- normalizing deterministically
- routing hard exceptions upward

This is the semantic-compiler/JEV principle applied to web ingestion: **software defines the legal state/action space; the small model performs fuzzy classification inside it.**
