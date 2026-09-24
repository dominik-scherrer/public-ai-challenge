# Scout Municipality Benchmark

## Goal

Use real municipalities to test the two core Scout abilities:

1. **adaptive scouting**
2. **semantic compilation of heterogeneous service handling**

The benchmark is intentionally heterogeneous.

## First implementation batch

| Municipality | Scout challenge | Primary proof |
|---|---|---|
| **Binn VS** | tiny traditional municipality | broad-small-site strategy and coverage |
| **Ausserberg VS** | product reference with forms/handoffs | factory-ready municipality JSON |
| **Dübendorf ZH** | structured i-web service catalogue | service-directory strategy and repeatability |
| **Bosco/Gurin TI** | municipality mixed with tourism/community content | mixed-content precision |
| **Zürich ZH** | very large mature city ecosystem | targeted-large-city strategy |

These five are more useful for the Scout MVP than beginning with language diversity alone.

## Why these cases

### Binn — broad small-site case

Expected strategy:

```text
broad_small_site
```

Tests:

- near-complete bounded discovery
- unusual local terminology
- possible-new service candidates
- low-cost deterministic acquisition
- whether complex planning is unnecessary

### Ausserberg — factory integration case

Expected strategy:

```text
broad_small_site or targeted administrative sections
```

Tests:

- move-in/move-out information
- forms
- contacts
- official handoffs
- local administrative pages
- whether `MunicipalityDiscovery` is sufficient for downstream MCP generation

### Dübendorf — structured catalogue case

Expected strategy:

```text
service_directory
```

Tests:

- detecting `/dienstleistungen/` structure
- enumerating service pages efficiently
- repeated templates
- reusable structural hints
- distinguishing catalogue service from transaction/handoff resources

### Bosco/Gurin — mixed-content precision case

Expected strategy:

```text
mixed_content
```

Tests separation of:

- municipal administration
- tourism
- accommodation
- associations
- events
- local commerce

Primary metric:

> false-positive municipal service rate

### Zürich — large-city selectivity case

Expected strategy:

```text
targeted_large_city
```

Tests:

- Service Index-driven targeting
- high branching factor
- department/portal boundaries
- structured APIs/live sources
- authenticated/external handoffs
- avoiding whole-site crawl

Primary metric:

> useful indexed-service coverage per request

## Later benchmark expansion

After the core Scout loop works:

| Municipality | Main later test |
|---|---|
| Biel/Bienne BE | bilingual source/service matching |
| Lausanne VD | French-language portability |
| Lugano TI | Italian eGovernment ecosystem |
| Ilanz/Glion GR | smaller multilingual/decentralized structure |
| Airolo TI | custom form/service implementation |

These matter, but they are secondary to proving adaptive strategy + semantic handling first.

## Benchmark outputs

For each municipality preserve:

- Recon result
- chosen Scout strategy
- strategy reason
- requests/pages examined
- stop reason
- indexed services checked
- service findings
- catalog suggestions
- final MunicipalityDiscovery JSON
- factory-readiness assessment

## Benchmark principle

The system should not merely return different content.

It should demonstrate different **behavior**:

```text
Binn          → broad
Dübendorf     → catalogue-driven
Bosco/Gurin   → broad + aggressive filtering
Zürich        → targeted
```

And despite those differences, all runs should compile into the same:

```text
municipality-discovery/v1
```

That is the architectural proof.
