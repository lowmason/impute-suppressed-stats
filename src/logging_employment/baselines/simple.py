"""§10.1 equal residual allocation and §10.2 establishment-count proportional allocation.

§10.2 IS ALSO THE UNIVERSAL FALLBACK RUNG. Its inputs are the only ones complete on every
suppressed cell of the D1 window -- `qtrly_establishments` is non-null and at least 1 on all 1,227
of them -- which is why §10.8 ranks it 4 as "the minimum fallback" and why every other estimator
composes against `establishment_weights` rather than declining.

WITHIN-QUARTER CONSTANCY IS A LABELLED ASSUMPTION, NOT A MEASUREMENT. §10.2 writes A_{s,t} with a
monthly subscript, but QCEW publishes establishment counts quarterly and `qcew_monthly` repeats the
quarterly value across all three months of its quarter (measured: constant in all 1,572
state-quarters). §11.1 defines only A_{s,q(t)} and calls within-quarter constancy "a baseline
modeling assumption, not a public identity". Using the repeated value is correct; calling it a
monthly measurement would not be.

§11.5's score is q = (A + eps_A) * exp(mu), and eps_A has no value anywhere in the spec. It is not
needed here: A >= 1 on every suppressed cell, so a positive offset would change the weights without
protecting anything. Stage 5 must set eps_A itself for the model's own score.
"""

from __future__ import annotations

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import OWN, EstimatorContext


def _missing_rows(context: EstimatorContext, anchor: Anchor) -> pl.DataFrame:
    """The published state rows for this month's missing cells."""
    return context.monthly.filter(
        (pl.col("area_type") == "state")
        & (pl.col("reference_month") == anchor.reference_month)
        & (pl.col("state_fips").is_in(list(anchor.missing_cells)))
    )


def establishment_weights(context: EstimatorContext, anchor: Anchor) -> dict[str, float]:
    """A_{s,t} per missing cell -- §10.2's weight and every other estimator's fallback.

    A cell with no usable published establishment count -- no row at all, a null, or a
    non-positive value -- is OMITTED from the returned dict rather than given a zero. The three
    cases are deliberately collapsed here, because what matters downstream is identical for all
    three: there is no public establishment count to weight the cell with. Omission is what makes
    that visible, since the returned domain then falls short of the missing set and `allocate`'s
    domain check refuses the month by name instead of normalizing a partial vector over whichever
    cells happened to have inputs.

    This returns a bare dict, not a `Weights`: it is the fallback rung, and only `compose` and
    `EstablishmentProportional` are entitled to declare a basis for it.
    """
    rows = _missing_rows(context, anchor)
    return {
        str(row["state_fips"]): float(row["qtrly_establishments"])
        for row in rows.iter_rows(named=True)
        if row["qtrly_establishments"] is not None and row["qtrly_establishments"] > 0
    }


class EqualAllocation:
    """§10.1: q identically 1, so R_t splits evenly. "Use only as a sanity check."

    Absent from §10.8's fallback hierarchy on purpose -- it ignores every public signal about a
    state, including the establishment counts that are published even when employment is not.
    """

    estimator_id = "equal_residual"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights:
        """q identically 1 over the whole missing set."""
        return Weights(
            values=dict.fromkeys(anchor.missing_cells, 1.0),
            basis=dict.fromkeys(anchor.missing_cells, OWN),
        )


class EstablishmentProportional:
    """§10.2: q = A_{s,t}. §10.8's rung 4 and the fallback every composite leans on."""

    estimator_id = "establishment_proportional"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights:
        """A_{s,t} per cell, with any unweightable cell left for `allocate` to refuse by name."""
        values = establishment_weights(context, anchor)
        return Weights(values=values, basis=dict.fromkeys(values, OWN))
