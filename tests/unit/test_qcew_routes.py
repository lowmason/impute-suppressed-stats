"""Slice-route URL construction, the boundary probe, and CSV reading."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import httpx
import polars as pl
import pytest

from logging_employment import constants
from logging_employment.ingest import qcew
from logging_employment.ingest.base import HttpFetcher

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"
BULK = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "bulk_2017.zip"
TARGET_MEMBER = "2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv"


def _fetcher(handler) -> HttpFetcher:
    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(transport=httpx.MockTransport(handler))
    return fetcher


def test_slice_url_interpolates_year_quarter_and_industry() -> None:
    assert qcew.slice_url(2017, 1, "113310") == (
        "https://data.bls.gov/cew/data/api/2017/1/industry/113310.csv"
    )


def test_boundary_probe_returns_the_earliest_year_that_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        year = int(str(request.url).split("/api/")[1].split("/")[0])
        if year < 2015:
            return httpx.Response(404, content=b"")
        return httpx.Response(200, content=FIXTURE.read_bytes())

    assert qcew.probe_slice_boundary(_fetcher(handler), "113310", range(2010, 2020)) == 2015


def test_boundary_probe_does_not_hard_code_a_year() -> None:
    # D5 and Stage 0's auditor note both forbid it: the earliest year served was "a status
    # measured in one run, not a property of the route".
    source = Path(qcew.__file__).read_text()
    assert "2014" not in source


def test_every_slice_column_is_read_as_a_string() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    assert set(frame.schema.values()) == {pl.String}
    assert frame["area_fips"].str.len_chars().min() == 5  # leading zeros survive


def test_the_fixture_carries_the_columns_the_parser_needs() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    for column in (
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "size_code",
        "year",
        "qtr",
        "disclosure_code",
        "qtrly_estabs",
        "month1_emplvl",
        "month2_emplvl",
        "month3_emplvl",
        "total_qtrly_wages",
    ):
        assert column in frame.columns


def test_route_selection_uses_the_measured_boundary() -> None:
    assert qcew.route_for_year(2017, earliest_slice_year=2014) == "slice"
    # Forced: today's measured boundary makes this unreachable in production, so the bulk branch
    # would otherwise never execute.
    assert qcew.route_for_year(2017, earliest_slice_year=2020) == "bulk"


def test_the_bulk_fixture_carries_the_audited_member_bytes() -> None:
    """`bulk_2017.zip` is reduced, so pin the member the reduction was supposed to preserve.

    The fixture is not the archive Stage 0 fetched -- that one is 439 MB across 2,232 members and
    untrackable -- but the target member inside it must still be byte-identical to the audited
    archive's. This asserts that, rather than asserting that `tests/fixtures/qcew/README.md`
    says so.
    """
    with zipfile.ZipFile(io.BytesIO(BULK.read_bytes())) as archive:
        members = archive.namelist()
        digest = hashlib.sha256(archive.read(TARGET_MEMBER)).hexdigest()
    assert digest == "47bfbef888054477d4fc4fcf4c2a04e70b72610ec4125eeb279c613a14c48caa"
    # More than one member, or the filter below narrows one name to one name and proves nothing.
    assert len(members) == 4


def test_bulk_columns_are_renamed_to_the_slice_vocabulary() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    assert "qtrly_estabs" in frame.columns
    assert "qtrly_estabs_count" not in frame.columns
    for bulk_name in qcew.BULK_TO_SLICE_COLUMNS:
        assert bulk_name not in frame.columns


def test_both_routes_agree_on_the_columns_the_parser_reads() -> None:
    slice_frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    bulk_frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    needed = {
        "area_fips",
        "own_code",
        "industry_code",
        "agglvl_code",
        "size_code",
        "year",
        "qtr",
        "disclosure_code",
        "qtrly_estabs",
        "month1_emplvl",
        "month2_emplvl",
        "month3_emplvl",
        "total_qtrly_wages",
    }
    assert needed <= set(slice_frame.columns)
    assert needed <= set(bulk_frame.columns)


def test_bulk_only_title_columns_are_dropped() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    for title_column in qcew.BULK_ONLY_TITLE_COLUMNS:
        assert title_column not in frame.columns


def test_the_member_filter_picks_the_target_among_near_misses() -> None:
    """The fixture carries decoys, so the filter narrows many names to one, as in production.

    Against a single-member fixture this function is indistinguishable from one with no filter
    at all -- deleting the comprehension leaves every other test here green.
    """
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    assert frame["industry_code"].unique().to_list() == [constants.INDUSTRY_CODE]


def test_an_ambiguous_industry_substring_fails_closed() -> None:
    """Matching is unanchored, so a shorter code can hit several members (§18.3: raise).

    `11331` is `113310`'s parent and publishes under the same "Logging" title; the digits also
    fall inside `111331 Apple orchards`. That is a property of the real archive, not of a
    constructed one, so the fixture's own members demonstrate it.
    """
    with pytest.raises(ValueError, match="expected one member for industry 11331"):
        qcew.read_bulk_zip(BULK.read_bytes(), "11331")
