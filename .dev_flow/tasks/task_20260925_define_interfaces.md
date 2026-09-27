# Task: Define Pipeline Interfaces

> **Task ID:** task_20260925_define_interfaces
> **Created:** 2026-09-25
> **Last updated:** 2026-09-25 11:15
> **Status:** done
> **Contributors:** antigravity

## Current Work Item
- **Document:** [PL_REFACTOR_INTERFACES](../../docs/pipeline_interfaces.plan.md)
- **Phase:** implement
- **Traceable ID:** PL_REFACTOR_INTERFACES

## Intent
The user wants to formally define interfaces for the main pipeline phases/stages (Scout, Synthesis, Judge, MCP Serving) and prepare the project structure to allow one or several implementations of these interfaces. The goal is to plan the refactoring needed to transition the current codebase to this interface-driven design.

## Description
This task covers the design of the abstract interfaces (using Python `typing.Protocol` or `abc.ABC`) for the main stages of the public-ai-challenge pipeline, and the creation of a refactoring plan to adapt the existing codebases (Scout, Synthesis, Judge, PublicAI alternative) to these interfaces.

### Subtask: Plan Refactoring (antigravity)
- **Status:** done
- **Goal:** Draft the implementation plan for defining the interfaces and refactoring the code.
- [x] Analyze current phase inputs/outputs.
- [x] Create `docs/pipeline_interfaces.plan.md`.
- [x] Present the plan to the user for review.

### Subtask: Implement Interfaces & Adapters (antigravity)
- **Status:** done
- **Goal:** Implement core models, protocols, phase adapters, and wire them up.
- [x] Phase 1: Define Core Domain Models & Interfaces (`core/models.py`, `core/interfaces.py`).
- [x] Phase 2: Refactor Scout Implementations with adapters.
- [x] Phase 3: Refactor Synthesis & MCP Implementations with adapters.
- [x] Phase 4: Refactor Judge Implementations with adapters.
- [x] Phase 5: Update Demo/Orchestrator to use Interfaces.
- [x] Verify test suite passes (93 tests passing).

## Coordination Notes
- (antigravity) 2026-09-25: Created task and started drafting the refactoring plan.

## Blocking Issues

## Relevant Context
| Context | Note | Added by |
|---------|------|----------|
| `docs/pipeline_interfaces.plan.md` | The refactoring plan being drafted | antigravity |

## Shared Activity Log
- 2026-09-25 (antigravity): Created task and started planning.
