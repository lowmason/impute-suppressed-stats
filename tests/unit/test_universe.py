"""REQ-002, INV-009, SRC-QCEW-006 and SRC-QCEW-007 in code."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment import constants
from logging_employment.contracts import SUPPRESSION_TYPES
from logging_employment.errors import ConceptViolationError
from logging_employment.harmonize import universe
from logging_employment.ingest import qcew

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


def _parsed() -> pl.DataFrame:
    return qcew.parse_qcew_monthly(
        qcew.read_slice_csv(FIXTURE.read_bytes()),
        snapshot_id="s",
        release_vintage="2017Q1",
        release_status="final",
        naics_vintage="NAICS 2017",
    )


def test_the_universe_filter_keeps_private_state_and_national_rows_only() -> None:
    filtered = qcew.apply_universe_filter(_parsed())
    assert filtered["ownership_code"].unique().to_list() == [constants.PRIVATE_OWN_CODE]
    kept = set(filtered["area_fips"].unique().to_list())
    assert kept <= constants.STATE_AREAS | {constants.NATIONAL_AREA}
    assert "72000" not in kept  # Puerto Rico is outside states_dc
    assert filtered.filter(pl.col("aggregation_level") == "78").height == 0  # no counties


def test_the_filter_actually_removes_rows_the_fixture_contains() -> None:
    # Without this, the filter could be a no-op and every assertion above would still hold.
    parsed = _parsed()
    assert set(parsed["ownership_code"].unique().to_list()) == {"3", "5"}
    assert "72000" in parsed["area_fips"].to_list()
    assert qcew.apply_universe_filter(parsed).height < parsed.height


def test_every_real_row_carries_suppression_type_unknown() -> None:
    # INV-009: primary_like / complementary_like are for Stage 4's synthetic masks only.
    filtered = qcew.apply_universe_filter(_parsed())
    assert filtered["suppression_type"].unique().to_list() == ["unknown"]
    assert SUPPRESSION_TYPES[0] == "unknown"


def test_the_labelled_suppression_types_never_appear_on_a_parsed_row() -> None:
    values = set(_parsed()["suppression_type"].unique().to_list())
    assert values.isdisjoint({"primary_like", "complementary_like"})
    assert set(SUPPRESSION_TYPES) == {"unknown", "primary_like", "complementary_like"}


def test_dc_is_in_the_universe_but_contributes_no_row() -> None:
    # Stage 0 measured 11000 publishing zero private 113310 rows in all 96 months. The universe
    # includes it; the data does not. Those are different statements and both must survive.
    assert "11000" in constants.STATE_AREAS
    assert qcew.apply_universe_filter(_parsed()).filter(pl.col("area_fips") == "11000").height == 0


def test_the_universe_report_counts_suppressed_state_cells_per_month() -> None:
    report = universe.state_universe_report(qcew.apply_universe_filter(_parsed()))
    assert set(report) >= {
        "months",
        "suppressed_state_cells_by_month",
        "non_state_areas_present",
        "national_row_present_by_month",
        "months_with_a_complete_state_sum",
    }
    # Stage 0 measured zero months free of a suppressed state cell; this fixture is one quarter of
    # that window, so the count is reported rather than asserted to a fixed number.
    assert isinstance(report["months_with_a_complete_state_sum"], int)


def test_the_report_sees_non_state_areas_on_an_unfiltered_frame() -> None:
    # Run on the *unfiltered* frame: apply_universe_filter drops non-state areas by construction,
    # so asserting an empty list downstream of it could never fail. Puerto Rico (72000) is present
    # in 2017 state-like rows, which is where this check has content.
    report = universe.state_universe_report(_parsed())
    assert "72000" in report["non_state_areas_present"]


def test_the_report_never_claims_an_identity_on_an_incomplete_state_sum() -> None:
    report = universe.state_universe_report(qcew.apply_universe_filter(_parsed()))
    for month, suppressed in report["suppressed_state_cells_by_month"].items():
        if suppressed > 0:
            assert month not in report["identity_evaluable_months"]


def test_a_month_with_no_national_row_is_not_identity_evaluable() -> None:
    # Two separate reasons a month cannot be evaluated; the report must not conflate them.
    filtered = qcew.apply_universe_filter(_parsed())
    without_national = filtered.filter(pl.col("area_fips") != constants.NATIONAL_AREA)
    report = universe.state_universe_report(without_national)
    assert report["identity_evaluable_months"] == []
    assert not any(report["national_row_present_by_month"].values())


def test_every_month_appears_in_every_per_month_mapping() -> None:
    # A month missing from a mapping reads as "no suppressed cells" to a caller using .get().
    report = universe.state_universe_report(qcew.apply_universe_filter(_parsed()))
    months = set(report["months"])
    assert set(report["suppressed_state_cells_by_month"]) == months
    assert set(report["national_row_present_by_month"]) == months


def test_alignment_passes_when_national_and_state_rows_share_industry_and_ownership() -> None:
    universe.assert_definitional_alignment(qcew.apply_universe_filter(_parsed()))


def test_alignment_fails_when_ownership_differs_between_levels() -> None:
    frame = qcew.apply_universe_filter(_parsed())
    doctored = frame.with_columns(
        pl.when(pl.col("area_type") == "national")
        .then(pl.lit("3"))
        .otherwise(pl.col("ownership_code"))
        .alias("ownership_code")
    )
    with pytest.raises(ConceptViolationError, match="ownership"):
        universe.assert_definitional_alignment(doctored)


def test_alignment_fails_when_the_naics_vintage_differs_between_levels() -> None:
    frame = qcew.apply_universe_filter(_parsed())
    doctored = frame.with_columns(
        pl.when(pl.col("area_type") == "national")
        .then(pl.lit("NAICS 2022"))
        .otherwise(pl.col("naics_vintage"))
        .alias("naics_vintage")
    )
    with pytest.raises(ConceptViolationError, match="naics_vintage"):
        universe.assert_definitional_alignment(doctored)
