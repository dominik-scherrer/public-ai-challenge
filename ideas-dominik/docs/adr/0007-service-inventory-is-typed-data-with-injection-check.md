---
status: accepted
---

# The Service Inventory is typed data, and the Judge runs a separate injection check

Service Inventory content reaches the Citizen chat's LLM context via `get_service`. A compromised or manipulated Municipality website would pass the Judge's provenance check, because the malicious text *is* supported by its source. We therefore treat the Service Inventory as typed data, not prose: fees are amount + currency, deadlines are a number of days, required documents come from a controlled list where possible, links must point to the Municipality's own domain. Free text is short and sanitized. The Judge additionally runs an injection check that flags — never passes through — instructions to a model, foreign-domain links and payment details.

## Considered options

- **Rely on the provenance Judge alone.** Rejected: it verifies support, not intent.

## Consequences

- Part of the MMP schema is fixed by this decision (typed attribute fields, own-domain link rule).
- A Handoff can never lead to a form outside the Municipality's domain, which also rules out phishing via MMP.
- Some legitimate content (e.g. a third-party booking platform the Municipality really uses) will be withheld until an allow-list exists.
