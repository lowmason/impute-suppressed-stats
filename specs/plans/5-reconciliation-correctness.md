# Reconciliation Correctness Batch — Implementation Plan

**Status: COMPLETE (2026-09-05)** — executed via executing-plans; nothing deferred

> **For agentic workers:** REQUIRED SUB-SKILL: **executing-plans** — inline execution was chosen
> at the handoff on 2026-09-05, so run the tasks yourself in plan order rather than dispatching
> subagents. Its stop-and-ask rules and completion chain apply. Steps use checkbox (`- [ ]`)
> syntax for tracking.

> Branch: `reconciliation-correctness`, stacked on `deferred-quickfixes`. The baseline of 1105
> holds only with that branch's four added tests present; against `main` it is 1101.

> Source: `specs/deferred_items.md`, section `## 4-stage3-logging-employment-spec — 2026-09-05`.
> There is no spec for this work — the three deferred items ARE the requirements. On plan
> completion, tick those three items per the Plan Completion Protocol.

**Goal:** Close the three Stage 3 reconciliation defects that are latent on the D1 window and live
in Stage 5/6 — a projection that reports convergence it did not achieve, three provenance enums
that constrain nothing, and three bound-handling gaps in balanced integerization.

**Architecture:** All three are narrow, self-contained fixes inside the existing `reconcile/` and
`baselines/` subpackages. No new modules and no schema changes. Task 1 changes one public
signature (`kl_project`), which is why it goes first and updates its seven call sites in the same
task. Tasks 2 and 3 are additive guards that touch no signature.

**Tech Stack:** Python ≥ 3.14, uv + hatchling, Polars, NumPy, pytest.

---

## Global Constraints

- Python ≥ 3.14 for the package; the PEP 723 scripts under `scripts/audit/` promise ≥ 3.12.
- `line-length = 100` for both `ruff` and `black`; `[tool.black] target-version = ["py312"]`.
- `interrogate` runs at `fail-under = 100` over `src/` — every new function needs a docstring.
- Tests run with `uv run pytest -q`. Nothing in this plan touches the network.
- Determinism is a hard requirement: §16.1 requires every command to be idempotent for identical
  inputs. Do not introduce an unseeded RNG, a set iteration, or a dict-order dependency.
- Baseline before starting: **1105 passed, 0 failed, 0 skipped** on a machine with
  `data/staged/qcew_monthly.parquet` present. Without that file, 10 integration tests skip and the
  count is 1095 passed / 10 skipped — that is environmental, not a regression.

---

## A design decision that changed on evidence — read before Task 1

The deferred item says `kl_project` "should return the achieved violation **or raise**". Raising
was the initial recommendation, because it matches the repo's fail-closed culture. **Measurement
refuted it.** Do not implement a raise.

`projection.py`'s own module docstring states the contract:

> the acceptance test is the one §17.3 states -- violation must never increase -- rather than a
> convergence proof

§17.3's property tests deliberately feed **jointly infeasible** two-margin systems and assert only
that violation does not increase. Measured on the existing test inputs, the achieved violation
exceeds `tolerance=1e-9` in **3 of 25** cases in `test_projection_never_increases_constraint_violation`,
with a worst residual violation of **16.15**. A raise at `violation > tolerance` would therefore
break a spec-mandated property test and contradict the module's stated contract.

A function that explicitly does not promise convergence must **report** non-convergence, not raise
on it. Task 1 returns `(x, violation)`. Callers that DO require convergence — `reconcile_matrix` is
the only one today — keep raising, which they already do.

---

### Task 1: `kl_project` returns the achieved violation

**Files:**
- Modify: `src/logging_employment/reconcile/projection.py:71-108`
- Modify: `src/logging_employment/reconcile/matrix.py:71-89`
- Test: `tests/unit/test_projection.py` (5 call sites unpack; 1 new test)
- Test: `tests/unit/test_reconcile_properties.py:163` (1 call site unpacks)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `kl_project(...) -> tuple[np.ndarray, float]` — the projected vector and the total
  absolute margin violation it achieved. `constraint_violation(x, margins, targets) -> float` is
  unchanged and stays exported.

