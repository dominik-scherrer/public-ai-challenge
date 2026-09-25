# Implementation Plan: Merged Final Pipeline {#PL_MERGE_FINAL}

> **Code:** PL_MERGE_FINAL
> **Status:** in-progress
> **Created:** 2026-09-25
> **Updated:** 2026-09-25
>
> **Goal:** Merge the strengths of the Scout, Gemeinde, and PublicAI pipelines into a final, unified solution implementing the core `Protocol` interfaces.

## Goal

To create a `phase1_scout` and `phase2_synthesis` package that combines the robust security of the PublicAI crawler, the heuristic adaptability of Scout, the simple schema generation of Gemeinde Synthesis, and the rigorous hallucination prevention of the PublicAI Reviewer agent.

## Strategy

We will create two new packages that implement the interfaces defined in `core/interfaces.py`:

### 1. Phase 1 Final: Secure Scout (`src/public_ai_challenge/phase1_scout/`)
- **Base:** Scout heuristic matching (`discovery.py`).
- **Network Layer:** Replaces standard `httpx` fetching with the PublicAI `SafeCrawler` to enforce IP/DNS restrictions and PII-stripping HTML parsing.
- **Adapter:** `FinalScoutAdapter` implementing `ScoutProtocol`.

### 2. Phase 2 Final: Reviewed Synthesis (`src/public_ai_challenge/phase2_synthesis/`)
- **Base:** Synthesis Gemeinde agent extraction (`agents.py` & `data_generator.py`).
- **Validation:** Integrates a Reviewer Agent step that mathematically validates the structured `ExtractedData` claims against the raw HTML fragments (borrowed from PublicAI Builder).
- **Adapter:** `FinalSynthesisAdapter` implementing `SynthesisProtocol`.

## Execution Steps

- [ ] **Step 1: Scaffold Final Packages**
  - Create `phase1_scout/` and `phase2_synthesis/`.
  - Add `__init__.py`.
- [ ] **Step 2: Implement Phase 1 Final**
  - Extract and adapt `SafeCrawler` to serve the `PageIR` format expected by Scout heuristics.
  - Implement `FinalScoutAdapter`.
- [ ] **Step 3: Implement Phase 2 Final**
  - Use the existing Gemeinde data generator.
  - Inject a PydanticAI Reviewer Agent after synthesis to validate claims against cached fragments.
  - Implement `FinalSynthesisAdapter`.
- [ ] **Step 4: Update Demo Orchestrator**
  - Modify `demo/demo.py` to use `FinalScoutAdapter` and `FinalSynthesisAdapter` by default.
- [ ] **Step 5: Verification**
  - Ensure all tests pass.
  - Execute end-to-end demo and verify valid outputs.
