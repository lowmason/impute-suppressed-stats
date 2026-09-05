"""Shared setup for the Stage 3 CLI integration tests.

`staged_repo` gives a command a complete, self-contained repository to run against: a config whose
storage roots point inside `tmp_path`, a staged layer copied from the COMMITTED fixture under
`tests/fixtures/baselines/`, and a completed `build-constraints` run so `schema_manifest.json`
exists — `run-baselines` gates on that file the same way `solve-bounds` does.

Copying a committed fixture rather than slicing `data/staged` at test time is the point. `data/`
is gitignored, so a fixture derived from it at run time is pinned to untracked, rebuildable data
and is not frozen in any useful sense.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl
import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import _input_digests, app
from logging_employment.config import load_config
from logging_employment.runs import run_dir, run_id

REPO = Path(__file__).resolve().parents[2]
BASELINE_FIXTURES = REPO / "tests" / "fixtures" / "baselines"
STAGED_TABLES = ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge")


@dataclass(frozen=True)
class StagedRepo:
    """A throwaway repository: where its config lives, and where its run outputs land."""

    config_path: Path
    run_dir: Path


@pytest.fixture()
def staged_repo(tmp_path: Path) -> StagedRepo:
    """A tmp repo holding the frozen Stage 3 staged layer and a built constraint system."""
    staged = tmp_path / "staged"
    staged.mkdir()
    for name in STAGED_TABLES:
        pl.read_parquet(BASELINE_FIXTURES / f"{name}.parquet").write_parquet(
            staged / f"{name}.parquet"
        )
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(staged)
    raw["storage"]["raw_uri"] = str(tmp_path / "raw")
    raw["storage"]["output_uri"] = str(tmp_path / "runs")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False))

    result = CliRunner().invoke(app, ["build-constraints", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    cfg = load_config(config_path)
    return StagedRepo(
        config_path=config_path, run_dir=run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    )
