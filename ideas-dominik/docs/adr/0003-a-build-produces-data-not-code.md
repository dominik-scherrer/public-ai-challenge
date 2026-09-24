---
status: accepted
---

# A Build produces data, not code; one generic MMP server serves all Municipalities

A Build outputs a Service inventory (JSON validated against the MMP schema). A single generic, multi-tenant MMP server serves every Municipality, addressed by BFS-Gemeindenummer (`mmp://<bfs>/…`). The LLM never writes code that runs on public infrastructure.

## Considered options

- **Generated MCP server code per Municipality** (team's initial preference). Rejected: ~2,100 codebases nobody maintains (see ADR-0004), LLM-generated code on public infrastructure cannot be proven safe by an answer-level judge (prompt injection from scraped pages could reach code), protocol conformance drifts, and every security/protocol fix means regenerating all servers.
- **Data plus a sandboxed generated Handoff adapter.** Rejected for now: still per-Municipality code without anyone to maintain it.

## Consequences

- Protocol conformance is structural: every Municipality runs the same server.
- A rerun swaps data; rollback is reverting to the previous Build. A bad Service is dropped, not a crashing server.
- The LLM judge can check every attribute against its source quote rather than sampling program behaviour.
- CMS vendors can publish MMP-conformant JSON directly and skip the builder.
- Pitch wording stays "the builder turns a website into a working MCP server in minutes" — by configuring the shared server, not by writing one.
