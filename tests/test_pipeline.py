"""End-to-end pipeline test with mocked HTTP — fetch → analyze → store."""

import httpx
import respx

from harken.config import Config
from harken.models import Sentiment
from harken.pipeline import Pipeline
from harken.store import Store


@respx.mock
def test_track_fetches_analyzes_and_stores(tmp_path):
    hn = {
        "hits": [
            {"objectID": "1", "title": "Acme is fantastic and fast", "author": "a",
             "points": 10, "created_at_i": 1_700_000_000},
            {"objectID": "2", "title": "Acme is buggy and slow, terrible", "author": "b",
             "points": 2, "created_at_i": 1_700_000_100},
            {"objectID": "3", "comment_text": "Acme pricing is too expensive", "author": "c",
             "story_title": "Acme", "created_at_i": 1_700_000_200},
        ]
    }
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json=hn)
    )

    cfg = Config(db_path=str(tmp_path / "t.db"), sources=["hackernews"])
    pipe = Pipeline(cfg)
    result = pipe.track("acme")

    assert result.fetched == 3
    assert result.new == 3
    assert result.by_source["hackernews"] == 3
    assert not result.errors

    # sentiment was applied
    rows = pipe.store.mentions(query="acme")
    sentiments = {m.sentiment for m in rows}
    assert Sentiment.POSITIVE in sentiments
    assert Sentiment.NEGATIVE in sentiments
    pipe.close()


@respx.mock
def test_track_isolates_source_failure(tmp_path):
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(500)
    )
    cfg = Config(db_path=str(tmp_path / "t.db"), sources=["hackernews"])
    pipe = Pipeline(cfg)
    result = pipe.track("acme")
    assert "hackernews" in result.errors
    assert result.fetched == 0  # run survived the failure
    pipe.close()


def test_unknown_source_is_reported(tmp_path):
    cfg = Config(db_path=str(tmp_path / "t.db"), sources=["nope"])
    pipe = Pipeline(cfg)
    result = pipe.track("acme")
    assert result.errors["nope"] == "unknown source"
    pipe.close()


def test_sample_demo_data_flows_through(tmp_path):
    from harken.analyze.insights import ThemeExtractor
    from harken.analyze.sentiment import LexiconSentiment
    from harken.sample_data import DEMO_QUERY, sample_mentions

    store = Store(tmp_path / "demo.db")
    mentions = sample_mentions()
    sent = LexiconSentiment()
    for m in mentions:
        r = sent.score(m.content)
        m.sentiment = r.label
    store.upsert(mentions)
    stored = store.mentions(query=DEMO_QUERY, limit=1000)
    themes = ThemeExtractor().extract(stored)
    assert len(stored) >= 30
    assert len(themes) >= 3
    summary = store.summary(query=DEMO_QUERY)
    # the sample data is intentionally mixed sentiment
    assert summary["by_sentiment"].get("positive", 0) > 0
    assert summary["by_sentiment"].get("negative", 0) > 0
    store.close()
