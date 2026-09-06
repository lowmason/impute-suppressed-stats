"""The Estimator protocol and the declared-composite rule that keeps §10.8 populated."""

from __future__ import annotations

import pytest

from logging_employment.baselines.interfaces import FALLBACK, OWN, Decline, compose
from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.anchor import Anchor

CELLS = ("01", "02", "04")


def _anchor() -> Anchor:
    return Anchor("2024-03", 100.0, CELLS, "declared_national_total")


def test_full_own_coverage_needs_no_fallback() -> None:
    w = compose(
        {"01": 1.0, "02": 2.0, "04": 3.0},
        {"01": 9.0, "02": 9.0, "04": 9.0},
        _anchor(),
        allowed=True,
    )
    assert set(w.basis.values()) == {"own_estimator"}


def test_partial_own_coverage_composes_and_records_the_basis_per_cell() -> None:
    """Two gap cells, and the WHOLE mapping: labelling only the first gap must not pass."""
    anchor = Anchor("2024-03", 100.0, ("01", "02", "04", "05"), "declared_national_total")
    w = compose(
        {"01": 1.0, "02": 2.0},
        {"01": 9.0, "02": 9.0, "04": 7.0, "05": 8.0},
        anchor,
        allowed=True,
    )
    assert w.values["04"] == 7.0
    assert w.values["05"] == 8.0
    assert w.basis == {"01": OWN, "02": OWN, "04": FALLBACK, "05": FALLBACK}


def test_composition_refused_by_config_yields_a_decline_not_a_silent_subset() -> None:
    out = compose(
        {"01": 1.0, "02": 2.0}, {"01": 9.0, "02": 9.0, "04": 7.0}, _anchor(), allowed=False
    )
    assert isinstance(out, Decline)
    assert "04" in out.reason


def test_a_fallback_that_cannot_cover_the_gap_is_refused() -> None:
    """§10.2's rung is complete on D1, but the code may not assume that."""
    with pytest.raises(WeightDomainError):
        compose({"01": 1.0}, {"01": 9.0, "02": 9.0}, _anchor(), allowed=True)


def test_a_non_positive_own_weight_falls_back_rather_than_poisoning_the_vector() -> None:
    """§12.2 requires positive weights; a zero own-weight is not one."""
    w = compose(
        {"01": 1.0, "02": 0.0, "04": 3.0},
        {"01": 9.0, "02": 5.0, "04": 9.0},
        _anchor(),
        allowed=True,
    )
    assert w.values["02"] == 5.0
    assert w.basis["02"] == "establishment_fallback"


def test_arms_in_incommensurable_units_are_refused() -> None:
    """The units guard. Measured on 2024-03: without it, nine states with full observed
    histories received 0.58 of 1,589 employees between them — 0.037% of the residual — while a
    single fallback state took 1,257, purely because establishment counts are ~1e4 larger than
    national shares. `allocate` normalizes the union, so the larger-scaled arm wins outright and
    the output still looks well-formed: positive everywhere and summing exactly to R_t.
    """
    shares = {"01": 0.0155, "02": 0.0029}
    counts = {"01": 77.0, "02": 72.0, "04": 16.0}
    with pytest.raises(WeightDomainError, match="scale"):
        compose(shares, counts, _anchor(), allowed=True)


def test_arms_on_a_common_scale_compose_without_complaint() -> None:
    """The same shapes, both arms in employees, pass the guard."""
    own = {"01": 24.6, "02": 4.6}
    fallback = {"01": 30.0, "02": 28.0, "04": 6.2}
    w = compose(own, fallback, _anchor(), allowed=True)
    assert w.basis["04"] == "establishment_fallback"
    assert w.values["04"] == 6.2


def test_the_units_guard_is_skipped_when_there_is_nothing_to_compare() -> None:
    """With no usable own weight the vector is all-fallback, and normalization is scale-free."""
    w = compose({}, {"01": 9.0, "02": 9.0, "04": 7.0}, _anchor(), allowed=True)
    assert set(w.basis.values()) == {"establishment_fallback"}
