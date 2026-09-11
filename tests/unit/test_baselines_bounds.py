"""INV-002's per-cell half on the baseline production path (R-S5P-3).

The adding-up half has been enforced since Stage 3. The bounds half was not: nothing in
`baselines/` read `deterministic_bounds`, so an estimate above a solved upper bound shipped as
`anchored_and_reconciled`. On D1 that is harmless -- ALL 1,227 suppressed state cells are
`unbounded` with a null `selected_upper`, so no bound can bind -- and the two halves are exactly
that pair: the first cell that CAN violate must halt the run, and the D1 shape must be
bit-for-bit unchanged.

No `data/` is touched. The runner is driven on `harmonized_toy`, whose 2023-01 missing set is the
single state '04' against a residual of 50, so the allocated estimate is 50.0 for every estimator
and one finite upper of 10.0 is enough to fire.
"""

from __future__ import annotations

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from logging_employment.baselines.runner import (
    assert_within_bounds,
    run_baselines,
    state_total_bounds,
)
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA
from logging_employment.errors import BoundViolationError, ConceptViolationError
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


def test_an_estimate_above_its_solved_upper_bound_halts_the_run(
    harmonized_toy, appendix_a_config
) -> None:
    """INV-002 admits no per-month refusal, so this raises rather than writing a decline row."""
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config)
    target = _january_cell(unchecked)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (10.0 if cell == target else None) for cell in _cell_ids(unchecked)},
    )
    with pytest.raises(BoundViolationError) as excinfo:
        run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    message = str(excinfo.value)
    assert target in message
    assert "estimate=50.0" in message
    assert "[0.0, 10.0]" in message


def test_the_d1_shape_of_every_upper_null_changes_nothing(
    harmonized_toy, appendix_a_config
) -> None:
    """All 1,227 suppressed state cells are `unbounded` on D1, so the gate must be a no-op there.

    The denominator matters and an earlier draft got it wrong. 1,241 is D1's count of UNKNOWN
    cells across BOTH kinds -- 1,227 `state_total` plus 14 `national_size` -- so "1,227 of 1,241
    suppressed state cells" implied 14 suppressed state cells with a finite upper, which would
    mean a bound COULD bind and contradicts the very point being made. Measured from
    `runs/f03023ac9f3a/deterministic_bounds.parquet`: 4,716 `state_total|` rows, of which exactly
    1,227 are `unbounded` and 1,227 have a null `selected_upper`.
    """
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
