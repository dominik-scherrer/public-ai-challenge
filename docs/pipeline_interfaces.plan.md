# Implementation Plan: Define Pipeline Interfaces  {#PL_REFACTOR_INTERFACES}

> **Code:** PL_REFACTOR_INTERFACES
> **Status:** draft
> **Created:** 2026-09-25
> **Updated:** 2026-09-25
>
> **Concept:** [public_ai_challenge.concept.md](./public_ai_challenge.concept.md)
>
> **Goal:** Formally define abstract interfaces (Protocols/ABCs) for the main pipeline phases (Scout, Synthesis, Judge) so that multiple implementations (e.g. from the `publicai` alternative vs the `pipeline` main branch) can be swapped out seamlessly.

## Goal

To establish a clear, strongly-typed boundary between the 4 pipeline phases using standard Python interfaces (`typing.Protocol` or `abc.ABC`), and to adapt the existing code to these interfaces. This will allow the main orchestrator (or demo script) to inject any implementation (e.g., `ScoutPublicAI` vs `ScoutScrapy`) interchangeably.

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Interface Type | `typing.Protocol` | Python structural subtyping allows us to type-check implementations without forcing them to inherit from a common base class, which is better for retrofitting existing independent subprojects. |
| Domain Models | Unified `core/models.py` | Currently, Phase 1 outputs `MunicipalityDiscovery` and Phase 2 expects `ScoutedService`. We need a unified set of models (or adaptors) passed between these interface boundaries. |

## Progress

- [ ] Phase 1 — Define Core Domain Models & Interfaces
- [ ] Phase 2 — Refactor Scout Implementations
- [ ] Phase 3 — Refactor Synthesis & MCP Implementations
- [ ] Phase 4 — Refactor Judge Implementations
- [ ] Phase 5 — Update Demo/Orchestrator to use Interfaces

## Phases

### Phase 1 — Define Core Domain Models & Interfaces (`src/public_ai_challenge/core/`) [TODO]

**Depends on:** none
**Verify:** Static type checking (`mypy` or `pyright`) passes on the new `core/` package.

What to create:
| Entity | Module | Purpose |
|--------|--------|---------|
| Core Models | `core/models.py` | Unified data models passed between phases (e.g., `MunicipalityScoutResult`, `ServiceInventoryRecord`, `JudgeEvaluation`). |
| Pipeline Protocols | `core/interfaces.py` | `ScoutProtocol`, `SynthesisProtocol`, `JudgeProtocol`, `McpServerProtocol`. |

Notes:
- The interfaces should be asynchronous (`async def`).

### Phase 2 — Refactor Scout Implementations [TODO]

**Depends on:** Phase 1
**Verify:** The existing `phase1_scout_pipeline` passes its own tests and correctly implements `ScoutProtocol`.

What to implement:
- Wrap `phase1_scout_pipeline` in a class `ScoutPipelineImpl` that implements `ScoutProtocol`.
- Wrap `alternative_pipeline_publicai`'s scouting logic in a class `ScoutPublicAIImpl` that implements `ScoutProtocol`.

### Phase 3 — Refactor Synthesis & MCP Implementations [TODO]

**Depends on:** Phase 1
**Verify:** `phase2_synthesis_gemeinde` correctly implements `SynthesisProtocol` and `McpServerProtocol`.

What to implement:
- Create `SynthesisGemeindeImpl` implementing `SynthesisProtocol`.
- Create `McpServerGemeindeImpl` implementing `McpServerProtocol` (extracting the server logic from `pipeline.py`).

### Phase 4 — Refactor Judge Implementations [TODO]

**Depends on:** Phase 1
**Verify:** `phase3_judge_pipeline` correctly implements `JudgeProtocol`.

What to implement:
- Create `JudgePipelineImpl` implementing `JudgeProtocol` that wraps the existing `BuildJudge` orchestrator.

### Phase 5 — Update Demo/Orchestrator [TODO]

**Depends on:** Phase 2, 3, 4
**Verify:** `demo/demo.py` runs end-to-end using the new interfaces.

What to implement:
- Update `demo/demo.py` to instantiate the implementations and pass them sequentially through the interfaces.

## Changelog

| Date | Change |
|------|--------|
| 2026-09-25 | Initial draft of the refactoring plan |
