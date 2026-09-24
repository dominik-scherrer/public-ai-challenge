# MunicipalityDiscovery Contract

## 1. Purpose

This document defines the stable handoff from **Scout** to the **MCP Factory**.

The contract describes how one municipality exposes and handles its public services.

It is not intended to normalize every municipal fact into one national database.

Schema identifier:

```text
municipality-discovery/v1
```

## 2. Top-level artifact

Conceptual shape:

```json
{
  "schema": "municipality-discovery/v1",

  "municipality": {
    "name": "Binn",
    "canton": "VS",
    "official_url": "https://www.binn.ch/"
  },

  "build": {
    "run_id": "...",
    "scouted_at": "...",
    "service_index_version": "v1"
  },

  "strategy": {
    "mode": "broad_small_site",
    "reason": "The official site is small and broad discovery is economical."
  },

  "services": [],

  "catalog_suggestions": [],

  "coverage": {},

  "failures": []
}
```

## 3. MunicipalityService

Each indexed service receives a record, even when it is not observed.

```json
{
  "service_id": "waste_collection",
  "local_name": "Abfallentsorgung",

  "index_relation": "indexed",

  "availability": "supported",

  "handling": {
    "type": "mixed",
    "interaction": "information",
    "summary": "General guidance is published as HTML and the collection schedule is provided as an official PDF.",
    "live": false,
    "external_system": null
  },

  "sources": [
    {
      "source_id": "src_...",
      "url": "https://...",
      "role": "service_page",
      "retrieved_at": "..."
    },
    {
      "source_id": "src_...",
      "url": "https://...",
      "role": "calendar_pdf",
      "retrieved_at": "..."
    }
  ],

  "information": {
    "available": true,
    "structured": false
  },

  "confidence": 0.93,

  "limitations": []
}
```

## 4. Index relation

Allowed values:

- `indexed`
- `variant`
- `possible_new`

The Scout never silently adds services to the Service Index.

For `possible_new`, the final artifact should also include a `CatalogSuggestion`.

## 5. Availability

Allowed values:

- `supported`
- `partial`
- `handoff_only`
- `unavailable`
- `not_observed`

Absence of evidence is `not_observed`, not `unavailable`.

## 6. Handling

Handling captures the municipality-specific implementation.

### Type

- `static_page`
- `structured_page`
- `pdf`
- `html_form`
- `external_handoff`
- `live_feed`
- `structured_api`
- `mixed`
- `unknown`

### Interaction

- `information`
- `wayfinding`
- `request`
- `transaction`

### Summary

`handling.summary` is a short model-generated semantic explanation of how the municipality handles the service.

This is an intentional LLM-powered field.

It should be grounded only in the attached source bundle.

## 7. Source roles

Initial source roles:

- `municipal_service_page`
- `service_directory`
- `department_page`
- `contact_page`
- `form`
- `application_pdf`
- `information_pdf`
- `calendar_pdf`
- `regulation_pdf`
- `official_handoff`
- `live_feed`
- `structured_api`

Roles can evolve versionedly.

## 8. CatalogSuggestion

Example:

```json
{
  "local_name": "Strahlerpatente",
  "proposal": "possible_new_service",
  "reason": "A source-backed municipal permit is offered but no suitable Service Index entry exists.",
  "sources": [
    {"url": "...", "role": "municipal_service_page"}
  ],
  "confidence": 0.94
}
```

Suggestions are reviewed before Service Index changes.

## 9. Coverage

Coverage should make Scout completeness inspectable.

Example:

```json
{
  "indexed_services_checked": 32,
  "supported": 11,
  "partial": 4,
  "handoff_only": 5,
  "unavailable": 0,
  "not_observed": 12,
  "new_candidates": 1
}
```

## 10. Provenance rule

Every supported/partial/handoff service must reference official source material.

Semantic handling descriptions are model interpretations, not authority statements.

The source bundle remains the evidence underneath them.

## 11. MCP Factory contract

The MCP Factory consumes this model and should not need Scout internals.

It must not depend on:

- raw HTML
- PageIR
- Scout graph state
- crawl queues
- prompts
- model provider details

The purpose of the contract is to let Scout and MCP Factory evolve independently.
