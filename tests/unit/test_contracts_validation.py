import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.errors import ConceptViolationError


def test_a_suppression_type_outside_the_declared_set_is_refused():
    frame = pl.DataFrame({"suppression_type": ["primary_like", "invented_kind"]})
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        contracts.assert_declared_provenance(frame)


def test_the_declared_suppression_types_pass():
    frame = pl.DataFrame({"suppression_type": ["unknown", "primary_like", "complementary_like"]})
    contracts.assert_declared_provenance(frame)


def test_every_holdout_regime_carries_a_disposition():
    assert set(contracts.REGIME_DISPOSITIONS) == set(contracts.HOLDOUT_REGIMES)
    assert contracts.REGIME_DISPOSITIONS["preliminary_to_final_vintage"] == "cannot_run_on_d1"


def test_the_two_validation_schemas_are_distinct_and_fingerprinted():
    a = contracts.schema_fingerprint(contracts.VALIDATION_SCORE_SCHEMA)
    b = contracts.schema_fingerprint(contracts.VALIDATION_METRIC_SCHEMA)
    assert a != b
    # R-COMP-10: a metric row is unreadable without the base it was computed over.
    assert "denominator" in contracts.VALIDATION_METRIC_SCHEMA
    assert "denominator_basis" in contracts.VALIDATION_METRIC_SCHEMA


def test_the_scoreboard_schema_is_declared_and_distinct():
    """M13: no scoreboard schema existed, though `cli.py` has persisted the artifact since plan 11."""
    board = contracts.VALIDATION_SCOREBOARD_SCHEMA
    assert contracts.schema_fingerprint(board) != contracts.schema_fingerprint(
        contracts.VALIDATION_METRIC_SCHEMA
    )
    assert board["wape"] == pl.Float64
    assert board["seed"] == pl.Int64
    # The gate's comparand needs its base, exactly as a metric row does (R-COMP-10).
    assert "denominator" in board
    assert "denominator_basis" in board


def test_an_empty_scoreboard_still_carries_its_columns():
    """An empty board must carry its columns, so a gate reads "nothing scored", not "13 missing".

    WHERE THE BARE FRAME ACTUALLY COMES FROM, measured 2026-09-09 on polars 1.44.1: not from
    `build_scoreboard`. Handed a bare `pl.DataFrame()` it RAISES `ColumnNotFoundError: unable to
    find column "metric_family"`, and handed a schema-shaped empty metrics frame it already
    returns a correct (0, 13) board that `validate_frame` accepts. The bare frame is written by
    the CALLER — `run_pseudo_suppression`'s three empty-run fallbacks, which are shaped alongside
    this.
    """
    from logging_employment.validate.scoreboard import build_scoreboard

    # The real path: a rowless but schema-SHAPED metrics frame, which is what the harness hands
    # over. This already returned (0, 13) before the early return below existed, so the
    # load-bearing half of this test is the `validate_frame` call.
    empty = build_scoreboard(pl.DataFrame(schema=contracts.VALIDATION_METRIC_SCHEMA))
    assert empty.height == 0
    contracts.validate_frame(empty, contracts.VALIDATION_SCOREBOARD_SCHEMA, "validation_scoreboard")

    # The early return. Before it lands this line raises `ColumnNotFoundError`, not
    # `AttributeError` — a bare frame has no `metric_family` for `headline` to filter on.
    assert build_scoreboard(pl.DataFrame()).height == 0


def test_a_null_in_a_required_column_is_refused():
    frame = pl.DataFrame(
        {
            "regime": ["small_cell_biased", None],
            "seed": [1024, 1024],
            "mask_arm": ["state_total", "state_total"],
            "estimator_id": ["equal_residual", "equal_residual"],
            "metric_family": ["point", "point"],
            "denominator": [1.0, 1.0],
            "denominator_basis": ["masked_cell_rows", "masked_cell_rows"],
            "n_scored": [1, 1],
            # Present so the ABSENT-column branch cannot fire first and mask the null branch this
            # test is about (R-S5G-1 added both to `VALIDATION_REQUIRED_NON_NULL`).
            "stratum_kind": ["overall", "overall"],
            "stratum_value": ["all", "all"],
        }
    )
    with pytest.raises(ConceptViolationError, match="regime"):
        contracts.assert_required_columns_present(frame, "validation_metrics")


def test_a_table_with_no_declared_requirement_is_refused_rather_than_waved_through():
    """A silent pass for an unknown name would make the gate look applied where it was not."""
    with pytest.raises(ConceptViolationError, match="invented_table"):
        contracts.assert_required_columns_present(pl.DataFrame(), "invented_table")


def test_metric_name_is_not_required_and_the_reason_is_recorded():
    """Measured: NULL on all 70 `declines` rows, because that family emits counts not one metric.

    Recorded rather than fixed (decided 2026-09-08): naming it would move a second golden column
    beyond what V3 authorises. If a later plan gives declines rows a metric_name, this test is the
    one to delete.
    """
    assert "metric_name" not in contracts.VALIDATION_REQUIRED_NON_NULL["validation_metrics"]


def test_wape_is_not_required_because_an_all_declining_estimator_has_no_error():
    assert "wape" not in contracts.VALIDATION_REQUIRED_NON_NULL["validation_scoreboard"]


def test_a_required_column_missing_entirely_is_refused():
    """The gate is named for presence, so absence must fail — it used to be silently skipped.

    Measured before the fix: a one-column frame passed the `validation_metrics` gate without a word
    about its eight missing columns. `validate_frame` runs first at the only production call site,
    so this was never a live hole; but the two callers in `tests/` reach this function without it.
    """
    with pytest.raises(ConceptViolationError, match="absent from the frame"):
        contracts.assert_required_columns_present(
            pl.DataFrame({"unrelated": [1]}), "validation_metrics"
        )


def test_a_stratum_kind_outside_the_declared_set_is_refused():
    """removing `("stratum_kind", STRATUM_KINDS)` from the provenance loop must redden this.

    `validate/harness.py` runs the gate over the assembled metrics frame; without a refusal test
    the entry could be deleted with the suite green, which is `INTERVAL_SOURCES`' situation.
    """
    frame = pl.DataFrame({"stratum_kind": ["overall", "by_state"]})
    with pytest.raises(ConceptViolationError, match="stratum_kind"):
        contracts.assert_declared_provenance(frame)


def test_every_declared_stratum_kind_passes():
    contracts.assert_declared_provenance(
        pl.DataFrame({"stratum_kind": list(contracts.STRATUM_KINDS)})
    )
