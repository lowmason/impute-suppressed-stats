"""The §17.6 golden comparator must refuse every real move while absorbing the last ulps.

A tolerance comparator that silently accepts everything is the failure this file exists for: both
goldens would stay green and the units-and-magnitude net would be gone with no test reddening. So
most cases below are REFUSALS, each a move the old exact `.equals` caught and this one must too.
"""

import math

import polars as pl
import pytest
from tests.golden_compare import ABS_TOL, REL_TOL, assert_matches_golden


def _frame(**overrides):
    columns = {
        "estimator_id": ["a", "b"],
        "estimate": [3891.083970564594, 0.0],
        "estimate_integer": [3891, 0],
        "residual": [7.2760e-12, None],
    }
    columns.update(overrides)
    return pl.DataFrame(
        columns,
        schema={
            "estimator_id": pl.String,
            "estimate": pl.Float64,
            "estimate_integer": pl.Int64,
            "residual": pl.Float64,
        },
    )


def test_the_tolerances_are_the_ones_the_decision_named():
    """rel 1e-12 / abs 1e-9: observed ubuntu-vs-Mac drift is <= 1.5e-14 rel and 2.1e-12 abs."""
    assert (REL_TOL, ABS_TOL) == (1e-12, 1e-9)


def test_identical_frames_match():
    assert_matches_golden(_frame(), _frame())


def test_a_one_ulp_shift_matches():
    shifted = math.nextafter(3891.083970564594, math.inf)
    assert_matches_golden(_frame(estimate=[shifted, 0.0]), _frame())


def test_round_off_noise_around_zero_matches():
    """`anchor_adding_up_max_abs` is 0.0 on one platform and ~1e-12 on the other."""
    assert_matches_golden(_frame(residual=[0.0, None]), _frame())


def test_a_relative_move_above_the_tolerance_is_refused():
    moved = 3891.083970564594 * (1 + 1e-9)
    with pytest.raises(AssertionError, match="estimate"):
        assert_matches_golden(_frame(estimate=[moved, 0.0]), _frame())


def test_an_absolute_move_above_the_floor_is_refused_near_zero():
    with pytest.raises(AssertionError, match="estimate"):
        assert_matches_golden(_frame(estimate=[3891.083970564594, 2e-9]), _frame())


def test_a_null_against_a_value_is_refused_even_when_the_value_is_zero():
    """Null means "no estimate"; 0.0 means "estimated zero". No tolerance joins them."""
    with pytest.raises(AssertionError, match="residual"):
        assert_matches_golden(_frame(residual=[7.2760e-12, 0.0]), _frame())


def test_nan_matches_only_nan():
    with pytest.raises(AssertionError, match="estimate"):
        assert_matches_golden(_frame(estimate=[math.nan, 0.0]), _frame())
    assert_matches_golden(_frame(estimate=[math.nan, 0.0]), _frame(estimate=[math.nan, 0.0]))


def test_an_infinity_matches_only_the_same_infinity():
    with pytest.raises(AssertionError, match="estimate"):
        assert_matches_golden(_frame(estimate=[math.inf, 0.0]), _frame(estimate=[1e308, 0.0]))
    assert_matches_golden(_frame(estimate=[math.inf, 0.0]), _frame(estimate=[math.inf, 0.0]))


def test_an_integer_column_is_compared_exactly():
    """§12.6's released integers: a one-employee flip is a real change, never round-off."""
    with pytest.raises(AssertionError, match="estimate_integer"):
        assert_matches_golden(_frame(estimate_integer=[3892, 0]), _frame())


def test_a_string_column_is_compared_exactly():
    with pytest.raises(AssertionError, match="estimator_id"):
        assert_matches_golden(_frame(estimator_id=["a", "c"]), _frame())


def test_a_reordered_or_retyped_schema_is_refused():
    golden = _frame()
    with pytest.raises(AssertionError, match="schema"):
        assert_matches_golden(golden.select(reversed(golden.columns)), golden)
    with pytest.raises(AssertionError, match="schema"):
        assert_matches_golden(
            golden.with_columns(pl.col("estimate_integer").cast(pl.Int32)), golden
        )


def test_a_different_row_count_is_refused():
    with pytest.raises(AssertionError, match="rows"):
        assert_matches_golden(_frame().head(1), _frame())
