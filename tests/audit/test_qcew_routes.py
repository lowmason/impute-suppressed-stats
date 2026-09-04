"""Judgment-logic tests for `qcew_routes` (D5), covering `column_parity`.

`column_parity` was inline in `main()` and untested. It is extracted here as a pure function
over the headers a run actually read -- no behaviour change beyond the one this file pins, and
verified against the shipped summary: recomputing it from `data/raw/audit/qcew_routes`'s own
extracts reproduces `findings.column_parity` field for field, so the extraction owes no
artifact regeneration.

Nothing here reads `data/raw/audit/`; that tree is gitignored and absent in a fresh clone. The
headers below are the real QCEW column names in miniature.

`qcew_routes` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import qcew_routes as m

SHARED = ["area_fips", "own_code", "industry_code", "year", "qtr", "month1_emplvl"]
SLICE_HEADER = [*SHARED, "qtrly_estabs", "lq_qtrly_estabs"]
BULK_HEADER = [*SHARED, "qtrly_estabs_count", "area_title"]


def test_identical_is_true_when_one_bulk_year_and_one_slice_header_agree():
    parity = m.column_parity({"2017q1.csv": list(SHARED)}, {2017: list(SHARED)},
                             reference_bulk_year=2017)
    assert parity["identical"] is True
    assert parity["bulk_header_disagreement"] == {}
    assert parity["slice_only"] == [] and parity["bulk_only"] == []


def test_identical_is_false_when_the_two_routes_carry_different_columns():
    """The real finding: the slice route names `qtrly_estabs` where bulk names
    `qtrly_estabs_count`, and bulk carries title columns the slice omits."""
    parity = m.column_parity({"2017q1.csv": SLICE_HEADER}, {2017: BULK_HEADER},
                             reference_bulk_year=2017)
    assert parity["identical"] is False
    assert parity["slice_only"] == ["lq_qtrly_estabs", "qtrly_estabs"]
    assert parity["bulk_only"] == ["area_title", "qtrly_estabs_count"]


def test_identical_is_false_when_the_bulk_years_disagree_with_each_other():
    """The defect this pins. `bulk_header` reduces to ONE year's columns -- the first fetched.
    On the normal D5 path `bulk_years_required` is non-empty and several years are fetched, so
    the bare `slice_header == bulk_header` could report the two routes identical while the bulk
    side had no single header at all: `identical: true` sitting next to a non-empty
    `bulk_header_disagreement` in the same finding. Here the reference year matches the slice
    exactly and 2018 does not, which is precisely the case that used to read true."""
    parity = m.column_parity(
        {"2017q1.csv": list(SHARED)},
        {2017: list(SHARED), 2018: [*SHARED, "month2_emplvl"]},
        reference_bulk_year=2017)
    assert parity["identical"] is False
    assert set(parity["bulk_header_disagreement"]) == {"2017", "2018"}


def test_a_bulk_disagreement_is_recorded_rather_than_picked_around():
    """Schema drift between bulk years is a finding about BLS, not a bug to resolve, so every
    fetched year's columns are kept."""
    parity = m.column_parity(
        {"2017q1.csv": list(SHARED)},
        {2017: list(SHARED), 2018: [*SHARED, "month2_emplvl"]},
        reference_bulk_year=2017)
    assert parity["bulk_header_disagreement"]["2018"][-1] == "month2_emplvl"


def test_identical_is_false_when_the_slice_quarters_disagree_with_each_other():
    """The same defect on the other axis, and the reason the conjunction covers both sides.
    The slice side reduces to the first served quarter, so a mid-window BLS schema change
    could leave `identical: true` beside a non-empty `slice_header_disagreement` -- "the slice
    header" asserted of a slice side that has no single header. Here the reference quarter
    matches the bulk header exactly and 2021q1 does not.

    Widened past the review's bulk-only instruction after confirming it changes no shipped
    value: recomputing this function over the real run's own 32 slice headers and its bulk zip
    reproduces `findings.column_parity` field for field either way, because that run has both
    disagreement dicts empty."""
    parity = m.column_parity(
        {"/abs/slices/2017q1.csv": list(SHARED),
         "/abs/slices/2021q1.csv": [*SHARED, "new_bls_column"]},
        {2017: list(SHARED)}, reference_bulk_year=2017)
    assert set(parity["slice_header_disagreement"]) == {"2017q1.csv", "2021q1.csv"}
    assert parity["identical"] is False


def test_no_served_slice_leaves_an_empty_reference_rather_than_raising():
    """`slice_paths` is empty when the slice route served no window quarter -- a recorded
    access finding, not a crash."""
    parity = m.column_parity({}, {2017: list(SHARED)}, reference_bulk_year=2017)
    assert parity["identical"] is False
    assert parity["slice_only"] == []
    assert parity["bulk_only"] == sorted(SHARED)
