import polars as pl

from logging_employment.validate.metrics import point_metrics


def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["a", "a", "a", "b", "b", "b"],
            "cell_id": ["c1", "c2", "c3"] * 2,
            "state_fips": ["06", "41", "23"] * 2,
            "reference_month": ["2019-03", "2019-03", "2019-04"] * 2,
            "truth": [100.0, 200.0, 300.0] * 2,
            "estimate": [110.0, 180.0, None, None, None, None],
            "decline_kind": [None, None, "data_gap", "by_design", "by_design", "by_design"],
        }
    )


def _national():
    return pl.DataFrame(
        {
            "reference_month": ["2019-03", "2019-04"],
            "national_employment": [1000.0, 2000.0],
        }
    )


def test_a_declined_row_is_excluded_from_the_numerator_but_not_the_denominator():
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    a = out.filter((pl.col("estimator_id") == "a") & (pl.col("stratum_kind") == "overall"))
    assert a["n_scored"].unique().to_list() == [2]
    assert a["denominator"].unique().to_list() == [3.0]
    assert a["n_declined_data_gap"].unique().to_list() == [1]


def test_an_all_declining_estimator_reports_null_not_zero():
    """`harvest_proportional` declines by design; a 0.0 WAPE would read as perfect accuracy."""
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    b = out.filter(
        (pl.col("estimator_id") == "b")
        & (pl.col("metric_name") == "wape")
        & (pl.col("stratum_kind") == "overall")
    )
    assert b["value"].item() is None
    assert b["n_scored"].item() == 0
    assert b["n_declined_by_design"].item() == 3


def test_wape_is_computed_over_the_scored_rows_only():
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    wape = out.filter(
        (pl.col("estimator_id") == "a")
        & (pl.col("metric_name") == "wape")
        & (pl.col("stratum_kind") == "overall")
    )["value"].item()
    # (|110-100| + |180-200|) / (100 + 200) = 30 / 300
    assert abs(wape - 0.1) < 1e-12


def test_state_share_absolute_error_divides_each_cell_by_its_own_month_national_total():
    """§13.6's state-share absolute error, R-S5G-4.

    Both scored cells fall in 2019-03, whose national total is 1000: |110-100|/1000 = 0.01 and
    |180-200|/1000 = 0.02, so the mean is 0.015. Computing it against a pooled denominator instead
    would let a large month dominate a small one, which is the comparison a SHARE metric exists to
    avoid.
    """
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    value = out.filter(
        (pl.col("estimator_id") == "a") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert abs(value - 0.015) < 1e-12


def test_state_share_absolute_error_is_null_when_nothing_scored():
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    value = out.filter(
        (pl.col("estimator_id") == "b") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert value is None


def test_a_month_with_no_national_row_is_excluded_rather_than_counted_as_zero_error():
    """Null, never 0.0 — the module rule. A cell whose month has no denominator has no share."""
    out = point_metrics(
        _scores(),
        regime="r",
        seed=1,
        arm="state_total",
        national_totals=_national().filter(pl.col("reference_month") == "2019-04"),
    )
    value = out.filter(
        (pl.col("estimator_id") == "a") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert value is None


def test_wape_is_emitted_per_census_division_with_that_division_s_own_denominator():
    """R-S5G-1: §13.10's per-stratum gate needs a WAPE it can read, with its own base.

    `06` and `41` are both `pacific` and both scored: (|110-100| + |180-200|) / (100 + 200) = 0.1,
    over a denominator of 2 masked cell-rows rather than the estimator's 3.
    """
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    pacific = out.filter(
        (pl.col("estimator_id") == "a")
        & (pl.col("stratum_kind") == "census_division")
        & (pl.col("stratum_value") == "pacific")
    )
    assert pacific["metric_name"].to_list() == ["wape"]
    assert abs(pacific["value"].item() - 0.1) < 1e-12
    assert pacific["denominator"].item() == 2.0
    assert pacific["n_scored"].item() == 2


def test_only_the_divisions_present_in_the_replicate_are_emitted():
    """A division this mask never touched has no row, rather than a null one a gate would read."""
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    divisions = set(out.filter(pl.col("stratum_kind") == "census_division")["stratum_value"])
    assert divisions == {"pacific", "new_england"}


def test_an_unstratified_row_carries_the_overall_sentinel_and_never_a_null():
    """The `mask_arm` defect, refused by construction: `validate_frame` cannot see a null."""
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    assert out["stratum_kind"].null_count() == 0
    assert out["stratum_value"].null_count() == 0
    overall = out.filter(pl.col("stratum_kind") == "overall")
    assert overall["stratum_value"].unique().to_list() == ["all"]


def test_a_state_outside_the_census_partition_is_refused_rather_than_bucketed():
    """`72` is Puerto Rico: a REQ-002 universe violation, not a stratum needing a home."""
    import pytest

    from logging_employment.errors import ConceptViolationError

    rogue = _scores().with_columns(
        pl.when(pl.col("cell_id") == "c1")
        .then(pl.lit("72"))
        .otherwise(pl.col("state_fips"))
        .alias("state_fips")
    )
    with pytest.raises(ConceptViolationError, match="72"):
        point_metrics(rogue, regime="r", seed=1, arm="state_total", national_totals=_national())
