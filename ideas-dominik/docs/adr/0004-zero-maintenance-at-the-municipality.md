---
status: accepted
---

# Zero maintenance at the Municipality; the LLM judge is the only quality gate

We cannot assume any Municipality has staff capable of maintaining, reviewing or operating anything MMP produces. Therefore every Build must be fully automated end to end, and an LLM judge is the only quality gate before a Build goes live. All maintenance sits with the MMP operator, once, for all Municipalities.

## Consequences

- Everything a Build produces must be judge-checkable attribute by attribute (supports ADR-0003).
- Freshness comes from Scheduled Builds. A Municipality *may* start a Requested Build (one action, no expertise), but nothing depends on it doing so; nobody at the Municipality is expected to notice a stale or broken Build.
- Unless a Municipality opts in to sign-off (OQ-1), the "not yet verified by the Gemeinde" label is permanent, and runtime behaviour (cite source, refuse rather than guess, `report_gap`) carries the accountability.
