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

- `ideas-patrick/hackathon-mvp-plan.md` is historical input, not the source of truth — do not treat it as authoritative for architecture decisions.
- The municipality data already delivered under `pipeline/handoff/delivery-2026-09-24/` is kept as reference data (example Service Inventories), independent of which plan produced it.
- `pipeline/` is the active ingestion/implementation workstream (Scout). It should conform to `docs/architecture/adr/`; where it currently doesn't (see the status table in `docs/architecture/README.md`), that's an open gap to resolve deliberately, not a precedent to build further on.
- `pipeline/observatory/` tracks live build status, open PRs, and unresolved team tensions (competing contracts, competing Factory designs) — check it before assuming what's already decided.
