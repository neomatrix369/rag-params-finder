"""CLI presentation helpers — live watch table and experiment summary.

Extracted from ``cli.main`` (Slice 45 fat-surface slim).
"""

from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from cli.api_client import get_experiment
from server.utils.logger import get_logger

console = Console()
logger = get_logger(__name__)

TERMINAL_PHASES = {"complete", "failed", "interrupted", "cancelled"}
POLL_INTERVAL_S = 2.0
_TRIAL_STATE_STYLES: dict[str, str] = {
    "completed": "green",
    "failed": "red",
    "pruned": "dim",
    "interrupted": "yellow",
}


def _build_runs_table(runs: list[dict]) -> Table:
    table = Table(title="Run Status", show_lines=True)
    table.add_column("Run ID", style="dim", max_width=10)
    table.add_column("Model")
    table.add_column("Chunker")
    table.add_column("Size/Overlap")
    table.add_column("Retrieval")
    table.add_column("Phase")
    table.add_column("Error", style="red", max_width=50)

    phase_styles = {
        "complete": "bold green",
        "failed": "bold red",
        "interrupted": "bold yellow",
    }

    for run in runs:
        phase = run.get("phase", "unknown")
        style = phase_styles.get(phase, "cyan")
        error_msg = run.get("error_message") or ""
        if len(error_msg) > 80:
            error_msg = error_msg[:77] + "..."
        table.add_row(
            run.get("run_id", "?")[:8],
            run.get("embedding_model", "?"),
            run.get("chunking_method", "?"),
            f"{run.get('chunk_size', '?')}/{run.get('overlap', '?')}",
            run.get("retrieval_method", "?"),
            f"[{style}]{phase}[/{style}]",
            error_msg,
        )
    return table


def _watch_experiment(experiment_id: str) -> None:
    """Poll experiment status and display live table until all runs finish."""
    logger.info("watch started — experiment %s", experiment_id)
    console.print(f"\n[cyan]Watching experiment {experiment_id[:8]}...[/cyan]\n")

    poll_count = 0
    data: dict = {}
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            poll_count += 1
            try:
                data = get_experiment(experiment_id)
            except Exception as e:
                logger.warning("watch poll failed — #%s: %s", poll_count, e)
                live.update(f"[red]Poll error: {e}[/red]")
                time.sleep(POLL_INTERVAL_S)
                continue

            runs = data.get("runs", [])
            status = data.get("status", "unknown")
            logger.debug("watch poll OK — #%s status=%s runs=%s", poll_count, status, len(runs))

            table = _build_runs_table(runs)
            live.update(table)

            if status in TERMINAL_PHASES or status in (
                "partial",
                "cancelled",
                "paused",
                "complete",
                "failed",
            ):
                break

            all_done = runs and all(r.get("phase") in TERMINAL_PHASES for r in runs)
            if all_done:
                time.sleep(POLL_INTERVAL_S)
                try:
                    data = get_experiment(experiment_id)
                except Exception as e:
                    logger.warning(
                        "watch final poll failed — %s: %s",
                        experiment_id,
                        e,
                    )
                break

            time.sleep(POLL_INTERVAL_S)

    _print_summary(data)


