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

We build a two-stage **MMP Pipeline (Builder + Server)**:

```text
Municipality URL
      ↓
SCOUT
      ↓
MunicipalityDiscovery JSON
      ↓
BUILDER & JUDGE
      ↓
Service Inventory JSON -> Shared MMP Server
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

The builder determines how to expose each service declaratively (ADR-0003: Data, not code).

```text
static page       → retrieval capability
PDF/document      → document or handoff capability
HTML form         → guidance + official handoff
external portal   → routing capability
live feed         → feed adapter
structured API    → API-backed tool
```

The shared runtime owns transport, schemas, safety, caching, response envelopes and conformance tests.

## Run the Live Pipeline Demo

The live pipeline demo loads scouted municipal services, fetches official web pages live, runs data extraction, and serves the results over a FastMCP server.

1. Ensure dependencies are installed:
   `sh
   uv sync
   `

2. Add your OpenAI API key in .env:
   `sh
   echo "OPENAI_API_KEY=your_key_here" >> .env
   `

3. Run the live demo:
   `sh
   uv run python demo/demo.py
   `
