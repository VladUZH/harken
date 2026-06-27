"""The pipeline: fetch → analyze → store. The one core job, done well.

A single source failing (rate limit, network) never sinks the run — its error is
collected and reported, and the other sources still land.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from harken.analyze.insights import Theme, ThemeExtractor
from harken.analyze.sentiment import LexiconSentiment
from harken.config import Config
from harken.llm import get_provider
from harken.models import Mention
from harken.sources import REGISTRY
from harken.store import Store


@dataclass
class TrackResult:
    query: str
    fetched: int = 0
    new: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    themes: list[Theme] = field(default_factory=list)


class Pipeline:
    def __init__(self, config: Config | None = None, store: Store | None = None):
        self.config = config or Config()
        self.store = store or Store(self.config.db_path)
        self.sentiment = LexiconSentiment()
        self.themes = ThemeExtractor()

    def close(self) -> None:
        self.store.close()

    # -- ingest --------------------------------------------------------------
    def track(self, query: str) -> TrackResult:
        result = TrackResult(query=query)
        collected: list[Mention] = []

        for name in self.config.sources:
            source_cls = REGISTRY.get(name)
            if source_cls is None:
                result.errors[name] = "unknown source"
                continue
            try:
                source = source_cls(**self.config.source_options(name))
                mentions = source.fetch(query, limit=self.config.per_source_limit)
                collected.extend(mentions)
                result.by_source[name] = len(mentions)
            except Exception as e:  # isolate per-source failures
                result.errors[name] = f"{type(e).__name__}: {e}"

        # analyze sentiment on everything we collected
        for m in collected:
            r = self.sentiment.score(m.content)
            m.sentiment, m.sentiment_score = r.label, r.score

        result.fetched = len(collected)
        result.new = self.store.upsert(collected)

        # cluster themes over the full stored set for this query, then persist labels
        stored = self.store.mentions(query=query, limit=100_000)
        themes = self.themes.extract(stored)
        self._maybe_llm_label(themes, stored)
        self.store.upsert(stored)  # write theme labels back
        result.themes = themes
        return result

    # -- optional LLM theme labelling ---------------------------------------
    def _maybe_llm_label(self, themes: list[Theme], mentions: list[Mention]) -> None:
        if not themes or self.config.llm_provider in ("", "none", "null"):
            return
        try:
            provider = get_provider(self.config.llm_provider)
            if not getattr(provider, "available", False):
                return
            by_label = {t.label: t for t in themes}
            samples = {
                t.label: [m.content[:160] for m in mentions if m.theme == t.label][:3]
                for t in themes
            }
            prompt = (
                "Give each cluster a short human-readable theme name (2-4 words). "
                "Return JSON mapping the original label to the new name.\n\n"
                + json.dumps(samples, ensure_ascii=False)
            )
            raw = provider.complete(
                prompt,
                system="You label clusters of product-related social mentions. Output JSON only.",
                max_tokens=400,
            )
            mapping = _parse_json(raw)
            for old, new in (mapping or {}).items():
                if old in by_label and isinstance(new, str) and new.strip():
                    t = by_label[old]
                    for m in mentions:
                        if m.theme == old:
                            m.theme = new.strip()
                    t.label = new.strip()
        except Exception:
            # LLM labelling is a nice-to-have; never let it break the run
            return


def _parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
