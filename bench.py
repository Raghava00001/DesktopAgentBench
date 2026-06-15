"""
DesktopAgentBench — CLI Entry Point

Usage:
    python bench.py run --config configs/default.yaml
    python bench.py validate --tasks-dir tasks/
    python bench.py list-tasks --tasks-dir tasks/
    python bench.py list-agents
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

console = Console()


def _setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """DesktopAgentBench — Windows desktop agent reliability benchmark."""
    _setup_logging(verbose)


@cli.command()
@click.option("--config", "-c", default="configs/default.yaml", help="Config file path")
@click.option("--agent", "-a", default=None, help="Agent spec (overrides config)")
@click.option("--split", "-s", default=None, help="Task split: dev|held_out|all")
@click.option("--tasks", "-t", default=None, help="Comma-separated task IDs")
@click.option("--profile", "-p", default=None, help="Chaos profile name")
@click.option("--repetitions", "-n", type=int, default=None, help="Repetitions per variant")
def run(
    config: str,
    agent: str | None,
    split: str | None,
    tasks: str | None,
    profile: str | None,
    repetitions: int | None,
) -> None:
    """Run the benchmark evaluation."""
    from src.core.config import load_config
    from src.core.orchestrator import Orchestrator

    console.print("[bold green]DesktopAgentBench[/bold green] — Starting benchmark run")

    # Load config
    cfg = load_config(config)

    # CLI overrides
    if agent:
        cfg.agent = agent
    if split:
        from src.core.config import SplitType
        cfg.split = SplitType(split)
    if tasks:
        cfg.task_filter = tasks.split(",")
    if profile:
        cfg.chaos_profiles = [profile]
    if repetitions:
        cfg.repetitions = repetitions

    # Run
    orchestrator = Orchestrator(cfg)
    metrics = orchestrator.run()

    # Summary
    console.print()
    table = Table(title="Benchmark Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Direction")

    metric_data = [
        ("TSR", f"{metrics.tsr.value:.4f}", "^ higher is better"),
        ("RS", f"{metrics.rs.value:.4f}", "^ closer to 1.0"),
        ("RR", f"{metrics.rr.value:.4f}", "^ higher is better"),
        ("UAR", f"{metrics.uar.value:.4f}", "v lower is better"),
        ("HAR", f"{metrics.har.value:.4f}", "v lower is better"),
        ("LHDI", f"{metrics.lhdi.value:.4f}", "v lower is better"),
        ("ITS", f"{metrics.its.value:.6f}", "^ higher is better"),
    ]

    for name, value, direction in metric_data:
        table.add_row(name, value, direction)

    console.print(table)
    console.print(f"\n[dim]Total runs: {metrics.total_runs} | Tasks: {metrics.total_tasks} | Variants: {metrics.total_variants}[/dim]")


@cli.command("validate")
@click.option("--tasks-dir", "-d", default="tasks", help="Tasks directory")
def validate(tasks_dir: str) -> None:
    """Validate all task definitions against the schema."""
    from src.tasks.loader import TaskLoader

    loader = TaskLoader(Path(tasks_dir))
    valid, errors = loader.validate_all()

    if errors:
        console.print(f"[bold red]Validation errors ({len(errors)}):[/bold red]")
        for err in errors:
            console.print(f"  [red]X[/red] {err}")

    console.print(f"\n[green]OK: {valid} valid[/green] | [red]FAIL: {len(errors)} invalid[/red]")

    if errors:
        sys.exit(1)


@cli.command("list-tasks")
@click.option("--tasks-dir", "-d", default="tasks", help="Tasks directory")
@click.option("--split", "-s", default=None, help="Filter by split")
def list_tasks(tasks_dir: str, split: str | None) -> None:
    """List all available tasks."""
    from src.tasks.loader import TaskLoader

    loader = TaskLoader(Path(tasks_dir))
    tasks = loader.load_all(split)

    table = Table(title="Task Corpus", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="bold")
    table.add_column("Category")
    table.add_column("App")
    table.add_column("Difficulty")
    table.add_column("Split")
    table.add_column("Title")

    for task in sorted(tasks, key=lambda t: t.task_id):
        table.add_row(
            task.task_id,
            task.category,
            task.app,
            task.difficulty.value,
            task.split,
            task.title[:50],
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(tasks)} tasks[/dim]")


@cli.command("list-agents")
def list_agents() -> None:
    """List all available agent adapters."""
    from src.agents.registry import get_agent_registry

    registry = get_agent_registry()
    registry.discover_builtins()

    table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Class")

    for name, cls in registry.get_all().items():
        table.add_row(name, f"{cls.__module__}:{cls.__name__}")

    console.print(table)


@cli.command("report")
@click.argument("results_dir")
def report(results_dir: str) -> None:
    """Regenerate reports from existing results."""
    results_path = Path(results_dir)
    if not results_path.exists():
        console.print(f"[red]Results directory not found: {results_path}[/red]")
        sys.exit(1)

    console.print(f"[dim]Report generation from existing results — not yet implemented[/dim]")


if __name__ == "__main__":
    cli()
