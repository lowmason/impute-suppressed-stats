"""§12.5 size matrix reconciliation: row sums to reconciled state totals, columns to class margins.

NO REAL INPUT UNTIL STAGE 6. Stage 2's `target_cell` carries state totals, national size classes,
and national totals -- and no state-by-size cell at all. This module is therefore exercised only
by synthetic fixtures in Stage 3, and becomes live when Stage 6 builds the state x month x size
grid. That is a statement about the data, not a gap in the implementation.

§12.5's rules, in order: without bounds use RAS/IPF or an equivalent entropy projection; with
bounds or overlapping margins use the general convex projection; and "If margins are inconsistent,
fail and diagnose rather than forcing convergence." That third rule needs TWO checks, not one.

The first is the obvious one: row totals and column totals must sum to the same number, tested
before any iteration, because an IPF loop over inconsistent margins does not diverge loudly -- it
oscillates quietly and returns whichever half-step the iteration cap happened to stop on.

The second is the one it is easy to omit. Margins that sum equally can still be unreachable from a
given seed, because the seed's zero pattern fixes which cells can carry weight. A seed of
[[0, 3], [2, 0]] against rows [10, 20] and columns [25, 5] passes the sum check -- both are 30 --
and a feasible point exists at [[7.5, 2.5], [17.5, 2.5]], yet the floored zeros cannot grow against
the column constraints and the iteration settles at row sums [5, 25]. Returning that is exactly the
"forcing convergence" the rule forbids, so the achieved margins are verified before returning.
"""

from __future__ import annotations

import numpy as np

from ..errors import IncompatibleMarginError
from .projection import kl_project


def reconcile_matrix(
    seed: np.ndarray,
    row_totals: np.ndarray,
    column_totals: np.ndarray | None,
    *,
    tolerance: float,
    max_iterations: int,
    floor: float,
) -> np.ndarray:
    """Scale `seed` so its rows sum to `row_totals` and, when given, columns to `column_totals`."""
    seed = np.asarray(seed, dtype=float)
    n_rows, n_cols = seed.shape

    if column_totals is not None:
        row_sum = float(np.sum(row_totals))
        col_sum = float(np.sum(column_totals))
        if not np.isclose(row_sum, col_sum, rtol=0.0, atol=max(tolerance, 1e-6)):
            raise IncompatibleMarginError(
                f"row totals sum to {row_sum} but column totals sum to {col_sum}; §12.5 requires "
                "failing and diagnosing rather than forcing convergence"
            )

    # One margin row per constraint, over the flattened matrix.
    margins: list[np.ndarray] = []
    targets: list[float] = []
    for r in range(n_rows):
        row = np.zeros(n_rows * n_cols)
        row[r * n_cols : (r + 1) * n_cols] = 1.0
        margins.append(row)
        targets.append(float(row_totals[r]))
    if column_totals is not None:
        for c in range(n_cols):
            col = np.zeros(n_rows * n_cols)
            col[c::n_cols] = 1.0
            margins.append(col)
            targets.append(float(column_totals[c]))

    margin_matrix = np.vstack(margins)
    target_vector = np.array(targets)
    flat, violation = kl_project(
        seed.reshape(-1),
        margin_matrix,
        target_vector,
        lower=np.zeros(n_rows * n_cols),
        upper=np.full(n_rows * n_cols, np.inf),
        floor=floor,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )

    achieved = margin_matrix @ flat
    if not np.allclose(achieved, target_vector, rtol=1e-6, atol=max(tolerance, 1e-9)):
        raise IncompatibleMarginError(
            f"reconciliation did not converge to the requested margins: total absolute violation "
            f"{violation} after {max_iterations} "
            f"iterations; requested {target_vector.tolist()} but achieved {achieved.tolist()}. "
            "The margins may be unreachable from this seed's zero pattern; §12.5 requires failing "
            "and diagnosing rather than forcing convergence"
        )
    return flat.reshape(n_rows, n_cols)
