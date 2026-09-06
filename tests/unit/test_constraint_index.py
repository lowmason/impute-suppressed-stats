"""The indexed lookups and the frame filters they replace must agree, on every component.

`solve_bounds` builds one `SystemIndex` and threads it through `column_specs`, `matrix_rows` and
`equality_matrix`; that is what turns tens of thousands of full-frame scans into none. Each of
those functions keeps its filter path, for two callers that cannot use the index: `diagnostics`,
which is reached through a local import from inside `solve_bounds`' own except branch, and any
caller that hands in a system the index was not built from -- which
`test_a_soft_row_is_recorded_but_never_narrows_a_bound` does deliberately.

So production takes the indexed path and the filter path is the one that stops being exercised.
`diagnose` runs only on an infeasible component, and the D1 window has none. Without these tests
the two could drift apart and only an infeasible run would notice.

List equality throughout, never set or dict equality: both of the orders these functions return
are HiGHS input. `column_specs`' key order becomes the model's column indices (`_model` builds
`at` from `list(specs)`) and `matrix_rows`' cell order becomes `addRow`'s index array. A
permutation of either is invisible to every other test in this repo -- reversing them leaves the
suite green and the bounds bit-identical -- which is the whole reason this file exists.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, index, rank, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]
CONSTRAINT_FIXTURES = REPO / "tests" / "fixtures" / "constraints"

_REAL_2024 = (
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


def _national(month: str, employment: int, establishments: int) -> dict[str, object]:
    return {
        "area_fips": "US000",
        "area_type": "national",
        "state_fips": None,
        "aggregation_level": "18",
        "reference_month": month,
        "employment_value": employment,
        "employment_raw": str(employment),
        "qtrly_establishments": establishments,
    }


@pytest.fixture()
def toy_system(make_monthly, make_size):
    """A hand-built system with one coupled component and several singletons."""
    cfg = load_config(REPO / "config.yaml")
    data = HarmonizedData(
        qcew_monthly=make_monthly(_national("2024-03", 41668, 7713)),
        qcew_national_size=make_size(*_REAL_2024),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    built = graph.assign_components(system.build_constraint_system(data, cfg))
    return built, graph.component_membership(built), cfg


@pytest.fixture()
def tracked_system():
    """The §17.6 audited fixture: a real multi-component system, tracked in the repo."""
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(
        system.build_constraint_system(HarmonizedData.load(CONSTRAINT_FIXTURES), cfg)
    )
    return built, graph.component_membership(built), cfg


def _components(membership: pl.DataFrame) -> list[str]:
    return sorted(set(membership["component_id"].to_list()))


@pytest.fixture(params=["toy", "tracked"])
def either_system(request, toy_system, tracked_system):
    return toy_system if request.param == "toy" else tracked_system


def test_the_index_and_the_filters_agree_on_every_components_column_specs(either_system) -> None:
    built, membership, _ = either_system
    built_index = index.build_index(built, membership)
    for component_id in _components(membership):
        indexed = bounds.column_specs(built, component_id, membership, index=built_index)
        filtered = bounds.column_specs(built, component_id, membership)
        assert list(indexed) == list(filtered), component_id
        assert indexed == filtered, component_id


def test_the_index_and_the_filters_agree_on_every_components_matrix_rows(either_system) -> None:
    built, membership, _ = either_system
    built_index = index.build_index(built, membership)
    for component_id in _components(membership):
        indexed = bounds.matrix_rows(built, component_id, index=built_index)
        filtered = bounds.matrix_rows(built, component_id)
        assert indexed == filtered, component_id
        for one, other in zip(indexed, filtered, strict=True):
            assert one["cells"] == other["cells"], component_id
            assert one["values"] == other["values"], component_id


def test_the_index_and_the_filters_agree_on_every_components_equality_matrix(
    either_system,
) -> None:
    built, membership, _ = either_system
    built_index = index.build_index(built, membership)
    for component_id in _components(membership):
        indexed, indexed_cells = rank.equality_matrix(
            built, component_id, membership, index=built_index
        )
        filtered, filtered_cells = rank.equality_matrix(built, component_id, membership)
        assert indexed_cells == filtered_cells, component_id
        assert indexed.shape == filtered.shape, component_id
        assert (indexed == filtered).all(), component_id


def test_the_index_covers_every_component_and_every_constraint(either_system) -> None:
    """A lookup that silently misses is the failure mode a `.get(key, [])` default would hide.

    An empty coefficient group makes `_single_cell` return False, so the row reaches
    `model.addRow` with no cells and no values -- a constraint on nothing, which narrows no bound
    and raises nothing. No dataset in this repo has an orphan `constraint_id` in either direction,
    so no other test can distinguish "the lookup never missed" from "the lookup would have been
    fine if it had". This asserts the covering directly.
    """
    built, membership, _ = either_system
    built_index = index.build_index(built, membership)
    assert set(built_index.cells_by_component) == set(_components(membership))
    assert set(built_index.coefficients_by_constraint) == set(
        built.coefficients["constraint_id"].to_list()
    )
    assert set(built.rows["constraint_id"].to_list()) <= set(built_index.coefficients_by_constraint)


def test_the_index_is_built_from_the_system_it_is_handed_not_a_cached_one(toy_system) -> None:
    """`constraint_set_hash` is not a safe cache key, so the index must never be memoised on it.

    `dataclasses.replace` produces a different `BuiltSystem` carrying the SAME hash -- both
    `graph.assign_components` and the soft-row bound test rely on exactly that. An index keyed on
    the hash would serve the pre-replacement frames to a caller holding the post-replacement
    system, silently.
    """
    from dataclasses import replace

    built, membership, _ = toy_system
    widened = replace(built, rows=built.rows.head(built.rows.height - 1))
    assert widened.constraint_set_hash == built.constraint_set_hash
    full = index.build_index(built, membership)
    trimmed = index.build_index(widened, membership)
    assert sum(len(v) for v in trimmed.hard_rows_by_component.values()) < sum(
        len(v) for v in full.hard_rows_by_component.values()
    )
