"""The roadmap's Stage 2 exit criteria, on the real D1 window.

Skipped when `data/staged/` is absent. Those tables are gitignored and rebuilt from 562 MB of
frozen source bytes, so this runs where the data lives rather than in CI.

Nothing here asserts a count. Every number this file used to pin -- 1,227 suppressed state-months,
4,716 state cells, 8 size components, 4,000 cache hits, one narrow cell at 2023-03 class 6, and the
fourteen hand-derived national-size pairs -- was a measurement dated 2026-09-05, and one BLS
revision moves all of them. What is asserted instead is structure, with every quantity recomputed
at run time from the staged tables and from `config.yaml`. The fourteen pairs still exist as
literals, in `tests/integration/test_national_size_margin_golden.py`, where the input is a tracked
fixture and an equality against typed numbers means what a golden is supposed to mean.

The national size family is represented here by exactly one test, and only for the claim that
golden structurally cannot make. The golden re-solves a fixture and states both the fourteen
ENDPOINT pairs and the label they carry, so on that input it already refuses a mislabel. What it
cannot reach is the LIVE build: its fixture was generated FROM these staged tables and is frozen at
the vintage someone last regenerated it, so a break in the live size-row path -- endpoint or label
-- stays invisible there until that happens. That gap is the whole reason the size test below
exists. The sharp-bounds oracle this file used to recompute from the live published rows is gone on
purpose: the golden states that same equality against controlled input, which is strictly stronger
than restating it against input that moves.

Non-vacuity guards here are derived from `project.start_month` / `project.end_month` wherever the
alternative would be a non-emptiness test read off the data. The engine, the cell index and every
frame these tests hold against each other descend from one `HarmonizedData.load`, so a guard read
off any of them is a guard that a silent upstream row filter satisfies by shrinking every side
together; the configured window is the one input to these comparisons that no data-path defect can
move.

This file records nothing. The anti-drift rule's "record them in the run manifest" half is already
satisfied outside the test suite -- `cli.py`'s `solve-bounds` writes `disclosure_flags.parquet` and
echoes the flag tallies into the run directory -- and an acceptance test that grew a manifest side
effect would be writing the measurements it just stopped asserting.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path

import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.config import Config, load_config
from logging_employment.constraints import bounds, graph, rank, system
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

# The family prefix `cells.cell_id` stamps on the front of every identifier. Used in place of a
# `starts_with("state_total|")` string so that one expression is the file's single notion of "which
# family is this cell", and a rename in `cells` moves every test together.
_KIND = pl.col("cell_id").str.split("|").list.first()


@pytest.fixture(scope="module")
def config() -> Config:
    """The run's configuration -- the one input to this file that is not downstream of the data."""
    return load_config(REPO / "config.yaml")


@pytest.fixture(scope="module")
def harmonized(config) -> HarmonizedData:
    """The Stage 1 tables, loaded once and shared with the solve below.

    Deliberately the same frames `solved` builds from: an oracle re-loading the same directory
    would not be any more independent of the loader, and the guards that do close that gap are
    derived from `config` instead.
    """
    return HarmonizedData.load(STAGED)


@pytest.fixture(scope="module")
def solved(config, harmonized):
    """The built system, the solved bounds and the disclosure flags, as `(built, result, flags)`.

    One convention, used by every test below: unpack all three positionally, name the ones the test
    reads and write `_` for the rest -- `built, result, _`, `_, result, _`, `built, _, _`. Naming an
    unused one is not an option (ruff's RUF059), and a file where one test writes `built, _, flags`
    and its neighbour writes `built, result, flags` is how independent edits to this module have
    disagreed with each other before.
    """
    built = graph.assign_components(system.build_constraint_system(harmonized, config))
    result = bounds.solve_bounds(built, config.constraints)
    flags = build_flags(result.bounds, built.cells, config.disclosure)
    return built, result, flags


def _configured_months(config: Config) -> list[str]:
    """Every `YYYY-MM` the configured window covers, derived from config rather than from data."""
    first = int(config.project.start_month[:4]) * 12 + int(config.project.start_month[5:7]) - 1
    last = int(config.project.end_month[:4]) * 12 + int(config.project.end_month[5:7]) - 1
    return [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(first, last + 1)]


def _months_missing(present: Iterable[str], expected: Iterable[str]) -> list[str]:
    """Months in `expected` with no row in `present`, sorted.

    The one spelling of "does this frame reach the window the run was configured for" in this file.
    Three assertions below go through it; two spellings of it would be two things to weaken.
    """
    return sorted(set(expected) - set(present))


