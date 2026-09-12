"""§13.7 coverage by Census division — the half of R-S5G-1 the golden alone used to pin.

Every expectation is derived with numpy from the fixture's own residuals, never through
`probabilistic_metrics` or its helpers: an expectation computed by the code under test is derived
from the bug it should catch. The ensemble arithmetic mirrors the hand-derived oracle in
`tests/integration/test_validation_golden.py`.
"""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from logging_employment.errors import ConceptViolationError
from logging_employment.validate.metrics import probabilistic_metrics

ESTIMATOR = "cbp_intensity"  # an interval-bearing family (§10.7)
DIVISION = {"06": "pacific", "41": "pacific", "53": "pacific", "23": "new_england"}


def _scores(estimator: str = ESTIMATOR) -> pl.DataFrame:
    """Six masked cells over three divisions.

    pacific: three scored. new_england: one scored, one declined. east_north_central: one masked
    cell, declined -- a division with rows and nothing to score.
    """
    return pl.DataFrame(
        {
            "estimator_id": [estimator] * 6,
            "cell_id": [f"c{i}" for i in range(1, 7)],
            "state_fips": ["06", "41", "53", "23", "09", "17"],
            "truth": [100.0, 200.0, 150.0, 120.0, 90.0, 80.0],
            "estimate": [110.0, 190.0, 170.0, 100.0, None, None],
            "decline_kind": [None, None, None, None, "data_gap", "by_design"],
        },
        schema_overrides={"estimate": pl.Float64},
    )


def _oracle(scores: pl.DataFrame) -> dict[str, tuple[int, int]]:
    """(seen, hits) per division: leave-one-out over the WHOLE scored pool, 90% central interval."""
    scored = scores.filter(pl.col("estimate").is_not_null())
    pool = (scored["estimate"] - scored["truth"]).to_numpy()
    out: dict[str, list[int]] = {}
    for position, row in enumerate(scored.iter_rows(named=True)):
        ensemble = np.maximum(np.delete(pool, position) + row["estimate"], 0.0)
        lo, hi = np.quantile(ensemble, 0.05), np.quantile(ensemble, 0.95)
        tally = out.setdefault(DIVISION[row["state_fips"]], [0, 0])
        tally[0] += 1
        tally[1] += int(lo <= row["truth"] <= hi)
    return {k: (v[0], v[1]) for k, v in out.items()}


def _division_rows(out: pl.DataFrame) -> dict[str, dict]:
    rows = out.filter(pl.col("stratum_kind") == "census_division")
    assert set(rows["metric_name"]) <= {"coverage_0.90"}
    return {r["stratum_value"]: r for r in rows.iter_rows(named=True)}


def test_each_division_row_carries_its_own_scored_count_and_base():
    """`n_scored` was the ESTIMATOR's on every division row, so it exceeded `denominator`."""
    rows = _division_rows(probabilistic_metrics(_scores(), regime="r", seed=1, arm="state_total"))
    assert (rows["pacific"]["n_scored"], rows["pacific"]["denominator"]) == (3, 3.0)
    assert (rows["new_england"]["n_scored"], rows["new_england"]["denominator"]) == (1, 2.0)
    for row in rows.values():
        assert row["n_scored"] <= row["denominator"]


def test_division_coverage_matches_an_independent_leave_one_out_oracle():
    scores = _scores()
    rows = _division_rows(probabilistic_metrics(scores, regime="r", seed=1, arm="state_total"))
    for division, (seen, hits) in _oracle(scores).items():
        assert rows[division]["calibration_sample_size"] == seen
        assert rows[division]["value"] == pytest.approx(hits / seen)


def test_division_calibration_samples_add_up_to_the_overall_one():
    """The pool stays GLOBAL; only the tally is split, so the parts must sum to the whole."""
    out = probabilistic_metrics(_scores(), regime="r", seed=1, arm="state_total")
    overall = out.filter(
        (pl.col("stratum_kind") == "overall") & (pl.col("metric_name") == "coverage_0.90")
    )
    assert overall["calibration_sample_size"].item() == 4
    assert sum(r["calibration_sample_size"] for r in _division_rows(out).values()) == 4


def test_every_masked_division_gets_a_row_and_an_all_declined_one_is_null_like_wape():
    """WAPE emits a null row for a division whose masked cells all declined; coverage emitted
    NOTHING, so the two families disagreed on which divisions exist and a §13.10 gate reading both
    would have had to outer-join them to notice.
    """
    rows = _division_rows(probabilistic_metrics(_scores(), regime="r", seed=1, arm="state_total"))
    assert set(rows) == {"pacific", "new_england", "east_north_central"}
    enc = rows["east_north_central"]
    assert enc["value"] is None
    assert (enc["n_scored"], enc["calibration_sample_size"], enc["denominator"]) == (0, 0, 1.0)


def test_an_estimator_without_intervals_emits_one_overall_null_row_and_no_divisions():
    """No ensemble exists to stratify; a division row here would be null for a reason a gate cannot
    tell from failure."""
    out = probabilistic_metrics(_scores("equal_residual"), regime="r", seed=1, arm="state_total")
    assert out.height == 1
    assert out["stratum_kind"].item() == "overall"
    assert out["value"].item() is None


def test_the_national_size_arm_is_not_stratified_and_not_refused():
    """`US` is a national cell's `state_fips`, and a Census division is meaningless for it."""
    national = _scores().with_columns(pl.lit("US").alias("state_fips"))
    out = probabilistic_metrics(national, regime="r", seed=1, arm="national_size")
    assert set(out["stratum_kind"]) == {"overall"}


def test_a_territory_is_refused_on_the_probabilistic_path_too():
    """`with_census_division` is called separately here, so the refusal needs its own pin."""
    rogue = _scores().with_columns(
        pl.when(pl.col("cell_id") == "c1")
        .then(pl.lit("72"))
        .otherwise(pl.col("state_fips"))
        .alias("state_fips")
    )
    with pytest.raises(ConceptViolationError, match="72"):
        probabilistic_metrics(rogue, regime="r", seed=1, arm="state_total")
