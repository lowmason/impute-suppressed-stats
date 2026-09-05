"""§12.2's required no-bound fast path, and the domain refusal that guards it.

§10 (spec:942) requires every baseline to use "the same source universe, training windows,
pseudo-suppression masks, hard bounds, and reconciliation layer as the full model". This module is
that layer's single entry point: an estimator supplies weights and calls `allocate`, and never
computes an estimate itself. That is what makes "the same reconciliation layer" concrete rather
than aspirational.

WHY THE DOMAIN REFUSAL IS HERE AND NOT IN A BASELINE. A weight vector defined on a strict subset
of the missing set, normalized to the residual, silently reallocates the absent cells' share onto
the cells that happen to have inputs. Nothing about the output looks wrong -- it sums to R_t and
every value is positive -- which is exactly why it must be refused mechanically rather than caught
by review. Declared composition (own weight where defined, establishment weight elsewhere, basis
recorded per cell) is permitted; silent subsetting is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..errors import InfeasibleResidualError, WeightDomainError
from .anchor import Anchor


@dataclass(frozen=True)
class Weights:
    """Positive raw weights per cell, with the provenance of each.

    `basis` is not decoration. Every §10.3 and §10.4 estimator runs as a composite on the D1
    window -- a large minority of cells take the establishment fallback rather than the
    estimator's own signal -- so without a per-cell basis a reader, and Stage 4's scoreboard,
    would report a composite's score as a pure estimator's. The split itself is a measurement
    that a revision moves, so it is written to the run manifest rather than pinned here.
    """

    values: dict[str, float]
    basis: dict[str, str]


def check_domain(weights: Weights, anchor: Anchor) -> None:
    """Refuse any weight vector that is not exactly the missing set, positive, and finite."""
    wanted = set(anchor.missing_cells)
    got = set(weights.values)
    if wanted != got:
        raise WeightDomainError(
            f"{anchor.reference_month}: weight domain does not match the missing set; "
            f"absent={sorted(wanted - got)} unexpected={sorted(got - wanted)}"
        )
    if set(weights.basis) != got:
        raise WeightDomainError(
            f"{anchor.reference_month}: every weight needs a recorded basis; "
            f"missing basis for {sorted(got - set(weights.basis))}"
        )
    bad = sorted(
        cell for cell, value in weights.values.items() if not math.isfinite(value) or value <= 0.0
    )
    if bad:
        raise WeightDomainError(
            f"{anchor.reference_month}: §12.2 requires positive raw weights; "
            f"non-positive or non-finite at {bad}"
        )


def allocate(anchor: Anchor, weights: Weights) -> dict[str, float]:
    """§12.2: E_{s,t} = R_t * q_{s,t} / sum_{j in M_t} q_{j,t}.

    The required no-bound fast path, kept as its own code path rather than folded into §12.3's
    bounded scaling. On the D1 window every state cell is unbounded above, so this path carries
    the whole production load and deserves to be readable on its own.

    The domain check runs BEFORE the empty-missing-set shortcut, not after. Checking second would
    let a caller pass a populated weight vector against an empty missing set and receive `{}`
    rather than a refusal -- the same silent-mismatch failure `check_domain` exists to prevent,
    only inverted. An empty vector against an empty missing set passes the check and reaches the
    shortcut, which is the case that legitimately allocates nothing.
    """
    check_domain(weights, anchor)
    if anchor.residual < 0.0:
        # `scale_into_bounds` fails closed on this input; the unbounded path must agree, or the
        # shared entry point every estimator passes through is the one that quietly returns
        # negative employment. Stage 4's masks recompute R_t' and can drive it below zero.
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: residual {anchor.residual} is negative, so every "
            "allocation would be negative employment; §12.3's predicate refuses this"
        )
    if not anchor.missing_cells:
        return {}
    total = sum(weights.values.values())
    if total <= 0.0:  # unreachable after check_domain; kept so the division is provably safe
        raise WeightDomainError(f"{anchor.reference_month}: weights sum to {total}")
    return {cell: anchor.residual * weights.values[cell] / total for cell in anchor.missing_cells}
