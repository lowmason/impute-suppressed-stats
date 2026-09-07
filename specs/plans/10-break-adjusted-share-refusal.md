# Break-Adjusted Share Refusal Implementation Plan

**Status: COMPLETE (2026-09-07)** — executed via executing-plans; nothing deferred

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `BreakAdjustedShare` return `None` — taking the declared §10.2 establishment fallback — whenever the cut it selects leaves fewer than two points in the recent segment, so §10.3's variant 5 stops emitting variant 1's and variant 3's numbers under its own name.

**Architecture:** One four-line change to `BreakAdjustedShare._reduce` in `src/logging_employment/baselines/historical.py`: drop the `len(shares) < 4` short-circuit, add a `len(shares) < 2` guard so `max(steps)` is legal, and add a `len(segment) < 2` check after the cut is selected. Refusal reuses the existing `None` path that `_ShareBaseline.weights` already honours, so no new code path, config key, or decline reason is introduced. The class docstring is rewritten in the same commit because R-BREAK-4 exists precisely so the declaration cannot outlive the behaviour.

**Tech Stack:** Python 3.14, Polars, pytest, ruff/black (line length 100), `uv` for execution.

**Spec:** `specs/break-adjusted-share-refusal.md`. Read it before Task 2 — the requirement labels (R-BREAK-1 … R-BREAK-5) and test labels (T-1 … T-8) below refer to its sections.

## Global Constraints

- **The tie rule MUST NOT change (R-BREAK-5).** `cut = steps.index(max(steps)) + 1` takes the **earliest** tied step. It is *declared* by this plan, never altered. Changing it to the latest tied step would move cells for a reason the spec has not argued.
- **`tests/fixtures/baselines/baseline_results_golden.parquet` MUST be byte-identical after this change.** Verified before planning: the fixture yields exactly three cells with a history, all length 6 with the cut at position 3, leaving a three-point segment — every one is kept. `git status --short tests/fixtures/baselines/` MUST print nothing at every commit. **Never regenerate the golden.** §17.6 requires a documented reason and reviewer approval for a re-pin, and this change is not one.
- **No new config key, no new decline reason, no new code path (R-BREAK-3).** The refused cell is *composed*, not declined; `weight_basis` records the existing `establishment_fallback`.
- **The docstring MUST NOT restate D1 measurement counts (R-BREAK-4).** Counts are measurements a revision moves; this package reports the own/fallback split from `baseline_manifest.json`'s `weight_basis_counts`, not from prose.
- **`grep -n "below four" src/logging_employment/baselines/historical.py` MUST return nothing** when the plan is done.
- **Do not edit `specs/plans/completed/*`, `specs/findings/*`, or `specs/logging-employment-spec.md`.** They contain the phrase "below four" as historical record. §10.3 is deliberately **not** amended (spec §6).
- **Change no other §10.3 variant.** Four variants coinciding on a length-1 history is a property of one-element lists, not a defect (spec §2). `LastObservedShare`, `SameMonthPreviousYearShare`, `RollingMedianShare` and `ExponentiallyWeightedShare` are untouched by this plan.
- **Change nothing in Stage 4.** Stage 4 consumes the corrected estimator; its scoreboard is not planned here.
- **Five distinct numbers is NOT the requirement.** The requirement is that each variant does what it says *or refuses*. Coincidental agreement is permitted; structural impersonation is not. Do not add a distinctness assertion beyond the one `test_the_five_variants_compute_five_different_numbers_on_one_history` already makes on its own fixture.
- **Line length 100.** Run `uv run ruff check` and `uv run ruff format --check` **before** `pytest` on every task; a lint failure after a green test run wastes a cycle.
- **Execute in the main checkout, not a worktree.** `data/` is gitignored and large; a worktree turns data-reading tests into silent skips.

> Deviation: honoured, and executed on branch `break-adjusted-share-refusal` within that checkout
> rather than on `main` — the repo's convention, cf. plan 9's `10d9295`. A branch is not a
> worktree, so `data/` stays visible and no data-reading test silently skips.

