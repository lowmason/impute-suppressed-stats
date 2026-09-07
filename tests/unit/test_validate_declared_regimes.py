from pathlib import Path

import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import select_targets


def test_the_vintage_regime_refuses_rather_than_returning_nothing():
    """An empty partition would read as 'scored, nothing wrong'. It must raise."""
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    with pytest.raises(NotImplementedError, match="second snapshot"):
        select_targets("preliminary_to_final_vintage", monthly, seed=1024, config=cfg)


def test_the_config_default_agrees_with_the_data():
    assert load_config(Path("config.yaml")).validation.include_vintage_comparison is False


def test_the_naics_transition_regime_targets_the_measured_seam():
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    targets = select_targets("naics_transition", monthly, seed=1024, config=cfg)
    assert targets
    assert all("2021" in t.reference_month or "2022" in t.reference_month for t in targets)


def test_break_windows_are_declared_in_config_not_detected():
    cfg = load_config(Path("config.yaml"))
    windows = cfg.validation.structural_break_windows
    assert len(windows) >= 1
    assert all(len(w) == 2 for w in windows)
