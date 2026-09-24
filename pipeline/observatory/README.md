# Project Build Observatory

A project-wide, evidence-based coordination dashboard stored under `pipeline/observatory/`.

## Important scope distinction

The observatory **reads the whole repository and Git state** but **writes only inside `pipeline/observatory/`**.

This preserves ownership boundaries while giving the team one integrated view.

## It tracks

- the system as four blocks — **Discovery → Service Compiler → MCP Builder → Citizen Experience** — and the typed handoffs between them (Service Leads, capability plan, village MCP)
- **Trust · provenance · Judge** wrapping the whole chain, and **Operate** alongside it
- modules inside each block, on one maturity scale: research → designed → prototype → working → verified → demo ready
- three cross-cutting rails: Trust, AI / models, Standards
- benchmark municipalities (Batch A / B), tests, evals and acceptance checks
- Git commits, PRs and unmerged branches, owners, open decisions and conflicts between docs
- project history and next actions

## What it is not

It is not a task tracker that guesses completion from filenames.

A document can prove that something is **designed**. Only code that runs moves a module to **prototype** or beyond, and only real benchmark runs and passing checks move it past that.

## Files

- `index.html` — the dashboard, four tabs:
  - **Architecture**: *what is this system?* Four blocks with their handoffs, Trust wrapping the chain, Operate, cross-cutting rails, and a maturity meter per module. Click a block, handoff or module for the inspector.
  - **Build**: *how far have we built it?* Open PRs, next actions, decisions, conflicts, owners.
  - **Evidence**: benchmark municipalities, tests, evals and MVP acceptance checks.
  - **History**: day-grouped log with filter and search.
  Open it straight from disk; `#build`, `#evidence` and `#history` link to tabs.
- `state.json` — current machine-readable integrated state
- `history.jsonl` — material project history
- `REFRESH_PROMPT.md` — agentic repo-analysis contract

## Scheduling

The desired active-hack cadence is every 30 minutes.

ChatGPT scheduled tasks have a minimum one-hour cadence, so a true 30-minute rebuild requires an external scheduler such as GitHub Actions or another authorized runner. The refresh contract is runner-agnostic.
