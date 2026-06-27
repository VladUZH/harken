"""Swappable LLM providers. Optional — Harken works fully without any of them.

The default is :class:`NullProvider` (no network, no key): sentiment falls back
to the lexicon analyzer and themes to TF clustering. Set ``HARKEN_LLM_PROVIDER``
(+ the provider's key) to upgrade. No vendor is hard-wired — adding a provider is
one small class.
"""

from __future__ import annotations

import os

from harken.llm.base import LLMProvider
from harken.llm.null import NullProvider

# name -> import path (lazy, so optional SDKs aren't required to import this module)
_PROVIDERS = {
    "none": "harken.llm.null:NullProvider",
    "null": "harken.llm.null:NullProvider",
    "anthropic": "harken.llm.anthropic_provider:AnthropicProvider",
    "openai": "harken.llm.openai_provider:OpenAIProvider",
    "ollama": "harken.llm.ollama_provider:OllamaProvider",
}


def get_provider(name: str | None = None, **kwargs) -> LLMProvider:
    """Return a provider by name (or from ``HARKEN_LLM_PROVIDER``; default none)."""
    name = (name or os.getenv("HARKEN_LLM_PROVIDER") or "none").lower()
    target = _PROVIDERS.get(name)
    if target is None:
        raise ValueError(
            f"Unknown LLM provider {name!r}. Options: {', '.join(sorted(set(_PROVIDERS)))}"
        )
    module_path, cls_name = target.split(":")
    import importlib

    cls = getattr(importlib.import_module(module_path), cls_name)
    return cls(**kwargs)


__all__ = ["LLMProvider", "NullProvider", "get_provider"]