def test_every_suppressed_state_month_carries_a_bound_status(solved, config) -> None:
    """The name is the invariant; the 1,227 this test used to assert twice was not.

    That literal was Stage 1's stamp, a measurement one BLS revision moves, and it stood in for
    claims a revision does not move: the cell index carries exactly the suppressed state rows the
    staged layer publishes, every one of them has exactly one row in `deterministic_bounds`, both
    endpoints are what `unbounded` is supposed to mean, and the label agrees with them.

    The source anchor is not redundant with the coverage assertions. Both sides of the join descend
    from the same `build_target_cells` call, so a regression that dropped *some* suppressed state
    cells would drop their bound rows with them and leave the join exactly as green as it is here.
    """
    built, result, _ = solved
    # Read the staged parquet directly rather than through the `harmonized` fixture, and do not
    # fold this into it: `built.cells` and `result.bounds` both descend from `HarmonizedData.load`,
    # so an anchor read through that loader would move with the very defect it exists to catch.
    staged_state = pl.read_parquet(STAGED / "qcew_monthly.parquet").filter(
        pl.col("area_type") == "state"
    )
    absent = _months_missing(staged_state["reference_month"].to_list(), _configured_months(config))
    assert not absent, (
        f"the staged state panel publishes no row at all for {absent}; it does not cover "
        f"{config.project.start_month}..{config.project.end_month}, so the anchor below is scoped "
        "to whatever survived the harmonize step rather than to the configured window"
    )

    staged_suppressed = staged_state.filter(pl.col("observation_status") == "suppressed")
    suppressed = built.cells.filter(
        (pl.col("observation_status") == "suppressed") & (_KIND == "state_total")
    )
    # The `> 0` half is the non-vacuity guard, chained onto the anchor rather than left to the
    # status assertion below: `set(...) == {"unbounded"}` does fail on an empty frame today, but
    # that is a property of the `==` form, not a guarantee.
    assert suppressed.height == staged_suppressed.height > 0

    covered = result.bounds.join(suppressed.select("cell_id"), on="cell_id", how="semi")
    missing = suppressed.select("cell_id").join(
        result.bounds.select("cell_id"), on="cell_id", how="anti"
    )
    # The three `sorted(...)` calls in this test's failure messages are not correctness fixes --
    # a message renders only on an already-red assert -- but the frames behind them came through a
    # join, whose row order polars leaves unspecified, so the unsorted form makes the first three
    # names printed differ between runs of the same failure.
    assert (
        missing.is_empty()
    ), f"suppressed state cells with no bound row: {sorted(missing['cell_id'].to_list())[:3]}"
    # The anti-join says every suppressed cell has at least one bound row; this says at most one.
    # `semi` returns the matching left rows, so a duplicated bound row inflates it while the
    # anti-join stays empty.
    assert covered.height == suppressed.height

    # `classify_bound_status` returns `unbounded` when EITHER endpoint is None, so the label alone
    # cannot tell "floored at zero, open above" from "nothing bounds this cell at all" -- a run
    # that lost §9.1's `x >= 0` on every one of these cells carries this same label. Assert the two
    # endpoints the label is derived from, then the label. Not `selected_lower == 0.0`: 0.0 is a
    # measurement of the box, emptiness of the null set is the structure.
    assert covered.filter(pl.col("selected_lower").is_null()).is_empty(), (
        "suppressed state cells whose sharp lower bound went missing: "
        f"{sorted(covered.filter(pl.col('selected_lower').is_null())['cell_id'].to_list())[:3]}"
    )
    assert covered.filter(pl.col("selected_upper").is_not_null()).is_empty()
    assert set(covered["bound_status"]) == {"unbounded"}


