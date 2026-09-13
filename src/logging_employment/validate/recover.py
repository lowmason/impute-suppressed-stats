"""§13.2 steps 5-6 and §13.5: rank, bound and check analysis on a masked component.

Always a FULL rebuild. `BuiltSystem.constraint_set_hash` is a stored field, so patching a system
with `dataclasses.replace` copies the unmasked hash verbatim — the patched object would report a
hash that matches the persisted constraint set and the run manifest while describing a different
system. Measured: a full rebuild costs ~0.05 s and the solve ~0.31 s, against ~30 s for the
estimator pass this sits beside, so there is nothing to optimise here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import polars as pl

from ..config import Config
from ..constraints.bounds import solve_bounds
from ..constraints.cells import KIND_NATIONAL_SIZE, KIND_STATE_TOTAL
from ..constraints.system import build_constraint_system
from ..contracts import HarmonizedData
from ..errors import ConstraintDataError
from .mask import MaskTarget, apply_mask, apply_size_mask


def _no_recoverable() -> pl.DataFrame:
    """The step-6 frame of a mask with nothing exactly recoverable: rowless but SHAPED."""
    return pl.DataFrame(schema={"state_fips": pl.String, "reference_month": pl.String})


@dataclass(frozen=True)
class MaskedSystem:
    """A solved constraint system for one mask, the truth it withheld, and what still recovers it.

    `recoverable` holds the `(state_fips, reference_month)` of every withheld state cell the masked
    system still pins to one value -- §13.2 step 6's cases, which `harness.reject_exactly_recoverable`
    drops from scoring. It defaults to empty for the size arm, whose step-6 rule is `D-085`'s.
    """

    bounds: pl.DataFrame
    components: pl.DataFrame
    constraint_set_hash: str
    truth: pl.DataFrame
    recoverable: pl.DataFrame = field(default_factory=_no_recoverable)


def mask_and_solve(
    data: HarmonizedData, targets: Sequence[MaskTarget], config: Config
) -> MaskedSystem:
    """Apply the mask, rebuild the system from the masked frame, solve it, and check it.

    Two checks run on every solve, because a masked system is the only place either can be seen. A
    withheld truth outside its masked bounds HALTS (§13.5, `assert_truth_within_bounds`), and a
    withheld cell the masked system still recovers exactly is returned in `recoverable` for the
    harness to reject (§13.2 step 6). Before `D-111` neither could fire on the state-total arm,
    because every masked state cell was `[0, +inf)`.
    """
    masked, truth = apply_mask(data, targets) if targets else (data, _empty_truth())
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    located = locate_withheld(truth, built.cells, result.bounds)
    assert_truth_within_bounds(located, tolerance=config.constraints.feasibility_tolerance)
    return MaskedSystem(
        bounds=result.bounds,
        components=result.components,
        constraint_set_hash=built.constraint_set_hash,
        truth=truth,
        recoverable=exactly_recoverable(located),
    )


def locate_withheld(truth: pl.DataFrame, cells: pl.DataFrame, bounds: pl.DataFrame) -> pl.DataFrame:
    """Each withheld state cell beside its `cell_id` and masked bounds, joined on key columns.

    Joined on the cells table's own `state_fips` and `reference_month`, never by parsing `cell_id`
    (`mask_and_solve_size` records what substring matching on it measured). LEFT joins, so a
    withheld cell the system somehow lacks survives as nulls for `assert_truth_within_bounds` to
    refuse, rather than vanishing from the check.
    """
    ids = cells.filter(pl.col("cell_id").str.starts_with(f"{KIND_STATE_TOTAL}|")).select(
        "cell_id", "state_fips", "reference_month"
    )
    return truth.join(ids, on=["state_fips", "reference_month"], how="left").join(
        bounds.select("cell_id", "selected_lower", "selected_upper", "bound_status"),
        on="cell_id",
        how="left",
    )


def assert_truth_within_bounds(located: pl.DataFrame, *, tolerance: float) -> None:
    """§13.5: "A known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug".

    `tolerance` is the solver's `feasibility_tolerance`, because the endpoints came out of HiGHS at
    that tolerance. A withheld cell with no located bound halts too: a check that silently skips the
    cells it cannot find passes exactly the case it exists to catch.
    """
    unchecked = located.filter(pl.col("cell_id").is_null() | pl.col("selected_lower").is_null())
    if unchecked.height:
        first = unchecked.row(0, named=True)
        raise ConstraintDataError(
            f"{unchecked.height} withheld cell(s) have no masked bound to check, e.g. "
            f"{first['state_fips']}/{first['reference_month']}; §13.5's rule cannot pass a cell it "
            "never compared"
        )
    outside = located.filter(
        (pl.col("truth") < pl.col("selected_lower") - tolerance)
        | (
            pl.col("selected_upper").is_not_null()
            & (pl.col("truth") > pl.col("selected_upper") + tolerance)
        )
    )
    if outside.height:
        first = outside.row(0, named=True)
        raise ConstraintDataError(
            f"{outside.height} withheld truth(s) fall outside their masked deterministic bounds, "
            f"e.g. {first['cell_id']}: truth {first['truth']} against [{first['selected_lower']}, "
            f"{first['selected_upper']}]. §13.5 treats this as a constraint-data bug until proven "
            "otherwise, so the run halts rather than scoring against a system that excludes the truth"
        )


def exactly_recoverable(located: pl.DataFrame) -> pl.DataFrame:
    """§13.2 step 6's cases: the withheld state cells the masked system still pins to one value."""
    return (
        located.filter(pl.col("bound_status") == "exactly_recoverable")
        .select("state_fips", "reference_month")
        .sort("state_fips", "reference_month")
    )


def _empty_truth() -> pl.DataFrame:
    """The truth frame a no-target mask withholds: rowless but SHAPED.

    A bare `pl.DataFrame()` would make every downstream join fail on a missing column, reporting a
    schema error where the fact is that this replicate masked nothing.
    """
    return pl.DataFrame(
        schema={
            "state_fips": pl.String,
            "reference_month": pl.String,
            "truth": pl.Int64,
            "qtrly_establishments": pl.Int64,
            "suppression_type": pl.String,
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
