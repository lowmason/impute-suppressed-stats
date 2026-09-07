"""The runner: one gate for the window, one row per (estimator, cell), declines included."""

from __future__ import annotations

from unittest import mock

import polars as pl
import pytest

from logging_employment.baselines import runner
from logging_employment.baselines.runner import (
    FALLBACK_ORDER,
    REGISTRY,
    preferred_estimator,
    run_baselines,
)
from logging_employment.contracts import (
    BASELINE_RESULT_SCHEMA,
    HarmonizedData,
    assert_declared_provenance,
)
from logging_employment.errors import ConceptViolationError, UniverseClosureError
from logging_employment.reconcile.allocate import Weights


def test_the_fallback_order_is_the_specs_four_rungs_in_its_order() -> None:
    """§10.8 lists four, and §10.1 is deliberately not among them."""
    assert FALLBACK_ORDER == (
        "cbp_intensity",
        "constrained_regression",
        "share_last_observed",
        "establishment_proportional",
    )
    assert "equal_residual" not in FALLBACK_ORDER


def test_the_registry_carries_every_section_10_estimator() -> None:
    ids = {e.estimator_id for e in REGISTRY}
    assert "equal_residual" in ids
    assert "establishment_proportional" in ids
    assert "cbp_intensity" in ids
    assert "harvest_proportional" in ids
    assert "constrained_regression" in ids
    assert len([i for i in ids if i.startswith("share_")]) == 5


def test_a_broken_universe_halts_the_whole_run_not_one_month(
    harmonized_toy, appendix_a_config
) -> None:
    """§18.3: "The pipeline MUST fail rather than guess when ... source universes cannot be
    reconciled." A gap means every month's residual is suspect, not just the failing month's."""
    broken = harmonized_toy.qcew_monthly.with_columns(
        pl.when(pl.col("area_type") == "national")
        .then(pl.col("qtrly_establishments") + 7)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    data = HarmonizedData(
        broken,
        harmonized_toy.qcew_national_size,
        harmonized_toy.cbp_state_size,
        harmonized_toy.bridge,
    )
    with pytest.raises(UniverseClosureError):
        run_baselines(data, appendix_a_config)


def test_a_decline_is_a_row_not_an_absence(harmonized_toy, appendix_a_config) -> None:
    """A silent NaN or a dropped row is indistinguishable from a bug."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    harvest = results.filter(pl.col("estimator_id") == "harvest_proportional")
    assert harvest.height > 0
    assert harvest["reconciliation_status"].unique().to_list() == ["declined"]
    assert harvest["decline_reason"].null_count() == 0
    assert harvest["estimate"].null_count() == harvest.height


def test_every_running_estimator_sums_to_the_residual(harmonized_toy, appendix_a_config) -> None:
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    totals = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual")
    )
    for row in totals.iter_rows(named=True):
        assert row["total"] == pytest.approx(row["residual"], abs=1e-6)


def test_the_results_match_the_declared_schema(harmonized_toy, appendix_a_config) -> None:
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert list(results.columns) == list(BASELINE_RESULT_SCHEMA)


def test_the_preferred_estimator_follows_the_fallback_order(
    harmonized_toy, appendix_a_config
) -> None:
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert preferred_estimator(results) in FALLBACK_ORDER


def test_the_integer_estimates_balance_to_the_allocations_own_total(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.6 step 5: recheck every hard margin after rounding.

    The total must come from the allocation, not from `round(residual)`: `integerize` distributes
    exactly `total - sum(floors)` units, so a total that disagrees with the values by one unit
    leaves a unit unplaced. The two agree on D1 and diverge under a fractional Stage 4 residual.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    per_month = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("continuous"),
        pl.col("estimate_integer").sum().alias("integer"),
    )
    for row in per_month.iter_rows(named=True):
        assert row["integer"] == round(row["continuous"])


def test_every_row_carries_the_constraint_set_hash_it_was_produced_beside(
    harmonized_toy, appendix_a_config
) -> None:
    """A declared-but-always-null provenance column is worse than no column.

    §18.1's reproducibility check needs these estimates tied to the Stage 2 system they sit
    beside, so the hash is threaded in rather than left for a reader to infer from the directory.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config, constraint_set_hash="abc123")
    assert results["constraint_set_hash"].unique().to_list() == ["abc123"]


