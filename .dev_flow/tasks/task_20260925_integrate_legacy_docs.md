# Task: Integrate Legacy and Architecture Docs into Dev-Flow Specs

> **Task ID:** `task_20260925_integrate_legacy_docs`
> **Created:** 2026-09-25 13:38
> **Last updated:** 2026-09-25 13:38
> **Status:** `done`
> **Contributors:** `antigravity`

## Current Work Item

| Field | Value |
|-------|-------|
| **Document** | n/a |
| **Pipeline phase** | `do` |
| **Traceable ID** | n/a |
| **Ticket** | n/a |

## Intent

- **Goal (why):** There are several docs in docs/architecture and docs/legacy_notes. We need to integrate their relevant content into the dev-flow specs to unify the documentation.
- **Target state:** All relevant architecture and legacy concepts are accurately represented in dev-flow formatted specs and concepts.
- **Expected result:** Missing concepts/specs are created, existing ones are updated, and legacy files are superseded or referenced correctly.

## Description

The project currently has scattered documentation in `docs/architecture` and `docs/legacy_notes`. This task is to review those files and integrate their key ideas, rules, and designs into the unified dev-flow concepts (`*.concept.md`) and specifications (`*.sp.md`).

## Subtasks

### Subtask: Initial Exploration and Planning
> Author: `antigravity` — Created: 13:38 — Last updated: 13:38 — Status: `in-progress`

**Goal:** Explore the contents of `docs/architecture` and `docs/legacy_notes` to identify what needs porting.

**Progress:**
- [x] Read docs/architecture and docs/legacy_notes.
- [x] Ported glossary definitions from CONTEXT.md to _glossary.md.
- [x] Rewrote _framework.md to align with the core architectural components (Builder, Judge, Server, Client).
- [x] Patched gemeinde_mcp.concept.md and gemeinde_mcp.sp.md to strictly follow ADR-0003 (data, not code), ADR-0004 (Judge), and ADR-0007 (JSON Service Inventory), removing legacy Python tool generation contradictions.
- [ ] **Next:** Mark task as done and surface findings to the user.

**Activity:**
- 13:37 — task created
- 13:39 — Integrated core ADR decisions into dev-flow pipeline specs (C_GMP, SP_GMP)
- 13:39 — Ported glossary and updated architectural framework

## Coordination Notes

- 13:38 [antigravity] — created task

## Blocking Issues

[No blockers yet.]

## Relevant Context

| Type | Name / Path | Note (added by) |
|------|-------------|-----------------|
| Reference | `docs/architecture/` | Target folder for integration — `antigravity` |
| Reference | `docs/legacy_notes/` | Target folder for integration — `antigravity` |

## Shared Activity Log

- 13:38 [antigravity] — created task

---

*This is a shared file. Each contributor owns their own subtask block and their own tagged entries in shared sections (Description paragraphs, Coordination Notes, Blocking Issues, Relevant Context rows, Activity Log entries). Do not refactor others' content. Coordinate via Coordination Notes. See `phases/status.md` (dev-flow skill) for the full protocol.*