- [x] **Step 1: Write the failing test**

Append to `tests/unit/test_projection.py`:

```python
def test_an_infeasible_bounded_system_reports_its_violation_rather_than_returning_silently() -> None:
    """The bug this test pins: the loop breaks on step size, not on violation.

    With `upper=[1,1]` and a target of 10, every update is fully clipped, so iteration one moves
    nothing and the step-size break fires immediately. The old signature returned `[1., 1.]` --
    a vector 8.0 away from its margin -- with no signal at all, and `kl_project` is exported, so
    Stage 5 and Stage 6 can call it directly and get that answer.
    """
    out, violation = kl_project(
        np.array([1.0, 1.0]),
        np.array([[1.0, 1.0]]),
        np.array([10.0]),
        lower=np.zeros(2),
        upper=np.ones(2),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=ITERS,
    )
    assert out.tolist() == [1.0, 1.0]
    assert violation == pytest.approx(8.0)
    assert violation == pytest.approx(constraint_violation(out, np.array([[1.0, 1.0]]), np.array([10.0])))
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_projection.py -q -k infeasible_bounded`
Expected: FAIL with `ValueError: too many values to unpack (expected 2)` — `kl_project` still
returns a bare array.

> Deviation: it failed, but not that way. numpy unpacked the 2-element `array([1., 1.])`
> into two scalars without raising, so the test failed on `out.tolist()` instead. A red for
> the right reason, via a different mechanism — and itself a small argument for the tuple,
> since the old signature let a 2-cell unpack look like it worked.

- [x] **Step 3: Change the return type**

In `src/logging_employment/reconcile/projection.py`, replace the signature line and the final
`return x`:

```python
def kl_project(
    seed: np.ndarray,
    margins: np.ndarray,
    targets: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    floor: float,
    tolerance: float,
    max_iterations: int,
) -> tuple[np.ndarray, float]:
    """Project `seed` onto {x : margins @ x == targets, lower <= x <= upper} under I-divergence.

    Returns `(x, violation)`. The loop breaks on STEP SIZE, not on violation, so a fully-clipped
    update exits on iteration one having moved nothing -- with `upper=[1,1]` against a target of
    10 the result is 8.0 away from its margin. That is not a defect in the algorithm: §17.3's
    acceptance criterion is that violation never increases, not that it reaches zero, and the
    property tests feed jointly infeasible systems on purpose. It IS a defect to hand that vector
    back as if it were converged, so the achieved violation is returned alongside it and a caller
    that requires convergence checks it. Raising here instead would break §17.3's property test.

    `targets` is the one argument never coerced through `np.asarray`; the returned violation
    inherits that, which is correct for the ndarray callers this package has and worth knowing
    before passing a list.
    """
```

Then replace the last line of the function:

```python
    return x, constraint_violation(x, margins, targets)
```

- [x] **Step 4: Run the new test to verify it passes**

Run: `uv run pytest tests/unit/test_projection.py -q -k infeasible_bounded`
Expected: PASS.

- [x] **Step 5: Update the five existing call sites in `tests/unit/test_projection.py`**

Each of these five currently binds `out = kl_project(...)`. Change each to `out, _ = kl_project(...)`.
The two call sites inside `pytest.raises` blocks (`test_a_non_indicator_margin_row_is_refused`,
`test_a_negative_coefficient_margin_is_refused_rather_than_escaping_the_bounds`) do NOT bind a
result and must be left alone.

The five to change, by test name:

> Deviation: the new test in Step 1 was renamed to
> `test_an_infeasible_bounded_system_reports_its_violation`. The name as planned made the
> `def` line 101 chars, and black wrapped the return annotation onto its own line.

- `test_projection_reaches_a_single_sum_constraint_exactly`
- `test_projection_never_increases_constraint_violation`
- `test_a_zero_seed_is_floored_rather_than_making_the_objective_undefined`
- `test_projection_respects_finite_upper_bounds`
- `test_projection_output_is_strictly_positive`

