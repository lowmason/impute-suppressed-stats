"""The §17.6-style golden for §13's metrics, on the frozen in-git fixture.

Task 19 lists this fixture in its Files block but no step builds one, so the shape is this repo's
existing golden convention (`test_baseline_golden.py`): the inputs are `tests/fixtures/baselines/`,
which is IN GIT and not sliced from `data/staged`, so the golden is reproducible on a clean
checkout with no rebuilt data layer.

`replicates_per_regime` is 3 rather than Appendix A's 20: the fixture carries 12 months, and at 20
the single-month regimes' own lookback guard refuses the draw — measured, `concentration_proxy`
would mask 7 of 12 months for state 12, leaving fewer than the configured 6 lookback months. That
refusal is the guard working; the golden simply sizes its config to the fixture.

WHAT THIS GOLDEN DOES NOT PROTECT, recorded so a later reader does not assume it does: plan 10's
`BreakAdjustedShare` refusal gets no end-to-end coverage here. §17.6's missing cells almost all
lack a share history, so no refusal fires. A Stage 4 MASK, not this golden, is what moves a
refusal count.
"""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import (
    VALIDATION_METRIC_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from logging_employment.validate.harness import run_pseudo_suppression

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "baselines"
GOLDEN = REPO / "tests" / "fixtures" / "validation" / "validation_metrics_golden.parquet"


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
    return run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY, _fixture_config())


def test_the_metrics_match_the_golden(fixture_run):
    """§17.4 row 7: the harness generates pseudo-suppression metrics, and they do not drift."""
    golden = pl.read_parquet(GOLDEN)
    produced = fixture_run.metrics
    assert produced.columns == golden.columns
    key = ["regime", "seed", "mask_arm", "estimator_id", "metric_family", "metric_name"]
    assert produced.sort(key).equals(golden.sort(key))


def test_the_golden_matches_the_declared_schema():
    validate_frame(pl.read_parquet(GOLDEN), VALIDATION_METRIC_SCHEMA, "validation_metrics_golden")


def test_the_golden_covers_every_estimator_and_a_composed_arm(fixture_run):
    """A golden that scored two estimators would drift silently on the other eight."""
    assert fixture_run.scores["estimator_id"].n_unique() == len(REGISTRY)
    # The own/fallback split is the signal plan 10's composed refusals need; it must not be null.
    assert fixture_run.scoreboard["n_own_estimator"].null_count() == 0
    assert fixture_run.scoreboard["n_establishment_fallback"].null_count() == 0
