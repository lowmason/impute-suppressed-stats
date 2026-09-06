# Test-Suite Assertion Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the test assertions that report green on evidence they never ran — dated literals pinned against gitignored data, and three audit tests that silently skip in a clean clone — with assertions computed at run time or read from tracked inputs.

**Architecture:** Three moves, in dependency order. (1) Freeze the one oracle worth keeping: the fourteen hand-derived national-size bounds move out of a live-data test into a new golden whose *input* is a tracked fixture, so the equality means what a golden is supposed to mean and runs in a clean clone. (2) Rewrite the remaining live-data assertions so every quantity is recomputed from the staged tables or from `config.yaml`, and split the two tests whose names encode a data-derived tally. (3) Convert the three `tests/audit/` tests that read gitignored `data/` to the tracked `specs/findings/` artifacts, and inventory the siblings.

**Tech Stack:** Python ≥3.14, Polars, pytest (`--import-mode=importlib`), ruff + black at line-length 100.

## Global Constraints

Every task's requirements implicitly include this section.

- **THE ANTI-DRIFT RULE** (Stage 3 plan, verbatim): "Every count in this plan — 96/96, 1,227, 3,489, 762/465, 32/32, 9–15 — is a measurement dated 2026-09-05, not an invariant. Compute them at run time, record them in the run manifest, and assert on **structure** …, never on the literal number. One BLS revision moves every one of them."
- **A REPLACEMENT MUST STILL BE ABLE TO FAIL.** Every assertion this plan writes is mutation-proven: break the behaviour the test names, observe RED. An assertion that cannot fail is worse than the literal it replaced, because it looks like coverage and is not. This is the plan's primary risk and its acceptance criterion.
- **NON-VACUITY GUARDS COME FROM CONFIG, NOT FROM DATA.** Both the engine and every oracle in the live-data tests descend from one `HarmonizedData.load`, so a guard read off either side is satisfied by a silent upstream row filter shrinking both sides together. `cfg.project.start_month` / `end_month` is the one input no data-path defect can move. *Measured: a loader dropping four of eight March size slices left every proposed size assertion green while the literal it replaced went red.*
- **POLARS JOIN ORDER IS UNSPECIFIED.** No `to_list()` equality, `== [...]`, or positional read downstream of a `join` without an explicit `.sort()` on both sides. Mutation testing structurally cannot find this class, so it is a review item, not a test item.
- **Polars, never pandas.** Style gates: `ruff check` and `black --check` at line-length 100.
- **`data/` is gitignored in its entirety.** A test that reads under `data/` does not run in CI. Tracked equivalents live under `specs/findings/` and `tests/fixtures/`.

## Rulings this plan makes

The deferred items say each breach "needs a ruling on what its structural form is." These are those rulings; each task implements one.

| # | Ruling |
|---|---|
| R1 | The frozen-input golden is a NEW file, `tests/integration/test_national_size_margin_golden.py`. No existing helper's signature changes; a duplicated preamble is the cheaper risk. |
| R2 | The fixture INCLUDES the published state March rows, so `assert_definitional_alignment` is not vacuous inside it. |
| R3 | No `slow` marker and no `skipif` on the golden. Running in a clean clone is the point. |
| R4 | Once the input is frozen, §17.6's golden rule applies to EXPECTED_BOUNDS — and regenerating the fixture is itself a golden update needing the same approval. |
| R5 | The fixture README records row counts, `snapshot_id`s and `release_vintage`s, not a byte hash: parquet bytes are polars-version dependent. |
| R6 | EXPECTED_BOUNDS lives ONLY in the golden. No weakened copy stays in the live-data file. |
| R7 | The three live-data national-size tests collapse to ONE: the label-consistency claim. The golden owns the oracle equality with controlled input; margin-vs-support is dropped, its premise having been measured false. |
| R8 | Every `to_list()` equality / positional read downstream of a join gets `.sort()` on both sides. |
| R9 | Any helper with exactly one caller is inlined. |
| R10 | `test_anchor.py`'s NIT takes BOTH halves — the docstring fix AND the fixture rebuild. Fixing only the prose leaves an accurate docstring describing a test that passes when `closure_audit` silently drops non-closing months. |
| R11 | Only `anchor.py:9`'s `1,227` is fixed. The same literal sits in five other docstrings where it scopes a claim rather than decorating one; those get a new deferred item with the inventory, not five unbudgeted rulings inside this plan. |

---

## File Structure

| File | Responsibility |
|---|---|
| `tests/fixtures/national_size_margin/*.parquet` (create, 4 files, 38.8 KB) | The frozen input for the golden: 401 `qcew_monthly` rows, 51 `qcew_national_size` rows, empty `cbp_state_size` and `bridge`. Tracked in git. |
| `tests/fixtures/national_size_margin/README.md` (create) | Provenance: row counts, `snapshot_id`s, `release_vintage`s, and the regeneration procedure. No byte hash (R5). |
| `tests/integration/test_national_size_margin_golden.py` (create, 241 lines, 4 tests) | Sole home of `EXPECTED_BOUNDS`. Re-solves the frozen fixture. No `skipif`, no `slow` — runs in a clean clone in 1.8 s. |
| `tests/integration/test_d1_acceptance.py` (replace, 110 → 759 lines, 5 → 10 tests) | Live-`data/staged/` structure only. No count asserted anywhere. |
| `tests/integration/test_d1_baselines.py` (modify) | The composite split becomes a flag-flip oracle instead of a magic string. |
| `tests/unit/test_baseline_interfaces.py` (modify, `:28-33`) | Per-cell basis integrity, which the integration test cannot recompute. |
| `tests/unit/test_anchor.py` (modify, `:171-215`) | The NIT: docstring corrected AND the fixture rebuilt so the gate discriminates. |
| `src/logging_employment/reconcile/anchor.py` (modify, `:9`) | Drop the dated `1,227` from a §5.5 dimension-matching argument. |
| `tests/audit/test_ces_levels.py` (modify, 7 hunks) | Three artifact tests read tracked `specs/findings/source-audit.md` instead of gitignored `data/`. |

## Verification status of the code in this plan

Read this before executing. It is not uniform, and the difference matters.

| Tasks | Status |
|---|---|
| 1, 2, 3 (fixture, golden, acceptance) | **Assembled and run as a unit.** `test_d1_acceptance.py` → `10 passed in 13.03s`; the golden → `3 passed in 1.78s` against the frozen fixture (the 4th, the git-tracked guard, fails from `/tmp` by design and passes once committed). Every assertion mutation-proven across three adversarial rounds. |
| 6, 7 (CES) | **Measured in a fresh `git clone`.** Before: `39 passed, 3 skipped`. After: `42 passed`. The seven hunks were proven to reproduce the converted file byte-for-byte. |
| 4, 5 (baselines, anchor NIT) | **Verified at recon, NOT re-run as an assembled unit.** Both the proposal and its adversarial tightening ran code and mutation-proved their assertions, but these tasks did not go through the third reconciliation round. They touch different files from Tasks 1–3, so there is no cross-file consistency risk — but treat their code as needing a real run at Step 2, not a formality. |

