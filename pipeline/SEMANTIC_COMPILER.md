# Semantic Compiler — Scout Step 2

## 1. Purpose

The semantic compiler is no longer a generic field-normalization stage.

It is **Scout Step 2**:

> **compress heterogeneous local service implementations into one typed MunicipalityDiscovery contract.**

Scout Step 1 finds the service and source bundle.

Scout Step 2 understands what that bundle means.

## 2. Input

For one service candidate:

```text
Service Index entry (optional)
+
ScoutFinding
+
official source bundle
+
municipality context
```

## 3. Questions the model answers

The semantic inspection agent should determine:

1. What service/capability does this represent?
2. Is it an indexed service, a variant, or possibly new?
3. Is it supported, partial, handoff-only, unavailable or merely not observed?
4. How is the service handled locally?
5. What interaction class applies?
6. Which source/resource is primary?
7. Is there a live/structured source?
8. Is an external official system involved?
9. What information is missing or inaccessible?

## 4. Handling model

Recommended handling types:

- `static_page`
- `structured_page`
- `pdf`
- `html_form`
- `external_handoff`
- `live_feed`
- `structured_api`
- `mixed`
- `unknown`

Interaction types:

- `information`
- `wayfinding`
- `request`
- `transaction`

Example:

```json
{
  "type": "mixed",
  "interaction": "information",
  "summary": "Waste guidance is published on a municipal page while collection dates are provided in a linked official PDF calendar.",
  "live": false,
  "external_system": null
}
```

The `summary` is intentionally semantic.

It lets the model express local reality without requiring one enormous universal schema.

## 5. Availability semantics

Use:

- `supported`
- `partial`
- `handoff_only`
- `unavailable`
- `not_observed`

Definitions:

### supported
Enough official material exists for the factory to build a useful capability.

### partial
The service is visible, but important implementation information is incomplete or inaccessible.

### handoff_only
The municipality exposes the service primarily by routing to another official system.

### unavailable
The source explicitly indicates that this channel/service is unavailable.

### not_observed
Scout did not find sufficient evidence.

Not-observed is not negative evidence.

## 6. Pydantic output

The semantic agent should return typed Pydantic output rather than prose plus post-parsing.

Conceptually:

```python
class Handling(BaseModel):
    type: HandlingType
    interaction: InteractionType
    summary: str
    live: bool = False
    external_system: str | None = None

class MunicipalityService(BaseModel):
    service_id: str | None
    local_name: str
    index_relation: IndexRelation
    availability: Availability
    handling: Handling
    sources: list[SourceRef]
    confidence: float
```

## 7. Why this is the AI-heavy layer

Traditional scraping can discover:

- text
- links
- forms
- PDFs
- APIs

Scout Step 2 has to infer:

- which sources collectively implement one service
- whether a portal is a handoff or the actual service
- whether a local label maps to an indexed capability
- whether a strange local service is a new capability candidate
- how to describe the local implementation meaningfully to the MCP Factory

That semantic compression is the core AI advantage.

## 8. Deterministic validation

After model output:

- validate schema
- validate source references
- validate URLs
- enforce allowed enums
- attach provenance
- detect missing primary sources
- reject impossible claims

The model does not make its own output true.

## 9. Factory relationship

Scout Step 2 should not decide the final MCP tool implementation.

It describes reality:

```text
"HTML form plus municipal information page"
```

The MCP Factory decides:

```text
"generate guidance + form-handoff adapter"
```

That separation preserves a stable inter-agent contract.
