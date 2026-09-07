"""§10.7's empirical predictive intervals, from rolling pseudo-suppression residuals.

ONE object: the residual-shifted ensemble. Both the quantiles and the CRPS are derived from it, so
an interval and a score can never disagree about the same predictive distribution.

Log score is deliberately NOT offered. An empirical ensemble assigns zero density outside its own
range, so a log score is -inf whenever the truth falls outside — a property of the density
estimator, not of the method being scored. §13.7 permits "CRPS or log score"; this package reports
CRPS.
"""

from __future__ import annotations

import numpy as np


def residual_ensemble(residuals: np.ndarray, point: float) -> np.ndarray:
    """The point estimate shifted by every pooled residual.

    The residual pool MUST exclude the target's own cell: a residual computed on the cell being
    scored is the withheld truth in another form (§13.4 bullet 1).
    """
    return np.asarray(residuals, dtype=float) + float(point)


def clip_at_zero(ensemble: np.ndarray) -> tuple[np.ndarray, int]:
    """Employment cannot be negative. Returns the clipped ensemble AND the count clipped.

    The count is returned rather than discarded because clipping shifts nominal coverage; a
    coverage number computed over a clipped ensemble with an unreported clip rate is not
    interpretable.
    """
    clipped = np.maximum(ensemble, 0.0)
    return clipped, int((ensemble < 0.0).sum())


def empirical_interval(ensemble: np.ndarray, level: float) -> tuple[float, float]:
    """A central `level` interval from the ensemble's own quantiles."""
    tail = (1.0 - level) / 2.0
    return (
        float(np.quantile(ensemble, tail)),
        float(np.quantile(ensemble, 1.0 - tail)),
    )


def crps(ensemble: np.ndarray, truth: float) -> float:
    """CRPS by the energy form: E|X - y| - 0.5 * E|X - X'|.

    The second term uses the sorted-ensemble identity
    `sum_i sum_j |x_i - x_j| = 2 * sum_i (2i - n + 1) * x_(i)`
    rather than materialising the n x n pairwise matrix. It is an IDENTITY, not an approximation —
    `test_the_closed_form_matches_the_pairwise_matrix` pins the two against each other.

    The reason is cost, and it is not academic. The harness scores one CRPS per masked cell over an
    ensemble of the other cells' residuals, so the pairwise form is O(n^2) per cell and O(n^3) per
    estimator; `whole_seasonal_blocks` masks 291 cells, and §13.7's metrics — not `run_baselines` —
    became the harness's dominant cost.
    """
    x = np.sort(np.asarray(ensemble, dtype=float))
    n = x.size
    term_one = np.abs(x - float(truth)).mean()
    weights = 2.0 * np.arange(n, dtype=float) - n + 1.0
    term_two = 2.0 * float(np.dot(weights, x)) / (n * n)
    return float(term_one - 0.5 * term_two)
