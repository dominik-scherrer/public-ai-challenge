# Why this handoff looks like this

The first question was not "how do we scrape municipalities?"

It was:

> How do we hand data to the MCP/runtime workstream so they can continue independently?

That led to one architectural decision:

> **The crawler does not hand off pages. It hands off a typed Service Inventory.**

## Why not raw HTML or PageIR?

Raw HTML, snapshots and PageIR are useful evidence, but they leak ingestion implementation details into the runtime.

If the MCP server depends on those representations, every future crawler change becomes a runtime change.

Instead:

```text
crawler-specific representations
        ↓
normalization / validation
        ↓
stable Service Inventory
        ↓
generic MCP server
```

This lets us evolve scraping and MCP independently.

## Why preserve provenance?

The project is about grounded public information.

A service record without its official source is not enough.

So each service keeps source references and the inventory carries the referenced source metadata. The MCP can therefore return the service plus the official page used to support it.

## Why explicit unknowns?

Municipal sites are incomplete and heterogeneous.

The pipeline must not turn absence into invention.

That is why records expose completeness and why partial builds are valid. A missing fee, opening hour or requirement remains unknown until supported by evidence.

## Why Ausserberg first?

Ausserberg is a good system-integration municipality because it contains several service shapes at once:

- information
- HTML forms
- municipal requests
- PDFs/forms
- external cantonal routing

It is therefore better for proving the complete product path than a municipality that is only easy to crawl.

## Why still keep the seven benchmark municipalities?

The seven benchmark places are not just demo municipalities. They are architectural tests:

- **Binn** — tiny / sparse
- **Bosco/Gurin** — noisy mixed municipal/tourism context
- **Ilanz/Glion** — smaller / multilingual / decentralized
- **Biel/Bienne** — bilingual identity
- **Lugano** — Italian / eGovernment
- **Lausanne** — French portability
- **Zürich** — large-site selective discovery

Together they test whether the ingestion approach generalizes across very different Swiss municipal realities.

## Current batch caveat

The first delivery is intentionally labelled **source-backed seed**.

It exists to unblock the MCP person now.

It should be replaced by native crawler-produced batches as the crawler matures, while preserving the same `mmp-service-inventory/v0` contract.

That replacement should require no MCP-side architecture change.


## Why capabilities, not MCP tool names?

Patrick's live MCP now exposes a broad capability-oriented tool surface: moving, forms, permits, waste, facilities, finance, reporting and municipal information.

That does not change the ingestion architecture. It clarifies it.

The Service Inventory should describe stable semantic capabilities such as `residence_registration`, `office_hours`, `forms` or `building_application`. Patrick's runtime decides whether those capabilities are exposed as one tool, several tools, or renamed tools.

This prevents a deployment detail in the MCP server from becoming part of the crawler's canonical schema.