- [x] **Step 6: Update the call site in `tests/unit/test_reconcile_properties.py`**

In `test_property_4_projection_never_increases_constraint_violation`, change:

```python
        out = kl_project(
```

to:

```python
        out, _ = kl_project(
```

- [x] **Step 7: Update `reconcile_matrix` to use the returned violation**

In `src/logging_employment/reconcile/matrix.py`, change the call and the post-check. Current:

```python
    flat = kl_project(
        seed.reshape(-1),
        margin_matrix,
        target_vector,
        lower=np.zeros(n_rows * n_cols),
        upper=np.full(n_rows * n_cols, np.inf),
        floor=floor,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )

    achieved = margin_matrix @ flat
    if not np.allclose(achieved, target_vector, rtol=1e-6, atol=max(tolerance, 1e-9)):
        raise IncompatibleMarginError(
            f"reconciliation did not converge to the requested margins: total absolute violation "
            f"{constraint_violation(flat, margin_matrix, target_vector)} after {max_iterations} "
```

Replace with:

```python
    flat, violation = kl_project(
        seed.reshape(-1),
        margin_matrix,
        target_vector,
        lower=np.zeros(n_rows * n_cols),
        upper=np.full(n_rows * n_cols, np.inf),
        floor=floor,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )

    achieved = margin_matrix @ flat
    if not np.allclose(achieved, target_vector, rtol=1e-6, atol=max(tolerance, 1e-9)):
        raise IncompatibleMarginError(
            f"reconciliation did not converge to the requested margins: total absolute violation "
            f"{violation} after {max_iterations} "
```

Leave the rest of the message and the `raise` intact.

Then fix the now-unused import. Line 86 was the **only** use of `constraint_violation` in
`matrix.py` (verified by grep), so replacing it makes the import dead and ruff's default `F` rules
flag it as F401. Change line 29 from:

```python
from .projection import constraint_violation, kl_project
```

to:

```python
from .projection import kl_project
```

This is safe: `reconcile/__init__.py` imports `constraint_violation` from `.projection` directly,
not via `matrix`, so the package export is unaffected.

- [x] **Step 8: Run the full suite**

Run: `uv run pytest -q`
Expected: `1106 passed` (baseline 1105 + the one new test), 0 failed.

- [x] **Step 9: Commit**

```bash
git add src/logging_employment/reconcile/projection.py \
        src/logging_employment/reconcile/matrix.py \
        tests/unit/test_projection.py \
        tests/unit/test_reconcile_properties.py
git commit -m "fix(reconcile): return kl_project's achieved violation instead of implying convergence

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: enforce the three provenance enums

**Files:**
- Modify: `src/logging_employment/contracts.py` (import line 17; new function after `ANCHOR_BASES`)
- Modify: `src/logging_employment/baselines/runner.py:196`
- Test: `tests/unit/test_baselines_runner.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `assert_declared_provenance(frame: pl.DataFrame) -> None` in `contracts.py`, raising
  `ConceptViolationError` when `reconciliation_status`, `weight_basis`, or `anchor_basis` carries a
  value outside its declared tuple.

**Why in `contracts.py` and not `runner.py`:** the enums are declared there and the defect is that
declaration and enforcement live apart. Keeping the check beside the tuples means a later stage
that adds a value cannot forget the guard. `contracts.py` already imports from `.errors`
(`SchemaMismatchError` at line 17), so there is no new import cycle.

**Guarding `run_baselines`' return closes the whole write path — verified, not assumed.**
`runner.py:196` is the ONLY place in `src/` that constructs a `BASELINE_RESULT_SCHEMA` frame
(`grep -rn "schema=BASELINE_RESULT_SCHEMA" src/` returns exactly that one line). `cli.py:252`
binds `results, audit = run_baselines(...)` and writes `results` unmodified at `cli.py:259`; the
`reconcile` command at `cli.py:330` READS that parquet rather than building one. So there is no
second constructor to guard and no unguarded write path left behind.

