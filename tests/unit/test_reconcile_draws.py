"""§16.2's reconcile_draws: one path for a point estimate and for a posterior."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.config import ReconciliationConfig
from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.draws import (
    PosteriorDraws,
    ReconciliationInputs,
    reconcile_draws,
)
from logging_employment.reconcile.scaling import Bounds

CELLS = ("01", "02", "04")


def _config() -> ReconciliationConfig:
    return ReconciliationConfig(
        single_margin_method="bounded_proportional_scaling",
        general_method="kl_projection",
        integerize_release=True,
    )


def _inputs(residual: float = 100.0) -> ReconciliationInputs:
    return ReconciliationInputs(
        anchor=Anchor("2024-03", residual, CELLS, "declared_national_total"),
        bounds=Bounds(lower=dict.fromkeys(CELLS, 0.0), upper=dict.fromkeys(CELLS, None)),
    )


def test_a_single_draw_reconciles_exactly_to_the_residual() -> None:
    """A baseline point estimate is a one-draw posterior; there is no second entry point."""
    raw = PosteriorDraws(cell_ids=CELLS, values=np.array([[1.0, 2.0, 1.0]]), chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape == (1, 3)
    assert out.values[0].sum() == pytest.approx(100.0, abs=1e-6)


def test_every_draw_is_reconciled_not_only_the_mean() -> None:
    """INV-012's shape: the constraint holds on each draw, not on a summary of them."""
    rng = np.random.default_rng(20260905)
    raw = PosteriorDraws(
        cell_ids=CELLS, values=rng.uniform(0.1, 9.0, size=(64, 3)), chain=None, draw=None
    )
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape == (64, 3)
    for row in out.values:
        assert row.sum() == pytest.approx(100.0, abs=1e-6)


def test_the_draw_axis_is_never_reduced() -> None:
    """§12.7: joint draws MUST remain available; a summary here would destroy the dependence."""
    raw = PosteriorDraws(cell_ids=CELLS, values=np.ones((32, 3)), chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape[0] == 32


def test_chain_and_draw_indexes_survive_reconciliation() -> None:
    raw = PosteriorDraws(
        cell_ids=CELLS,
        values=np.ones((4, 3)),
        chain=np.array([0, 0, 1, 1]),
        draw=np.array([0, 1, 0, 1]),
    )
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.chain.tolist() == [0, 0, 1, 1]
    assert out.draw.tolist() == [0, 1, 0, 1]


def test_reconciled_draws_are_negatively_dependent_across_cells() -> None:
    """§12.7's motivation, made checkable: adding up to a fixed total induces negative dependence.

    Marginal intervals cannot see this, which is exactly why the draws must stay joint.
    """
    rng = np.random.default_rng(4096)
    raw = PosteriorDraws(
        cell_ids=CELLS, values=rng.uniform(0.5, 5.0, size=(512, 3)), chain=None, draw=None
    )
    out = reconcile_draws(raw, _inputs(), _config())
    corr = np.corrcoef(out.values, rowvar=False)
    assert corr[0, 1] < 0.0


def test_a_cell_set_mismatch_is_refused() -> None:
    raw = PosteriorDraws(cell_ids=("01", "02"), values=np.ones((2, 2)), chain=None, draw=None)
    with pytest.raises(ValueError):
        reconcile_draws(raw, _inputs(), _config())


def test_a_negative_draw_is_refused_rather_than_floored_into_a_legal_weight() -> None:
    """§12.4 authorises a floor "for zero raw seeds" — nothing about negative ones.

    `max(value, zero_seed_floor)` maps -300 to 1e-12, so an out-of-domain draw becomes a legal
    weight and is reconciled away with no signal: the plan's version returned a row summing to
    exactly the residual, with the -300 simply gone. A draw outside the domain is a modelling
    failure upstream, and §18.3 wants it surfaced rather than absorbed.
    """
    raw = PosteriorDraws(
        cell_ids=CELLS, values=np.array([[-300.0, 2.0, 1.0]]), chain=None, draw=None
    )
    with pytest.raises(WeightDomainError, match="negative"):
        reconcile_draws(raw, _inputs(), _config())


def test_a_zero_draw_is_still_floored_rather_than_refused() -> None:
    """The floor keeps doing its actual job: a raw draw of exactly 0 is not a positive weight."""
    raw = PosteriorDraws(cell_ids=CELLS, values=np.array([[0.0, 2.0, 1.0]]), chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values[0].sum() == pytest.approx(100.0, abs=1e-6)
    assert out.values[0][0] >= 0.0
