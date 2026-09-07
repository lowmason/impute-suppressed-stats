# Estimator Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the two-arm composition step `baselines/interfaces.py::compose` performs a written
contract — a declared employees-valued type in place of a magnitude tripwire, exactly one fallback
construction whose intensity each estimator declares, and a `decline_kind` on every declined row.

**Architecture:** `EmployeeWeights` is a frozen wrapper that carries the unit claim structurally, so
a raw establishment count cannot reach `compose` at a call site; the `MAX_SCALE_RATIO` guard it
replaces is deleted, because the honest ratio range and the bug's range overlap and no threshold
separates them. A new `baselines/fallback.py` owns the single fallback construction, the two
declared intensities, and the lazy `compose_with_declared_fallback` wrapper each composing
estimator calls. `Decline` gains a closed-set `kind`, which reaches `baseline_results.parquet` as a
new column and the run manifest as a breakdown.

**Tech Stack:** Python ≥3.14, Polars, Pydantic, Typer, pytest, uv. Lint/format: ruff + black at
line-length 100. `interrogate` runs at `fail-under = 100` over `src/`, so **every** new module,
class, function, and `__post_init__` needs a docstring.

**Spec:** `specs/estimator-composition.md` (requirements R-COMP-1 … R-COMP-11, tests T-1 … T-6).

## Global Constraints

- Line length 100 (`ruff` and `black` both configured at 100 in `pyproject.toml`).
- Docstring coverage is enforced at 100% over `src/` by `interrogate`; `tests/` is excluded.
- The full suite is green at the start of this plan: `1156 passed` on 2026-09-07. No task may
  leave it red, and no task may add a skip.
- `data/` is gitignored and large. Execute this plan **in the main checkout**, not a worktree —
  `tests/integration/test_d1_baselines.py` and `test_d1_acceptance.py` carry a `skipif` on the
  staged data and would silently skip in a fresh worktree.
- Run tests with `uv run pytest`. There is no `timeout` binary on this machine; do not wrap
  commands in one.
- The spec amendment in Task 7 assumes one reading that is stated here so a reviewer can veto it:
  `specs/estimator-composition.md` §4.2 says "**§7 `baseline_result`.** Add `decline_kind`", but
  `specs/logging-employment-spec.md` §7 runs 7.1–7.12 and contains no `baseline_result` contract
  (verified: `grep -n "baseline_result" specs/logging-employment-spec.md` returns only the
  `baseline_results/` directory line in §6.2). Since the amendment is filed under "Amendments to
  `logging-employment-spec.md`", a code-only reading would not be an amendment at all. Task 7
  therefore **adds §7.13 `baseline_result`** with `decline_kind` in it, mirroring §7.12's shape.

---

### Task 1: `EmployeeWeights` — the unit carried by the type

Satisfies R-COMP-1, R-COMP-2, and test T-2. The magnitude guard stays alive in this task and is
deleted in Task 2, so this task's diff is exactly "the arms are now typed".

**Files:**
- Modify: `src/logging_employment/baselines/interfaces.py`
- Modify: `src/logging_employment/baselines/__init__.py`
- Modify: `src/logging_employment/baselines/historical.py:154-159`
- Modify: `src/logging_employment/baselines/intensity.py:129-133`
- Modify: `src/logging_employment/baselines/regression.py:73-98`
- Test: `tests/unit/test_baseline_interfaces.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `EmployeeWeights(values: dict[str, float])` — frozen dataclass in `interfaces.py`.
  - `usable_own(own: EmployeeWeights, anchor: Anchor) -> dict[str, float]`
  - `compose(own: EmployeeWeights, fallback: EmployeeWeights, anchor: Anchor, *, allowed: bool)
    -> Weights | Decline` — the two arms are now positional-typed, everything else unchanged.

- [ ] **Step 1: Write the failing tests**

Replace the whole of `tests/unit/test_baseline_interfaces.py` with the version below. Every
`compose` call now wraps its arms; `test_arms_in_incommensurable_units_are_refused` and
`test_arms_on_a_common_scale_compose_without_complaint` are gone, replaced by the two tests that
carry their meaning under the new design — `test_a_raw_dict_cannot_be_passed_as_an_arm` (T-1) and
`test_an_empty_own_arm_composes_into_an_all_fallback_composite` (T-2).

```python
"""The Estimator protocol and the declared-composite rule that keeps §10.8 populated."""

from __future__ import annotations

import pytest

from logging_employment.baselines.interfaces import (
    FALLBACK,
    OWN,
    Decline,
    EmployeeWeights,
    compose,
)
from logging_employment.errors import ConceptViolationError, WeightDomainError
from logging_employment.reconcile.anchor import Anchor

CELLS = ("01", "02", "04")


def _anchor() -> Anchor:
    return Anchor("2024-03", 100.0, CELLS, "declared_national_total")


def test_full_own_coverage_needs_no_fallback() -> None:
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0, "04": 3.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 9.0}),
        _anchor(),
        allowed=True,
    )
    assert set(w.basis.values()) == {"own_estimator"}


def test_partial_own_coverage_composes_and_records_the_basis_per_cell() -> None:
    """Two gap cells, and the WHOLE mapping: labelling only the first gap must not pass."""
    anchor = Anchor("2024-03", 100.0, ("01", "02", "04", "05"), "declared_national_total")
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0, "05": 8.0}),
        anchor,
        allowed=True,
    )
    assert w.values["04"] == 7.0
    assert w.values["05"] == 8.0
    assert w.basis == {"01": OWN, "02": OWN, "04": FALLBACK, "05": FALLBACK}


def test_composition_refused_by_config_yields_a_decline_not_a_silent_subset() -> None:
    out = compose(
        EmployeeWeights({"01": 1.0, "02": 2.0}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0}),
        _anchor(),
        allowed=False,
    )
    assert isinstance(out, Decline)
    assert "04" in out.reason


def test_a_fallback_that_cannot_cover_the_gap_is_refused() -> None:
    """§10.2's rung is complete on D1, but the code may not assume that."""
    with pytest.raises(WeightDomainError):
        compose(
            EmployeeWeights({"01": 1.0}),
            EmployeeWeights({"01": 9.0, "02": 9.0}),
            _anchor(),
            allowed=True,
        )


def test_a_non_positive_own_weight_falls_back_rather_than_poisoning_the_vector() -> None:
    """§12.2 requires positive weights; a zero own-weight is not one.

    Also pins the negative half of `EmployeeWeights`' contract: the type does NOT validate
    positivity. A zero here is a cell with no own signal, and `compose` hands it to the fallback.
    """
    w = compose(
        EmployeeWeights({"01": 1.0, "02": 0.0, "04": 3.0}),
        EmployeeWeights({"01": 9.0, "02": 5.0, "04": 9.0}),
        _anchor(),
        allowed=True,
    )
    assert w.values["02"] == 5.0
    assert w.basis["02"] == "establishment_fallback"


def test_a_raw_dict_cannot_be_passed_as_an_arm() -> None:
    """T-1. The substitution the deleted magnitude guard could not see.

    Measured on the D1 window: replacing the scaled fallback with a raw establishment count
    produced ratios of 0.182-0.811 for the share family and 0.160-0.316 for §10.4 — entirely
    inside the honest 0.947-4.996 range — and shipped own-cell estimates up to 6.12x too large
    with zero guard trips, every value positive and every month summing exactly to the residual.
    So this asserts a CONSTRUCTION failure, never a magnitude: no threshold separates the two.
    """
    raw_establishment_counts = {"01": 9.0, "02": 9.0, "04": 7.0}
    with pytest.raises(ConceptViolationError, match="EmployeeWeights"):
        compose(
            EmployeeWeights({"01": 1.0, "02": 2.0}),
            raw_establishment_counts,
            _anchor(),
            allowed=True,
        )
    with pytest.raises(ConceptViolationError, match="EmployeeWeights"):
        compose(
            {"01": 1.0, "02": 2.0},
            EmployeeWeights(raw_establishment_counts),
            _anchor(),
            allowed=True,
        )


def test_an_empty_own_arm_composes_into_an_all_fallback_composite() -> None:
    """T-2 / R-COMP-2. §10.6 composes entirely from the fallback when the fit has too few rows,
    so an empty own arm is a valid composite rather than an error the type may refuse."""
    w = compose(
        EmployeeWeights({}),
        EmployeeWeights({"01": 9.0, "02": 9.0, "04": 7.0}),
        _anchor(),
        allowed=True,
    )
    assert set(w.basis.values()) == {"establishment_fallback"}
    assert w.values == {"01": 9.0, "02": 9.0, "04": 7.0}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baseline_interfaces.py -q`
Expected: FAIL — `ImportError: cannot import name 'EmployeeWeights'`.

- [ ] **Step 3: Add the type and retype `compose`**

In `src/logging_employment/baselines/interfaces.py`, add `ConceptViolationError` to the errors
import:

```python
from ..errors import ConceptViolationError, WeightDomainError
```

Add the type immediately after the `FALLBACK` / `MAX_SCALE_RATIO` constants:

```python
@dataclass(frozen=True)
class EmployeeWeights:
    """A weight vector in EMPLOYEES, claimed where it is constructed rather than inferred.

    `allocate` normalizes the union of a composite's two arms, so a union of arms in different
    units is decided entirely by whichever arm is numerically larger -- and the result is positive
    in every cell and sums exactly to R_t, which is why review does not catch it. The claim is
    made once, here, by whoever builds the vector; nothing re-derives it from the values.

    NO POSITIVITY CHECK HERE, DELIBERATELY. `compose` reads a non-positive own weight as a cell
    with no own signal and hands that cell to the fallback, which is behaviour §12.2 requires and
    a test pins. Positivity is enforced by `allocate.check_domain` on the COMPOSED vector -- the
    one that becomes estimates -- so validating it here would turn a legitimate fall-back into a
    raise.
    """

    values: dict[str, float]
```

Replace the `usable`/`gaps` prologue of `compose` with a public helper, placed just above
`compose`:

```python
def usable_own(own: EmployeeWeights, anchor: Anchor) -> dict[str, float]:
    """The own weights `compose` will actually use: in the missing set, present, and positive.

    Public so a caller can ask whether a fallback arm is needed at all before paying to build one.
    Duplicating this predicate at a call site would let "needs a fallback" and "took the fallback"
    drift apart, which is the split `weight_basis` exists to report.
    """
    return {
        cell: value
        for cell, value in own.values.items()
        if cell in anchor.missing_cells and value is not None and value > 0.0
    }