The code below was executed with `REPO` hardcoded to an absolute path; in place it uses
`Path(__file__).resolve().parents[2]`, which is what both files already use today.

---

### Task 1: Freeze the national-size margin fixture

**Files:**
- Create: `tests/fixtures/national_size_margin/qcew_monthly.parquet` (401 rows, 30,306 B)
- Create: `tests/fixtures/national_size_margin/qcew_national_size.parquet` (51 rows, 5,669 B)
- Create: `tests/fixtures/national_size_margin/cbp_state_size.parquet` (0 rows, 1,866 B)
- Create: `tests/fixtures/national_size_margin/bridge.parquet` (0 rows, 935 B)
- Create: `tests/fixtures/national_size_margin/README.md`

**Interfaces:**
- Consumes: `data/staged/` (present only where the D1 build has been run).
- Produces: a tracked `staged_root` that `HarmonizedData.load` accepts, carrying every March
  reference month of the configured window plus the published state rows for those months.

Per R2 the state rows are included: without them
`harmonize.universe.assert_definitional_alignment` returns early and the golden's alignment gate
is vacuous. The national-only variant is 18 KB and produces identical bounds — it is the wrong
trade.

- [ ] **Step 1: Confirm the source data is present**

Run: `ls data/staged/qcew_monthly.parquet data/staged/qcew_national_size.parquet`
Expected: both paths listed. If absent, run `logging-estimates build-harmonized` first — this task
cannot be done from a clean clone, which is exactly why its output is committed.

- [ ] **Step 2: Generate the fixture**

Run the procedure below. It selects the March reference months of the configured window from
`qcew_national_size`, the published state rows for those months from `qcew_monthly`, and writes
empty frames carrying the correct schemas for `cbp_state_size` and `bridge`.

<details>
<summary>Fixture generation procedure (verified: produces 401/51/0/0 rows)</summary>

**Building `tests/fixtures/national_size_margin/`

The frozen input behind `tests/integration/test_national_size_margin_golden.py`. Four parquet
files plus a `README.md`, all tracked in git — the golden's third test reads the *index*, not the
working tree, so **the fixture must be `git add`-ed in the same commit as the test file.** A step
that writes both to disk and stages only the `.py` leaves that test red with every file present.
`git check-ignore` exits 1 on both paths, so no `-f` is needed.

#### Preconditions

- Run from the repo root, `/Users/lowell/Projects/impute-suppressed-stats`.
- `data/staged/` present, i.e. `logging-estimates build-harmonized` has been run. The four staged
  tables this reads are `qcew_national_size.parquet`, `qcew_monthly.parquet`,
  `cbp_state_size.parquet`, `bridge.parquet`.
- polars 1.44.1 on CPython 3.14.0 for the byte sizes below to reproduce exactly. Row counts and
  column values do not depend on the polars version; parquet bytes do.

#### The procedure

This is the same text as the `Regenerating` section of `tests/fixtures/national_size_margin/README.md`.
The two were checked mechanically, not by eye: the fence was extracted from the README with a
regex and `diff`ed against the script that was actually executed (output in §"What I ran" below).

```bash
uv run python - <<'PY'
from pathlib import Path

import polars as pl

STAGED = Path("data/staged")
DST = Path("tests/fixtures/national_size_margin")
INDUSTRY = "113310"

DST.mkdir(parents=True, exist_ok=True)

size = pl.read_parquet(STAGED / "qcew_national_size.parquet").filter(
    pl.col("industry_code") == INDUSTRY
)
months = sorted(set(size["reference_month"].to_list()))
monthly = pl.read_parquet(STAGED / "qcew_monthly.parquet").filter(
    pl.col("reference_month").is_in(months) & pl.col("area_type").is_in(["national", "state"])
)

size.sort(["reference_month", "size_class"]).write_parquet(DST / "qcew_national_size.parquet")
monthly.sort(["reference_month", "area_type", "area_fips"]).write_parquet(
    DST / "qcew_monthly.parquet"
)
for name in ("cbp_state_size", "bridge"):
    pl.read_parquet(STAGED / f"{name}.parquet").clear().write_parquet(DST / f"{name}.parquet")

for path in sorted(DST.glob("*.parquet")):
    print(f"{path.name:30s} {pl.read_parquet(path).height:>4d} rows  {path.stat().st_size:>6d} B")
PY
```

Then write the README (its text is the third deliverable of this task) and commit both with the
test file:

```bash
git add tests/fixtures/national_size_margin tests/integration/test_national_size_margin_golden.py
git commit
```

#### Result

```
bridge.parquet                    0 rows     935 B
cbp_state_size.parquet            0 rows    1866 B
qcew_monthly.parquet            401 rows   30306 B
qcew_national_size.parquet       51 rows    5669 B
```

Plus `README.md`, 10,264 B. Parquet total **38,776 B**; with the README, 49,040 B.

| File | Rows | Bytes | Contents |
|---|---|---|---|
| `qcew_national_size.parquet` | 51 | 5,669 | NAICS 113310, `2017-03 … 2024-03`, classes `1`–`6` through 2021-03 and `1`–`7` from 2022-03; 37 `observed`, 14 `suppressed` |
| `qcew_monthly.parquet` | 401 | 30,306 | 8 national all-sizes March rows + 393 published state March rows (50 FIPS × 8 Marches − 7 unpublished pairs) |
| `cbp_state_size.parquet` | 0 | 1,866 | schema only |
| `bridge.parquet` | 0 | 935 | schema only |
| `README.md` | — | 10,264 | the fixture contract |

#### Why the two `.sort(...)` calls, and why the bytes are reproducible

Writing the frames in staged order would make the fixture depend on whatever order the harmonize
step last emitted rows in, which is not a property anyone reviews. Sorting makes the output a
function of the staged *rows*.

Both sort keys are total orders on this data, so there are no ties for a sort to break arbitrarily
and the byte output is deterministic:

```
qcew_monthly  rows 401 unique (reference_month, area_type, area_fips) 401
qcew_national_size rows 51 unique (reference_month, size_class) 51
```

Measured, not argued: running the procedure a second time into a fresh directory produced files
`cmp`-identical to the first, byte for byte (output below).

The sort cannot move the golden's answer — `cells.build_target_cells` sorts by `cell_id` — and the
fourteen pairs were checked against the sorted fixture, which is what the delivered test runs on.

#### What I ran

Working copy of the procedure, differing from the delivered text on the `DST` line only:

