"""QCEW quarterly acquisition over both published routes, and the monthly parser.

D5 makes acquisition dual-route: the Open Data CSV slice endpoint and the downloadable bulk
files, behind one interface, selected by reference year. The boundary between them is measured
each run rather than stored. Stage 0 probed the slice route across candidate years and recorded
the earliest year it served as a status observed in one run rather than a property of the route,
so no year appears here as a literal -- `probe_slice_boundary` re-measures it and the run manifest
records what that run found.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterable
from typing import Literal

import polars as pl

from ..constants import QCEW_DISCLOSURE_CODES
from ..contracts import QCEW_MONTHLY_SCHEMA
from ..errors import UnknownDisclosureCodeError
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


PARSER_VERSION = "qcew_monthly/1"

# The three published monthly employment levels, in the order the source lays them out: index i
# of this tuple is month i of the quarter, which is what `reference_month` is derived from.
_MONTH_COLUMNS = ("month1_emplvl", "month2_emplvl", "month3_emplvl")
# Every field a suppression can zero out. Wages join the months here because the true-zero rule
# asks whether the *whole cell* is zero, not just its employment.
_VALUE_COLUMNS = (*_MONTH_COLUMNS, "total_qtrly_wages")

# What makes a source row that row, and so what `source_row_hash` is taken over. All seven
# dimensions are load-bearing: on a single quarter of the slice fixture, dropping ownership,
# aggregation level and size class collapses 18 pairs of distinct observations onto shared
# hashes -- including area 26165 in 2017-03, where a suppressed Local Government cell and a
# Private cell reporting 93 would have shared one identity. `month_column` extends the quarterly
# key across the monthly expansion.
_ROW_IDENTITY_COLUMNS = (
    "area_fips",
    "own_code",
    "industry_code",
    "agglvl_code",
    "size_code",
    "year",
    "qtr",
    "month_column",
)


def is_true_zero_expr() -> pl.Expr:
    """True where a published zero is a real zero rather than a withheld value.

    The predicate is the establishment count, not the disclosure character. BLS publishes no
    titles file for `disclosure_code`, so nothing fetched defines what any code means; what Stage
    0 measured is that rows carrying zero establishments carry zero everything, while suppressed
    rows keep a positive establishment count. A cell with no establishments has no employment,
    which is the source-specific rule INV-003 requires before a zero may be read as substantive.
    """
    zero_value_columns = pl.all_horizontal(
        [pl.col(c).cast(pl.Int64, strict=False).fill_null(-1) == 0 for c in _VALUE_COLUMNS]
    )
    return (pl.col("qtrly_estabs").cast(pl.Int64, strict=False) == 0) & zero_value_columns


def _check_disclosure_codes(frame: pl.DataFrame) -> None:
    """Halt on any disclosure code outside the measured allowlist (§18.3)."""
    seen = set(frame["disclosure_code"].fill_null("").unique().to_list())
    unknown = sorted(seen - QCEW_DISCLOSURE_CODES)
    if unknown:
        raise UnknownDisclosureCodeError(
            f"disclosure codes {unknown} are outside the measured allowlist "
            f"{sorted(QCEW_DISCLOSURE_CODES)}"
        )


def _check_dash_rows_carry_no_establishments(frame: pl.DataFrame) -> None:
    """Halt if a '-' row carries establishments, which would break the true-zero premise."""
    offending = frame.filter(
        (pl.col("disclosure_code") == "-")
        & (pl.col("qtrly_estabs").cast(pl.Int64, strict=False) > 0)
    )
    if offending.height:
        raise ValueError(
            f"{offending.height} row(s) carry disclosure_code '-' with qtrly_estabs > 0; the "
            "true-zero rule rests on those two never co-occurring, so this run halts rather than "
            "guessing which reading is right"
        )


def parse_qcew_monthly(
    frame: pl.DataFrame,
    *,
    snapshot_id: str,
    release_vintage: str,
    release_status: str,
    naics_vintage: str,
) -> pl.DataFrame:
    """Turn quarterly QCEW rows into normalized monthly rows (§7.3, SRC-QCEW-002/003/004).

    Disclosure metadata is read first and numeric values are derived second, so a suppressed row's
    literal zero never becomes an integer employment level.
    """
    _check_disclosure_codes(frame)
    _check_dash_rows_carry_no_establishments(frame)

    suppressed = pl.col("disclosure_code") == "N"
    true_zero = is_true_zero_expr()

    prepared = frame.with_columns(
        pl.concat_str([pl.col("year"), pl.lit("Q"), pl.col("qtr")]).alias("reference_quarter"),
        pl.col("qtrly_estabs").cast(pl.Int64, strict=False).alias("qtrly_establishments"),
        pl.col("total_qtrly_wages").alias("wages_raw"),
        pl.when(suppressed)
        .then(None)
        .otherwise(pl.col("total_qtrly_wages").cast(pl.Int64, strict=False))
        .alias("wages_value"),
        true_zero.alias("is_true_zero"),
        pl.when(suppressed)
        .then(pl.lit("suppressed"))
        .when(true_zero)
        .then(pl.lit("true_zero"))
        .otherwise(pl.lit("observed"))
        .alias("observation_status"),
    )

    monthly = prepared.unpivot(
        index=[c for c in prepared.columns if c not in _MONTH_COLUMNS],
        on=list(_MONTH_COLUMNS),
        variable_name="month_column",
        value_name="employment_raw",
    ).with_columns(
        pl.col("month_column").str.extract(r"^month(\d)_emplvl$", 1).cast(pl.Int64).alias("mi")
    )

    return (
        monthly.with_columns(
            pl.format(
                "{}-{}",
                pl.col("year"),
                ((pl.col("qtr").cast(pl.Int64) - 1) * 3 + pl.col("mi"))
                .cast(pl.String)
                .str.pad_start(2, "0"),
            ).alias("reference_month"),
            pl.when(suppressed)
            .then(None)
            .otherwise(pl.col("employment_raw").cast(pl.Int64, strict=False))
            .alias("employment_value"),
            (pl.col("employment_raw") == "0").alias("is_published_numeric_zero"),
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(release_vintage).alias("release_vintage"),
            pl.lit(release_status).alias("release_status"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.when(pl.col("agglvl_code") == "18")
            .then(pl.lit("national"))
            .when(pl.col("agglvl_code") == "58")
            .then(pl.lit("state"))
            .otherwise(pl.lit("other"))
            .alias("area_type"),
            pl.when(pl.col("area_fips") == "US000")
            .then(None)
            .otherwise(pl.col("area_fips").str.slice(0, 2))
            .alias("state_fips"),
            pl.col("own_code").alias("ownership_code"),
            pl.col("agglvl_code").alias("aggregation_level"),
            pl.concat_str([pl.col(c) for c in _ROW_IDENTITY_COLUMNS], separator="|")
            .map_elements(
                lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest(), return_dtype=pl.String
            )
            .alias("source_row_hash"),
        )
        .sort(["area_fips", "reference_month"])
        .select(list(QCEW_MONTHLY_SCHEMA))
        .cast(QCEW_MONTHLY_SCHEMA)  # type: ignore[arg-type]
    )
