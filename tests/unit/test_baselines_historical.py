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


# --- do the five variants compute five numbers? ------------------------------------------------


def _share_rows(months: list[str], employment: list[int]) -> list[dict]:
    """A national row and one state-01 row per month, then the suppressed anchor month. Integer
    employment over an integer national total, because on tenths the largest-step argmax is decided
    by float noise: on [0.1, 0.2, 0.3, 0.4] the steps are 0.1, 0.09999999999999998 and
    0.10000000000000003, so the cut lands last and the segment is one point."""
    rows: list[dict] = []
    for month, value in zip(months, employment, strict=True):
        rows.append(
            {
                "area_type": "national",
                "area_fips": "US000",
                "state_fips": None,
                "aggregation_level": "18",
                "reference_month": month,
                "employment_value": 1000,
                "qtrly_establishments": 100,
            }
        )
        rows.append(
            {
                "state_fips": "01",
                "area_fips": "01000",
                "reference_month": month,
                "employment_value": value,
                "qtrly_establishments": 4,
                "observation_status": "observed",
            }
        )
    rows.append(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 1000,
            "qtrly_establishments": 100,
        }
    )
    rows.append(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 4,
            "observation_status": "suppressed",
        }
    )
    return rows


def _breaking_history(make_monthly) -> pl.DataFrame:
    """Twelve months of history plus the anchor month, with a level break between month 8 and
    month 9. Twelve so SameMonthPreviousYearShare can resolve 2023-03; a break in the interior so
    BreakAdjustedShare's segment has more than one point; state 02 disclosed at the anchor month so
    the establishment fallback has an intensity if a variant declines."""
    months = [f"2023-{m:02d}" for m in range(3, 13)] + ["2024-01", "2024-02"]
    rows = _share_rows(months, [20, 10, 11, 9, 10, 11, 9, 10, 30, 31, 29, 34])
    rows.append(
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": 800,
            "qtrly_establishments": 80,
            "observation_status": "observed",
        }
    )
    return make_monthly(*rows)


def test_the_five_variants_compute_five_different_numbers_on_one_history(
    make_monthly, appendix_a_config
) -> None:
    """test_section_10_3_ships_exactly_five_variants checks that five estimator ids exist; nothing
    checked that five estimators exist. Below four shares BreakAdjustedShare is bitwise identical
    to RollingMedianShare, and the suite's only all-variants fixture is a three-month history on
    which the five produce three distinct numbers -- so a duplicate variant was undetectable.

    The values are stated as arithmetic over the fixture's own numbers rather than as a bare
    distinctness assert: the twelve-month span exists so SameMonthPreviousYearShare can resolve
    2023-03, and if historical_lookback_months ever drops below 12 a distinctness-only assert would
    fail for a config reason wearing a collapse reason's clothes."""
    monthly = _breaking_history(make_monthly)
    context = _context(monthly, appendix_a_config)
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")

    values = {}
    for cls in ALL_FIVE:
        out = cls().weights(context, anchor)
        assert out.basis["01"] == OWN, f"{cls.__name__} fell back; fix the fixture, not this"
        values[cls().estimator_id] = out.values["01"]

    assert values["share_last_observed"] == pytest.approx(34.0)
    assert values["share_same_month_prior_year"] == pytest.approx(20.0)
    assert values["share_rolling_median"] == pytest.approx(11.0)
    # The largest single step is 10 -> 30, so the segment is [30, 31, 29, 34], median (30 + 31) / 2.
    assert values["share_break_adjusted"] == pytest.approx(30.5)
    assert len(set(values.values())) == 5


def test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median(
    make_monthly, appendix_a_config
) -> None:
    """Documents the degeneracy rather than hiding it, and takes no position on whether it is
    right: with three shares there is no segment to split, so the variant returns the whole-history
    median and ignores a violent break at the most recent observation. The deferred item that
    revisits the threshold must change this test."""
    monthly = make_monthly(*_share_rows(["2023-12", "2024-01", "2024-02"], [10, 11, 90]))
    context = _context(monthly, appendix_a_config)
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")

    broken = BreakAdjustedShare().weights(context, anchor).values["01"]
    median = RollingMedianShare().weights(context, anchor).values["01"]
    assert broken == median
    assert broken == pytest.approx(11.0)
    # The break this variant exists to follow is derived, not asserted in prose: the most recent
    # observation is 90, and a variant that segmented on it would return that instead of 11.
    assert LastObservedShare().weights(context, anchor).values["01"] == pytest.approx(90.0)


def test_the_break_adjusted_docstring_scopes_its_own_claim() -> None:
    """The sentence half of the pair: the two tests above hold that the claim is TRUE, this holds
    that the claim is still MADE. Before this batch the docstring said a plain median "is what this
    variant exists NOT to be", full stop, which is false on every history shorter than four.

    Whitespace-normalized so that re-wrapping the docstring does not redden this: the claim is the
    sentence, not the line breaks."""
    doc = " ".join(BreakAdjustedShare.__doc__.split())
    assert "At four or more shares this is not a plain median over the whole lookback" in doc
    assert "below four it is exactly that" in doc
