"""The default provider: does nothing, so callers fall back to local analysis."""

from __future__ import annotations

from harken.llm.base import LLMProvider


class NullProvider(LLMProvider):
    name = "none"
    available = False

    def __init__(self, **_):
        pass

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        raise RuntimeError(
            "No LLM provider configured. Set HARKEN_LLM_PROVIDER (anthropic|openai|ollama) "
            "to enable LLM-powered analysis. Local lexicon/TF analysis is used by default."
        )
