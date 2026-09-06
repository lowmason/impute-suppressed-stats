"""The substitute allocation anchor, and the gate that admits it.

WHY THIS MODULE EXISTS. §12.2 defines the residual `R_t = N_t - sum_{s in D_t} E^obs` "for a
compatible national total N_t" and never defines *compatible*. §5.5 does, listing ten dimensions
that MUST be evaluated before a source value is used. Nine match by construction here, because
N_t and the state rows are the same field of the same QCEW file: reference period; industry code
and NAICS vintage (one §5.5 bullet, not two); ownership coverage; employment concept; statistical
unit; size concept; release vintage and revision status; disclosure and noise regime -- both rows
come from one BLS disclosure regime, and that the national cell survives suppression while many
state cells do not is that regime operating as designed, not a difference in it; and exact rather
than rounded, sampled, or modeled values. The tenth, the geography universe, is exactly what
`closure_audit` measures.

WHAT THE GATE TESTS, AND WHAT IT DOES NOT. It tests the *universe*, not the *measure*. National
`qtrly_establishments` minus the sum over all published state rows -- including the
employment-suppressed ones, which still publish establishment counts -- must be exactly 0. Gap-0
closure forces every absent area to contribute zero establishments, and a QCEW area with zero
establishments classified into the industry has no covered jobs under §3.2's estimand. It does NOT
verify the employment identity; `SRC-QCEW-006`'s `decline` stands and this module does not rescue
it.

HONEST CAVEAT. `qtrly_establishments` is constant within a state-quarter, so a per-month gate
re-tests each quarterly value three times. A contamination confined to one month inside a quarter
is undetectable by construction. The gate is quarterly-resolution evidence wearing a monthly
shape, and it is recorded per month only because the residual is monthly.

WHAT THIS IS NOT. The anchor is a `modeling_assumption` (INV-004), never a constraint row. No row
is built, `assert_no_national_employment_margin` stays in force unqualified, and INV-005 keeps a
modeling assumption out of the deterministic feasible set. The adding-up restriction to R_t does
imply E_{s,t} <= R_t on every imputed cell -- a restriction the deterministic engine does not
have -- but that ceiling is DERIVED FROM A PUBLISHED NUMBER, not synthesized from a percentile or
a threshold guess, which is what distinguishes it from §9.3's "arbitrary top-class caps". It must
never be written back into `deterministic_bounds`.

RETIREMENT CONDITION. If a future QCEW vintage ever yields a month with no suppressed state cell,
`SRC-QCEW-006` becomes testable on that month. At that point assert `abs(R_t) <= tolerance`, fail
closed otherwise, and retire this anchor in favour of the verified identity -- rather than keeping
both and letting them disagree silently.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

from ..contracts import ANCHOR_AUDIT_SCHEMA
from ..errors import ConceptViolationError, UniverseClosureError

DISCLOSED_STATUSES: tuple[str, ...] = ("observed", "true_zero")
DECLARED_NATIONAL_TOTAL = "declared_national_total"


@dataclass(frozen=True)
class Partition:
    """One month's split of the state panel into disclosed and missing cells.

    A (state, month) with no published row is in NEITHER frame. On the D1 window that is 84 pairs
    -- ND absent 48 months, DE absent 36 -- plus DC, which publishes no row in any month. Their
    employment, if any, sits inside the residual with no cell to receive it; the closure gate is
    what licenses treating that quantity as zero.
    """

    disclosed: pl.DataFrame
    missing: pl.DataFrame


@dataclass(frozen=True)
class Anchor:
    """One month's allocation target: what to allocate, and over which cells."""

    reference_month: str
    residual: float
    missing_cells: tuple[str, ...]
    anchor_basis: str


def observed_partition(monthly: pl.DataFrame) -> dict[str, Partition]:
    """The production partition: disclosed is observed plus true_zero, missing is suppressed.

    This is the DEFAULT partition builder. `national_residual` takes a `Partition` argument rather
    than calling this, so Stage 4's pseudo-suppression mask can supply a different one without
    mutating `qcew_monthly` or reimplementing the residual.
    """
    states = monthly.filter(pl.col("area_type") == "state")
    out: dict[str, Partition] = {}
    for (month,), group in states.group_by("reference_month", maintain_order=True):
        out[str(month)] = Partition(
            disclosed=group.filter(pl.col("observation_status").is_in(DISCLOSED_STATUSES)),
            missing=group.filter(pl.col("observation_status") == "suppressed"),
        )
    return out


def _disclosed_sum(partition: Partition, reference_month: str) -> float:
    """Total published employment across the disclosed cells, refusing a null.

    `fill_null(0)` reads like null handling and is a no-op -- Polars' `sum()` already skips nulls
    -- so a suppressed cell mistakenly placed in `disclosed` would contribute 0 and silently
    inflate R_t by its true employment, handing the anchor employees that no cell in the missing
    set can receive. This function takes an arbitrary caller-supplied partition (that is the whole
    point of the mask-parameterised signature), so the D_t/M_t confusion is refused here rather
    than trusted not to happen.
    """
    for name, frame in (("disclosed", partition.disclosed), ("missing", partition.missing)):
        strays = set(frame["reference_month"].to_list()) - {reference_month}
        if strays:
            raise ConceptViolationError(
                f"{reference_month}: the {name} frame carries rows for {sorted(strays)}; a "
                "partition belongs to exactly one month, and summing another month's rows into "
                "this month's disclosed total silently moves the residual"
            )
    nulls = partition.disclosed.filter(pl.col("employment_value").is_null())
    if nulls.height:
        raise ConceptViolationError(
            f"{reference_month}: {nulls.height} disclosed cell(s) carry a null employment_value "
            f"(state_fips {sorted(set(nulls['state_fips'].to_list()))}); a cell with no published "
            "value belongs in the missing set, and summing it as zero would inflate the residual"
        )
    return float(partition.disclosed["employment_value"].sum() or 0.0)


