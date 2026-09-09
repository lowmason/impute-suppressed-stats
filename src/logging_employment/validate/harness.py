"""§16.2's `run_pseudo_suppression`.

Cost, measured 2026-09-07 on the D1 staged layer at one seed -- 9 of the 13 regimes score, one
(regime, seed) pass each, 9 passes in all: 226.6 s for the full ten-estimator registry, 49.6 s for
`share_last_observed` alone, 6.2 s for `establishment_proportional` alone. Those last two are the
controlled comparison and they name the bill: both do identical `run_baselines` work for one
estimator, and the only difference between them is that one is in `metrics._INTERVAL_FAMILIES` and
one is not. The 43 s between them is §13.7's CRPS.

So the dominant cost is the metric layer, not `run_baselines`, and it is superlinear in an
estimator's own scored-cell count (`intervals.crps` is O(n log n) per cell, O(n^2 log n) per
estimator). Ten estimators cost 36x one rather than 10x. An earlier note here read "~30 s per
replicate, essentially all of it `run_baselines`"; that predates the sorted-ensemble CRPS, and it
also read `replicates_per_regime` as this loop's trip count -- that setting sizes the MASK
(`regimes.sample_targets`), while the loop runs once per configured seed.

The estimator subset is still the lever, it just pulls on CRPS: `run_baselines` takes one, regimes
can declare the ones they need, and `validate --estimators` reaches it from the command line. The
shipped three-seed, full-registry run is 11:03.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..baselines.interfaces import Estimator
from ..baselines.runner import REGISTRY, run_baselines
from ..config import Config
from ..contracts import REGIME_SWITCHES, HarmonizedData, assert_declared_provenance
from ..errors import ConceptViolationError
from .leakage import assert_no_future_rows, assert_no_retained_truth
from .mask import MaskTarget, apply_mask
from .metrics import (
    bound_metrics,
    constraint_metrics,
    decline_and_basis_report,
    point_metrics,
    probabilistic_metrics,
)
from .recover import MaskedSystem, mask_and_solve
from .regimes import REGIME_SPECS, rolling_origin_frames, rolling_origins, select_targets
from .scoreboard import assert_scored_cells_are_primary_like, build_scoreboard


@dataclass(frozen=True)
class ValidationResult:
    """§16.2's return: the scored rows, the metric rows, the scoreboard, and the manifest."""

    scores: pl.DataFrame
    metrics: pl.DataFrame
    scoreboard: pl.DataFrame
    manifest: dict[str, object]


