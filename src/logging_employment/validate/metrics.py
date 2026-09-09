"""§13.5-13.8's metric families, each carrying the denominator it was computed over.

Read the vacuity note before trusting a §13.5 number. On the `state_total` arm every masked cell is
`unbounded` with `selected_upper = null`, so a truth-in-bound rate of 1.0 means "[0, +inf) contains
the truth", not "the bounds were informative". `bound_cells_finite_upper` is what separates the
two, and it is on every row for that reason.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from .intervals import clip_at_zero, crps, empirical_interval, residual_ensemble


def bound_metrics(scores: pl.DataFrame, *, regime: str, seed: int, arm: str) -> pl.DataFrame:
    """§13.5's five metrics, per estimator, with vacuity made visible."""
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        finite = group.filter(pl.col("selected_upper").is_not_null())
        n_finite = finite.height

        contained = group.filter(
            (pl.col("selected_lower") <= pl.col("truth"))
            & (pl.col("selected_upper").is_null() | (pl.col("truth") <= pl.col("selected_upper")))
        ).height
        exact = group.filter(pl.col("bound_status") == "exactly_recoverable").height
        width = (finite["selected_upper"] - finite["selected_lower"]).mean() if n_finite else None

        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": str(estimator),
            "metric_family": "deterministic_bounds",
            "denominator": float(group.height),
            "denominator_basis": "masked_cells",
            "n_scored": group.height,
            "bound_cells_finite_upper": n_finite,
        }
        rows.append(
            {
                **base,
                "metric_name": "truth_in_bound_rate",
                "value": contained / group.height if group.height else None,
            }
        )
        rows.append(
            {
                **base,
                "metric_name": "exact_recovery_rate",
                "value": exact / group.height if group.height else None,
            }
        )
        # None, never inf and never 0: an unbounded cell has no width to average.
        rows.append({**base, "metric_name": "mean_feasible_width", "value": width})
    return pl.DataFrame(rows)


_POINT_NAMES = ("mae", "rmse", "bias", "wape", "median_ape")


def point_metrics(scores: pl.DataFrame, *, regime: str, seed: int, arm: str) -> pl.DataFrame:
    """§13.6's point metrics over the SCORED rows, with the declined rows counted beside them.

    The denominator is masked cell-rows; the numerator is rows carrying an estimate. Reporting only
    the numerator is the failure §13.8's closing paragraph names: a method that declines its hard
    months looks better than one that attempts them.
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        scored = group.filter(pl.col("estimate").is_not_null())
        counts = {
            kind: group.filter(pl.col("decline_kind") == kind).height
            for kind in ("by_design", "data_gap", "reconciliation_failure")
        }
        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": str(estimator),
            "metric_family": "point",
            "denominator": float(group.height),
            "denominator_basis": "masked_cell_rows",
            "n_scored": scored.height,
            "n_declined_by_design": counts["by_design"],
            "n_declined_data_gap": counts["data_gap"],
            "n_declined_reconciliation_failure": counts["reconciliation_failure"],
        }
        if scored.height == 0:
            # Null, never 0.0. A zero error over zero rows reads as perfect accuracy.
            rows.extend({**base, "metric_name": n, "value": None} for n in _POINT_NAMES)
            continue

        err = scored["estimate"] - scored["truth"]
        abs_err = err.abs()
        values = {
            "mae": abs_err.mean(),
            "rmse": float((err**2).mean() ** 0.5),
            "bias": err.mean(),
            "wape": (
                float(abs_err.sum() / scored["truth"].abs().sum())
                if scored["truth"].abs().sum()
                else None
            ),
            "median_ape": (
                float((abs_err / scored["truth"].abs()).median())
                if scored.filter(pl.col("truth").abs() > 0).height == scored.height
                else None
            ),
        }
        rows.extend({**base, "metric_name": n, "value": values[n]} for n in _POINT_NAMES)
    return pl.DataFrame(rows)


_LEVELS = (0.50, 0.80, 0.90, 0.95)
# §10.7 names exactly three families that SHOULD carry intervals. Everything else is point-only,
# and says so in `interval_source` rather than being silently absent from the coverage table.
_INTERVAL_FAMILIES = ("share_", "cbp_intensity", "constrained_regression")


def probabilistic_metrics(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.7's coverage, width and CRPS from §10.7's residual-shifted ensembles."""
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        name = str(estimator)
        eligible = any(name.startswith(f) or name == f for f in _INTERVAL_FAMILIES)
        scored = group.filter(pl.col("estimate").is_not_null())
        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": name,
            "metric_family": "probabilistic",
            "denominator": float(group.height),
            "denominator_basis": "masked_cell_rows",
            "n_scored": scored.height,
        }
        if not eligible or scored.height < 2:
            rows.append(
                {
                    **base,
                    "metric_name": "coverage_0.90",
                    "value": None,
                    "interval_source": "none",
                    "calibration_sample_size": 0,
                }
            )
            continue

        residual_pool = (scored["estimate"] - scored["truth"]).to_numpy()
        covered = {level: 0 for level in _LEVELS}
        widths: list[float] = []
        crps_values: list[float] = []
        clipped_total = 0
        for position, row in enumerate(scored.iter_rows(named=True)):
            # LEAVE-ONE-OUT BY POSITION, not by value. A residual computed on this cell IS the
            # withheld truth (§13.4), so it must go; excluding by float equality would also drop
            # every OTHER cell that happens to share the same residual, silently shrinking the
            # calibration sample.
            others = np.delete(residual_pool, position)
            if others.size < 2:
                continue
            ensemble, n_clipped = clip_at_zero(residual_ensemble(others, row["estimate"]))
            clipped_total += n_clipped
            for level in _LEVELS:
                lo, hi = empirical_interval(ensemble, level)
                if lo <= row["truth"] <= hi:
                    covered[level] += 1
                if level == 0.90:
                    widths.append(hi - lo)
            crps_values.append(crps(ensemble, row["truth"]))

        n = len(crps_values)
        common = {
            **base,
            "interval_source": "rolling_residual_ensemble",
            "calibration_sample_size": n,
        }
        for level in _LEVELS:
            rows.append(
                {
                    **common,
                    "metric_name": f"coverage_{level:.2f}",
                    "value": covered[level] / n if n else None,
                }
            )
        rows.append(
            {
                **common,
                "metric_name": "mean_interval_width_0.90",
                "value": float(np.mean(widths)) if widths else None,
            }
        )
        rows.append(
            {**common, "metric_name": "crps", "value": float(np.mean(crps_values)) if n else None}
        )
        # The clip is REPORTED, not absorbed: it shifts nominal coverage.
        rows.append({**common, "metric_name": "n_clipped_at_zero", "value": float(clipped_total)})
    return pl.DataFrame(rows)


