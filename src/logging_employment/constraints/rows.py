"""§7.8 constraint rows: the factory, and the four restrictions it refuses to build.

Every restriction in the system passes through `constraint`. That is deliberate: INV-004 requires
each one to carry a label, and §9.3 names forms that must never become hard equations. A guard
placed at the single construction point cannot be bypassed by a builder written later, which a
review checklist can.

`evidence_kind` is what licenses a restriction, and §7.8's field list has no column for it, so the
factory writes it into `provenance_text` behind a fixed `evidence_kind=` prefix. That keeps the
warrant queryable in the persisted table rather than only in this module's arguments.

What the vintage guard here does and does not cover, because INV-007 is easy to overclaim. This
module sees exactly one vintage: `naics_vintage`, which is the only vintage `target_cell` carries.
`vintage_status` reads that and nothing else, so the factory's refusal is a refusal to make a hard
row spanning two NAICS vintages. `release_vintage` is not visible here at all. It is guarded
separately and more narrowly by `cells._assert_one_vintage_per_cell`, which raises when a single
area-month is published under more than one release vintage -- one cell built from two
publications. That check says nothing about a row spanning two *different* area-months whose
release vintages differ, and neither does this one. On the pilot window that silence is correct
rather than a hole: `qcew_monthly` carries 32 release vintages, one per reference quarter, so
period-to-period variation in `release_vintage` is the ordinary state of a retrospective panel and
not an incompatibility. Neither check, alone or together, should be cited as a general INV-007
guarantee.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from ..contracts import (
    CONSTRAINT_CLASSES,
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    EVIDENCE_KINDS,
    EVIDENCE_PREFIX,
    HARD_ELIGIBLE_CLASSES,
    RELATIONS,
)
from ..errors import ConceptViolationError, HardConstraintClassError, IncompatibleMarginError
from .cells import (
    KIND_NATIONAL_SIZE,
    KIND_NATIONAL_TOTAL,
    KIND_STATE_TOTAL,
    NATIONAL_STATE_FIPS,
)


@dataclass(frozen=True)
class ConstraintDraft:
    """One §7.8 row and its §7.9 coefficients, before a component has been assigned."""

    constraint_id: str
    constraint_class: str
    relation: str
    rhs_lower: float | None
    rhs_upper: float | None
    is_hard: bool
    period_scope: str
    geography_scope: str
    industry_scope: str
    ownership_scope: str
    source_snapshot_ids: str
    provenance_text: str
    vintage_compatibility_status: str
    coefficients: tuple[tuple[str, float], ...]


def vintage_status(vintages: Iterable[str]) -> str:
    """`compatible` when every participating cell shares one NAICS vintage, else `incompatible`."""
    return "compatible" if len(set(vintages)) <= 1 else "incompatible"


def _check_relation(
    relation: str,
    rhs_lower: float | None,
    rhs_upper: float | None,
    coefficients: tuple[tuple[str, float], ...],
) -> None:
    """Halt unless the right-hand side has the shape the relation implies."""
    if relation == "eq" and (rhs_lower is None or rhs_lower != rhs_upper):
        raise ValueError(f"relation 'eq' needs rhs_lower == rhs_upper, got {rhs_lower}/{rhs_upper}")
    if relation == "ge" and (rhs_lower is None or rhs_upper is not None):
        raise ValueError(f"relation 'ge' needs rhs_lower only, got {rhs_lower}/{rhs_upper}")
    if relation == "le" and (rhs_upper is None or rhs_lower is not None):
        raise ValueError(f"relation 'le' needs rhs_upper only, got {rhs_lower}/{rhs_upper}")
    if relation == "range" and (rhs_lower is None or rhs_upper is None):
        raise ValueError(f"relation 'range' needs both ends, got {rhs_lower}/{rhs_upper}")
    if relation == "integrality":
        if rhs_lower is not None or rhs_upper is not None:
            raise ValueError("relation 'integrality' carries no right-hand side")
        if len(coefficients) != 1:
            raise ValueError("relation 'integrality' applies to exactly one cell")


def constraint(
    *,
    constraint_id: str,
    constraint_class: str,
    relation: str,
    coefficients: tuple[tuple[str, float], ...],
    rhs_lower: float | None,
    rhs_upper: float | None,
    is_hard: bool,
    evidence_kind: str,
    period_scope: str,
    geography_scope: str,
    industry_scope: str,
    ownership_scope: str,
    source_snapshot_ids: str,
    provenance_text: str,
    vintage_compatibility_status: str,
) -> ConstraintDraft:
    """Build one labelled restriction, or refuse.

    Four refusals, each naming what it protects:

    1. §7.8 -- only `public_accounting_fact` and `definitional_support` may be hard.
    2. §9.3 -- a restriction warranted by an assumed disclosure threshold may never be hard,
       whatever class the caller asks for.
    3. INV-007 -- a hard restriction may not span cells the caller has found vintage-incompatible.
       The status comes from `vintage_status`, which reads `naics_vintage` only; see the module
       docstring for what that leaves to `cells._assert_one_vintage_per_cell` and what neither
       check covers.
    4. Shape -- the right-hand side must match the relation.
    """
    if constraint_class not in CONSTRAINT_CLASSES:
        raise ValueError(f"unknown constraint_class {constraint_class!r}")
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}")
    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(f"unknown evidence_kind {evidence_kind!r}")
    if not coefficients:
        raise ValueError(f"{constraint_id}: a constraint with no coefficients restricts nothing")
    named = [cell for cell, _ in coefficients]
    if len(set(named)) != len(named):
        raise ValueError(f"{constraint_id}: a cell appears twice in one constraint")

    if is_hard and constraint_class not in HARD_ELIGIBLE_CLASSES:
        raise HardConstraintClassError(
            f"{constraint_id}: class {constraint_class!r} may not be hard; §7.8 allows "
            f"is_hard=true only for {list(HARD_ELIGIBLE_CLASSES)}"
        )
    if is_hard and evidence_kind == "assumed_threshold":
        raise HardConstraintClassError(
            f"{constraint_id}: warranted by evidence_kind='assumed_threshold', which §9.3 forbids "
            "as a hard constraint. Record it as a sensitivity_assumption with is_hard=false"
        )
    if is_hard and vintage_compatibility_status != "compatible":
        raise IncompatibleMarginError(
            f"{constraint_id}: vintage_compatibility_status={vintage_compatibility_status!r}; "
            "INV-007 forbids stacking incompatible vintages into a hard equation"
        )
    _check_relation(relation, rhs_lower, rhs_upper, coefficients)

    return ConstraintDraft(
        constraint_id=constraint_id,
        constraint_class=constraint_class,
        relation=relation,
        rhs_lower=rhs_lower,
        rhs_upper=rhs_upper,
        is_hard=is_hard,
        period_scope=period_scope,
        geography_scope=geography_scope,
        industry_scope=industry_scope,
        ownership_scope=ownership_scope,
        source_snapshot_ids=source_snapshot_ids,
        provenance_text=f"{EVIDENCE_PREFIX}{evidence_kind}; {provenance_text}",
        vintage_compatibility_status=vintage_compatibility_status,
        coefficients=tuple(coefficients),
    )


def assert_no_national_employment_margin(
    drafts: Sequence[ConstraintDraft], kinds: Mapping[str, str]
) -> None:
    """Halt if any restriction couples state employment cells to each other or to the national row.

    Stage 0's `SRC-QCEW-006` verdict is `decline`, and the finding's consequence paragraph is
    explicit: no national employment margin may be created out of that identity. Both shapes are
    refused, because the identity can be written either way -- as a sum of states equalling the
    national row, or as a sum of states equalling a number lifted from it.
    """
    for draft in drafts:
        touched = [kinds[cell] for cell, _ in draft.coefficients]
        states = touched.count(KIND_STATE_TOTAL)
        if states > 1 or (states and KIND_NATIONAL_TOTAL in touched):
            raise IncompatibleMarginError(
                f"{draft.constraint_id} couples {states} state-total cell(s) "
                f"{'to the national row ' if KIND_NATIONAL_TOTAL in touched else ''}"
                "-- SRC-QCEW-006 came back `decline`, so no national employment margin may be "
                "created out of that identity"
            )


def to_frames(drafts: Sequence[ConstraintDraft]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Project drafts onto the §7.8 and §7.9 tables, sorted, with `component_id` still null."""
    row_records = [
        {
            "constraint_id": d.constraint_id,
            "component_id": None,
            "constraint_class": d.constraint_class,
            "relation": d.relation,
            "rhs_lower": d.rhs_lower,
            "rhs_upper": d.rhs_upper,
            "is_hard": d.is_hard,
            "period_scope": d.period_scope,
            "geography_scope": d.geography_scope,
            "industry_scope": d.industry_scope,
            "ownership_scope": d.ownership_scope,
            "source_snapshot_ids": d.source_snapshot_ids,
            "provenance_text": d.provenance_text,
            "vintage_compatibility_status": d.vintage_compatibility_status,
        }
        for d in drafts
    ]
    coefficient_records = [
        {"constraint_id": d.constraint_id, "cell_id": cell, "coefficient": value}
        for d in drafts
        for cell, value in d.coefficients
    ]
    row_frame = pl.DataFrame(row_records, schema=CONSTRAINT_ROW_SCHEMA).sort("constraint_id")
    coefficient_frame = pl.DataFrame(
        coefficient_records, schema=CONSTRAINT_COEFFICIENT_SCHEMA
    ).sort(["constraint_id", "cell_id"])
    return row_frame, coefficient_frame


