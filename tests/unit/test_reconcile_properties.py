"""§17.3's seven reconciliation properties, and §17.1's rows 8-10 named explicitly.

Properties 2, 3 and 5 use SYNTHETIC fixtures by necessity, not by convenience. On the D1 window
`selected_upper` is null on 1,227 of 1,241 unknown cells, so a finite upper bound never binds and
`sum U < R_t` never fires; and `target_cell` carries no state-by-size cell at all until Stage 6.
Drawing these properties' inputs from the real tables would produce three tests that pass without
exercising the behaviour they are named for.

No Hypothesis: this repo hand-rolls property tests over a seeded generator, and the seeds are fixed
constants so any failure reproduces.
"""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.errors import InfeasibleResidualError
from logging_employment.reconcile.allocate import Weights, allocate
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.integerize import integerize
from logging_employment.reconcile.matrix import reconcile_matrix
from logging_employment.reconcile.projection import constraint_violation, kl_project
from logging_employment.reconcile.scaling import Bounds, scale_into_bounds

SEED = 20260905
TOL = 1.0e-9
ITERS = 200
FLOOR = 1.0e-12
TRIALS = 200


def _cells(n: int) -> tuple[str, ...]:
    return tuple(f"{i:02d}" for i in range(1, n + 1))


def _weights(cells, rng) -> Weights:
    values = {c: float(rng.uniform(0.05, 20.0)) for c in cells}
    return Weights(values=values, basis=dict.fromkeys(values, "own_estimator"))


# --------------------------------------------------------------------------- §17.1 rows 8-10


def test_section_17_1_row_8_computes_residual_allocation_exactly() -> None:
    """§17.1 row 8: "compute residual allocation exactly"."""
    cells = _cells(4)
    anchor = Anchor("2024-03", 1000.0, cells, "declared_national_total")
    weights = Weights(
        values={c: float(i + 1) for i, c in enumerate(cells)},
        basis=dict.fromkeys(cells, "own_estimator"),
    )
    out = allocate(anchor, weights)
    assert sum(out.values()) == pytest.approx(1000.0, abs=1e-9)
    assert out[cells[0]] == pytest.approx(100.0)


def test_section_17_1_row_9_solves_bounded_proportional_scaling() -> None:
    """§17.1 row 9: "solve bounded proportional scaling"."""
    cells = _cells(3)
    anchor = Anchor("2024-03", 100.0, cells, "declared_national_total")
    bounds = Bounds(
        lower=dict.fromkeys(cells, 10.0), upper={cells[0]: 20.0, cells[1]: None, cells[2]: None}
    )
    out = scale_into_bounds(
        anchor,
        _weights(cells, np.random.default_rng(SEED)),
        bounds,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-6)
    assert out[cells[0]] <= 20.0 + 1e-9


def test_section_17_1_row_10_balances_integer_rounding() -> None:
    """§17.1 row 10: "balance integer rounding"."""
    out = integerize({"01": 33.4, "02": 33.3, "04": 33.3}, total=100)
    assert sum(out.values()) == 100


# --------------------------------------------------------------------- §17.3 properties 1-7


def test_property_1_no_bound_scaling_sums_exactly_to_the_residual() -> None:
    rng = np.random.default_rng(SEED)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 16)))
        residual = float(rng.uniform(1.0, 5000.0))
        anchor = Anchor("2024-03", residual, cells, "declared_national_total")
        out = allocate(anchor, _weights(cells, rng))
        assert sum(out.values()) == pytest.approx(residual, rel=1e-12)


def test_property_2_bounded_scaling_respects_every_bound() -> None:
    """SYNTHETIC finite uppers: on D1 every state cell is unbounded above."""
    rng = np.random.default_rng(SEED + 1)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 10)))
        lower = {c: float(rng.uniform(0.0, 5.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 200.0)) for c in cells}
        residual = float(rng.uniform(sum(lower.values()), sum(upper.values())))
        anchor = Anchor("2024-03", residual, cells, "declared_national_total")
        out = scale_into_bounds(
            anchor,
            _weights(cells, rng),
            Bounds(lower=lower, upper=upper),
            tolerance=TOL,
            max_iterations=ITERS,
        )
        assert sum(out.values()) == pytest.approx(residual, abs=1e-5)
        for cell in cells:
            assert out[cell] >= lower[cell] - 1e-7
            assert out[cell] <= upper[cell] + 1e-7


