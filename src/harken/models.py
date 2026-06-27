"""Core data models for Harken.

Everything flowing through the pipeline is normalised into a :class:`Mention`.
Sources produce them, analyzers annotate them, the store persists them, and the
web dashboard renders them.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel


class Sentiment(str, Enum):
    """Coarse sentiment label. Kept deliberately small — useful, not precise."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class Mention(BaseModel):
    """A single thing someone said, somewhere, that matched a tracked query.

    ``id`` is a stable content hash so the same item fetched twice (or by two
    overlapping queries) de-duplicates cleanly in the store.
    """

    id: str = ""
    source: str  # e.g. "hackernews", "reddit", "mastodon"
    query: str  # the tracked term this mention matched
    author: str | None = None
    title: str | None = None
    text: str = ""
    url: str | None = None
    created_at: datetime
    score: int | None = None  # upvotes / points / favourites, source-dependent

    # Populated by analyzers (None until analysed).
    sentiment: Sentiment | None = None
    sentiment_score: float | None = None  # signed, roughly [-1, 1]
    theme: str | None = None

    def model_post_init(self, __context) -> None:  # noqa: D401
        if not self.id:
            self.id = self.compute_id()

    @property
    def content(self) -> str:
        """Title + body, the text analyzers actually read."""
        parts = [p for p in (self.title, self.text) if p]
        return "\n".join(parts).strip()

    def compute_id(self) -> str:
        basis = self.url or f"{self.source}:{self.author}:{self.content[:200]}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
