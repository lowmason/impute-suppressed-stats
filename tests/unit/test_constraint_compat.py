"""The §5.5 gates that must pass before a constraint row exists."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.constraints import compat
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError, IncompatibleMarginError


def _real_2024(make_monthly, make_size):
    """The real published 2024 margin: seven classes, two suppressed, 7713 establishments."""
    monthly = make_monthly(
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "qtrly_establishments": 7713,
            "employment_value": 41668,
            "employment_raw": "41668",
        }
    )
    published = [
        ("1", 5007, 7630, 0, 4, "", "observed"),
        ("2", 1501, 9955, 5, 9, "", "observed"),
        ("3", 803, 10480, 10, 19, "", "observed"),
        ("4", 357, 10316, 20, 49, "", "observed"),
        ("5", 40, 2507, 50, 99, "", "observed"),
        ("6", 4, None, 100, 249, "N", "suppressed"),
        ("7", 1, None, 250, 499, "N", "suppressed"),
    ]
    size = make_size(
        *[
            {
                "size_class": k,
                "establishments": n,
                "employment": e,
                "size_lower": lo,
                "size_upper": hi,
                "disclosure_code": code,
                "observation_status": status,
            }
            for k, n, e, lo, hi, code, status in published
        ]
    )
    return monthly, size


def test_the_real_2024_margin_passes_both_gates(make_monthly, make_size) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    report = compat.assert_size_margin_compatible(monthly, size)
    assert report["years_checked"] == [2024]
    assert report["establishment_gap_by_year"] == {2024: 0}
    assert report["employment_checkable_years"] == []
    assert report["observed_support_rows_checked"] == 5


def test_a_year_with_no_suppressed_class_is_reported_as_employment_checkable(
    make_monthly, make_size
) -> None:
    # 2017 is the one such year in the window, and its residual is exactly 0.
    monthly = make_monthly(
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2017-03",
            "qtrly_establishments": 60,
            "employment_value": 300,
            "employment_raw": "300",
        }
    )
    size = make_size(
        {
            "reference_year": 2017,
            "reference_month": "2017-03",
            "size_class": "1",
            "establishments": 50,
            "employment": 100,
            "size_lower": 0,
            "size_upper": 4,
        },
        {
            "reference_year": 2017,
            "reference_month": "2017-03",
            "size_class": "2",
            "establishments": 10,
            "employment": 200,
            "size_lower": 5,
            "size_upper": 99,
        },
    )
    report = compat.assert_size_margin_compatible(monthly, size)
    assert report["employment_checkable_years"] == [2017]


def test_an_establishment_gap_halts_rather_than_stacking_two_universes(
    make_monthly, make_size
) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    monthly = monthly.with_columns(pl.lit(9999).alias("qtrly_establishments"))
    with pytest.raises(IncompatibleMarginError, match="establishment"):
        compat.assert_size_margin_compatible(monthly, size)


def test_two_rows_for_one_year_and_class_halt(make_monthly, make_size) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    with pytest.raises(IncompatibleMarginError, match="more than one row"):
        compat.assert_size_margin_compatible(monthly, pl.concat([size, size.head(1)]))


def test_a_non_march_size_row_halts_before_any_support_is_built(make_monthly, make_size) -> None:
    # INV-011: a March-reference class bound is not imposed outside its valid reference period.
    monthly, size = _real_2024(make_monthly, make_size)
    with pytest.raises(ConceptViolationError, match="March"):
        compat.assert_size_margin_compatible(
            monthly, size.with_columns(pl.lit("2024-06").alias("reference_month"))
        )


def test_the_support_rule_is_checked_against_every_observed_row(make_size) -> None:
    # Measured while this plan was written: all 37 observed window rows satisfy the band. A row
    # that does not means the class titles do not describe published data, and the support
    # constraint must not be built as hard.
    good = make_size(
        {
            "size_class": "5",
            "establishments": 40,
            "employment": 2507,
            "size_lower": 50,
            "size_upper": 99,
        }
    )
    assert compat.assert_size_support_holds(good) == 1
    bad = make_size(
        {
            "size_class": "5",
            "establishments": 40,
            "employment": 100,
            "size_lower": 50,
            "size_upper": 99,
        }
    )
    with pytest.raises(ConceptViolationError, match="size support"):
        compat.assert_size_support_holds(bad)


def test_an_open_ended_class_is_checked_on_its_lower_side_only(make_size) -> None:
    # Class 9 is "1000 or more employees per establishment"; `size_upper` is null and no number
    # may be invented to close it (§9.3 forbids arbitrary top-class caps).
    rows = make_size(
        {
            "size_class": "9",
            "establishments": 2,
            "employment": 999_999,
            "size_lower": 1000,
            "size_upper": None,
        }
    )
    assert compat.assert_size_support_holds(rows) == 1


def test_the_entry_point_calls_stage_ones_alignment_check(make_monthly, make_size) -> None:
    # SRC-QCEW-007 requires the alignment check before a constraint is created, and Stage 1 left
    # it off the build path for exactly that reason.
    monthly, size = _real_2024(make_monthly, make_size)
    misaligned = pl.concat(
        [monthly, make_monthly({"industry_code": "111110", "area_type": "state"})]
    )
    data = HarmonizedData(
        qcew_monthly=misaligned,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    with pytest.raises(ConceptViolationError, match="definitionally aligned"):
        compat.run_compatibility_gates(data, industry_code="113310")


def test_a_null_national_vintage_is_a_conflict_rather_than_a_silent_pass(
    make_monthly, make_size
) -> None:
    # Deviation from the plan's code block, kept because this is a fail-closed gate: `!=` yields
    # null when either side is null and `filter` drops a null predicate, so a national row with no
    # recorded NAICS vintage would pass the vintage check instead of halting it. `ne_missing`
    # reads null as a value that differs from a non-null one.
    monthly, size = _real_2024(make_monthly, make_size)
    monthly = monthly.with_columns(pl.lit(None, dtype=pl.String).alias("naics_vintage"))
    with pytest.raises(IncompatibleMarginError, match="NAICS vintages that differ"):
        compat.assert_size_margin_compatible(monthly, size)


def test_an_unmeasurable_observed_row_is_a_violation_rather_than_a_silent_skip(make_size) -> None:
    # Review finding: a null in any comparand makes the band comparison null and `filter` drops a
    # null predicate, so the row left the gate unchecked *and* was still counted in the return
    # value -- the one number that exists to show the gate was not vacuous.
    rows = make_size(
        {
            "size_class": "5",
            "establishments": 40,
            "employment": 2507,
            "size_lower": 50,
            "size_upper": 99,
        },
        {
            "size_class": "4",
            "establishments": 5,
            "employment": 150,
            "size_lower": None,
            "size_upper": 49,
        },
    )
    with pytest.raises(ConceptViolationError, match="size support"):
        compat.assert_size_support_holds(rows)


def test_a_size_row_with_no_reference_month_cannot_slip_the_march_gate(
    make_monthly, make_size
) -> None:
    # `~ends_with` is null on a null month, and a null predicate is dropped by `filter`.
    monthly, size = _real_2024(make_monthly, make_size)
    nulled = size.with_columns(pl.lit(None, dtype=pl.String).alias("reference_month"))
    with pytest.raises(ConceptViolationError, match="March"):
        compat.assert_size_margin_compatible(monthly, nulled)
