"""Tests for no-API-key theme extraction."""

from datetime import datetime, timezone

from harken.analyze.insights import ThemeExtractor
from harken.models import Mention


def m(text: str, title: str | None = None) -> Mention:
    return Mention(
        source="test",
        query="acme",
        title=title,
        text=text,
        created_at=datetime.now(timezone.utc),
    )


def test_extracts_distinct_themes():
    mentions = [
        m("The pricing is too expensive for small teams, pricing needs work"),
        m("Pricing model is confusing and expensive"),
        m("The new dashboard performance is fast and snappy"),
        m("Dashboard performance improved a lot, very fast now"),
        m("Love the dark mode in the dashboard"),
    ]
    extractor = ThemeExtractor(max_themes=4)
    themes = extractor.extract(mentions)
    assert len(themes) >= 2
    labels = " ".join(t.label.lower() for t in themes)
    # the two dominant topics should surface
    assert "pricing" in labels or "expensive" in labels
    assert "dashboard" in labels or "performance" in labels


def test_assigns_mentions_to_themes():
    mentions = [
        m("pricing is expensive"),
        m("pricing too high"),
        m("the api docs are great"),
        m("api documentation is excellent"),
    ]
    extractor = ThemeExtractor(max_themes=3)
    themes = extractor.extract(mentions)
    # every theme has at least one mention assigned
    assert all(t.count >= 1 for t in themes)
    # mentions got a theme label written back
    assert any(mn.theme for mn in mentions)


def test_handles_empty():
    extractor = ThemeExtractor()
    assert extractor.extract([]) == []


def test_ignores_stopwords_and_query_term():
    mentions = [m("acme is the the the best with and for")] * 3
    extractor = ThemeExtractor()
    themes = extractor.extract(mentions)
    for t in themes:
        assert "the" not in t.terms
        assert "acme" not in t.terms  # the tracked term itself is not a theme
