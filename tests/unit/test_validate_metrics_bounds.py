import polars as pl

from logging_employment.validate.metrics import bound_metrics


def _scores(upper):
    return pl.DataFrame(
        {
            "estimator_id": ["equal_residual"] * 2,
            "cell_id": ["a", "b"],
            "truth": [100.0, 200.0],
            "selected_lower": [0.0, 0.0],
            "selected_upper": upper,
            "bound_status": ["unbounded", "unbounded"],
        }
    )


def test_a_null_upper_bound_counts_as_containing_the_truth():
    """`[0, +inf)` contains everything. A naive `truth <= upper` would drop both rows."""
    out = bound_metrics(
        _scores([None, None]), regime="small_cell_biased", seed=1, arm="state_total"
    )
    rate = out.filter(pl.col("metric_name") == "truth_in_bound_rate")["value"].item()
    assert rate == 1.0


def test_a_vacuous_arm_is_flagged_by_finite_upper_count():
    out = bound_metrics(
        _scores([None, None]), regime="small_cell_biased", seed=1, arm="state_total"
    )
    assert out["bound_cells_finite_upper"].unique().to_list() == [0]
    width = out.filter(pl.col("metric_name") == "mean_feasible_width")["value"].item()
    assert width is None, "an infinite width must be null, not inf and not 0"


def test_a_finite_upper_bound_produces_a_real_width():
    out = bound_metrics(
        _scores([150.0, 500.0]), regime="cbp_size_gaps", seed=1, arm="national_size"
    )
    assert out["bound_cells_finite_upper"].unique().to_list() == [2]
    width = out.filter(pl.col("metric_name") == "mean_feasible_width")["value"].item()
    # [0, 150] and [0, 500] are 150 and 500 wide; their mean is 325.
    assert width == (150.0 + 500.0) / 2
