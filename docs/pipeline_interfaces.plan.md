# Implementation Plan: Define Pipeline Interfaces  {#PL_REFACTOR_INTERFACES}

> **Code:** PL_REFACTOR_INTERFACES
> **Status:** completed
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

- [x] Phase 1 — Define Core Domain Models & Interfaces
- [x] Phase 2 — Refactor Scout Implementations
- [x] Phase 3 — Refactor Synthesis & MCP Implementations
- [x] Phase 4 — Refactor Judge Implementations
- [x] Phase 5 — Update Demo/Orchestrator to use Interfaces

## Phases

### Phase 1 — Define Core Domain Models & Interfaces (`src/public_ai_challenge/core/`) [DONE]

**Depends on:** none
**Verify:** Static type checking & test coverage in `tests/test_core_interfaces/`.

What was created:
| Entity | Module | Purpose |
|--------|--------|---------|
| Core Models | `core/models.py` | Unified data models passed between phases (`ScoutResult`, `ServiceInventoryRecord`, `JudgeReport`, `JudgeFinding`). |
| Pipeline Protocols | `core/interfaces.py` | `ScoutProtocol`, `SynthesisProtocol`, `JudgeProtocol`, `McpServerProtocol`. |

### Phase 2 — Refactor Scout Implementations [DONE]

**Depends on:** Phase 1
**Verify:** Conformance test in `tests/test_core_interfaces/test_interfaces.py`.

What was implemented:
- `ScoutPipelineAdapter` (`phase1_scout_pipeline/adapter.py`) implementing `ScoutProtocol`.
- `FileScoutAdapter` (`phase1_scout_pipeline/adapter.py`) implementing `ScoutProtocol` from static files.
- `PublicAIScoutAdapter` (`alternative_pipeline_publicai/adapter.py`) implementing `ScoutProtocol`.

### Phase 3 — Refactor Synthesis & MCP Implementations [DONE]

**Depends on:** Phase 1
**Verify:** Conformance test in `tests/test_core_interfaces/test_interfaces.py`.

What was implemented:
- `SynthesisGemeindeAdapter` (`phase2_synthesis_gemeinde/adapter.py`) implementing `SynthesisProtocol`.
- `McpServerGemeindeAdapter` (`phase2_synthesis_gemeinde/adapter.py`) implementing `McpServerProtocol`.

### Phase 4 — Refactor Judge Implementations [DONE]

**Depends on:** Phase 1
**Verify:** Conformance test in `tests/test_core_interfaces/test_interfaces.py`.

What was implemented:
- `JudgePipelineAdapter` (`phase3_judge/adapter.py`) implementing `JudgeProtocol`.

### Phase 5 — Update Demo/Orchestrator [DONE]

**Depends on:** Phase 2, 3, 4
**Verify:** `demo/demo.py` runs end-to-end through the abstract interfaces across all 4 stages.

What was implemented:
- Refactored `demo/demo.py` to instantiate and execute `ScoutProtocol`, `SynthesisProtocol`, `JudgeProtocol`, and `McpServerProtocol`.

## Changelog

| Date | Change |
|------|--------|
| 2026-09-25 | Implemented core interfaces, phase adapters, updated demo, and verified 93 passing tests. |
