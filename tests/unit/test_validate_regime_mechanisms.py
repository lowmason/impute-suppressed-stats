"""Every regime declares WHY it has no selector, rather than the harness templating one reason."""

import pytest

from logging_employment.contracts import HOLDOUT_REGIMES
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.regimes import (
    REGIME_MECHANISMS,
    REGIME_SPECS,
    RegimeSpec,
)


def test_every_regime_declares_a_mechanism_from_the_closed_set():
    assert set(REGIME_SPECS) == set(HOLDOUT_REGIMES)
    for name, spec in REGIME_SPECS.items():
        assert spec.mechanism in REGIME_MECHANISMS, name


def test_a_masking_regime_has_a_selector_and_a_non_masking_one_has_a_reason():
    """The pairing R-S4C-1 asks for, as a property of all thirteen rather than a spot check."""
    for name, spec in REGIME_SPECS.items():
        if spec.mechanism == "qcew_mask":
            assert spec.select is not None, name
            assert spec.no_score_reason is None, name
        else:
            assert spec.select is None, name
            assert spec.no_score_reason, name


def test_a_spec_whose_mechanism_and_selector_disagree_is_refused():
    """The late `_SELECTORS` mutation at the foot of regimes.py is why this is enforced."""
    with pytest.raises(ConceptViolationError, match="qcew_mask"):
        RegimeSpec(
            name="invented",
            disposition="feasible",
            grain="single_month",
            select=None,
            mechanism="qcew_mask",
            no_score_reason=None,
        )


def test_the_cbp_reason_does_not_claim_an_entry_point_nothing_calls():
    """M8: the shipped manifest asserts `cbp_size_gaps` is exercised through its own entry point.

    `cbp_size_gap_keys` and `apply_cbp_gap` HAD no caller and no test anywhere in the package when
    this was measured (2026-09-08) — Task 6 of plan 12 gives them one — so the sentence was false,
    and it was false because it came from a `{name}` template shared with `rolling_origin`, for
    which it is true.
    """
    reason = REGIME_SPECS["cbp_size_gaps"].no_score_reason
    assert "exercised through its own entry point" not in reason
    assert "state-year" in reason
    assert "fallback arm" in reason


def test_the_rolling_origin_reason_is_scoped_to_the_registry_it_was_measured_against():
    """R-S4C-3: adding a smoothing estimator must invalidate the reason, not be inherited by it."""
    reason = REGIME_SPECS["rolling_origin"].no_score_reason
    assert "registry" in reason
    assert "2026-09-08" in reason


def test_no_reason_defers_the_question_to_a_later_plan():
    """R-S4C-2: a measurement or a declaration, never a deferral."""
    for name, spec in REGIME_SPECS.items():
        if spec.no_score_reason is None:
            continue
        lowered = spec.no_score_reason.lower()
        assert "deferred" not in lowered, name
        assert "not yet" not in lowered, name
