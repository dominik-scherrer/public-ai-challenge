# Architecture — Scout Agent

## 1. Goal

Scout turns an official municipality website into a typed, provenance-preserving **MunicipalityDiscovery** artifact for the MCP Factory.

Input:

```text
official municipality URL
+
versioned Service Index
```

Output:

```text
MunicipalityDiscovery
```

The difficult part is not extracting every field from every page. It is understanding:

- which indexed services are present
- which services are not observed
- which additional or variant services exist
- how the municipality locally handles each service
- which official resources define that service

## 2. Two-step Scout

```text
                        SERVICE INDEX
                              │
                              ▼
MUNICIPALITY URL ──→ RECON / STRATEGY
                              │
                              ▼
                    SCOUT STEP 1
                    adaptive discovery
                              │
                       ScoutFindings[]
                              │
                              ▼
                    SCOUT STEP 2
                    semantic compilation
                              │
                              ▼
                   MunicipalityDiscovery
                              │
                              ▼
                         MCP FACTORY
```

## 3. Recon and strategy

Before crawling deeply, Scout inspects enough of the municipality to choose a strategy.

Signals include:

- estimated site size
- navigation branching
- service directory presence
- sitemap availability
- CMS patterns
- language structure
- amount of municipal vs non-municipal content
- eGovernment portal links
- static vs rendered content
- structured feeds/APIs

Typed strategy example:

```json
{
  "mode": "service_directory",
  "reason": "A structured /dienstleistungen/ catalogue was detected.",
  "roots": ["https://.../dienstleistungen/"],
  "max_pages": 120,
  "max_depth": 3,
  "target_services": ["..."],
  "allow_external_handoffs": true
}
```

Allowed strategy families:

- `broad_small_site`
- `service_directory`
- `targeted_large_city`
- `mixed_content`
- `custom`

The agent chooses; deterministic runtime validates and executes.

## 4. Step 1 — adaptive service discovery

Scout searches for all services from the Service Index.

For each candidate it records:

- local label
- candidate indexed service
- confidence
- official source URLs
- resource roles
- discovery evidence

Scout also records:

- `possible_new`
- `possible_variant`

It never silently changes the Service Index.

Example finding:

```json
{
  "local_name": "Strahlerpatente",
  "service_id": null,
  "index_relation": "possible_new",
  "confidence": 0.94,
  "sources": [
    {"url": "...", "role": "service_page"},
    {"url": "...", "role": "application_pdf"}
  ]
}
```

## 5. Step 2 — semantic municipality compilation

Step 2 takes the findings and understands how each service is handled locally.

The model answers questions such as:

- Is this information-only, wayfinding, request or transaction?
- Is the implementation a static page, PDF, form, handoff, feed, API or mixed?
- Which source is primary?
- Which supporting resources belong to the service?
- Does the municipality expose enough information to call this supported?
- What is missing or inaccessible?

This produces one typed service record.

Example:

```json
{
  "service_id": "move_in",
  "local_name": "Zuzug",
  "index_relation": "indexed",
  "availability": "handoff_only",
  "handling": {
    "type": "external_handoff",
    "interaction": "transaction",
    "summary": "The municipality explains the move-in process locally and routes the citizen to the official external registration service.",
    "live": false,
    "external_system": "eUmzugCH"
  },
  "sources": [
    {"url": "...", "role": "municipal_service_page"},
    {"url": "...", "role": "official_handoff"}
  ]
}
```

## 6. MunicipalityDiscovery boundary

The final artifact includes:

```text
municipality
build
strategy
services[]
catalog_suggestions[]
coverage
failures[]
sources[]
```

This is the only artifact the MCP Factory needs.

Raw HTML, PageIR, crawl queues and browser state remain Scout internals.

## 7. AI vs deterministic runtime

### PydanticAI reasoning

Use model intelligence for:

- reconnaissance interpretation
- strategy choice
- service classification
- source relevance
- service/index matching
- semantic interpretation of local handling
- possible new/variant service detection
- concise handling summary

### Deterministic Python

Software owns:

- URL validation
- private-network protection
- redirect handling
- crawl queue
- request budgets
- canonicalization/deduplication
- caching/snapshots
- timestamps/hashes
- provenance
- schema validation
- stop conditions
- artifact serialization

The model may propose. Software decides what is executable.

## 8. Graph orchestration

Conceptual Scout graph:

```text
ReconNode
    ↓
StrategyNode
    ↓
ScoutNode
    ↓
CoverageCheck
   ↙        ↘
follow-up   enough
   ↓         ↓
ScoutNode  InspectServices
               ↓
          CompileDiscovery
               ↓
             Validate
```

The graph state is typed.

It should be possible to inspect:

- current strategy
- URLs visited
- budget remaining
- indexed services found
- indexed services still unresolved
- candidate new services
- follow-up reasons
- stop reason

## 9. Source discipline

Always preserve source snapshots or source metadata before semantic interpretation.

```text
source
 ↓
observation
 ↓
semantic interpretation
 ↓
MunicipalityService
```

Official does not mean current, and not-observed does not mean unavailable.

## 10. Relationship to MCP Factory

Scout describes local reality.

The MCP Factory converts that description into a municipality-specific implementation inside a fixed runtime standard.

```text
Scout:       "how does this municipality handle the service?"
Factory:     "how should that become an MCP capability?"
```

Those responsibilities must remain separate.
