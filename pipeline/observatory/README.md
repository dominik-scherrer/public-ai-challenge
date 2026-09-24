# Scout Observatory

A project-wide, evidence-based coordination dashboard stored under `pipeline/observatory/`.

## Important scope distinction

The observatory **reads the whole repository and Git state** but **writes only inside `pipeline/observatory/`**.

This preserves ownership boundaries while giving the team one integrated view.

## It tracks

- **Scout**, the agent this workstream builds: Municipality URL + Service Index → Step 1 Discover → ScoutFindings[] → Step 2 Understand / Compile → MunicipalityDiscovery JSON → MCP Factory (downstream, abstract)
- live status on every part of that diagram: planned → in progress → needs refinement → implemented
- the runtime / control layers: what AI reasoning (PydanticAI) owns vs. the deterministic Python runtime
- architectural maturity and the benchmark municipalities (Binn, Ausserberg, Dübendorf, Bosco/Gurin, Zürich)
- tests per branch, tool grounding, Scout evals and MVP acceptance
- PRs, branches, open decisions, conflicts and project history

## What it is not

It is not a task tracker that guesses completion from filenames.

A document can only make something **planned**. Code moves it to **in progress**; code that matches the Scout design and is tested makes it **implemented**. Hand-seeded data never counts as a Scout run.

## Files

- `index.html` — the Scout Observatory, four tabs:
  - **Scout**: the architecture as a living diagram — inputs, both Scout steps, the two artifacts, the Factory, runtime layers, then implementation status, maturity and benchmark cases. Click any card for its evidence.
  - **Build**: open PRs and branches, next actions, decisions, conflicts.
  - **Evidence**: tests per branch, tool grounding, Scout evals, MVP acceptance.
  - **History**: day-grouped log with filter and search.
  Open it straight from disk; `#build`, `#evidence` and `#history` link to tabs.
- `state.json` — current machine-readable integrated state
- `history.jsonl` — material project history
- `REFRESH_PROMPT.md` — agentic repo-analysis contract

## Scheduling

The desired active-hack cadence is every 30 minutes.

ChatGPT scheduled tasks have a minimum one-hour cadence, so a true 30-minute rebuild requires an external scheduler such as GitHub Actions or another authorized runner. The refresh contract is runner-agnostic.
