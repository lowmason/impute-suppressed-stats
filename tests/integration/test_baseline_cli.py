"""The two Stage 3 commands: what they write, and that a second run writes the same bytes."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from logging_employment.cli import app

runner = CliRunner()


def test_run_baselines_writes_results_and_a_sibling_manifest(staged_repo) -> None:
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    out = staged_repo.run_dir / "baseline_results"
    assert (out / "baseline_results.parquet").exists()
    assert (out / "anchor_audit.parquet").exists()
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    assert "preferred_estimator" in manifest
    assert "output_hashes" in manifest
    assert "weight_basis_counts" in manifest


def test_run_baselines_does_not_touch_the_stage_2_manifest(staged_repo) -> None:
    """`solve-bounds` reads schema_manifest.json's bytes as a precondition gate."""
    before = (staged_repo.run_dir / "schema_manifest.json").read_bytes()
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    assert (staged_repo.run_dir / "schema_manifest.json").read_bytes() == before


def test_a_second_run_is_byte_identical(staged_repo) -> None:
    """§16.1: every command MUST be idempotent for the same inputs."""
    path = staged_repo.run_dir / "baseline_results" / "baseline_results.parquet"
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    first = path.read_bytes()
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert path.read_bytes() == first


def test_the_manifest_records_the_composite_split(staged_repo) -> None:
    """Stage 4 must not report a composite's score as a pure estimator's.

    The split is recorded PER ESTIMATOR. Pooled across all ten it cannot answer the only
    question §10.8's ranking turns on — what fraction of THIS estimator's cells fell back —
    because one pure estimator's own-weighted cells mask another's fallbacks.
    """
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    counts = manifest["weight_basis_counts"]
    # A pure estimator: every cell its own.
    assert set(counts["establishment_proportional"]) == {"own_estimator"}
    # A composite: both arms present, and the fallback share recoverable on its own.
    assert set(counts["cbp_intensity"]) >= {"own_estimator", "establishment_fallback"}


def test_declines_are_counted_in_the_manifest(staged_repo) -> None:
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    assert "harvest_proportional" in manifest["declines"]


def test_reconcile_writes_a_manifest_like_every_other_command(staged_repo) -> None:
    """§16.1: "Every command MUST write a machine-readable manifest".

    The plan's version only echoed. A verifier that leaves no artifact gives §18.1 nothing to
    reproduce against, and the MUST is not conditional on the command producing data.
    """
    assert (
        runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)]).exit_code
        == 0
    )
    result = runner.invoke(app, ["reconcile", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "reconcile_manifest.json").read_text())
    assert manifest["within_tolerance"] is True
    assert manifest["checked_pairs"] > 0
    assert manifest["max_residual_drift"] <= manifest["tolerance"]
    # The digest pins WHICH results were checked, so a later edit cannot masquerade as verified.
    assert len(manifest["baseline_results_sha256"]) == 64


def test_reconcile_refuses_before_run_baselines_has_produced_anything(staged_repo) -> None:
    """The precondition gate, matching how `solve-bounds` gates on `build-constraints`."""
    result = runner.invoke(app, ["reconcile", "--config", str(staged_repo.config_path)])
    assert result.exit_code != 0
    assert "run-baselines" in result.output