def test_no_national_size_label_contradicts_the_interval_the_engine_gave_that_cell(
    solved, config
) -> None:
    """The one national-size claim `test_national_size_margin_golden.py` structurally cannot make.

    That golden re-solves a tracked fixture and states the fourteen ENDPOINT pairs and the one
    label they carry. It is the stronger statement about the arithmetic, and this file no longer
    restates it; it makes a label claim too, so the difference here is not WHICH claim but on WHICH
    INPUT. Its fixture was generated from these same staged tables and is frozen at the vintage
    someone last regenerated it, so nothing it says reaches the live build until that happens.
    Every claim below is about `data/staged/` as it stands on this run.

    Both directions the endpoints can contradict the label are asserted, because both are labels:
    `classify_bound_status` returns `unbounded` only when an endpoint is None and `solve_bounds`
    writes `infeasible` only on a component whose endpoints it also blanked, so two finite
    endpoints refute both; and `exactly_recoverable` is a claim that public information pins the
    cell to a single job count, so an interval holding two whole job counts may not carry it. Each
    reads the label against the interval rather than restating the rule that chose it. Which of
    §7.10's remaining values a given width earns is that rule, and `tests/unit/test_bound_status.py`
    owns it.

    Scope, stated rather than implied. This reddens for a cell the engine DID bound and then
    mislabelled. A cell it failed to bound at all leaves a null endpoint, skips the loop, and is
    the golden's endpoint equality to catch.
    """
    built, result, _ = solved
    size_cells = built.cells.filter(_KIND == "national_size").select("cell_id", "reference_month")
    # The window guard, read off `project.start_month` / `end_month` rather than off the data:
    # every March the run is configured for must have reached the cell index as a national size
    # cell. All of them, not just the suppressed ones -- "every March carries a suppressed class"
    # is a fact about one vintage (2017-03 carries none today), and a March that goes fully
    # published is a legitimate BLS revision rather than a regression.
    absent = _months_missing(
        size_cells["reference_month"].to_list(),
        [month for month in _configured_months(config) if month.endswith("-03")],
    )
    assert not absent, (
        f"the cell index carries no national size cell at all for {absent}; the size universe "
        f"does not cover {config.project.start_month}..{config.project.end_month}, so the loop "
        "below runs over whatever survived the load rather than over the configured window"
    )

    # The second guard is structural, and it is the one that stops the loop passing by running
    # over nothing: the loop reads `bound_status` out of `deterministic_bounds`, so a size family
    # that reached the index and then lost its §7.10 rows leaves every label claim below vacuous.
    # Measured: dropping exactly those rows leaves the window guard above green, because the
    # published classes of every March are still there. Stated here rather than delegated to the
    # index-wide height equality in the narrow-flag test -- delegating this file's non-vacuity to
    # a neighbour is what let a half-emptied size table pass before.
    labelled = size_cells.join(
        result.bounds.select("cell_id", "bound_status", "selected_lower", "selected_upper"),
        on="cell_id",
        how="left",
    )
    unsolved = labelled.filter(pl.col("bound_status").is_null())
    assert unsolved.is_empty(), (
        f"{unsolved.height} national size cell(s) carry no row in deterministic_bounds, e.g. "
        f"{sorted(unsolved['cell_id'].to_list())[:3]}; the label claims below would pass by "
        "having nothing to read"
    )

    # `labelled` came through a join, so its row order is unspecified; every assertion below is
    # per-row and independent of that order, and the two messages above are sorted.
    for row in labelled.filter(pl.col("bound_status") != "observed").iter_rows(named=True):
        lower, upper = row["selected_lower"], row["selected_upper"]
        if lower is None or upper is None:
            continue
        assert row["bound_status"] not in {"unbounded", "infeasible"}, (
            f"{row['cell_id']} carries the finite interval [{lower}, {upper}] but is labelled "
            f"{row['bound_status']}, a label that says public information bounds this cell on "
            "neither side"
        )
        if math.floor(upper) - math.ceil(lower) >= 1:
            assert row["bound_status"] != "exactly_recoverable", (
                f"{row['cell_id']} is labelled {row['bound_status']} on [{lower}, {upper}], an "
                "interval that contains more than one whole job count"
            )


def _suppressed_ids(built: system.BuiltSystem) -> pl.DataFrame:
    """Just the `cell_id`s of the suppressed cells, for semi-joining a flag or bound frame."""
    return built.cells.filter(pl.col("observation_status") == "suppressed").select("cell_id")


def _scored(
    built: system.BuiltSystem, result: bounds.BoundResult, flags: pl.DataFrame
) -> pl.DataFrame:
    """`flags` beside the columns both flag definitions are stated against.

    `observation_status` is the suppressed-only guard the module exists for; `selected_lower` /
    `selected_upper` are what the two width columns are supposed to be derived from.
    """
    return flags.join(
        built.cells.select(["cell_id", "observation_status"]), on="cell_id", how="inner"
    ).join(
        result.bounds.select(["cell_id", "selected_lower", "selected_upper"]),
        on="cell_id",
        how="inner",
    )


