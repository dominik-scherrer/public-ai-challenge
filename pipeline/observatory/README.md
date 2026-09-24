# Project Build Observatory

A project-wide, evidence-based coordination dashboard stored under `pipeline/observatory/`.

## Important scope distinction

The observatory **reads the whole repository and Git state** but **writes only inside `pipeline/observatory/`**.

This preserves ownership boundaries while giving the team one integrated view.

## It tracks

- product/MMP concept
- municipality/service research
- data acquisition pipeline
- MVP implementation
- MCP runtime
- UX/reference client
- QA/Judge/provenance
- deployment/GTM
- Git commits and PRs
- cross-stream tensions and open decisions
- project history and next actions

## What it is not

It is not a task tracker that guesses completion from filenames.

A document can prove that something is **designed**. Only runtime/code/test evidence should move implementation modules to **implemented**.

## Files

- `index.html` — project-wide visual dashboard
- `state.json` — current machine-readable integrated state
- `history.jsonl` — material project history
- `REFRESH_PROMPT.md` — agentic repo-analysis contract

## Scheduling

The desired active-hack cadence is every 30 minutes.

ChatGPT scheduled tasks have a minimum one-hour cadence, so a true 30-minute rebuild requires an external scheduler such as GitHub Actions or another authorized runner. The refresh contract is runner-agnostic.
