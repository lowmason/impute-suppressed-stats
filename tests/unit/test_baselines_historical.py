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
from logging_employment.reconcile.anchor import Anchor, Partition, observed_partition

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
        observed_partition(monthly),
        state_fips="01",
        before="2022-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert kept["reference_month"].to_list() == ["2021-12"]
    history = observed_share_history(
        monthly,
        observed_partition(monthly),
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
        observed_partition(monthly),
        state_fips="01",
        before="2022-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == ["2021-12"]


def test_the_history_comes_from_the_partition_not_from_observation_status(
    make_monthly, appendix_a_config
) -> None:
    """§13.4's leakage control, made structural rather than remembered.

    Under a Stage 4 pseudo-suppression mask the held-out cell still carries its published value in
    `qcew_monthly`. A history filtered on `observation_status` therefore hands this estimator the
    very number it is being scored against: with state 01 published at 400 of a national 1000 and
    masked in 2024-02, the table-based filter returned an own weight of exactly 400.0 — the
    held-out value, laundered through the share. Reading the partition makes that impossible
    instead of forbidden.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-02",
            "employment_value": 1000,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-02",
            "employment_value": 400,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-02",
            "employment_value": 600,
            "qtrly_establishments": 10,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 1000,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 400,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": 600,
            "qtrly_establishments": 10,
        },
    )
    states = monthly.filter(pl.col("area_type") == "state")
    feb = states.filter(pl.col("reference_month") == "2024-02")
    masked = {
        "2024-02": Partition(
            disclosed=feb.filter(pl.col("state_fips") == "02"),
            missing=feb.filter(pl.col("state_fips") == "01"),
        ),
        "2024-03": observed_partition(monthly)["2024-03"],
    }
    context = EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=masked, config=appendix_a_config
    )
    history = observed_share_history(
        monthly,
        masked,
        state_fips="01",
        before="2024-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert history["share"].to_list() == []
    out = LastObservedShare().weights(
        context, Anchor("2024-03", 400.0, ("01",), "declared_national_total")
    )
    assert out.basis["01"] == FALLBACK


def test_a_published_zero_enters_the_history_as_a_zero_share(
    make_monthly, appendix_a_config
) -> None:
    """`disclosed` is observed PLUS true_zero, so a published zero is a datum, not a gap.

    Filtering on `observation_status == "observed"` skipped past a published zero to whatever
    older positive value happened to precede it — reporting a stale level as the state's latest
    share. The zero is now the latest share, and since §12.2 requires positive weights the cell
    takes the declared fallback instead.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-01",
            "employment_value": 1000,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-01",
            "employment_value": 400,
            "qtrly_establishments": 10,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-02",
            "employment_value": 1000,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-02",
            "employment_value": 0,
            "qtrly_establishments": 10,
            "observation_status": "true_zero",
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 1000,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 10,
        },
    )
    history = observed_share_history(
        monthly,
        observed_partition(monthly),
        state_fips="01",
        before="2024-03",
        lookback_months=24,
        may_cross_vintage=True,
        vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == ["2024-01", "2024-02"]
    assert history["share"].to_list()[-1] == 0.0
