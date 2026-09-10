from pathlib import Path

import pytest
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import select_targets


@requires_staged
def test_the_vintage_regime_refuses_rather_than_returning_nothing():
    """An empty partition would read as 'scored, nothing wrong'. It must raise."""
    monthly = HarmonizedData.load(STAGED).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    with pytest.raises(NotImplementedError, match="second snapshot"):
        select_targets("preliminary_to_final_vintage", monthly, seed=1024, config=cfg)


def test_the_config_default_agrees_with_the_data():
    assert load_config(Path("config.yaml")).validation.include_vintage_comparison is False


@requires_staged
def test_the_naics_transition_regime_targets_the_measured_seam():
    monthly = HarmonizedData.load(STAGED).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    targets = select_targets("naics_transition", monthly, seed=1024, config=cfg)
    assert targets
    assert all("2021" in t.reference_month or "2022" in t.reference_month for t in targets)


def test_break_windows_are_declared_in_config_not_detected():
    cfg = load_config(Path("config.yaml"))
    windows = cfg.validation.structural_break_windows
    assert len(windows) >= 1
    assert all(len(w) == 2 for w in windows)


@requires_staged
def test_asking_for_the_vintage_regime_makes_the_harness_refuse():
    """§13.3 regime 12 is fail-closed, not skip-quietly.

    Appendix A ships `include_vintage_comparison: true`. This package defaults it false because the
    data cannot support it, and the plan requires the harness to REFUSE rather than emit an empty
    partition if an operator turns it back on. Before this, every `include_*` flag was decorative:
    the harness iterated `REGIME_SPECS` and read none of them.
    """
    from logging_employment.validate.harness import run_pseudo_suppression

    data = HarmonizedData.load(STAGED)
    cfg = load_config(Path("config.yaml"))
    asked = cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(
                update={"include_vintage_comparison": True, "pseudo_suppression_seeds": []}
            )
        }
    )
    with pytest.raises(NotImplementedError, match="second snapshot"):
        run_pseudo_suppression(data, (), asked)
