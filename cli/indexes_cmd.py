"""CLI commands for search-index management (Atlas Search or Postgres catalog)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from cli.api_client import get_stores
from server.db.mongo.atlas import get_database
from server.db.mongo.indexes import (
    ensure_indexes,
    list_cluster_search_indexes,
    prune_unknown_search_indexes,
    reset_chunks_search_indexes,
)
from server.db.ports.registry import is_same_adapter
from server.settings import normalize_storage_backend, settings
from server.utils.logger import get_logger

indexes_app = typer.Typer(help="Manage search indexes on the connected storage backend")
console = Console()
logger = get_logger(__name__)


def _print_store_index_summary(store: dict[str, object]) -> None:
    """Render the active store's mapping summary from GET /api/stores."""
    provider = str(store.get("provider") or "")
    labels = store.get("labels")
    index_label = "Index"
    if isinstance(labels, dict):
        index_label = str(labels.get("index") or index_label)
    summary = store.get("index_summary")
    table = Table(title=f"{provider} {index_label} summary", show_lines=True)
    table.add_column("Field")
    table.add_column("Value")
    if isinstance(summary, dict):
        for key, value in summary.items():
            if isinstance(value, list):
                rendered = ", ".join(str(item) for item in value)
            else:
                rendered = str(value)
            table.add_row(key, rendered)
    console.print(table)


@indexes_app.command("list")
def indexes_list() -> None:
    """List the active vector store's index summary via GET /api/stores."""
    catalog = get_stores()
    active = str(catalog.get("active") or "")
    stores = catalog.get("stores")
    if not isinstance(stores, list):
        console.print("[yellow]Store catalog did not include a stores list.[/yellow]")
        raise typer.Exit(1)
    current = next(
        (row for row in stores if isinstance(row, dict) and row.get("provider") == active),
        None,
    )
    if not isinstance(current, dict):
        console.print(f"[yellow]No catalog entry for active store {active!r}.[/yellow]")
        raise typer.Exit(1)
    _print_store_index_summary(current)


@indexes_app.command("reset")
def indexes_reset(
    unknown_only: bool = typer.Option(
        True,
        "--unknown-only/--all",
        help="Drop only unknown indexes (default) or all indexes on chunks and recreate",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Drop search indexes and recreate required ones on chunks (Mongo/Atlas only)."""
    backend = normalize_storage_backend(settings.storage_backend)
    if is_same_adapter(backend, "postgres"):
        console.print(
            "[yellow]indexes reset[/yellow] is Atlas-only. "
            "Postgres indexes are created by schema.sql at server bootstrap — "
            "restart the server or re-run pool init; then `indexes list` to verify."
        )
        raise typer.Exit(0)
    if not is_same_adapter(backend, "mongodb"):
        console.print(
            f"[yellow]indexes reset[/yellow] unsupported for STORAGE_BACKEND={backend!r}."
        )
        raise typer.Exit(0)

    rows = list_cluster_search_indexes()
    unknown = [row for row in rows if not row["known"]]

    if unknown_only:
        if not unknown:
            console.print("[green]No unknown search indexes to drop.[/green]")
            console.print("[cyan]Ensuring required indexes on chunks...[/cyan]")
            ensure_indexes()
            console.print("[green]Done.[/green]")
            return

        lines = ["Will drop unknown search indexes:"]
        for row in unknown:
            lines.append(f"  • {row['database']}.{row['collection']} → {row['name']}")
        lines.append("")
        lines.append("Then ensure required indexes exist on chunks.")
        console.print("\n".join(lines))

        if not force and not typer.confirm("Continue?"):
            console.print("[dim]Reset cancelled[/dim]")
            raise typer.Exit(0)

        dropped = prune_unknown_search_indexes()
        ensure_indexes()
        logger.info("indexes reset (unknown-only) — dropped=%s", dropped)
        console.print(
            f"[green]Dropped {len(dropped)} unknown index(es). Required indexes ensured.[/green]"
        )
        return

    db_name = get_database().name
    chunks_rows = [
        row for row in rows if row["database"] == db_name and row["collection"] == "chunks"
    ]

    if chunks_rows:
        console.print(
            "[yellow]Warning:[/yellow] This drops ALL search indexes on "
            f"[bold]{db_name}.chunks[/bold] and recreates them.\n"
            "Queries will fail until indexes rebuild (~1–2 min).\n"
            "Chunk documents and embeddings are [bold]not[/bold] deleted."
        )
        for row in chunks_rows:
            console.print(f"  • {row['name']} ({row['index_type']}, {row['status']})")
    else:
        console.print(
            f"[dim]No search indexes on {db_name}.chunks — will create required indexes.[/dim]"
        )

    if not force and not typer.confirm("Continue?"):
        console.print("[dim]Reset cancelled[/dim]")
        raise typer.Exit(0)

    reset_chunks_search_indexes()
    logger.info("indexes reset (all on chunks) — database=%s", db_name)
    console.print("[green]Chunks search indexes reset and recreated.[/green]")
