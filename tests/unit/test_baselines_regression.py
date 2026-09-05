"""§10.6 constrained regression: positive predictions from training-visible cells only."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from logging_employment.baselines.interfaces import EstimatorContext
from logging_employment.baselines.regression import ConstrainedRegression, fit_log_intensity
from logging_employment.reconcile.anchor import Anchor, Partition, observed_partition


def _panel(make_monthly) -> pl.DataFrame:
    rows = [
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 300,
            "qtrly_establishments": 30,
        }
    ]
    for fips, emp, est in [("01", 40, 4), ("02", 60, 6), ("04", 80, 8), ("05", 100, 10)]:
        rows.append(
            {
                "state_fips": fips,
                "area_fips": f"{fips}000",
                "reference_month": "2024-03",
                "employment_value": emp,
                "qtrly_establishments": est,
                "observation_status": "observed",
            }
        )
    rows.append(
        {
            "state_fips": "06",
            "area_fips": "06000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 5,
            "observation_status": "suppressed",
        }
    )
    return make_monthly(*rows)


def test_predictions_are_strictly_positive(make_monthly, appendix_a_config) -> None:
    """§10.6: "produce positive predictions". A log-intensity model exponentiates, so this holds
    by construction -- and the test pins the construction, not the arithmetic."""
    monthly = _panel(make_monthly)
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame(),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    anchor = Anchor("2024-03", 20.0, ("06",), "declared_national_total")
    out = ConstrainedRegression().weights(context, anchor)
    assert out.values["06"] > 0.0


def test_the_fit_uses_only_training_visible_cells(make_monthly, appendix_a_config) -> None:
    """ "Training-visible" is undefined in the spec; the partition argument is its definition.

    A cell in `partition.missing` must not enter the fit even when the table shows a value -- that
    is exactly the situation Stage 4's mask creates, and §13.4's leakage control depends on it.
    """
    monthly = _panel(make_monthly)
    states = monthly.filter(pl.col("area_type") == "state")
    # Mask 05 as if pseudo-suppressed: its value is present in the table but must not be learned.
    masked = {
        "2024-03": Partition(
            disclosed=states.filter(pl.col("state_fips").is_in(["01", "02", "04"])),
            missing=states.filter(pl.col("state_fips").is_in(["05", "06"])),
        )
    }
    context = EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=masked, config=appendix_a_config
    )
    training = ConstrainedRegression().training_rows(context, "2024-03")
    assert sorted(training["state_fips"].to_list()) == ["01", "02", "04"]


def test_the_ridge_penalty_shrinks_the_slope(make_monthly) -> None:
    rows = pl.DataFrame(
        {
            "state_fips": ["01", "02", "04", "05"],
            "log_exposure": [0.0, 1.0, 2.0, 3.0],
            "log_intensity": [0.0, 1.0, 2.0, 3.0],
        }
    )
    weak, _ = fit_log_intensity(rows, ridge=0.001)
    strong, _ = fit_log_intensity(rows, ridge=100.0)
    assert abs(strong[1]) < abs(weak[1])


def test_a_fit_with_too_few_training_rows_falls_back(make_monthly, appendix_a_config) -> None:
    """One observed cell cannot identify a slope; fall back rather than fitting noise."""
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 100,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 40,
            "qtrly_establishments": 4,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 6,
            "observation_status": "suppressed",
        },
    )
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame(),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    anchor = Anchor("2024-03", 60.0, ("02",), "declared_national_total")
    out = ConstrainedRegression().weights(context, anchor)
    assert out.basis["02"] == "establishment_fallback"
