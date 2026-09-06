"""The substitute allocation anchor: the gate that admits it and the residual it yields."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.errors import ConceptViolationError, UniverseClosureError
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

    `anchored` IS the gap being zero (anchor.py: `establishment_gap == 0 and residual >= 0`), and
    asserting it here is safe because the frame below is synthetic -- the gap is fixture-designed,
    not measured, and no BLS revision can move it. The anti-drift rule binds assertions on live
    data; see `tests/integration/test_d1_baselines.py` for the same claim made structurally.

    2024-03 closes and 2024-04 does not, so `anchored` is asserted as the fixture's own designed
    pattern -- the evidence that a failing month survives into the artifact rather than
    disappearing before `assert_universe_closes` sees it.
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
            # One establishment the state table does not carry: the gate must fail this month,
            # and employment is left alone so `residual >= 0` and the gap is the only cause.
            "qtrly_establishments": 7,
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
    assert audit["reference_month"].to_list() == ["2024-03", "2024-04"]
    assert audit["anchored"].to_list() == [True, False]


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


def test_a_national_month_with_no_state_rows_is_still_gated(make_monthly) -> None:
    """The audit is driven by the panel's months, not by the partition's keys.

    `observed_partition` emits a key only for months that have state rows, so a month publishing
    a national row against no state rows at all would be absent from the audit entirely and the
    gate would pass over it in silence — the shape most likely to mean a truncated ingest. It
    appears with a zero state sum and a gap equal to the national count, which is a failure.
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
            "employment_value": 100,
            "qtrly_establishments": 999,
        },
    )
    audit = closure_audit(monthly, observed_partition(monthly))
    assert audit.height == 2
    assert "2024-04" in audit["reference_month"].to_list()
    with pytest.raises(UniverseClosureError, match="2024-04"):
        assert_universe_closes(audit)


def test_a_null_employment_in_the_disclosed_set_halts_rather_than_summing_as_zero(
    make_monthly,
) -> None:
    """`fill_null(0)` reads as null handling but is a no-op: Polars' `sum()` already skips nulls.

    A suppressed cell mistakenly placed in `disclosed` would therefore contribute 0 and inflate
    R_t by its true employment, handing the anchor employees no cell in the missing set can
    receive. The mask-parameterised signature hands this partition to arbitrary callers, so the
    D_t/M_t confusion is refused rather than trusted not to happen.
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
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "employment_value": None,
            "qtrly_establishments": 6,
            "observation_status": "suppressed",
        },
    )
    states = monthly.filter(pl.col("area_type") == "state")
    confused = Partition(disclosed=states, missing=states.head(0))
    with pytest.raises(ConceptViolationError, match="02"):
        national_residual(monthly, confused, reference_month="2024-03")


def test_a_partition_from_another_month_is_refused(make_monthly) -> None:
    """A partition belongs to exactly one month, and nothing but this check says so.

    `_disclosed_sum` sums whatever frame it is handed, and `reference_month` was used only to find
    the national row. A partition spanning two months therefore returned a residual computed
    against the wrong disclosed total, silently — the same D_t confusion the null guard refuses,
    in a different shape.
    """
    monthly = make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 300,
            "qtrly_establishments": 12,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 100,
            "qtrly_establishments": 6,
        },
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-04",
            "employment_value": 300,
            "qtrly_establishments": 12,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-04",
            "employment_value": 100,
            "qtrly_establishments": 6,
        },
    )
    both_months = monthly.filter(pl.col("area_type") == "state")
    straddling = Partition(disclosed=both_months, missing=both_months.head(0))
    with pytest.raises(ConceptViolationError, match="2024-04"):
        national_residual(monthly, straddling, reference_month="2024-03")
