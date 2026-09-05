"""Typed configuration, loaded from YAML, with credentials kept out of the resolved form."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, field_validator

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
    """Where raw bytes, staged frames, and run outputs live."""

    raw_uri: str
    staged_uri: str
    output_uri: str
    immutable_raw: bool


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


class Config(_Strict):
    """The whole resolved configuration."""

    project: ProjectConfig
    storage: StorageConfig
    sources: SourcesConfig
    constraints: ConstraintsConfig
    disclosure: DisclosureConfig


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
