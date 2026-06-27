"""Anthropic Claude provider (optional).

Requires ``pip install anthropic`` and ``ANTHROPIC_API_KEY``. Model defaults to
Claude Opus 4.8 and is overridable via ``HARKEN_LLM_MODEL``.
"""

from __future__ import annotations

import os

from harken.llm.base import LLMProvider

DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None, **_):
        self.model = model or os.getenv("HARKEN_LLM_MODEL") or DEFAULT_MODEL
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:  # pragma: no cover - optional dep
                raise RuntimeError(
                    "The 'anthropic' package is required for the Anthropic provider. "
                    "Install it with: pip install anthropic"
                ) from e
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        client = self._get_client()
        resp = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