def _agrees(column: str, derived: pl.Expr) -> pl.Expr:
    """Whether `column` equals `derived` row by row, counting two nulls as agreement.

    Never null, so `~_agrees(...)` is a filter that surfaces disagreement rather than dropping it:
    `is_null` and `is_not_null` are total, and Kleene `false & null` is false, so a row where one
    side is null and the other is not comes back False. The epsilon is float-noise tolerance -- the
    two sides are the same double-precision operations on the same data.
    """
    return (pl.col(column).is_null() & derived.is_null()) | (
        pl.col(column).is_not_null()
        & derived.is_not_null()
        & ((pl.col(column) - derived).abs() <= 1e-9)
    )


def test_the_narrow_flag_is_the_configured_gate_applied_only_to_suppressed_cells(
    solved, config
) -> None:
    """Not "exactly one cell is narrow": that tally is a measurement of one vintage.

    What the flag MEANS is the invariant -- narrow is suppressed AND an interval that clears a
    threshold living in `config.yaml` -- and that holds at every vintage. The gate's INPUTS are
    pinned first, because the equality below reads `feasible_width` and `relative_width` out of
    `build_flags`' own output: without the derivation check, a mutation of either formula moves the
    flag and the expectation together and nothing here can see it.
    """
    built, result, flags = solved
    scored = _scored(built, result, flags)
    # Both directions, because only one of them is guarded in the source. The chain up to
    # `result.bounds.height` pins bounds-within-cells, which is what `build_flags` itself raises
    # on; the equality against the cell index pins cells-within-bounds, which nothing checks. A
    # cell whose §7.10 row went missing is absent from `disclosure_flags.parquet` as well, so §9.8's
    # MUST review path never sees it -- the failure mode that guard was written to prevent, arriving
    # from the side it cannot see. No literal: both heights are recomputed from this run.
    assert scored.height == flags.height == result.bounds.height == built.cells.height

    width = pl.col("selected_upper") - pl.col("selected_lower")
    midpoint = (pl.col("selected_upper") + pl.col("selected_lower")) / 2
    # §21 and `DisclosureConfig`'s own docstring define the second as width over MIDPOINT.
    misderived = scored.filter(
        ~(
            _agrees("feasible_width", width)
            & _agrees(
                "relative_width", pl.when(midpoint > 0).then(width / midpoint).otherwise(None)
            )
        )
    )
    assert misderived.is_empty(), misderived.select(
        ["cell_id", "selected_lower", "selected_upper", "feasible_width", "relative_width"]
    )

    # §14.2's disjunction, rebuilt from the configured thresholds rather than from the widths any
    # one BLS vintage happens to produce. Null safe by construction: a cell with no width fails the
    # first term, and Kleene `false & null` is false, so the gate is never null.
    disclosure = config.disclosure
    expected = (
        (pl.col("observation_status") == "suppressed")
        & pl.col("feasible_width").is_not_null()
        & (
            (pl.col("feasible_width") <= disclosure.narrow_interval_absolute_width)
            | (
                pl.col("relative_width").is_not_null()
                & (pl.col("relative_width") <= disclosure.narrow_interval_relative_width)
            )
        )
    )
    disagreeing = scored.filter(pl.col("narrow_feasible_interval_flag").ne_missing(expected))
    assert disagreeing.is_empty(), disagreeing.select(
        ["cell_id", "observation_status", "feasible_width", "relative_width"]
    )

    # Preconditions, not tallies. If either population empties out, this run stopped exercising the
    # gate and the equality above went vacuous rather than became true.
    assert (
        scored.filter(
            (pl.col("observation_status") == "suppressed") & pl.col("feasible_width").is_not_null()
        ).height
        > 0
    ), "precondition failed: no suppressed cell carries a width, so the gate is never evaluated"
    assert scored.filter(pl.col("observation_status") != "suppressed").height > 0, (
        "precondition failed: no published cell in the window, so the suppressed-only guard "
        "is never exercised"
    )


