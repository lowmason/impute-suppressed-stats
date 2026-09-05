# Stage 3: Exact Reconciliation and Transparent Baselines — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: **executing-plans** — inline execution was chosen
> at the handoff on 2026-09-05, so run the tasks yourself in plan order rather than dispatching
> subagents. Its stop-and-ask rules and completion chain apply. Steps use checkbox (`- [ ]`)
> syntax for tracking.

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage 3 — on plan completion, tick the stage
> and re-validate later stages against what shipped.

**Goal:** Ship the reconciliation layer and every required transparent baseline, each emitting
coherent point estimates inside the Stage 2 feasible set, anchored on a substitute allocation
target that is declared, gated, and labelled rather than assumed.

**Architecture:** A `reconcile/` subpackage implements the five §12 algorithms behind one shared
entry point that every estimator must pass through. An `anchor.py` module computes the substitute
allocation target — the published national employment row, admitted only when a per-run
establishment-closure gate passes — and hands downstream code a `(R_t, D_t, M_t)` triple. A
`baselines/` subpackage implements §10.1–10.6 as weight-vector producers behind one `Estimator`
protocol; none of them allocates, they only supply weights. Two CLI commands (`run-baselines`,
`reconcile`) persist the results and a manifest, both idempotent for identical inputs.

**Tech Stack:** Python ≥ 3.14, uv + hatchling, Polars, NumPy, SciPy, HiGHS via `highspy`, Typer,
pytest.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Python floor `>=3.14`**; console script is **`logging-estimates`** (not `logging-employment`).
  Declared in `pyproject.toml:6` and `pyproject.toml:21`.
- **Polars, never pandas.** The whole package is Polars; `import pandas` is a defect.
- **Normative keywords are defined by the spec itself** (§1.1, spec:29-31): MUST, MUST NOT,
  SHOULD, SHOULD NOT, MAY are normative. Never soften a MUST into a log line.
- **Every command MUST write a machine-readable manifest and MUST be idempotent for the same
  inputs** (§16.1, spec:1663).
- **THE MASK-PARAMETERISED SIGNATURE.** `national_residual()` and every function downstream of it
  MUST take the `(D_t, M_t)` partition as an argument. They MUST NOT read `observation_status`
  from a table internally. Stage 4 recomputes `R_t'` from a pseudo-suppression mask; a residual
  function that reads its own partition forces Stage 4 to mutate `qcew_monthly` or reimplement the
  anchor. This is a defect Stage 4 would inherit, so it is fixed here.
- **THE ANTI-DRIFT RULE.** Every count in this plan — 96/96, 1,227, 3,489, 762/465, 32/32, 9–15 —
  is a measurement dated 2026-09-05, not an invariant. Compute them at run time, record them in the
  run manifest, and assert on **structure** (the gate is evaluated; a failing month halts; a partial
  weight vector is refused), never on the literal number. One BLS revision moves every one of them.
  A test that asserts `gap == 0` on live data is a test that a revision breaks for the wrong reason.
- **NO SYNTHESIZED BOUNDS, IN EITHER DIRECTION.** §9.3 (spec:861-872) forbids "arbitrary top-class
  caps". A null `selected_upper` reads as `+inf` and MUST NOT be coerced to a number. The symmetric
  temptation is equally forbidden: every suppressed cell has ≥ 1 establishment, which invites a
  floor of 1 employee per cell. That is as much an invention as a cap — it is not a published value
  and it would contradict Stage 2's hash-pinned `deterministic_bounds`. Out of scope, both ways.
- **STAGE 2'S OUTPUTS ARE FROZEN.** No constraint row is built by this stage.
  `rows.assert_no_national_employment_margin` stays in force **unqualified** — do not add an
  `is_hard` escape hatch. `constraint_set_hash` and `data/constraints/` stay byte-identical, all
  1,227 state cells keep `selected_lower = 0.0`, `selected_upper = null`,
  `bound_status = 'unbounded'`, and no cell is reclassified.
- **INV-004 SCOPE — DECIDED, NOT OPEN.** The adding-up restriction to `R_t` binds every released
  estimate but carries no `constraint_row` label. The clean-looking fix — a `modeling_assumption`,
  `is_hard=false` row — is refused at build time by `assert_no_national_employment_margin`, which
  iterates every draft with no `is_hard` test. **The reading this plan takes: INV-004's labelling
  obligation stops at the constraint system.** §9.1 confines that layer to what public information
  logically implies, and INV-005 would exclude a `modeling_assumption` row from the feasible set
  anyway. The anchor is therefore labelled in the run manifest and in the per-cell `anchor_basis`
  column, not as a constraint row. **Do not weaken the guard.** It is Stage 2's correct
  implementation of the `decline` verdict.
- **DECLINE, NEVER FABRICATE.** A baseline that cannot weight a cell either takes the declared
  §10.2 fallback or declines the month with a reason string written as a `declined` row in
  `baseline_results/`. A silent NaN, a silently dropped cell, or a silently subset weight vector is
  forbidden. A decline is a visible outcome, never inferred from an absent row.

---

## What the evidence already settles

Read this section before Task 1. These facts were measured against the shipped tables and code on
2026-09-05, and an implementer who does not know them will build the wrong thing.

### 1. There is no national employment margin, and there never will be one in this stage

`SRC-QCEW-006` came back **`decline`** — for unverifiability, not geography. Every one of the
window's 96 months carries 9–15 suppressed state cells, so no month ever offered a complete
published state sum against which to test the employment identity. Stage 2 therefore refuses to
build the margin, in code, and this stage does not overturn that.

The consequence for reconciliation is blunt: **every one of the 1,227 suppressed state-month cells
is `bound_status = 'unbounded'`, with `selected_lower = 0.0` and `selected_upper = null`.** Only 14
national size-class cells are `partially_identified`.

### 2. The substitute anchor is the published national employment row, admitted by a gate

The national row **is** published: 96 rows, one per month, every one `observation_status =
'observed'`, zero nulls. What Stage 0 could not verify is whether that row's universe equals the
union of the state universes. §12.2 (spec:1284) conditions its residual on "a **compatible**
national total `N_t`" and never defines *compatible*; **§5.5 (spec:247-262) does**, listing ten
dimensions that MUST be evaluated before a source value is used.

Nine of the ten match by construction — `N_t` and the state rows are the same field of the same
QCEW file: same reference month, industry code, NAICS vintage, ownership (`own_code 5`), employment
concept, statistical unit, size concept (`size_code '0'`), release vintage (`release_status
'final'`), and both are exact published values. **The one dimension in doubt is the geography
universe**, and that is exactly what the gate measures.

**The gate: national `qtrly_establishments` minus the sum over ALL published state rows — including
the employment-suppressed ones, which still publish establishment counts — must equal exactly 0.**
Integer equality, no tolerance.

Measured: **gap = 0 in 96 of 96 months**, at 48–50 publishing areas, `min = max = 0`.

This is a test of the **universe**, not of the **measure**. Gap-0 closure forces every absent area
(DC in all 96 months, DE in 36, ND in 48) to contribute zero establishments, and a QCEW area with
zero establishments classified into 113310 has no covered jobs, since §3.2's estimand counts jobs
*at establishments classified into* the industry. Omitting a zero component does not omit a
component included in the national total, so §3.2's prohibition ("A national control MUST NOT be
imposed on a state universe that omits components included in the national total", spec:122) is
not triggered.

**HONEST CAVEAT the plan carries and Task 3 asserts in a docstring:** `qtrly_establishments` is
constant within all 1,572 state-quarters (measured: 0 varying, every quarter exactly 3 months), so
the "96/96 monthly" gate is **32 independent quarterly facts replayed three times**. A
contamination confined to one month within a quarter is undetectable by construction.

**Do not cite §9.3 as the warrant.** §9.3 governs what may be encoded as a *hard constraint*, which
this design deliberately never does; and its own permission is gated on "compatible", the very
predicate at issue, which makes the argument circular. Cite §5.5 as the warrant and §9.3 only in
the negative — to show the anchor appears on no prohibited list.

### 3. The partition has three traps

- **`D_t` is 3,489 cells, not 3,462.** Select on `observation_status in ('observed','true_zero')`.
  Selecting `== 'observed'` alone drops the 27 `true_zero` cells into `M_t`, where they would be
  imputed despite being published zeros.
- **`M_t` is 1,227 cells**, `|M_t|` ∈ [9, 15], never 0.
- **A (state, month) with no published row is in neither set.** 84 such pairs — ND absent 48
  months, DE absent 36 — plus DC (`'11'`), which publishes no row in any of the 96 months. The
  staged state panel carries **50** distinct `state_fips`, not 51, and **4,716** cells, not
  50 × 96 = 4,800. **Never index a dense state × month grid.**

Measured residual: `R_t = N_t - Σ_{D_t} E^obs` is strictly positive in 96/96 months, min 696,
median 1,480, max 2,711, total 142,658 over 1,227 cells.

### 4. Two §17.3 exit criteria are vacuous on D1 and MUST run on synthetic fixtures

§12.3's failure predicate is **strict** (spec:1312-1318): `Σ L > R_t` **or** `Σ U < R_t`. With
`selected_upper` null on 1,227 of 1,241 unknown cells, null reads as `+inf`, so the clip's upper arm
is a no-op and **the `Σ U < R_t` half can never fire on a state cell**. §17.3's "bounded scaling
respects every lower and upper bound" and "bounded scaling fails on infeasible residuals" therefore
**cannot be exercised on D1** and MUST run on synthetic finite-upper fixtures. Task 18 says so
explicitly; without that, those two exit criteria are vacuous.

Because the predicate is strict, `R_t = Σ L` is **feasible** — the degenerate case where every cell
sits at its bound MUST succeed. With `L = 0` everywhere this means raise only on `R_t < 0`, never on
`R_t = 0`. A guard written `R_t <= 0` fail-closes on a case the spec requires to succeed.

Likewise §12.5: `target_cell` carries **zero** state-by-size cells (4,716 `state_total`, 51
`national_size`, 8 `national_total`), so matrix reconciliation has **no real input until Stage 6**
and is tested synthetically by construction.

### 5. Baseline coverage is not uniform, and the composite rule is what keeps §10.8 populated

Six states have **zero** observed-employment months in the window — AK (`02`), HI (`15`), NV
(`32`), VT (`50`) at 96/96 suppressed; DE (`10`) at 51 suppressed + 9 true_zero; ND (`38`) at 30
suppressed + 18 true_zero. Every month's `M_t` contains at least one of them.

| Baseline | Runs | Own-weight | Fallback |
|---|---|---|---|
| §10.1 equal | 96/96 months | n/a (q ≡ 1) | none |
| §10.2 establishment-proportional | 96/96 months | 1,227/1,227 | none — the universal rung |
| §10.3 historical shares (×5) | 96/96 months | 762/1,227 | 465 via §10.2 |
| §10.4 CBP intensity | 84/96 months | 1,041/1,080 | 186 cells (HI, RI) via §10.2 |
| §10.5 harvest | 0/96 — declines | — | — |
| §10.6 constrained regression | 96/96 months | per fit | §10.2 |

**Under an all-or-nothing rule, §10.3 and §10.4 would decline in 96/96 months**, emptying §10.8
rungs 1 and 3 and leaving the roadmap's "named preferred transparent baseline slot" unfillable.
The declared-composite rule is what prevents that: own weight where defined, §10.2 establishment
weight elsewhere, with a per-cell `weight_basis` column and counts in the manifest. §10.8's own
rank-1 phrasing — "CBP/QCEW employee-per-establishment **with robust historical adjustment**" — is
the spec's precedent that a composed estimator is legitimate.

**§10.2's fallback rung never fails:** `qtrly_establishments` is non-null and ≥ 1 (range 1..282) on
every one of the 1,227 suppressed cells, and its sum over `M_t` is strictly positive every month.

**§10.4 declines for reference year 2024** — 12 months, 147 suppressed cells. `cbp_state_size`
publishes 2017–2023 only and `regime_for_year(2024)` raises. The whole content of §10.4 is a
year-specific March intensity; carrying 2023 forward is an invention with no spec basis. Decline
and record it. **HI (`15`) and RI (`44`) have no `cbp_state_size` row in any published year.**

**CBP suppression:** 4 of the `size_code '001'` rows have null employment and MUST be dropped, not
read as zero (INV-003).

**The window spans a NAICS vintage break at 2022-01** — NAICS 2017 covers 2017-01..2021-12, NAICS
2022 covers 2022-01..2024-12. §10.3's "classification-consistent periods" (spec:974) requires an
explicit rule for whether a lookback may cross it. Task 12 sets that rule.

### 6. Sequencing hazard that will look like a bug

`run_id` hashes `resolved_dict(cfg)`, so **adding the `reconciliation:` block re-keys the run
directory** (measured: `e1e20b583449` → `e04604e5dbce`) and orphans Stage 2's outputs.
`data/constraints/` is **not** run-scoped and holds stale tables until rebuilt. Task 1 therefore
ends by re-running `build-constraints` **then** `solve-bounds`. If you skip it, `solve-bounds`
fails with `typer.BadParameter` — **that is designed behaviour, not a defect.**

`run-baselines` and `reconcile` MUST write a **sibling** `baseline_manifest.json`. Never edit
`schema_manifest.json`: `solve-bounds` reads its bytes as a precondition gate and an idempotence
test pins them.

### 7. What the spec does not specify, and this stage must originate

§12 specifies **no** numeric tolerance, **no** iteration cap, and **no** convergence criterion
anywhere. Appendix A's `feasibility_tolerance: 1.0e-7` and `rank_tolerance: 1.0e-10` sit under
`constraints:` and belong to the LP/MILP bound solver — **reusing 1.0e-7 for reconciliation is a
new decision requiring justification, not an inheritance.** Appendix A's `reconciliation:` block
has exactly three keys and no tolerance key:

```yaml
reconciliation:
  single_margin_method: 'bounded_proportional_scaling'
  general_method: 'kl_projection'
  integerize_release: true
```

This stage must originate, and record in config: the reconciliation tolerance, the bisection
stopping rule and iteration cap, the RAS/IPF convergence test and inconsistency threshold, §12.4's
"small positive floor for zero raw seeds" (undefined at a zero seed, so a hard numerical
requirement), and §12.6 step 3's tie-break — which **MUST be deterministic** (by `cell_id`) or
§16.1's idempotence requirement breaks.

`ε_A` in §11.5's score `q = (A + ε_A)·exp(μ)` also has no specified value. §11.5 belongs to Stage
5, but §10.2's weights are the same `A`; this plan sets no `ε_A` and Task 11 uses `A` directly,
since `A ≥ 1` on every suppressed cell makes a positive offset unnecessary here.

---

## File structure

**New subpackage `src/logging_employment/reconcile/`** — the §12 algorithms, one responsibility
per file:

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports |
| `anchor.py` | The closure gate, `Anchor`, `national_residual(...)` |
| `allocate.py` | The shared entry point and its domain refusal; §12.2 no-bound fast path |
| `scaling.py` | §12.3 bounded proportional scaling by bisection |
| `projection.py` | §12.4 KL projection into the feasible polytope |
| `matrix.py` | §12.5 row–column reconciliation (RAS/IPF) |
| `integerize.py` | §12.6 balanced integerization |
| `draws.py` | §12.7 + §16.2 `reconcile_draws`, `PosteriorDraws` |

**New subpackage `src/logging_employment/baselines/`** — one file per estimator family:

| File | Responsibility |
|---|---|
| `__init__.py` | Public exports, the estimator registry |
| `interfaces.py` | The `Estimator` protocol; the composite weight vector |
| `simple.py` | §10.1 equal, §10.2 establishment-proportional |
| `historical.py` | §10.3's five share variants |
| `intensity.py` | §10.4 CBP/QCEW employee-per-establishment |
| `harvest.py` | §10.5's required decline |
| `regression.py` | §10.6 constrained regression |
| `runner.py` | §10.8 fallback ordering, orchestration, `baseline_results/` |

**Modified:** `config.py` (`ReconciliationConfig`, `BaselinesConfig`), `contracts.py` (the two new
schemas and three new enums), `errors.py` (four new exception classes), `cli.py` (`run-baselines`,
`reconcile`), `pyproject.toml` (declare `numpy`), `config.yaml`, `tests/unit/test_config.py`.

**Tests:** `tests/unit/test_anchor.py`, `test_allocate.py`, `test_scaling.py`, `test_projection.py`,
`test_matrix.py`, `test_integerize.py`, `test_reconcile_draws.py`, `test_baseline_interfaces.py`,
`test_baselines_simple.py`, `test_baselines_historical.py`, `test_baselines_intensity.py`,
`test_baselines_harvest.py`, `test_baselines_regression.py`, `test_reconcile_properties.py`;
`tests/integration/test_baseline_cli.py`, `test_baseline_golden.py`, `test_d1_baselines.py`.

---

### Task 1: Dependencies, the `reconciliation:` and `baselines:` config blocks, and the re-key rebuild

**Files:**
- Modify: `pyproject.toml` (dependencies)
- Modify: `src/logging_employment/config.py`
- Modify: `config.yaml`
- Test: `tests/unit/test_config.py` (extend `APPENDIX_A`)

**Interfaces:**
- Consumes: nothing from this stage.
- Produces: `ReconciliationConfig`, `BaselinesConfig`, and two new `Config` attributes
  `config.reconciliation` and `config.baselines`. Every later task reads these.

Read §7 of "What the evidence already settles" before starting. Adding a config block re-keys
`run_id`, and this task ends by rebuilding Stage 2's outputs under the new key.

- [ ] **Step 1: Declare numpy as a direct dependency**

`numpy` is imported directly by four shipped modules — `constraints/graph.py:16`,
`constraints/diagnostics.py:19`, `constraints/rank.py:21`, `constraints/bounds.py:26` — but appears
nowhere in `pyproject.toml`. It resolves today only because `scipy` pulls it in transitively. This
stage adds more direct numpy imports, so declare it now.

In `pyproject.toml`, add one line to `dependencies`, keeping the list alphabetical:

```toml
dependencies = [
    "highspy>=1.15.1",
    "httpx>=0.28",
    "numpy>=2.5",
    "polars>=1.44",
    "pyarrow>=25.0",
    "pydantic>=2.13",
    "pyyaml>=6.0",
    "scipy>=1.18.1",
    "typer>=0.27",
]
```

Run `uv sync` and confirm it reports no change to the resolved set — numpy 2.5.2 is already
installed transitively, so this declares reality rather than changing it.

- [ ] **Step 2: Write the failing config test**

Append to `tests/unit/test_config.py`. Do **not** yet edit `APPENDIX_A`; this test asserts the new
blocks parse, and it must fail first.

```python
def test_the_reconciliation_block_parses_with_appendix_a_methods(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.reconciliation.single_margin_method == "bounded_proportional_scaling"
    assert cfg.reconciliation.general_method == "kl_projection"
    assert cfg.reconciliation.integerize_release is True


def test_the_reconciliation_tolerance_is_this_packages_decision_not_appendix_as(
    tmp_path: Path,
) -> None:
    """Appendix A's `reconciliation:` block has three keys and no tolerance.

    `feasibility_tolerance: 1.0e-7` lives under `constraints:` and belongs to the LP/MILP bound
    solver. Reusing the number here is a new decision, so it is configured separately and can
    diverge without touching the solver.
    """
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.reconciliation.tolerance == 1.0e-9
    assert cfg.constraints.feasibility_tolerance == 1.0e-7


def test_an_unknown_general_method_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("kl_projection", "hand_waving")))


def test_a_nondeterministic_integerization_tiebreak_is_rejected(tmp_path: Path) -> None:
    """§16.1 requires idempotence; a random tie-break would break it."""
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("largest_remainder", "random")))
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_config.py -k reconciliation -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'reconciliation'`, or a
pydantic `ValidationError` for the extra `reconciliation` key once `APPENDIX_A` is edited.

- [ ] **Step 4: Add the two config classes**

In `src/logging_employment/config.py`, after `ConstraintsConfig` and before `DisclosureConfig`:

```python
class ReconciliationConfig(_Strict):
    """The §12 reconciliation layer's settings (Appendix A `reconciliation:`, plus this
    package's own numerical decisions).

    Appendix A supplies exactly three keys. §12 specifies no tolerance, no iteration cap, and no
    convergence criterion anywhere, so the remaining five are originated here rather than
    inherited. `feasibility_tolerance` under `constraints:` belongs to the LP/MILP bound solver
    and is deliberately not reused: a bound solved to 1e-7 and a residual reconciled to 1e-9 are
    different obligations, and coupling them would make a solver tuning change silently move a
    published total.
    """

    single_margin_method: Literal["bounded_proportional_scaling"]
    general_method: Literal["kl_projection", "weighted_quadratic"]
    integerize_release: bool
    # Originated here. Tighter than the solver's 1e-7 because a residual is an adding-up identity
    # over at most 15 cells, not an optimum over a polytope.
    tolerance: float = 1.0e-9
    max_bisection_iterations: int = 200
    max_projection_iterations: int = 1000
    # §12.4 requires "a small positive floor for zero raw seeds" and gives no value. A seed of
    # exactly 0 makes the KL objective undefined, so this is a hard numerical requirement.
    zero_seed_floor: float = 1.0e-12
    # §12.6 step 3. MUST stay deterministic or §16.1's idempotence requirement breaks.
    integerization_tiebreak: Literal["largest_remainder"] = "largest_remainder"


class BaselinesConfig(_Strict):
    """Which §10 baselines run, and the declared-composite policy they run under.

    `allow_declared_composite` is not a convenience switch. With it false, §10.3 and §10.4 decline
    in every month of the D1 window — six states have no observed employment history and two have
    no CBP row at all, and every month's missing set contains at least one of them — which would
    leave §10.8's rungs 1 and 3 permanently empty. See the plan's coverage table.
    """

    allow_declared_composite: bool = True
    composite_fallback: Literal["establishment_proportional"] = "establishment_proportional"
    historical_lookback_months: int = 24
    # §10.3 requires "classification-consistent periods". The window breaks at 2022-01.
    historical_may_cross_naics_vintage: bool = False
    # §10.6. scipy is already a declared dependency; sklearn is not and is not added.
    regression_ridge_penalty: float = 1.0
```

Then extend `Config` itself:

```python
class Config(_Strict):
    """The whole resolved configuration."""

    project: ProjectConfig
    storage: StorageConfig
    sources: SourcesConfig
    constraints: ConstraintsConfig
    reconciliation: ReconciliationConfig
    baselines: BaselinesConfig
    disclosure: DisclosureConfig
```

- [ ] **Step 5: Add the blocks to `config.yaml` and to `APPENDIX_A`**

Append to `config.yaml`, after the `constraints:` block and before `disclosure:`:

```yaml
reconciliation:
  single_margin_method: 'bounded_proportional_scaling'
  general_method: 'kl_projection'
  integerize_release: true
  # Originated by plan 4, not by Appendix A, which has no tolerance key.
  tolerance: 1.0e-9
  max_bisection_iterations: 200
  max_projection_iterations: 1000
  zero_seed_floor: 1.0e-12
  integerization_tiebreak: 'largest_remainder'

baselines:
  allow_declared_composite: true
  composite_fallback: 'establishment_proportional'
  historical_lookback_months: 24
  historical_may_cross_naics_vintage: false
  regression_ridge_penalty: 1.0
```

Make the identical addition inside the `APPENDIX_A` string literal at
`tests/unit/test_config.py:12`. The two must stay in step: `APPENDIX_A` is what every config test
parses, and `config.yaml` is what every CLI run parses.

