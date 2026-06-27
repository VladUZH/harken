"""Harken command-line interface."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from harken import __version__
from harken.analyze.insights import ThemeExtractor
from harken.analyze.sentiment import LexiconSentiment
from harken.config import Config
from harken.models import Sentiment
from harken.pipeline import Pipeline
from harken.sample_data import DEMO_QUERY, sample_mentions
from harken.sources import DEFAULT_SOURCES, REGISTRY
from harken.store import Store

app = typer.Typer(
    help="Harken — self-hosted social listening. Hear what the internet says about you.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

DEMO_DB = "harken-demo.db"


def _version(value: bool):
    if value:
        console.print(f"harken {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _v: bool = typer.Option(False, "--version", callback=_version, is_eager=True, help="Show version."),
):
    pass


@app.command()
def demo(
    serve: bool = typer.Option(True, help="Launch the web dashboard after loading."),
    port: int = typer.Option(8042, help="Port for the dashboard."),
):
    """Load a bundled sample dataset and show the full pipeline — zero config, no keys."""
    console.print(Panel.fit(
        "[bold]Harken demo[/bold]\nLoading a bundled [italic]sample[/italic] dataset (synthetic, not real posts)\n"
        "and running the real pipeline: aggregate → sentiment → themes.",
        border_style="cyan",
    ))
    store = Store(DEMO_DB)
    mentions = sample_mentions()
    sentiment = LexiconSentiment()
    for m in mentions:
        r = sentiment.score(m.content)
        m.sentiment, m.sentiment_score = r.label, r.score
    store.upsert(mentions)
    stored = store.mentions(query=DEMO_QUERY, limit=10_000)
    ThemeExtractor().extract(stored)  # tags each mention with its theme, in place
    store.upsert(stored)
    _print_report(store, DEMO_QUERY)
    store.close()

    if serve:
        console.print(f"\n[bold cyan]Dashboard →[/bold cyan] http://localhost:{port}\n")
        _serve(DEMO_DB, port)


@app.command()
def track(
    query: str = typer.Argument(..., help="Keyword / brand / product to track."),
    sources: str = typer.Option(None, help="Comma-separated sources (default: hackernews,reddit)."),
    limit: int = typer.Option(50, help="Max items per source."),
    db: str = typer.Option(None, help="Database path (default: harken.db)."),
):
    """Fetch live mentions for a keyword from free sources, analyze, and store them."""
    cfg = Config()
    if sources:
        cfg.sources = [s.strip() for s in sources.split(",") if s.strip()]
    if limit:
        cfg.per_source_limit = limit
    if db:
        cfg.db_path = db

    console.print(f"Listening for [bold]“{query}”[/bold] across: {', '.join(cfg.sources)} …")
    pipe = Pipeline(cfg)
    result = pipe.track(query)

    for src, err in result.errors.items():
        console.print(f"  [yellow]![/yellow] {src}: {err}")
    console.print(
        f"[green]✓[/green] {result.fetched} fetched · [bold]{result.new}[/bold] new · "
        f"{sum(result.by_source.values())} matched"
    )
    _print_report(pipe.store, query)
    pipe.close()
    console.print(f"\nView the dashboard: [cyan]harken serve --db {cfg.db_path}[/cyan]")


@app.command()
def report(
    query: str = typer.Argument(None, help="Keyword to report on (default: most recent)."),
    db: str = typer.Option("harken.db", help="Database path."),
):
    """Print a sentiment + theme report for a tracked keyword."""
    store = Store(db)
    q = query or (store.queries()[0] if store.queries() else None)
    if not q:
        console.print("[yellow]No data yet. Run `harken track \"keyword\"` or `harken demo`.[/yellow]")
        raise typer.Exit(1)
    _print_report(store, q)
    store.close()


@app.command()
def serve(
    db: str = typer.Option("harken.db", help="Database path."),
    port: int = typer.Option(8042, help="Port."),
    host: str = typer.Option("127.0.0.1", help="Bind host."),
):
    """Launch the local web dashboard."""
    console.print(f"[bold cyan]Harken dashboard →[/bold cyan] http://{host}:{port}")
    _serve(db, port, host)


@app.command()
def sources():
    """List available mention sources."""
    table = Table(title="Sources")
    table.add_column("name", style="bold")
    table.add_column("label")
    table.add_column("zero-config", justify="center")
    for name, cls in REGISTRY.items():
        zc = "[green]yes[/green]" if (name in DEFAULT_SOURCES and not cls.needs_config) else "—"
        table.add_row(name, cls.label, zc)
    console.print(table)


# -- helpers -----------------------------------------------------------------
def _serve(db: str, port: int, host: str = "127.0.0.1"):
    import uvicorn

    from harken.web.app import create_app

    uvicorn.run(create_app(db), host=host, port=port, log_level="warning")


def _print_report(store: Store, query: str):
    summary = store.summary(query=query)
    total = summary["total"] or 1
    bs = summary["by_sentiment"]
    pos, neu, neg = bs.get("positive", 0), bs.get("neutral", 0), bs.get("negative", 0)

    table = Table(title=f"“{query}” — {summary['total']} mentions", show_header=False, box=None)
    table.add_column(justify="right", style="bold")
    table.add_column()
    table.add_row("positive", f"[green]{'█' * round(20 * pos / total)}[/green] {pos}")
    table.add_row("neutral", f"[grey50]{'█' * round(20 * neu / total)}[/grey50] {neu}")
    table.add_row("negative", f"[red]{'█' * round(20 * neg / total)}[/red] {neg}")
    table.add_row("sources", ", ".join(f"{k} ({v})" for k, v in summary["by_source"].items()))
    console.print(table)

    mentions = store.mentions(query=query, limit=10_000)
    themes = ThemeExtractor().extract(mentions)
    if themes:
        tt = Table(title="Top themes", show_header=True, box=None)
        tt.add_column("theme", style="yellow")
        tt.add_column("mentions", justify="right")
        for t in themes[:6]:
            tt.add_row(t.label, str(t.count))
        console.print(tt)

    # a couple of representative quotes
    neg_quotes = [m for m in mentions if m.sentiment is Sentiment.NEGATIVE and m.text][:2]
    pos_quotes = [m for m in mentions if m.sentiment is Sentiment.POSITIVE and m.text][:2]
    if pos_quotes or neg_quotes:
        console.print()
        for m in pos_quotes:
            console.print(f"  [green]+[/green] [dim]{m.source}[/dim] {m.text[:120]}")
        for m in neg_quotes:
            console.print(f"  [red]−[/red] [dim]{m.source}[/dim] {m.text[:120]}")


if __name__ == "__main__":
    app()
