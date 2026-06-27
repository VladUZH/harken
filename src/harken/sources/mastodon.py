"""Mastodon source via a public instance search API — no key for public posts.

Defaults to mastodon.social; override with ``instance=`` (or ``HARKEN_MASTODON_INSTANCE``).
Public-status search via the v2 search endpoint works unauthenticated on many
instances; some require a token (roadmap).
"""

from __future__ import annotations

from datetime import datetime, timezone

from harken.models import Mention
from harken.sources.base import Source


class MastodonSource(Source):
    name = "mastodon"
    label = "Mastodon"
    needs_config = False

    def __init__(self, instance: str = "mastodon.social", **options):
        super().__init__(**options)
        self.instance = instance.replace("https://", "").rstrip("/")

    def fetch(self, query: str, limit: int = 50) -> list[Mention]:
        url = f"https://{self.instance}/api/v2/search"
        params = {"q": query, "type": "statuses", "limit": min(limit, 40)}
        with self._client() as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        mentions: list[Mention] = []
        for st in data.get("statuses", []):
            acct = st.get("account", {})
            created = _parse(st.get("created_at"))
            mentions.append(
                Mention(
                    source=self.name,
                    query=query,
                    author=acct.get("acct"),
                    title=None,
                    text=_strip_html(st.get("content", "")),
                    url=st.get("url"),
                    created_at=created,
                    score=st.get("favourites_count"),
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


def _strip_html(s: str) -> str:
    import re

    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()
