"""Source interface and shared HTTP helper."""

from __future__ import annotations

import httpx

from harken.models import Mention

USER_AGENT = "harken/0.1 (+https://github.com/VladUZH/harken)"


class Source:
    """Base class for a mention source.

    Subclasses set :attr:`name` and implement :meth:`fetch`. Sources should be
    resilient: a network error for one source must never sink the whole run
    (the pipeline isolates failures), but raising here is fine — the caller
    catches it.
    """

    name: str = "base"
    #: human-readable, shown in the dashboard
    label: str = "Base"
    #: whether the source needs configuration to do anything useful
    needs_config: bool = False

    def __init__(self, **options):
        self.options = options

    def fetch(self, query: str, limit: int = 50) -> list[Mention]:
        raise NotImplementedError

    # -- helpers -------------------------------------------------------------
    def _client(self, **kwargs) -> httpx.Client:
        headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
        return httpx.Client(headers=headers, timeout=15.0, **kwargs)
