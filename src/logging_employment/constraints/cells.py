"""§7.7 target cells: one row per atomic cell in the constraint universe.

§9.2 fixes the atomic key at state x month x ownership x NAICS x release_vintage for state totals,
and adds the March-reference size class for the size universe. `cell_id` does not encode that key
literally: `_ID_FIELDS` always carries `size_class` and always omits `release_vintage`. It also
stamps the family onto the front of the id, because §7.7 requires size cells and total cells to
have distinct IDs and a shared prefix would leave that to luck.

`size_class` in `_ID_FIELDS` is the real §9.2 key field for a size cell, but a total cell (state or
national) has no size class in its own universe; it carries `size_class` only because §7.7's row
schema gives every `target_cell` row that column, and fills it with the synthetic
`TOTAL_SIZE_CLASS` ("ALL") to satisfy that schema. `release_vintage` is omitted from `_ID_FIELDS`
entirely. Separately, `_assert_one_vintage_per_cell` groups `qcew_monthly` by `area_fips` and
`reference_month` and raises (INV-007) when a group carries more than one distinct
`release_vintage` -- one area-month published under more than one vintage.

`qcew_national_size` carries no ownership column -- §7.4's field list has none -- so the ownership
code stamped on a size cell comes from configuration. What licenses that stamp is
`compat.assert_size_margin_compatible`, which must have passed before these cells are used; the
stamp records a decision the gate justified, not one this module verified.
"""

from __future__ import annotations

from collections.abc import Iterable

import polars as pl

from ..contracts import TARGET_CELL_SCHEMA, HarmonizedData
from ..errors import ConceptViolationError

KIND_STATE_TOTAL = "state_total"
KIND_NATIONAL_TOTAL = "national_total"
KIND_NATIONAL_SIZE = "national_size"

# `state_fips` on a national cell. Not a FIPS code, and deliberately not null: a null would be
# indistinguishable from a missing value in a join, and no two-character FIPS can collide with it.
NATIONAL_STATE_FIPS = "US"

# §7.7: "For the state-total model, use a synthetic total size class such as `ALL`."
TOTAL_SIZE_CLASS = "ALL"

_ID_FIELDS = (
    "state_fips",
    "reference_month",
    "ownership_code",
    "industry_code",
    "naics_vintage",
    "size_class",
)


def cell_id(
    kind: str,
    *,
    state_fips: str,
    reference_month: str,
    ownership_code: str,
    industry_code: str,
    naics_vintage: str,
    size_class: str,
) -> str:
    """The identifier for one atomic cell: kind and key (state, month, ownership, industry,
    naics_vintage, size_class), pipe-separated."""
    return (
        f"{kind}|{state_fips}|{reference_month}|{ownership_code}|{industry_code}|"
        f"{naics_vintage}|{size_class}"
    )


def _cell_id_expr(kind: str) -> pl.Expr:
    """`cell_id` as an expression over columns already named for the key.

    Kept beside the string form, and pinned equal to it by a test: two encodings of one identifier
    that drift apart would produce cells no coefficient row could find.

    `concat_str` returns null when any input is null, and that is the behaviour to keep rather than
    paper over: coercing a missing key field into the literal string "None" would manufacture a
    plausible-looking `cell_id` for a cell that has no real key. It is not, by itself, a guarantee
    that the null gets caught. `validate_frame` checks only column names and dtypes, never values,
    so a null `cell_id` passes it silently, and the duplicate check in `build_target_cells` only
    raises when two or more rows share one id -- a single null `cell_id` would ship undetected.
    This expression keeps the identifier honest when a key field is null; it does not, on its own,
    turn that into a build failure.
    """
    return pl.concat_str(
        [pl.lit(kind), *(pl.col(name) for name in _ID_FIELDS)], separator="|"
    ).alias("cell_id")


def _select(frame: pl.DataFrame, kind: str, size_concept: str, value_column: str) -> pl.DataFrame:
    """Project a source frame onto §7.7's twelve fields, in the spec's order."""
    return frame.select(
        _cell_id_expr(kind),
        pl.col("state_fips"),
        pl.col("reference_month"),
        pl.lit(size_concept).alias("size_concept"),
        pl.col("size_class"),
        pl.col("ownership_code"),
        pl.col("industry_code"),
        pl.col("naics_vintage"),
        pl.col("observation_status"),
        pl.col(value_column).alias("observed_value"),
        pl.col("snapshot_id").alias("source_snapshot_id"),
        pl.col("disclosure_code").alias("qcew_disclosure_code"),
    ).cast(TARGET_CELL_SCHEMA)  # type: ignore[arg-type]


def state_total_cells(monthly: pl.DataFrame, *, size_concept: str) -> pl.DataFrame:
    """One cell per published state-month, whatever its observation status."""
    rows = monthly.filter(pl.col("area_type") == "state").with_columns(
        pl.lit(TOTAL_SIZE_CLASS).alias("size_class")
    )
    return _select(rows, KIND_STATE_TOTAL, size_concept, "employment_value")


