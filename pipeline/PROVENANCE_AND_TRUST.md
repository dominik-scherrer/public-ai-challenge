# Provenance and Trust

## 1. Provenance is part of the product

Every service field should be inspectable back to evidence.

The MCP should never return only:

```json
{"fee": "CHF 20"}
```

It should be able to explain:

```text
fee = CHF 20
source = official municipality page
retrieved = 2026-09-24
evidence = exact source passage
extraction = deterministic parse / inferred mapping
freshness = known / unknown
```

## 2. Provenance classifications

Use explicit classifications:

| Classification | Meaning |
|---|---|
| `official` | Directly published by the responsible public authority |
| `observed` | Directly observed in another source or registry |
| `derived` | Deterministically transformed or computed from observed data |
| `inferred` | Semantic interpretation produced by a model |
| `dynamic` | Computed at query time from current parameters |

Example:

```text
Municipal page says "Gebühr CHF 30"
→ official observation

Parser converts CHF 30 into
amount=30, currency=CHF
→ derived

Model maps paragraph to
service.fee
→ inferred mapping

MCP computes "fresh for 14 days"
→ dynamic
```

The original official observation remains available underneath all later transformations.

## 3. Do not hide trust inside one score

Avoid:

```json
{"trust_score": 0.87}
```

Prefer:

```json
{
  "trust": {
    "authority": "high",
    "directness": "primary",
    "freshness": "known",
    "evidence_coverage": 0.92,
    "extraction_confidence": 0.96,
    "conflicts": []
  }
}
```

A convenience summary may exist:

```json
{"trust_summary": "high"}
```

but it must be derived from inspectable dimensions.

## 4. Source provenance

Minimum source record:

```json
{
  "source_id": "src_...",
  "classification": "official",
  "source_type": "municipality_website",
  "publisher": {
    "name": "Stadt Zürich",
    "authority_level": "municipality"
  },
  "url": "...",
  "canonical_url": "...",
  "retrieved_at": "...",
  "source_modified_at": null,
  "content_type": "text/html",
  "language": "de",
  "sha256": "sha256:...",
  "snapshot_id": "snapshot_..."
}
```

## 5. Field-level evidence

Each extracted field should support:

```json
{
  "field": "fees[0].amount",
  "value": 30,
  "classification": "inferred",
  "source_refs": ["src_..."],
  "evidence": [
    {
      "source_ref": "src_...",
      "text": "Die Gebühr beträgt CHF 30.",
      "selector": "main article p:nth-of-type(4)"
    }
  ],
  "extractor": {
    "name": "service-extractor",
    "version": "0.1.0",
    "model": "optional-model-id"
  }
}
```

## 6. Freshness

Never equate `official` with `current`.

Track separately:

- `retrieved_at`
- `source_modified_at`, if available
- HTTP validators (`etag`, `last-modified`)
- last successful verification
- refresh policy
- stale threshold by content class

Example:

```json
{
  "freshness": {
    "retrieved_at": "2026-09-24T13:15:00Z",
    "source_modified_at": null,
    "verified_at": "2026-09-24T13:15:00Z",
    "status": "fresh",
    "policy": "refresh_30d"
  }
}
```

## 7. Crawl provenance

The acquisition process itself should be auditable.

```json
{
  "crawl_id": "crawl_...",
  "strategy": "directory_crawl",
  "strategy_reason": [
    "large site",
    "service directory discovered",
    "official eGov portal discovered"
  ],
  "page_budget": 300,
  "languages_requested": ["de"],
  "languages_discovered": ["de", "en"],
  "pages_examined": 187,
  "pages_retained": 76,
  "stop_reason": "service coverage converged"
}
```

This explains not only where claims came from, but also why the system believes it searched enough.

## 8. Snapshot discipline

A crawl should produce a manifest:

```json
{
  "crawl_id": "crawl_2026-09-24_001",
  "municipality": "Ilanz/Glion",
  "started_at": "...",
  "completed_at": "...",
  "entrypoint": "...",
  "pipeline_versions": {
    "fetcher": "0.1.0",
    "parser": "0.1.0",
    "extractor": "0.1.0"
  },
  "results": {
    "pages_fetched": 17,
    "services_detected": 32,
    "services_verified": 27,
    "services_partial": 5,
    "conflicts": 1
  }
}
```

The key distinction:

> Real data can still be stale. A frozen snapshot must identify itself as frozen.
