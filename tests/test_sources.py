"""Source adapter tests — HTTP is mocked, so these run offline and deterministically."""

import httpx
import respx

from harken.sources.bluesky import BlueskySource
from harken.sources.hackernews import HackerNewsSource
from harken.sources.reddit import RedditSource


@respx.mock
def test_hackernews_parses_hits():
    payload = {
        "hits": [
            {
                "objectID": "111",
                "title": "Acme is great",
                "author": "alice",
                "points": 42,
                "created_at_i": 1_700_000_000,
            },
            {
                "objectID": "222",
                "comment_text": "I tried <b>Acme</b> and it&#x27;s fast",
                "story_title": "Show HN: Acme",
                "author": "bob",
                "created_at_i": 1_700_000_500,
            },
        ]
    }
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json=payload)
    )
    out = HackerNewsSource().fetch("acme", limit=10)
    assert len(out) == 2
    assert out[0].source == "hackernews"
    assert out[0].author == "alice"
    assert out[0].url == "https://news.ycombinator.com/item?id=111"
    # html stripped + entities decoded
    assert "fast" in out[1].text
    assert "<b>" not in out[1].text
    assert "it's" in out[1].text


@respx.mock
def test_reddit_parses_children():
    payload = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Thoughts on Acme?",
                        "selftext": "is it any good",
                        "author": "carol",
                        "score": 7,
                        "permalink": "/r/test/comments/1/thoughts",
                        "created_utc": 1_700_000_000,
                    }
                }
            ]
        }
    }
    respx.get("https://www.reddit.com/search.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    out = RedditSource().fetch("acme")
    assert len(out) == 1
    assert out[0].source == "reddit"
    assert out[0].url == "https://www.reddit.com/r/test/comments/1/thoughts"
    assert out[0].score == 7


@respx.mock
def test_bluesky_parses_posts():
    payload = {
        "posts": [
            {
                "uri": "at://did:plc:abc/app.bsky.feed.post/xyz",
                "author": {"handle": "dave.bsky.social"},
                "record": {"text": "acme rocks", "createdAt": "2026-06-01T12:00:00Z"},
                "likeCount": 3,
            }
        ]
    }
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts").mock(
        return_value=httpx.Response(200, json=payload)
    )
    out = BlueskySource().fetch("acme")
    assert len(out) == 1
    assert out[0].author == "dave.bsky.social"
    assert out[0].url == "https://bsky.app/profile/dave.bsky.social/post/xyz"


def test_mention_id_is_stable_and_dedupes():
    from datetime import datetime, timezone

    from harken.models import Mention

    kw = dict(source="hackernews", query="acme", created_at=datetime.now(timezone.utc))
    a = Mention(url="https://x/1", text="hello", **kw)
    b = Mention(url="https://x/1", text="hello", **kw)
    c = Mention(url="https://x/2", text="hello", **kw)
    assert a.id == b.id  # same url -> same id
    assert a.id != c.id
