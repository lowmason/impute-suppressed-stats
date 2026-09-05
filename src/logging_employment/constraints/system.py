"""§16.2's `ConstraintSystem` and `build_constraint_system`.

Assembly order is load-bearing and matches §5.5 and SRC-QCEW-007: the compatibility gates run
first, then cells, then rows. A gate that ran after the rows were built would be checking a system
that already existed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import polars as pl

from ..config import Config
from ..constants import PRIVATE_OWN_CODE
from ..contracts import (
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    TARGET_CELL_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from ..errors import IncompatibleMarginError
from . import cells as cells_module
from . import compat
from . import rows as rows_module

CellTable = pl.DataFrame
ConstraintRowTable = pl.DataFrame
SparseCoefficientTable = pl.DataFrame


class ConstraintSystem(Protocol):
    """§16.2's structural interface: cells, rows, and sparse coefficients."""

    cells: CellTable
    rows: ConstraintRowTable
    coefficients: SparseCoefficientTable


@dataclass(frozen=True)
class BuiltSystem:
    """A concrete `ConstraintSystem`, plus the hash and the gate report it was built under."""

    cells: CellTable
    rows: ConstraintRowTable
    coefficients: SparseCoefficientTable
    constraint_set_hash: str
    compatibility_report: dict[str, object]


def _frame_digest(frame: pl.DataFrame) -> str:
    """A sha256 over a frame's columns and its rows in total order."""
    ordered = frame.sort(by=frame.columns)
    payload = json.dumps(
        {"columns": ordered.columns, "rows": ordered.rows()}, default=str, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def constraint_set_hash(
    cells: CellTable, rows: ConstraintRowTable, coefficients: SparseCoefficientTable
) -> str:
    """The §18.1 constraint-set hash.

    `component_id` is excluded: components are *derived* from the coefficient pattern, so a system
    hashed before and after decomposition is the same system. Including it would make the hash
    change when only the labelling did, and §18.1 wants the hash to identify the constraint set.
    """
    without_components = rows.drop("component_id")
    digests = [_frame_digest(f) for f in (cells, without_components, coefficients)]
    return hashlib.sha256("|".join(digests).encode("utf-8")).hexdigest()


def build_constraint_system(data: HarmonizedData, config: Config) -> BuiltSystem:
    """Assemble the whole deterministic system from the harmonized layer (§16.2)."""
    industry = config.project.industry_code_used
    report = compat.run_compatibility_gates(data, industry_code=industry)

    cell_frame = cells_module.build_target_cells(
        data,
        industry_code=industry,
        ownership_code=PRIVATE_OWN_CODE,
        size_concept=config.project.size_concept,
    )
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry)

    drafts = [
        *rows_module.observed_value_rows(cell_frame),
        *rows_module.nonnegativity_rows(cell_frame),
        *rows_module.integrality_rows(cell_frame),
        *rows_module.size_margin_rows(cell_frame),
        *rows_module.size_support_rows(cell_frame, size),
    ]
    kinds = {cid: cid.split("|")[0] for cid in cell_frame["cell_id"].to_list()}
    rows_module.assert_no_national_employment_margin(drafts, kinds)

    row_frame, coefficient_frame = rows_module.to_frames(drafts)
    validate_frame(cell_frame, TARGET_CELL_SCHEMA, "target_cell")
    validate_frame(row_frame, CONSTRAINT_ROW_SCHEMA, "constraint_row")
    validate_frame(coefficient_frame, CONSTRAINT_COEFFICIENT_SCHEMA, "constraint_coefficient")

    return BuiltSystem(
        cells=cell_frame,
        rows=row_frame,
        coefficients=coefficient_frame,
        constraint_set_hash=constraint_set_hash(cell_frame, row_frame, coefficient_frame),
        compatibility_report=report,
    )


def load_system(constraints_dir: Path, *, expected_hash: str | None = None) -> BuiltSystem:
    """Rebuild a system from the three persisted tables, optionally pinned to a known hash.

    `solve-bounds` runs as a separate invocation, so it reads what `build-constraints` wrote rather
    than reassembling from the harmonized layer. Recomputing the constraint set here would make the
    two commands two implementations of one contract, and §17.6's golden constraint matrices would
    only ever check one of them.

    `expected_hash` closes the gap that separation opens. The run id is derived from the
    *harmonized* inputs while these tables come from `data/constraints/`, so nothing else stops a
    `solve-bounds` run from writing bounds into a directory keyed to inputs that did not produce
    them. Passing the hash the build recorded is what makes §18.1's `constraint_set_hash`
    load-bearing rather than decorative.
    """
    frames = {}
    for name in ("target_cell", "constraint_row", "constraint_coefficient"):
        path = constraints_dir / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing; run `build-constraints` first")
        frames[name] = pl.read_parquet(path)
    digest = constraint_set_hash(
        frames["target_cell"], frames["constraint_row"], frames["constraint_coefficient"]
    )
    if expected_hash is not None and digest != expected_hash:
        raise IncompatibleMarginError(
            f"constraint_set_hash mismatch: {constraints_dir} holds {digest}, the run manifest "
            f"records {expected_hash}. These tables were not built from the harmonized inputs "
            "this run is keyed to; re-run `build-constraints`"
        )
    return BuiltSystem(
        cells=frames["target_cell"],
        rows=frames["constraint_row"],
        coefficients=frames["constraint_coefficient"],
        constraint_set_hash=digest,
        compatibility_report={},
    )
