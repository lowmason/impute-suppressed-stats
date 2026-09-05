"""Table schemas, the observation-status vocabulary, and fingerprint determinism."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.errors import SchemaMismatchError


def test_observation_statuses_separate_absent_from_suppressed_and_zero() -> None:
    assert contracts.OBSERVATION_STATUSES == ("observed", "suppressed", "true_zero", "absent")


def test_qcew_monthly_carries_every_field_the_spec_names() -> None:
    # fmt: off
    expected = [
        "snapshot_id", "release_vintage", "release_status", "reference_quarter",
        "reference_month", "area_fips", "area_type", "state_fips", "industry_code",
        "naics_vintage", "ownership_code", "aggregation_level", "size_code",
        "qtrly_establishments", "employment_raw", "employment_value", "wages_raw",
        "wages_value", "disclosure_code", "observation_status", "is_published_numeric_zero",
        "is_true_zero", "source_row_hash",
    ]
    # fmt: on
    assert list(contracts.QCEW_MONTHLY_SCHEMA) == expected


def test_area_fips_is_a_string_so_leading_zeros_survive() -> None:
    assert contracts.QCEW_MONTHLY_SCHEMA["area_fips"] == pl.String
    assert contracts.QCEW_MONTHLY_SCHEMA["state_fips"] == pl.String


def test_fingerprint_is_deterministic_and_order_sensitive() -> None:
    a = {"x": pl.String, "y": pl.Int64}
    b = {"y": pl.Int64, "x": pl.String}
    assert contracts.schema_fingerprint(a) == contracts.schema_fingerprint(a)
    assert len(contracts.schema_fingerprint(a)) == 64
    assert contracts.schema_fingerprint(a) != contracts.schema_fingerprint(b)


def test_validate_frame_names_the_offending_columns() -> None:
    frame = pl.DataFrame({"x": ["a"]})
    with pytest.raises(SchemaMismatchError, match="y"):
        contracts.validate_frame(frame, {"x": pl.String, "y": pl.Int64}, "toy")
