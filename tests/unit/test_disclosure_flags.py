"""§9.8: which cells go to disclosure review, and which must never be sent there."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA, TARGET_CELL_SCHEMA
from logging_employment.disclosure import flags

REPO = Path(__file__).resolve().parents[2]


def _frames(*rows: tuple[str, str, float | None, float | None]):
    cells = pl.DataFrame(
        [
            {
                "cell_id": cell_id,
                "state_fips": "US",
                "reference_month": "2024-03",
                "size_concept": "march_reference",
                "size_class": "6",
                "ownership_code": "5",
                "industry_code": "113310",
                "naics_vintage": "NAICS 2022",
                "observation_status": status,
                "observed_value": None,
                "source_snapshot_id": "s",
                "qcew_disclosure_code": "N",
            }
            for cell_id, status, _, _ in rows
        ],
        schema=TARGET_CELL_SCHEMA,
    )
    bounds = pl.DataFrame(
        [
            {
                "cell_id": cell_id,
                "component_id": "c000000",
                "rank": 1,
                "nullity": 1,
                "lp_lower": lower,
                "lp_upper": upper,
                "milp_lower": None,
                "milp_upper": None,
                "selected_lower": lower,
                "selected_upper": upper,
                "bound_status": (
                    "observed"
                    if status != "suppressed"
                    else ("unbounded" if upper is None else "partially_identified")
                ),
                "exactly_identified": False,
                "integer_exactly_identified": False,
                "solver_status": "optimal",
                "solver_tolerance": 1e-7,
                "constraint_set_hash": "h",
            }
            for cell_id, status, lower, upper in rows
        ],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    return bounds, cells


def _cfg():
    return load_config(REPO / "config.yaml").disclosure


def test_a_published_cell_is_never_flagged_even_though_its_interval_is_a_point() -> None:
    # The trap this test exists for: an observed cell has width 0, which passes every narrowness
    # test ever written. Flagging it would send 3,462 already-public state-months to review.
    bounds, cells = _frames(("observed-cell", "observed", 700.0, 700.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["exact_reconstruction_flag"].to_list() == [False]
    assert built["narrow_feasible_interval_flag"].to_list() == [False]


def test_an_exactly_recoverable_suppressed_cell_raises_both_flags() -> None:
    bounds, cells = _frames(("exact-cell", "suppressed", 42.0, 42.0))
    built = flags.build_flags(
        bounds.with_columns(
            pl.lit("exactly_recoverable").alias("bound_status"),
            pl.lit(True).alias("exactly_identified"),
        ),
        cells,
        _cfg(),
    )
    assert built["exact_reconstruction_flag"].to_list() == [True]
    assert built["narrow_feasible_interval_flag"].to_list() == [True]


def test_the_one_real_D1_cell_that_clears_the_relative_threshold_is_flagged() -> None:
    # 2023 class 6: [700, 884]. Width 184, midpoint 792, relative width 0.2323 <= 0.25.
    bounds, cells = _frames(("narrow-cell", "suppressed", 700.0, 884.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["relative_width"][0] == pytest.approx(184 / 792)
    assert built["narrow_feasible_interval_flag"].to_list() == [True]
    assert built["exact_reconstruction_flag"].to_list() == [False]


def test_the_next_widest_real_cell_is_not_flagged() -> None:
    # 2024 class 6: [400, 530]. Width 130, midpoint 465, relative width 0.2796 > 0.25.
    bounds, cells = _frames(("wider-cell", "suppressed", 400.0, 530.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["narrow_feasible_interval_flag"].to_list() == [False]


def test_the_absolute_test_alone_is_sufficient() -> None:
    # §14.2 asks for "narrow in absolute or relative terms". Width 10 on a midpoint of 10,000 is
    # relatively enormous and absolutely disclosive.
    bounds, cells = _frames(("absolute-cell", "suppressed", 9995.0, 10005.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["narrow_feasible_interval_flag"].to_list() == [True]


def test_an_unbounded_cell_carries_no_width_and_no_flag() -> None:
    bounds, cells = _frames(("open-cell", "suppressed", 0.0, None))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["feasible_width"][0] is None
    assert built["narrow_feasible_interval_flag"].to_list() == [False]
