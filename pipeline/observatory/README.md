# Pipeline Build Observatory

A lightweight, static dashboard for the current state and history of the ingestion pipeline.

Open `index.html` directly in a browser.

## What it shows

- current build phase
- operational pipeline flow
- module-by-module status
- next actions
- open questions
- development history
- relevant pull requests

The dashboard deliberately distinguishes **designed** from **implemented** work.

## Files

- `index.html` — self-contained visual dashboard
- `state.json` — machine-readable current state
- `history.jsonl` — append-only material history events
- `REFRESH_PROMPT.md` — instructions for an agentic refresh job

## Refresh cadence

The intended cadence is every 30 minutes during active hacking.

ChatGPT scheduled tasks currently support at most hourly execution, so a 30-minute refresh needs an external scheduler (for example GitHub Actions or another runner) invoking an authorized model/tooling workflow.

The dashboard itself has no runtime dependency and can be rebuilt by replacing its embedded state.
