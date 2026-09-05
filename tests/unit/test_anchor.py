"""The substitute allocation anchor: the gate that admits it and the residual it yields."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.errors import UniverseClosureError
from logging_employment.reconcile.anchor import (
    Partition,
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)


def test_the_disclosed_set_includes_true_zero_cells(make_monthly) -> None:
    """A published zero is disclosed, not missing.

    Selecting on `observation_status == 'observed'` alone drops every `true_zero` cell into the
    missing set, where it would be imputed despite having been published. On the D1 window that
    is 27 cells.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 100,
            "qtrly_establishments": 12,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "employment_value": 60,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "employment_value": 0,
            "qtrly_establishments": 2,
            "observation_status": "true_zero",
        },
        {
            "state_fips": "04",
            "area_fips": "04000",
            "employment_value": None,
            "qtrly_establishments": 4,
            "observation_status": "suppressed",
        },
    )
    part = observed_partition(monthly)["2024-03"]
    assert sorted(part.disclosed["state_fips"].to_list()) == ["01", "02"]
    assert part.missing["state_fips"].to_list() == ["04"]


def test_the_residual_is_the_national_total_net_of_every_disclosed_cell(make_monthly) -> None:
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 100,
            "qtrly_establishments": 12,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "employment_value": 60,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "employment_value": 0,
            "qtrly_establishments": 2,
            "observation_status": "true_zero",
        },
        {
            "state_fips": "04",
            "area_fips": "04000",
            "employment_value": None,
            "qtrly_establishments": 4,
            "observation_status": "suppressed",
        },
    )
    part = observed_partition(monthly)["2024-03"]
    anchor = national_residual(monthly, part, reference_month="2024-03")
    assert anchor.residual == 40.0
    assert anchor.missing_cells == ("04",)
    assert anchor.anchor_basis == "declared_national_total"


def test_national_residual_never_reads_observation_status(make_monthly) -> None:
    """The mask-parameterised signature, asserted rather than documented.

    Stage 4 recomputes the residual from a pseudo-suppression mask. If `national_residual` read
    the partition from the table it would force Stage 4 to mutate `qcew_monthly`. Here a cell
    marked `observed` is passed in the missing set, and the residual must honour the argument.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 100,
            "qtrly_establishments": 12,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "employment_value": 60,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "employment_value": 30,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
    )
    states = monthly.filter(pl.col("area_type") == "state")
    masked = Partition(
        disclosed=states.filter(pl.col("state_fips") == "01"),
        missing=states.filter(pl.col("state_fips") == "02"),
    )
    anchor = national_residual(monthly, masked, reference_month="2024-03")
    assert anchor.residual == 40.0
    assert anchor.missing_cells == ("02",)


def test_a_nonzero_establishment_gap_halts_the_run(make_monthly) -> None:
    """§18.3: fail rather than guess when source universes cannot be reconciled.

    This is a whole-run halt, not a per-month decline. A gap means the national row contains
    something the state table does not, which makes every month's residual suspect.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 100,
            "qtrly_establishments": 99,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "employment_value": 60,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
    )
    audit = closure_audit(monthly, observed_partition(monthly))
    with pytest.raises(UniverseClosureError) as excinfo:
        assert_universe_closes(audit)
    assert "2024-03" in str(excinfo.value)
    assert "93" in str(excinfo.value)


def test_the_gate_is_evaluated_for_every_month_not_only_failing_ones(make_monthly) -> None:
    """The audit is a diffable artifact: every month appears, passing or not.

    Asserted on structure, never on the gap being zero -- the anti-drift rule. A revision that
    moves a published establishment count must break this test for the right reason or not at all.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 100,
            "qtrly_establishments": 6,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 60,
            "qtrly_establishments": 6,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-04",
            "employment_value": 90,
            "qtrly_establishments": 6,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-04",
            "employment_value": 50,
            "qtrly_establishments": 6,
        },
    )
    audit = closure_audit(monthly, observed_partition(monthly))
    assert audit.height == 2
    assert set(audit.columns) >= {"establishment_gap", "publishing_area_count", "anchored"}
    assert audit["anchored"].all()


def test_a_month_with_no_missing_cells_yields_no_anchor(make_monthly) -> None:
    """Nothing to allocate is not a failure; it is a month that needs no anchor."""
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 60,
            "qtrly_establishments": 6,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "employment_value": 60,
            "qtrly_establishments": 6,
            "observation_status": "observed",
        },
    )
    part = observed_partition(monthly)["2024-03"]
    anchor = national_residual(monthly, part, reference_month="2024-03")
    assert anchor.missing_cells == ()
    assert anchor.residual == 0.0