**The guard passes on real data — verified against the shipped D1 run.** All 12,270 rows of
`runs/320caf9c8934/baseline_results/baseline_results.parquet` carry only declared values:
`reconciliation_status` ∈ {anchored_and_reconciled, declined}, `weight_basis` ∈
{establishment_fallback, none, own_estimator}, `anchor_basis` = {declared_national_total}. Step 6
will not fail on the integration test.

- [x] **Step 1: Write the failing test**

Append to `tests/unit/test_baselines_runner.py`:

```python
def test_a_typo_in_a_provenance_column_is_refused_rather_than_persisted() -> None:
    """The three enums were declared and enforced nothing.

    `BASELINE_RESULT_SCHEMA` checks dtypes only, so `pl.String` accepted any string: a typo in
    `weight_basis` -- which `run_baselines` copies from an estimator's own `outcome.basis` --
    reached `baseline_results.parquet` and passed every test in the suite.
    """
    from logging_employment.contracts import BASELINE_RESULT_SCHEMA, assert_declared_provenance
    from logging_employment.errors import ConceptViolationError

    row = {name: None for name in BASELINE_RESULT_SCHEMA}
    row.update(
        {
            "estimator_id": "x",
            "cell_id": "c",
            "state_fips": "01",
            "reference_month": "2017-01",
            "weight_basis": "own_estimator",
            "anchor_basis": "declared_national_total",
            "reconciliation_status": "anchored_and_reconciled",
        }
    )
    assert_declared_provenance(pl.DataFrame([row], schema=BASELINE_RESULT_SCHEMA)) is None

    for column, typo in (
        ("weight_basis", "own_estimatorr"),
        ("anchor_basis", "declared_national_totl"),
        ("reconciliation_status", "anchored_and_reconcild"),
    ):
        bad = dict(row)
        bad[column] = typo
        with pytest.raises(ConceptViolationError, match=column):
            assert_declared_provenance(pl.DataFrame([bad], schema=BASELINE_RESULT_SCHEMA))
```

If `tests/unit/test_baselines_runner.py` does not already import `polars as pl` and `pytest`, add
those imports at the top of the file.

> Deviation: `pl` and `pytest` were already imported. `assert_declared_provenance` and
> `ConceptViolationError` were added to the module-level imports rather than imported inside
> the test body, avoiding a redundant local re-import of `BASELINE_RESULT_SCHEMA`.
> A second test was also added — `test_a_null_provenance_value_is_permitted_because_a_declining_row_has_none`
> — pinning that nulls stay legal, so a later tightening cannot make declines unrepresentable.
> That makes the count after Task 2 **1108**, not the 1107 the plan predicted.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_baselines_runner.py -q -k typo_in_a_provenance`
Expected: FAIL with `ImportError: cannot import name 'assert_declared_provenance'`.

- [x] **Step 3: Add the guard to `contracts.py`**

Change the import on line 17 from:

```python
from .errors import SchemaMismatchError
```

to:

```python
from .errors import ConceptViolationError, SchemaMismatchError
```

Then add this function immediately after the `ANCHOR_BASES` declaration:

```python
def assert_declared_provenance(frame: pl.DataFrame) -> None:
    """Refuse a provenance value outside its declared tuple.

    The three tuples above are the closed sets a baseline row's provenance may draw from, but
    `BASELINE_RESULT_SCHEMA` checks dtypes only -- `pl.String` accepts any string. `weight_basis`
    is the live exposure: `run_baselines` copies it from an estimator's own `outcome.basis`, so a
    third-party estimator's typo reached `baseline_results.parquet` and passed every test. Nulls
    are permitted: a declining row carries no estimate and no weight to describe.
    """
    for column, allowed in (
        ("reconciliation_status", RECONCILIATION_STATUSES),
        ("weight_basis", WEIGHT_BASES),
        ("anchor_basis", ANCHOR_BASES),
    ):
        if column not in frame.columns:
            continue
        seen = set(frame[column].drop_nulls().to_list())
        undeclared = sorted(seen - set(allowed))
        if undeclared:
            raise ConceptViolationError(
                f"{column} carries undeclared value(s) {undeclared}; the declared set is "
                f"{list(allowed)}. A value outside it reaches baseline_results.parquet and every "
                f"downstream consumer reads it as provenance."
            )
