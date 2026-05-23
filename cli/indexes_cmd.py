"""CLI commands for Atlas Search index management."""

import typer
from rich.console import Console
from rich.table import Table

from server.db.indexes import (
    M0_SEARCH_INDEX_LIMIT,
    SearchIndexInfo,
    list_cluster_search_indexes,
    prune_unknown_search_indexes,
    reset_chunks_search_indexes,
)
from server.utils.logger import get_logger

indexes_app = typer.Typer(help="Manage Atlas Search indexes on the connected cluster")
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


@indexes_app.command("list")
def indexes_list() -> None:
    """List all Atlas Search indexes on the cluster (known vs unknown)."""
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
    """Drop search indexes and recreate required ones on chunks."""
    rows = list_cluster_search_indexes()
    unknown = [row for row in rows if not row["known"]]

    if unknown_only:
        if not unknown:
            console.print("[green]No unknown search indexes to drop.[/green]")
            console.print("[cyan]Ensuring required indexes on chunks...[/cyan]")
            from server.db.indexes import ensure_indexes

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
        from server.db.indexes import ensure_indexes

        ensure_indexes()
        logger.info("indexes reset (unknown-only) — dropped=%s", dropped)
        console.print(
            f"[green]Dropped {len(dropped)} unknown index(es). Required indexes ensured.[/green]"
        )
        return

    from server.db.atlas import get_database

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
