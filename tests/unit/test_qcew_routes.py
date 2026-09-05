"""Slice-route URL construction, the boundary probe, and CSV reading."""

from __future__ import annotations

from pathlib import Path

import httpx
import polars as pl

from logging_employment.ingest import qcew
from logging_employment.ingest.base import HttpFetcher

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


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
