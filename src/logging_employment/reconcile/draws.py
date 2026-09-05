"""§16.2's `reconcile_draws`, and the joint-draw guarantee of §12.7.

Deviation from §16.2: the spec types the second parameter `ConstraintSystem`. The reconciler
needs an allocation anchor and per-cell bounds; a `BuiltSystem` carries a cell table, row table,
and coefficient table, and neither an anchor -- which is a Stage 3 modeling assumption that no
constraint row may encode -- nor bounds in per-cell form. `ReconciliationInputs` is that pair.
Stage 5 constructs one from `deterministic_bounds` plus the anchor and calls the same function.

§12.7: "Posterior summaries must be computed from reconciled joint draws." This function returns
draws and never summarises, and never reduces the draw axis. The negative dependence that adding
up induces is visible only in the joint object, so a mean computed here and passed on would
silently discard the thing §12.7 exists to protect.

NO `general_method` GUARD HERE. This function takes §12.3's bounded-scaling path, which
`single_margin_method` governs and whose `Literal` admits one value. `general_method` governs
§12.4 and §12.5 -- `projection.py` and `matrix.py` -- so refusing `weighted_quadratic` here would
disable draw reconciliation over a setting this path never consults, while leaving the objective
it actually names unguarded. The refusal belongs where the config is read; see
`projection.require_supported_method`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import ReconciliationConfig
from ..errors import WeightDomainError
from .allocate import Weights
from .anchor import Anchor
from .scaling import Bounds, scale_into_bounds


@dataclass(frozen=True)
class PosteriorDraws:
    """Joint draws over cells, with the chain and draw indexes §15.4's store must preserve."""

    cell_ids: tuple[str, ...]
    values: np.ndarray  # shape (n_draws, n_cells)
    chain: np.ndarray | None
    draw: np.ndarray | None


@dataclass(frozen=True)
class ReconciliationInputs:
    """The feasible set as the reconciler needs it: one anchor and per-cell bounds."""

    anchor: Anchor
    bounds: Bounds


def _draw_weights(anchor: Anchor, row: np.ndarray, floor: float) -> Weights:
    """One draw's raw weights, flooring zeros but refusing negatives.

    §12.4 authorises "a small positive floor for zero raw seeds" and nothing more. Applying that
    floor to a negative value would convert an out-of-domain draw into a legal weight and let the
    allocation absorb it without a signal, which §18.3 forbids: a draw below zero is an upstream
    modelling failure, not a rounding artifact.
    """
    values: dict[str, float] = {}
    for cell, value in zip(anchor.missing_cells, row, strict=True):
        number = float(value)
        if number < 0.0:
            raise WeightDomainError(
                f"{anchor.reference_month}: draw for cell {cell} is negative ({number}); §12.4's "
                "floor covers zero raw seeds only, and flooring a negative would hide an "
                "out-of-domain draw inside a well-formed allocation"
            )
        values[cell] = max(number, floor)
    return Weights(values=values, basis=dict.fromkeys(anchor.missing_cells, "own_estimator"))


def reconcile_draws(
    raw_draws: PosteriorDraws,
    feasible_set: ReconciliationInputs,
    config: ReconciliationConfig,
) -> PosteriorDraws:
    """Map every raw draw into the feasible set, one draw at a time, preserving the draw axis."""
    anchor = feasible_set.anchor
    if tuple(raw_draws.cell_ids) != tuple(anchor.missing_cells):
        raise ValueError(
            f"draw cells {list(raw_draws.cell_ids)} do not match the missing set "
            f"{list(anchor.missing_cells)}"
        )

    reconciled = np.empty_like(np.asarray(raw_draws.values, dtype=float))
    for index, row in enumerate(np.asarray(raw_draws.values, dtype=float)):
        allocated = scale_into_bounds(
            anchor,
            _draw_weights(anchor, row, config.zero_seed_floor),
            feasible_set.bounds,
            tolerance=config.tolerance,
            max_iterations=config.max_bisection_iterations,
        )
        reconciled[index] = [allocated[cell] for cell in anchor.missing_cells]

    return PosteriorDraws(
        cell_ids=raw_draws.cell_ids,
        values=reconciled,
        chain=raw_draws.chain,
        draw=raw_draws.draw,
    )
