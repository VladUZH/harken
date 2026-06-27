"""SQLite store tests — temp DB, no network."""

from datetime import datetime, timezone

from harken.models import Mention, Sentiment
from harken.store import Store


def mk(text, sentiment=None, source="hackernews", query="acme", url=None):
    return Mention(
        source=source,
        query=query,
        text=text,
        url=url,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        sentiment=sentiment,
    )


def test_upsert_and_dedupe(tmp_path):
    db = Store(tmp_path / "t.db")
    new1 = db.upsert([mk("hello", url="https://x/1"), mk("world", url="https://x/2")])
    assert new1 == 2
    # re-inserting the same urls adds no new rows
    new2 = db.upsert([mk("hello", url="https://x/1")])
    assert new2 == 0
    assert len(db.mentions(query="acme")) == 2
    db.close()


def test_upsert_updates_sentiment(tmp_path):
    db = Store(tmp_path / "t.db")
    db.upsert([mk("buggy", url="https://x/1")])
    db.upsert([mk("buggy", url="https://x/1", sentiment=Sentiment.NEGATIVE)])
    got = db.mentions(query="acme")[0]
    assert got.sentiment is Sentiment.NEGATIVE
    db.close()


def test_filter_by_sentiment_and_source(tmp_path):
    db = Store(tmp_path / "t.db")
    db.upsert([
        mk("a", url="u1", sentiment=Sentiment.POSITIVE, source="hackernews"),
        mk("b", url="u2", sentiment=Sentiment.NEGATIVE, source="reddit"),
    ])
    assert len(db.mentions(sentiment=Sentiment.POSITIVE)) == 1
    assert db.mentions(source="reddit")[0].text == "b"
    db.close()


def test_summary_aggregates(tmp_path):
    db = Store(tmp_path / "t.db")
    db.upsert([
        mk("a", url="u1", sentiment=Sentiment.POSITIVE),
        mk("b", url="u2", sentiment=Sentiment.POSITIVE),
        mk("c", url="u3", sentiment=Sentiment.NEGATIVE, source="reddit"),
    ])
    s = db.summary(query="acme")
    assert s["total"] == 3
    assert s["by_sentiment"]["positive"] == 2
    assert s["by_source"]["reddit"] == 1
    assert s["by_day"]["2026-06-01"] == 3
    db.close()


def test_timeseries_and_net_sentiment(tmp_path):
    db = Store(tmp_path / "t.db")
    db.upsert([
        mk("a", url="u1", sentiment=Sentiment.POSITIVE),
        mk("b", url="u2", sentiment=Sentiment.POSITIVE),
        mk("c", url="u3", sentiment=Sentiment.NEGATIVE),
        mk("d", url="u4", sentiment=Sentiment.NEUTRAL),
    ])
    ts = db.timeseries(query="acme")
    assert len(ts) == 1
    day = ts[0]
    assert day["date"] == "2026-06-01"
    assert day["positive"] == 2 and day["negative"] == 1 and day["neutral"] == 1
    assert day["total"] == 4
    # net = (2 - 1) / 4 = 0.25
    assert db.net_sentiment(query="acme") == 0.25
    db.close()
