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
from ..errors import HardConstraintClassError, IncompatibleMarginError
from .cells import KIND_NATIONAL_TOTAL, KIND_STATE_TOTAL


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
