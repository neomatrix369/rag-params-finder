import importlib.metadata

import typer
from rich.console import Console
from rich.panel import Panel

from cli.api_client import (
    cancel_experiment,
    delete_experiment,
    pause_experiment,
    resume_experiment,
    submit_experiment,
)
from cli.config_loader import load_config
from cli.display import _watch_experiment
from cli.indexes_cmd import indexes_app
from server.utils.logger import get_logger

app = typer.Typer(help="RAG Params Finder CLI")
app.add_typer(indexes_app, name="indexes")
console = Console()
logger = get_logger(__name__)

_DASHBOARD_URL = "http://localhost:5374"


@app.command()
def run(
    config: str = typer.Option(..., "--config", help="Path to experiment YAML config"),
    detach: bool = typer.Option(False, "--detach", help="Submit and exit without watching"),
    watch: bool = typer.Option(True, "--watch/--no-watch", help="Poll and display live status"),
):
    """Submit an experiment to the server."""
    logger.info("run command — config=%s detach=%s watch=%s", config, detach, watch)
    console.print(f"[cyan]Loading config from {config}...[/cyan]")

    try:
        config_data = load_config(config)
        logger.debug("run command — experiment_name=%s", config_data.get("experiment_name"))

        console.print("[cyan]Submitting experiment to server...[/cyan]")
        response = submit_experiment(config_data)

        run_count = response.get("run_count", "?")
        logger.info(
            "submit OK — name=%s runs=%s",
            response.get("experiment_name"),
            run_count,
        )
        console.print(
            Panel.fit(
                f"[green]✓[/green] Experiment submitted: {response['experiment_name']}\n"
                f"Runs: {run_count}\n"
                f"Status: {response['status']}",
                title="Submitted",
                border_style="green",
            )
        )

        if detach:
            logger.info("run command — detach mode, exiting without watch")
            console.print(f"Detached. Check dashboard at {_DASHBOARD_URL}")
            return

        if not watch:
            logger.info("run command — watch disabled, exiting")
            console.print(f"Check dashboard at {_DASHBOARD_URL} for progress")
            return

        experiment_id = response.get("experiment_id")
        if not experiment_id:
            logger.warning("submit OK — missing experiment_id, cannot watch")
            console.print("[yellow]Server did not return experiment_id — cannot watch.[/yellow]")
            console.print(f"Check dashboard at {_DASHBOARD_URL}")
            return

        _watch_experiment(experiment_id)

    except FileNotFoundError as e:
        logger.error("run command failed — config file: %s", e)
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except RuntimeError as e:
        logger.error("run command failed — submit: %s", e)
        console.print(f"[red]Failed to submit experiment: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("run command failed — submit: %s", e, exc_info=True)
        console.print(f"[red]Failed to submit experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cancel(
    experiment_id: str = typer.Argument(..., help="Experiment ID to cancel"),
):
    """Cancel a running experiment."""
    logger.info("cancel command — experiment_id=%s", experiment_id)
    console.print(f"[cyan]Requesting cancellation for {experiment_id[:8]}...[/cyan]")

    try:
        response = cancel_experiment(experiment_id)
        eid = experiment_id[:8]
        console.print(
            Panel.fit(
                f"[yellow]⚠[/yellow]  Cancel requested for experiment [bold]{eid}[/bold]\n"
                f"{response.get('message', 'Experiment will stop after current phase')}",
                title="Cancellation",
                border_style="yellow",
            )
        )
    except RuntimeError as e:
        logger.error("cancel command failed — %s", e)
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("cancel command failed — request: %s", e, exc_info=True)
        console.print(f"[red]Failed to cancel experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def pause(
    experiment_id: str = typer.Argument(..., help="Experiment ID to pause"),
):
    """Pause a running experiment (stops after the current phase)."""
    logger.info("pause command — experiment_id=%s", experiment_id)
    console.print(f"[cyan]Requesting pause for {experiment_id[:8]}...[/cyan]")

    try:
        response = pause_experiment(experiment_id)
        eid = experiment_id[:8]
        console.print(
            Panel.fit(
                f"[yellow]⏸[/yellow]  Pause requested for experiment [bold]{eid}[/bold]\n"
                f"{response.get('message', 'Experiment will pause after current phase')}",
                title="Pause",
                border_style="yellow",
            )
        )
    except RuntimeError as e:
        logger.error("pause command failed — %s", e)
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("pause command failed — request: %s", e, exc_info=True)
        console.print(f"[red]Failed to pause experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def resume(
    experiment_id: str = typer.Argument(..., help="Experiment ID to resume"),
):
    """Resume a paused experiment from the next incomplete parameter combination."""
    logger.info("resume command — experiment_id=%s", experiment_id)
    console.print(f"[cyan]Resuming experiment {experiment_id[:8]}...[/cyan]")

    try:
        response = resume_experiment(experiment_id)
        eid = experiment_id[:8]
        console.print(
            Panel.fit(
                f"[green]▶[/green]  Resume requested for experiment [bold]{eid}[/bold]\n"
                f"{response.get('message', 'Remaining runs will execute')}",
                title="Resume",
                border_style="green",
            )
        )
    except RuntimeError as e:
        logger.error("resume command failed — %s", e)
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("resume command failed — request: %s", e, exc_info=True)
        console.print(f"[red]Failed to resume experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def delete(
    experiment_id: str = typer.Argument(..., help="Experiment ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Delete an experiment and all its associated data (chunks, results, run statuses)."""
    logger.info("delete command — experiment_id=%s force=%s", experiment_id, force)

    if not force:
        console.print(
            f"[yellow]⚠ Warning:[/yellow] This will permanently delete experiment "
            f"[bold]{experiment_id[:8]}[/bold] and all associated data:\n"
            "  - Experiment metadata\n"
            "  - Run statuses\n"
            "  - Chunks (embeddings)\n"
            "  - Query results"
        )
        confirm = typer.confirm("Are you sure you want to continue?")
        if not confirm:
            console.print("[dim]Deletion cancelled[/dim]")
            logger.info("delete command — cancelled by user")
            raise typer.Exit(0)

    console.print(f"[cyan]Deleting experiment {experiment_id[:8]}...[/cyan]")

    try:
        response = delete_experiment(experiment_id)
        eid = experiment_id[:8]
        deleted_counts = response.get("deleted_counts", {})

        lines = [
            f"[red]✗[/red]  Deleted experiment [bold]{eid}[/bold]",
            "",
            "[bold]Deleted documents:[/bold]",
            f"  Experiments:  {deleted_counts.get('experiments', 0)}",
            f"  Run statuses: {deleted_counts.get('run_status', 0)}",
            f"  Chunks:       {deleted_counts.get('chunks', 0)}",
            f"  Results:      {deleted_counts.get('results', 0)}",
        ]

        console.print(
            Panel.fit(
                "\n".join(lines),
                title="Deletion Complete",
                border_style="red",
            )
        )
        logger.info("delete OK — experiment %s counts=%s", experiment_id, deleted_counts)

    except RuntimeError as e:
        logger.error("delete command failed — %s", e)
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        logger.error("delete command failed — request: %s", e, exc_info=True)
        console.print(f"[red]Failed to delete experiment: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """Print the installed package version."""
    console.print(importlib.metadata.version("rag-params-finder"))


if __name__ == "__main__":
    app()
