"""Frame factories for the Stage 2 unit suite.

A `qcew_monthly` row literal means filling 24 columns, most of which no constraint builder reads.
These factories fill every column, so the frame matches the shipped schema exactly, and let a test
name only the fields its assertion is about.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.contracts import QCEW_MONTHLY_SCHEMA, QCEW_NATIONAL_SIZE_SCHEMA

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
