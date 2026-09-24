# Project Build Observatory — Refresh Prompt

## Scope

Repository: `dominik-scherrer/public-ai-challenge`

### Read scope
Read the **entire repository** and Git metadata needed to understand the project:
- main README and work packages
- docs/
- ideas*/
- pipeline/
- src/
- pyproject/deployment files
- open/merged pull requests
- recent commits
- CI/status information when present

### Write scope
**Hard rule:** modify only `pipeline/observatory/`.

The observatory is a project-wide read model stored inside the pipeline workstream. Do not edit other teams' files.

## Goal

Act as an evidence-based information orchestrator for the whole hackathon build.

Explain:
- what the project is trying to build
- where each workstream stands
- what changed in Git
- what is implemented versus merely designed
- where team approaches converge or conflict
- what is blocking the critical path
- what should happen next

## Required evidence surfaces

Inspect:
1. repository tree
2. recent commits
3. open and recently merged PRs
4. README work packages
5. active architecture/MVP/build-plan docs
6. source/runtime files
7. tests/evals/fixtures/baselines
8. open-question and ADR documents

## Status vocabulary

Use only:
- `not_started`
- `designed`
- `in_progress`
- `implemented`
- `blocked`
- `deferred`

Research/document artifacts can be `implemented` as research outputs, but do not use that to imply runtime code exists.

## Project streams

At minimum assess:
- Product / MMP concept
- Municipality/service research
- Data acquisition / ingestion
- MVP implementation
- MCP runtime
- UX / reference client
- Quality / Judge / provenance
- Deployment / GTM

Add/remove streams only when repository evidence warrants it.

## Git section

Maintain:
- main HEAD SHA/message/time
- open PRs relevant to project state
- recently merged PRs
- recent meaningful commits
- CI/check status if available
- branch divergence when it matters

Git activity is evidence of change, not evidence of completion.

## Integration analysis

Explicitly flag tensions between documents/workstreams, for example:
- incompatible scope assumptions
- competing canonical schemas
- baseline-vs-target model strategy
- overlapping ownership
- decisions made in one folder but not reflected elsewhere

Do not silently reconcile disagreements. Name them and identify the decision needed.

## Files to update

- `pipeline/observatory/state.json`
- `pipeline/observatory/history.jsonl`
- embedded state in `pipeline/observatory/index.html`

Preserve history. Append only material changes.

Avoid timestamp-only commits.

Commit message when material state changes:

`chore(pipeline): refresh project observatory`


## Tool grounding matrix

Read `pipeline/grounding/tool-grounding-matrix.json` on every refresh.

Report:
- total tools
- count by maturity: dummy / grounded_1 / grounded_n / generalized / local_only / rejected
- municipalities contributing supported observations
- tools with `reshape_contract`, `local_capability`, or `reject_candidate` observations
- recent contract changes

Never promote a tool because code exists or because a README claims support. Grounding requires a real Agent Scrap observation tied to source refs.
