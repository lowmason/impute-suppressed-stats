"""The runner: one gate for the window, one row per (estimator, cell), declines included."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.runner import (
    FALLBACK_ORDER,
    REGISTRY,
    preferred_estimator,
    run_baselines,
)
from logging_employment.contracts import BASELINE_RESULT_SCHEMA, HarmonizedData
from logging_employment.errors import UniverseClosureError


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
