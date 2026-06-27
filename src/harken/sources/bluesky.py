"""Bluesky source via the public AT Protocol search endpoint — no auth needed.

Uses the public ``app.bsky.feed.searchPosts`` XRPC endpoint on the bsky.app
public API host, which serves results without a session for reasonable use.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harken.models import Mention
from harken.sources.base import Source

_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


class BlueskySource(Source):
    name = "bluesky"
    label = "Bluesky"
    needs_config = False

    def fetch(self, query: str, limit: int = 50) -> list[Mention]:
        params = {"q": query, "limit": min(limit, 100), "sort": "latest"}
        with self._client() as client:
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        mentions: list[Mention] = []
        for post in data.get("posts", []):
            author = post.get("author", {})
            record = post.get("record", {})
            handle = author.get("handle")
            uri = post.get("uri", "")
            rkey = uri.split("/")[-1] if uri else ""
            created = _parse(record.get("createdAt"))
            mentions.append(
                Mention(
                    source=self.name,
                    query=query,
                    author=handle,
                    title=None,
                    text=record.get("text", ""),
                    url=f"https://bsky.app/profile/{handle}/post/{rkey}"
                    if handle and rkey
                    else None,
                    created_at=created,
                    score=post.get("likeCount"),
                )
            )
        return mentions


def _parse(s: str | None) -> datetime:
    if not s:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