```

Then rewrite `compose`'s signature and body (the `_assert_comparable_scales` call stays for now
and reads the wrapped values):

```python
def compose(
    own: EmployeeWeights,
    fallback: EmployeeWeights,
    anchor: Anchor,
    *,
    allowed: bool,
) -> Weights | Decline:
    """Own weight where it is positive and finite, declared fallback elsewhere.

    Both arms are `EmployeeWeights` and nothing else. A type annotation alone would not carry
    that: nothing in this project runs a static type checker, so the refusal below is what stops
    a plain `dict[str, float]` from impersonating an employees-valued arm at a call site.

    Raises `WeightDomainError` when the fallback itself cannot cover the gap: that is a data
    problem, not an estimator's refusal, and it must not be reported as a decline.
    """
    for name, arm in (("own", own), ("fallback", fallback)):
        if not isinstance(arm, EmployeeWeights):
            raise ConceptViolationError(
                f"{anchor.reference_month}: compose's {name} arm is a {type(arm).__name__}, not "
                "an EmployeeWeights. Both arms are employees-valued and the unit is carried by "
                "the type: measured on D1, substituting a raw establishment count for the scaled "
                "fallback shipped own-cell estimates up to 6.12x too large while every value "
                "stayed positive and every month summed exactly to the residual"
            )
    usable = usable_own(own, anchor)
    gaps = [cell for cell in anchor.missing_cells if cell not in usable]
    if not gaps:
        return Weights(values=usable, basis=dict.fromkeys(usable, OWN))

    if not allowed:
        return Decline(
            reason=(
                "baselines.allow_declared_composite is false and this estimator has no own weight "
                f"for {sorted(gaps)}"
            )
        )

    uncovered = [cell for cell in gaps if fallback.values.get(cell, 0.0) <= 0.0]
    if uncovered:
        raise WeightDomainError(
            f"{anchor.reference_month}: the establishment fallback cannot weight {sorted(uncovered)}"
        )

    _assert_comparable_scales(usable, fallback.values, anchor)
    values = dict(usable) | {cell: fallback.values[cell] for cell in gaps}
    basis = dict.fromkeys(usable, OWN) | dict.fromkeys(gaps, FALLBACK)
    return Weights(values=values, basis=basis)
```

- [ ] **Step 4: Wrap the four call sites**

In `src/logging_employment/baselines/historical.py`, add `EmployeeWeights` to the interfaces
import and wrap the own arm (lines 154-159):

```python
from .interfaces import Decline, EmployeeWeights, EstimatorContext, compose
```

```python
        return compose(
            EmployeeWeights(own),
            EmployeeWeights(establishment_fallback_in_employees(context, anchor)),
            anchor,
            allowed=cfg.allow_declared_composite,
        )
```

In `src/logging_employment/baselines/intensity.py` (lines 129-133):

```python
from .interfaces import Decline, EmployeeWeights, EstimatorContext, compose
```

```python
        # Both arms in employees: the fallback is the shrinkage limit, not a bare exposure count.
        fallback = {cell: national * value for cell, value in exposure.items()}
        return compose(
            EmployeeWeights(own),
            EmployeeWeights(fallback),
            anchor,
            allowed=context.config.baselines.allow_declared_composite,
        )
```

In `src/logging_employment/baselines/regression.py`, both call sites (lines 73-81 and 93-98):

```python
from .interfaces import Decline, EmployeeWeights, EstimatorContext, compose
```

```python
        if training.height < MINIMUM_TRAINING_ROWS:
            # Not a decline: the declared fallback covers it, and a two-point fit would be noise
            # dressed as a model.
            return compose(
                EmployeeWeights({}),
                EmployeeWeights(establishment_fallback_in_employees(context, anchor)),
                anchor,
                allowed=context.config.baselines.allow_declared_composite,
            )
```

```python
        # The own arm is exp(mu) * A, i.e. employees, so the fallback must be too. On D1 the
        # exposure covers every missing cell and no gap arises, but a raw-A fallback here would be
        # the same units bug §10.3 and §10.4 carried, waiting for the first month that has one.
        return compose(
            EmployeeWeights(own),
            EmployeeWeights(establishment_fallback_in_employees(context, anchor)),
            anchor,
            allowed=context.config.baselines.allow_declared_composite,
        )
```

In `src/logging_employment/baselines/__init__.py`, export the new type:

```python
from .interfaces import Decline, EmployeeWeights, Estimator, EstimatorContext, compose

__all__ = ["Decline", "EmployeeWeights", "Estimator", "EstimatorContext", "compose"]
```

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, 1155 passed. The count DROPS BY ONE from the 1156 this plan starts at:
`test_baseline_interfaces.py` goes from eight tests to seven, because the two magnitude-guard
tests are replaced by T-1 and T-2. Both removals are subsumed, which is the claim a reviewer
should check rather than reconstruct: `test_arms_in_incommensurable_units_are_refused` asserted the
guard this plan deletes, and T-1 asserts the refusal that replaces it on the substitution the guard
could not see; `test_arms_on_a_common_scale_compose_without_complaint` asserted that an honest
composite passes, which is exactly what
`test_partial_own_coverage_composes_and_records_the_basis_per_cell` asserts over the same shape. A
different number means a test elsewhere changed behaviour.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment/baselines tests/unit/test_baseline_interfaces.py
git commit -m "feat(baselines): carry the composite's unit in a declared type (R-COMP-1, R-COMP-2)"
```

---

### Task 2: Delete the magnitude guard and the prose it licensed

Satisfies R-COMP-3 and R-COMP-4. The prose is a deliverable here, not cleanup: this repo's
recurring failure is an aged claim surviving the code change that falsified it, and
`interfaces.py`'s module docstring currently asserts that a guard enforces the unit.

**Files:**
- Modify: `src/logging_employment/baselines/interfaces.py:23-31, 36-37, 51-53, 83-105, 144`
- Modify: `tests/integration/test_baseline_golden.py` (module docstring + golden test docstring)

**Interfaces:**
- Consumes: `EmployeeWeights`, `compose` from Task 1.
- Produces: `MAX_SCALE_RATIO` and `_assert_comparable_scales` no longer exist.

- [ ] **Step 1: Delete the guard**

In `src/logging_employment/baselines/interfaces.py`:

Delete the two now-unused imports:

```python
import math
import statistics
```

Delete the constant and its comment:

```python
# A units tripwire, not a statistical threshold. Arms that genuinely share a unit sit within a
# small factor of each other; the failure this exists to catch was four orders of magnitude.
MAX_SCALE_RATIO = 100.0
```

Delete the whole `_assert_comparable_scales` function (its `def` line through the closing paren of
the `raise`), and delete its call site inside `compose`:

```python
    _assert_comparable_scales(usable, fallback.values, anchor)
```

- [ ] **Step 2: Rewrite the module docstring paragraph it licensed**

In `src/logging_employment/baselines/interfaces.py`, replace the final paragraph of the module
docstring — the one beginning `BOTH ARMS MUST BE IN THE SAME UNIT, AND THE GUARD ENFORCES IT.` and
ending `...rather than a statistical test of anything.` — with:

```
BOTH ARMS ARE IN EMPLOYEES, AND THE TYPE IS WHAT SAYS SO. `allocate` normalizes the merged vector
as a whole (E = R * q / sum q), so a union of arms in different units is decided entirely by
whichever arm is numerically larger. Measured on 2024-03 with §10.3's shares against raw
establishment counts: nine states holding full observed histories received 0.58 of 1,589 employees
between them -- 0.037% of the residual -- while one fallback state took 1,257. Nothing about that
output looks wrong; it is positive everywhere and sums exactly to R_t.

A MAGNITUDE TRIPWIRE WAS TRIED AND REMOVED, AND NO THRESHOLD REPLACES IT. `MAX_SCALE_RATIO = 100`
compared the two arms' medians over 495 of 660 `compose` calls and caught the four-orders-of-
magnitude shape. It could not catch the case its own callers were written to prevent: substituting
a raw establishment count for the scaled fallback produced ratios of 0.182-0.811 for the share
family and 0.160-0.316 for §10.4, inside the honest 0.947-4.996 range, and reintroduced on D1 that
bug tripped the guard zero times while shipping own-cell estimates up to 6.12x too large. The
honest range and the bug's range overlap, so the unit is carried by `EmployeeWeights` instead --
a claim made once, where the vector is built, that a plain dict cannot impersonate at a call site.
(Measured 2026-09-06 on the D1 window and `tests/fixtures/baselines/`; see
`specs/estimator-composition.md` §2.)
```

- [ ] **Step 3: State the golden's role where the golden is defined (R-COMP-4)**

Removing the guard leaves the frozen baseline golden as the only remaining check on a *data*
pathology a type cannot see. In `tests/integration/test_baseline_golden.py`, replace the module
docstring:

```python
"""§17.4 row 4 and §17.6: every baseline on a frozen fixture, pinned to golden output.

THIS FILE IS THE UNITS-AND-MAGNITUDE REGRESSION NET. `EmployeeWeights` carries the composite's
unit claim structurally, but a type cannot see a corrupt source column or a CBP vintage that moves
an intensity -- both change the NUMBERS while every arm stays honestly typed. Since
`MAX_SCALE_RATIO` was removed (see `specs/estimator-composition.md` R-COMP-3), the golden below is
the only check that would redden on either. Re-pinning it is therefore a decision about the data,
not a chore: §17.6 requires a documented reason and reviewer approval, and the reason belongs in
the commit that regenerates the file.
"""
```

and extend the golden test's docstring with the same claim in one line:

```python
def test_the_baseline_output_matches_its_golden_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    """§17.6 golden coverage for baseline predictions and reconciliation.

    Also the units-and-magnitude regression net described in this module's docstring: a source
    column or a CBP vintage that moves an intensity redden here or nowhere.

    The in-memory frame is put into the writer's own row order before comparing.
    `run_baselines` returns rows in emission order (month, then estimator) while
    `write_parquet_deterministic` sorts on write, so a direct `.equals` is False even when every
    value agrees. Reusing `deterministic_order` rather than re-sorting by hand keeps the test
    from drifting away from the writer it is checking.
    """
```

- [ ] **Step 4: Verify the guard is gone by name**

Run:

```bash
grep -rn "MAX_SCALE_RATIO\|_assert_comparable_scales\|comparable scales\|THE GUARD ENFORCES" src/ tests/
```

