"""OpenAI-compatible provider (optional).

Talks to any OpenAI-compatible /chat/completions endpoint via httpx (no SDK
required). Works with OpenAI, OpenRouter, Together, etc. via ``HARKEN_LLM_BASE_URL``.
Requires ``OPENAI_API_KEY`` (or ``HARKEN_LLM_API_KEY``).
"""

from __future__ import annotations

import os

import httpx

from harken.llm.base import LLMProvider

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, **_):
        self.model = model or os.getenv("HARKEN_LLM_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.getenv("HARKEN_LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._api_key = api_key or os.getenv("HARKEN_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model, "messages": messages, "max_tokens": max_tokens},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
