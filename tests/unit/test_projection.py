"""§12.4 generalized projection: never increases violation, respects bounds, honours the floor."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.reconcile.projection import (
    constraint_violation,
    kl_project,
    require_supported_method,
)

FLOOR = 1.0e-12
TOL = 1.0e-9
ITERS = 1000


def test_projection_reaches_a_single_sum_constraint_exactly() -> None:
    seed = np.array([1.0, 2.0, 1.0])
    margins = np.array([[1.0, 1.0, 1.0]])
    out = kl_project(
        seed,
        margins,
        np.array([100.0]),
        lower=np.zeros(3),
        upper=np.full(3, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out.sum() == pytest.approx(100.0, abs=1e-6)


def test_projection_never_increases_constraint_violation() -> None:
    """§17.3's property, stated directly."""
    rng = np.random.default_rng(20260905)
    for _ in range(25):
        n = int(rng.integers(3, 8))
        seed = rng.uniform(0.1, 10.0, size=n)
        margins = np.vstack([np.ones(n), rng.integers(0, 2, size=n).astype(float)])
        targets = np.array([seed.sum() * 1.3, seed.sum() * 0.4])
        before = constraint_violation(seed, margins, targets)
        out = kl_project(
            seed,
            margins,
            targets,
            lower=np.zeros(n),
            upper=np.full(n, np.inf),
            floor=FLOOR,
            tolerance=TOL,
            max_iterations=ITERS,
        )
        assert constraint_violation(out, margins, targets) <= before + 1e-9


def test_a_zero_seed_is_floored_rather_than_making_the_objective_undefined() -> None:
    """§12.4: "with a small positive floor for zero raw seeds"."""
    seed = np.array([0.0, 1.0, 1.0])
    out = kl_project(
        seed,
        np.array([[1.0, 1.0, 1.0]]),
        np.array([30.0]),
        lower=np.zeros(3),
        upper=np.full(3, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert np.all(np.isfinite(out))
    assert out[0] > 0.0
    assert out.sum() == pytest.approx(30.0, abs=1e-6)


def test_projection_respects_finite_upper_bounds() -> None:
    seed = np.array([5.0, 1.0, 1.0])
    upper = np.array([2.0, np.inf, np.inf])
    out = kl_project(
        seed,
        np.array([[1.0, 1.0, 1.0]]),
        np.array([20.0]),
        lower=np.zeros(3),
        upper=upper,
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out[0] <= 2.0 + 1e-9
    assert out.sum() == pytest.approx(20.0, abs=1e-6)


def test_projection_output_is_strictly_positive() -> None:
    """A KL projection cannot leave the positive orthant; a zero would make a later log undefined."""
    seed = np.array([1.0, 1.0, 1.0])
    out = kl_project(
        seed,
        np.array([[1.0, 1.0, 1.0]]),
        np.array([3.0]),
        lower=np.zeros(3),
        upper=np.full(3, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert np.all(out > 0.0)


def test_a_non_indicator_margin_row_is_refused() -> None:
    """The uniform multiplicative update is the I-projection only for 0/1 incidence rows.

    For a row like `[2, 1]` the update still lands on the hyperplane, so the result looks
    converged while minimizing a different objective than the one §12.4 names -- exactly the
    silent substitution the `weighted_quadratic` paragraph forbids. Refused rather than
    silently answered.
    """
    with pytest.raises(ValueError, match="indicator"):
        kl_project(
            np.array([1.0, 5.0]),
            np.array([[2.0, 1.0]]),
            np.array([10.0]),
            lower=np.zeros(2),
            upper=np.full(2, np.inf),
            floor=FLOOR,
            tolerance=TOL,
            max_iterations=ITERS,
        )


def test_a_negative_coefficient_margin_is_refused_rather_than_escaping_the_bounds() -> None:
    """A negative coefficient reached the one code path that skipped the bound clip.

    With `[[1, -1]]` the plan's version returned `[5., 5.]` against an upper bound of 2 -- the
    `continue` jumped past `np.clip`. The indicator check refuses the input outright, which is
    the honest answer for a margin shape this stage never builds.
    """
    with pytest.raises(ValueError, match="indicator"):
        kl_project(
            np.array([1.0, 5.0]),
            np.array([[1.0, -1.0]]),
            np.array([10.0]),
            lower=np.zeros(2),
            upper=np.full(2, 2.0),
            floor=FLOOR,
            tolerance=TOL,
            max_iterations=ITERS,
        )


def test_weighted_quadratic_is_refused_as_unimplemented() -> None:
    """§12.4 permits it but requires the objective and weights to be validation-tested.

    Nothing in Stage 3 validates a second objective, so the config value is a version marker and
    the path raises rather than quietly running KL under a different name.
    """
    require_supported_method("kl_projection")
    with pytest.raises(NotImplementedError, match="reconciliation.general_method"):
        require_supported_method("weighted_quadratic")