Expected: no output (exit status 1). This is the exit criterion "`MAX_SCALE_RATIO` does not appear
in the codebase" as a command rather than an assertion.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, 1155 passed — unchanged from Task 1. This task deletes production code and rewrites
prose; it adds and removes no test.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment/baselines/interfaces.py tests/integration/test_baseline_golden.py
git commit -m "refactor(baselines): remove MAX_SCALE_RATIO and the claim it licensed (R-COMP-3, R-COMP-4)"
```

---

### Task 3: One fallback construction, with a declared intensity

Satisfies R-COMP-5, R-COMP-6, R-COMP-7 and test T-4.

**Files:**
- Create: `src/logging_employment/baselines/fallback.py`
- Modify: `src/logging_employment/baselines/interfaces.py` (`Estimator` protocol)
- Modify: `src/logging_employment/baselines/simple.py` (remove the two moved functions; declare
  `fallback_intensity = None` on both estimators)
- Modify: `src/logging_employment/baselines/intensity.py` (import the moved CBP helpers; declare
  and use the national intensity)
- Modify: `src/logging_employment/baselines/historical.py`
- Modify: `src/logging_employment/baselines/regression.py`
- Modify: `src/logging_employment/baselines/harvest.py` (`fallback_intensity = None`)
- Test: `tests/unit/test_baselines_fallback.py` (new)

**Interfaces:**
- Consumes: `EmployeeWeights`, `usable_own`, `compose`, `OWN`, `FALLBACK` from Task 1;
  `establishment_weights(context, anchor) -> dict[str, float]` from `simple.py` (unchanged, still
  returns RAW establishment counts).
- Produces, all in `baselines/fallback.py`:
  - `DISCLOSED_QCEW = "disclosed_qcew"`, `NATIONAL_CBP_MARCH = "national_cbp_march"`,
    `FALLBACK_INTENSITIES: tuple[str, ...]`
  - `ALL_ESTABLISHMENTS_SIZE_CODE = "001"` (moved from `intensity.py`)
  - `intensity_rows(cbp: pl.DataFrame, reference_year: int) -> pl.DataFrame` (moved and made
    public; was `intensity._intensity_rows`)
  - `national_march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> float | None` (moved
    from `intensity.py`)
  - `disclosed_intensity(context: EstimatorContext, anchor: Anchor) -> float | None` (moved from
    `simple.py`)
  - `national_cbp_march_intensity(context: EstimatorContext, anchor: Anchor) -> float | None`
  - `resolve_intensity(basis: str, context: EstimatorContext, anchor: Anchor) -> float | None`
  - `establishment_fallback(context, anchor, *, intensity: float) -> EmployeeWeights`
  - `declared_fallback(estimator: Estimator, context, anchor) -> EmployeeWeights`
  - `compose_with_declared_fallback(estimator, own: EmployeeWeights, context, anchor)
    -> Weights | Decline`
  - `Estimator` gains the attribute `fallback_intensity: str | None`.
- **Import direction, which must not be reversed:** `interfaces` ← `simple` ← `fallback` ←
  {`historical`, `regression`, `intensity`} ← `runner`. `fallback.py` **never** imports
  `intensity.py`; `intensity.py` imports `intensity_rows` and `national_march_intensity` back out
  of `fallback.py`. That is why §10.4's CBP March helpers move: they are one of the two declared
  intensities, so the module that resolves a declaration must own them, and `march_intensity`'s
  shrink target is exactly that value.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_baselines_fallback.py`:

```python
"""The one fallback construction, and each estimator's declared intensity (R-COMP-5 to R-COMP-7)."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.fallback import (
    DISCLOSED_QCEW,
    FALLBACK_INTENSITIES,
    NATIONAL_CBP_MARCH,
    declared_fallback,
    establishment_fallback,
    resolve_intensity,
)
from logging_employment.baselines.harvest import HarvestProportional
from logging_employment.baselines.historical import LastObservedShare
from logging_employment.baselines.intensity import CbpIntensity
from logging_employment.baselines.interfaces import EmployeeWeights, EstimatorContext
from logging_employment.baselines.regression import ConstrainedRegression
from logging_employment.baselines.runner import REGISTRY
from logging_employment.baselines.simple import EqualAllocation, establishment_weights
from logging_employment.errors import ConceptViolationError
from logging_employment.reconcile.anchor import national_residual, observed_partition

COMPOSING_IDS = {
    "share_last_observed",
    "share_same_month_prior_year",
    "share_rolling_median",
    "share_exponentially_weighted",
    "share_break_adjusted",
    "cbp_intensity",
    "constrained_regression",
}


def _panel(make_monthly) -> pl.DataFrame:
    """One month: state 01 disclosed at 40 over 4, state 02 suppressed with 6 establishments."""
    return make_monthly(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 100,
            "qtrly_establishments": 10,
        },
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": 40,
            "qtrly_establishments": 4,
            "observation_status": "observed",
        },
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 6,
            "observation_status": "suppressed",
        },
    )


def _cbp() -> pl.DataFrame:
    """A CBP frame for 2024 with one state: 70 employees over 10 establishments, so the national
    March intensity is 7.0 and is distinguishable from the disclosed 10.0."""
    return pl.DataFrame(
        {
            "reference_year": [2024],
            "state_fips": ["01"],
            "size_code": ["001"],
            "establishments": [10],
            "employment": [70],
        }
    )


def _context_and_anchor(monthly, cfg, cbp=None):
    partitions = observed_partition(monthly)
    context = EstimatorContext(
        monthly=monthly,
        cbp=pl.DataFrame() if cbp is None else cbp,
        partitions=partitions,
        config=cfg,
    )
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    return context, anchor


def test_every_estimator_declares_a_fallback_intensity_or_declares_none() -> None:
    """R-COMP-6. The declaration is a property of the estimator, so it is readable without
    reading a method body -- which is what lets the manifest report it."""
    for estimator in REGISTRY:
        declared = estimator.fallback_intensity
        assert declared is None or declared in FALLBACK_INTENSITIES, estimator.estimator_id
        assert (estimator.estimator_id in COMPOSING_IDS) == (declared is not None)


def test_the_two_families_declare_the_two_different_intensities() -> None:
    """R-COMP-7: the divergence is permitted and declared, not standardised away."""
    declared = {e.estimator_id: e.fallback_intensity for e in REGISTRY}
    assert declared["share_last_observed"] == DISCLOSED_QCEW
    assert declared["constrained_regression"] == DISCLOSED_QCEW
    assert declared["cbp_intensity"] == NATIONAL_CBP_MARCH
    assert declared["equal_residual"] is None
    assert declared["harvest_proportional"] is None


@pytest.mark.parametrize(
    ("estimator", "expected_intensity"),
    [
        # The disclosed ratio of two published sums on this fixture: 40 employees over 4
        # establishments.
        (LastObservedShare(), 10.0),
        (ConstrainedRegression(), 10.0),
        # §10.4's national CBP March intensity: 70 over 10. A DIFFERENT number from the same
        # fixture, which is what makes this parametrize check R-COMP-7's divergence rather than
        # three readings of one class attribute.
        (CbpIntensity(), 7.0),
    ],
)
def test_the_shipped_fallback_arm_is_the_declared_intensity_times_exposure(
    estimator, expected_intensity, make_monthly, appendix_a_config
) -> None:
    """T-4, per estimator rather than for the registry in aggregate.

    Two things, and the second is why `CbpIntensity` is in the list: the intensity is resolved
    independently here and compared against the arm the estimator actually ships, so a declaration
    that drifts from its body fails rather than agreeing with itself; and the expected value is
    pinned per estimator, so the two families having to disagree (R-COMP-7) is asserted rather
    than assumed. A parametrize over two estimators that declare the SAME intensity would pass on
    a registry where every estimator read one shared constant.
    """
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config, cbp=_cbp())
    intensity = resolve_intensity(estimator.fallback_intensity, context, anchor)
    assert intensity == pytest.approx(expected_intensity)
    exposure = establishment_weights(context, anchor)
    arm = declared_fallback(estimator, context, anchor)
    assert arm.values == {
        cell: pytest.approx(value * intensity) for cell, value in exposure.items()
    }


def test_the_fallback_construction_returns_the_declared_type(
    make_monthly, appendix_a_config
) -> None:
    """R-COMP-5: one construction, and what it returns is what `compose` accepts."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    arm = establishment_fallback(context, anchor, intensity=2.0)
    assert isinstance(arm, EmployeeWeights)
    assert arm.values == {"02": 12.0}


def test_an_undeclared_intensity_name_is_refused_by_name(
    make_monthly, appendix_a_config
) -> None:
    """A typo in a declaration must not reach the manifest as if it were a choice.

    A real context and anchor, not `None`: passing `None` would pass today only because the
    membership guard happens to precede every use of them, and would turn into an `AttributeError`
    on `None` -- not the refusal this test names -- the moment those statements were reordered.
    """
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    with pytest.raises(ConceptViolationError, match="declared fallback intensity"):
        resolve_intensity("employees_per_acre", context, anchor)


@pytest.mark.parametrize("estimator", [EqualAllocation(), HarvestProportional()])
def test_an_estimator_that_declares_no_intensity_cannot_build_a_fallback_arm(
    estimator, make_monthly, appendix_a_config
) -> None:
    """R-COMP-6's other half: a composing estimator with no declaration is a bug, not a default."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    with pytest.raises(ConceptViolationError, match="fallback_intensity"):
        declared_fallback(estimator, context, anchor)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_baselines_fallback.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.baselines.fallback'`.

- [ ] **Step 3: Create `baselines/fallback.py`**

