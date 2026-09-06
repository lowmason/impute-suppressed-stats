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

import math
from collections.abc import Collection
from dataclasses import dataclass

import highspy
import numpy as np
import polars as pl

from ..config import ConstraintsConfig
from ..contracts import DETERMINISTIC_BOUNDS_SCHEMA
from ..errors import InfeasibleComponentError, SolverError
from .graph import assign_components, component_membership
from .index import SystemIndex, build_index
from .rank import rank_table
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


def _single_cell(cells: list[str], values: list[float]) -> bool:
    """True when a row touches exactly one cell with coefficient 1.0."""
    return len(cells) == 1 and values[0] == 1.0


def _component_cells(
    component_id: str, membership: pl.DataFrame, index: SystemIndex | None
) -> list[str]:
    """One component's cells, sorted -- the order that becomes the model's column indices."""
    if index is not None:
        return index.cells_by_component[component_id]
    return sorted(membership.filter(pl.col("component_id") == component_id)["cell_id"].to_list())


def _hard_rows(
    built: BuiltSystem, component_id: str, index: SystemIndex | None
) -> list[dict[str, object]]:
    """One component's hard rows, in frame order.

    INV-005: only public accounting facts and valid definitional restrictions enter the
    deterministic feasible set, and `is_hard` is exactly that predicate (§7.8 restricts it to
    those two classes). A soft row stays in the graph and in the persisted table -- it is part of
    the recorded system -- but it must not move a bound. Stage 3 adds CBP as
    `empirical_measurement`, which is when this filter starts doing visible work.

    Both `column_specs` and `matrix_rows` come through here, so the predicate is written once and
    the two cannot disagree about which rows they are dividing between them.
    """
    if index is not None:
        return index.hard_rows_by_component.get(component_id, [])
    return built.rows.filter(
        (pl.col("component_id") == component_id) & pl.col("is_hard")
    ).to_dicts()


def _entries(
    built: BuiltSystem, constraint_id: str, index: SystemIndex | None
) -> tuple[list[str], list[float]]:
    """One constraint's `(cells, values)`, in frame order and aligned to each other.

    Subscripted rather than `.get(..., ([], []))`: an empty group would make `_single_cell` return
    False, so the row would reach `model.addRow` with no cells and no values -- a constraint on
    nothing, narrowing no bound and raising nothing. REQ-029 has this system fail closed, and a
    `KeyError` naming the constraint is what failing closed looks like here.
    """
    if index is not None:
        return index.coefficients_by_constraint[constraint_id]
    frame = built.coefficients.filter(pl.col("constraint_id") == constraint_id)
    return frame["cell_id"].to_list(), [float(v) for v in frame["coefficient"].to_list()]


def column_specs(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    *,
    index: SystemIndex | None = None,
) -> dict[str, ColumnSpec]:
    """The box and integrality of every cell in one component."""
    cells = _component_cells(component_id, membership, index)
    box: dict[str, list[float]] = {cell: [-INFINITY, INFINITY] for cell in cells}
    integer = dict.fromkeys(cells, False)
    for row in _hard_rows(built, component_id, index):
        entry_cells, entry_values = _entries(built, row["constraint_id"], index)
        if row["relation"] == "integrality":
            integer[entry_cells[0]] = True
            continue
        if not _single_cell(entry_cells, entry_values):
            continue
        cell = entry_cells[0]
        if row["rhs_lower"] is not None:
            box[cell][0] = max(box[cell][0], float(row["rhs_lower"]))
        if row["rhs_upper"] is not None:
            box[cell][1] = min(box[cell][1], float(row["rhs_upper"]))
    return {
        cell: ColumnSpec(lower=box[cell][0], upper=box[cell][1], is_integer=integer[cell])
        for cell in cells
    }


