"""§10.5 declines on this window. The decline is the deliverable, not a gap."""

from __future__ import annotations

import polars as pl

from logging_employment.baselines.harvest import HarvestProportional
from logging_employment.baselines.interfaces import Decline, EstimatorContext
from logging_employment.reconcile.anchor import Anchor, observed_partition


def test_the_harvest_baseline_declines_rather_than_fabricating_a_factor(
    make_monthly, appendix_a_config
) -> None:
    """Roadmap Stage 3 exit criterion, verbatim: "declines to run without a harvest factor
    rather than fabricating one". §10.5 itself states no precondition, so the obligation is the
    roadmap's, and this test is what discharges it.
    """
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
    )
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame(),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    anchor = Anchor("2024-03", 40.0, ("01",), "declared_national_total")
    out = HarvestProportional().weights(context, anchor)
    assert isinstance(out, Decline)
    assert "harvest" in out.reason.lower()
    assert "Stage 7" in out.reason


def test_the_decline_is_a_pass_for_the_run_every_baseline_criterion(
    make_monthly, appendix_a_config
) -> None:
    """§17.4 row 4 says run every baseline on a frozen fixture. A clean decline satisfies it.

    Without this the Task 19 integration test would read the decline as a failed baseline and
    either be weakened or start excluding §10.5 -- both of which lose the criterion.
    """
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
    )
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame(),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    out = HarvestProportional().weights(
        context, Anchor("2024-03", 40.0, ("01",), "declared_national_total")
    )
    assert isinstance(out, Decline)
    assert out.reason  # a decline always carries a reason a reader can act on
