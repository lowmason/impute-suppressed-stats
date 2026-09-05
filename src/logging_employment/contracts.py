"""Polars schemas for every table this stage persists, and their fingerprints.

Field order follows the spec's own listing in §7.1-§7.5 and §8.6. Order is load-bearing: the
schema fingerprint is computed over the ordered pairs, so a reordering is a schema change and is
meant to be detected as one.
"""

from __future__ import annotations

import hashlib
import json

import polars as pl

from .errors import SchemaMismatchError

# `observation_status` is named in §7.3, §7.4, §7.7 and §15.2 and enumerated in none of them, so
# these four values are this package's decision rather than the spec's text. `absent` is the one
# that is easy to miss and impossible to fold in: Stage 0 measured that DC (11000) publishes no
# private 113310 row in any of the window's 96 months, which is not a suppressed cell and not a
# zero. Collapsing it into either would state something about DC that no source published.
OBSERVATION_STATUSES: tuple[str, ...] = ("observed", "suppressed", "true_zero", "absent")

# INV-009: the real-world suppression type is unknown unless a public source identifies one, and
# QCEW identifies none. The two labelled values exist for Stage 4's synthetic masks and must never
# be written onto a real row.
SUPPRESSION_TYPES: tuple[str, ...] = ("unknown", "primary_like", "complementary_like")

SOURCE_REGISTRY_SCHEMA: dict[str, pl.DataType] = {
    "source_id": pl.String,
    "agency": pl.String,
    "dataset": pl.String,
    "landing_url": pl.String,
    "endpoint_pattern": pl.String,
    "access_status": pl.String,
    "frequency": pl.String,
    "reference_period": pl.String,
    "geography": pl.String,
    "industry_detail": pl.String,
    "ownership": pl.String,
    "statistical_unit": pl.String,
    "employment_concept": pl.String,
    "size_dimension": pl.String,
    "disclosure_regime": pl.String,
    "revision_policy": pl.String,
    "model_role": pl.String,
    "limitations": pl.String,
}

SOURCE_SNAPSHOT_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "source_id": pl.String,
    "request_url_or_file": pl.String,
    "request_parameters_json": pl.String,
    "retrieved_at_utc": pl.String,
    "source_publication_date": pl.String,
    "reference_start": pl.String,
    "reference_end": pl.String,
    "release_status": pl.String,
    "naics_vintage": pl.String,
    "schema_fingerprint": pl.String,
    "content_sha256": pl.String,
    "byte_count": pl.Int64,
    "http_status": pl.Int64,
    "parser_version": pl.String,
    "raw_path": pl.String,
}

QCEW_MONTHLY_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "release_vintage": pl.String,
    "release_status": pl.String,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "area_fips": pl.String,
    "area_type": pl.String,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "ownership_code": pl.String,
    "aggregation_level": pl.String,
    "size_code": pl.String,
    "qtrly_establishments": pl.Int64,
    "employment_raw": pl.String,
    "employment_value": pl.Int64,
    "wages_raw": pl.String,
    "wages_value": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
    "is_published_numeric_zero": pl.Boolean,
    "is_true_zero": pl.Boolean,
    "source_row_hash": pl.String,
    # This package's addition, not a field §7.3 names: INV-009 requires the real-world suppression
    # type to be recorded as `unknown`, and a default that exists only in Stage 4 could not be
    # distinguished from a value Stage 4 chose.
    "suppression_type": pl.String,
}

QCEW_NATIONAL_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "size_class": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
}

CBP_STATE_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "legal_form_code": pl.String,
    "size_code": pl.String,
    "size_label": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "employment_flag": pl.String,
    "employment_noise_range": pl.String,
    "disclosure_status": pl.String,
    "disclosure_regime": pl.String,
    "reference_period": pl.String,
}

BRIDGE_SCHEMA: dict[str, pl.DataType] = {
    "bridge_id": pl.String,
    "source_concept": pl.String,
    "target_concept": pl.String,
    "valid_start": pl.String,
    "valid_end": pl.String,
    "method": pl.String,
    "uncertainty_treatment": pl.String,
    "verification_status": pl.String,
}


def schema_fingerprint(schema: dict[str, pl.DataType]) -> str:
    """A sha256 over the schema's ordered (name, dtype) pairs."""
    payload = json.dumps([[name, str(dtype)] for name, dtype in schema.items()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_frame(frame: pl.DataFrame, schema: dict[str, pl.DataType], name: str) -> None:
    """Raise SchemaMismatchError unless the frame's columns and dtypes match the schema exactly."""
    missing = [c for c in schema if c not in frame.columns]
    extra = [c for c in frame.columns if c not in schema]
    if missing or extra:
        raise SchemaMismatchError(f"{name}: missing={missing} extra={extra}")
    wrong = [
        (c, str(schema[c]), str(frame.schema[c])) for c in schema if frame.schema[c] != schema[c]
    ]
    if wrong:
        raise SchemaMismatchError(f"{name}: dtype mismatches {wrong}")
