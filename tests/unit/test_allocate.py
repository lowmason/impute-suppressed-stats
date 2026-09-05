"""§12.2's no-bound fast path, and the refusal that keeps a composite declared."""

from __future__ import annotations

import pytest

from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.allocate import Weights, allocate, check_domain
from logging_employment.reconcile.anchor import Anchor


def _anchor(residual: float = 100.0, cells: tuple[str, ...] = ("01", "02", "04")) -> Anchor:
    return Anchor(
        reference_month="2024-03",
        residual=residual,
        missing_cells=cells,
        anchor_basis="declared_national_total",
    )


def _weights(values: dict[str, float]) -> Weights:
    return Weights(values=values, basis={k: "own_estimator" for k in values})


def test_the_allocation_sums_exactly_to_the_residual() -> None:
    out = allocate(_anchor(), _weights({"01": 1.0, "02": 2.0, "04": 1.0}))
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-9)
    assert out["02"] == pytest.approx(50.0)


def test_a_weight_vector_missing_a_cell_is_refused_not_normalized() -> None:
    """Normalizing a partial vector silently reallocates the absent cell's share.

    That is fabricating an allocation, so it is refused. A baseline that cannot weight every cell
    must declare a composite and record `establishment_fallback` per cell, not quietly drop one.
    """
    with pytest.raises(WeightDomainError) as excinfo:
        check_domain(_weights({"01": 1.0, "02": 2.0}), _anchor())
    assert "04" in str(excinfo.value)


def test_a_weight_vector_with_an_extra_cell_is_refused() -> None:
    with pytest.raises(WeightDomainError):
        check_domain(_weights({"01": 1.0, "02": 1.0, "04": 1.0, "05": 1.0}), _anchor())


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
def test_a_non_positive_or_nan_weight_is_refused(bad: float) -> None:
    """§12.2 says "positive raw weights". A zero weight is a silent decline for that cell."""
    with pytest.raises(WeightDomainError):
        check_domain(_weights({"01": 1.0, "02": bad, "04": 1.0}), _anchor())


def test_a_zero_residual_allocates_zero_to_every_cell() -> None:
    """R_t = 0 is feasible, not an error: §12.3's predicate is strict."""
    out = allocate(_anchor(residual=0.0), _weights({"01": 1.0, "02": 2.0, "04": 1.0}))
    assert set(out.values()) == {0.0}


def test_an_empty_missing_set_allocates_nothing() -> None:
    out = allocate(_anchor(residual=0.0, cells=()), Weights(values={}, basis={}))
    assert out == {}


def test_a_declared_composite_is_permitted_and_its_basis_survives() -> None:
    """Own weight where defined, establishment weight elsewhere -- recorded per cell."""
    weights = Weights(
        values={"01": 1.0, "02": 2.0, "04": 1.0},
        basis={"01": "own_estimator", "02": "own_estimator", "04": "establishment_fallback"},
    )
    check_domain(weights, _anchor())
    out = allocate(_anchor(), weights)
    assert sum(out.values()) == pytest.approx(100.0)
    assert weights.basis["04"] == "establishment_fallback"


def test_weights_against_an_empty_missing_set_are_refused_not_ignored() -> None:
    """The empty-missing-set shortcut must not run before the domain check.

    Returning `{}` here would discard a populated weight vector without a word -- the same silent
    mismatch `check_domain` exists to prevent, only inverted. The plan ordered the shortcut first;
    ordering the check first is strictly tighter and costs nothing.
    """
    with pytest.raises(WeightDomainError):
        allocate(_anchor(residual=0.0, cells=()), _weights({"01": 1.0}))
