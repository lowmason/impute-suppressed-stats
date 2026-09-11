import polars as pl
import pytest

from logging_employment.baselines.runner import (
    FALLBACK_ORDER,
    FALLBACK_RUNGS,
    PREFERRABLE,
    REGISTRY,
)
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.metrics import decline_and_basis_report, point_metrics
from logging_employment.validate.scoreboard import (
    assert_scored_cells_are_primary_like,
    best_scoring_baseline,
    build_scoreboard,
    preferred_baseline,
)


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
            "state_fips": ["06", "41"] * 2,
            "reference_month": ["2019-03", "2019-03"] * 2,
            "truth": truth * 2,
            "estimate": [110.0, 180.0, None, None],
            "decline_kind": [None, None, "by_design", "by_design"],
            "weight_basis": ["own_estimator", "establishment_fallback", "none", "none"],
        }
    )


def _national():
    """R-S5G-4's denominator. One month, so every scored cell shares it."""
    return pl.DataFrame({"reference_month": ["2019-03"], "national_employment": [1000.0]})


def _metrics():
    scores = _scores()
    return pl.concat(
        [
            point_metrics(
                scores,
                regime="small_cell_biased",
                seed=1024,
                arm="state_total",
                national_totals=_national(),
            ),
            decline_and_basis_report(
                scores, regime="small_cell_biased", seed=1024, arm="state_total"
            ),
        ],
        how="diagonal",
    )


def test_the_preferred_baseline_is_the_best_scoring_hierarchy_member_that_scored_anything():
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


def _seed_metrics(
    estimates: dict[str, float | None], *, regime: str, seed: int, n_cells: int
) -> pl.DataFrame:
    """One seed's metrics for a hand-specified per-cell estimate, with truth fixed at 100.

    Built through the emitters for the same reason `_scores` is. Truth is constant so that WAPE is
    exactly `|estimate - 100| / 100` regardless of `n_cells`, which lets a test vary the DENOMINATOR
    (masked cell-rows) independently of the score it weights.
    """
    rows: dict[str, list[object]] = {
        "estimator_id": [],
        "cell_id": [],
        "state_fips": [],
        "reference_month": [],
        "truth": [],
        "estimate": [],
        "decline_kind": [],
        "weight_basis": [],
    }
    for estimator_id, estimate in estimates.items():
        for index in range(n_cells):
            rows["estimator_id"].append(estimator_id)
            rows["cell_id"].append(f"c{index}")
            rows["state_fips"].append("06")
            rows["reference_month"].append("2019-03")
            rows["truth"].append(100.0)
            rows["estimate"].append(estimate)
            rows["decline_kind"].append(None if estimate is not None else "by_design")
            rows["weight_basis"].append("own_estimator" if estimate is not None else "none")
    scores = pl.DataFrame(rows, schema_overrides={"estimate": pl.Float64})
    return pl.concat(
        [
            point_metrics(
                scores, regime=regime, seed=seed, arm="state_total", national_totals=_national()
            ),
            decline_and_basis_report(scores, regime=regime, seed=seed, arm="state_total"),
        ],
        how="diagonal",
    )


def test_an_estimator_outside_10_8s_hierarchy_is_never_the_preferred_baseline():
    """§10.1's equal allocation is a sanity check, so it cannot be what §13.10 gates against.

    The disqualification is structural -- it ignores the establishment counts QCEW publishes for
    suppressed cells -- so scoring best does not earn it the designation.
    """
    board = build_scoreboard(
        _seed_metrics(
            {"equal_residual": 105.0, "cbp_intensity": 120.0},
            regime="long_consecutive_runs",
            seed=1024,
            n_cells=4,
        )
    )
    assert preferred_baseline(board, regime="long_consecutive_runs") == "cbp_intensity"