def _format_duration(started_at: str | None, completed_at: str | None) -> str:
    """Human-readable duration between two ISO timestamps."""
    if not started_at or not completed_at:
        return "—"
    from datetime import datetime as _dt

    start = _dt.fromisoformat(started_at.replace("Z", "+00:00"))
    end = _dt.fromisoformat(completed_at.replace("Z", "+00:00"))
    secs = (end - start).total_seconds()
    if secs < 60:
        return f"{secs:.1f}s"
    mins = int(secs // 60)
    rem = int(secs % 60)
    return f"{mins}m {rem}s"


def _format_bayesian_lines(bayesian_summary: dict, grid_equivalent_count: object) -> list[str]:
    """Format Bayesian Search section output lines.

    Args:
        bayesian_summary: The Bayesian experiment summary dict.
        grid_equivalent_count: Grid-equivalent count (fallback for missing in summary).

    Returns:
        List of Rich-markup lines for the Bayesian section.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("[bold]Bayesian Search[/bold]")

    planned = bayesian_summary.get("planned_trials", "?")
    attempted = bayesian_summary.get("attempted_trials", "?")
    grid_eq = bayesian_summary.get("grid_equivalent_count") or grid_equivalent_count
    discarded = bayesian_summary.get("discarded_trials", 0)

    lines.append("  Strategy:  bayesian (TPE)")
    lines.append(f"  Trials:    {attempted}/{planned} attempted  ·  {grid_eq} grid-equivalent")
    if discarded:
        lines.append(f"  Discarded: {discarded} (sampler exhausted unique candidates)")

    best_score = bayesian_summary.get("best_query_avg_score")
    best_chunk = bayesian_summary.get("best_chunk_size")
    best_overlap = bayesian_summary.get("best_overlap")
    if best_score is not None:
        lines.append(
            f"  Best:      chunk_size={best_chunk}  overlap={best_overlap}  score={best_score:.4f}"
        )

    trial_log = bayesian_summary.get("trial_log", [])
    if trial_log:
        lines.append("")
        lines.append("[bold]Trial History[/bold]")
        header = f"  {'#':>3}  {'chunk':>5}  {'ovlp':>4}  {'state':<11}  {'score':>7}"
        lines.append(f"[dim]{header}[/dim]")
        for i, entry in enumerate(trial_log, start=1):
            score_val = entry.get("score")
            score_str = f"{score_val:.4f}" if isinstance(score_val, float) else "      —"
            state = str(entry.get("state", "?"))
            state_style = _TRIAL_STATE_STYLES.get(state, "")
            if state_style:
                state_fmt = f"[{state_style}]{state:<11}[/{state_style}]"
            else:
                state_fmt = f"{state:<11}"
            lines.append(
                f"  {i:>3}  {entry.get('chunk_size', '?'):>5}  "
                f"{entry.get('overlap', '?'):>4}  {state_fmt}  {score_str:>7}"
            )

    return lines


def _print_summary(data: dict) -> None:
    """Print a final summary panel with success/failure breakdown."""
    status = data.get("status", "unknown")
    runs = data.get("runs", [])
    name = data.get("experiment_name", "?")

    completed = [r for r in runs if r.get("phase") == "complete"]
    failed = [r for r in runs if r.get("phase") == "failed"]
    other = [r for r in runs if r.get("phase") not in ("complete", "failed")]

    status_style = {
        "complete": "green",
        "partial": "yellow",
        "failed": "red",
        "cancelled": "yellow",
        "paused": "magenta",
    }.get(status, "cyan")

    lines = [f"[{status_style} bold]{status.upper()}[/{status_style} bold]  {name}"]
    lines.append(
        f"  [green]{len(completed)} passed[/green]  "
        f"[red]{len(failed)} failed[/red]  "
        f"[dim]{len(other)} other[/dim]"
    )

    git_commit = data.get("git_commit")
    git_branch = data.get("git_branch")
    git_dirty = data.get("git_dirty", False)
    started_at = data.get("started_at")
    completed_at = data.get("completed_at")
    env_params = data.get("env_params", {})

    lines.append("")
    lines.append("[bold]Metadata[/bold]")
    if git_commit:
        dirty_flag = " [yellow](dirty)[/yellow]" if git_dirty else ""
        branch_info = f" ({git_branch})" if git_branch else ""
        lines.append(f"  Git: [cyan]{git_commit}{branch_info}[/cyan]{dirty_flag}")
    app_ver = data.get("app_version")
    py_ver = data.get("python_version")
    if app_ver or py_ver:
        lines.append(f"  Version:  app={app_ver or '?'}  python={py_ver or '?'}")
    if started_at:
        lines.append(f"  Started:  {started_at}")
    if completed_at:
        lines.append(f"  Finished: {completed_at}")
        lines.append(f"  Duration: {_format_duration(started_at, completed_at)}")
    if env_params:
        rpm = env_params.get("voyage_rpm_limit", "?")
        tpm = env_params.get("voyage_tpm_limit", "?")
        lines.append(f"  RPM/TPM:  {rpm}/{tpm}")

    lines.append("")
    lines.append("[bold]Config[/bold]")
    data_paths = data.get("data_paths", [])
    lines.append(f"  Data:     {len(data_paths)} path(s)")
    for p in data_paths:
        lines.append(f"            [dim]{p}[/dim]")
    queries_file = data.get("queries_file")
    if queries_file:
        lines.append(f"  Queries:  {queries_file}")
    rerank = data.get("rerank_model")
    lines.append(f"  Rerank:   {rerank or 'none'}")
    lines.append(f"  Top-K:    {data.get('top_k_initial', '?')} → {data.get('top_k_final', '?')}")
    parallel = data.get("parallelism", "?")
    on_error = data.get("on_error", "?")
    lines.append(f"  Parallel: {parallel}  on_error: {on_error}")
    sweep = data.get("sweep_summary", {})
    if sweep:
        lines.append(
            f"  Sweep:    {', '.join(sweep.get('models', []))} × "
            f"{', '.join(sweep.get('chunking_methods', []))} × "
            f"sizes {sweep.get('chunk_sizes', [])} × "
            f"overlaps {sweep.get('overlaps', [])}"
        )

    search_strategy = (data.get("config") or {}).get("execution", {}).get("search_strategy", "grid")
    bayesian_summary = data.get("bayesian_summary") if search_strategy == "bayesian" else None
    if bayesian_summary:
        lines.extend(
            _format_bayesian_lines(
                bayesian_summary,
                data.get("grid_equivalent_count", "?"),
            )
        )

    if failed:
        lines.append("")
        lines.append("[red bold]Failures:[/red bold]")
        for r in failed:
            run_id = r.get("run_id", "?")[:8]
            model = r.get("embedding_model", "?")
            err = r.get("error_message") or "unknown error"
            lines.append(f"  [dim]{run_id}[/dim] ({model}): {err}")

    logger.info("watch finished — experiment %s status=%s", data.get("experiment_id", "?"), status)
    console.print(
        Panel.fit(
            "\n".join(lines),
            title="Experiment Result",
            border_style=status_style,
        )
    )
