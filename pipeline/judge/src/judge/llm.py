"""Multi-model judge calling: JSON-schema prompt in, parsed verdict out.

Ported from the pattern in dominik-scherrer/thesis-educational-agent's
eval/src/pipeline/score_answers.py — same shape (a rubric YAML with a
system+instruction template, several independent judge models, retry on
parse failure) adapted for binary verdicts instead of 1-10 scores.

Ensemble: OpenAI + Apertus. Two providers, not one, because ADR-0004 makes
the Judge the *only* gate — a single model would be a single point of
failure for that. The Apertus call reuses the exact env-var convention
pipeline/legacy/prototype/model_adapter.py already established
(PUBLIC_AI_ENDPOINT / PUBLIC_AI_BASE_URL / PUBLIC_AI_API_KEY /
PUBLIC_AI_MODEL) rather than inventing a second naming scheme for the
same "OpenAI-compatible endpoint" concept — see pipeline/README.md and
pipeline/SEMANTIC_COMPILER.md for why Apertus specifically (small,
constrained, eventually Swiss-sovereign execution model).

Each provider only participates once it's actually configured (env vars
present). With zero or one configured, the ensemble still runs — but
resolve_judge_models() prints a warning, because a "2-model ensemble"
that's silently running as 1 model is exactly the failure mode this
exists to avoid. Use --dry-run (see pipeline.py) when neither is
configured; don't let the pipeline pretend a 1-model run is a validated
ensemble result.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

RUBRICS_DIR = Path(__file__).resolve().parent.parent.parent / "rubrics"


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


# --- provider: openai ------------------------------------------------------

OPENAI_MODEL = "gpt-6-luna"  # matches scripts/test_openai.py


def openai_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def call_openai(system_prompt: str, instruction: str) -> Optional[str]:
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
        model=OPENAI_MODEL,
        reasoning={"effort": "low"},
        input=f"{system_prompt}\n\n{instruction}",
    )
    return response.output_text


# --- provider: apertus -------------------------------------------------
# Dependency-free OpenAI-compatible call, matching
# pipeline/legacy/prototype/model_adapter.py's ModelConfig.from_env() exactly —
# same env vars, so anyone who's already pointed the crawler at an Apertus
# endpoint doesn't need to configure anything twice.


# Swisscom's Swiss AI Weeks Apertus endpoint (see docs/Example Curl Swiss API.txt) is the
# same OpenAI-compatible shape; it is used when PUBLIC_AI_* is not set.
SWISSCOM_DEFAULT_MODEL = "swiss-ai/Apertus-v1.5-70B"


def _swisscom_endpoint() -> str:
    base = os.getenv("SWISSCOM_BASE_API", "").strip().rstrip("/")
    return f"{base}/chat/completions" if base and os.getenv("SWISSCOM_API_KEY", "").strip() else ""


def _apertus_endpoint() -> str:
    endpoint = os.getenv("PUBLIC_AI_ENDPOINT", "").strip()
    if endpoint:
        return endpoint
    base_url = os.getenv("PUBLIC_AI_BASE_URL", "").strip().rstrip("/")
    if base_url:
        return f"{base_url}/chat/completions"
    return _swisscom_endpoint()


def _apertus_model() -> str:
    model = os.getenv("PUBLIC_AI_MODEL", "").strip()
    if model or not _swisscom_endpoint() or _apertus_endpoint() != _swisscom_endpoint():
        return model
    return os.getenv("SWISSCOM_MODEL", "").strip() or SWISSCOM_DEFAULT_MODEL


def _apertus_key() -> str:
    if _apertus_endpoint() == _swisscom_endpoint() and _swisscom_endpoint():
        return os.getenv("SWISSCOM_API_KEY", "").strip()
    return os.getenv("PUBLIC_AI_API_KEY", "").strip()


def apertus_is_configured() -> bool:
    return bool(_apertus_endpoint()) and bool(_apertus_model())


def call_apertus(system_prompt: str, instruction: str) -> Optional[str]:
    endpoint = _apertus_endpoint()
    model = _apertus_model()
    api_key = _apertus_key()

    if not endpoint or not model:
        raise JudgeConfigError(
            "Apertus is not configured. Set PUBLIC_AI_ENDPOINT (or PUBLIC_AI_BASE_URL) "
            "and PUBLIC_AI_MODEL — same variables pipeline/legacy/prototype/scraper.py uses — "
            "or run the judge pipeline with --dry-run."
        )

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
        ],
    }
    headers = {"Content-Type": "application/json", "User-Agent": "MMP-Judge/0.1"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise JudgeConfigError(f"Apertus endpoint returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise JudgeConfigError(f"Apertus request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise JudgeConfigError("Unexpected Apertus response shape") from exc


# --- ensemble ---------------------------------------------------------------

_PROVIDERS: dict[str, tuple[Callable[[], bool], Callable[[str, str], Optional[str]]]] = {
    "openai": (openai_is_configured, call_openai),
    "apertus": (apertus_is_configured, call_apertus),
}

# The full intended ensemble, in order. resolve_judge_models() filters this
# down to what's actually configured right now — extend this tuple, don't
# just swap entries, if a third provider is added later.
JUDGE_MODELS: tuple[str, ...] = ("openai", "apertus")


def resolve_judge_models(models: Optional[tuple[str, ...]] = None) -> list[str]:
    """Which providers are actually usable right now, with a loud warning if that's fewer than intended."""
    candidates = models or JUDGE_MODELS
    configured = [label for label in candidates if _PROVIDERS[label][0]()]

    if len(configured) < len(candidates):
        missing = [label for label in candidates if label not in configured]
        print(
            f"[judge] WARNING: running with {len(configured)}/{len(candidates)} configured "
            f"judge model(s); missing: {', '.join(missing)}. A result from this ensemble is "
            f"NOT the validated {len(candidates)}-model consensus ADR-0004 assumes.",
        )
    if not configured:
        raise JudgeConfigError(
            f"No judge model is configured out of {list(candidates)}. "
            "Configure at least one, or run the judge pipeline with --dry-run."
        )
    return configured


def call_judge_ensemble(
    rubric: RubricPrompt,
    *,
    max_retries: int = 1,
    models: Optional[list[str]] = None,
    **template_vars: Any,
) -> list[tuple[str, Optional[dict[str, Any]]]]:
    """Calls every configured judge model, returns [(model_label, parsed_json_or_None), ...].

    A None result means the model failed to produce parseable JSON after
    retries — callers must treat that as "could not verify", never as pass.
    """
    system_prompt, instruction = rubric.render(**template_vars)
    active_models = models if models is not None else resolve_judge_models()
    results: list[tuple[str, Optional[dict[str, Any]]]] = []

    for label in active_models:
        _, call_fn = _PROVIDERS[label]
        attempts_left = max_retries + 1
        parsed: Optional[dict[str, Any]] = None
        while attempts_left > 0 and parsed is None:
            raw = call_fn(system_prompt, instruction)
            parsed = extract_and_parse_json(raw) if raw else None
            attempts_left -= 1
        results.append((label, parsed))

    return results