def matrix_rows(
    built: BuiltSystem, component_id: str, *, index: SystemIndex | None = None
) -> list[dict[str, object]]:
    """Every hard row of this component that `column_specs` did not fold into a column bound.

    That is every row coupling two or more cells, plus any single-cell row whose coefficient is
    not exactly 1.0 -- `_single_cell` rejects those, so they reach the matrix rather than being
    silently divided through. The two functions partition the hard non-integrality rows
    between them, which is the property that matters.

    Soft rows are excluded here for the same INV-005 reason `_hard_rows` states. Both filters
    have to agree: a soft row admitted by one and rejected by the other would put half a
    restriction in the model. They agree structurally rather than by inspection, because both
    take their rows from `_hard_rows` and narrow from there.
    """
    kept: list[dict[str, object]] = []
    for row in _hard_rows(built, component_id, index):
        if row["relation"] == "integrality":
            continue
        entry_cells, entry_values = _entries(built, row["constraint_id"], index)
        if _single_cell(entry_cells, entry_values):
            continue
        kept.append(
            {
                "constraint_id": row["constraint_id"],
                "lower": -INFINITY if row["rhs_lower"] is None else float(row["rhs_lower"]),
                "upper": INFINITY if row["rhs_upper"] is None else float(row["rhs_upper"]),
                "cells": entry_cells,
                "values": entry_values,
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
    index: SystemIndex | None = None,
    specs: dict[str, ColumnSpec] | None = None,
) -> dict[str, tuple[float | None, float | None, str]]:
    """Sharp bounds for every unknown cell in one component.

    Observed cells are not solved: INV-001 pins them to their published values, and an equality
    already in the model would return that value at some solver cost. The feasibility probe below
    is what still exercises those equalities.

    `specs` is accepted because `solve_bounds` has already computed it for its own record loop and
    an integer re-solve would otherwise compute it a third time. It is not an override: passing
    anything but this component's own specs is a caller error, which is why it is keyword-only and
    defaults to computing them here.
    """
    if specs is None:
        specs = column_specs(built, component_id, membership, index=index)
    rows = matrix_rows(built, component_id, index=index)
    model, at = _model(specs, rows, config, integer=integer)

    model.run()
    probe = model.getModelStatus()
    if probe == highspy.HighsModelStatus.kInfeasible:
        raise InfeasibleComponentError(
            f"component {component_id} has no feasible point across {len(specs)} cell(s) and "
            f"{len(rows)} coupling row(s); §9.6 forbids relaxing a production constraint to "
            "continue. Run `solve-bounds` diagnostics for the conflicting rows"
        )

    unknown = (
        index.suppressed
        if index is not None
        else set(
            built.cells.filter(pl.col("observation_status") == "suppressed")["cell_id"].to_list()
        )
    )
    solved: dict[str, tuple[float | None, float | None, str]] = {}
    for cell, column in at.items():
        if cell not in unknown:
            continue
        lower, lower_status = _optimize(model, column, highspy.ObjSense.kMinimize)
        upper, upper_status = _optimize(model, column, highspy.ObjSense.kMaximize)
        status = (
            "optimal"
            if lower_status == upper_status == "optimal"
            else ("unbounded" if "unbounded" in (lower_status, upper_status) else lower_status)
        )
        solved[cell] = (lower, upper, status)
    return solved


def classify_bound_status(
    *,
    observation_status: str,
    lower: float | None,
    upper: float | None,
    is_integer: bool,
    tolerance: float,
) -> tuple[str, bool, bool]:
    """§7.10's `bound_status`, plus the two exactness flags, from solver output alone.

    One function with one rule table, because a status typed at five call sites is a status that
    will disagree with itself. Two of §7.10's seven values are never returned here:
    `model_estimable` and `model_only` are claims about what a model can do, and §9.1 forbids a
    model at this stage. Stage 8's §15.3 mapping assigns a model-dependence level to a released
    cell; that is a different question asked later.

    `exactly_identified` means the sharp interval is a point. On a published cell that is trivially
    true, and it is left true rather than special-cased: whether a point may be *re-published* is a
    disclosure question, and `disclosure.flags` is what answers it.
    """
    if observation_status != "suppressed":
        return "observed", True, True
    if lower is None or upper is None:
        return "unbounded", False, False
    if is_integer:
        exact = math.ceil(lower - tolerance) == math.floor(upper + tolerance)
        return ("exactly_recoverable" if exact else "partially_identified"), exact, exact
    exact = (upper - lower) <= tolerance
    return ("exactly_recoverable" if exact else "partially_identified"), exact, False


@dataclass(frozen=True)
class BoundResult:
    """§16.2's `solve_bounds` return: the §7.10 table, the rank records, and any diagnostic."""

    bounds: pl.DataFrame
    components: pl.DataFrame
    diagnostics: tuple[object, ...]


def _needs_milp(
    solved: dict[str, tuple[float | None, float | None, str]],
    specs: dict[str, ColumnSpec],
    config: BoundConfig,
) -> bool:
    """Whether an integer re-solve of this component can change anything, at a price worth paying.

    Component-level rather than cell-level (§9.6 step 3): one integer model serves every unknown
    cell in the component, and building it once is cheaper than deciding cell by cell.
    """
    if not config.enforce_integrality:
        return False
    for cell, (lower, upper, _) in solved.items():
        if lower is None or upper is None or not specs[cell].is_integer:
            continue
        if (upper - lower) < config.use_milp_when_lp_interval_width_below:
            return True
    return False


def solve_bounds(
    system: BuiltSystem, config: BoundConfig, *, quarantined: Collection[str] = ()
) -> BoundResult:
    """Sharp bounds for every cell in the system (§16.2, §9.6).

    A component that is infeasible halts the run with the §9.7 diagnostic attached, unless it was
    explicitly named in `quarantined`. Nothing in the D1 window is quarantined; the parameter
    exists because §9.7 makes quarantine the only alternative to a hard failure, and an
    undocumented way to continue past an infeasibility is worse than a named one.
    """
    built = system if system.rows["component_id"].null_count() == 0 else assign_components(system)
    membership = component_membership(built)
    # Built from `built`, never from `system`: the line above may have replaced one with the
    # other, and an index carrying the pre-decomposition rows would put every hard row under a
    # null `component_id` and return an empty row list for every component. Both objects share a
    # `constraint_set_hash` (§18.1 excludes `component_id`), so no hash check would catch it.
    index = build_index(built, membership)
    components = rank_table(
        built, rank_tolerance=config.rank_tolerance, membership=membership, index=index
    )
    rank_by_component = {
        row["component_id"]: (row["numerical_rank"], row["nullity"])
        for row in components.iter_rows(named=True)
    }
    cell_component = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    observation = dict(zip(built.cells["cell_id"], built.cells["observation_status"], strict=True))
    observed_value = dict(zip(built.cells["cell_id"], built.cells["observed_value"], strict=True))

    records: list[dict[str, object]] = []
    reports: list[object] = []
    for component_id in sorted(set(membership["component_id"].to_list())):
        specs = column_specs(built, component_id, membership, index=index)
        # Whether *this* component was found infeasible, which is not the same question as whether
        # it was quarantined. Quarantine is permission to continue past an infeasibility; it is not
        # an instruction to discard the bounds of a component that solved. Re-testing membership of
        # `quarantined` in the record branch below conflated the two and blanked every bound in a
        # feasible quarantined component to `infeasible` with no diagnostic to show for it.
        infeasible = False
        try:
            lp = solve_component(
                built, component_id, membership, config, integer=False, index=index, specs=specs
            )
        except InfeasibleComponentError as failure:
            from . import diagnostics as diagnostics_module  # local: breaks an import cycle

            infeasible = True
            report = diagnostics_module.diagnose(
                built, component_id, membership, config, index=index
            )
            reports.append(report)
            if component_id not in quarantined:
                raise InfeasibleComponentError(
                    f"{failure}\n{diagnostics_module.render(report)}"
                ) from failure
            lp = {
                cell: (None, None, "infeasible")
                for cell in specs
                if observation.get(cell) == "suppressed"
            }

        milp: dict[str, tuple[float | None, float | None, str]] = {}
        if lp and not infeasible and _needs_milp(lp, specs, config):
            try:
                milp = solve_component(
                    built, component_id, membership, config, integer=True, index=index, specs=specs
                )
            except InfeasibleComponentError as failure:
                # An LP-feasible component with no integer point. The §9.7 diagnostic is built on
                # the LP relaxation and would report zero slack here, so attaching it would say
                # "nothing is wrong" about a run that just halted. Name the real cause instead.
                if component_id not in quarantined:
                    raise InfeasibleComponentError(
                        f"component {component_id} is feasible as a linear program but has no "
                        "integer-valued point, so §9.6's integrality requirement cannot be met. "
                        "This is not a conflict between published values -- the §9.7 row "
                        "diagnostic would report no slack -- so look at the integrality rows and "
                        "the class supports that box these cells, not at the coupling rows"
                    ) from failure
                milp = {}

        numerical_rank, nullity = rank_by_component[component_id]
        for cell in specs:
            status_word = observation[cell]
            if status_word == "suppressed" and infeasible:
                bound_status, exact, integer_exact = "infeasible", False, False
                lp_lower = lp_upper = milp_lower = milp_upper = None
                selected_lower = selected_upper = None
                solver_status = "infeasible"
            elif status_word == "suppressed":
                lp_lower, lp_upper, solver_status = lp[cell]
                milp_lower, milp_upper = (
                    milp.get(cell, (None, None, ""))[:2] if milp else (None, None)
                )
                selected_lower = milp_lower if milp_lower is not None else lp_lower
                selected_upper = milp_upper if milp_upper is not None else lp_upper
                bound_status, exact, integer_exact = classify_bound_status(
                    observation_status=status_word,
                    lower=selected_lower,
                    upper=selected_upper,
                    is_integer=specs[cell].is_integer,
                    tolerance=config.feasibility_tolerance,
                )
            else:
                value = None if observed_value[cell] is None else float(observed_value[cell])
                lp_lower = lp_upper = milp_lower = milp_upper = None
                selected_lower = selected_upper = value
                solver_status = "not_solved"
                bound_status, exact, integer_exact = classify_bound_status(
                    observation_status=status_word,
                    lower=value,
                    upper=value,
                    is_integer=specs[cell].is_integer,
                    tolerance=config.feasibility_tolerance,
                )
            records.append(
                {
                    "cell_id": cell,
                    "component_id": cell_component[cell],
                    "rank": numerical_rank,
                    "nullity": nullity,
                    "lp_lower": lp_lower,
                    "lp_upper": lp_upper,
                    "milp_lower": milp_lower,
                    "milp_upper": milp_upper,
                    "selected_lower": selected_lower,
                    "selected_upper": selected_upper,
                    "bound_status": bound_status,
                    "exactly_identified": exact,
                    "integer_exactly_identified": integer_exact,
                    "solver_status": solver_status,
                    "solver_tolerance": config.feasibility_tolerance,
                    "constraint_set_hash": built.constraint_set_hash,
                }
            )
    return BoundResult(
        bounds=pl.DataFrame(records, schema=DETERMINISTIC_BOUNDS_SCHEMA).sort("cell_id"),
        components=components,
        diagnostics=tuple(reports),
    )
