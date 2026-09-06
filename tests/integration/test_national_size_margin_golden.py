"""§17.6: the audited golden for the national by-size margin, on frozen input.

The fourteen `EXPECTED_BOUNDS` pairs are the sharp bounds of every suppressed national size class
in the D1 window, derived by hand from the published all-sizes margin and the published class
supports before this engine existed. That makes them the one golden here that cannot have been
regenerated from a broken engine -- but a golden is only as frozen as its input, and until this
file existed they were compared against `data/staged/`, which is gitignored and rebuilt from live
BLS bytes. A revision to any of the published rows underneath them would have broken a
cardinality-14 equality for a reason that has nothing to do with this engine, and in a clean clone
the comparison did not run at all.

Here the input is `tests/fixtures/national_size_margin/` -- tracked, frozen, and the very rows the
derivation was done on. A diff in `EXPECTED_BOUNDS` is now a claim that this engine changed, and
§17.6's rule applies to it: a documented reason and reviewer approval. The same rule applies to
regenerating the fixture, because re-running its generation script after a revision would undo the
freeze silently while leaving the dict looking untouched.

This module is the only home of that equality. `tests/integration/test_d1_acceptance.py` keeps a
national-size claim this file structurally cannot make: that on the live `data/staged/` build, a
cell carrying two finite endpoints is not labelled with a status meaning public information bounds
it on neither side. This fixture is generated *from* those tables, so a break in the live size-row
build stays invisible here until someone regenerates it. What that file used to carry and no
longer does is this same fourteen-pair equality, run against `data/staged/`; it is made below
instead, against input a BLS revision cannot move.

Two things this file deliberately does not do. It carries no `slow` marker and no `skipif`: it
runs in a clean clone with no `data/` tree at all, in seconds rather than minutes, and that is the
point of it. And it is a new module rather than an addition to `test_constraint_golden.py`, whose
fixture directory is pinned by two other goldens that seven more Marches of size rows would break;
the short preamble below is duplicated on purpose.

What is frozen is the input, not the whole run. `config.yaml` is read on every solve, so
`constraints.use_milp_when_lp_interval_width_below` is a live input to these numbers: raise it past
the narrowest interval here and these cells route through the integer re-solve instead, at which
point the dict is no longer the LP answer it was derived as. That coupling is asserted rather than
described -- `test_the_milp_branch_stays_dormant_so_these_pairs_are_the_lp_answer` reads the
threshold and the widths at run time and writes down neither. `project.industry_code_used` and
`project.size_concept` are live in the same way and are not covered here.

What the frozen input cannot reach, permanently, until it is regenerated: `size_upper` is non-null
on every one of its size rows, so the open-ended top class -- the `ge`-only branch of
`rows.size_support_rows` -- is never built here, and no cell in this family is ever `unbounded`,
`infeasible` or `exactly_recoverable`. The status these cells do carry is asserted rather than
described; which *other* status a different width would earn is `tests/unit/`'s question, not a
golden's.
"""

from __future__ import annotations

import subprocess
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import Config, load_config
from logging_employment.constraints import bounds, graph, system
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "national_size_margin"
FIXTURE_TABLES = ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge")

# The sharp bounds for all 14 suppressed national size cells of the D1 window, derived
# analytically from the published margin and supports before this engine existed. Keys are
# (reference year, size class).
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


def _suppressed_size_bounds() -> tuple[pl.DataFrame, Config]:
    """The solved rows for the suppressed national size cells, and the config that solved them."""
    cfg = load_config(REPO / "config.yaml")
    data = HarmonizedData.load(FIXTURES)
    built = graph.assign_components(system.build_constraint_system(data, cfg))
    solved = bounds.solve_bounds(built, cfg.constraints).bounds.filter(
        pl.col("cell_id").str.starts_with("national_size|")
        & (pl.col("bound_status") != "observed"),
    )
    return solved, cfg


def test_the_frozen_fixture_reproduces_the_hand_derived_national_size_bounds() -> None:
    """The independent oracle, held against input that a BLS revision can no longer move.

    The comparison is an equality on the whole dict rather than a lookup per key, so a missing
    key fails as loudly as a moved number. That is what makes this golden survive the defect an
    oracle recomputed from the same load cannot see: a loader that silently dropped four of the
    eight Marches would shrink a recomputed oracle and the engine together and stay green, while
    here it takes eight keys out of `produced` and `EXPECTED_BOUNDS`, being fixed text, does not
    move with it.

    The frame's own row count is pinned beside the dict, because the dict cannot pin it. The key
    is `(year, size_class)` and drops the rest of `cell_id`, so any two rows agreeing on those two
    fields collapse to one entry and row order decides which one survives. Measured: a join fanout
    inside `solve_bounds` that emits all fourteen rows twice leaves `produced` identical, so the
    equality alone cannot refuse it. `solved.height` is what refuses it -- and, with the equality
    fixing `len(produced)` at fourteen, what makes the dict build genuinely order-invariant instead
    of order-invariant only while the keys happen not to collide.

    Because the fourteen values are known rather than recomputed, this equality is also where the
    two mechanisms that produce them are pinned. The published margin (`rows.size_margin_rows`) and
    the support cap (`rhs_upper` in `rows.size_support_rows`) each close a proper subset of the
    fourteen tighter than the other does, so deleting either one moves numbers in this dict.
    Neither deletion is visible in the *shape* of the answer: with either gone, all fourteen still
    come back two-sided and with the same status, so a test that reads only endpoint-finiteness or
    the label -- which is all a test recomputing its oracle from the same load can afford -- sees
    nothing. That is why the mechanism claim belongs here and not in the live-data file.

    The label is read out of the same rows rather than described beside them.
    `classify_bound_status` returns `unbounded` when an endpoint is `None` and
    `exactly_recoverable` when the interval collapses; a one-word change there can label every one
    of these finite intervals `unbounded` without moving a single number in the dict above, and the
    equality alone would not see it.
    """
    solved, _ = _suppressed_size_bounds()
    produced = {}
    labels = set()
    for row in solved.iter_rows(named=True):
        _, _, month, _, _, _, size_class = row["cell_id"].split("|")
        produced[(int(month[:4]), size_class)] = (
            row["selected_lower"],
            row["selected_upper"],
        )
        labels.add(row["bound_status"])
    assert produced == EXPECTED_BOUNDS
    assert solved.height == len(EXPECTED_BOUNDS)
    assert labels == {"partially_identified"}


