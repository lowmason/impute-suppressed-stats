"""§10.1 and §10.2, and the establishment rung every other baseline falls back to."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.interfaces import EstimatorContext
from logging_employment.baselines.simple import (
    EqualAllocation,
    EstablishmentProportional,
    establishment_weights,
)
from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.allocate import allocate
from logging_employment.reconcile.anchor import Anchor, observed_partition


def _context(monthly: pl.DataFrame, cfg) -> EstimatorContext:
    return EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=observed_partition(monthly), config=cfg
    )


def _anchor(cells: tuple[str, ...], residual: float = 90.0) -> Anchor:
    return Anchor("2024-03", residual, cells, "declared_national_total")


def test_equal_allocation_splits_the_residual_evenly(make_monthly, appendix_a_config) -> None:
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 1,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 99,
        },
        {
            "state_fips": "04",
            "area_fips": "04000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 50,
        },
    )
    anchor = _anchor(("01", "02", "04"))
    weights = EqualAllocation().weights(_context(monthly, appendix_a_config), anchor)
    out = allocate(anchor, weights)
    assert out == pytest.approx({"01": 30.0, "02": 30.0, "04": 30.0})


def test_establishment_proportional_weights_by_exposure(make_monthly, appendix_a_config) -> None:
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 1,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 2,
        },
    )
    anchor = _anchor(("01", "02"), residual=90.0)
    weights = EstablishmentProportional().weights(_context(monthly, appendix_a_config), anchor)
    out = allocate(anchor, weights)
    assert out == pytest.approx({"01": 30.0, "02": 60.0})


def test_the_establishment_rung_covers_every_missing_cell(make_monthly, appendix_a_config) -> None:
    """The property that makes §10.2 usable as the universal fallback."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 4,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 7,
        },
    )
    anchor = _anchor(("01", "02"))
    weights = establishment_weights(_context(monthly, appendix_a_config), anchor)
    assert set(weights) == {"01", "02"}
    assert all(value > 0 for value in weights.values())


def test_a_missing_cell_with_no_establishment_row_is_not_silently_dropped(
    make_monthly, appendix_a_config
) -> None:
    """An absent row is absence, not zero. It must surface, not vanish from the weight vector."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 4,
        },
    )
    anchor = _anchor(("01", "38"))
    context = _context(monthly, appendix_a_config)
    weights = establishment_weights(context, anchor)
    # The bare dict omits the cell -- that is the design, and it is only half the claim.
    assert "38" not in weights
    # The half the name promises: entering the reconciliation layer surfaces the gap by name
    # rather than normalizing a partial vector over the cells that happen to have inputs.
    with pytest.raises(WeightDomainError, match="38"):
        allocate(anchor, EstablishmentProportional().weights(context, anchor))