def test_the_narrow_gate_moves_with_the_configured_threshold(solved, config) -> None:
    """The equality above compares the flag against `config.yaml`'s own numbers.

    So it still passes if `build_flags` ignores the config and hardcodes today's threshold -- or
    today's `cell_id`. These three re-flags put the knife edge on each branch in turn, at widths
    read off this run rather than typed in.
    """
    built, result, flags = solved
    disclosure = config.disclosure
    # `.sort` on both sides of the two list comparisons below, and here. Polars documents join
    # row order as unspecified -- "the ordering might differ across Polars versions or even
    # between different runs" -- so an equality between two `to_list()`s, one of which came
    # through a join, is a false failure waiting for a polars upgrade.
    bounded = (
        flags.join(_suppressed_ids(built), on="cell_id", how="semi")
        .filter(pl.col("feasible_width").is_not_null())
        .sort("cell_id")
    )
    assert bounded.height > 0, "precondition failed: no suppressed cell has a finite interval"
    assert bounded["relative_width"].null_count() < bounded.height, (
        "precondition failed: no suppressed cell has a relative width, so the relative branch "
        "cannot be exercised"
    )
    min_width, max_width = bounded["feasible_width"].min(), bounded["feasible_width"].max()
    relative = bounded["relative_width"].drop_nulls()
    assert min_width >= 1.0 and relative.min() > 1e-9, (
        "precondition failed: a suppressed interval is at most one employee wide, so a threshold "
        "strictly below every real width would be negative, and nothing in the codebase stops a "
        "config file declaring a negative width -- but a run that needed one would be measuring "
        "an interval narrower than a single employee"
    )
    # The "off" position for each branch: strictly below every real interval, so the branch it
    # disables can flag nothing, and still a width a config file could legally carry.
    off_absolute, off_relative = min_width - 1.0, relative.min() - 1e-9

    # Both branches off: nothing is narrow. Alone this is vacuous -- a flag stuck at False passes
    # it -- and it earns its place only beside the two knife edges below. It does carry the guard,
    # though: every published cell has width 0, well inside this absolute threshold, so dropping
    # the suppressed-only test lights up the whole published window.
    below = disclosure.model_copy(
        update={
            "narrow_interval_absolute_width": off_absolute,
            "narrow_interval_relative_width": off_relative,
        }
    )
    assert (
        build_flags(result.bounds, built.cells, below)["narrow_feasible_interval_flag"].sum() == 0
    )

    # The absolute branch alone, opened exactly to the widest real interval. At the shipped config
    # this branch is inert -- the narrowest suppressed interval is far wider than the configured
    # absolute width -- so without this case its deletion would go unnoticed.
    by_absolute = disclosure.model_copy(
        update={
            "narrow_interval_absolute_width": max_width,
            "narrow_interval_relative_width": off_relative,
        }
    )
    flagged = (
        build_flags(result.bounds, built.cells, by_absolute)
        .filter(pl.col("narrow_feasible_interval_flag"))
        .sort("cell_id")
    )
    assert flagged["cell_id"].to_list() == bounded["cell_id"].to_list()

    # The relative branch alone, opened exactly to the widest real ratio. `<=` is the boundary the
    # config documents, so the cell sitting on the threshold must be inside it.
    by_relative = disclosure.model_copy(
        update={
            "narrow_interval_absolute_width": off_absolute,
            "narrow_interval_relative_width": relative.max(),
        }
    )
    flagged = (
        build_flags(result.bounds, built.cells, by_relative)
        .filter(pl.col("narrow_feasible_interval_flag"))
        .sort("cell_id")
    )
    assert (
        flagged["cell_id"].to_list()
        == bounded.filter(pl.col("relative_width").is_not_null())["cell_id"].to_list()
    )


