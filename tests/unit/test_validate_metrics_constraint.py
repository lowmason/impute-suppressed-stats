import polars as pl

from logging_employment.validate.metrics import decline_and_basis_report


def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["share_break_adjusted"] * 4 + ["harvest_proportional"] * 2,
            "cell_id": ["c1", "c2", "c3", "c4", "c1", "c2"],
            "estimate": [1.0, 2.0, 3.0, 4.0, None, None],
            "decline_kind": [None] * 4 + ["by_design"] * 2,
            "weight_basis": [
                "own_estimator",
                "establishment_fallback",
                "establishment_fallback",
                "establishment_fallback",
                "none",
                "none",
            ],
        }
    )


def test_a_composed_refusal_is_invisible_to_decline_counts_but_visible_in_weight_basis():
    """Plan 10's refusals compose. Decline counts alone report full coverage."""
    out = decline_and_basis_report(_scores(), regime="r", seed=1, arm="state_total")
    row = out.filter(pl.col("estimator_id") == "share_break_adjusted").row(0, named=True)
    assert row["n_declined_by_design"] == 0
    assert row["n_declined_data_gap"] == 0
    assert row["n_own_estimator"] == 1
    assert row["n_establishment_fallback"] == 3


def test_every_report_row_states_its_denominator():
    out = decline_and_basis_report(_scores(), regime="r", seed=1, arm="state_total")
    assert out["denominator"].null_count() == 0
    assert set(out["denominator_basis"].unique().to_list()) == {"masked_cell_rows"}


def test_a_fully_declining_estimator_is_reported_as_declining_not_absent():
    out = decline_and_basis_report(_scores(), regime="r", seed=1, arm="state_total")
    row = out.filter(pl.col("estimator_id") == "harvest_proportional").row(0, named=True)
    assert row["n_declined_by_design"] == 2
    assert row["n_scored"] == 0
