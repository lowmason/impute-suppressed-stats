"""INV-002's per-cell half on the baseline production path (R-S5P-3, then D-111).

The adding-up half has been enforced since Stage 3. The bounds half was not: nothing in
`baselines/` read `deterministic_bounds`, so an estimate above a solved upper bound shipped as
`anchored_and_reconciled`. Since `D-111` a published private `113` parent bounds most suppressed
state cells above, and §12.2's unbounded allocation sits above that parent on almost every month,
so the runner no longer HALTS on a binding bound: it reallocates by §12.3's bounded proportional
scaling. What still halts is a month whose bounds cannot hold its residual, and a value that escapes
its interval after scaling.

No `data/` is touched. The runner is driven on `harmonized_toy`. Its 2023-01 missing set is the
single state '04' against a residual of 50, so one finite upper of 10.0 cannot be scaled into; its
2023-02 missing set is '04' and '06' against 80, split 20/60 by establishments, so a cap of 50 on
'06' binds and '04' takes the remainder.
"""

from __future__ import annotations

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from logging_employment.baselines.runner import (
    REGISTRY,
    assert_within_bounds,
    run_baselines,
    state_total_bounds,
)
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA
from logging_employment.errors import (
    BoundViolationError,
    ConceptViolationError,
    InfeasibleResidualError,
)
from logging_employment.reconcile.scaling import Bounds

TOY_CELL = "state_total|04|2023-01|5|113310|NAICS 2022|ALL"


def _bounds_row(cell_id: str, lower: float | None, upper: float | None) -> dict[str, object]:
    """One `deterministic_bounds` row, every schema column filled.

    Written out rather than taken from a factory because the three columns this test cares about
    -- `cell_id`, `selected_lower`, `selected_upper` -- are the ones a factory would default.
    """
    return {
        "cell_id": cell_id,
        "component_id": "c000000",
        "rank": 1,
        "nullity": 1,
        "lp_lower": lower,
        "lp_upper": upper,
        "milp_lower": None,
        "milp_upper": None,
        "selected_lower": lower,
        "selected_upper": upper,
        "bound_status": "unbounded" if upper is None else "partially_identified",
        "exactly_identified": False,
        "integer_exactly_identified": False,
        "solver_status": "optimal",
        "solver_tolerance": 1e-7,
        "constraint_set_hash": "h",
    }


def _cell_ids(results: pl.DataFrame) -> list[str]:
    """Every `cell_id` the runner produced, read off its own output rather than recomputed.

    Recomputing the seven-field id here would re-derive it from the same `cell_id()` call the
    runner uses, so a keying bug would agree with itself and the bound would be checked against a
    cell nothing ever allocates.
    """
    return sorted(set(results["cell_id"].to_list()))


def _january_cell(results: pl.DataFrame) -> str:
    """The `cell_id` of the one suppressed cell in 2023-01: state '04', residual 50."""
    january = results.filter(
        (pl.col("reference_month") == "2023-01") & (pl.col("state_fips") == "04")
    )
    return str(january["cell_id"].to_list()[0])


def test_a_bound_its_months_residual_cannot_fit_under_halts_the_run(
    harmonized_toy, appendix_a_config
) -> None:
    """January's only missing cell is capped at 10 against a residual of 50: §12.3 refuses.

    Scaling cannot help a month whose uppers sum below its residual, and §12.3 forbids approximating
    that away, so this still HALTS -- as `InfeasibleResidualError`, not as a decline row.
    """
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config)
    target = _january_cell(unchecked)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (10.0 if cell == target else None) for cell in _cell_ids(unchecked)},
    )
    with pytest.raises(InfeasibleResidualError, match="fall below residual"):
        run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)


def test_an_estimate_above_its_upper_bound_is_scaled_into_it_rather_than_halting(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.3: February's residual of 80 splits 20/60 by establishments; capped at 50, '06' takes 50.

    The cap binds, so the scaling factor rises until the uncapped cell absorbs the rest: '04' goes
    from 20 to 30, the month still sums to its residual, and the integer release honours the cap.
    """
    proportional = [e for e in REGISTRY if e.estimator_id == "establishment_proportional"]
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config, estimators=proportional)
    february = unchecked.filter(pl.col("reference_month") == "2023-02")
    before = dict(zip(february["state_fips"], february["estimate"], strict=True))
    assert before == pytest.approx({"04": 20.0, "06": 60.0})
    capped = february.filter(pl.col("state_fips") == "06")["cell_id"].item()
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (50.0 if cell == capped else None) for cell in _cell_ids(unchecked)},
    )
    checked, _ = run_baselines(
        harmonized_toy, appendix_a_config, estimators=proportional, bounds=bounds
    )
    after = checked.filter(pl.col("reference_month") == "2023-02")
    estimates = dict(zip(after["state_fips"], after["estimate"], strict=True))
    assert estimates == pytest.approx({"04": 30.0, "06": 50.0})
    integers = dict(zip(after["state_fips"], after["estimate_integer"], strict=True))
    assert integers == {"04": 30, "06": 50}


def test_an_upper_a_solver_tolerance_below_an_integer_still_admits_that_integer(
    harmonized_toy, appendix_a_config
) -> None:
    """HiGHS reports an integer bound only to within `feasibility_tolerance`: 49.99999995 is 50.

    `integer_bounds` cuts the release with that tolerance, so '06' may carry 50. The integer check
    must admit what that cut admits, or a bound the solver could not tell from 50 halts the run.
    """
    proportional = [e for e in REGISTRY if e.estimator_id == "establishment_proportional"]
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config, estimators=proportional)
    february = unchecked.filter(pl.col("reference_month") == "2023-02")
    capped = february.filter(pl.col("state_fips") == "06")["cell_id"].item()
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (50.0 - 5e-8 if cell == capped else None) for cell in _cell_ids(unchecked)},
    )
    checked, _ = run_baselines(
        harmonized_toy, appendix_a_config, estimators=proportional, bounds=bounds
    )
    after = checked.filter(pl.col("reference_month") == "2023-02")
    integers = dict(zip(after["state_fips"], after["estimate_integer"], strict=True))
    assert integers == {"04": 30, "06": 50}


def test_a_month_whose_allocation_sits_inside_every_bound_is_left_bit_identical(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.2's fast path survives: a finite upper that does not bind moves nothing, not one bit."""
    unchecked, unchecked_audit = run_baselines(harmonized_toy, appendix_a_config)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper=dict.fromkeys(_cell_ids(unchecked), 1_000_000.0),
    )
    checked, checked_audit = run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    assert_frame_equal(checked, unchecked)
    assert_frame_equal(checked_audit, unchecked_audit)


