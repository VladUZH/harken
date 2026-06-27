"""LLM provider factory tests — no network, no keys."""

import pytest

from harken.llm import NullProvider, get_provider


def test_default_is_null(monkeypatch):
    monkeypatch.delenv("HARKEN_LLM_PROVIDER", raising=False)
    p = get_provider()
    assert isinstance(p, NullProvider)
    assert p.available is False


def test_null_provider_raises_on_complete():
    p = get_provider("none")
    with pytest.raises(RuntimeError):
        p.complete("hello")


def test_unknown_provider_errors():
    with pytest.raises(ValueError):
        get_provider("definitely-not-a-provider")


def test_anthropic_provider_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = get_provider("anthropic")
    assert p.name == "anthropic"
    assert p.available is False  # no key -> not available, so pipeline skips it


def test_openai_provider_reads_model_env(monkeypatch):
    monkeypatch.setenv("HARKEN_LLM_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    p = get_provider("openai")
    assert p.model == "gpt-test"
    assert p.available is True