def run_pseudo_suppression(
    data: HarmonizedData,
    estimators: Sequence[Estimator] = REGISTRY,
    config: Config | None = None,
) -> ValidationResult:
    """Every enabled regime, every seed. Refuses rather than skipping.

    `config` is keyword-optional only so the §16.2 argument ORDER survives; it is required in
    fact. A bare `assert` would vanish under `python -O`, and this package raises typed errors for
    caller mistakes everywhere else.
    """
    if config is None:
        raise ConceptViolationError(
            "run_pseudo_suppression requires a Config: the harness needs `config.constraints` for "
            "solve_bounds and the full object for run_baselines"
        )
    all_scores: list[pl.DataFrame] = []
    all_metrics: list[pl.DataFrame] = []
    regimes: dict[str, dict[str, object]] = {}

    for name, spec in REGIME_SPECS.items():
        entry: dict[str, object] = {
            "disposition": spec.disposition,
            "grain": spec.grain,
            "n_scored": 0,
            "replicates": 0,
            "hashes": [],
            "estimators": [e.estimator_id for e in estimators],
        }
        # THE SWITCH IS CHECKED FIRST, AND THE FAIL-CLOSED REFUSAL SECOND. Order matters: an
        # operator who turns `include_vintage_comparison` ON is ASKING for a regime this window
        # cannot support, and must get a refusal rather than a config-derived note. With the
        # switch OFF the ask was never made, so the note is the honest record.
        switch = REGIME_SWITCHES.get(name)
        if switch is not None and not getattr(config.validation, switch):
            # EXCLUDED, NOT ABSENT (R-S4C-12). A regime that vanished from the manifest when its
            # switch went off would leave a reader unable to tell it from a regime that never
            # existed, which is the empty-partition-as-success this stage refuses everywhere else.
            # The declared reason rides along: the switch says why it did not run HERE, and the
            # declared reason says why it could not have anyway.
            entry["reason"] = (
                f"excluded by `validation.{switch}: false`; its declared reason is "
                f"{spec.no_score_reason or 'none — this regime masks QCEW cells and would score'}"
            )
            regimes[name] = entry
            continue

        if spec.disposition == "cannot_run_on_d1":
            # FAIL CLOSED when the operator asks for a regime the data cannot support. Appendix A
            # ships `include_vintage_comparison: true`; this package defaults it false because no
            # period in any staged table carries a second snapshot. Reaching here means the switch
            # is ON, so this must RAISE — `select_targets` owns that refusal — rather than record a
            # disposition and move on, which would hand back an empty partition reading as
            # "scored, nothing wrong".
            select_targets(name, data.qcew_monthly, seed=0, config=config)

        # A `feasible` regime that scores nothing MUST say why, in ITS OWN words. The reason used
        # to be templated on `{name}` across every selectorless regime, which asserted of both that
        # the regime "is exercised through its own entry point in `validate.regimes`" — true for
        # `rolling_origin`, false for `cbp_size_gaps`, whose entry points have no caller and no
        # test. The false version shipped in `runs/f03023ac9f3a/validation_manifest.json`. The
        # reason now comes from `RegimeSpec.no_score_reason`, which is PROVABLY non-None here:
        # `__post_init__` ties `select is None` to a non-`qcew_mask` mechanism and every one of
        # those must declare a reason. Do not add an `or "..."` fallback — that fallback would be
        # a shared template, which is the defect this replaced.
        if spec.select is None:
            if spec.mechanism == "frame_truncation":
                # §13.4 bullet 3, ON THE LIVE PATH. Measured 2026-09-08, `assert_no_future_rows`
                # had zero callers in `src/` and ran only inside two test modules, so Stage 4's
                # exit criterion "a rolling-origin run provably contains no future-period rows"
                # was discharged by nothing a run executes. The origins are recorded because a
                # guard that ran nowhere and a guard that ran everywhere both report success.
                origins = rolling_origins(data.qcew_monthly, config=config)
                for origin, frame in rolling_origin_frames(data.qcew_monthly, origins=origins):
                    assert_no_future_rows(frame, origin=origin)
                entry["origins_checked"] = list(origins)
            entry["reason"] = spec.no_score_reason
            regimes[name] = entry
            continue

        for replicate, seed in enumerate(config.validation.pseudo_suppression_seeds):
            targets = select_targets(name, data.qcew_monthly, seed=seed, config=config)
            if not targets:
                continue
            masked, truth = apply_mask(data, targets)
            assert_no_retained_truth(masked, truth)
            system = mask_and_solve(data, targets, config)
            results, _audit = run_baselines(masked, config, estimators=estimators)
            scored = _join_truth(
                results, truth, system, targets, regime=name, seed=seed, replicate=replicate
            )
            assert_declared_provenance(scored)
            # §13.10 gates "on primary-like masks" and nothing downstream carries the label to
            # scope by, so this is the only place the guarantee can be made. See the function.
            assert_scored_cells_are_primary_like(scored)
            all_scores.append(scored)
            all_metrics.append(point_metrics(scored, regime=name, seed=seed, arm="state_total"))
            all_metrics.append(bound_metrics(scored, regime=name, seed=seed, arm="state_total"))
            all_metrics.append(decline_and_basis_report(scored, regime=name, seed=seed))
            all_metrics.append(
                probabilistic_metrics(scored, regime=name, seed=seed, arm="state_total")
            )
            all_metrics.append(
                constraint_metrics(
                    scored,
                    # Computed over the FULL result frame, not over `scored`. The adding-up
                    # identity is a property of the month's whole missing set; `scored` is the
                    # masked subset of it, so summing there compares a part against the whole.
                    # Measured on one small-cell replicate: 4134.4 / 2833.2 employees of apparent
                    # violation against a true 4.5e-13.
                    _anchor_residuals(results),
                    regime=name,
                    seed=seed,
                    arm="state_total",
                )
            )
            entry["replicates"] = int(entry["replicates"]) + 1
            entry["n_scored"] = int(entry["n_scored"]) + scored.height
            entry["hashes"].append(system.constraint_set_hash)
        if entry["replicates"] == 0 and "reason" not in entry:
            entry["reason"] = (
                f"{name}'s selector returned no eligible target for any configured seed; "
                "the panel carries no population matching this design on this window"
            )
        regimes[name] = entry

    manifest: dict[str, object] = {"regimes": regimes}
    scores = pl.concat(all_scores, how="vertical") if all_scores else pl.DataFrame()
    metrics = pl.concat(all_metrics, how="diagonal") if all_metrics else pl.DataFrame()
    board = build_scoreboard(metrics) if metrics.height else pl.DataFrame()
    return ValidationResult(scores, metrics, board, manifest)


