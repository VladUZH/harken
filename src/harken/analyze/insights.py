"""Theme extraction — group mentions into the topics people keep raising.

No API key, no embeddings: a transparent TF-based salient-term extractor that
clusters mentions by their dominant shared terms. Good enough to answer "what
are people actually talking about?" at a glance. An optional LLM pass can relabel
these themes with nicer names (see :meth:`harken.pipeline.Pipeline._maybe_llm_label`).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from harken.models import Mention

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "is", "are", "was",
    "were", "be", "been", "being", "to", "of", "in", "on", "for", "with",
    "at", "by", "from", "as", "into", "about", "it", "its", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "them", "my",
    "your", "our", "their", "me", "us", "so", "just", "very", "really", "not",
    "no", "yes", "can", "will", "would", "should", "could", "do", "does",
    "did", "have", "has", "had", "get", "got", "im", "ive", "id", "youre",
    "dont", "doesnt", "didnt", "isnt", "wasnt", "arent", "thats", "whats",
    "there", "here", "what", "which", "who", "when", "where", "why", "how",
    "all", "any", "some", "more", "most", "much", "many", "one", "two", "up",
    "out", "down", "over", "than", "too", "also", "like", "use", "using",
    "used", "still", "even", "now", "new", "make", "makes", "made", "via",
    "after", "before", "while", "because", "http", "https",
    "com", "www", "amp",
}

_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9'+-]{1,}")


@dataclass
class Theme:
    label: str
    terms: list[str]
    count: int = 0
    mention_ids: list[str] = field(default_factory=list)


def _tokens(text: str, extra_stop: set[str]) -> list[str]:
    out = []
    for t in _TOKEN_RE.findall(text.lower()):
        t = t.split("'")[0].strip("-+")  # normalise possessives/contractions: quill's -> quill
        if len(t) < 3 or t in _STOPWORDS or t in extra_stop or t.isdigit():
            continue
        out.append(t)
    return out


class ThemeExtractor:
    """Cluster mentions into themes by shared salient terms."""

    name = "tf-themes"

    def __init__(self, max_themes: int = 6, min_cluster: int = 1):
        self.max_themes = max_themes
        self.min_cluster = min_cluster

    def extract(self, mentions: list[Mention]) -> list[Theme]:
        if not mentions:
            return []

        # the tracked query terms should not themselves become themes
        extra_stop = set()
        for mn in mentions:
            for w in _TOKEN_RE.findall(mn.query.lower()):
                extra_stop.add(w)

        # document frequency of each term
        df: Counter[str] = Counter()
        per_mention: dict[str, set[str]] = {}
        for mn in mentions:
            toks = set(_tokens(mn.content, extra_stop))
            per_mention[mn.id] = toks
            df.update(toks)

        # candidate theme seeds = most common meaningful terms (df >= 2 if we can)
        common = [t for t, c in df.most_common() if c >= 2]
        if not common:
            common = [t for t, _ in df.most_common()]
        seeds = common[: self.max_themes]
        if not seeds:
            return []

        themes: list[Theme] = []
        claimed: set[str] = set()
        for seed in seeds:
            members = [
                mn for mn in mentions
                if mn.id not in claimed and seed in per_mention[mn.id]
            ]
            if len(members) < self.min_cluster:
                continue
            # enrich the label with the next most co-occurring term
            co: Counter[str] = Counter()
            for mn in members:
                co.update(per_mention[mn.id])
            co.pop(seed, None)
            terms = [seed] + [t for t, _ in co.most_common(2)]
            label = " / ".join(terms[:2]) if len(terms) > 1 else seed
            theme = Theme(
                label=label,
                terms=terms,
                count=len(members),
                mention_ids=[mn.id for mn in members],
            )
            for mn in members:
                mn.theme = label
                claimed.add(mn.id)
            themes.append(theme)

        themes.sort(key=lambda t: t.count, reverse=True)
        return themes
