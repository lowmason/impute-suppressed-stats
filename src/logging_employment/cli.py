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


registry_app = typer.Typer(help="Source registry commands.")
app.add_typer(registry_app, name="registry")


@registry_app.command("verify")
def registry_verify(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Check the seed registry against §7.1 and report every problem found."""
    from .registry.loader import load_registry
    from .registry.validation import verify

    load_config(config)
    seed = Path(__file__).parent / "registry" / "sources.yaml"
    problems = verify(load_registry(seed))
    for problem in problems:
        typer.echo(f"PROBLEM: {problem}")
    if problems:
        raise typer.Exit(code=1)
    typer.echo("OK: registry verified")


@app.command("fetch")
def fetch(
    source: str = typer.Option(..., "--source", help="qcew, qcew_size, or cbp"),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Acquire raw bytes for one source into the immutable store and record a snapshot row."""
    if source not in {"qcew", "qcew_size", "cbp"}:
        raise typer.BadParameter(f"unknown source {source!r}")
    from .fetching import fetch_source

    cfg = load_config(config)
    rows = fetch_source(source, cfg, env_path=Path(".env"))
    typer.echo(f"{source}: {len(rows)} snapshot row(s) -> {cfg.storage.raw_uri}")


@app.command("build-harmonized")
def build_harmonized_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Assemble the harmonized Parquet layer from stored raw bytes and print output hashes."""
    from .build import build_harmonized

    cfg = load_config(config)
    hashes = build_harmonized(
        cfg,
        raw_root=Path(cfg.storage.raw_uri),
        out_root=Path(cfg.storage.staged_uri),
        manifest_path=Path(cfg.storage.output_uri) / "source_manifest.parquet",
    )
    for table, digest in sorted(hashes.items()):
        typer.echo(f"{table} {digest}")