def test_the_exact_reconstruction_flag_is_raised_by_recoverable_bounds_alone(
    solved, config
) -> None:
    """Not "the window contains no exactly recoverable cell".

    That is a fact about one vintage's constraint system, and the next benchmark can make it false
    without anything here being wrong. The invariant is that the flag tracks `bound_status`, so
    whatever the count, a recoverable cell is withheld rather than published.
    """
    built, result, flags = solved
    scored = _scored(built, result, flags)
    # `_scored` reads `bound_status` out of `flags`, not out of the engine: `build_flags` copies it
    # into `FLAG_SCHEMA`, and the bounds side of that join contributes only the endpoints. So the
    # equality below is `build_flags`' flag against `build_flags`' own column unless the copy is
    # pinned first. That column is also what a §9.8 reviewer reads out of
    # `disclosure_flags.parquet`, and nothing else in this file touches it. Measured: corrupting it
    # alone, with every engine label intact, left all ten tests here green.
    passthrough = flags.join(
        result.bounds.select("cell_id", "bound_status"),
        on="cell_id",
        how="inner",
        suffix="_engine",
    )
    assert passthrough.height == flags.height
    assert passthrough.filter(
        pl.col("bound_status").ne_missing(pl.col("bound_status_engine"))
    ).is_empty()

    expected = (pl.col("observation_status") == "suppressed") & (
        pl.col("bound_status") == "exactly_recoverable"
    )
    disagreeing = scored.filter(pl.col("exact_reconstruction_flag").ne_missing(expected))
    assert disagreeing.is_empty(), disagreeing.select(
        ["cell_id", "observation_status", "bound_status"]
    )

    # No cell in today's window is exactly recoverable, so the equality above is half vacuous: a
    # flag wired to False satisfies it. Collapse one real suppressed interval to a point -- the
    # cell is picked off this run, so no cell_id is pinned -- and the flag must follow it.
    victim = (
        flags.join(_suppressed_ids(built), on="cell_id", how="semi")
        .filter(pl.col("feasible_width").is_not_null())
        .sort("cell_id")["cell_id"]  # join order is unspecified; see the note in the test above
        .first()
    )
    assert victim is not None, "precondition failed: no suppressed cell has a finite interval"
    recovered = result.bounds.with_columns(
        pl.when(pl.col("cell_id") == victim)
        .then(pl.col("selected_lower"))
        .otherwise(pl.col("selected_upper"))
        .alias("selected_upper"),
        pl.when(pl.col("cell_id") == victim)
        .then(pl.lit("exactly_recoverable"))
        .otherwise(pl.col("bound_status"))
        .alias("bound_status"),
    )
    # `build_flags` joins its two arguments and today ends `.sort("cell_id")`, so the two reads
    # below are ordered as things stand. Both are re-stated against that sort rather than against
    # the join: `.sort` makes the list equality independent of the join, and `.item()` raises
    # unless the filter matched exactly one row, which `[0]` on an unexpectedly empty or doubled
    # frame would not.
    reflagged = build_flags(recovered, built.cells, config.disclosure)
    assert reflagged.filter(pl.col("exact_reconstruction_flag")).sort("cell_id")[
        "cell_id"
    ].to_list() == [victim]
    # §9.8 sends both kinds to review, and a point interval is narrow under any non-negative
    # configured width, so the collapsed cell must raise the narrow flag as well.
    assert reflagged.filter(pl.col("cell_id") == victim)["narrow_feasible_interval_flag"].item()


def _coupling_rows(built: system.BuiltSystem) -> pl.DataFrame:
    """Every constraint row touching two or more cells -- the only rows that can fuse a component."""
    return (
        built.coefficients.group_by("constraint_id")
        .len()
        .filter(pl.col("len") > 1)
        .select("constraint_id")
    )


def test_no_coupling_row_touches_a_state_cell_so_each_state_cell_is_its_own_component(
    solved,
) -> None:
    """SRC-QCEW-006 came back `decline`, so no restriction may couple a state cell to anything.

    `rows.assert_no_national_employment_margin` is where that is enforced; the decomposition is
    where it shows up. The singleton components are exactly the state cells, counted from the cell
    index rather than typed. Exactly, not `>=`: `cells.national_total_cells` emits a national cell
    only for a month the size margin needs, so every national cell is necessarily coupled.
    """
    built, result, _ = solved
    coupled_cells = built.coefficients.join(_coupling_rows(built), on="constraint_id", how="semi")
    assert coupled_cells.filter(_KIND == "state_total").height == 0

    membership = graph.component_membership(built)
    state_cells = built.cells.filter(_KIND == "state_total").select("cell_id")
    state_components = membership.join(state_cells, on="cell_id", how="semi").join(
        result.components.select("component_id", "cell_count"), on="component_id", how="left"
    )
    assert state_components.height == state_cells.height
    assert set(state_components["cell_count"].to_list()) == {1}
    assert result.components.filter(pl.col("cell_count") == 1).height == state_cells.height


def test_each_size_margin_month_is_one_component_holding_that_month_s_national_cells(
    solved,
) -> None:
    """`rows.size_margin_rows` writes one equality per March, the only coupling row this stage builds.

    So the coupled components are exactly the national cells partitioned by reference month: one
    component per month, no month split across two, and the coupling rows named for those months.
    """
    built, result, _ = solved
    membership = graph.component_membership(built)
    national = (
        built.cells.filter(_KIND != "state_total")
        .select("cell_id", "reference_month")
        .join(membership, on="cell_id", how="left")
    )
    months = sorted(set(national["reference_month"].to_list()))

    assert set(
        national.group_by("reference_month").agg(pl.col("component_id").n_unique())["component_id"]
    ) == {1}
    assert set(
        national.group_by("component_id").agg(pl.col("reference_month").n_unique())[
            "reference_month"
        ]
    ) == {1}

    coupled = result.components.filter(pl.col("cell_count") > 1)
    assert set(coupled["component_id"]) == set(national["component_id"])
    assert coupled.height == len(months)
    assert set(_coupling_rows(built)["constraint_id"]) == {f"size_margin|{m}" for m in months}

    sized = coupled.select("component_id", "cell_count").join(
        national.group_by("component_id").len(), on="component_id", how="left"
    )
    assert sized.filter(pl.col("cell_count") != pl.col("len")).height == 0


