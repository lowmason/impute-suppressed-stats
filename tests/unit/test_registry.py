"""The source registry carries §7.1's fields and refuses free-floating disclosure prose."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from logging_employment.contracts import SOURCE_REGISTRY_SCHEMA
from logging_employment.registry.loader import load_registry, registry_frame
from logging_employment.registry.models import SourceRegistryRow
from logging_employment.registry.validation import verify

SEED = (
    Path(__file__).resolve().parents[2] / "src" / "logging_employment" / "registry" / "sources.yaml"
)


def _row(**overrides: str) -> SourceRegistryRow:
    base = {
        "source_id": "qcew",
        "agency": "BLS",
        "dataset": "QCEW quarterly industry data",
        "landing_url": "https://www.bls.gov/cew/",
        "endpoint_pattern": "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv",
        "access_status": "verified",
        "frequency": "quarterly",
        "reference_period": "calendar quarter, monthly employment fields",
        "geography": "national, state, MSA, county",
        "industry_detail": "NAICS 6-digit",
        "ownership": "all ownership codes; 5 = Private",
        "statistical_unit": "establishment",
        "employment_concept": "covered wage-and-salary jobs",
        "size_dimension": "none in the quarterly file (size_code 0 only)",
        "disclosure_regime": "qcew_disclosure_code_v1",
        "revision_policy": "finalized with the following year's Q1 release",
        "model_role": "hard constraint source",
        "limitations": "cells with disclosure_code N carry no employment value",
    }
    base.update(overrides)
    return SourceRegistryRow(**base)


def test_all_eighteen_fields_are_required() -> None:
    assert set(SourceRegistryRow.model_fields) == set(SOURCE_REGISTRY_SCHEMA)


def test_access_status_is_an_enum() -> None:
    with pytest.raises(ValidationError):
        _row(access_status="probably_fine")


def test_registry_frame_matches_the_declared_schema() -> None:
    frame = registry_frame([_row()])
    assert frame.schema == pl.Schema(SOURCE_REGISTRY_SCHEMA)


def test_verify_flags_a_versionless_disclosure_regime() -> None:
    problems = verify([_row(disclosure_regime="values are protected somehow")])
    assert any("disclosure_regime" in p for p in problems)


def test_verify_flags_a_duplicate_source_id() -> None:
    problems = verify([_row(), _row()])
    assert any("duplicate" in p for p in problems)


def test_the_seed_registry_is_sound() -> None:
    rows = load_registry(SEED)
    assert {r.source_id for r in rows} == {"qcew", "qcew_size", "cbp"}
    assert verify(rows) == []
