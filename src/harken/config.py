"""Runtime configuration. Everything has a sane default; nothing requires a key."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]


@dataclass
class Config:
    db_path: str = field(default_factory=lambda: os.getenv("HARKEN_DB", "harken.db"))
    # which sources to query (default = zero-config ones)
    sources: list[str] = field(
        default_factory=lambda: _env_list("HARKEN_SOURCES") or ["hackernews", "reddit"]
    )
    per_source_limit: int = field(
        default_factory=lambda: int(os.getenv("HARKEN_LIMIT", "50"))
    )
    llm_provider: str = field(default_factory=lambda: os.getenv("HARKEN_LLM_PROVIDER", "none"))
    # source-specific options
    mastodon_instance: str = field(
        default_factory=lambda: os.getenv("HARKEN_MASTODON_INSTANCE", "mastodon.social")
    )
    rss_feeds: list[str] = field(default_factory=lambda: _env_list("HARKEN_RSS_FEEDS"))

    def source_options(self, name: str) -> dict:
        if name == "mastodon":
            return {"instance": self.mastodon_instance}
        if name == "rss":
            return {"feeds": self.rss_feeds}
        return {}
