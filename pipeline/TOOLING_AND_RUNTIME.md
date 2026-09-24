# Tooling and Runtime — What to Reuse

## 1. Principle

Do not build browser plumbing unless the challenge needs it.

The open-source scraping and browser-agent ecosystem already converges on a useful pattern:

> **use cheap deterministic extraction where possible, escalate to a browser when necessary, and use models to discover/repair structure rather than repeatedly doing all work.**

## 2. Candidate: Crawl4AI

Strong candidate for the first implementation because it already provides:

- browser-backed crawling
- cleaned HTML / markdown representations
- structured extraction
- CSS/XPath extraction
- model-assisted extraction
- session handling
- adaptive crawling patterns

Most relevant pattern:

```text
model inspects unfamiliar page
        ↓
compile extraction schema/selectors
        ↓
reuse deterministic extraction
```

This maps directly to the semantic-compiler architecture.

### Use in this project

Potential role:

- initial runtime/prototype
- browser fallback
- DOM cleaning
- structured extraction
- proof that compiled selectors can replace repeated LLM work

Do not make the project architecture depend on one library. Keep internal IR and provenance schemas library-neutral.

## 3. Candidate: Crawlee + Playwright

Crawlee is useful if we want a lower-level crawler runtime with explicit separation between lightweight HTTP/HTML crawling and Playwright browser crawling.

Potential role:

- crawl queue
- concurrency/rate controls
- request deduplication
- browser escalation
- production-ish crawl runtime

Playwright should be treated as the rendering/interaction engine, not as the orchestration architecture.

## 4. Candidate: Stagehand

Stagehand is useful as an architectural reference for hybrid deterministic/AI browser automation.

Interesting ideas to borrow:

- observe before act
- typed extraction
- use AI only where page structure is uncertain
- convert successful model-driven behavior into repeatable operations
- separate planning/trajectory from execution

Potential role:

- interactive eGov edge cases
- reference implementation for model→browser action boundaries

Not the default crawler.

## 5. Candidate: Browser Use

Useful as a reference for full browser-agent loops and typed action schemas.

Potential role:

- study action/observation schemas
- complex portal interaction experiments

Not recommended as the default ingestion engine because most municipal pages do not justify a fully autonomous browser agent.

## 6. Recommended first stack

For the hackathon:

```text
HTTP client
  + HTML parser
  + cache/snapshot layer
  + Crawl4AI or Playwright fallback
  + JSON Schema / Pydantic-like typed IR
  + Apertus-compatible model adapter
```

The architecture must keep these replaceable.

## 7. Anti-blocking / crawler etiquette

This project should not optimize for stealth.

Instead:

- fetch only public information needed for the service corpus
- identify the crawler reasonably
- use conservative request rates
- cache every successful fetch
- avoid repeated requests for unchanged pages
- use sitemaps/service directories
- limit depth and page budgets
- back off on errors
- record failed/blocked access as evidence, not as a prompt to bypass controls

This is both operationally safer and aligned with the project goal: efficient public-information acquisition.

## 8. Runtime interfaces

Keep the core independent from tooling through narrow interfaces:

```text
Fetcher.fetch(url, mode) -> SourceSnapshot
Cleaner.clean(snapshot) -> PageIR
Planner.plan(Context, Recon) -> CrawlPlan
Classifier.classify(PageIR) -> PageClassification
Extractor.extract(PageIR, ServiceSchema) -> ClaimIR
Validator.validate(ClaimIR) -> ValidatedClaims
```

A future runtime can swap Crawl4AI, Crawlee, Playwright or another implementation without changing the service/provenance model.
