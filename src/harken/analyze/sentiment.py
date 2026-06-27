"""Lexicon-based sentiment analysis — no API key, no model download, no network.

This is intentionally simple and transparent: a curated valence lexicon plus
negation and intensifier handling, scored VADER-style and normalised to roughly
[-1, 1]. It will never beat an LLM, but it runs instantly on a clean clone and
makes the zero-config demo honest. Plug an LLM analyzer in front of it for
better results (see :mod:`harken.analyze.pipeline_analyzer`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from harken.models import Sentiment

# --- Curated valence lexicon -------------------------------------------------
# Hand-built (MIT-clean, no third-party data licence). Values are signed
# valence in roughly [-3, 3]. Not exhaustive — covers common product / social
# sentiment vocabulary. Contributions welcome.
_LEXICON: dict[str, float] = {
    # strong positive
    "amazing": 3, "awesome": 3, "excellent": 3, "fantastic": 3, "incredible": 3,
    "love": 3, "loved": 3, "perfect": 3, "brilliant": 3, "outstanding": 3,
    "wonderful": 3, "superb": 3, "delightful": 3, "phenomenal": 3, "gem": 3,
    # positive
    "good": 2, "great": 2, "nice": 2, "helpful": 2, "useful": 2, "solid": 2,
    "clean": 2, "fast": 2, "smooth": 2, "happy": 2, "glad": 2, "impressed": 2,
    "impressive": 2, "reliable": 2, "intuitive": 2, "elegant": 2, "polished": 2,
    "recommend": 2, "recommended": 2, "works": 1.5, "working": 1.5, "thanks": 2,
    "thank": 2, "appreciate": 2, "win": 2, "winning": 2, "best": 2.5, "like": 1.5,
    "liked": 1.5, "enjoy": 2, "enjoyed": 2, "cool": 1.5, "neat": 1.5, "yay": 2,
    "kudos": 2, "promising": 1.5, "slick": 2, "lightweight": 1.5, "free": 1,
    # mild positive
    "ok": 0.5, "okay": 0.5, "fine": 0.5, "decent": 1, "better": 1, "improved": 1.5,
    # negative
    "bad": -2, "poor": -2, "slow": -2, "buggy": -2.5, "bug": -1.5, "broken": -2.5,
    "broke": -2, "crash": -2.5, "crashes": -2.5, "crashed": -2.5, "fail": -2,
    "failed": -2, "failing": -2, "error": -1.5, "errors": -1.5, "issue": -1,
    "issues": -1, "problem": -1.5, "problems": -1.5, "annoying": -2, "frustrating": -2.5,
    "frustrated": -2.5, "confusing": -2, "confused": -1.5, "disappointing": -2.5,
    "disappointed": -2.5, "useless": -3, "worthless": -3, "garbage": -3, "trash": -3,
    "horrible": -3, "terrible": -3, "awful": -3, "hate": -3, "hated": -3,
    "worst": -3, "sucks": -2.5, "suck": -2.5, "painful": -2, "clunky": -2,
    "bloated": -2, "expensive": -1.5, "overpriced": -2, "scam": -3, "spam": -2,
    "lacking": -1.5, "missing": -1, "unreliable": -2.5, "insecure": -2,
    "vulnerable": -1.5, "regret": -2.5, "meh": -1, "disaster": -3, "nightmare": -3,
    "concerned": -1.5, "concern": -1.5, "worried": -1.5, "ugly": -2,
}

_INTENSIFIERS: dict[str, float] = {
    "very": 1.4, "really": 1.4, "absolutely": 1.6, "extremely": 1.7, "so": 1.3,
    "super": 1.5, "incredibly": 1.6, "totally": 1.4, "completely": 1.4,
    "highly": 1.4, "insanely": 1.6, "ridiculously": 1.5, "remarkably": 1.4,
}
_DAMPENERS: dict[str, float] = {
    "slightly": 0.6, "somewhat": 0.7, "kinda": 0.7, "barely": 0.5, "a": 1.0,
    "bit": 0.7, "little": 0.7,
}
_NEGATORS = {
    "not", "no", "never", "n't", "cannot", "cant", "can't", "without",
    "hardly", "neither", "nor", "isnt", "isn't", "wasnt", "wasn't", "dont",
    "don't", "doesnt", "doesn't", "didnt", "didn't",
}

_POSITIVE_EMOJI = "🎉🚀😀😃😄😁😊🙂👍❤️💜✨🔥💯🥳😍🤩👏"
_NEGATIVE_EMOJI = "😞😢😭😠😡👎💩😤🤬😩😖💔🙄😒"

_TOKEN_RE = re.compile(r"[a-zA-Z']+")


@dataclass
class SentimentResult:
    label: Sentiment
    score: float  # signed, roughly [-1, 1]


class LexiconSentiment:
    """Rule-based sentiment scorer. Stateless and thread-safe."""

    name = "lexicon"

    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold

    def score(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            return SentimentResult(Sentiment.NEUTRAL, 0.0)

        tokens = _TOKEN_RE.findall(text.lower())
        total = 0.0
        hits = 0
        for i, tok in enumerate(tokens):
            val = _LEXICON.get(tok)
            if val is None:
                continue
            hits += 1
            # look back up to 3 tokens for negators / intensifiers
            mult = 1.0
            negated = False
            for prev in tokens[max(0, i - 3):i]:
                if prev in _NEGATORS:
                    negated = True
                if prev in _INTENSIFIERS:
                    mult *= _INTENSIFIERS[prev]
                if prev in _DAMPENERS:
                    mult *= _DAMPENERS[prev]
            v = val * mult
            if negated:
                v = -v * 0.85  # negation flips and slightly dampens
            total += v

        # emoji contribute directly
        for ch in text:
            if ch in _POSITIVE_EMOJI:
                total += 2
                hits += 1
            elif ch in _NEGATIVE_EMOJI:
                total -= 2
                hits += 1

        if hits == 0:
            return SentimentResult(Sentiment.NEUTRAL, 0.0)

        # VADER-style normalisation: squash unbounded sum into (-1, 1)
        norm = total / (total * total + 4) ** 0.5

        if norm >= self.threshold:
            label = Sentiment.POSITIVE
        elif norm <= -self.threshold:
            label = Sentiment.NEGATIVE
        else:
            label = Sentiment.NEUTRAL
        return SentimentResult(label, round(norm, 4))
