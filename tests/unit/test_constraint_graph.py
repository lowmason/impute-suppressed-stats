"""CON-001/002/004: the bipartite graph, its components, and what explains each one."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import graph, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]


def _built(make_monthly, make_size):
    monthly = make_monthly(
        {
            "state_fips": "01",
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        {
            "state_fips": "02",
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 1000,
            "qtrly_establishments": 54,
        },
    )
    size = make_size(
        {
            "size_class": "1",
            "establishments": 50,
            "employment": 100,
            "size_lower": 0,
            "size_upper": 4,
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
    )
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    return system.build_constraint_system(data, load_config(REPO / "config.yaml"))


def test_the_two_suppressed_state_cells_are_their_own_components(make_monthly, make_size) -> None:
    # Nothing couples them: SRC-QCEW-006 came back `decline`, so there is no state-sum margin.
    assigned = graph.assign_components(_built(make_monthly, make_size))
    membership = graph.component_membership(assigned)
    by_cell = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    state_components = {v for k, v in by_cell.items() if k.startswith("state_total|")}
    assert len(state_components) == 2


def test_the_size_classes_and_the_national_row_share_one_component(make_monthly, make_size) -> None:
    assigned = graph.assign_components(_built(make_monthly, make_size))
    membership = graph.component_membership(assigned)
    by_cell = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    coupled = {v for k, v in by_cell.items() if k.startswith(("national_size|", "national_total|"))}
    assert len(coupled) == 1


def test_component_ids_are_stable_across_runs_and_ordered_by_their_smallest_cell(
    make_monthly, make_size
) -> None:
    first = graph.component_membership(graph.assign_components(_built(make_monthly, make_size)))
    second = graph.component_membership(graph.assign_components(_built(make_monthly, make_size)))
    assert first.equals(second)
    smallest = first.group_by("component_id").agg(pl.col("cell_id").min()).sort("component_id")
    assert smallest["cell_id"].to_list() == sorted(smallest["cell_id"].to_list())


def test_every_row_receives_a_component_id_and_the_cells_table_keeps_its_shape(
    make_monthly, make_size
) -> None:
    # §7.7's field list has no component_id; membership is derived, never stored on the cells.
    built = _built(make_monthly, make_size)
    assigned = graph.assign_components(built)
    assert assigned.rows["component_id"].null_count() == 0
    assert assigned.cells.columns == built.cells.columns
    assert graph.component_membership(assigned)["cell_id"].n_unique() == assigned.cells.height


def test_provenance_names_the_constraints_and_snapshots_behind_each_component(
    make_monthly, make_size
) -> None:
    # CON-004: store enough provenance to explain which public margins identify or narrow a cell.
    assigned = graph.assign_components(_built(make_monthly, make_size))
    provenance = graph.component_provenance(assigned)
    coupled = provenance.filter(pl.col("cell_count") > 1).row(0, named=True)
    assert "size_margin|2024-03" in coupled["constraint_ids"]
    assert coupled["hard_constraint_count"] == coupled["constraint_count"]
    assert "2024_q1_by_size" in coupled["source_snapshot_ids"]


def test_component_snapshots_are_a_set_of_ids_not_a_concatenation_of_lists(
    make_monthly, make_size
) -> None:
    # Not in the plan's code block. `source_snapshot_ids` is comma-joined *per row*, so a margin
    # row carries "a,b" while the fixing rows carry "a" and "b". Calling `.unique()` on the column
    # treats "a,b" as a third distinct value and the component reports a,a,b,b -- four tokens for
    # two snapshots. CON-004 provenance is meant to be read by an auditor; splitting first makes
    # the field a real set.
    assigned = graph.assign_components(_built(make_monthly, make_size))
    coupled = (
        graph.component_provenance(assigned).filter(pl.col("cell_count") > 1).row(0, named=True)
    )
    tokens = coupled["source_snapshot_ids"].split(",")
    assert tokens == sorted(set(tokens))
    assert set(tokens) == {"2024_q1_by_size", "2024q1"}