Also update `config.yaml`'s header comment, which currently says the
"constraints/model/reconciliation/validation/promotion/disclosure blocks are omitted" — the
reconciliation block is no longer omitted.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS, all tests including the four new ones.

- [ ] **Step 7: Rebuild Stage 2's outputs under the new run id**

Adding a config block changes `resolved_dict(cfg)`, which `run_id` hashes, so the run directory
re-keys and Stage 2's outputs are orphaned. `data/constraints/` is not run-scoped and holds stale
tables until rebuilt.

```bash
uv run logging-estimates build-constraints --config config.yaml
uv run logging-estimates solve-bounds --config config.yaml
```

Expected from `solve-bounds`: a `bound_status` tally with `unbounded` far exceeding every other
status, and a `flagged N narrow, 0 exact` line.

**If you skip `build-constraints` and run `solve-bounds` alone, it fails with
`typer.BadParameter` naming a missing `schema_manifest.json`. That is designed behaviour — the
precondition gate doing its job — not a defect. Run `build-constraints` and retry.**

Record the new run id; later tasks write into the same directory.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock src/logging_employment/config.py config.yaml tests/unit/test_config.py
git commit -m "feat(config): add the reconciliation and baselines blocks, and declare numpy"
```

---

### Task 2: Stage 3 table contracts, enums, and errors

**Files:**
- Modify: `src/logging_employment/contracts.py`
- Modify: `src/logging_employment/errors.py`
- Test: `tests/unit/test_contracts.py`

**Interfaces:**
- Consumes: `schema_fingerprint`, `validate_frame` (both already in `contracts.py`).
- Produces: `BASELINE_RESULT_SCHEMA`, `ANCHOR_AUDIT_SCHEMA`, the enums
  `RECONCILIATION_STATUSES`, `WEIGHT_BASES`, `ANCHOR_BASES`, and four exception classes:
  `UniverseClosureError`, `InfeasibleResidualError`, `WeightDomainError`, `NoHarvestFactorError`.

- [ ] **Step 1: Write the failing contract test**

Append to `tests/unit/test_contracts.py`:

```python
def test_the_baseline_result_schema_carries_per_cell_weight_provenance() -> None:
    """A reader must never mistake a fallback-weighted cell for an own-estimator one."""
    assert "weight_basis" in BASELINE_RESULT_SCHEMA
    assert "anchor_basis" in BASELINE_RESULT_SCHEMA
    assert "reconciliation_status" in BASELINE_RESULT_SCHEMA


def test_reconciliation_status_is_distinct_from_hard_constraint_satisfaction() -> None:
    """INV-002 binds hard public accounting constraints; the anchor is a modeling assumption.

    The enum must be able to say "reconciled to a declared anchor" without that reading as
    "satisfies a hard constraint", or INV-008's separation collapses.
    """
    assert "anchored_and_reconciled" in RECONCILIATION_STATUSES
    assert "declined" in RECONCILIATION_STATUSES
    assert "hard_constraint_satisfied" not in RECONCILIATION_STATUSES


def test_a_declined_baseline_row_is_representable() -> None:
    """A decline is a visible row, never an absent one."""
    assert BASELINE_RESULT_SCHEMA["decline_reason"] == pl.String
    assert BASELINE_RESULT_SCHEMA["estimate"] == pl.Float64
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_contracts.py -k baseline -v`
Expected: FAIL with `NameError: name 'BASELINE_RESULT_SCHEMA' is not defined`.

- [ ] **Step 3: Add the enums**

In `contracts.py`, after `BOUND_STATUSES`:

```python
# §7.11 names no reconciliation status and enumerates none, unlike `release_action`'s eight
# values, so these five are this package's decision. The separation that matters is the last two:
# a cell reconciled to the declared anchor is NOT a cell satisfying a hard public accounting
# constraint. INV-002 binds only the latter; INV-008 forbids relabelling one as the other.
RECONCILIATION_STATUSES: tuple[str, ...] = (
    "observed",
    "anchored_and_reconciled",
    "reconciled_no_anchor",
    "declined",
    "infeasible",
)

# Per-cell provenance for the weight that produced an estimate. §10.8's rank-1 phrasing
# ("employee-per-establishment WITH ROBUST HISTORICAL ADJUSTMENT") is the spec's own precedent
# that a composed estimator is legitimate; this column is what keeps the composition declared
# rather than silent.
WEIGHT_BASES: tuple[str, ...] = ("own_estimator", "establishment_fallback", "none")

# What licensed the allocation target. Only one value is reachable in this stage; `verified_
# identity` exists for the retirement condition in Task 3's docstring, when a future QCEW vintage
# publishes a month with no suppressed cell and SRC-QCEW-006 becomes testable.
ANCHOR_BASES: tuple[str, ...] = ("declared_national_total", "verified_identity", "none")
```

- [ ] **Step 4: Add the two schemas**

After `DETERMINISTIC_BOUNDS_SCHEMA`:

```python
# One row per (estimator, cell). A declined cell is a row with a null `estimate` and a populated
# `decline_reason`, never an absent row: absence is indistinguishable from a bug.
BASELINE_RESULT_SCHEMA: dict[str, pl.DataType] = {
    "estimator_id": pl.String,
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "raw_weight": pl.Float64,
    "estimate": pl.Float64,
    "estimate_integer": pl.Int64,
    "weight_basis": pl.String,
    "anchor_basis": pl.String,
    "reconciliation_status": pl.String,
    "decline_reason": pl.String,
    "residual": pl.Float64,
    "missing_set_size": pl.Int64,
    "constraint_set_hash": pl.String,
}

# One row per reference month. This is the anchor as a diffable artifact rather than a docstring:
# every number the admission gate looked at, recorded whether it passed or not.
ANCHOR_AUDIT_SCHEMA: dict[str, pl.DataType] = {
    "reference_month": pl.String,
    "national_total": pl.Int64,
    "national_establishments": pl.Int64,
    "state_establishments_sum": pl.Int64,
    "establishment_gap": pl.Int64,
    "publishing_area_count": pl.Int64,
    "disclosed_sum": pl.Int64,
    "disclosed_count": pl.Int64,
    "residual": pl.Int64,
    "missing_set_size": pl.Int64,
    "anchored": pl.Boolean,
    "implied_intensity": pl.Float64,
}
```

- [ ] **Step 5: Add the four exception classes**

Append to `errors.py`, following the house style — one sentence, naming the offending value:

```python
class UniverseClosureError(LoggingEmploymentError):
    """The establishment universes of the national row and the state rows do not close.

    §18.3 requires the pipeline to fail rather than guess when source universes cannot be
    reconciled. This is a whole-run halt, not a per-month decline: a nonzero gap means the
    published national row contains something the state table does not, and every month's
    residual is then suspect, not just the failing one's.
    """


class InfeasibleResidualError(LoggingEmploymentError):
    """§12.3's summed bounds exclude the residual, so no feasible scaling exists."""


class WeightDomainError(LoggingEmploymentError):
    """A weight vector's domain is not the missing set, or it carries a null or non-positive weight.

    Normalizing a weight vector defined on a strict subset of the missing set silently reallocates
    the absent cells' share onto the cells that happen to have inputs. That is fabricating an
    allocation, so it is refused rather than normalized.
    """


class NoHarvestFactorError(LoggingEmploymentError):
    """The harvest-proportional baseline has no harvest-origin volume and no latent factor."""
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_contracts.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/errors.py tests/unit/test_contracts.py
git commit -m "feat(contracts): declare the Stage 3 tables, provenance enums, and fail-closed errors"
```

---

### Task 3: The substitute allocation anchor and its universe-closure gate

**Files:**
- Create: `src/logging_employment/reconcile/__init__.py`
- Create: `src/logging_employment/reconcile/anchor.py`
- Test: `tests/unit/test_anchor.py`

**Interfaces:**
- Consumes: `HarmonizedData.qcew_monthly`; `UniverseClosureError`, `ANCHOR_AUDIT_SCHEMA`,
  `ANCHOR_BASES` from Task 2.
- Produces:
  - `@dataclass(frozen=True) Partition(disclosed: pl.DataFrame, missing: pl.DataFrame)`
  - `@dataclass(frozen=True) Anchor(reference_month: str, residual: float, missing_cells:
    tuple[str, ...], anchor_basis: str)`
  - `def observed_partition(monthly: pl.DataFrame) -> dict[str, Partition]`
  - `def closure_audit(monthly: pl.DataFrame, partitions: Mapping[str, Partition]) -> pl.DataFrame`
  - `def national_residual(monthly: pl.DataFrame, partition: Partition, *, reference_month: str)
    -> Anchor`
  - `def assert_universe_closes(audit: pl.DataFrame) -> None`

**This is the blocking design task. Every baseline consumes it. Read "What the evidence already
settles" §2 and §3 before writing a line.**

`national_residual` takes the partition as an argument. It MUST NOT read `observation_status`.
`observed_partition` is the *default* partition builder for a production run; Stage 4 will build a
different one from a pseudo-suppression mask and pass it to the same `national_residual`.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_anchor.py`:

```python
"""The substitute allocation anchor: the gate that admits it and the residual it yields."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.errors import UniverseClosureError
from logging_employment.reconcile.anchor import (
    Partition,
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)


def test_the_disclosed_set_includes_true_zero_cells(make_monthly) -> None:
    """A published zero is disclosed, not missing.

    Selecting on `observation_status == 'observed'` alone drops every `true_zero` cell into the
    missing set, where it would be imputed despite having been published. On the D1 window that
    is 27 cells.
    """
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "employment_value": 100, "qtrly_establishments": 12},
        {"state_fips": "01", "area_fips": "01000", "employment_value": 60,
         "qtrly_establishments": 6, "observation_status": "observed"},
        {"state_fips": "02", "area_fips": "02000", "employment_value": 0,
         "qtrly_establishments": 2, "observation_status": "true_zero"},
        {"state_fips": "04", "area_fips": "04000", "employment_value": None,
         "qtrly_establishments": 4, "observation_status": "suppressed"},
    )
    part = observed_partition(monthly)["2024-03"]
    assert sorted(part.disclosed["state_fips"].to_list()) == ["01", "02"]
    assert part.missing["state_fips"].to_list() == ["04"]


def test_the_residual_is_the_national_total_net_of_every_disclosed_cell(make_monthly) -> None:
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "employment_value": 100, "qtrly_establishments": 12},
        {"state_fips": "01", "area_fips": "01000", "employment_value": 60,
         "qtrly_establishments": 6, "observation_status": "observed"},
        {"state_fips": "02", "area_fips": "02000", "employment_value": 0,
         "qtrly_establishments": 2, "observation_status": "true_zero"},
        {"state_fips": "04", "area_fips": "04000", "employment_value": None,
         "qtrly_establishments": 4, "observation_status": "suppressed"},
    )
    part = observed_partition(monthly)["2024-03"]
    anchor = national_residual(monthly, part, reference_month="2024-03")
    assert anchor.residual == 40.0
    assert anchor.missing_cells == ("04",)
    assert anchor.anchor_basis == "declared_national_total"


def test_national_residual_never_reads_observation_status(make_monthly) -> None:
    """The mask-parameterised signature, asserted rather than documented.

    Stage 4 recomputes the residual from a pseudo-suppression mask. If `national_residual` read
    the partition from the table it would force Stage 4 to mutate `qcew_monthly`. Here a cell
    marked `observed` is passed in the missing set, and the residual must honour the argument.
    """
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "employment_value": 100, "qtrly_establishments": 12},
        {"state_fips": "01", "area_fips": "01000", "employment_value": 60,
         "qtrly_establishments": 6, "observation_status": "observed"},
        {"state_fips": "02", "area_fips": "02000", "employment_value": 30,
         "qtrly_establishments": 6, "observation_status": "observed"},
    )
    states = monthly.filter(pl.col("area_type") == "state")
    masked = Partition(
        disclosed=states.filter(pl.col("state_fips") == "01"),
        missing=states.filter(pl.col("state_fips") == "02"),
    )
    anchor = national_residual(monthly, masked, reference_month="2024-03")
    assert anchor.residual == 40.0
    assert anchor.missing_cells == ("02",)


def test_a_nonzero_establishment_gap_halts_the_run(make_monthly) -> None:
    """§18.3: fail rather than guess when source universes cannot be reconciled.

    This is a whole-run halt, not a per-month decline. A gap means the national row contains
    something the state table does not, which makes every month's residual suspect.
    """
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "employment_value": 100, "qtrly_establishments": 99},
        {"state_fips": "01", "area_fips": "01000", "employment_value": 60,
         "qtrly_establishments": 6, "observation_status": "observed"},
    )
    audit = closure_audit(monthly, observed_partition(monthly))
    with pytest.raises(UniverseClosureError) as excinfo:
        assert_universe_closes(audit)
    assert "2024-03" in str(excinfo.value)
    assert "93" in str(excinfo.value)


def test_the_gate_is_evaluated_for_every_month_not_only_failing_ones(make_monthly) -> None:
    """The audit is a diffable artifact: every month appears, passing or not.

    Asserted on structure, never on the gap being zero — the anti-drift rule. A revision that
    moves a published establishment count must break this test for the right reason or not at all.
    """
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "reference_month": "2024-03",
         "employment_value": 100, "qtrly_establishments": 6},
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2024-03",
         "employment_value": 60, "qtrly_establishments": 6},
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "reference_month": "2024-04",
         "employment_value": 90, "qtrly_establishments": 6},
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2024-04",
         "employment_value": 50, "qtrly_establishments": 6},
    )
    audit = closure_audit(monthly, observed_partition(monthly))
    assert audit.height == 2
    assert set(audit.columns) >= {"establishment_gap", "publishing_area_count", "anchored"}
    assert audit["anchored"].all()


def test_a_month_with_no_missing_cells_yields_no_anchor(make_monthly) -> None:
    """Nothing to allocate is not a failure; it is a month that needs no anchor."""
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "employment_value": 60, "qtrly_establishments": 6},
        {"state_fips": "01", "area_fips": "01000", "employment_value": 60,
         "qtrly_establishments": 6, "observation_status": "observed"},
    )
    part = observed_partition(monthly)["2024-03"]
    anchor = national_residual(monthly, part, reference_month="2024-03")
    assert anchor.missing_cells == ()
    assert anchor.residual == 0.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_anchor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.reconcile'`.

- [ ] **Step 3: Create the subpackage**

Create `src/logging_employment/reconcile/__init__.py`:

```python
"""The §12 exact reconciliation layer.

§12.1: "The predictive model ranks feasible allocations. The reconciliation layer maps each draw
into the deterministic feasible set. It is not optional post-hoc cosmetic adjustment." Nothing in
this subpackage is skippable by configuration, and no key exists to disable it.
"""

from __future__ import annotations

from .anchor import Anchor, Partition, national_residual, observed_partition

__all__ = ["Anchor", "Partition", "national_residual", "observed_partition"]
```

- [ ] **Step 4: Write `anchor.py`**

```python
"""The substitute allocation anchor, and the gate that admits it.

WHY THIS MODULE EXISTS. §12.2 defines the residual `R_t = N_t - sum_{s in D_t} E^obs` "for a
compatible national total N_t" and never defines *compatible*. §5.5 does, listing ten dimensions
that MUST be evaluated before a source value is used. Nine match by construction here -- N_t and
the state rows are the same field of the same QCEW file at the same reference month, industry,
NAICS vintage, ownership, employment concept, statistical unit, size concept, and release vintage,
and both are exact published values. The tenth, the geography universe, is exactly what
`closure_audit` measures.

WHAT THE GATE TESTS, AND WHAT IT DOES NOT. It tests the *universe*, not the *measure*. National
`qtrly_establishments` minus the sum over all published state rows -- including the
employment-suppressed ones, which still publish establishment counts -- must be exactly 0. Gap-0
closure forces every absent area to contribute zero establishments, and a QCEW area with zero
establishments classified into the industry has no covered jobs under §3.2's estimand. It does NOT
verify the employment identity; `SRC-QCEW-006`'s `decline` stands and this module does not rescue
it.

HONEST CAVEAT. `qtrly_establishments` is constant within a state-quarter, so a per-month gate
re-tests each quarterly value three times. A contamination confined to one month inside a quarter
is undetectable by construction. The gate is quarterly-resolution evidence wearing a monthly
shape, and it is recorded per month only because the residual is monthly.

WHAT THIS IS NOT. The anchor is a `modeling_assumption` (INV-004), never a constraint row. No row
is built, `assert_no_national_employment_margin` stays in force unqualified, and INV-005 keeps a
modeling assumption out of the deterministic feasible set. The adding-up restriction to R_t does
imply E_{s,t} <= R_t on every imputed cell -- a restriction the deterministic engine does not
have -- but that ceiling is DERIVED FROM A PUBLISHED NUMBER, not synthesized from a percentile or
a threshold guess, which is what distinguishes it from §9.3's "arbitrary top-class caps". It must
never be written back into `deterministic_bounds`.

RETIREMENT CONDITION. If a future QCEW vintage ever yields a month with no suppressed state cell,
`SRC-QCEW-006` becomes testable on that month. At that point assert `abs(R_t) <= tolerance`, fail
closed otherwise, and retire this anchor in favour of the verified identity -- rather than keeping
both and letting them disagree silently.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import polars as pl

from ..contracts import ANCHOR_AUDIT_SCHEMA
from ..errors import UniverseClosureError

DISCLOSED_STATUSES: tuple[str, ...] = ("observed", "true_zero")
DECLARED_NATIONAL_TOTAL = "declared_national_total"


@dataclass(frozen=True)
class Partition:
    """One month's split of the state panel into disclosed and missing cells.

    A (state, month) with no published row is in NEITHER frame. On the D1 window that is 84 pairs
    -- ND absent 48 months, DE absent 36 -- plus DC, which publishes no row in any month. Their
    employment, if any, sits inside the residual with no cell to receive it; the closure gate is
    what licenses treating that quantity as zero.
    """

    disclosed: pl.DataFrame
    missing: pl.DataFrame


@dataclass(frozen=True)
class Anchor:
    """One month's allocation target: what to allocate, and over which cells."""

    reference_month: str
    residual: float
    missing_cells: tuple[str, ...]
    anchor_basis: str


def observed_partition(monthly: pl.DataFrame) -> dict[str, Partition]:
    """The production partition: disclosed is observed plus true_zero, missing is suppressed.

    This is the DEFAULT partition builder. `national_residual` takes a `Partition` argument rather
    than calling this, so Stage 4's pseudo-suppression mask can supply a different one without
    mutating `qcew_monthly` or reimplementing the residual.
    """
    states = monthly.filter(pl.col("area_type") == "state")
    out: dict[str, Partition] = {}
    for (month,), group in states.group_by("reference_month", maintain_order=True):
        out[str(month)] = Partition(
            disclosed=group.filter(pl.col("observation_status").is_in(DISCLOSED_STATUSES)),
            missing=group.filter(pl.col("observation_status") == "suppressed"),
        )
    return out


def _national_row(monthly: pl.DataFrame, reference_month: str) -> dict[str, object]:
    """The single national row for a month, or a halt naming the month."""
    rows = monthly.filter(
        (pl.col("area_type") == "national") & (pl.col("reference_month") == reference_month)
    )
    if rows.height != 1:
        raise UniverseClosureError(
            f"{reference_month}: expected exactly one national row, found {rows.height}"
        )
    return rows.row(0, named=True)


def national_residual(
    monthly: pl.DataFrame, partition: Partition, *, reference_month: str
) -> Anchor:
    """§12.2's residual for one month, over the partition the caller supplies.

    MUST NOT consult `observation_status`: the partition argument is authoritative. A `true_zero`
    cell contributes 0 to the disclosed sum, which is why it belongs in `disclosed` rather than
    `missing` -- it is a published value, and imputing it would overwrite a fact.
    """
    national = _national_row(monthly, reference_month)
    disclosed_sum = float(partition.disclosed["employment_value"].fill_null(0).sum())
    residual = float(national["employment_value"]) - disclosed_sum
    return Anchor(
        reference_month=reference_month,
        residual=residual,
        missing_cells=tuple(partition.missing["state_fips"].to_list()),
        anchor_basis=DECLARED_NATIONAL_TOTAL,
    )


def closure_audit(monthly: pl.DataFrame, partitions: Mapping[str, Partition]) -> pl.DataFrame:
    """Every number the admission gate looked at, one row per month, passing or not.

    The audit is written whether or not the gate passes, so a failing run leaves the evidence that
    explains it rather than only an exception.
    """
    states = monthly.filter(pl.col("area_type") == "state")
    rows: list[dict[str, object]] = []
    for month in sorted(partitions):
        part = partitions[month]
        national = _national_row(monthly, month)
        published = states.filter(pl.col("reference_month") == month)
        national_est = int(national["qtrly_establishments"])
        state_est = int(published["qtrly_establishments"].fill_null(0).sum())
        disclosed_sum = int(part.disclosed["employment_value"].fill_null(0).sum())
        residual = int(national["employment_value"]) - disclosed_sum
        missing_n = part.missing.height
        missing_est = int(part.missing["qtrly_establishments"].fill_null(0).sum())
        rows.append(
            {
                "reference_month": month,
                "national_total": int(national["employment_value"]),
                "national_establishments": national_est,
                "state_establishments_sum": state_est,
                "establishment_gap": national_est - state_est,
                "publishing_area_count": published.height,
                "disclosed_sum": disclosed_sum,
                "disclosed_count": part.disclosed.height,
                "residual": residual,
                "missing_set_size": missing_n,
                "anchored": national_est - state_est == 0 and residual >= 0,
                # A falsification band, not an accuracy score: implied employees per establishment
                # across the missing set. If it drifts far from the disclosed states' intensity,
                # the completeness assumption is the first thing to doubt.
                "implied_intensity": (residual / missing_est) if missing_est else None,
            }
        )
    return pl.DataFrame(rows, schema=ANCHOR_AUDIT_SCHEMA)


def assert_universe_closes(audit: pl.DataFrame) -> None:
    """Halt the whole run if any month's establishment universes fail to close (§18.3).

    Not a per-month decline. A nonzero gap means the published national row contains a component
    the state table does not, which makes every month's residual suspect rather than one month's.
    """
    broken = audit.filter(pl.col("establishment_gap") != 0)
    if broken.height:
        first = broken.row(0, named=True)
        raise UniverseClosureError(
            f"establishment universes do not close in {broken.height} month(s); "
            f"first {first['reference_month']}: national {first['national_establishments']} "
            f"minus state sum {first['state_establishments_sum']} "
            f"= {first['establishment_gap']} across "
            f"{first['publishing_area_count']} publishing areas"
        )
    negative = audit.filter(pl.col("residual") < 0)
    if negative.height:
        first = negative.row(0, named=True)
        raise UniverseClosureError(
            f"{first['reference_month']}: residual {first['residual']} is negative, so the "
            "disclosed cells already exceed the published national total"
        )
```

**Note the strictness of the residual guard: `residual < 0`, never `residual <= 0`.** §12.3's
predicate is strict, so `R_t = 0` with all lower bounds at 0 is a feasible degenerate case that
MUST succeed. A `<= 0` guard fail-closes on a case the spec requires to work. It never fires on D1
(min residual 696) but Stage 4's masks reach it.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_anchor.py -v`
Expected: PASS, all six tests.

- [ ] **Step 6: Confirm the gate on the real window**

