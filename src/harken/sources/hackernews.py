"""Hacker News source via the public Algolia API — no key, no rate-limit pain.

This is the zero-config workhorse: it works on a clean clone with nothing set up.
"""

from __future__ import annotations

from datetime import datetime, timezone

from harken.models import Mention
from harken.sources.base import Source

_API = "https://hn.algolia.com/api/v1/search_by_date"


class HackerNewsSource(Source):
    name = "hackernews"
    label = "Hacker News"
    needs_config = False

    def fetch(self, query: str, limit: int = 50) -> list[Mention]:
        params = {
            "query": query,
            "tags": "(story,comment)",
            "hitsPerPage": min(limit, 100),
        }
        with self._client() as client:
            resp = client.get(_API, params=params)
            resp.raise_for_status()
            data = resp.json()

        mentions: list[Mention] = []
        for hit in data.get("hits", []):
            text = hit.get("title") or hit.get("story_title") or ""
            body = hit.get("comment_text") or hit.get("story_text") or ""
            object_id = hit.get("objectID")
            ts = hit.get("created_at_i")
            created = (
                datetime.fromtimestamp(ts, tz=timezone.utc)
                if ts
                else datetime.now(timezone.utc)
            )
            mentions.append(
                Mention(
                    source=self.name,
                    query=query,
                    author=hit.get("author"),
                    title=text or None,
                    text=_strip_html(body),
                    url=f"https://news.ycombinator.com/item?id={object_id}"
                    if object_id
                    else hit.get("url"),
                    created_at=created,
                    score=hit.get("points"),
                )
            )
        return mentions


def _strip_html(s: str) -> str:
    if not s:
        return ""
    import re

    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&")
    s = s.replace("&gt;", ">").replace("&lt;", "<")
    return re.sub(r"\s+", " ", s).strip()
