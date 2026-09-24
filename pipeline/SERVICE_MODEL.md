# Service Lead Model

## 1. Purpose

Agent 1 does not produce a fully normalized municipal service record.

It produces a **Service Lead**: a compact, provenance-preserving handoff that tells Agent 2:

- what service appears to exist
- how the municipality names it
- where the authoritative source material is
- what kind of source each URL is
- why we think the pages belong together

## 2. Minimal contract

```json
{
  "service_lead_id": "lead_binn_strahlerpatent",

  "labels": {
    "de": "Strahlerpatente"
  },

  "service_type_hint": "permit",

  "authority": {
    "country": "CH",
    "canton": "VS",
    "municipality": "Binn",
    "department": null
  },

  "sources": [
    {
      "source_ref": "src_001",
      "role": "service_page"
    },
    {
      "source_ref": "src_002",
      "role": "application_pdf"
    }
  ],

  "discovery": {
    "confidence": 0.91,
    "method": "heuristic-v1",
    "evidence": [
      {
        "source_ref": "src_001",
        "text": "Strahlerpatente"
      }
    ]
  },

  "status": "candidate"
}
```

## 3. What is intentionally absent

Agent 1 does not need to populate:

- normalized fees
- eligibility
- required documents
- processing times
- opening hours
- canonical national service concepts
- transaction inputs
- full eCH-0070 mapping

Those belong to Agent 2 if they are useful for the local MCP capability.

## 4. Service type hint

`service_type_hint` helps routing and grouping but is not canonical truth.

Examples:

- `waste_collection`
- `residence_certificate`
- `permit`
- `facility_booking`
- `contact_hours`
- `unknown`

It may remain `unknown`.

## 5. Source roles

Useful source roles include:

- `service_page`
- `department_page`
- `form`
- `application_pdf`
- `information_pdf`
- `calendar_pdf`
- `official_portal`
- `external_handoff`
- `contact_page`

The same service lead can reference several sources.

## 6. Identity and grouping

Page identity is not service identity.

Agent 1 should group pages when evidence suggests they support one citizen capability:

```text
Abfallentsorgung
+ Abfallkalender.pdf
+ Sammelstellen
+ Gebührenblatt

→ one service lead / source bundle
```

But uncertain grouping should remain explicit rather than silently merged.

## 7. Multilingual pages

Multilingual equivalents can be grouped when obvious, but perfect cross-language normalization is no longer a first-batch requirement.

Preserve original official labels and source languages.

## 8. Downstream handoff

The Service Lead is an input to Agent 2, not the final public service object.

Agent 2 is free to compile different local MCP tools from different municipalities even when the broad service category is similar.
