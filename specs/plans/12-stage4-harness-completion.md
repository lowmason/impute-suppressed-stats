# Stage 4 Harness Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via
> subagent-driven-development (the default) — or executing-plans when your human partner chose
> inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every Stage 4 regime state why it does not score with a measurement or a
declaration rather than a deferral, and make the three persisted validation tables gate on schemas
that match what they actually produce.

**Architecture:** Three independent seams, touched in order. (1) `validate/regimes.py` gains a
declared *mechanism* per regime, so `validate/harness.py` derives each non-scoring reason from the
regime's own declaration instead of a `{name}` template that was false for one of the two.
(2) `validate/leakage.py`'s two guards become typed raises and the future-row guard starts running
on the live path, once per panel-derived rolling origin. (3) `contracts.py` grows the six
provenance columns the harness already writes plus a scoreboard schema, `harness.py` starts
producing the three columns the schema already declared, and `cli.py::validate_command` gates all
three tables. No regime gains or loses a score.

**Tech Stack:** Python ≥3.14, Polars 1.44, pydantic v2, Typer, pytest. Run everything with
`uv run`.

---

## Global Constraints

These bind every task. A task's requirements implicitly include this section.

- **No `ValidationConfig` field may be added OR removed.** `runs.run_id` hashes
  `config.resolved_dict(cfg)`, which is `cfg.model_dump(mode="json")` — the whole model, verified
  at `src/logging_employment/config.py`. So an added key re-identifies every run directory exactly
  as a removed one does, and `runs/f03023ac9f3a` (the Stage 4 acceptance artifact) must still
  resolve from the shipped `config.yaml` (V1). The spec's R-S4C-11 states the removal half; the
  addition half is derived here and is the sharper constraint, because "run the guard at each
  **configured** origin" (R-S4C-4) reads as an invitation to add one. **Any new knob is a module
  constant or is derived from the panel.**
- **No identifier is renamed.** Not a regime, not a config key, not a schema field
  (R-S4C-7, R-S4C-11, spec §4).
- **Line length 100.** `ruff` and `black` are both configured to it (`pyproject.toml:41,50`).
- **Every function in `src/` needs a docstring.** `[tool.interrogate] fail-under = 100`, with
  `exclude = ["tests"]` — so test functions do not need one, though this repo writes them anyway
  where the test encodes a reason.
- **`lookback_months_masked` is the per-state masked-month count** for the row's state in that
  replicate — not `minimum_unmasked_lookback_months`. Decided 2026-09-08 with the human partner:
  the spec's phrase "from the regime's configuration" (R-S4C-15) admits both readings, and the
  global-constant reading would write the identical value 6 on all 12,530 D1 rows, which is a
  fabricated column rather than a recorded one.
- **`metric_name` is NULL on every `declines` row** (measured: 70 of 70 on the fixture). This is
  the same shape as M12's NULL `mask_arm` but the spec does not name it, and the decision
  (2026-09-08) is **record, do not fix**: the family emits counts rather than one named metric, and
  giving it a name would move a second golden column beyond what V3 authorizes. Task 12 excludes it
  from the required-non-null set *with that reason written down*.
- **Test commands** are `uv run pytest <path> -v` from the repo root. `data/staged` is gitignored;
  tests that need it carry the `skipif` pytestmark that `tests/integration/test_d1_validation.py`
  already uses. Prefer `tests/fixtures/baselines/` — it is in git and a full 10-estimator harness
  pass over it takes seconds.

### Facts re-confirmed against the working tree before this plan was written

The spec asks a plan not to re-derive its measurements but to re-confirm any it depends on. These
were re-measured 2026-09-08 at `e5d4bdd`:

| Claim | Status |
|---|---|
| M11's column arithmetic | **Confirmed exactly.** 23 produced, 20 declared, the 6 produced-not-declared and 3 declared-not-produced are the named ones. |
| M11's `seed` dtype | **Confirmed.** `pl.lit(1024)` is `Int32` on polars 1.44.1; the metrics frame's `seed` is `Int64` because it is built from Python dicts. |
| M6's nondeterminism | **Confirmed.** Three separate processes drew three different 20-key sets; sorting before the sample makes all three identical. |
| M1's truncation width | **Confirmed.** Origin `2022-01` leaves 3,024 of 4,812 rows — 1,788 removed. |
| M14's `-O` hole | **Confirmed.** The same call raises `AssertionError` under `python` and returns silently under `python -O`. |
| M2's malformed origin | **Confirmed**, and worse than recorded — see Task 2. |
| **M13's aside** — "§15.1 names the artifact" | **FALSE.** `scoreboard` appears nowhere in `specs/logging-employment-spec.md`; §15.1's nine-item list stops at `validation_metrics.parquet`. The artifact is named only in the roadmap and produced by `cli.py:456`. R-S4C-17's actual obligation (a §7 field list + a `contracts.py` schema) is unaffected; Task 11 records the correction rather than repeating the claim. |
| **V3's "270 declines rows"** | **Wrong file.** 270 is the D1 figure (9 regimes × 10 estimators × 3 seeds). `tests/fixtures/validation/validation_metrics_golden.parquet` holds **70** (7 × 10 × 1), all with NULL `mask_arm`. Task 10 pins 70 and the property, not 270. |

---

## File Structure

**Modified:**
- `src/logging_employment/errors.py` — one new exception class.
- `src/logging_employment/validate/leakage.py` — bare asserts become typed raises.
- `src/logging_employment/validate/regimes.py` — `RegimeSpec` gains a mechanism and its own
  reason; `rolling_origin_frames` refuses an out-of-panel origin; a new `rolling_origins`
  derivation.
- `src/logging_employment/contracts.py` — switch/regime mappings, six score columns, a scoreboard
  schema, a required-non-null table and its assertion.
- `src/logging_employment/validate/harness.py` — switch gating, mechanism-derived reasons, the
  future-row guard on the live path, three new score columns, a derived metric arm.
- `src/logging_employment/validate/metrics.py` — `decline_and_basis_report` gains `arm`.
- `src/logging_employment/validate/scoreboard.py` — schema-shaped empty frame.
- `src/logging_employment/cli.py` — `validate_frame` gates all three tables.
- `src/logging_employment/config.py` — `ValidationConfig` docstring records each switch's kind.
- `specs/logging-employment-spec.md` — Appendix A switch kinds; §7.14 and §7.15 field lists.
- `tests/fixtures/validation/validation_metrics_golden.parquet` — regenerated once, in Task 10.

**Created:**
- `tests/unit/test_validate_leakage_guards.py`
- `tests/unit/test_validate_rolling_origins.py`
- `tests/unit/test_validate_regime_mechanisms.py`
- `tests/unit/test_validate_cbp_gap.py`
- `tests/unit/test_validation_switch_kinds.py`
- `tests/integration/test_stage4_acceptance.py`

Why these boundaries: `regimes.py` is 381 lines and already holds every regime declaration, so the
mechanism field belongs there rather than in a new module; `contracts.py` is where every other
declared set and schema in this package lives. New test modules rather than growing
`test_validate_temporal_regimes.py` because each covers a distinct seam and this repo's suite is
parallel — wall clock is the slowest module.

---

### Task 1: Typed leakage guards, and a witness that `-O` no longer disarms them

Closes R-S4C-20 and V5. `assert_no_retained_truth` is called from `src/` at `harness.py:126`,
inside the scoring loop, so this closes a hole on the shipped path rather than a prospective one.

**Files:**
- Modify: `src/logging_employment/errors.py` (append after `NoHarvestFactorError`)
- Modify: `src/logging_employment/validate/leakage.py:82-85`, `:95-98`
- Modify: `tests/integration/test_validate_leakage.py:26`, `:111`
- Test: `tests/unit/test_validate_leakage_guards.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `errors.LeakageError`. `assert_no_retained_truth(masked: HarmonizedData, truth:
  pl.DataFrame) -> None` and `assert_no_future_rows(frame: pl.DataFrame, *, origin: str) -> None`
  keep their signatures and now raise `LeakageError` instead of `AssertionError`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validate_leakage_guards.py`:

```python
"""§13.4's guards must survive `python -O`, which strips a bare `assert` statement."""

import subprocess
import sys
import textwrap

import polars as pl
import pytest

from logging_employment.errors import LeakageError
from logging_employment.validate.leakage import assert_no_future_rows


def test_a_future_row_is_refused_with_a_typed_error():
    frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
    with pytest.raises(LeakageError, match="future"):
        assert_no_future_rows(frame, origin="2020-01")


def test_the_guard_still_refuses_under_dash_o():
    """M14: a bare `assert` vanishes under -O, so the guard on the live path was strippable.

    Run in a SUBPROCESS because -O is decided at interpreter start: `sys.flags.optimize` cannot be
    changed from inside a running test session, so an in-process test would assert nothing.
    """
    program = textwrap.dedent(
        """
        import polars as pl
        from logging_employment.errors import LeakageError
        from logging_employment.validate.leakage import assert_no_future_rows

        frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
        try:
            assert_no_future_rows(frame, origin="2020-01")
        except LeakageError:
            print("REFUSED")
        else:
            print("PASSED")
        """
    )
    done = subprocess.run(
        [sys.executable, "-O", "-c", program], capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "REFUSED"
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validate_leakage_guards.py -v`
Expected: both FAIL — `ImportError: cannot import name 'LeakageError'`.

- [ ] **Step 3: Add the exception class**

Append to `src/logging_employment/errors.py`:

```python
class LeakageError(LoggingEmploymentError):
    """§13.4's leakage controls found the thing they exist to find.

    A typed raise rather than a bare `assert`, because `python -O` strips assert statements and
    both guards run on the live path: `assert_no_retained_truth` from `validate/harness.py` inside
    the scoring loop, and `assert_no_future_rows` once per rolling origin. Measured 2026-09-08
    before this class existed, the same call raised under `python` and returned silently under
    `python -O`. The package states this convention at `validate/harness.py:63-73` and these two
    functions were the only places in it that violated the convention.
    """
```

- [ ] **Step 4: Convert both guards**

In `src/logging_employment/validate/leakage.py`, add `from ..errors import LeakageError` beneath
the existing `from ..contracts import HarmonizedData` import.

Replace the `assert` at `:82-85` with:

```python
            if str(value) == withheld:
                raise LeakageError(
                    f"{column} on {row['state_fips']}/{row['reference_month']} retains the "
                    f"held-out value {withheld}"
                )
```

Replace the `assert` at `:95-98` with:

```python
    if future.height:
        raise LeakageError(
            f"{future.height} future rows at or after origin {origin}: "
            f"{sorted(future['reference_month'].unique().to_list())[:5]}"
        )
```

- [ ] **Step 5: Update the two existing tests that expect `AssertionError`**

In `tests/integration/test_validate_leakage.py`, add `LeakageError` to the imports:

```python
from logging_employment.errors import LeakageError
```

At `:26` change `pytest.raises(AssertionError, match="future")` to
`pytest.raises(LeakageError, match="future")`.

At `:111` change `pytest.raises(AssertionError, match="employment_raw")` to
`pytest.raises(LeakageError, match="employment_raw")`.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/unit/test_validate_leakage_guards.py -v`
Expected: 2 passed.

Run: `uv run pytest tests/integration/test_validate_leakage.py -v`
Expected: all pass, or all SKIP if `data/staged` is absent — that module reads
`HarmonizedData.load(Path("data/staged"))` directly. If they skip, say so in the task report
rather than reporting a pass.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/errors.py src/logging_employment/validate/leakage.py \
  tests/unit/test_validate_leakage_guards.py tests/integration/test_validate_leakage.py
git commit -m "fix(validate): leakage guards raise a typed error, not a strippable assert"
```

---

### Task 2: `rolling_origin_frames` refuses an origin the panel does not contain

Closes R-S4C-5. **Read the deviation note in Step 1 before writing code** — R-S4C-5 places this
refusal inside `assert_no_future_rows`, and it cannot live there.

**Files:**
- Modify: `src/logging_employment/validate/regimes.py:259-272`
- Test: `tests/unit/test_validate_rolling_origins.py` (create)

**Interfaces:**
- Consumes: `errors.LeakageError` exists (Task 1) but is not used here — an out-of-panel origin is
  a caller mistake, not a leak, so it raises `ConceptViolationError` like every other caller
  mistake in this package.
- Produces: `rolling_origin_frames(monthly: pl.DataFrame, *, origins: Sequence[str]) ->
  Iterator[tuple[str, pl.DataFrame]]` — same signature, now refusing eagerly. A private
  `_truncated(monthly, origins)` generator holds the yielding half.

- [ ] **Step 1: Understand two things before writing anything**

**(a) Why the check is not in `assert_no_future_rows`.** R-S4C-5 says that function "MUST refuse an
origin that matches no period in the frame". It cannot: the guard is handed the *truncated* frame,
whose every period is strictly below the origin by construction, so the origin is never a member of
the frame it is given. The question is answerable only against the pre-truncation panel, which is
what `rolling_origin_frames` holds. The substance of M2 — `origins=['banana']` returns all 4,812
rows untruncated and the guard passes — is caught here, and it is also caught for the well-formed
out-of-panel case `'2099-01'` that M2 does not name. Record this deviation in the docstring, not
just in the task report.

**(b) A `yield` in the function body makes the guard unreachable.** `rolling_origin_frames` is a
generator function, so nothing in its body executes until a caller iterates it. Measured
2026-09-08: with the refusal written inline, `rolling_origin_frames(monthly, origins=['banana'])`
returns a generator object and raises nothing, and `pytest.raises` around the bare call fails. The
validation must therefore run in a plain function that *returns* a separate generator. That is why
`_truncated` exists.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_validate_rolling_origins.py`:

```python
"""The rolling-origin generator's refusals, on the committed fixture layer."""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.regimes import rolling_origin_frames

FIXTURE = Path("tests/fixtures/baselines")


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(FIXTURE).qcew_monthly


def test_a_malformed_origin_is_refused_on_the_bare_call():
    """M2: `origins=['banana']` used to truncate nothing and pass the future-row guard.

    Asserted on the BARE call, with no iteration: a refusal that only fires once a caller consumes
    the generator is not a guard, and inlining it into the generator body is exactly that bug.
    """
    with pytest.raises(ConceptViolationError, match="banana"):
        rolling_origin_frames(_monthly(), origins=["banana"])


def test_a_well_formed_origin_outside_the_panel_is_refused():
    """The case M2 does not name: '2099-01' parses, truncates nothing, and passed."""
    with pytest.raises(ConceptViolationError, match="2099-01"):
        rolling_origin_frames(_monthly(), origins=["2099-01"])


def test_an_in_panel_origin_still_yields_a_past_only_frame():
    monthly = _monthly()
    produced = list(rolling_origin_frames(monthly, origins=["2023-07"]))
    assert len(produced) == 1
    origin, frame = produced[0]
    assert origin == "2023-07"
    assert frame.height < monthly.height
    assert frame.filter(pl.col("reference_month") >= "2023-07").height == 0
```

- [ ] **Step 3: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validate_rolling_origins.py -v`
Expected: the two refusal tests FAIL with `DID NOT RAISE ConceptViolationError`; the third passes.

- [ ] **Step 4: Split the eager refusal from the lazy truncation**

