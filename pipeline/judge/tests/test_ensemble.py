"""Tests resolve_judge_models() -- the piece that decides whether a run is
actually the 2-model (OpenAI + Apertus) ensemble ADR-0004 assumes, or a
degraded 1-model run that must say so loudly rather than pass silently.

No real network calls or keys needed: openai_is_configured/apertus_is_configured
only check env vars.
"""

import os

import pytest

from judge.llm import (
    JUDGE_MODELS,
    JudgeConfigError,
    apertus_is_configured,
    openai_is_configured,
    resolve_judge_models,
)

ENV_KEYS = ["OPENAI_API_KEY", "PUBLIC_AI_ENDPOINT", "PUBLIC_AI_BASE_URL", "PUBLIC_AI_API_KEY", "PUBLIC_AI_MODEL"]


@pytest.fixture
def clean_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield monkeypatch


def test_intended_ensemble_is_openai_and_apertus():
    assert set(JUDGE_MODELS) == {"openai", "apertus"}


def test_neither_configured_is_not_configured(clean_env):
    assert openai_is_configured() is False
    assert apertus_is_configured() is False


def test_apertus_requires_both_endpoint_and_model(clean_env):
    clean_env.setenv("PUBLIC_AI_ENDPOINT", "https://example.test/v1/chat/completions")
    assert apertus_is_configured() is False  # no PUBLIC_AI_MODEL yet
    clean_env.setenv("PUBLIC_AI_MODEL", "apertus-8b")
    assert apertus_is_configured() is True


def test_apertus_accepts_base_url_instead_of_endpoint(clean_env):
    clean_env.setenv("PUBLIC_AI_BASE_URL", "https://example.test/v1")
    clean_env.setenv("PUBLIC_AI_MODEL", "apertus-8b")
    assert apertus_is_configured() is True


def test_resolve_raises_when_nothing_configured(clean_env):
    with pytest.raises(JudgeConfigError):
        resolve_judge_models()


def test_resolve_returns_only_configured_providers(clean_env, capsys):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    configured = resolve_judge_models()
    assert configured == ["openai"]
    # must warn loudly that this is a degraded run, not a silent 1-model pass
    assert "WARNING" in capsys.readouterr().out


def test_resolve_returns_both_when_fully_configured(clean_env, capsys):
    clean_env.setenv("OPENAI_API_KEY", "sk-test")
    clean_env.setenv("PUBLIC_AI_ENDPOINT", "https://example.test/v1/chat/completions")
    clean_env.setenv("PUBLIC_AI_MODEL", "apertus-8b")
    configured = resolve_judge_models()
    assert configured == ["openai", "apertus"]
    assert "WARNING" not in capsys.readouterr().out