```bash
uv run python -c "
import polars as pl
from pathlib import Path
from logging_employment.contracts import HarmonizedData
from logging_employment.reconcile.anchor import closure_audit, observed_partition, assert_universe_closes
d = HarmonizedData.load(Path('data/staged'))
audit = closure_audit(d.qcew_monthly, observed_partition(d.qcew_monthly))
assert_universe_closes(audit)
print('months', audit.height, 'gap range', audit['establishment_gap'].min(), audit['establishment_gap'].max())
print('residual range', audit['residual'].min(), audit['residual'].max())
print('missing set size range', audit['missing_set_size'].min(), audit['missing_set_size'].max())
"
```

Expected: 96 months, gap range 0 0, a strictly positive residual range, and a missing-set size
range within [9, 15]. **Record what it prints; do not hardcode it into a test.**

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/reconcile/ tests/unit/test_anchor.py
git commit -m "feat(reconcile): add the declared allocation anchor and its universe-closure gate"
```

---

### Task 4: The shared allocation entry point and its domain refusal (§12.2)

**Files:**
- Create: `src/logging_employment/reconcile/allocate.py`
- Test: `tests/unit/test_allocate.py`

**Interfaces:**
- Consumes: `Anchor` from Task 3; `WeightDomainError`, `WEIGHT_BASES` from Task 2.
- Produces:
  - `@dataclass(frozen=True) Weights(values: dict[str, float], basis: dict[str, str])`
  - `def check_domain(weights: Weights, anchor: Anchor) -> None`
  - `def allocate(anchor: Anchor, weights: Weights) -> dict[str, float]`

§10 (spec:942) requires every baseline to use "the same ... reconciliation layer as the full
model". This module is that layer's front door: **every estimator supplies only weights and calls
`allocate`.** No estimator computes an estimate itself.

The domain refusal lands **here, with the entry point, and before any baseline exists.** If it
arrives later, the first baseline gets written against a permissive front door and the tightening
breaks it.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_allocate.py`:

```python
"""§12.2's no-bound fast path, and the refusal that keeps a composite declared."""

from __future__ import annotations

import pytest

from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.allocate import Weights, allocate, check_domain
from logging_employment.reconcile.anchor import Anchor


def _anchor(residual: float = 100.0, cells: tuple[str, ...] = ("01", "02", "04")) -> Anchor:
    return Anchor(
        reference_month="2024-03",
        residual=residual,
        missing_cells=cells,
        anchor_basis="declared_national_total",
    )


def _weights(values: dict[str, float]) -> Weights:
    return Weights(values=values, basis={k: "own_estimator" for k in values})


def test_the_allocation_sums_exactly_to_the_residual() -> None:
    out = allocate(_anchor(), _weights({"01": 1.0, "02": 2.0, "04": 1.0}))
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-9)
    assert out["02"] == pytest.approx(50.0)


def test_a_weight_vector_missing_a_cell_is_refused_not_normalized() -> None:
    """Normalizing a partial vector silently reallocates the absent cell's share.

    That is fabricating an allocation, so it is refused. A baseline that cannot weight every cell
    must declare a composite and record `establishment_fallback` per cell, not quietly drop one.
    """
    with pytest.raises(WeightDomainError) as excinfo:
        check_domain(_weights({"01": 1.0, "02": 2.0}), _anchor())
    assert "04" in str(excinfo.value)


def test_a_weight_vector_with_an_extra_cell_is_refused() -> None:
    with pytest.raises(WeightDomainError):
        check_domain(_weights({"01": 1.0, "02": 1.0, "04": 1.0, "05": 1.0}), _anchor())


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
def test_a_non_positive_or_nan_weight_is_refused(bad: float) -> None:
    """§12.2 says "positive raw weights". A zero weight is a silent decline for that cell."""
    with pytest.raises(WeightDomainError):
        check_domain(_weights({"01": 1.0, "02": bad, "04": 1.0}), _anchor())


def test_a_zero_residual_allocates_zero_to_every_cell() -> None:
    """R_t = 0 is feasible, not an error: §12.3's predicate is strict."""
    out = allocate(_anchor(residual=0.0), _weights({"01": 1.0, "02": 2.0, "04": 1.0}))
    assert set(out.values()) == {0.0}


def test_an_empty_missing_set_allocates_nothing() -> None:
    out = allocate(_anchor(residual=0.0, cells=()), Weights(values={}, basis={}))
    assert out == {}


def test_a_declared_composite_is_permitted_and_its_basis_survives() -> None:
    """Own weight where defined, establishment weight elsewhere -- recorded per cell."""
    weights = Weights(
        values={"01": 1.0, "02": 2.0, "04": 1.0},
        basis={"01": "own_estimator", "02": "own_estimator", "04": "establishment_fallback"},
    )
    check_domain(weights, _anchor())
    out = allocate(_anchor(), weights)
    assert sum(out.values()) == pytest.approx(100.0)
    assert weights.basis["04"] == "establishment_fallback"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_allocate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.reconcile.allocate'`.

- [ ] **Step 3: Write `allocate.py`**

```python
"""§12.2's required no-bound fast path, and the domain refusal that guards it.

§10 (spec:942) requires every baseline to use "the same source universe, training windows,
pseudo-suppression masks, hard bounds, and reconciliation layer as the full model". This module is
that layer's single entry point: an estimator supplies weights and calls `allocate`, and never
computes an estimate itself. That is what makes "the same reconciliation layer" concrete rather
than aspirational.

WHY THE DOMAIN REFUSAL IS HERE AND NOT IN A BASELINE. A weight vector defined on a strict subset
of the missing set, normalized to the residual, silently reallocates the absent cells' share onto
the cells that happen to have inputs. Nothing about the output looks wrong -- it sums to R_t and
every value is positive -- which is exactly why it must be refused mechanically rather than caught
by review. Declared composition (own weight where defined, establishment weight elsewhere, basis
recorded per cell) is permitted; silent subsetting is not.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..errors import WeightDomainError
from .anchor import Anchor


@dataclass(frozen=True)
class Weights:
    """Positive raw weights per cell, with the provenance of each.

    `basis` is not decoration. §10.3 runs at 762/1,227 own-weight on the D1 window and §10.4 at
    1,041/1,080 over the 84 months it covers; without a per-cell basis a reader -- and Stage 4's
    scoreboard -- would report a composite's score as a pure estimator's.
    """

    values: dict[str, float]
    basis: dict[str, str]


def check_domain(weights: Weights, anchor: Anchor) -> None:
    """Refuse any weight vector that is not exactly the missing set, positive, and finite."""
    wanted = set(anchor.missing_cells)
    got = set(weights.values)
    if wanted != got:
        raise WeightDomainError(
            f"{anchor.reference_month}: weight domain does not match the missing set; "
            f"absent={sorted(wanted - got)} unexpected={sorted(got - wanted)}"
        )
    if set(weights.basis) != got:
        raise WeightDomainError(
            f"{anchor.reference_month}: every weight needs a recorded basis; "
            f"missing basis for {sorted(got - set(weights.basis))}"
        )
    bad = sorted(
        cell
        for cell, value in weights.values.items()
        if not math.isfinite(value) or value <= 0.0
    )
    if bad:
        raise WeightDomainError(
            f"{anchor.reference_month}: §12.2 requires positive raw weights; "
            f"non-positive or non-finite at {bad}"
        )


def allocate(anchor: Anchor, weights: Weights) -> dict[str, float]:
    """§12.2: E_{s,t} = R_t * q_{s,t} / sum_{j in M_t} q_{j,t}.

    The required no-bound fast path, kept as its own code path rather than folded into §12.3's
    bounded scaling. On the D1 window every state cell is unbounded above, so this path carries
    the whole production load and deserves to be readable on its own.
    """
    if not anchor.missing_cells:
        return {}
    check_domain(weights, anchor)
    total = sum(weights.values.values())
    if total <= 0.0:  # unreachable after check_domain; kept so the division is provably safe
        raise WeightDomainError(f"{anchor.reference_month}: weights sum to {total}")
    return {cell: anchor.residual * weights.values[cell] / total for cell in anchor.missing_cells}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_allocate.py -v`
Expected: PASS, all eight tests (the parametrized one counts three).

- [ ] **Step 5: Export from the subpackage**

Extend `src/logging_employment/reconcile/__init__.py`:

```python
from .allocate import Weights, allocate, check_domain
from .anchor import Anchor, Partition, national_residual, observed_partition

__all__ = [
    "Anchor",
    "Partition",
    "Weights",
    "allocate",
    "check_domain",
    "national_residual",
    "observed_partition",
]
```

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/reconcile/ tests/unit/test_allocate.py
git commit -m "feat(reconcile): add the shared allocation entry point and its domain refusal"
```

---

### Task 5: Bounded proportional scaling by bisection (§12.3)

**Files:**
- Create: `src/logging_employment/reconcile/scaling.py`
- Test: `tests/unit/test_scaling.py`

**Interfaces:**
- Consumes: `Anchor`, `Weights`, `check_domain` from Tasks 3–4; `InfeasibleResidualError`.
- Produces:
  - `@dataclass(frozen=True) Bounds(lower: dict[str, float], upper: dict[str, float | None])`
  - `def clipped_sum(lam: float, weights: Weights, bounds: Bounds, cells: Sequence[str]) -> float`
  - `def scale_into_bounds(anchor: Anchor, weights: Weights, bounds: Bounds, *,
    tolerance: float, max_iterations: int) -> dict[str, float]`

**Read this before writing.** §12.3's failure predicate is **strict**:

> The function MUST fail if: `Σ_s L_{s,t} > R_t` or `Σ_s U_{s,t} < R_t`.

Two consequences an implementer gets wrong:

1. **`R_t = Σ L` is FEASIBLE.** The degenerate case where every cell sits at its lower bound MUST
   succeed. With `L = 0` everywhere this means raise only on `R_t < 0`, never on `R_t = 0`. A
   guard written `R_t <= 0` fail-closes on a case the spec requires to work.
2. **A null upper bound reads as `+inf`.** On the D1 window `selected_upper` is null on 1,227 of
   1,241 unknown cells, so `Σ U = +inf` and the `Σ U < R_t` half of the predicate **can never fire
   on a state cell**. Do not coerce null to a number to make the arithmetic tidy — that invents
   the cap §9.3 forbids. Represent it as `math.inf` and let the comparison be vacuous.

The spec writes the failure predicate with a bare `Σ_s` while the adding-up condition three lines
above uses `Σ_{s∈M_t}`. Implement both over `M_t`: summing bounds over disclosed cells too would
be incoherent with §12.2's definition of `R_t` as the national total net of disclosed cells. This
is an editorial asymmetry in the spec, not a second index set.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_scaling.py`:

