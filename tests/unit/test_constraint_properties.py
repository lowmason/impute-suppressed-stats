"""§17.2's eight Stage 2 constraint properties, on generated toy systems."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, rows, system
from logging_employment.contracts import TARGET_CELL_SCHEMA
from logging_employment.errors import IncompatibleMarginError, InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]
CONFIG = load_config(REPO / "config.yaml")


def _cells(values: dict[str, float | None], vintages: dict[str, str] | None = None):
    """A `target_cell` frame from `{cell_id: observed value or None}`."""
    vintages = vintages or {}
    return pl.DataFrame(
        [
            {
                "cell_id": cell_id,
                "state_fips": "US",
                "reference_month": "2024-03",
                "size_concept": "march_reference",
                "size_class": cell_id,
                "ownership_code": "5",
                "industry_code": "113310",
                "naics_vintage": vintages.get(cell_id, "NAICS 2022"),
                "observation_status": "observed" if value is not None else "suppressed",
                "observed_value": value,
                "source_snapshot_id": "toy",
                "qcew_disclosure_code": "" if value is not None else "N",
            }
            for cell_id, value in values.items()
        ],
        schema=TARGET_CELL_SCHEMA,
    )


def _margin(name: str, weights: dict[str, float], *, vintages: list[str] | None = None):
    """One equality coupling several cells, summing to zero."""
    return rows.constraint(
        constraint_id=name,
        constraint_class="public_accounting_fact",
        relation="eq",
        coefficients=tuple(weights.items()),
        rhs_lower=0.0,
        rhs_upper=0.0,
        is_hard=True,
        evidence_kind="published_value",
        period_scope="2024-03",
        geography_scope="US",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="toy",
        provenance_text=f"toy margin {name}",
        vintage_compatibility_status=rows.vintage_status(vintages or ["NAICS 2022"]),
    )


def _solve(values, drafts, vintages=None):
    cells = _cells(values, vintages)
    all_drafts = [
        *rows.observed_value_rows(cells),
        *rows.nonnegativity_rows(cells),
        *rows.integrality_rows(cells),
        *drafts,
    ]
    row_frame, coefficient_frame = rows.to_frames(all_drafts)
    built = graph.assign_components(
        system.BuiltSystem(
            cells=cells,
            rows=row_frame,
            coefficients=coefficient_frame,
            constraint_set_hash=system.constraint_set_hash(cells, row_frame, coefficient_frame),
            compatibility_report={},
        )
    )
    result = bounds.solve_bounds(built, CONFIG.constraints)
    return {
        row["cell_id"]: (row["selected_lower"], row["selected_upper"], row["bound_status"])
        for row in result.bounds.iter_rows(named=True)
    }


def test_parent_equals_children() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": 40.0, "c": 30.0},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert all(status == "observed" for _, _, status in solved.values())
    with pytest.raises(InfeasibleComponentError):
        _solve(
            {"P": 100.0, "a": 30.0, "b": 40.0, "c": 31.0},
            [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
        )


def test_one_missing_child_is_exactly_recoverable() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": 40.0, "c": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert solved["c"] == (30.0, 30.0, "exactly_recoverable")


def test_two_missing_children_are_only_partially_identified_under_nonnegativity() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": None, "c": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert solved["b"] == (0.0, 70.0, "partially_identified")
    assert solved["c"] == (0.0, 70.0, "partially_identified")


def test_overlapping_margins_identify_a_cell_despite_two_suppressions_per_row() -> None:
    # A 2x2 table: row 1 holds two suppressed cells, so its own margin identifies neither. The
    # column margin does, because the other member of column 1 is published.
    solved = _solve(
        {
            "x11": None,
            "x12": None,
            "x21": 20.0,
            "x22": 30.0,
            "r1": 50.0,
            "r2": 50.0,
            "c1": 25.0,
            "c2": 75.0,
        },
        [
            _margin("row1", {"x11": 1.0, "x12": 1.0, "r1": -1.0}),
            _margin("row2", {"x21": 1.0, "x22": 1.0, "r2": -1.0}),
            _margin("col1", {"x11": 1.0, "x21": 1.0, "c1": -1.0}),
            _margin("col2", {"x12": 1.0, "x22": 1.0, "c2": -1.0}),
        ],
    )
    assert solved["x11"] == (5.0, 5.0, "exactly_recoverable")
    assert solved["x12"] == (45.0, 45.0, "exactly_recoverable")


def test_a_rounding_interval_blocks_a_recovery_an_exact_parent_would_allow() -> None:
    exact = _solve(
        {"P": 100.0, "a": 30.0, "b": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "P": -1.0})],
    )
    assert exact["b"] == (70.0, 70.0, "exactly_recoverable")

    rounded = _solve(
        {"P": None, "a": 30.0, "b": None},
        [
            _margin("m", {"a": 1.0, "b": 1.0, "P": -1.0}),
            rows.rounding_interval_row(
                "round|P",
                "P",
                published_value=100.0,
                grid_width=100.0,
                endpoint_rule="lower closed, upper open per source documentation",
                period_scope="2024-03",
                geography_scope="US",
                industry_scope="113310",
                ownership_scope="5",
                source_snapshot_ids="toy",
            ),
        ],
    )
    assert rounded["b"] == (20.0, 120.0, "partially_identified")


def test_integrality_tightens_a_bound_the_lp_leaves_fractional() -> None:
    # 2x - y = 0 with y in [1, 3]: the LP allows x in [0.5, 1.5], integrality pins x to 1.
    solved = _solve(
        {"x": None, "y": None},
        [
            _margin("m", {"x": 2.0, "y": -1.0}),
            rows.rounding_interval_row(
                "round|y",
                "y",
                published_value=2.0,
                grid_width=2.0,
                endpoint_rule="toy grid",
                period_scope="2024-03",
                geography_scope="US",
                industry_scope="113310",
                ownership_scope="5",
                source_snapshot_ids="toy",
            ),
        ],
    )
    assert solved["x"] == (1.0, 1.0, "exactly_recoverable")


def test_a_margin_spanning_two_naics_vintages_is_detected_rather_than_stacked() -> None:
    with pytest.raises(IncompatibleMarginError, match="vintage"):
        _solve(
            {"P": 100.0, "a": 30.0, "b": None},
            [
                _margin(
                    "m",
                    {"a": 1.0, "b": 1.0, "P": -1.0},
                    vintages=["NAICS 2017", "NAICS 2022"],
                )
            ],
            vintages={"a": "NAICS 2017"},
        )


def test_components_solve_independently() -> None:
    together = _solve(
        {"P": 100.0, "a": 30.0, "b": None, "Q": 60.0, "c": 10.0, "d": None},
        [
            _margin("m1", {"a": 1.0, "b": 1.0, "P": -1.0}),
            _margin("m2", {"c": 1.0, "d": 1.0, "Q": -1.0}),
        ],
    )
    alone = _solve(
        {"P": 100.0, "a": 30.0, "b": None},
        [_margin("m1", {"a": 1.0, "b": 1.0, "P": -1.0})],
    )
    assert together["b"] == alone["b"] == (70.0, 70.0, "exactly_recoverable")
    assert together["d"] == (50.0, 50.0, "exactly_recoverable")


def test_an_lp_feasible_component_with_no_integer_point_names_integrality_not_a_row_conflict() -> (
    None
):
    # Review finding: the MILP re-solve sat outside the `try`, so an integer-infeasible component
    # raised the LP-worded message -- "no feasible point ... run diagnostics for the conflicting
    # rows" -- and an operator sent looking for a conflict between published values would find
    # none. `2a - P = 0` with `P` pinned at 3 is LP-feasible at `a = 1.5` and has no integer point.
    with pytest.raises(InfeasibleComponentError) as caught:
        _solve({"P": 3.0, "a": None}, [_margin("m", {"a": 2.0, "P": -1.0})])
    message = str(caught.value)
    assert "no integer-valued point" in message
    assert "integrality rows" in message
    assert "conflicting rows" not in message
