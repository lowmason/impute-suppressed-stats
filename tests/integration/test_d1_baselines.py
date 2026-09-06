"""The D1 acceptance run for Stage 3, on the real window.

Skipped when `data/staged/` is absent, matching the shipped Stage 2 acceptance file. Those tables
are gitignored and rebuilt from frozen source bytes, so this runs where the data lives. The repo
configures no marker filter, so `slow` documents the cost rather than excluding the file — the
skip is what keeps a fresh clone green.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.interfaces import FALLBACK, OWN
from logging_employment.baselines.runner import preferred_estimator, run_baselines
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]
STAGED = REPO / "data" / "staged"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (STAGED / "qcew_monthly.parquet").exists(),
        reason="data/staged is gitignored; the D1 acceptance run needs the rebuilt tables",
    ),
]


def _run():
    cfg = load_config(REPO / "config.yaml")
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    return run_baselines(data, cfg), cfg, data


def test_the_universe_gate_is_evaluated_for_every_window_month() -> None:
    """Structure, not the number: the anti-drift rule. A revision may move the gap; it must not
    be able to skip the gate."""
    (results, audit), _, data = _run()
    panel_months = data.qcew_monthly.filter(pl.col("area_type") == "state")[
        "reference_month"
    ].n_unique()
    # Against the PANEL, not against the results. Every month of the panel must be gated, whether
    # or not it had anything to allocate; comparing to the results' months would hold merely
    # because every D1 month happens to carry a suppressed cell, and would start passing a
    # skipped gate the moment one month came back fully disclosed.
    assert audit.height == panel_months
    assert set(results["reference_month"].unique().to_list()) <= set(
        audit["reference_month"].to_list()
    )
    assert audit["anchored"].null_count() == 0


def test_every_running_estimator_sums_to_its_months_residual() -> None:
    (results, _), cfg, _data = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    totals = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual")
    )
    worst = (totals["total"] - totals["residual"]).abs().max()
    assert worst <= max(cfg.reconciliation.tolerance * 1e3, 1e-6)


def test_no_estimate_is_negative() -> None:
    (results, _), _cfg, _data = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert ran["estimate"].min() >= 0.0


def test_a_preferred_transparent_baseline_is_named() -> None:
    """The roadmap's "named preferred transparent baseline slot that Stage 4 fills with numbers"."""
    (results, _), _cfg, _data = _run()
    assert preferred_estimator(results)


def _status_by_estimator_month(frame: pl.DataFrame) -> dict[tuple[str, str], str]:
    """The one `reconciliation_status` each estimator-month carries.

    `run_baselines` writes decline rows for a month's whole missing set or reconciles all of it,
    never a mix; the set arithmetic below reads one status per key, so that is checked here rather
    than assumed.
    """
    grouped = frame.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("reconciliation_status").unique().alias("statuses")
    )
    out: dict[tuple[str, str], str] = {}
    for row in grouped.iter_rows(named=True):
        assert len(row["statuses"]) == 1, row
        out[(row["estimator_id"], row["reference_month"])] = row["statuses"][0]
    return out


def test_the_composite_split_is_recorded_rather_than_hidden() -> None:
    """Declared composition, not a dated count: whatever composed, the output says which cells
    came from the fallback arm.

    The oracle is the run itself under the one flag that governs composition. With
    `allow_declared_composite` false, `compose` refuses on the same `gaps` it would otherwise
    label -- and refuses BEFORE labelling anything -- so an estimator-month that reconciles with
    the flag on and declines with it off is exactly an estimator-month that composed. That set is
    derived here, never typed: on a vintage where every estimator's own arm covers every cell,
    both sides are empty and the claim still holds. The old `"establishment_fallback" in ...` was
    the dated fact that six D1 states have no observed history and two have no CBP row.
    """
    (results, _), cfg, data = _run()
    # The oracle is the difference the flag makes, so the run under test has to be the permissive
    # one. Config, not data: nothing a QCEW vintage does moves this.
    assert cfg.baselines.allow_declared_composite
    strict = cfg.model_copy(
        update={"baselines": cfg.baselines.model_copy(update={"allow_declared_composite": False})}
    )
    without_composite, _ = run_baselines(data, strict)

    ran = _status_by_estimator_month(results)
    refused = _status_by_estimator_month(without_composite)
    # Both runs cover the same estimator-months, so a key the strict run DROPS rather than
    # declines fails here instead of falling silently out of `composed`.
    assert set(ran) == set(refused)
    composed = {
        key
        for key, status in ran.items()
        if status == "anchored_and_reconciled" and refused[key] == "declined"
    }
    reconciled = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    labelled = set(
        reconciled.filter(pl.col("weight_basis") == FALLBACK)
        .select(["estimator_id", "reference_month"])
        .unique()
        .iter_rows()
    )
    assert labelled == composed
    # `none` is the declined rows' basis; a reconciled cell always names the arm it used.
    assert set(reconciled["weight_basis"].unique().to_list()) <= {OWN, FALLBACK}

    # Liveness, DERIVED from the panel rather than typed -- the anti-drift rule's own method
    # applied to the premise the magic string rested on. A state with no observed employment month
    # anywhere in the panel can carry no own weight under a share estimator, so a missing set
    # containing one must compose. Computed at run time this is AK, DE, HI, NV, ND, VT today. On a
    # vintage where every state has a history the set is empty and the demand lapses BY
    # CONSTRUCTION: that is what separates "nothing needed the fallback arm" from "the fallback
    # arm stopped working", and it is why this `assert composed` is not a dated literal.
    states = data.qcew_monthly.filter(pl.col("area_type") == "state")
    with_history = set(
        states.filter(pl.col("observation_status") == "observed")["state_fips"].unique().to_list()
    )
    without_history = set(results["state_fips"].unique().to_list()) - with_history
    if without_history:
        assert composed, (
            f"states {sorted(without_history)} have no observed month in the panel, so some "
            "estimator-month must have composed; none did"
        )
