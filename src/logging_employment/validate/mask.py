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


def parents_to_hide(parent: pl.DataFrame, chosen: pl.DataFrame) -> pl.DataFrame:
    """§13.2 step 4 for the §9.3 parent: the masked cells whose published parent is hidden too.

    THE RULE: hide a parent exactly when it holds no establishments besides the masked cell's own --
    parent `qtrly_establishments` minus child `qtrly_establishments` at most 0 -- and leave every
    other parent as public as it really is. Establishment counts are published even for suppressed
    cells, so the rule reads nothing a real suppression would withhold.

    Why this rule and not a propensity, measured 2026-09-12 (`specs/stage5-parent-margin.md` R-PM-3):

    * Where the child is all of the parent's establishments BLS hid the parent on 123 of 123 real
      suppressions, and on all 336 published month-values with no sibling establishments the parent
      EQUALS the child. That is the one case where a visible parent recovers the target exactly
      (§13.2 step 6), and there the rule and BLS's own complementary suppression coincide.
    * Everywhere else the rule leaves the parent visible, and BLS hid it on 34 of 286 real
      suppressions: 21 of 95 with one sibling establishment, 13 of 191 with two or more. The rule
      never hides a parent BLS published; its error is optimism, on 34 of 409 (8.3%). A pseudo-target
      cannot reach the one-sibling case with its parent visible -- a published child with one sibling
      establishment never has a published parent (0 of 49) -- so on the synthetic path the optimism
      is confined to the two-or-more stratum.

    A flat co-suppression rate would ignore the one public variable that measurably drives it, and a
    propensity fitted to 34 events would describe noise. Returns sorted `(state_fips,
    reference_month)` keys, so the leakage guard can re-apply the rule to a masked layer.
    """
    published = parent.filter(pl.col("observation_status") != "suppressed").select(
        "state_fips",
        "reference_month",
        pl.col("qtrly_establishments").alias("parent_establishments"),
    )
    return (
        chosen.select(
            "state_fips",
            "reference_month",
            pl.col("qtrly_establishments").alias("child_establishments"),
        )
        .join(published, on=["state_fips", "reference_month"], how="inner")
        .filter(pl.col("parent_establishments") - pl.col("child_establishments") <= 0)
        .select("state_fips", "reference_month")
        .sort("state_fips", "reference_month")
    )


def _hide(frame: pl.DataFrame, selector: pl.Expr, label: pl.Expr) -> pl.DataFrame:
    """Rewrite the selected rows exactly as a real `N` suppression publishes them, labelled `label`.

    One rewrite for the `113310` target and its `113` parent, so a hidden parent is
    indistinguishable from a real suppressed one in precisely the columns a hidden child is.
    """
    return frame.with_columns(
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
        .then(label)
        .otherwise(pl.col("suppression_type"))
        .alias("suppression_type"),
    )


def apply_mask(
    data: HarmonizedData, targets: Sequence[MaskTarget]
) -> tuple[HarmonizedData, pl.DataFrame]:
    """Hide every target and return `(masked_data, truth_table)`.

    The truth table is captured BEFORE the flip and is the harness's only copy of the held-out
    values. It is never handed to an estimator.

    The private 113 parent of a target is hidden too exactly when `parents_to_hide` names it
    (§13.2 step 4); every other parent keeps its real visibility.
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

    labels = pl.DataFrame(
        {
            "state_fips": [t.state_fips for t in targets],
            "reference_month": [t.reference_month for t in targets],
            "_label": [t.suppression_type for t in targets],
        }
    )

    # The INV-009 label rides on the truth table, not just on the masked frame. `baseline_results`
    # carries no `suppression_type`, so this is the harness's only route from a target's label to
    # its scored row — and §13.2 step 8 requires primary-like and complementary-like cells to be
    # scored SEPARATELY.
    truth = chosen.join(labels, on=["state_fips", "reference_month"], how="left").select(
        pl.col("state_fips"),
        pl.col("reference_month"),
        pl.col("employment_value").alias("truth"),
        pl.col("qtrly_establishments"),
        pl.col("_label").alias("suppression_type"),
    )

    masked = _hide(
        monthly.join(labels, on=["state_fips", "reference_month"], how="left"),
        selector,
        pl.col("_label"),
    ).drop("_label")

    # §13.2 step 4 for the §9.3 parent: hide exactly the parents `parents_to_hide` names and leave
    # every other one as public as it really is. `complementary_like` because the parent is hidden
    # to protect the target, which is what that INV-009 label means.
    hidden = parents_to_hide(data.qcew_state_parent, chosen)
    parent = data.qcew_state_parent
    if hidden.height:
        parent = _hide(
            parent,
            pl.struct("state_fips", "reference_month").is_in(hidden.to_dicts()),
            pl.lit("complementary_like"),
        )
    return dataclasses.replace(data, qcew_monthly=masked, qcew_state_parent=parent), truth


def apply_size_mask(
    data: HarmonizedData, reference_month: str, size_classes: Sequence[str]
) -> tuple[HarmonizedData, pl.DataFrame]:
    """Hide national size classes in one March margin.

    This is the arm on which §13.2 steps 3 and 6 have identification content: a March margin is a
    genuine multi-cell component, so masking one class is recoverable by subtraction and masking
    two is not.

    NOTE THE COLUMN NAMES. `qcew_national_size` does NOT share `qcew_monthly`'s vocabulary: it uses
    `size_class`, `employment` and `establishments` where the monthly table uses `size_code`,
    `employment_value` and `qtrly_establishments`, and it carries no `employment_raw`,
    `wages_raw` or `is_published_numeric_zero`. Writing the monthly names here silently masks
    nothing — the filter matches zero rows.
    """
    size = data.qcew_national_size
    selector = (
        (pl.col("reference_month") == reference_month)
        & (pl.col("industry_code") == "113310")
        & pl.col("size_class").is_in(list(size_classes))
    )
    chosen = size.filter(selector)
    if chosen.height != len(size_classes):
        raise ConceptViolationError(
            f"{len(size_classes)} size classes requested, {chosen.height} matched in "
            f"{reference_month}"
        )
    truth = chosen.select("reference_month", "size_class", pl.col("employment").alias("truth"))
    masked = size.with_columns(
        pl.when(selector).then(None).otherwise(pl.col("employment")).alias("employment"),
        pl.when(selector)
        .then(pl.lit("N"))
        .otherwise(pl.col("disclosure_code"))
        .alias("disclosure_code"),
        pl.when(selector)
        .then(pl.lit("suppressed"))
        .otherwise(pl.col("observation_status"))
        .alias("observation_status"),
    )
    return dataclasses.replace(data, qcew_national_size=masked), truth