```

- [x] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_baselines_runner.py -q -k typo_in_a_provenance`
Expected: PASS.

- [x] **Step 5: Call the guard from `run_baselines`**

In `src/logging_employment/baselines/runner.py`, change the import on line 25 from:

```python
from ..contracts import BASELINE_RESULT_SCHEMA, HarmonizedData
```

to:

```python
from ..contracts import BASELINE_RESULT_SCHEMA, HarmonizedData, assert_declared_provenance
```

Then replace the return statement at line 196:

```python
    return pl.DataFrame(rows, schema=BASELINE_RESULT_SCHEMA), audit
```

with:

```python
    results = pl.DataFrame(rows, schema=BASELINE_RESULT_SCHEMA)
    assert_declared_provenance(results)
    return results, audit
```

- [x] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: `1107 passed`, 0 failed. In particular `tests/integration/test_d1_baselines.py` must
still pass — it runs `run_baselines` over the real D1 window, so it proves every value the
shipped estimators actually emit is inside the declared sets.

- [x] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py \
        src/logging_employment/baselines/runner.py \
        tests/unit/test_baselines_runner.py
git commit -m "fix(contracts): enforce the three provenance enums instead of only declaring them

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `integerize` bound handling

**Files:**
- Modify: `src/logging_employment/reconcile/integerize.py:42-60`
- Test: `tests/unit/test_integerize.py`

**Interfaces:**
- Consumes: nothing from Tasks 1 or 2.
- Produces: `integerize` keeps its signature
  `integerize(values, total, *, lower=None, upper=None) -> dict[str, int]`. It now raises
  `ValueError` on a contradictory bound pair, ignores bounds for cells absent from `values`, and
  orders by the remainder above the EFFECTIVE floor.

**The three gaps, each with its measured reproduction.** Do not take these on faith — every one
was run against the shipped implementation:

| Gap | Call | Shipped result | Correct result |
|---|---|---|---|
| A. no `lower <= upper` check | `integerize({"a": 4.0}, 3, lower={"a": 5}, upper={"a": 3})` | `{'a': 3}` — silently below its lower bound of 5 | raise |
| B. cap loop iterates `upper` | `integerize({"a": 1.0}, 1, upper={"a": None, "ghost": -1})` | `{'a': 2, 'ghost': -1}` — phantom cell, and `a` is wrong | `{'a': 1}` |
| C. raw fractional ordering | `integerize({"a": 0.9, "b": 0.8}, 3, lower={"a": 2})` | `{'a': 3, 'b': 0}` | `{'a': 2, 'b': 1}` |

**Note on gap B:** the deferred item says "a cap for an absent cell injects a phantom entry". That
is true only for a **negative** cap. With `cap=0` the guard `floors.get(cell, 0) > cap` is `0 > 0`,
which is false, so no entry appears. The fix is the same either way — iterate the cells that have
values — but write the test for the negative cap, because that is the reachable case.

- [x] **Step 1: Write the three failing tests**

> Deviation: the first test was renamed to `test_a_contradictory_bound_pair_is_refused`;
> the planned name made the `def` line 103 chars. The other two kept their names.

Append to `tests/unit/test_integerize.py`:

