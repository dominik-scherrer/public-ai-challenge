# Municipality Benchmark

## Goal

Use a deliberately heterogeneous municipality set to test whether the ingestion system adapts to different Swiss realities.

The benchmark should stress:

- municipality scale
- site scale
- language
- multilingual equivalence
- administrative complexity
- eGovernment maturity
- sparse service representation
- mixed-content websites
- rural / merged municipalities

## Initial benchmark set

| Municipality | Character | Main test |
|---|---|---|
| Zürich ZH | very large city | large-site precision and selective discovery |
| Lausanne VD | large city | French extraction and ontology portability |
| Lugano TI | medium city | Italian + external/dedicated eGov transactions |
| Biel/Bienne BE | bilingual city | multilingual service equivalence |
| Ilanz/Glion GR | small regional municipality | multilingual + merged/decentralized structure |
| Binn VS | tiny alpine municipality | sparse traditional municipal website |
| Bosco/Gurin TI | very tiny mountain municipality | municipal / tourism / association content separation |

## Why seven instead of five?

Five large or well-known cities would bias the system toward mature portals.

The additional tiny municipalities test the opposite failure mode:

> Can the system recognize municipal services when there is no clean service catalogue at all?

## Expected strategy by municipality

### Zürich

Likely:

```text
DISCOVERY_CRAWL
→ DIRECTORY_CRAWL
```

Do not crawl the entire city website.

Test:

- directory discovery
- eGov endpoints
- page-budget discipline
- high branching factor
- deduplication

### Lausanne

Likely:

```text
DISCOVERY_CRAWL
→ DIRECTORY or SECTION
```

Test:

- French-language service extraction
- ontology independence from German terms

### Lugano

Likely:

```text
DISCOVERY_CRAWL
→ DIRECTORY_CRAWL
→ external official eGov portal
```

Test:

- Italian-language extraction
- distinction between informational page and executable service endpoint

### Biel/Bienne

Likely:

```text
SECTION / DIRECTORY
+ multilingual pairing
```

Test:

- DE/FR service equivalence
- duplicate prevention
- language coverage parity

### Ilanz/Glion

Likely:

```text
SECTION_CRAWL
```

Test:

- smaller administration
- services embedded in departmental pages
- German / Romansh variation
- merged municipality structure

### Binn

Likely:

```text
FULL_CRAWL
```

Test:

- tiny site
- low service density
- traditional CMS
- whether broad crawling is cheaper than complex planning

### Bosco/Gurin

Likely:

```text
FULL_CRAWL
+ aggressive classification
```

Test:

- distinguish municipal services from:
  - tourism
  - accommodation
  - associations
  - commercial activity
  - events
- very small administration
- unusual language context

## Benchmark principle

Zürich primarily tests **recall under bounded crawling**.

Bosco/Gurin primarily tests **precision under noisy crawling**.

Together, they help test whether adaptive orchestration is actually useful.