def test_the_rank_cache_reports_its_hits_truthfully_and_never_changes_an_answer(
    solved, config
) -> None:
    """CON-005 is "one computation per distinct component shape".

    The matrices are recompared here byte for byte -- an identity independent of `rank._shape_key`,
    so a key that stopped collapsing identical matrices could not agree with it. The separating
    direction (a key that collapses DISTINCT matrices) is unobservable on this window, because
    every distinct matrix shape here occurs with exactly one value pattern; it lives in
    `tests/unit/test_constraint_rank.py`.
    """
    built, result, _ = solved
    # The window guard again, because everything below is a per-component loop: on an emptied or
    # truncated components table every assertion in this test is a loop over nothing. Read off the
    # cell index rather than off the staged parquet, unlike the guard in
    # `test_every_suppressed_state_month_carries_a_bound_status`: that one exists to anchor the
    # index against the file, this one only asks whether the decomposition covers the window. Do
    # not unify the two -- that anchor's independence from `HarmonizedData.load` is the point of it.
    absent = _months_missing(built.cells["reference_month"].to_list(), _configured_months(config))
    assert not absent, (
        f"the cell index carries no cell at all for {absent}; the per-component checks below would "
        "run over a truncated decomposition and pass by having nothing to disagree with"
    )

    # Each component's dense equality matrix, keyed by component id. `equality_matrix` sorts both
    # its rows and its columns internally, so `tobytes()` is a stable identity here.
    membership = graph.component_membership(built)
    matrices = {
        component_id: rank.equality_matrix(built, component_id, membership)[0]
        for component_id in sorted(set(membership["component_id"].to_list()))
    }
    by_shape: dict[tuple[tuple[int, int], bytes], list[str]] = {}
    for component_id in sorted(matrices):
        matrix = matrices[component_id]
        by_shape.setdefault((matrix.shape, matrix.tobytes()), []).append(component_id)
    # One computation per shape CLASS, rather than naming which member of the class was the one
    # computed. `solve_bounds` walks `sorted(set(membership["component_id"]))` today, so naming the
    # lexicographic first agrees with it by construction -- and would go red on a reordered or
    # parallelised solve that has nothing wrong with it. What CON-005 claims is the count.
    computed = set(result.components.filter(~pl.col("cache_hit"))["component_id"])
    assert len(computed) == len(by_shape)
    for shape, members in sorted(by_shape.items()):
        assert len(computed & set(members)) == 1, (
            f"shape {shape[0]} was computed {len(computed & set(members))} time(s) across "
            f"{len(members)} identical component(s), e.g. {members[:3]}"
        )

    tolerance = config.constraints.rank_tolerance
    for row in result.components.iter_rows(named=True):
        matrix = matrices[row["component_id"]]
        assert (row["equality_row_count"], row["cell_count"]) == matrix.shape
        assert row["structural_rank"] == rank.structural_rank_of(matrix)
        assert row["numerical_rank"] == rank.numerical_rank_of(matrix, tolerance=tolerance)
        assert row["nullity"] == matrix.shape[1] - row["numerical_rank"]

    # Both shape fields again, from the frames rather than through `equality_matrix`, so a defect
    # in that helper cannot move the table and its recomputation together.
    counted = (
        result.components.select("component_id", "cell_count", "equality_row_count")
        .join(
            membership.group_by("component_id").len().rename({"len": "n"}),
            on="component_id",
            how="left",
        )
        .join(
            built.rows.filter((pl.col("relation") == "eq") & pl.col("is_hard"))
            .group_by("component_id")
            .len()
            .rename({"len": "equalities"}),
            on="component_id",
            how="left",
        )
        .with_columns(pl.col("equalities").fill_null(0))
    )
    assert (
        counted.filter(
            (pl.col("cell_count") != pl.col("n"))
            | (pl.col("equality_row_count") != pl.col("equalities"))
        ).height
        == 0
    )


