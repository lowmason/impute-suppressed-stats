"""CON-001, CON-002 and CON-004: the sparse bipartite graph and its connected components.

Nodes are cells and constraint rows; an edge is a non-zero coefficient. Two cells are in the same
component when a chain of constraints connects them, which is exactly the condition under which
solving one can change the bounds of the other -- so components are the unit §9.6 batches over.

Component labels are ordered by the smallest `cell_id` each component contains. SciPy's labelling
is an implementation detail of its traversal order; a run whose component ids moved because SciPy
changed would look like a data change in every manifest that records them.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components

from .system import BuiltSystem

COMPONENT_ID_FORMAT = "c{:06d}"


def _labels(built: BuiltSystem) -> dict[str, str]:
    """One component label per cell id, ordered by the smallest cell id in each component."""
    cell_ids = built.cells["cell_id"].to_list()
    row_ids = built.rows["constraint_id"].to_list()
    cell_at = {cell: i for i, cell in enumerate(cell_ids)}
    row_at = {row: len(cell_ids) + i for i, row in enumerate(row_ids)}

    left = np.array([cell_at[c] for c in built.coefficients["cell_id"].to_list()], dtype=np.int64)
    right = np.array(
        [row_at[r] for r in built.coefficients["constraint_id"].to_list()], dtype=np.int64
    )
    size = len(cell_ids) + len(row_ids)
    adjacency = coo_matrix((np.ones(left.size), (left, right)), shape=(size, size))
    _, raw = connected_components(csr_matrix(adjacency + adjacency.T), directed=False)

    smallest: dict[int, str] = {}
    for cell, label in zip(cell_ids, raw[: len(cell_ids)].tolist(), strict=True):
        if label not in smallest or cell < smallest[label]:
            smallest[label] = cell
    ordered = sorted(smallest, key=lambda label: smallest[label])
    names = {label: COMPONENT_ID_FORMAT.format(i) for i, label in enumerate(ordered)}
    return {
        cell: names[label]
        for cell, label in zip(cell_ids, raw[: len(cell_ids)].tolist(), strict=True)
    }


def assign_components(built: BuiltSystem) -> BuiltSystem:
    """Return the same system with `component_id` filled on every constraint row.

    The label lands on rows only. §7.7's field list has no `component_id`, and a `target_cell`
    frame carrying an extra column would fail `validate_frame` -- so cell membership is *derived*
    by `component_membership` rather than stored, which also keeps one authority for it.
    """
    by_cell = _labels(built)
    row_component = (
        built.coefficients.with_columns(
            pl.col("cell_id").replace_strict(by_cell).alias("component_id")
        )
        .group_by("constraint_id")
        .agg(pl.col("component_id").first())
    )
    rows = (
        built.rows.drop("component_id")
        .join(row_component, on="constraint_id", how="left")
        .select(built.rows.columns)
        .sort("constraint_id")
    )
    return replace(built, rows=rows)


def component_membership(built: BuiltSystem) -> pl.DataFrame:
    """`cell_id` to `component_id`, derived through the rows that touch each cell.

    Every cell carries at least one row -- an observed cell its fixing, a suppressed cell its
    nonnegativity -- so this covers the whole index rather than the coupled part of it.
    """
    return (
        built.coefficients.join(
            built.rows.select(["constraint_id", "component_id"]), on="constraint_id", how="left"
        )
        .select(["cell_id", "component_id"])
        .unique()
        .sort("cell_id")
    )


def component_provenance(built: BuiltSystem) -> pl.DataFrame:
    """CON-004: what explains each component, in one row per component."""
    per_cell = (
        component_membership(built).group_by("component_id").agg(pl.len().alias("cell_count"))
    )
    per_row = built.rows.group_by("component_id").agg(
        pl.len().alias("constraint_count"),
        pl.col("is_hard").sum().alias("hard_constraint_count"),
        pl.col("constraint_id").sort().str.join(",").alias("constraint_ids"),
        # Split before de-duplicating. Each row's `source_snapshot_ids` is itself a comma-joined
        # list, so a margin row's "a,b" is a third distinct value beside the fixing rows' "a" and
        # "b"; de-duplicating the raw column would report a,a,b,b for two snapshots. CON-004
        # provenance is read by an auditor, so this is the set of ids behind the component.
        pl.col("source_snapshot_ids")
        .str.split(",")
        .list.explode(keep_nulls=False, empty_as_null=False)
        .unique()
        .sort()
        .str.join(",")
        .alias("source_snapshot_ids"),
    )
    return per_cell.join(per_row, on="component_id", how="left").sort("component_id")
