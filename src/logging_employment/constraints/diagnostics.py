"""§9.7: everything an infeasible component must report before the run stops.

Two independent accounts of the same failure, because §9.7 asks for an irreducible infeasible
subsystem "when supported; otherwise a minimum-slack diagnostic solution", and neither alone is
enough to act on. The IIS names a set of restrictions that cannot hold together; the minimum-slack
solution says by how much, which is what distinguishes a rounding disagreement of a few employees
from a universe mismatch of thousands.

Slack is added to coupling rows only. Column bounds -- nonnegativity and the class supports -- are
definitional, and a diagnostic that "fixed" the infeasibility by letting employment go negative
would be describing a different problem than the one the run hit.
"""

from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np
import polars as pl

from .bounds import INFINITY, BoundConfig, column_specs, matrix_rows
from .index import SystemIndex
from .system import BuiltSystem

MAX_REPORTED_SLACK_ROWS = 5


@dataclass(frozen=True)
class InfeasibilityDiagnostic:
    """§9.7's required content for one infeasible component."""

    component_id: str
    cell_ids: tuple[str, ...]
    source_snapshot_ids: tuple[str, ...]
    iis_constraint_ids: tuple[str, ...]
    iis_cell_ids: tuple[str, ...]
    minimum_slack: float
    largest_slack_constraints: tuple[tuple[str, float], ...]
    candidate_conflicts: tuple[str, ...]


def _candidate_conflicts(rows: pl.DataFrame) -> tuple[str, ...]:
    """The mixed-vintage and mixed-universe readings §9.7 asks a diagnostic to offer."""
    found: list[str] = []
    for column, label in (
        ("vintage_compatibility_status", "vintage compatibility"),
        ("ownership_scope", "ownership universe"),
        ("geography_scope", "geography universe"),
        ("industry_scope", "industry scope"),
    ):
        values = sorted(set(rows[column].to_list()))
        if len(values) > 1:
            found.append(f"{label}: {values}")
    return tuple(found)


def diagnose(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    config: BoundConfig,
    *,
    index: SystemIndex | None = None,
) -> InfeasibilityDiagnostic:
    """Build both accounts of one component's infeasibility."""
    specs = column_specs(built, component_id, membership, index=index)
    coupling = matrix_rows(built, component_id, index=index)
    rows = built.rows.filter(pl.col("component_id") == component_id)
    order = list(specs)
    at = {cell: i for i, cell in enumerate(order)}

    # --- account one: an irreducible infeasible subsystem, if HiGHS offers one ------------------
    plain = highspy.Highs()
    plain.setOptionValue("output_flag", False)
    plain.addVars(
        len(order),
        np.array([specs[c].lower for c in order]),
        np.array([specs[c].upper for c in order]),
    )
    for row in coupling:
        indices = np.array([at[c] for c in row["cells"]], dtype=np.int32)
        plain.addRow(row["lower"], row["upper"], indices.size, indices, np.array(row["values"]))
    plain.run()
    iis_constraints: tuple[str, ...] = ()
    iis_cells: tuple[str, ...] = ()
    status, iis = plain.getIis()
    if status == highspy.HighsStatus.kOk and iis.valid_:
        iis_constraints = tuple(
            str(coupling[i]["constraint_id"]) for i in list(iis.row_index_) if i < len(coupling)
        )
        iis_cells = tuple(order[i] for i in list(iis.col_index_) if i < len(order))

    # --- account two: the minimum total slack, and where it lands -------------------------------
    slack = highspy.Highs()
    slack.setOptionValue("output_flag", False)
    slack.addVars(
        len(order),
        np.array([specs[c].lower for c in order]),
        np.array([specs[c].upper for c in order]),
    )
    costs = [0.0] * len(order)
    for offset, row in enumerate(coupling):
        slack.addVars(2, np.array([0.0, 0.0]), np.array([INFINITY, INFINITY]))
        positive = len(order) + 2 * offset
        indices = np.array([at[c] for c in row["cells"]] + [positive, positive + 1], dtype=np.int32)
        values = np.array([*row["values"], 1.0, -1.0])
        slack.addRow(row["lower"], row["upper"], indices.size, indices, values)
        costs.extend([1.0, 1.0])
    slack.changeColsCost(len(costs), np.array(range(len(costs)), dtype=np.int32), np.array(costs))
    slack.changeObjectiveSense(highspy.ObjSense.kMinimize)
    slack.run()
    total = float(slack.getInfo().objective_function_value)
    values = list(slack.getSolution().col_value)
    per_row = [
        (str(row["constraint_id"]), values[len(order) + 2 * i] + values[len(order) + 2 * i + 1])
        for i, row in enumerate(coupling)
    ]
    per_row.sort(key=lambda pair: pair[1], reverse=True)

    return InfeasibilityDiagnostic(
        component_id=component_id,
        cell_ids=tuple(order),
        source_snapshot_ids=tuple(
            sorted({s for joined in rows["source_snapshot_ids"] for s in joined.split(",")})
        ),
        iis_constraint_ids=iis_constraints,
        iis_cell_ids=iis_cells,
        minimum_slack=total,
        largest_slack_constraints=tuple(per_row[:MAX_REPORTED_SLACK_ROWS]),
        candidate_conflicts=_candidate_conflicts(rows),
    )


def render(report: InfeasibilityDiagnostic) -> str:
    """The diagnostic as the run's final message. §9.7's list, in order."""
    lines = [
        f"component: {report.component_id}",
        f"cells: {len(report.cell_ids)}",
        f"source snapshots: {', '.join(report.source_snapshot_ids)}",
        f"candidate conflicts: {'; '.join(report.candidate_conflicts) or 'none detected'}",
        f"irreducible infeasible subsystem: {', '.join(report.iis_constraint_ids) or 'unavailable'}",
        f"minimum slack: {report.minimum_slack:.6g}",
        "largest required slack: "
        + ", ".join(f"{name}={value:.6g}" for name, value in report.largest_slack_constraints),
    ]
    return "\n".join(lines)
