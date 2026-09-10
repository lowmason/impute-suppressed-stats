"""Config parses Appendix A's shape, and the resolved form carries no secret."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from logging_employment.config import Config, load_config, resolved_dict
from logging_employment.runs import run_id

# NOT Appendix A's fence. Measured against `specs/logging-employment-spec.md`'s `## Appendix A`
# block, this constant differs from it in five ways, every one of which is this package's doing
# rather than the spec's:
#   1. it OMITS `model:` -- Stage 5's block, for which `Config` has no field. Adding one would put
#      a key in `resolved_dict` and re-identify every run directory under `runs/`.
#   2. it OMITS `promotion:` and `validation:`, which `Config` defaults.
#   3. it ADDS `baselines:` and the two `disclosure:` narrow-interval widths, which `Config`
#      REQUIRES and the spec states nowhere.
#   4. it ADDS five `reconciliation:` keys this package originated (`tolerance`,
#      `max_bisection_iterations`, `max_projection_iterations`, `zero_seed_floor`,
#      `integerization_tiebreak`).
#   5. it OMITS Appendix A's seven `enabled: false` sources.
# The name says so because the old one (`APPENDIX_A`) claimed to be the spec's example
# configuration and was not, which is how "Appendix A loads" stayed believable while the real
# fence produced eleven validation errors. `appendix_a_fence()` below reads the actual block.
APPENDIX_A_AS_THE_CODE_REQUIRES = """
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


def test_the_code_shaped_config_parses(tmp_path: Path) -> None:
    """The CODE-shaped config loads -- renamed because it never tested Appendix A's own fence.

    See the constant's header for the five ways it differs. What Appendix A itself does is
    `test_the_spec_fence_is_short_only_the_keys_the_spec_never_states`.
    """
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    assert cfg.project.geography_universe == "states_dc"
    assert cfg.project.start_month == "2017-01"
    assert cfg.sources.cbp.api_key_env == "CENSUS_API_KEY"
    assert cfg.sources.cbp.fail_on_unknown_disclosure_regime is True


def test_an_unknown_analysis_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(
            _write(
                tmp_path,
                APPENDIX_A_AS_THE_CODE_REQUIRES.replace("retrospective_final", "guesswork"),
            )
        )


def test_a_window_outside_d1_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="start_month"):
        load_config(
            _write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("'2017-01'", "'2017-1'"))
        )


def test_resolved_config_names_the_env_var_but_never_a_key_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CENSUS_API_KEY", "supersecretvalue")
    resolved = resolved_dict(load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES)))
    assert "supersecretvalue" not in str(resolved)
    assert resolved["sources"]["cbp"]["api_key_env"] == "CENSUS_API_KEY"


def test_the_constraints_block_parses_with_appendix_a_values(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    assert cfg.constraints.enforce_integrality is True
    assert cfg.constraints.solver == "highs"
    assert cfg.constraints.use_milp_when_lp_interval_width_below == 25
    assert cfg.constraints.feasibility_tolerance == 1.0e-7
    assert cfg.constraints.rank_tolerance == 1.0e-10


def test_the_narrowness_thresholds_are_separate_keys_from_the_milp_switch(tmp_path: Path) -> None:
    # The §21 "Disclosure thresholds" row is governance policy; the MILP switch is a solver knob.
    # Reusing one for the other is the failure this test exists to prevent.
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    assert cfg.disclosure.narrow_interval_absolute_width == 10
    assert cfg.disclosure.narrow_interval_relative_width == 0.25
    assert (
        cfg.disclosure.narrow_interval_absolute_width
        != cfg.constraints.use_milp_when_lp_interval_width_below
    )


def test_an_unknown_solver_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("'highs'", "'glpk'")))


def test_the_shipped_config_carries_both_new_blocks() -> None:
    cfg = load_config(Path(__file__).resolve().parents[2] / "config.yaml")
    assert cfg.constraints.solver == "highs"
    assert cfg.disclosure.narrow_interval_relative_width == 0.25


