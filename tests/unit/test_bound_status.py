"""One classification function, one test per label it can return."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import bounds, system
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA, HarmonizedData

REPO = Path(__file__).resolve().parents[2]
TOLERANCE = 1.0e-7


def test_a_published_cell_is_observed() -> None:
    status, exact, integer_exact = bounds.classify_bound_status(
        observation_status="observed",
        lower=700.0,
        upper=700.0,
        is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "observed"
    # True because the interval *is* a point. Whether that point may be re-published is a
    # disclosure question, and `disclosure.flags` answers it -- this field does not.
    assert exact is True and integer_exact is True


def test_an_integer_cell_pinned_between_two_consecutive_bounds_is_exactly_recoverable() -> None:
    status, exact, integer_exact = bounds.classify_bound_status(
        observation_status="suppressed",
        lower=41.6,
        upper=42.3,
        is_integer=True,
        tolerance=TOLERANCE,
    )
    # ceil(41.6) == floor(42.3) == 42 -- §9.6's integer exactness rule: exactly one integer lies
    # in the interval. The plan's original numbers here were [41.2, 41.9], where ceil is 42 and
    # floor is 41, so *no* integer lies in the interval at all; the width is unchanged at 0.7 so
    # the contrast with the continuous case below still holds.
    assert status == "exactly_recoverable"
    assert exact is True and integer_exact is True


def test_the_same_width_on_a_continuous_cell_is_only_partially_identified() -> None:
    status, exact, _ = bounds.classify_bound_status(
        observation_status="suppressed",
        lower=41.2,
        upper=41.9,
        is_integer=False,
        tolerance=TOLERANCE,
    )
    assert status == "partially_identified"
    assert exact is False


def test_a_finite_interval_wider_than_tolerance_is_partially_identified() -> None:
    status, _, _ = bounds.classify_bound_status(
        observation_status="suppressed",
        lower=400.0,
        upper=530.0,
        is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "partially_identified"


def test_a_cell_with_no_upper_bound_is_unbounded() -> None:
    status, exact, _ = bounds.classify_bound_status(
        observation_status="suppressed",
        lower=0.0,
        upper=None,
        is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "unbounded"
    assert exact is False


def test_stage_two_never_emits_a_model_dependent_status() -> None:
    # `model_estimable` and `model_only` say something about a model, and §9.1 forbids one here.
    # Stage 8's §15.3 mapping is where a released cell acquires a model-dependence level.
    returned = {
        bounds.classify_bound_status(
            observation_status=obs, lower=lo, upper=hi, is_integer=True, tolerance=TOLERANCE
        )[0]
        for obs in ("observed", "suppressed", "true_zero")
        for lo, hi in ((0.0, None), (1.0, 1.0), (1.0, 9.0))
    }
    assert returned & {"model_estimable", "model_only"} == set()


def test_a_narrow_component_triggers_the_integer_resolve(make_monthly, make_size) -> None:
    # The MILP *switch*, not the tightening: two classes of one establishment each, in [0, 4] and
    # [5, 9], summing to 11. The LP gives [2, 4] and [7, 9] -- widths of 2, below the configured
    # threshold of 25 -- so an integer re-solve runs and its values are the ones selected. That
    # integrality can actually move a bound is §17.2's property, tested on a toy in Task 15.
    monthly = make_monthly(
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 11,
            "employment_raw": "11",
            "qtrly_establishments": 2,
        }
    )
    size = make_size(
        {
            "size_class": "1",
            "establishments": 1,
            "employment": None,
            "size_lower": 0,
            "size_upper": 4,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
        {
            "size_class": "2",
            "establishments": 1,
            "employment": None,
            "size_lower": 5,
            "size_upper": 9,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
    )
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    result = bounds.solve_bounds(system.build_constraint_system(data, cfg), cfg.constraints)
    unknown = result.bounds.filter(pl.col("bound_status") != "observed")
    assert unknown.height == 2
    assert unknown["milp_lower"].null_count() == 0  # width 2 < the configured MILP threshold of 25
    assert unknown["selected_lower"].to_list() == unknown["milp_lower"].to_list()


def test_solve_bounds_returns_one_row_per_cell_in_the_shipped_schema(
    make_monthly, make_size
) -> None:
    monthly = make_monthly(
        {
            "state_fips": "01",
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 200,
            "qtrly_establishments": 60,
        },
    )
    size = make_size(
        {
            "size_class": "1",
            "establishments": 60,
            "employment": 200,
            "size_lower": 0,
            "size_upper": 4,
        }
    )
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    built = system.build_constraint_system(data, cfg)
    result = bounds.solve_bounds(built, cfg.constraints)
    assert result.bounds.schema == pl.Schema(DETERMINISTIC_BOUNDS_SCHEMA)
    assert result.bounds.height == built.cells.height
    assert set(result.bounds["constraint_set_hash"]) == {built.constraint_set_hash}
    assert result.components["component_id"].n_unique() == result.components.height


def test_an_integer_interval_containing_no_integer_is_not_called_exactly_recoverable() -> None:
    # [41.2, 41.9] holds no integer, so `ceil == floor` is false and the cell is reported as
    # partially identified rather than exactly recovered. With `enforce_integrality` on, an
    # interval this narrow triggers the MILP re-solve, which reports the component infeasible
    # before any label is assigned -- this classification is what remains when integrality is
    # configured off, and it must not claim a recovery it cannot make.
    status, exact, integer_exact = bounds.classify_bound_status(
        observation_status="suppressed",
        lower=41.2,
        upper=41.9,
        is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "partially_identified"
    assert exact is False and integer_exact is False
