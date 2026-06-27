"""Ollama provider (optional) — fully local LLM, no API key, no cloud.

Point Harken at a local Ollama server (default http://localhost:11434). This is
the "self-hosted all the way down" option: your data never leaves your machine.
"""

from __future__ import annotations

import os

import httpx

from harken.llm.base import LLMProvider

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    name = "ollama"
    available = True  # assumes a local server; errors surface on call if not

    def __init__(self, model: str | None = None, host: str | None = None, **_):
        self.model = model or os.getenv("HARKEN_LLM_MODEL") or DEFAULT_MODEL
        self.host = (host or os.getenv("HARKEN_LLM_HOST") or DEFAULT_HOST).rstrip("/")

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        resp = httpx.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "system": system or "",
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
