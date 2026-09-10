import subprocess
import sys
import textwrap
from pathlib import Path

import polars as pl
import pytest
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HOLDOUT_REGIMES, HarmonizedData
from logging_employment.validate.regimes import REGIME_SPECS, select_targets


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(STAGED).qcew_monthly


def test_every_spec_declares_a_grain_and_a_disposition():
    assert set(REGIME_SPECS) == set(HOLDOUT_REGIMES)
    for spec in REGIME_SPECS.values():
        assert spec.grain in {"single_month", "blackout"}
        assert spec.disposition in {"feasible", "vacuous_on_registry", "cannot_run_on_d1"}


@requires_staged
@pytest.mark.parametrize(
    "regime",
    [
        "small_cell_biased",
        "concentration_proxy",
        "clustered_states_within_month",
        "long_consecutive_runs",
        "whole_state_year_blocks",
        "whole_seasonal_blocks",
    ],
)
def test_a_feasible_regime_selects_only_eligible_targets(regime):
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    targets = select_targets(regime, monthly, seed=1024, config=cfg)
    assert targets, f"{regime} selected nothing"
    keys = {(t.state_fips, t.reference_month) for t in targets}
    chosen = monthly.filter(
        pl.struct("state_fips", "reference_month").is_in(
            [{"state_fips": s, "reference_month": m} for s, m in keys]
        )
    )
    assert chosen.filter(pl.col("observation_status") != "observed").height == 0
    assert chosen.filter(pl.col("qtrly_establishments") <= 0).height == 0


@requires_staged
def test_a_never_observed_state_is_never_selected():
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    never = {"02", "10", "15", "32", "38", "50"}
    for regime in REGIME_SPECS:
        if REGIME_SPECS[regime].disposition != "feasible":
            continue
        for t in select_targets(regime, monthly, seed=1024, config=cfg):
            assert t.state_fips not in never


@requires_staged
def test_a_single_month_regime_leaves_lookback_history_unmasked():
    """The blackout distinction: a small-cell mask must not erase its own share history."""
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    targets = select_targets("small_cell_biased", monthly, seed=1024, config=cfg)
    per_state: dict[str, int] = {}
    for t in targets:
        per_state[t.state_fips] = per_state.get(t.state_fips, 0) + 1
    # No state may lose more months than its lookback can absorb.
    assert max(per_state.values()) <= 96 - cfg.validation.minimum_unmasked_lookback_months


def test_the_census_divisions_partition_the_state_universe():
    from logging_employment.constants import STATES_DC_FIPS
    from logging_employment.validate.regimes import CENSUS_DIVISIONS

    flat = [f for members in CENSUS_DIVISIONS.values() for f in members]
    assert len(flat) == len(set(flat)), "a state appears in two divisions"
    assert set(flat) == set(STATES_DC_FIPS)


@requires_staged
def test_every_selector_is_reproducible_within_a_process():
    """§16.1's idempotence MUST, at the selection layer.

    Two of the seven selectors sampled from an UNORDERED frame — `unique()` and `group_by()` give
    no order guarantee, so a seeded `sample` over them picked a different month or state-year per
    process. The `validate` CLI's idempotence test caught it end to end; this catches it here,
    where the cause is legible.
    """
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    for regime, spec in REGIME_SPECS.items():
        if spec.select is None:
            continue
        first = select_targets(regime, monthly, seed=1024, config=cfg)
        second = select_targets(regime, monthly, seed=1024, config=cfg)
        assert first == second, f"{regime} is not reproducible for a fixed seed"


@requires_staged
def test_every_selector_is_reproducible_ACROSS_processes():
    """The property a within-process repeat cannot check.

    Polars returns the same arbitrary order twice inside one process, so an unordered `unique()`
    or `group_by()` feeding a seeded `sample` looks stable until the next run. Measured before the
    fix: `clustered_states_within_month` and `whole_state_year_blocks` produced a different digest
    in every fresh interpreter, which is what broke §16.1's idempotence MUST for the `validate`
    command. Two subprocesses is the cheapest honest test of it.
    """
    script = textwrap.dedent("""
        import hashlib
        import sys
        from pathlib import Path
        from logging_employment.config import load_config
        from logging_employment.contracts import HarmonizedData
        from logging_employment.validate.regimes import REGIME_SPECS, select_targets

        monthly = HarmonizedData.load(Path(sys.argv[1])).qcew_monthly
        cfg = load_config(Path("config.yaml"))
        parts = []
        for regime, spec in sorted(REGIME_SPECS.items()):
            if spec.select is None:
                continue
            targets = select_targets(regime, monthly, seed=1024, config=cfg)
            parts.append(regime + ":" + repr(sorted((t.state_fips, t.reference_month) for t in targets)))
        print(hashlib.sha256("|".join(parts).encode()).hexdigest())
        """)
    digests = {
        subprocess.run(
            [sys.executable, "-c", script, str(STAGED)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for _ in range(2)
    }
    # A subprocess that printed nothing would give {""} and pass vacuously.
    assert digests != {""}, "the subprocess produced no digest"
    assert len(next(iter(digests))) == 64
    assert len(digests) == 1, f"selection differs across processes: {digests}"