def _national_row(monthly: pl.DataFrame, reference_month: str) -> dict[str, object]:
    """The single national row for a month, or a halt naming the month."""
    rows = monthly.filter(
        (pl.col("area_type") == "national") & (pl.col("reference_month") == reference_month)
    )
    if rows.height != 1:
        raise UniverseClosureError(
            f"{reference_month}: expected exactly one national row, found {rows.height}"
        )
    return rows.row(0, named=True)


def national_residual(
    monthly: pl.DataFrame, partition: Partition, *, reference_month: str
) -> Anchor:
    """§12.2's residual for one month, over the partition the caller supplies.

    MUST NOT consult `observation_status`: the partition argument is authoritative. A `true_zero`
    cell contributes 0 to the disclosed sum, which is why it belongs in `disclosed` rather than
    `missing` -- it is a published value, and imputing it would overwrite a fact.
    """
    national = _national_row(monthly, reference_month)
    disclosed_sum = float(_disclosed_sum(partition, reference_month))
    residual = float(national["employment_value"]) - disclosed_sum
    return Anchor(
        reference_month=reference_month,
        residual=residual,
        missing_cells=tuple(partition.missing["state_fips"].to_list()),
        anchor_basis=DECLARED_NATIONAL_TOTAL,
    )


def closure_audit(monthly: pl.DataFrame, partitions: Mapping[str, Partition]) -> pl.DataFrame:
    """Every number the admission gate looked at, one row per month, passing or not.

    The audit is written whether or not the gate passes, so a failing run leaves the evidence that
    explains it rather than only an exception.
    """
    states = monthly.filter(pl.col("area_type") == "state")
    empty = Partition(disclosed=states.head(0), missing=states.head(0))
    # Driven by the months present in `monthly`, NOT by the partition keys. `observed_partition`
    # emits a key only for months that have state rows, so a month publishing a national row with
    # no state rows at all would be absent from the audit entirely and `assert_universe_closes`
    # would pass over it in silence -- the one shape most likely to mean a truncated ingest.
    # Looking the partition up with an empty default makes such a month appear with
    # `state_establishments_sum = 0` and a gap equal to the national count, which is a failure.
    rows: list[dict[str, object]] = []
    for month in sorted(monthly["reference_month"].unique().to_list()):
        part = partitions.get(month, empty)
        national = _national_row(monthly, month)
        published = states.filter(pl.col("reference_month") == month)
        national_est = int(national["qtrly_establishments"])
        state_est = int(published["qtrly_establishments"].fill_null(0).sum())
        disclosed_sum = int(_disclosed_sum(part, month))
        residual = int(national["employment_value"]) - disclosed_sum
        missing_n = part.missing.height
        missing_est = int(part.missing["qtrly_establishments"].fill_null(0).sum())
        rows.append(
            {
                "reference_month": month,
                "national_total": int(national["employment_value"]),
                "national_establishments": national_est,
                "state_establishments_sum": state_est,
                "establishment_gap": national_est - state_est,
                "publishing_area_count": published.height,
                "disclosed_sum": disclosed_sum,
                "disclosed_count": part.disclosed.height,
                "residual": residual,
                "missing_set_size": missing_n,
                "anchored": national_est - state_est == 0 and residual >= 0,
                # A falsification band, not an accuracy score: implied employees per establishment
                # across the missing set. It is EXPECTED to sit below the disclosed states'
                # intensity, because suppression tracks small, less employment-dense states --
                # measured on D1, implied runs 2.88-4.46 against disclosed 5.44-6.38, a ratio of
                # 0.48-0.74 in 96 of 96 months. A ratio near or above 1, or one far below that
                # band, is the signal; "differs from disclosed" on its own is the normal case and
                # would fire on every month of a window this same run declares admissible.
                "implied_intensity": (residual / missing_est) if missing_est else None,
            }
        )
    return pl.DataFrame(rows, schema=ANCHOR_AUDIT_SCHEMA)


def assert_universe_closes(audit: pl.DataFrame) -> None:
    """Halt the whole run if any month's establishment universes fail to close (§18.3).

    Not a per-month decline. A nonzero gap means the published national row contains a component
    the state table does not, which makes every month's residual suspect rather than one month's.
    """
    broken = audit.filter(pl.col("establishment_gap") != 0)
    if broken.height:
        first = broken.row(0, named=True)
        raise UniverseClosureError(
            f"establishment universes do not close in {broken.height} month(s); "
            f"first {first['reference_month']}: national {first['national_establishments']} "
            f"minus state sum {first['state_establishments_sum']} "
            f"= {first['establishment_gap']} across "
            f"{first['publishing_area_count']} publishing areas"
        )
    negative = audit.filter(pl.col("residual") < 0)
    if negative.height:
        first = negative.row(0, named=True)
        raise UniverseClosureError(
            f"{first['reference_month']}: residual {first['residual']} is negative, so the "
            "disclosed cells already exceed the published national total"
        )
