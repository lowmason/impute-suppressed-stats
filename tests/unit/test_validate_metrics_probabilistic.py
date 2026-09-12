"""§13.7 coverage by Census division (R-S5G-1), and the residual SIGN of its ensemble (`D-112`).

Every expectation is derived with numpy from the fixture's own residuals, never through
`probabilistic_metrics` or its helpers: an expectation computed by the code under test is derived
from the bug it should catch. A residual is `estimate - truth`, so the truth a pooled residual
predicts is `estimate - residual`; the oracles are written from that identity, not from the code's
expression, and mirror the hand-derived one in `tests/integration/test_validation_golden.py`.

The division tests do NOT pin the sign, and cannot: on `_scores()` the same cells hit under either
sign (measured 2026-09-12: c1 and c2 in pacific, neither c3 nor new_england's c4), so only the interval
endpoints move. That is how an oracle copying the shipped `estimate + residual` passed from Stage 4 to
plan 14. The sign is pinned by the one-sided pools at the end of this module (`_one_sided`), whose
expectations follow from the identity with no quantile to interpolate.
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
        # truth = estimate - residual, over every OTHER cell's residual.
        ensemble = np.maximum(row["estimate"] - np.delete(pool, position), 0.0)
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
    """Inside the ensemble branch, coverage emits a row for every division WAPE does, null where
    nothing reached an ensemble. Outside it -- no interval family, or fewer than two scored cells --
    it emits none
    (`test_an_estimator_without_intervals_emits_one_overall_null_row_and_no_divisions` and
    `test_an_interval_family_with_fewer_than_two_scored_cells_emits_no_division_rows`), so a gate
    reading both families must outer-join.
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


def test_an_interval_family_with_fewer_than_two_scored_cells_emits_no_division_rows():
    """The branch where the families' strata differ: `point_metrics` still emits division WAPE here."""
    one = _scores().with_columns(
        pl.when(pl.col("cell_id") == "c1")
        .then(pl.col("estimate"))
        .otherwise(pl.lit(None, dtype=pl.Float64))
        .alias("estimate")
    )
    out = probabilistic_metrics(one, regime="r", seed=1, arm="state_total")
    assert out.height == 1
    assert out["stratum_kind"].item() == "overall"


def _one_sided(truth: list[float], residual: list[float]) -> pl.DataFrame:
    """Scored cells built FROM their residuals, so each cell's truth is known without the code."""
    return pl.DataFrame(
        {
            "estimator_id": [ESTIMATOR] * len(truth),
            "cell_id": [f"b{i}" for i in range(len(truth))],
            "state_fips": ["06", "41", "53", "23"][: len(truth)],
            "truth": truth,
            "estimate": [t + r for t, r in zip(truth, residual, strict=True)],
            "decline_kind": [None] * len(truth),
        },
        schema_overrides={"estimate": pl.Float64, "decline_kind": pl.String},
    )


def test_a_constant_bias_is_removed_so_every_interval_holds_the_truth_exactly():
    """`D-112`'s pin, derived from `truth = estimate - residual` rather than from the code.

    Every cell over-estimates by exactly 25, so every OTHER cell's residual is 25 and
    `estimate_i - 25` IS `truth_i`: each leave-one-out ensemble is a point mass on its own truth.
    Every interval at every level covers, at width zero, with CRPS zero. The shipped
    `estimate + residual` put that point mass at `truth + 50` -- coverage 0.00 and CRPS 50.
    """
    out = probabilistic_metrics(
        _one_sided([100.0, 200.0, 150.0, 120.0], [25.0] * 4),
        regime="r",
        seed=1,
        arm="state_total",
    )
    coverage = out.filter(pl.col("metric_name").str.starts_with("coverage_"))
    # Four levels overall, plus 90% for pacific (06, 41, 53) and new_england (23).
    assert coverage.height == 6
    assert coverage["value"].to_list() == [1.0] * 6
    overall = {
        r["metric_name"]: r["value"]
        for r in out.filter(pl.col("stratum_kind") == "overall").iter_rows(named=True)
    }
    assert overall["mean_interval_width_0.90"] == 0.0
    assert overall["crps"] == pytest.approx(0.0, abs=1e-9)
    assert overall["n_clipped_at_zero"] == 0.0


def test_the_zero_clip_counts_what_the_truth_identity_makes_negative():
    """`n_clipped_at_zero` moves with the sign too, so it is pinned the same way, with no quantile.

    Residuals (`estimate - truth`) are 2, 50, 60 and 70, so the estimates are 3, 250, 360 and 470.
    The first cell's ensemble is `3 - 50`, `3 - 60`, `3 - 70`: three negatives. Every other cell's
    estimate exceeds each residual it is paired with (its smallest member is 250 - 70, 360 - 70 or
    470 - 60), so nothing else clips. The shipped sign added the residuals and clipped none.
    """
    out = probabilistic_metrics(
        _one_sided([1.0, 200.0, 300.0, 400.0], [2.0, 50.0, 60.0, 70.0]),
        regime="r",
        seed=1,
        arm="state_total",
    )
    assert out.filter(pl.col("metric_name") == "n_clipped_at_zero")["value"].item() == 3.0
