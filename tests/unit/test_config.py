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