In `src/logging_employment/validate/regimes.py`, add `ConceptViolationError` to the errors import
(there is none today — add `from ..errors import ConceptViolationError` beneath the
`from ..contracts import ...` line), then replace `rolling_origin_frames` entirely:

```python
def rolling_origin_frames(
    monthly: pl.DataFrame, *, origins: Sequence[str]
) -> Iterator[tuple[str, pl.DataFrame]]:
    """§13.3's rolling-origin design: one past-only frame per origin.

    TRUNCATION, not masking. A mask nulls a value and leaves the row; the exit criterion asks that
    the run "provably contains no future-period rows", which only removing them can satisfy.

    Reported scope: measured 2026-09-08, no §10 estimator reads a future period, so this regime
    does not separate any Stage 3 baseline. It is built now because Stage 5's model will, and
    because the guard is what makes that claim checkable rather than assumed.

    THE MEMBERSHIP REFUSAL LIVES HERE AND NOT IN `assert_no_future_rows`, which is where R-S4C-5
    places it. A truncated frame never contains its own origin — every period in it is strictly
    below the origin by construction — so the guard cannot ask this question about the frame it is
    handed. Only the pre-truncation panel can answer it, and this is the function that holds one.

    THE REFUSAL IS EAGER, which is why `_truncated` is a separate function. A `yield` anywhere in
    this body would defer every line of it until a caller iterated, so the check would not run on
    the bare call — measured 2026-09-08, the inline version returned a generator and raised
    nothing.
    """
    panel = set(monthly["reference_month"].unique().to_list())
    unknown = [origin for origin in origins if origin not in panel]
    if unknown:
        raise ConceptViolationError(
            f"origin(s) {unknown} name no period in this panel, whose months run "
            f"{min(panel)}..{max(panel)}. An origin outside it truncates nothing and leaves the "
            "§13.4 guard passing over an untruncated frame: measured, `origins=['banana']` "
            "returned all 4,812 rows and `assert_no_future_rows` reported no future row, because "
            "every period sorts below the string."
        )
    return _truncated(monthly, origins)


def _truncated(monthly: pl.DataFrame, origins: Sequence[str]) -> Iterator[tuple[str, pl.DataFrame]]:
    """One past-only frame per origin. Called only by `rolling_origin_frames`, after its refusal."""
    for origin in origins:
        yield origin, monthly.filter(pl.col("reference_month") < origin)
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/test_validate_rolling_origins.py -v`
Expected: 3 passed.

Run: `uv run pytest tests/unit/test_validate_temporal_regimes.py -v`
Expected: pass, or SKIP/fail-on-missing-data — that module loads `data/staged` at
`test_validate_temporal_regimes.py:10`. Its origins `2020-01` and `2022-01` are both in the D1
panel (verified), so it stays green where the data exists.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/validate/regimes.py tests/unit/test_validate_rolling_origins.py
git commit -m "fix(validate): refuse a rolling origin the panel does not contain"
```

---

### Task 3: Rolling origins derived from the panel, not from a new config key

Supplies R-S4C-4's "configured origins" without adding a `ValidationConfig` field, which V1
forbids. Read the Global Constraints entry on `run_id` before starting.

**Files:**
- Modify: `src/logging_employment/validate/regimes.py` (add after `rolling_origin_frames`)
- Test: `tests/unit/test_validate_rolling_origins.py` (extend)

**Interfaces:**
- Consumes: `rolling_origin_frames` refuses an out-of-panel origin (Task 2) — every origin this
  function returns is drawn from the panel, so the pair composes without a refusal.
- Produces: `rolling_origins(monthly: pl.DataFrame, *, config: Config) -> tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_validate_rolling_origins.py` (and add
`from logging_employment.config import load_config` and
`from logging_employment.validate.regimes import rolling_origins` to its imports):

```python
def test_the_fixture_panel_yields_no_origin_because_it_is_one_year_long():
    """Measured: `tests/fixtures/baselines` carries 2023-01..2023-12 and nothing before it.

    So the guard is VACUOUS on the fixture and binding on D1, and the manifest records which. A
    January with no history behind it would truncate to an empty frame, which proves nothing.
    """
    cfg = load_config(Path("config.yaml"))
    assert rolling_origins(_monthly(), config=cfg) == ()


def test_origins_are_januaries_with_enough_history_behind_them():
    """Derived from a synthetic panel, so the expectation does not restate the implementation."""
    cfg = load_config(Path("config.yaml"))
    months = [f"{year}-{month:02d}" for year in (2019, 2020, 2021) for month in range(1, 13)]
    monthly = pl.DataFrame({"reference_month": months})
    # 2019-01 sits at index 0, below the 6-month floor; 2020-01 and 2021-01 clear it.
    assert rolling_origins(monthly, config=cfg) == ("2020-01", "2021-01")


def test_every_derived_origin_is_accepted_by_the_generator():
    """The two functions compose: nothing `rolling_origins` returns can trip Task 2's refusal."""
    cfg = load_config(Path("config.yaml"))
    months = [f"{year}-{month:02d}" for year in (2019, 2020) for month in range(1, 13)]
    monthly = pl.DataFrame({"reference_month": months})
    origins = rolling_origins(monthly, config=cfg)
    assert [origin for origin, _ in rolling_origin_frames(monthly, origins=origins)] == list(
        origins
    )
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validate_rolling_origins.py -v`
Expected: FAIL — `ImportError: cannot import name 'rolling_origins'`.

- [ ] **Step 3: Implement the derivation**

Add to `src/logging_employment/validate/regimes.py`, immediately after `_truncated`:

```python
def rolling_origins(monthly: pl.DataFrame, *, config: Config) -> tuple[str, ...]:
    """The origins §13.4's future-row guard runs at: each January with enough history behind it.

    DERIVED FROM THE PANEL, NOT CONFIGURED, and that is a constraint rather than a preference.
    `runs.run_id` hashes `config.resolved_dict`, which is `Config.model_dump(mode="json")` — the
    whole model — so ADDING a `ValidationConfig` key re-identifies every run directory on disk
    exactly as removing one does. `runs/f03023ac9f3a` is Stage 4's acceptance artifact and must
    still resolve from the shipped `config.yaml`. A panel-derived rule needs no new key.

    Januaries rather than the declared break windows, which was the alternative considered:
    `structural_break_windows` and `naics_seam_month` name months this panel's ESTIMATORS are
    stressed at, which is a different question from where a real-time frame should be cut, and
    reusing them would make an edit to either silently move the other. The history floor is
    `minimum_unmasked_lookback_months`, reused rather than re-declared — a January with less than
    that behind it truncates to a frame too short to estimate from, which proves nothing.

    Measured 2026-09-08: seven origins on `data/staged` (2018-01 through 2024-01, with 2017-01
    excluded by the floor) and NONE on the committed `tests/fixtures/baselines` layer, which
    carries 2023 alone. The guard is therefore vacuous on the fixture and binding on D1, and
    `run_pseudo_suppression` records which in the manifest rather than leaving a reader to assume.
    """
    months = sorted(monthly["reference_month"].unique().to_list())
    floor = config.validation.minimum_unmasked_lookback_months
    return tuple(
        month for index, month in enumerate(months) if month.endswith("-01") and index >= floor
    )
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_rolling_origins.py -v`
Expected: 6 passed.

- [ ] **Step 5: Confirm the D1 derivation matches the docstring**

Run:

```bash
uv run python -c "
import polars as pl
from pathlib import Path
from logging_employment.config import load_config
from logging_employment.validate.regimes import rolling_origins
m = pl.read_parquet('data/staged/qcew_monthly.parquet')
print(rolling_origins(m, config=load_config(Path('config.yaml'))))
"
```

Expected: `('2018-01', '2019-01', '2020-01', '2021-01', '2022-01', '2023-01', '2024-01')`.
If `data/staged` is absent, skip this step and say so in the task report — do not report the
docstring's seven origins as verified when you did not verify them.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/validate/regimes.py tests/unit/test_validate_rolling_origins.py
git commit -m "feat(validate): derive rolling origins from the panel, not a new config key"
```

---

### Task 4: A regime declares its mechanism, and the harness derives each reason from it

Closes R-S4C-1, R-S4C-2, R-S4C-3 and R-S4C-9. This is the task that removes M8's false sentence —
the one shipped verbatim in `runs/f03023ac9f3a/validation_manifest.json`.

**Files:**
- Modify: `src/logging_employment/validate/regimes.py:44-52` (`RegimeSpec`), `:218-226` and
  `:373-381` (both `REGIME_SPECS` comprehensions)
- Modify: `src/logging_employment/validate/harness.py:106-119`
- Modify: `tests/integration/test_d1_validation.py:96-106`
- Test: `tests/unit/test_validate_regime_mechanisms.py` (create)

**Interfaces:**
- Consumes: nothing from Tasks 1–3.
- Produces:
  - `regimes.REGIME_MECHANISMS: tuple[str, ...]`
  - `RegimeSpec(name: str, disposition: str, grain: str, select: Callable | None, mechanism: str,
    no_score_reason: str | None)` — two new fields, both required positionally-or-by-keyword; the
    two comprehensions that build `REGIME_SPECS` must both pass them.
  - Task 5 reads `spec.mechanism == "frame_truncation"`; Task 7 reads `spec.no_score_reason`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validate_regime_mechanisms.py`:

```python
"""Every regime declares WHY it has no selector, rather than the harness templating one reason."""

import pytest

from logging_employment.contracts import HOLDOUT_REGIMES
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.regimes import (
    REGIME_MECHANISMS,
    REGIME_SPECS,
    RegimeSpec,
)


def test_every_regime_declares_a_mechanism_from_the_closed_set():
    assert set(REGIME_SPECS) == set(HOLDOUT_REGIMES)
    for name, spec in REGIME_SPECS.items():
        assert spec.mechanism in REGIME_MECHANISMS, name


def test_a_masking_regime_has_a_selector_and_a_non_masking_one_has_a_reason():
    """The pairing R-S4C-1 asks for, as a property of all thirteen rather than a spot check."""
    for name, spec in REGIME_SPECS.items():
        if spec.mechanism == "qcew_mask":
            assert spec.select is not None, name
            assert spec.no_score_reason is None, name
        else:
            assert spec.select is None, name
            assert spec.no_score_reason, name


def test_a_spec_whose_mechanism_and_selector_disagree_is_refused():
    """The late `_SELECTORS` mutation at the foot of regimes.py is why this is enforced."""
    with pytest.raises(ConceptViolationError, match="qcew_mask"):
        RegimeSpec(
            name="invented",
            disposition="feasible",
            grain="single_month",
            select=None,
            mechanism="qcew_mask",
            no_score_reason=None,
        )


def test_the_cbp_reason_does_not_claim_an_entry_point_nothing_calls():
    """M8: the shipped manifest asserts `cbp_size_gaps` is exercised through its own entry point.

    `cbp_size_gap_keys` and `apply_cbp_gap` have no caller and no test anywhere in the package, so
    the sentence was false — and it was false because it came from a `{name}` template shared with
    `rolling_origin`, for which it is true.
    """
    reason = REGIME_SPECS["cbp_size_gaps"].no_score_reason
    assert "exercised through its own entry point" not in reason
    assert "state-year" in reason
    assert "fallback arm" in reason


def test_the_rolling_origin_reason_is_scoped_to_the_registry_it_was_measured_against():
    """R-S4C-3: adding a smoothing estimator must invalidate the reason, not be inherited by it."""
    reason = REGIME_SPECS["rolling_origin"].no_score_reason
    assert "registry" in reason
    assert "2026-09-08" in reason


def test_no_reason_defers_the_question_to_a_later_plan():
    """R-S4C-2: a measurement or a declaration, never a deferral."""
    for name, spec in REGIME_SPECS.items():
        if spec.no_score_reason is None:
            continue
        lowered = spec.no_score_reason.lower()
        assert "deferred" not in lowered, name
        assert "not yet" not in lowered, name
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validate_regime_mechanisms.py -v`
Expected: FAIL — `ImportError: cannot import name 'REGIME_MECHANISMS'`.

- [ ] **Step 3: Declare the mechanisms and the reasons**

In `src/logging_employment/validate/regimes.py`, insert above `RegimeSpec` (after the
`CENSUS_DIVISIONS` block):

```python
# WHY a regime produces no `MaskTarget`, declared per regime rather than inferred from
# `select is None`. That test conflates three unrelated situations — a regime that uses a different
# mechanism entirely, one that is vacuous on the §10 registry, and one that refuses on this window
# — and the harness templated ONE sentence on `{name}` across all of them. Measured 2026-09-08, the
# sentence was true of `rolling_origin` and false of `cbp_size_gaps`, whose named entry points have
# no caller and no test anywhere in the package, and the false version shipped verbatim in
# `runs/f03023ac9f3a/validation_manifest.json`.
REGIME_MECHANISMS: tuple[str, ...] = (
    "qcew_mask",
    "frame_truncation",
    "cbp_gap",
    "no_registry_estimator",
    "no_second_vintage",
)

_MECHANISMS: dict[str, str] = {
    "rolling_origin": "frame_truncation",
    "cbp_size_gaps": "cbp_gap",
    "retrospective_smoothing": "no_registry_estimator",
    "preliminary_to_final_vintage": "no_second_vintage",
}

# Each regime's own sentence, a MEASUREMENT or a DECLARATION and never a deferral (R-S4C-2). The
# two measured ones carry the date and the registry they were measured against, so that adding an
# estimator invalidates them rather than letting them be silently inherited.
_NO_SCORE_REASONS: dict[str, str] = {
    "rolling_origin": (
        "rolling_origin truncates the frame rather than masking a QCEW cell, so it produces no "
        "MaskTarget. Measured 2026-09-08 against the ten-estimator §10 registry: truncation moves "
        "no estimator's pre-origin estimate — rolling_origin_frames removes 1,788 of 4,812 rows "
        "at origin 2022-01, the widest blackout in the file, and every estimator returns what it "
        "returned unmasked — so this regime separates ZERO baselines on THIS registry. The scope "
        "is the registry: adding a smoothing or autoregressive estimator invalidates this reason "
        "rather than inheriting it. A scoreboard entry that cannot discriminate would read as "
        "evidence, so the regime records the §13.4 future-row guard instead of a score; the "
        "origins it was checked at are recorded beside this reason."
    ),
    "cbp_size_gaps": (
        "cbp_size_gaps removes CBP state-year rows rather than masking a QCEW cell, so it "
        "produces no MaskTarget and scores no cell on its own: it changes cbp_intensity's weight "
        "basis, not the set of masked cells. Measured 2026-09-08: removal causes ZERO additional "
        "declines (147 declined rows before and after) and moves the cell to the declared fallback "
        "arm, and because national_march_intensity pools over surviving rows the effect reaches "
        "every state in the year rather than only the holed state-year."
    ),
    "retrospective_smoothing": "no smoothing estimator in the §10 registry",
    "preliminary_to_final_vintage": "no second snapshot in any staged table",
}
```

Then replace the `RegimeSpec` dataclass:

```python
@dataclass(frozen=True)
class RegimeSpec:
    """One §13.3 regime: how it selects, at what grain, whether it can run, and by what mechanism."""

    name: str
    disposition: str
    # "blackout" regimes INTEND to erase a state's history; "single_month" regimes must not.
    grain: str
    select: Callable[[pl.DataFrame, int, Config], list[MaskTarget]] | None
    mechanism: str
    no_score_reason: str | None

    def __post_init__(self) -> None:
        """Refuse a spec whose mechanism, selector and reason disagree.

        Enforced rather than conventional because this module MUTATES `_SELECTORS` after the first
        `REGIME_SPECS` comprehension runs and rebuilds the dict at the foot of the file. A regime
        that gained a selector without gaining `qcew_mask` — or lost one without gaining a reason —
        would otherwise reach the harness as a silent no-op, which is the failure this stage
        refuses everywhere else.
        """
        if self.mechanism not in REGIME_MECHANISMS:
            raise ConceptViolationError(
                f"{self.name}: mechanism {self.mechanism!r} is not declared; the set is "
                f"{list(REGIME_MECHANISMS)}"
            )
        if (self.mechanism == "qcew_mask") != (self.select is not None):
            raise ConceptViolationError(
                f"{self.name}: mechanism {self.mechanism!r} and "
                f"select={'a callable' if self.select else 'None'} disagree. A qcew_mask regime "
                "has a selector and every other mechanism has none."
            )
        if (self.mechanism == "qcew_mask") != (self.no_score_reason is None):
            raise ConceptViolationError(
                f"{self.name}: a qcew_mask regime declares no no_score_reason and every other "
                "mechanism must declare one — a regime that scores nothing must say why "
                "(R-S4C-2), and the reason must be its own rather than a shared template."
            )