def test_weight_basis_counts_are_recoverable_from_the_results(
    harmonized_toy, appendix_a_config
) -> None:
    """Stage 4 must be able to tell a composite's score from a pure estimator's."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert set(ran["weight_basis"].unique().to_list()) <= {
        "own_estimator",
        "establishment_fallback",
    }


def test_an_unweightable_cell_declines_the_month_rather_than_killing_the_run(
    harmonized_toy, appendix_a_config
) -> None:
    """ "Decline, never fabricate" — but also never abort ten estimators over one cell.

    A suppressed cell with no usable establishment count makes `allocate` refuse the weight
    vector. That must land as a `declined` row for the estimator that hit it, leaving every other
    estimator and every other month intact. `qtrly_establishments` is >= 1 on all 1,227 suppressed
    cells today, but that is a measurement a revision can move, not an invariant.
    """
    jan = pl.col("reference_month") == "2023-01"
    # State 04 loses its establishment count, and the national row loses the same 5 — the universe
    # must still close, or the gate halts first and this tests nothing about the runner.
    broken = harmonized_toy.qcew_monthly.with_columns(
        pl.when(jan & (pl.col("state_fips") == "04"))
        .then(0)
        .when(jan & (pl.col("area_type") == "national"))
        .then(pl.col("qtrly_establishments") - 5)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    data = HarmonizedData(
        broken,
        harmonized_toy.qcew_national_size,
        harmonized_toy.cbp_state_size,
        harmonized_toy.bridge,
    )
    results, _ = run_baselines(data, appendix_a_config)
    assert set(results["estimator_id"].unique().to_list()) == {e.estimator_id for e in REGISTRY}
    jan = results.filter(pl.col("reference_month") == "2023-01")
    assert "declined" in jan["reconciliation_status"].unique().to_list()
    # The other month is untouched: one bad cell must not take the window with it.
    feb = results.filter(pl.col("reference_month") == "2023-02")
    assert "anchored_and_reconciled" in feb["reconciliation_status"].unique().to_list()


def test_a_typo_in_a_provenance_column_is_refused_rather_than_persisted() -> None:
    """The three enums were declared and enforced nothing.

    `BASELINE_RESULT_SCHEMA` checks dtypes only, so `pl.String` accepted any string: a typo in
    `weight_basis` -- which `run_baselines` copies from an estimator's own `outcome.basis` --
    reached `baseline_results.parquet` and passed every test in the suite.
    """
    row = {name: None for name in BASELINE_RESULT_SCHEMA}
    row.update(
        {
            "estimator_id": "x",
            "cell_id": "c",
            "state_fips": "01",
            "reference_month": "2017-01",
            "weight_basis": "own_estimator",
            "anchor_basis": "declared_national_total",
            "reconciliation_status": "anchored_and_reconciled",
        }
    )
    assert assert_declared_provenance(pl.DataFrame([row], schema=BASELINE_RESULT_SCHEMA)) is None

    for column, typo in (
        ("weight_basis", "own_estimatorr"),
        ("anchor_basis", "declared_national_totl"),
        ("reconciliation_status", "anchored_and_reconcild"),
    ):
        bad = dict(row)
        bad[column] = typo
        with pytest.raises(ConceptViolationError, match=column):
            assert_declared_provenance(pl.DataFrame([bad], schema=BASELINE_RESULT_SCHEMA))


def test_a_null_provenance_value_is_permitted_because_a_declining_row_has_none() -> None:
    """A declined row carries no estimate and no weight to describe, so null is not a typo."""
    row = {name: None for name in BASELINE_RESULT_SCHEMA}
    row["reconciliation_status"] = "declined"
    assert assert_declared_provenance(pl.DataFrame([row], schema=BASELINE_RESULT_SCHEMA)) is None


def test_an_estimators_own_refusal_is_recorded_as_by_design(
    harmonized_toy, appendix_a_config
) -> None:
    """T-3, call site 2: `estimator.weights` returned a `Decline`.

    §10.5's harvest baseline is the archetype. Its months are absent from the scored set for a
    reason no amount of better data changes, which is what separates it from the other two kinds.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    harvest = results.filter(pl.col("estimator_id") == "harvest_proportional")
    assert set(harvest["reconciliation_status"].unique().to_list()) == {"declined"}
    assert set(harvest["decline_kind"].unique().to_list()) == {"by_design"}


def test_a_missing_input_is_recorded_as_a_data_gap(harmonized_toy, appendix_a_config) -> None:
    """T-3, call site 1: `compose` raised because the fallback could not cover a cell.

    The kind is asserted, not the prose. A scoreboard that grouped on `decline_reason` would be
    grouping on a sentence that names a state fips.
    """
    jan = pl.col("reference_month") == "2023-01"
    broken = harmonized_toy.qcew_monthly.with_columns(
        pl.when(jan & (pl.col("state_fips") == "04"))
        .then(0)
        .when(jan & (pl.col("area_type") == "national"))
        .then(pl.col("qtrly_establishments") - 5)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    data = HarmonizedData(
        broken,
        harmonized_toy.qcew_national_size,
        harmonized_toy.cbp_state_size,
        harmonized_toy.bridge,
    )
    results, _ = run_baselines(data, appendix_a_config)
    declined = results.filter(
        (pl.col("reference_month") == "2023-01") & (pl.col("reconciliation_status") == "declined")
    )
    assert "data_gap" in declined["decline_kind"].unique().to_list()


def test_a_reconciliation_refusal_is_recorded_as_a_reconciliation_failure(
    harmonized_toy, appendix_a_config
) -> None:
    """T-3, call site 3: `allocate` refused the weight vector the estimator produced.

    Driven through a stub estimator rather than through data, because the shipped estimators reach
    `allocate` only with a domain-complete vector -- which is the property that makes this the
    third kind and not the second.
    """

    class _WrongDomain:
        """A stub that weights one cell too few, which is what `allocate` refuses by name."""

        estimator_id = "equal_residual"
        fallback_intensity = None

        def weights(self, context, anchor):
            """A vector missing the last cell, so `check_domain` refuses it."""
            return Weights(
                values=dict.fromkeys(anchor.missing_cells[:-1], 1.0),
                basis=dict.fromkeys(anchor.missing_cells[:-1], "own_estimator"),
            )

    with mock.patch.object(runner, "REGISTRY", (_WrongDomain(),)):
        results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert set(results["decline_kind"].unique().to_list()) == {"reconciliation_failure"}


def test_a_reconciled_row_carries_no_decline_kind(harmonized_toy, appendix_a_config) -> None:
    """The column describes a decline; a row that produced an estimate has none to describe."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert ran["decline_kind"].null_count() == ran.height


def test_no_declined_row_reaches_the_output_without_a_kind(
    harmonized_toy, appendix_a_config
) -> None:
    """R-COMP-9's exit criterion, over every estimator the registry ships."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    declined = results.filter(pl.col("reconciliation_status") == "declined")
    assert declined.height > 0
    assert declined["decline_kind"].null_count() == 0