def test_the_unrestricted_best_is_reported_beside_the_preferred_baseline():
    """The sanity check has to stay legible. §10.1 beating every rung says the establishment
    counts are not earning their place, which is a finding about the data -- discarding it would
    trade one silent resolution for another."""
    board = build_scoreboard(
        _seed_metrics(
            {"equal_residual": 105.0, "cbp_intensity": 120.0},
            regime="long_consecutive_runs",
            seed=1024,
            n_cells=4,
        )
    )
    assert best_scoring_baseline(board, regime="long_consecutive_runs") == "equal_residual"


def test_harvest_proportional_is_disqualified_by_10_5_even_when_it_scores_best():
    """Today it is excluded only incidentally, by `n_scored > 0`, because it declines by design on
    this window. §10.5 calls it "a benchmark, not a preferred standalone estimator", so the
    exclusion must survive a window where it does score."""
    board = build_scoreboard(
        _seed_metrics(
            {"harvest_proportional": 101.0, "cbp_intensity": 120.0},
            regime="small_cell_biased",
            seed=1024,
            n_cells=4,
        )
    )
    assert preferred_baseline(board, regime="small_cell_biased") == "cbp_intensity"


def test_a_10_3_share_variant_outside_the_four_rungs_can_still_be_preferred():
    """The guard against fixing this with a literal `FALLBACK_ORDER` membership test.

    Rung 3 is "reconciled historical shares" -- all five §10.3 variants -- and `FALLBACK_ORDER`
    names `share_last_observed` as ONE representative. Measured on D1's `whole_state_year_blocks`,
    `share_rolling_median` pools to 0.1342 against `share_last_observed`'s 0.1403, so a literal
    four-tuple restriction would name the worse of two estimators the hierarchy ranks equally.
    """
    board = build_scoreboard(
        _seed_metrics(
            {"share_rolling_median": 105.0, "cbp_intensity": 120.0},
            regime="whole_state_year_blocks",
            seed=1024,
            n_cells=4,
        )
    )
    assert preferred_baseline(board, regime="whole_state_year_blocks") == "share_rolling_median"


def test_the_preferred_baseline_pools_seeds_by_denominator_rather_than_taking_the_best_one():
    """The scoreboard is one row per (regime, seed, estimator); ranking its rows takes an argmin
    over seeds, which is an order statistic that rewards VARIANCE rather than accuracy.

    Weighted by masked cell-rows: `cbp_intensity` scores (0.0*1 + 0.5*9)/10 = 0.45 against
    `share_last_observed`'s (0.5*1 + 0.3*9)/10 = 0.32. The unweighted mean would invert that
    (0.25 against 0.40), so this pins the weight and not merely the fact of aggregating.
    """
    metrics = pl.concat(
        [
            _seed_metrics(
                {"cbp_intensity": 100.0, "share_last_observed": 150.0},
                regime="concentration_proxy",
                seed=1024,
                n_cells=1,
            ),
            _seed_metrics(
                {"cbp_intensity": 150.0, "share_last_observed": 130.0},
                regime="concentration_proxy",
                seed=2048,
                n_cells=9,
            ),
        ],
        how="diagonal",
    )
    board = build_scoreboard(metrics)
    assert preferred_baseline(board, regime="concentration_proxy") == "share_last_observed"


def test_a_regime_where_only_a_disqualified_estimator_scored_has_no_preferred_baseline():
    """The stated cost of the restriction, pinned so it stays visible.

    Measured on the D1 acceptance run this happens in zero of nine regimes -- every regime has
    hierarchy members scoring -- but the shape is reachable and §13.10 must read `None` rather
    than a sanity check.
    """
    board = build_scoreboard(
        _seed_metrics(
            {"equal_residual": 105.0}, regime="long_consecutive_runs", seed=1024, n_cells=4
        )
    )
    assert preferred_baseline(board, regime="long_consecutive_runs") is None
    assert best_scoring_baseline(board, regime="long_consecutive_runs") == "equal_residual"


