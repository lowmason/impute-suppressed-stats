"""§10.4: the preferred transparent structural baseline.

"For each state-year, estimate a robust March employee-per-establishment intensity from CBP, shrink
it toward regional/national values, combine it with QCEW establishment exposure, and reconcile to
the national residual." §10.8's rung 1, and the roadmap's preferred-baseline slot that Stage 4
fills with numbers -- so its coverage holes are load-bearing, not incidental.

WHAT CBP DOES AND DOES NOT COVER ON THIS WINDOW, MEASURED.
- 2017-2023 only. Reference year 2024 has no CBP vintage at all, so the 12 months of 2024
  DECLINE. Carrying the 2023 March intensity forward would be an invention: the entire content of
  §10.4 is a year-specific March intensity, so a carried-forward value is not a weaker version of
  this baseline, it is a different one wearing its name.
- Hawaii ('15') and Rhode Island ('44') have no row in any published year, and take the declared
  establishment fallback rather than emptying the baseline.
- Rows carrying a null employment under CBP suppression are dropped, never read as zero (INV-003).

CBP IS A MEASUREMENT, NOT A CONSTRAINT. SRC-CBP-004 enters CBP employment as an
`empirical_measurement` with `is_hard = false`, and §9.3 keeps it out of the deterministic feasible
set. Nothing here builds a constraint row. CBP's own noise infusion is why: `EMP_N_F` carries the
per-cell noise band and this table does not even have a column for it (see
`specs/deferred_items.md`), so a hard equality on a noised value would be false precision.

SHRINKAGE IS THIS PACKAGE'S FORM, NOT THE SPEC'S. §10.4 says "shrink toward regional/national
values" and gives no functional form. A count-weighted shrink toward the national March intensity
with weight n/(n+k) is used, k=5.0. A state with one establishment is pulled most of the way to the
national value; a state with a hundred is barely moved. `k` is recorded here because it is a
decision, not a measurement.

THE FALLBACK ARM IS THE SHRINKAGE LIMIT. A cell with no CBP row cannot take a bare establishment
count as its weight: the own arm is `intensity x A` in employees, so merging a raw `A` makes
`allocate` treat that state as carrying exactly one employee per establishment -- measured on
2023-06, Hawaii landed at 0.93 against a national 5.9. `national_intensity x A` is the right
answer and costs nothing, because it is precisely what this estimator's own shrinkage returns in
the limit: as n -> 0, weight = n/(n+k) -> 0 and the shrunk intensity IS the national intensity.
"""

from __future__ import annotations

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EmployeeWeights, EstimatorContext, compose
from .simple import establishment_weights

DEFAULT_SHRINK_STRENGTH = 5.0
ALL_ESTABLISHMENTS_SIZE_CODE = "001"


def _intensity_rows(cbp: pl.DataFrame, reference_year: int) -> pl.DataFrame:
    """The usable CBP rows for one reference year: published, all-establishments, non-empty."""
    return cbp.filter(
        (pl.col("reference_year") == reference_year)
        & (pl.col("size_code") == ALL_ESTABLISHMENTS_SIZE_CODE)
        & pl.col("employment").is_not_null()
        & (pl.col("establishments") > 0)
    )


def national_march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> float | None:
    """The national March employees-per-establishment, and the n -> 0 limit of the shrunk value.

    Returned separately so a state with no CBP row can be weighted at the same limit rather than
    at a bare establishment count, which would silently assert an intensity of 1.0.
    """
    rows = _intensity_rows(cbp, reference_year)
    if rows.height == 0:
        return None
    establishments = float(rows["establishments"].sum())
    if establishments <= 0.0:
        return None
    return float(rows["employment"].sum()) / establishments


def march_intensity(
    cbp: pl.DataFrame,
    *,
    reference_year: int,
    shrink_strength: float = DEFAULT_SHRINK_STRENGTH,
) -> dict[str, float]:
    """Shrunk March employees-per-establishment per state, for one CBP reference year."""
    rows = _intensity_rows(cbp, reference_year)
    if rows.height == 0:
        return {}
    national = national_march_intensity(cbp, reference_year=reference_year)
    if national is None:
        return {}
    out: dict[str, float] = {}
    for row in rows.iter_rows(named=True):
        n = float(row["establishments"])
        raw = float(row["employment"]) / n
        weight = n / (n + shrink_strength)
        out[str(row["state_fips"])] = weight * raw + (1.0 - weight) * national
    return out


class CbpIntensity:
    """§10.4. q = shrunk CBP March intensity x QCEW establishment exposure."""

    estimator_id = "cbp_intensity"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Employees per cell, declining the whole month when CBP has no matching vintage."""
        reference_year = int(anchor.reference_month.split("-")[0])
        available = set(context.cbp["reference_year"].unique().to_list())
        if reference_year not in available:
            return Decline(
                reason=(
                    f"CBP publishes no reference year {reference_year}; §10.4's estimator is a "
                    "year-specific March intensity, and carrying an earlier year forward would be "
                    "an assumption this baseline does not make"
                )
            )
        intensity = march_intensity(context.cbp, reference_year=reference_year)
        national = national_march_intensity(context.cbp, reference_year=reference_year)
        exposure = establishment_weights(context, anchor)
        if national is None:
            return Decline(
                reason=(
                    f"CBP reference year {reference_year} publishes no usable establishment "
                    "count, so neither a state intensity nor its national limit exists"
                )
            )
        own = {
            cell: intensity[cell] * exposure[cell]
            for cell in anchor.missing_cells
            if cell in intensity and cell in exposure
        }
        # Both arms in employees: the fallback is the shrinkage limit, not a bare exposure count.
        fallback = {cell: national * value for cell, value in exposure.items()}
        return compose(
            EmployeeWeights(own),
            EmployeeWeights(fallback),
            anchor,
            allowed=context.config.baselines.allow_declared_composite,
        )
