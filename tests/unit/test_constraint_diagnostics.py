"""§9.7: what an infeasible component must say before the run stops."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, diagnostics, graph, system
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]


def _infeasible(make_monthly, make_size):
    """2024's real margin, with the residual moved from 780 to 600.

    x6 + x7 = 600 with x6 >= 400 and x7 >= 250 has no solution: the supports need 650. This is the
    shape §9.6 step 5 and §9.7 are written for -- a rounding, revision or vintage conflict between
    a published total and published components -- and it is a two-line perturbation of real data
    rather than an invented toy.
    """
    monthly = make_monthly(
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 41488,
            "employment_raw": "41488",
            "qtrly_establishments": 7713,
        }
    )
    size = make_size(
        {
            "size_class": "1",
            "establishments": 5007,
            "employment": 7630,
            "size_lower": 0,
            "size_upper": 4,
        },
        {
            "size_class": "2",
            "establishments": 1501,
            "employment": 9955,
            "size_lower": 5,
            "size_upper": 9,
        },
        {
            "size_class": "3",
            "establishments": 803,
            "employment": 10480,
            "size_lower": 10,
            "size_upper": 19,
        },
        {
            "size_class": "4",
            "establishments": 357,
            "employment": 10316,
            "size_lower": 20,
            "size_upper": 49,
        },
        {
            "size_class": "5",
            "establishments": 40,
            "employment": 2507,
            "size_lower": 50,
            "size_upper": 99,
        },
        {
            "size_class": "6",
            "establishments": 4,
            "employment": None,
            "size_lower": 100,
            "size_upper": 249,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
        {
            "size_class": "7",
            "establishments": 1,
            "employment": None,
            "size_lower": 250,
            "size_upper": 499,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
    )
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(system.build_constraint_system(data, cfg))
    membership = graph.component_membership(built)
    component = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]
    return built, membership, component, cfg


def test_the_diagnostic_reports_the_minimum_slack_and_the_row_carrying_it(
    make_monthly, make_size
) -> None:
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert report.minimum_slack == pytest.approx(50.0)
    assert report.largest_slack_constraints[0][0].startswith("size_margin|")


def test_the_diagnostic_names_every_snapshot_involved(make_monthly, make_size) -> None:
    # §9.7: "all source snapshots involved".
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert "2024_q1_by_size" in report.source_snapshot_ids
    assert "2024q1" in report.source_snapshot_ids


def test_an_irreducible_subsystem_is_reported_when_the_solver_supplies_one(
    make_monthly, make_size
) -> None:
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert report.iis_constraint_ids or report.minimum_slack > 0


def test_the_run_halts_with_the_diagnostic_rather_than_relaxing(make_monthly, make_size) -> None:
    built, _, component, cfg = _infeasible(make_monthly, make_size)
    with pytest.raises(InfeasibleComponentError) as failure:
        bounds.solve_bounds(built, cfg.constraints)
    assert "minimum slack" in str(failure.value)
    assert component in str(failure.value)


def test_an_explicitly_quarantined_component_records_infeasible_instead_of_halting(
    make_monthly, make_size
) -> None:
    built, _, component, cfg = _infeasible(make_monthly, make_size)
    result = bounds.solve_bounds(built, cfg.constraints, quarantined=[component])
    assert set(
        result.bounds.filter(pl.col("component_id") == component).filter(
            pl.col("bound_status") != "observed"
        )["bound_status"]
    ) == {"infeasible"}
    assert len(result.diagnostics) == 1
