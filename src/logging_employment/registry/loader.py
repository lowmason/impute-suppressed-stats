"""Loading the registry from YAML and rendering it as a typed frame."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl
import yaml

from ..contracts import SOURCE_REGISTRY_SCHEMA
from .models import SourceRegistryRow


def load_registry(path: Path) -> list[SourceRegistryRow]:
    """Parse every row in the registry file, validating each against §7.1."""
    payload = yaml.safe_load(path.read_text())
    return [SourceRegistryRow.model_validate(entry) for entry in payload["sources"]]


def registry_frame(rows: Sequence[SourceRegistryRow]) -> pl.DataFrame:
    """Render registry rows as a frame in the declared column order and dtypes."""
    return pl.DataFrame(
        [row.model_dump() for row in rows], schema=SOURCE_REGISTRY_SCHEMA, orient="row"
    )