```
$ diff /tmp/sizegolden_final/make_fixture.py /tmp/sizegolden_final/make_fixture_tmp.py
6c6
< DST = Path("tests/fixtures/national_size_margin")
---
> DST = Path("/tmp/final/fixture")

$ cd /Users/lowell/Projects/impute-suppressed-stats && uv run python /tmp/sizegolden_final/make_fixture_tmp.py
bridge.parquet                    0 rows     935 B
cbp_state_size.parquet            0 rows    1866 B
qcew_monthly.parquet            401 rows   30306 B
qcew_national_size.parquet       51 rows    5669 B

$ uv run python -c "import polars, sys; print('polars', polars.__version__); print('CPython', sys.version.split()[0])"
polars 1.44.1
CPython 3.14.0
```

The README's fence is the same program, checked mechanically:

```
$ python3 -c "<extract the ```bash fence from README.md into /tmp/sizegolden_final/readme_fence.py>"
$ diff /tmp/sizegolden_final/make_fixture.py /tmp/sizegolden_final/readme_fence.py && echo IDENTICAL
IDENTICAL
```

Determinism:

```
$ uv run python /tmp/sizegolden_final/make_fixture_regen2.py     # DST = /tmp/sizegolden_final/regen2
bridge.parquet                    0 rows     935 B
cbp_state_size.parquet            0 rows    1866 B
qcew_monthly.parquet            401 rows   30306 B
qcew_national_size.parquet       51 rows    5669 B
$ cmp /tmp/final/fixture/<each>.parquet /tmp/sizegolden_final/regen2/<each>.parquet
  bridge.parquet: byte-identical
  cbp_state_size.parquet: byte-identical
  qcew_monthly.parquet: byte-identical
  qcew_national_size.parquet: byte-identical
```

#### R8 (join row order) as it applies to this script

Three sites match the R8 grep, none of them a defect:

| Line | Site | Why it is order-invariant |
|---|---|---|
| `months = sorted(set(size["reference_month"].to_list()))` | `to_list()` | reduced through `set()` and then `sorted()`; used only as an `is_in` membership list |
| `size.sort([...])` | `.sort(...)` | this *is* the R8 remedy — an explicit total order before writing |
| `monthly.sort([...])` | `.sort(...)` | same |

No `join` appears in the script, no `== [...]` comparison, and no positional or index read.

#### Regenerating is a §17.6 golden update

This procedure re-freezes the input the fourteen hand-derived `EXPECTED_BOUNDS` pairs are held
against. Running it therefore needs the same documented reason and reviewer approval an edit to
those pairs needs. Without that rule the freeze comes undone silently: re-run it after a BLS
revision and the dict still looks untouched while the thing it is compared against has moved. The
rule is stated in three places — the module docstring, the fixture README, and here — because the
person who runs the snippet may never open the test file.

If the D1 window changes (`project.start_month` / `project.end_month`), the fixture and
`EXPECTED_BOUNDS` must be regenerated **together**, with a fresh hand derivation for any March that
joins: `cells.build_target_cells` derives its month list from the size rows it is handed, so a
widened window leaves this golden quietly checking the same eight frozen Marches. That is still a
true statement about the engine — it just stops being coterminous with the configured window.

</details>

- [ ] **Step 3: Verify the row counts and sizes**

Run:
```bash
uv run python -c "
import polars as pl, pathlib
for p in sorted(pathlib.Path('tests/fixtures/national_size_margin').glob('*.parquet')):
    print(f'{p.name}: {pl.read_parquet(p).height} rows, {p.stat().st_size} B')
"
```
Expected:
```
bridge.parquet: 0 rows, 935 B
cbp_state_size.parquet: 0 rows, 1866 B
qcew_monthly.parquet: 401 rows, 30306 B
qcew_national_size.parquet: 51 rows, 5669 B
```
Byte sizes are polars-version dependent and may differ; row counts must match exactly. If a row
count differs, the window moved — stop and re-read R4 before continuing, because regenerating this
fixture is a §17.6 golden update.

- [ ] **Step 4: Write the README**

It records row counts, `snapshot_id`s and `release_vintage`s — **not** a byte hash (R5), because
parquet bytes vary with the polars version. State that regenerating the fixture is itself a golden
update requiring §17.6 approval (R4).

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/national_size_margin/
git commit -m "test(fixtures): freeze the national-size margin input as a tracked golden fixture"
```

---

### Task 2: The frozen-input national-size golden

**Files:**
- Create: `tests/integration/test_national_size_margin_golden.py`
- Test: itself

**Interfaces:**
- Consumes: `tests/fixtures/national_size_margin/` from Task 1.
- Produces: the sole home of `EXPECTED_BOUNDS`. Task 3 deletes the live-data copy and depends on
  this existing first, so the fourteen pairs are never homeless.

This is the ruling on the item's "arguable one". `EXPECTED_BOUNDS` is an independent oracle —
derived analytically from the published margin before the engine existed — and that is the
strongest form of golden, so it is kept. The defect was never the oracle; it was that a golden
freezes its **input** and this one read live gitignored data. Freezing the input keeps every bit
of the oracle's power, and as a side effect the test stops skipping in CI.

- [ ] **Step 1: Write the file**

```python
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
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/integration/test_national_size_margin_golden.py -q`
Expected: `4 passed` in roughly 2 s. It must NOT skip — that is the point of the task. If it
skips, the fixture from Task 1 is not where the test looks.

- [ ] **Step 3: Prove the golden discriminates**

