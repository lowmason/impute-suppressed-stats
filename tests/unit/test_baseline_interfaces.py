"""The Estimator protocol and the declared-composite rule that keeps §10.8 populated."""

from __future__ import annotations

import pytest

from logging_employment.baselines.interfaces import (
    FALLBACK,
    OWN,
    Decline,
    EmployeeWeights,
    compose,
)
from logging_employment.errors import ConceptViolationError, WeightDomainError
from logging_employment.reconcile.anchor import Anchor

CELLS = ("01", "02", "04")


def _anchor() -> Anchor:
    return Anchor("2024-03", 100.0, CELLS, "declared_national_total")


def test_full_own_coverage_needs_no_fallback() -> None:
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0, "04": 3.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 9.0}),
        _anchor(),
        allowed=True,
    )
    assert set(w.basis.values()) == {"own_estimator"}


def test_partial_own_coverage_composes_and_records_the_basis_per_cell() -> None:
    """Two gap cells, and the WHOLE mapping: labelling only the first gap must not pass."""
    anchor = Anchor("2024-03", 100.0, ("01", "02", "04", "05"), "declared_national_total")
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0, "05": 8.0}),
        anchor,
        allowed=True,
    )
    assert w.values["04"] == 7.0
    assert w.values["05"] == 8.0
    assert w.basis == {"01": OWN, "02": OWN, "04": FALLBACK, "05": FALLBACK}


def test_composition_refused_by_config_yields_a_decline_not_a_silent_subset() -> None:
    out = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0}),
        _anchor(),
        allowed=False,
    )
    assert isinstance(out, Decline)
    assert "04" in out.reason


def test_a_fallback_that_cannot_cover_the_gap_is_refused() -> None:
    """§10.2's rung is complete on D1, but the code may not assume that."""
    with pytest.raises(WeightDomainError):
        compose(
            EmployeeWeights({"01": 1.0}),
            EmployeeWeights({"01": 9.0, "02": 9.0}),
            _anchor(),
            allowed=True,
        )


def test_a_non_positive_own_weight_falls_back_rather_than_poisoning_the_vector() -> None:
    """§12.2 requires positive weights; a zero own-weight is not one.

    Also pins the negative half of `EmployeeWeights`' contract: the type does NOT validate
    positivity. A zero here is a cell with no own signal, and `compose` hands it to the fallback.
    """
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 0.0, "04": 3.0}),
        EmployeeWeights({"01": 9.0, "02": 5.0, "04": 9.0}),
        _anchor(),
        allowed=True,
    )
    assert w.values["02"] == 5.0
    assert w.basis["02"] == "establishment_fallback"


def test_a_raw_dict_cannot_be_passed_as_an_arm() -> None:
    """T-1. The substitution the deleted magnitude guard could not see.

    Measured on the D1 window: replacing the scaled fallback with a raw establishment count
    produced ratios of 0.182-0.811 for the share family and 0.160-0.316 for §10.4 — entirely
    inside the honest 0.947-4.996 range — and shipped own-cell estimates up to 6.12x too large
    with zero guard trips, every value positive and every month summing exactly to the residual.
    So this asserts a CONSTRUCTION failure, never a magnitude: no threshold separates the two.
    """
    raw_establishment_counts = {"01": 9.0, "02": 9.0, "04": 7.0}
    with pytest.raises(ConceptViolationError, match="EmployeeWeights"):
        compose(
            EmployeeWeights({"01": 1.0, "02": 2.0}),
            raw_establishment_counts,
            _anchor(),
            allowed=True,
        )
    with pytest.raises(ConceptViolationError, match="EmployeeWeights"):
        compose(
            {"01": 1.0, "02": 2.0},
            EmployeeWeights(raw_establishment_counts),
            _anchor(),
            allowed=True,
        )


def test_an_empty_own_arm_composes_into_an_all_fallback_composite() -> None:
    """T-2 / R-COMP-2. §10.6 composes entirely from the fallback when the fit has too few rows,
    so an empty own arm is a valid composite rather than an error the type may refuse."""
    w = compose(
        EmployeeWeights({}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0}),
        _anchor(),
        allowed=True,
    )
    assert set(w.basis.values()) == {"establishment_fallback"}
    assert w.values == {"01": 9.0, "02": 9.0, "04": 7.0}
