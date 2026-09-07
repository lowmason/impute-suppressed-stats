"""The `validate` command: it writes metrics, a manifest, and the same bytes twice.

COST DEVIATION, stated rather than silent. The plan's version of these two tests invokes the full
harness three times at `config.yaml`'s three seeds. Measured on D1, one full pass is ~13 minutes
(27 replicates x ~30 s, dominated by `run_baselines`), so the pair would add ~40 minutes to a suite
whose current wall clock is 2:46 — and the suite runs `slow` tests by default. These tests drive
the real CLI end to end against a ONE-SEED copy of the shipped config, which exercises the same
wiring, the same manifest and the same idempotence at a third of the cost. The three-seed
acceptance run is Task 19 Step 3's job, and its numbers are recorded in the plan's completion
stamp rather than asserted here.
"""

import json
from pathlib import Path

import polars as pl
import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import app

REPO = Path(__file__).resolve().parents[2]
STAGED = REPO / "data" / "staged"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (STAGED / "qcew_monthly.parquet").exists(),
        reason="data/staged is gitignored; the validate CLI needs the rebuilt tables",
    ),
]


@pytest.fixture(scope="module")
def one_seed_config(tmp_path_factory) -> Path:
    """The shipped config with a single seed, so the run is a third of the full harness."""
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["validation"]["pseudo_suppression_seeds"] = [1024]
    path = tmp_path_factory.mktemp("validate-cli") / "config.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return path


def _metrics_path(config: Path) -> Path:
    """The run directory this config hashes to, not whichever run sorts last.

    `max(runs/*/validation_metrics.parquet)` would pick up a run written by a DIFFERENT config —
    including the three-seed acceptance run — and then assert against numbers this test never
    produced.
    """
    from logging_employment.cli import _input_digests
    from logging_employment.config import load_config
    from logging_employment.runs import run_dir, run_id

    cfg = load_config(config)
    return run_dir(cfg, run_id(cfg, _input_digests(cfg))) / "validation_metrics.parquet"


@pytest.fixture(scope="module")
def first_run(one_seed_config) -> tuple[Path, bytes]:
    """One CLI invocation, shared. Each pass is ~3.7 minutes, so three would be eleven."""
    result = CliRunner().invoke(app, ["validate", "--config", str(one_seed_config)])
    assert result.exit_code == 0, result.output
    path = _metrics_path(one_seed_config)
    assert path.exists(), f"no validation_metrics.parquet at {path}"
    return path, path.read_bytes()


def test_validate_writes_metrics_and_a_manifest(first_run):
    path, _ = first_run
    metrics = pl.read_parquet(path)
    assert metrics.height > 0
    assert metrics["denominator"].null_count() == 0

    manifest = json.loads((path.parent / "validation_manifest.json").read_text())
    assert "regimes" in manifest
    assert manifest["regimes"]["preliminary_to_final_vintage"]["disposition"] == "cannot_run_on_d1"
    # A refused regime records WHY and emits no scores — never an empty partition.
    assert manifest["regimes"]["preliminary_to_final_vintage"]["n_scored"] == 0
    assert manifest["regimes"]["preliminary_to_final_vintage"]["reason"]


def test_validate_is_idempotent_for_identical_inputs(one_seed_config, first_run):
    """§16.1's MUST, and the only test that could have caught the defect it did.

    Two selectors sampled from an UNORDERED frame (`unique()` / `group_by()` give no order
    guarantee), so a seeded draw picked a different month per PROCESS. Every within-process
    assertion passed — Polars returns the same arbitrary order twice in one interpreter — and only
    comparing the bytes of two separate CLI invocations saw it.
    """
    path, before = first_run
    second = CliRunner().invoke(app, ["validate", "--config", str(one_seed_config)])
    assert second.exit_code == 0, second.output
    assert path.read_bytes() == before
