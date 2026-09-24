---
status: accepted
---

# eCH-0070 is the canonical Service model; the shared MCP schema is the protocol

MMP is pitched as public infrastructure, which is only credible as a *standard*, not as a scraper. We therefore separate two things: the **builder** (an LLM agent that scrapes a Municipality website, extracts its Services, runs QA and can host the resulting MCP server) is the product we demo; the **shared schema** that every generated server conforms to is the protocol we claim. Without a shared schema each generated server is a snowflake and "protocol" is just a pun on MCP.

For that schema, every extracted Service is mapped to a Leistungs-ID from eCH-0070 (*Inventar der Leistungen der öffentlichen Verwaltung der Schweiz*, V4.2.0) where a match exists, with an explicit `unmapped` bucket for the rest. eCH-0070 is flat, numbered, bilingual (DE/FR), carries synonyms/descriptors (useful for LLM matching), a `Vollzug durch` attribute (lets us filter to Gemeinde-level Leistungen) and an electronic-availability flag, and is maintained by the eCH standards body.

## Considered options

- **Free-form, LLM-derived taxonomy per site.** Faster to build, no mapping step — but no comparability across Municipalities, no coverage measurement, and a governance story ("who owns the taxonomy?") we'd have to invent. Rejected.
- **Invent our own MMP taxonomy.** Same governance problem, plus it competes with an existing Swiss standard. Rejected.

## Consequences

- The pitch line becomes "eCH-0070 over MCP": an existing Swiss standard gets an AI-native interface.
- QA gets an objective target: coverage of the Gemeinde-level Leistungen. The coverage report is a second deliverable for the Municipality at near-zero cost.
- The mapping step is a real engineering task (fuzzy/semantic match against ~17 attributes incl. synonyms); it needs its own quality gate.
- The builder must never *invent* a Service to fill a gap in the inventory — missing is a finding, not a bug.
