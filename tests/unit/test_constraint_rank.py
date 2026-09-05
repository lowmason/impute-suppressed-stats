"""CON-003 and CON-005: two ranks per component, and one computation per distinct shape."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import graph, rank, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]


_CLASSES_2024 = (
    {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0, "size_upper": 4},
    {"size_class": "2", "establishments": 20, "employment": 120, "size_lower": 5, "size_upper": 9},
    {
        "size_class": "3",
        "establishments": 10,
        "employment": 130,
        "size_lower": 10,
        "size_upper": 19,
    },
    {"size_class": "4", "establishments": 5, "employment": 150, "size_lower": 20, "size_upper": 49},
    {
        "size_class": "5",
        "establishments": 4,
        "employment": None,
        "size_lower": 50,
        "size_upper": 99,
        "disclosure_code": "N",
        "observation_status": "suppressed",
    },
    {
        "size_class": "6",
        "establishments": 2,
        "employment": None,
        "size_lower": 100,
        "size_upper": 249,
        "disclosure_code": "N",
        "observation_status": "suppressed",
    },
)


def _system(monthly_rows, size_rows):
    data = HarmonizedData(
        qcew_monthly=monthly_rows,
        qcew_national_size=size_rows,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    return graph.assign_components(system.build_constraint_system(data, cfg)), cfg


def _national(month: str, employment: int, establishments: int) -> dict[str, object]:
    return {
        "area_fips": "US000",
        "area_type": "national",
        "state_fips": None,
        "aggregation_level": "18",
        "reference_month": month,
        "reference_quarter": month[:4] + "Q1",
        "employment_value": employment,
        "employment_raw": str(employment),
        "qtrly_establishments": establishments,
    }


@pytest.fixture()
def single_year_table(make_monthly, make_size) -> pl.DataFrame:
    """One March, six classes, two suppressed, plus one suppressed state cell."""
    monthly = make_monthly(
        {
            "state_fips": "01",
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        _national("2024-03", 1000, 91),
    )
    built, cfg = _system(monthly, make_size(*_CLASSES_2024))
    return rank.rank_table(built, rank_tolerance=cfg.constraints.rank_tolerance)


@pytest.fixture()
def built_size_component(single_year_table) -> pl.DataFrame:
    return single_year_table


@pytest.fixture()
def two_identical_years(make_monthly, make_size) -> pl.DataFrame:
    """Two Marches with the same class structure and the same suppression pattern."""

    def _year(year: int) -> list[dict[str, object]]:
        return [
            row
            | {
                "reference_year": year,
                "reference_month": f"{year}-03",
                "reference_quarter": f"{year}Q1",
                "snapshot_id": f"{year}_q1_by_size",
            }
            for row in _CLASSES_2024
        ]

    monthly = make_monthly(_national("2023-03", 1000, 91), _national("2024-03", 1000, 91))
    size = make_size(*_year(2023), *_year(2024))
    built, cfg = _system(monthly, size)
    return rank.rank_table(built, rank_tolerance=cfg.constraints.rank_tolerance)


def test_a_matrix_can_be_structurally_full_rank_and_numerically_deficient() -> None:
    # The two ranks answer different questions, which is why CON-003 asks for both. Two identical
    # rows have a perfect matching in the bipartite pattern and one linearly independent row.
    matrix = np.array([[1.0, 1.0], [1.0, 1.0]])
    assert rank.structural_rank_of(matrix) == 2
    assert rank.numerical_rank_of(matrix, tolerance=1e-10) == 1


def test_a_component_with_no_equality_carries_rank_zero_and_full_nullity() -> None:
    # Every suppressed state cell is this shape: nonnegativity and integrality, no equality.
    matrix = np.zeros((0, 1))
    assert rank.structural_rank_of(matrix) == 0
    assert rank.numerical_rank_of(matrix, tolerance=1e-10) == 0


def test_the_size_component_has_one_degree_of_freedom_per_pair_of_unknowns(
    make_monthly, make_size, built_size_component
) -> None:
    table = built_size_component
    coupled = table.filter(pl.col("cell_count") > 1).row(0, named=True)
    assert coupled["cell_count"] == 7  # six classes plus the national all-sizes cell
    assert coupled["equality_row_count"] == 6  # the margin, four class fixings, one total fixing
    assert coupled["numerical_rank"] == 6
    assert coupled["nullity"] == 1


def test_two_structurally_identical_components_are_computed_once(
    make_monthly, make_size, two_identical_years
) -> None:
    # CON-005: cache reusable hierarchy matrices across periods when definitions are unchanged.
    table = two_identical_years
    coupled = table.filter(pl.col("cell_count") > 1).sort("component_id")
    assert coupled.height == 2
    assert coupled["cache_hit"].to_list() == [False, True]
    assert coupled["numerical_rank"].n_unique() == 1


def test_every_component_appears_exactly_once_in_the_table(single_year_table) -> None:
    assert single_year_table["component_id"].n_unique() == single_year_table.height
