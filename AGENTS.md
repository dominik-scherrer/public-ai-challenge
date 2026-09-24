# AGENTS.md

Guidance for any AI agent (or person) working in this repository.

## What this is

Model Municipality Protocol (MMP) — public infrastructure making Swiss municipality services reachable through chat, for the Public AI Challenge hackathon (Team 34). See `README.md` for the problem statement and work packages.

## Read this first

**`docs/architecture/`** is the accepted architecture for this project:

- `docs/architecture/CONTEXT.md` — glossary. Use these terms (Build, Judge, Service Inventory, Withheld Attribute, Build Floor, Handoff, ...) in code, docs, commits and PRs, not ad-hoc synonyms.
- `docs/architecture/adr/` — architecture decisions, all `status: accepted`. Before proposing or building anything that touches the data model, the MCP server shape, sovereignty/hosting, or quality gating, read the relevant ADR. Its README (`docs/architecture/README.md`) also tracks which ADRs are implemented, deferred, or currently at risk from work in `pipeline/` — check that table before assuming an ADR is settled in practice.
- `docs/architecture/OPEN-QUESTIONS.md` — decisions deliberately left open. Don't silently resolve one of these; flag it instead.

## Working conventions

- `ideas-patrick/hackathon-mvp-plan.md`, and the `publicai/` subproject built from it, are historical/competing input, not the source of truth — do not treat either as authoritative for architecture decisions. They may still be a useful implementation reference, but `docs/architecture/adr/` governs when they disagree.
- The municipality data already delivered under `pipeline/legacy/handoff/delivery-2026-09-24/` is kept as reference data (example Service Inventories), independent of which plan produced it.
- The repo is a monorepo of independent subprojects, each with its own `pyproject.toml` + `uv.lock` (run `uv sync` / `uv run ...` from inside the subproject, not the repo root):
  - `pipeline/scout/` — the active ingestion/discovery workstream (Scout).
  - `pipeline/judge/` — the Judge: provenance, injection/safety and coverage checks over a Build's Service Inventory (implements ADR-0004 and ADR-0007). See `pipeline/judge/README.md`.
  - `publicai/` — Patrick's "Factory" MVP; see the point above.
  - `mmp/` — the MMP MVP built against `docs/architecture/adr/`: Build (reuses Patrick's crawler, now for any host) → Judge (`pipeline/judge`, path dependency) → Service Inventory; the shared MMP server; the Reference Client. See `mmp/README.md`.
  - The root `pyproject.toml` is a separate, minimal project of its own, not a shared base for the subprojects above.
- Everything else directly under `pipeline/` (`ARCHITECTURE.md`, `BUILD_PLAN.md`, etc.) is Scout's own working notes, not the accepted architecture — that's `docs/architecture/`. `pipeline/legacy/` is superseded ingestion/prototype code kept for reference, not a base to build on.
- Each subproject should conform to `docs/architecture/adr/`; where it currently doesn't (see the status table in `docs/architecture/README.md`), that's an open gap to resolve deliberately, not a precedent to build further on.
- `pipeline/observatory/` tracks live build status, open PRs, and unresolved team tensions (competing contracts, competing Factory designs) — check it before assuming what's already decided.
