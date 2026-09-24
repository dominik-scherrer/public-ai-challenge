# The MMP Judge

Implements `docs/architecture/adr/0004` (the Judge is the only quality gate — no municipality ever reviews a Build) and `docs/architecture/adr/0007` (typed data + a separate injection check). Read both before changing anything here — this module exists to make those two ADRs true in code, not to reinterpret them.

## Three checks, not one score

Per `docs/architecture/README.md`'s glossary, the Judge is a gate, not a grader. Every check here produces `pass` / `fail` / `withheld`, never a 1–10 quality rating:

| Check | File | Runs on | Model needed? |
|---|---|---|---|
| **Provenance** — does the evidence actually support the claim? | `pipeline.py` (`judge_provenance`) + `rubrics/provenance_judge.yml` | one attribute at a time | yes, if evidence exists |
| **Injection / safety** — instructions-to-a-model, foreign-domain links, payment details | `injection.py` (deterministic) + `pipeline.py` (`judge_injection`) + `rubrics/injection_judge.yml` | free-text fields | deterministic first, model as fallback |
| **Coverage** — how much of the expected service set did this Build produce? | `coverage.py` | the whole Build | no — pure counting |

A claim with no evidence is **withheld**, not failed, and never reaches a model — see `adapters.py`. A flagged injection is dropped outright, never shown "with a warning." Coverage below the Build Floor blocks the whole Build (previous Build stays live), because that pattern signals a site relaunch, not normal content drift.

## Why this looks like `dominik-scherrer/thesis-educational-agent`

The rubric-YAML-plus-multi-model-ensemble pattern in `llm.py` is lifted directly from that repo's `eval/src/pipeline/score_answers.py` — same shape (system + instruction template, several independent judge models, retry on unparseable JSON), because it already works and was already validated once. What's different, and why:

- **Binary verdicts, not 1–10 scores.** The thesis judges subjective pedagogical quality (Spearman-appropriate). MMP's checks are closer to its binary criteria (score_5/6, Cohen's κ) — provenance and injection are verifiable against source text, not a judgment call, so `pass`/`fail`/`withheld` is the honest output shape.
- **An explicit `withheld` state.** The thesis judge always scores something. MMP's Judge is allowed to say "I have nothing to check this against" and that has to be a distinct, common, non-alarming outcome — not a failure mode.
- **Fail-closed everywhere.** An unparseable model response is a `fail` (provenance) or a `flag` (injection), never silently skipped or treated as a pass. Wrong information reaching a citizen is worse than an over-cautious withhold.

## What this validates against real data right now — and what it doesn't yet

Run it against the actual Ausserberg delivery:

```bash
uv run python -m pipeline.judge.pipeline pipeline/handoff/delivery-2026-09-24/ausserberg/inventory.json
```

Every claim currently comes back **withheld**. That's correct, not broken: `documents.jsonl` is empty in every delivered municipality (see `adapters.py`'s docstring) — the crawler hasn't started capturing source quotes yet, so there is nothing for the provenance judge to check anything against. `test_adapters.py::test_current_seed_data_has_no_evidence_yet` pins this down; when it starts failing, that's the signal that real evidence has landed and this module needs a look, not a bug.

Because of that gap, the only way to actually validate the judge models today is against `fixtures/gold_set.json` — a small hand-built set of claims with real, fabricated, and unrelated evidence, plus injection attempts a keyword filter would and wouldn't catch. This is the same move as the thesis's `eval/human_eval_kits/`: **measure the judge against known-correct and known-wrong cases before trusting it**, especially given ADR-0004 makes it the *only* gate, with zero human review. Its main finding transfers directly here too — disagreement is usually the rubric being ambiguous, not the model being bad, so if a gold-set case fails, tighten `rubrics/*.yml` wording before assuming the model is at fault.

```bash
cp .env.example .env   # add a real OPENAI_API_KEY, and PUBLIC_AI_* for Apertus if you have access
uv sync
OPENAI_API_KEY=... uv run pytest pipeline/judge/tests/test_gold_set_live.py -v
```

## Ensemble: OpenAI + Apertus

`llm.py`'s `JUDGE_MODELS = ("openai", "apertus")` is the intended ensemble — two independent models, because ADR-0004 makes the Judge the *only* gate and one model would be a single point of failure for that. Apertus is called through the exact same env vars (`PUBLIC_AI_ENDPOINT` / `PUBLIC_AI_BASE_URL` / `PUBLIC_AI_API_KEY` / `PUBLIC_AI_MODEL`) that `pipeline/prototype/scraper.py`'s model adapter already uses — one Apertus endpoint configuration serves both.

`resolve_judge_models()` checks what's actually configured at call time and only uses that subset. **It prints a loud `WARNING` line if that's fewer than both** — a 1-model run must never look like a validated 2-model consensus just because Apertus access wasn't provisioned yet. As of this writing, only `OPENAI_API_KEY` is realistically available to this hackathon team; treat every judge-report produced until Apertus is reachable as a single-model result, not the real gate.

## Known gaps (don't build past these without a decision)

- **Apertus access isn't provisioned yet.** The ensemble code supports two models; whether the team actually has a reachable Apertus/Swisscom endpoint for this hackathon is a separate, open question. Until then every run prints the "N/2 configured" warning above — that's expected, not a bug to silence.
- **Coverage reference list is a placeholder.** `config/reference_categories.yml` is six categories pulled from `docs/architecture/CONTEXT.md` and the seed data's own tags — not the real eCH-0070 Gemeinde-Leistungen list ADR-0001 calls for. `coverage.py` doesn't need to change when that lands; only the config file does.
- **No Build Floor number is defensible yet.** `DEFAULT_BUILD_FLOOR = 0.5` in `pipeline.py` is a placeholder, not a measured threshold. Pick a real one only after running coverage against a few real Builds.
- **Same rubric text for both models.** `provenance_judge.yml` / `injection_judge.yml` are sent unmodified to both OpenAI and Apertus. That's the standard ensemble move (independent models, identical instructions), but Apertus is explicitly the "small, constrained" model in this project's own architecture docs (`pipeline/SEMANTIC_COMPILER.md`) — if it turns out to need simpler prompting to perform reliably, that's a per-provider rubric variant to add, not a reason to drop it from the ensemble.

## Layout

```
pipeline/judge/
  schemas.py       Claim / Verdict / *Result dataclasses — the internal contract
  adapters.py       inventory.json -> list[Claim] (the only file that should need
                    to change when ingestion's schema changes)
  llm.py            rubric loading, multi-model calling, JSON extraction + retry
  injection.py      deterministic foreign-link / payment / keyword checks
  coverage.py       Build Floor math
  pipeline.py       orchestrates all three checks, CLI entry point
  rubrics/          *.yml prompts fed to llm.py
  config/           reference_categories.yml (coverage denominator)
  fixtures/         gold_set.json
  tests/            deterministic + dry-run tests (no key needed) and
                    test_gold_set_live.py (skipped without OPENAI_API_KEY)
```
