"""The number Stage 5's §13.10 promotion gate compares against.

Provenance rules, each from a measured trap:
  - the preferred baseline is read PER MONTH, never from the window scalar: measured, the scalar
    names `cbp_intensity` for all 96 months while CBP is published only through 2023, so it names
    an estimator that produced nothing in 12 of them;
  - a null metric never sorts ahead of a real one — an estimator that declined every cell has no
    error, not zero error;
  - the own/fallback split rides on every row, per estimator, because §10.3 variant 5's refusals
    COMPOSE rather than decline and are invisible to decline counts.
"""

from __future__ import annotations

import polars as pl


def build_scoreboard(metrics: pl.DataFrame) -> pl.DataFrame:
    """One row per (regime, estimator) for the headline metric, with its provenance attached.

    The own/fallback split is JOINED, not selected. `point_metrics` and `decline_and_basis_report`
    emit different column sets and the harness concatenates them with `how="diagonal"`, so
    `n_own_estimator` is null on every point row. Selecting it straight off the filtered point rows
    returns null for all of them — silently dropping the one column that makes §10.3 variant 5's
    composed refusals visible, which is the whole reason the report exists.
    """
    headline = metrics.filter(
        (pl.col("metric_family") == "point") & (pl.col("metric_name") == "wape")
    ).select(
        "regime",
        "seed",
        "mask_arm",
        "estimator_id",
        pl.col("value").alias("wape"),
        "denominator",
        "denominator_basis",
        "n_scored",
        "n_declined_by_design",
        "n_declined_data_gap",
        "n_declined_reconciliation_failure",
    )
    basis = metrics.filter(pl.col("metric_family") == "declines").select(
        "regime", "seed", "estimator_id", "n_own_estimator", "n_establishment_fallback"
    )
    return headline.join(basis, on=["regime", "seed", "estimator_id"], how="left").sort(
        "regime", "estimator_id"
    )


def preferred_baseline(scoreboard: pl.DataFrame, *, regime: str) -> str | None:
    """The best-scoring estimator that actually scored something, or None.

    `n_scored > 0` is a filter, not a tiebreak: an all-declining estimator has a null WAPE, and a
    sort that treats null as smallest would crown `harvest_proportional`, which declines by design
    in every month of the window.
    """
    candidates = scoreboard.filter(
        (pl.col("regime") == regime) & (pl.col("n_scored") > 0) & pl.col("wape").is_not_null()
    )
    if candidates.height == 0:
        return None
    return candidates.sort("wape")["estimator_id"].to_list()[0]
