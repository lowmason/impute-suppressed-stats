"""QCEW quarterly acquisition over both published routes, and the monthly parser.

D5 makes acquisition dual-route: the Open Data CSV slice endpoint and the downloadable bulk
files, behind one interface, selected by reference year. The boundary between them is measured
each run rather than stored. Stage 0 probed the slice route across candidate years and recorded
the earliest year it served as a status observed in one run rather than a property of the route,
so no year appears here as a literal -- `probe_slice_boundary` re-measures it and the run manifest
records what that run found.
"""

from __future__ import annotations

import io
from collections.abc import Iterable

import polars as pl

from .base import FetchedBytes, HttpFetcher

SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
BULK_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip"


def slice_url(year: int, qtr: int, industry: str) -> str:
    """The Open Data slice URL for one industry-quarter."""
    return SLICE_URL.format(year=year, qtr=qtr, industry=industry)


def read_slice_csv(raw: bytes) -> pl.DataFrame:
    """Read a slice CSV with every column typed as String.

    Nothing is coerced at read time. `area_fips` is a zero-padded code, not a number, and a
    suppressed row publishes a literal `0` that must not become an integer before the disclosure
    code has been read (SRC-QCEW-002: parse disclosure metadata before deriving numeric values).
    """
    return pl.read_csv(io.BytesIO(raw), infer_schema_length=0)


def probe_slice_boundary(
    fetcher: HttpFetcher, industry: str, candidate_years: Iterable[int]
) -> int:
    """The earliest candidate year whose Q1 slice returns a non-empty 200.

    Measured, never stored: the value this returns is written to the run manifest so a later
    reader can see which boundary that run used. The two-part predicate is what Stage 0's probe
    separates -- years before the boundary answered 404 with an empty body, years from it on
    answered 200 with a CSV -- so neither half of it is redundant.
    """
    served: list[int] = []
    for year in sorted(candidate_years):
        response = fetcher.get(slice_url(year, 1, industry))
        if response.http_status == 200 and response.content.strip():
            served.append(year)
    if not served:
        raise ValueError(f"the slice route served no candidate year for industry {industry}")
    return served[0]


def fetch_slice(fetcher: HttpFetcher, year: int, qtr: int, industry: str) -> FetchedBytes:
    """Fetch one industry-quarter over the slice route."""
    return fetcher.get(slice_url(year, qtr, industry))
