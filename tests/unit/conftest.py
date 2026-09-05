"""Frame factories for the Stage 2 unit suite.

A `qcew_monthly` row literal means filling 24 columns, most of which no constraint builder reads.
These factories fill every column, so the frame matches the shipped schema exactly, and let a test
name only the fields its assertion is about.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.contracts import (
    BRIDGE_SCHEMA,
    CBP_STATE_SIZE_SCHEMA,
    QCEW_MONTHLY_SCHEMA,
    QCEW_NATIONAL_SIZE_SCHEMA,
    HarmonizedData,
)

_MONTHLY_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2024q1",
    "release_vintage": "2024q1",
    "release_status": "final",
    "reference_quarter": "2024Q1",
    "reference_month": "2024-03",
    "area_fips": "01000",
    "area_type": "state",
    "state_fips": "01",
    "industry_code": "113310",
    "naics_vintage": "NAICS 2022",
    "ownership_code": "5",
    "aggregation_level": "58",
    "size_code": "0",
    "qtrly_establishments": 10,
    "employment_raw": "100",
    "employment_value": 100,
    "wages_raw": "1000",
    "wages_value": 1000,
    "disclosure_code": "",
    "observation_status": "observed",
    "is_published_numeric_zero": False,
    "is_true_zero": False,
    "source_row_hash": "deadbeef",
    "suppression_type": "unknown",
}

_SIZE_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2024_q1_by_size",
    "reference_year": 2024,
    "reference_quarter": "2024Q1",
    "reference_month": "2024-03",
    "industry_code": "113310",
    "naics_vintage": "NAICS 2022",
    "size_class": "1",
    "size_lower": 0,
    "size_upper": 4,
    "establishments": 100,
    "employment": 200,
    "disclosure_code": "",
    "observation_status": "observed",
}


@pytest.fixture()
def make_monthly() -> Callable[..., pl.DataFrame]:
    """Build a `qcew_monthly` frame from partial row dicts."""

    def _build(*rows: dict[str, object]) -> pl.DataFrame:
        return pl.DataFrame(
            [_MONTHLY_DEFAULTS | dict(row) for row in rows], schema=QCEW_MONTHLY_SCHEMA
        )

    return _build


@pytest.fixture()
def make_size() -> Callable[..., pl.DataFrame]:
    """Build a `qcew_national_size` frame from partial row dicts."""

    def _build(*rows: dict[str, object]) -> pl.DataFrame:
        return pl.DataFrame(
            [_SIZE_DEFAULTS | dict(row) for row in rows], schema=QCEW_NATIONAL_SIZE_SCHEMA
        )

    return _build


_CBP_TOY_DEFAULTS: dict[str, object] = {
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


@pytest.fixture()
def harmonized_toy(make_monthly) -> HarmonizedData:
    """A two-month, four-state `HarmonizedData` the runner can be driven end to end on.

    Built to the shape the runner's tests need, and every property is load-bearing:

    * The establishment universes CLOSE EXACTLY in both months — national 50 against states
      10+20+5+15 — because `run_baselines` calls `assert_universe_closes` before anything else and
      a fixture that failed the gate would test only the halt.
    * Every month has a suppressed cell, so no month is skipped for an empty missing set.
    * State '04' is suppressed in BOTH months, so it never acquires an observed history and the
      §10.3 family must reach for its declared fallback.
    * State '06' is absent from CBP entirely, so §10.4 must compose rather than decline.
    * Residuals are positive in both months (50 and 80), so the anchor is admissible.
    """
    rows = [
        # 2023-01: only '04' is suppressed; residual 500 - 450 = 50.
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2023-01",
            "employment_value": 500,
            "qtrly_establishments": 50,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2023-01",
            "employment_value": 100,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2023-01",
            "employment_value": 200,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "04",
            "area_fips": "04000",
            "reference_month": "2023-01",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
        {
            "state_fips": "06",
            "area_fips": "06000",
            "reference_month": "2023-01",
            "employment_value": 150,
            "qtrly_establishments": 15,
        },
        # 2023-02: '04' and '06' suppressed; residual 400 - 320 = 80.
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2023-02",
            "employment_value": 400,
            "qtrly_establishments": 50,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2023-02",
            "employment_value": 110,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2023-02",
            "employment_value": 210,
            "qtrly_establishments": 20,
        },
        {
            "state_fips": "04",
            "area_fips": "04000",
            "reference_month": "2023-02",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 5,
        },
        {
            "state_fips": "06",
            "area_fips": "06000",
            "reference_month": "2023-02",
            "observation_status": "suppressed",
            "employment_value": None,
            "qtrly_establishments": 15,
        },
    ]
    cbp = pl.DataFrame(
        [
            _CBP_TOY_DEFAULTS | {"state_fips": "01", "establishments": 10, "employment": 100},
            _CBP_TOY_DEFAULTS | {"state_fips": "02", "establishments": 20, "employment": 200},
            _CBP_TOY_DEFAULTS | {"state_fips": "04", "establishments": 5, "employment": 25},
        ],
        schema=CBP_STATE_SIZE_SCHEMA,
    )
    return HarmonizedData(
        qcew_monthly=make_monthly(*rows),
        qcew_national_size=pl.DataFrame([], schema=QCEW_NATIONAL_SIZE_SCHEMA),
        cbp_state_size=cbp,
        bridge=pl.DataFrame([], schema=BRIDGE_SCHEMA),
    )