def test_every_registry_estimator_is_classified_against_10_8s_hierarchy():
    """A new estimator must be placed deliberately, not inherit a default.

    `PREFERRABLE` is the complement of an explicit denylist, so an estimator added to `REGISTRY`
    without a decision would silently become gate-eligible. This is the assertion that stops it.
    """
    assert PREFERRABLE == frozenset(
        {
            "cbp_intensity",
            "constrained_regression",
            "share_last_observed",
            "share_same_month_prior_year",
            "share_rolling_median",
            "share_exponentially_weighted",
            "share_break_adjusted",
            "establishment_proportional",
        }
    )
    registry_ids = {estimator.estimator_id for estimator in REGISTRY}
    assert registry_ids - PREFERRABLE == {"equal_residual", "harvest_proportional"}
    # The other direction, which the line above does not cover: a rung naming an id that no
    # estimator answers to would never match, silently making that rung member ineligible forever.
    assert PREFERRABLE <= registry_ids


def test_each_named_rung_representative_sits_in_the_rung_it_represents():
    """`FALLBACK_ORDER` and `FALLBACK_RUNGS` describe one hierarchy and must not drift apart.

    `FALLBACK_ORDER` is §10.8's four names in §10.8's order; `FALLBACK_RUNGS` is what each of those
    names stands for. Positional alignment is the check -- a subset test would pass even if a
    representative were filed under the wrong rung, which is what decides ties.
    """
    assert len(FALLBACK_ORDER) == len(FALLBACK_RUNGS)
    for representative, rung in zip(FALLBACK_ORDER, FALLBACK_RUNGS, strict=True):
        assert representative in rung
    assert set(FALLBACK_ORDER) <= PREFERRABLE


def test_estimators_that_pool_to_the_same_score_are_broken_by_10_8s_rung_order():
    """The tie is measured, not hypothetical: on D1's `long_consecutive_runs`,
    `establishment_proportional` and `share_same_month_prior_year` both pool to 0.4229.

    §10.8 is a preference order, so rung 3 takes it from rung 4. Without a tiebreak the winner is
    whatever `group_by` happened to emit first. Note the two sort the other way alphabetically, so
    this distinguishes the rung order from an id sort rather than merely pinning determinism.
    """
    board = build_scoreboard(
        _seed_metrics(
            {"establishment_proportional": 120.0, "share_same_month_prior_year": 120.0},
            regime="long_consecutive_runs",
            seed=1024,
            n_cells=4,
        )
    )
    assert (
        preferred_baseline(board, regime="long_consecutive_runs") == "share_same_month_prior_year"
    )


def _board_with_arms(*arms: str) -> pl.DataFrame:
    """One regime's board replicated across `arms`, which is the shape the guard exists to refuse.

    Built by relabelling a real board rather than by concatenating two `_seed_metrics` calls: the
    declines family carries no `mask_arm`, so emitting two arms through the emitters would give
    `build_scoreboard`'s join two basis rows per key and fan the board out. The guard's job is to
    refuse a multi-arm board however it arose.
    """
    board = build_scoreboard(
        _seed_metrics(
            {"cbp_intensity": 120.0, "share_last_observed": 130.0},
            regime="small_cell_biased",
            seed=1024,
            n_cells=4,
        )
    )
    return pl.concat(
        [board.with_columns(pl.lit(arm).alias("mask_arm")) for arm in arms], how="vertical"
    )


def test_a_complementary_like_scored_row_is_refused():
    """§13.10 gates "on primary-like masks" and the scoreboard carries no label to scope by, so the
    scoping is a PRECONDITION on what may be scored rather than a split of what was.

    Enforced rather than assumed: it currently holds because every selector in `validate.regimes`
    emits primary-like targets, and an invariant resting on which selectors happen to be wired is
    the silent failure this refuses.
    """
    scored = pl.DataFrame({"suppression_type": ["primary_like", "complementary_like"]})
    with pytest.raises(ConceptViolationError):
        assert_scored_cells_are_primary_like(scored)