```python
"""The one construction that turns §10.2 establishment exposure into an employees-valued arm.

WHY THERE IS EXACTLY ONE. Before this module each composing baseline built and scaled its own
fallback, which is how §10.3 and §10.6 came to scale by the disclosed intensity while §10.4 scales
by the national CBP March one, with no section asking for either. The values are close on D1 --
disclosed 5.442-6.380, national 5.914-6.139 -- so this was never a numerical problem; it was an
unexplained divergence in a layer Stage 4 is about to score.

THE DIVERGENCE IS KEPT, AND DECLARED. §10.4's national value is exactly its own shrinkage limit as
the CBP cell count goes to zero, a derivation §10.3 and §10.6 have nothing equivalent to appeal
to. So it is not standardised away; each estimator names its choice in `fallback_intensity`, the
run manifest reports it, and a reader can check an arm against the name without reading source.

WHY §10.4's CBP MARCH HELPERS LIVE HERE. `national_march_intensity` is one of the two declared
intensities, so the module that resolves a declaration owns it. `intensity.py` imports it back for
its own arm -- the shrunk per-state value shrinks TOWARD it -- and that direction is what keeps the
two modules acyclic: nothing here imports an estimator module.

THE ARM IS BUILT LAZILY. `compose_with_declared_fallback` computes the gap first and pays for the
arm only when a gap exists. That is not an optimisation. Building it eagerly, as every caller used
to, means a month whose own arm covers the whole missing set still resolves an intensity and still
reads a partition it never uses -- so a partition disagreement that cannot affect the answer would
raise anyway.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from ..errors import ConceptViolationError
from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EmployeeWeights, Estimator, EstimatorContext, compose, usable_own
from .simple import establishment_weights

# The two declared intensities, as a closed set. An estimator's `fallback_intensity` is written
# into `baseline_manifest.json`, so a value outside this tuple would reach a run's output as
# though it were a choice someone made.
DISCLOSED_QCEW = "disclosed_qcew"
NATIONAL_CBP_MARCH = "national_cbp_march"
FALLBACK_INTENSITIES: tuple[str, ...] = (DISCLOSED_QCEW, NATIONAL_CBP_MARCH)

ALL_ESTABLISHMENTS_SIZE_CODE = "001"


def intensity_rows(cbp: pl.DataFrame, reference_year: int) -> pl.DataFrame:
    """The usable CBP rows for one reference year: published, all-establishments, non-empty."""
    return cbp.filter(
        (pl.col("reference_year") == reference_year)
        & (pl.col("size_code") == ALL_ESTABLISHMENTS_SIZE_CODE)
        & pl.col("employment").is_not_null()
        & (pl.col("establishments") > 0)
    )


def national_march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> float | None:
    """The national March employees-per-establishment, and the n -> 0 limit of the shrunk value.

    §10.4's declared fallback intensity, and the target its own per-state shrinkage pulls toward.
    A state with no CBP row weighted at this value is weighted at exactly what this estimator's
    shrinkage returns in the limit; weighting it at a bare establishment count would instead
    assert an intensity of 1.0.
    """
    rows = intensity_rows(cbp, reference_year)
    if rows.height == 0:
        return None
    establishments = float(rows["establishments"].sum())
    if establishments <= 0.0:
        return None
    return float(rows["employment"].sum()) / establishments


def disclosed_intensity(context: EstimatorContext, anchor: Anchor) -> float | None:
    """Published employees per establishment across this month's disclosed cells.

    §10.3's and §10.6's declared fallback intensity: a published ratio of two published sums. It
    is preferred over the residual-implied ratio (R_t / sum A over the missing set) because it
    stays positive and well defined when R_t is 0 -- a degenerate case §12.3 requires to succeed.
    `None` when the disclosed set carries no establishments, which leaves the caller to fall back
    to an empty arm rather than divide by zero.
    """
    disclosed = context.partitions[anchor.reference_month].disclosed
    establishments = float(disclosed["qtrly_establishments"].fill_null(0).sum())
    if establishments <= 0.0:
        return None
    return float(disclosed["employment_value"].fill_null(0).sum()) / establishments


def national_cbp_march_intensity(context: EstimatorContext, anchor: Anchor) -> float | None:
    """§10.4's declared intensity, resolved for the anchor's own reference year."""
    reference_year = int(anchor.reference_month.split("-")[0])
    return national_march_intensity(context.cbp, reference_year=reference_year)


_RESOLVERS: dict[str, Callable[[EstimatorContext, Anchor], float | None]] = {
    DISCLOSED_QCEW: disclosed_intensity,
    NATIONAL_CBP_MARCH: national_cbp_march_intensity,
}


def resolve_intensity(
    basis: str, context: EstimatorContext, anchor: Anchor
) -> float | None:
    """The value of a declared intensity, or `None` when its inputs do not support one."""
    if basis not in _RESOLVERS:
        raise ConceptViolationError(
            f"{basis!r} is not a declared fallback intensity; the declared set is "
            f"{list(FALLBACK_INTENSITIES)}. An estimator's `fallback_intensity` is written into "
            "baseline_manifest.json as the scaling a reader can check its arm against, so a name "
            "outside the set would reach a run's output as though it were a choice"
        )
    return _RESOLVERS[basis](context, anchor)


def establishment_fallback(
    context: EstimatorContext, anchor: Anchor, *, intensity: float
) -> EmployeeWeights:
    """§10.2 exposure scaled into EMPLOYEES. The only fallback arm construction there is.

    The intensity arrives as an argument rather than being chosen here, which is what makes
    "which intensity scaled this arm" a property of the caller that a manifest can report.
    """
    exposure = establishment_weights(context, anchor)
    return EmployeeWeights({cell: value * intensity for cell, value in exposure.items()})


def declared_fallback(
    estimator: Estimator, context: EstimatorContext, anchor: Anchor
) -> EmployeeWeights:
    """The fallback arm THIS estimator declares, empty when its intensity has no value.

    An empty arm is not an error here: `compose` refuses the cells it cannot cover, by name, and
    that refusal carries the month and the cells a reader needs.
    """
    basis = estimator.fallback_intensity
    if basis is None:
        raise ConceptViolationError(
            f"{estimator.estimator_id} asked for a fallback arm but declares no "
            "fallback_intensity; the choice of intensity is a property of the estimator so that a "
            "run's manifest can report it, and there is no default to fall through to"
        )
    intensity = resolve_intensity(basis, context, anchor)
    if intensity is None or intensity <= 0.0:
        return EmployeeWeights({})
    return establishment_fallback(context, anchor, intensity=intensity)


def compose_with_declared_fallback(
    estimator: Estimator,
    own: EmployeeWeights,
    context: EstimatorContext,
    anchor: Anchor,
) -> Weights | Decline:
    """`compose`, with the declared fallback arm built only when a gap actually needs one.

    Every composing estimator goes through here rather than calling `compose` directly, so the
    fallback's construction and its intensity are decided in one place for all seven of them.
    """
    needs_fallback = any(cell not in usable_own(own, anchor) for cell in anchor.missing_cells)
    fallback = (
        declared_fallback(estimator, context, anchor) if needs_fallback else EmployeeWeights({})
    )
    return compose(
        own, fallback, anchor, allowed=context.config.baselines.allow_declared_composite
    )
```

- [ ] **Step 4: Add the declaration to the `Estimator` protocol**

In `src/logging_employment/baselines/interfaces.py`, extend the protocol:

```python
class Estimator(Protocol):
    """A named producer of positive raw weights over one month's missing set."""

    estimator_id: str
    # Which intensity scales this estimator's fallback arm, or None when it builds none. Declared
    # here rather than chosen inside `weights` so that a run's manifest can report the choice, and
    # so §10.3's disclosed value and §10.4's national one stay a reviewable difference rather than
    # an accident (see `specs/estimator-composition.md` R-COMP-6 and R-COMP-7).
    fallback_intensity: str | None

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Positive weights for every cell in `anchor.missing_cells`, or a `Decline`."""
        ...
```

- [ ] **Step 5: Strip the moved functions out of `simple.py` and declare `None`**

In `src/logging_employment/baselines/simple.py`, delete `disclosed_intensity` (lines 88-99) and
`establishment_fallback_in_employees` (lines 102-121) entirely, along with the now-unused imports
they were the only users of. After the deletions the module's imports are:

```python
import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import OWN, EstimatorContext
```

Add the declaration to both estimator classes in that file:

```python
class EqualAllocation:
    """§10.1: q identically 1, so R_t splits evenly. "Use only as a sanity check."

    Absent from §10.8's fallback hierarchy on purpose -- it ignores every public signal about a
    state, including the establishment counts that are published even when employment is not.
    """

    estimator_id = "equal_residual"
    # Composes nothing: q is 1 over the whole missing set, so there is no gap to fill.
    fallback_intensity = None
```

```python
class EstablishmentProportional:
    """§10.2: q = A_{s,t}. §10.8's rung 4 and the fallback every composite leans on."""

    estimator_id = "establishment_proportional"
    # This IS the fallback rung. Its own arm is the raw establishment count, and scaling it would
    # be a no-op under normalization, so it declares no intensity and composes with nothing.
    fallback_intensity = None
```

In `src/logging_employment/baselines/harvest.py`:

```python
class HarvestProportional:
    """§10.5. Declines until Stage 7 supplies a harvest factor."""

    estimator_id = "harvest_proportional"
    # Declines on this window, so it never reaches a composite.
    fallback_intensity = None
```

- [ ] **Step 6: Rewire `historical.py`**

Replace the two `.interfaces` / `.simple` imports:

```python
from .fallback import DISCLOSED_QCEW, compose_with_declared_fallback
from .interfaces import Decline, EmployeeWeights, EstimatorContext
```

(`compose` and `establishment_fallback_in_employees` are no longer imported here.)

Declare the intensity on the shared base, so all five variants inherit it:

```python
class _ShareBaseline:
    """Shared plumbing: extract each missing cell's share history, reduce it, then compose."""

    estimator_id = "historical_share"
    # §10.3 has no shrinkage limit to appeal to, so its fallback is scaled by the published ratio
    # of two published sums over the month's disclosed cells (R-COMP-7).
    fallback_intensity = DISCLOSED_QCEW
```

And replace the `compose(...)` tail of `weights`:

```python
                # Share -> employees, so both arms of the composite share a unit.
                own[cell] = reduced * national
        return compose_with_declared_fallback(self, EmployeeWeights(own), context, anchor)
```

The local `cfg = context.config.baselines` binding is still used for the lookback keys, so leave
it; only its `allow_declared_composite` read goes away.

- [ ] **Step 7: Rewire `regression.py`**

```python
from .fallback import DISCLOSED_QCEW, compose_with_declared_fallback
from .interfaces import Decline, EmployeeWeights, EstimatorContext
from .simple import establishment_weights
```

```python
class ConstrainedRegression:
    """§10.6. q = exp(predicted log intensity) x exposure, reconciled through the shared layer."""

    estimator_id = "constrained_regression"
    # Same choice as §10.3, and for the same reason: no shrinkage limit exists to appeal to.
    fallback_intensity = DISCLOSED_QCEW
```

Both call sites collapse to one line each:

```python
        if training.height < MINIMUM_TRAINING_ROWS:
            # Not a decline: the declared fallback covers it, and a two-point fit would be noise
            # dressed as a model.
            return compose_with_declared_fallback(self, EmployeeWeights({}), context, anchor)
```

```python
        # The own arm is exp(mu) * A, i.e. employees, and `compose_with_declared_fallback` is the
        # only thing that builds the other arm -- so a raw-A fallback cannot be reintroduced here.
        return compose_with_declared_fallback(self, EmployeeWeights(own), context, anchor)
```

- [ ] **Step 8: Rewire `intensity.py`**

Delete `ALL_ESTABLISHMENTS_SIZE_CODE`, `_intensity_rows` and `national_march_intensity` from this
module and import them from `fallback.py`:

