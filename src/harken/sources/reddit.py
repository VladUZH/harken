"""Reddit source via the public search JSON endpoint — no OAuth for light use.

Reddit serves ``/search.json`` without authentication at low volume. For heavier
use, set ``HARKEN_REDDIT_*`` credentials (roadmap) — but the zero-config path
works for trying it out. Reddit rate-limits aggressively; the pipeline treats a
429/network error as "this source returned nothing" rather than failing the run.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harken.models import Mention
from harken.sources.base import Source

_API = "https://www.reddit.com/search.json"


class RedditSource(Source):
    name = "reddit"
    label = "Reddit"
    needs_config = False

    def fetch(self, query: str, limit: int = 50) -> list[Mention]:
        params = {"q": query, "limit": min(limit, 100), "sort": "new", "type": "link"}
        with self._client() as client:
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        mentions: list[Mention] = []
        for child in data.get("data", {}).get("children", []):
            d = child.get("data", {})
            ts = d.get("created_utc")
            created = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                if ts
                else datetime.now(timezone.utc)
            )
            permalink = d.get("permalink")
            mentions.append(
                Mention(
                    source=self.name,
                    query=query,
                    author=d.get("author"),
                    title=d.get("title") or None,
                    text=d.get("selftext") or "",
                    url=f"https://www.reddit.com{permalink}" if permalink else d.get("url"),
                    created_at=created,
                    score=d.get("score"),
                )
            )
        return mentions
