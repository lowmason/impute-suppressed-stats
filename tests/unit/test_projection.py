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
    out, _ = kl_project(
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
        out, _ = kl_project(
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
    targets = np.array([30.0])
    # Read BEFORE the call on purpose. Dropping the seed floor aliases `x` to `seed`, so the
    # in-place scaling rewrites the caller's array; an expectation derived after the call would
    # then be derived from the very corruption it is meant to catch, and would pass either way.
    expected_scale = targets[0] / seed.sum()
    out, _ = kl_project(
        seed,
        np.array([[1.0, 1.0, 1.0]]),
        targets,
        lower=np.zeros(3),
        upper=np.full(3, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert np.all(np.isfinite(out))
    assert out[0] > 0.0
    assert out.sum() == pytest.approx(targets[0], abs=1e-6)
    # The floored cell must ride the SAME scale factor as every other cell. The clip at the foot
    # of the margin loop cannot supply that, because `current` is read before it runs, so a floor
    # imposed only there leaves this ratio at exactly 1.0.
    assert out[0] / FLOOR == pytest.approx(expected_scale, rel=1e-6)


def test_projection_respects_finite_upper_bounds() -> None:
    seed = np.array([5.0, 1.0, 1.0])
    upper = np.array([2.0, np.inf, np.inf])
    out, _ = kl_project(
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
    out, _ = kl_project(
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


def test_an_infeasible_bounded_system_reports_its_violation() -> None:
    """The bug this test pins: the loop breaks on step size, not on violation.

    With `upper=[1,1]` and a target of 10, every update is fully clipped, so iteration one moves
    nothing and the step-size break fires immediately. The old signature returned `[1., 1.]` --
    a vector 8.0 away from its margin -- with no signal at all, and `kl_project` is exported, so
    Stage 5 and Stage 6 can call it directly and get that answer.
    """
    out, violation = kl_project(
        np.array([1.0, 1.0]),
        np.array([[1.0, 1.0]]),
        np.array([10.0]),
        lower=np.zeros(2),
        upper=np.ones(2),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out.tolist() == [1.0, 1.0]
    assert violation == pytest.approx(8.0)
    assert violation == pytest.approx(
        constraint_violation(out, np.array([[1.0, 1.0]]), np.array([10.0]))
    )