def test_the_d1_shape_of_every_upper_null_changes_nothing(
    harmonized_toy, appendix_a_config
) -> None:
    """A cell with no finite upper -- every suppressed state cell before `D-111`, and every one
    without a published private `113` parent after it -- must leave the run bit-identical."""
    unchecked, unchecked_audit = run_baselines(harmonized_toy, appendix_a_config)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper=dict.fromkeys(_cell_ids(unchecked), None),
    )
    checked, checked_audit = run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    assert_frame_equal(checked, unchecked)
    assert_frame_equal(checked_audit, unchecked_audit)


def test_a_bounds_mapping_keyed_by_state_is_refused_rather_than_ignored(
    harmonized_toy, appendix_a_config
) -> None:
    """`upper_of` reads an absent key as `+inf`, so miskeying would make the gate a silent no-op.

    `scale_into_bounds` keys its `Bounds` by `anchor.missing_cells`, which on this path is a bare
    state -- so this is the mistake the type invites, not a hypothetical one.
    """
    with pytest.raises(ConceptViolationError, match="no deterministic bound"):
        run_baselines(
            harmonized_toy,
            appendix_a_config,
            bounds=Bounds(lower={"04": 0.0, "06": 0.0}, upper={"04": None, "06": None}),
        )


def test_the_integer_release_is_checked_too_not_only_the_float() -> None:
    """§12.6's largest-remainder rounding can move a value across a bound the float honoured."""
    bounds = Bounds(lower={TOY_CELL: 0.0}, upper={TOY_CELL: 10.4})
    cell_ids = {"04": TOY_CELL}
    assert_within_bounds(
        {"04": 10.4},
        bounds,
        cell_ids=cell_ids,
        estimator_id="equal_residual",
        reference_month="2023-01",
        tolerance=1e-9,
        quantity="estimate",
    )
    with pytest.raises(BoundViolationError, match="estimate_integer=11.0"):
        assert_within_bounds(
            {"04": 11.0},
            bounds,
            cell_ids=cell_ids,
            estimator_id="equal_residual",
            reference_month="2023-01",
            tolerance=1e-9,
            quantity="estimate_integer",
        )


def test_the_loader_keeps_state_total_cells_and_reads_a_null_upper_as_unbounded() -> None:
    """A national size row in the same table is not a state-total bound and must not be keyed in."""
    other = "state_total|06|2023-02|5|113310|NAICS 2022|ALL"
    frame = pl.DataFrame(
        [
            _bounds_row(TOY_CELL, 0.0, None),
            _bounds_row(other, 3.0, 12.0),
            _bounds_row("national_size|US|2023-01|5|113310|NAICS 2022|1", 1.0, 2.0),
        ],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    bounds = state_total_bounds(frame)
    assert sorted(bounds.lower) == [TOY_CELL, other]
    assert bounds.upper_of(TOY_CELL) == float("inf")
    assert bounds.upper_of(other) == 12.0
    assert bounds.lower[other] == 3.0


def test_the_loader_refuses_two_rows_for_one_cell() -> None:
    """`component_id`/`rank`/`nullity` mean the schema admits duplicates; D1 having one is a
    measurement. `dict(zip(...))` would keep the last row and check against an arbitrary one."""
    frame = pl.DataFrame(
        [_bounds_row(TOY_CELL, 0.0, None), _bounds_row(TOY_CELL, 0.0, 9.0)],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    with pytest.raises(ConceptViolationError, match="more than one row"):
        state_total_bounds(frame)


def test_the_loader_refuses_a_null_lower_while_accepting_a_null_upper() -> None:
    """§9.3's nonnegativity holds for every cell, so a null lower is unsolved, not unbounded."""
    frame = pl.DataFrame(
        [_bounds_row(TOY_CELL, None, None)],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    with pytest.raises(ConceptViolationError, match="null selected_lower"):
        state_total_bounds(frame)
