"""§12.3 bounded proportional scaling: bisection, strict failure, and infinite uppers."""

from __future__ import annotations

import math

import pytest

from logging_employment.errors import InfeasibleResidualError, WeightDomainError
from logging_employment.reconcile.allocate import Weights
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.scaling import Bounds, clipped_sum, scale_into_bounds

TOL = 1.0e-9
ITERS = 200


def _anchor(residual: float, cells: tuple[str, ...] = ("01", "02", "04")) -> Anchor:
    return Anchor("2024-03", residual, cells, "declared_national_total")


def _weights(values: dict[str, float]) -> Weights:
    return Weights(values=values, basis={k: "own_estimator" for k in values})


def _open_bounds(cells: tuple[str, ...]) -> Bounds:
    """The D1 shape: lower 0, upper null."""
    return Bounds(lower={c: 0.0 for c in cells}, upper={c: None for c in cells})


def test_with_open_bounds_scaling_reduces_to_the_proportional_split() -> None:
    """1,227 of 1,241 D1 cells have this shape, so this is the production path."""
    cells = ("01", "02", "04")
    out = scale_into_bounds(
        _anchor(100.0),
        _weights({"01": 1.0, "02": 2.0, "04": 1.0}),
        _open_bounds(cells),
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-7)
    assert out["02"] == pytest.approx(50.0, abs=1e-7)


def test_every_bound_is_respected_when_a_cap_binds() -> None:
    """Synthetic finite uppers: this property CANNOT be exercised on D1 data."""
    bounds = Bounds(
        lower={"01": 0.0, "02": 0.0, "04": 0.0},
        upper={"01": 10.0, "02": 1000.0, "04": 1000.0},
    )
    out = scale_into_bounds(
        _anchor(100.0),
        _weights({"01": 5.0, "02": 1.0, "04": 1.0}),
        bounds,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-7)
    assert out["01"] <= 10.0 + 1e-9
    for cell, value in out.items():
        assert value >= bounds.lower[cell] - 1e-9


def test_a_residual_below_the_summed_lower_bounds_fails() -> None:
    bounds = Bounds(
        lower={"01": 50.0, "02": 50.0, "04": 50.0},
        upper={"01": None, "02": None, "04": None},
    )
    with pytest.raises(InfeasibleResidualError) as excinfo:
        scale_into_bounds(
            _anchor(100.0),
            _weights({"01": 1.0, "02": 1.0, "04": 1.0}),
            bounds,
            tolerance=TOL,
            max_iterations=ITERS,
        )
    assert "150" in str(excinfo.value)


def test_a_residual_above_the_summed_upper_bounds_fails() -> None:
    bounds = Bounds(
        lower={"01": 0.0, "02": 0.0, "04": 0.0},
        upper={"01": 10.0, "02": 10.0, "04": 10.0},
    )
    with pytest.raises(InfeasibleResidualError):
        scale_into_bounds(
            _anchor(100.0),
            _weights({"01": 1.0, "02": 1.0, "04": 1.0}),
            bounds,
            tolerance=TOL,
            max_iterations=ITERS,
        )


def test_a_residual_exactly_equal_to_the_summed_lower_bounds_succeeds() -> None:
    """§12.3's predicate is STRICT (`>` and `<`), so equality is feasible.

    A guard written `sum_L >= R_t` would fail-close on the case the spec requires to succeed. It
    never fires on D1, where every lower bound is 0 and the minimum residual is far above it, but
    Stage 4's masks and any §17.3 random-feasible generator reach it directly.
    """
    bounds = Bounds(
        lower={"01": 30.0, "02": 30.0, "04": 40.0},
        upper={"01": 30.0, "02": 30.0, "04": 40.0},
    )
    out = scale_into_bounds(
        _anchor(100.0),
        _weights({"01": 1.0, "02": 1.0, "04": 1.0}),
        bounds,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out == pytest.approx({"01": 30.0, "02": 30.0, "04": 40.0}, abs=1e-7)


def test_a_null_upper_bound_is_infinite_and_never_becomes_a_number() -> None:
    """§9.3 forbids arbitrary caps; a null upper must stay open, not become a big float.

    The representation is asserted directly. Checking only the downstream `clipped_sum` has no
    detection power: under a 1e15 sentinel the clip still evaluates to 1e12 per cell and the sum
    is still 2e12, so a coercion that violates §9.3 would pass unnoticed.
    """
    cells = ("01", "02")
    bounds = _open_bounds(cells)
    assert math.isinf(bounds.upper_of("01"))
    assert clipped_sum(1e12, _weights({"01": 1.0, "02": 1.0}), bounds, cells) == pytest.approx(2e12)


def test_the_clipped_sum_is_monotone_in_lambda() -> None:
    """The property §12.3 cites as its justification for bisection."""
    cells = ("01", "02", "04")
    weights = _weights({"01": 1.0, "02": 2.0, "04": 3.0})
    bounds = Bounds(
        lower={"01": 1.0, "02": 0.0, "04": 0.0},
        upper={"01": 5.0, "02": None, "04": 20.0},
    )
    values = [clipped_sum(lam, weights, bounds, cells) for lam in (0.0, 0.5, 1.0, 2.0, 10.0, 100.0)]
    assert values == sorted(values)


def test_a_zero_residual_with_zero_lower_bounds_succeeds() -> None:
    cells = ("01", "02")
    out = scale_into_bounds(
        _anchor(0.0, cells),
        _weights({"01": 1.0, "02": 1.0}),
        _open_bounds(cells),
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(0.0, abs=1e-9)


def test_a_partial_weight_vector_is_refused_here_too() -> None:
    """The domain refusal is not bypassable by entering through the bounded path."""
    cells = ("01", "02", "04")
    with pytest.raises(WeightDomainError):
        scale_into_bounds(
            _anchor(100.0),
            _weights({"01": 1.0, "02": 1.0}),
            _open_bounds(cells),
            tolerance=TOL,
            max_iterations=ITERS,
        )


def test_weights_against_an_empty_missing_set_are_refused_here_too() -> None:
    """Same tightening as the unbounded entry point: the check precedes the shortcut.

    Returning `{}` for a populated weight vector against an empty missing set would let the
    bounded path launder a mismatch the unbounded path refuses.
    """
    with pytest.raises(WeightDomainError):
        scale_into_bounds(
            _anchor(0.0, ()),
            _weights({"01": 1.0}),
            _open_bounds(()),
            tolerance=TOL,
            max_iterations=ITERS,
        )


def test_a_float_rounded_lower_sum_equal_to_the_residual_still_succeeds() -> None:
    """The degenerate Σ L = R_t case must survive floating-point accumulation.

    Seven cells at lower 0.1 sum to 0.7000000000000001, so an exact `>` guard reads the case as
    infeasible and raises on precisely what §12.3's strict predicate requires to succeed. The
    guard is widened by the configured tolerance instead.
    """
    cells = tuple(f"{i:02d}" for i in range(7))
    assert sum(0.1 for _ in cells) > 0.7  # the rounding this test exists to survive
    bounds = Bounds(lower={c: 0.1 for c in cells}, upper={c: None for c in cells})
    out = scale_into_bounds(
        _anchor(0.7, cells),
        _weights({c: 1.0 for c in cells}),
        bounds,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out == pytest.approx({c: 0.1 for c in cells}, abs=1e-9)
