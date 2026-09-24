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
- where each Scout part stands (planned / in progress / needs refinement / implemented)
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

## Scout model (`scout` in state.json)

The observatory is centred on **Scout**, the agent this workstream builds:

```text
Municipality URL + Service Index
→ Step 1 Scout / Discover   → ScoutFindings[]
→ Step 2 Understand / Compile → MunicipalityDiscovery JSON (municipality-discovery/v1)
→ MCP Factory (downstream, kept abstract)
```

Source of truth for the design: `pipeline/README.md`, `ARCHITECTURE.md`, `SERVICE_MODEL.md`, `BUILD_PLAN.md`, `EVALS.md` (currently on PR #12, `docs/scout-pipeline-architecture`, until merged).

Shape:
- `scout.inputs[]`: Municipality URL, Service Index.
- `scout.steps[]`: `{id: discover|compile, name, tagline, tone, output, cards[]}`. Cards are the diagram boxes: Recon, Choose strategy, Scouting strategy, Discover services, Source bundles / Semantic service inspection, Handling interpretation, Availability + confidence, Compile municipality contract. `tags` + `tag_kind` (`strategy`, `handling`, `availability`, `plain`) render the chips.
- `scout.artifacts[]`: `findings` (ScoutFindings[]) and `discovery` (MunicipalityDiscovery, with `keys`).
- `scout.downstream`: the MCP Factory. Keep it short; it is not tracked module by module.
- `scout.layers[]`: `ai` (PydanticAI) and `det` (Python runtime), each with `items[]`.
- `scout.foundations[]`: contracts, Service Index (`ref_item: "index"`), provenance, evals.
- `scout.maturity[]`: architectural questions answered `yes`, `partial` or `no`.
- `scout.benchmark[]`: Binn, Ausserberg, Dübendorf, Bosco/Gurin, Zürich with expected strategy, purpose and `run` (`none` until a committed Scout run exists).

Every card, artifact, input, foundation and layer item carries `status`, and where useful `where`, `summary`, `next` and `evidence: [{path, ref?}]` (`ref` = branch when not `main`).

## Status vocabulary

Use only: `planned` → `in_progress` → `needs_refinement` → `implemented`.

- `planned`: specified in docs or not at all; no code.
- `in_progress`: code exists for part of it.
- `needs_refinement`: code exists but matches an earlier design and has to change for Scout (e.g. ServiceLead → ScoutFinding), or has failing tests.
- `implemented`: code exists, is tested, and matches the Scout design. Say in `where` if it is only on an open PR.

Docs never move anything past `planned`. Hand-seeded data is not a Scout run.

## Evidence section (`evidence` in state.json)

Keep current:
- `tests`: each suite per branch with `passed` / `total`. Run them; don't infer.
- `grounding`: counts per level from `pipeline/grounding/tool-grounding-matrix.json`. Only real Scout / Agent Scrap observations move a tool out of `dummy`.
- `evals`: Scout metrics from `pipeline/EVALS.md`, grouped by `step`, `status: not_measured` until a real number exists (then add `value`).
- `acceptance`: Scout MVP acceptance from `pipeline/BUILD_PLAN.md`, status `open`, `partial` or `met`, and a one-line note.

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

List branches that have no PR yet under `git.branches`. Tag `open_prs`, `branches`, `tensions` and `history` entries with `stages: [...]` — any step id (`discover`, `compile`) or item id (card, artifact, input, foundation, `factory`) so they link to the architecture view. Open-question `area` should be a stage id when one fits.

Preserve history. Append only material changes.

Avoid timestamp-only commits.

Commit message when material state changes:

`chore(pipeline): refresh project observatory`
