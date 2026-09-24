# Canonical Service Model

## 1. Purpose

Create one typed representation that can absorb heterogeneous municipal service pages without losing source terminology or provenance.

## 2. Example service record

```json
{
  "service_id": "ch.zh.zurich.residence.registration",
  "concept": "residence_registration",

  "labels": {
    "de": "Wohnsitz anmelden"
  },

  "description": "...",

  "provider": {
    "name": "Stadt Zürich",
    "authority_level": "municipality"
  },

  "jurisdiction": {
    "country": "CH",
    "canton": "ZH",
    "municipality": "Zürich"
  },

  "eligibility": [],
  "requirements": [],
  "documents": [],

  "fees": [
    {
      "amount": null,
      "currency": "CHF",
      "description": null
    }
  ],

  "processing_time": null,

  "channels": {
    "online": false,
    "in_person": true,
    "postal": false
  },

  "actions": [
    {
      "type": "online_transaction",
      "url": null
    }
  ],

  "contacts": [],

  "source_refs": [],
  "field_provenance": {}
}
```

## 3. Preserve original wording

Normalization should not destroy source terminology.

Keep:

```json
{
  "concept": "residence_certificate",
  "labels": {
    "de": "Wohnsitzbestätigung",
    "fr": "Attestation de domicile",
    "it": "Certificato di domicilio"
  }
}
```

The canonical concept is machine-facing.

Labels are source-facing.

## 4. Observation before claim

Raw extraction:

```json
{
  "observation_id": "obs_...",
  "source_ref": "src_...",
  "text": "Die Gebühr beträgt CHF 30.",
  "selector": "...",
  "language": "de"
}
```

Typed claim:

```json
{
  "field": "fees[0].amount",
  "value": 30,
  "classification": "inferred",
  "observation_refs": ["obs_..."]
}
```

## 5. Conflict representation

Do not silently select one value.

```json
{
  "field": "fees[0].amount",
  "status": "conflict",
  "candidates": [
    {
      "value": 20,
      "source_ref": "src_a"
    },
    {
      "value": 30,
      "source_ref": "src_b"
    }
  ]
}
```

A resolver may later choose based on:

- authority
- date
- page role
- jurisdiction
- explicit supersession

The conflict itself should remain inspectable.

## 6. Service identity

Service identity is not page identity.

One canonical service may have:

- multiple languages
- multiple official pages
- a PDF
- an online transaction endpoint
- a responsible office page
- a cantonal reference

All belong to one service entity when evidence supports that conclusion.
