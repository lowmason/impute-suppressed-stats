"""§16.2's `run_pseudo_suppression`.

Cost: one replicate is ~30 s, essentially all of it `run_baselines` (the mask-and-solve arm is
~0.36 s). 13 regimes x 20 replicates is ~2.2 hours at the full registry, which is why
`run_baselines` takes an estimator subset and why regimes declare the estimators they need.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..baselines.interfaces import Estimator
from ..baselines.runner import REGISTRY, run_baselines
from ..config import Config
from ..contracts import HarmonizedData, assert_declared_provenance
from ..errors import ConceptViolationError
from .leakage import assert_no_retained_truth
from .mask import apply_mask
from .metrics import (
    bound_metrics,
    constraint_metrics,
    decline_and_basis_report,
    point_metrics,
    probabilistic_metrics,
)
from .recover import MaskedSystem, mask_and_solve
from .regimes import REGIME_SPECS, select_targets
from .scoreboard import build_scoreboard


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
        if spec.disposition != "feasible":
            # FAIL CLOSED when the operator asks for a regime the data cannot support. Appendix A
            # ships `include_vintage_comparison: true`; this package defaults it false because no
            # period in any staged table carries a second snapshot. Turning it back on must RAISE
            # — `select_targets` owns that refusal — rather than record a disposition and move on,
            # which would hand back an empty partition reading as "scored, nothing wrong".
            if (
                spec.disposition == "cannot_run_on_d1"
                and config.validation.include_vintage_comparison
            ):
                select_targets(name, data.qcew_monthly, seed=0, config=config)
            entry["reason"] = (
                "no second snapshot in any staged table"
                if spec.disposition == "cannot_run_on_d1"
                else "no smoothing estimator in the §10 registry"
            )
            regimes[name] = entry
            continue

        # A `feasible` regime that scores nothing MUST say why. Two of the thirteen do not mask
        # QCEW cells at all: `rolling_origin` TRUNCATES the frame (`regimes.rolling_origin_frames`)
        # and `cbp_size_gaps` drops CBP state-years (`regimes.apply_cbp_gap`), so neither produces
        # a `MaskTarget` and neither reaches this loop. Without this note the manifest reads
        # `feasible, scored=0` with no explanation — the empty partition that reads as "scored,
        # nothing wrong", which this stage refuses everywhere else.
        if spec.select is None:
            entry["reason"] = (
                f"{name} does not mask QCEW cells and so produces no MaskTarget; it is exercised "
                "through its own entry point in `validate.regimes`, not through this scoring loop. "
                "Wiring it into the loop is a deferred item."
            )
            regimes[name] = entry
            continue

        for seed in config.validation.pseudo_suppression_seeds:
            targets = select_targets(name, data.qcew_monthly, seed=seed, config=config)
            if not targets:
                continue
            masked, truth = apply_mask(data, targets)
            assert_no_retained_truth(masked, truth)
            system = mask_and_solve(data, targets, config)
            results, _audit = run_baselines(masked, config, estimators=estimators)
            scored = _join_truth(results, truth, system, regime=name, seed=seed)
            assert_declared_provenance(scored)
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
    *,
    regime: str,
    seed: int,
) -> pl.DataFrame:
    """Attach truth, masked bounds, the INV-009 label, and the MASKED hash to the estimator rows.

    The bounds come from `system`, never from the run directory's shipped
    `deterministic_bounds.parquet` — that table still carries the published value for a masked
    cell, so joining it would hand the harness the answer.

    The truth join is INNER on purpose: it drops every cell the mask did not hide, so a scored row
    that was never masked is impossible by construction rather than by assertion.
    """
    labelled = truth.select("state_fips", "reference_month", "truth", "suppression_type")
    bounds = system.bounds.select("cell_id", "selected_lower", "selected_upper", "bound_status")
    return (
        results.join(labelled, on=["state_fips", "reference_month"], how="inner")
        .join(bounds, on="cell_id", how="left")
        .with_columns(
            pl.lit(regime).alias("regime"),
            pl.lit(seed).alias("seed"),
            pl.lit(system.constraint_set_hash).alias("masked_constraint_set_hash"),
            pl.col("truth").cast(pl.Float64),
        )
    )


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