```python
from .fallback import (
    NATIONAL_CBP_MARCH,
    compose_with_declared_fallback,
    intensity_rows,
    national_march_intensity,
)
from .interfaces import Decline, EmployeeWeights, EstimatorContext
from .simple import establishment_weights
```

`march_intensity` stays here — it is §10.4's own arm — and now calls the moved helpers:

```python
def march_intensity(
    cbp: pl.DataFrame,
    *,
    reference_year: int,
    shrink_strength: float = DEFAULT_SHRINK_STRENGTH,
) -> dict[str, float]:
    """Shrunk March employees-per-establishment per state, for one CBP reference year."""
    rows = intensity_rows(cbp, reference_year)
    if rows.height == 0:
        return {}
    national = national_march_intensity(cbp, reference_year=reference_year)
    if national is None:
        return {}
    out: dict[str, float] = {}
    for row in rows.iter_rows(named=True):
        n = float(row["establishments"])
        raw = float(row["employment"]) / n
        weight = n / (n + shrink_strength)
        out[str(row["state_fips"])] = weight * raw + (1.0 - weight) * national
    return out
```

Declare the intensity and drop the hand-built fallback:

```python
class CbpIntensity:
    """§10.4. q = shrunk CBP March intensity x QCEW establishment exposure."""

    estimator_id = "cbp_intensity"
    # The national March intensity is exactly this estimator's own shrinkage limit as n -> 0, so
    # a cell with no CBP row is weighted at what its own model would have returned. §10.3 and
    # §10.6 have no such limit, which is why they declare a different intensity (R-COMP-7).
    fallback_intensity = NATIONAL_CBP_MARCH
```

and the tail of `weights` becomes:

```python
        own = {
            cell: intensity[cell] * exposure[cell]
            for cell in anchor.missing_cells
            if cell in intensity and cell in exposure
        }
        return compose_with_declared_fallback(self, EmployeeWeights(own), context, anchor)
```

The `national is None` decline above it stays exactly as it is: it names the missing CBP input in
its own words, and letting `declared_fallback` return an empty arm instead would surface the same
data problem as an anonymous `WeightDomainError`. The `national` local is still read by that
check, so it is not unused. Also delete the now-stale comment line
`# Both arms in employees: the fallback is the shrinkage limit, not a bare exposure count.` — the
class attribute says it now.

Finally, update the module docstring's last paragraph. Replace the sentence

```
`national_intensity x A` is the right
answer and costs nothing, because it is precisely what this estimator's own shrinkage returns in
the limit: as n -> 0, weight = n/(n+k) -> 0 and the shrunk intensity IS the national intensity.
```

with

```
`national_intensity x A` is the right
answer and costs nothing, because it is precisely what this estimator's own shrinkage returns in
the limit: as n -> 0, weight = n/(n+k) -> 0 and the shrunk intensity IS the national intensity.
That choice is declared as `fallback_intensity = NATIONAL_CBP_MARCH` rather than written into this
module's body, and `baselines/fallback.py` is the one thing that builds the arm.
```

- [ ] **Step 9: Run the new test, then the full suite**

Run: `uv run pytest tests/unit/test_baselines_fallback.py -q`
Expected: PASS, 9 passed — six test functions; T-4 is parametrized over three estimators and the
no-declaration test over two.

Run: `uv run pytest -q`
Expected: PASS, 1164 passed (1155 + 9).

- [ ] **Step 10: Lint and commit**

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment/baselines tests/unit/test_baselines_fallback.py
git commit -m "refactor(baselines): one fallback construction with a declared intensity (R-COMP-5 to R-COMP-7)"
```

---

### Task 4: The intensity and the residual come from one partition

Satisfies R-COMP-8 and test T-5. `disclosed_intensity` reads `context.partitions[...]` while the
residual arrives on the anchor; under a Stage 4 mask the two agree only if the harness rebuilt the
context from the same mask. This makes the disagreement a refusal.

Note for the implementer: `specs/deferred_items.md`'s `disclosed_intensity` item stays **unticked**
by this plan. It is scoped to Stage 4 enforcing this in the harness; this task supplies the
requirement Stage 4 enforces.

**Files:**
- Modify: `src/logging_employment/baselines/fallback.py`
- Modify: `tests/unit/test_baselines_historical.py:96-103` and `:275-290`
- Test: `tests/unit/test_baselines_fallback.py` (append)

**Interfaces:**
- Consumes: `disclosed_intensity` from Task 3.
- Produces: `disclosed_intensity` raises `ConceptViolationError` when the context's partition for
  the month implies a residual other than `anchor.residual`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_baselines_fallback.py`:

```python
def test_the_disclosed_intensity_refuses_a_partition_that_is_not_the_anchors(
    make_monthly, appendix_a_config
) -> None:
    """T-5 / R-COMP-8. The residual and the intensity are two readings of one disclosed set.

    A Stage 4 harness that masks a cell for the anchor but hands the estimator the unmasked
    partitions would scale the fallback off a disclosed set the residual was never computed over.
    Nothing signals that: both numbers are positive and the month still sums to R_t.
    """
    monthly = _panel(make_monthly)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")

    march = partitions["2024-03"]
    states = monthly.filter(pl.col("area_type") == "state")
    masked = {
        "2024-03": Partition(
            disclosed=march.disclosed.filter(pl.col("state_fips") != "01"),
            missing=states.filter(pl.col("state_fips").is_in(["01", "02"])),
        )
    }
    stale = EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=masked, config=appendix_a_config
    )
    with pytest.raises(ConceptViolationError, match="one partition"):
        disclosed_intensity(stale, anchor)


def test_the_disclosed_intensity_accepts_the_partition_the_anchor_came_from(
    make_monthly, appendix_a_config
) -> None:
    """The other half: agreement is the normal case and must not raise."""
    monthly = _panel(make_monthly)
    context, anchor = _context_and_anchor(monthly, appendix_a_config)
    assert disclosed_intensity(context, anchor) == pytest.approx(10.0)


def test_the_national_cbp_intensity_reads_no_partition_and_is_unaffected(
    make_monthly, appendix_a_config
) -> None:
    """R-COMP-8 binds the intensity DERIVED FROM THE DISCLOSED SET. §10.4's is derived from CBP,
    so the same stale context leaves it untouched -- the check is placed where it can bite."""
    monthly = _panel(make_monthly)
    cbp = _cbp()
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    states = monthly.filter(pl.col("area_type") == "state")
    stale = EstimatorContext(
        monthly=monthly,
        cbp=cbp,
        partitions={
            "2024-03": Partition(
                disclosed=partitions["2024-03"].disclosed.filter(pl.col("state_fips") != "01"),
                missing=states,
            )
        },
        config=appendix_a_config,
    )
    assert national_cbp_march_intensity(stale, anchor) == pytest.approx(7.0)
```

Extend that file's imports accordingly:

```python
from logging_employment.baselines.fallback import (
    DISCLOSED_QCEW,
    FALLBACK_INTENSITIES,
    NATIONAL_CBP_MARCH,
    declared_fallback,
    disclosed_intensity,
    establishment_fallback,
    national_cbp_march_intensity,
    resolve_intensity,
)
...
from logging_employment.reconcile.anchor import Partition, national_residual, observed_partition
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_fallback.py -k partition -q`
Expected: FAIL — `DID NOT RAISE ConceptViolationError` on the first test.

- [ ] **Step 3: Add the refusal**

In `src/logging_employment/baselines/fallback.py`, add `math` to the imports and
`national_residual` to the anchor import:

```python
import math
...
from ..reconcile.anchor import Anchor, national_residual
```

Add the check just above `disclosed_intensity`:

```python
def _assert_the_partition_is_the_anchors(context: EstimatorContext, anchor: Anchor) -> None:
    """Refuse an intensity derived from a partition other than the one the residual came from.

    §12.2's residual and this intensity are two readings of one disclosed set. The intensity looks
    its partition up in the context while the residual arrives on the anchor, and under a §13.2
    pseudo-suppression mask the two agree only if the harness rebuilt `EstimatorContext.partitions`
    from the same mask it handed the anchor. Recomputing the residual is what makes that a refusal
    rather than a hope: same partition, same residual, by construction.

    SCOPE. This witnesses the DISCLOSED side, which is the side the intensity reads. It says
    nothing about the missing set, deliberately -- `allocate.check_domain` already refuses a weight
    vector whose domain is not the missing set, and asserting it here as well would refuse the
    hand-built anchors that several unit tests use to drive one cell at a time.
    """
    partition = context.partitions[anchor.reference_month]
    implied = national_residual(
        context.monthly, partition, reference_month=anchor.reference_month
    )
    if not math.isclose(implied.residual, anchor.residual, rel_tol=1e-9, abs_tol=1e-9):
        raise ConceptViolationError(
            f"{anchor.reference_month}: the context's partition implies a residual of "
            f"{implied.residual:.6g} but the anchor carries {anchor.residual:.6g}. The intensity "
            "that scales the fallback arm and the residual that arm is allocated against must "
            "come from one partition, or a mask moves one without moving the other and every "
            "value stays positive while the month still sums to the residual"
        )
```

and call it as the first statement of `disclosed_intensity`:

```python
def disclosed_intensity(context: EstimatorContext, anchor: Anchor) -> float | None:
    """Published employees per establishment across this month's disclosed cells.

    §10.3's and §10.6's declared fallback intensity: a published ratio of two published sums. It
    is preferred over the residual-implied ratio (R_t / sum A over the missing set) because it
    stays positive and well defined when R_t is 0 -- a degenerate case §12.3 requires to succeed.
    `None` when the disclosed set carries no establishments, which leaves the caller to fall back
    to an empty arm rather than divide by zero.

    Refuses outright when the context's partition is not the one the anchor's residual came from
    (R-COMP-8).
    """
    _assert_the_partition_is_the_anchors(context, anchor)
    disclosed = context.partitions[anchor.reference_month].disclosed
    ...
```

- [ ] **Step 4: Repair the two fixtures the refusal exposes**

Exactly two existing tests build an anchor by hand *and* reach the disclosed fallback. Both are in
`tests/unit/test_baselines_historical.py`. Every other hand-built anchor in the suite is covered by
its own arm, so the lazy construction in `compose_with_declared_fallback` never resolves an
intensity for it. Do not widen this repair.

**4a.** `test_a_state_with_no_observed_history_takes_the_declared_fallback` (around line 96). The
fixture's 2024-03 month has national 100 and one disclosed cell — state 01 at 43 over 4 — so the
partition implies a residual of 57 while the anchor was typed as 50.0. Build the anchor from the
partition instead. Add `national_residual` to that file's anchor import:

```python
from logging_employment.reconcile.anchor import (
    Anchor,
    Partition,
    national_residual,
    observed_partition,
)
```

and replace the body:

```python
@pytest.mark.parametrize("cls", ALL_FIVE)
def test_a_state_with_no_observed_history_takes_the_declared_fallback(
    cls, make_monthly, appendix_a_config
) -> None:
    """Six D1 states are in this position for all 96 months, so the rung is never idle.

    The fallback arm is in EMPLOYEES, not establishments: A scaled by the month's disclosed
    employees-per-establishment, so it can be merged with an own arm that is a predicted
    employment level. Derived from the fixture below rather than typed: at 2024-03 the only
    disclosed cell is state 01 with 43 employees over 4 establishments.

    The anchor comes from `national_residual` rather than being typed, because R-COMP-8 requires
    the intensity and the residual to come from one partition and refuses them when they do not.
    """
    monthly = _history(make_monthly)
    partitions = observed_partition(monthly)
    anchor = national_residual(monthly, partitions["2024-03"], reference_month="2024-03")
    assert anchor.missing_cells == ("02",)
    out = cls().weights(_context(monthly, appendix_a_config), anchor)
    assert out.basis["02"] == FALLBACK
    assert out.values["02"] == pytest.approx(6.0 * (43 / 4))
```

**4b.** The masked-partition test around line 275 (the one whose last two statements are
`out = LastObservedShare().weights(context, Anchor("2024-03", 400.0, ("01",), ...))` and
`assert out.basis["01"] == FALLBACK`). Its `masked` dict masks February but leaves 2024-03 as the
unmasked partition, in which state 01 is disclosed and the missing set is empty — so the typed
400.0 disagrees with the implied 0. Mask 2024-03 too, which is what the test's own premise
describes, and derive the anchor:

```python
    states = monthly.filter(pl.col("area_type") == "state")
    feb = states.filter(pl.col("reference_month") == "2024-02")
    march = states.filter(pl.col("reference_month") == "2024-03")
    masked = {
        "2024-02": Partition(
            disclosed=feb.filter(pl.col("state_fips") == "02"),
            missing=feb.filter(pl.col("state_fips") == "01"),
        ),
        # The mask holds state 01 out in the anchor month too. Leaving 2024-03 unmasked made the
        # fixture describe a mask it did not apply: the anchor's residual was typed while the
        # partition said the missing set was empty, which R-COMP-8 now refuses.
        "2024-03": Partition(
            disclosed=march.filter(pl.col("state_fips") == "02"),
            missing=march.filter(pl.col("state_fips") == "01"),
        ),
    }
```

and replace the two closing statements with:

```python
    anchor = national_residual(monthly, masked["2024-03"], reference_month="2024-03")
    assert anchor.residual == pytest.approx(400.0)
    out = LastObservedShare().weights(context, anchor)
    assert out.basis["01"] == FALLBACK
```

The `history["share"].to_list() == []` assertion above is unaffected: `observed_share_history`
reads months in `[floor, before)` and excludes the anchor month itself.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, 1167 passed (1164 + the three tests appended in Step 1). The two repaired tests in
Step 4 change no count: `test_a_state_with_no_observed_history_takes_the_declared_fallback` stays
parametrized over the same five variants.

- [ ] **Step 6: Lint and commit**

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment/baselines/fallback.py tests/unit
git commit -m "feat(baselines): refuse an intensity from a partition the anchor did not use (R-COMP-8)"
```

---

### Task 5: `decline_kind`, and the golden it re-pins

Satisfies R-COMP-9, R-COMP-11, and tests T-3 and T-6. `runner.py` funnels three different
situations into one row shape, so nothing downstream can tell an estimator's considered refusal
from a data problem without reading prose — and §13's scoreboard defines no decline metric, so a
data bug can make a baseline's WAPE look *better* than a correct implementation's.

**Files:**
- Modify: `src/logging_employment/contracts.py:219` (after `ANCHOR_BASES`), `:231-235`, `:321-336`
- Modify: `src/logging_employment/baselines/interfaces.py` (`Decline`, `compose`)
- Modify: `src/logging_employment/baselines/intensity.py` (two `Decline`s)
- Modify: `src/logging_employment/baselines/harvest.py` (one `Decline`)
- Modify: `src/logging_employment/baselines/runner.py:118-198, 201-227`
- Modify: `tests/unit/test_baselines_harvest.py`, `tests/unit/test_baselines_intensity.py`
- Test: `tests/unit/test_baselines_runner.py` (append T-3)
- Regenerate: `tests/fixtures/baselines/baseline_results_golden.parquet`

**Interfaces:**
- Consumes: `compose` from Task 1.
- Produces:
  - `contracts.DECLINE_KINDS: tuple[str, ...] = ("by_design", "data_gap", "reconciliation_failure")`
  - `BASELINE_RESULT_SCHEMA` gains `"decline_kind": pl.String` immediately after `decline_reason`.
  - `Decline(reason: str, kind: str)` — `kind` is required and validated against `DECLINE_KINDS`.
  - `runner._decline_rows(estimator_id, anchor, reason, constraint_set_hash, ids, *, kind: str)`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_baselines_runner.py` (T-3 — one test per kind, each driving a different
`runner.py` call site):

```python
def test_an_estimators_own_refusal_is_recorded_as_by_design(
    harmonized_toy, appendix_a_config
) -> None:
    """T-3, call site 2: `estimator.weights` returned a `Decline`.

    §10.5's harvest baseline is the archetype. Its months are absent from the scored set for a
    reason no amount of better data changes, which is what separates it from the other two kinds.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    harvest = results.filter(pl.col("estimator_id") == "harvest_proportional")
    assert set(harvest["reconciliation_status"].unique().to_list()) == {"declined"}
    assert set(harvest["decline_kind"].unique().to_list()) == {"by_design"}


def test_a_missing_input_is_recorded_as_a_data_gap(harmonized_toy, appendix_a_config) -> None:
    """T-3, call site 1: `compose` raised because the fallback could not cover a cell.

    The kind is asserted, not the prose. A scoreboard that grouped on `decline_reason` would be
    grouping on a sentence that names a state fips.
    """
    jan = pl.col("reference_month") == "2023-01"
    broken = harmonized_toy.qcew_monthly.with_columns(
        pl.when(jan & (pl.col("state_fips") == "04"))
        .then(0)
        .when(jan & (pl.col("area_type") == "national"))
        .then(pl.col("qtrly_establishments") - 5)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    data = HarmonizedData(
        broken,
        harmonized_toy.qcew_national_size,
        harmonized_toy.cbp_state_size,
        harmonized_toy.bridge,
    )
    results, _ = run_baselines(data, appendix_a_config)
    declined = results.filter(
        (pl.col("reference_month") == "2023-01") & (pl.col("reconciliation_status") == "declined")
    )
    assert "data_gap" in declined["decline_kind"].unique().to_list()


def test_a_reconciliation_refusal_is_recorded_as_a_reconciliation_failure(
    harmonized_toy, appendix_a_config
) -> None:
    """T-3, call site 3: `allocate` refused the weight vector the estimator produced.

    Driven through a stub estimator rather than through data, because the shipped estimators reach
    `allocate` only with a domain-complete vector -- which is the property that makes this the
    third kind and not the second.
    """

    class _WrongDomain:
        """A stub that weights one cell too few, which is what `allocate` refuses by name."""

        estimator_id = "equal_residual"
        fallback_intensity = None

        def weights(self, context, anchor):
            """A vector missing the last cell, so `check_domain` refuses it."""
            return Weights(
                values=dict.fromkeys(anchor.missing_cells[:-1], 1.0),
                basis=dict.fromkeys(anchor.missing_cells[:-1], "own_estimator"),
            )

    with mock.patch.object(runner, "REGISTRY", (_WrongDomain(),)):
        results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert set(results["decline_kind"].unique().to_list()) == {"reconciliation_failure"}


def test_a_reconciled_row_carries_no_decline_kind(harmonized_toy, appendix_a_config) -> None:
    """The column describes a decline; a row that produced an estimate has none to describe."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert ran["decline_kind"].null_count() == ran.height


def test_no_declined_row_reaches_the_output_without_a_kind(
    harmonized_toy, appendix_a_config
) -> None:
    """R-COMP-9's exit criterion, over every estimator the registry ships."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    declined = results.filter(pl.col("reconciliation_status") == "declined")
    assert declined.height > 0
    assert declined["decline_kind"].null_count() == 0
```

That file needs these added to its imports:

```python
from unittest import mock

from logging_employment.baselines import runner
from logging_employment.reconcile.allocate import Weights
```