def decline_and_basis_report(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.8's R-COMP-10 report: decline counts by kind AND weight basis, per method per regime.

    The weight-basis half is not redundant. Plan 10's `BreakAdjustedShare` refusals reuse the
    `None` path, so the cell is COMPOSED onto the §10.2 fallback rather than declined: it carries
    `weight_basis = 'establishment_fallback'` and NO `decline_kind`. A report built from decline
    counts alone therefore shows §10.3 variant 5 as fully covered. Measured on D1,
    `share_break_adjusted` is 226 own / 1,001 fallback against its three siblings' 327/900.

    `arm` matches the four sibling emitters. Without it this family wrote a NULL `mask_arm` on
    every row it produced — 70 of 70 on the committed fixture, 270 of 270 on D1, against zero nulls
    in each of the other four families — and that null was persisted in `validation_metrics`
    without ever failing `validate_frame`. The damage stops at that table: `build_scoreboard`'s
    `basis` frame selects only (`regime`, `seed`, `estimator_id`, `n_own_estimator`,
    `n_establishment_fallback`) and drops `mask_arm` before the join, so the board takes its
    `mask_arm` from the point rows alone, where it is non-null on all 350 of them. (1,168 is the
    whole golden table, on which `mask_arm` IS null 70 times — those 70 are exactly this family's
    rows, which is the defect, not a counterexample to it.)
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        rows.append(
            {
                "regime": regime,
                "seed": seed,
                "mask_arm": arm,
                "estimator_id": str(estimator),
                "metric_family": "declines",
                "denominator": float(group.height),
                "denominator_basis": "masked_cell_rows",
                "n_scored": group.filter(pl.col("estimate").is_not_null()).height,
                "n_declined_by_design": group.filter(pl.col("decline_kind") == "by_design").height,
                "n_declined_data_gap": group.filter(pl.col("decline_kind") == "data_gap").height,
                "n_declined_reconciliation_failure": group.filter(
                    pl.col("decline_kind") == "reconciliation_failure"
                ).height,
                "n_own_estimator": group.filter(pl.col("weight_basis") == "own_estimator").height,
                "n_establishment_fallback": group.filter(
                    pl.col("weight_basis") == "establishment_fallback"
                ).height,
            }
        )
    return pl.DataFrame(rows)


def constraint_metrics(
    scores: pl.DataFrame, anchor_residuals: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.8's residual norms and violation counts.

    Two rules that are silent when broken. (1) An empty row set yields NULL, never 0.0 — a norm of
    zero over zero rows reads as a perfect pass, so `constraint_rows_scored` rides alongside.
    (2) The anchor's adding-up residual is its OWN column, outside the norms: the anchor is a
    `modeling_assumption` and never a constraint row (INV-004/INV-005), so folding it in would
    report a modelling choice as a constraint violation.
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        scored = group.filter(pl.col("estimate").is_not_null())
        n = scored.height
        negatives = scored.filter(pl.col("estimate") < 0).height
        integer_violations = scored.filter(
            pl.col("estimate_integer").is_not_null()
            & ((pl.col("estimate_integer") - pl.col("estimate")).abs() > 1.0)
        ).height
        anchor = anchor_residuals.filter(pl.col("estimator_id") == estimator)
        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": str(estimator),
            "metric_family": "constraint",
            "denominator": float(group.height),
            "denominator_basis": "masked_cell_rows",
            "n_scored": n,
            "constraint_rows_scored": n,
        }
        rows.append({**base, "metric_name": "negative_outputs", "value": float(negatives)})
        rows.append(
            {**base, "metric_name": "integerization_violations", "value": float(integer_violations)}
        )
        rows.append(
            {
                **base,
                "metric_name": "anchor_adding_up_max_abs",
                "value": float(anchor["residual_abs"].max()) if anchor.height else None,
            }
        )
    return pl.DataFrame(rows)
