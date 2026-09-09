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
