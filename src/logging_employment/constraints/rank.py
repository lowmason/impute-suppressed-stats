"""CON-003 and CON-005: rank, nullity, and one computation per distinct component shape.

Rank is computed over the component's *equality* rows. Inequalities -- nonnegativity, class
supports, rounding intervals -- narrow a feasible set without removing a degree of freedom, so
counting them would report a cell as identified when it is only bounded. Nullity is therefore the
number of free directions the equalities leave, which is what CON-003 records and what a reader
uses to explain why a cell is or is not pinned.

Both ranks are computed because they answer different questions. Structural rank is a property of
the sparsity pattern -- the largest matching between rows and columns -- and cannot be fooled by
cancellation; numerical rank is a property of the values, and is the one that changes when two
margins say the same thing. A component where they disagree is a component where the pattern
promises identification the numbers do not deliver.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import structural_rank

from .graph import component_membership
from .index import SystemIndex
from .system import BuiltSystem


@dataclass(frozen=True)
class RankRecord:
    """CON-003's record for one component."""

    component_id: str
    cell_count: int
    equality_row_count: int
    structural_rank: int
    numerical_rank: int
    nullity: int
    cache_hit: bool


def structural_rank_of(matrix: np.ndarray) -> int:
    """The largest row-column matching in the matrix's sparsity pattern."""
    if matrix.size == 0 or matrix.shape[0] == 0:
        return 0
    return int(structural_rank(csr_matrix(matrix)))


def numerical_rank_of(matrix: np.ndarray, *, tolerance: float) -> int:
    """The number of linearly independent rows at the configured tolerance."""
    if matrix.size == 0 or matrix.shape[0] == 0:
        return 0
    return int(np.linalg.matrix_rank(matrix, tol=tolerance))


def equality_matrix(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    *,
    index: SystemIndex | None = None,
) -> tuple[np.ndarray, list[str]]:
    """The dense equality matrix for one component, with its column order.

    Dense because a component here is at most a few dozen cells; the whole system is sparse, but no
    single component is large enough for a sparse rank routine to pay for itself.

    Soft equalities are excluded. Rank here answers "how many degrees of freedom does the feasible
    set leave", and INV-005 says a soft restriction is not part of that set.
    """
    if index is None:
        cells = sorted(
            membership.filter(pl.col("component_id") == component_id)["cell_id"].to_list()
        )
        equality_ids = built.rows.filter(
            (pl.col("component_id") == component_id)
            & (pl.col("relation") == "eq")
            & pl.col("is_hard")  # INV-005: rank describes the feasible set, so only hard rows count
        )["constraint_id"].to_list()
    else:
        cells = index.cells_by_component[component_id]
        equality_ids = [
            row["constraint_id"]
            for row in index.hard_rows_by_component.get(component_id, [])
            if row["relation"] == "eq"  # INV-005 already applied: the index holds hard rows only
        ]
    equality_ids = sorted(equality_ids)
    matrix = np.zeros((len(equality_ids), len(cells)))
    at_row = {name: i for i, name in enumerate(equality_ids)}
    at_column = {name: i for i, name in enumerate(cells)}
    # Written positionally by key, so the order coefficients arrive in cannot reach the matrix --
    # which is what lets the indexed and filtered paths differ in iteration order and still agree.
    for constraint_id in equality_ids:
        if index is None:
            entries = built.coefficients.filter(pl.col("constraint_id") == constraint_id)
            pairs = zip(entries["cell_id"], entries["coefficient"], strict=True)
        else:
            pairs = zip(*index.coefficients_by_constraint[constraint_id], strict=True)
        for cell, coefficient in pairs:
            matrix[at_row[constraint_id], at_column[cell]] = coefficient
    return matrix, cells


def _shape_key(matrix: np.ndarray) -> str:
    """CON-005's cache key: the matrix itself, positionally, with no cell identity in it.

    Two Marches whose class structure and suppression pattern are unchanged produce the same key,
    which is exactly the "definitions are unchanged" condition CON-005 names.
    """
    payload = f"{matrix.shape}|{np.array2string(matrix, precision=12, threshold=matrix.size + 1)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def component_rank(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    *,
    rank_tolerance: float,
    cache: dict[str, tuple[int, int]],
    index: SystemIndex | None = None,
) -> RankRecord:
    """Rank and nullity for one component, reusing a cached shape when one matches."""
    matrix, cells = equality_matrix(built, component_id, membership, index=index)
    key = _shape_key(matrix)
    hit = key in cache
    if not hit:
        cache[key] = (
            structural_rank_of(matrix),
            numerical_rank_of(matrix, tolerance=rank_tolerance),
        )
    structural, numerical = cache[key]
    return RankRecord(
        component_id=component_id,
        cell_count=len(cells),
        equality_row_count=matrix.shape[0],
        structural_rank=structural,
        numerical_rank=numerical,
        nullity=len(cells) - numerical,
        cache_hit=hit,
    )


def rank_table(
    built: BuiltSystem,
    *,
    rank_tolerance: float,
    membership: pl.DataFrame | None = None,
    index: SystemIndex | None = None,
) -> pl.DataFrame:
    """One `RankRecord` per component, in component order.

    `membership` and `index` are accepted so `solve_bounds` can hand over what it has already
    derived; deriving membership here as well produced two frames with identical content and paid
    for the join twice. Component order is unchanged and must stay so: CON-005's cache is filled
    in this order, and which component records `cache_hit=False` is a function of it.
    """
    if membership is None:
        membership = component_membership(built)
    cache: dict[str, tuple[int, int]] = {}
    records = [
        component_rank(
            built,
            component_id,
            membership,
            rank_tolerance=rank_tolerance,
            cache=cache,
            index=index,
        )
        for component_id in sorted(set(membership["component_id"].to_list()))
    ]
    return pl.DataFrame([record.__dict__ for record in records])
