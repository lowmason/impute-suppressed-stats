"""§13.2 steps 5-6: rank and bound analysis on a masked component.

Always a FULL rebuild. `BuiltSystem.constraint_set_hash` is a stored field, so patching a system
with `dataclasses.replace` copies the unmasked hash verbatim — the patched object would report a
hash that matches the persisted constraint set and the run manifest while describing a different
system. Measured: a full rebuild costs ~0.05 s and the solve ~0.31 s, against ~30 s for the
estimator pass this sits beside, so there is nothing to optimise here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..config import Config
from ..constraints.bounds import solve_bounds
from ..constraints.cells import KIND_NATIONAL_SIZE
from ..constraints.system import build_constraint_system
from ..contracts import HarmonizedData
from .mask import MaskTarget, apply_mask, apply_size_mask


@dataclass(frozen=True)
class MaskedSystem:
    """A solved constraint system for one mask, plus the truth it withheld."""

    bounds: pl.DataFrame
    components: pl.DataFrame
    constraint_set_hash: str
    truth: pl.DataFrame


def mask_and_solve(
    data: HarmonizedData, targets: Sequence[MaskTarget], config: Config
) -> MaskedSystem:
    """Apply the mask, rebuild the system from the masked frame, and solve it."""
    masked, truth = apply_mask(data, targets) if targets else (data, _empty_truth())
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    return MaskedSystem(
        bounds=result.bounds,
        components=result.components,
        constraint_set_hash=built.constraint_set_hash,
        truth=truth,
    )


def _empty_truth() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "state_fips": pl.String,
            "reference_month": pl.String,
            "truth": pl.Int64,
            "qtrly_establishments": pl.Int64,
        }
    )


def is_exactly_recoverable(bounds: pl.DataFrame, cell_id: str) -> bool:
    """§13.2 step 6's predicate, and only this one.

    NOT `exactly_identified`: that column is True for every published cell (3,534 of them on D1),
    because a published value is trivially identified by its own equality row. Filtering on it
    would reject every mask.
    """
    row = bounds.filter(pl.col("cell_id") == cell_id)
    if row.height == 0:
        raise KeyError(f"{cell_id!r} is not in this system's bounds")
    return row["bound_status"].item() == "exactly_recoverable"


def mask_and_solve_size(
    data: HarmonizedData, reference_month: str, *, n_classes: int, seed: int, config: Config
) -> tuple[MaskedSystem, str]:
    """Mask `n_classes` observed size classes in one March and solve. Returns the first cell_id.

    `solve_bounds` MAY raise: flipping a size cell to suppressed ADDS a hard `size_support` range
    row (`rows.size_support_rows` fires only for suppressed classes), so a mask on this arm can
    make the component infeasible. That is a legitimate outcome of a legitimate mask and the
    harness records it rather than crashing the run.
    """
    size = data.qcew_national_size.filter(
        (pl.col("industry_code") == "113310")
        & (pl.col("reference_month") == reference_month)
        & (pl.col("observation_status") == "observed")
    )
    drawn = size.sample(n=n_classes, with_replacement=False, shuffle=True, seed=seed)
    codes = drawn["size_class"].to_list()
    masked, truth = apply_size_mask(data, reference_month, codes)
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    # Looked up on the cells table's own key columns, NOT matched by substring on `cell_id`.
    # `cell_id` is a pipe-separated key whose fields include "113310" and "NAICS 2017", so
    # `str.contains(size_class)` on a one-character class matches every cell in the month —
    # measured, that returned 6 rows where 1 was wanted.
    candidates = built.cells.filter(
        (pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_SIZE}|"))
        & (pl.col("reference_month") == reference_month)
        & (pl.col("size_class") == codes[0])
    )
    if candidates.height != 1:
        raise KeyError(
            f"{KIND_NATIONAL_SIZE} {reference_month}/{codes[0]} matched {candidates.height} "
            "cells; exactly one was expected"
        )
    target_id = candidates["cell_id"].item()
    return (
        MaskedSystem(result.bounds, result.components, built.constraint_set_hash, truth),
        target_id,
    )
