# Provenance and Trust

## 1. Provenance remains a first-class requirement

The architectural boundary changed, but provenance did not become less important.

Agent 1 now needs to prove:

> **Why do we believe this service exists, and which authoritative sources should Agent 2 inspect?**

It no longer needs field-level provenance for every normalized service attribute.

## 2. Source provenance

Every source keeps:

```json
{
  "source_id": "src_...",
  "classification": "official",
  "source_type": "municipality_website",
  "publisher": {
    "name": "Gemeinde Binn",
    "authority_level": "municipality"
  },
  "url": "...",
  "canonical_url": "...",
  "retrieved_at": "...",
  "source_modified_at": null,
  "content_type": "text/html",
  "language": "de",
  "sha256": "sha256:..."
}
```

## 3. Service-lead provenance

A Service Lead should expose:

```json
{
  "service_lead_id": "lead_...",
  "labels": {"de": "Strahlerpatente"},
  "sources": [
    {"source_ref": "src_1", "role": "service_page"},
    {"source_ref": "src_2", "role": "application_pdf"}
  ],
  "discovery": {
    "confidence": 0.91,
    "method": "heuristic-v1",
    "evidence": [
      {
        "source_ref": "src_1",
        "text": "Strahlerpatente"
      }
    ]
  }
}
```

The important audit questions are:

- Where was the service discovered?
- Is the publisher authoritative?
- Which source bundle was handed to Agent 2?
- When was it fetched?
- Was the grouping inferred?
- Were any relevant pages inaccessible?

## 4. Classification vocabulary

| Classification | Meaning |
|---|---|
| `official` | Published directly by the responsible authority |
| `observed` | Directly observed in another source |
| `derived` | Deterministically produced from source data |
| `inferred` | Semantic judgement by a model/heuristic |
| `dynamic` | Computed at request/runtime |

Example:

```text
"Strahlerpatente" appears on municipality page
→ official observation

page classified as a municipal service
→ inferred

PDF link grouped with that service lead
→ inferred or derived depending on rule

Agent 2 later interprets fee/process details
→ downstream responsibility
```

## 5. Trust dimensions

Avoid one opaque score.

For discovery, keep dimensions such as:

```json
{
  "trust": {
    "authority": "high",
    "source_directness": "primary",
    "freshness": "unknown",
    "service_identity_confidence": 0.91,
    "source_bundle_confidence": 0.83
  }
}
```

## 6. Crawl provenance

Record how discovery happened:

```json
{
  "crawl_id": "crawl_...",
  "strategy": "full_crawl",
  "page_budget": 50,
  "pages_examined": 31,
  "service_leads_found": 12,
  "stop_reason": "queue_exhausted"
}
```

This lets Agent 2 and later evaluators distinguish a service lead found in a nearly complete tiny-site crawl from one found in a heavily bounded large-site crawl.

## 7. Freshness

Official does not mean current.

Keep:

- retrieval timestamp
- last-modified/etag when available
- content hash
- crawl/build ID
- inaccessible/failed source records

Freshness interpretation can happen downstream.

## 8. Responsibility boundary

Agent 1 provenance answers:

> **What did we discover and where?**

Agent 2 / Judge provenance answers:

> **What factual claims did we derive from those sources and should they be exposed?**

Do not mix the two stages.
