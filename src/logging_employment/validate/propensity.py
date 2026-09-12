"""§13.2 step 1: a configurable propensity over PUBLIC predictors only.

§13.2 names five predictors. Three enter the score -- establishment count, historical volatility and
sparsity. Employment per establishment is deliberately left out (see the `_epe` note in
`target_propensity`), and the fifth -- "parent share" -- is NOT implemented and is not approximated: the STATE-level staged tables (`qcew_monthly`, `cbp_state_size`) carry industry 113310
alone, so the pipeline has no parent 1133 or 113 state series to form a share against
(`qcew_national_size` carries 113, 1133 and 11331, but only nationally). A private 113 state series
IS published -- measured 2026-09-11 in `specs/findings/qcew-parent-margins.md` -- and is not
ingested (`D-111`). Ingesting it is all an ESTABLISHMENT-count share needs,
since establishment counts are published even where employment is suppressed. An EMPLOYMENT share
would also need a leave-one-out form like the volatility term, because a same-month share contains
the hidden target's own value (§13.4). Fabricating a share
from the national total instead would make the predictor a function of the residual this harness is
trying to score.

Every predictor below is computable from data that stays public when the target is hidden:
establishment counts are published even for employment-suppressed cells, and the volatility and
sparsity terms read the state's OTHER months, never the target month's own value.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from ..config import Config
from .mask import MaskTarget, eligible_targets


def target_propensity(monthly: pl.DataFrame, *, config: Config) -> pl.DataFrame:
    """A propensity in [0, 1] per eligible cell. Higher = more primary-like.

    The volatility term is LEAVE-ONE-OUT. A plain per-state mean and standard deviation would
    include the target's own month, so perturbing a cell's employment would move that cell's own
    propensity — a §13.4 bullet-1 violation at selection time, and one that a docstring claiming
    otherwise does not fix. Verified by the leakage test in this task: with the pooled statistics
    the perturbation test fails; with the sums below it passes.
    """
    del config  # No threshold here is configurable yet; the signature is §16.2's, not a promise.
    eligible = eligible_targets(monthly)
    observed = monthly.filter(
        (pl.col("area_type") == "state") & (pl.col("observation_status") == "observed")
    )
    # Sums, not moments, so each row's own contribution can be subtracted back out.
    stats = observed.group_by("state_fips").agg(
        pl.col("employment_value").cast(pl.Float64).sum().alias("_sum"),
        (pl.col("employment_value").cast(pl.Float64) ** 2).sum().alias("_sumsq"),
        pl.len().alias("_n"),
    )
    max_n = stats["_n"].max()

    scored = (
        eligible.join(stats, on="state_fips", how="left")
        .with_columns(pl.col("employment_value").cast(pl.Float64).alias("_v"))
        .with_columns((pl.col("_n") - 1).alias("_n_loo"))
        .with_columns(
            ((pl.col("_sum") - pl.col("_v")) / pl.col("_n_loo").clip(lower_bound=1)).alias(
                "_mean_loo"
            )
        )
        .with_columns(
            (
                ((pl.col("_sumsq") - pl.col("_v") ** 2) / pl.col("_n_loo").clip(lower_bound=1))
                - pl.col("_mean_loo") ** 2
            )
            .clip(lower_bound=0.0)
            .sqrt()
            .alias("_sd_loo")
        )
        .with_columns(
            (pl.col("_sd_loo") / pl.col("_mean_loo").clip(lower_bound=1.0))
            .fill_null(0.0)
            .alias("_cv"),
            (1.0 - pl.col("_n_loo") / max_n).alias("_sparsity"),
            (1.0 / (1.0 + pl.col("qtrly_establishments").cast(pl.Float64))).alias("_small"),
        )
    )
    # `_epe` (employment per establishment) is NOT in the score: it is a function of the target's
    # own held-out value. It is dropped rather than reported, so no downstream stratification can
    # reach for it by accident.
    return scored.with_columns(
        (
            0.5 * pl.col("_small")
            + 0.3 * pl.col("_cv").clip(upper_bound=1.0)
            + 0.2 * pl.col("_sparsity")
        ).alias("propensity")
    ).drop("_sum", "_sumsq", "_n", "_v", "_n_loo", "_mean_loo", "_sd_loo")


def sample_targets(monthly: pl.DataFrame, *, n: int, seed: int, config: Config) -> list[MaskTarget]:
    """Draw `n` primary-like targets without replacement, weighted by propensity.

    The draw is genuinely propensity-WEIGHTED, not a uniform sample that is merely sorted by
    propensity afterwards. `pl.DataFrame.sample` takes no weight vector, so the draw goes through
    `numpy.random.Generator.choice(p=...)`, seeded from the same integer. Sorting a uniform sample
    would leave `small_cell_biased` — the regime whose only selector this is — drawing the same
    population as a random mask, which §13.2 prohibits as the ONLY design and which the regime's
    own name would then misreport.
    """
    scored = target_propensity(monthly, config=config)
    take = min(n, scored.height)
    if take == 0:
        return []
    weights = scored["propensity"].to_numpy().astype(float)
    total = weights.sum()
    # A degenerate score vector falls back to uniform rather than raising: every cell is then
    # equally primary-like, which is a statement about the panel, not an error.
    probabilities = weights / total if total > 0 else None
    index = np.random.default_rng(seed).choice(
        scored.height, size=take, replace=False, p=probabilities
    )
    drawn = scored[index.tolist()].sort("propensity", descending=True)
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def complementary_partners(
    monthly: pl.DataFrame, target: MaskTarget, *, n: int, seed: int
) -> list[MaskTarget]:
    """§13.2 step 3's complementary-like cells, in the target's own month.

    SCOPE, stated because the obvious reading is wrong: on the `state_total` arm this defeats no
    subtraction, because there is none. Measured 2026-09-07, all 4,716 state cells are single-cell
    components — `assert_no_national_employment_margin` is Stage 0's SRC-QCEW-006 `decline` in
    code. A masked state total is `unbounded` with and without partners.

    The partners are still required: §13.2 step 8 scores primary-like and complementary-like cells
    separately, and INV-009 reserves those labels for synthetic masks. Task 8's national-size arm
    is where a complementary mask actually changes identification.
    """
    same_month = eligible_targets(monthly).filter(
        (pl.col("reference_month") == target.reference_month)
        & (pl.col("state_fips") != target.state_fips)
    )
    drawn = same_month.sample(
        n=min(n, same_month.height), with_replacement=False, shuffle=True, seed=seed
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "complementary_like")
        for r in drawn.iter_rows(named=True)
    ]
