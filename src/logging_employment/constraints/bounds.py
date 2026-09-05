"""§9.6: sharp LP bounds for every unknown cell, one HiGHS model per component.

Two optimizations per unknown cell -- a minimize and a maximize -- give `L_j` and `U_j` of §9.1.
They are sharp feasible bounds under the encoded public information, and they are not confidence
or credible intervals; §7.10 keeps them in columns that Stage 5's posterior intervals never share
(INV-008).

Model construction folds single-cell rows into column bounds and leaves everything else in the
matrix. That is not an optimization: it is §9.1's own form, where `x >= 0` and the box constraints
sit outside `Bx = c`. A row qualifies only when it touches one cell with coefficient exactly 1.0,
so a scaled single-cell restriction still reaches the matrix rather than being silently divided.

Every component gets a feasibility probe before any objective is solved, including components with
no unknown cell. Without it, a component whose published values contradict each other -- 2017's
size margin, if BLS ever revised one class and not the total -- would pass unexamined because there
was nothing to optimize.
"""

from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np
import polars as pl

from ..config import ConstraintsConfig
from ..errors import InfeasibleComponentError, SolverError
from .system import BuiltSystem

# §16.2 names this type `BoundConfig`. It is the `constraints:` block, under the name the spec's
# signature uses.
BoundConfig = ConstraintsConfig

INFINITY = highspy.kHighsInf


@dataclass(frozen=True)
class ColumnSpec:
    """One decision variable: its box, and whether it is an integer count."""

    lower: float
    upper: float
    is_integer: bool


def _single_cell(entries: pl.DataFrame) -> bool:
    """True when a row touches exactly one cell with coefficient 1.0."""
    return entries.height == 1 and entries["coefficient"][0] == 1.0


def column_specs(
    built: BuiltSystem, component_id: str, membership: pl.DataFrame
) -> dict[str, ColumnSpec]:
    """The box and integrality of every cell in one component."""
    cells = sorted(membership.filter(pl.col("component_id") == component_id)["cell_id"].to_list())
    box: dict[str, list[float]] = {cell: [-INFINITY, INFINITY] for cell in cells}
    integer = dict.fromkeys(cells, False)
    # INV-005: only public accounting facts and valid definitional restrictions enter the
    # deterministic feasible set, and `is_hard` is exactly that predicate (§7.8 restricts it to
    # those two classes). A soft row stays in the graph and in the persisted table -- it is part of
    # the recorded system -- but it must not move a bound. Stage 3 adds CBP as
    # `empirical_measurement`, which is when this filter starts doing visible work.
    rows = built.rows.filter((pl.col("component_id") == component_id) & pl.col("is_hard"))
    for row in rows.iter_rows(named=True):
        entries = built.coefficients.filter(pl.col("constraint_id") == row["constraint_id"])
        if row["relation"] == "integrality":
            integer[entries["cell_id"][0]] = True
            continue
        if not _single_cell(entries):
            continue
        cell = entries["cell_id"][0]
        if row["rhs_lower"] is not None:
            box[cell][0] = max(box[cell][0], float(row["rhs_lower"]))
        if row["rhs_upper"] is not None:
            box[cell][1] = min(box[cell][1], float(row["rhs_upper"]))
    return {
        cell: ColumnSpec(lower=box[cell][0], upper=box[cell][1], is_integer=integer[cell])
        for cell in cells
    }


def matrix_rows(built: BuiltSystem, component_id: str) -> list[dict[str, object]]:
    """Every hard row of this component that couples two or more cells.

    Soft rows are excluded here for the same INV-005 reason `column_specs` states. Both filters
    have to agree: a soft row admitted by one and rejected by the other would put half a
    restriction in the model.
    """
    kept: list[dict[str, object]] = []
    for row in built.rows.filter(
        (pl.col("component_id") == component_id)
        & (pl.col("relation") != "integrality")
        & pl.col("is_hard")  # INV-005; see `column_specs`
    ).iter_rows(named=True):
        entries = built.coefficients.filter(pl.col("constraint_id") == row["constraint_id"])
        if _single_cell(entries):
            continue
        kept.append(
            {
                "constraint_id": row["constraint_id"],
                "lower": -INFINITY if row["rhs_lower"] is None else float(row["rhs_lower"]),
                "upper": INFINITY if row["rhs_upper"] is None else float(row["rhs_upper"]),
                "cells": entries["cell_id"].to_list(),
                "values": [float(v) for v in entries["coefficient"].to_list()],
            }
        )
    return kept


