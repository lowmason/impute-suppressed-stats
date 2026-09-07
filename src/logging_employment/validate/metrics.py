"""§13.5-13.8's metric families, each carrying the denominator it was computed over.

Read the vacuity note before trusting a §13.5 number. On the `state_total` arm every masked cell is
`unbounded` with `selected_upper = null`, so a truth-in-bound rate of 1.0 means "[0, +inf) contains
the truth", not "the bounds were informative". `bound_cells_finite_upper` is what separates the
two, and it is on every row for that reason.
"""

from __future__ import annotations

import polars as pl


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