Perturb one endpoint and confirm RED:
```bash
python3 - <<'EOF'
import pathlib
p = pathlib.Path('tests/integration/test_national_size_margin_golden.py')
s = p.read_text()
p.write_text(s.replace('(2018, "5"): (2300.0, 2984.0)', '(2018, "5"): (2300.0, 2985.0)', 1))
EOF
uv run pytest tests/integration/test_national_size_margin_golden.py -q 2>&1 | tail -3
git checkout tests/integration/test_national_size_margin_golden.py
```
Expected: at least one FAILED, then the file restored. Confirm `git status --porcelain` is clean
for that path afterwards.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_national_size_margin_golden.py
git commit -m "test(integration): re-home the fourteen hand-derived bounds against frozen input"
```

---

### Task 3: Rewrite `test_d1_acceptance.py` so no count is asserted

**Files:**
- Modify (whole-file replacement): `tests/integration/test_d1_acceptance.py` (110 → 759 lines)

**Interfaces:**
- Consumes: `tests/integration/test_national_size_margin_golden.py` from Task 2 — this task DELETES
  `EXPECTED_BOUNDS` from the live-data file, so Task 2 must land first (R6).
- Produces: nothing other tasks depend on.

One whole-file replacement rather than four patches, deliberately. Four independent edits to one
110-line file is how this repo's plans have produced inconsistent fixture unpacking and duplicate
helpers before; the four breaches share the `solved` fixture and the module preamble.

Five tests become ten. That is forced by the item, not scope creep: it complains that "a
data-derived tally [is] encoded in a test's own NAME", and you cannot fix
`test_no_real_cell_is_exactly_recoverable_and_exactly_one_is_narrow` without splitting the name.
Likewise the component test bundled a correctness claim (which cells are singletons) with a
performance one (cache hits), and those need different treatments.

**What is deliberately NOT here.** The three live-data national-size tests an earlier draft carried
are collapsed to one (R7). The oracle equality belongs to Task 2's golden, where the input is
frozen; restating it here against input that moves is the weakened copy R6 forbids. The surviving
size test asserts only the label-consistency claim — a cell with two finite endpoints must not be
labelled `unbounded` or `infeasible` — because that is the one claim the golden structurally cannot
make: its fixture is generated FROM these tables, so a break in the live size-row build is
invisible to it until someone regenerates.

- [ ] **Step 1: Record the baseline**

Run: `uv run pytest tests/integration/test_d1_acceptance.py -q`
Expected: `5 passed`. Note the duration. If it SKIPS, `data/staged/` is absent and this task cannot
be verified here — stop and say so rather than committing unverified.

- [ ] **Step 2: Replace the file in full**

```python
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
```

- [ ] **Step 3: Run it**

Run: `uv run pytest tests/integration/test_d1_acceptance.py -q`
Expected: `10 passed` in roughly 13 s.

- [ ] **Step 4: Prove the rewrite did not go vacuous**

This is the acceptance criterion for the whole plan, so run it rather than assume it. Make
`classify_bound_status` return `unbounded` unconditionally — every cell then carries a label that
contradicts the finite interval printed beside it — and confirm the size test catches it.

```bash
cp src/logging_employment/constraints/bounds.py /tmp/bounds.orig
python3 - <<'EOF'
import pathlib
p = pathlib.Path('src/logging_employment/constraints/bounds.py')
s = p.read_text()
i = s.index('def classify_bound_status(')
j = s.index('"""', s.index('"""', i) + 3) + 3   # end of its docstring
p.write_text(s[:j] + '\n    return "unbounded", False, False' + s[j:])
EOF
uv run pytest tests/integration/test_d1_acceptance.py -q 2>&1 | tail -4
cp /tmp/bounds.orig src/logging_employment/constraints/bounds.py
```

Expected, verified 2026-09-06:
```
FAILED tests/integration/test_d1_acceptance.py::test_no_national_size_label_contradicts_the_interval_the_engine_gave_that_cell
1 failed, 9 passed
```

Then confirm the restore took and the file is green again:

Run: `git status --porcelain src/ && uv run pytest tests/integration/test_d1_acceptance.py -q`
Expected: no output from `git status`, then `10 passed`. Do not proceed with a dirty `src/` — this
project has a recorded incident of a mutation run leaving the working tree modified.

- [ ] **Step 5: Confirm no count survived**

Run: `grep -nE '== *[0-9]{3,}|>= *[0-9]{3,}|> *[0-9]{3,}' tests/integration/test_d1_acceptance.py`
Expected: no output. Any hit is a literal the rewrite missed.

- [ ] **Step 6: Style gates**

Run: `uv run ruff check tests/integration/test_d1_acceptance.py && uv run black --check tests/integration/test_d1_acceptance.py`
Expected: `All checks passed!` and `1 file would be left unchanged`.

- [ ] **Step 7: Commit**

```bash
git add tests/integration/test_d1_acceptance.py
git commit -m "test(integration): assert Stage 2's exit criteria on structure, not on dated counts"
```

---

### Task 4: Replace the composite-split magic string with a flag-flip oracle

**Files:**
- Modify: `tests/integration/test_d1_baselines.py` (import block; replace lines 78-83)
- Modify: `tests/unit/test_baseline_interfaces.py:28-33`

**Interfaces:**
- Consumes: `logging_employment.baselines.interfaces.{FALLBACK, OWN}` and
  `logging_employment.baselines.runner.run_baselines`.
- Produces: nothing other tasks depend on.

The breach is `"establishment_fallback" in ...` — a magic string standing in for the dated fact
that six D1 states have no observed employment month and two have no CBP row. A QCEW revision that
publishes Delaware removes the last fallback cell and reddens the test while the code behaves
perfectly.

The structural claim underneath is stated in `interfaces.py:12-20`: composition is PERMITTED but
DECLARED, and the failure it guards is silent subsetting. So the claim is not "someone fell back
today" — it is "whichever estimator-months fell back are exactly the ones the output labels as
having fallen back", which holds vacuously and correctly on a vintage where nothing composes.

The oracle is the run itself under `allow_declared_composite`. `compose` computes `gaps` once and
then either declines (flag off) or labels them `FALLBACK` (flag on), and the refusal happens BEFORE
any labelling — so "reconciles with the flag on, declines with it off" is an independent witness
that a mislabelling mutation cannot move.

- [ ] **Step 1: Add the import**

Add to the import block, before the existing `...baselines.runner` import (alphabetical):

```python
from logging_employment.baselines.interfaces import FALLBACK, OWN
```

- [ ] **Step 2: Replace lines 78-83 in full**

```python
def _status_by_estimator_month(frame: pl.DataFrame) -> dict[tuple[str, str], str]:
    """The one `reconciliation_status` each estimator-month carries.

    `run_baselines` writes decline rows for a month's whole missing set or reconciles all of it,
    never a mix; the set arithmetic below reads one status per key, so that is checked here rather
    than assumed.
    """
    grouped = frame.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("reconciliation_status").unique().alias("statuses")
    )
    out: dict[tuple[str, str], str] = {}
    for row in grouped.iter_rows(named=True):
        assert len(row["statuses"]) == 1, row
        out[(row["estimator_id"], row["reference_month"])] = row["statuses"][0]
    return out


