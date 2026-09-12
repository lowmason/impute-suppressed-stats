"""§12.3 bounded proportional scaling, solved by bisection.

E_{s,t} = clip(lambda * q_{s,t}, L_{s,t}, U_{s,t}), for the lambda making sum_{M_t} E = R_t.

WHY BISECTION AND NOT A ROOT FINDER. §12.3 names it: "Because the summed clipped allocation is
monotone in lambda, use robust bisection." Monotonicity is the whole reason the method is safe --
the clipped sum is a non-decreasing piecewise-linear function of lambda with flat segments where
every cell is clipped, and Newton or a secant method stalls on exactly those flats.
`test_the_clipped_sum_is_monotone_in_lambda` pins the property the choice rests on.

WHY NULL UPPERS ARE INFINITE. On the D1 window `selected_upper` is null on 1,227 of 1,241 unknown
cells, because `SRC-QCEW-006` came back `decline` and no other public fact has been made a
constraint row. (One exists: a disclosed private `113` parent bounds 756 of the 1,227 above, measured
2026-09-11 and routed to `specs/stage5-parent-margin.md`; until it lands every such upper is null.)
`None` maps to `math.inf`, which makes the clip's upper arm a no-op and the
`sum U < R_t` half of §12.3's predicate vacuous. Coercing null to a large finite number instead
would invent the "arbitrary top-class cap" §9.3 forbids by name, and would silently change results
whenever the chosen number happened to bind.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import InfeasibleResidualError
from .allocate import Weights, check_domain
from .anchor import Anchor


@dataclass(frozen=True)
class Bounds:
    """Per-cell deterministic bounds. A `None` upper means unbounded above, not a missing value."""

    lower: dict[str, float]
    upper: dict[str, float | None]

    def upper_of(self, cell: str) -> float:
        """The upper bound as a float, with `None` read as positive infinity."""
        value = self.upper.get(cell)
        return math.inf if value is None else float(value)


def clipped_sum(lam: float, weights: Weights, bounds: Bounds, cells: Sequence[str]) -> float:
    """sum_s clip(lam * q_s, L_s, U_s) -- non-decreasing in `lam`."""
    return sum(
        min(max(lam * weights.values[cell], bounds.lower[cell]), bounds.upper_of(cell))
        for cell in cells
    )


def scale_into_bounds(
    anchor: Anchor,
    weights: Weights,
    bounds: Bounds,
    *,
    tolerance: float,
    max_iterations: int,
) -> dict[str, float]:
    """Solve for lambda by bisection, or fail per §12.3's strict predicate.

    The domain check precedes the empty-missing-set shortcut, matching `allocate`: checking second
    would let a populated weight vector pass silently against an empty missing set.
    """
    check_domain(weights, anchor)
    cells = anchor.missing_cells
    if not cells:
        return {}

    lower_sum = sum(bounds.lower[cell] for cell in cells)
    upper_sum = sum(bounds.upper_of(cell) for cell in cells)
    # STRICT, per §12.3 -- but compared against the originated tolerance rather than in
    # exact float arithmetic. Equality is feasible: the degenerate case where every cell sits
    # exactly on a bound MUST succeed, and `>=` would fail-close on it. Exact `>` is not enough
    # either, because the sums are accumulated in floating point: seven cells at lower 0.1 sum to
    # 0.7000000000000001, which an exact `>` reads as infeasible against a residual of 0.7 --
    # rejecting the very case the paragraph above promises will work. Both arms are widened by
    # `tolerance` so the boundary is governed by the configured value in both directions.
    if lower_sum - anchor.residual > tolerance:
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: summed lower bounds {lower_sum} exceed residual "
            f"{anchor.residual}; §12.3 forbids approximating this away"
        )
    if anchor.residual - upper_sum > tolerance:
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: summed upper bounds {upper_sum} fall below residual "
            f"{anchor.residual}; §12.3 forbids approximating this away"
        )

    if math.isclose(lower_sum, anchor.residual, rel_tol=0.0, abs_tol=tolerance):
        return {cell: bounds.lower[cell] for cell in cells}

    lo, hi = 0.0, 1.0
    # Grow the bracket rather than guessing one: the weights carry no scale guarantee, so a fixed
    # upper bracket would silently fail on a small-weight month. `clipped_sum(0) == lower_sum`,
    # which the check above has already put at or below the residual, so `lo` starts valid.
    for _ in range(max_iterations):
        if clipped_sum(hi, weights, bounds, cells) >= anchor.residual:
            break
        lo, hi = hi, hi * 2.0
    else:  # pragma: no cover - the upper_sum check above makes this unreachable in practice
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: no bracket reaches residual {anchor.residual}"
        )

    for _ in range(max_iterations):
        mid = 0.5 * (lo + hi)
        total = clipped_sum(mid, weights, bounds, cells)
        if abs(total - anchor.residual) <= tolerance:
            break
        if total < anchor.residual:
            lo = mid
        else:
            hi = mid
    lam = 0.5 * (lo + hi)
    return {
        cell: min(max(lam * weights.values[cell], bounds.lower[cell]), bounds.upper_of(cell))
        for cell in cells
    }
