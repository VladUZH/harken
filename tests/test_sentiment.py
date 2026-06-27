"""Tests for the no-API-key lexicon sentiment analyzer."""

from harken.analyze.sentiment import LexiconSentiment
from harken.models import Sentiment


def make():
    return LexiconSentiment()


def test_clearly_positive():
    a = make()
    r = a.score("This tool is absolutely fantastic, I love it!")
    assert r.label is Sentiment.POSITIVE
    assert r.score > 0.2


def test_clearly_negative():
    a = make()
    r = a.score("Honestly terrible experience, buggy and frustrating. I hate it.")
    assert r.label is Sentiment.NEGATIVE
    assert r.score < -0.2


def test_neutral_factual():
    a = make()
    r = a.score("The release ships on Tuesday and supports SQLite.")
    assert r.label is Sentiment.NEUTRAL


def test_negation_flips_positive():
    a = make()
    pos = a.score("This is good.")
    neg = a.score("This is not good.")
    assert pos.score > 0
    assert neg.score < pos.score  # negation pulls it down / negative


def test_intensifier_amplifies():
    a = make()
    plain = a.score("good")
    strong = a.score("very good")
    assert strong.score > plain.score


def test_empty_is_neutral():
    a = make()
    r = a.score("")
    assert r.label is Sentiment.NEUTRAL
    assert r.score == 0.0


def test_emoji_positive():
    a = make()
    r = a.score("shipped it 🎉🚀")
    assert r.score > 0