def test_the_reconciliation_block_parses_with_appendix_a_methods(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
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
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    assert cfg.reconciliation.tolerance == 1.0e-9
    assert cfg.constraints.feasibility_tolerance == 1.0e-7


def test_an_unknown_general_method_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(
            _write(
                tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("kl_projection", "hand_waving")
            )
        )


def test_a_nondeterministic_integerization_tiebreak_is_rejected(tmp_path: Path) -> None:
    """§16.1 requires idempotence; a random tie-break would break it."""
    with pytest.raises(ValidationError):
        load_config(
            _write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("largest_remainder", "random"))
        )


def test_the_constraints_location_is_a_config_key_with_a_default(tmp_path: Path) -> None:
    """Appendix A's `storage:` block has four keys and no constraints location.

    The default is §6.2's `data/constraints/` -- the exact path the old derivation resolved to
    for the shipped `staged_uri`, so a config written before this key existed keeps writing
    where it always wrote.
    """
    cfg = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    assert cfg.storage.constraints_uri == "data/constraints"


REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "specs" / "logging-employment-spec.md"

# Appendix A's seven declared-inactive source entries, in the order the spec lists them.
INACTIVE_SOURCES = ("tpo", "fia", "ces", "susb", "bds", "nonemployer", "bea")


def appendix_a_fence() -> dict[str, Any]:
    """Appendix A's example configuration, parsed out of the spec file itself.

    Read rather than retyped, for `classification.classification_memo`'s reason: a literal is a
    second source of truth that drifts silently, and the whole point of this fixture is to witness
    what the SPEC says, not what a test author copied. Anchored at the `## Appendix A` heading and
    taking the first fence under it, so a fenced block added earlier in the file cannot stand in.
    """
    lines = SPEC.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"##\s+Appendix A\b", line)), None)
    assert start is not None, "the spec has no `## Appendix A` heading"
    opened: int | None = None
    for i in range(start + 1, len(lines)):
        if not lines[i].startswith("```"):
            continue
        if opened is None:
            opened = i
        else:
            return yaml.safe_load("\n".join(lines[opened + 1 : i]))
    raise AssertionError("Appendix A carries no closed fenced block")


def _appendix_a_made_loadable() -> dict[str, Any]:
    """Appendix A's fence minus `model:`, plus the three keys the spec never states.

    Patched HERE and not in `config.py`, which is the whole point of the previous test: a default
    for `narrow_interval_absolute_width` would turn a governance threshold §21 explicitly defers
    to its owner into a silent constant, and a `model:` field would re-identify every run
    directory for a stage that does not exist yet. `baselines: {}` is enough because every
    `BaselinesConfig` field carries a default -- the block is required only because `Config`
    declares no default for it.
    """
    fence = appendix_a_fence()
    fence.pop("model")
    fence["baselines"] = {}
    fence["disclosure"] = {
        **fence["disclosure"],
        "narrow_interval_absolute_width": 10,
        "narrow_interval_relative_width": 0.25,
    }
    return fence


