import typer
from rich.console import Console
from rich.panel import Panel
from cli.config_loader import load_config
from cli.api_client import submit_experiment

app = typer.Typer(help="RAG Params Finder CLI")
console = Console()


@app.command()
def run(
    config: str = typer.Option(..., "--config", help="Path to experiment YAML config"),
    detach: bool = typer.Option(False, "--detach", help="Submit and exit without watching"),
):
    """
    Submit an experiment to the server.

    For Slice 1: --watch flag not implemented yet.
    """

    console.print(f"[cyan]Loading config from {config}...[/cyan]")

    try:
        # Load YAML config
        config_data = load_config(config)

        # Submit to server
        console.print("[cyan]Submitting experiment to server...[/cyan]")
        response = submit_experiment(config_data)

        # Display result
        console.print(Panel.fit(
            f"[green]✓[/green] Experiment submitted: {response['experiment_name']}\n"
            f"Status: {response['status']}\n"
            f"Message: {response['message']}",
            title="Success",
            border_style="green"
        ))

        if not detach:
            console.print("\n[yellow]Note: --watch flag not yet implemented (Slice 4)[/yellow]")
            console.print("Check the dashboard at http://localhost:5173 for progress")

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Failed to submit experiment: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
