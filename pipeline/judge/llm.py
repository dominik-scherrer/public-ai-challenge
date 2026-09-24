"""Multi-model judge calling: JSON-schema prompt in, parsed verdict out.

Ported from the pattern in dominik-scherrer/thesis-educational-agent's
eval/src/pipeline/score_answers.py — same shape (a rubric YAML with a
system+instruction template, several independent judge models, retry on
parse failure) adapted for binary verdicts instead of 1-10 scores.

Ensemble note: the thesis called three independent models (gemini, openai,
qwen) per claim because a single-model judge is a single point of failure
— see docs/architecture/adr/0004 ("the Judge is the only quality gate").
This repo currently only has an OpenAI key wired up (scripts/test_openai.py),
so JUDGE_MODELS has one entry for now. Add a second provider before this
runs in production, not after.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml

RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"

# (label, model_id). Extend this list — don't just swap the one entry —
# once a second provider is available. See module docstring.
JUDGE_MODELS: list[tuple[str, str]] = [
    ("openai", "gpt-6-luna"),
]


class JudgeConfigError(RuntimeError):
    pass


class RubricPrompt:
    def __init__(self, path: Path):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise JudgeConfigError(f"Rubric YAML must be a mapping: {path}")
        self.id: str = raw.get("id", path.stem)
        self.system: str = (raw.get("system") or "").strip()
        self.instruction_template: str = (raw.get("instruction") or "").strip()
        self.variables: list[str] = raw.get("variables", [])

    def render(self, **kwargs: Any) -> tuple[str, str]:
        missing = [v for v in self.variables if v not in kwargs]
        if missing:
            raise JudgeConfigError(f"Rubric {self.id} missing variables: {missing}")
        instruction = self.instruction_template
        for key, value in kwargs.items():
            instruction = instruction.replace(f"{{{key}}}", str(value))
        return self.system, instruction


def load_rubric(name: str) -> RubricPrompt:
    """name e.g. 'provenance_judge' or 'injection_judge'."""
    path = RUBRICS_DIR / f"{name}.yml"
    if not path.exists():
        raise JudgeConfigError(f"No rubric file at {path}")
    return RubricPrompt(path)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_and_parse_json(response_text: str) -> Optional[dict[str, Any]]:
    """Best-effort JSON extraction — models wrap JSON in prose or code fences."""
    if not response_text:
        return None
    text = response_text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def call_model(model: str, system_prompt: str, instruction: str, *, temperature: float = 0.0) -> Optional[str]:
    """One call to one model. Returns raw text, or None on failure.

    Isolated in its own function so tests can monkeypatch it instead of
    hitting a real API — see tests/test_pipeline_dry_run.py.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise JudgeConfigError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add a key, "
            "or run the judge pipeline with --dry-run to exercise the deterministic "
            "path only."
        )
    from openai import OpenAI  # imported lazily so --dry-run never needs the package configured

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        input=f"{system_prompt}\n\n{instruction}",
    )
    return response.output_text


def call_judge_ensemble(
    rubric: RubricPrompt,
    *,
    max_retries: int = 1,
    models: Optional[list[tuple[str, str]]] = None,
    **template_vars: Any,
) -> list[tuple[str, Optional[dict[str, Any]]]]:
    """Calls every configured judge model, returns [(model_label, parsed_json_or_None), ...].

    A None result means the model failed to produce parseable JSON after
    retries — callers must treat that as "could not verify", never as pass.
    """
    system_prompt, instruction = rubric.render(**template_vars)
    results: list[tuple[str, Optional[dict[str, Any]]]] = []

    for label, model in models or JUDGE_MODELS:
        attempts_left = max_retries + 1
        parsed: Optional[dict[str, Any]] = None
        while attempts_left > 0 and parsed is None:
            raw = call_model(model, system_prompt, instruction)
            parsed = extract_and_parse_json(raw) if raw else None
            attempts_left -= 1
        results.append((label, parsed))

    return results