```python
def test_a_contradictory_bound_pair_is_refused_rather_than_silently_breaking_the_lower_bound() -> None:
    """`floors` took the lower bound, then the cap loop overwrote it with the upper bound.

    Nothing compared the two, so `lower=5, upper=3` returned 3 -- below a bound the caller
    declared. D1 has `lower=0, upper=None` throughout, so this is latent here and live in
    Stage 6, which supplies real class bands.
    """
    with pytest.raises(ValueError, match="lower bound"):
        integerize({"a": 4.0}, 3, lower={"a": 5}, upper={"a": 3})


def test_a_cap_for_a_cell_with_no_value_does_not_inject_a_phantom_entry() -> None:
    """The cap loop iterated `upper`, not `values`, so it could create a cell out of nothing.

    A negative cap made `floors.get(cell, 0) > cap` true for a cell that was never passed in.
    That entry lowered `base`, which raised `remaining`, so the surviving real cell also came
    back wrong: `{'a': 2, 'ghost': -1}` for a total of 1.
    """
    assert integerize({"a": 1.0}, 1, upper={"a": None, "ghost": -1}) == {"a": 1}


def test_the_remainder_order_is_taken_above_the_effective_floor_not_the_raw_value() -> None:
    """Largest-remainder is only largest-remainder if the remainder is measured from the floor used.

    `a`'s floor is raised to its lower bound of 2, which already consumes its 0.9 fraction, so it
    has no claim on the spare unit -- but the raw fractional part still sorted it first and it
    took the unit anyway, leaving `b` at 0 despite a 0.8 remainder.
    """
    assert integerize({"a": 0.9, "b": 0.8}, 3, lower={"a": 2}) == {"a": 2, "b": 1}
```

- [x] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/unit/test_integerize.py -q -k "contradictory or phantom or effective_floor"`
Expected: 3 failed —
`DID NOT RAISE`; `assert {'a': 2, 'ghost': -1} == {'a': 1}`; `assert {'a': 3, 'b': 0} == {'a': 2, 'b': 1}`.

- [x] **Step 3: Rewrite the floor and ordering block**

In `src/logging_employment/reconcile/integerize.py`, replace lines 42-60 — everything from
`floors = {...}` through the close of the `order = sorted(...)` call. Current:

```python
    floors = {cell: max(math.floor(value), lower.get(cell, 0)) for cell, value in values.items()}
    for cell, cap in upper.items():
        if cap is not None and floors.get(cell, 0) > cap:
            floors[cell] = int(cap)

    base = sum(floors.values())
    if base > total:
        raise ValueError(
            f"summed integer lower bounds {base} exceed the required total {total}; "
            "§12.6 cannot round into an infeasible margin"
        )

    remaining = total - base
    # Ties break by cell_id ascending. Sorting on (-fraction, cell) makes the whole order total,
    # so the same input yields the same output on every run and every platform.
    order = sorted(
        values,
        key=lambda cell: (-(values[cell] - math.floor(values[cell])), cell),
    )
```

Replace with:

```python
    # Bounds are read per CELL THAT HAS A VALUE, never by iterating `upper`. Iterating the bound
    # dict let a cap for an absent cell create an entry -- with a negative cap, `floors.get(cell,
    # 0) > cap` is true for a cell that was never passed in -- and that phantom entry lowered
    # `base`, so the real cells came back wrong too. A bounds dict covering a superset of the
    # cells being integerized is a legitimate call shape; the extra keys are simply not this
    # call's business.
    for cell in values:
        floor_bound = lower.get(cell, 0)
        cap = upper.get(cell)
        if cap is not None and floor_bound > cap:
            raise ValueError(
                f"cell {cell!r} has lower bound {floor_bound} above its upper bound {cap}; "
                "§12.6 cannot round into a contradictory pair, and clamping to the cap would "
                "silently return a value below the lower bound the caller declared"
            )

    floors = {}
    for cell, value in values.items():
        seat = max(math.floor(value), lower.get(cell, 0))
        cap = upper.get(cell)
        floors[cell] = int(cap) if cap is not None and seat > cap else seat

    base = sum(floors.values())
    if base > total:
        raise ValueError(
            f"summed integer lower bounds {base} exceed the required total {total}; "
            "§12.6 cannot round into an infeasible margin"
        )

    remaining = total - base
    # The remainder is measured from the floor ACTUALLY USED, not from `math.floor(value)`. Once
    # a floor has been raised by `lower` or lowered by `upper`, the raw fractional part is no
    # longer the cell's claim on the spare units: a cell whose floor was raised past its own
    # value has a negative remainder and correctly sorts last. Ties break by cell_id ascending,
    # so the whole order is total and the same input yields the same output on every platform.
    order = sorted(
        values,
        key=lambda cell: (-(values[cell] - floors[cell]), cell),
    )
