"""Typed configuration, loaded from YAML, with credentials kept out of the resolved form."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Named here so the secret guard and the resolved-config writer share one list (D3).
SECRET_ENV_VARS = ("CENSUS_API_KEY", "BLS_API_KEY", "BEA_API_KEY", "FRED_API_KEY")


class _Strict(BaseModel):
    """Base model that rejects unknown keys, so a typo in config.yaml halts rather than defaults."""

    model_config = ConfigDict(extra="forbid")


class ProjectConfig(_Strict):
    """The estimand: industry, ownership, geography universe, window, and mode."""

    name: str
    industry_code_supplied: str
    industry_code_used: str
    industry_title: str
    ownership: Literal["private"]
    geography_universe: Literal["states_dc"]
    start_month: str
    end_month: str
    analysis_mode: Literal["retrospective_final", "realtime_asof"]
    size_concept: Literal["march_reference", "contemporaneous_modeled"]

    @field_validator("start_month", "end_month")
    @classmethod
    def _is_a_month(cls, value: str) -> str:
        """Reject anything that is not a zero-padded `YYYY-MM`."""
        if not _MONTH.match(value):
            raise ValueError(f"expected YYYY-MM, got {value!r}")
        return value


class StorageConfig(_Strict):
    """Where raw bytes, staged frames, constraint tables, and run outputs live.

    Appendix A's `storage:` block supplies four keys and no constraints location, so
    `constraints_uri` is originated here; its VALUE is §6.2's `data/constraints/`. Defaulted
    rather than required so a config written before the key existed stays valid under
    `extra="forbid"`, and the default is the exact path the location was previously *derived*
    to be. Configured rather than inferred: deriving it from `staged_uri`'s parent moved the
    constraint tables whenever the staged root moved.
    """

    raw_uri: str
    staged_uri: str
    output_uri: str
    immutable_raw: bool
    constraints_uri: str = "data/constraints"


class QcewSourceConfig(_Strict):
    """QCEW quarterly acquisition settings."""

    enabled: bool
    release_status: Literal["final", "preliminary"] = "final"


class QcewSizeSourceConfig(_Strict):
    """QCEW by-size acquisition settings."""

    enabled: bool


class CbpSourceConfig(_Strict):
    """CBP acquisition settings, including the fail-closed disclosure switch."""

    enabled: bool
    api_key_env: str
    fail_on_unknown_disclosure_regime: bool


class SourcesConfig(_Strict):
    """The three sources Stage 1 ingests. Later stages add their own keys."""

    qcew: QcewSourceConfig
    qcew_size: QcewSizeSourceConfig
    cbp: CbpSourceConfig


class ConstraintsConfig(_Strict):
    """The deterministic engine's solver settings (Appendix A `constraints:`).

    `use_milp_when_lp_interval_width_below` is a *performance* switch: it decides when an integer
    re-solve is worth its cost, never whether a cell is disclosive. The disclosure thresholds live
    in `DisclosureConfig` and are a governance decision (§21).
    """

    enforce_integrality: bool
    use_milp_when_lp_interval_width_below: float
    solver: Literal["highs"]
    feasibility_tolerance: float
    rank_tolerance: float


class ReconciliationConfig(_Strict):
    """The §12 reconciliation layer's settings (Appendix A `reconciliation:`, plus this
    package's own numerical decisions).

    Appendix A supplies exactly three keys. §12 specifies no tolerance, no iteration cap, and no
    convergence criterion anywhere, so the remaining five are originated here rather than
    inherited. `feasibility_tolerance` under `constraints:` belongs to the LP/MILP bound solver
    and is deliberately not reused: a bound solved to 1e-7 and a residual reconciled to 1e-9 are
    different obligations, and coupling them would make a solver tuning change silently move a
    published total.
    """

    single_margin_method: Literal["bounded_proportional_scaling"]
    general_method: Literal["kl_projection", "weighted_quadratic"]
    integerize_release: bool
    # Originated here. Tighter than the solver's 1e-7 because a residual is an adding-up identity
    # over at most 15 cells, not an optimum over a polytope.
    tolerance: float = 1.0e-9
    max_bisection_iterations: int = 200
    max_projection_iterations: int = 1000
    # §12.4 requires "a small positive floor for zero raw seeds" and gives no value. A seed of
    # exactly 0 makes the KL objective undefined, so this is a hard numerical requirement.
    zero_seed_floor: float = 1.0e-12
    # §12.6 step 3. MUST stay deterministic or §16.1's idempotence requirement breaks.
    integerization_tiebreak: Literal["largest_remainder"] = "largest_remainder"


class BaselinesConfig(_Strict):
    """Which §10 baselines run, and the declared-composite policy they run under.

    `allow_declared_composite` is not a convenience switch. With it false, §10.3 and §10.4 decline
    in every month of the D1 window — six states have no observed employment history and two have
    no CBP row at all, and every month's missing set contains at least one of them — which would
    leave §10.8's rungs 1 and 3 permanently empty. See the plan's coverage table.
    """

    allow_declared_composite: bool = True
    composite_fallback: Literal["establishment_proportional"] = "establishment_proportional"
    historical_lookback_months: int = 24
    # §10.3 requires "classification-consistent periods". The window breaks at 2022-01.
    historical_may_cross_naics_vintage: bool = False
    # §10.6. scipy is already a declared dependency; sklearn is not and is not added.
    regression_ridge_penalty: float = 1.0


class DisclosureConfig(_Strict):
    """Disclosure actions and the narrowness thresholds (Appendix A `disclosure:`, §21).

    The two width keys resolve §21's "Disclosure thresholds" row, which the spec leaves to the
    governance owner. A cell is narrow when its feasible width is at most
    `narrow_interval_absolute_width` employees, or when width divided by midpoint is at most
    `narrow_interval_relative_width`. §14.2 asks for both an absolute and a relative test, so both
    are configured and either one alone is sufficient to route a cell to review.
    """

    exact_reconstruction_action: Literal["withhold", "manual_review", "release"]
    narrow_interval_action: Literal["withhold", "manual_review", "release"]
    publish_label_required: bool
    narrow_interval_absolute_width: float
    narrow_interval_relative_width: float


class ValidationConfig(_Strict):
    """§13's harness settings, adapted from Appendix A.

    `include_vintage_comparison` defaults False against Appendix A's True: measured 2026-09-07, no
    period in any staged table carries a second snapshot, and `release_vintage` is the reference
    quarter lowercased rather than a publication vintage. Turning it on is a fail-closed error in
    `regimes.py`, not a silent empty partition.
    """

    pseudo_suppression_seeds: list[int] = [1024, 2048, 4096]
    include_random_mask_sanity_check: bool = True
    include_primary_like: bool = True
    include_complementary_like: bool = True
    include_long_runs: bool = True
    include_rolling_origin: bool = True
    include_retrospective_smoothing: bool = False
    include_vintage_comparison: bool = False
    replicates_per_regime: int = 20
    minimum_unmasked_lookback_months: int = 6
    minimum_missing_set_size: int = 2
    # DECLARED, not detected. A per-cell break detector inside a validation stage is a research
    # project, and the national series does not separate COVID from seasonality cleanly enough to
    # justify one. The second window overlaps `naics_transition`; score a month under ONE label.
    structural_break_windows: list[tuple[str, str]] = [
        ("2020-03", "2020-06"),
        ("2021-10", "2022-03"),
    ]
    naics_seam_month: str = "2022-01"
    naics_seam_halfwidth_months: int = 3

    @model_validator(mode="after")
    def _refuse_a_random_mask_only_design(self) -> ValidationConfig:
        """§13.2 forbids random masking as the ONLY validation design; refuse that config.

        A validator rather than a check inside the harness, because the harness would discover it
        one full pass late. `include_random_mask_sanity_check` is deliberately absent from the
        disjunction: it names the design this rule exists to exclude, not one of the designed
        regimes that satisfies it.
        """
        designed = (
            self.include_primary_like
            or self.include_complementary_like
            or self.include_long_runs
            or self.include_rolling_origin
            or self.include_retrospective_smoothing
            or self.include_vintage_comparison
        )
        if not designed:
            raise ValueError(
                "random_mask_only: §13.2 prohibits random masking as the ONLY validation design. "
                "Enable at least one designed regime beside the random sanity check."
            )
        return self


class PromotionConfig(_Strict):
    """§13.10's gates. Configurable engineering thresholds, not findings."""

    minimum_wape_improvement: float = 0.05
    maximum_major_stratum_wape_degradation: float = 0.02
    nominal_coverage_tolerance: float = 0.05