(`run_baselines`, `REGISTRY`, `HarmonizedData` and `pl` are already imported there.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_runner.py -q`
Expected: FAIL — `ColumnNotFoundError: decline_kind`.

- [ ] **Step 3: Declare the closed set and the column**

In `src/logging_employment/contracts.py`, add after `ANCHOR_BASES` (line 219):

```python
# Why a declining estimator declined, as three groupable values rather than prose. §13.5-13.8
# score estimates against truth and define no decline metric, so an estimator whose months drop
# out of the scored set drops out non-randomly -- and a data bug can make a baseline's WAPE look
# BETTER than a correct implementation's. `decline_reason` stays free text beside this; the kind
# is what a scoreboard groups on.
DECLINE_KINDS: tuple[str, ...] = ("by_design", "data_gap", "reconciliation_failure")
```

Add it to `assert_declared_provenance`'s loop:

```python
    for column, allowed in (
        ("reconciliation_status", RECONCILIATION_STATUSES),
        ("weight_basis", WEIGHT_BASES),
        ("anchor_basis", ANCHOR_BASES),
        ("decline_kind", DECLINE_KINDS),
    ):
```

Add the column to `BASELINE_RESULT_SCHEMA`, immediately after `decline_reason` — the module
docstring notes that field order is load-bearing for the fingerprint, and R-COMP-9 places this
column beside `decline_reason`:

```python
    "decline_reason": pl.String,
    "decline_kind": pl.String,
    "residual": pl.Float64,
```

- [ ] **Step 4: Make `Decline` carry a kind**

In `src/logging_employment/baselines/interfaces.py`, import the closed set:

```python
from ..contracts import DECLINE_KINDS
```

and replace the `Decline` dataclass:

```python
@dataclass(frozen=True)
class Decline:
    """A baseline's refusal to run for a month, carrying the reason AND the kind of refusal.

    `reason` is free text a reader acts on. `kind` is the closed set a scoreboard groups on: a
    month that leaves the scored set because an input was missing biases a point-metric comparison
    in a way an estimator's considered refusal does not, and prose cannot be grouped. The kind is
    required rather than defaulted, so no code path can produce a decline without one.
    """

    reason: str
    kind: str

    def __post_init__(self) -> None:
        """Refuse a decline whose kind is outside the declared set."""
        if self.kind not in DECLINE_KINDS:
            raise ConceptViolationError(
                f"decline_kind {self.kind!r} is outside the declared set {list(DECLINE_KINDS)}; "
                "every decline reaches baseline_results.parquet and §13's scoreboard groups on it"
            )
```

And give `compose`'s config decline its kind:

```python
    if not allowed:
        return Decline(
            reason=(
                "baselines.allow_declared_composite is false and this estimator has no own weight "
                f"for {sorted(gaps)}"
            ),
            # `by_design`, not `data_gap`: the fallback arm exists and covers these cells, and the
            # run is configured to refuse composing with it. Nothing about the inputs is absent.
            kind="by_design",
        )
```

- [ ] **Step 5: Give the other three declines their kinds**

In `src/logging_employment/baselines/harvest.py`:

```python
        return Decline(
            reason=(
                "no harvest-origin volume and no latent harvest factor are available: Appendix A "
                "ships tpo.enabled=false and fia.enabled=false and the config declares neither "
                "source. Stage 7 supplies the harvest factor; until then §10.5 declines rather "
                "than allocating on a substitute proxy that would be scored as if it were this "
                "baseline"
            ),
            # The archetype of `by_design`: §10.5 refuses, and no vintage of the inputs it does
            # have would change that. Stage 7 replaces the refusal, not the data.
            kind="by_design",
        )
```

In `src/logging_employment/baselines/intensity.py`, both declines are absent inputs:

```python
        if reference_year not in available:
            return Decline(
                reason=(
                    f"CBP publishes no reference year {reference_year}; §10.4's estimator is a "
                    "year-specific March intensity, and carrying an earlier year forward would be "
                    "an assumption this baseline does not make"
                ),
                kind="data_gap",
            )
```

```python
        if national is None:
            return Decline(
                reason=(
                    f"CBP reference year {reference_year} publishes no usable establishment "
                    "count, so neither a state intensity nor its national limit exists"
                ),
                kind="data_gap",
            )
```

- [ ] **Step 6: Write the kind at all three runner call sites**

In `src/logging_employment/baselines/runner.py`, give `_decline_rows` a required keyword and emit
the column:

```python
def _decline_rows(
    estimator_id: str,
    anchor,
    reason: str,
    constraint_set_hash: str | None,
    ids: dict[str, str],
    *,
    kind: str,
) -> list[dict[str, object]]:
    """One visible row per cell a declining estimator could not weight, carrying the kind.

    `kind` is keyword-only and has no default: the three call sites below are three different
    situations, and the whole point of the column is that a reader can tell them apart without
    parsing `reason`.
    """
    return [
        {
            "estimator_id": estimator_id,
            "cell_id": ids[cell],
            "state_fips": cell,
            "reference_month": anchor.reference_month,
            "raw_weight": None,
            "estimate": None,
            "estimate_integer": None,
            "weight_basis": "none",
            "anchor_basis": anchor.anchor_basis,
            "reconciliation_status": "declined",
            "decline_reason": reason,
            "decline_kind": kind,
            "residual": anchor.residual,
            "missing_set_size": len(anchor.missing_cells),
            "constraint_set_hash": constraint_set_hash,
        }
        for cell in anchor.missing_cells
    ]
```

Then the three sites, in order:

```python
            except WeightDomainError as exc:
                # An estimator whose fallback cannot cover a cell raises rather than returning a
                # `Decline`, and `compose`'s docstring is right that the two are different things:
                # one is a data problem, the other a considered refusal. But the plan's "decline,
                # never fabricate" rule is about the OUTPUT, and it requires a visible row either
                # way — an absent row is indistinguishable from a bug. So the raise is preserved
                # inside `compose`, and here it becomes a `declined` row carrying the exception's
                # own words, which name it as the data problem it is. Without this, one cell with
                # no usable establishment count kills all ten estimators across every month.
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        str(exc),
                        constraint_set_hash,
                        ids,
                        kind="data_gap",
                    )
                )
                continue
            if isinstance(outcome, Decline):
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        outcome.reason,
                        constraint_set_hash,
                        ids,
                        kind=outcome.kind,
                    )
                )
                continue
```

```python
            except WeightDomainError as exc:
                # A cell the estimator could not weight is a DECLINE, per the plan's "decline,
                # never fabricate" rule — not a dead run. `qtrly_establishments` is currently >= 1
                # on every suppressed cell, but that is a measurement a revision can move, and one
                # such cell would otherwise abort all ten estimators across all months.
                # `UniverseClosureError` stays a whole-run halt: that one really is global.
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        str(exc),
                        constraint_set_hash,
                        ids,
                        kind="reconciliation_failure",
                    )
                )
                continue
```

And add the null to the reconciled row dict, beside `decline_reason`:

```python
                        "decline_reason": None,
                        "decline_kind": None,
```

Finally, extend the module docstring's `EVERY DECLINE IS A ROW` paragraph:

```
EVERY DECLINE IS A ROW, AND EVERY ROW NAMES ITS KIND. A baseline that cannot run for a month writes
a row with a null estimate and a populated `decline_reason`, never no row at all: an absent row is
indistinguishable from a bug, and §17.4 row 4's "run every baseline on a small frozen fixture" is
satisfied by a clean decline only if the decline is visible in the output. The three situations
below -- a data problem, an estimator's considered refusal, and a reconciliation failure -- used to
produce one indistinguishable row shape. `decline_kind` separates them, because §13.5-13.8 score
against truth and define no decline metric: an estimator whose months drop out of the scored set
drops out non-randomly, and a data bug can make a baseline's WAPE look better than a correct
implementation's.
```

- [ ] **Step 7: Update the two unit tests that construct or assert a `Decline`**

`tests/unit/test_baselines_harvest.py:34-37` and `:65-68` assert `isinstance(out, Decline)`; add
the kind assertion beside each:

```python
    assert isinstance(out, Decline)
    assert out.kind == "by_design"
```

`tests/unit/test_baselines_intensity.py:110`, likewise:

```python
    assert isinstance(out, Decline)
    assert out.kind == "data_gap"
```

- [ ] **Step 8: Run the suite and confirm exactly the golden fails**

Run: `uv run pytest -q`
Expected: FAIL — one failure, `test_the_baseline_output_matches_its_golden_fixture`, because the
frame now carries a column the pinned file does not. Every other test passes. If anything else
fails, stop and fix it before regenerating: a golden re-pinned over an unrelated failure records
the bug.

- [ ] **Step 9: Regenerate the golden (T-6)**

Only `baseline_results_golden.parquet` changes; `anchor_audit_golden.parquet` is untouched.

```bash
uv run python - <<'PY'
from pathlib import Path

from logging_employment.baselines.runner import run_baselines
from logging_employment.build import write_parquet_deterministic
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData

repo = Path.cwd()
fixtures = repo / "tests" / "fixtures" / "baselines"
results, _ = run_baselines(HarmonizedData.load(fixtures), load_config(repo / "config.yaml"))
digest = write_parquet_deterministic(results, fixtures / "baseline_results_golden.parquet")
print("baseline_results_golden", digest)
print("columns", results.columns)
PY
```

Expected: prints a sha256 and a column list ending `..., 'decline_reason', 'decline_kind',
'residual', 'missing_set_size', 'constraint_set_hash']`.

- [ ] **Step 10: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS, 1172 passed (1167 + the five tests appended in Step 1).

- [ ] **Step 11: Lint and commit**

The §17.6 reason goes in this commit message, not only in the spec — that is what T-6 asks for.

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment tests/unit tests/fixtures/baselines/baseline_results_golden.parquet
git commit -m "$(cat <<'MSG'
feat(baselines): give every decline a kind (R-COMP-9, R-COMP-11)

`runner.py` funnelled a data problem, an estimator's considered refusal and a
reconciliation failure into one row shape, so nothing downstream could tell them
apart without parsing `decline_reason`. §13.5-13.8 score estimates against truth
and define no decline metric, so an estimator whose months drop out of the scored
set drops out non-randomly -- and a data bug can make a baseline's WAPE look
better than a correct implementation's.

§17.6 golden update, with its reason: `BASELINE_RESULT_SCHEMA` gains
`decline_kind` beside `decline_reason`, which is a schema fingerprint change, so
`tests/fixtures/baselines/baseline_results_golden.parquet` is regenerated from
the committed fixture. No estimate, weight, basis or residual in the file
changes; the diff is one added column. Reviewer approval required per §17.6.
MSG
)"
```

---

### Task 6: The run manifest declares what it did

The manifest halves of R-COMP-6 and R-COMP-9: the declared intensity per estimator, and the
decline breakdown by kind. Without this the declarations are readable only from source, which is
the thing R-COMP-6 exists to fix.

**Files:**
- Modify: `src/logging_employment/cli.py:239-307`
- Test: `tests/integration/test_baseline_cli.py`

**Interfaces:**
- Consumes: `REGISTRY` and `Estimator.fallback_intensity` from Task 3; `decline_kind` from Task 5.
- Produces: `baseline_manifest.json` gains `fallback_intensity: {estimator_id: str}` and its
  `declines` key becomes `{estimator_id: {decline_kind: count}}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/test_baseline_cli.py`:

```python
def test_the_manifest_declares_each_estimators_fallback_intensity(staged_repo) -> None:
    """R-COMP-6. Two baselines answer "how many employees does an establishment carry"
    differently, and R-COMP-7 keeps it that way — so the choice has to be readable from a run's
    output rather than from source."""
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    declared = manifest["fallback_intensity"]
    assert declared["share_last_observed"] == "disclosed_qcew"
    assert declared["constrained_regression"] == "disclosed_qcew"
    assert declared["cbp_intensity"] == "national_cbp_march"
    # An estimator that composes nothing declares nothing, and is absent rather than null.
    assert "equal_residual" not in declared
    assert "harvest_proportional" not in declared


def test_declines_are_broken_down_by_kind_not_pooled(staged_repo) -> None:
    """R-COMP-9. §13's scoreboard must be able to tell a considered refusal from a data gap:
    pooled, a baseline that drops months for a data reason is indistinguishable from §10.5."""
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    declines = manifest["declines"]
    assert set(declines["harvest_proportional"]) == {"by_design"}
    assert declines["harvest_proportional"]["by_design"] > 0
```

Strengthen the existing `test_declines_are_counted_in_the_manifest` so it does not pass on the old
pooled shape:

