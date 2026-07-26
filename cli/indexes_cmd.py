"""CLI commands for search-index management (Atlas Search or Postgres catalog)."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from server.core.search_index_guard import (
    collect_postgres_index_snapshot,
    postgres_vector_extension_present,
)
from server.core.search_index_plan import (
    POSTGRES_REQUIRED_INDEXES,
    POSTGRES_VECTOR_EXTENSION,
    required_postgres_catalog_indexes,
)
from server.db.atlas import get_database
from server.db.indexes import (
    M0_SEARCH_INDEX_LIMIT,
    SearchIndexInfo,
    ensure_indexes,
    list_cluster_search_indexes,
    prune_unknown_search_indexes,
    reset_chunks_search_indexes,
)
from server.settings import normalize_storage_backend, settings
from server.utils.logger import get_logger

indexes_app = typer.Typer(help="Manage search indexes on the connected storage backend")
console = Console()
logger = get_logger(__name__)


def _build_indexes_table(rows: list[SearchIndexInfo]) -> Table:
    table = Table(title="Atlas Search Indexes", show_lines=True)
    table.add_column("Status", max_width=8)
    table.add_column("Database")
    table.add_column("Collection")
    table.add_column("Index")
    table.add_column("Type")
    table.add_column("State")

    for row in rows:
        tag = "[green]KNOWN[/green]" if row["known"] else "[yellow]UNKNOWN[/yellow]"
        table.add_row(
            tag,
            row["database"],
            row["collection"],
            row["name"],
            row["index_type"],
            row["status"],
        )
    return table


def _list_postgres_catalog_indexes() -> None:
    """List required vs present HNSW/GIN indexes from the Postgres catalog."""
    required = required_postgres_catalog_indexes()
    extension_ok = postgres_vector_extension_present()
    snapshot = collect_postgres_index_snapshot(required)
    present = snapshot.chunks_ready
    missing = required - present

    table = Table(title="Postgres Catalog Indexes (chunks)", show_lines=True)
    table.add_column("Status", max_width=10)
    table.add_column("Object")
    table.add_column("Kind")

    ext_tag = "[green]PRESENT[/green]" if extension_ok else "[red]MISSING[/red]"
    table.add_row(ext_tag, POSTGRES_VECTOR_EXTENSION, "extension")
    for name in sorted(POSTGRES_REQUIRED_INDEXES):
        if name in present:
            table.add_row("[green]PRESENT[/green]", name, "index")
        else:
            table.add_row("[red]MISSING[/red]", name, "index")

    console.print(table)
    console.print(
        f"\nExtension vector: {'ok' if extension_ok else 'MISSING'} — "
        f"[green]{len(present)} present[/green], "
        f"[red]{len(missing)} missing[/red] of {len(required)} required indexes"
    )
    if missing or not extension_ok:
        console.print(
            "[yellow]Remediation:[/yellow] re-run schema bootstrap "
            "(restart server / pool init) so schema.sql applies HNSW/GIN indexes."
        )


@indexes_app.command("list")
def indexes_list() -> None:
    """List search indexes for the active storage backend."""
    backend = normalize_storage_backend(settings.storage_backend)
    if backend == "postgres":
        _list_postgres_catalog_indexes()
        return
    if backend != "mongodb":
        console.print(f"[yellow]indexes[/yellow] unsupported for STORAGE_BACKEND={backend!r}.")
        raise typer.Exit(0)

    rows = list_cluster_search_indexes()
    if not rows:
        console.print("[dim]No Atlas Search indexes found on this cluster.[/dim]")
        return

    console.print(_build_indexes_table(rows))
    known_count = sum(1 for row in rows if row["known"])
    unknown_count = len(rows) - known_count
    console.print(
        f"\nTotal: {len(rows)}/{M0_SEARCH_INDEX_LIMIT} (M0 free-tier limit) — "
        f"[green]{known_count} known[/green], "
        f"[yellow]{unknown_count} unknown[/yellow]"
    )


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
    if backend == "postgres":
        console.print(
            "[yellow]indexes reset[/yellow] is Atlas-only. "
            "Postgres indexes are created by schema.sql at server bootstrap — "
            "restart the server or re-run pool init; then `indexes list` to verify."
        )
        raise typer.Exit(0)
    if backend != "mongodb":
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
