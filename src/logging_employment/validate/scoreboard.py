"""The number Stage 5's §13.10 promotion gate compares against.

Provenance rules, each from a measured trap:
  - THE PER-MONTH RULE BELONGS TO A DIFFERENT QUESTION IN A DIFFERENT MODULE, and this bullet
    used to read as though it governed here. §10.8 resolved by AVAILABILITY -- which rung actually
    produced rows -- is `baselines.runner.preferred_estimator_by_month`, and THAT must be read per
    month rather than from the window scalar: measured, the scalar names `cbp_intensity` for all
    96 months while CBP is published only through 2023, so it names an estimator that produced
    nothing in 12 of them. This module answers the SCORING question instead -- best hierarchy
    member per regime, against pseudo-suppression truth -- and the scoreboard carries no month
    column at all. Neither substitutes for the other;
  - a null metric never sorts ahead of a real one — an estimator that declined every cell has no
    error, not zero error;
  - the own/fallback split rides on every row, per estimator, because §10.3 variant 5's refusals
    COMPOSE rather than decline and are invisible to decline counts;
  - the gate's comparand is restricted to §10.8's hierarchy while the unrestricted best is
    reported beside it, because §13.10's failure branch is "deploy the simpler method" and an
    estimator §10.8 refuses to rank is not something anyone would deploy. Two functions, one
    gating, deliberately: see `preferred_baseline` and `best_scoring_baseline`;
  - scores are POOLED across a regime's seeds before ranking, never ranked across them.
"""

from __future__ import annotations

import polars as pl

from ..baselines.runner import FALLBACK_RUNGS, PREFERRABLE, RUNG_OF


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


def _best(scoreboard: pl.DataFrame, *, regime: str, eligible: frozenset[str] | None) -> str | None:
    """The regime's lowest pooled-WAPE estimator among `eligible`, or None if none scored.

    POOLED ACROSS SEEDS, NOT RANKED ACROSS THEM. The scoreboard is one row per
    (regime, seed, estimator), so sorting its rows and taking the first is an argmin over
    seeds x estimators -- an order statistic that rewards VARIANCE, not accuracy. Measured on D1's
    `long_consecutive_runs`, `equal_residual` holds both the best single row in the regime (0.1106)
    and the two worst (2.0258, 2.0452); ranking rows crowned it on the strength of one lucky seed.

    The weight is `denominator`, the masked cell-row count, so a seed that masked more cells counts
    for more. Stated plainly, because it is an approximation: WAPE's own denominator is
    `sum|truth|` (`metrics.point_metrics`) and the scoreboard does not carry it, so this is
    cell-weighted pooling rather than an exact pooled WAPE. On D1 the distinction does not bind --
    unweighted, cell-weighted and `n_scored`-weighted pooling pick the same estimator in 9 of 9
    regimes -- and only the row-argmin differs from all three.

    `n_scored > 0` is a filter, not a tiebreak: an all-declining estimator has a null WAPE, and a
    sort that treats null as smallest would crown `harvest_proportional`, which declines by design
    in every month of the window.
    """
    candidates = scoreboard.filter(
        (pl.col("regime") == regime) & (pl.col("n_scored") > 0) & pl.col("wape").is_not_null()
    )
    if eligible is not None:
        candidates = candidates.filter(pl.col("estimator_id").is_in(sorted(eligible)))
    if candidates.height == 0:
        return None
    pooled = candidates.group_by("estimator_id").agg(
        ((pl.col("wape") * pl.col("denominator")).sum() / pl.col("denominator").sum()).alias(
            "pooled_wape"
        )
    )
    ranked = pooled.with_columns(
        pl.col("estimator_id")
        .replace_strict(RUNG_OF, default=len(FALLBACK_RUNGS), return_dtype=pl.Int32)
        .alias("rung")
    ).sort("pooled_wape", "rung", "estimator_id")
    return str(ranked["estimator_id"].to_list()[0])


def preferred_baseline(scoreboard: pl.DataFrame, *, regime: str) -> str | None:
    """§13.10's comparand: the best-scoring member of §10.8's hierarchy, or None.

    RESTRICTED TO THE HIERARCHY BECAUSE THE GATE'S FAILURE BRANCH IS "deploy the simpler method".
    §13.10 asks whether the model beats what would otherwise ship, and §10.8 is what would
    otherwise ship. An estimator the hierarchy refuses to rank is not deployable, so gating against
    it can block a model in favour of something no one would deploy -- and §10.1 and §10.5
    disqualify their two by name.

    Returns None where no hierarchy member scored. That is the cost of the restriction, and it is
    real but not observed: on the D1 acceptance run (`runs/f03023ac9f3a`) every one of the nine
    scored regimes has hierarchy members scoring, so this returns a name in 9 of 9. §13.10 must
    read None rather than silently fall through to a sanity check.

    Pair it with `best_scoring_baseline`: where the two disagree, the divergence is the §10.1
    signal, not an error.
    """
    return _best(scoreboard, regime=regime, eligible=PREFERRABLE)


def best_scoring_baseline(scoreboard: pl.DataFrame, *, regime: str) -> str | None:
    """The best-scoring estimator of ANY kind, hierarchy member or not.

    Reported beside `preferred_baseline`, never in place of it. Scoring and §10.8's ordering answer
    different questions, and this one is diagnostic: equal allocation out-scoring every hierarchy
    member says the establishment counts QCEW publishes for suppressed cells are not earning their
    place on that regime -- which is exactly the use §10.1 puts it to. Suppressing that to report
    only the gate's comparand would discard the sanity check the spec asks for.

    It is NOT a promotion comparand. Nothing may gate on it.
    """
    return _best(scoreboard, regime=regime, eligible=None)
