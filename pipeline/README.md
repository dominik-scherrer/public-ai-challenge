# Swiss Grounding MCP — Service Discovery → Local MCP Compilation

This directory defines the pipeline that turns heterogeneous Swiss municipal websites into **service leads with authoritative source bundles**, which are then compiled downstream into a municipality-specific MCP.

The key boundary is now simpler:

> **Agent 1 discovers what services exist and where the authoritative material lives. Agent 2 understands each service deeply and builds the local MCP capability.**

Agent 1 does **not** need to normalize every fee, requirement, opening hour or procedure into one national service schema.

## System boundary

```text
municipality website
    ↓
reconnaissance
    ↓
adaptive crawl / discovery
    ↓
SERVICE LEADS
(name / hint / authority / source bundle / provenance)
    ↓
Agent 2 — Service Compiler
(inspect local sources, understand local capability)
    ↓
MCP Capability Plan
    ↓
municipality-specific MCP
    ↓
citizen / agent
```

## Agent 1 — Discovery

Agent 1 answers:

- What municipal services appear to exist?
- Which pages/documents are authoritative for each service?
- Which links belong together?
- Which municipality/department published them?
- When and how were they discovered?
- How confident are we that this is a real municipal service?

It should not try to fully understand or normalize the service.

Example output:

```json
{
  "service_lead_id": "lead_binn_waste",
  "label": "Abfall / Kehricht",
  "service_type_hint": "waste_collection",
  "municipality": "Binn",
  "sources": [
    {"url": "...", "role": "service_page"},
    {"url": "...", "role": "calendar_pdf"}
  ],
  "confidence": 0.93
}
```

## Agent 2 — Service Compiler

Agent 2 receives one service lead plus its source bundle and decides:

- what the service actually supports locally
- what information can be exposed
- what MCP tools/resources make sense
- what inputs are needed
- what limitations apply
- whether a handoff to another portal is required

The common standard is therefore primarily the **MCP/protocol boundary**, not necessarily one globally normalized municipal data model.

## Fetch principle

Use the cheapest sufficient tool:

```text
HTTP fetch
   ↓ insufficient / JS shell
headless browser
   ↓ genuine interaction required
agentic browser
```

A browser is a fallback, not the default.

## Documents

- `ARCHITECTURE.md` — Agent 1 → Agent 2 system boundary
- `CRAWL_STRATEGIES.md` — adaptive discovery strategies
- `TOOLING_AND_RUNTIME.md` — crawler/runtime options
- `SEMANTIC_COMPILER.md` — service lead → local MCP capability compilation
- `PROVENANCE_AND_TRUST.md` — source/service-lead provenance
- `MUNICIPALITY_BENCHMARK.md` — discovery-shape benchmark
- `SERVICE_MODEL.md` — minimal Service Lead contract
- `BUILD_PLAN.md` — current implementation sequence
- `EVALS.md` — discovery and downstream acceptance criteria

## Hackathon claim

> **We do not try to flatten every Swiss municipality into one giant normalized dataset. We discover each municipality's services, preserve the authoritative sources, and compile those local capabilities into an MCP tailored to that municipality.**