def _scope(cell: dict[str, object]) -> dict[str, str]:
    """The four §7.8 scope fields for a restriction that touches exactly one cell."""
    return {
        "period_scope": str(cell["reference_month"]),
        "geography_scope": str(cell["state_fips"]),
        "industry_scope": str(cell["industry_code"]),
        "ownership_scope": str(cell["ownership_code"]),
    }


def observed_value_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """Pin every observed and true-zero cell to its published value (INV-001, §9.3 first bullet).

    True zeros are pinned alongside observed values because Stage 1 established them with a
    source-specific rule (INV-003): a cell with no establishments has no employment. A cell whose
    zero was never established that way carries `observation_status = 'suppressed'` and is left
    free here.
    """
    published = cells_frame.filter(pl.col("observation_status").is_in(["observed", "true_zero"]))
    return [
        constraint(
            constraint_id=f"fix|{cell['cell_id']}",
            constraint_class="public_accounting_fact",
            relation="eq",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=float(cell["observed_value"]),
            rhs_upper=float(cell["observed_value"]),
            is_hard=True,
            evidence_kind="published_value",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text=(
                f"published QCEW value {cell['observed_value']} for {cell['cell_id']}, "
                f"disclosure code {cell['qcew_disclosure_code']!r}"
            ),
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in published.iter_rows(named=True)
    ]


def nonnegativity_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """`x >= 0` for every unknown cell (§9.1, §9.3 nonnegativity bullet).

    Emitted per cell rather than declared once for the system: §7.9's coefficient table is the
    single source of truth for what the solver sees, and a restriction that lives only in a
    docstring carries no INV-004 label.
    """
    return [
        constraint(
            constraint_id=f"nonneg|{cell['cell_id']}",
            constraint_class="definitional_support",
            relation="ge",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=0.0,
            rhs_upper=None,
            is_hard=True,
            evidence_kind="unit_definition",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text="employment is a count of jobs and cannot be negative",
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in cells_frame.filter(pl.col("observation_status") == "suppressed").iter_rows(
            named=True
        )
    ]


def integrality_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """Integrality for every unknown cell (§9.3 integrality bullet, §9.6 step 2)."""
    return [
        constraint(
            constraint_id=f"integer|{cell['cell_id']}",
            constraint_class="definitional_support",
            relation="integrality",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=None,
            rhs_upper=None,
            is_hard=True,
            evidence_kind="unit_definition",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text="QCEW employment is an integer count of jobs",
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in cells_frame.filter(pl.col("observation_status") == "suppressed").iter_rows(
            named=True
        )
    ]


def size_margin_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """One equality per March: the published size classes sum to the published all-sizes total.

    Written as `sum(classes) - total = 0` rather than `sum(classes) = <number>`, so the national
    all-sizes cell is a cell of the system and INV-001 pins it through its own fixing row. A number
    lifted into a right-hand side would leave that value unpinned and unauditable.

    This is the *only* margin this stage builds. There is no state-sum equivalent:
    `SRC-QCEW-006` came back `decline`.
    """
    drafts: list[ConstraintDraft] = []
    size_cells = cells_frame.filter(pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_SIZE}|"))
    total_cells = {
        cell["reference_month"]: cell
        for cell in cells_frame.filter(
            pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_TOTAL}|")
        ).iter_rows(named=True)
    }
    for month, group in size_cells.group_by("reference_month", maintain_order=True):
        reference_month = str(month[0])
        total = total_cells[reference_month]
        members = group.sort("size_class")
        coefficients = tuple(
            (str(cell["cell_id"]), 1.0) for cell in members.iter_rows(named=True)
        ) + ((str(total["cell_id"]), -1.0),)
        snapshots = sorted(
            {*members["source_snapshot_id"].to_list(), str(total["source_snapshot_id"])}
        )
        drafts.append(
            constraint(
                constraint_id=f"size_margin|{reference_month}",
                constraint_class="public_accounting_fact",
                relation="eq",
                coefficients=coefficients,
                rhs_lower=0.0,
                rhs_upper=0.0,
                is_hard=True,
                evidence_kind="published_value",
                period_scope=reference_month,
                geography_scope=NATIONAL_STATE_FIPS,
                industry_scope=str(total["industry_code"]),
                ownership_scope=str(total["ownership_code"]),
                source_snapshot_ids=",".join(snapshots),
                provenance_text=(
                    f"published national size classes {members['size_class'].to_list()} sum to the "
                    f"published all-sizes national total for {reference_month}"
                ),
                vintage_compatibility_status=vintage_status(
                    [*members["naics_vintage"].to_list(), str(total["naics_vintage"])]
                ),
            )
        )
    return drafts


def size_support_rows(cells_frame: pl.DataFrame, size_rows: pl.DataFrame) -> list[ConstraintDraft]:
    """The §9.3 "documented size support" for every suppressed class.

    A class of `n` establishments each holding between `lower` and `upper` employees holds between
    `n * lower` and `n * upper` in total. `compat.assert_size_support_holds` measures that rule
    against every observed row before this builder runs, so the support is documented rather than
    assumed.

    INV-011 is enforced here rather than trusted from the data: this builder refuses a non-March
    row outright, so a later stage that reuses it cannot produce a March class bound for June.
    An open-ended top class emits its lower bound only -- §9.3 forbids arbitrary top-class caps,
    and a number invented to close the band would be one.
    """
    industries = size_rows["industry_code"].unique().to_list()
    if len(industries) > 1:
        raise ConceptViolationError(
            f"the size frame carries {len(industries)} industries "
            f"({sorted(map(str, industries))[:3]}...); this builder matches a size row to a cell on "
            "(reference_month, size_class) and never on industry, so a second industry would "
            "bound this industry's cell by its own establishment count. Filter to "
            "`project.industry_code_used` before calling"
        )

    # Null-closed, as in `compat.assert_size_support_holds`: `~ends_with` is null on a null
    # month and a null predicate is dropped, so the row would slip an INV-011 gate.
    off_march = size_rows.filter(
        pl.col("reference_month").is_null() | ~pl.col("reference_month").str.ends_with("-03")
    )
    if off_march.height:
        raise ConceptViolationError(
            f"{off_march.height} size row(s) are not March-referenced, e.g. "
            f"{off_march['reference_month'][0]}; a March-reference class support may not be built "
            "outside its valid reference period (INV-011)"
        )
    by_cell = {
        cell["cell_id"]: cell
        for cell in cells_frame.filter(
            pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_SIZE}|")
            & (pl.col("observation_status") == "suppressed")
        ).iter_rows(named=True)
    }
    drafts: list[ConstraintDraft] = []
    for row in size_rows.filter(pl.col("observation_status") == "suppressed").iter_rows(named=True):
        identifier = None
        for cell_id, cell in by_cell.items():
            if (
                cell["reference_month"] == row["reference_month"]
                and cell["size_class"] == row["size_class"]
            ):
                identifier = cell_id
                break
        if identifier is None:
            continue
        lower = float(row["establishments"] * row["size_lower"])
        upper = (
            None if row["size_upper"] is None else float(row["establishments"] * row["size_upper"])
        )
        drafts.append(
            constraint(
                constraint_id=f"size_support|{identifier}",
                constraint_class="definitional_support",
                relation="range" if upper is not None else "ge",
                coefficients=((identifier, 1.0),),
                rhs_lower=lower,
                rhs_upper=upper,
                is_hard=True,
                evidence_kind="class_definition",
                source_snapshot_ids=str(row["snapshot_id"]),
                provenance_text=(
                    f"{row['establishments']} published establishment(s) in class "
                    f"{row['size_class']} ([{row['size_lower']}, {row['size_upper']}] employees "
                    "per establishment, March reference)"
                ),
                vintage_compatibility_status="compatible",
                **_scope(by_cell[identifier]),
            )
        )
    return drafts


def rounding_interval_row(
    constraint_id: str,
    cell_id: str,
    *,
    published_value: float,
    grid_width: float,
    endpoint_rule: str,
    period_scope: str,
    geography_scope: str,
    industry_scope: str,
    ownership_scope: str,
    source_snapshot_ids: str,
) -> ConstraintDraft:
    """§9.4: a value rounded to grid width `r` enters as `[y - r/2, y + r/2]`, never as an equality.

    §9.4 writes the upper endpoint as strictly open. A linear program has no strict inequality, so
    the interval is encoded closed and `endpoint_rule` records what the source documents. That is a
    conservative widening -- it can only make a bound looser, never falsely exact, which is the
    direction INV-006 cares about.

    No QCEW field this stage reads is rounded, so nothing in the D1 run calls this. It exists
    because §9.4 requires rounding rules to be field-specific and encodable, and the §17.2 property
    "rounding intervals avoid false exact recovery" exercises it.
    """
    return constraint(
        constraint_id=constraint_id,
        constraint_class="definitional_support",
        relation="range",
        coefficients=((cell_id, 1.0),),
        rhs_lower=published_value - grid_width / 2,
        rhs_upper=published_value + grid_width / 2,
        is_hard=True,
        evidence_kind="rounding_documentation",
        period_scope=period_scope,
        geography_scope=geography_scope,
        industry_scope=industry_scope,
        ownership_scope=ownership_scope,
        source_snapshot_ids=source_snapshot_ids,
        provenance_text=(
            f"published value {published_value} rounded to grid width {grid_width}; "
            f"endpoint behaviour: {endpoint_rule}"
        ),
        vintage_compatibility_status="compatible",
    )
