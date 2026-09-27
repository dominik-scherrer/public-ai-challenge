# Evaluation Plan

## 1. Core metrics

### Discovery recall

Of a manually verified set of municipal services, how many did the pipeline find?

### Precision

Of extracted service candidates, how many are actually municipal public services?

Especially important for:

- Bosco/Gurin
- Binn
- mixed tourism / municipal sites

### Provenance coverage

Percentage of populated structured fields that can be traced to exact evidence.

Target:

```text
100% for hackathon demo
```

A field without evidence should be absent or explicitly marked unresolved.

### Language coverage

For multilingual municipalities:

- were all relevant language variants discovered?
- were equivalent services paired?
- were false duplicates created?

### Crawl efficiency

Track:

```text
pages fetched
pages retained
services discovered
model calls
tokens consumed
time elapsed
```

Useful derived metrics:

```text
services / 100 pages
services / model call
evidence-bearing fields / token
```

## 2. Per-municipality stress tests

### Zürich

Question:

> Can we avoid crawling the whole site while still finding a useful service set?

Primary metrics:

- pages avoided
- service yield
- directory discovery accuracy

### Biel/Bienne

Question:

> Can we recognize that German and French pages represent the same service?

Primary metrics:

- multilingual pairing precision
- duplicate rate
- language coverage parity

### Binn

Question:

> Is a broad deterministic crawl cheaper and more complete than agentic planning?

Primary metrics:

- total site pages
- service precision
- crawl completeness

### Bosco/Gurin

Question:

> Can we separate public authority information from tourism, associations and commerce?

Primary metrics:

- false-positive service rate
- source-authority classification

## 3. Trust / provenance checks

Every returned field should answer:

```text
What?
Where from?
Who published it?
When fetched?
How transformed?
What exact evidence supports it?
Official / observed / derived / inferred / dynamic?
```

## 4. Failure modes worth demonstrating

- stale source
- conflicting fee values
- missing language variant
- official page linking to external eGov portal
- service described only inside a departmental page
- PDF containing required documents
- tourism page falsely resembling a service
- service pages duplicated across languages
- target page unavailable
- unsupported municipality structure

## 5. Hackathon demo idea

Show the same pipeline on:

```text
Binn
→ FULL_CRAWL

Biel/Bienne
→ multilingual SECTION/DIRECTORY crawl

Zürich
→ DIRECTORY_CRAWL with bounded page budget
```

Then expose:

```text
service result
+
source evidence
+
crawl strategy
+
why the system stopped
```

The demo claim becomes:

> One ingestion architecture, different acquisition strategies, inspectable provenance everywhere.
