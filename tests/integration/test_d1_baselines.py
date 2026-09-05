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


def test_the_composite_split_is_recorded_rather_than_hidden() -> None:
    (results, _), _cfg, _data = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    counts = ran.group_by(["estimator_id", "weight_basis"]).len()
    assert counts.height > 0
    assert "establishment_fallback" in ran["weight_basis"].unique().to_list()