def test_the_composite_split_is_recorded_rather_than_hidden() -> None:
    """Declared composition, not a dated count: whatever composed, the output says which cells
    came from the fallback arm.

    The oracle is the run itself under the one flag that governs composition. With
    `allow_declared_composite` false, `compose` refuses on the same `gaps` it would otherwise
    label -- and refuses BEFORE labelling anything -- so an estimator-month that reconciles with
    the flag on and declines with it off is exactly an estimator-month that composed. That set is
    derived here, never typed: on a vintage where every estimator's own arm covers every cell,
    both sides are empty and the claim still holds. The old `"establishment_fallback" in ...` was
    the dated fact that six D1 states have no observed history and two have no CBP row.
    """
    (results, _), cfg, data = _run()
    # The oracle is the difference the flag makes, so the run under test has to be the permissive
    # one. Config, not data: nothing a QCEW vintage does moves this.
    assert cfg.baselines.allow_declared_composite
    strict = cfg.model_copy(
        update={"baselines": cfg.baselines.model_copy(update={"allow_declared_composite": False})}
    )
    without_composite, _ = run_baselines(data, strict)

    ran = _status_by_estimator_month(results)
    refused = _status_by_estimator_month(without_composite)
    # Both runs cover the same estimator-months, so a key the strict run DROPS rather than
    # declines fails here instead of falling silently out of `composed`.
    assert set(ran) == set(refused)
    composed = {
        key
        for key, status in ran.items()
        if status == "anchored_and_reconciled" and refused[key] == "declined"
    }
    reconciled = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    labelled = set(
        reconciled.filter(pl.col("weight_basis") == FALLBACK)
        .select(["estimator_id", "reference_month"])
        .unique()
        .iter_rows()
    )
    assert labelled == composed
    # `none` is the declined rows' basis; a reconciled cell always names the arm it used.
    assert set(reconciled["weight_basis"].unique().to_list()) <= {OWN, FALLBACK}

    # Liveness, DERIVED from the panel rather than typed -- the anti-drift rule's own method
    # applied to the premise the magic string rested on. A state with no observed employment month
    # anywhere in the panel can carry no own weight under a share estimator, so a missing set
    # containing one must compose. Computed at run time this is AK, DE, HI, NV, ND, VT today. On a
    # vintage where every state has a history the set is empty and the demand lapses BY
    # CONSTRUCTION: that is what separates "nothing needed the fallback arm" from "the fallback
    # arm stopped working", and it is why this `assert composed` is not a dated literal.
    states = data.qcew_monthly.filter(pl.col("area_type") == "state")
    with_history = set(
        states.filter(pl.col("observation_status") == "observed")["state_fips"].unique().to_list()
    )
    without_history = set(results["state_fips"].unique().to_list()) - with_history
    if without_history:
        assert composed, (
            f"states {sorted(without_history)} have no observed month in the panel, so some "
            "estimator-month must have composed; none did"
        )
```

Do NOT convert the liveness precondition into `pytest.skip`. Under the hiding mutation a skip is
green in CI, which converts the vacuity hole into a quieter one. The `if without_history:` guard is
what makes the assert safe, and it is guarded by data, not by a policy switch.

- [ ] **Step 3: Run it**

Run: `uv run pytest tests/integration/test_d1_baselines.py -q`
Expected: `3 passed`, roughly 60 s. Measured at recon: `|composed| = 564`,
`without_history = ['02','10','15','32','38','50']` — AK, DE, HI, NV, ND, VT, derived rather than
typed.

- [ ] **Step 4: Widen the unit test so per-cell integrity is pinned somewhere**

The arms cannot be recomputed in the integration test — `CbpIntensity` supplies its own fallback
arm `national * exposure` (`intensity.py:130`), and 303 of its 303 fallback rows fail a
`establishment_fallback_in_employees` match while all 4,698 share-family rows pass it. So pin
per-cell integrity in the unit test instead, where it costs 0.06 s. Replace
`tests/unit/test_baseline_interfaces.py:28-33` with:

```python
def test_partial_own_coverage_composes_and_records_the_basis_per_cell() -> None:
    """Two gap cells, and the WHOLE mapping: labelling only the first gap must not pass."""
    anchor = Anchor("2024-03", 100.0, ("01", "02", "04", "05"), "declared_national_total")
    w = compose(
        {"01": 1.0, "02": 2.0},
        {"01": 9.0, "02": 9.0, "04": 7.0, "05": 8.0},
        anchor,
        allowed=True,
    )
    assert w.values["04"] == 7.0
    assert w.values["05"] == 8.0
    assert w.basis == {"01": OWN, "02": OWN, "04": FALLBACK, "05": FALLBACK}
```

Import `OWN`/`FALLBACK` from `logging_employment.baselines.interfaces` rather than spelling the
strings. The units guard is unaffected: own median 1.5 against fallback median 9.0 is a ratio of
6.0, well inside `MAX_SCALE_RATIO`.

- [ ] **Step 5: Run both**

Run: `uv run pytest tests/unit/test_baseline_interfaces.py tests/integration/test_d1_baselines.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_d1_baselines.py tests/unit/test_baseline_interfaces.py
git commit -m "test(baselines): witness the composite split by the flag that governs it"
```

---

### Task 5: The anchor NIT — both halves — and the dated docstring

**Files:**
- Modify: `tests/unit/test_anchor.py:171-215`
- Modify: `src/logging_employment/reconcile/anchor.py:9-12`

**Interfaces:** none consumed or produced.

Per R10 this takes both halves. The recorded finding
(`specs/findings/stage3-plan-audit.md:189-195`) asks only for the docstring, but fixing only the
prose leaves an accurate docstring describing a test that passes when `closure_audit` silently
drops non-closing months — measured: (b1) alone PASSES under the gate-skipping mutation while
(b1)+(b2) FAILS with `assert 1 == 2`. Shipping the prose fix alone would leave exactly the defect
class this plan exists to remove.

- [ ] **Step 1: Fix the docstring's false claim**

Replace the docstring at `tests/unit/test_anchor.py:172-176`:

```python
    """The audit is a diffable artifact: every month appears, passing or not.

    Asserted on structure, never on the gap being zero -- the anti-drift rule. A revision that
    moves a published establishment count must break this test for the right reason or not at all.
    """
```

with:

```python
    """The audit is a diffable artifact: every month appears, passing or not.

    `anchored` IS the gap being zero (anchor.py: `establishment_gap == 0 and residual >= 0`), and
    asserting it here is safe because the frame below is synthetic -- the gap is fixture-designed,
    not measured, and no BLS revision can move it. The anti-drift rule binds assertions on live
    data; see `tests/integration/test_d1_baselines.py` for the same claim made structurally.

    2024-03 closes and 2024-04 does not, so `anchored` is asserted as the fixture's own designed
    pattern -- the evidence that a failing month survives into the artifact rather than
    disappearing before `assert_universe_closes` sees it.
    """
```

- [ ] **Step 2: Make the fixture discriminate**

In the third row dict of the `make_monthly(...)` call (the 2024-04 national row,
`test_anchor.py:194-202`), replace `"qtrly_establishments": 6,` with:

```python
            # One establishment the state table does not carry: the gate must fail this month,
            # and employment is left alone so `residual >= 0` and the gap is the only cause.
            "qtrly_establishments": 7,
```

- [ ] **Step 3: Assert the designed pattern rather than blanket success**

Replace the three closing assertions (`test_anchor.py:212-214`) with:

```python
    assert audit.height == 2
    assert set(audit.columns) >= {"establishment_gap", "publishing_area_count", "anchored"}
    assert audit["reference_month"].to_list() == ["2024-03", "2024-04"]
    assert audit["anchored"].to_list() == [True, False]
