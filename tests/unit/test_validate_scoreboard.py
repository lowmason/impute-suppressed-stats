import polars as pl

from logging_employment.validate.metrics import decline_and_basis_report, point_metrics
from logging_employment.validate.scoreboard import build_scoreboard, preferred_baseline


def _scores():
    """Built by the emitters, never by hand.

    A hand-written metrics frame carrying all thirteen columns on point rows is a frame the harness
    never produces, and it hides the defect this fixture exists to catch: the two emitters have
    disjoint column sets, so a scoreboard that SELECTS the basis columns off point rows gets null.
    """
    truth = [100.0, 200.0]
    return pl.DataFrame(
        {
            "estimator_id": ["cbp_intensity"] * 2 + ["harvest_proportional"] * 2,
            "cell_id": ["c1", "c2"] * 2,
            "truth": truth * 2,
            "estimate": [110.0, 180.0, None, None],
            "decline_kind": [None, None, "by_design", "by_design"],
            "weight_basis": ["own_estimator", "establishment_fallback", "none", "none"],
        }
    )


def _metrics():
    scores = _scores()
    return pl.concat(
        [
            point_metrics(scores, regime="small_cell_biased", seed=1024, arm="state_total"),
            decline_and_basis_report(scores, regime="small_cell_biased", seed=1024),
        ],
        how="diagonal",
    )


def test_the_preferred_baseline_is_the_best_scoring_estimator_that_scored_anything():
    board = build_scoreboard(_metrics())
    assert preferred_baseline(board, regime="small_cell_biased") == "cbp_intensity"


def test_an_estimator_that_scored_nothing_can_never_be_preferred():
    """A null WAPE must not sort to the front as if it were zero error."""
    board = build_scoreboard(_metrics())
    assert preferred_baseline(board, regime="small_cell_biased") != "harvest_proportional"


def test_every_scoreboard_row_carries_its_denominator_and_basis_split():
    board = build_scoreboard(_metrics())
    for column in ("denominator", "n_scored", "n_own_estimator", "n_establishment_fallback"):
        assert column in board.columns
    assert board["denominator"].null_count() == 0


def test_the_own_fallback_split_survives_the_concat():
    """The regression guard. Before the join, these were null on every row.

    `point_metrics` does not emit the basis columns and `decline_and_basis_report` does not emit
    `metric_name`; a diagonal concat leaves each null on the other's rows. A scoreboard that
    selects rather than joins reports `n_own_estimator = None` for every estimator, which is
    exactly the signal §10.3 variant 5's composed refusals need.
    """
    board = build_scoreboard(_metrics())
    assert board["n_own_estimator"].null_count() == 0
    assert board["n_establishment_fallback"].null_count() == 0
    row = board.filter(pl.col("estimator_id") == "cbp_intensity").row(0, named=True)
    assert row["n_own_estimator"] == 1
    assert row["n_establishment_fallback"] == 1


def test_a_regime_with_no_scoring_estimator_has_no_preferred_baseline():
    empty = _metrics().with_columns(pl.lit(None, dtype=pl.Float64).alias("value"))
    assert preferred_baseline(build_scoreboard(empty), regime="small_cell_biased") is None
