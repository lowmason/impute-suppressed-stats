"""§12.4 general feasible-polytope projection under I-divergence (KL).

x = argmin_{x in F} sum_i [ x_i log(x_i / seed_i) - x_i + seed_i ]

Solved by iterative proportional fitting with bound clipping: for each margin in turn, scale the
cells it touches so the margin is met, then clip to bounds and repeat. On a pure equality system
with no bounds this is exactly IPF and converges to the I-projection; with bounds it is the
standard clipped variant, and the acceptance test is the one §17.3 states -- violation must never
increase -- rather than a convergence proof.

WHY MARGINS MUST BE 0/1 INDICATOR ROWS. The I-projection onto `sum_i a_i x_i = t` is
`x_i = seed_i * exp(lambda * a_i)`, which the uniform scaling `x[touched] *= target / current`
reproduces only when every nonzero `a_i` is the same value. For a row like `[2, 1]` the scaled
vector still lands on the hyperplane, so the result looks converged while minimizing a different
objective than the one §12.4 names. Every margin this stage builds is an incidence row, so the
restriction costs nothing and is asserted at entry rather than left as a comment -- a later stage
passing weighted margins would otherwise get a silently non-KL answer.

WHY A FLOOR ON ZERO SEEDS IS MANDATORY, NOT COSMETIC. The objective contains log(x_i / seed_i),
which is undefined at seed_i = 0, and multiplicative updates cannot lift a zero seed off zero at
any rate. §12.4 requires "a small positive floor for zero raw seeds"; the value is this package's
decision and lives in `config.reconciliation.zero_seed_floor`.

WHY `weighted_quadratic` IS NOT IMPLEMENTED HERE. §12.4 permits it but requires the objective and
weights to be "versioned and validation-tested". Nothing in Stage 3 validates a second objective,
so the config value is accepted as a version marker and `require_supported_method` raises rather
than quietly running KL under a different name. The guard belongs wherever the config is actually
read -- `reconcile_draws` and the CLI commands -- because neither `kl_project` nor
`reconcile_matrix` takes a config argument.
"""

from __future__ import annotations

import numpy as np

SUPPORTED_METHODS: tuple[str, ...] = ("kl_projection",)


def require_supported_method(method: str) -> None:
    """Refuse a `general_method` this stage does not actually implement.

    §12.4 allows a weighted quadratic objective but requires it to be versioned and
    validation-tested. Accepting the config value and running KL anyway would make the version
    marker a lie, so the honest gap is raised instead.
    """
    if method not in SUPPORTED_METHODS:
        raise NotImplementedError(
            f"reconciliation.general_method={method!r} is not implemented; §12.4 requires a "
            f"substituted objective to be versioned and validation-tested, and this stage "
            f"validates only {SUPPORTED_METHODS[0]!r}"
        )


def constraint_violation(x: np.ndarray, margins: np.ndarray, targets: np.ndarray) -> float:
    """Total absolute margin violation -- the quantity §17.3 requires never to increase."""
    return float(np.abs(margins @ x - targets).sum())


def _require_indicator_margins(margins: np.ndarray) -> None:
    """Refuse any margin matrix that is not 0/1, which the uniform update silently mis-projects."""
    if margins.size and not np.isin(margins, (0.0, 1.0)).all():
        raise ValueError(
            "margins must be 0/1 indicator rows; the multiplicative update reproduces the "
            "I-projection only for incidence rows, and weighted coefficients would minimize a "
            "different objective than §12.4 names"
        )


def kl_project(
    seed: np.ndarray,
    margins: np.ndarray,
    targets: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    floor: float,
    tolerance: float,
    max_iterations: int,
) -> np.ndarray:
    """Project `seed` onto {x : margins @ x == targets, lower <= x <= upper} under I-divergence."""
    margins = np.asarray(margins, dtype=float)
    _require_indicator_margins(margins)
    x = np.maximum(np.asarray(seed, dtype=float), floor)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)

    for _ in range(max_iterations):
        previous = x.copy()
        for row, target in zip(margins, targets, strict=True):
            touched = row != 0.0
            if not touched.any():
                continue
            current = float(row @ x)
            if current <= 0.0:
                # Reachable only when every touched cell has been clipped to an upper bound of 0,
                # since an indicator row over x >= floor > 0 is otherwise strictly positive.
                # Spread the target evenly rather than dividing by zero; the clip below still runs.
                x[touched] = max(target / touched.sum(), floor)
            else:
                x[touched] *= target / current
            # Clipping follows BOTH branches. Skipping it on the degenerate branch returned
            # vectors that violated `upper` outright.
            x = np.clip(x, np.maximum(lower, floor), upper)
        if np.max(np.abs(x - previous)) <= tolerance:
            break
    return x