```python
def test_declines_are_counted_in_the_manifest(staged_repo) -> None:
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    assert "harvest_proportional" in manifest["declines"]
    assert isinstance(manifest["declines"]["harvest_proportional"], dict)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_baseline_cli.py -q`
Expected: FAIL — `KeyError: 'fallback_intensity'` and `TypeError`/assertion on the pooled int.

- [ ] **Step 3: Write both into the manifest**

In `src/logging_employment/cli.py`, add `REGISTRY` to the `run-baselines` import block:

```python
    from .baselines.runner import (
        REGISTRY,
        preferred_estimator,
        preferred_estimator_by_month,
        run_baselines,
    )
```

(match the block's existing import form; the names above are the ones this command already uses.)

Replace the `declines` comprehension with a nested one and add the declaration map:

```python
    # Nested by kind, not pooled. §13.5-13.8 define no decline metric, so a scoreboard has to be
    # able to separate §10.5's considered refusal from a month an estimator lost to a data gap:
    # pooled, a broken baseline and a benchmark that never runs look identical.
    declines: dict[str, dict[str, int]] = {}
    for row in (
        results.filter(pl.col("reconciliation_status") == "declined")
        .group_by(["estimator_id", "decline_kind"])
        .len()
        .iter_rows(named=True)
    ):
        declines.setdefault(row["estimator_id"], {})[row["decline_kind"]] = row["len"]
    # R-COMP-6: which intensity scaled each estimator's fallback arm, read off the estimators
    # themselves. §10.3 and §10.6 declare the disclosed ratio and §10.4 the national CBP March
    # one, and R-COMP-7 keeps that difference rather than standardising it — so it is reported
    # here, where a reader can check an arm against the name without reading source.
    fallback_intensity = {
        estimator.estimator_id: estimator.fallback_intensity
        for estimator in REGISTRY
        if estimator.fallback_intensity is not None
    }
```

Add the key to the manifest dict, beside `weight_basis_counts` as R-COMP-6 requires:

```python
                "weight_basis_counts": basis_counts,
                "fallback_intensity": fallback_intensity,
                "declines": declines,
```

And update the echo loop for the nested shape:

```python
    for estimator_id, counts in sorted(basis_counts.items()):
        for basis, count in sorted(counts.items()):
            typer.echo(f"{estimator_id} {basis} {count}")
    for estimator_id, kinds in sorted(declines.items()):
        for kind, count in sorted(kinds.items()):
            typer.echo(f"declined {estimator_id} {kind} {count}")
```

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -q`
Expected: PASS, 1174 passed (1172 + the two tests appended in Step 1).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src tests && uv run black --check src tests && uv run interrogate src
git add src/logging_employment/cli.py tests/integration/test_baseline_cli.py
git commit -m "feat(cli): declare the fallback intensity and break declines out by kind"
```

---

### Task 7: Amend `logging-employment-spec.md`

`specs/estimator-composition.md` §4 lists three amendments. This task makes them. R-COMP-10 lands
here and nowhere else — it is a requirement *on Stage 4*, and this spec is sequenced before Stage 4
is planned precisely so the requirement exists before the scoreboard is built.

No test is added for these edits. The one test that reads this file
(`tests/unit/test_classification.py`) parses §3.1 only and is unaffected; a prose-pin test on the
new sections would assert that a sentence exists, not that it is true.

**Files:**
- Modify: `specs/logging-employment-spec.md` — insert §7.13 after §7.12, §10.9 after §10.8, and one
  paragraph at the end of §13.8

**Interfaces:**
- Consumes: the shipped column list from Task 5's `BASELINE_RESULT_SCHEMA`.
- Produces: nothing code-facing.

- [ ] **Step 1: Add §7.13 `baseline_result`**

Insert immediately before the `---` that closes §7 (after §7.12's `release_action` block). The
column list must match `BASELINE_RESULT_SCHEMA`'s order exactly, including `decline_kind` after
`decline_reason`. Only `decline_kind` is enumerated: `weight_basis` and `reconciliation_status` are
this implementation's closed sets, which §7.11 declined to enumerate, and originating them here
would state something this document has not decided.

````markdown
### 7.13 `baseline_result`

One row per estimator, reference month, and missing cell — including the cells a declining
estimator could not weight, which are rows with a null estimate rather than absences.

```text
estimator_id
cell_id
state_fips
reference_month
raw_weight
estimate
estimate_integer
weight_basis
anchor_basis
reconciliation_status
decline_reason
decline_kind
residual
missing_set_size
constraint_set_hash
```

Allowed `decline_kind` values:

```text
by_design
data_gap
reconciliation_failure
```

`decline_reason` is free text for a reader; `decline_kind` is the closed set §13 groups on.
A declining estimator MUST write rows, never omit them: an absent row is indistinguishable from a
bug.
````

- [ ] **Step 2: Add §10.9 "Composition and the fallback arm"**

Insert after §10.8's numbered list and before the `---` that closes §10.

```markdown
### 10.9 Composition and the fallback arm

A baseline MAY compose an **own arm** — the weights its own method produces — with the §10.2
establishment fallback arm, cell by cell, and reconcile the union. §10.8's rank-1 phrasing,
"reconciled CBP/QCEW employee-per-establishment with robust historical adjustment", is this
document's own precedent that a composed estimator is a legitimate baseline rather than a degraded
one.

Composition MUST be visible per cell. Every reconciled cell MUST record which arm produced its
weight, and a run's baseline manifest MUST report the split per estimator. Reporting a composite's
score as a pure estimator's is a validation defect under §13.

Both arms MUST be employees-valued, and the unit MUST be carried structurally — by the type of the
value handed to composition — rather than checked after the fact by comparing the two arms'
magnitudes. Reconciliation normalizes the union of the arms, so arms in different units are decided
entirely by whichever is numerically larger, and the result is positive in every cell and sums
exactly to the residual. A magnitude comparison cannot separate an honest composite from a units
error: the two ranges overlap.

There MUST be exactly one construction that turns §10.2 establishment exposure into an
employees-valued fallback arm. It MUST take the intensity that scales it as an argument; no
estimator may build or scale a fallback arm itself. Each estimator MUST declare which intensity
scales its fallback arm, and that declaration MUST appear in the run's baseline manifest. The
declared intensities need not agree across baselines — §10.4's national CBP March intensity is
exactly its own shrinkage limit as the CBP cell count goes to zero, a derivation §10.3 and §10.6
have no equivalent of — but each estimator's choice MUST be readable from the run output without
reading source.

An intensity derived from the disclosed set MUST come from the same partition the month's residual
was derived from. Under a §13.2 pseudo-suppression mask the two agree only if the harness rebuilds
the estimator's partitions from the same mask it used for the residual, and a disagreement MUST
fail rather than silently scale the fallback off the wrong disclosed set.
```

- [ ] **Step 3: Add the decline-reporting requirement to §13**

Append to the end of §13.8, after the sentence "Reconciled production output requires zero
hard-constraint violations within tolerance." and before `### 13.9`:

```markdown
Every scored comparison in §13.5–13.8 MUST report decline counts by kind, per method and per
holdout regime, and MUST state the denominator it was computed over. A method whose months drop out
of the scored set drops out non-randomly, so an unreported data-driven decline can make a broken
implementation's point and probabilistic metrics look better than a correct one's.
```

- [ ] **Step 4: Verify the three sections landed and the spec still parses**

Run:

```bash
grep -n "^### 7.13\|^### 10.9\|decline counts by kind" specs/logging-employment-spec.md
```

Expected: three lines, in ascending order.

Run: `uv run pytest tests/unit/test_classification.py -q`
Expected: PASS, 3 passed — the §3.1 parser is anchored and is not reached by any of these edits.

- [ ] **Step 5: Commit**

```bash
git add specs/logging-employment-spec.md
git commit -m "spec(baselines): §10.9 composition, §7.13 baseline_result, §13 decline reporting"
```

---

## Exit criteria check

Run these after Task 7, before the Plan Completion Protocol. Each maps to a bullet in
`specs/estimator-composition.md` §7.

- [ ] **A raw establishment fallback arm cannot be constructed or passed to `compose`, demonstrated
  by T-1.**
  Run: `uv run pytest tests/unit/test_baseline_interfaces.py::test_a_raw_dict_cannot_be_passed_as_an_arm -v`
  Expected: PASS.

- [ ] **`MAX_SCALE_RATIO` does not appear in the codebase.**
  Run: `grep -rn "MAX_SCALE_RATIO" src/ tests/`
  Expected: no output.

- [ ] **Exactly one construction converts exposure into employees, and each estimator's choice is
  readable from the run output.**
  Run: `grep -rn "def establishment_fallback\b" src/` → exactly one hit, in
  `src/logging_employment/baselines/fallback.py`.
  Run: `grep -rn "intensity\b" src/logging_employment/baselines/historical.py src/logging_employment/baselines/regression.py`
  → only the `fallback_intensity = DISCLOSED_QCEW` declarations and the import, no arithmetic.
  Run: `uv run pytest tests/integration/test_baseline_cli.py::test_the_manifest_declares_each_estimators_fallback_intensity -v`
  Expected: PASS.

- [ ] **Every declined row carries a `decline_kind`, and no code path produces a decline without
  one.**
  Run: `uv run pytest tests/unit/test_baselines_runner.py -k decline -v`
  Expected: PASS.
  Run: `grep -rn "Decline(" src/` → four sites, each with a `kind=`.

- [ ] **The full suite passes with no new skips.**
  Run: `uv run pytest -q -rs`
  Expected: `1174 passed`, and the skip list is identical to the pre-plan run (the `data/`-gated
  D1 integration tests only, and only when `data/staged` is absent).

- [ ] **The golden's regeneration is accompanied by its documented reason.**
  Run: `git log --format=%B -n 1 -- tests/fixtures/baselines/baseline_results_golden.parquet | head -20`
  Expected: Task 5's message, naming R-COMP-9 and §17.6.

- [ ] **`specs/deferred_items.md` has both composition items ticked.** Done by the Plan Completion
  Protocol, not here: tick `MAX_SCALE_RATIO = 100.0 is an originated tripwire with no spec warrant`
  and `§10.3's fallback scales by the DISCLOSED intensity; §10.4's uses the NATIONAL one` with
  `→ done in plan 9`. Leave `disclosed_intensity reads the partition from the context while the
  residual comes from the anchor` **unticked** — it is scoped to Stage 4 enforcing this in the
  harness, and the roadmap's Stage 4 entry cites it as that stage's own reading. Stage 4's plan
  closes it and should record that this spec supplied the requirement.
