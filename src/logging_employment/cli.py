"""The `logging-estimates` command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import load_config

app = typer.Typer(add_completion=False, help="Monthly state Logging employment estimates.")


@app.callback()
def main() -> None:
    """Pin the app as a command group.

    Typer collapses a one-command app into a bare top-level command, which would make
    `logging-estimates validate-config` invalid today and valid once a second command lands.
    The callback fixes the invocation syntax regardless of how many commands are registered.
    """


@app.command("validate-config")
def validate_config(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Parse the configuration and report the resolved estimand."""
    cfg = load_config(config)
    typer.echo(
        f"OK: {cfg.project.industry_code_used} / {cfg.project.ownership} / "
        f"{cfg.project.geography_universe} / {cfg.project.start_month}..{cfg.project.end_month}"
    )
