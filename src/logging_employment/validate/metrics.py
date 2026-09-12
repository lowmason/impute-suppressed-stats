"""§13.5-13.8's metric families, each carrying the denominator it was computed over.

Read the vacuity note before trusting a §13.5 number. On the `state_total` arm every masked cell is
`unbounded` with `selected_upper = null`, so a truth-in-bound rate of 1.0 means "[0, +inf) contains
the truth", not "the bounds were informative". `bound_cells_finite_upper` is what separates the
two, and it is on every row for that reason.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from ..errors import ConceptViolationError
from .intervals import clip_at_zero, crps, empirical_interval, residual_ensemble
from .regimes import DIVISION_OF

# The sentinel pair an unstratified row carries. A VALUE, never a null -- see `STRATUM_KINDS`.
_OVERALL: dict[str, object] = {"stratum_kind": "overall", "stratum_value": "all"}


def with_census_division(scores: pl.DataFrame) -> pl.DataFrame:
    """Attach §13.10's stratum to each scored row, refusing a FIPS the partition does not cover.

    Fail-closed rather than an `unassigned` bucket: `DIVISION_OF` covers states+DC exactly
    (measured, 51 of 51 against `constants.STATES_DC_FIPS`), so an uncovered value means a
    territory or a malformed code reached the scoring frame -- the REQ-002 universe violation
    `harmonize/universe.py` exists to prevent, not a stratum that needs a home. Bucketing it would
    put a row §13.10 must not gate on into a stratum §13.10 gates on.

    Called for the `state_total` arm ONLY. A `national_size` cell carries `state_fips = "US"`, for
    which no division exists, so both emitters skip stratification on that arm rather than route a
    legal national row into this refusal.
    """
    out = scores.with_columns(
        pl.col("state_fips").replace_strict(DIVISION_OF, default=None).alias("census_division")
    )
    uncovered = out.filter(pl.col("census_division").is_null())["state_fips"].to_list()
    # Stringified before sorting: a null FIPS beside a real one would otherwise make `sorted` raise
    # TypeError and hide the named refusal behind a crash.
    unknown = sorted({"null" if v is None else str(v) for v in uncovered})
    if unknown:
        raise ConceptViolationError(
            f"state_fips {unknown} falls in no Census division; the partition is "
            f"validate/regimes.py::CENSUS_DIVISIONS and covers states+DC only"
        )
    return out


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
            **_OVERALL,
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


_POINT_NAMES = ("mae", "rmse", "bias", "wape", "median_ape", "state_share_absolute_error")


def national_monthly_totals(monthly: pl.DataFrame) -> pl.DataFrame:
    """The published national employment level per month, as `state_share_absolute_error`'s base.

    Derived from the MASKED frame by its only caller, not from the unmasked one. The two agree --
    every mask this harness applies hides a state cell and leaves the national row alone -- so the
    choice buys no different number; it buys a §13.4 leakage argument that is structural instead of
    verbal. A denominator read out of the unmasked frame would have to be argued safe; one read out
    of a frame `assert_no_retained_truth` has already cleared cannot carry withheld truth at all.

    This is NOT `SRC-QCEW-006`'s declined national/state identity. That decline forbids a hard
    CONSTRAINT ROW equating the national level to the state sum, and
    `constraints/rows.py::assert_no_national_employment_margin` still enforces it. A metric
    denominator asserts no identity and enters no constraint system: it rescales an error that was
    already computed, so §9.3's prohibition is untouched.
    """
    return (
        monthly.filter(pl.col("area_type") == "national")
        .select("reference_month", pl.col("employment_value").cast(pl.Float64))
        .rename({"employment_value": "national_employment"})
    )


def _state_share_absolute_error(scored: pl.DataFrame) -> float | None:
    """§13.6's state-share absolute error: mean |estimate - truth| / national employment.

    PER MONTH, not pooled. The share is of the month the cell belongs to, so a 2017 error and a
    2024 error are made comparable before they are averaged; dividing the pooled absolute error by
    a pooled national total instead would weight each month by its own size, which is what `mae`
    and `wape` already do. Stated because the metric is otherwise easy to read as a rescaled MAE:
    it is a rescaled MAE only on a window whose national level is constant, and D1's is not.

    A cell whose month carries no national row is EXCLUDED, and an all-excluded set yields None --
    the module's "Null, never 0.0" rule. Measured 2026-09-11 on `data/staged/qcew_monthly.parquet`,
    all 96 national rows are `observed` with a non-null `employment_value`, so no cell is dropped
    on D1; the branch guards a revision, not today's data.
    """
    usable = scored.filter(
        pl.col("national_employment").is_not_null() & (pl.col("national_employment") > 0)
    )
    if usable.is_empty():
        return None
    errors = (usable["estimate"] - usable["truth"]).abs() / usable["national_employment"]
    return float(errors.mean())


def point_metrics(
    scores: pl.DataFrame,
    *,
    regime: str,
    seed: int,
    arm: str,
    national_totals: pl.DataFrame,
) -> pl.DataFrame:
    """§13.6's point metrics over the SCORED rows, with the declined rows counted beside them.

    The denominator is masked cell-rows; the numerator is rows carrying an estimate. Reporting only
    the numerator is the failure §13.8's closing paragraph names: a method that declines its hard
    months looks better than one that attempts them.

    `national_totals` is REQUIRED rather than defaulted to None (R-S5G-4). §13.6 lists state-share
    absolute error "at minimum", so an overload that silently emits it as null whenever a caller
    forgets the argument would reinstate the absence this requirement exists to close -- and it
    would do so on the artifact, where nothing downstream can tell "no denominator" from "no
    error". `national_monthly_totals` builds the frame.
    """
    rows: list[dict[str, object]] = []
    joined = scores.join(national_totals, on="reference_month", how="left")
    # Stratified on the STATE arm only -- see `with_census_division`. A division WAPE over national
    # size-class cells would mean nothing.
    stratify = arm == "state_total"
    if stratify:
        joined = with_census_division(joined)
    for (estimator,), group in joined.group_by("estimator_id", maintain_order=True):
        rows.extend(
            _point_rows(
                group, base=_base(regime, seed, arm, str(estimator)), names=_POINT_NAMES, **_OVERALL
            )
        )
        # §13.10's per-stratum gate needs WAPE and nothing else, so only WAPE is stratified
        # (R-S5G-1). Emitting all six per division would multiply the table by the partition for
        # five metrics no gate reads. The divisions PRESENT are enumerated, never the nine: a
        # division this replicate did not mask has no rows, and a zero-row WAPE of null would be
        # indistinguishable from a division that scored and failed.
        divisions = sorted(set(group["census_division"].to_list())) if stratify else []
        for division in divisions:
            rows.extend(
                _point_rows(
                    group.filter(pl.col("census_division") == division),
                    base=_base(regime, seed, arm, str(estimator)),
                    names=("wape",),
                    stratum_kind="census_division",
                    stratum_value=division,
                )
            )
    return pl.DataFrame(rows)


def _base(regime: str, seed: int, arm: str, estimator: str) -> dict[str, object]:
    """The identifying half of a point row, shared by the overall and the stratified emissions."""
    return {
        "regime": regime,
        "seed": seed,
        "mask_arm": arm,
        "estimator_id": estimator,
        "metric_family": "point",
    }


def _point_rows(
    group: pl.DataFrame,
    *,
    base: dict[str, object],
    names: tuple[str, ...],
    stratum_kind: str,
    stratum_value: str,
) -> list[dict[str, object]]:
    """`names` computed over `group`, which is a whole estimator's rows or one stratum's.

    EVERY row carries the denominator of the set it was computed over, stratified or not (R-COMP-10
    and §13.10's "no major stratum degrades by more than 2% WAPE"). A stratified WAPE reported
    against the pooled denominator would make a two-cell division and a two-hundred-cell division
    read as equally solid evidence for failing a promotion.
    """
    scored = group.filter(pl.col("estimate").is_not_null())
    counts = {
        kind: group.filter(pl.col("decline_kind") == kind).height
        for kind in ("by_design", "data_gap", "reconciliation_failure")
    }
    row = {
        **base,
        "stratum_kind": stratum_kind,
        "stratum_value": stratum_value,
        "denominator": float(group.height),
        "denominator_basis": "masked_cell_rows",
        "n_scored": scored.height,
        "n_declined_by_design": counts["by_design"],
        "n_declined_data_gap": counts["data_gap"],
        "n_declined_reconciliation_failure": counts["reconciliation_failure"],
    }
    if scored.height == 0:
        # Null, never 0.0. A zero error over zero rows reads as perfect accuracy.
        return [{**row, "metric_name": n, "value": None} for n in names]

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
        "state_share_absolute_error": _state_share_absolute_error(scored),
    }
    return [{**row, "metric_name": n, "value": values[n]} for n in names]


_LEVELS = (0.50, 0.80, 0.90, 0.95)
# §10.7 names exactly three families that SHOULD carry intervals. Everything else is point-only,
# and says so in `interval_source` rather than being silently absent from the coverage table.
_INTERVAL_FAMILIES = ("share_", "cbp_intensity", "constrained_regression")


def probabilistic_metrics(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.7's coverage, width and CRPS from §10.7's residual-shifted ensembles."""
    rows: list[dict[str, object]] = []
    # State arm only, for the reason `with_census_division` gives.
    stratify = arm == "state_total"
    frame = with_census_division(scores) if stratify else scores
    for (estimator,), group in frame.group_by("estimator_id", maintain_order=True):
        name = str(estimator)
        eligible = any(name.startswith(f) or name == f for f in _INTERVAL_FAMILIES)
        scored = group.filter(pl.col("estimate").is_not_null())
        by_division: dict[str, list[int]] = {}
        base = {
            **_OVERALL,
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
                hit = lo <= row["truth"] <= hi
                if hit:
                    covered[level] += 1
                if level == 0.90:
                    widths.append(hi - lo)
                    # BUCKETED HERE, not recomputed in a second pass (R-S5G-1). The ensemble is
                    # the harness's dominant cost and is superlinear in scored cells, so a
                    # per-division pass would multiply the expensive half by the partition to
                    # learn something this loop already knows. The CALIBRATION POOL stays global:
                    # leave-one-out over every scored residual, never over the division's alone.
                    # Stratifying the pool would shrink each sample to a handful of cells and
                    # report the resulting noise as miscalibration.
                    if stratify:
                        tally = by_division.setdefault(row["census_division"], [0, 0])
                        tally[0] += 1
                        tally[1] += int(hit)
            crps_values.append(crps(ensemble, row["truth"]))

        n = len(crps_values)
        common = {
            **base,
            "interval_source": "leave_one_out_residual_ensemble",
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
        # EVERY division this estimator has masked cells in gets a row -- the same set `point_metrics`
        # emits WAPE for -- so §13.10's two stratum inputs agree on which strata exist. A division
        # whose masked cells all declined, or whose scored cells never reached a leave-one-out
        # ensemble, has `seen == 0` and a NULL value, never 0.0. Each row carries ITS division's base:
        # masked rows as `denominator`, scored rows as `n_scored`, ensembled rows as
        # `calibration_sample_size`. Inheriting the estimator-wide `n_scored` from `common` would
        # report more scored cells than the division has masked cells, an impossible state.
        divisions = sorted(set(group["census_division"].to_list())) if stratify else []
        for division in divisions:
            in_division = group.filter(pl.col("census_division") == division)
            seen, hits = by_division.get(division, (0, 0))
            rows.append(
                {
                    **common,
                    "stratum_kind": "census_division",
                    "stratum_value": division,
                    "metric_name": "coverage_0.90",
                    "value": hits / seen if seen else None,
                    "denominator": float(in_division.height),
                    "n_scored": in_division.filter(pl.col("estimate").is_not_null()).height,
                    "calibration_sample_size": seen,
                }
            )
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
    whole golden table, on which `mask_arm` WAS null 70 times before this parameter existed — those
    70 were exactly this family's rows, which is the defect, not a counterexample to it. The
    committed golden was regenerated when `arm` landed and now has zero nulls; the diff was
    inspected first and `mask_arm` was the only column that moved.)
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        rows.append(
            {
                **_OVERALL,
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
            **_OVERALL,
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
