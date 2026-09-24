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
- where each stage and module stands on the maturity scale
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

## System model (`system` in state.json)

The pipeline no longer normalizes services into one national dataset. Model it as four blocks joined by typed handoffs:

| Block | Question | Hands off |
|---|---|---|
| **Discovery** (Agent 1) | What services exist here, and where is the authoritative material? | `service-leads` — ServiceLead[] |
| **Service Compiler** (Agent 2) | What does this service require here, and how should an MCP expose it? | `capability-plan` — mcp-capability-plan/v1 |
| **MCP Builder** (deterministic) | Does the plan validate, and can it run safely as tools? | `village-mcp` — an MCP per municipality |
| **Citizen Experience** (host model) | Can a citizen get an official answer or the right handoff? | — |

- `system.stages[]`: `{id, name, agent, question, title, handoff, flow[], modules[]}`. `handoff` is the id of the artifact this block emits.
- `system.artifacts[]`: `{id, name, schema, from, to, maturity, summary, fields[], absent[], example, evidence[], ref?, where?}`. `absent` lists what is deliberately *not* in the handoff; keep it, it is the point of the boundary.
- `system.wrap`: **Trust · provenance · Judge**, which wraps the whole chain. Same shape as a block, without `handoff`.
- `system.operate`: rebuild, refresh, deploy, govern. Same shape.
- `system.claim`: the one-line architecture claim.

Modules: `{id, name, maturity, owner, summary, next, evidence[], ref?, where?, flag?}`.
- `evidence` lists repo paths that prove the maturity claim. `ref` is the branch those paths live on when not `main`; `where` is a human label such as `PR #7`, `docs branch` or `outside the repo`.
- `flag` is optional: `conflict`, `blocked`, `deferred` or `superseded` (built for an earlier boundary).
- Keep module ids stable so history stays readable.

Three **rails** (Trust, AI / models, Standards) have one short `cells.<block id>` sentence per block. Do not turn rails into modules.

## Maturity vocabulary

Use only, in order:

`not_started` → `research` → `designed` → `prototype` → `working` → `verified` → `demo_ready`

- `research`: findings or open decision, no agreed design.
- `designed`: a document specifies it. Docs alone can never go higher.
- `prototype`: code exists and runs in at least one case (tests or a real run).
- `working`: runs on real benchmark data through the intended path, not seed data.
- `verified`: has passing checks against acceptance criteria or evals.
- `demo_ready`: works in the actual demo setup, with the actual hosts.

Code on an open PR counts, but say so in `where`. Seed or hand-assembled data is not a crawler run.

## Evidence section (`evidence` in state.json)

Keep current:
- `municipalities`: benchmark set grouped by `batch`, with discovery `shape`, `test`, `seed_sources` and `leads` (Service Leads produced by the crawler; `null` until a run exists).
- `tests`: each suite, where it lives, count and result (`pass`, `fail`, `no_data`, `none`). Run them; don't infer.
- `evals`: metrics from `pipeline/EVALS.md`, `status: not_measured` until a real number exists (then add `value`).
- `acceptance`: checks with a `group` (e.g. Batch A discovery, End to end), status `open`, `partial` or `met`, and a one-line note.

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

### Embedded state in `index.html`

The page is static and must open from `file://`, so it carries a copy of `state.json`.
Replace only the single line `window.__BUILD_STATE__=…;` inside `<script id="build-state">` with the minified contents of `state.json`. Do not edit the layout or rendering code during a refresh.

List branches that have no PR yet under `git.branches`. Tag `open_prs`, `branches`, `tensions` and `history` entries with `stages: [...]` (block ids, `trust` or `operate`) so they link to the architecture view. Open-question `area` should be a stage id when one fits.

Preserve history. Append only material changes.

Avoid timestamp-only commits.

Commit message when material state changes:

`chore(pipeline): refresh project observatory`
