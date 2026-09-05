"""§10.6: a regularized model for log employment intensity, fit on training-visible cells only.

"Fit a regularized model for log employment intensity using only training-visible cells, produce
positive predictions, then reconcile each prediction vector to the feasible set."

"TRAINING-VISIBLE" IS UNDEFINED IN THE SPEC -- it appears exactly once, in §10.6 -- so Stage 3
defines it, because Stage 4 drives it. A cell is training-visible when it is in its month's
`partition.disclosed`. That is the same mask-parameterised rule the anchor follows, and it is what
keeps §13.4's leakage control enforceable: under a pseudo-suppression mask the masked cell still
carries its published value in `qcew_monthly`, so an estimator that read the table instead of the
partition would train on the answer. Reading the partition makes leakage structurally impossible
rather than a thing Stage 4 must remember to check.

MODEL FORM. log(E/A) regressed on log(A) with a ridge penalty, fit per month on that month's
training-visible cells, then exponentiated and multiplied by exposure -- so predictions are
positive by construction rather than by clipping. The ridge penalty comes from
`config.baselines.regression_ridge_penalty`.

DEPENDENCY DECISION. numpy and scipy are already declared; scikit-learn is not and is not added. A
ridge fit is a closed-form solve and does not justify a new dependency.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext, compose
from .simple import establishment_fallback_in_employees, establishment_weights

MINIMUM_TRAINING_ROWS = 3


def fit_log_intensity(rows: pl.DataFrame, *, ridge: float) -> tuple[np.ndarray, list[str]]:
    """Ridge-fit `log_intensity ~ 1 + log_exposure`. Returns the coefficients and their names."""
    x = np.column_stack([np.ones(rows.height), rows["log_exposure"].to_numpy()])
    y = rows["log_intensity"].to_numpy()
    penalty = ridge * np.eye(x.shape[1])
    penalty[0, 0] = 0.0  # never shrink the intercept toward zero; the level is not the target
    beta = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    return beta, ["intercept", "log_exposure"]


class ConstrainedRegression:
    """§10.6. q = exp(predicted log intensity) x exposure, reconciled through the shared layer."""

    estimator_id = "constrained_regression"

    def training_rows(self, context: EstimatorContext, reference_month: str) -> pl.DataFrame:
        """The training-visible cells for a month: disclosed by the partition, with positive inputs."""
        partition = context.partitions[reference_month]
        return (
            partition.disclosed.filter(
                pl.col("employment_value").is_not_null()
                & (pl.col("employment_value") > 0)
                & (pl.col("qtrly_establishments") > 0)
            )
            .with_columns(
                pl.col("qtrly_establishments").log().alias("log_exposure"),
                (pl.col("employment_value") / pl.col("qtrly_establishments"))
                .log()
                .alias("log_intensity"),
            )
            .select(["state_fips", "log_exposure", "log_intensity"])
        )

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Predicted employment levels as weights, composed with the establishment fallback."""
        training = self.training_rows(context, anchor.reference_month)
        exposure = establishment_weights(context, anchor)
        if training.height < MINIMUM_TRAINING_ROWS:
            # Not a decline: the declared fallback covers it, and a two-point fit would be noise
            # dressed as a model.
            return compose(
                {},
                establishment_fallback_in_employees(context, anchor),
                anchor,
                allowed=context.config.baselines.allow_declared_composite,
            )
        beta, _ = fit_log_intensity(
            training, ridge=context.config.baselines.regression_ridge_penalty
        )
        own: dict[str, float] = {}
        for cell, exposure_value in exposure.items():
            log_exposure = float(np.log(exposure_value))
            predicted_intensity = float(np.exp(beta[0] + beta[1] * log_exposure))
            own[cell] = predicted_intensity * exposure_value
        # The own arm is exp(mu) * A, i.e. employees, so the fallback must be too. On D1 the
        # exposure covers every missing cell and no gap arises, but a raw-A fallback here would be
        # the same units bug §10.3 and §10.4 carried, waiting for the first month that has one.
        return compose(
            own,
            establishment_fallback_in_employees(context, anchor),
            anchor,
            allowed=context.config.baselines.allow_declared_composite,
        )
