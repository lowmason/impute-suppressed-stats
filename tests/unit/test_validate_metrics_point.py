import polars as pl

from logging_employment.validate.metrics import point_metrics


def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["a", "a", "a", "b", "b", "b"],
            "cell_id": ["c1", "c2", "c3"] * 2,
            "truth": [100.0, 200.0, 300.0] * 2,
            "estimate": [110.0, 180.0, None, None, None, None],
            "decline_kind": [None, None, "data_gap", "by_design", "by_design", "by_design"],
        }
    )


def test_a_declined_row_is_excluded_from_the_numerator_but_not_the_denominator():
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    a = out.filter(pl.col("estimator_id") == "a")
    assert a["n_scored"].unique().to_list() == [2]
    assert a["denominator"].unique().to_list() == [3.0]
    assert a["n_declined_data_gap"].unique().to_list() == [1]


def test_an_all_declining_estimator_reports_null_not_zero():
    """`harvest_proportional` declines by design; a 0.0 WAPE would read as perfect accuracy."""
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    b = out.filter((pl.col("estimator_id") == "b") & (pl.col("metric_name") == "wape"))
    assert b["value"].item() is None
    assert b["n_scored"].item() == 0
    assert b["n_declined_by_design"].item() == 3


def test_wape_is_computed_over_the_scored_rows_only():
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    wape = out.filter((pl.col("estimator_id") == "a") & (pl.col("metric_name") == "wape"))[
        "value"
    ].item()
    # (|110-100| + |180-200|) / (100 + 200) = 30 / 300
    assert abs(wape - 0.1) < 1e-12