**Commands used throughout:**

```bash
uv run ruff check src/ tests/
```

```bash
uv run pytest tests/unit/test_baselines_historical.py -q --no-header
```

The full suite takes ~3 minutes:

```bash
uv run pytest tests/ -q --no-header
```

---

## Background the executor needs

**What the code does today.** `_ShareBaseline.weights` loops over the anchor's missing cells, builds each cell's share history, and calls `self._reduce(shares, anchor, history)`. If `_reduce` returns `None` (or a non-positive number) the cell is simply left out of the `own` dict, and `compose_with_declared_fallback` covers it with the §10.2 establishment arm, recording `weight_basis = establishment_fallback`. `SameMonthPreviousYearShare` already uses that path. `BreakAdjustedShare` is the only variant that never refuses.

**Two traps this plan is built around. Both were confirmed by running the change before the plan was written.**

1. **The shared `_history` fixture has no real break, and float noise decides its cut.** It builds state 01's employment as `40 + i` over a national total of 100, so the in-window shares are `[0.40, 0.41, 0.42]` — nominally equal steps. In IEEE 754 the two steps are `0.009999999999999953` and `0.010000000000000009`, so the argmax lands on the *last* step, the segment is one point, and variant 5 refuses. `test_every_variant_produces_positive_weights_for_a_state_with_history[BreakAdjustedShare]` then fails. **The spec's §5 "Replaced" list does not mention this test — it names only two, and there are three.** Task 1 fixes the fixture first, for that reason.

2. **A refusal is not a local change: it reaches R-COMP-8.** The moment a cell falls back, `compose_with_declared_fallback` builds a fallback arm, which resolves the `disclosed_qcew` intensity, which checks that the anchor's residual matches the one the context's partition implies. Any test that hand-types `Anchor("2024-03", 50.0, ...)` **and** triggers a fallback raises `ConceptViolationError: ... implies a residual of 200 but the anchor carries 50`. T-7 therefore MUST build its anchor with `national_residual(...)`, exactly as `test_a_state_with_no_observed_history_takes_the_declared_fallback` already does.

**The complete set of tests this change breaks, measured on the current tree** (`uv run pytest tests/ -q` with `_reduce` changed and nothing else — 3 failed, 1172 passed):

| Test | Task that resolves it | How |
|---|---|---|
| `test_every_variant_produces_positive_weights_for_a_state_with_history[BreakAdjustedShare]` | Task 1 | fixture given a genuine interior break |
| `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median` | Task 2 | **deleted** — its premise is the defect |
| `test_the_break_adjusted_docstring_scopes_its_own_claim` | Task 2 | **rewritten** to pin the new claim |

Nothing else in the suite moves, and the golden integration test passes untouched.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `src/logging_employment/baselines/historical.py` | Modify `BreakAdjustedShare` (~line 209-227) | The reduction rule and its declaration. The only source file this plan touches. |
| `tests/unit/test_baselines_historical.py` | Modify `_history` (~line 39); delete one test, rewrite one, add a helper and seven (~line 490-520) | Unit coverage for the rule and the composition path. |
| `tests/fixtures/baselines/baseline_results_golden.parquet` | **Unchanged — must stay byte-identical** | The §17.6 golden. |

---

## Task 1: Give the shared history fixture a genuine break

`_history` is consumed by exactly two tests (`test_every_variant_produces_positive_weights_for_a_state_with_history` at line 86 and `test_a_state_with_no_observed_history_takes_the_declared_fallback` at line 108). Its state-01 series is an arithmetic progression, so once variant 5 starts reading the cut, float representation error picks the argmax. This task lands **before** the behaviour change so the fixture is honest under both the old rule and the new one — it is green either way, which is what makes it separately reviewable.

The anchor month's value **must stay 43**: the sibling test derives its expected fallback from it (`6.0 * (43 / 4)`), so moving it silently breaks a derived pin.

