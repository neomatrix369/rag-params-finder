import importlib.metadata
import time

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from cli.api_client import get_experiment, submit_experiment
from cli.config_loader import load_config

app = typer.Typer(help="RAG Params Finder CLI")
console = Console()

TERMINAL_PHASES = {"complete", "failed", "interrupted"}
POLL_INTERVAL_S = 2.0


def _build_runs_table(runs: list[dict]) -> Table:
    table = Table(title="Run Status", show_lines=True)
    table.add_column("Run ID", style="dim", max_width=10)
    table.add_column("Model")
    table.add_column("Chunker")
    table.add_column("Size/Overlap")
    table.add_column("Retrieval")
    table.add_column("Phase")

    phase_styles = {
        "complete": "bold green",
        "failed": "bold red",
        "interrupted": "bold yellow",
    }

    for run in runs:
        phase = run.get("phase", "unknown")
        style = phase_styles.get(phase, "cyan")
        table.add_row(
            run.get("run_id", "?")[:8],
            run.get("embedding_model", "?"),
            run.get("chunking_method", "?"),
            f"{run.get('chunk_size', '?')}/{run.get('overlap', '?')}",
            run.get("retrieval_method", "?"),
            f"[{style}]{phase}[/{style}]",
        )
    return table


def _watch_experiment(experiment_id: str) -> None:
    """Poll experiment status and display live table until all runs finish."""
    console.print(f"\n[cyan]Watching experiment {experiment_id[:8]}...[/cyan]\n")

    with Live(console=console, refresh_per_second=1) as live:
        while True:
            try:
                data = get_experiment(experiment_id)
            except Exception as e:
                live.update(f"[red]Poll error: {e}[/red]")
                time.sleep(POLL_INTERVAL_S)
                continue

            runs = data.get("runs", [])
            status = data.get("status", "unknown")

            table = _build_runs_table(runs)
            live.update(table)

            if status in TERMINAL_PHASES or status == "partial":
                break

            all_done = runs and all(r.get("phase") in TERMINAL_PHASES for r in runs)
            if all_done:
                break

            time.sleep(POLL_INTERVAL_S)

    console.print(f"\n[bold]Experiment finished: {status}[/bold]")


@app.command()
def run(
    config: str = typer.Option(..., "--config", help="Path to experiment YAML config"),
    detach: bool = typer.Option(False, "--detach", help="Submit and exit without watching"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Poll and display live status"),
):
    """Submit an experiment to the server."""
    console.print(f"[cyan]Loading config from {config}...[/cyan]")

    try:
        config_data = load_config(config)

        console.print("[cyan]Submitting experiment to server...[/cyan]")
        response = submit_experiment(config_data)

        run_count = response.get("run_count", "?")
        console.print(Panel.fit(
            f"[green]✓[/green] Experiment submitted: {response['experiment_name']}\n"
            f"Runs: {run_count}\n"
            f"Status: {response['status']}",
            title="Submitted",
            border_style="green",
        ))

        if detach:
            console.print("Detached. Check dashboard at http://localhost:5173")
            return

        if not watch:
            console.print("Check dashboard at http://localhost:5173 for progress")
            return

        experiment_id = response.get("experiment_id")
        if not experiment_id:
            console.print("[yellow]Server did not return experiment_id — cannot watch.[/yellow]")
            console.print("Check dashboard at http://localhost:5173")
            return

        _watch_experiment(experiment_id)

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to submit experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Print the installed package version."""
    console.print(importlib.metadata.version("rag-params-finder"))


if __name__ == "__main__":
    app()
