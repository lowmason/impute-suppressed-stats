"""The roadmap's Stage 2 exit criteria, on the real D1 window.

Skipped when `data/staged/` is absent. Those tables are gitignored and rebuilt from 562 MB of
frozen source bytes, so this runs where the data lives rather than in CI.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, system
from logging_employment.contracts import HarmonizedData
from logging_employment.disclosure.flags import build_flags

REPO = Path(__file__).resolve().parents[2]
STAGED = REPO / "data" / "staged"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (STAGED / "qcew_monthly.parquet").exists(),
        reason="data/staged/ is gitignored; run `build-harmonized` first",
    ),
]

# The sharp bounds for all 14 suppressed national size cells, derived analytically from the
# published margin and supports before this engine existed. Keys are (reference year, size class).
EXPECTED_BOUNDS: dict[tuple[int, str], tuple[float, float]] = {
    (2018, "5"): (2300.0, 2984.0),
    (2018, "6"): (900.0, 1584.0),
    (2019, "5"): (2450.0, 3304.0),
    (2019, "6"): (600.0, 1454.0),
    (2020, "5"): (2407.0, 3301.0),
    (2020, "6"): (600.0, 1494.0),
    (2021, "5"): (2274.0, 3019.0),
    (2021, "6"): (500.0, 1245.0),
    (2022, "6"): (400.0, 553.0),
    (2022, "7"): (250.0, 403.0),
    (2023, "6"): (700.0, 884.0),
    (2023, "7"): (250.0, 434.0),
    (2024, "6"): (400.0, 530.0),
    (2024, "7"): (250.0, 380.0),
}


@pytest.fixture(scope="module")
def solved():
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(
        system.build_constraint_system(HarmonizedData.load(STAGED), cfg)
    )
    result = bounds.solve_bounds(built, cfg.constraints)
    flags = build_flags(result.bounds, built.cells, cfg.disclosure)
    return built, result, flags


def test_every_suppressed_state_month_carries_a_bound_status(solved) -> None:
    built, result, _ = solved
    suppressed = built.cells.filter(
        (pl.col("observation_status") == "suppressed")
        & pl.col("cell_id").str.starts_with("state_total|")
    )
    assert suppressed.height == 1227  # Stage 1's stamp: 1,227 of 4,716 states+DC cells
    joined = result.bounds.join(suppressed.select("cell_id"), on="cell_id", how="semi")
    assert joined.height == 1227
    assert set(joined["bound_status"]) == {"unbounded"}


def test_the_national_size_bounds_match_the_hand_derived_values(solved) -> None:
    _, result, _ = solved
    produced = {}
    for row in result.bounds.filter(
        pl.col("cell_id").str.starts_with("national_size|") & (pl.col("bound_status") != "observed")
    ).iter_rows(named=True):
        _, _, month, _, _, _, size_class = row["cell_id"].split("|")
        produced[(int(month[:4]), size_class)] = (row["selected_lower"], row["selected_upper"])
    assert produced == EXPECTED_BOUNDS


def test_no_real_cell_is_exactly_recoverable_and_exactly_one_is_narrow(solved) -> None:
    # Stated in advance rather than discovered here: no window year has exactly one suppressed
    # class, so exact recovery cannot fire. 2023 class 6 is the single cell whose relative width
    # (184/792 = 0.232) clears the configured 0.25 threshold.
    _, _, flags = solved
    assert flags["exact_reconstruction_flag"].sum() == 0
    narrow = flags.filter(pl.col("narrow_feasible_interval_flag"))
    assert narrow.height == 1
    assert narrow["cell_id"][0].endswith("|6")
    assert "2023-03" in narrow["cell_id"][0]


def test_the_component_decomposition_and_the_rank_cache_behave_at_scale(solved) -> None:
    _, result, _ = solved
    # 4,716 state cells and 8 size components: the state cells are singletons because
    # SRC-QCEW-006 came back `decline`.
    assert result.components.filter(pl.col("cell_count") == 1).height >= 4716
    assert result.components.filter(pl.col("cell_count") > 1).height == 8
    assert result.components["cache_hit"].sum() > 4000  # CON-005 doing real work


def test_no_hard_constraint_rests_on_an_assumed_threshold(solved) -> None:
    # §9.3's final bullets, asserted on the shipped artifact rather than only in the factory.
    built, _, _ = solved
    hard = built.rows.filter(pl.col("is_hard"))
    assert set(hard["constraint_class"]) <= {"public_accounting_fact", "definitional_support"}
    assert hard.filter(pl.col("provenance_text").str.contains("assumed_threshold")).height == 0
