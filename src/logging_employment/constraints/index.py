"""One pass over the frames, so the solve path never scans them again.

`solve_bounds` visits every component and, inside each, every row. Written as frame filters --
`built.rows.filter(component_id == ...)` once per component, `built.coefficients.filter(
constraint_id == ...)` once per row -- each lookup is a full scan of a system-sized frame. On the
D1 window that came to tens of thousands of scans for a system whose components average one cell
apiece, and they dominated the function's wall time. This module does the same grouping once.

It is a read structure, not a second authority. Every field is a regrouping of what `BuiltSystem`
already holds, in the order the frames already hold it, and each consumer keeps the filter path it
had for the callers that cannot supply an index.

ORDER IS THE CONTRACT. Two of these groupings are solver input rather than presentation:
`cells_by_component` becomes the model's column indices, and `coefficients_by_constraint` becomes
`addRow`'s index array. Both are built by appending during a single pass in frame order, not by
`group_by` -- which does not preserve key order here and guarantees nothing about order within a
group. Nothing downstream can see a permutation of either: on this window every hard coefficient
is +/-1, so reversing them leaves every bound bit-identical and the whole suite green. The
ordering discipline therefore lives here and in `tests/unit/test_constraint_index.py`, not in a
consumer's assertion.

An index is only valid for the exact `(built, membership)` pair it was built from. It is passed
explicitly for that reason and never memoised: `constraint_set_hash` deliberately excludes
`component_id` (§18.1), so `dataclasses.replace` yields a different system carrying the same hash
-- which `graph.assign_components` relies on -- and a hash-keyed cache would serve the wrong
frames with nothing to notice.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from .system import BuiltSystem


@dataclass(frozen=True)
class SystemIndex:
    """Every per-component and per-constraint lookup the solve path makes, grouped once."""

    cells_by_component: dict[str, list[str]]
    """Component to its cells, sorted -- the order `column_specs` and `equality_matrix` impose."""

    hard_rows_by_component: dict[str, list[dict[str, object]]]
    """Component to its `is_hard` rows, in frame order.

    One dict serves all three consumers, which each narrow it further in Python:
    `column_specs` takes the integrality rows and the single-cell rows, `matrix_rows` takes
    everything else, and `equality_matrix` takes `relation == "eq"`. Building three separately
    filtered dicts would discard the property `matrix_rows`' docstring rests on -- that it and
    `column_specs` partition one row set between them -- by giving each an independently written
    predicate that could drift.
    """

    coefficients_by_constraint: dict[str, tuple[list[str], list[float]]]
    """Constraint to its `(cells, values)`, in frame order and aligned to each other."""

    suppressed: frozenset[str]
    """The §7.7 suppressed cells. Invariant across a run; `solve_component` rebuilt it per call."""


def build_index(built: BuiltSystem, membership: pl.DataFrame) -> SystemIndex:
    """Group a system's frames once, for the whole solve.

    `membership` is taken as an argument rather than derived here because it is the caller's
    authority for which cells belong to which component -- `column_specs` accepts it as a
    parameter for the same reason, and a caller solving one system against another's partition is
    a case the bound tests exercise on purpose.
    """
    cells_by_component: dict[str, list[str]] = {}
    for cell, component in zip(membership["cell_id"], membership["component_id"], strict=True):
        cells_by_component.setdefault(component, []).append(cell)
    for group in cells_by_component.values():
        group.sort()

    hard_rows_by_component: dict[str, list[dict[str, object]]] = {}
    for row in built.rows.filter(pl.col("is_hard")).iter_rows(named=True):
        hard_rows_by_component.setdefault(row["component_id"], []).append(row)

    coefficients_by_constraint: dict[str, tuple[list[str], list[float]]] = {}
    for constraint, cell, coefficient in zip(
        built.coefficients["constraint_id"],
        built.coefficients["cell_id"],
        built.coefficients["coefficient"],
        strict=True,
    ):
        cells, values = coefficients_by_constraint.setdefault(constraint, ([], []))
        cells.append(cell)
        values.append(float(coefficient))

    return SystemIndex(
        cells_by_component=cells_by_component,
        hard_rows_by_component=hard_rows_by_component,
        coefficients_by_constraint=coefficients_by_constraint,
        suppressed=frozenset(
            built.cells.filter(pl.col("observation_status") == "suppressed")["cell_id"].to_list()
        ),
    )