def national_total_cells(
    monthly: pl.DataFrame, *, size_concept: str, reference_months: Iterable[str]
) -> pl.DataFrame:
    """One cell per national month that a size margin needs.

    Restricted to the months named by the caller rather than emitting all 96. A national cell that
    no constraint touches would add an isolated observed cell to the system and, worse, would read
    as a national/state link that `SRC-QCEW-006`'s `decline` forbids.
    """
    rows = monthly.filter(
        (pl.col("area_type") == "national")
        & pl.col("reference_month").is_in(list(reference_months))
    ).with_columns(
        pl.lit(NATIONAL_STATE_FIPS).alias("state_fips"),
        pl.lit(TOTAL_SIZE_CLASS).alias("size_class"),
    )
    return _select(rows, KIND_NATIONAL_TOTAL, size_concept, "employment_value")


def national_size_cells(
    size_rows: pl.DataFrame, *, ownership_code: str, size_concept: str
) -> pl.DataFrame:
    """One cell per published national size class. Caller filters to the target industry first."""
    rows = size_rows.with_columns(
        pl.lit(NATIONAL_STATE_FIPS).alias("state_fips"),
        pl.lit(ownership_code).alias("ownership_code"),
    )
    return _select(rows, KIND_NATIONAL_SIZE, size_concept, "employment")


def _assert_one_vintage_per_cell(monthly: pl.DataFrame) -> None:
    """Halt if one area-month is published under more than one release vintage (INV-007)."""
    offending = (
        monthly.group_by(["area_fips", "reference_month"])
        .agg(pl.col("release_vintage").n_unique().alias("vintages"))
        .filter(pl.col("vintages") > 1)
    )
    if offending.height:
        first = offending.row(0, named=True)
        raise ConceptViolationError(
            f"{offending.height} area-month(s) carry more than one release vintage, e.g. "
            f"{first['area_fips']} {first['reference_month']}; stacking them into one cell would "
            "merge two vintages of the same published value (INV-007)"
        )


# The three statuses every constraint builder covers. `contracts.OBSERVATION_STATUSES` also allows
# `absent`, which Stage 1's parser never writes: DC publishes no row at all rather than an absent
# one, so absence shows up as a missing row, not as a cell. A cell carrying `absent` would receive
# neither a fixing row (which covers observed and true_zero) nor a nonnegativity row (which covers
# suppressed), would reach the solver with an unbounded box in both directions, and would match no
# branch of `classify_bound_status`.
_CONSTRAINABLE_STATUSES = frozenset({"observed", "true_zero", "suppressed"})


def _assert_every_cell_is_constrainable(cells: pl.DataFrame) -> None:
    """Halt on a cell no builder would cover, or a published cell with no parseable value.

    Both conditions are measured absent from the D1 window -- 0 rows carry a fourth status and 0
    non-suppressed rows carry a null value -- and both are §18.3 conditions rather than rows to
    skip: a published cell whose value did not parse is a parser defect, and silently dropping it
    would remove a public accounting fact from the system.
    """
    unhandled = sorted(set(cells["observation_status"].to_list()) - _CONSTRAINABLE_STATUSES)
    if unhandled:
        raise ConceptViolationError(
            f"observation status(es) {unhandled} reached the cell index; no constraint builder "
            f"covers them, so those cells would reach the solver unconstrained"
        )
    unparsed = cells.filter(
        (pl.col("observation_status") != "suppressed") & pl.col("observed_value").is_null()
    )
    if unparsed.height:
        raise ConceptViolationError(
            f"{unparsed.height} published cell(s) carry no value, e.g. "
            f"{unparsed['cell_id'][0]}; a published cell with no parseable value is a parser "
            "defect, not a cell to skip (§18.3)"
        )


def build_target_cells(
    data: HarmonizedData, *, industry_code: str, ownership_code: str, size_concept: str
) -> pl.DataFrame:
    """The whole §7.7 target-cell index, sorted by `cell_id`."""
    _assert_one_vintage_per_cell(data.qcew_monthly)
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry_code)
    months = sorted(set(size["reference_month"].to_list()))
    built = pl.concat(
        [
            state_total_cells(data.qcew_monthly, size_concept=size_concept),
            national_total_cells(
                data.qcew_monthly, size_concept=size_concept, reference_months=months
            ),
            national_size_cells(size, ownership_code=ownership_code, size_concept=size_concept),
        ]
    ).sort("cell_id")
    duplicates = built.group_by("cell_id").len().filter(pl.col("len") > 1)
    if duplicates.height:
        raise ConceptViolationError(
            f"{duplicates.height} duplicate cell_id(s), e.g. {duplicates['cell_id'][0]}; §9.2 "
            "requires every atomic key to be mutually exclusive within a constraint system"
        )
    _assert_every_cell_is_constrainable(built)
    return built