def _join_truth(
    results: pl.DataFrame,
    truth: pl.DataFrame,
    system: MaskedSystem,
    targets: Sequence[MaskTarget],
    *,
    regime: str,
    seed: int,
    replicate: int,
) -> pl.DataFrame:
    """Attach truth, masked bounds, the INV-009 label, the MASKED hash and the mask's own shape.

    The bounds come from `system`, never from the run directory's shipped
    `deterministic_bounds.parquet` — that table still carries the published value for a masked
    cell, so joining it would hand the harness the answer.

    The truth join is INNER on purpose: it drops every cell the mask did not hide, so a scored row
    that was never masked is impossible by construction rather than by assertion. The `arms` and
    `lookback` joins are INNER for the same reason — every surviving row was a target, so a null
    `mask_arm` is unconstructible rather than merely unexpected. Neither can fan out: `apply_mask`
    refuses a duplicated target, so `arms` is one row per (state, month) and `lookback` one per
    state.

    `lookback_months_masked` is the count of months THIS replicate masked for the row's state, not
    `config.validation.minimum_unmasked_lookback_months`. The global floor would write the same
    value on every row of every regime, which records nothing; the per-state count separates a
    twelve-month blackout from a single-month draw, which is the distinction §13.3's grain exists
    to make.
    """
    labelled = truth.select("state_fips", "reference_month", "truth", "suppression_type")
    bounds = system.bounds.select("cell_id", "selected_lower", "selected_upper", "bound_status")
    arms = pl.DataFrame(
        {
            "state_fips": [target.state_fips for target in targets],
            "reference_month": [target.reference_month for target in targets],
            "mask_arm": [target.arm for target in targets],
        },
        schema={"state_fips": pl.String, "reference_month": pl.String, "mask_arm": pl.String},
    )
    masked_months: dict[str, int] = {}
    for target in targets:
        masked_months[target.state_fips] = masked_months.get(target.state_fips, 0) + 1
    lookback = pl.DataFrame(
        {
            "state_fips": list(masked_months),
            "lookback_months_masked": list(masked_months.values()),
        },
        schema={"state_fips": pl.String, "lookback_months_masked": pl.Int64},
    )
    return (
        results.join(labelled, on=["state_fips", "reference_month"], how="inner")
        .join(bounds, on="cell_id", how="left")
        .join(arms, on=["state_fips", "reference_month"], how="inner")
        .join(lookback, on="state_fips", how="inner")
        .with_columns(
            pl.lit(regime).alias("regime"),
            # DTYPE DECLARED, not inferred: `pl.lit(1024)` is Int32 on polars 1.44 while the
            # metrics frame builds Int64 from Python dicts, so the two frames disagreed on `seed`
            # and `validate_frame` would have raised on dtype even after the column sets matched.
            pl.lit(seed, dtype=pl.Int64).alias("seed"),
            pl.lit(replicate, dtype=pl.Int64).alias("replicate"),
            pl.lit(system.constraint_set_hash).alias("masked_constraint_set_hash"),
            pl.col("truth").cast(pl.Float64),
        )
    )


def _mask_arm(targets: Sequence[MaskTarget]) -> str:
    """The single INV-009 arm this replicate masked, or a refusal if it masked two.

    `MaskTarget.arm` was read by nothing anywhere in the package while every metric emit site
    passed the literal `"state_total"`; this is its first consumer, so the field stops being
    decorative. The scores frame carries the arm PER ROW and the metric emitters take one SCALAR
    per (regime, seed), so a replicate spanning two arms would label every metric row with one of
    them. `scoreboard._best` already refuses a two-arm regime downstream; refusing here names the
    replicate that produced it rather than the board that inherited it.
    """
    arms = sorted({target.arm for target in targets})
    if len(arms) != 1:
        raise ConceptViolationError(
            f"this replicate masked {len(arms)} mask arms ({', '.join(arms) or 'none'}); the "
            "metric emitters take one arm per (regime, seed), and pooling a state-total metric "
            "with a national-size one under a single label is the ambiguity §13.10 refuses"
        )
    return arms[0]


def _anchor_residuals(results: pl.DataFrame) -> pl.DataFrame:
    """Per-estimator adding-up residual, kept OUTSIDE the constraint norms (INV-004/INV-005).

    Takes the FULL `run_baselines` frame, never the truth-joined subset. Every estimate in a month
    sums to that month's residual across the WHOLE missing set; the masked cells are a part of it,
    and summing the part against the whole reports a violation of thousands of employees where the
    real figure is machine epsilon.
    """
    return (
        results.filter(pl.col("estimate").is_not_null())
        .group_by("estimator_id", "reference_month")
        .agg((pl.col("estimate").sum() - pl.col("residual").first()).abs().alias("residual_abs"))
        .group_by("estimator_id")
        .agg(pl.col("residual_abs").max())
    )
