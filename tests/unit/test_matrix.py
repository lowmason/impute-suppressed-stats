"""§12.5 row-and-column reconciliation. Synthetic by construction: D1 has no state-by-size cells."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.errors import IncompatibleMarginError
from logging_employment.reconcile.matrix import reconcile_matrix

TOL = 1.0e-9
ITERS = 1000
FLOOR = 1.0e-12


def test_row_totals_alone_are_matched_exactly() -> None:
    seed = np.array([[1.0, 1.0], [2.0, 2.0]])
    out = reconcile_matrix(
        seed, np.array([10.0, 20.0]), None, tolerance=TOL, max_iterations=ITERS, floor=FLOOR
    )
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-7)


def test_row_and_column_reconciliation_is_exact() -> None:
    """§17.3's property. Consistent margins: both totals sum to 30."""
    seed = np.array([[1.0, 3.0], [2.0, 1.0]])
    out = reconcile_matrix(
        seed,
        np.array([10.0, 20.0]),
        np.array([12.0, 18.0]),
        tolerance=TOL,
        max_iterations=ITERS,
        floor=FLOOR,
    )
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-6)
    assert out.sum(axis=0) == pytest.approx([12.0, 18.0], abs=1e-6)


def test_inconsistent_margins_fail_rather_than_forcing_convergence() -> None:
    """§12.5's third rule, verbatim: "fail and diagnose rather than forcing convergence"."""
    seed = np.ones((2, 2))
    with pytest.raises(IncompatibleMarginError) as excinfo:
        reconcile_matrix(
            seed,
            np.array([10.0, 20.0]),
            np.array([12.0, 99.0]),
            tolerance=TOL,
            max_iterations=ITERS,
            floor=FLOOR,
        )
    assert "30" in str(excinfo.value)
    assert "111" in str(excinfo.value)


def test_a_zero_seed_row_is_floored_rather_than_dividing_by_zero() -> None:
    seed = np.array([[0.0, 0.0], [1.0, 1.0]])
    out = reconcile_matrix(
        seed, np.array([10.0, 20.0]), None, tolerance=TOL, max_iterations=ITERS, floor=FLOOR
    )
    assert np.all(np.isfinite(out))
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-7)


def test_a_seed_zero_pattern_that_cannot_meet_the_margins_fails_loudly() -> None:
    """The margins are consistent and a feasible point exists, yet IPF cannot reach it.

    With a seed of [[0, 3], [2, 0]] the floored zeros can never grow enough against the column
    constraints, and the iteration settles on row sums [5, 25] against requested [10, 20] --
    while [[7.5, 2.5], [17.5, 2.5]] satisfies both margins exactly. The up-front consistency
    check passes (both margins sum to 30), so without a post-projection check this returns a
    silently wrong matrix. §12.5 requires failing and diagnosing instead.
    """
    seed = np.array([[0.0, 3.0], [2.0, 0.0]])
    with pytest.raises(IncompatibleMarginError, match="did not converge"):
        reconcile_matrix(
            seed,
            np.array([10.0, 20.0]),
            np.array([25.0, 5.0]),
            tolerance=TOL,
            max_iterations=ITERS,
            floor=FLOOR,
        )


def test_the_achieved_margin_check_does_not_reject_ordinary_convergence() -> None:
    """The post-check must bite only on non-convergence, not on healthy IPF residue.

    Randomised consistent margins over strictly positive seeds -- the shape §17.3's property 5
    generates -- must all pass, or the check would turn a working reconciliation into a halt.
    """
    rng = np.random.default_rng(20260905)
    for _ in range(25):
        rows, cols = int(rng.integers(2, 6)), int(rng.integers(2, 6))
        seed = rng.uniform(0.1, 10.0, size=(rows, cols))
        row_totals = rng.uniform(10.0, 100.0, size=rows)
        column_totals = rng.uniform(1.0, 10.0, size=cols)
        column_totals *= row_totals.sum() / column_totals.sum()
        out = reconcile_matrix(
            seed,
            row_totals,
            column_totals,
            tolerance=TOL,
            max_iterations=5000,
            floor=FLOOR,
        )
        assert out.sum(axis=1) == pytest.approx(row_totals, rel=1e-4)
        assert out.sum(axis=0) == pytest.approx(column_totals, rel=1e-4)
