"""FastAPI app serving the dashboard + a small JSON API over the store."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from harken.models import Mention, Sentiment
from harken.store import Store

_HERE = Path(__file__).parent

# Per-source display metadata: a short glyph badge + accent colour, kept offline
# (no icon fonts / CDNs). Matches the product's "no telemetry" premise.
SOURCE_META = {
    "hackernews": {"label": "Hacker News", "glyph": "Y", "color": "#ff6a3d"},
    "reddit": {"label": "Reddit", "glyph": "r/", "color": "#ff4f3f"},
    "mastodon": {"label": "Mastodon", "glyph": "@", "color": "#7c7fff"},
    "bluesky": {"label": "Bluesky", "glyph": "◈", "color": "#3aa8ff"},
    "rss": {"label": "RSS", "glyph": "∿", "color": "#e0a23a"},
}


def create_app(db_path: str = "harken.db") -> FastAPI:
    app = FastAPI(title="Harken", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_HERE / "templates"))
    templates.env.filters["reltime"] = _reltime
    app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

    def store() -> Store:
        return Store(db_path)

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, q: str | None = None):
        db = store()
        try:
            queries = db.queries()
            query = q or (queries[0] if queries else None)
            summary = db.summary(query=query) if query else {
                "total": 0, "by_sentiment": {}, "by_source": {}, "by_day": {}
            }
            mentions = db.mentions(query=query, limit=200) if query else []
            timeseries = db.timeseries(query=query) if query else []
            themes = _themes_from(mentions)
            bs = summary["by_sentiment"]
            ctx = {
                "queries": queries,
                "query": query,
                "summary": summary,
                "mentions": [_view(m) for m in mentions],
                "themes": themes,
                "timeseries": timeseries,
                "max_day": max((d["total"] for d in timeseries), default=0),
                "pos": bs.get("positive", 0),
                "neu": bs.get("neutral", 0),
                "neg": bs.get("negative", 0),
                "net": db.net_sentiment(query=query) if query else 0.0,
                "top_theme": themes[0]["label"] if themes else None,
                "source_meta": SOURCE_META,
            }
            return templates.TemplateResponse(request, "dashboard.html", ctx)
        finally:
            db.close()

    @app.get("/api/mentions")
    def api_mentions(
        q: str | None = None,
        source: str | None = None,
        sentiment: str | None = None,
        limit: int = Query(200, le=1000),
    ):
        db = store()
        try:
            sent = Sentiment(sentiment) if sentiment in {s.value for s in Sentiment} else None
            rows = db.mentions(query=q, source=source, sentiment=sent, limit=limit)
            return JSONResponse([_view(m) for m in rows])
        finally:
            db.close()

    @app.get("/api/summary")
    def api_summary(q: str | None = None):
        db = store()
        try:
            return JSONResponse({
                "summary": db.summary(query=q),
                "timeseries": db.timeseries(query=q),
                "net": db.net_sentiment(query=q),
            })
        finally:
            db.close()

    return app


def _themes_from(mentions):
    from collections import Counter
    c = Counter(m.theme for m in mentions if m.theme)
    return [{"label": label, "count": n} for label, n in c.most_common(8)]


def _view(m: Mention) -> dict:
    meta = SOURCE_META.get(m.source, {"label": m.source, "glyph": "•", "color": "#8b93a1"})
    return {
        "id": m.id,
        "source": m.source,
        "source_label": meta["label"],
        "source_glyph": meta["glyph"],
        "source_color": meta["color"],
        "author": m.author,
        "title": m.title,
        "text": m.text,
        "url": m.url,
        "created_at": m.created_at.isoformat(),
        "reltime": _reltime(m.created_at),
        "score": m.score,
        "sentiment": m.sentiment.value if m.sentiment else "neutral",
        "sentiment_score": m.sentiment_score,
        "theme": m.theme,
    }


def _reltime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "now"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}h"
    days = hrs // 24
    if days < 7:
        return f"{days}d"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w"
    return f"{days // 30}mo"
