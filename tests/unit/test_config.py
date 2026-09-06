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
reconciliation:
  single_margin_method: 'bounded_proportional_scaling'
  general_method: 'kl_projection'
  integerize_release: true
  # Originated by plan 4, not by Appendix A, which has no tolerance key.
  tolerance: 1.0e-9
  max_bisection_iterations: 200
  max_projection_iterations: 1000
  zero_seed_floor: 1.0e-12
  integerization_tiebreak: 'largest_remainder'

baselines:
  allow_declared_composite: true
  composite_fallback: 'establishment_proportional'
  historical_lookback_months: 24
  historical_may_cross_naics_vintage: false
  regression_ridge_penalty: 1.0

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


def test_the_reconciliation_block_parses_with_appendix_a_methods(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.reconciliation.single_margin_method == "bounded_proportional_scaling"
    assert cfg.reconciliation.general_method == "kl_projection"
    assert cfg.reconciliation.integerize_release is True


def test_the_reconciliation_tolerance_is_this_packages_decision_not_appendix_as(
    tmp_path: Path,
) -> None:
    """Appendix A's `reconciliation:` block has three keys and no tolerance.

    `feasibility_tolerance: 1.0e-7` lives under `constraints:` and belongs to the LP/MILP bound
    solver. Reusing the number here is a new decision, so it is configured separately and can
    diverge without touching the solver.
    """
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.reconciliation.tolerance == 1.0e-9
    assert cfg.constraints.feasibility_tolerance == 1.0e-7


def test_an_unknown_general_method_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("kl_projection", "hand_waving")))


def test_a_nondeterministic_integerization_tiebreak_is_rejected(tmp_path: Path) -> None:
    """§16.1 requires idempotence; a random tie-break would break it."""
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("largest_remainder", "random")))


def test_the_constraints_location_is_a_config_key_with_a_default(tmp_path: Path) -> None:
    """Appendix A's `storage:` block has four keys and no constraints location.

    The default is §6.2's `data/constraints/` -- the exact path the old derivation resolved to
    for the shipped `staged_uri`, so a config written before this key existed keeps writing
    where it always wrote.
    """
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.storage.constraints_uri == "data/constraints"
