"""The one place a cell becomes hidden.

The mask lives in the FRAME, not in a hand-built `Partition`. `observed_partition`'s docstring
invites a partition-only mask, and measured on 2026-09-07 that route leaves the constraint system
still fixing the answer: view A (table untouched) keeps a `fix|state_total|...` equality at the
held-out value and reports `bound_status='observed'`, while view B (frame masked) reports
`unbounded`. The partition-only view also leaves the truth in
`context.partitions[m].missing["employment_value"]`, one column read from any estimator. Masking
the frame makes the leak unconstructible rather than merely unused.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..contracts import SUPPRESSION_TYPES, HarmonizedData
from ..errors import ConceptViolationError


@dataclass(frozen=True)
class MaskTarget:
    """One cell to hide, with the INV-009 label it will carry."""

    state_fips: str
    reference_month: str
    arm: str
    suppression_type: str


def eligible_targets(monthly: pl.DataFrame) -> pl.DataFrame:
    """Cells a mask may hide: published state cells that have at least one establishment.

    A `true_zero` cell has `qtrly_establishments == 0`, and masking one costs a whole month across
    nine estimators — measured, eight raise `WeightDomainError` and one declines, because the
    disclosed establishment total that scales their fallback arm goes to zero. The loss lands only
    on the states that carry true zeros, so admitting them biases the scoreboard non-randomly.
    """
    return monthly.filter(
        (pl.col("area_type") == "state")
        & (pl.col("observation_status") == "observed")
        & (pl.col("qtrly_establishments") > 0)
    )


def apply_mask(
    data: HarmonizedData, targets: Sequence[MaskTarget]
) -> tuple[HarmonizedData, pl.DataFrame]:
    """Hide every target and return `(masked_data, truth_table)`.

    The truth table is captured BEFORE the flip and is the harness's only copy of the held-out
    values. It is never handed to an estimator.
    """
    for target in targets:
        if target.suppression_type not in SUPPRESSION_TYPES:
            raise ConceptViolationError(
                f"suppression_type {target.suppression_type!r} is not declared; the set is "
                f"{list(SUPPRESSION_TYPES)} (INV-009)"
            )

    monthly = data.qcew_monthly
    keys = [(t.state_fips, t.reference_month) for t in targets]
    if len(keys) != len(set(keys)):
        raise ConceptViolationError(
            "a cell appears twice in the target set; masking it twice would duplicate its row in "
            "the masked frame and double-count it in the missing set"
        )
    selector = pl.struct("state_fips", "reference_month").is_in(
        [{"state_fips": s, "reference_month": m} for s, m in keys]
    )

    chosen = monthly.filter(selector)
    if chosen.height != len(set(keys)):
        raise ConceptViolationError(
            f"{len(set(keys))} targets requested but {chosen.height} rows matched; a target with "
            "no published row cannot be masked (the six never-observed states are permanently in "
            "the missing set and are never eligible)"
        )
    bad_status = chosen.filter(pl.col("observation_status") != "observed")
    if bad_status.height:
        raise ConceptViolationError(
            f"{bad_status.height} target(s) have observation_status != 'observed'; masking an "
            "already-suppressed cell hides nothing and double-counts it in the missing set"
        )
    bad_est = chosen.filter(pl.col("qtrly_establishments") <= 0)
    if bad_est.height:
        raise ConceptViolationError(
            f"{bad_est.height} target(s) have qtrly_establishments <= 0. Measured 2026-09-07: "
            "masking such a cell raises WeightDomainError in eight estimators and declines a "
            "ninth, costing the whole month non-randomly"
        )

    truth = chosen.select(
        pl.col("state_fips"),
        pl.col("reference_month"),
        pl.col("employment_value").alias("truth"),
        pl.col("qtrly_establishments"),
    )

    labels = pl.DataFrame(
        {
            "state_fips": [t.state_fips for t in targets],
            "reference_month": [t.reference_month for t in targets],
            "_label": [t.suppression_type for t in targets],
        }
    )

    masked = (
        monthly.join(labels, on=["state_fips", "reference_month"], how="left")
        .with_columns(
            pl.when(selector)
            .then(None)
            .otherwise(pl.col("employment_value"))
            .alias("employment_value"),
            pl.when(selector)
            .then(pl.lit("0"))
            .otherwise(pl.col("employment_raw"))
            .alias("employment_raw"),
            pl.when(selector).then(None).otherwise(pl.col("wages_value")).alias("wages_value"),
            pl.when(selector).then(pl.lit("0")).otherwise(pl.col("wages_raw")).alias("wages_raw"),
            pl.when(selector)
            .then(pl.lit("N"))
            .otherwise(pl.col("disclosure_code"))
            .alias("disclosure_code"),
            pl.when(selector)
            .then(pl.lit("suppressed"))
            .otherwise(pl.col("observation_status"))
            .alias("observation_status"),
            pl.when(selector)
            .then(True)
            .otherwise(pl.col("is_published_numeric_zero"))
            .alias("is_published_numeric_zero"),
            pl.when(selector)
            .then(pl.col("_label"))
            .otherwise(pl.col("suppression_type"))
            .alias("suppression_type"),
        )
        .drop("_label")
    )
    return dataclasses.replace(data, qcew_monthly=masked), truth
