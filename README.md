# Public AI Challenge - Team 34

## Problem

Switzerland has more than 2,000 municipalities, and their websites expose public services in very different ways:

- small municipality websites with a few administrative pages
- structured service catalogues
- PDFs and forms
- external cantonal or federal portals
- live feeds and APIs
- mixed municipal, tourism and community content
- different languages, terminology and information architectures

The hard problem is not merely scraping text. It is understanding **which public services exist, how each municipality handles them, and which official sources define them**.

## Solution

We build a two-stage **Municipality MCP Factory**:

```text
Municipality URL
      ↓
SCOUT
      ↓
MunicipalityDiscovery JSON
      ↓
MCP FACTORY
      ↓
Municipality-specific MCP server
```

The two agents have different responsibilities.

### Scout — adaptive discovery and semantic compilation

Scout turns an unfamiliar municipality website into one stable, typed description of that municipality.

Scout has two steps:

```text
STEP 1 — SCOUT
recon → choose strategy → discover known services → detect possible new services

STEP 2 — COMPILE
understand how each service is handled locally
→ validate provenance
→ write MunicipalityDiscovery JSON
```

Scout is agentic because the correct discovery strategy depends on the municipality.

A tiny village may justify a broad crawl. A structured i-web municipality may expose a service catalogue. A large city requires targeted discovery. A mixed municipality/tourism site requires aggressive filtering.

Scout is also semantic: the model interprets heterogeneous local implementations such as:

- static information page
- PDF calendar
- HTML form
- external official handoff
- live feed
- structured API
- mixed implementation

The output is not generated MCP code. It is a typed municipality specification.

### MCP Factory

The second agent consumes the validated municipality JSON and builds a municipality-specific MCP server inside a maintained server standard.

The factory decides how each discovered service should be exposed based on its local handling pattern.

```text
static page       → retrieval capability
PDF/document      → document or handoff capability
HTML form         → guidance + official handoff
external portal   → routing capability
live feed         → feed adapter
structured API    → API-backed tool
```

The shared runtime owns transport, schemas, safety, caching, response envelopes and conformance tests.

## Stable boundary

The contract between the two stages is:

```text
MunicipalityDiscovery
```

It contains:

- municipality identity
- Scout run/build metadata
- the version of the Service Index used
- one record per investigated service
- local service name
- availability / coverage
- semantic description of how the service is handled
- official source URLs and resource roles
- evidence and provenance
- possible new-service / variant suggestions
- coverage summary and discovery failures

The Service Index is a versioned list of services Scout actively looks for. Scout may propose additions or variants, but never silently modifies the index.

## AI architecture

We deliberately separate AI reasoning from deterministic control.

**AI / PydanticAI agents**
- understand unfamiliar site structure
- choose scouting strategy
- classify services
- interpret local service handling
- identify variants and possible new services
- compile typed semantic output

**Deterministic Python**
- networking and URL safety
- crawl budgets
- redirects and canonicalization
- caching and snapshots
- provenance
- schema validation
- stop conditions
- artifact writing

The planned orchestration model is **PydanticAI + typed graph/state orchestration**, with Pydantic models as the contracts between nodes.

## Work packages

- **Scout / Pipeline**
  - Service Index
  - adaptive reconnaissance and scouting
  - service discovery
  - semantic service inspection
  - MunicipalityDiscovery JSON
  - provenance and evaluation
- **MCP Factory**
  - consume MunicipalityDiscovery
  - generate/configure municipality service adapters
  - generate tests
  - package MCP server
  - conformance validation
- **Product / UX**
  - citizen conversation
  - service presentation
  - handoff experience
  - demo narrative
- **Quality**
  - discovery precision/recall
  - provenance
  - coverage
  - generated-server conformance
  - lifecycle and refresh
- **Deployment / Adoption**
  - package/deploy generated MCP servers
  - municipality lifecycle
  - go-to-market and governance

## Development principle

We iterate against real municipalities.

Each Scout run teaches us:

- which Service Index concepts are useful
- which services are missing from the index
- which tool abstractions are still dummy assumptions
- which MCP capabilities can be grounded in real official sources
- which capabilities should remain local rather than universal

Reality continuously improves the factory.

---

## Test the OpenAI API

Install the project dependencies:

```sh
uv sync
```

If `.env` does not exist yet, copy `.env.example` to `.env`. Set `OPENAI_API_KEY` in `.env`, then run the CLI from the repository root:

```sh
uv run python scripts/test_openai.py
```

To send a different prompt:

```sh
uv run python scripts/test_openai.py "Say hello in German."
```

