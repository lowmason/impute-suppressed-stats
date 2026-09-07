"""The one fallback construction, and each estimator's declared intensity (R-COMP-5 to R-COMP-7)."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.fallback import (
    DISCLOSED_QCEW,
    FALLBACK_INTENSITIES,
    NATIONAL_CBP_MARCH,
    declared_fallback,
    disclosed_intensity,
    establishment_fallback,
    national_cbp_march_intensity,
    resolve_intensity,
)
from logging_employment.baselines.harvest import HarvestProportional
from logging_employment.baselines.historical import LastObservedShare
from logging_employment.baselines.intensity import CbpIntensity
from logging_employment.baselines.interfaces import EmployeeWeights, EstimatorContext
from logging_employment.baselines.regression import ConstrainedRegression
from logging_employment.baselines.runner import REGISTRY
from logging_employment.baselines.simple import EqualAllocation, establishment_weights
from logging_employment.errors import ConceptViolationError
from logging_employment.reconcile.anchor import Partition, national_residual, observed_partition

COMPOSING_IDS = {
    "share_last_observed",
    "share_same_month_prior_year",
    "share_rolling_median",
    "share_exponentially_weighted",
    "share_break_adjusted",
    "cbp_intensity",
    "constrained_regression",
}


def _panel(make_monthly) -> pl.DataFrame:
    """One month: state 01 disclosed at 40 over 4, state 02 suppressed with 6 establishments."""
    return make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 100,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 40,
            "qtrly_establishments": 4,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 6,
            "observation_status": "suppressed",
        },
    )


def _cbp() -> pl.DataFrame:
    """A CBP frame for 2024 with one state: 70 employees over 10 establishments, so the national
    March intensity is 7.0 and is distinguishable from the disclosed 10.0."""
    return pl.DataFrame(
        {
            "reference_year": [2024],
            "state_fips": ["01"],
            "size_code": ["001"],
            "establishments": [10],
            "employment": [70],
        }
    )


def _context_and_anchor(monthly, cfg, cbp=None):
    partitions = observed_partition(monthly)
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame() if cbp is None else cbp,
        partitions=partitions,
        config=cfg,
    )
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    return context, anchor


def test_every_estimator_declares_a_fallback_intensity_or_declares_none() -> None:
    """R-COMP-6. The declaration is a property of the estimator, so it is readable without
    reading a method body -- which is what lets the manifest report it."""
    for estimator in REGISTRY:
        declared = estimator.fallback_intensity
        assert declared is None or declared in FALLBACK_INTENSITIES, estimator.estimator_id
        assert (estimator.estimator_id in COMPOSING_IDS) == (declared is not None)


def test_the_two_families_declare_the_two_different_intensities() -> None:
    """R-COMP-7: the divergence is permitted and declared, not standardised away."""
    declared = {e.estimator_id: e.fallback_intensity for e in REGISTRY}
    assert declared["share_last_observed"] == DISCLOSED_QCEW
    assert declared["constrained_regression"] == DISCLOSED_QCEW
    assert declared["cbp_intensity"] == NATIONAL_CBP_MARCH
    assert declared["equal_residual"] is None
    assert declared["harvest_proportional"] is None


@pytest.mark.parametrize(
    ("estimator", "expected_intensity"),
    [
        # The disclosed ratio of two published sums on this fixture: 40 employees over 4
        # establishments.
        (LastObservedShare(), 10.0),
        (ConstrainedRegression(), 10.0),
        # §10.4's national CBP March intensity: 70 over 10. A DIFFERENT number from the same
        # fixture, which is what makes this parametrize check R-COMP-7's divergence rather than
        # three readings of one class attribute.
        (CbpIntensity(), 7.0),
    ],
)
def test_the_shipped_fallback_arm_is_the_declared_intensity_times_exposure(
    estimator, expected_intensity, make_monthly, appendix_a_config
) -> None:
    """T-4, per estimator rather than for the registry in aggregate.

    Two things, and the second is why `CbpIntensity` is in the list: the intensity is resolved
    independently here and compared against the arm the estimator actually ships, so a declaration
    that drifts from its body fails rather than agreeing with itself; and the expected value is
    pinned per estimator, so the two families having to disagree (R-COMP-7) is asserted rather
    than assumed. A parametrize over two estimators that declare the SAME intensity would pass on
    a registry where every estimator read one shared constant.
    """
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config, cbp=_cbp())
    intensity = resolve_intensity(estimator.fallback_intensity, context, anchor)
    assert intensity == pytest.approx(expected_intensity)
    exposure = establishment_weights(context, anchor)
    arm = declared_fallback(estimator, context, anchor)
    assert arm.values == {
        cell: pytest.approx(value * intensity) for cell, value in exposure.items()
    }


def test_the_fallback_construction_returns_the_declared_type(
    make_monthly, appendix_a_config
) -> None:
    """R-COMP-5: one construction, and what it returns is what `compose` accepts."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    arm = establishment_fallback(context, anchor, intensity=2.0)
    assert isinstance(arm, EmployeeWeights)
    assert arm.values == {"02": 12.0}