def test_property_3_bounded_scaling_fails_on_infeasible_residuals() -> None:
    """SYNTHETIC: the `sum U < R_t` half cannot fire on D1, where every upper is null.

    The `match=` is the property, not decoration. scaling.py's bracket-exhaustion `for...else`
    raises the same InfeasibleResidualError type, so with §12.3's `sum U < R_t` refusal deleted the
    bare form passed and the whole 1123-test suite stayed green. The two anchors are unrolled so
    each arm can assert its own message.
    """
    rng = np.random.default_rng(SEED + 2)
    for _ in range(TRIALS // 2):
        cells = _cells(int(rng.integers(2, 8)))
        lower = {c: float(rng.uniform(1.0, 10.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 10.0)) for c in cells}
        anchor_low = Anchor("2024-03", sum(lower.values()) - 1.0, cells, "declared_national_total")
        anchor_high = Anchor("2024-03", sum(upper.values()) + 1.0, cells, "declared_national_total")
        bounds = Bounds(lower=lower, upper=upper)
        weights = _weights(cells, rng)
        with pytest.raises(InfeasibleResidualError, match="exceed residual"):
            scale_into_bounds(anchor_low, weights, bounds, tolerance=TOL, max_iterations=ITERS)
        with pytest.raises(InfeasibleResidualError, match="fall below residual"):
            scale_into_bounds(anchor_high, weights, bounds, tolerance=TOL, max_iterations=ITERS)


def test_property_3b_a_residual_exactly_on_a_bound_sum_is_feasible() -> None:
    """§12.3's predicate is strict, so the boundary case must SUCCEED, not raise.

    Guarded separately from property 3 because the natural implementation of "fails on infeasible
    residuals" is `>=`, which silently makes this case fail too.
    """
    cells = _cells(3)
    lower = dict.fromkeys(cells, 10.0)
    anchor = Anchor("2024-03", 30.0, cells, "declared_national_total")
    out = scale_into_bounds(
        anchor,
        _weights(cells, np.random.default_rng(SEED)),
        Bounds(lower=lower, upper=dict.fromkeys(cells, None)),
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(30.0, abs=1e-7)


def test_property_4_projection_never_increases_constraint_violation() -> None:
    rng = np.random.default_rng(SEED + 3)
    for _ in range(TRIALS // 2):
        n = int(rng.integers(3, 10))
        seed = rng.uniform(0.1, 50.0, size=n)
        margins = np.vstack([np.ones(n), (rng.random(n) < 0.5).astype(float)])
        targets = np.array(
            [float(seed.sum() * rng.uniform(0.5, 2.0)), float(seed.sum() * rng.uniform(0.1, 0.6))]
        )
        before = constraint_violation(seed, margins, targets)
        out, _ = kl_project(
            seed,
            margins,
            targets,
            lower=np.zeros(n),
            upper=np.full(n, np.inf),
            floor=FLOOR,
            tolerance=TOL,
            max_iterations=1000,
        )
        assert constraint_violation(out, margins, targets) <= before + 1e-6


def test_property_5_row_and_column_reconciliation_is_exact() -> None:
    """SYNTHETIC: `target_cell` carries no state-by-size cell until Stage 6."""
    rng = np.random.default_rng(SEED + 4)
    for _ in range(TRIALS // 4):
        rows, cols = int(rng.integers(2, 6)), int(rng.integers(2, 6))
        seed = rng.uniform(0.1, 10.0, size=(rows, cols))
        row_totals = rng.uniform(10.0, 100.0, size=rows)
        column_totals = rng.uniform(1.0, 10.0, size=cols)
        column_totals *= row_totals.sum() / column_totals.sum()  # make the margins consistent
        out = reconcile_matrix(
            seed, row_totals, column_totals, tolerance=TOL, max_iterations=5000, floor=FLOOR
        )
        # rel=1e-9, not 1e-4: reconcile_matrix itself refuses unless np.allclose(rtol=1e-6), so a
        # looser assertion here cannot fail if the function returns at all -- it would be testing
        # "did not raise", not "is exact". Measured true error is 2.7e-11.
        assert out.sum(axis=1) == pytest.approx(row_totals, rel=1e-9)
        assert out.sum(axis=0) == pytest.approx(column_totals, rel=1e-9)


def test_property_6_integerization_preserves_required_totals() -> None:
    rng = np.random.default_rng(SEED + 5)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 16)))
        total = int(rng.integers(0, 5000))
        raw = rng.uniform(0.0, 1.0, size=len(cells))
        values = {c: float(total * v / raw.sum()) for c, v in zip(cells, raw, strict=True)}
        out = integerize(values, total=total)
        assert sum(out.values()) == total


def test_property_7_cell_ordering_does_not_shift_results_materially() -> None:
    """Solver tolerance and cell ordering must not create material instability."""
    rng = np.random.default_rng(SEED + 6)
    for _ in range(TRIALS // 4):
        cells = _cells(int(rng.integers(3, 12)))
        residual = float(rng.uniform(10.0, 3000.0))
        weights = _weights(cells, rng)
        lower = dict.fromkeys(cells, 0.0)
        upper = {c: None for c in cells}
        forward = scale_into_bounds(
            Anchor("2024-03", residual, cells, "declared_national_total"),
            weights,
            Bounds(lower=lower, upper=upper),
            tolerance=TOL,
            max_iterations=ITERS,
        )
        reversed_cells = tuple(reversed(cells))
        backward = scale_into_bounds(
            Anchor("2024-03", residual, reversed_cells, "declared_national_total"),
            Weights(
                values={c: weights.values[c] for c in reversed_cells},
                basis={c: "own_estimator" for c in reversed_cells},
            ),
            Bounds(lower=lower, upper=upper),
            tolerance=TOL,
            max_iterations=ITERS,
        )
        for cell in cells:
            assert forward[cell] == pytest.approx(backward[cell], rel=1e-9, abs=1e-9)


def test_property_7b_integerization_is_order_independent() -> None:
    values = {"04": 3.5, "01": 3.5, "02": 3.0}
    forward = integerize(values, total=10)
    backward = integerize(dict(reversed(list(values.items()))), total=10)
    assert forward == backward


# --- what the seven properties do not reach ----------------------------------------------------


def test_projection_actually_reaches_a_feasible_systems_margins() -> None:
    """Property 4's companion. "Never increases" is satisfied by an implementation that does
    nothing: an identity kl_project passes test_property_4 on all 100 trials, because
    after == before clears `after <= before + 1e-6`. On a system that IS feasible the projection
    must arrive, not merely not-diverge.

    Deterministic and separate rather than folded into property 4, which stays faithful to
    spec:1740 -- 3 of its 100 trials legitimately do not move, so a strict-decrease assertion
    inside its loop would be flaky by construction."""
    seed = np.array([1.0, 2.0, 3.0, 4.0])
    margins = np.vstack([np.ones(4), np.array([1.0, 1.0, 0.0, 0.0])])
    targets = np.array([20.0, 8.0])

    out, _ = kl_project(
        seed,
        margins,
        targets,
        lower=np.zeros(4),
        upper=np.full(4, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=1000,
    )

    assert constraint_violation(out, margins, targets) == pytest.approx(0.0, abs=1e-8)


@pytest.mark.parametrize("tolerance", [1.0e-9, 1.0e-6])
def test_property_7_solver_tolerance_does_not_move_the_solution(tolerance: float) -> None:
    """The second half of §17.3's last bullet -- "ordering or solver tolerances do not create
    material instability". test_property_7_cell_ordering... varies cell order only, and no test in
    the repo varied a reconcile tolerance at all: TOL is a pinned module constant in all four
    reconcile test files.

    Compared at the LOOSER tolerance's precision, never tighter than the looser solve can promise.
    The residual is drawn strictly inside [sum L, sum U] so property 3's refusals never fire."""
    rng = np.random.default_rng(SEED + 6)
    for _ in range(20):
        cells = _cells(int(rng.integers(2, 10)))
        lower = {c: float(rng.uniform(0.0, 5.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 200.0)) for c in cells}
        residual = float(rng.uniform(sum(lower.values()), sum(upper.values())))
        anchor = Anchor("2024-01", residual, cells, "declared_national_total")
        weights = _weights(cells, rng)
        bounds = Bounds(lower=lower, upper=upper)

        tight = scale_into_bounds(anchor, weights, bounds, tolerance=TOL, max_iterations=ITERS)
        loose = scale_into_bounds(
            anchor, weights, bounds, tolerance=tolerance, max_iterations=ITERS
        )
        for cell in cells:
            assert tight[cell] == pytest.approx(loose[cell], abs=1e-5)