def test_the_milp_branch_stays_dormant_so_these_pairs_are_the_lp_answer() -> None:
    """The one input this fixture cannot freeze, checked against the widths rather than described.

    `config.yaml` is read on every solve, so `use_milp_when_lp_interval_width_below` is live even
    though the rows are not. `bounds._needs_milp` re-solves a component as an integer program when
    any interval in it is narrower than that key; raising the key past the narrowest interval here
    routes these cells through the integer branch, and the dict above stops being the LP answer the
    hand derivation produced -- silently, because on this fixture the integer re-solve happens to
    return the same fourteen pairs.

    Both halves are read at run time. Neither the threshold nor the narrowest width is written
    down, so this survives a BLS revision that moves the widths and a policy change that moves the
    key; what it refuses is the two crossing.
    """
    solved, cfg = _suppressed_size_bounds()
    widths = (solved["selected_upper"] - solved["selected_lower"]).to_list()
    assert widths, "no suppressed size cell was solved; the check below is vacuous"
    assert min(widths) >= cfg.constraints.use_milp_when_lp_interval_width_below
    # The consequence, not just its precondition: no `milp_*` value was produced for any cell.
    assert solved["milp_lower"].null_count() == solved.height
    assert solved["milp_upper"].null_count() == solved.height


def test_the_fixture_carries_both_levels_so_the_alignment_gate_is_not_vacuous() -> None:
    """Why published state March rows are in a fixture whose golden needs only the national ones.

    `build_constraint_system` runs `harmonize.universe.assert_definitional_alignment` before it
    creates a single row, and that gate returns early when either level is absent -- its own
    docstring says "That is not a pass." A national-only fixture reproduces all fourteen pairs, so
    the golden above would not notice SRC-QCEW-007 being skipped inside this file.

    Two claims, because the fixture's shape is only half of what "not vacuous" means. The first
    assert is that both levels are present. The second is that the gate is still wired into the
    build path and still raises on this frame: a national/state pair that disagrees on NAICS
    vintage must halt `build_constraint_system`. On a national-only frame that misalignment cannot
    exist and the gate returns without looking, so the second assert fails there too -- the two
    check each other rather than restating one property twice.

    The exception type is all that is pinned. `run_compatibility_gates` calls
    `assert_definitional_alignment` before anything else can raise, so the type identifies the gate
    without this test depending on the wording of its message.
    """
    data = HarmonizedData.load(FIXTURES)
    levels = set(data.qcew_monthly["area_type"].unique().to_list())
    assert {"national", "state"} <= levels
    misaligned = replace(
        data,
        qcew_monthly=data.qcew_monthly.with_columns(
            pl.when(pl.col("area_type") == "state")
            .then(pl.lit("NAICS 2012"))
            .otherwise(pl.col("naics_vintage"))
            .alias("naics_vintage")
        ),
    )
    with pytest.raises(ConceptViolationError):
        system.build_constraint_system(misaligned, load_config(REPO / "config.yaml"))


def test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data() -> None:
    """The property that makes the golden above mean anything.

    `data/` is gitignored. If these four tables were sliced out of it at test time, the golden
    would be pinned to whatever that machine last rebuilt, and a fresh clone could not run this
    file at all.

    `tests/integration/test_baseline_golden.py` states the same claim as `path.exists()`, which a
    locally generated, gitignored file satisfies. Asking git is what separates the two. `git -C
    <root>` rather than a bare `git`, because `ls-files` resolves its pathspec against the process
    CWD -- the trap `scripts/audit/verify_extracts.py` documents. There is no skip and no
    fallback: where git cannot answer, in an unpacked tarball with no `.git`, this file's central
    claim cannot be verified, and a green test would be asserting it anyway.

    `ls-files` output is kept as repo-relative paths rather than reduced to basenames, so a file
    added under a subdirectory of the fixture -- a derivation worksheet, say -- is checked where it
    actually lives instead of being looked for beside the parquets and reported missing.
    """
    prefix = FIXTURES.relative_to(REPO).as_posix()
    listed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--", prefix],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.returncode == 0, (
        f"`git ls-files` failed in {REPO}: {listed.stderr.strip() or listed.returncode}. This "
        "file asserts that its fixture is in git; where git cannot say, the assertion is "
        "unverifiable rather than satisfied"
    )
    tracked = {line for line in listed.stdout.splitlines() if line}
    expected = {f"{prefix}/{name}.parquet" for name in FIXTURE_TABLES}
    assert expected | {f"{prefix}/README.md"} <= tracked
    # Tracked but deleted from the working tree is still a golden nobody can run.
    for line in sorted(tracked):
        assert (REPO / line).exists()