def _model(
    specs: dict[str, ColumnSpec],
    rows: list[dict[str, object]],
    config: BoundConfig,
    *,
    integer: bool,
) -> tuple[highspy.Highs, dict[str, int]]:
    """A HiGHS model for one component, and the column index of each cell."""
    order = list(specs)
    at = {cell: i for i, cell in enumerate(order)}
    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("primal_feasibility_tolerance", config.feasibility_tolerance)
    model.setOptionValue("dual_feasibility_tolerance", config.feasibility_tolerance)
    model.setOptionValue("mip_feasibility_tolerance", config.feasibility_tolerance)
    model.addVars(
        len(order),
        np.array([specs[cell].lower for cell in order]),
        np.array([specs[cell].upper for cell in order]),
    )
    for row in rows:
        indices = np.array([at[cell] for cell in row["cells"]], dtype=np.int32)
        model.addRow(row["lower"], row["upper"], indices.size, indices, np.array(row["values"]))
    if integer:
        marked = [i for cell, i in at.items() if specs[cell].is_integer]
        if marked:
            model.changeColsIntegrality(
                len(marked),
                np.array(marked, dtype=np.int32),
                np.array([highspy.HighsVarType.kInteger] * len(marked)),
            )
    return model, at


def _optimize(model: highspy.Highs, index: int, sense: object) -> tuple[float | None, str]:
    """One objective solve, returning the optimum or `None` when that direction is unbounded."""
    model.changeColsCost(1, np.array([index], dtype=np.int32), np.array([1.0]))
    model.changeObjectiveSense(sense)
    model.run()
    status = model.getModelStatus()
    # Read the optimum *before* clearing the cost. `objective_function_value` is evaluated against
    # the model's current cost vector, so clearing the cost first reports 0.0 for every solve --
    # every bound in the engine would come back 0.0 rather than wrong-looking.
    optimum = float(model.getInfo().objective_function_value)
    model.changeColsCost(1, np.array([index], dtype=np.int32), np.array([0.0]))
    if status == highspy.HighsModelStatus.kOptimal:
        return optimum, "optimal"
    if status == highspy.HighsModelStatus.kUnbounded:
        return None, "unbounded"
    # REQ-029 names the solver among the things this system fails closed on. `kIterationLimit`,
    # `kTimeLimit` and `kUnknown` are not answers, and returning `None` for them would be
    # indistinguishable from `kUnbounded` two lines up -- a cell the solver gave up on would ship
    # as a cell public data cannot bound.
    raise SolverError(
        f"HiGHS returned {model.modelStatusToString(status)} while optimizing column {index}; "
        "that is neither an optimum nor an unbounded direction, so no bound can be recorded"
    )


def solve_component(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    config: BoundConfig,
    *,
    integer: bool,
) -> dict[str, tuple[float | None, float | None, str]]:
    """Sharp bounds for every unknown cell in one component.

    Observed cells are not solved: INV-001 pins them to their published values, and an equality
    already in the model would return that value at some solver cost. The feasibility probe below
    is what still exercises those equalities.
    """
    specs = column_specs(built, component_id, membership)
    rows = matrix_rows(built, component_id)
    model, at = _model(specs, rows, config, integer=integer)

    model.run()
    probe = model.getModelStatus()
    if probe == highspy.HighsModelStatus.kInfeasible:
        raise InfeasibleComponentError(
            f"component {component_id} has no feasible point across {len(specs)} cell(s) and "
            f"{len(rows)} coupling row(s); §9.6 forbids relaxing a production constraint to "
            "continue. Run `solve-bounds` diagnostics for the conflicting rows"
        )

    unknown = set(
        built.cells.filter(pl.col("observation_status") == "suppressed")["cell_id"].to_list()
    )
    solved: dict[str, tuple[float | None, float | None, str]] = {}
    for cell, index in at.items():
        if cell not in unknown:
            continue
        lower, lower_status = _optimize(model, index, highspy.ObjSense.kMinimize)
        upper, upper_status = _optimize(model, index, highspy.ObjSense.kMaximize)
        status = (
            "optimal"
            if lower_status == upper_status == "optimal"
            else ("unbounded" if "unbounded" in (lower_status, upper_status) else lower_status)
        )
        solved[cell] = (lower, upper, status)
    return solved