def test_an_undeclared_intensity_name_is_refused_by_name(make_monthly, appendix_a_config) -> None:
    """A typo in a declaration must not reach the manifest as if it were a choice.

    A real context and anchor, not `None`: passing `None` would pass today only because the
    membership guard happens to precede every use of them, and would turn into an `AttributeError`
    on `None` -- not the refusal this test names -- the moment those statements were reordered.
    """
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    with pytest.raises(ConceptViolationError, match="declared fallback intensity"):
        resolve_intensity("employees_per_acre", context, anchor)


@pytest.mark.parametrize("estimator", [EqualAllocation(), HarvestProportional()])
def test_an_estimator_that_declares_no_intensity_cannot_build_a_fallback_arm(
    estimator, make_monthly, appendix_a_config
) -> None:
    """R-COMP-6's other half: a composing estimator with no declaration is a bug, not a default."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    with pytest.raises(ConceptViolationError, match="fallback_intensity"):
        declared_fallback(estimator, context, anchor)


def test_the_disclosed_intensity_refuses_a_partition_that_is_not_the_anchors(
    make_monthly, appendix_a_config
) -> None:
    """T-5 / R-COMP-8. The residual and the intensity are two readings of one disclosed set.

    A Stage 4 harness that masks a cell for the anchor but hands the estimator the unmasked
    partitions would scale the fallback off a disclosed set the residual was never computed over.
    Nothing signals that: both numbers are positive and the month still sums to R_t.
    """
    monthly = _panel(make_monthly)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")

    march = partitions["2024-03"]
    states = monthly.filter(pl.col("area_type") == "state")
    masked = {
        "2024-03": Partition(
            disclosed=march.disclosed.filter(pl.col("state_fips") != "01"),
            missing=states.filter(pl.col("state_fips").is_in(["01", "02"])),
        )
    }
    stale = EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=masked, config=appendix_a_config
    )
    with pytest.raises(ConceptViolationError, match="one partition"):
        disclosed_intensity(stale, anchor)


def test_the_disclosed_intensity_accepts_the_partition_the_anchor_came_from(
    make_monthly, appendix_a_config
) -> None:
    """The other half: agreement is the normal case and must not raise."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    assert disclosed_intensity(context, anchor) == pytest.approx(10.0)


def test_the_national_cbp_intensity_reads_no_partition_and_is_unaffected(
    make_monthly, appendix_a_config
) -> None:
    """R-COMP-8 binds the intensity DERIVED FROM THE DISCLOSED SET. §10.4's is derived from CBP,
    so the same stale context leaves it untouched -- the check is placed where it can bite."""
    monthly = _panel(make_monthly)
    cbp = _cbp()
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    states = monthly.filter(pl.col("area_type") == "state")
    stale = EstimatorContext(
        monthly=monthly,
        cbp=cbp,
        partitions={
            "2024-03": Partition(
                disclosed=partitions["2024-03"].disclosed.filter(pl.col("state_fips") != "01"),
                missing=states,
            )
        },
        config=appendix_a_config,
    )
    assert national_cbp_march_intensity(stale, anchor) == pytest.approx(7.0)
