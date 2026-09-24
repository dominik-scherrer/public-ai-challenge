"""One small OpenAI-compatible chat client for both roles MMP needs a model for.

- **chat** (the Reference Client): must run on Swiss public AI for the
  sovereignty offer to be true (ADR-0002). Configured with ``PUBLIC_AI_*``.
- **build** (extraction during a Build): may use any capable model, because its
  input is public web content (ADR-0002, Consequences). Configured with
  ``MMP_BUILD_*``, falling back to ``PUBLIC_AI_*`` and then ``OPENAI_API_KEY``.

Tool calling: Apertus on the Public AI Inference Utility does not support the
OpenAI ``tools`` parameter (see OQ-2 and litellm#21124), so MMP never relies
on it. Every model call asks for one JSON object and is parsed defensively,
which works the same on Apertus, OpenAI and anything else OpenAI-compatible.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol

PUBLIC_AI_DEFAULT_BASE_URL = "https://api.publicai.co/v1"
PUBLIC_AI_DEFAULT_MODEL = "swiss-ai/apertus-v1.5-70b"
USER_AGENT = "MMP-Reference-Client/0.1"


class LLMError(RuntimeError):
    pass


class ChatModel(Protocol):
    label: str

    def complete_json(self, system: str, messages: list[dict[str, str]]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    api_key: str
    model: str

    @property
    def host(self) -> str:
        return re.sub(r"^https?://", "", self.base_url).split("/")[0]


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def chat_config() -> ModelConfig | None:
    key = _env("PUBLIC_AI_API_KEY")
    if not key:
        return None
    return ModelConfig(
        base_url=_env("PUBLIC_AI_BASE_URL") or PUBLIC_AI_DEFAULT_BASE_URL,
        api_key=key,
        model=_env("PUBLIC_AI_MODEL") or PUBLIC_AI_DEFAULT_MODEL,
    )


def build_config() -> ModelConfig | None:
    if _env("MMP_BUILD_API_KEY"):
        return ModelConfig(
            base_url=_env("MMP_BUILD_BASE_URL") or "https://api.openai.com/v1",
            api_key=_env("MMP_BUILD_API_KEY"),
            model=_env("MMP_BUILD_MODEL") or "gpt-6-luna",
        )
    public = chat_config()
    if public:
        return public
    if _env("OPENAI_API_KEY"):
        return ModelConfig(
            base_url="https://api.openai.com/v1",
            api_key=_env("OPENAI_API_KEY"),
            model=_env("MMP_BUILD_MODEL") or "gpt-6-luna",
        )
    return None


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any] | None:
    """Best-effort: models wrap JSON in prose or code fences (same idea as the Judge's llm.py)."""
    if not text:
        return None
    cleaned = _FENCE.sub("", text.strip())
    # thinking models may emit a reasoning block first
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()
    for candidate in (cleaned, *(m.group(0) for m in [_OBJECT.search(cleaned)] if m)):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


class OpenAICompatibleModel:
    def __init__(self, config: ModelConfig, *, timeout: float = 90, retries: int = 1):
        from openai import OpenAI

        self.config = config
        self.label = f"{config.model} @ {config.host}"
        self._retries = retries
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=timeout,
            default_headers={"User-Agent": USER_AGENT},
        )

    def complete_json(self, system: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        convo = [{"role": "system", "content": system}, *messages]
        last = ""
        for _ in range(self._retries + 1):
            response = self._client.chat.completions.create(
                model=self.config.model,
                messages=convo,
                temperature=0,
            )
            last = response.choices[0].message.content or ""
            parsed = parse_json_object(last)
            if parsed is not None:
                return parsed
            convo = [
                *convo,
                {"role": "assistant", "content": last},
                {"role": "user", "content": "Antworte ausschliesslich mit einem gültigen JSON-Objekt."},
            ]
        raise LLMError(f"Model returned no parseable JSON object: {last[:300]!r}")