**Files:**
- Modify: `tests/unit/test_baselines_historical.py:39-72` (`_history`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `_history(make_monthly) -> pl.DataFrame` — unchanged signature. State 01 is observed at `2023-01`, `2023-02`, `2023-03`, `2024-03` with employment `10, 40, 41, 43` over a national total of 100; state 02 is suppressed in all four months with 6 establishments.

- [x] **Step 1: Read the current fixture**

Run: `sed -n '39,73p' tests/unit/test_baselines_historical.py`

Expected: a `for i, month in enumerate([...])` loop whose state-01 row carries `"employment_value": 40 + i,`.

- [x] **Step 2: Replace the loop header so employment is an explicit list**

In `tests/unit/test_baselines_historical.py`, change the opening of `_history` from:

```python
def _history(make_monthly) -> pl.DataFrame:
    rows = []
    for i, month in enumerate(["2023-01", "2023-02", "2023-03", "2024-03"]):
```

to:

```python
def _history(make_monthly) -> pl.DataFrame:
    """State 01 observed in three in-window months plus the anchor month, state 02 suppressed.

    THE HISTORY CARRIES A REAL LEVEL BREAK, AND THAT IS LOAD-BEARING. An arithmetic series --
    this fixture was `40 + i` -- has nominally equal steps, so `BreakAdjustedShare`'s
    largest-step argmax is decided by float representation error rather than by the data: on
    shares 0.40, 0.41, 0.42 the two steps are 0.009999999999999953 and 0.010000000000000009, the
    cut lands last, and the segment is one point. Under R-BREAK-1 that variant then refuses and
    this fixture's own test fails for a floating-point reason wearing a coverage reason's
    clothes. The 10 -> 40 jump gives the cut somewhere real to land.

    THE ANCHOR MONTH STAYS AT 43. `test_a_state_with_no_observed_history_takes_the_declared_
    fallback` derives its expected weight from this fixture as `6.0 * (43 / 4)`, so 2024-03's
    employment is not free to move with the rest of the series.
    """
    rows = []
    for month, employment in zip(
        ["2023-01", "2023-02", "2023-03", "2024-03"], [10, 40, 41, 43], strict=True
    ):
```

- [x] **Step 3: Point the state-01 row at the new variable**

In the same function, change:

```python
                "employment_value": 40 + i,
```

to:

```python
                "employment_value": employment,
```

- [x] **Step 4: Lint, then run the file's tests against the UNCHANGED source**

```bash
uv run ruff check src/ tests/ && uv run pytest tests/unit/test_baselines_historical.py -q --no-header
```

Expected: PASS, 18 passed. The old `len(shares) < 4` rule reduces `[0.10, 0.40, 0.41]` to the plain median 0.40, which is positive, so every variant still takes `OWN` — the fixture change is behaviour-preserving under the current source. If `test_a_state_with_no_observed_history_takes_the_declared_fallback` fails, the anchor month's 43 was moved; put it back.

- [x] **Step 5: Confirm the golden fixture is untouched**

```bash
git status --short tests/fixtures/baselines/
```

Expected: no output.

- [x] **Step 7: Commit**

```bash
git add tests/unit/test_baselines_historical.py
git commit -m "test(baselines): give the shared share history a real level break

An arithmetic series has nominally equal steps, so BreakAdjustedShare's
largest-step argmax is decided by float representation error. Lands ahead
of the refusal rule so the fixture is honest under both."
```

---

## Task 2: `BreakAdjustedShare` refuses a degenerate cut

The plan's centre. R-BREAK-1, R-BREAK-2, R-BREAK-4 and R-BREAK-5 all land here, in one commit, because a docstring that outlives its behaviour is the defect R-BREAK-4 was written to prevent.

**Files:**
- Test: `tests/unit/test_baselines_historical.py` — delete one test, add a helper and six, rewrite one
- Modify: `src/logging_employment/baselines/historical.py:209-227` (`BreakAdjustedShare`)

**Interfaces:**
- Consumes: `_history` from Task 1 (unchanged signature); `BreakAdjustedShare` from `logging_employment.baselines.historical`.
- Produces: `BreakAdjustedShare._reduce(self, shares: list[float], anchor, history) -> float | None` — returns `None` when `len(shares) < 2` or when the selected cut leaves fewer than two points, and `statistics.median(segment)` otherwise. Task 3 drives this through `BreakAdjustedShare().weights(context, anchor)`.
- Produces: `_reduce_shares(shares: list[float]) -> float | None`, a module-level test helper calling `_reduce` with `None` for both the anchor and the history. Task 3 does not use it — T-7 drives the full `weights` path instead.

- [x] **Step 1: Add the `statistics` import**

At the top of `tests/unit/test_baselines_historical.py`, change:

```python
from __future__ import annotations

import polars as pl
import pytest
```

to:

```python
from __future__ import annotations

import statistics

import polars as pl
import pytest
```

> Task 3 needs a second import (`Weights`). It is added there, not here: ruff's `F401` fires on an import with no use yet, which would fail this task's own lint gate at Step 7.

- [x] **Step 2: Delete the test whose premise is the defect**

Delete `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median` in its entirety — the `def` line at roughly line 490 through its final `assert`, including the docstring. Spec §5 requires deletion, not adjustment: it asserts `broken == median` and `broken == pytest.approx(11.0)`, and R-BREAK-1 makes both false. Adjusting it would also raise `ConceptViolationError`, because its hand-typed `Anchor("2024-03", 50.0, ...)` disagrees with the residual its partition implies once the refused cell needs a fallback arm.

- [x] **Step 3: Add the reduction helper and T-1 … T-6**

Insert this immediately after `_breaking_history`'s consumer `test_the_five_variants_compute_five_different_numbers_on_one_history`, where the deleted test used to be:

```python
def _reduce_shares(shares: list[float]) -> float | None:
    """`BreakAdjustedShare._reduce` on a bare share list.

    The rule is a pure reduction over a list of floats, so it is driven directly rather than
    through a fixture. The anchor and history arguments are `None` rather than stubs: this variant
    selects by POSITION and reads neither, so `None` makes that structural -- a future revision
    that starts reading either raises here instead of quietly agreeing.

    Integer-valued floats throughout, for the reason `_share_rows` gives: on tenths the
    largest-step argmax is decided by float representation error rather than by the data.

> Deviation: that final docstring paragraph shipped narrowed. "Integer-valued floats throughout"
> is falsified by T-1…T-4 directly below it, which use 0.02, 0.10, 0.50, 0.52, 0.11 and 0.90 — a
> docstring contradicted by the code under it is exactly the R-BREAK-4 defect, and shipping one
> inside the fix for R-BREAK-4 would be self-defeating. The shipped text states the property that
> does hold across all six cases: where a case admits more than one step, its largest is kept well
> clear of its second largest. Same reason, true of the cases it governs.
    """
    return BreakAdjustedShare()._reduce(shares, None, None)


def test_a_one_point_history_admits_no_cut_and_is_refused() -> None:
    """T-1. A one-point history has no steps, so `max(steps)` would raise on an empty sequence --
    the guard is what makes the reduction total, not a threshold on the history length."""
    assert _reduce_shares([0.02]) is None


def test_a_two_point_history_leaves_a_one_point_segment_and_is_refused() -> None:
    """T-2. The only cut a two-point history admits puts one point in the recent segment, and the
    median of one point is that point -- which is `LastObservedShare`, not this variant."""
    assert _reduce_shares([0.02, 0.05]) is None


def test_a_short_history_cut_in_the_middle_keeps_its_two_point_segment() -> None:
    """T-3. The keep half of R-BREAK-2: three points is not too few when the cut falls inside.

    The contrast is DERIVED rather than asserted in prose -- `statistics.median` is called on the
    same list, so if this variant ever collapsed back to the plain median the second assert would
    equal the first instead of differing from it."""
    shares = [0.10, 0.50, 0.52]
    assert _reduce_shares(shares) == pytest.approx(0.51)
    assert statistics.median(shares) == pytest.approx(0.50)


def test_a_short_history_cut_at_the_end_is_refused() -> None:
    """T-4. The refuse half of R-BREAK-2, on a history the same length as T-3's: length decides
    nothing, the cut decides. These are the numbers the deleted `<4` test used to reduce to 0.11,
    so the second assert names the value this variant no longer emits."""
    shares = [0.10, 0.11, 0.90]
    assert _reduce_shares(shares) is None
    assert statistics.median(shares) == pytest.approx(0.11)


def test_a_long_history_whose_largest_step_is_its_last_is_refused() -> None:
    """T-5. The case no length threshold can catch and no previous test reached: twelve points,
    far past any plausible minimum, and still no evidence of a segment. Under the `<4` rule this
    returned the median of the one-point segment -- the last observation, i.e. variant 1."""
    shares = [10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 11.0, 90.0]
    assert len(shares) == 12
    assert _reduce_shares(shares) is None


def test_a_long_history_with_an_interior_break_follows_the_recent_segment() -> None:
    """T-6. The variant still does its job where the evidence supports it.

    The same twelve values `_breaking_history` uses, so the unit rule and the all-variants fixture
    cannot drift apart. The inequality below is a property of THIS fixture, not an invariant:
    a recent segment may agree with the whole-history median by coincidence, which §2 permits."""
    shares = [20.0, 10.0, 11.0, 9.0, 10.0, 11.0, 9.0, 10.0, 30.0, 31.0, 29.0, 34.0]
    # The largest single step is 10 -> 30, so the segment is [30, 31, 29, 34], median (30 + 31) / 2.
    assert _reduce_shares(shares) == pytest.approx(30.5)
    assert statistics.median(shares) == pytest.approx(11.0)
```

- [x] **Step 4: Rewrite the docstring-pinning test**

Replace `test_the_break_adjusted_docstring_scopes_its_own_claim` (the last test in the file) with:

```python
def test_the_break_adjusted_docstring_declares_its_refusal() -> None:
    """The sentence half of the pair: the seven tests above hold that the claim is TRUE, this holds
    that the claim is still MADE. It asserts the sentences EXIST, not that they are accurate --
    T-3, T-4 and T-5 are what make them accurate, and this test would pass over a false docstring.

    Whitespace-normalized so that re-wrapping the docstring does not redden this: the claim is the
    sentence, not the line breaks."""
    doc = " ".join(BreakAdjustedShare.__doc__.split())
    assert "A cut leaving fewer than two points in the recent segment is not evidence" in doc
    assert "THE THRESHOLD IS A PROPERTY OF THE SELECTED CUT, NOT OF THE HISTORY LENGTH" in doc
    assert "THE EARLIEST TIED STEP WINS" in doc
    # R-BREAK-4: the replaced claim named a threshold of four, and both its halves are now false.
    assert "below four" not in doc
```

- [x] **Step 5: Run the tests to verify they fail**

```bash
uv run pytest tests/unit/test_baselines_historical.py -q --no-header
```

Expected: **FAIL, 6 failed, 17 passed.** Measured on the current tree, the six are:

| Test | Old code returns | Why it fails |
|---|---|---|
| T-1 `..._one_point_history...` | `0.02` | `len(shares) < 4` short-circuits to `statistics.median([0.02])` — an assertion failure, not a `ValueError` |
| T-2 `..._two_point_history...` | `0.035` | same short-circuit, `median([0.02, 0.05])` |
| T-3 `..._cut_in_the_middle...` | `0.50` | the plain median of all three, not `0.51` |
| T-4 `..._cut_at_the_end...` | `0.11` | the plain median, where R-BREAK-1 wants `None` |
| T-5 `..._largest_step_is_its_last...` | `90.0` | twelve shares clear the `< 4` gate, so the cut runs and `median([90.0])` is the last observation |
| `..._docstring_declares_its_refusal` | — | fails on the first `assert ... in doc` |

**T-6 PASSES at this step, and that is correct.** Twelve shares with an interior break clear the old `< 4` gate and take the same cut, so the old and new rules agree on it. T-6 is a REGRESSION GUARD — it pins that this change does not move the case where the evidence supports the variant. Do not "fix" it.

If any of the six PASSES here, the implementation was written first — revert it and re-run.

- [x] **Step 6: Replace the docstring and the reduction**

In `src/logging_employment/baselines/historical.py`, replace the whole `BreakAdjustedShare` class body — from its docstring through the final `return statistics.median(segment)` — with:

```python
class BreakAdjustedShare(_ShareBaseline):
    """§10.3 variant 5: robust to a level break in the share series.

    Uses the median of the most recent segment after the largest single-step change, so one
    reclassification or one plant closure does not drag the estimate toward a regime that ended.

    REFUSES RATHER THAN IMPERSONATES. A cut leaving fewer than two points in the recent segment
    is not evidence of a regime, so this variant declines it: a one-point segment IS the last
    observation, which is variant 1, and a history too short to cut at all reduces to the plain
    median, which is variant 3. Either would ship another variant's number under this one's name.
    `_reduce` returns `None` instead and the cell takes the declared §10.2 fallback -- the same
    refusal `SameMonthPreviousYearShare` makes, for the same reason.

    THE THRESHOLD IS A PROPERTY OF THE SELECTED CUT, NOT OF THE HISTORY LENGTH. A three-point
    history cut in the middle leaves two points and is kept; a twelve-point history whose largest
    step is its last leaves one point and is refused. No bound on the number of shares separates
    those two cases.

    THE EARLIEST TIED STEP WINS. `steps.index(max(steps))` takes the first maximum, so a history
    with two equal largest steps segments at the earlier one. That is declared here, not chosen
    here: it is the behaviour this class has always had, and moving it would move cells for a
    reason nothing has argued.
    """

    estimator_id = "share_break_adjusted"

    def _reduce(self, shares, anchor, history):
        """The median of the segment following the largest single-step level change, or `None`.

        The length guard is not the threshold: it is what makes `max(steps)` legal, since a
        one-point history has no steps to take a maximum over and `max(())` raises. The threshold
        proper is the segment check, which is why it reads the cut rather than the input.
        """
        if len(shares) < 2:
            return None
        steps = [abs(shares[i + 1] - shares[i]) for i in range(len(shares) - 1)]
        cut = steps.index(max(steps)) + 1
        segment = shares[cut:]
        if len(segment) < 2:
            return None
        return statistics.median(segment)
```

> Do **not** touch `steps.index(max(steps))`. R-BREAK-5 declares the earliest-tied-step rule and forbids changing it in this plan.

- [x] **Step 7: Lint, then run the file's tests to verify they pass**

```bash
uv run ruff check src/ tests/ && uv run ruff format --check src/logging_employment/baselines/historical.py tests/unit/test_baselines_historical.py && uv run pytest tests/unit/test_baselines_historical.py -q --no-header
```

Expected: `All checks passed!`, `2 files already formatted`, then PASS, 23 passed.

- [x] **Step 8: Verify the exit-criterion grep and the untouched golden**

```bash
grep -n "below four" src/logging_employment/baselines/historical.py; echo "grep exit: $?"
```

Expected: no matching lines and `grep exit: 1`.

```bash
git status --short tests/fixtures/baselines/
```

Expected: no output.

- [x] **Step 9: Commit**

```bash
git add src/logging_employment/baselines/historical.py tests/unit/test_baselines_historical.py
git commit -m "feat(baselines): the break-adjusted share refuses a degenerate cut

R-BREAK-1: _reduce returns None unless the selected cut leaves at least two
points in the recent segment. A one-point segment is LastObservedShare and a
whole-history median is RollingMedianShare, so either shipped another
variant's number under variant 5's label.

R-BREAK-2: the threshold reads the CUT, not the history length -- a length-3
history cut in the middle is kept, a length-12 history cut at its end is not.
R-BREAK-4: the docstring's four-share claim is replaced by the refusal it now
makes. R-BREAK-5: the earliest-tied-step rule is declared, not changed."
```

---

## Task 3: A refused cell composes rather than declines

R-BREAK-3 and T-7. Task 2 proved the *reduction* refuses; this proves the refusal lands on the declared §10.2 fallback instead of declining the month — the property Stage 4's scoreboard depends on.

**Files:**
- Test: `tests/unit/test_baselines_historical.py` — add one test after `test_a_long_history_with_an_interior_break_follows_the_recent_segment`

**Interfaces:**
- Consumes: `BreakAdjustedShare._reduce` from Task 2; the existing `_share_rows(months, employment) -> list[dict]` and `_context(monthly, cfg) -> EstimatorContext` helpers; `national_residual`, `observed_partition`, `FALLBACK` and `pytest`, all already imported at the top of the file.
- Produces: nothing later tasks consume.

- [x] **Step 1: Add the `Weights` import**

In `tests/unit/test_baselines_historical.py`, change:

```python
from logging_employment.baselines.interfaces import FALLBACK, OWN, EstimatorContext
```

to:

```python
from logging_employment.baselines.interfaces import FALLBACK, OWN, EstimatorContext
from logging_employment.reconcile.allocate import Weights
```

> Add this together with Step 2's test, in one pass. On its own it is an unused import and `uv run ruff check` fails with `F401`.

- [x] **Step 2: Write the test**

Insert after `test_a_long_history_with_an_interior_break_follows_the_recent_segment` and before the docstring test:

```python
def test_a_refused_cell_takes_the_establishment_fallback_rather_than_declining(
    make_monthly, appendix_a_config
) -> None:
    """T-7. R-BREAK-3: refusal reuses the existing `None` path, so the cell is COMPOSED, not
    declined -- no new decline reason and no new config key.

    The anchor comes from `national_residual` rather than being typed, because R-COMP-8 requires
    the intensity and the residual to come from one partition and refuses them when they do not:
    a hand-typed residual raises `ConceptViolationError` here the moment a fallback arm is built.
    State 02 is disclosed at the anchor so the fallback has an intensity to be scaled by."""
    rows = _share_rows(["2023-12", "2024-01", "2024-02"], [10, 11, 90])
    rows.append(
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": 800,
            "qtrly_establishments": 80,
            "observation_status": "observed",
        }
    )
    monthly = make_monthly(*rows)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    assert anchor.missing_cells == ("01",)

    out = BreakAdjustedShare().weights(_context(monthly, appendix_a_config), anchor)

    assert isinstance(out, Weights), "a refused cell is composed, not declined"
    assert out.basis["01"] == FALLBACK
    # Derived from the fixture: 2024-03's only disclosed cell is state 02, 800 employees over 80
    # establishments, and state 01 brings 4 establishments of exposure to that intensity.
    assert out.values["01"] == pytest.approx(4 * (800 / 80))
```

> The share history here is `[0.010, 0.011, 0.090]` — its largest step is the last, so the cut leaves one point and Task 2's rule refuses it. That is the same shape as T-4, driven through the full `weights` path.

- [x] **Step 3: Run the test to verify it passes**

```bash
uv run ruff check src/ tests/ && uv run pytest tests/unit/test_baselines_historical.py::test_a_refused_cell_takes_the_establishment_fallback_rather_than_declining -q --no-header
```

Expected: PASS, 1 passed.

> This test is written **after** its implementation on purpose — Task 2 shipped the behaviour it checks. To see it fail as a red bar, temporarily insert `if len(shares) < 4: return statistics.median(shares)` as the first line of `_reduce` and re-run: it fails on `out.basis["01"] == FALLBACK`, because under the old rule the cell reduces to 0.011 and takes `OWN`.
>
> **Undo that insertion by deleting the two lines you just typed — by hand.** Do not reach for `git checkout` or `git restore`: your Task 3 test edit is uncommitted at this point, and a checkout that slips past `historical.py` to the test file or the working tree discards it. Re-run the command above and confirm `1 passed` before continuing.

> Deviation: the red bar was taken WITHOUT the temporary source edit. This step's own warning is
> the argument against it — with the Task 3 test edit uncommitted, mutating `historical.py` puts
> the only copy of that edit one slipped checkout away from gone, for a witness obtainable another
> way. The old `<4` rule was instead restored by monkeypatching `BreakAdjustedShare._reduce` in a
> throwaway `uv run python` process: the basis flipped to `own_estimator` with value **11.0** --
> `RollingMedianShare`'s number, §1's impersonation reproduced end-to-end -- against
> `establishment_fallback` at 40.0 under the shipped rule. The same process confirmed
> `RollingMedianShare` takes `own_estimator` on that fixture, ruling out the vacuous pass where an
> empty history sends the cell to the fallback via `if not shares: continue`. No file was mutated.

- [x] **Step 4: Run the full suite**

```bash
uv run pytest tests/ -q --no-header
```

Expected: **PASS, 1181 passed**, no new skips. Measured on a full prototype run of this exact change: the tree before this plan is `1175 passed`, and the plan deletes one test and adds seven (T-1…T-6 and T-7; the docstring test is renamed, not added), for a net of `+6`. `tests/integration/test_baseline_golden.py` is among the passes — that is T-8.

- [x] **Step 5: Confirm the golden parquet is byte-identical (T-8)**

```bash
git status --short tests/fixtures/baselines/ && git diff --stat
```

Expected: `git status` prints nothing for the fixtures directory, and `git diff --stat` shows no `tests/fixtures/` entry. If `baseline_results_golden.parquet` appears, **stop and report** — per spec §4 a plan that finds otherwise has changed something the spec did not ask for. Do not regenerate it.

- [x] **Step 6: Walk the spec's §7 exit criteria explicitly**

```bash
grep -n "below four" src/logging_employment/baselines/historical.py; echo "grep exit: $? (1 = criterion met)"
```

Confirm each of §7's bullets: T-5 covers the length-12 refusal; T-3 covers the length-3 keep; the grep returns nothing; the golden is unchanged in the diff; the full suite passes with no new skips. The final bullet — ticking `specs/deferred_items.md` — is the Plan Completion Protocol's job, not this task's.

- [x] **Step 7: Commit**

```bash
git add tests/unit/test_baselines_historical.py
git commit -m "test(baselines): a refused break-adjusted cell composes, not declines

T-7 / R-BREAK-3. The anchor is built by national_residual rather than typed:
once a fallback arm exists, R-COMP-8 refuses an anchor whose residual does not
match the partition its intensity came from."
```

---

## Plan Completion Protocol notes for the executor

When every task is done and the final review is resolved, run the protocol from the writing-plans skill. Two specifics for this plan:

1. **The `deferred_items.md` item to tick is the one at line 688**, whose text begins:

   > `- [ ] **`BreakAdjustedShare`'s `<4` fallback is a design choice nobody chose.**`

   There is a **second, already-ticked** `BreakAdjustedShare` item at line 593 (`→ done in plan 7`) — leave it alone. Tick line 688's box and append `→ done in plan 10`.

2. **Retire the spec too.** `specs/break-adjusted-share-refusal.md` exists, and no other live plan in `specs/plans/` carries the `break-adjusted-share-refusal` suffix, so it moves to `specs/completed/` marked complete at the top, in the same `chore(specs): retire plan 10` commit as the plan's move to `specs/plans/completed/`. Re-point any relative links in both files for their new depth. This spec has no roadmap stage (see its header), so there is no roadmap inherited-contract block to correct.

3. **Expect nothing to defer.** Every spec requirement has a task. If the gate does turn something up, add the section to `specs/deferred_items.md`; otherwise use the `nothing deferred` form of the status header.
