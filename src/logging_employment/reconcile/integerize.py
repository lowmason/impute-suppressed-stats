"""§12.6 balanced integerization.

"Integerization MUST NOT be applied independently cell by cell." That sentence is the module's
reason to exist: three cells at 3.4 rounded independently give 9, and the margin they were
reconciled to is gone. The units are allocated against the margin instead -- floor everything,
count what is left, and hand the remainder out by largest fractional part.

THE TIE-BREAK MUST BE DETERMINISTIC. §16.1 requires every command to be idempotent for the same
inputs. Ties are common here because reconciled allocations of equal-weight cells are exactly
equal, so a tie-break by dict order, hash order, or anything unordered would make two runs of the
same data disagree on which cell got the extra job. Ties break by `cell_id` ascending. That
hardcoded ordering IS `ReconciliationConfig.integerization_tiebreak = 'largest_remainder'`; the
function takes no config argument, because the field's `Literal` admits exactly one value and a
parameter would imply a choice that does not exist.

BOUNDS ARE READ PER CELL THAT HAS A VALUE. Iterating the `upper` dict instead let a cap for a cell
with no value create an entry, which lowered `base` and corrupted the real cells' allocation; and
a `lower` above an `upper` was silently resolved in the cap's favour, returning a value below the
bound the caller declared. Both are refused or ignored now rather than absorbed. The remainder
that orders the round-robin is measured from the floor actually used, because a floor raised by
`lower` has already consumed the cell's fractional claim.

THE PLACEMENT BUDGET IS COMPUTED ONCE. It bounds how many index steps the round-robin may take,
and it must be fixed before the loop starts. Evaluating `len(order) * (remaining + 1)` inside the
loop condition recomputes it against a `remaining` that falls with every placement, so the ceiling
descends toward the climbing index and the loop can exit with units still in hand -- reporting an
infeasible margin on inputs that are perfectly feasible, which defeats the only reason `upper`
exists.
"""

from __future__ import annotations

import math


def integerize(
    values: dict[str, float],
    total: int,
    *,
    lower: dict[str, int] | None = None,
    upper: dict[str, int | None] | None = None,
) -> dict[str, int]:
    """Round `values` to integers summing exactly to `total`, respecting integer bounds."""
    if not values:
        return {}
    lower = lower or {}
    upper = upper or {}

    # Bounds are read per CELL THAT HAS A VALUE, never by iterating `upper`. Iterating the bound
    # dict let a cap for an absent cell create an entry -- with a negative cap, `floors.get(cell,
    # 0) > cap` is true for a cell that was never passed in -- and that phantom entry lowered
    # `base`, so the real cells came back wrong too. A bounds dict covering a superset of the
    # cells being integerized is a legitimate call shape; the extra keys are simply not this
    # call's business.
    for cell in values:
        floor_bound = lower.get(cell, 0)
        cap = upper.get(cell)
        if cap is not None and floor_bound > cap:
            raise ValueError(
                f"cell {cell!r} has lower bound {floor_bound} above its upper bound {cap}; "
                "§12.6 cannot round into a contradictory pair, and clamping to the cap would "
                "silently return a value below the lower bound the caller declared"
            )

    floors = {}
    for cell, value in values.items():
        seat = max(math.floor(value), lower.get(cell, 0))
        cap = upper.get(cell)
        floors[cell] = int(cap) if cap is not None and seat > cap else seat

    base = sum(floors.values())
    if base > total:
        raise ValueError(
            f"summed integer lower bounds {base} exceed the required total {total}; "
            "§12.6 cannot round into an infeasible margin"
        )

    remaining = total - base
    # The remainder is measured from the floor ACTUALLY USED, not from `math.floor(value)`. Once
    # a floor has been raised by `lower` or lowered by `upper`, the raw fractional part is no
    # longer the cell's claim on the spare units: a cell whose floor was raised past its own
    # value has a negative remainder and correctly sorts last. Ties break by cell_id ascending,
    # so the whole order is total and the same input yields the same output on every platform.
    order = sorted(
        values,
        key=lambda cell: (-(values[cell] - floors[cell]), cell),
    )

    out = dict(floors)
    index = 0
    # Fixed before the loop, from the INITIAL remainder. One full pass of `len(order)` indices
    # places at least one unit unless no cell has headroom left, so `remaining` passes suffice.
    limit = len(order) * (remaining + 1)
    while remaining > 0 and index < limit:
        cell = order[index % len(order)]
        cap = upper.get(cell)
        if cap is None or out[cell] < cap:
            out[cell] += 1
            remaining -= 1
        index += 1
    if remaining > 0:
        raise ValueError(
            f"{remaining} unit(s) could not be placed without breaching an integer upper bound"
        )
    return out
