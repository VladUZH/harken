"""FastAPI app serving the dashboard + a small JSON API over the store."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from harken.models import Sentiment
from harken.store import Store

_HERE = Path(__file__).parent


def create_app(db_path: str = "harken.db") -> FastAPI:
    app = FastAPI(title="Harken", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_HERE / "templates"))
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
            mentions = db.mentions(query=query, limit=100) if query else []
            themes = _themes_from(mentions)
            return templates.TemplateResponse(
                request,
                "dashboard.html",
                {
                    "queries": queries,
                    "query": query,
                    "summary": summary,
                    "mentions": mentions,
                    "themes": themes,
                    "max_day": max(summary["by_day"].values(), default=0),
                },
            )
        finally:
            db.close()

    @app.get("/api/mentions")
    def api_mentions(
        q: str | None = None,
        source: str | None = None,
        sentiment: str | None = None,
        limit: int = Query(100, le=1000),
    ):
        db = store()
        try:
            sent = Sentiment(sentiment) if sentiment in {s.value for s in Sentiment} else None
            rows = db.mentions(query=q, source=source, sentiment=sent, limit=limit)
            return JSONResponse([_mention_json(m) for m in rows])
        finally:
            db.close()

    @app.get("/api/summary")
    def api_summary(q: str | None = None):
        db = store()
        try:
            return JSONResponse(db.summary(query=q))
        finally:
            db.close()

    return app


def _themes_from(mentions):
    from collections import Counter
    c = Counter(m.theme for m in mentions if m.theme)
    return [{"label": label, "count": n} for label, n in c.most_common(8)]


def _mention_json(m):
    return {
        "id": m.id,
        "source": m.source,
        "author": m.author,
        "title": m.title,
        "text": m.text,
        "url": m.url,
        "created_at": m.created_at.isoformat(),
        "score": m.score,
        "sentiment": m.sentiment.value if m.sentiment else None,
        "sentiment_score": m.sentiment_score,
        "theme": m.theme,
    }