def test_an_all_primary_like_scored_frame_passes():
    """The guard must permit the ordinary case; the assertion is that it does not raise."""
    scored = pl.DataFrame({"suppression_type": ["primary_like"] * 3})
    assert_scored_cells_are_primary_like(scored)


def test_a_scored_frame_missing_the_label_column_is_refused():
    """Absence must not read as compliance. A frame that dropped `suppression_type` upstream would
    otherwise satisfy an `is_in` check vacuously, which is how the label got lost in the first
    place -- the emitters group without it and nothing noticed."""
    with pytest.raises(ConceptViolationError):
        assert_scored_cells_are_primary_like(pl.DataFrame({"estimator_id": ["cbp_intensity"]}))


def test_the_refusal_names_the_work_that_would_make_it_legal():
    """A precondition that fires without saying what to do sends the next reader to git blame."""
    scored = pl.DataFrame({"suppression_type": ["complementary_like"]})
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        assert_scored_cells_are_primary_like(scored)


def test_preferred_baseline_refuses_a_scoreboard_carrying_two_mask_arms():
    """The sibling silent-pooling path. `mask_arm` is already a scoreboard column and `_best`
    pooled across it, so a second scoring arm would mix state totals with national size classes
    into one WAPE -- the same shape as the seed argmin, one level up."""
    with pytest.raises(ConceptViolationError):
        preferred_baseline(
            _board_with_arms("state_total", "national_size"), regime="small_cell_biased"
        )


def test_best_scoring_baseline_refuses_a_scoreboard_carrying_two_mask_arms():
    with pytest.raises(ConceptViolationError):
        best_scoring_baseline(
            _board_with_arms("state_total", "national_size"), regime="small_cell_biased"
        )


def test_a_single_arm_scoreboard_is_still_ranked():
    """The guard must refuse ambiguity, not the ordinary case."""
    board = _board_with_arms("state_total")
    assert preferred_baseline(board, regime="small_cell_biased") == "cbp_intensity"


def _board_with_an_arm_per_estimator(
    arms: dict[str, dict[str, float | None]], *, regime: str
) -> pl.DataFrame:
    """A board whose estimators sit on DIFFERENT arms, which `_board_with_arms` cannot express.

    That helper replicates one estimator set across every arm, so `PREFERRABLE` selects the same
    names on both and the eligibility filter cannot hide an arm from the guard. The shape that
    hides one is the asymmetric board: §10.8's hierarchy on one arm, something else on a second.
    Relabelled rather than emitted through the emitters twice, for `_board_with_arms`' reason --
    the declines family carries no `mask_arm`, so two arms through the emitters fan the join out.
    """
    return pl.concat(
        [
            build_scoreboard(
                _seed_metrics(estimates, regime=regime, seed=1024, n_cells=4)
            ).with_columns(pl.lit(arm).alias("mask_arm"))
            for arm, estimates in arms.items()
        ],
        how="vertical",
    )


def test_the_arm_refusal_does_not_depend_on_which_wrapper_asks():
    """The guard ran AFTER the `eligible` narrowing, so it fired for one caller and not the other.

    `best_scoring_baseline` passes `eligible=None` and saw both arms; `preferred_baseline` -- the
    wrapper roadmap Stage 4 point (3) tells Stage 5 to gate on -- saw only §10.8's members, so a
    second arm carrying nothing but non-hierarchy estimators was invisible to it. It returned
    `cbp_intensity`, a name pooled from a board spanning two arms, while its sibling raised on the
    same frame. The guarantee is a property of the board, not of the caller.
    """
    board = _board_with_an_arm_per_estimator(
        {"state_total": {"cbp_intensity": 110.0}, "national_size": {"equal_residual": 105.0}},
        regime="small_cell_biased",
    )
    with pytest.raises(ConceptViolationError, match="mask arm"):
        best_scoring_baseline(board, regime="small_cell_biased")
    with pytest.raises(ConceptViolationError, match="mask arm"):
        preferred_baseline(board, regime="small_cell_biased")


