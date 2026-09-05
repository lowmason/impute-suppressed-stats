"""The §5.5 compatibility gates that run before any constraint row is created.

Two checks, and the asymmetry between them is the point of this module.

`assert_definitional_alignment` is Stage 1's. SRC-QCEW-007 requires it here rather than on the
build path, because it guards constraint construction: a misaligned national/state pair must never
reach the point where it could become a hard equation.

`assert_size_margin_compatible` is this stage's, and it is what licenses treating the national
by-size file and the national all-sizes row as one universe. §7.4's field list carries no ownership
column, so the harmonized layer cannot grant that licence by itself. What the gate can and cannot
show, stated rather than assumed: the *establishment* margin is checkable in all eight window
years, because every establishment cell is published; the *employment* margin is checkable in
exactly one, 2017, the only year with no suppressed class. A passing gate therefore rests mostly on
establishments, and reading it as proof that the two employment universes agree year by year would
be reading more than it measures. `employment_checkable_years` in the report is what keeps that
distinction visible to a caller.
"""

from __future__ import annotations

import polars as pl

from ..contracts import HarmonizedData
from ..errors import ConceptViolationError, IncompatibleMarginError
from ..harmonize.universe import assert_definitional_alignment

MARCH_SUFFIX = "-03"


def assert_size_support_holds(size_rows: pl.DataFrame) -> int:
    """Halt unless every observed size row lies inside its own class band.

    The rule under test is `n * lower <= employment <= n * upper`: a class of `n` establishments
    each holding between `lower` and `upper` employees can hold no more and no less in total. That
    is what makes the support a §9.3 "documented size support" rather than an assumption, and
    checking it against published rows is what keeps it measured. A null `size_upper` is an
    open-ended top class, checked on its lower side only.

    Returns the number of observed rows checked, so a caller can record that the gate had something
    to check rather than passing vacuously.
    """
    observed = size_rows.filter(pl.col("observation_status") == "observed")
    violations = observed.filter(
        (pl.col("employment") < pl.col("establishments") * pl.col("size_lower"))
        | (
            pl.col("size_upper").is_not_null()
            & (pl.col("employment") > pl.col("establishments") * pl.col("size_upper"))
        )
    )
    if violations.height:
        first = violations.row(0, named=True)
        raise ConceptViolationError(
            f"{violations.height} observed row(s) fall outside their own size support, e.g. "
            f"{first['reference_year']} class {first['size_class']}: {first['employment']} "
            f"employees across {first['establishments']} establishments in band "
            f"[{first['size_lower']}, {first['size_upper']}]. The class titles do not describe "
            "published data, so the support may not be built as a hard constraint"
        )
    return observed.height


def assert_size_margin_compatible(
    monthly: pl.DataFrame, size_rows: pl.DataFrame
) -> dict[str, object]:
    """Halt unless the national by-size rows and the national all-sizes row are one universe.

    Four conditions, each a §5.5 gate item: one row per year and class (statistical unit and
    ownership coverage -- a second ownership universe in the file would show up here as a duplicate
    key); the published establishment sum equals the all-sizes establishment count (geography and
    ownership); every size row is March-referenced (reference period, INV-011); and the size rows'
    NAICS vintage matches the national row's for that month (industry vintage).
    """
    off_march = size_rows.filter(~pl.col("reference_month").str.ends_with(MARCH_SUFFIX))
    if off_march.height:
        raise ConceptViolationError(
            f"{off_march.height} size row(s) are not March-referenced, e.g. "
            f"{off_march['reference_month'][0]}; a March-reference class bound may not be built "
            "for another month (INV-011, §11.9)"
        )

    duplicates = (
        size_rows.group_by(["reference_year", "size_class"]).len().filter(pl.col("len") > 1)
    )
    if duplicates.height:
        first = duplicates.row(0, named=True)
        raise IncompatibleMarginError(
            f"{duplicates.height} (year, size_class) key(s) carry more than one row, e.g. "
            f"{first['reference_year']} class {first['size_class']}; a second ownership or "
            "geography universe in the by-size file would look exactly like this (INV-007)"
        )

    national = monthly.filter(
        (pl.col("area_type") == "national") & pl.col("reference_month").str.ends_with(MARCH_SUFFIX)
    ).select(["reference_month", "naics_vintage", "qtrly_establishments", "employment_value"])
    joined = (
        size_rows.group_by(["reference_year", "reference_month"])
        .agg(
            pl.col("establishments").sum().alias("size_establishments"),
            pl.col("naics_vintage").n_unique().alias("size_vintages"),
            pl.col("naics_vintage").first().alias("size_vintage"),
            pl.col("employment").sum().alias("observed_employment"),
            (pl.col("observation_status") == "suppressed").sum().alias("suppressed_classes"),
        )
        .join(national, on="reference_month", how="left")
        .sort("reference_year")
    )

    missing = joined.filter(pl.col("qtrly_establishments").is_null())
    if missing.height:
        raise IncompatibleMarginError(
            f"{missing.height} size year(s) have no national all-sizes row to close against, "
            f"e.g. {missing['reference_month'][0]}; the margin has no right-hand side"
        )

    gaps = joined.with_columns(
        (pl.col("qtrly_establishments") - pl.col("size_establishments")).alias("estab_gap")
    )
    bad = gaps.filter((pl.col("estab_gap") != 0) | (pl.col("size_vintages") > 1))
    if bad.height:
        first = bad.row(0, named=True)
        raise IncompatibleMarginError(
            f"{bad.height} year(s) fail the establishment check, e.g. {first['reference_year']}: "
            f"by-size sum {first['size_establishments']} against all-sizes "
            f"{first['qtrly_establishments']} (gap {first['estab_gap']}), size vintages "
            f"{first['size_vintages']}. Stacking these would join two universes (INV-007)"
        )

    # `ne_missing`, not `!=`: a plain inequality yields null when either side is null, and a null
    # predicate is dropped by `filter`, so a size row whose national counterpart has no recorded
    # NAICS vintage would pass a gate whose entire purpose is to halt. `ne_missing` treats null as
    # a value that differs from a non-null one, which is the fail-closed reading.
    vintage_conflict = gaps.filter(pl.col("size_vintage").ne_missing(pl.col("naics_vintage")))
    if vintage_conflict.height:
        first = vintage_conflict.row(0, named=True)
        raise IncompatibleMarginError(
            f"{vintage_conflict.height} year(s) pair NAICS vintages that differ, e.g. "
            f"{first['reference_year']}: size {first['size_vintage']} against national "
            f"{first['naics_vintage']} (INV-007)"
        )

    return {
        "years_checked": gaps["reference_year"].to_list(),
        "establishment_gap_by_year": dict(
            zip(gaps["reference_year"].to_list(), gaps["estab_gap"].to_list(), strict=True)
        ),
        "employment_checkable_years": gaps.filter(pl.col("suppressed_classes") == 0)[
            "reference_year"
        ].to_list(),
        "observed_support_rows_checked": assert_size_support_holds(size_rows),
    }


def run_compatibility_gates(data: HarmonizedData, *, industry_code: str) -> dict[str, object]:
    """Every gate, in the order a constraint builder needs them. Returns the margin report."""
    assert_definitional_alignment(data.qcew_monthly)
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry_code)
    return assert_size_margin_compatible(data.qcew_monthly, size)
