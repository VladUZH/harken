"""Pluggable mention sources.

Each source implements :class:`~harken.sources.base.Source`. New sources are
registered in :data:`REGISTRY`. All sources shipped in v1 work with no paid
credentials; ``hackernews`` needs no key at all.
"""

from __future__ import annotations

from harken.sources.base import Source
from harken.sources.bluesky import BlueskySource
from harken.sources.hackernews import HackerNewsSource
from harken.sources.mastodon import MastodonSource
from harken.sources.reddit import RedditSource
from harken.sources.rss import RSSSource

REGISTRY: dict[str, type[Source]] = {
    HackerNewsSource.name: HackerNewsSource,
    RedditSource.name: RedditSource,
    MastodonSource.name: MastodonSource,
    BlueskySource.name: BlueskySource,
    RSSSource.name: RSSSource,
}

# Sources that work with zero configuration (no key, no account).
DEFAULT_SOURCES = ["hackernews", "reddit"]

__all__ = ["Source", "REGISTRY", "DEFAULT_SOURCES"]
