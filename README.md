# Public AI Challenge — Team 34

We are building a **public, municipality-grounded AI service for Switzerland**.

The goal is to make fragmented municipal information easier for people and AI systems to use: discover services across very different municipal websites, preserve the source evidence, normalize the result, and expose it through a reusable public interface such as MCP.

## What we are building

```text
municipal websites / portals
        ↓
adaptive ingestion pipeline
        ↓
structured services + provenance
        ↓
public knowledge / MCP layer
        ↓
user-facing experiences and agents
```

A key design principle is to keep **AI interpretation separate from authority**. Models can help understand unfamiliar websites and extract meaning, while deterministic software owns crawling boundaries, validation, provenance, budgets and reproducibility.

## Ingestion pipeline — current prototype

The `pipeline/` workstream turns heterogeneous municipal websites into typed, provenance-preserving service records.

Current executable v0 proves:

- bounded HTTP-first crawling
- raw source snapshots with retrieval metadata and SHA-256
- a structured `PageIR`
- deterministic service-candidate detection
- optional OpenAI-compatible / Public AI model extraction
- partial canonical service records with source references and evidence
- JSONL outputs and fixture-based tests

The planned architecture extends this into an adaptive pipeline:

```text
reconnaissance
→ typed CrawlPlan
→ deterministic runtime
→ PageIR
→ constrained model extraction
→ ClaimIR
→ validation + provenance
→ canonical service records
```

The long-term hypothesis is simple: **use capable models to understand unfamiliar structures once, then compile that understanding into bounded, reusable rules that cheaper models and deterministic software can replay.**

See [pipeline/README.md](pipeline/README.md), [pipeline/ARCHITECTURE.md](pipeline/ARCHITECTURE.md) and [pipeline/BUILD_PLAN.md](pipeline/BUILD_PLAN.md).

## Pilot municipalities

We deliberately test across both cities and small villages rather than optimizing only for mature city portals:

| Pilot | Why it matters |
|---|---|
| **Binn VS** | tiny municipality; simple full-crawl baseline |
| **Biel/Bienne BE** | bilingual services and multilingual identity |
| **Zürich ZH** | large-site selective discovery under crawl budgets |
| Lausanne VD | French-language portability |
| Lugano TI | Italian services and external eGovernment flows |
| Ilanz/Glion GR | smaller, multilingual and decentralized structure |
| Bosco/Gurin TI | very small, noisy mix of municipal/tourism content |

The first vertical proof focuses on **Binn → Biel/Bienne → Zürich** before expanding to the full benchmark.

## Team workstreams

This is a collaborative build. Current work spans:

- **Data acquisition & service model** — municipal discovery, ingestion, normalization and MCP-ready data
- **User experience** — narrative, interaction and conversation flows
- **System architecture** — interfaces, components and integration
- **Quality assurance** — grounding, evaluation, scalability and lifecycle
- **Deployment & adoption** — how the service could operate and grow as public infrastructure

## Hackathon direction

The project is intentionally not “just a chatbot” and not “just a scraper”.

We want to demonstrate a reusable public infrastructure layer where municipal information remains **grounded, inspectable, multilingual and attributable to its official source**, while Public AI models such as Apertus are used where semantic interpretation adds value.
