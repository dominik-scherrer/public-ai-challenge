# Task: Reorganize Pipeline Phases and Systematize Project Documentation

> **Task ID:** `task_20260925_reorganize_phases`
> **Created:** 2026-09-25 10:40
> **Last updated:** 2026-09-25 10:40
> **Status:** `review-pending`
> **Contributors:** `antigravity`

## Current Work Item

| Field | Value |
|-------|-------|
| **Document** | `plan` — Implementation Plan: Monorepo Consolidation & Phased Structure |
| **Pipeline phase** | `plan` |
| **Traceable ID** | `PL_REORG` |
| **Ticket** | n/a |

## Intent

- **Goal (why):** Prepare the project for final jury presentation by separating demo/test artifacts, consolidating scattered documentation into `docs/legacy_notes/`, and organizing the independent subprojects (Scout, Gemeinde MCP, Judge, PublicAI) into explicit phased directories under `src/public_ai_challenge/` side by side.
- **Target state:** 
  1. `docs/` contains official `architecture/`, preserved dev-flow documents, and a dedicated `legacy_notes/pipeline_working_notes/` folder.
  2. `src/public_ai_challenge/` holds `phase1_scout_pipeline`, `phase2_synthesis_gemeinde`, `phase3_judge_pipeline`, and `alternative_pipeline_publicai`.
  3. `tests/` structured matching each phase.
  4. `demo/` completely separated from production source code with working `demo.py`.
  5. Retired subprojects and scripts moved cleanly to `archive/`.
- **Expected result:** All unit tests pass, demo runs cleanly with zero regressions, and folder hierarchy reflects clear phases.

## Description

Refactoring codebase layout following dev-flow Refactoring Protocol: consolidating subprojects into phased packages under `src/public_ai_challenge`, relocating working notes to `docs/legacy_notes/`, and isolating demo artifacts in `demo/`. — `antigravity`

## Subtasks

### Subtask: Execute Project Layout Refactoring
> Author: `antigravity` — Created: 10:40 — Last updated: 10:40 — Status: `in-progress`

**Goal:** Execute doc archiving, source code relocation by phases, test partitioning, demo isolation, dependency merging, and verification.

**Progress:**
- [x] Initialized task context
- [x] Step 0: Move pipeline working notes to `docs/legacy_notes/pipeline_working_notes/`
- [x] Step 1: Migrate code into `src/public_ai_challenge/phase*`
- [x] Step 2: Partition tests and update imports
- [x] Step 3: Isolate `demo/` and update `demo/demo.py`
- [x] Step 4: Merge dependencies into root `pyproject.toml`
- [x] Step 5: Archive obsolete directories into `archive/`
- [x] Step 6: Verify all tests and demo execution (90 tests passing, demo working end-to-end)

**Activity:**
- 10:40 — Created task file and defined refactoring subtask.
- 10:55 — Successfully migrated documentation, structured phases under `src/public_ai_challenge/`, partitioned test suites, isolated `demo/`, consolidated dependencies in `pyproject.toml`, and verified all 90 tests passing + live demo functional.

## Coordination Notes

- 10:40 [antigravity] — Starting refactoring protocol.
- 10:57 [antigravity] — All phases complete and verified. Ready for user review.

## Blocking Issues

[No blockers yet.]

## Relevant Context

| Type | Name / Path | Note (added by) |
|------|-------------|-----------------|
| ADR | `docs/architecture/README.md` | Accepted architecture authority — `antigravity` |
| Concept | `docs/gemeinde_mcp.concept.md` | Active dev-flow concept — `antigravity` |
| Plan | `docs/gemeinde_mcp.plan.md` | Active dev-flow plan — `antigravity` |

## Shared Activity Log

- 10:40 [antigravity] — created task for pipeline phases reorganization and documentation systematization

---

*This is a shared file. Each contributor owns their own subtask block and their own tagged entries in shared sections. Do not refactor others' content. Coordinate via Coordination Notes. See `phases/status.md` (dev-flow skill) for the full protocol.*
