# Architecture — Discover Services, Compile Local MCP Capabilities

## 1. Goal

Given an official municipality URL, identify the services the municipality exposes and produce provenance-preserving **Service Leads** that a downstream Service Compiler can turn into a municipality-specific MCP.

Agent 1 does not need to fully normalize the service domain.

## 2. Revised architecture

```text
MUNICIPALITY WEBSITE
        │
        ▼
┌─────────────────────────────┐
│ AGENT 1 — DISCOVERY         │
│                             │
│ recon / crawl / classify    │
│ identify service surfaces   │
│ group authoritative sources │
└──────────────┬──────────────┘
               │
               │ ServiceLead[]
               ▼
┌─────────────────────────────┐
│ AGENT 2 — SERVICE COMPILER  │
│                             │
│ inspect local source bundle │
│ understand local semantics  │
│ choose useful capabilities  │
└──────────────┬──────────────┘
               │
               │ McpCapabilityPlan
               ▼
┌─────────────────────────────┐
│ MCP BUILDER / RUNTIME       │
│                             │
│ tools / retrieval / handoff │
│ validation / packaging      │
└──────────────┬──────────────┘
               │
               ▼
        CITIZEN / AGENT
```

Trust/provenance spans the whole chain.

## 3. Agent 1 contract

Agent 1 should determine:

```text
service identity / label
+ municipality / authority
+ source URLs
+ source roles
+ discovery evidence
+ language
+ confidence
+ crawl provenance
```

It should **not** be responsible for extracting and normalizing every service attribute.

For example, for waste collection:

```json
{
  "service_lead_id": "lead_binn_waste",
  "label": "Abfallentsorgung",
  "service_type_hint": "waste_collection",
  "authority": {
    "municipality": "Binn",
    "canton": "VS"
  },
  "sources": [
    {"source_ref": "src_12", "role": "service_page"},
    {"source_ref": "src_18", "role": "calendar_pdf"}
  ],
  "confidence": 0.93
}
```

No normalized collection days, zones or fees are required at this stage.

## 4. Source bundles

A service is often spread across several sources:

```text
service landing page
+ PDF/form
+ department page
+ external official portal handoff
```

Agent 1's main semantic task is to group those sources into one plausible service lead.

This is more important than field extraction.

## 5. Agent 2 contract

Agent 2 receives:

```text
municipality context
+ service lead
+ authoritative source bundle
```

and emits a typed capability plan, for example:

```json
{
  "schema": "mcp-capability-plan/v1",
  "service": {
    "label": "Abfallentsorgung",
    "municipality": "Binn"
  },
  "capabilities": [
    {
      "tool": "get_waste_information",
      "inputs": [],
      "source_strategy": "document_lookup"
    },
    {
      "tool": "get_collection_calendar",
      "inputs": [],
      "source_strategy": "pdf_table"
    }
  ],
  "limitations": [
    "No address-specific collection API detected."
  ]
}
```

The downstream compiler may choose different MCP surfaces for the same broad service in different municipalities.

## 6. Important architectural consequence

The common abstraction is deliberately small:

```text
Service Lead
→ local understanding
→ MCP capability
```

We do **not** require:

```text
all municipalities
→ identical fully normalized service schema
```

Cross-municipality normalization (including eCH-0070) may still be useful for indexing, discovery and analytics, but is not required to produce the first useful MCP.

## 7. Discovery runtime

Agent 1 still uses adaptive acquisition:

```text
cheap reconnaissance
→ choose FULL / SECTION / DIRECTORY / DISCOVERY
→ HTTP first
→ browser only when needed
→ classify service vs noise
→ attach related source links
→ stop
```

## 8. Model roles

### Deterministic software

- URL normalization
- redirect/canonical deduplication
- fetch/cache/snapshot
- crawl budgets
- domain policy
- provenance
- link graph
- output validation

### Small model / heuristic layer

- service-vs-noise classification
- page role
- service-type hints
- source relevance
- source grouping suggestions

### Large model

Use only where needed:

- unfamiliar site architecture
- ambiguous service grouping
- difficult portal/source relationships
- compiling the downstream MCP capability plan

## 9. Core claim

> **The scraper discovers capabilities and their evidence. The Service Compiler understands them. The MCP is where local municipal semantics become a usable machine interface.**
