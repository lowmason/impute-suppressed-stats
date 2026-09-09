"""Stage 4's exit criteria, witnessed on the committed fixture layer rather than on data/staged.

The fixture is in git, so these run on a clean checkout. Where a claim is about D1 specifically the
test says so and carries the `data/staged` skipif.
"""

from pathlib import Path

import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.harness import run_pseudo_suppression

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "baselines"
STAGED = REPO / "data" / "staged"


def _fixture_config() -> Config:
    cfg = load_config(REPO / "config.yaml")
    return cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(
                update={"replicates_per_regime": 3, "pseudo_suppression_seeds": [1024]}
            )
        }
    )


@pytest.fixture(scope="module")
def fixture_run():
    """One full-registry harness pass, shared by every test here.

    Module scope because the pass costs ~11s and both tests need the same one; nothing about
    parallelism — no xdist plugin is installed in this venv and nothing configures it.
    """
    return run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY, _fixture_config())


def test_the_rolling_origin_entry_records_the_origins_its_guard_checked(fixture_run):
    """R-S4C-4: the guard is the deliverable, so the manifest must say where it ran.

    On this fixture the answer is NONE — it carries 2023 alone, so no January has the configured
    six months of history behind it. An empty list is the honest record and is not the same as an
    absent key: absent would mean the guard was never reached.
    """
    entry = fixture_run.manifest["regimes"]["rolling_origin"]
    assert "origins_checked" in entry
    assert entry["origins_checked"] == []
    assert entry["n_scored"] == 0


def test_only_the_truncating_regime_records_origins(fixture_run):
    """A key that appeared on every entry would say nothing about which regime owns the guard."""
    carrying = {
        name
        for name, entry in fixture_run.manifest["regimes"].items()
        if "origins_checked" in entry
    }
    assert carrying == {"rolling_origin"}


@pytest.mark.slow
@pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(),
    reason="data/staged is gitignored; the seven D1 origins need the rebuilt tables",
)
def test_the_guard_is_binding_on_the_d1_panel():
    """The fixture makes the guard vacuous, so the binding case is witnessed separately.

    Two estimators rather than the registry: this test is about the origins, and §13.7's CRPS is
    the harness's dominant cost.
    """
    cfg = load_config(REPO / "config.yaml")
    cfg = cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(update={"pseudo_suppression_seeds": [1024]})
        }
    )
    result = run_pseudo_suppression(HarmonizedData.load(STAGED), REGISTRY[:2], cfg)
    origins = result.manifest["regimes"]["rolling_origin"]["origins_checked"]
    assert origins == [
        "2018-01",
        "2019-01",
        "2020-01",
        "2021-01",
        "2022-01",
        "2023-01",
        "2024-01",
    ]
