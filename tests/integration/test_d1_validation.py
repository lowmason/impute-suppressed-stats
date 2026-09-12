"""§17.4 row 7: the harness generates pseudo-suppression metrics on the D1 layer.

COST DEVIATION, stated rather than silent. The plan runs `run_pseudo_suppression` once per test at
`config.yaml`'s three seeds; measured, that module took 6:29, of which 5:25 was the single
`REGISTRY[:4]` test. The cost is not `run_baselines` — it is §13.7's CRPS, which is O(n^2) per
scored cell and so O(n^3) per estimator, and `whole_seasonal_blocks` masks 291 cells. These tests
therefore run each estimator subset ONCE at module scope, on a one-seed copy of the config. The
assertions are unchanged; only the number of harness invocations is. The three-seed run is Task 19
Step 3's, recorded in the plan's completion stamp.
"""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import (
    VALIDATION_METRIC_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from logging_employment.validate.harness import run_pseudo_suppression

REPO = Path(__file__).resolve().parents[2]
STAGED = REPO / "data" / "staged"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (STAGED / "qcew_monthly.parquet").exists(),
        reason="data/staged is gitignored; the D1 validation run needs the rebuilt tables",
    ),
]


def _one_seed(cfg: Config) -> Config:
    return cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(update={"pseudo_suppression_seeds": [1024]})
        }
    )


@pytest.fixture(scope="module")
def four_rung_run():
    """One harness pass over the first four estimators, shared by every test that needs it."""
    cfg = _one_seed(load_config(REPO / "config.yaml"))
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    return run_pseudo_suppression(data, REGISTRY[:4], cfg)


def test_the_harness_produces_metrics_that_match_the_declared_schema(four_rung_run):
    validate_frame(four_rung_run.metrics, VALIDATION_METRIC_SCHEMA, "validation_metrics")
    assert four_rung_run.metrics["denominator"].null_count() == 0


def test_every_scored_cell_was_actually_masked(four_rung_run):
    """The harness must never report a cell it did not hide."""
    assert four_rung_run.scores["truth"].null_count() == 0
    assert set(four_rung_run.scores["suppression_type"].unique().to_list()) <= {
        "primary_like",
        "complementary_like",
    }


def test_a_never_observed_state_never_appears_as_scored(four_rung_run):
    never = {"02", "10", "15", "32", "38", "50"}
    assert not (set(four_rung_run.scores["state_fips"].unique().to_list()) & never)


def test_one_metric_row_is_reproducible_from_the_scores(four_rung_run):
    """Derived, not typed. Recompute a WAPE from `validation_scores` and match the metric row."""
    row = four_rung_run.metrics.filter(
        # OVERALL: the recomputation below pools the whole (regime, seed, estimator); a division row
        # shares the metric name and would match only by emission order.
        (pl.col("metric_name") == "wape") & (pl.col("stratum_kind") == "overall")
    ).row(0, named=True)
    subset = four_rung_run.scores.filter(
        (pl.col("regime") == row["regime"])
        & (pl.col("seed") == row["seed"])
        & (pl.col("estimator_id") == row["estimator_id"])
        & pl.col("estimate").is_not_null()
    )
    expected = float(
        (subset["estimate"] - subset["truth"]).abs().sum() / subset["truth"].abs().sum()
    )
    assert abs(row["value"] - expected) < 1e-9


def test_a_refused_regime_is_recorded_with_its_reason_and_scores_nothing(four_rung_run):
    """A regime that cannot run must not emit an empty partition that reads as 'nothing wrong'."""
    entry = four_rung_run.manifest["regimes"]["preliminary_to_final_vintage"]
    assert entry["disposition"] == "cannot_run_on_d1"
    assert entry["n_scored"] == 0
    assert "second snapshot" in entry["reason"]


def test_no_regime_reports_zero_scores_without_saying_why(four_rung_run):
    """The plan's own rule, applied to every regime rather than only the refused one.

    `rolling_origin` and `cbp_size_gaps` are declared feasible and score nothing here, because
    neither masks QCEW cells: one truncates the frame and the other drops CBP state-years. The
    guard now also refuses a reason that defers the question to a later plan rather than answering
    it.
    """
    deferrals = ("deferred", "not yet", "unwired", "to be wired", "future plan")
    for name, entry in four_rung_run.manifest["regimes"].items():
        if entry["n_scored"] != 0:
            continue
        reason = entry.get("reason")
        assert reason, f"{name} scored nothing and gave no reason"
        # R-S4C-2: a measurement or a declaration, never a deferral. This test used to accept any
        # non-empty string, including "Wiring it into the loop is a deferred item" — a sentence
        # that describes the plan's state rather than the regime's.
        lowered = reason.lower()
        for phrase in deferrals:
            assert phrase not in lowered, f"{name}'s reason defers rather than explains: {reason}"


def test_every_scored_cell_on_a_real_run_is_primary_like(four_rung_run):
    """The precondition §13.10 rests on, witnessed on a real run rather than only in a unit test.

    The harness refuses a non-primary-like scored cell, so this fixture completing is already
    evidence; asserting the property makes it legible and would catch a guard wired somewhere the
    scores frame does not flow through.
    """
    assert four_rung_run.scores["suppression_type"].unique().to_list() == ["primary_like"]
