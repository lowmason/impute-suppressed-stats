"""Stage 4's exit criteria, witnessed on the committed fixture layer rather than on data/staged.

The fixture is in git, so these run on a clean checkout. Where a claim is about D1 specifically the
test says so and carries the `data/staged` skipif.
"""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import (
    VALIDATION_SCORE_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from logging_employment.validate.harness import run_pseudo_suppression

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "baselines"
STAGED = REPO / "data" / "staged"


def _fixture_config() -> Config:
    cfg = load_config(REPO / "config.yaml")
    return cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(
                update={"replicates_per_regime": 3, "pseudo_suppression_seeds": [1024]}
            )
        }
    )


@pytest.fixture(scope="module")
def fixture_run():
    """One full-registry harness pass, shared by every test here.

    Module scope because the pass costs ~11s and both tests need the same one; nothing about
    parallelism — no xdist plugin is installed in this venv and nothing configures it.
    """
    return run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY, _fixture_config())


def test_the_rolling_origin_entry_records_the_origins_its_guard_checked(fixture_run):
    """R-S4C-4: the guard is the deliverable, so the manifest must say where it ran.

    On this fixture the answer is NONE — it carries 2023 alone, so no January has the configured
    six months of history behind it. An empty list is the honest record and is not the same as an
    absent key: absent would mean the guard was never reached.
    """
    entry = fixture_run.manifest["regimes"]["rolling_origin"]
    assert "origins_checked" in entry
    assert entry["origins_checked"] == []
    assert entry["n_scored"] == 0


def test_only_the_truncating_regime_records_origins(fixture_run):
    """A key that appeared on every entry would say nothing about which regime owns the guard."""
    carrying = {
        name
        for name, entry in fixture_run.manifest["regimes"].items()
        if "origins_checked" in entry
    }
    assert carrying == {"rolling_origin"}


@pytest.mark.slow
@pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(),
    reason="data/staged is gitignored; the seven D1 origins need the rebuilt tables",
)
def test_the_guard_is_binding_on_the_d1_panel():
    """The fixture makes the guard vacuous, so the binding case is witnessed separately.

    Two estimators rather than the registry: this test is about the origins, and §13.7's CRPS is
    the harness's dominant cost.
    """
    cfg = load_config(REPO / "config.yaml")
    cfg = cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(update={"pseudo_suppression_seeds": [1024]})
        }
    )
    result = run_pseudo_suppression(HarmonizedData.load(STAGED), REGISTRY[:2], cfg)
    origins = result.manifest["regimes"]["rolling_origin"]["origins_checked"]
    assert origins == [
        "2018-01",
        "2019-01",
        "2020-01",
        "2021-01",
        "2022-01",
        "2023-01",
        "2024-01",
    ]


def test_a_regime_excluded_by_its_switch_appears_with_a_reason_naming_the_switch(fixture_run):
    """R-S4C-12: excluded is not absent. A vanishing regime is the empty partition this refuses."""
    for regime, switch in (
        ("retrospective_smoothing", "include_retrospective_smoothing"),
        ("preliminary_to_final_vintage", "include_vintage_comparison"),
    ):
        entry = fixture_run.manifest["regimes"][regime]
        assert entry["n_scored"] == 0
        assert switch in entry["reason"], entry["reason"]


def test_the_config_derived_reason_still_carries_the_declared_one(fixture_run):
    """The switch is WHY it did not run here; the declared reason is why it could not anyway."""
    entry = fixture_run.manifest["regimes"]["preliminary_to_final_vintage"]
    assert "second snapshot" in entry["reason"]


def test_an_enabled_switch_leaves_its_regime_alone(fixture_run):
    """`include_long_runs` ships true, so `long_consecutive_runs` must still score."""
    entry = fixture_run.manifest["regimes"]["long_consecutive_runs"]
    assert entry["n_scored"] > 0
    assert "include_long_runs" not in str(entry.get("reason", ""))


def test_turning_the_vintage_switch_on_still_raises(fixture_run):
    """The fail-closed refusal must survive the switch gating, not be swallowed by it.

    `tests/unit/test_validate_declared_regimes.py::test_asking_for_the_vintage_regime_makes_the
    _harness_refuse` is the pin; this asserts the ORDER — the switch check must not return a
    config-derived reason for a regime the operator explicitly asked for.
    """
    del fixture_run
    cfg = _fixture_config()
    cfg = cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(update={"include_vintage_comparison": True})
        }
    )
    with pytest.raises(NotImplementedError, match="second snapshot"):
        run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY[:1], cfg)


def test_the_scores_frame_produces_exactly_what_it_declares(fixture_run):
    """M11: 23 produced against 20 declared, overlapping in 17 — a three-way disagreement.

    `cli.py` called the produced set "a superset", which it was not: three declared columns were
    produced by nothing. Set equality, not containment, is the assertion.
    """
    assert set(fixture_run.scores.columns) == set(VALIDATION_SCORE_SCHEMA)
    validate_frame(fixture_run.scores, VALIDATION_SCORE_SCHEMA, "validation_scores")


def test_the_seed_column_is_int64_in_both_frames(fixture_run):
    """R-S4C-18: resolved toward the DECLARATION, not by weakening the schema to Int32.

    `pl.lit(seed)` infers Int32 on polars 1.44 while the metrics frame builds Int64 from Python
    dicts, so the two disagreed. Seeds come from `config.validation.pseudo_suppression_seeds` and
    nothing bounds them to 32 bits.
    """
    assert fixture_run.scores.schema["seed"] == pl.Int64
    assert fixture_run.metrics.schema["seed"] == pl.Int64


def test_the_two_constraint_hashes_are_different_columns(fixture_run):
    """M11: `masked_constraint_set_hash` is not a rename of `constraint_set_hash`.

    Neither may be dropped as a duplicate. The masked one is the hash of the system this replicate
    actually solved; the unmasked one rides in from `run_baselines` and is null on this fixture.
    """
    assert "constraint_set_hash" in fixture_run.scores.columns
    assert "masked_constraint_set_hash" in fixture_run.scores.columns
    assert fixture_run.scores["masked_constraint_set_hash"].null_count() == 0


def test_the_three_new_columns_are_derived_rather_than_constant(fixture_run):
    """A column with one value on every row records nothing.

    Two of the three legitimately have one HERE: `mask_arm` is `state_total` by design, and
    `replicate` is `[0]` because this fixture configures a single seed — it varies only across a
    multi-seed run. `lookback_months_masked` is the one this test actually shows varying.
    """
    scores = fixture_run.scores
    assert scores["mask_arm"].null_count() == 0
    assert scores["mask_arm"].unique().to_list() == ["state_total"]
    assert scores["replicate"].unique().to_list() == [0]
    # `lookback_months_masked` is the per-state masked-month count, so a blackout regime's rows
    # must carry more than a single-month regime's.
    blackout = scores.filter(pl.col("regime") == "long_consecutive_runs")
    single = scores.filter(pl.col("regime") == "small_cell_biased")
    assert blackout["lookback_months_masked"].max() > single["lookback_months_masked"].max()