```

- [ ] **Step 4: Run and mutation-check**

Run: `uv run pytest tests/unit/test_anchor.py -q`
Expected: all pass.

Then confirm the test now discriminates: make `closure_audit` skip non-closing months, re-run, and
confirm this test FAILS (`assert 1 == 2` on `audit.height`). Restore with `git checkout src/`.

- [ ] **Step 5: Drop the dated count from `anchor.py`**

Replace (verbatim, unique in the file):

```
come from one BLS disclosure regime, and that the national cell survives suppression while 1,227
state cells do not is that regime operating as designed, not a difference in it; and exact rather
than rounded, sampled, or modeled values. The tenth, the geography universe, is exactly what
`closure_audit` measures.
```

with:

```
come from one BLS disclosure regime, and that the national cell survives suppression while many
state cells do not is that regime operating as designed, not a difference in it; and exact rather
than rounded, sampled, or modeled values. The tenth, the geography universe, is exactly what
`closure_audit` measures.
```

Note "many", not "the suppressed state cells": the latter is circular — it would read "survives
suppression while the suppressed state cells do not [survive suppression]".

Per R11, `anchor.py:9` is the ONLY site fixed. The same `1,227` sits in `scaling.py:11`,
`simple.py:4`, `test_scaling.py:32`, `test_baselines_runner.py:146` and
`test_reconcile_properties.py:4`, where it scopes a claim rather than decorating one. Those get a
deferred item at completion, not five unbudgeted rulings here.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_anchor.py src/logging_employment/reconcile/anchor.py
git commit -m "test(anchor): make the every-month gate discriminate, and drop a dated count"
```

---

### Task 6: Convert the three clean-clone-skipping CES tests to the tracked document

**Files:**
- Modify: `tests/audit/test_ces_levels.py` (596 → 641 lines, seven hunks)

**Interfaces:**
- Consumes: `specs/findings/source-audit.md` (tracked) in place of
  `data/raw/audit/ces/summary.json` (gitignored).
- Produces: nothing other tasks depend on.

Three tests read gitignored `data/` through a `_ces_summary()` helper, so none runs on a fresh
checkout or in CI. Plan 7 Task 1 already established the pattern — read the tracked
`specs/findings/source-audit.md` — which is why its truth pin never skips.

**Measured in a fresh `git clone`, which is the only way to see this at all** (the tests pass
locally because the data is present):

| Target | BEFORE | AFTER |
|---|---|---|
| `tests/audit/test_ces_levels.py` | 39 passed, 3 skipped | **42 passed, 0 skipped** |
| `tests/audit` | 678 passed, 5 skipped | **681 passed, 2 skipped** |
| `tests` (full) | 1121 passed, 16 skipped | **1124 passed, 13 skipped** |

Do NOT write those numbers into the code. An earlier draft typed `39 passed / 3 skipped` into a
docstring in the present tense, where the conversion in the same commit would have made it false.

- [ ] **Step 1: Confirm the starting state**

Run: `uv run pytest tests/audit/test_ces_levels.py -q`
Expected locally: `42 passed` (the data is present, so nothing skips — which is the blind spot this
task fixes). `grep -c '^def test_' tests/audit/test_ces_levels.py` → `42`.

- [ ] **Step 2: Apply hunks H1–H6**

Each `OLD` block below occurs exactly once in the file; verify that before replacing.

#### 1. The patch — seven hunks, in order

Apply in the listed order. Every `OLD` block below occurs **exactly once** in
`tests/audit/test_ces_levels.py` at `49a48b5`; §3 proves that mechanically.

#### H1 — delete `import pathlib` (line 23)

Forced, not cosmetic: `pathlib` is used at exactly one site in the file (`:541`, inside the
`_ces_summary` helper H2 removes). Leaving it in fails `ruff check` with F401. `json`, `re` and
`pytest` all stay — `pytest` is still used at `:188`, `:204`, `:497`.

**OLD**
```python
import json
import pathlib
import re
```

**NEW**
```python
import json
import re
```

#### H2 — replace `_ces_summary()` with the tracked-document helper (lines 540–544)

The gitignored-summary reader is **deleted outright, not left behind as a fallback** (R6's
principle, applied here by analogy). The replacement is the helper that already exists lower in
the file at `:576`, moved up to where its callers now are and given an honest docstring: the old
one pointed at `_ces_summary`, "which is exactly what the `_ces_summary` helper above does" —
a function this commit deletes. H6 removes the copy left behind at the old position.

The move itself is cosmetic — Python resolves module-level names at call time, so the helper
worked below its callers and would work below them still.

**Do not stop after H2: no gate catches the half-applied state, and I measured that rather than
assuming it.** With H1–H5 applied and H6 skipped, the file carries *two* definitions of
`_ces_findings_from_the_shipped_document` with identical bodies; the later one silently wins, and
the stale docstring naming the now-deleted `_ces_summary` stays live — the exact aged-prose defect
class this commit exists to remove. `ruff` does not flag it (F811 is "redefinition of *unused*
name", and the first definition **is** used by the three tests sitting between the two defs, so
even `--select F811` explicitly is silent):

```
$ python3 -c "... apply ah.HUNKS[:5] only ..."   # -> /tmp/final/work/half_applied.py
wrote half_applied.py (H1-H5 only, H6 and H7 NOT applied)
$ uv run ruff check /tmp/final/work/half_applied.py
All checks passed!
$ cd /Users/lowell/Projects/impute-suppressed-stats && uv run ruff check --select F811 /tmp/final/work/half_applied.py
All checks passed!
$ cd /tmp/final/work/clone && uv run black --check tests/audit/test_ces_levels.py   # half-applied file copied in
All done! ✨ 🍰 ✨
1 file would be left unchanged.
$ cd /tmp/final/work/clone && env -u PYTHONPATH HOME=... .venv/bin/python -m pytest \
    tests/audit/test_ces_levels.py -q --no-header -p no:cacheprovider
..........................................                               [100%]
42 passed in 0.13s
```

Green ruff, green black, 42 passed, and a duplicate definition carrying a docstring about a
function that no longer exists. **H6 is not optional and nothing downstream will remind you.**

**OLD**
```python
def _ces_summary() -> dict:
    path = pathlib.Path(m.__file__).resolve().parents[2] / "data/raw/audit/ces/summary.json"
    if not path.exists():
        pytest.skip(f"{path} not present; run ces_levels.py first")
    return json.loads(path.read_text(encoding="utf-8"))
```

**NEW**
```python
def _ces_findings_from_the_shipped_document() -> dict:
    """The tracked document, not data/raw/audit/ces/summary.json: data/ is gitignored in its
    entirety, so nothing under it exists in a fresh clone and a truth pin written against the
    summary skips silently there. Readable because `assemble_finding.fence` renders each
    source's `findings` object whole and unmodified rather than summarising it. That the fence
    still equals the summary it was rendered from is kept true by re-running the assembler
    after an audit, not by a gate, so this reads the tracked copy as the shipped artifact it is
    in its own right."""
    document = (_common.FINDINGS_DIR / "source-audit.md").read_text(encoding="utf-8")
    (ces,) = [
        b for b in re.split(r"^### `", document, flags=re.MULTILINE)[1:] if b.startswith("ces`")
    ]
    return json.loads(ces.split("**findings**:\n\n```json\n", 1)[1].split("\n```", 1)[0])
```

