"""SQLite persistence. One file, no server, your data stays on your box.

The store is deliberately tiny: upsert mentions (de-duplicated by content id),
query them back with filters, and compute the aggregates the dashboard needs.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from harken.models import Mention, Sentiment

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    query         TEXT NOT NULL,
    author        TEXT,
    title         TEXT,
    text          TEXT,
    url           TEXT,
    created_at    TEXT NOT NULL,
    score         INTEGER,
    sentiment     TEXT,
    sentiment_score REAL,
    theme         TEXT,
    fetched_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_query ON mentions(query);
CREATE INDEX IF NOT EXISTS idx_created ON mentions(created_at);
"""


class Store:
    def __init__(self, path: str | Path = "harken.db"):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        with closing(self._conn.cursor()) as cur:
            cur.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- writes --------------------------------------------------------------
    def upsert(self, mentions: list[Mention]) -> int:
        """Insert or replace mentions. Returns count of *new* rows."""
        now = datetime.now(timezone.utc).isoformat()
        new = 0
        with closing(self._conn.cursor()) as cur:
            for m in mentions:
                cur.execute("SELECT 1 FROM mentions WHERE id = ?", (m.id,))
                existed = cur.fetchone() is not None
                cur.execute(
                    """
                    INSERT INTO mentions
                        (id, source, query, author, title, text, url, created_at,
                         score, sentiment, sentiment_score, theme, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET
                        sentiment=excluded.sentiment,
                        sentiment_score=excluded.sentiment_score,
                        theme=excluded.theme,
                        score=excluded.score
                    """,
                    (
                        m.id, m.source, m.query, m.author, m.title, m.text, m.url,
                        m.created_at.isoformat(), m.score,
                        m.sentiment.value if m.sentiment else None,
                        m.sentiment_score, m.theme, now,
                    ),
                )
                if not existed:
                    new += 1
        self._conn.commit()
        return new

    # -- reads ---------------------------------------------------------------
    def mentions(
        self,
        query: str | None = None,
        source: str | None = None,
        sentiment: Sentiment | None = None,
        limit: int = 500,
    ) -> list[Mention]:
        sql = "SELECT * FROM mentions WHERE 1=1"
        args: list = []
        if query:
            sql += " AND query = ?"
            args.append(query)
        if source:
            sql += " AND source = ?"
            args.append(source)
        if sentiment:
            sql += " AND sentiment = ?"
            args.append(sentiment.value)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with closing(self._conn.cursor()) as cur:
            cur.execute(sql, args)
            return [_row_to_mention(r) for r in cur.fetchall()]

    def queries(self) -> list[str]:
        with closing(self._conn.cursor()) as cur:
            cur.execute("SELECT DISTINCT query FROM mentions ORDER BY query")
            return [r["query"] for r in cur.fetchall()]

    def summary(self, query: str | None = None) -> dict:
        ms = self.mentions(query=query, limit=100_000)
        by_sentiment = Counter(m.sentiment.value if m.sentiment else "unscored" for m in ms)
        by_source = Counter(m.source for m in ms)
        by_day: Counter[str] = Counter(m.created_at.date().isoformat() for m in ms)
        return {
            "total": len(ms),
            "by_sentiment": dict(by_sentiment),
            "by_source": dict(by_source),
            "by_day": dict(sorted(by_day.items())),
        }


def _row_to_mention(r: sqlite3.Row) -> Mention:
    return Mention(
        id=r["id"],
        source=r["source"],
        query=r["query"],
        author=r["author"],
        title=r["title"],
        text=r["text"] or "",
        url=r["url"],
        created_at=datetime.fromisoformat(r["created_at"]),
        score=r["score"],
        sentiment=Sentiment(r["sentiment"]) if r["sentiment"] else None,
        sentiment_score=r["sentiment_score"],
        theme=r["theme"],
    )
