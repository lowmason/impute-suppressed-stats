"""§9.8: "Exactly recoverable and unusually narrow cells MUST be sent to disclosure review."

Both flags are computed for suppressed cells only, and that guard is the whole reason this module
exists rather than the two predicates living inline. A published cell's feasible interval is a
point -- it was pinned to its own value by INV-001 -- so every width test ever written passes on it.
Flagging those would route thousands of already-public state-months to review and bury the handful
of cells that carry real reconstruction risk.

"Unusually narrow" is a governance decision, not a measurement: §21 leaves disclosure thresholds to
the owner. The two widths come from configuration, and §14.2's "narrow in absolute or relative
terms" is read as a disjunction -- either test alone routes the cell to review.

Stage 8 widens this into §7.12's `disclosure_decision`, whose other three flags need a posterior,
an employer linkage judgement, and an analytic-sufficiency judgement that Stage 2 cannot make.
"""

from __future__ import annotations

import polars as pl

from ..config import DisclosureConfig

FLAG_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "bound_status": pl.String,
    "feasible_width": pl.Float64,
    "relative_width": pl.Float64,
    "exact_reconstruction_flag": pl.Boolean,
    "narrow_feasible_interval_flag": pl.Boolean,
}


def build_flags(
    bounds: pl.DataFrame, cells: pl.DataFrame, config: DisclosureConfig
) -> pl.DataFrame:
    """One row per cell, with both Stage 2 flags and the widths that decided them."""
    suppressed = pl.col("observation_status") == "suppressed"
    width = pl.col("selected_upper") - pl.col("selected_lower")
    midpoint = (pl.col("selected_upper") + pl.col("selected_lower")) / 2
    return (
        bounds.join(cells.select(["cell_id", "observation_status"]), on="cell_id", how="left")
        .with_columns(
            width.alias("feasible_width"),
            pl.when(midpoint > 0).then(width / midpoint).otherwise(None).alias("relative_width"),
        )
        .with_columns(
            (suppressed & (pl.col("bound_status") == "exactly_recoverable")).alias(
                "exact_reconstruction_flag"
            ),
            (
                suppressed
                & pl.col("feasible_width").is_not_null()
                & (
                    (pl.col("feasible_width") <= config.narrow_interval_absolute_width)
                    | (
                        pl.col("relative_width").is_not_null()
                        & (pl.col("relative_width") <= config.narrow_interval_relative_width)
                    )
                )
            ).alias("narrow_feasible_interval_flag"),
        )
        .select(list(FLAG_SCHEMA))
        .cast(FLAG_SCHEMA)  # type: ignore[arg-type]
        .sort("cell_id")
    )
