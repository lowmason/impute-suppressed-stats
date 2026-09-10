"""§16.1: both commands write a machine-readable manifest and are idempotent for equal inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl
import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import app
from logging_employment.config import load_config

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "constraints"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """A config whose storage roots point inside tmp_path, with the golden staged tables."""
    staged = tmp_path / "staged"
    staged.mkdir()
    for name in ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge"):
        pl.read_parquet(FIXTURES / f"{name}.parquet").write_parquet(staged / f"{name}.parquet")
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(staged)
    raw["storage"]["raw_uri"] = str(tmp_path / "raw")
    raw["storage"]["output_uri"] = str(tmp_path / "runs")
    raw["storage"]["constraints_uri"] = str(tmp_path / "constraints")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


def _run(config: Path, *args: str) -> None:
    result = CliRunner().invoke(app, [*args, "--config", str(config)])
    assert result.exit_code == 0, result.output


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_constraints_writes_all_three_tables_and_a_manifest(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    cfg = load_config(workspace)
    constraints = Path(cfg.storage.constraints_uri)
    for name in ("target_cell", "constraint_row", "constraint_coefficient"):
        assert (constraints / f"{name}.parquet").exists()
    run_root = Path(cfg.storage.output_uri)
    run = next(run_root.iterdir())
    assert (run / "constraint_manifest.parquet").exists()
    assert (run / "config.resolved.yaml").exists()
    manifest = json.loads((run / "schema_manifest.json").read_text())
    assert manifest["constraint_set_hash"]
    assert manifest["compatibility_report"]["establishment_gap_by_year"]


def test_both_commands_are_idempotent_for_identical_inputs(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    first = {p.name: _digest(p) for p in sorted(run.glob("*.parquet"))}
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    runs_now = list(Path(cfg.storage.output_uri).iterdir())
    assert len(runs_now) == 1, "a second run created a second directory, so it was not idempotent"
    assert {p.name: _digest(p) for p in sorted(run.glob("*.parquet"))} == first


def test_solve_bounds_writes_bounds_ranks_and_flags(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    bounds = pl.read_parquet(run / "deterministic_bounds.parquet")
    assert bounds.filter(pl.col("bound_status") == "partially_identified").height == 2
    assert (run / "component_rank.parquet").exists()
    assert (run / "disclosure_flags.parquet").exists()


def test_solve_bounds_writes_a_manifest_naming_every_output_it_wrote(workspace: Path) -> None:
    """R-S5P-5: §16.1 requires a machine-readable manifest per command; this one wrote none.

    The digests are checked against the files rather than merely asserted present -- a manifest
    whose `output_hashes` are stale describes some other run, which is worse than no manifest.
    """
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    manifest = json.loads((run / "bounds_manifest.json").read_text())
    assert set(manifest["output_hashes"]) == {
        "deterministic_bounds",
        "component_rank",
        "disclosure_flags",
    }
    for table, digest in manifest["output_hashes"].items():
        assert _digest(run / f"{table}.parquet") == digest
    built = json.loads((run / "schema_manifest.json").read_text())
    assert manifest["constraint_set_hash"] == built["constraint_set_hash"]
    bounds = pl.read_parquet(run / "deterministic_bounds.parquet")
    assert manifest["bound_status_counts"] == dict(
        bounds.group_by("bound_status").len().iter_rows()
    )


def test_a_refused_solve_bounds_leaves_no_manifest_behind(workspace: Path) -> None:
    """The manifest is written on the success path only, or it would assert a run that failed."""
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    output_root = Path(load_config(workspace).storage.output_uri)
    assert not list(output_root.rglob("bounds_manifest.json"))


def test_every_manifest_stamps_the_code_that_wrote_it(workspace: Path) -> None:
    """R-S5P-5: `run_id` hashes config and inputs but NOT source, so a run directory can be stale.

    Deliberately NOT pinned to a value: `code_commit` moves with every commit and carries a
    `-dirty` suffix in any working tree, so a literal would be re-typed forever. What must hold is
    that the keys exist on every manifest and carry something a reader can compare -- and that the
    two commands writing into one directory agree, since they ran from one checkout.
    """
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    stamps = [
        json.loads((run / name).read_text())
        for name in ("schema_manifest.json", "bounds_manifest.json")
    ]
    for manifest in stamps:
        assert manifest["code_commit"]
        assert manifest["uv_lock_sha256"]
    assert stamps[0]["code_commit"] == stamps[1]["code_commit"]
    assert stamps[0]["uv_lock_sha256"] == stamps[1]["uv_lock_sha256"]


def test_solve_bounds_without_a_prior_build_names_what_is_missing(workspace: Path) -> None:
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    assert "build-constraints" in str(result.output) + str(result.exception)


def test_solve_bounds_refuses_inputs_that_did_not_produce_the_constraint_tables(
    workspace: Path,
) -> None:
    # The run id is derived from the harmonized inputs; the constraint tables come from
    # data/constraints/. Without a check, moving a staged value and re-running `solve-bounds`
    # alone would write bounds into a directory keyed to inputs that never produced them. The
    # idempotence test above runs both commands in order, so it cannot see this.
    _run(workspace, "build-constraints")
    cfg = load_config(workspace)
    staged = Path(cfg.storage.staged_uri) / "qcew_monthly.parquet"
    pl.read_parquet(staged).with_columns(
        pl.when(pl.col("state_fips") == "01")
        .then(2501)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    ).write_parquet(staged)
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    message = str(result.output) + str(result.exception)
    assert "build-constraints" in message or "constraint_set_hash" in message
    assert not list(Path(cfg.storage.output_uri).rglob("deterministic_bounds.parquet"))