def test_a_second_arm_whose_estimators_all_declined_is_still_a_second_arm():
    """The discriminator between checking before the eligibility filter and before ALL of them.

    `share_last_observed` is IN `PREFERRABLE`, so eligibility is not what hides this arm --
    `n_scored > 0` is. An estimator that declined every cell still gets a wape row
    (`metrics.point_metrics` emits every point name null rather than emitting nothing), and that
    row carries the arm. Dropping it before the guard looks means a run scored on two arms reads
    as single-arm whenever the second one happened to decline.
    """
    board = _board_with_an_arm_per_estimator(
        {
            "state_total": {"cbp_intensity": 110.0},
            "national_size": {"share_last_observed": None},
        },
        regime="small_cell_biased",
    )
    with pytest.raises(ConceptViolationError, match="mask arm"):
        preferred_baseline(board, regime="small_cell_biased")
    with pytest.raises(ConceptViolationError, match="mask arm"):
        best_scoring_baseline(board, regime="small_cell_biased")


def test_a_two_arm_regime_where_nothing_scored_is_refused_rather_than_read_as_no_comparand():
    """`None` means "no hierarchy member scored", which §13.10 reads as "no comparand". A two-arm
    board is a different thing -- a run whose scoring is ambiguous -- and returning `None` for it
    hands the gate the "scored, nothing wrong" reading this harness refuses everywhere else.

    It took that path because every candidate was filtered out before the guard ran, so the
    `height == 0` early return fired first.
    """
    board = _board_with_an_arm_per_estimator(
        {
            "state_total": {"cbp_intensity": None},
            "national_size": {"equal_residual": None},
        },
        regime="small_cell_biased",
    )
    with pytest.raises(ConceptViolationError, match="mask arm"):
        preferred_baseline(board, regime="small_cell_biased")


def test_regimes_sitting_on_different_arms_do_not_contaminate_each_other():
    """Moving the guard up must not widen its SCOPE. Pooling never crosses regimes, so a board
    carrying two arms across two regimes is not ambiguous and a scoreboard-wide check would refuse
    a legitimate run the moment a second arm is scored anywhere. The last assertion covers the
    other edge the move touches: a regime with no rows at all has no arms, so it must still read as
    "no comparand" rather than raising.
    """
    board = pl.concat(
        [
            _board_with_an_arm_per_estimator(
                {"state_total": {"cbp_intensity": 110.0}}, regime="small_cell_biased"
            ),
            _board_with_an_arm_per_estimator(
                {"national_size": {"cbp_intensity": 120.0}}, regime="long_consecutive_runs"
            ),
        ],
        how="vertical",
    )
    assert preferred_baseline(board, regime="small_cell_biased") == "cbp_intensity"
    assert preferred_baseline(board, regime="long_consecutive_runs") == "cbp_intensity"
    assert preferred_baseline(board, regime="rolling_origin") is None


def test_the_board_keeps_one_row_per_group_when_the_metrics_carry_strata():
    """R-S5G-1's fan-out guard: the board's grain must not follow the partition.

    `build_scoreboard` selects `metric_family == 'point' & metric_name == 'wape'`. Per-division
    WAPE rows match both clauses, so without the `stratum_kind == 'overall'` filter the left join
    to `basis` returns a row per division per group and the board silently multiplies --
    `validate_frame` compares names and dtypes and cannot see a row count. §13.10's comparand is a
    (270, 13) board; a fan-out there corrupts the number Stage 5 is promoted against.
    """
    metrics = _metrics()
    stratified = metrics.filter(pl.col("stratum_kind") == "census_division")
    assert stratified.height > 0, "fixture must actually carry stratified rows"
    board = build_scoreboard(metrics)
    assert (
        board.height
        == metrics.filter(
            (pl.col("metric_family") == "point")
            & (pl.col("metric_name") == "wape")
            & (pl.col("stratum_kind") == "overall")
        ).height
    )
    assert board.select("regime", "seed", "estimator_id").n_unique() == board.height
