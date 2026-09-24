# Tool Grounding Loop

The current MCP tool surface is treated as a set of **capability hypotheses**.

Agent Scrap does not try to prove the entire tool catalogue in advance. Each real municipality crawl contributes evidence that either grounds, reshapes, localizes, or eventually rejects a tool abstraction.

## Loop

```text
real municipality
→ Agent Scrap
→ Service Leads + authoritative source bundles
→ tool observations
→ update grounding matrix
→ inspect gaps / wrong abstractions
→ improve MCP tool contracts
→ next municipality
```

## Maturity

| State | Meaning |
|---|---|
| `dummy` | tool exists, but no real municipality has grounded it |
| `grounded_1` | supported by one municipality |
| `grounded_n` | supported by multiple municipalities |
| `generalized` | deliberately stabilized after repeated grounding |
| `local_only` | valid local capability that should not become universal |
| `rejected` | reality showed the abstraction is wrong/unhelpful |

Only `grounded_1` and `grounded_n` are advanced automatically. `generalized`, `local_only`, and `rejected` are explicit design decisions.

## Files

- `tool-grounding-matrix.json` — source of truth for current maturity
- `agent-scrap-observation.schema.json` — handoff event contract
- `example-observations.json` — example Agent Scrap output
- `apply_observations.py` — dependency-free matrix updater
- `tests/test_apply_observations.py` — grounding-loop tests

## Agent Scrap observation

Agent Scrap emits observations after each real crawl.

```json
{
  "municipality": "Binn",
  "service_lead_id": "lead_binn_waste",
  "tool_id": "garbage_collection",
  "result": "supported",
  "source_refs": ["src_012", "src_018"],
  "notes": "Municipal waste guidance and calendar found."
}
```

Possible results:

- `supported` — real source bundle supports the current tool hypothesis
- `not_observed` — no supporting service was found; this is **not** evidence that the municipality lacks it
- `reshape_contract` — service exists but current tool shape does not fit reality
- `local_capability` — real service exists but appears municipality-specific
- `reject_candidate` — evidence suggests the current abstraction is misleading or redundant

## Important rule

Absence is not automatically negative evidence.

A bounded crawl that does not discover a service should normally emit `not_observed`, not `reject_candidate`.

## Observatory

The project observatory should read `tool-grounding-matrix.json` and show:

- dummy vs grounded tools
- municipalities contributing evidence
- contract changes
- local-only/rejected decisions
- grounding progress over time

The refresh agent should never infer grounding from a README or dummy implementation alone.