class Config(_Strict):
    """The whole resolved configuration."""

    project: ProjectConfig
    storage: StorageConfig
    sources: SourcesConfig
    constraints: ConstraintsConfig
    reconciliation: ReconciliationConfig
    baselines: BaselinesConfig
    disclosure: DisclosureConfig
    validation: ValidationConfig = ValidationConfig()
    promotion: PromotionConfig = PromotionConfig()


def load_config(path: Path) -> Config:
    """Parse and validate a config file. Raises pydantic.ValidationError on any violation."""
    return Config.model_validate(yaml.safe_load(path.read_text()))


def resolved_dict(cfg: Config) -> dict[str, object]:
    """The config as it is written to a run directory.

    Only `api_key_env` -- the *name* of an environment variable -- survives; no value is read
    here, so no key can leak into a manifest through this path (§7.2, D3).
    """
    return cfg.model_dump(mode="json")


def credentials(env_path: Path | None = None) -> dict[str, str]:
    """Credentials from the repo-root `.env`, falling back to the process environment.

    Returns only the keys D3 names. The caller passes values to a request; nothing here writes
    them anywhere.
    """
    values: dict[str, str] = {}
    if env_path is not None and env_path.exists():
        values.update({k: v for k, v in dotenv_values(env_path).items() if v is not None})
    for name in (*SECRET_ENV_VARS, "BLS_CONTACT_EMAIL"):
        from_env = os.environ.get(name)
        if from_env:
            values[name] = from_env
    return values
