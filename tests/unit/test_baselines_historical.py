"""§10.3's five share variants, the vintage rule, and the composite that keeps them running."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.historical import (
    BreakAdjustedShare,
    ExponentiallyWeightedShare,
    LastObservedShare,
    RollingMedianShare,
    SameMonthPreviousYearShare,
    observed_share_history,
)
from logging_employment.baselines.interfaces import FALLBACK, OWN, EstimatorContext
from logging_employment.reconcile.anchor import Anchor, observed_partition

ALL_FIVE = [
    LastObservedShare,
    SameMonthPreviousYearShare,
    RollingMedianShare,
    ExponentiallyWeightedShare,
    BreakAdjustedShare,
]


def test_section_10_3_ships_exactly_five_variants() -> None:
    """The spec lists five; a sixth or a fourth is a spec-coverage defect, not a style choice."""
    assert len(ALL_FIVE) == 5
    assert len({cls().estimator_id for cls in ALL_FIVE}) == 5


def _history(make_monthly) -> pl.DataFrame:
    rows = []
    for i, month in enumerate(["2023-01", "2023-02", "2023-03", "2024-03"]):
        rows.append(
            {
                "area_type": "national",
                "area_fips": "US000",
                "state_fips": None,
                "aggregation_level": "18",
                "reference_month": month,
                "employment_value": 100,
                "qtrly_establishments": 10,
            }
        )
        rows.append(
            {
                "state_fips": "01",
                "area_fips": "01000",
                "reference_month": month,
                "employment_value": 40 + i,
                "qtrly_establishments": 4,
                "observation_status": "observed",
            }
        )
        rows.append(
            {
                "state_fips": "02",
                "area_fips": "02000",
                "reference_month": month,
                "employment_value": None,
                "qtrly_establishments": 6,
                "observation_status": "suppressed",
            }
        )
    return make_monthly(*rows)


def _context(monthly, cfg) -> EstimatorContext:
    return EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=observed_partition(monthly), config=cfg
    )


@pytest.mark.parametrize("cls", ALL_FIVE)
def test_every_variant_produces_positive_weights_for_a_state_with_history(
    cls, make_monthly, appendix_a_config
) -> None:
    monthly = _history(make_monthly)
    # State 01 has history; force it into the missing set so a share exists to use.
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")
    out = cls().weights(_context(monthly, appendix_a_config), anchor)
    assert out.values["01"] > 0.0
    assert out.basis["01"] == OWN


@pytest.mark.parametrize("cls", ALL_FIVE)
def test_a_state_with_no_observed_history_takes_the_declared_fallback(
    cls, make_monthly, appendix_a_config
) -> None:
    """Six D1 states are in this position for all 96 months, so the rung is never idle.

    The fallback arm is in EMPLOYEES, not establishments: A scaled by the month's disclosed
    employees-per-establishment, so it can be merged with an own arm that is a predicted
    employment level. Derived from the fixture below rather than typed: at 2024-03 the only
    disclosed cell is state 01 with 43 employees over 4 establishments.
    """
    monthly = _history(make_monthly)
    anchor = Anchor("2024-03", 50.0, ("02",), "declared_national_total")
    out = cls().weights(_context(monthly, appendix_a_config), anchor)
    assert out.basis["02"] == FALLBACK
    assert out.values["02"] == pytest.approx(6.0 * (43 / 4))


def test_a_lookback_stops_at_the_naics_vintage_break(make_monthly, appendix_a_config) -> None:
    """§10.3: "Historical shares must use classification-consistent periods"."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2021-12",
            "naics_vintage": "NAICS 2017",
            "employment_value": 90,
            "qtrly_establishments": 4,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2021-12",
            "naics_vintage": "NAICS 2017",
            "employment_value": 100,
            "qtrly_establishments": 4,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2022-03",
            "naics_vintage": "NAICS 2022",
            "employment_value": 10,
            "qtrly_establishments": 4,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2022-03",
            "employment_value": 100,
            "qtrly_establishments": 4,
        },
    )
    # The 2021-12 share is now well defined, so the ONLY thing that can exclude it is the
    # vintage filter. Without the national row this assertion passed on an empty inner join and
    # said nothing about classification consistency at all.
    kept = observed_share_history(
        monthly,
        state_fips="01",
        before="2022-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert kept["reference_month"].to_list() == ["2021-12"]
    history = observed_share_history(
        monthly,
        state_fips="01",
        before="2022-03",
        lookback_months=24,
        may_cross_vintage=False,
        vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == []


def test_crossing_the_break_is_possible_only_when_config_permits(
    make_monthly, appendix_a_config
) -> None:
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2021-12",
            "naics_vintage": "NAICS 2017",
            "employment_value": 90,
            "qtrly_establishments": 4,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2021-12",
            "employment_value": 100,
            "qtrly_establishments": 4,
        },
    )
    history = observed_share_history(
        monthly,
        state_fips="01",
        before="2022-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == ["2021-12"]
