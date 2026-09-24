# Open questions

Decisions deliberately deferred. Each one names what is decided around it so the gap is explicit.

## OQ-1 — Municipality sign-off before publish?

**Status:** open (2026-09-24). Team preference: avoid a human sign-off gate.

**Decided around it:** Provenance check, eCH-0070 coverage check and runtime source-citation/refusal are in scope (QA layers 1, 2, 4). A Build that has not been reviewed by the Municipality is served with a visible "not yet verified by the Gemeinde" label.

**Why it stays open:** Without sign-off nobody is accountable for a wrong Auskunft, and small Municipalities may not adopt something they never approved. With sign-off, "easy for small Gemeinden" becomes ~30 min of clerk time per Build — concrete, but a gate. Needs a governance answer (who is the publisher of record?), not a technical one.

## OQ-2 — Does the public model call MMP tools reliably?

**Status:** open, risk (2026-09-24). Untested.

**Decided around it:** Reference Client = Open WebUI fork with own MCP Apps host (ADR-0006).

**Why it matters:** If the Swiss public model behind the fork does not reliably call `find_service` / `get_service`, the Reference Client — the only sovereign path (ADR-0002) — fails regardless of the UI. Test first with a dummy MMP server before building the host.

Same test covers Service selection: with no server-side semantic search, the model picks the Service from the compact `list_services` output (titles, tier, eCH-0070 synonyms); `find_service` is only a keyword fallback.