def _error_locations(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Every `(dotted location, error type)` `Config` reports for `payload`, sorted."""
    with pytest.raises(ValidationError) as caught:
        Config.model_validate(payload)
    return sorted((".".join(str(p) for p in e["loc"]), e["type"]) for e in caught.value.errors())


def test_the_spec_fence_is_short_only_the_keys_the_spec_never_states() -> None:
    """Appendix A's own fence must load but for keys no code can supply.

    Before Appendix A's seven `enabled: false` sources were declared on `SourcesConfig`, this
    fence produced ELEVEN errors: those seven, `model`, and the three below. The seven were the
    only ones code could fix. What is left is a spec gap in both directions and is asserted here
    rather than papered over:

    * `model:` is Stage 5's block and this package has no field for it. Adding one would put a
      key in `resolved_dict` and re-identify every run directory in `runs/`, so the first
      assertion pins that it is still rejected and the second, after popping it, pins that no
      other extra survives.
    * `baselines:` and the two `disclosure:` widths have no values ANYWHERE in the spec --
      `BaselinesConfig` and §21's "Disclosure thresholds" row are this package's originations.
      Defaulting them so the fence loads clean would invent policy the spec declines to state,
      and would delete the evidence that it declines to.
    """
    fence = appendix_a_fence()
    assert ("model", "extra_forbidden") in _error_locations(fence)

    fence.pop("model")
    assert _error_locations(fence) == [
        ("baselines", "missing"),
        ("disclosure.narrow_interval_absolute_width", "missing"),
        ("disclosure.narrow_interval_relative_width", "missing"),
    ]


def test_the_spec_fence_declares_seven_inactive_sources_and_all_seven_load() -> None:
    """The seven the spec lists are the seven the code accepts, and each is disabled as read."""
    sources = appendix_a_fence()["sources"]
    assert sorted(sources) == sorted(("qcew", "qcew_size", "cbp", *INACTIVE_SOURCES))
    assert all(sources[name] == {"enabled": False} for name in INACTIVE_SOURCES)

    cfg = Config.model_validate(_appendix_a_made_loadable())
    assert all(getattr(cfg.sources, name).enabled is False for name in INACTIVE_SOURCES)
    assert cfg.sources.qcew.release_status == "final"


def test_an_inactive_source_may_not_be_enabled(tmp_path: Path) -> None:
    """`enabled: true` on a source with no ingest module is refused at load, not at `fetch`."""
    doctored = APPENDIX_A_AS_THE_CODE_REQUIRES.replace(
        "sources:\n", "sources:\n  tpo:\n    enabled: true\n"
    )
    with pytest.raises(ValidationError, match="Input should be False"):
        load_config(_write(tmp_path, doctored))


def test_a_misspelled_source_name_is_still_rejected(tmp_path: Path) -> None:
    """Declaring the seven as fields must not become `extra="allow"` for source names."""
    doctored = APPENDIX_A_AS_THE_CODE_REQUIRES.replace(
        "sources:\n", "sources:\n  qcew_sise:\n    enabled: false\n"
    )
    with pytest.raises(ValidationError, match="qcew_sise"):
        load_config(_write(tmp_path, doctored))


def test_an_inactive_source_reaches_neither_the_resolved_config_nor_the_run_id(
    tmp_path: Path,
) -> None:
    """Declaring the seven must not move a run id (`runs.py`, and `ValidationConfig`'s warning).

    `runs.run_id` hashes `resolved_dict`, so any key that reaches the dump renames every existing
    `runs/<id>/`. A source that is `enabled: false` contributes no bytes to any stage, so its
    entry is `exclude=True` and the two configs below -- one carrying all seven, one carrying
    none -- must resolve and identify identically.
    """
    without = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    declared = "sources:\n" + "".join(f"  {n}:\n    enabled: false\n" for n in INACTIVE_SOURCES)
    with_seven = load_config(
        _write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("sources:\n", declared))
    )
    assert with_seven.sources.bea is not None
    assert without.sources.bea is None
    assert sorted(resolved_dict(with_seven)["sources"]) == ["cbp", "qcew", "qcew_size"]
    assert resolved_dict(with_seven) == resolved_dict(without)
    assert run_id(with_seven, {}) == run_id(without, {})


def test_the_shipped_configs_run_id_is_unmoved_by_the_inactive_source_fields() -> None:
    """A literal pin on the id `config.yaml` derives, because the cost of moving it is external.

    `runs/f03023ac9f3a` is Stage 4's acceptance artifact and is derived from this config plus the
    staged inputs. Those inputs are gitignored, so the digest map here is empty and the pinned
    value is not that directory's name -- it is a canary over the same `resolved_dict` input,
    which is the half of the id a config change can move. Measured before this change and
    unchanged by it.
    """
    assert run_id(load_config(REPO_ROOT / "config.yaml"), {}) == "39d1d0859838"