```

- [ ] **Step 4: Delete the first `REGIME_SPECS` comprehension, then rebuild the second**

`REGIME_SPECS` is built twice today — at `:218-226` and again at `:373-381` — because `_SELECTORS`
is mutated in between. **Delete `:218-226` entirely.** Do not edit it and do not port the new
fields into it: at that point in the module `_structural_break` and `_naics_transition` are not yet
registered, so both regimes would be built with `select=None` and `mechanism="qcew_mask"`, which
`__post_init__` now refuses — the module would fail to import. That first dict was always stale and
only the rebuild at the foot of the file was ever read.

Nothing between the two comprehensions reads `REGIME_SPECS` at import time: `select_targets`
(`:229-256`) sits between them but reads it at CALL time. Confirm after the edit with
`uv run python -c "import logging_employment.validate.regimes"`, which must print nothing.

Then apply this body to the surviving comprehension at the foot of the file:

```python
REGIME_SPECS: dict[str, RegimeSpec] = {
    name: RegimeSpec(
        name=name,
        disposition=REGIME_DISPOSITIONS[name],
        grain=_GRAINS.get(name, "single_month"),
        select=_SELECTORS.get(name),
        mechanism=_MECHANISMS.get(name, "qcew_mask"),
        no_score_reason=_NO_SCORE_REASONS.get(name),
    )
    for name in HOLDOUT_REGIMES
}
```

Keep the `: dict[str, RegimeSpec]` annotation on it, since it is now the only definition. Replace
its existing explanatory comment with one that says why there is only one:

```python
# Built ONCE, at the foot of the module, after every selector is registered. There used to be a
# second comprehension above `select_targets` and a rebuild here, because `_structural_break` and
# `_naics_transition` are registered late; the first dict was always stale and only the rebuild was
# ever read. `RegimeSpec.__post_init__` now refuses a mechanism/selector mismatch, so the stale
# first pass would raise at import — which is the check working, and the reason there is one dict.
# `preliminary_to_final_vintage` stays out of `_SELECTORS` on purpose, so its disposition raises.
```

- [ ] **Step 5: Run the unit test**

Run: `uv run pytest tests/unit/test_validate_regime_mechanisms.py -v`
Expected: 6 passed.

Run: `uv run pytest tests/unit/test_validate_declared_regimes.py -v`
Expected: 5 passed — that module reads `REGIME_SPECS["retrospective_smoothing"].select is None`,
which is unchanged.

- [ ] **Step 6: Make the harness read the declared reason**

In `src/logging_employment/validate/harness.py`, replace the `spec.select is None` block at
`:106-119` with:

```python
        # A `feasible` regime that scores nothing MUST say why, in ITS OWN words. The reason used
        # to be templated on `{name}` across every selectorless regime, which asserted of both that
        # the regime "is exercised through its own entry point in `validate.regimes`" — true for
        # `rolling_origin`, false for `cbp_size_gaps`, whose entry points have no caller and no
        # test. The false version shipped in `runs/f03023ac9f3a/validation_manifest.json`. The
        # reason now comes from `RegimeSpec.no_score_reason`, which is PROVABLY non-None here:
        # `__post_init__` ties `select is None` to a non-`qcew_mask` mechanism and every one of
        # those must declare a reason. Do not add an `or "..."` fallback — that fallback would be
        # a shared template, which is the defect this replaced.
        if spec.select is None:
            entry["reason"] = spec.no_score_reason
            regimes[name] = entry
            continue
```

- [ ] **Step 7: Strengthen the pin test**

R-S4C-2 requires the existing pin to reject a deferral, not merely a non-empty string. In
`tests/integration/test_d1_validation.py`, replace the body of
`test_no_regime_reports_zero_scores_without_saying_why` (`:104-106`) with:

```python
    deferrals = ("deferred", "not yet", "unwired", "to be wired", "future plan")
    for name, entry in four_rung_run.manifest["regimes"].items():
        if entry["n_scored"] != 0:
            continue
        reason = entry.get("reason")
        assert reason, f"{name} scored nothing and gave no reason"
        # R-S4C-2: a measurement or a declaration, never a deferral. This test used to accept any
        # non-empty string, including "Wiring it into the loop is a deferred item" — a sentence
        # that describes the plan's state rather than the regime's.
        lowered = reason.lower()
        for phrase in deferrals:
            assert phrase not in lowered, f"{name}'s reason defers rather than explains: {reason}"
```

Update that test's docstring to drop the sentence "Before this guard the manifest recorded them as
`feasible, scored=0`" — keep the paragraph but replace its last sentence with: "The guard now also
refuses a reason that defers the question to a later plan rather than answering it."

- [ ] **Step 8: Run the integration test**

Run: `uv run pytest tests/integration/test_d1_validation.py -v`
Expected: all pass, or the whole module SKIPs when `data/staged` is absent (its pytestmark). If it
skips, report that — a skipped module is not a passing one.

- [ ] **Step 9: Commit**

```bash
git add src/logging_employment/validate/regimes.py src/logging_employment/validate/harness.py \
  tests/unit/test_validate_regime_mechanisms.py tests/integration/test_d1_validation.py
git commit -m "fix(validate): a regime declares its own no-score reason, not a shared template"
```

---

### Task 5: The future-row guard runs on the live path, and its origins reach the manifest

Closes R-S4C-4. Per M2 nothing discharges Stage 4's exit criterion "a rolling-origin run provably
contains no future-period rows" today: `assert_no_future_rows` has zero callers in `src/`.

**Files:**
- Modify: `src/logging_employment/validate/harness.py` (imports, and the `spec.select is None`
  block Task 4 rewrote)
- Test: `tests/integration/test_stage4_acceptance.py` (create)

**Interfaces:**
- Consumes: `regimes.rolling_origins` (Task 3), `regimes.rolling_origin_frames` (Task 2),
  `leakage.assert_no_future_rows` raising `LeakageError` (Task 1), `spec.mechanism` (Task 4).
- Produces: `manifest["regimes"]["rolling_origin"]["origins_checked"]` — a `list[str]`, present on
  that regime's entry only.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_stage4_acceptance.py`:

```python
"""Stage 4's exit criteria, witnessed on the committed fixture layer rather than on data/staged.

The fixture is in git, so these run on a clean checkout. Where a claim is about D1 specifically the
test says so and carries the `data/staged` skipif.
"""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import Config, load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.harness import run_pseudo_suppression

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "baselines"


def _fixture_config() -> Config:
    cfg = load_config(REPO / "config.yaml")
    return cfg.model_copy(
        update={
            "validation": cfg.validation.model_copy(
                update={"replicates_per_regime": 3, "pseudo_suppression_seeds": [1024]}
            )
        }
    )


@pytest.fixture(scope="module")
def fixture_run():
    """One full-registry harness pass, shared by every test here — the suite runs in parallel."""
    return run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY, _fixture_config())


def test_the_rolling_origin_entry_records_the_origins_its_guard_checked(fixture_run):
    """R-S4C-4: the guard is the deliverable, so the manifest must say where it ran.

    On this fixture the answer is NONE — it carries 2023 alone, so no January has the configured
    six months of history behind it. An empty list is the honest record and is not the same as an
    absent key: absent would mean the guard was never reached.
    """
    entry = fixture_run.manifest["regimes"]["rolling_origin"]
    assert "origins_checked" in entry
    assert entry["origins_checked"] == []
    assert entry["n_scored"] == 0


def test_only_the_truncating_regime_records_origins(fixture_run):
    """A key that appeared on every entry would say nothing about which regime owns the guard."""
    carrying = {
        name
        for name, entry in fixture_run.manifest["regimes"].items()
        if "origins_checked" in entry
    }
    assert carrying == {"rolling_origin"}
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: FAIL — `AssertionError: assert 'origins_checked' in {...}`.

- [ ] **Step 3: Wire the guard into the harness**

In `src/logging_employment/validate/harness.py`, extend the leakage import and the regimes import:

```python
from .leakage import assert_no_future_rows, assert_no_retained_truth
```

```python
from .regimes import REGIME_SPECS, rolling_origin_frames, rolling_origins, select_targets
```

Then replace the `spec.select is None` block Task 4 wrote with:

```python
        if spec.select is None:
            if spec.mechanism == "frame_truncation":
                # §13.4 bullet 3, ON THE LIVE PATH. Measured 2026-09-08, `assert_no_future_rows`
                # had zero callers in `src/` and ran only inside two test modules, so Stage 4's
                # exit criterion "a rolling-origin run provably contains no future-period rows"
                # was discharged by nothing a run executes. The origins are recorded because a
                # guard that ran nowhere and a guard that ran everywhere both report success.
                origins = rolling_origins(data.qcew_monthly, config=config)
                for origin, frame in rolling_origin_frames(data.qcew_monthly, origins=origins):
                    assert_no_future_rows(frame, origin=origin)
                entry["origins_checked"] = list(origins)
            entry["reason"] = spec.no_score_reason
            regimes[name] = entry
            continue
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: 2 passed.

- [ ] **Step 5: Witness the guard binding on D1**

Add to `tests/integration/test_stage4_acceptance.py`:

```python
STAGED = REPO / "data" / "staged"


@pytest.mark.slow
@pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(),
    reason="data/staged is gitignored; the seven D1 origins need the rebuilt tables",
)
def test_the_guard_is_binding_on_the_d1_panel():
    """The fixture makes the guard vacuous, so the binding case is witnessed separately.

    Two estimators rather than the registry: this test is about the origins, and §13.7's CRPS is
    the harness's dominant cost.
    """
    cfg = load_config(REPO / "config.yaml")
    cfg = cfg.model_copy(
        update={"validation": cfg.validation.model_copy(update={"pseudo_suppression_seeds": [1024]})}
    )
    result = run_pseudo_suppression(HarmonizedData.load(STAGED), REGISTRY[:2], cfg)
    origins = result.manifest["regimes"]["rolling_origin"]["origins_checked"]
    assert origins == [
        "2018-01",
        "2019-01",
        "2020-01",
        "2021-01",
        "2022-01",
        "2023-01",
        "2024-01",
    ]
```

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: 3 passed, or 2 passed + 1 skipped without `data/staged`.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/validate/harness.py tests/integration/test_stage4_acceptance.py
git commit -m "feat(validate): run the future-row guard per rolling origin and record them"
```

---

### Task 6: `cbp_size_gap_keys` becomes deterministic, tested, and truthfully documented

Closes R-S4C-6, R-S4C-7, R-S4C-8 and V6. The determinism fix is load-bearing rather than
incidental: Task 4 records a *measured* reason for this regime, and a measurement taken from a
nondeterministic selector is not reproducible, against §16.1's idempotence requirement.

**Files:**
- Modify: `src/logging_employment/validate/regimes.py:337-362`
- Test: `tests/unit/test_validate_cbp_gap.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `cbp_size_gap_keys(data: HarmonizedData, *, seed: int, config: Config) ->
  list[tuple[str, int]]` and `apply_cbp_gap(data: HarmonizedData, keys: Sequence[tuple[str, int]])
  -> HarmonizedData` — both unchanged in signature. This task gives them their first test; they
  still have no caller in `src/`, which is what Task 4's reason now says instead of claiming
  otherwise.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validate_cbp_gap.py`:

```python
"""§16.1 idempotence for the CBP gap selector, which had no test and no caller until now."""

import subprocess
import sys
import textwrap
from pathlib import Path

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import apply_cbp_gap, cbp_size_gap_keys

FIXTURE = Path("tests/fixtures/baselines")

_DRAW = """
from pathlib import Path
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import cbp_size_gap_keys

data = HarmonizedData.load(Path("tests/fixtures/baselines"))
cfg = load_config(Path("config.yaml"))
print(cbp_size_gap_keys(data, seed=1024, config=cfg))
"""


