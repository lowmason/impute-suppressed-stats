"""QCEW establishment-size ingestion: a national six-digit benchmark, first quarter only."""

from __future__ import annotations

import io
import zipfile

import polars as pl

from ..constants import (
    INDUSTRY_CODE,
    QCEW_ALL_SIZES_CODE,
    QCEW_DISCLOSURE_CODES,
)
from ..contracts import QCEW_NATIONAL_SIZE_SCHEMA
from ..errors import (
    MissingCrossTabulationError,
    UnknownDisclosureCodeError,
    UnknownSizeCodeError,
)
from .qcew import BULK_ONLY_TITLE_COLUMNS, BULK_TO_SLICE_COLUMNS

BY_SIZE_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip"

PARSER_VERSION = "qcew_national_size/1"

# Employment bounds for every size class BLS publishes a title for, code 0 excepted: "All
# establishment sizes" is a total over the dimension rather than a range within it, so it has no
# bounds to carry. Code 9's title is "1000 or more employees per establishment" -- open-ended, so
# its upper bound is null rather than a number invented to close it.
#
# These are not typed from documentation: the by-size file ships its own `size_title` column, and
# `test_size_class_bounds_agree_with_the_titles_the_file_publishes` re-derives this whole table
# from the fixture's titles and asserts it matches. The reader drops `size_title` for schema
# parity with the quarterly routes, so the derivation happens in the test, against raw bytes.
SIZE_CLASS_BOUNDS: dict[str, tuple[int, int | None]] = {
    "1": (0, 4),
    "2": (5, 9),
    "3": (10, 19),
    "4": (20, 49),
    "5": (50, 99),
    "6": (100, 249),
    "7": (250, 499),
    "8": (500, 999),
    "9": (1000, None),
}


def read_by_size_zip(raw: bytes) -> pl.DataFrame:
    """Read the single CSV member of a `<year>_q1_by_size.zip`, every column as String.

    The by-size file speaks the *bulk* column vocabulary -- `qtrly_estabs_count` rather than
    `qtrly_estabs`, plus the five title columns -- so the same reconciliation the bulk route
    already needed is reused here rather than a second mapping written for one publisher.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {members}")
        with archive.open(members[0]) as handle:
            frame = pl.read_csv(handle.read(), infer_schema_length=0)
    frame = frame.rename({k: v for k, v in BULK_TO_SLICE_COLUMNS.items() if k in frame.columns})
    return frame.drop([c for c in BULK_ONLY_TITLE_COLUMNS if c in frame.columns])


def assert_no_state_industry_size(frame: pl.DataFrame, industry: str) -> None:
    """Halt if any aggregation level carries state geography, this industry, and size at once.

    Named for the predicate it checks, which is narrower than "this file has no state rows": the
    by-size file does carry non-national areas at some aggregation levels. What §2.2 row 3 rests
    on is that none of those levels also carries the six-digit industry with a size breakout, and
    that is what this checks. Halting is the §18.3 response to a requested cross-tabulation that
    is absent -- and, symmetrically, to one that turns out to be present when the spec assumed it
    was not.
    """
    industry_rows = frame.filter(pl.col("industry_code") == industry)
    offending = industry_rows.filter(
        (~pl.col("area_fips").str.starts_with("US")) & (pl.col("size_code") != QCEW_ALL_SIZES_CODE)
    )
    if offending.height:
        levels = sorted(offending["agglvl_code"].unique().to_list())
        raise MissingCrossTabulationError(
            f"state x {industry} x size rows appear at aggregation level(s) {levels}; §2.2 row 3 "
            "assumed no such table exists, so this run halts rather than proceeding on a premise "
            "the file just contradicted"
        )


def _check_disclosure_codes(frame: pl.DataFrame) -> None:
    """Halt on any disclosure code outside the measured allowlist (§18.3)."""
    seen = set(frame["disclosure_code"].fill_null("").unique().to_list())
    unknown = sorted(seen - QCEW_DISCLOSURE_CODES)
    if unknown:
        raise UnknownDisclosureCodeError(
            f"disclosure codes {unknown} are outside the measured allowlist "
            f"{sorted(QCEW_DISCLOSURE_CODES)}"
        )


def _check_size_codes(frame: pl.DataFrame) -> None:
    """Halt on a size code with no published bounds, rather than emitting a null range."""
    unknown = sorted(set(frame["size_code"].unique().to_list()) - set(SIZE_CLASS_BOUNDS))
    if unknown:
        raise UnknownSizeCodeError(
            f"size codes {unknown} carry no published bounds; known codes are "
            f"{sorted(SIZE_CLASS_BOUNDS)}"
        )


def parse_qcew_national_size(
    frame: pl.DataFrame,
    *,
    snapshot_id: str,
    reference_year: int,
    naics_vintage: str,
    industry: str = INDUSTRY_CODE,
) -> pl.DataFrame:
    """Build `qcew_national_size` from the by-size file (§7.4).

    Every row is stamped with March of the reference year. That is not a convenience:
    SRC-QSIZE-001 requires the March classification definition to survive into the table, and the
    file itself is first-quarter-only, so a row that lost its March stamp could not be recovered
    from the data.

    The dimensionality check runs here rather than being left to a caller, because SRC-QSIZE-002
    binds *the parser*: a guarantee only the test suite invokes is not one the build path has.

    `observation_status` is binary. `qcew_monthly` needs a true-zero rule because suppressed and
    genuinely-zero cells both publish `0`; measured on the shipped fixture, no row this parser
    emits carries zero establishments, so that case does not arise here. A test pins the
    measurement so a later file cannot quietly invalidate it.
    """
    assert_no_state_industry_size(frame, industry)

    national = frame.filter(
        (pl.col("size_code") != "0") & (pl.col("area_fips").str.starts_with("US"))
    )
    _check_disclosure_codes(national)
    _check_size_codes(national)

    return (
        national.with_columns(
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(reference_year).cast(pl.Int64).alias("reference_year"),
            pl.lit(f"{reference_year}Q1").alias("reference_quarter"),
            pl.lit(f"{reference_year}-03").alias("reference_month"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.col("size_code").alias("size_class"),
            # No `default=`: an unmapped code must raise, not silently null its bounds. The guard
            # above catches it first with a named error; this keeps the invariant local too.
            pl.col("size_code")
            .replace_strict({k: v[0] for k, v in SIZE_CLASS_BOUNDS.items()})
            .cast(pl.Int64)
            .alias("size_lower"),
            pl.col("size_code")
            .replace_strict({k: v[1] for k, v in SIZE_CLASS_BOUNDS.items()})
            .cast(pl.Int64)
            .alias("size_upper"),
            pl.col("qtrly_estabs").cast(pl.Int64, strict=False).alias("establishments"),
            pl.when(pl.col("disclosure_code") == "N")
            .then(None)
            .otherwise(pl.col("month3_emplvl").cast(pl.Int64, strict=False))
            .alias("employment"),
            pl.when(pl.col("disclosure_code") == "N")
            .then(pl.lit("suppressed"))
            .otherwise(pl.lit("observed"))
            .alias("observation_status"),
        )
        .sort(["industry_code", "size_class"])
        .select(list(QCEW_NATIONAL_SIZE_SCHEMA))
        .cast(QCEW_NATIONAL_SIZE_SCHEMA)  # type: ignore[arg-type]
    )
