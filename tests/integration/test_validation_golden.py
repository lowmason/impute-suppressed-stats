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

import numpy as np
import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import (
    INTERVAL_SOURCES,
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


def test_no_metric_family_carries_a_null_mask_arm(fixture_run):
    """M12: the `declines` family carried a NULL `mask_arm` on 70 of 70 rows here, 270 of 270 on D1.

    `validation_metrics` IS gated by `validate_frame` and the gate did not see it: `validate_frame`
    compares columns and dtypes, and `dict[str, pl.DataType]` has no nullability slot. The cause
    was that `decline_and_basis_report` took no `arm` parameter while its four siblings did.
    """
    assert fixture_run.metrics["mask_arm"].null_count() == 0
    declines = fixture_run.metrics.filter(pl.col("metric_family") == "declines")
    assert declines.height == 70
    assert declines["mask_arm"].unique().to_list() == ["state_total"]


def test_the_arm_comes_from_the_mask_rather_than_a_literal(fixture_run):
    """R-S4C-16: `MaskTarget.arm` was read by nothing; this is its first consumer.

    Every selector builds `state_total` targets today, so the VALUE does not change — which is
    exactly why the literal survived. What changes is where it comes from.
    """
    assert fixture_run.metrics["mask_arm"].unique().to_list() == ["state_total"]
    assert fixture_run.scores["mask_arm"].unique().to_list() == ["state_total"]


def test_the_interval_source_names_leave_one_out_rather_than_rolling(fixture_run):
    """R-S5P-7: `interval_source` names what is computed, and `rolling_` named something else.

    `probabilistic_metrics` builds each ensemble from `np.delete(residual_pool, position)` — the
    pool is every OTHER scored residual in the same (regime, seed, arm, estimator) group, with no
    time ordering and no window. Nothing rolls. The old value `rolling_residual_ensemble` promised
    §13.10's coverage gate a time-ordered interval that the code never computed, and the gate
    cannot tell the difference: `interval_source` is outside `assert_declared_provenance`'s five
    columns, so `INTERVAL_SOURCES` is checked by nothing at runtime and this test IS the check.

    Scope is the label. A time-ordered rolling interval is explicitly NOT built here
    (`specs/stage5-preconditions.md` §4).
    """
    assert INTERVAL_SOURCES == ("leave_one_out_residual_ensemble", "none")
    golden = pl.read_parquet(GOLDEN)
    for frame, origin in ((golden, "golden"), (fixture_run.metrics, "produced")):
        sources = set(frame["interval_source"].drop_nulls().to_list())
        assert sources <= set(INTERVAL_SOURCES), f"{origin} carries {sorted(sources)}"
        assert "leave_one_out_residual_ensemble" in sources, origin


def test_a_hand_derived_row_reproduces_the_golden_interval(fixture_run):
    """The oracle beside the whole-frame `equals`: one row derived from numpy, not from the code.

    `test_the_metrics_match_the_golden` compares the golden against the function that wrote it, so
    it detects drift and cannot detect a value that was wrong when it was frozen. This re-derives
    §13.7's 90% coverage and mean width for the widest interval-bearing group in the fixture
    (`whole_seasonal_blocks` x `cbp_intensity`, 37 scored cells) from the SCORES — which are data —
    without calling `probabilistic_metrics`. It is also what proves R-S5P-7 moved a label only: it
    passes unchanged on both sides of the rename.
    """
    regime, estimator = "whole_seasonal_blocks", "cbp_intensity"
    group = fixture_run.scores.filter(
        (pl.col("regime") == regime)
        & (pl.col("seed") == 1024)
        & (pl.col("estimator_id") == estimator)
    ).filter(pl.col("estimate").is_not_null())
    pool = (group["estimate"] - group["truth"]).to_numpy()
    assert pool.size == 37
    covered, widths = 0, []
    for position, row in enumerate(group.iter_rows(named=True)):
        ensemble = np.maximum(np.delete(pool, position) + float(row["estimate"]), 0.0)
        lo, hi = np.quantile(ensemble, 0.05), np.quantile(ensemble, 0.95)
        covered += int(lo <= row["truth"] <= hi)
        widths.append(hi - lo)
    golden = pl.read_parquet(GOLDEN).filter(
        (pl.col("regime") == regime)
        & (pl.col("estimator_id") == estimator)
        & (pl.col("metric_family") == "probabilistic")
    )

    def _value(name: str) -> float:
        return golden.filter(pl.col("metric_name") == name)["value"].item()

    assert covered == 33
    assert _value("coverage_0.90") == pytest.approx(covered / pool.size)
    assert _value("mean_interval_width_0.90") == pytest.approx(float(np.mean(widths)))