def test_the_rank_cache_computes_once_per_shape_rather_than_once_per_component(solved) -> None:
    """The performance half of CON-005, as a ceiling derived from the decomposition.

    Rather than a floor typed from one run: a singleton's equality matrix is `[[1.0]]` when the
    cell is published and 0x1 when it is suppressed, so two shapes cover every singleton however
    many there are, and each coupled component can contribute at most one more.
    """
    built, result, _ = solved
    # `observed` and `true_zero` are the two statuses `rows.observed_value_rows` pins with a hard
    # equality. Every other status reaches the rank matrix with no equality row of its own, and
    # `cells` admits no fourth (`_assert_every_cell_is_constrainable`).
    singleton_shapes = (
        built.cells.filter(_KIND == "state_total")["observation_status"]
        .is_in(("observed", "true_zero"))
        .n_unique()
    )
    coupled = result.components.filter(pl.col("cell_count") > 1).height
    computations = int((~result.components["cache_hit"]).sum())
    assert computations <= singleton_shapes + coupled
    # This line is the test's only non-vacuity guard: on an emptied components table the ceiling
    # above holds trivially and this does not.
    assert computations < result.components.height


def test_no_hard_constraint_rests_on_an_assumed_threshold(solved) -> None:
    """§9.3's final bullets, asserted on the shipped artifact rather than only in the factory.

    §7.8 gives the warrant no column of its own, so `rows._draft` encodes it into
    `provenance_text` behind the fixed `contracts.EVIDENCE_PREFIX`. A substring search for
    "assumed_threshold" over that free-text column is therefore only as good as the encoding, and
    it fails open in both directions the encoding can break: `str.contains` on a null yields null,
    which `filter` drops, and a refactor that moved the kind into a column of its own would leave
    the prose behind and match nothing. Measured on this window, with a hard row genuinely
    warranted by an assumed threshold planted: under either break all ten tests in this file stay
    green, and this is the only one that reads the column at all.

    So the encoding is pinned before it is searched -- every hard row parses to a kind, and every
    kind is one `contracts` declares -- and the search is on the parsed kind rather than on the
    sentence around it. `strip_prefix` returns its input unchanged when the prefix is absent, so a
    row that lost the prefix arrives as its own prose and fails the closed-set assertion.
    """
    built, _, _ = solved
    hard = built.rows.filter(pl.col("is_hard"))
    # The only non-vacuity guard this test has: every assertion below is a subset or an emptiness,
    # and an empty frame satisfies all of them.
    assert hard.height > 0, "precondition failed: the built system carries no hard constraint row"
    assert set(hard["constraint_class"]) <= {"public_accounting_fact", "definitional_support"}

    kinds = (
        hard["provenance_text"]
        .str.split("; ")
        .list.first()
        .str.strip_prefix(contracts.EVIDENCE_PREFIX)
    )
    assert kinds.null_count() == 0, (
        f"{kinds.null_count()} hard row(s) carry no provenance text, so the warrant search below "
        "matches nothing regardless of what those rows actually rest on"
    )
    # `.drop_nulls()` so the two assertions catch disjoint breaks rather than both catching a
    # null: without it the null case arrives here as an undeclared `None`, the assertion above
    # stops being the only thing that can see it, and `sorted` on a set mixing `None` with a
    # string raises TypeError while rendering the message.
    undeclared = sorted(set(kinds.drop_nulls()) - set(contracts.EVIDENCE_KINDS))
    assert not undeclared, (
        f"hard rows carry warrant(s) {undeclared[:3]} that `contracts.EVIDENCE_KINDS` does not "
        "declare; §9.3 refuses a warrant by name, so a provenance string this cannot parse is a "
        "warrant this test cannot read"
    )
    assert "assumed_threshold" not in set(kinds)

    # The sentence as well as the parsed kind, and searched separately from it so the two catch
    # disjoint breaks. `_draft` refuses a warrant by `evidence_kind`, which makes the kind the
    # load-bearing field and the assertion above the semantically exact one -- but a row whose
    # prose cites an assumed threshold while its kind claims something else is a row whose two
    # halves disagree, and reading only the parsed kind cannot see that. Measured: a hard row
    # prefixed `evidence_kind=published_value` whose prose reads "derived from an
    # assumed_threshold of 250" clears every assertion above. The prefix segment is excluded
    # rather than re-searched, so this cannot stand in for the assertion above.
    prose = hard["provenance_text"].str.split("; ").list.slice(1).list.join("; ")
    citing = prose.str.contains("assumed_threshold")
    assert not citing.any(), (
        f"{citing.sum()} hard row(s) cite an assumed disclosure threshold in their provenance "
        f"while carrying a declared warrant that is not one, e.g. {prose.filter(citing)[0]!r}"
    )
