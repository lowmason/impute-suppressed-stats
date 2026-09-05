"""Config parses Appendix A's shape, and the resolved form carries no secret."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from logging_employment.config import load_config, resolved_dict

APPENDIX_A = """
project:
  name: 'logging-state-employment'
  industry_code_supplied: '1113310'
  industry_code_used: '113310'
  industry_title: 'Logging'
  ownership: 'private'
  geography_universe: 'states_dc'
  start_month: '2017-01'
  end_month: '2024-12'
  analysis_mode: 'retrospective_final'
  size_concept: 'march_reference'
storage:
  raw_uri: 'data/raw'
  staged_uri: 'data/staged'
  output_uri: 'runs'
  immutable_raw: true
sources:
  qcew:
    enabled: true
    release_status: 'final'
  qcew_size:
    enabled: true
  cbp:
    enabled: true
    api_key_env: 'CENSUS_API_KEY'
    fail_on_unknown_disclosure_regime: true
constraints:
  enforce_integrality: true
  use_milp_when_lp_interval_width_below: 25
  solver: 'highs'
  feasibility_tolerance: 1.0e-7
  rank_tolerance: 1.0e-10
disclosure:
  exact_reconstruction_action: 'withhold'
  narrow_interval_action: 'manual_review'
  publish_label_required: true
  narrow_interval_absolute_width: 10
  narrow_interval_relative_width: 0.25
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_appendix_a_config_parses(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.project.geography_universe == "states_dc"
    assert cfg.project.start_month == "2017-01"
    assert cfg.sources.cbp.api_key_env == "CENSUS_API_KEY"
    assert cfg.sources.cbp.fail_on_unknown_disclosure_regime is True


def test_an_unknown_analysis_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("retrospective_final", "guesswork")))


def test_a_window_outside_d1_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="start_month"):
        load_config(_write(tmp_path, APPENDIX_A.replace("'2017-01'", "'2017-1'")))


def test_resolved_config_names_the_env_var_but_never_a_key_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CENSUS_API_KEY", "supersecretvalue")
    resolved = resolved_dict(load_config(_write(tmp_path, APPENDIX_A)))
    assert "supersecretvalue" not in str(resolved)
    assert resolved["sources"]["cbp"]["api_key_env"] == "CENSUS_API_KEY"


def test_the_constraints_block_parses_with_appendix_a_values(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.constraints.enforce_integrality is True
    assert cfg.constraints.solver == "highs"
    assert cfg.constraints.use_milp_when_lp_interval_width_below == 25
    assert cfg.constraints.feasibility_tolerance == 1.0e-7
    assert cfg.constraints.rank_tolerance == 1.0e-10


def test_the_narrowness_thresholds_are_separate_keys_from_the_milp_switch(tmp_path: Path) -> None:
    # The §21 "Disclosure thresholds" row is governance policy; the MILP switch is a solver knob.
    # Reusing one for the other is the failure this test exists to prevent.
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.disclosure.narrow_interval_absolute_width == 10
    assert cfg.disclosure.narrow_interval_relative_width == 0.25
    assert (
        cfg.disclosure.narrow_interval_absolute_width
        != cfg.constraints.use_milp_when_lp_interval_width_below
    )


def test_an_unknown_solver_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("'highs'", "'glpk'")))


def test_the_shipped_config_carries_both_new_blocks() -> None:
    cfg = load_config(Path(__file__).resolve().parents[2] / "config.yaml")
    assert cfg.constraints.solver == "highs"
    assert cfg.disclosure.narrow_interval_relative_width == 0.25
