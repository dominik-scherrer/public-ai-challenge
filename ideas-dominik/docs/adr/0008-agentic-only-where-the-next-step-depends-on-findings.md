---
status: proposed
---

# Agentic only where the next step depends on what was just found

**Proposal for team discussion.** We use an agent (a model deciding its own next step with tools) in exactly two places: **discovery** in the Builder and the **Citizen chat** in the Reference Client. Everything else is a single structured LLM call or deterministic code. Reason: the Judge can reliably check single calls against their sources, and a Build must be reproducible without anyone at the Municipality watching it (ADR-0004).

## The split

| Component | Step | Type |
|---|---|---|
| Builder | **Discovery** — find service pages (A–Z list, online counter, "mehr…" links, sites without sitemap) | **Agentic** |
| | Extraction — one page → typed Service | Single LLM call, structured JSON output |
| | eCH-0070 mapping | Code pre-filters candidates by keywords/synonyms → single LLM call picks ID or `unmapped` |
| Judge | Provenance per attribute | Single LLM call (attribute + source quote → supported y/n) |
| | Injection check | Code rules (own domain, IBAN pattern) → single LLM call for model-directed instructions |
| | Coverage, Build Floor, schema validation, publish | Deterministic code |
| MMP server | All tools incl. `start_service` (URL templating from typed data) | **Deterministic code, no LLM** |
| Reference Client | Citizen chat: `list_services` → choose → `get_service` → `start_service` | **Agentic** (tool-calling loop) |
| | Abstracting a Gap Report into a topic | Single LLM call, in the client, before sending |
| Operator | Processing Feedback | Targeted rebuild of affected Services — same pipeline, no extra agent |

## Considered options

- **Whole Builder as one agent** ("go build the MCP for seewil.ch"). Simplest to prototype, but two runs over the same site can differ, failures are hard to localise, and the Judge would be checking the output of a process it can't see step by step.
- **No agent at all** (deterministic crawler only). Reproducible, but breaks on the long tail of heterogeneous Gemeinde websites — which is exactly the small Municipalities we target.

## Consequences

- The discovery agent's output (list of found URLs) is logged per Build and diffed against the previous Build; a large diff trips the Build Floor.
- The MMP server contains no LLM: stateless, cheap, and nothing to prompt-inject on the server.
- The only agent running in front of Citizens on public AI is the chat → OQ-2 (tool-calling reliability) is the critical test.

## Questions for the team

1. Is discovery really the only step that needs agency, or does extraction need to follow links too (e.g. a Service spread across a page plus a PDF)?
2. Do we accept a deterministic MMP server — i.e. no LLM-generated answers server-side, all wording happens in the client?
3. Who builds the discovery agent vs. the extraction/Judge pipeline — can these be split between two people?
