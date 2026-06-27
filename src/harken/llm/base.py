"""LLM provider interface.

A provider does exactly one thing: turn a (system, prompt) pair into text.
Higher-level analysis (sentiment refinement, theme labelling) builds prompts on
top of this and parses the result, so providers stay tiny and interchangeable.
"""

from __future__ import annotations


class LLMProvider:
    name = "base"
    available = False  # whether this provider can actually make a call

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
        raise NotImplementedError
