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
import zipfile
from collections.abc import Iterable
from typing import Literal

import polars as pl

from .base import FetchedBytes, HttpFetcher

SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
BULK_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip"

# Stage 0 measured `column_parity.identical = false` between the two routes. These four names are
# the disagreements that matter -- the bulk file spells the establishment-count family with a
# `_count` infix. Mapping is one-directional: bulk is renamed into the slice vocabulary, because
# the slice route serves the whole window today and its names are what the parser reads.
BULK_TO_SLICE_COLUMNS: dict[str, str] = {
    "qtrly_estabs_count": "qtrly_estabs",
    "lq_qtrly_estabs_count": "lq_qtrly_estabs",
    "oty_qtrly_estabs_count_chg": "oty_qtrly_estabs_chg",
    "oty_qtrly_estabs_count_pct_chg": "oty_qtrly_estabs_pct_chg",
}

# Five title columns the bulk file carries and the slice file does not. Dropped rather than kept:
# they are labels for codes this package resolves through its own harmonized dimensions, and
# keeping them would give two routes two different column sets for the same table.
BULK_ONLY_TITLE_COLUMNS: tuple[str, ...] = (
    "agglvl_title",
    "area_title",
    "industry_title",
    "own_title",
    "size_title",
)


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


def bulk_url(year: int) -> str:
    """The downloadable bulk-file URL for one reference year."""
    return BULK_URL.format(year=year)


def route_for_year(year: int, earliest_slice_year: int) -> Literal["slice", "bulk"]:
    """Which route serves this reference year, given the boundary measured this run."""
    return "slice" if year >= earliest_slice_year else "bulk"


def read_bulk_zip(raw: bytes, industry: str) -> pl.DataFrame:
    """Read the one industry member out of a bulk zip, in the slice column vocabulary.

    The member name embeds the industry code and its title, e.g.
    `2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv`, so the member is selected
    by an industry-code substring rather than by a reconstructed filename. Anything other than
    exactly one match is an archive shape this package does not recognize, and §18.3 makes that
    a raise carrying the offending value rather than a guess at which member was meant.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.namelist() if industry in n and n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one member for industry {industry}, found {members}")
        with archive.open(members[0]) as handle:
            frame = pl.read_csv(handle.read(), infer_schema_length=0)
    frame = frame.rename({k: v for k, v in BULK_TO_SLICE_COLUMNS.items() if k in frame.columns})
    return frame.drop([c for c in BULK_ONLY_TITLE_COLUMNS if c in frame.columns])
