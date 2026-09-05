"""§17.6: audited golden fixtures for the constraint matrix and the LP/MILP bounds.

Golden updates require a documented reason and reviewer approval (§17.6 final line). The values
here are published QCEW figures for March 2024 plus two synthetic state rows, and the two bounds
were derived by hand before any of this code existed: residual 41668 - 40888 = 780, against
supports [400, 996] and [250, 499]. A diff in this file is a claim that one of those changed.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "constraints"


def _built():
    cfg = load_config(REPO / "config.yaml")
    return (
        graph.assign_components(system.build_constraint_system(HarmonizedData.load(FIXTURES), cfg)),
        cfg,
    )


def test_the_constraint_matrix_matches_its_golden() -> None:
    built, _ = _built()
    golden = pl.read_csv(FIXTURES / "golden_constraint_matrix.csv")
    assert built.coefficients.sort(["constraint_id", "cell_id"]).equals(golden)


def test_the_bounds_match_their_golden() -> None:
    built, cfg = _built()
    produced = (
        bounds.solve_bounds(built, cfg.constraints)
        .bounds.select(
            ["cell_id", "selected_lower", "selected_upper", "bound_status", "exactly_identified"]
        )
        .sort("cell_id")
    )
    assert produced.equals(pl.read_csv(FIXTURES / "golden_bounds.csv"))


def test_the_golden_carries_the_two_hand_derived_bounds() -> None:
    # A golden that was regenerated from a broken engine would still equal itself. This is the
    # assertion that does not.
    golden = pl.read_csv(FIXTURES / "golden_bounds.csv")
    by_class = {
        row["cell_id"].rsplit("|", 1)[1]: (row["selected_lower"], row["selected_upper"])
        for row in golden.iter_rows(named=True)
        if row["cell_id"].startswith("national_size|")
    }
    assert by_class["6"] == (400.0, 530.0)
    assert by_class["7"] == (250.0, 380.0)
