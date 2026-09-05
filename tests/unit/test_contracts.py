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
        "is_true_zero", "source_row_hash", "suppression_type",
    ]
    # fmt: on
    assert list(contracts.QCEW_MONTHLY_SCHEMA) == expected


def test_suppression_type_is_this_packages_addition_not_a_field_the_spec_names() -> None:
    # §7.3 does not list it. INV-009 requires the value, and a column introduced downstream could
    # not be told apart from one Stage 4's synthetic masks had set.
    assert contracts.QCEW_MONTHLY_SCHEMA["suppression_type"] == pl.String
    assert list(contracts.QCEW_MONTHLY_SCHEMA)[-1] == "suppression_type"
    assert contracts.SUPPRESSION_TYPES == ("unknown", "primary_like", "complementary_like")


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


def test_the_four_schemas_carry_exactly_the_fields_the_spec_lists() -> None:
    assert list(contracts.TARGET_CELL_SCHEMA) == [
        "cell_id",
        "state_fips",
        "reference_month",
        "size_concept",
        "size_class",
        "ownership_code",
        "industry_code",
        "naics_vintage",
        "observation_status",
        "observed_value",
        "source_snapshot_id",
        "qcew_disclosure_code",
    ]
    assert list(contracts.CONSTRAINT_ROW_SCHEMA) == [
        "constraint_id",
        "component_id",
        "constraint_class",
        "relation",
        "rhs_lower",
        "rhs_upper",
        "is_hard",
        "period_scope",
        "geography_scope",
        "industry_scope",
        "ownership_scope",
        "source_snapshot_ids",
        "provenance_text",
        "vintage_compatibility_status",
    ]
    assert list(contracts.CONSTRAINT_COEFFICIENT_SCHEMA) == [
        "constraint_id",
        "cell_id",
        "coefficient",
    ]
    assert list(contracts.DETERMINISTIC_BOUNDS_SCHEMA) == [
        "cell_id",
        "component_id",
        "rank",
        "nullity",
        "lp_lower",
        "lp_upper",
        "milp_lower",
        "milp_upper",
        "selected_lower",
        "selected_upper",
        "bound_status",
        "exactly_identified",
        "integer_exactly_identified",
        "solver_status",
        "solver_tolerance",
        "constraint_set_hash",
    ]


def test_only_the_first_two_constraint_classes_may_be_hard() -> None:
    # §7.8: "Only the first two may have is_hard=true."
    assert contracts.CONSTRAINT_CLASSES == (
        "public_accounting_fact",
        "definitional_support",
        "empirical_measurement",
        "modeling_assumption",
        "sensitivity_assumption",
    )
    assert contracts.HARD_ELIGIBLE_CLASSES == contracts.CONSTRAINT_CLASSES[:2]


def test_the_seven_bound_statuses_are_the_ones_7_10_suggests() -> None:
    assert contracts.BOUND_STATUSES == (
        "observed",
        "exactly_recoverable",
        "partially_identified",
        "model_estimable",
        "model_only",
        "unbounded",
        "infeasible",
    )


def test_an_assumed_threshold_is_an_evidence_kind_so_it_can_be_refused_by_name() -> None:
    assert "assumed_threshold" in contracts.EVIDENCE_KINDS
    assert contracts.RELATIONS == ("eq", "le", "ge", "range", "integrality")


def test_harmonized_data_loads_the_four_stage_one_tables(tmp_path) -> None:
    for name, schema in (
        ("qcew_monthly", {"reference_month": pl.String}),
        ("qcew_national_size", {"reference_year": pl.Int64}),
        ("cbp_state_size", {"reference_year": pl.Int64}),
        ("bridge", {"bridge_id": pl.String}),
    ):
        pl.DataFrame(schema=schema).write_parquet(tmp_path / f"{name}.parquet")
    data = contracts.HarmonizedData.load(tmp_path)
    assert data.qcew_monthly.height == 0
    assert data.bridge.columns == ["bridge_id"]


def test_a_missing_harmonized_table_names_the_path_rather_than_raising_from_polars(
    tmp_path,
) -> None:
    with pytest.raises(FileNotFoundError, match="qcew_monthly.parquet"):
        contracts.HarmonizedData.load(tmp_path)


def test_the_new_schemas_have_distinct_fingerprints() -> None:
    prints = {
        contracts.schema_fingerprint(s)
        for s in (
            contracts.TARGET_CELL_SCHEMA,
            contracts.CONSTRAINT_ROW_SCHEMA,
            contracts.CONSTRAINT_COEFFICIENT_SCHEMA,
            contracts.DETERMINISTIC_BOUNDS_SCHEMA,
        )
    }
    assert len(prints) == 4


def test_the_baseline_result_schema_carries_per_cell_weight_provenance() -> None:
    """A reader must never mistake a fallback-weighted cell for an own-estimator one."""
    assert "weight_basis" in contracts.BASELINE_RESULT_SCHEMA
    assert "anchor_basis" in contracts.BASELINE_RESULT_SCHEMA
    assert "reconciliation_status" in contracts.BASELINE_RESULT_SCHEMA


def test_reconciliation_status_is_distinct_from_hard_constraint_satisfaction() -> None:
    """INV-002 binds hard public accounting constraints; the anchor is a modeling assumption.

    The enum must be able to say "reconciled to a declared anchor" without that reading as
    "satisfies a hard constraint", or INV-008's separation collapses.
    """
    assert "anchored_and_reconciled" in contracts.RECONCILIATION_STATUSES
    assert "declined" in contracts.RECONCILIATION_STATUSES
    assert "hard_constraint_satisfied" not in contracts.RECONCILIATION_STATUSES


def test_a_declined_baseline_row_is_representable() -> None:
    """A decline is a visible row, never an absent one."""
    assert contracts.BASELINE_RESULT_SCHEMA["decline_reason"] == pl.String
    assert contracts.BASELINE_RESULT_SCHEMA["estimate"] == pl.Float64
