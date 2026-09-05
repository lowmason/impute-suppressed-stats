"""The §7.1 `source_registry` row."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SourceRegistryRow(BaseModel):
    """One logical source product, described in the eighteen fields §7.1 requires."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    agency: str
    dataset: str
    landing_url: str | None
    endpoint_pattern: str | None
    access_status: Literal["verified", "documented", "unverified", "retired"]
    frequency: str
    reference_period: str
    geography: str
    industry_detail: str
    ownership: str
    statistical_unit: str
    employment_concept: str
    size_dimension: str | None
    disclosure_regime: str
    revision_policy: str
    model_role: str
    limitations: str
