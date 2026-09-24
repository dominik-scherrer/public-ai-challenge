# Semantic Compiler — From Service Lead to Local MCP Capability

## 1. Revised goal

The semantic compiler no longer needs to turn every municipal webpage into one normalized national service record.

Its strongest role is downstream:

> **Given a discovered service and its authoritative source bundle, compile a useful municipality-specific MCP capability.**

## 2. Two semantic stages

### Stage A — Discovery classifier

Cheap / constrained.

Input:

```text
PageIR + link graph + municipality context
```

Output:

```json
{
  "page_role": "service",
  "service_probability": 0.94,
  "service_type_hint": "permit",
  "related_source_candidates": [
    {"url": "...", "role": "application_pdf"}
  ]
}
```

The result becomes a Service Lead.

### Stage B — Service Compiler

More capable model.

Input:

```text
Service Lead
+ authoritative source bundle
+ municipality context
```

Output:

```text
McpCapabilityPlan
```

This is where deeper local interpretation belongs.

## 3. Capability IR

Example:

```json
{
  "schema": "mcp-capability-plan/v1",
  "service_lead_ref": "lead_binn_waste",

  "capabilities": [
    {
      "tool": "get_waste_information",
      "description": "Return official local waste guidance.",
      "inputs": [],
      "source_strategy": "document_lookup"
    },
    {
      "tool": "get_collection_calendar",
      "description": "Return collection schedule information available in the municipal sources.",
      "inputs": [],
      "source_strategy": "pdf_table"
    }
  ],

  "handoffs": [],

  "limitations": [
    "No address-specific API detected."
  ]
}
```

## 4. Why this boundary is better

Different municipalities can expose the same broad service very differently.

```text
Binn waste service
→ PDF calendar + local guidance
→ document-oriented MCP capability

Zürich waste service
→ structured/open-data endpoint
→ address-aware MCP capability
```

Trying to fully normalize both before MCP compilation can throw away useful local structure.

## 5. Common protocol, local capability

The shared contract should focus on:

- provenance
- MCP safety/runtime rules
- capability-plan schema
- source handling
- packaging/deployment
- evidence/refusal behavior

It does not require every municipality to expose identical tools internally.

## 6. Apertus path

This makes the model split cleaner.

### Small Apertus / deterministic layer

- service-vs-noise classification
- page role
- service type hint
- link/source relevance
- obvious grouping

### Larger planner/compiler

- understand source bundle
- decide local capability shape
- define tool inputs/outputs
- identify source strategies
- express limitations
- resolve difficult ambiguity

### Deterministic builder

- validate capability IR
- generate/configure runtime
- bind allowed sources
- enforce budgets/security
- test tool contract

## 7. Semantic compiler hypothesis

The architectural experiment is now:

> **Can we reduce heterogeneous municipal websites to reliable Service Leads, then use a planning model to compile each local service into a bounded MCP capability without requiring a giant universal data schema?**

That is the experiment to measure.