```python
"""§12.3 bounded proportional scaling: bisection, strict failure, and infinite uppers."""

from __future__ import annotations

import math

import pytest

from logging_employment.errors import InfeasibleResidualError, WeightDomainError
from logging_employment.reconcile.allocate import Weights
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.scaling import Bounds, clipped_sum, scale_into_bounds

TOL = 1.0e-9
ITERS = 200


def _anchor(residual: float, cells: tuple[str, ...] = ("01", "02", "04")) -> Anchor:
    return Anchor("2024-03", residual, cells, "declared_national_total")


def _weights(values: dict[str, float]) -> Weights:
    return Weights(values=values, basis={k: "own_estimator" for k in values})


def _open_bounds(cells: tuple[str, ...]) -> Bounds:
    """The D1 shape: lower 0, upper null."""
    return Bounds(lower={c: 0.0 for c in cells}, upper={c: None for c in cells})


def test_with_open_bounds_scaling_reduces_to_the_proportional_split() -> None:
    """1,227 of 1,241 D1 cells have this shape, so this is the production path."""
    cells = ("01", "02", "04")
    out = scale_into_bounds(
        _anchor(100.0), _weights({"01": 1.0, "02": 2.0, "04": 1.0}), _open_bounds(cells),
        tolerance=TOL, max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-7)
    assert out["02"] == pytest.approx(50.0, abs=1e-7)


def test_every_bound_is_respected_when_a_cap_binds() -> None:
    """Synthetic finite uppers: this property CANNOT be exercised on D1 data."""
    bounds = Bounds(lower={"01": 0.0, "02": 0.0, "04": 0.0},
                    upper={"01": 10.0, "02": 1000.0, "04": 1000.0})
    out = scale_into_bounds(
        _anchor(100.0), _weights({"01": 5.0, "02": 1.0, "04": 1.0}), bounds,
        tolerance=TOL, max_iterations=ITERS,
    )
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-7)
    assert out["01"] <= 10.0 + 1e-9
    for cell, value in out.items():
        assert value >= bounds.lower[cell] - 1e-9


def test_a_residual_below_the_summed_lower_bounds_fails() -> None:
    bounds = Bounds(lower={"01": 50.0, "02": 50.0, "04": 50.0},
                    upper={"01": None, "02": None, "04": None})
    with pytest.raises(InfeasibleResidualError) as excinfo:
        scale_into_bounds(_anchor(100.0), _weights({"01": 1.0, "02": 1.0, "04": 1.0}), bounds,
                          tolerance=TOL, max_iterations=ITERS)
    assert "150" in str(excinfo.value)


def test_a_residual_above_the_summed_upper_bounds_fails() -> None:
    bounds = Bounds(lower={"01": 0.0, "02": 0.0, "04": 0.0},
                    upper={"01": 10.0, "02": 10.0, "04": 10.0})
    with pytest.raises(InfeasibleResidualError):
        scale_into_bounds(_anchor(100.0), _weights({"01": 1.0, "02": 1.0, "04": 1.0}), bounds,
                          tolerance=TOL, max_iterations=ITERS)


def test_a_residual_exactly_equal_to_the_summed_lower_bounds_succeeds() -> None:
    """§12.3's predicate is STRICT (`>` and `<`), so equality is feasible.

    A guard written `sum_L >= R_t` would fail-close on the case the spec requires to succeed. It
    never fires on D1, where every lower bound is 0 and the minimum residual is far above it, but
    Stage 4's masks and any §17.3 random-feasible generator reach it directly.
    """
    bounds = Bounds(lower={"01": 30.0, "02": 30.0, "04": 40.0},
                    upper={"01": 30.0, "02": 30.0, "04": 40.0})
    out = scale_into_bounds(_anchor(100.0), _weights({"01": 1.0, "02": 1.0, "04": 1.0}), bounds,
                            tolerance=TOL, max_iterations=ITERS)
    assert out == pytest.approx({"01": 30.0, "02": 30.0, "04": 40.0}, abs=1e-7)


def test_a_null_upper_bound_is_infinite_and_never_becomes_a_number() -> None:
    """§9.3 forbids arbitrary caps; a null upper must stay open, not become a big float."""
    cells = ("01", "02")
    bounds = _open_bounds(cells)
    assert clipped_sum(1e12, _weights({"01": 1.0, "02": 1.0}), bounds, cells) == pytest.approx(2e12)


def test_the_clipped_sum_is_monotone_in_lambda() -> None:
    """The property §12.3 cites as its justification for bisection."""
    cells = ("01", "02", "04")
    weights = _weights({"01": 1.0, "02": 2.0, "04": 3.0})
    bounds = Bounds(lower={"01": 1.0, "02": 0.0, "04": 0.0},
                    upper={"01": 5.0, "02": None, "04": 20.0})
    values = [clipped_sum(lam, weights, bounds, cells) for lam in (0.0, 0.5, 1.0, 2.0, 10.0, 100.0)]
    assert values == sorted(values)


def test_a_zero_residual_with_zero_lower_bounds_succeeds() -> None:
    cells = ("01", "02")
    out = scale_into_bounds(_anchor(0.0, cells), _weights({"01": 1.0, "02": 1.0}),
                            _open_bounds(cells), tolerance=TOL, max_iterations=ITERS)
    assert sum(out.values()) == pytest.approx(0.0, abs=1e-9)


def test_a_partial_weight_vector_is_refused_here_too() -> None:
    """The domain refusal is not bypassable by entering through the bounded path."""
    cells = ("01", "02", "04")
    with pytest.raises(WeightDomainError):
        scale_into_bounds(_anchor(100.0), _weights({"01": 1.0, "02": 1.0}), _open_bounds(cells),
                          tolerance=TOL, max_iterations=ITERS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_scaling.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `scaling.py`**

```python
"""§12.3 bounded proportional scaling, solved by bisection.

E_{s,t} = clip(lambda * q_{s,t}, L_{s,t}, U_{s,t}), for the lambda making sum_{M_t} E = R_t.

WHY BISECTION AND NOT A ROOT FINDER. §12.3 names it: "Because the summed clipped allocation is
monotone in lambda, use robust bisection." Monotonicity is the whole reason the method is safe --
the clipped sum is a non-decreasing piecewise-linear function of lambda with flat segments where
every cell is clipped, and Newton or a secant method stalls on exactly those flats. `test_the_
clipped_sum_is_monotone_in_lambda` pins the property the choice rests on.

WHY NULL UPPERS ARE INFINITE. On the D1 window `selected_upper` is null on 1,227 of 1,241 unknown
cells, because `SRC-QCEW-006` came back `decline` and nonnegativity is the only public fact
touching a state cell. `None` maps to `math.inf`, which makes the clip's upper arm a no-op and the
`sum U < R_t` half of §12.3's predicate vacuous. Coercing null to a large finite number instead
would invent the "arbitrary top-class cap" §9.3 forbids by name, and would silently change results
whenever the chosen number happened to bind.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import InfeasibleResidualError
from .allocate import Weights, check_domain
from .anchor import Anchor


@dataclass(frozen=True)
class Bounds:
    """Per-cell deterministic bounds. A `None` upper means unbounded above, not a missing value."""

    lower: dict[str, float]
    upper: dict[str, float | None]

    def upper_of(self, cell: str) -> float:
        """The upper bound as a float, with `None` read as positive infinity."""
        value = self.upper.get(cell)
        return math.inf if value is None else float(value)


def clipped_sum(
    lam: float, weights: Weights, bounds: Bounds, cells: Sequence[str]
) -> float:
    """sum_s clip(lam * q_s, L_s, U_s) -- non-decreasing in `lam`."""
    return sum(
        min(max(lam * weights.values[cell], bounds.lower[cell]), bounds.upper_of(cell))
        for cell in cells
    )


def scale_into_bounds(
    anchor: Anchor,
    weights: Weights,
    bounds: Bounds,
    *,
    tolerance: float,
    max_iterations: int,
) -> dict[str, float]:
    """Solve for lambda by bisection, or fail per §12.3's strict predicate."""
    cells = anchor.missing_cells
    if not cells:
        return {}
    check_domain(weights, anchor)

    lower_sum = sum(bounds.lower[cell] for cell in cells)
    upper_sum = sum(bounds.upper_of(cell) for cell in cells)
    # STRICT, per spec:1312-1318. Equality is feasible: the degenerate case where every cell sits
    # exactly on a bound must succeed, and a `>=` here would fail-close on it.
    if lower_sum > anchor.residual:
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: summed lower bounds {lower_sum} exceed residual "
            f"{anchor.residual}; §12.3 forbids approximating this away"
        )
    if upper_sum < anchor.residual:
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: summed upper bounds {upper_sum} fall below residual "
            f"{anchor.residual}; §12.3 forbids approximating this away"
        )

    if math.isclose(lower_sum, anchor.residual, rel_tol=0.0, abs_tol=tolerance):
        return {cell: bounds.lower[cell] for cell in cells}

    lo, hi = 0.0, 1.0
    # Grow the bracket rather than guessing one: the weights carry no scale guarantee, so a fixed
    # upper bracket would silently fail on a small-weight month.
    for _ in range(max_iterations):
        if clipped_sum(hi, weights, bounds, cells) >= anchor.residual:
            break
        lo, hi = hi, hi * 2.0
    else:  # pragma: no cover - unreachable given the upper_sum check above
        raise InfeasibleResidualError(
            f"{anchor.reference_month}: no bracket reaches residual {anchor.residual}"
        )

    for _ in range(max_iterations):
        mid = 0.5 * (lo + hi)
        total = clipped_sum(mid, weights, bounds, cells)
        if abs(total - anchor.residual) <= tolerance:
            break
        if total < anchor.residual:
            lo = mid
        else:
            hi = mid
    lam = 0.5 * (lo + hi)
    return {
        cell: min(max(lam * weights.values[cell], bounds.lower[cell]), bounds.upper_of(cell))
        for cell in cells
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_scaling.py -v`
Expected: PASS, all nine tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/reconcile/scaling.py tests/unit/test_scaling.py
git commit -m "feat(reconcile): solve bounded proportional scaling by bisection with strict failure"
```

---

### Task 6: KL projection into the feasible polytope (§12.4)

**Files:**
- Create: `src/logging_employment/reconcile/projection.py`
- Test: `tests/unit/test_projection.py`

**Interfaces:**
- Consumes: `ReconciliationConfig`; numpy, scipy.
- Produces:
  - `def kl_project(seed: np.ndarray, margins: np.ndarray, targets: np.ndarray, *,
    lower: np.ndarray, upper: np.ndarray, floor: float, tolerance: float,
    max_iterations: int) -> np.ndarray`
  - `def constraint_violation(x: np.ndarray, margins: np.ndarray, targets: np.ndarray) -> float`

§12.4 requires, for overlapping margins, minimizing the I-divergence
`Σ_i [x_i log(x_i / x̃_i) - x_i + x̃_i]` over the feasible set, "with a small positive floor for
zero raw seeds". A zero seed makes the objective undefined, so the floor is a hard numerical
requirement, not a nicety — it comes from `config.reconciliation.zero_seed_floor`.

A weighted quadratic projection MAY be substituted, but §12.4 requires the objective and weights to
be "versioned and validation-tested". `general_method` in config is that version marker; this task
implements `kl_projection` only and leaves `weighted_quadratic` unimplemented, raising
`NotImplementedError` naming the config key — an honest gap beats a silently different objective.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_projection.py`:

```python
"""§12.4 generalized projection: never increases violation, respects bounds, honours the floor."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.reconcile.projection import constraint_violation, kl_project

FLOOR = 1.0e-12
TOL = 1.0e-9
ITERS = 1000


def test_projection_reaches_a_single_sum_constraint_exactly() -> None:
    seed = np.array([1.0, 2.0, 1.0])
    margins = np.array([[1.0, 1.0, 1.0]])
    out = kl_project(seed, margins, np.array([100.0]), lower=np.zeros(3),
                     upper=np.full(3, np.inf), floor=FLOOR, tolerance=TOL, max_iterations=ITERS)
    assert out.sum() == pytest.approx(100.0, abs=1e-6)


def test_projection_never_increases_constraint_violation() -> None:
    """§17.3's property, stated directly."""
    rng = np.random.default_rng(20260905)
    for _ in range(25):
        n = int(rng.integers(3, 8))
        seed = rng.uniform(0.1, 10.0, size=n)
        margins = np.vstack([np.ones(n), rng.integers(0, 2, size=n).astype(float)])
        targets = np.array([seed.sum() * 1.3, seed.sum() * 0.4])
        before = constraint_violation(seed, margins, targets)
        out = kl_project(seed, margins, targets, lower=np.zeros(n), upper=np.full(n, np.inf),
                         floor=FLOOR, tolerance=TOL, max_iterations=ITERS)
        assert constraint_violation(out, margins, targets) <= before + 1e-9


def test_a_zero_seed_is_floored_rather_than_making_the_objective_undefined() -> None:
    """§12.4: "with a small positive floor for zero raw seeds"."""
    seed = np.array([0.0, 1.0, 1.0])
    out = kl_project(seed, np.array([[1.0, 1.0, 1.0]]), np.array([30.0]), lower=np.zeros(3),
                     upper=np.full(3, np.inf), floor=FLOOR, tolerance=TOL, max_iterations=ITERS)
    assert np.all(np.isfinite(out))
    assert out[0] > 0.0
    assert out.sum() == pytest.approx(30.0, abs=1e-6)


def test_projection_respects_finite_upper_bounds() -> None:
    seed = np.array([5.0, 1.0, 1.0])
    upper = np.array([2.0, np.inf, np.inf])
    out = kl_project(seed, np.array([[1.0, 1.0, 1.0]]), np.array([20.0]), lower=np.zeros(3),
                     upper=upper, floor=FLOOR, tolerance=TOL, max_iterations=ITERS)
    assert out[0] <= 2.0 + 1e-9
    assert out.sum() == pytest.approx(20.0, abs=1e-6)


def test_projection_output_is_strictly_positive() -> None:
    """A KL projection cannot leave the positive orthant; a zero would make a later log undefined."""
    seed = np.array([1.0, 1.0, 1.0])
    out = kl_project(seed, np.array([[1.0, 1.0, 1.0]]), np.array([3.0]), lower=np.zeros(3),
                     upper=np.full(3, np.inf), floor=FLOOR, tolerance=TOL, max_iterations=ITERS)
    assert np.all(out > 0.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_projection.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `projection.py`**

```python
"""§12.4 general feasible-polytope projection under I-divergence (KL).

x = argmin_{x in F} sum_i [ x_i log(x_i / seed_i) - x_i + seed_i ]

Solved by iterative proportional fitting with bound clipping: for each margin in turn, scale the
cells it touches so the margin is met, then clip to bounds and repeat. On a pure equality system
with no bounds this is exactly IPF and converges to the I-projection; with bounds it is the
standard clipped variant, and the acceptance test is the one §17.3 states -- violation must never
increase -- rather than a convergence proof.

WHY A FLOOR ON ZERO SEEDS IS MANDATORY, NOT COSMETIC. The objective contains log(x_i / seed_i),
which is undefined at seed_i = 0, and multiplicative updates cannot lift a zero seed off zero at
any rate. §12.4 requires "a small positive floor for zero raw seeds"; the value is this package's
decision and lives in `config.reconciliation.zero_seed_floor`.

WHY `weighted_quadratic` IS NOT IMPLEMENTED HERE. §12.4 permits it but requires the objective and
weights to be "versioned and validation-tested". Nothing in Stage 3 validates a second objective,
so the config value is accepted as a version marker and the code path raises rather than quietly
running KL under a different name.
"""

from __future__ import annotations

import numpy as np


def constraint_violation(
    x: np.ndarray, margins: np.ndarray, targets: np.ndarray
) -> float:
    """Total absolute margin violation -- the quantity §17.3 requires never to increase."""
    return float(np.abs(margins @ x - targets).sum())


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
) -> np.ndarray:
    """Project `seed` onto {x : margins @ x == targets, lower <= x <= upper} under I-divergence."""
    x = np.maximum(np.asarray(seed, dtype=float), floor)
    lower = np.asarray(lower, dtype=float)
    upper = np.asarray(upper, dtype=float)

    for _ in range(max_iterations):
        previous = x.copy()
        for row, target in zip(margins, targets, strict=True):
            touched = row != 0.0
            if not touched.any():
                continue
            current = float(row @ x)
            if current <= 0.0:
                # Every touched cell is at the floor; a multiplicative update cannot move them, so
                # distribute the target evenly rather than dividing by zero.
                x[touched] = max(target / touched.sum(), floor)
                continue
            x[touched] *= target / current
            x = np.clip(x, np.maximum(lower, floor), upper)
        if np.max(np.abs(x - previous)) <= tolerance:
            break
    return x
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_projection.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/reconcile/projection.py tests/unit/test_projection.py
git commit -m "feat(reconcile): project draws into the feasible polytope under I-divergence"
```

---

### Task 7: Size-matrix reconciliation (§12.5)

**Files:**
- Create: `src/logging_employment/reconcile/matrix.py`
- Test: `tests/unit/test_matrix.py`

**Interfaces:**
- Consumes: `kl_project`, `constraint_violation`; `IncompatibleMarginError` (already in `errors.py`).
- Produces: `def reconcile_matrix(seed: np.ndarray, row_totals: np.ndarray,
  column_totals: np.ndarray | None, *, tolerance: float, max_iterations: int,
  floor: float) -> np.ndarray`

**This task has no real input on the D1 window, by construction.** `target_cell` carries 4,716
`state_total` cells, 51 `national_size` cells, and 8 `national_total` cells — and **zero**
state-by-size cells. Matrix reconciliation therefore has nothing to reconcile until Stage 6 builds
the state × month × size grid. It is implemented and tested **synthetically** now because Stage 6
consumes it and §17.3 requires the property, not because this stage runs it on data.

§12.5's three rules: without bounds use RAS/IPF or an equivalent entropy projection; with bounds or
overlapping margins use the general convex projection; **if margins are inconsistent, fail and
diagnose rather than forcing convergence.**

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_matrix.py`:

```python
"""§12.5 row-and-column reconciliation. Synthetic by construction: D1 has no state-by-size cells."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.errors import IncompatibleMarginError
from logging_employment.reconcile.matrix import reconcile_matrix

TOL = 1.0e-9
ITERS = 1000
FLOOR = 1.0e-12


def test_row_totals_alone_are_matched_exactly() -> None:
    seed = np.array([[1.0, 1.0], [2.0, 2.0]])
    out = reconcile_matrix(seed, np.array([10.0, 20.0]), None,
                           tolerance=TOL, max_iterations=ITERS, floor=FLOOR)
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-7)


def test_row_and_column_reconciliation_is_exact() -> None:
    """§17.3's property. Consistent margins: both totals sum to 30."""
    seed = np.array([[1.0, 3.0], [2.0, 1.0]])
    out = reconcile_matrix(seed, np.array([10.0, 20.0]), np.array([12.0, 18.0]),
                           tolerance=TOL, max_iterations=ITERS, floor=FLOOR)
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-6)
    assert out.sum(axis=0) == pytest.approx([12.0, 18.0], abs=1e-6)


def test_inconsistent_margins_fail_rather_than_forcing_convergence() -> None:
    """§12.5's third rule, verbatim: "fail and diagnose rather than forcing convergence"."""
    seed = np.ones((2, 2))
    with pytest.raises(IncompatibleMarginError) as excinfo:
        reconcile_matrix(seed, np.array([10.0, 20.0]), np.array([12.0, 99.0]),
                         tolerance=TOL, max_iterations=ITERS, floor=FLOOR)
    assert "30" in str(excinfo.value)
    assert "111" in str(excinfo.value)


def test_a_zero_seed_row_is_floored_rather_than_dividing_by_zero() -> None:
    seed = np.array([[0.0, 0.0], [1.0, 1.0]])
    out = reconcile_matrix(seed, np.array([10.0, 20.0]), None,
                           tolerance=TOL, max_iterations=ITERS, floor=FLOOR)
    assert np.all(np.isfinite(out))
    assert out.sum(axis=1) == pytest.approx([10.0, 20.0], abs=1e-7)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_matrix.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `matrix.py`**

```python
"""§12.5 size matrix reconciliation: row sums to reconciled state totals, columns to class margins.

NO REAL INPUT UNTIL STAGE 6. Stage 2's `target_cell` carries state totals, national size classes,
and national totals -- and no state-by-size cell at all. This module is therefore exercised only
by synthetic fixtures in Stage 3, and becomes live when Stage 6 builds the state x month x size
grid. That is a statement about the data, not a gap in the implementation.

§12.5's rules, in order: without bounds use RAS/IPF or an equivalent entropy projection; with
bounds or overlapping margins use the general convex projection; and "If margins are inconsistent,
fail and diagnose rather than forcing convergence." The third rule is why the consistency check
runs BEFORE any iteration: an IPF loop over inconsistent margins does not diverge loudly, it
oscillates quietly and returns whichever half-step the iteration cap happened to stop on.
"""

from __future__ import annotations

import numpy as np

from ..errors import IncompatibleMarginError
from .projection import kl_project


def reconcile_matrix(
    seed: np.ndarray,
    row_totals: np.ndarray,
    column_totals: np.ndarray | None,
    *,
    tolerance: float,
    max_iterations: int,
    floor: float,
) -> np.ndarray:
    """Scale `seed` so its rows sum to `row_totals` and, when given, columns to `column_totals`."""
    seed = np.asarray(seed, dtype=float)
    n_rows, n_cols = seed.shape

    if column_totals is not None:
        row_sum = float(np.sum(row_totals))
        col_sum = float(np.sum(column_totals))
        if not np.isclose(row_sum, col_sum, rtol=0.0, atol=max(tolerance, 1e-6)):
            raise IncompatibleMarginError(
                f"row totals sum to {row_sum} but column totals sum to {col_sum}; §12.5 requires "
                "failing and diagnosing rather than forcing convergence"
            )

    # One margin row per constraint, over the flattened matrix.
    margins: list[np.ndarray] = []
    targets: list[float] = []
    for r in range(n_rows):
        row = np.zeros(n_rows * n_cols)
        row[r * n_cols : (r + 1) * n_cols] = 1.0
        margins.append(row)
        targets.append(float(row_totals[r]))
    if column_totals is not None:
        for c in range(n_cols):
            col = np.zeros(n_rows * n_cols)
            col[c::n_cols] = 1.0
            margins.append(col)
            targets.append(float(column_totals[c]))

    flat = kl_project(
        seed.reshape(-1),
        np.vstack(margins),
        np.array(targets),
        lower=np.zeros(n_rows * n_cols),
        upper=np.full(n_rows * n_cols, np.inf),
        floor=floor,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    return flat.reshape(n_rows, n_cols)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_matrix.py -v`
Expected: PASS, all four tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/reconcile/matrix.py tests/unit/test_matrix.py
git commit -m "feat(reconcile): reconcile a size matrix to row and column margins, failing on inconsistency"
```

---

### Task 8: Balanced integerization (§12.6)

**Files:**
- Create: `src/logging_employment/reconcile/integerize.py`
- Test: `tests/unit/test_integerize.py`

**Interfaces:**
- Consumes: `ReconciliationConfig.integerization_tiebreak`.
- Produces: `def integerize(values: dict[str, float], total: int, *, lower: dict[str, int] |
  None = None, upper: dict[str, int | None] | None = None) -> dict[str, int]`

§12.6's six steps, verbatim: floor each value; compute remaining units for each required margin;
distribute units by largest fractional remainder or a controlled-rounding optimizer; respect
deterministic lower and upper integer bounds; recheck every hard margin; store both continuous and
integerized values. And then: **"Integerization MUST NOT be applied independently cell by cell."**

That final line is the whole point of the task. Rounding each cell on its own breaks the margin —
three cells at 3.4 each round to 9, not the 10 they summed to. The tie-break MUST be deterministic
(by `cell_id`) or §16.1's idempotence requirement breaks.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_integerize.py`:

```python
"""§12.6 balanced integerization: the margin survives rounding, and rounding is reproducible."""

from __future__ import annotations

import pytest

from logging_employment.reconcile.integerize import integerize


def test_the_total_survives_rounding() -> None:
    """Independent rounding would give 9, not 10. §12.6 forbids exactly that."""
    out = integerize({"01": 3.4, "02": 3.3, "04": 3.3}, total=10)
    assert sum(out.values()) == 10


def test_units_go_to_the_largest_fractional_remainders() -> None:
    out = integerize({"01": 1.9, "02": 1.6, "04": 1.5}, total=5)
    assert sum(out.values()) == 5
    assert out["01"] == 2


def test_the_tiebreak_is_deterministic_and_repeatable() -> None:
    """§16.1 requires idempotence; a random tie-break would break it.

    Identical fractional parts across every cell force the tie-break to decide alone.
    """
    values = {"04": 1.5, "01": 1.5, "02": 1.5}
    first = integerize(values, total=5)
    for _ in range(20):
        assert integerize(values, total=5) == first
    # Ties break by cell_id ascending, so the lowest ids take the extra units.
    assert first["01"] == 2
    assert first["02"] == 2
    assert first["04"] == 1


def test_integer_lower_and_upper_bounds_are_respected() -> None:
    out = integerize({"01": 5.5, "02": 2.5, "04": 2.0}, total=10,
                     upper={"01": 4, "02": None, "04": None})
    assert sum(out.values()) == 10
    assert out["01"] <= 4


def test_a_zero_total_yields_all_zeros() -> None:
    assert integerize({"01": 0.0, "02": 0.0}, total=0) == {"01": 0, "02": 0}


def test_an_empty_input_returns_empty() -> None:
    assert integerize({}, total=0) == {}


def test_a_total_below_the_summed_lower_bounds_raises() -> None:
    with pytest.raises(ValueError):
        integerize({"01": 1.0, "02": 1.0}, total=1, lower={"01": 1, "02": 1})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_integerize.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `integerize.py`**

```python
"""§12.6 balanced integerization.

"Integerization MUST NOT be applied independently cell by cell." That sentence is the module's
reason to exist: three cells at 3.4 rounded independently give 9, and the margin they were
reconciled to is gone. The units are allocated against the margin instead -- floor everything,
count what is left, and hand the remainder out by largest fractional part.

THE TIE-BREAK MUST BE DETERMINISTIC. §16.1 requires every command to be idempotent for the same
inputs. Ties are common here because reconciled allocations of equal-weight cells are exactly
equal, so a tie-break by dict order, hash order, or anything unordered would make two runs of the
same data disagree on which cell got the extra job. Ties break by `cell_id` ascending.
"""

from __future__ import annotations

import math


def integerize(
    values: dict[str, float],
    total: int,
    *,
    lower: dict[str, int] | None = None,
    upper: dict[str, int | None] | None = None,
) -> dict[str, int]:
    """Round `values` to integers summing exactly to `total`, respecting integer bounds."""
    if not values:
        return {}
    lower = lower or {}
    upper = upper or {}

    floors = {cell: max(int(math.floor(value)), lower.get(cell, 0)) for cell, value in values.items()}
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

    out = dict(floors)
    index = 0
    while remaining > 0 and index < len(order) * (remaining + 1):
        cell = order[index % len(order)]
        cap = upper.get(cell)
        if cap is None or out[cell] < cap:
            out[cell] += 1
            remaining -= 1
        index += 1
    if remaining > 0:
        raise ValueError(
            f"{remaining} unit(s) could not be placed without breaching an integer upper bound"
        )
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_integerize.py -v`
Expected: PASS, all seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/reconcile/integerize.py tests/unit/test_integerize.py
git commit -m "feat(reconcile): integerize against the margin rather than cell by cell"
```

---

### Task 9: `reconcile_draws`, `PosteriorDraws`, and joint dependence (§12.7, §16.2)

**Files:**
- Create: `src/logging_employment/reconcile/draws.py`
- Modify: `src/logging_employment/reconcile/__init__.py`
- Test: `tests/unit/test_reconcile_draws.py`

**Interfaces:**
- Consumes: everything from Tasks 3–8; `ReconciliationConfig`.
- Produces:
  - `@dataclass(frozen=True) PosteriorDraws(cell_ids: tuple[str, ...], values: np.ndarray,
    chain: np.ndarray | None, draw: np.ndarray | None)`
  - `def reconcile_draws(raw_draws: PosteriorDraws, feasible_set: ReconciliationInputs,
    config: ReconciliationConfig) -> PosteriorDraws`
  - `@dataclass(frozen=True) ReconciliationInputs(anchor: Anchor, bounds: Bounds)`

§16.2 gives the signature `reconcile_draws(raw_draws: PosteriorDraws, feasible_set:
ConstraintSystem, config: ReconciliationConfig) -> PosteriorDraws`. Stage 3 has no posterior yet —
that is Stage 5 — so this task defines `PosteriorDraws` and implements the function so that a
one-draw array (a baseline point estimate) and an N-draw array (Stage 5's posterior) go through the
identical path. **Stage 5 must not need a second entry point.**

`feasible_set` is typed `ReconciliationInputs` rather than `ConstraintSystem`: the reconciler needs
an anchor and per-cell bounds, and a `BuiltSystem` carries neither in that shape. Note the
deviation in the docstring so Stage 5's implementer is not surprised by the signature.

§12.7: posterior summaries MUST be computed from reconciled **joint** draws, and joint draws MUST
remain available downstream. This function therefore returns draws, never summaries, and never
reduces the draw axis.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_reconcile_draws.py`:

```python
"""§16.2's reconcile_draws: one path for a point estimate and for a posterior."""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.config import ReconciliationConfig
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.draws import (
    PosteriorDraws,
    ReconciliationInputs,
    reconcile_draws,
)
from logging_employment.reconcile.scaling import Bounds

CELLS = ("01", "02", "04")


def _config() -> ReconciliationConfig:
    return ReconciliationConfig(
        single_margin_method="bounded_proportional_scaling",
        general_method="kl_projection",
        integerize_release=True,
    )


def _inputs(residual: float = 100.0) -> ReconciliationInputs:
    return ReconciliationInputs(
        anchor=Anchor("2024-03", residual, CELLS, "declared_national_total"),
        bounds=Bounds(lower=dict.fromkeys(CELLS, 0.0), upper=dict.fromkeys(CELLS, None)),
    )


def test_a_single_draw_reconciles_exactly_to_the_residual() -> None:
    """A baseline point estimate is a one-draw posterior; there is no second entry point."""
    raw = PosteriorDraws(cell_ids=CELLS, values=np.array([[1.0, 2.0, 1.0]]), chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape == (1, 3)
    assert out.values[0].sum() == pytest.approx(100.0, abs=1e-6)


def test_every_draw_is_reconciled_not_only_the_mean() -> None:
    """INV-012's shape: the constraint holds on each draw, not on a summary of them."""
    rng = np.random.default_rng(20260905)
    raw = PosteriorDraws(cell_ids=CELLS, values=rng.uniform(0.1, 9.0, size=(64, 3)),
                         chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape == (64, 3)
    for row in out.values:
        assert row.sum() == pytest.approx(100.0, abs=1e-6)


def test_the_draw_axis_is_never_reduced() -> None:
    """§12.7: joint draws MUST remain available; a summary here would destroy the dependence."""
    raw = PosteriorDraws(cell_ids=CELLS, values=np.ones((32, 3)), chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.values.shape[0] == 32


def test_chain_and_draw_indexes_survive_reconciliation() -> None:
    raw = PosteriorDraws(cell_ids=CELLS, values=np.ones((4, 3)),
                         chain=np.array([0, 0, 1, 1]), draw=np.array([0, 1, 0, 1]))
    out = reconcile_draws(raw, _inputs(), _config())
    assert out.chain.tolist() == [0, 0, 1, 1]
    assert out.draw.tolist() == [0, 1, 0, 1]


def test_reconciled_draws_are_negatively_dependent_across_cells() -> None:
    """§12.7's motivation, made checkable: adding up to a fixed total induces negative dependence.

    Marginal intervals cannot see this, which is exactly why the draws must stay joint.
    """
    rng = np.random.default_rng(4096)
    raw = PosteriorDraws(cell_ids=CELLS, values=rng.uniform(0.5, 5.0, size=(512, 3)),
                         chain=None, draw=None)
    out = reconcile_draws(raw, _inputs(), _config())
    corr = np.corrcoef(out.values, rowvar=False)
    assert corr[0, 1] < 0.0


def test_a_cell_set_mismatch_is_refused() -> None:
    raw = PosteriorDraws(cell_ids=("01", "02"), values=np.ones((2, 2)), chain=None, draw=None)
    with pytest.raises(ValueError):
        reconcile_draws(raw, _inputs(), _config())
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_reconcile_draws.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `draws.py`**

```python
"""§16.2's `reconcile_draws`, and the joint-draw guarantee of §12.7.

ONE PATH FOR A POINT ESTIMATE AND A POSTERIOR. A baseline produces one vector; Stage 5 produces
thousands. Both enter here as a (draws, cells) array and leave reconciled, so Stage 5 needs no
second entry point and no separate code path can drift away from this one.

> Deviation from §16.2: the spec types the second parameter `ConstraintSystem`. The reconciler
> needs an allocation anchor and per-cell bounds; a `BuiltSystem` carries a cell table, row table,
> and coefficient table, and neither an anchor -- which is a Stage 3 modeling assumption that no
> constraint row may encode -- nor bounds in per-cell form. `ReconciliationInputs` is that pair.
> Stage 5 constructs one from `deterministic_bounds` plus the anchor and calls the same function.

§12.7: "Posterior summaries must be computed from reconciled joint draws." This function returns
draws and never summarises, and never reduces the draw axis. The negative dependence that adding
up induces is visible only in the joint object, so a mean computed here and passed on would
silently discard the thing §12.7 exists to protect.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import ReconciliationConfig
from .allocate import Weights
from .anchor import Anchor
from .scaling import Bounds, scale_into_bounds


@dataclass(frozen=True)
class PosteriorDraws:
    """Joint draws over cells, with the chain and draw indexes §16.2's store must preserve."""

    cell_ids: tuple[str, ...]
    values: np.ndarray  # shape (n_draws, n_cells)
    chain: np.ndarray | None
    draw: np.ndarray | None


@dataclass(frozen=True)
class ReconciliationInputs:
    """The feasible set as the reconciler needs it: one anchor and per-cell bounds."""

    anchor: Anchor
    bounds: Bounds


def reconcile_draws(
    raw_draws: PosteriorDraws,
    feasible_set: ReconciliationInputs,
    config: ReconciliationConfig,
) -> PosteriorDraws:
    """Map every raw draw into the feasible set, one draw at a time, preserving the draw axis."""
    if config.general_method == "weighted_quadratic":
        raise NotImplementedError(
            "reconciliation.general_method='weighted_quadratic' is permitted by §12.4 only with a "
            "versioned, validation-tested objective and weights; Stage 3 validates none, so this "
            "path is not implemented"
        )
    anchor = feasible_set.anchor
    if tuple(raw_draws.cell_ids) != tuple(anchor.missing_cells):
        raise ValueError(
            f"draw cells {list(raw_draws.cell_ids)} do not match the missing set "
            f"{list(anchor.missing_cells)}"
        )

    reconciled = np.empty_like(np.asarray(raw_draws.values, dtype=float))
    for index, row in enumerate(np.asarray(raw_draws.values, dtype=float)):
        weights = Weights(
            # §12.4's floor doubles as the guard that keeps a zero draw a legal weight: §12.2
            # requires positive raw weights, and a raw draw of exactly 0 is not one.
            values={
                cell: max(float(value), config.zero_seed_floor)
                for cell, value in zip(anchor.missing_cells, row, strict=True)
            },
            basis=dict.fromkeys(anchor.missing_cells, "own_estimator"),
        )
        allocated = scale_into_bounds(
            anchor,
            weights,
            feasible_set.bounds,
            tolerance=config.tolerance,
            max_iterations=config.max_bisection_iterations,
        )
        reconciled[index] = [allocated[cell] for cell in anchor.missing_cells]

    return PosteriorDraws(
        cell_ids=raw_draws.cell_ids,
        values=reconciled,
        chain=raw_draws.chain,
        draw=raw_draws.draw,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_reconcile_draws.py -v`
Expected: PASS, all six tests.

- [ ] **Step 5: Export the full reconcile surface**

Rewrite `src/logging_employment/reconcile/__init__.py`'s exports to cover the whole subpackage:

```python
from .allocate import Weights, allocate, check_domain
from .anchor import (
    Anchor,
    Partition,
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)
from .draws import PosteriorDraws, ReconciliationInputs, reconcile_draws
from .integerize import integerize
from .matrix import reconcile_matrix
from .projection import constraint_violation, kl_project
from .scaling import Bounds, scale_into_bounds

__all__ = [
    "Anchor",
    "Bounds",
    "Partition",
    "PosteriorDraws",
    "ReconciliationInputs",
    "Weights",
    "allocate",
    "assert_universe_closes",
    "check_domain",
    "closure_audit",
    "constraint_violation",
    "integerize",
    "kl_project",
    "national_residual",
    "observed_partition",
    "reconcile_draws",
    "reconcile_matrix",
    "scale_into_bounds",
]
```

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/reconcile/ tests/unit/test_reconcile_draws.py
git commit -m "feat(reconcile): add reconcile_draws with one path for point estimates and posteriors"
```

---

### Task 10: The `Estimator` protocol and the declared-composite weight machinery

**Files:**
- Create: `src/logging_employment/baselines/__init__.py`
- Create: `src/logging_employment/baselines/interfaces.py`
- Test: `tests/unit/test_baseline_interfaces.py`

**Interfaces:**
- Consumes: `Weights`, `Anchor`, `WeightDomainError`, `WEIGHT_BASES`, `BaselinesConfig`.
- Produces:
  - `class Estimator(Protocol)` with `estimator_id: str` and
    `def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline`
  - `@dataclass(frozen=True) EstimatorContext(monthly, cbp, partitions, config)`
  - `@dataclass(frozen=True) Decline(reason: str)`
  - `def compose(own: dict[str, float], fallback: dict[str, float], anchor: Anchor, *,
    allowed: bool) -> Weights`

§16.2 names `Estimator` only inside `run_pseudo_suppression`'s signature and never defines it.
Stage 3 defines it, because Stage 4 consumes it.

**The composite rule is the load-bearing piece.** Under an all-or-nothing rule §10.3 and §10.4
decline in 96/96 months on the D1 window, emptying §10.8's rungs 1 and 3. `compose` is what turns
partial coverage into a declared composite with per-cell provenance instead of either a silent
subset or a total decline.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baseline_interfaces.py`:

```python
"""The Estimator protocol and the declared-composite rule that keeps §10.8 populated."""

from __future__ import annotations

import pytest

from logging_employment.baselines.interfaces import Decline, compose
from logging_employment.errors import WeightDomainError
from logging_employment.reconcile.anchor import Anchor

CELLS = ("01", "02", "04")


def _anchor() -> Anchor:
    return Anchor("2024-03", 100.0, CELLS, "declared_national_total")


def test_full_own_coverage_needs_no_fallback() -> None:
    w = compose({"01": 1.0, "02": 2.0, "04": 3.0}, {"01": 9.0, "02": 9.0, "04": 9.0},
                _anchor(), allowed=True)
    assert set(w.basis.values()) == {"own_estimator"}


def test_partial_own_coverage_composes_and_records_the_basis_per_cell() -> None:
    """Six D1 states have no observed history and two have no CBP row; every month hits one."""
    w = compose({"01": 1.0, "02": 2.0}, {"01": 9.0, "02": 9.0, "04": 7.0},
                _anchor(), allowed=True)
    assert w.values["04"] == 7.0
    assert w.basis["01"] == "own_estimator"
    assert w.basis["04"] == "establishment_fallback"


def test_composition_refused_by_config_yields_a_decline_not_a_silent_subset() -> None:
    out = compose({"01": 1.0, "02": 2.0}, {"01": 9.0, "02": 9.0, "04": 7.0},
                  _anchor(), allowed=False)
    assert isinstance(out, Decline)
    assert "04" in out.reason


def test_a_fallback_that_cannot_cover_the_gap_is_refused() -> None:
    """§10.2's rung is complete on D1, but the code may not assume that."""
    with pytest.raises(WeightDomainError):
        compose({"01": 1.0}, {"01": 9.0, "02": 9.0}, _anchor(), allowed=True)


def test_a_non_positive_own_weight_falls_back_rather_than_poisoning_the_vector() -> None:
    """§12.2 requires positive weights; a zero own-weight is not one."""
    w = compose({"01": 1.0, "02": 0.0, "04": 3.0}, {"01": 9.0, "02": 5.0, "04": 9.0},
                _anchor(), allowed=True)
    assert w.values["02"] == 5.0
    assert w.basis["02"] == "establishment_fallback"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baseline_interfaces.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.baselines'`.

- [ ] **Step 3: Write `interfaces.py`**

```python
"""The `Estimator` protocol, and the declared-composite rule every baseline composes under.

§16.2 names `Estimator` inside `run_pseudo_suppression`'s signature and never defines it. Stage 3
defines it because Stage 4 consumes it.

AN ESTIMATOR PRODUCES WEIGHTS, NOT ESTIMATES. §10 (spec:942) requires every baseline to use "the
same ... reconciliation layer as the full model". The way to make that true rather than merely
stated is to leave estimators no way to produce a number: they return q, and `reconcile.allocate`
turns q into an estimate. §10.1 is q identically 1; §10.2 is q = establishments; §10.3 is a share
variant; §10.4 is shrunk CBP intensity times exposure; §10.6 is exp(prediction).

WHY COMPOSITION IS DECLARED RATHER THAN FORBIDDEN OR SILENT. Six D1 states have zero observed
employment months (AK, DE, HI, ND, NV, VT) and two have no CBP row in any year (HI, RI). Every
month's missing set contains at least one of each, so an all-or-nothing rule would make §10.3 and
§10.4 decline in 96 of 96 months and leave §10.8's rungs 1 and 3 permanently empty -- including the
"preferred transparent baseline" slot Stage 4 must fill with numbers. Silent subsetting is the
other failure: normalizing a partial vector reallocates the uncovered cells' share onto the covered
ones and looks perfectly well-formed. So composition is permitted, and every composed cell carries
`weight_basis = 'establishment_fallback'` in the output table and a count in the manifest. §10.8's
own rank-1 phrasing -- "employee-per-establishment WITH ROBUST HISTORICAL ADJUSTMENT" -- is the
spec's precedent that a composed estimator is legitimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import polars as pl

from ..config import Config
from ..errors import WeightDomainError
from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor, Partition

OWN = "own_estimator"
FALLBACK = "establishment_fallback"


@dataclass(frozen=True)
class Decline:
    """A baseline's refusal to run for a month, carrying the reason a reader needs."""

    reason: str


@dataclass(frozen=True)
class EstimatorContext:
    """Everything an estimator may read. Nothing here is a source endpoint."""

    monthly: pl.DataFrame
    cbp: pl.DataFrame
    partitions: dict[str, Partition]
    config: Config


class Estimator(Protocol):
    """A named producer of positive raw weights over one month's missing set."""

    estimator_id: str

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Positive weights for every cell in `anchor.missing_cells`, or a `Decline`."""
        ...


def compose(
    own: dict[str, float],
    fallback: dict[str, float],
    anchor: Anchor,
    *,
    allowed: bool,
) -> Weights | Decline:
    """Own weight where it is positive and finite, declared fallback elsewhere.

    Raises `WeightDomainError` when the fallback itself cannot cover the gap: that is a data
    problem, not an estimator's refusal, and it must not be reported as a decline.
    """
    usable = {
        cell: value
        for cell, value in own.items()
        if cell in anchor.missing_cells and value is not None and value > 0.0
    }
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

    uncovered = [cell for cell in gaps if fallback.get(cell, 0.0) <= 0.0]
    if uncovered:
        raise WeightDomainError(
            f"{anchor.reference_month}: the establishment fallback cannot weight {sorted(uncovered)}"
        )

    values = dict(usable) | {cell: fallback[cell] for cell in gaps}
    basis = dict.fromkeys(usable, OWN) | dict.fromkeys(gaps, FALLBACK)
    return Weights(values=values, basis=basis)
```

Create `src/logging_employment/baselines/__init__.py`:

```python
"""The §10 transparent baselines.

Every estimator here produces weights and nothing else; `reconcile.allocate` turns weights into
estimates. That is what makes §10's "same reconciliation layer as the full model" concrete.
"""

from __future__ import annotations

from .interfaces import Decline, Estimator, EstimatorContext, compose

__all__ = ["Decline", "Estimator", "EstimatorContext", "compose"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baseline_interfaces.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/ tests/unit/test_baseline_interfaces.py
git commit -m "feat(baselines): add the Estimator protocol and the declared-composite weight rule"
```

---

### Task 11: §10.1 equal allocation and §10.2 establishment-proportional allocation

**Files:**
- Create: `src/logging_employment/baselines/simple.py`
- Test: `tests/unit/test_baselines_simple.py`

**Interfaces:**
- Consumes: `Estimator`, `EstimatorContext`, `Weights`, `Anchor`.
- Produces: `EqualAllocation` (`estimator_id = "equal_residual"`),
  `EstablishmentProportional` (`estimator_id = "establishment_proportional"`), and
  `def establishment_weights(context: EstimatorContext, anchor: Anchor) -> dict[str, float]` —
  the universal fallback rung every other baseline composes against.

§10.1: `Ê_{s,t} = R_t / |M_t|` — "Use only as a sanity check." It is deliberately absent from
§10.8's hierarchy.
§10.2: `Ê_{s,t} = R_t · A_{s,t} / Σ_{j∈M_t} A_{j,t}` — "the minimum fallback when only QCEW
establishment exposure is available", and §10.8's rung 4.

**§10.2's inputs are complete on the whole D1 window** — `qtrly_establishments` is non-null and
≥ 1 (measured range 1..282) on all 1,227 suppressed cells, and its sum over `M_t` is strictly
positive in every month. That completeness is why it doubles as the universal fallback rung.

**Record the within-quarter constancy as a labelled assumption.** §10.2 writes `A_{s,t}` monthly,
but QCEW publishes establishments quarterly and `qcew_monthly` repeats the quarterly value across
the three months (measured: constant in all 1,572 state-quarters). §11.1 defines only `A_{s,q(t)}`
and calls within-quarter constancy "a baseline modeling assumption, not a public identity". Say so
in the docstring; do not silently treat the repeated value as a monthly measurement.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baselines_simple.py`:

```python
"""§10.1 and §10.2, and the establishment rung every other baseline falls back to."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.interfaces import EstimatorContext
from logging_employment.baselines.simple import (
    EqualAllocation,
    EstablishmentProportional,
    establishment_weights,
)
from logging_employment.reconcile.allocate import allocate
from logging_employment.reconcile.anchor import Anchor, observed_partition


def _context(monthly: pl.DataFrame, cfg) -> EstimatorContext:
    return EstimatorContext(
        monthly=monthly, cbp=pl.DataFrame(), partitions=observed_partition(monthly), config=cfg
    )


def _anchor(cells: tuple[str, ...], residual: float = 90.0) -> Anchor:
    return Anchor("2024-03", residual, cells, "declared_national_total")


def test_equal_allocation_splits_the_residual_evenly(make_monthly, appendix_a_config) -> None:
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 1},
        {"state_fips": "02", "area_fips": "02000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 99},
        {"state_fips": "04", "area_fips": "04000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 50},
    )
    anchor = _anchor(("01", "02", "04"))
    weights = EqualAllocation().weights(_context(monthly, appendix_a_config), anchor)
    out = allocate(anchor, weights)
    assert out == pytest.approx({"01": 30.0, "02": 30.0, "04": 30.0})


def test_establishment_proportional_weights_by_exposure(make_monthly, appendix_a_config) -> None:
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 1},
        {"state_fips": "02", "area_fips": "02000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 2},
    )
    anchor = _anchor(("01", "02"), residual=90.0)
    weights = EstablishmentProportional().weights(_context(monthly, appendix_a_config), anchor)
    out = allocate(anchor, weights)
    assert out == pytest.approx({"01": 30.0, "02": 60.0})


def test_the_establishment_rung_covers_every_missing_cell(make_monthly, appendix_a_config) -> None:
    """The property that makes §10.2 usable as the universal fallback."""
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 4},
        {"state_fips": "02", "area_fips": "02000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 7},
    )
    anchor = _anchor(("01", "02"))
    weights = establishment_weights(_context(monthly, appendix_a_config), anchor)
    assert set(weights) == {"01", "02"}
    assert all(value > 0 for value in weights.values())


def test_a_missing_cell_with_no_establishment_row_is_not_silently_dropped(
    make_monthly, appendix_a_config
) -> None:
    """An absent row is absence, not zero. It must surface, not vanish from the weight vector."""
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 4},
    )
    anchor = _anchor(("01", "38"))
    weights = establishment_weights(_context(monthly, appendix_a_config), anchor)
    assert "38" not in weights
```

Add the shared config fixture to `tests/unit/conftest.py`. It needs two module-level imports
that file does not yet have — add them to its existing import block:

```python
from pathlib import Path

from logging_employment.config import Config, load_config
```

then the fixture itself:

```python
@pytest.fixture()
def appendix_a_config() -> "Config":
    """The Appendix A configuration, parsed once, for estimators that read config keys."""
    return load_config(Path(__file__).resolve().parents[2] / "config.yaml")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_simple.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `simple.py`**

```python
"""§10.1 equal residual allocation and §10.2 establishment-count proportional allocation.

§10.2 IS ALSO THE UNIVERSAL FALLBACK RUNG. Its inputs are the only ones complete on every
suppressed cell of the D1 window -- `qtrly_establishments` is non-null and at least 1 on all 1,227
of them -- which is why §10.8 ranks it 4 as "the minimum fallback" and why every other estimator
composes against `establishment_weights` rather than declining.

WITHIN-QUARTER CONSTANCY IS A LABELLED ASSUMPTION, NOT A MEASUREMENT. §10.2 writes A_{s,t} with a
monthly subscript, but QCEW publishes establishment counts quarterly and `qcew_monthly` repeats the
quarterly value across all three months of its quarter (measured: constant in all 1,572
state-quarters). §11.1 defines only A_{s,q(t)} and calls within-quarter constancy "a baseline
modeling assumption, not a public identity". Using the repeated value is correct; calling it a
monthly measurement would not be.

§11.5's score is q = (A + eps_A) * exp(mu), and eps_A has no value anywhere in the spec. It is not
needed here: A >= 1 on every suppressed cell, so a positive offset would change the weights without
protecting anything. Stage 5 must set eps_A itself for the model's own score.
"""

from __future__ import annotations

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import OWN, EstimatorContext


def _missing_rows(context: EstimatorContext, anchor: Anchor) -> pl.DataFrame:
    """The published state rows for this month's missing cells."""
    return context.monthly.filter(
        (pl.col("area_type") == "state")
        & (pl.col("reference_month") == anchor.reference_month)
        & (pl.col("state_fips").is_in(list(anchor.missing_cells)))
    )


def establishment_weights(context: EstimatorContext, anchor: Anchor) -> dict[str, float]:
    """A_{s,t} per missing cell -- §10.2's weight and every other estimator's fallback.

    A cell with no published row is omitted rather than given a zero: absence and a published zero
    are different facts, and `compose` must be able to tell them apart.
    """
    rows = _missing_rows(context, anchor)
    return {
        str(row["state_fips"]): float(row["qtrly_establishments"])
        for row in rows.iter_rows(named=True)
        if row["qtrly_establishments"] is not None and row["qtrly_establishments"] > 0
    }


class EqualAllocation:
    """§10.1: q identically 1, so R_t splits evenly. "Use only as a sanity check."

    Absent from §10.8's fallback hierarchy on purpose -- it ignores every public signal about a
    state, including the establishment counts that are published even when employment is not.
    """

    estimator_id = "equal_residual"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights:
        return Weights(
            values=dict.fromkeys(anchor.missing_cells, 1.0),
            basis=dict.fromkeys(anchor.missing_cells, OWN),
        )


class EstablishmentProportional:
    """§10.2: q = A_{s,t}. §10.8's rung 4 and the fallback every composite leans on."""

    estimator_id = "establishment_proportional"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights:
        values = establishment_weights(context, anchor)
        return Weights(values=values, basis=dict.fromkeys(values, OWN))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baselines_simple.py -v`
Expected: PASS, all four tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/simple.py tests/unit/ tests/unit/conftest.py
git commit -m "feat(baselines): add equal and establishment-proportional allocation"
```

---

### Task 12: §10.3's five historical state-share variants

**Files:**
- Create: `src/logging_employment/baselines/historical.py`
- Test: `tests/unit/test_baselines_historical.py`

**Interfaces:**
- Consumes: `establishment_weights`, `compose`, `BaselinesConfig`.
- Produces: five estimators sharing one share-extraction helper —
  `LastObservedShare`, `SameMonthPreviousYearShare`, `RollingMedianShare`,
  `ExponentiallyWeightedShare`, `BreakAdjustedShare`.

§10.3 requires exactly five, listed verbatim (spec:968-972):

1. last observed state share;
2. same-month previous-year share;
3. rolling median share;
4. exponentially weighted historical share; and
5. a robust break-adjusted share.

Plus: "Every estimate must be reconciled to the current residual. **Historical shares must use
classification-consistent periods.**"

**The classification rule.** The window breaks at 2022-01 — NAICS 2017 covers 2017-01..2021-12,
NAICS 2022 covers 2022-01..2024-12. `config.baselines.historical_may_cross_naics_vintage` defaults
`false`, so a lookback stops at the break. This is what "classification-consistent periods" means
operationally, and it is a config key rather than a constant because the correct answer depends on
whether 113310 was actually retabulated at the break — which Stage 0 recorded as an *uncited*
premise (see `specs/deferred_items.md`).

**Coverage.** Six states have zero observed employment months in the whole window — AK, DE, HI, ND,
NV, VT — so no in-window share exists for them and every month's missing set contains at least one.
Measured split: **762 of 1,227 cells own-weight, 465 establishment-fallback.** Without composition
this family declines in 96/96 months and §10.8's rung 3 is empty.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baselines_historical.py`:

```python
"""§10.3's five share variants, the vintage rule, and the composite that keeps them running."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.historical import (
    BreakAdjustedShare,
    ExponentiallyWeightedShare,
    LastObservedShare,
    RollingMedianShare,
    SameMonthPreviousYearShare,
    observed_share_history,
)
from logging_employment.baselines.interfaces import FALLBACK, OWN, EstimatorContext
from logging_employment.reconcile.anchor import Anchor, observed_partition

ALL_FIVE = [
    LastObservedShare,
    SameMonthPreviousYearShare,
    RollingMedianShare,
    ExponentiallyWeightedShare,
    BreakAdjustedShare,
]


def test_section_10_3_ships_exactly_five_variants() -> None:
    """The spec lists five; a sixth or a fourth is a spec-coverage defect, not a style choice."""
    assert len(ALL_FIVE) == 5
    assert len({cls().estimator_id for cls in ALL_FIVE}) == 5


def _history(make_monthly) -> pl.DataFrame:
    rows = []
    for i, month in enumerate(["2023-01", "2023-02", "2023-03", "2024-03"]):
        rows.append({"area_type": "national", "area_fips": "US000", "state_fips": None,
                     "aggregation_level": "18", "reference_month": month,
                     "employment_value": 100, "qtrly_establishments": 10})
        rows.append({"state_fips": "01", "area_fips": "01000", "reference_month": month,
                     "employment_value": 40 + i, "qtrly_establishments": 4,
                     "observation_status": "observed"})
        rows.append({"state_fips": "02", "area_fips": "02000", "reference_month": month,
                     "employment_value": None, "qtrly_establishments": 6,
                     "observation_status": "suppressed"})
    return make_monthly(*rows)


def _context(monthly, cfg) -> EstimatorContext:
    return EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                            partitions=observed_partition(monthly), config=cfg)


@pytest.mark.parametrize("cls", ALL_FIVE)
def test_every_variant_produces_positive_weights_for_a_state_with_history(
    cls, make_monthly, appendix_a_config
) -> None:
    monthly = _history(make_monthly)
    # State 01 has history; force it into the missing set so a share exists to use.
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")
    out = cls().weights(_context(monthly, appendix_a_config), anchor)
    assert out.values["01"] > 0.0
    assert out.basis["01"] == OWN


@pytest.mark.parametrize("cls", ALL_FIVE)
def test_a_state_with_no_observed_history_takes_the_declared_fallback(
    cls, make_monthly, appendix_a_config
) -> None:
    """Six D1 states are in this position for all 96 months; 465 of 1,227 cells fall here."""
    monthly = _history(make_monthly)
    anchor = Anchor("2024-03", 50.0, ("02",), "declared_national_total")
    out = cls().weights(_context(monthly, appendix_a_config), anchor)
    assert out.basis["02"] == FALLBACK
    assert out.values["02"] == 6.0


def test_a_lookback_stops_at_the_naics_vintage_break(make_monthly, appendix_a_config) -> None:
    """§10.3: "Historical shares must use classification-consistent periods"."""
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2021-12",
         "naics_vintage": "NAICS 2017", "employment_value": 90, "qtrly_establishments": 4},
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2022-03",
         "naics_vintage": "NAICS 2022", "employment_value": 10, "qtrly_establishments": 4},
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "reference_month": "2022-03",
         "employment_value": 100, "qtrly_establishments": 4},
    )
    history = observed_share_history(
        monthly, state_fips="01", before="2022-03",
        lookback_months=24, may_cross_vintage=False, vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == []


def test_crossing_the_break_is_possible_only_when_config_permits(
    make_monthly, appendix_a_config
) -> None:
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2021-12",
         "naics_vintage": "NAICS 2017", "employment_value": 90, "qtrly_establishments": 4},
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "reference_month": "2021-12",
         "employment_value": 100, "qtrly_establishments": 4},
    )
    history = observed_share_history(
        monthly, state_fips="01", before="2022-03",
        lookback_months=24, may_cross_vintage=True, vintage="NAICS 2022",
    )
    assert history["reference_month"].to_list() == ["2021-12"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_historical.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `historical.py`**

```python
"""§10.3's five historical state-share baselines.

The spec lists exactly five (spec:968-972): last observed share, same-month previous-year share,
rolling median share, exponentially weighted historical share, and a robust break-adjusted share.
All five share one history extractor and differ only in how they reduce a series of shares to one
number, which is the whole reason they belong in one module.

CLASSIFICATION-CONSISTENT PERIODS. §10.3 requires them and does not define them. The D1 window
carries a NAICS vintage break at 2022-01 -- NAICS 2017 through 2021-12, NAICS 2022 from 2022-01 --
so a 24-month lookback from 2022-06 would otherwise mix two classifications. The default is to stop
at the break. It is a config key rather than a constant because whether 113310 was actually
retabulated at that break is an UNCITED premise in this repo (see `specs/deferred_items.md`), and a
key can be flipped by whoever finds the citation; a constant would have to be argued with.

COVERAGE, MEASURED. Six states have zero observed employment months in the whole window -- AK, DE,
HI, ND, NV, VT -- so no in-window share exists for them, and every one of the 96 months' missing
sets contains at least one. 762 of 1,227 cells get an own share; 465 take the declared
establishment fallback. Without composition this entire family would decline in 96/96 months and
§10.8's rung 3 would be permanently empty.
"""

from __future__ import annotations

import statistics

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext, compose
from .simple import establishment_weights


def observed_share_history(
    monthly: pl.DataFrame,
    *,
    state_fips: str,
    before: str,
    lookback_months: int,
    may_cross_vintage: bool,
    vintage: str,
) -> pl.DataFrame:
    """One state's observed shares of the national total, most recent last.

    A share is only defined where both the state row is observed and the national row is published,
    so months failing either are absent rather than zero.
    """
    national = monthly.filter(pl.col("area_type") == "national").select(
        ["reference_month", pl.col("employment_value").alias("national_value")]
    )
    rows = (
        monthly.filter(
            (pl.col("area_type") == "state")
            & (pl.col("state_fips") == state_fips)
            & (pl.col("observation_status") == "observed")
            & (pl.col("reference_month") < before)
        )
        .join(national, on="reference_month", how="inner")
        .filter(pl.col("national_value") > 0)
    )
    if not may_cross_vintage:
        rows = rows.filter(pl.col("naics_vintage") == vintage)
    return (
        rows.with_columns(
            (pl.col("employment_value") / pl.col("national_value")).alias("share")
        )
        .sort("reference_month")
        .tail(lookback_months)
        .select(["reference_month", "share"])
    )


class _ShareBaseline:
    """Shared plumbing: extract each missing cell's share history, reduce it, then compose."""

    estimator_id = "historical_share"

    def _reduce(self, shares: list[float], anchor: Anchor, history: pl.DataFrame) -> float | None:
        raise NotImplementedError

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        cfg = context.config.baselines
        vintage = _vintage_at(context.monthly, anchor.reference_month)
        own: dict[str, float] = {}
        for cell in anchor.missing_cells:
            history = observed_share_history(
                context.monthly,
                state_fips=cell,
                before=anchor.reference_month,
                lookback_months=cfg.historical_lookback_months,
                may_cross_vintage=cfg.historical_may_cross_naics_vintage,
                vintage=vintage,
            )
            shares = history["share"].to_list()
            if not shares:
                continue
            reduced = self._reduce(shares, anchor, history)
            if reduced is not None and reduced > 0.0:
                own[cell] = reduced
        return compose(
            own,
            establishment_weights(context, anchor),
            anchor,
            allowed=cfg.allow_declared_composite,
        )


def _vintage_at(monthly: pl.DataFrame, reference_month: str) -> str:
    """The NAICS vintage the target month is published under."""
    rows = monthly.filter(pl.col("reference_month") == reference_month)
    return str(rows["naics_vintage"][0])


class LastObservedShare(_ShareBaseline):
    """§10.3 variant 1."""

    estimator_id = "share_last_observed"

    def _reduce(self, shares, anchor, history):
        return shares[-1]


class SameMonthPreviousYearShare(_ShareBaseline):
    """§10.3 variant 2: the same calendar month one year earlier, or nothing.

    Falls back to no own weight rather than to the nearest month: substituting a different month
    would make this variant indistinguishable from `LastObservedShare` exactly when it matters.
    """

    estimator_id = "share_same_month_prior_year"

    def _reduce(self, shares, anchor, history):
        year, month = anchor.reference_month.split("-")
        wanted = f"{int(year) - 1:04d}-{month}"
        matched = history.filter(pl.col("reference_month") == wanted)["share"].to_list()
        return matched[0] if matched else None


class RollingMedianShare(_ShareBaseline):
    """§10.3 variant 3."""

    estimator_id = "share_rolling_median"

    def _reduce(self, shares, anchor, history):
        return statistics.median(shares)


class ExponentiallyWeightedShare(_ShareBaseline):
    """§10.3 variant 4. The half-life is one year of the lookback, so recency dominates smoothly."""

    estimator_id = "share_exponentially_weighted"
    decay = 0.5 ** (1.0 / 12.0)

    def _reduce(self, shares, anchor, history):
        weights = [self.decay ** (len(shares) - 1 - i) for i in range(len(shares))]
        return sum(w * s for w, s in zip(weights, shares, strict=True)) / sum(weights)


class BreakAdjustedShare(_ShareBaseline):
    """§10.3 variant 5: robust to a level break in the share series.

    Uses the median of the most recent segment after the largest single-step change, so one
    reclassification or one plant closure does not drag the estimate toward a regime that ended.
    A plain median over the whole lookback is what this variant exists NOT to be.
    """

    estimator_id = "share_break_adjusted"

    def _reduce(self, shares, anchor, history):
        if len(shares) < 4:
            return statistics.median(shares)
        steps = [abs(shares[i + 1] - shares[i]) for i in range(len(shares) - 1)]
        cut = steps.index(max(steps)) + 1
        segment = shares[cut:] or shares
        return statistics.median(segment)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baselines_historical.py -v`
Expected: PASS — 13 tests (two parametrized over five classes, plus three).

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/historical.py tests/unit/test_baselines_historical.py
git commit -m "feat(baselines): add the five historical share variants with a vintage-consistent lookback"
```

---

### Task 13: §10.4 CBP/QCEW employee-per-establishment baseline

**Files:**
- Create: `src/logging_employment/baselines/intensity.py`
- Test: `tests/unit/test_baselines_intensity.py`

**Interfaces:**
- Consumes: `establishment_weights`, `compose`; `HarmonizedData.cbp_state_size`.
- Produces: `CbpIntensity` (`estimator_id = "cbp_intensity"`), and
  `def march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> dict[str, float]`.

§10.4, verbatim: "For each state-year, estimate a robust March employee-per-establishment intensity
from CBP, shrink it toward regional/national values, combine it with QCEW establishment exposure,
and reconcile to the national residual. **This is the preferred transparent structural baseline.**"

It is §10.8's rung 1 and the roadmap's "named preferred transparent baseline slot that Stage 4
fills with numbers", so its coverage limits are load-bearing rather than incidental.

**Measured coverage.**

- `cbp_state_size` publishes **2017–2023 only**. **Reference year 2024 declines** — 12 months, 147
  suppressed cells. The whole content of §10.4 is a *year-specific* March intensity; carrying 2023
  forward is an invention with no spec basis. If someone later wants carry-forward it must be a
  config key, labelled a modeling assumption, and defaulted off.
- **Hawaii (`15`) and Rhode Island (`44`) have no `cbp_state_size` row in any published year** —
  186 cells take the establishment fallback.
- **4 CBP rows carry null employment and MUST be dropped, not read as zero** (INV-003).
- CBP is `empirical_measurement` with `is_hard = false` per SRC-CBP-004 and §9.3. It never becomes
  a constraint. Nothing in this task writes a constraint row.

**Shrinkage.** §10.4 says "shrink it toward regional/national values" without giving a form. Use a
count-weighted shrink toward the national March intensity, with weight `n / (n + k)` where `n` is
the state's establishment count and `k` a fixed prior strength. Record `k` in the docstring as this
package's decision.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baselines_intensity.py`:

```python
"""§10.4, the preferred transparent baseline, and the two coverage holes it must declare."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.interfaces import FALLBACK, OWN, Decline, EstimatorContext
from logging_employment.baselines.intensity import CbpIntensity, march_intensity
from logging_employment.contracts import CBP_STATE_SIZE_SCHEMA
from logging_employment.reconcile.anchor import Anchor, observed_partition

_CBP_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2023", "reference_year": 2023, "state_fips": "01",
    "industry_code": "113310", "naics_vintage": "NAICS 2022", "legal_form_code": "001",
    "size_code": "001", "size_label": "All establishments", "size_lower": 0, "size_upper": None,
    "establishments": 10, "employment": 50, "employment_flag": "", "employment_noise_range": "0",
    "disclosure_status": "published", "disclosure_regime": "noise_infusion",
    "reference_period": "week_including_march_12",
}


def _cbp(*rows: dict[str, object]) -> pl.DataFrame:
    return pl.DataFrame([_CBP_DEFAULTS | dict(r) for r in rows], schema=CBP_STATE_SIZE_SCHEMA)


def test_intensity_is_employment_over_establishments_per_state() -> None:
    out = march_intensity(
        _cbp({"state_fips": "01", "employment": 50, "establishments": 10},
             {"state_fips": "02", "employment": 90, "establishments": 30}),
        reference_year=2023,
    )
    assert out["01"] == pytest.approx(5.0)
    assert out["02"] == pytest.approx(3.0)


def test_a_suppressed_cbp_cell_is_dropped_not_read_as_zero() -> None:
    """INV-003. A null employment is absence of a measurement, not a measurement of zero."""
    out = march_intensity(
        _cbp({"state_fips": "01", "employment": None, "establishments": 10,
              "disclosure_status": "suppressed"}),
        reference_year=2023,
    )
    assert "01" not in out


def test_reference_year_2024_declines_rather_than_carrying_2023_forward(
    make_monthly, appendix_a_config
) -> None:
    """CBP publishes 2017-2023 only. §10.4's whole content is a year-specific March intensity."""
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2024-06",
         "observation_status": "suppressed", "employment_value": None,
         "qtrly_establishments": 5},
    )
    context = EstimatorContext(monthly=monthly, cbp=_cbp({"reference_year": 2023}),
                               partitions=observed_partition(monthly), config=appendix_a_config)
    anchor = Anchor("2024-06", 40.0, ("01",), "declared_national_total")
    out = CbpIntensity().weights(context, anchor)
    assert isinstance(out, Decline)
    assert "2024" in out.reason


def test_a_state_absent_from_cbp_takes_the_declared_fallback(
    make_monthly, appendix_a_config
) -> None:
    """Hawaii and Rhode Island are in this position for every published year."""
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2023-06",
         "observation_status": "suppressed", "employment_value": None, "qtrly_establishments": 5},
        {"state_fips": "15", "area_fips": "15000", "reference_month": "2023-06",
         "observation_status": "suppressed", "employment_value": None, "qtrly_establishments": 3},
    )
    context = EstimatorContext(
        monthly=monthly, cbp=_cbp({"state_fips": "01", "reference_year": 2023}),
        partitions=observed_partition(monthly), config=appendix_a_config,
    )
    anchor = Anchor("2023-06", 40.0, ("01", "15"), "declared_national_total")
    out = CbpIntensity().weights(context, anchor)
    assert out.basis["01"] == OWN
    assert out.basis["15"] == FALLBACK


def test_shrinkage_pulls_a_thin_state_toward_the_national_intensity() -> None:
    """§10.4: "shrink it toward regional/national values"."""
    cbp = _cbp(
        {"state_fips": "01", "employment": 1000, "establishments": 100},
        {"state_fips": "02", "employment": 100, "establishments": 1},
    )
    out = march_intensity(cbp, reference_year=2023, shrink_strength=5.0)
    # State 02's raw intensity is 100; national is 1100/101 ~= 10.9. One establishment cannot
    # carry a raw intensity that far from the national value.
    assert out["02"] < 100.0
    assert out["01"] == pytest.approx(10.0, abs=1.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_intensity.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `intensity.py`**

```python
"""§10.4: the preferred transparent structural baseline.

"For each state-year, estimate a robust March employee-per-establishment intensity from CBP, shrink
it toward regional/national values, combine it with QCEW establishment exposure, and reconcile to
the national residual." §10.8's rung 1, and the roadmap's preferred-baseline slot that Stage 4
fills with numbers -- so its coverage holes are load-bearing, not incidental.

WHAT CBP DOES AND DOES NOT COVER ON THIS WINDOW, MEASURED.
- 2017-2023 only. Reference year 2024 has no CBP vintage at all, so the 12 months of 2024 -- 147
  suppressed cells -- DECLINE. Carrying the 2023 March intensity forward would be an invention: the
  entire content of §10.4 is a year-specific March intensity, so a carried-forward value is not a
  weaker version of this baseline, it is a different one wearing its name.
- Hawaii ('15') and Rhode Island ('44') have no row in any published year. 186 cells take the
  declared establishment fallback rather than emptying the baseline.
- Four rows carry a null employment under CBP suppression and are dropped, never read as zero
  (INV-003).

CBP IS A MEASUREMENT, NOT A CONSTRAINT. SRC-CBP-004 enters CBP employment as an
`empirical_measurement` with `is_hard = false`, and §9.3 keeps it out of the deterministic feasible
set. Nothing here builds a constraint row. CBP's own noise infusion is why: `EMP_N_F` carries the
per-cell noise band and this table does not even have a column for it (see
`specs/deferred_items.md`), so a hard equality on a noised value would be false precision.

SHRINKAGE IS THIS PACKAGE'S FORM, NOT THE SPEC'S. §10.4 says "shrink toward regional/national
values" and gives no functional form. A count-weighted shrink toward the national March intensity
with weight n/(n+k) is used, k=5.0. A state with one establishment is pulled most of the way to the
national value; a state with a hundred is barely moved. `k` is recorded here because it is a
decision, not a measurement.
"""

from __future__ import annotations

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext, compose
from .simple import establishment_weights

DEFAULT_SHRINK_STRENGTH = 5.0
ALL_ESTABLISHMENTS_SIZE_CODE = "001"


def march_intensity(
    cbp: pl.DataFrame,
    *,
    reference_year: int,
    shrink_strength: float = DEFAULT_SHRINK_STRENGTH,
) -> dict[str, float]:
    """Shrunk March employees-per-establishment per state, for one CBP reference year."""
    rows = cbp.filter(
        (pl.col("reference_year") == reference_year)
        & (pl.col("size_code") == ALL_ESTABLISHMENTS_SIZE_CODE)
        & pl.col("employment").is_not_null()
        & (pl.col("establishments") > 0)
    )
    if rows.height == 0:
        return {}
    national_employment = float(rows["employment"].sum())
    national_establishments = float(rows["establishments"].sum())
    national_intensity = national_employment / national_establishments
    out: dict[str, float] = {}
    for row in rows.iter_rows(named=True):
        n = float(row["establishments"])
        raw = float(row["employment"]) / n
        weight = n / (n + shrink_strength)
        out[str(row["state_fips"])] = weight * raw + (1.0 - weight) * national_intensity
    return out


class CbpIntensity:
    """§10.4. q = shrunk CBP March intensity x QCEW establishment exposure."""

    estimator_id = "cbp_intensity"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        reference_year = int(anchor.reference_month.split("-")[0])
        available = set(context.cbp["reference_year"].unique().to_list())
        if reference_year not in available:
            return Decline(
                reason=(
                    f"CBP publishes no reference year {reference_year}; §10.4's estimator is a "
                    "year-specific March intensity, and carrying an earlier year forward would be "
                    "an assumption this baseline does not make"
                )
            )
        intensity = march_intensity(context.cbp, reference_year=reference_year)
        exposure = establishment_weights(context, anchor)
        own = {
            cell: intensity[cell] * exposure[cell]
            for cell in anchor.missing_cells
            if cell in intensity and cell in exposure
        }
        return compose(
            own, exposure, anchor, allowed=context.config.baselines.allow_declared_composite
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baselines_intensity.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/intensity.py tests/unit/test_baselines_intensity.py
git commit -m "feat(baselines): add the CBP/QCEW intensity baseline with declared coverage holes"
```

---

### Task 14: §10.5 harvest-proportional — the required decline

**Files:**
- Create: `src/logging_employment/baselines/harvest.py`
- Test: `tests/unit/test_baselines_harvest.py`

**Interfaces:**
- Consumes: `NoHarvestFactorError`, `Decline`.
- Produces: `HarvestProportional` (`estimator_id = "harvest_proportional"`).

**The decline is required by the roadmap, not by §10.5.** §10.5 is two sentences with no
precondition: "Allocate residual using harvest-origin volume or the estimated latent harvest
factor. It is a benchmark, not a preferred standalone estimator." The obligation comes from the
roadmap's Stage 3 exit criteria: *"the harvest-proportional baseline declines to run without a
harvest factor rather than fabricating one."* **Cite the roadmap, not the spec.**

No harvest input exists: Appendix A ships `tpo.enabled: false` and `fia.enabled: false`, and
`config.yaml` carries no `tpo` or `fia` source entry at all. Stage 7 is the stage that supplies one.

**§17.4 row 4 requires "run every baseline on a small frozen fixture". A clean decline counts as a
pass.** State that in the test, or the integration test in Task 19 will read the decline as a
failure.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_baselines_harvest.py`:

```python
"""§10.5 declines on this window. The decline is the deliverable, not a gap."""

from __future__ import annotations

import polars as pl

from logging_employment.baselines.harvest import HarvestProportional
from logging_employment.baselines.interfaces import Decline, EstimatorContext
from logging_employment.reconcile.anchor import Anchor, observed_partition


def test_the_harvest_baseline_declines_rather_than_fabricating_a_factor(
    make_monthly, appendix_a_config
) -> None:
    """Roadmap Stage 3 exit criterion, verbatim: "declines to run without a harvest factor
    rather than fabricating one". §10.5 itself states no precondition, so the obligation is the
    roadmap's, and this test is what discharges it.
    """
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 5},
    )
    context = EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                               partitions=observed_partition(monthly), config=appendix_a_config)
    anchor = Anchor("2024-03", 40.0, ("01",), "declared_national_total")
    out = HarvestProportional().weights(context, anchor)
    assert isinstance(out, Decline)
    assert "harvest" in out.reason.lower()
    assert "Stage 7" in out.reason


def test_the_decline_is_a_pass_for_the_run_every_baseline_criterion(
    make_monthly, appendix_a_config
) -> None:
    """§17.4 row 4 says run every baseline on a frozen fixture. A clean decline satisfies it.

    Without this the Task 19 integration test would read the decline as a failed baseline and
    either be weakened or start excluding §10.5 -- both of which lose the criterion.
    """
    monthly = make_monthly(
        {"state_fips": "01", "area_fips": "01000", "observation_status": "suppressed",
         "employment_value": None, "qtrly_establishments": 5},
    )
    context = EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                               partitions=observed_partition(monthly), config=appendix_a_config)
    out = HarvestProportional().weights(
        context, Anchor("2024-03", 40.0, ("01",), "declared_national_total")
    )
    assert isinstance(out, Decline)
    assert out.reason  # a decline always carries a reason a reader can act on
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/unit/test_baselines_harvest.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `harvest.py`**

```python
"""§10.5 harvest-proportional allocation, which declines on this window.

§10.5 is two sentences and states no precondition: "Allocate residual using harvest-origin volume
or the estimated latent harvest factor. It is a benchmark, not a preferred standalone estimator."
The obligation to decline rather than improvise comes from the roadmap's Stage 3 exit criteria --
"the harvest-proportional baseline declines to run without a harvest factor rather than fabricating
one" -- so cite the roadmap for the refusal, not the spec.

THERE IS NO HARVEST INPUT. Appendix A ships `tpo.enabled: false` and `fia.enabled: false`, and
`config.yaml` carries no tpo or fia source entry at all. §11.4's latent harvest factor is Stage 7's
deliverable. The tempting substitutes -- timber acreage, a national harvest series spread by state
area, a proxy built from establishment counts -- would each be a different estimator wearing this
one's name, and would be scored by Stage 4 as though §10.5 had run.

This estimator becomes live when Stage 7 supplies `features/harvest_factor.py`. Until then the
decline is the deliverable, and §17.4 row 4's "run every baseline on a small frozen fixture" is
satisfied by a clean decline.
"""

from __future__ import annotations

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext


class HarvestProportional:
    """§10.5. Declines until Stage 7 supplies a harvest factor."""

    estimator_id = "harvest_proportional"

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        return Decline(
            reason=(
                "no harvest-origin volume and no latent harvest factor are available: Appendix A "
                "ships tpo.enabled=false and fia.enabled=false and the config declares neither "
                "source. Stage 7 supplies the harvest factor; until then §10.5 declines rather "
                "than allocating on a substitute proxy that would be scored as if it were this "
                "baseline"
            )
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baselines_harvest.py -v`
Expected: PASS, both tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/harvest.py tests/unit/test_baselines_harvest.py
git commit -m "feat(baselines): decline harvest-proportional allocation rather than fabricating a factor"
```

---

### Task 15: §10.6 constrained regression baseline

**Files:**
- Create: `src/logging_employment/baselines/regression.py`
- Test: `tests/unit/test_baselines_regression.py`

**Interfaces:**
- Consumes: `establishment_weights`, `compose`, `BaselinesConfig.regression_ridge_penalty`; numpy.
- Produces: `ConstrainedRegression` (`estimator_id = "constrained_regression"`), and
  `def fit_log_intensity(rows: pl.DataFrame, *, ridge: float) -> tuple[np.ndarray, list[str]]`.

§10.6: "Fit a regularized model for log employment intensity using only **training-visible** cells,
produce positive predictions, then reconcile each prediction vector to the feasible set."

**"Training-visible" is undefined in the spec** — it appears twice, both in §10. Stage 3 must define
the interface Stage 4's pseudo-suppression mask later drives, or the definition becomes circular:
Stage 4 masks cells, and the estimator must be told which cells it may learn from rather than
inferring it from `observation_status`. **The `EstimatorContext.partitions` argument is that
interface** — training-visible means "in `partition.disclosed` for its month", exactly the
mask-parameterised rule the anchor already follows.

**Dependency decision: use `scipy`/`numpy`, not scikit-learn.** scipy is already a declared
dependency; sklearn is not, and a ridge regression is a closed-form solve. Do not add sklearn.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baselines_regression.py`:

```python
"""§10.6 constrained regression: positive predictions from training-visible cells only."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from logging_employment.baselines.interfaces import EstimatorContext
from logging_employment.baselines.regression import ConstrainedRegression, fit_log_intensity
from logging_employment.reconcile.anchor import Anchor, Partition, observed_partition


def _panel(make_monthly) -> pl.DataFrame:
    rows = [{"area_type": "national", "area_fips": "US000", "state_fips": None,
             "aggregation_level": "18", "reference_month": "2024-03",
             "employment_value": 300, "qtrly_establishments": 30}]
    for fips, emp, est in [("01", 40, 4), ("02", 60, 6), ("04", 80, 8), ("05", 100, 10)]:
        rows.append({"state_fips": fips, "area_fips": f"{fips}000", "reference_month": "2024-03",
                     "employment_value": emp, "qtrly_establishments": est,
                     "observation_status": "observed"})
    rows.append({"state_fips": "06", "area_fips": "06000", "reference_month": "2024-03",
                 "employment_value": None, "qtrly_establishments": 5,
                 "observation_status": "suppressed"})
    return make_monthly(*rows)


def test_predictions_are_strictly_positive(make_monthly, appendix_a_config) -> None:
    """§10.6: "produce positive predictions". A log-intensity model exponentiates, so this holds
    by construction -- and the test pins the construction, not the arithmetic."""
    monthly = _panel(make_monthly)
    context = EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                               partitions=observed_partition(monthly), config=appendix_a_config)
    anchor = Anchor("2024-03", 20.0, ("06",), "declared_national_total")
    out = ConstrainedRegression().weights(context, anchor)
    assert out.values["06"] > 0.0


def test_the_fit_uses_only_training_visible_cells(make_monthly, appendix_a_config) -> None:
    """"Training-visible" is undefined in the spec; the partition argument is its definition.

    A cell in `partition.missing` must not enter the fit even when the table shows a value -- that
    is exactly the situation Stage 4's mask creates, and §13.4's leakage control depends on it.
    """
    monthly = _panel(make_monthly)
    states = monthly.filter(pl.col("area_type") == "state")
    # Mask 05 as if pseudo-suppressed: its value is present in the table but must not be learned.
    masked = {"2024-03": Partition(
        disclosed=states.filter(pl.col("state_fips").is_in(["01", "02", "04"])),
        missing=states.filter(pl.col("state_fips").is_in(["05", "06"])),
    )}
    context = EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                               partitions=masked, config=appendix_a_config)
    training = ConstrainedRegression().training_rows(context, "2024-03")
    assert sorted(training["state_fips"].to_list()) == ["01", "02", "04"]


def test_the_ridge_penalty_shrinks_the_slope(make_monthly) -> None:
    rows = pl.DataFrame({
        "state_fips": ["01", "02", "04", "05"],
        "log_exposure": [0.0, 1.0, 2.0, 3.0],
        "log_intensity": [0.0, 1.0, 2.0, 3.0],
    })
    weak, _ = fit_log_intensity(rows, ridge=0.001)
    strong, _ = fit_log_intensity(rows, ridge=100.0)
    assert abs(strong[1]) < abs(weak[1])


def test_a_fit_with_too_few_training_rows_falls_back(make_monthly, appendix_a_config) -> None:
    """One observed cell cannot identify a slope; fall back rather than fitting noise."""
    monthly = make_monthly(
        {"area_type": "national", "area_fips": "US000", "state_fips": None,
         "aggregation_level": "18", "reference_month": "2024-03",
         "employment_value": 100, "qtrly_establishments": 10},
        {"state_fips": "01", "area_fips": "01000", "reference_month": "2024-03",
         "employment_value": 40, "qtrly_establishments": 4, "observation_status": "observed"},
        {"state_fips": "02", "area_fips": "02000", "reference_month": "2024-03",
         "employment_value": None, "qtrly_establishments": 6,
         "observation_status": "suppressed"},
    )
    context = EstimatorContext(monthly=monthly, cbp=pl.DataFrame(),
                               partitions=observed_partition(monthly), config=appendix_a_config)
    anchor = Anchor("2024-03", 60.0, ("02",), "declared_national_total")
    out = ConstrainedRegression().weights(context, anchor)
    assert out.basis["02"] == "establishment_fallback"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baselines_regression.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `regression.py`**

```python
"""§10.6: a regularized model for log employment intensity, fit on training-visible cells only.

"Fit a regularized model for log employment intensity using only training-visible cells, produce
positive predictions, then reconcile each prediction vector to the feasible set."

"TRAINING-VISIBLE" IS UNDEFINED IN THE SPEC -- it appears twice, both inside §10 -- so Stage 3
defines it, because Stage 4 drives it. A cell is training-visible when it is in its month's
`partition.disclosed`. That is the same mask-parameterised rule the anchor follows, and it is what
keeps §13.4's leakage control enforceable: under a pseudo-suppression mask the masked cell still
carries its published value in `qcew_monthly`, so an estimator that read the table instead of the
partition would train on the answer. Reading the partition makes leakage structurally impossible
rather than a thing Stage 4 must remember to check.

MODEL FORM. log(E/A) regressed on log(A) with a ridge penalty, fit per month on that month's
training-visible cells, then exponentiated and multiplied by exposure -- so predictions are
positive by construction rather than by clipping. The ridge penalty comes from
`config.baselines.regression_ridge_penalty`.

DEPENDENCY DECISION. numpy and scipy are already declared; scikit-learn is not and is not added. A
ridge fit is a closed-form solve and does not justify a new dependency.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext, compose
from .simple import establishment_weights

MINIMUM_TRAINING_ROWS = 3


def fit_log_intensity(
    rows: pl.DataFrame, *, ridge: float
) -> tuple[np.ndarray, list[str]]:
    """Ridge-fit `log_intensity ~ 1 + log_exposure`. Returns the coefficients and their names."""
    x = np.column_stack([np.ones(rows.height), rows["log_exposure"].to_numpy()])
    y = rows["log_intensity"].to_numpy()
    penalty = ridge * np.eye(x.shape[1])
    penalty[0, 0] = 0.0  # never shrink the intercept toward zero; the level is not the target
    beta = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    return beta, ["intercept", "log_exposure"]


class ConstrainedRegression:
    """§10.6. q = exp(predicted log intensity) x exposure, reconciled through the shared layer."""

    estimator_id = "constrained_regression"

    def training_rows(self, context: EstimatorContext, reference_month: str) -> pl.DataFrame:
        """The training-visible cells for a month: disclosed by the partition, with positive inputs."""
        partition = context.partitions[reference_month]
        return (
            partition.disclosed.filter(
                pl.col("employment_value").is_not_null()
                & (pl.col("employment_value") > 0)
                & (pl.col("qtrly_establishments") > 0)
            )
            .with_columns(
                pl.col("qtrly_establishments").log().alias("log_exposure"),
                (pl.col("employment_value") / pl.col("qtrly_establishments"))
                .log()
                .alias("log_intensity"),
            )
            .select(["state_fips", "log_exposure", "log_intensity"])
        )

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        training = self.training_rows(context, anchor.reference_month)
        exposure = establishment_weights(context, anchor)
        if training.height < MINIMUM_TRAINING_ROWS:
            # Not a decline: the declared fallback covers it, and a two-point fit would be noise
            # dressed as a model.
            return compose(
                {}, exposure, anchor, allowed=context.config.baselines.allow_declared_composite
            )
        beta, _ = fit_log_intensity(
            training, ridge=context.config.baselines.regression_ridge_penalty
        )
        own: dict[str, float] = {}
        for cell, exposure_value in exposure.items():
            log_exposure = float(np.log(exposure_value))
            predicted_intensity = float(np.exp(beta[0] + beta[1] * log_exposure))
            own[cell] = predicted_intensity * exposure_value
        return compose(
            own, exposure, anchor, allowed=context.config.baselines.allow_declared_composite
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baselines_regression.py -v`
Expected: PASS, all four tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/regression.py tests/unit/test_baselines_regression.py
git commit -m "feat(baselines): add the constrained regression baseline over training-visible cells"
```

---

### Task 16: §10.8's fallback hierarchy, the runner, and `baseline_results/`

**Files:**
- Create: `src/logging_employment/baselines/runner.py`
- Modify: `src/logging_employment/baselines/__init__.py`
- Test: `tests/unit/test_baseline_runner.py`

**Interfaces:**
- Consumes: every estimator; `closure_audit`, `assert_universe_closes`, `national_residual`,
  `allocate`, `integerize`; `BASELINE_RESULT_SCHEMA`.
- Produces:
  - `REGISTRY: tuple[Estimator, ...]` — every §10 estimator, in spec order
  - `FALLBACK_ORDER: tuple[str, ...]` — §10.8's four rungs, in the spec's order
  - `def run_baselines(data: HarmonizedData, config: Config) -> tuple[pl.DataFrame, pl.DataFrame]`
    returning `(baseline_results, anchor_audit)`
  - `def preferred_estimator(results: pl.DataFrame) -> str` — §10.8's ordering applied to what
    actually ran

§10.8's hierarchy, verbatim and ordered (spec:996-1001):

1. reconciled CBP/QCEW employee-per-establishment with robust historical adjustment;
2. reconciled constrained regression;
3. reconciled historical shares; then
4. establishment-count proportional allocation.

**§10.1 is deliberately absent from the hierarchy** — the spec calls it a sanity check only. Do not
add it as a fifth rung.

The runner is where the anchor gate runs once for the whole window (a `UniverseClosureError` is a
**whole-run halt**, per §18.3, not a per-month decline), and where every decline becomes a visible
row rather than an absent one.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_baseline_runner.py`:

```python
"""The runner: one gate for the window, one row per (estimator, cell), declines included."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.runner import (
    FALLBACK_ORDER,
    REGISTRY,
    preferred_estimator,
    run_baselines,
)
from logging_employment.contracts import BASELINE_RESULT_SCHEMA, HarmonizedData
from logging_employment.errors import UniverseClosureError


def test_the_fallback_order_is_the_specs_four_rungs_in_its_order() -> None:
    """§10.8 lists four, and §10.1 is deliberately not among them."""
    assert FALLBACK_ORDER == (
        "cbp_intensity",
        "constrained_regression",
        "share_last_observed",
        "establishment_proportional",
    )
    assert "equal_residual" not in FALLBACK_ORDER


def test_the_registry_carries_every_section_10_estimator() -> None:
    ids = {e.estimator_id for e in REGISTRY}
    assert "equal_residual" in ids
    assert "establishment_proportional" in ids
    assert "cbp_intensity" in ids
    assert "harvest_proportional" in ids
    assert "constrained_regression" in ids
    assert len([i for i in ids if i.startswith("share_")]) == 5


def test_a_broken_universe_halts_the_whole_run_not_one_month(
    harmonized_toy, appendix_a_config
) -> None:
    """§18.3: "The pipeline MUST fail rather than guess when ... source universes cannot be
    reconciled." A gap means every month's residual is suspect, not just the failing month's."""
    broken = harmonized_toy.qcew_monthly.with_columns(
        pl.when(pl.col("area_type") == "national")
        .then(pl.col("qtrly_establishments") + 7)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    data = HarmonizedData(broken, harmonized_toy.qcew_national_size,
                          harmonized_toy.cbp_state_size, harmonized_toy.bridge)
    with pytest.raises(UniverseClosureError):
        run_baselines(data, appendix_a_config)


def test_a_decline_is_a_row_not_an_absence(harmonized_toy, appendix_a_config) -> None:
    """A silent NaN or a dropped row is indistinguishable from a bug."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    harvest = results.filter(pl.col("estimator_id") == "harvest_proportional")
    assert harvest.height > 0
    assert harvest["reconciliation_status"].unique().to_list() == ["declined"]
    assert harvest["decline_reason"].null_count() == 0
    assert harvest["estimate"].null_count() == harvest.height


def test_every_running_estimator_sums_to_the_residual(harmonized_toy, appendix_a_config) -> None:
    results, audit = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    totals = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual")
    )
    for row in totals.iter_rows(named=True):
        assert row["total"] == pytest.approx(row["residual"], abs=1e-6)


def test_the_results_match_the_declared_schema(harmonized_toy, appendix_a_config) -> None:
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert list(results.columns) == list(BASELINE_RESULT_SCHEMA)


def test_the_preferred_estimator_follows_the_fallback_order(
    harmonized_toy, appendix_a_config
) -> None:
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    assert preferred_estimator(results) in FALLBACK_ORDER


def test_the_integer_estimates_balance_to_the_allocations_own_total(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.6 step 5: recheck every hard margin after rounding.

    The total must come from the allocation, not from `round(residual)`: `integerize` distributes
    exactly `total - sum(floors)` units, so a total that disagrees with the values by one unit
    leaves a unit unplaced. The two agree on D1 and diverge under a fractional Stage 4 residual.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    per_month = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("continuous"),
        pl.col("estimate_integer").sum().alias("integer"),
    )
    for row in per_month.iter_rows(named=True):
        assert row["integer"] == round(row["continuous"])


def test_every_row_carries_the_constraint_set_hash_it_was_produced_beside(
    harmonized_toy, appendix_a_config
) -> None:
    """A declared-but-always-null provenance column is worse than no column.

    §18.1's reproducibility check needs these estimates tied to the Stage 2 system they sit
    beside, so the hash is threaded in rather than left for a reader to infer from the directory.
    """
    results, _ = run_baselines(harmonized_toy, appendix_a_config, constraint_set_hash="abc123")
    assert results["constraint_set_hash"].unique().to_list() == ["abc123"]


def test_weight_basis_counts_are_recoverable_from_the_results(
    harmonized_toy, appendix_a_config
) -> None:
    """Stage 4 must be able to tell a composite's score from a pure estimator's."""
    results, _ = run_baselines(harmonized_toy, appendix_a_config)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert set(ran["weight_basis"].unique().to_list()) <= {
        "own_estimator", "establishment_fallback"
    }
```

Add a `harmonized_toy` fixture to `tests/unit/conftest.py` building a two-month, four-state
`HarmonizedData` whose establishment universes close exactly, with at least one suppressed cell per
month, one state with no observed history, and one state absent from CBP.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_baseline_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `runner.py`**

```python
"""Run every §10 baseline over the window, and rank what ran by §10.8's hierarchy.

THE GATE RUNS ONCE, FOR THE WINDOW. §18.3 requires the pipeline to fail rather than guess when
source universes cannot be reconciled. A nonzero establishment gap in any month means the published
national row contains a component the state table does not, which makes every month's residual
suspect -- so this halts the run rather than declining one month and shipping the other 95.

EVERY DECLINE IS A ROW. A baseline that cannot run for a month writes a row with a null estimate
and a populated `decline_reason`, never no row at all: an absent row is indistinguishable from a
bug, and §17.4 row 4's "run every baseline on a small frozen fixture" is satisfied by a clean
decline only if the decline is visible in the output.

§10.8's HIERARCHY HAS FOUR RUNGS AND §10.1 IS NOT ONE OF THEM. The spec calls equal allocation a
sanity check and leaves it out of the ordering on purpose -- it ignores the establishment counts
that QCEW publishes even for suppressed cells. It still runs and is still scored; it is just never
preferred.
"""

from __future__ import annotations

import polars as pl

from ..config import Config
from ..contracts import BASELINE_RESULT_SCHEMA, HarmonizedData
from ..reconcile.allocate import allocate
from ..reconcile.anchor import (
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)
from ..reconcile.integerize import integerize
from .harvest import HarvestProportional
from .historical import (
    BreakAdjustedShare,
    ExponentiallyWeightedShare,
    LastObservedShare,
    RollingMedianShare,
    SameMonthPreviousYearShare,
)
from .intensity import CbpIntensity
from .interfaces import Decline, Estimator, EstimatorContext
from .regression import ConstrainedRegression
from .simple import EqualAllocation, EstablishmentProportional

REGISTRY: tuple[Estimator, ...] = (
    EqualAllocation(),
    EstablishmentProportional(),
    LastObservedShare(),
    SameMonthPreviousYearShare(),
    RollingMedianShare(),
    ExponentiallyWeightedShare(),
    BreakAdjustedShare(),
    CbpIntensity(),
    HarvestProportional(),
    ConstrainedRegression(),
)

# §10.8's four rungs, in the spec's order. `share_last_observed` stands for rung 3's "reconciled
# historical shares"; the other four variants are scored but the hierarchy names one representative.
FALLBACK_ORDER: tuple[str, ...] = (
    "cbp_intensity",
    "constrained_regression",
    "share_last_observed",
    "establishment_proportional",
)


def run_baselines(
    data: HarmonizedData, config: Config, *, constraint_set_hash: str | None = None
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Every estimator, every month. Returns `(baseline_results, anchor_audit)`.

    `constraint_set_hash` is threaded in rather than recomputed: it identifies the Stage 2 system
    these estimates sit beside, and §18.1's reproducibility check needs the two to agree. The CLI
    reads it from `schema_manifest.json`, which is the same file `solve-bounds` gates on. It stays
    optional so a unit test can build a toy `HarmonizedData` without a Stage 2 run.
    """
    partitions = observed_partition(data.qcew_monthly)
    audit = closure_audit(data.qcew_monthly, partitions)
    assert_universe_closes(audit)

    context = EstimatorContext(
        monthly=data.qcew_monthly, cbp=data.cbp_state_size, partitions=partitions, config=config
    )
    rows: list[dict[str, object]] = []
    for month in sorted(partitions):
        anchor = national_residual(data.qcew_monthly, partitions[month], reference_month=month)
        if not anchor.missing_cells:
            continue
        for estimator in REGISTRY:
            outcome = estimator.weights(context, anchor)
            if isinstance(outcome, Decline):
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id, anchor, outcome.reason, constraint_set_hash
                    )
                )
                continue
            allocated = allocate(anchor, outcome)
            # Integerize against the allocation's OWN total, not `round(anchor.residual)`. The two
            # agree on D1, where every residual is a whole number, but they diverge the moment a
            # Stage 4 mask produces a fractional residual -- and `integerize` distributes exactly
            # `total - sum(floors)` units, so a total that disagrees with the values by one unit
            # leaves a unit unplaced or over-places one. Deriving it from the values keeps the
            # margin the integers are balanced against the same margin they came from.
            integer_total = int(round(sum(allocated.values())))
            integers = (
                integerize(allocated, total=integer_total)
                if config.reconciliation.integerize_release
                else dict.fromkeys(allocated, None)
            )
            if config.reconciliation.integerize_release:
                assert sum(integers.values()) == integer_total  # §12.6 step 5: recheck the margin
            for cell in anchor.missing_cells:
                rows.append(
                    {
                        "estimator_id": estimator.estimator_id,
                        "cell_id": f"state_total|{cell}|{month}",
                        "state_fips": cell,
                        "reference_month": month,
                        "raw_weight": float(outcome.values[cell]),
                        "estimate": float(allocated[cell]),
                        "estimate_integer": integers[cell],
                        "weight_basis": outcome.basis[cell],
                        "anchor_basis": anchor.anchor_basis,
                        "reconciliation_status": "anchored_and_reconciled",
                        "decline_reason": None,
                        "residual": anchor.residual,
                        "missing_set_size": len(anchor.missing_cells),
                        "constraint_set_hash": constraint_set_hash,
                    }
                )
    return pl.DataFrame(rows, schema=BASELINE_RESULT_SCHEMA), audit


def _decline_rows(
    estimator_id: str, anchor, reason: str, constraint_set_hash: str | None
) -> list[dict[str, object]]:
    """One visible row per cell a declining estimator could not weight."""
    return [
        {
            "estimator_id": estimator_id,
            "cell_id": f"state_total|{cell}|{anchor.reference_month}",
            "state_fips": cell,
            "reference_month": anchor.reference_month,
            "raw_weight": None,
            "estimate": None,
            "estimate_integer": None,
            "weight_basis": "none",
            "anchor_basis": anchor.anchor_basis,
            "reconciliation_status": "declined",
            "decline_reason": reason,
            "residual": anchor.residual,
            "missing_set_size": len(anchor.missing_cells),
            "constraint_set_hash": constraint_set_hash,
        }
        for cell in anchor.missing_cells
    ]


def preferred_estimator(results: pl.DataFrame) -> str:
    """§10.8's ordering, applied to whichever estimators actually produced estimates.

    Raises when no rung ran. Unreachable on D1 -- §10.2's inputs are complete on every suppressed
    cell, so rung 4 always produces estimates -- but reachable from a Stage 4 mask that empties
    every month's missing set, which is why it raises rather than returning a sentinel.
    """
    ran = set(
        results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")[
            "estimator_id"
        ].unique().to_list()
    )
    for estimator_id in FALLBACK_ORDER:
        if estimator_id in ran:
            return estimator_id
    raise ValueError("no estimator in §10.8's fallback hierarchy produced any estimate")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_baseline_runner.py -v`
Expected: PASS, all ten tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/baselines/ tests/unit/
git commit -m "feat(baselines): run every estimator under one gate and rank by the fallback hierarchy"
```

---

### Task 17: The `run-baselines` and `reconcile` CLI commands

**Files:**
- Modify: `src/logging_employment/cli.py`
- Test: `tests/integration/test_baseline_cli.py`

**Interfaces:**
- Consumes: `run_baselines`, `preferred_estimator`, `write_parquet_deterministic`, `run_dir`,
  `run_id`, `_input_digests`.
- Produces: two Typer commands writing `runs/<run_id>/baseline_results/` and a sibling
  `baseline_manifest.json`.

**Write a SIBLING manifest.** Never edit `schema_manifest.json`: `solve-bounds` reads its bytes as
a precondition gate and an idempotence test pins them. `run-baselines` writes
`baseline_manifest.json` alongside it.

Follow the shipped command template exactly — imports inside the function body to keep CLI start-up
cheap, `typer.Option(..., "--config", exists=True, dir_okay=False)`, and `typer.echo` summary lines.

§16.1 requires both commands to be idempotent for identical inputs.

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/test_baseline_cli.py`:

```python
"""The two Stage 3 commands: what they write, and that a second run writes the same bytes."""

from __future__ import annotations

import json

import polars as pl
from typer.testing import CliRunner

from logging_employment.cli import app

runner = CliRunner()


def test_run_baselines_writes_results_and_a_sibling_manifest(staged_repo) -> None:
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    out = staged_repo.run_dir / "baseline_results"
    assert (out / "baseline_results.parquet").exists()
    assert (out / "anchor_audit.parquet").exists()
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    assert "preferred_estimator" in manifest
    assert "output_hashes" in manifest
    assert "weight_basis_counts" in manifest


def test_run_baselines_does_not_touch_the_stage_2_manifest(staged_repo) -> None:
    """`solve-bounds` reads schema_manifest.json's bytes as a precondition gate."""
    before = (staged_repo.run_dir / "schema_manifest.json").read_bytes()
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert (staged_repo.run_dir / "schema_manifest.json").read_bytes() == before


def test_a_second_run_is_byte_identical(staged_repo) -> None:
    """§16.1: every command MUST be idempotent for the same inputs."""
    path = staged_repo.run_dir / "baseline_results" / "baseline_results.parquet"
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    first = path.read_bytes()
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert path.read_bytes() == first


def test_the_manifest_records_the_composite_split(staged_repo) -> None:
    """Stage 4 must not report a composite's score as a pure estimator's."""
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    counts = manifest["weight_basis_counts"]
    assert set(counts) >= {"own_estimator", "establishment_fallback"}


def test_declines_are_counted_in_the_manifest(staged_repo) -> None:
    runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    manifest = json.loads((staged_repo.run_dir / "baseline_manifest.json").read_text())
    assert "harvest_proportional" in manifest["declines"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/integration/test_baseline_cli.py -v`
Expected: FAIL — `run-baselines` is not a registered command.

- [ ] **Step 3: Add the two commands**

Append to `src/logging_employment/cli.py`:

```python
@app.command("run-baselines")
def run_baselines_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Run every §10 transparent baseline and persist the results under this run's directory."""
    import json

    import polars as pl

    from .baselines.runner import preferred_estimator, run_baselines
    from .build import write_parquet_deterministic
    from .contracts import (
        ANCHOR_AUDIT_SCHEMA,
        BASELINE_RESULT_SCHEMA,
        HarmonizedData,
        schema_fingerprint,
    )
    from .runs import run_dir, run_id

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    manifest_path = run / "schema_manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(
            f"{manifest_path} is missing: no `build-constraints` run matches the harmonized "
            "inputs currently in the staged directory. Run `build-constraints` first"
        )
    results, audit = run_baselines(
        data, cfg, constraint_set_hash=json.loads(manifest_path.read_text())["constraint_set_hash"]
    )

    out = run / "baseline_results"
    out.mkdir(parents=True, exist_ok=True)
    hashes = {
        "baseline_results": write_parquet_deterministic(
            results, out / "baseline_results.parquet"
        ),
        "anchor_audit": write_parquet_deterministic(audit, out / "anchor_audit.parquet"),
    }

    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    basis_counts = {
        row["weight_basis"]: row["len"]
        for row in ran.group_by("weight_basis").len().iter_rows(named=True)
    }
    declines = {
        row["estimator_id"]: row["len"]
        for row in results.filter(pl.col("reconciliation_status") == "declined")
        .group_by("estimator_id")
        .len()
        .iter_rows(named=True)
    }
    # A SIBLING manifest. `schema_manifest.json` is `solve-bounds`'s precondition gate and an
    # idempotence test pins its bytes, so nothing here may write to it.
    (run / "baseline_manifest.json").write_text(
        json.dumps(
            {
                "preferred_estimator": preferred_estimator(results),
                "output_hashes": hashes,
                "schema_fingerprints": {
                    "baseline_results": schema_fingerprint(BASELINE_RESULT_SCHEMA),
                    "anchor_audit": schema_fingerprint(ANCHOR_AUDIT_SCHEMA),
                },
                "weight_basis_counts": basis_counts,
                "declines": declines,
                "anchor": {
                    "basis": "declared_national_total",
                    "months_gated": audit.height,
                    "months_anchored": int(audit["anchored"].sum()),
                    "establishment_gap_max": int(audit["establishment_gap"].abs().max()),
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    typer.echo(f"preferred {preferred_estimator(results)}")
    for basis, count in sorted(basis_counts.items()):
        typer.echo(f"{basis} {count}")
    for estimator_id, count in sorted(declines.items()):
        typer.echo(f"declined {estimator_id} {count}")


@app.command("reconcile")
def reconcile_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Re-reconcile the persisted baseline estimates and report any drift.

    Stage 3 reconciles inside `run-baselines`, so this command exists to verify rather than to
    produce: it reloads the results, re-runs the allocation, and reports the largest difference.
    Stage 5 makes it load-bearing, when posterior draws reconcile separately from the estimators
    that seeded them.
    """
    import polars as pl

    from .contracts import HarmonizedData
    from .runs import run_dir, run_id

    cfg = load_config(config)
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    path = run / "baseline_results" / "baseline_results.parquet"
    if not path.exists():
        raise typer.BadParameter(
            f"{path} is missing: no `run-baselines` run matches the harmonized inputs currently "
            "in the staged directory. Run `run-baselines` first"
        )
    results = pl.read_parquet(path)
    HarmonizedData.load(Path(cfg.storage.staged_uri))
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    drift = (
        ran.group_by(["estimator_id", "reference_month"])
        .agg(pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual"))
        .with_columns((pl.col("total") - pl.col("residual")).abs().alias("drift"))
    )
    worst = float(drift["drift"].max()) if drift.height else 0.0
    typer.echo(f"checked {drift.height} (estimator, month) pairs")
    typer.echo(f"max residual drift {worst:.3e}")
    if worst > cfg.reconciliation.tolerance:
        raise typer.Exit(code=1)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_baseline_cli.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/cli.py tests/integration/test_baseline_cli.py
git commit -m "feat(cli): add run-baselines and reconcile with a sibling manifest"
```

---

### Task 18: §17.1 rows 8–10 and the seven §17.3 reconciliation property tests

**Files:**
- Create: `tests/unit/test_reconcile_properties.py`
- Test: itself

**Interfaces:**
- Consumes: the whole `reconcile` subpackage.
- Produces: no source. This task is the spec's testing obligation for Stage 3.

**§17.1's rows 8, 9 and 10** are, counting from row 1 "parse suppression-coded QCEW zero as null":

- row 8: **compute residual allocation exactly**
- row 9: **solve bounded proportional scaling**
- row 10: **balance integer rounding**

Rows 8–10 are already covered by Tasks 4, 5 and 8 respectively; this task adds one explicitly named
test per row so a reader can map the spec row to a test without inference.

**§17.3's seven properties**, verbatim (spec:1735-1743), each "for random feasible inputs":

1. no-bound scaling sums exactly to the residual;
2. bounded scaling respects every lower and upper bound;
3. bounded scaling fails on infeasible residuals;
4. generalized projection never increases constraint violation;
5. row and column reconciliation is exact;
6. integerization preserves required totals; and
7. ordering or solver tolerances do not create material instability.

**Properties 2 and 3 CANNOT be exercised on D1 data and MUST use synthetic finite-upper fixtures.**
On the real window `selected_upper` is null on 1,227 of 1,241 unknown cells, so `Σ U = +inf` and
the `Σ U < R_t` half of §12.3's predicate never fires. A property test drawing its bounds from
`deterministic_bounds` would pass without ever testing what it names. Generate finite uppers.

Property 5 is likewise synthetic by construction — `target_cell` carries no state-by-size cells
until Stage 6.

There is no Hypothesis dependency in this repo; property tests are hand-rolled with a seeded
`numpy.random.default_rng`. Follow that. Seeds are fixed constants so a failure is reproducible.

- [ ] **Step 1: Write the seven property tests plus the three named unit rows**

Create `tests/unit/test_reconcile_properties.py`:

```python
"""§17.3's seven reconciliation properties, and §17.1's rows 8-10 named explicitly.

Properties 2, 3 and 5 use SYNTHETIC fixtures by necessity, not by convenience. On the D1 window
`selected_upper` is null on 1,227 of 1,241 unknown cells, so a finite upper bound never binds and
`sum U < R_t` never fires; and `target_cell` carries no state-by-size cell at all until Stage 6.
Drawing these properties' inputs from the real tables would produce three tests that pass without
exercising the behaviour they are named for.

No Hypothesis: this repo hand-rolls property tests over a seeded generator, and the seeds are fixed
constants so any failure reproduces.
"""

from __future__ import annotations

import numpy as np
import pytest

from logging_employment.errors import InfeasibleResidualError
from logging_employment.reconcile.allocate import Weights, allocate
from logging_employment.reconcile.anchor import Anchor
from logging_employment.reconcile.integerize import integerize
from logging_employment.reconcile.matrix import reconcile_matrix
from logging_employment.reconcile.projection import constraint_violation, kl_project
from logging_employment.reconcile.scaling import Bounds, scale_into_bounds

SEED = 20260905
TOL = 1.0e-9
ITERS = 200
FLOOR = 1.0e-12
TRIALS = 200


def _cells(n: int) -> tuple[str, ...]:
    return tuple(f"{i:02d}" for i in range(1, n + 1))


def _weights(cells, rng) -> Weights:
    values = {c: float(rng.uniform(0.05, 20.0)) for c in cells}
    return Weights(values=values, basis=dict.fromkeys(values, "own_estimator"))


# --------------------------------------------------------------------------- §17.1 rows 8-10

def test_section_17_1_row_8_computes_residual_allocation_exactly() -> None:
    """§17.1 row 8: "compute residual allocation exactly"."""
    cells = _cells(4)
    anchor = Anchor("2024-03", 1000.0, cells, "declared_national_total")
    weights = Weights(values={c: float(i + 1) for i, c in enumerate(cells)},
                      basis=dict.fromkeys(cells, "own_estimator"))
    out = allocate(anchor, weights)
    assert sum(out.values()) == pytest.approx(1000.0, abs=1e-9)
    assert out[cells[0]] == pytest.approx(100.0)


def test_section_17_1_row_9_solves_bounded_proportional_scaling() -> None:
    """§17.1 row 9: "solve bounded proportional scaling"."""
    cells = _cells(3)
    anchor = Anchor("2024-03", 100.0, cells, "declared_national_total")
    bounds = Bounds(lower=dict.fromkeys(cells, 10.0),
                    upper={cells[0]: 20.0, cells[1]: None, cells[2]: None})
    out = scale_into_bounds(anchor, _weights(cells, np.random.default_rng(SEED)), bounds,
                            tolerance=TOL, max_iterations=ITERS)
    assert sum(out.values()) == pytest.approx(100.0, abs=1e-6)
    assert out[cells[0]] <= 20.0 + 1e-9


def test_section_17_1_row_10_balances_integer_rounding() -> None:
    """§17.1 row 10: "balance integer rounding"."""
    out = integerize({"01": 33.4, "02": 33.3, "04": 33.3}, total=100)
    assert sum(out.values()) == 100


# --------------------------------------------------------------------- §17.3 properties 1-7

def test_property_1_no_bound_scaling_sums_exactly_to_the_residual() -> None:
    rng = np.random.default_rng(SEED)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 16)))
        residual = float(rng.uniform(1.0, 5000.0))
        anchor = Anchor("2024-03", residual, cells, "declared_national_total")
        out = allocate(anchor, _weights(cells, rng))
        assert sum(out.values()) == pytest.approx(residual, rel=1e-12)


def test_property_2_bounded_scaling_respects_every_bound() -> None:
    """SYNTHETIC finite uppers: on D1 every state cell is unbounded above."""
    rng = np.random.default_rng(SEED + 1)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 10)))
        lower = {c: float(rng.uniform(0.0, 5.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 200.0)) for c in cells}
        residual = float(rng.uniform(sum(lower.values()), sum(upper.values())))
        anchor = Anchor("2024-03", residual, cells, "declared_national_total")
        out = scale_into_bounds(anchor, _weights(cells, rng),
                                Bounds(lower=lower, upper=upper),
                                tolerance=TOL, max_iterations=ITERS)
        assert sum(out.values()) == pytest.approx(residual, abs=1e-5)
        for cell in cells:
            assert out[cell] >= lower[cell] - 1e-7
            assert out[cell] <= upper[cell] + 1e-7


def test_property_3_bounded_scaling_fails_on_infeasible_residuals() -> None:
    """SYNTHETIC: the `sum U < R_t` half cannot fire on D1, where every upper is null."""
    rng = np.random.default_rng(SEED + 2)
    for _ in range(TRIALS // 2):
        cells = _cells(int(rng.integers(2, 8)))
        lower = {c: float(rng.uniform(1.0, 10.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 10.0)) for c in cells}
        anchor_low = Anchor("2024-03", sum(lower.values()) - 1.0, cells, "declared_national_total")
        anchor_high = Anchor("2024-03", sum(upper.values()) + 1.0, cells, "declared_national_total")
        bounds = Bounds(lower=lower, upper=upper)
        for anchor in (anchor_low, anchor_high):
            with pytest.raises(InfeasibleResidualError):
                scale_into_bounds(anchor, _weights(cells, rng), bounds,
                                  tolerance=TOL, max_iterations=ITERS)


def test_property_3b_a_residual_exactly_on_a_bound_sum_is_feasible() -> None:
    """§12.3's predicate is strict, so the boundary case must SUCCEED, not raise.

    Guarded separately from property 3 because the natural implementation of "fails on infeasible
    residuals" is `>=`, which silently makes this case fail too.
    """
    cells = _cells(3)
    lower = dict.fromkeys(cells, 10.0)
    anchor = Anchor("2024-03", 30.0, cells, "declared_national_total")
    out = scale_into_bounds(anchor, _weights(cells, np.random.default_rng(SEED)),
                            Bounds(lower=lower, upper=dict.fromkeys(cells, None)),
                            tolerance=TOL, max_iterations=ITERS)
    assert sum(out.values()) == pytest.approx(30.0, abs=1e-7)


def test_property_4_projection_never_increases_constraint_violation() -> None:
    rng = np.random.default_rng(SEED + 3)
    for _ in range(TRIALS // 2):
        n = int(rng.integers(3, 10))
        seed = rng.uniform(0.1, 50.0, size=n)
        margins = np.vstack([np.ones(n), (rng.random(n) < 0.5).astype(float)])
        targets = np.array([float(seed.sum() * rng.uniform(0.5, 2.0)),
                            float(seed.sum() * rng.uniform(0.1, 0.6))])
        before = constraint_violation(seed, margins, targets)
        out = kl_project(seed, margins, targets, lower=np.zeros(n), upper=np.full(n, np.inf),
                         floor=FLOOR, tolerance=TOL, max_iterations=1000)
        assert constraint_violation(out, margins, targets) <= before + 1e-6


def test_property_5_row_and_column_reconciliation_is_exact() -> None:
    """SYNTHETIC: `target_cell` carries no state-by-size cell until Stage 6."""
    rng = np.random.default_rng(SEED + 4)
    for _ in range(TRIALS // 4):
        rows, cols = int(rng.integers(2, 6)), int(rng.integers(2, 6))
        seed = rng.uniform(0.1, 10.0, size=(rows, cols))
        row_totals = rng.uniform(10.0, 100.0, size=rows)
        column_totals = rng.uniform(1.0, 10.0, size=cols)
        column_totals *= row_totals.sum() / column_totals.sum()  # make the margins consistent
        out = reconcile_matrix(seed, row_totals, column_totals,
                               tolerance=TOL, max_iterations=5000, floor=FLOOR)
        assert out.sum(axis=1) == pytest.approx(row_totals, rel=1e-4)
        assert out.sum(axis=0) == pytest.approx(column_totals, rel=1e-4)


def test_property_6_integerization_preserves_required_totals() -> None:
    rng = np.random.default_rng(SEED + 5)
    for _ in range(TRIALS):
        cells = _cells(int(rng.integers(2, 16)))
        total = int(rng.integers(0, 5000))
        raw = rng.uniform(0.0, 1.0, size=len(cells))
        values = {c: float(total * v / raw.sum()) for c, v in zip(cells, raw, strict=True)}
        out = integerize(values, total=total)
        assert sum(out.values()) == total


def test_property_7_cell_ordering_does_not_shift_results_materially() -> None:
    """Solver tolerance and cell ordering must not create material instability."""
    rng = np.random.default_rng(SEED + 6)
    for _ in range(TRIALS // 4):
        cells = _cells(int(rng.integers(3, 12)))
        residual = float(rng.uniform(10.0, 3000.0))
        weights = _weights(cells, rng)
        lower = dict.fromkeys(cells, 0.0)
        upper = {c: None for c in cells}
        forward = scale_into_bounds(
            Anchor("2024-03", residual, cells, "declared_national_total"), weights,
            Bounds(lower=lower, upper=upper), tolerance=TOL, max_iterations=ITERS
        )
        reversed_cells = tuple(reversed(cells))
        backward = scale_into_bounds(
            Anchor("2024-03", residual, reversed_cells, "declared_national_total"),
            Weights(values={c: weights.values[c] for c in reversed_cells},
                    basis={c: "own_estimator" for c in reversed_cells}),
            Bounds(lower=lower, upper=upper), tolerance=TOL, max_iterations=ITERS
        )
        for cell in cells:
            assert forward[cell] == pytest.approx(backward[cell], rel=1e-9, abs=1e-9)


def test_property_7b_integerization_is_order_independent() -> None:
    values = {"04": 3.5, "01": 3.5, "02": 3.0}
    forward = integerize(values, total=10)
    backward = integerize(dict(reversed(list(values.items()))), total=10)
    assert forward == backward
```

- [ ] **Step 2: Run the tests**

Run: `uv run pytest tests/unit/test_reconcile_properties.py -v`
Expected: PASS, 12 tests. If property 3b or 7 fails, the implementation has the strictness or
determinism defect those tests exist to catch — fix the implementation, not the test.

- [ ] **Step 3: Confirm the full unit suite still passes**

Run: `uv run pytest tests/unit -q`
Expected: PASS, with the Stage 1 and Stage 2 tests unchanged.

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_reconcile_properties.py
git commit -m "test(reconcile): add §17.3's seven properties and name §17.1 rows 8-10"
```

---

### Task 19: §17.4 row 4 integration, §17.6 golden fixtures, and the D1 acceptance run

**Files:**
- Create: `tests/integration/test_baseline_golden.py`
- Create: `tests/integration/test_d1_baselines.py`
- Create: `tests/fixtures/baselines/` (golden parquet)
- Test: itself

**Interfaces:**
- Consumes: everything.
- Produces: the evidence that discharges Stage 3's exit criteria.

**§17.4 row 4:** "run every baseline on a small frozen fixture". **A clean decline counts as a
pass** — §10.5 declines on this window by design, and 2024 declines for §10.4. If this test treats a
decline as a failure it will be weakened or start excluding those baselines, and the criterion is
lost either way.

**§17.6** requires golden coverage for baseline predictions and reconciliation. Follow the shipped
pattern in `tests/integration/test_constraint_golden.py`.

**The D1 acceptance run is marked `slow`** and excluded from the default run, like
`test_d1_acceptance.py`. It is the run that produces the numbers for the completion report.

- [ ] **Step 1: Write the integration and golden tests**

Create `tests/integration/test_baseline_golden.py`:

```python
"""§17.4 row 4 and §17.6: every baseline on a frozen fixture, pinned to golden output."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY, run_baselines

GOLDEN = "tests/fixtures/baselines/baseline_results_golden.parquet"


def test_every_baseline_runs_or_declines_cleanly_on_the_frozen_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    """§17.4 row 4. A DECLINE IS A PASS.

    §10.5 declines on this window by design and §10.4 declines for 2024. A test that treated a
    decline as a failure would be weakened or would start excluding those baselines, and either
    way the criterion "run every baseline" stops meaning anything.
    """
    results, _ = run_baselines(frozen_harmonized, appendix_a_config)
    seen = set(results["estimator_id"].unique().to_list())
    assert seen == {e.estimator_id for e in REGISTRY}
    for estimator_id in seen:
        rows = results.filter(pl.col("estimator_id") == estimator_id)
        statuses = set(rows["reconciliation_status"].unique().to_list())
        assert statuses <= {"anchored_and_reconciled", "declined"}
        if statuses == {"declined"}:
            assert rows["decline_reason"].null_count() == 0


def test_the_baseline_output_matches_its_golden_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    """§17.6 golden coverage for baseline predictions and reconciliation."""
    results, _ = run_baselines(frozen_harmonized, appendix_a_config)
    golden = pl.read_parquet(GOLDEN)
    assert results.equals(golden)


def test_the_anchor_audit_matches_its_golden_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    _, audit = run_baselines(frozen_harmonized, appendix_a_config)
    golden = pl.read_parquet("tests/fixtures/baselines/anchor_audit_golden.parquet")
    assert audit.equals(golden)
```

Create `tests/integration/test_d1_baselines.py`:

```python
"""The D1 acceptance run for Stage 3. Marked slow; excluded from the default suite."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import preferred_estimator, run_baselines
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData

pytestmark = pytest.mark.slow


def _run():
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    return run_baselines(data, cfg), cfg


def test_the_universe_gate_is_evaluated_for_every_window_month() -> None:
    """Structure, not the number: the anti-drift rule. A revision may move the gap; it must not
    be able to skip the gate."""
    (results, audit), _ = _run()
    assert audit.height == results["reference_month"].n_unique()
    assert audit["anchored"].null_count() == 0


def test_every_running_estimator_sums_to_its_months_residual() -> None:
    (results, _), cfg = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    totals = ran.group_by(["estimator_id", "reference_month"]).agg(
        pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual")
    )
    worst = (totals["total"] - totals["residual"]).abs().max()
    assert worst <= max(cfg.reconciliation.tolerance * 1e3, 1e-6)


def test_no_estimate_is_negative() -> None:
    (results, _), _ = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    assert ran["estimate"].min() >= 0.0


def test_a_preferred_transparent_baseline_is_named() -> None:
    """The roadmap's "named preferred transparent baseline slot that Stage 4 fills with numbers"."""
    (results, _), _ = _run()
    assert preferred_estimator(results)


def test_the_composite_split_is_recorded_rather_than_hidden() -> None:
    (results, _), _ = _run()
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    counts = ran.group_by(["estimator_id", "weight_basis"]).len()
    assert counts.height > 0
    assert "establishment_fallback" in ran["weight_basis"].unique().to_list()
```

- [ ] **Step 2: Run the integration tests to verify they fail**

Run: `uv run pytest tests/integration/test_baseline_golden.py -v`
Expected: FAIL — the golden fixtures do not exist yet.

- [ ] **Step 3: Generate the golden fixtures**

Build the frozen fixture and write the goldens once, then read them back:

```bash
uv run python -c "
from pathlib import Path
import polars as pl
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.baselines.runner import run_baselines
from logging_employment.build import write_parquet_deterministic

cfg = load_config(Path('config.yaml'))
data = HarmonizedData.load(Path(cfg.storage.staged_uri))
# Freeze a two-year slice so the fixture stays small and readable.
window = ['2022-%02d' % m for m in range(1, 13)]
sliced = HarmonizedData(
    data.qcew_monthly.filter(pl.col('reference_month').is_in(window)),
    data.qcew_national_size, data.cbp_state_size, data.bridge,
)
results, audit = run_baselines(sliced, cfg)
out = Path('tests/fixtures/baselines'); out.mkdir(parents=True, exist_ok=True)
write_parquet_deterministic(results, out / 'baseline_results_golden.parquet')
write_parquet_deterministic(audit, out / 'anchor_audit_golden.parquet')
print('results', results.height, 'audit', audit.height)
"
```

Wire `frozen_harmonized` in `tests/integration/conftest.py` to build the identical slice, so the
fixture the test runs and the fixture the golden was generated from cannot drift.

- [ ] **Step 4: Run the integration tests to verify they pass**

Run: `uv run pytest tests/integration/test_baseline_golden.py -v`
Expected: PASS, all three tests.

- [ ] **Step 5: Run the D1 acceptance run**

```bash
uv run logging-estimates run-baselines --config config.yaml
uv run logging-estimates reconcile --config config.yaml
uv run pytest tests/integration/test_d1_baselines.py -m slow -v
```

Record from the output, for the completion report: the preferred estimator, the own-weight versus
establishment-fallback counts per estimator, the decline counts per estimator, the number of months
gated and anchored, and the maximum residual drift.

**Do not hardcode any of those numbers into a test.** They are measurements dated to the run.

- [ ] **Step 6: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS. The Stage 1 and Stage 2 tests must be untouched — if `deterministic_bounds` or
`constraint_set_hash` changed, something in this stage wrote back into Stage 2's outputs, which the
Global Constraints forbid.

- [ ] **Step 7: Commit**

```bash
git add tests/integration/ tests/fixtures/baselines/
git commit -m "test(baselines): add the frozen-fixture, golden, and D1 acceptance runs"
```

---

## Self-review notes

**Spec coverage.** §10.1 → Task 11. §10.2 → Task 11. §10.3's five variants → Task 12. §10.4 →
Task 13. §10.5 → Task 14. §10.6 → Task 15. §10.7 → **not this stage**; empirical predictive
intervals come from rolling pseudo-suppression residuals, which is Stage 4's harness, and the
roadmap assigns REQ-013's interval half to Stage 4. §10.8 → Task 16. §12.1–12.7 → Tasks 4–9.
§16.1's two commands → Task 17. §16.2's `reconcile_draws` → Task 9. §17.1 rows 8–10 → Task 18.
§17.3's seven properties → Task 18. §17.4 row 4 → Task 19. §17.6 → Task 19. Appendix A's
`reconciliation:` block → Task 1.

**Deliberate deviations, each stated in the code that makes them:**
1. `reconcile_draws`'s second parameter is `ReconciliationInputs`, not `ConstraintSystem` (Task 9).
2. The `reconciliation:` config block carries five keys Appendix A does not (Task 1) — §12
   specifies no tolerance, iteration cap, or convergence criterion anywhere.
3. §10.4's shrinkage form and `k = 5.0` are this package's choice; §10.4 gives no form (Task 13).
4. §10.5's decline is required by the roadmap, not by §10.5 (Task 14).

**Known-vacuous-on-D1 criteria, called out in the tasks that own them:** §17.3 properties 2, 3 and
5 run on synthetic fixtures because D1 has no finite upper bounds and no state-by-size cells. If a
later reviewer finds these tests drawing from `deterministic_bounds`, they have been silently
weakened.

**Type consistency.** `Weights` is `(values, basis)` throughout. `Anchor` is
`(reference_month, residual, missing_cells, anchor_basis)` throughout. Every estimator's `weights`
returns `Weights | Decline`. `establishment_weights` returns a bare `dict[str, float]` — the
fallback rung, not a `Weights` — and only `compose` and `EstablishmentProportional` turn it into
one.

---

## Execution handoff

**Plan complete and saved to `specs/plans/4-stage3-logging-employment-spec.md`.**

**One spec section is consciously excluded: §10.7, baseline uncertainty.** Its empirical predictive
intervals are built "from rolling pseudo-suppression residuals", which is Stage 4's harness — and
the roadmap agrees, putting §10.7 in Stage 4's `Produces` and REQ-013's interval half in Stage 4's
`Gap closed`. Stage 3 ships point estimates; nothing here produces an interval.

**Recommended: `/clear` (or open a new session) and execute against the saved plan** — a fresh
session drops this planning conversation and lets execution run on the standard model default
(planning belongs on the stronger tier; execution does not). Two execution options, either session:

**1. Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks.

**2. Inline Execution** — I execute the tasks myself, in plan order (executing-plans).

Continuing in THIS session works too, but costs more on a long plan: every execution turn re-reads
the full planning history and inherits this session's model. **Which approach?**
