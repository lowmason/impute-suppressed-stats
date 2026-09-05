"""§10.4, the preferred transparent baseline, and the two coverage holes it must declare."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.intensity import CbpIntensity, march_intensity
from logging_employment.baselines.interfaces import FALLBACK, OWN, Decline, EstimatorContext
from logging_employment.contracts import CBP_STATE_SIZE_SCHEMA
from logging_employment.reconcile.anchor import Anchor, observed_partition

_CBP_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2023",
    "reference_year": 2023,
    "state_fips": "01",
    "industry_code": "113310",
    "naics_vintage": "NAICS 2022",
    "legal_form_code": "001",
    "size_code": "001",
    "size_label": "All establishments",
    "size_lower": 0,
    "size_upper": None,
    "establishments": 10,
    "employment": 50,
    "employment_flag": "",
    "employment_noise_range": "0",
    "disclosure_status": "published",
    "disclosure_regime": "noise_infusion",
    "reference_period": "week_including_march_12",
}


def _cbp(*rows: dict[str, object]) -> pl.DataFrame:
    return pl.DataFrame([_CBP_DEFAULTS | dict(r) for r in rows], schema=CBP_STATE_SIZE_SCHEMA)


def test_intensity_is_employment_over_establishments_per_state() -> None:
    """The raw ratio, with shrinkage switched off so the name matches what is asserted.

    `march_intensity` shrinks by default (k = 5.0), which for these inputs returns 4.5 and 3.0714,
    not 5.0 and 3.0 — the national intensity is 140/40 = 3.5 and state 01 carries weight
    10/15. Asserting the unshrunk ratio therefore requires asking for it. The shrunk path is
    covered by the test below.
    """
    out = march_intensity(
        _cbp(
            {"state_fips": "01", "employment": 50, "establishments": 10},
            {"state_fips": "02", "employment": 90, "establishments": 30},
        ),
        reference_year=2023,
        shrink_strength=0.0,
    )
    assert out["01"] == pytest.approx(5.0)
    assert out["02"] == pytest.approx(3.0)


def test_the_default_shrinkage_pulls_a_small_state_toward_the_national_intensity() -> None:
    """The default k = 5.0 path, with the arithmetic derived rather than typed."""
    out = march_intensity(
        _cbp(
            {"state_fips": "01", "employment": 50, "establishments": 10},
            {"state_fips": "02", "employment": 90, "establishments": 30},
        ),
        reference_year=2023,
    )
    national = 140 / 40
    assert out["01"] == pytest.approx((10 / 15) * 5.0 + (5 / 15) * national)
    assert out["02"] == pytest.approx((30 / 35) * 3.0 + (5 / 35) * national)


def test_a_suppressed_cbp_cell_is_dropped_not_read_as_zero() -> None:
    """INV-003. A null employment is absence of a measurement, not a measurement of zero."""
    out = march_intensity(
        _cbp(
            {
                "state_fips": "01",
                "employment": None,
                "establishments": 10,
                "disclosure_status": "suppressed",
            }
        ),
        reference_year=2023,
    )
    assert "01" not in out


def test_reference_year_2024_declines_rather_than_carrying_2023_forward(
    make_monthly, appendix_a_config
) -> None:
    """CBP publishes 2017-2023 only. §10.4's whole content is a year-specific March intensity."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-06",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
    )
    context = EstimatorContext(
        monthly=monthly,
        cbp=_cbp({"reference_year": 2023}),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    anchor = Anchor("2024-06", 40.0, ("01",), "declared_national_total")
    out = CbpIntensity().weights(context, anchor)
    assert isinstance(out, Decline)
    assert "2024" in out.reason


def test_a_state_absent_from_cbp_takes_the_declared_fallback(
    make_monthly, appendix_a_config
) -> None:
    """Hawaii and Rhode Island are in this position for every published year."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2023-06",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
        {
            "state_fips": "15",
            "area_fips": "15000",
            "reference_month": "2023-06",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 3,
        },
    )
    context = EstimatorContext(
        monthly=monthly,
        cbp=_cbp({"state_fips": "01", "reference_year": 2023}),
        partitions=observed_partition(monthly),
        config=appendix_a_config,
    )
    anchor = Anchor("2023-06", 40.0, ("01", "15"), "declared_national_total")
    out = CbpIntensity().weights(context, anchor)
    assert out.basis["01"] == OWN
    assert out.basis["15"] == FALLBACK


def test_shrinkage_pulls_a_thin_state_toward_the_national_intensity() -> None:
    """§10.4: "shrink it toward regional/national values"."""
    cbp = _cbp(
        {"state_fips": "01", "employment": 1000, "establishments": 100},
        {"state_fips": "02", "employment": 100, "establishments": 1},
    )
    out = march_intensity(cbp, reference_year=2023, shrink_strength=5.0)
    # State 02's raw intensity is 100; national is 1100/101 ~= 10.9. One establishment cannot
    # carry a raw intensity that far from the national value.
    assert out["02"] < 100.0
    assert out["01"] == pytest.approx(10.0, abs=1.0)


def test_the_fallback_arm_is_in_employees_not_establishments(
    make_monthly, appendix_a_config
) -> None:
    """A cell with no CBP row must not be weighted as if its intensity were 1.0.

    Composing `intensity x A` against a bare `A` makes `allocate` treat every fallback state as
    carrying one employee per establishment — measured on 2023-06, Hawaii came out at 0.93
    employees per establishment against a national 5.9. The fallback is the estimator's own
    shrinkage limit instead: as n -> 0 the shrunk intensity IS the national intensity, so
    `national_intensity x A` introduces no number the baseline did not already have.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2023-06",
            "employment_value": 1000,
            "qtrly_establishments": 40,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2023-06",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "44",
            "area_fips": "44000",
            "reference_month": "2023-06",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "06",
            "area_fips": "06000",
            "reference_month": "2023-06",
            "observation_status": "observed",
            "employment_value": 500,
            "qtrly_establishments": 20,
        },
    )
    cbp = _cbp({"state_fips": "01", "employment": 50, "establishments": 10})
    anchor = Anchor("2023-06", 500.0, ("01", "44"), "declared_national_total")
    context = EstimatorContext(
        monthly=monthly, cbp=cbp, partitions=observed_partition(monthly), config=appendix_a_config
    )
    out = CbpIntensity().weights(context, anchor)
    assert out.basis["44"] == FALLBACK
    # Both arms are employees, so the two equal-exposure cells sit within a factor of a few of
    # each other rather than differing by the intensity itself.
    assert 0.2 < out.values["44"] / out.values["01"] < 5.0