#### H3 — test 1 of 3, `:547`, source swap only

**OLD**
```python
    trimming to states, so the names have to say sm.state."""
    findings = _ces_summary()["findings"]
    for new, old in RENAMES:
```

**NEW**
```python
    trimming to states, so the names have to say sm.state."""
    findings = _ces_findings_from_the_shipped_document()
    for new, old in RENAMES:
```

#### H4 — test 2 of 3, `:557`, source swap + T1

T1 holds the half of "spans **more than** states_dc" that `assert non_state` does not: without
it, a map gutted of every states_dc code still satisfies the pin, because the four non-state
codes survive. Killed by M5, and M5 passes `assert non_state` first — proven, not assumed.

**OLD**
```python
    findings = _ces_summary()["findings"]
    coded = set(findings["publication_level_by_sm_state_code"])
    non_state = coded - set(_common.STATES_DC_FIPS)
    assert non_state, "map is states_dc-only; 'by_sm_state_code' no longer describes it"
    # The sibling finding that resolves those codes must agree on exactly which they are.
```

**NEW**
```python
    findings = _ces_findings_from_the_shipped_document()
    coded = set(findings["publication_level_by_sm_state_code"])
    non_state = coded - set(_common.STATES_DC_FIPS)
    assert non_state, "map is states_dc-only; 'by_sm_state_code' no longer describes it"
    # "spans MORE THAN states_dc" has two halves, and the assertion above only holds the second.
    # Without this line a map gutted of every states_dc code still satisfies it.
    assert set(_common.STATES_DC_FIPS) <= coded, "map no longer covers the states_dc universe"
    # The sibling finding that resolves those codes must agree on exactly which they are.
```

#### H5 — test 3 of 3, `:569`, source swap + docstring + T2 + T3

The shipped body is a bare loop with no docstring. Converting the source alone would leave a
loop that is trivially true on a flattened map, so T2 and T3 come with it. `assert near_miss`
does **not** — see §6.

**OLD**
```python
def test_near_miss_rows_are_keyed_by_codes_the_publication_map_left_at_none():
    findings = _ces_summary()["findings"]
    level = findings["publication_level_by_sm_state_code"]
    for row in findings["near_miss_sm_state_codes"]:
        assert level[row["state_code"]] == "none"
```

**NEW**
```python
def test_near_miss_rows_are_keyed_by_codes_the_publication_map_left_at_none():
    """Every row the near-miss list carries must be a code the publication map left at "none" --
    that is what makes it a near miss. Of the two assertions ahead of the loop only the first is
    a vacuity guard, turning a document on which the loop is trivially true back into a failure;
    the second catches a value set `level_of` could not have produced, on a document where the
    loop runs and passes on merit. The loop is also vacuous on an EMPTY near-miss list, and that
    is deliberately not asserted against: an empty list is a legitimate producer result
    (`near_miss_sm_state_codes([], ...) == []` is pinned above), so `assert near_miss` would be
    today's measurement written as an invariant. A list emptied without the document being
    regenerated around it is caught instead by
    `test_the_shipped_note_is_recomputable_from_the_findings_it_sits_beside`, which recomposes
    the shipped sentence from this same list and so knows which branch the producer took."""
    findings = _ces_findings_from_the_shipped_document()
    level = findings["publication_level_by_sm_state_code"]
    near_miss = findings["near_miss_sm_state_codes"]
    # A map flattened to all-"none" destroys the audit's core output and makes the loop below
    # trivially true for every row.
    assert set(level.values()) != {"none"}, "every code is 'none'; the map no longer discriminates"
    # And the map's values must be levels this run could actually have assigned -- recomputed
    # from the codes this run recorded, with `level_of` called live rather than read out of the
    # shipped `level` field, so a `level_of` regression that never reached the document is
    # caught too. A producer invariant, not a coincidence of today's data: `level_by_state`
    # minimises `level_of` over series filtered to the same candidate set that becomes
    # `logging_industry_codes`, and defaults to "none". `<=` and not `==` because a run in which
    # no jurisdiction publishes at some level must not fail. No literal anywhere -- a BLS
    # revision that adds a finer code moves the vocabulary and this moves with it, naming the
    # new level in the failure message.
    assignable = {"none"} | {
        m.level_of(row["industry_code"]) for row in findings["logging_industry_codes"]
    }
    assert (
        set(level.values()) <= assignable
    ), f"map carries levels level_of cannot produce: {set(level.values()) - assignable}"
    for row in near_miss:
        assert level[row["state_code"]] == "none"
```

`assert (...) , f"..."` rather than the more readable `assert x <= y, (\n    f"..."\n)`: that is
what this repo's `black` produces for a one-line message. The other form fails `black --check`.

#### H6 — delete the now-duplicate helper at its old position (lines 576–586)

H2 put the helper above its callers. This deletes the copy left at `:576`, whose docstring named
`_ces_summary`. The anchor stays unique after H2 because the two docstrings differ.
**Delete the trailing blank lines too** — the two blank lines between this helper and the test
that follows it belong to this hunk.

**OLD** (including the two trailing blank lines)
```python
def _ces_findings_from_the_shipped_document() -> dict:
    """The tracked document, not data/raw/audit/ces/summary.json: data/ is gitignored in its
    entirety, so a truth pin written against the summary is a silent skip in a clean clone --
    which is exactly what the `_ces_summary` helper above does."""
    document = (_common.FINDINGS_DIR / "source-audit.md").read_text(encoding="utf-8")
    (ces,) = [
        b for b in re.split(r"^### `", document, flags=re.MULTILINE)[1:] if b.startswith("ces`")
    ]
    return json.loads(ces.split("**findings**:\n\n```json\n", 1)[1].split("\n```", 1)[0])


```

**NEW**

(nothing — the block is removed entirely)


- [ ] **Step 3: Apply H7 (corrected)**

H7 differs from the version in the source patch document: that one false-failed on a legitimate
future run. `broader_code_note` has an explicit empty-`excluded` branch returning a different
sentence, and an empty `excluded` FORCES an empty `near_miss`
(`ces_levels.py: excluded_series_rows = ... if excluded_codes else []`), so comparing against `[]`
compares that branch with itself and reddens on good data. Measured: `1 failed, 41 passed` on a
legitimately-empty document. That is the same defect class this plan exists to remove, so it is
fixed here rather than shipped.

**OLD**
```python
        findings["excluded_broader_codes"], findings["near_miss_sm_state_codes"]
    )
    assert recomputed in findings["notes"]
```

