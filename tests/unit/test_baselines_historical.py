"""§10.3's five share variants, the vintage rule, and the composite that keeps them running."""

from __future__ import annotations

import statistics

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
from logging_employment.reconcile.allocate import Weights
from logging_employment.reconcile.anchor import (
    Anchor,
    Partition,
    national_residual,
    observed_partition,
)

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
    """State 01 observed in three in-window months plus the anchor month, state 02 suppressed.

    THE HISTORY CARRIES A REAL LEVEL BREAK, AND THAT IS LOAD-BEARING. An arithmetic series --
    this fixture was `40 + i` -- has nominally equal steps, so `BreakAdjustedShare`'s
    largest-step argmax is decided by float representation error rather than by the data: on
    shares 0.40, 0.41, 0.42 the two steps are 0.009999999999999953 and 0.010000000000000009, the
    cut lands last, and the segment is one point. Under R-BREAK-1 that variant then refuses and
    this fixture's own test fails for a floating-point reason wearing a coverage reason's
    clothes. The 10 -> 40 jump gives the cut somewhere real to land.

    THE ANCHOR MONTH STAYS AT 43. `test_a_state_with_no_observed_history_takes_the_declared_
    fallback` derives its expected weight from this fixture as `6.0 * (43 / 4)`, so 2024-03's
    employment is not free to move with the rest of the series.
    """
    rows = []
    for month, employment in zip(
        ["2023-01", "2023-02", "2023-03", "2024-03"], [10, 40, 41, 43], strict=True
    ):
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
                "employment_value": employment,
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

    The anchor comes from `national_residual` rather than being typed, because R-COMP-8 requires
    the intensity and the residual to come from one partition and refuses them when they do not.
    """
    monthly = _history(make_monthly)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    assert anchor.missing_cells == ("02",)
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
    march = states.filter(pl.col("reference_month") == "2024-03")
    masked = {
        "2024-02": Partition(
            disclosed=feb.filter(pl.col("state_fips") == "02"),
            missing=feb.filter(pl.col("state_fips") == "01"),
        ),
        # The mask holds state 01 out in the anchor month too. Leaving 2024-03 unmasked made the
        # fixture describe a mask it did not apply: the anchor's residual was typed while the
        # partition said the missing set was empty, which R-COMP-8 now refuses.
        "2024-03": Partition(
            disclosed=march.filter(pl.col("state_fips") == "02"),
            missing=march.filter(pl.col("state_fips") == "01"),
        ),
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
    anchor = national_residual(monthly, masked["2024-03"], reference_month="2024-03")
    assert anchor.residual == pytest.approx(400.0)
    out = LastObservedShare().weights(context, anchor)
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


def _reduce_shares(shares: list[float]) -> float | None:
    """`BreakAdjustedShare._reduce` on a bare share list.

    The rule is a pure reduction over a list of floats, so it is driven directly rather than
    through a fixture. The anchor and history arguments are `None` rather than stubs: this variant
    selects by POSITION and reads neither, so `None` makes that structural -- a future revision
    that starts reading either raises here instead of quietly agreeing.

    Where a case below admits more than one step, its largest is kept well clear of its second
    largest, for the reason `_share_rows` gives: two nominally equal steps are separated by float
    representation error rather than by the data, so a cut chosen between them would pin noise.
    """
    return BreakAdjustedShare()._reduce(shares, None, None)


def test_a_one_point_history_admits_no_cut_and_is_refused() -> None:
    """T-1. A one-point history has no steps, so `max(steps)` would raise on an empty sequence --
    the guard is what makes the reduction total, not a threshold on the history length."""
    assert _reduce_shares([0.02]) is None


def test_a_two_point_history_leaves_a_one_point_segment_and_is_refused() -> None:
    """T-2. The only cut a two-point history admits puts one point in the recent segment, and the
    median of one point is that point -- which is `LastObservedShare`, not this variant."""
    assert _reduce_shares([0.02, 0.05]) is None


def test_a_short_history_cut_in_the_middle_keeps_its_two_point_segment() -> None:
    """T-3. The keep half of R-BREAK-2: three points is not too few when the cut falls inside.

    The contrast is DERIVED rather than asserted in prose -- `statistics.median` is called on the
    same list, so if this variant ever collapsed back to the plain median the second assert would
    equal the first instead of differing from it."""
    shares = [0.10, 0.50, 0.52]
    assert _reduce_shares(shares) == pytest.approx(0.51)
    assert statistics.median(shares) == pytest.approx(0.50)


def test_a_short_history_cut_at_the_end_is_refused() -> None:
    """T-4. The refuse half of R-BREAK-2, on a history the same length as T-3's: length decides
    nothing, the cut decides. These are the numbers the deleted `<4` test used to reduce to 0.11,
    so the second assert names the value this variant no longer emits."""
    shares = [0.10, 0.11, 0.90]
    assert _reduce_shares(shares) is None
    assert statistics.median(shares) == pytest.approx(0.11)


def test_a_long_history_whose_largest_step_is_its_last_is_refused() -> None:
    """T-5. The case no length threshold can catch and no previous test reached: twelve points,
    far past any plausible minimum, and still no evidence of a segment. Under the `<4` rule this
    returned the median of the one-point segment -- the last observation, i.e. variant 1."""
    shares = [10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 90.0]
    assert len(shares) == 12
    assert _reduce_shares(shares) is None


def test_a_long_history_with_an_interior_break_follows_the_recent_segment() -> None:
    """T-6. The variant still does its job where the evidence supports it.

    The same twelve values `_breaking_history` uses, so the unit rule and the all-variants fixture
    cannot drift apart. The inequality below is a property of THIS fixture, not an invariant:
    a recent segment may agree with the whole-history median by coincidence, which §2 permits."""
    shares = [20.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 30.0, 31.0, 29.0, 34.0]
    # The largest single step is 10 -> 30, so the segment is [30, 31, 29, 34], median (30 + 31) / 2.
    assert _reduce_shares(shares) == pytest.approx(30.5)
    assert statistics.median(shares) == pytest.approx(11.0)


def test_a_refused_cell_takes_the_establishment_fallback_rather_than_declining(
    make_monthly, appendix_a_config
) -> None:
    """T-7. R-BREAK-3: refusal reuses the existing `None` path, so the cell is COMPOSED, not
    declined -- no new decline reason and no new config key.

    The anchor comes from `national_residual` rather than being typed, because R-COMP-8 requires
    the intensity and the residual to come from one partition and refuses them when they do not:
    a hand-typed residual raises `ConceptViolationError` here the moment a fallback arm is built.
    State 02 is disclosed at the anchor so the fallback has an intensity to be scaled by."""
    rows = _share_rows(["2023-12", "2024-01", "2024-02"], [10, 11, 90])
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
    monthly = make_monthly(*rows)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    assert anchor.missing_cells == ("01",)

    out = BreakAdjustedShare().weights(_context(monthly, appendix_a_config), anchor)

    assert isinstance(out, Weights), "a refused cell is composed, not declined"
    assert out.basis["01"] == FALLBACK
    # Derived from the fixture: 2024-03's only disclosed cell is state 02, 800 employees over 80
    # establishments, and state 01 brings 4 establishments of exposure to that intensity.
    assert out.values["01"] == pytest.approx(4 * (800 / 80))


def test_the_break_adjusted_docstring_declares_its_refusal() -> None:
    """The sentence half of the pair: the seven tests above hold that the claim is TRUE, this holds
    that the claim is still MADE. It asserts the sentences EXIST, not that they are accurate --
    T-3, T-4 and T-5 are what make them accurate, and this test would pass over a false docstring.

    Whitespace-normalized so that re-wrapping the docstring does not redden this: the claim is the
    sentence, not the line breaks."""
    doc = " ".join(BreakAdjustedShare.__doc__.split())
    assert "A cut leaving fewer than two points in the recent segment is not evidence" in doc
    assert "THE THRESHOLD IS A PROPERTY OF THE SELECTED CUT, NOT OF THE HISTORY LENGTH" in doc
    assert "THE EARLIEST TIED STEP WINS" in doc
    # R-BREAK-4: the replaced claim named a threshold of four, and both its halves are now false.
    assert "below four" not in doc