```

- [x] **Step 4: Run the three tests to verify they pass**

Run: `uv run pytest tests/unit/test_integerize.py -q -k "contradictory or phantom or effective_floor"`
Expected: 3 passed.

- [x] **Step 5: Run the whole integerize and property suites**

Run: `uv run pytest tests/unit/test_integerize.py tests/unit/test_reconcile_properties.py -q`
Expected: all pass. §17.3's property 6 ("integerization preserves required totals") is the one that
would catch a regression in the ordering change — the sum must still equal `total` exactly.

- [x] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: `1110 passed`, 0 failed. (Actual: 1111 — see the deviation.)

> Deviation: **1111 passed** — one more than planned, from the extra null-permissiveness
> test added in Task 2.

- [x] **Step 7: Update the module docstring**

`integerize.py`'s docstring explains the tie-break and the placement budget but not the bound
handling. Add this paragraph after the `THE TIE-BREAK MUST BE DETERMINISTIC` paragraph:

```
BOUNDS ARE READ PER CELL THAT HAS A VALUE. Iterating the `upper` dict instead let a cap for a cell
with no value create an entry, which lowered `base` and corrupted the real cells' allocation; and
a `lower` above an `upper` was silently resolved in the cap's favour, returning a value below the
bound the caller declared. Both are refused or ignored now rather than absorbed. The remainder
that orders the round-robin is measured from the floor actually used, because a floor raised by
`lower` has already consumed the cell's fractional claim.
```

- [x] **Step 8: Commit**

```bash
git add src/logging_employment/reconcile/integerize.py tests/unit/test_integerize.py
git commit -m "fix(reconcile): close integerize's three bound-handling gaps

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: gates and completion

**Files:**
- Modify: `specs/deferred_items.md` (tick the three source items)
- Modify: `specs/plans/5-reconciliation-correctness.md` (this file — status header and step ticks)

- [x] **Step 1: Run every gate**

```bash
uv run pytest -q
uv run black --check .
uv run ruff check --select I .
```

Expected: `1110 passed`; `black` reports all files unchanged; `ruff` reports `All checks passed!`.
Note that `uv run ruff check .` (without `--select I`) reports 24 pre-existing violations across
ISC004/TRY004/UP037/RUF100/RET501/UP047 — those are out of scope for this plan and must be
unchanged, not fixed. Confirm the count is still 24.

- [x] **Step 2: Confirm no unintended working-tree changes**

Run: `git status --porcelain`
Expected: only the files this plan names. This repo has a recorded incident of audit subagents
writing into the working tree, so check before committing rather than after.

- [x] **Step 3: Run the Plan Completion Protocol**

Per the writing-plans skill: resolve-before-defer gate, then markup this file with a status header,
then tick the three source items in `specs/deferred_items.md` with
`- [x] … → done in plan 5`, then `git mv` this file to `specs/plans/completed/` in a
`chore(specs): retire plan 5` commit. There is no spec to retire — this plan's requirements came
from the deferred backlog.

The three items to tick, all under `## 4-stage3-logging-employment-spec — 2026-09-05`:
- `**`kl_project` returns silently on an infeasible bounded system.**`
- `**The three provenance enums are declared but never enforced.**`
- `**`integerize` has three bound-handling gaps, all latent on D1 and all live in Stage 6.**`

Note for the tick on the first item: it proposed "return the achieved violation **or raise**". The
implementation returns the violation and deliberately does not raise — record that, with the reason
(§17.3's property test feeds jointly infeasible systems and asserts only non-increase), so a later
reader does not re-open it as a half-done fix.