def test_the_same_seed_gives_the_same_keys_in_separate_processes():
    """V6/M6: `unique()` gives no order guarantee, so a seeded sample over it is not reproducible.

    ACROSS PROCESSES, not within one. Measured 2026-09-08 before the fix, three runs of this exact
    program produced three different 20-key sets while a single process repeated itself — which is
    why the sibling defect at `_clustered` and `_state_year` was caught twice and this one never
    was. A subprocess is the only shape that witnesses it.
    """
    drawn = {
        subprocess.run(
            [sys.executable, "-c", textwrap.dedent(_DRAW)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for _ in range(3)
    }
    assert len(drawn) == 1, f"three processes drew {len(drawn)} different key sets"


def test_the_gap_removes_the_whole_state_year_across_every_size_code():
    """M3: this is a state-YEAR gap, not a size gap, whatever the identifier says."""
    data = HarmonizedData.load(FIXTURE)
    keys = cbp_size_gap_keys(data, seed=1024, config=load_config(Path("config.yaml")))
    gapped = apply_cbp_gap(data, keys[:1])
    state, year = keys[0]
    before = data.cbp_state_size.filter(
        (data.cbp_state_size["state_fips"] == state)
        & (data.cbp_state_size["reference_year"] == year)
    )
    after = gapped.cbp_state_size.filter(
        (gapped.cbp_state_size["state_fips"] == state)
        & (gapped.cbp_state_size["reference_year"] == year)
    )
    assert before.height > 1, "the fixture must carry more than one size row for this state-year"
    assert after.height == 0
    assert gapped.cbp_state_size.height == data.cbp_state_size.height - before.height


def test_an_empty_key_list_returns_the_data_untouched():
    data = HarmonizedData.load(FIXTURE)
    assert apply_cbp_gap(data, []) is data
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validate_cbp_gap.py -v`
Expected: `test_the_same_seed_gives_the_same_keys_in_separate_processes` FAILS with
`three processes drew 3 different key sets`. The other two pass — they do not depend on order.

- [ ] **Step 3: Sort before sampling, and correct the docstring**

Replace `cbp_size_gap_keys` in `src/logging_employment/validate/regimes.py`:

```python
def cbp_size_gap_keys(data: HarmonizedData, *, seed: int, config: Config) -> list[tuple[str, int]]:
    """(state_fips, reference_year) pairs whose CBP size rows this regime removes.

    A STATE-YEAR GAP, not a size gap, whatever the name says. `apply_cbp_gap` keys on
    `(state_fips, reference_year)` and removes the state-year across all seven size codes — 86 rows
    for a 20-key draw on D1. The identifiers `cbp_size_gaps` and `cbp_size_gap_keys` are NOT
    renamed: `cbp_size_gaps` is a member of `contracts.HOLDOUT_REGIMES` and appears in
    `REGIME_DISPOSITIONS`, so renaming would change the manifest's regime keys for no behavioural
    gain. The mismatch is recorded where it is read.

    Returns CBP keys, NOT `MaskTarget`s: no QCEW cell is hidden here, so the regime scores nothing
    on its own. CORRECTED 2026-09-08 — this docstring used to say removal "turns §10.4 from an
    own-arm estimator into a declining one for that state-year". Measured, that produces ZERO
    additional declines (147 declined rows before and after): `CbpIntensity.weights` declines only
    when the ENTIRE `reference_year` is absent, and holing one state moves that cell to the
    declared fallback arm instead. The effect is also not local — `national_march_intensity` is a
    pooled ratio over surviving rows, so dropping one state's row moves every state's shrunk
    intensity in that year (measured: all 1,080 non-declined `cbp_intensity` estimates across
    2017-2023 moved, max |delta| 421 employees). Confining the effect to the holed state-year would
    require handing the estimator an ungapped national value, which `fallback.resolve_intensity`
    does not permit; that is recorded, not fixed.

    SORT BEFORE SAMPLING. `unique()` gives no order guarantee, so a seeded sample over its output
    draws a different key set per process — the same defect diagnosed and fixed twice in this file
    (`_clustered`, `_state_year`) for breaking §16.1's idempotence MUST. It survived here because
    the pair had no test and no caller. Measured 2026-09-08: three processes, three different
    20-key sets before the sort and one after.
    """
    pool = (
        data.cbp_state_size.select("state_fips", "reference_year")
        .unique()
        .sort("state_fips", "reference_year")
    )
    drawn = pool.sample(
        n=min(config.validation.replicates_per_regime, pool.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [(r["state_fips"], r["reference_year"]) for r in drawn.iter_rows(named=True)]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_cbp_gap.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/validate/regimes.py tests/unit/test_validate_cbp_gap.py
git commit -m "fix(validate): make cbp_size_gap_keys deterministic and correct its docstring"
```

---

### Task 7: Declare what KIND each Appendix A switch is

Closes R-S4C-10, R-S4C-11 and R-S4C-13. Per M9 the seven switches were never a uniform set, and
every restatement that treated them as one has been wrong in a different way.

**Files:**
- Modify: `src/logging_employment/contracts.py` (after `REGIME_DISPOSITIONS`, `:401`)
- Modify: `src/logging_employment/config.py:173-180` (`ValidationConfig` docstring)
- Modify: `specs/logging-employment-spec.md:2163-2171` (Appendix A `validation` block)
- Test: `tests/unit/test_validation_switch_kinds.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `contracts.VALIDATION_SWITCH_KINDS: dict[str, str]`,
  `contracts.SWITCH_KINDS: tuple[str, ...]`, `contracts.REGIME_SWITCHES: dict[str, str]`. Task 8
  consumes `REGIME_SWITCHES`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_validation_switch_kinds.py`:

```python
"""M9: the seven Appendix A switches were never a uniform set, so each declares its kind."""

from logging_employment.config import ValidationConfig
from logging_employment.contracts import (
    HOLDOUT_REGIMES,
    REGIME_SWITCHES,
    SWITCH_KINDS,
    VALIDATION_SWITCH_KINDS,
)


def test_every_include_field_is_classified():
    """Derived from the model, so adding a switch without classifying it fails here."""
    switches = {name for name in ValidationConfig.model_fields if name.startswith("include_")}
    assert switches == set(VALIDATION_SWITCH_KINDS)


def test_every_declared_kind_is_from_the_closed_set():
    for switch, kind in VALIDATION_SWITCH_KINDS.items():
        assert kind in SWITCH_KINDS, switch


def test_the_four_regime_switches_name_real_regimes():
    """R-S4C-10: four of the seven name regimes; the mapping must be to declared ones."""
    regime_switches = {
        switch for switch, kind in VALIDATION_SWITCH_KINDS.items() if kind == "regime_switch"
    }
    assert regime_switches == set(REGIME_SWITCHES.values())
    assert set(REGIME_SWITCHES) <= set(HOLDOUT_REGIMES)
    assert REGIME_SWITCHES == {
        "long_consecutive_runs": "include_long_runs",
        "rolling_origin": "include_rolling_origin",
        "retrospective_smoothing": "include_retrospective_smoothing",
        "preliminary_to_final_vintage": "include_vintage_comparison",
    }


def test_the_mask_label_switches_are_not_regime_switches():
    """R-S4C-13: `include_primary_like` / `include_complementary_like` are INV-009 LABELS."""
    assert VALIDATION_SWITCH_KINDS["include_primary_like"] == "mask_label_switch"
    assert VALIDATION_SWITCH_KINDS["include_complementary_like"] == "mask_label_switch"


def test_the_sanity_check_switch_is_a_design_validity_operand():
    """It names a design with no implementation anywhere in the package — but it is not inert."""
    assert (
        VALIDATION_SWITCH_KINDS["include_random_mask_sanity_check"] == "design_validity_operand"
    )


def test_nine_of_thirteen_regimes_have_no_switch():
    """M9's count, as a property. A switch set that grew to cover them would be a design change."""
    assert len(HOLDOUT_REGIMES) - len(REGIME_SWITCHES) == 9
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_validation_switch_kinds.py -v`
Expected: FAIL — `ImportError: cannot import name 'REGIME_SWITCHES'`.

- [ ] **Step 3: Declare the kinds**

In `src/logging_employment/contracts.py`, insert immediately after the `REGIME_DISPOSITIONS` dict
(`:401`):

```python
# What KIND of thing each Appendix A `include_*` switch is. Measured 2026-09-08, the seven were
# never a regime partition and every restatement that treated them as one has been wrong in a
# different way: four name regimes, two name INV-009 mask LABELS, and one names a design with no
# implementation anywhere in the package. Nine of the thirteen regimes have no switch at all.
SWITCH_KINDS: tuple[str, ...] = (
    "regime_switch",
    "mask_label_switch",
    "design_validity_operand",
)

VALIDATION_SWITCH_KINDS: dict[str, str] = {
    "include_long_runs": "regime_switch",
    "include_rolling_origin": "regime_switch",
    "include_retrospective_smoothing": "regime_switch",
    "include_vintage_comparison": "regime_switch",
    # §13.2 steps 3 and 8, not regime selection. These name the INV-009 label a masked cell
    # carries; every selector in `validate/regimes.py` constructs `primary_like` targets and
    # `scoreboard.assert_scored_cells_are_primary_like` refuses anything else on the scoring arm,
    # so the complementary half binds on the national-size March margin instead.
    "include_primary_like": "mask_label_switch",
    "include_complementary_like": "mask_label_switch",
    # An operand of `ValidationConfig._refuse_a_random_mask_only_design`, and the ONLY flag not in
    # that validator's disjunction — it is the design the §13.2 rule exists to exclude, not one of
    # the designed regimes that satisfies it. It has no implementation and gates no selection.
    "include_random_mask_sanity_check": "design_validity_operand",
}

# The four regime switches, as regime -> switch. NO FIELD IS ADDED OR REMOVED to build this:
# `runs.run_id` hashes `config.resolved_dict`, which is the whole model, so either direction
# re-identifies every run directory on disk and orphans `runs/f03023ac9f3a`. Changing a DEFAULT is
# free, because `config.yaml:74-97` pins all fourteen keys and no default reaches the resolved
# config — which is the opposite of what both `specs/deferred_items.md` and the roadmap asserted
# until 8ed7ecd.
REGIME_SWITCHES: dict[str, str] = {
    "long_consecutive_runs": "include_long_runs",
    "rolling_origin": "include_rolling_origin",
    "retrospective_smoothing": "include_retrospective_smoothing",
    "preliminary_to_final_vintage": "include_vintage_comparison",
}
```

- [ ] **Step 4: Record the kinds on `ValidationConfig`**

Replace the `ValidationConfig` docstring in `src/logging_employment/config.py:174-180`:

```python
    """§13's harness settings, adapted from Appendix A.

    THE SEVEN `include_*` SWITCHES ARE THREE DIFFERENT KINDS OF THING, declared in
    `contracts.VALIDATION_SWITCH_KINDS` and summarised here because this is where a reader meets
    them. Four are REGIME SWITCHES and gate their regime in `validate/harness.py`; two name INV-009
    mask LABELS (§13.2 steps 3 and 8) and gate no regime; one names a design with no implementation
    anywhere in the package and is an operand of `_refuse_a_random_mask_only_design` below. Nine of
    the thirteen regimes have no switch at all, so the set was never a partition.

    NO FIELD MAY BE ADDED OR REMOVED. `runs.run_id` hashes `resolved_dict`, which is
    `model_dump(mode="json")` — the whole model — so either direction re-identifies every run
    directory and orphans `runs/f03023ac9f3a`. Changing a DEFAULT is free: `config.yaml:74-97`
    pins all fourteen keys, so no default reaches the resolved config.

    `include_vintage_comparison` defaults False against Appendix A's True: measured 2026-09-07, no
    period in any staged table carries a second snapshot, and `release_vintage` is the reference
    quarter lowercased rather than a publication vintage. Turning it on is a fail-closed error in
    `regimes.py`, not a silent empty partition.
    """
```

- [ ] **Step 5: Amend Appendix A**

In `specs/logging-employment-spec.md`, replace the `validation:` block at `:2163-2171` with:

```yaml
validation:
  pseudo_suppression_seeds: [1024, 2048, 4096]
  # The seven include_* switches are THREE KINDS of thing, not one. Declared in
  # contracts.VALIDATION_SWITCH_KINDS and enforced by tests/unit/test_validation_switch_kinds.py.
  # design-validity operand: an operand of ValidationConfig._refuse_a_random_mask_only_design,
  # naming the design §13.2 prohibits as the ONLY one. No implementation; gates no selection.
  include_random_mask_sanity_check: true
  # mask-label switches: §13.2 steps 3 and 8. These name the INV-009 label a masked cell carries,
  # not a regime. Neither is wired to regime selection and neither should be read as if it were.
  include_primary_like: true
  include_complementary_like: true
  # regime switches: each gates one §13.3 regime. A regime excluded by its switch still appears in
  # the run manifest with a reason naming the switch — it does not vanish. Nine of the thirteen
  # regimes have no switch at all, so these four are not a partition of §13.3.
  include_long_runs: true             # -> long_consecutive_runs
  include_rolling_origin: true        # -> rolling_origin
  include_retrospective_smoothing: true   # -> retrospective_smoothing
  include_vintage_comparison: true    # -> preliminary_to_final_vintage
```

Leave the two `false` values in the repo's own `config.yaml` alone — Appendix A states the spec's
defaults and `config.yaml` states this deployment's, with its reasons already recorded at
`config.yaml:81-85`.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/unit/test_validation_switch_kinds.py tests/unit/test_config_validation_block.py -v`
Expected: 6 + 3 = 9 passed.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/config.py \
  specs/logging-employment-spec.md tests/unit/test_validation_switch_kinds.py
git commit -m "docs(validate): declare which KIND each Appendix A validation switch is"
```

---

### Task 8: The four regime switches gate their regimes

Closes R-S4C-12 and completes V4. Expect a manifest change with no scoreboard change: the shipped
`config.yaml` sets `include_retrospective_smoothing: false` and `include_vintage_comparison: false`,
so those two regimes' entries move from a disposition-derived reason to a config-derived one.

**Files:**
- Modify: `src/logging_employment/validate/harness.py:78-104`
- Test: `tests/integration/test_stage4_acceptance.py` (extend)

**Interfaces:**
- Consumes: `contracts.REGIME_SWITCHES` (Task 7), `spec.no_score_reason` (Task 4).
- Produces: no new symbol. The manifest's `reason` for a switched-off regime now names the switch.

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_stage4_acceptance.py`:

```python
def test_a_regime_excluded_by_its_switch_appears_with_a_reason_naming_the_switch(fixture_run):
    """R-S4C-12: excluded is not absent. A vanishing regime is the empty partition this refuses."""
    for regime, switch in (
        ("retrospective_smoothing", "include_retrospective_smoothing"),
        ("preliminary_to_final_vintage", "include_vintage_comparison"),
    ):
        entry = fixture_run.manifest["regimes"][regime]
        assert entry["n_scored"] == 0
        assert switch in entry["reason"], entry["reason"]


def test_the_config_derived_reason_still_carries_the_declared_one(fixture_run):
    """The switch is WHY it did not run here; the declared reason is why it could not anyway."""
    entry = fixture_run.manifest["regimes"]["preliminary_to_final_vintage"]
    assert "second snapshot" in entry["reason"]


def test_an_enabled_switch_leaves_its_regime_alone(fixture_run):
    """`include_long_runs` ships true, so `long_consecutive_runs` must still score."""
    entry = fixture_run.manifest["regimes"]["long_consecutive_runs"]
    assert entry["n_scored"] > 0
    assert "include_long_runs" not in str(entry.get("reason", ""))


def test_turning_the_vintage_switch_on_still_raises(fixture_run):
    """The fail-closed refusal must survive the switch gating, not be swallowed by it.

    `tests/unit/test_validate_declared_regimes.py::test_asking_for_the_vintage_regime_makes_the
    _harness_refuse` is the pin; this asserts the ORDER — the switch check must not return a
    config-derived reason for a regime the operator explicitly asked for.
    """
    del fixture_run
    cfg = _fixture_config()
    cfg = cfg.model_copy(
        update={"validation": cfg.validation.model_copy(update={"include_vintage_comparison": True})}
    )
    with pytest.raises(NotImplementedError, match="second snapshot"):
        run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY[:1], cfg)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: the first two FAIL — the reason names no switch today.

- [ ] **Step 3: Gate on the switch**

In `src/logging_employment/validate/harness.py`, add `REGIME_SWITCHES` to the contracts import:

```python
from ..contracts import REGIME_SWITCHES, HarmonizedData, assert_declared_provenance
```

Then replace the `if spec.disposition != "feasible":` block at `:87-104` with:

```python
        # THE SWITCH IS CHECKED FIRST, AND THE FAIL-CLOSED REFUSAL SECOND. Order matters: an
        # operator who turns `include_vintage_comparison` ON is ASKING for a regime this window
        # cannot support, and must get a refusal rather than a config-derived note. With the
        # switch OFF the ask was never made, so the note is the honest record.
        switch = REGIME_SWITCHES.get(name)
        if switch is not None and not getattr(config.validation, switch):
            # EXCLUDED, NOT ABSENT (R-S4C-12). A regime that vanished from the manifest when its
            # switch went off would leave a reader unable to tell it from a regime that never
            # existed, which is the empty-partition-as-success this stage refuses everywhere else.
            # The declared reason rides along: the switch says why it did not run HERE, and the
            # declared reason says why it could not have anyway.
            entry["reason"] = (
                f"excluded by `validation.{switch}: false`; its declared reason is "
                f"{spec.no_score_reason or 'none — this regime masks QCEW cells and would score'}"
            )
            regimes[name] = entry
            continue

        if spec.disposition == "cannot_run_on_d1":
            # FAIL CLOSED when the operator asks for a regime the data cannot support. Appendix A
            # ships `include_vintage_comparison: true`; this package defaults it false because no
            # period in any staged table carries a second snapshot. Reaching here means the switch
            # is ON, so this must RAISE — `select_targets` owns that refusal — rather than record a
            # disposition and move on, which would hand back an empty partition reading as
            # "scored, nothing wrong".
            select_targets(name, data.qcew_monthly, seed=0, config=config)
```

Delete the old `entry["reason"] = ("no second snapshot..." if ... else ...)` ternary and its
`regimes[name] = entry; continue` — a `vacuous_on_registry` regime whose switch is on now falls
through to the `spec.select is None` branch, which reads its declared reason. That branch is the
single place a non-scoring reason is written, which is the point of R-S4C-1.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py tests/unit/test_validate_declared_regimes.py -v`
Expected: all pass. `test_asking_for_the_vintage_regime_makes_the_harness_refuse` is the one to
watch — it must still raise.

Run: `uv run pytest tests/integration/test_d1_validation.py -v`
Expected: pass or skip. `test_a_refused_regime_is_recorded_with_its_reason_and_scores_nothing`
asserts `"second snapshot" in entry["reason"]`, which the composed reason still satisfies.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/validate/harness.py tests/integration/test_stage4_acceptance.py
git commit -m "feat(validate): the four regime switches gate their regimes"
```

---

### Task 9: The scores frame produces and declares all 26 of its columns

Closes R-S4C-14, R-S4C-15 and the dtype half of R-S4C-18. **These are one task, not two:** after
either half alone the scores frame is further from its schema than before, so neither has an
independently testable deliverable. Together the produced and declared column sets are equal.

The arithmetic, re-measured 2026-09-08: 23 produced + 3 (`mask_arm`, `replicate`,
`lookback_months_masked`) = 26; 20 declared + 6 (`raw_weight`, `anchor_basis`,
`reconciliation_status`, `decline_reason`, `residual`, `constraint_set_hash`) = 26.

**Files:**
- Modify: `src/logging_employment/contracts.py:410-431` (`VALIDATION_SCORE_SCHEMA`)
- Modify: `src/logging_employment/validate/harness.py:121-129`, `:172-200` (`_join_truth`)
- Test: `tests/integration/test_stage4_acceptance.py` (extend)

**Interfaces:**
- Consumes: nothing from Tasks 1–8.
- Produces:
  - `VALIDATION_SCORE_SCHEMA` grows to 26 entries.
  - `harness._mask_arm(targets: Sequence[MaskTarget]) -> str` — Task 10 consumes it.
  - `harness._join_truth(results, truth, system, targets, *, regime, seed, replicate)` — gains a
    positional `targets` and a keyword `replicate`.

- [ ] **Step 1: Write the failing test**

Append to `tests/integration/test_stage4_acceptance.py` (add
`from logging_employment.contracts import VALIDATION_SCORE_SCHEMA, validate_frame` to its imports):

```python
def test_the_scores_frame_produces_exactly_what_it_declares(fixture_run):
    """M11: 23 produced against 20 declared, overlapping in 17 — a three-way disagreement.

    `cli.py` called the produced set "a superset", which it was not: three declared columns were
    produced by nothing. Set equality, not containment, is the assertion.
    """
    assert set(fixture_run.scores.columns) == set(VALIDATION_SCORE_SCHEMA)
    validate_frame(fixture_run.scores, VALIDATION_SCORE_SCHEMA, "validation_scores")


def test_the_seed_column_is_int64_in_both_frames(fixture_run):
    """R-S4C-18: resolved toward the DECLARATION, not by weakening the schema to Int32.

    `pl.lit(seed)` infers Int32 on polars 1.44 while the metrics frame builds Int64 from Python
    dicts, so the two disagreed. Seeds come from `config.validation.pseudo_suppression_seeds` and
    nothing bounds them to 32 bits.
    """
    assert fixture_run.scores.schema["seed"] == pl.Int64
    assert fixture_run.metrics.schema["seed"] == pl.Int64


def test_the_two_constraint_hashes_are_different_columns(fixture_run):
    """M11: `masked_constraint_set_hash` is not a rename of `constraint_set_hash`.

    Neither may be dropped as a duplicate. The masked one is the hash of the system this replicate
    actually solved; the unmasked one rides in from `run_baselines` and is null on this fixture.
    """
    assert "constraint_set_hash" in fixture_run.scores.columns
    assert "masked_constraint_set_hash" in fixture_run.scores.columns
    assert fixture_run.scores["masked_constraint_set_hash"].null_count() == 0


def test_the_three_new_columns_are_derived_rather_than_constant(fixture_run):
    """A column with one value on every row records nothing. `mask_arm` legitimately has one."""
    scores = fixture_run.scores
    assert scores["mask_arm"].null_count() == 0
    assert scores["mask_arm"].unique().to_list() == ["state_total"]
    assert scores["replicate"].unique().to_list() == [0]
    # `lookback_months_masked` is the per-state masked-month count, so a blackout regime's rows
    # must carry more than a single-month regime's.
    blackout = scores.filter(pl.col("regime") == "long_consecutive_runs")
    single = scores.filter(pl.col("regime") == "small_cell_biased")
    assert blackout["lookback_months_masked"].max() > single["lookback_months_masked"].max()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: the four new tests FAIL — the first with a `SchemaMismatchError` naming
`missing=['replicate', 'mask_arm', 'lookback_months_masked'] extra=[...6 names...]`.

- [ ] **Step 3: Declare the six provenance columns**

In `src/logging_employment/contracts.py`, replace `VALIDATION_SCORE_SCHEMA` (`:407-431`):

```python
# One row per (regime, seed, replicate, estimator, cell): the raw scored observations, including
# the ones that were declined. Distinct in grain from VALIDATION_METRIC_SCHEMA below, and
# conflating the two is how R-COMP-10's denominator gets lost.
#
# `replicate` is the INDEX OF THE SEED in `config.validation.pseudo_suppression_seeds`, so it is
# 1:1 with `seed` on any single run and the two together are one key rather than two. It is carried
# anyway because `pseudo_suppression_seeds` is configurable and a reader comparing two runs needs
# the slot as well as the value. `replicates_per_regime` is a DIFFERENT number: it sizes the mask
# (`regimes.sample_targets`), not this loop's trip count.
#
# The last six are the PROVENANCE columns `run_baselines` already writes and this schema used to
# omit, which is what made a scored row auditable and the declaration wrong at the same time. They
# are declared rather than dropped (R-S4C-14). `constraint_set_hash` and
# `masked_constraint_set_hash` are BOTH here and are different columns: the first rides in from
# `run_baselines`, the second is the hash of the masked system this replicate solved. Neither is a
# rename of the other and neither may be dropped as a duplicate.
VALIDATION_SCORE_SCHEMA: dict[str, pl.DataType] = {
    "regime": pl.String,
    "seed": pl.Int64,
    "replicate": pl.Int64,
    "mask_arm": pl.String,
    "estimator_id": pl.String,
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "suppression_type": pl.String,
    "truth": pl.Float64,
    "estimate": pl.Float64,
    "estimate_integer": pl.Int64,
    "weight_basis": pl.String,
    "decline_kind": pl.String,
    "bound_status": pl.String,
    "selected_lower": pl.Float64,
    "selected_upper": pl.Float64,
    "masked_constraint_set_hash": pl.String,
    "lookback_months_masked": pl.Int64,
    "missing_set_size": pl.Int64,
    "raw_weight": pl.Float64,
    "anchor_basis": pl.String,
    "reconciliation_status": pl.String,
    "decline_reason": pl.String,
    "residual": pl.Float64,
    "constraint_set_hash": pl.String,
}
```

- [ ] **Step 4: Produce the three declared columns**

In `src/logging_employment/validate/harness.py`, add the `MaskTarget` import:

```python
from .mask import MaskTarget, apply_mask
```

Add `_mask_arm` beneath `_join_truth`:

```python
def _mask_arm(targets: Sequence[MaskTarget]) -> str:
    """The single INV-009 arm this replicate masked, or a refusal if it masked two.

    `MaskTarget.arm` was read by nothing anywhere in the package while every metric emit site
    passed the literal `"state_total"`; this is its first consumer, so the field stops being
    decorative. The scores frame carries the arm PER ROW and the metric emitters take one SCALAR
    per (regime, seed), so a replicate spanning two arms would label every metric row with one of
    them. `scoreboard._best` already refuses a two-arm regime downstream; refusing here names the
    replicate that produced it rather than the board that inherited it.
    """
    arms = sorted({target.arm for target in targets})
    if len(arms) != 1:
        raise ConceptViolationError(
            f"this replicate masked {len(arms)} mask arms ({', '.join(arms) or 'none'}); the "
            "metric emitters take one arm per (regime, seed), and pooling a state-total metric "
            "with a national-size one under a single label is the ambiguity §13.10 refuses"
        )
    return arms[0]
```

Replace `_join_truth` entirely:

```python
def _join_truth(
    results: pl.DataFrame,
    truth: pl.DataFrame,
    system: MaskedSystem,
    targets: Sequence[MaskTarget],
    *,
    regime: str,
    seed: int,
    replicate: int,
) -> pl.DataFrame:
    """Attach truth, masked bounds, the INV-009 label, the MASKED hash and the mask's own shape.

    The bounds come from `system`, never from the run directory's shipped
    `deterministic_bounds.parquet` — that table still carries the published value for a masked
    cell, so joining it would hand the harness the answer.

    The truth join is INNER on purpose: it drops every cell the mask did not hide, so a scored row
    that was never masked is impossible by construction rather than by assertion. The `arms` and
    `lookback` joins are INNER for the same reason — every surviving row was a target, so a null
    `mask_arm` is unconstructible rather than merely unexpected. Neither can fan out: `apply_mask`
    refuses a duplicated target, so `arms` is one row per (state, month) and `lookback` one per
    state.

    `lookback_months_masked` is the count of months THIS replicate masked for the row's state, not
    `config.validation.minimum_unmasked_lookback_months`. The global floor would write the same
    value on every row of every regime, which records nothing; the per-state count separates a
    twelve-month blackout from a single-month draw, which is the distinction §13.3's grain exists
    to make.
    """
    labelled = truth.select("state_fips", "reference_month", "truth", "suppression_type")
    bounds = system.bounds.select("cell_id", "selected_lower", "selected_upper", "bound_status")
    arms = pl.DataFrame(
        {
            "state_fips": [target.state_fips for target in targets],
            "reference_month": [target.reference_month for target in targets],
            "mask_arm": [target.arm for target in targets],
        },
        schema={"state_fips": pl.String, "reference_month": pl.String, "mask_arm": pl.String},
    )
    masked_months: dict[str, int] = {}
    for target in targets:
        masked_months[target.state_fips] = masked_months.get(target.state_fips, 0) + 1
    lookback = pl.DataFrame(
        {
            "state_fips": list(masked_months),
            "lookback_months_masked": list(masked_months.values()),
        },
        schema={"state_fips": pl.String, "lookback_months_masked": pl.Int64},
    )
    return (
        results.join(labelled, on=["state_fips", "reference_month"], how="inner")
        .join(bounds, on="cell_id", how="left")
        .join(arms, on=["state_fips", "reference_month"], how="inner")
        .join(lookback, on="state_fips", how="inner")
        .with_columns(
            pl.lit(regime).alias("regime"),
            # DTYPE DECLARED, not inferred: `pl.lit(1024)` is Int32 on polars 1.44 while the
            # metrics frame builds Int64 from Python dicts, so the two frames disagreed on `seed`
            # and `validate_frame` would have raised on dtype even after the column sets matched.
            pl.lit(seed, dtype=pl.Int64).alias("seed"),
            pl.lit(replicate, dtype=pl.Int64).alias("replicate"),
            pl.lit(system.constraint_set_hash).alias("masked_constraint_set_hash"),
            pl.col("truth").cast(pl.Float64),
        )
    )
```

- [ ] **Step 5: Pass the new arguments from the loop**

In `run_pseudo_suppression`, change the seed loop header and the `_join_truth` call:

```python
        for replicate, seed in enumerate(config.validation.pseudo_suppression_seeds):
            targets = select_targets(name, data.qcew_monthly, seed=seed, config=config)
            if not targets:
                continue
            masked, truth = apply_mask(data, targets)
            assert_no_retained_truth(masked, truth)
            system = mask_and_solve(data, targets, config)
            results, _audit = run_baselines(masked, config, estimators=estimators)
            scored = _join_truth(
                results, truth, system, targets, regime=name, seed=seed, replicate=replicate
            )
```

Leave the five metric emit calls alone — Task 10 changes them.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: all pass.

Run: `uv run pytest tests/integration/test_validation_golden.py -v`
Expected: pass — the golden is the METRICS table, which this task does not touch.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/validate/harness.py \
  tests/integration/test_stage4_acceptance.py
git commit -m "fix(validate): the scores frame produces and declares the same 26 columns"
```

---

### Task 10: `decline_and_basis_report` takes an arm, and the golden is regenerated deliberately

Closes R-S4C-16 and V3. **Read the correction in Step 1 first:** V3's "270 declines rows" is the D1
figure, not the golden's.

**Files:**
- Modify: `src/logging_employment/validate/metrics.py:206-237`
- Modify: `src/logging_employment/validate/harness.py` (the five metric emit calls)
- Modify: `tests/fixtures/validation/validation_metrics_golden.parquet` (regenerate, once)
- Test: `tests/integration/test_validation_golden.py` (extend)

**Interfaces:**
- Consumes: `harness._mask_arm` (Task 9).
- Produces: `decline_and_basis_report(scores: pl.DataFrame, *, regime: str, seed: int, arm: str) ->
  pl.DataFrame` — now matching its four siblings' signature exactly.

- [ ] **Step 1: Note the corrected figures before you start**

V3 says the golden "gains `mask_arm` values on the 270 `declines` rows". Measured 2026-09-08, that
is the D1 count (9 scoring regimes × 10 estimators × 3 seeds = 270). The committed golden holds
**70** (7 scoring regimes × 10 estimators × 1 seed = 70) out of 1,168 rows, all with NULL
`mask_arm`. Both numbers are right about their own run; V3 attaches the D1 one to the fixture file.
Pin 70 and the property. Record this correction in your task report.

- [ ] **Step 2: Write the failing test**

Append to `tests/integration/test_validation_golden.py`:

```python
def test_no_metric_family_carries_a_null_mask_arm(fixture_run):
    """M12: the `declines` family carried a NULL `mask_arm` on 70 of 70 rows here, 270 of 270 on D1.

    `validation_metrics` IS gated by `validate_frame` and the gate did not see it: `validate_frame`
    compares columns and dtypes, and `dict[str, pl.DataType]` has no nullability slot. The cause
    was that `decline_and_basis_report` took no `arm` parameter while its four siblings did.
    """
    assert fixture_run.metrics["mask_arm"].null_count() == 0
    declines = fixture_run.metrics.filter(pl.col("metric_family") == "declines")
    assert declines.height == 70
    assert declines["mask_arm"].unique().to_list() == ["state_total"]


def test_the_arm_comes_from_the_mask_rather_than_a_literal(fixture_run):
    """R-S4C-16: `MaskTarget.arm` was read by nothing; this is its first consumer.

    Every selector builds `state_total` targets today, so the VALUE does not change — which is
    exactly why the literal survived. What changes is where it comes from.
    """
    assert fixture_run.metrics["mask_arm"].unique().to_list() == ["state_total"]
    assert fixture_run.scores["mask_arm"].unique().to_list() == ["state_total"]
```

- [ ] **Step 3: Run it to make sure it fails**

Run: `uv run pytest tests/integration/test_validation_golden.py -v`
Expected: `test_no_metric_family_carries_a_null_mask_arm` FAILS with `assert 70 == 0`.

- [ ] **Step 4: Give the report its arm**

In `src/logging_employment/validate/metrics.py`, change the signature at `:206` and the row dict at
`:218-235`:

```python
def decline_and_basis_report(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
```

Append to that function's docstring, before the closing quotes:

```
    `arm` matches the four sibling emitters. Without it this family wrote a NULL `mask_arm` on
    every row it produced — 70 of 70 on the committed fixture, 270 of 270 on D1, against zero nulls
    in each of the other four families — and `build_scoreboard` joins these rows onto the point
    rows by (regime, seed, estimator_id), so the null rode into every downstream read of the
    own/fallback split without ever failing `validate_frame`.
```

Add `"mask_arm": arm,` to the row dict, immediately after `"seed": seed,`:

```python
            {
                "regime": regime,
                "seed": seed,
                "mask_arm": arm,
                "estimator_id": str(estimator),
```

- [ ] **Step 5: Derive the arm at all five emit sites**

In `src/logging_employment/validate/harness.py`, inside the seed loop, add the derivation
immediately after the `if not targets: continue` guard:

```python
            arm = _mask_arm(targets)
```

Then replace every `arm="state_total"` with `arm=arm` in the five emit calls, and add
`arm=arm` to the `decline_and_basis_report` call:

```python
            all_metrics.append(point_metrics(scored, regime=name, seed=seed, arm=arm))
            all_metrics.append(bound_metrics(scored, regime=name, seed=seed, arm=arm))
            all_metrics.append(decline_and_basis_report(scored, regime=name, seed=seed, arm=arm))
            all_metrics.append(probabilistic_metrics(scored, regime=name, seed=seed, arm=arm))
```

and in the `constraint_metrics(...)` call, change its trailing `arm="state_total",` to `arm=arm,`.
Leave that call's long explanatory comment about `_anchor_residuals` untouched.

- [ ] **Step 6: Regenerate the golden, and INSPECT the diff before accepting it**

V3 requires this be a deliberate, reviewed step. Write the candidate to a scratch path first:

```bash
uv run python -c "
import polars as pl
from pathlib import Path
from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.harness import run_pseudo_suppression

cfg = load_config(Path('config.yaml'))
cfg = cfg.model_copy(update={'validation': cfg.validation.model_copy(
    update={'replicates_per_regime': 3, 'pseudo_suppression_seeds': [1024]})})
res = run_pseudo_suppression(HarmonizedData.load(Path('tests/fixtures/baselines')), REGISTRY, cfg)
res.metrics.write_parquet('/tmp/validation_metrics_candidate.parquet')
print('rows', res.metrics.height)
"
```

Then diff it against the committed golden, column by column:

```bash
uv run python -c "
import polars as pl
key = ['regime','seed','estimator_id','metric_family','metric_name']
old = pl.read_parquet('tests/fixtures/validation/validation_metrics_golden.parquet').sort(key)
new = pl.read_parquet('/tmp/validation_metrics_candidate.parquet').sort(key)
print('columns equal:', old.columns == new.columns)
print('heights:', old.height, new.height)
moved = [c for c in old.columns if not old[c].equals(new[c])]
print('columns that moved:', moved)
for c in moved:
    o, n = old[c], new[c]
    print(f'  {c}: old nulls={o.null_count()} new nulls={n.null_count()} '
          f'new values={sorted(set(n.drop_nulls().to_list()))[:5]}')
"
```

Expected output — **stop and report if it differs**:

```
columns equal: True
heights: 1168 1168
columns that moved: ['mask_arm']
  mask_arm: old nulls=70 new nulls=0 new values=['state_total']
```

Only when the diff reads exactly that, promote it:

```bash
cp /tmp/validation_metrics_candidate.parquet \
   tests/fixtures/validation/validation_metrics_golden.parquet
```

Do NOT use a `--force-regen` style shortcut, and do not promote a candidate whose diff you did not
read.

- [ ] **Step 7: Run the tests**

Run: `uv run pytest tests/integration/test_validation_golden.py -v`
Expected: all pass, including `test_the_metrics_match_the_golden` and
`test_the_golden_matches_the_declared_schema`.

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/logging_employment/validate/metrics.py src/logging_employment/validate/harness.py \
  tests/fixtures/validation/validation_metrics_golden.parquet \
  tests/integration/test_validation_golden.py
git commit -m "fix(validate): the declines family carries the mask arm it was measured on"
```

---

### Task 11: `validation_scoreboard` gets a declared schema and a §7 field list

Closes R-S4C-17. Note the correction: M13's aside that "§15.1 names the artifact" is false —
`scoreboard` appears nowhere in `specs/logging-employment-spec.md`, whose §15.1 list stops at
`validation_metrics.parquet`. The obligation R-S4C-17 states is unaffected.

**Files:**
- Modify: `src/logging_employment/contracts.py` (after `VALIDATION_METRIC_SCHEMA`)
- Modify: `src/logging_employment/validate/scoreboard.py:31-60` (`build_scoreboard`)
- Modify: `specs/logging-employment-spec.md` (after §7.13, `:741`)
- Test: `tests/unit/test_contracts_validation.py` (extend)

**Interfaces:**
- Consumes: `VALIDATION_METRIC_SCHEMA` unchanged.
- Produces: `contracts.VALIDATION_SCOREBOARD_SCHEMA: dict[str, pl.DataType]` — 13 entries. Task 12
  gates on it.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_contracts_validation.py`:

```python
def test_the_scoreboard_schema_is_declared_and_distinct():
    """M13: no scoreboard schema existed, though `cli.py` has persisted the artifact since plan 11."""
    board = contracts.VALIDATION_SCOREBOARD_SCHEMA
    assert contracts.schema_fingerprint(board) != contracts.schema_fingerprint(
        contracts.VALIDATION_METRIC_SCHEMA
    )
    assert board["wape"] == pl.Float64
    assert board["seed"] == pl.Int64
    # The gate's comparand needs its base, exactly as a metric row does (R-COMP-10).
    assert "denominator" in board
    assert "denominator_basis" in board


def test_an_empty_scoreboard_still_carries_its_columns():
    """`build_scoreboard` returned a bare DataFrame when no metric row existed, which no gate can
    check: `validate_frame` would report all thirteen columns missing rather than an empty board."""
    from logging_employment.validate.scoreboard import build_scoreboard

    empty = build_scoreboard(pl.DataFrame())
    assert empty.height == 0
    contracts.validate_frame(
        empty, contracts.VALIDATION_SCOREBOARD_SCHEMA, "validation_scoreboard"
    )
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_contracts_validation.py -v`
Expected: FAIL — `AttributeError: module 'logging_employment.contracts' has no attribute
'VALIDATION_SCOREBOARD_SCHEMA'`.

- [ ] **Step 3: Declare the schema**

In `src/logging_employment/contracts.py`, insert after `VALIDATION_METRIC_SCHEMA`:

```python
# One row per (regime, seed, estimator): §13.10's comparand, with the provenance that makes it
# readable. Declared 2026-09-08; the artifact has been persisted by `cli.py::validate_command`
# since plan 11 with no schema anywhere, and §15.1's nine-item release-table list does not name it
# either — the roadmap is the only place it appears.
#
# `wape` is the one column that may be NULL: an estimator that declined every cell has no error,
# not zero error, and `scoreboard._best` filters on that rather than sorting nulls first. Every
# other column is non-null by construction and `VALIDATION_REQUIRED_NON_NULL` says so.
VALIDATION_SCOREBOARD_SCHEMA: dict[str, pl.DataType] = {
    "regime": pl.String,
    "seed": pl.Int64,
    "mask_arm": pl.String,
    "estimator_id": pl.String,
    "wape": pl.Float64,
    "denominator": pl.Float64,
    "denominator_basis": pl.String,
    "n_scored": pl.Int64,
    "n_declined_by_design": pl.Int64,
    "n_declined_data_gap": pl.Int64,
    "n_declined_reconciliation_failure": pl.Int64,
    "n_own_estimator": pl.Int64,
    "n_establishment_fallback": pl.Int64,
}
```

- [ ] **Step 4: Give the empty board its columns**

In `src/logging_employment/validate/scoreboard.py`, add the import:

```python
from ..contracts import VALIDATION_SCOREBOARD_SCHEMA
```

and add this as the first statement of `build_scoreboard`, before `headline = ...`:

```python
    if metrics.is_empty():
        # SHAPED, not bare. An empty `pl.DataFrame()` carries no columns, so a `validate_frame`
        # gate on it reports thirteen missing columns rather than an empty board — a schema
        # failure where the truth is "this run scored nothing", which are different findings.
        return pl.DataFrame(schema=VALIDATION_SCOREBOARD_SCHEMA)
```

Also add a line to `build_scoreboard`'s docstring, after its existing final paragraph:

```
    The declared shape is `contracts.VALIDATION_SCOREBOARD_SCHEMA`; a column added here must be
    added there, or `cli.py::validate_command` refuses the write.
```

- [ ] **Step 5: Add both §7 field lists to the spec**

In `specs/logging-employment-spec.md`, insert after §7.13's closing text (`:741`, before the `---`
at `:743`):

````markdown
### 7.14 `validation_score`

One row per estimator, holdout regime, seed, replicate and masked cell — including the cells a
declining estimator could not weight, which are rows with a null estimate rather than absences.
The raw observations §13.5-§13.8's metrics are computed from.

```text
regime
seed
replicate
mask_arm
estimator_id
cell_id
state_fips
reference_month
suppression_type
truth
estimate
estimate_integer
weight_basis
decline_kind
bound_status
selected_lower
selected_upper
masked_constraint_set_hash
lookback_months_masked
missing_set_size
raw_weight
anchor_basis
reconciliation_status
decline_reason
residual
constraint_set_hash
```

`replicate` is the index of the seed within `validation.pseudo_suppression_seeds`, not a count of
masked cells — `replicates_per_regime` sizes the mask and is a different quantity.
`lookback_months_masked` is the number of months this replicate masked for that row's state.
`constraint_set_hash` and `masked_constraint_set_hash` are different columns: the first is the
system the estimators were run against, the second the masked system whose bounds were joined on.

### 7.15 `validation_scoreboard`

One row per holdout regime, seed and estimator: the headline point metric with the provenance
§13.10's promotion gate needs to read it.

```text
regime
seed
mask_arm
estimator_id
wape
denominator
denominator_basis
n_scored
n_declined_by_design
n_declined_data_gap
n_declined_reconciliation_failure
n_own_estimator
n_establishment_fallback
```

`wape` MAY be null: an estimator that declined every cell has no error, not zero error, and a
ranking that treats null as smallest would crown it. Every other column MUST carry a value. §15.1's
release-table list does not name this artifact; it is written to the run directory beside
`validation_metrics.parquet`.
````

- [ ] **Step 6: Run the tests**

Run: `uv run pytest tests/unit/test_contracts_validation.py tests/integration/test_validation_golden.py -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/validate/scoreboard.py \
  specs/logging-employment-spec.md tests/unit/test_contracts_validation.py
git commit -m "feat(contracts): declare validation_score and validation_scoreboard field lists"
```

---

### Task 12: `validate_frame` gates all three tables, and the required columns are non-null

Closes R-S4C-18 and R-S4C-19. Note R-S4C-19's explicit scope limit: `validate_frame` compares
columns and dtypes only and `dict[str, pl.DataType]` has no nullability slot, so this must NOT be
read as "add nullability to every schema in `contracts.py`". Extending the schema representation
package-wide is out of scope.

**Files:**
- Modify: `src/logging_employment/contracts.py` (after `VALIDATION_SCOREBOARD_SCHEMA`)
- Modify: `src/logging_employment/cli.py:442-459`
- Test: `tests/unit/test_contracts_validation.py` (extend),
  `tests/integration/test_validate_cli.py` (verify unchanged)

**Interfaces:**
- Consumes: all three schemas (Tasks 9 and 11).
- Produces: `contracts.VALIDATION_REQUIRED_NON_NULL: dict[str, tuple[str, ...]]` and
  `contracts.assert_required_columns_present(frame: pl.DataFrame, name: str) -> None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_contracts_validation.py`:

```python
def test_a_null_in_a_required_column_is_refused():
    frame = pl.DataFrame(
        {
            "regime": ["small_cell_biased", None],
            "seed": [1024, 1024],
            "mask_arm": ["state_total", "state_total"],
            "estimator_id": ["equal_residual", "equal_residual"],
            "metric_family": ["point", "point"],
            "denominator": [1.0, 1.0],
            "denominator_basis": ["masked_cell_rows", "masked_cell_rows"],
            "n_scored": [1, 1],
        }
    )
    with pytest.raises(ConceptViolationError, match="regime"):
        contracts.assert_required_columns_present(frame, "validation_metrics")


def test_a_table_with_no_declared_requirement_is_refused_rather_than_waved_through():
    """A silent pass for an unknown name would make the gate look applied where it was not."""
    with pytest.raises(ConceptViolationError, match="invented_table"):
        contracts.assert_required_columns_present(pl.DataFrame(), "invented_table")


def test_metric_name_is_not_required_and_the_reason_is_recorded():
    """Measured: NULL on all 70 `declines` rows, because that family emits counts not one metric.

    Recorded rather than fixed (decided 2026-09-08): naming it would move a second golden column
    beyond what V3 authorises. If a later plan gives declines rows a metric_name, this test is the
    one to delete.
    """
    assert "metric_name" not in contracts.VALIDATION_REQUIRED_NON_NULL["validation_metrics"]


def test_wape_is_not_required_because_an_all_declining_estimator_has_no_error():
    assert "wape" not in contracts.VALIDATION_REQUIRED_NON_NULL["validation_scoreboard"]
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `uv run pytest tests/unit/test_contracts_validation.py -v`
Expected: FAIL — no `assert_required_columns_present`.

- [ ] **Step 3: Declare the required columns and the assertion**

In `src/logging_employment/contracts.py`, insert after `VALIDATION_SCOREBOARD_SCHEMA`:

```python
# The columns whose MEANING requires a value, per persisted validation table (R-S4C-19).
#
# SCOPE, stated because the obvious reading overreaches. `validate_frame` compares columns and
# dtypes, and `dict[str, pl.DataType]` has no nullability slot — so this is a second, narrower
# declaration beside the schemas rather than an extension of them. Adding nullability to every
# schema in this module is explicitly out of scope.
#
# Each list holds only columns that are non-null BY CONSTRUCTION, not columns that merely happen to
# be non-null on a measured run. `selected_lower` and `bound_status` are absent for that reason:
# they arrive through a LEFT join on `cell_id`, so their nullability is a property of the data.
# `weight_basis` is absent because a declining row has no weight to describe.
# `metric_name` is absent because the `declines` family emits counts rather than one named metric
# and writes null there on every row — measured 2026-09-08, 70 of 70 on the committed fixture.
# That is the same shape as the `mask_arm` defect this table exists to close, and it is RECORDED
# rather than fixed: naming that metric would move a second column of the golden.
# `wape` is absent because an estimator that declined every cell has no error, not zero error.
VALIDATION_REQUIRED_NON_NULL: dict[str, tuple[str, ...]] = {
    "validation_scores": (
        "regime",
        "seed",
        "replicate",
        "mask_arm",
        "lookback_months_masked",
        "estimator_id",
        "cell_id",
        "state_fips",
        "reference_month",
        "truth",
        "suppression_type",
        "masked_constraint_set_hash",
    ),
    "validation_metrics": (
        "regime",
        "seed",
        "mask_arm",
        "estimator_id",
        "metric_family",
        "denominator",
        "denominator_basis",
        "n_scored",
    ),
    "validation_scoreboard": (
        "regime",
        "seed",
        "mask_arm",
        "estimator_id",
        "denominator",
        "denominator_basis",
        "n_scored",
        "n_own_estimator",
        "n_establishment_fallback",
    ),
}


def assert_required_columns_present(frame: pl.DataFrame, name: str) -> None:
    """Refuse a persisted validation table carrying a null where its meaning requires a value.

    The case that motivated this shipped: `validation_metrics` IS gated by `validate_frame`, and
    the gate did not see that the `declines` family wrote a NULL `mask_arm` on every row it
    produced, because it checks columns and dtypes and not nullity.

    An unknown `name` RAISES rather than passing. A silent pass would let a caller believe a table
    was gated when the gate had nothing to say about it, which is the same class of quiet success
    this stage refuses everywhere else.
    """
    required = VALIDATION_REQUIRED_NON_NULL.get(name)
    if required is None:
        raise ConceptViolationError(
            f"{name} declares no required-non-null columns; the declared tables are "
            f"{sorted(VALIDATION_REQUIRED_NON_NULL)}. Declare its columns or do not gate it — a "
            "silent pass would read as a check that ran."
        )
    offending = [
        (column, frame[column].null_count())
        for column in required
        if column in frame.columns and frame[column].null_count()
    ]
    if offending:
        raise ConceptViolationError(
            f"{name}: null values in column(s) whose meaning requires one — "
            f"{', '.join(f'{column} ({count} rows)' for column, count in offending)}"
        )
```

- [ ] **Step 4: Gate all three tables at the write site**

In `src/logging_employment/cli.py`, extend the `validate_command` import at `:422`:

```python
    from .contracts import (
        VALIDATION_METRIC_SCHEMA,
        VALIDATION_SCORE_SCHEMA,
        VALIDATION_SCOREBOARD_SCHEMA,
        HarmonizedData,
        assert_required_columns_present,
        validate_frame,
    )
```

Replace the comment and single gate at `:442-447` with:

```python
    # ALL THREE TABLES, gated before anything is written. `validation_scores` used to be excluded
    # with a comment calling its columns "a superset of VALIDATION_SCORE_SCHEMA", which was not
    # true in either direction: measured 2026-09-08, 23 produced against 20 declared with 17 in
    # common, so three declared columns were produced by nothing and six produced ones were
    # declared nowhere. The nullity pass is separate because `validate_frame` compares columns and
    # dtypes only, and the defect that motivated it — a NULL `mask_arm` on every `declines` row —
    # sat inside a table the schema gate already passed.
    for frame, schema, table in (
        (result.scores, VALIDATION_SCORE_SCHEMA, "validation_scores"),
        (result.metrics, VALIDATION_METRIC_SCHEMA, "validation_metrics"),
        (result.scoreboard, VALIDATION_SCOREBOARD_SCHEMA, "validation_scoreboard"),
    ):
        validate_frame(frame, schema, table)
        assert_required_columns_present(frame, table)
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/test_contracts_validation.py -v`
Expected: all pass.

Run: `uv run pytest tests/integration/test_validate_cli.py -v`
Expected: pass, or SKIP if it needs `data/staged`. This is the test that exercises the write site;
if it skips, run the gate by hand instead and report which you did:

```bash
uv run python -c "
import polars as pl
from pathlib import Path
from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import load_config
from logging_employment.contracts import (
    VALIDATION_METRIC_SCHEMA, VALIDATION_SCORE_SCHEMA, VALIDATION_SCOREBOARD_SCHEMA,
    HarmonizedData, assert_required_columns_present, validate_frame)
from logging_employment.validate.harness import run_pseudo_suppression
cfg = load_config(Path('config.yaml'))
cfg = cfg.model_copy(update={'validation': cfg.validation.model_copy(
    update={'replicates_per_regime': 3, 'pseudo_suppression_seeds': [1024]})})
r = run_pseudo_suppression(HarmonizedData.load(Path('tests/fixtures/baselines')), REGISTRY, cfg)
for f, s, n in ((r.scores, VALIDATION_SCORE_SCHEMA, 'validation_scores'),
                (r.metrics, VALIDATION_METRIC_SCHEMA, 'validation_metrics'),
                (r.scoreboard, VALIDATION_SCOREBOARD_SCHEMA, 'validation_scoreboard')):
    validate_frame(f, s, n); assert_required_columns_present(f, n); print(n, 'OK', f.height, 'rows')
"
```

Expected: three `OK` lines.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/cli.py \
  tests/unit/test_contracts_validation.py
git commit -m "feat(validate): gate all three validation tables on schema and required nullity"
```

---

### Task 13: The run id and the scoreboard do not move

Closes V1 and V2 — the two checks that say this whole plan was a declaration exercise and not a
behaviour change. V1 must be asserted, not assumed.

**Files:**
- Test: `tests/integration/test_stage4_acceptance.py` (extend)

**Interfaces:**
- Consumes: everything. This task adds no source change; if a test here fails, the fix belongs in
  the task that broke it.

- [ ] **Step 1: Write the acceptance tests**

Append to `tests/integration/test_stage4_acceptance.py` (add
`from logging_employment.cli import _input_digests` and
`from logging_employment.runs import run_id` to its imports):

```python
@pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(),
    reason="data/staged is gitignored; the run id is a function of the input digests",
)
def test_the_shipped_config_still_resolves_to_the_stage_4_acceptance_run():
    """V1: the sharpest single check that no config field was added or removed.

    `run_id` hashes `resolved_dict(cfg)` — the whole pydantic model — and the input digests. This
    cannot use the `staged_repo` fixture: that rewrites every `storage.*_uri` into a tmp path and
    copies the smaller fixture parquets, so both halves of the payload differ by construction. It
    needs the real `config.yaml` and the real staged layer.
    """
    cfg = load_config(REPO / "config.yaml")
    assert run_id(cfg, _input_digests(cfg)) == "f03023ac9f3a"


def test_no_scoring_regime_gained_or_lost_a_score(fixture_run):
    """V2: seven regimes score on this fixture and the same seven must score after.

    SEVEN, not V2's nine: nine is the D1 figure. `structural_break` and `naics_transition` find no
    in-window month on a fixture that carries 2023 alone, so they draw no target here.
    """
    scoring = {
        name
        for name, entry in fixture_run.manifest["regimes"].items()
        if entry["n_scored"] > 0
    }
    assert scoring == {
        "small_cell_biased",
        "concentration_proxy",
        "clustered_states_within_month",
        "long_consecutive_runs",
        "whole_state_year_blocks",
        "whole_seasonal_blocks",
        "regional_blocks",
    }


def test_the_scoreboard_is_unchanged_by_everything_in_this_plan(fixture_run):
    """V2: the board must be byte-identical, because nothing here touches a scored number.

    The `mask_arm` Task 10 added rides on the `declines` rows, and `build_scoreboard` joins those
    onto the point rows by (regime, seed, estimator_id) — `mask_arm` is not in the join key, so the
    join is unmoved. This asserts that rather than trusting it.
    """
    board = fixture_run.scoreboard
    assert board.height == 70
    assert board["mask_arm"].unique().to_list() == ["state_total"]
    assert board["wape"].null_count() == 13
    assert board["regime"].n_unique() == 7


def test_exactly_four_regimes_carry_a_changed_reason(fixture_run):
    """V4: two gain measured reasons and two gain config-derived ones. No other entry moves.

    SIX regimes carry a reason on this fixture, not four — measured 2026-09-08 before any of this
    plan landed. `structural_break` and `naics_transition` draw no target here (the fixture carries
    2023 alone, and their windows are 2020-2022), so `harness.py`'s selector-returned-nothing
    branch already gave each of them a reason and this plan does not touch either. V4's "exactly
    four" is about which reasons CHANGE, so this asserts the four individually and pins the other
    two as untouched rather than asserting a set of four that was never four.
    """
    regimes = fixture_run.manifest["regimes"]
    for name in ("rolling_origin", "cbp_size_gaps"):
        assert "2026-09-08" in regimes[name]["reason"], name
    for name in ("retrospective_smoothing", "preliminary_to_final_vintage"):
        assert "excluded by `validation.include_" in regimes[name]["reason"], name
    for name in ("structural_break", "naics_transition"):
        assert "no eligible target" in regimes[name]["reason"] or "carries no population" in (
            regimes[name]["reason"]
        ), name
    with_reason = {name for name, entry in regimes.items() if entry.get("reason")}
    assert with_reason == {
        "rolling_origin",
        "cbp_size_gaps",
        "retrospective_smoothing",
        "preliminary_to_final_vintage",
        "structural_break",
        "naics_transition",
    }
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/integration/test_stage4_acceptance.py -v`
Expected: all pass, with the V1 test skipped when `data/staged` is absent. If V1 fails with a
different run id, a `ValidationConfig` field was added or removed somewhere in Tasks 1–12 — find it
before doing anything else; that is the failure this test exists for.

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: green. The suite runs in parallel and includes `slow` tests; wall clock is the slowest
module. Report the exact counts, including skips — a skipped integration module is not a passing
one, and several here skip without `data/staged`.

- [ ] **Step 4: Lint**

Run: `uv run ruff check src tests && uv run ruff format --check src tests`
Expected: clean. Then `uv run interrogate src` — expected 100%, since every new `src/` function in
this plan carries a docstring.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_stage4_acceptance.py
git commit -m "test(validate): pin the run id, the scored set, and the scoreboard"
```

---

## Self-Review

**Spec coverage.** Every requirement maps to a task: R-S4C-1 → 4; R-S4C-2 → 4 (pin) + 12;
R-S4C-3 → 4; R-S4C-4 → 3 + 5; R-S4C-5 → 2; R-S4C-6, R-S4C-7, R-S4C-8 → 6; R-S4C-9 → 4;
R-S4C-10 → 7; R-S4C-11 → Global Constraints + 7 + 13 (V1); R-S4C-12 → 8; R-S4C-13 → 7;
R-S4C-14, R-S4C-15 → 9; R-S4C-16 → 10; R-S4C-17 → 11; R-S4C-18 → 9 (dtype) + 12 (gate);
R-S4C-19 → 12; R-S4C-20 → 1. Verifications: V1, V2, V4 → 13; V3 → 10; V5 → 1; V6 → 6.

**Out of scope, per spec §4 and confirmed here:** M5's pooled-intensity contamination is recorded
in Task 6's docstring and not fixed; neither regime is made to score; no CI and no `network` /
`slow` marker work; no identifier is renamed.

**Four corrections this plan carries against its own spec,** each measured rather than argued:

1. **V3's 270 is the D1 count; the golden holds 70.** Task 10 pins 70 and the property.
2. **M13's "§15.1 names the artifact" is false** — `scoreboard` appears nowhere in the main spec.
   R-S4C-17's obligation is unaffected; Task 11 records the correction in the new §7.15.
3. **R-S4C-5's refusal cannot live in `assert_no_future_rows`.** A truncated frame never contains
   its own origin. Task 2 puts it in `rolling_origin_frames`, which holds the panel, and writes the
   reason into the docstring.
4. **V4's "exactly four regimes" counts CHANGED reasons, not regimes carrying one.** Measured
   2026-09-08 on the fixture before any of this landed, six carry a reason: the four V4 names plus
   `structural_break` and `naics_transition`, which draw no in-window target and already hit the
   harness's selector-returned-nothing branch. Task 13 asserts the four individually and pins the
   other two as untouched.

**One constraint derived, not given:** R-S4C-11 forbids removing a `ValidationConfig` field.
Because `resolved_dict` is `model_dump(mode="json")`, adding one re-hashes `run_id` identically —
so V1 forbids both directions. That is why Task 3 derives the rolling origins from the panel
instead of taking the config key R-S4C-4's wording invites.

**One trap worth naming for the implementer:** `rolling_origin_frames` is a generator, so a
validation `raise` written into its body does not execute until a caller iterates. Measured — the
inline version returned a generator and raised nothing. Task 2 Step 1(b) covers it.

## File Structure

| File | Responsibility after this plan |
| --- | --- |
| `src/logging_employment/errors.py` | Gains `LeakageError` — the typed class the two §13.4 guards raise (R-S4C-20). |
| `src/logging_employment/validate/leakage.py` | Both guards raise `LeakageError`; `assert_no_future_rows` gains a `periods` universe and refuses an origin outside it (R-S4C-5, R-S4C-20). |
| `src/logging_employment/validate/regimes.py` | `RegimeSpec` gains `no_select_kind`; `rolling_origins()` derives the origins; `cbp_size_gap_keys` sorts before sampling; the two CBP docstrings state M3/M4/M5 (R-S4C-1, R-S4C-4, R-S4C-6, R-S4C-7, R-S4C-8). |
| `src/logging_employment/validate/harness.py` | Reasons derived from kind and switch, not templated; the rolling-origin guard runs here; the scored frame carries `replicate` / `mask_arm` / `lookback_months_masked` and an Int64 `seed` (R-S4C-1, R-S4C-2, R-S4C-3, R-S4C-4, R-S4C-9, R-S4C-12, R-S4C-15). |
| `src/logging_employment/validate/metrics.py` | `decline_and_basis_report` takes `arm` and names its metric (R-S4C-16). |
| `src/logging_employment/contracts.py` | `VALIDATION_SCORE_SCHEMA` +6 provenance columns; new `VALIDATION_SCOREBOARD_SCHEMA`; new `NON_NULL_VALIDATION_COLUMNS` + `assert_non_null`; `assert_declared_provenance` learns `mask_arm` (R-S4C-14, R-S4C-17, R-S4C-19). |
| `src/logging_employment/cli.py` | `validate_command` gates all three tables with `validate_frame` + `assert_non_null` (R-S4C-18, R-S4C-19). |
| `src/logging_employment/config.py` | `ValidationConfig`'s docstring states each switch's KIND (R-S4C-10, R-S4C-13). No field added or removed. |
| `specs/logging-employment-spec.md` | Appendix A's `validation:` block gains per-switch KIND comments; §7 gains `7.14 validation_score` and `7.15 validation_scoreboard` field lists (R-S4C-10, R-S4C-13, R-S4C-17). |
| `tests/unit/test_validate_leakage_guards.py` | **New.** Typed-error and `-O` survival tests, and the malformed-origin refusal (V5). |
| `tests/unit/test_validate_cbp_gap.py` | **New.** The state-year shape of the gap, and cross-process determinism (V6). |
| `tests/unit/test_validate_regime_reasons.py` | **New.** Every regime's kind/switch/reason wiring, checked structurally. |
| `tests/unit/test_contracts_validation.py` | Extended: the §7.14 / §7.15 field lists parsed **from the spec file** and compared to the schemas; the non-null declarations. |
| `tests/unit/test_config_validation_block.py` | Extended: the fourteen-field surface and the resolved-config digest (V1, cheap half). |
| `tests/integration/test_d1_validation.py` | The zero-score pin is strengthened to reject a deferral and to require a reason the package declares (R-S4C-2); the refused-regime test expects a config-derived reason. |
| `tests/integration/test_validation_golden.py` | Unchanged assertions; its fixture parquet is regenerated once, reviewed. |
| `tests/fixtures/validation/validation_metrics_golden.parquet` | Regenerated: 70 `declines` rows gain `mask_arm` and `metric_name`. Nothing else moves. |

---

### Task 1: Baseline the shipped run before touching anything

**Why this is a task and not a preamble:** `runs/` is gitignored, so `runs/f03023ac9f3a` cannot be restored from git. V2 requires the post-change `validation_scoreboard.parquet` to be byte-identical, and the roadmap already records that the on-disk artifacts were written by code four commits stale (metric rows 4,536 on disk vs 4,530 re-measured). Comparing against the on-disk bytes alone would therefore compare against an artifact no current input reproduces. This task freezes both references: the shipped bytes, and what HEAD produces today.

**Files:**
- Create: `runs/_baseline_pre_stage4c/` (gitignored; the underscore cannot collide with a 12-hex run id)
- Read: `runs/f03023ac9f3a/`

**Interfaces:**
- Produces: `runs/_baseline_pre_stage4c/shipped/` (a copy of the artifact as committed to disk) and `runs/_baseline_pre_stage4c/head/` (what HEAD produces now), plus `runs/_baseline_pre_stage4c/DIGESTS.txt`. Task 11 diffs against `head/`.

- [ ] **Step 1: Copy the shipped artifact out of harm's way**

```bash
mkdir -p runs/_baseline_pre_stage4c
cp -R runs/f03023ac9f3a runs/_baseline_pre_stage4c/shipped
ls -la runs/_baseline_pre_stage4c/shipped
```
Expected: `validation_scores.parquet`, `validation_metrics.parquet`, `validation_scoreboard.parquet`, `validation_manifest.json`.

- [ ] **Step 2: Record the baseline suite result at HEAD**

```bash
uv run pytest -q 2>&1 | tail -20 > runs/_baseline_pre_stage4c/suite_at_head.txt
cat runs/_baseline_pre_stage4c/suite_at_head.txt
```
Expected: a pass/fail line. **Record it.** Any failure here is pre-existing and must not be attributed to this plan later.

- [ ] **Step 3: Re-run the harness at HEAD and keep what it produces**

```bash
time uv run logging-estimates validate --config config.yaml
cp -R runs/f03023ac9f3a runs/_baseline_pre_stage4c/head
```
Expected: ~11 minutes; thirteen `<regime> <disposition> scored=<n>` lines; nine regimes with `scored>0`.

- [ ] **Step 4: Record every digest and the shipped-vs-HEAD drift**

```bash
uv run python - <<'PY' | tee runs/_baseline_pre_stage4c/DIGESTS.txt
import hashlib, json
from pathlib import Path
base = Path("runs/_baseline_pre_stage4c")
for side in ("shipped", "head"):
    for name in sorted(p.name for p in (base / side).iterdir()):
        digest = hashlib.sha256((base / side / name).read_bytes()).hexdigest()[:16]
        print(f"{side:8s} {name:32s} {digest}")
import polars as pl
for side in ("shipped", "head"):
    m = pl.read_parquet(base / side / "validation_metrics.parquet")
    s = pl.read_parquet(base / side / "validation_scoreboard.parquet")
    print(f"{side:8s} metrics_rows={m.height} scoreboard_rows={s.height}")
    reasons = json.loads((base / side / "validation_manifest.json").read_text())["regimes"]
    print(f"{side:8s} scored_regimes=" + ",".join(sorted(k for k, v in reasons.items() if v["n_scored"])))
PY
```
Expected: nine scored regimes on both sides. The `validation_scoreboard.parquet` digests are expected to MATCH between `shipped` and `head` (the stale rows are `probabilistic`, which the scoreboard does not read) — **but do not assume it. Write down what actually printed.** If they differ, V2 is measured against `head/`, and the difference is reported in Task 11.

- [ ] **Step 5: Commit the recorded facts (no source change)**

Nothing under `runs/` is committable. Instead, paste the Step 4 output and the Step 2 suite line into the task's completion note, and commit only this plan file if it is not yet committed:

```bash
git add specs/plans/12-stage4-harness-completion.md
git commit -m "docs(specs): plan 12 — Stage 4 harness completion

Baseline recorded before any change: shipped vs HEAD digests for
runs/f03023ac9f3a, copied to runs/_baseline_pre_stage4c/ (gitignored).

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016yXue1JwE4k46A3ayBd6hd"
```

---

### Task 2: Typed leakage errors, and an origin that cannot be malformed

**Requirements:** R-S4C-5, R-S4C-20. **Verification:** V5.

**Why:** `assert_no_retained_truth` is a bare `assert` on the shipped scoring path (`harness.py:126`), so it vanishes under `python -O` today — while `harness.py:63-73` states the opposite convention in prose. `assert_no_future_rows` has the same shape and becomes live in Task 4. Separately, `rolling_origin_frames(monthly, origins=['banana'])` returns all 4,812 rows untruncated and the guard passes: string comparison puts every `'2017-01'`-shaped month below `'banana'`, so nothing is filtered and nothing is at-or-after the origin.

**Files:**
- Modify: `src/logging_employment/errors.py` (append a class)
- Modify: `src/logging_employment/validate/leakage.py:82` and `:88-98`
- Modify: `tests/unit/test_validate_temporal_regimes.py:11-13`
- Modify: `tests/integration/test_validate_leakage.py:11-14,24-27`
- Test: `tests/unit/test_validate_leakage_guards.py` (new)

**Interfaces:**
- Produces: `errors.LeakageError`; `leakage.assert_no_future_rows(frame, *, origin: str, periods: Sequence[str]) -> None` — Task 4 calls it with the untruncated frame's distinct months as `periods`.
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_validate_leakage_guards.py`:

```python
"""§13.4's guards as typed, strip-proof refusals rather than bare asserts.

`python -O` deletes an `assert` statement outright. `assert_no_retained_truth` runs inside the
shipped scoring loop (`validate/harness.py`), so before this module the primary leakage control
was disarmed by an interpreter flag on the live path while the package documented the opposite
convention two functions above it.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import polars as pl
import pytest

from logging_employment.contracts import HarmonizedData
from logging_employment.errors import LeakageError
from logging_employment.validate.leakage import assert_no_future_rows, assert_no_retained_truth

_RETAINING_FRAME = """
import polars as pl
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import LeakageError
from logging_employment.validate.leakage import assert_no_retained_truth

data = HarmonizedData(
    qcew_monthly=pl.DataFrame(
        {"state_fips": ["41"], "reference_month": ["2019-06"], "employment_value": [58]}
    ),
    qcew_national_size=pl.DataFrame(),
    cbp_state_size=pl.DataFrame(),
    bridge=pl.DataFrame(),
)
truth = pl.DataFrame(
    {"state_fips": ["41"], "reference_month": ["2019-06"], "truth": [58]}
)
"""


def _masked_frame_that_retains_the_truth() -> tuple[HarmonizedData, pl.DataFrame]:
    """A one-row frame whose `employment_value` still equals the held-out value."""
    data = HarmonizedData(
        qcew_monthly=pl.DataFrame(
            {"state_fips": ["41"], "reference_month": ["2019-06"], "employment_value": [58]}
        ),
        qcew_national_size=pl.DataFrame(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    truth = pl.DataFrame({"state_fips": ["41"], "reference_month": ["2019-06"], "truth": [58]})
    return data, truth


def test_retained_truth_raises_a_typed_error():
    data, truth = _masked_frame_that_retains_the_truth()
    with pytest.raises(LeakageError, match="employment_value"):
        assert_no_retained_truth(data, truth)


def test_the_retained_truth_guard_still_fires_under_python_O():
    """V5. A bare `assert` here was deleted by `-O` on the shipped scoring path.

    Two subprocesses' worth of certainty is not needed; one optimized interpreter is. The
    `__debug__` assertion inside the script is what stops this passing vacuously on a
    non-optimized run.
    """
    script = textwrap.dedent(
        _RETAINING_FRAME
        + """
        if __debug__:
            raise SystemExit("this subprocess is not optimized; -O did not take")
        try:
            assert_no_retained_truth(data, truth)
        except LeakageError:
            print("raised")
        else:
            raise SystemExit("the guard did not fire under -O")
        """
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", script], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "raised"


def test_a_future_row_raises_a_typed_error():
    frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
    with pytest.raises(LeakageError, match="future"):
        assert_no_future_rows(frame, origin="2020-01", periods=["2019-12", "2020-01"])


def test_an_origin_matching_no_period_is_refused():
    """M2's malformed origin: `'banana'` truncated nothing and passed.

    Every `YYYY-MM` string sorts below `'banana'`, so the filter removed no row and the
    at-or-after check found none. The guard certified a frame it had not truncated.
    """
    frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
    with pytest.raises(LeakageError, match="banana"):
        assert_no_future_rows(frame, origin="banana", periods=["2019-12", "2020-01"])


def test_a_past_only_frame_passes():
    frame = pl.DataFrame({"reference_month": ["2019-11", "2019-12"]})
    assert_no_future_rows(frame, origin="2020-01", periods=["2019-11", "2019-12", "2020-01"])
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/unit/test_validate_leakage_guards.py -v
```
Expected: collection error — `ImportError: cannot import name 'LeakageError' from 'logging_employment.errors'`.

- [ ] **Step 3: Add the typed error**

Append to `src/logging_employment/errors.py`:

```python
class LeakageError(LoggingEmploymentError):
    """A §13.4 leakage control fired, or was asked to certify a frame it cannot speak for.

    Typed rather than a bare `assert` because `python -O` deletes an `assert` statement outright.
    `validate.leakage.assert_no_retained_truth` runs inside the shipped scoring loop
    (`validate/harness.py`), so until 2026-09-08 the package's primary leakage control was
    disarmed by an interpreter flag on the live path while `harness.py` documented the opposite
    convention. It also covers a guard that CANNOT certify what it was asked to: an origin
    matching no period in the frame truncates nothing, so passing is not evidence.
    """
```

- [ ] **Step 4: Make both guards typed, and give the origin guard a universe**

In `src/logging_employment/validate/leakage.py`, add `from collections.abc import Sequence` to the imports and `from ..errors import LeakageError` beside the existing `from ..contracts import HarmonizedData`.

Replace the assertion at the end of `assert_no_retained_truth`:

```python
            if str(value) == withheld:
                raise LeakageError(
                    f"{column} on {row['state_fips']}/{row['reference_month']} retains the "
                    f"held-out value {withheld}"
                )
```

Replace `assert_no_future_rows` entirely:

```python
def assert_no_future_rows(
    frame: pl.DataFrame, *, origin: str, periods: Sequence[str]
) -> None:
    """§13.4 bullet 3: a rolling-origin frame contains no period at or after the origin.

    This guard, not the mask, is what Stage 4's exit criterion "a rolling-origin run provably
    contains no future-period rows" is about — a mask hides values, it does not remove rows.

    `periods` is the UNTRUNCATED frame's month universe, and it is required rather than derived
    from `frame` because `frame` is the truncated one: every origin is trivially absent from it,
    so a check against `frame` alone can only ever be vacuous. Measured 2026-09-08 before this
    argument existed: `rolling_origin_frames(monthly, origins=['banana'])` returned all 4,812
    rows untruncated and this function passed, because every `YYYY-MM` string sorts below
    `'banana'` and so neither the filter nor the comparison here matched anything.
    """
    known = sorted(set(periods))
    if origin not in known:
        span = f"{known[0]}..{known[-1]}" if known else "an empty period universe"
        raise LeakageError(
            f"origin {origin!r} matches no period in {span}, so the truncation it names did not "
            "happen and this guard would certify a frame it never cut"
        )
    future = frame.filter(pl.col("reference_month") >= origin)
    if future.height:
        raise LeakageError(
            f"{future.height} future rows at or after origin {origin}: "
            f"{sorted(future['reference_month'].unique().to_list())[:5]}"
        )
```

- [ ] **Step 5: Update the two existing call sites**

In `tests/unit/test_validate_temporal_regimes.py`, replace the body of `test_every_rolling_origin_frame_is_provably_past_only`:

```python
def test_every_rolling_origin_frame_is_provably_past_only():
    """Stage 4's exit criterion, as an assertion over the truncated frame."""
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    periods = monthly["reference_month"].unique().to_list()
    for origin, frame in rolling_origin_frames(monthly, origins=["2020-01", "2022-01"]):
        assert_no_future_rows(frame, origin=origin, periods=periods)
        assert frame.height < monthly.height
```

In `tests/integration/test_validate_leakage.py`, add `LeakageError` to the imports (`from logging_employment.errors import LeakageError`) and replace:

```python
def test_a_rolling_origin_frame_carrying_a_future_row_is_refused():
    data = HarmonizedData.load(Path("data/staged"))
    periods = data.qcew_monthly["reference_month"].unique().to_list()
    with pytest.raises(LeakageError, match="future"):
        assert_no_future_rows(data.qcew_monthly, origin="2020-01", periods=periods)
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run pytest tests/unit/test_validate_leakage_guards.py tests/unit/test_validate_temporal_regimes.py -v
uv run pytest tests/integration/test_validate_leakage.py -v
```
Expected: all pass. (The integration module needs `data/staged`; it skips without it.)

- [ ] **Step 7: Commit**

```bash
uv run ruff check src tests && uv run black --check src tests
git add src/logging_employment/errors.py src/logging_employment/validate/leakage.py \
        tests/unit/test_validate_leakage_guards.py tests/unit/test_validate_temporal_regimes.py \
        tests/integration/test_validate_leakage.py
git commit -m "fix(validate): the §13.4 guards raise a typed error and refuse a malformed origin

R-S4C-5, R-S4C-20. Both guards were bare asserts, so \`python -O\` disarmed
\`assert_no_retained_truth\` on the shipped scoring path. \`assert_no_future_rows\`
now takes the untruncated frame's period universe and refuses an origin outside
it — measured, origins=['banana'] truncated nothing and passed.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_016yXue1JwE4k46A3ayBd6hd"
```