**NEW**
```python
        findings["excluded_broader_codes"], findings["near_miss_sm_state_codes"]
    )
    assert recomputed in findings["notes"]
    # `notes` is one string, so the assertion above is substring containment: any PREFIX of the
    # shipped sentence satisfies it, and a constant implementation returns the shipped sentence
    # whatever it is handed. So a note recomposed from an excluded list this run demonstrably did
    # NOT have must not be in `notes` either -- which is what plain containment cannot catch.
    # The differing list is the shipped one EXTENDED, never `[]`: broader_code_note returns a
    # wholly different sentence when `excluded` is empty (its first branch), so `[]` compares the
    # wrong branch -- and on a legitimate run that excludes nothing, which forces near_miss to []
    # as well, it compares that branch against itself and fails on good data. The added code is
    # non-numeric, so it can never be an SAE industry code and can never already be rendered in
    # the shipped sentence -- no assumption about which codes this particular run excluded.
    fabricated = findings["excluded_broader_codes"] + [
        {"industry_code": "no-such-code", "industry_name": "not an SAE industry"}
    ]
    fabricated_note = m.broader_code_note(fabricated, findings["near_miss_sm_state_codes"])
    assert fabricated_note not in findings["notes"]
```

- [ ] **Step 4: Run, and check the line count**

Run: `uv run pytest tests/audit/test_ces_levels.py -q && wc -l tests/audit/test_ces_levels.py`
Expected: `42 passed` and `641` lines.

- [ ] **Step 5: Verify in a clean clone — the only check that proves the task**

```bash
TMP=$(mktemp -d) && git clone -q . "$TMP/clone" \
  && (cd "$TMP/clone" && uv run pytest tests/audit/test_ces_levels.py -q 2>&1 | tail -3) \
  && rm -rf "$TMP"
```
Expected: `42 passed` with NO skips. Before this task the same command gives
`39 passed, 3 skipped`. Remove the temp directory afterwards.

- [ ] **Step 6: Style gates and commit**

```bash
uv run ruff check tests/audit/test_ces_levels.py && uv run black --check tests/audit/test_ces_levels.py
git add tests/audit/test_ces_levels.py
git commit -m "test(audit): read the CES artifact pins from the tracked findings document"
```

---

### Task 7: Act on the sibling inventory

**Files:**
- Modify: `tests/audit/test_qcew_codes.py:399` (if a tracked equivalent exists)

**Interfaces:** none.

The item says to check the siblings before fixing only `test_ces_levels.py`. The sweep across all
of `tests/audit/` was measured in a clean clone, not grepped, and found exactly two remaining
skips after Task 6 — one of the same family and one that is not:

| Site | Reads | Same family? |
|---|---|---|
| `tests/audit/test_qcew_codes.py:399` | `data/raw/audit/qcew_codes/summary.json` (gitignored) | **Yes** — same fix as Task 6 if `specs/findings/source-audit.md` carries the same values |
| `tests/audit/test_qcew_codes.py:378` | `~/.claude/skills/bls-data-context/references/qcew.md` | **No** — reads a personal skill file outside the repo entirely. Different problem, different fix. |

- [ ] **Step 1: Establish whether a tracked equivalent exists**

Run: `grep -n "qcew_codes\|naics_vintage_by_year" specs/findings/source-audit.md | head -20`

If the values `test_qcew_codes.py:399` asserts are present in the tracked document, convert it
using exactly the pattern Task 6 established, then re-run the clean-clone check and confirm
`tests/audit` reaches `682 passed, 1 skipped`.

If they are NOT present, STOP. Do not invent a tracked source. Record it as a deferred item
instead, with what you searched and why it did not resolve — a negative result without its scope
overclaims, and inventing an artifact to satisfy a test is worse than the skip.

- [ ] **Step 2: Record `:378` as deferred either way**

It reads a file under `~/.claude/skills/`, which no clone will ever have. That is not a
gitignored-data problem and its fix is a different decision (vendor the quotation, or drop the
test). Record it; do not fix it here.

- [ ] **Step 3: Commit whatever landed**

```bash
git add -A tests/audit/
git commit -m "test(audit): extend the tracked-source conversion to the qcew_codes sibling"
```

---

## Self-Review

**Spec coverage.** There is no spec — the requirements are the two `/deferred` items, and every
clause maps to a task:

| Requirement clause | Task |
|---|---|
| `suppressed.height == 1227` / `joined.height == 1227` (`:67`, `:69`) | 3 |
| tally in the test's own NAME plus the narrow cell's identity (`:84`, `:91-93`) | 3 |
| `>= 4716`, `== 8`, `> 4000` (`:100-102`) | 3 |
| `assert produced == EXPECTED_BOUNDS` (`:81`) — "the arguable one" | 1 + 2 (frozen input), 3 (removal) |
| `test_d1_baselines.py`'s one breach of the same family | 4 |
| `test_anchor.py:174` ships the plan-level NIT verbatim | 5 |
| `anchor.py:9` types "1,227" where it is load-bearing on nothing | 5 |
| `test_ces_levels.py`'s three clean-clone skips (`:534`, `:544`, `:556`) | 6 |
| "Check the sibling audit test files for the same pattern" | 7 |

**Placeholder scan.** No "TBD", no "similar to Task N", no "add appropriate handling". Every code
step carries the code. Task 7 Step 1 is conditional rather than placeholder: it names both branches
and what to do in each.

**Type consistency.** `test_d1_acceptance.py` is one whole-file replacement, so its three fixtures
(`config` → `Config`, `harmonized` → `HarmonizedData`, `solved` → `(built, result, flags)`) and its
helpers are defined once. The `solved` unpacking convention — positional, `_` for unread slots — is
documented in the fixture's own docstring because ruff's RUF059 forbids naming an unused one.
`FALLBACK`/`OWN` are imported from `baselines.interfaces` in both Task 4 files rather than spelled
as strings.

**Known coverage change, stated rather than buried.** Task 6 DELETES one assertion
(`assert near_miss, ...`). It was itself an anti-drift breach: a BLS revision giving Delaware, DC,
Hawaii and the Virgin Islands a real 113 series empties the list and regenerates the note around
it, and the guard would have gone red on a correct document with a message that misdirects the
debugger. Assertion coverage in that file goes from 13 rows to 12; the compensating control is
PIN4, which reddens when `near_miss` is emptied while the note goes stale.

---

## Execution Handoff

Plan complete and saved to `specs/plans/8-test-assertion-integrity.md`.

**Recommended: `/clear` (or open a new session) and execute against the saved plan** — a fresh
session drops this planning conversation and lets execution run on the standard model default.
Two execution options, either session:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks.
2. **Inline Execution** — tasks executed in plan order in one session (`executing-plans`).

Tasks 1 → 2 → 3 are strictly ordered (the fixture must exist before the golden, and the golden must
exist before the live-data copy of `EXPECTED_BOUNDS` is deleted). Tasks 4, 5, 6 are independent of
those and of each other. Task 7 follows Task 6.

**Tasks 1, 2, 3 and 6 cannot be verified from a clean clone** — they need `data/staged/` and
`data/raw/audit/ces/`. Task 6's Step 5 additionally needs a clean clone to prove the skip is gone.
Execute where the data lives.
