# Stage 4: Pseudo-Suppression Validation Harness and Baseline Scoreboard — Implementation Plan

**Status: COMPLETE (2026-09-07)** — executed via executing-plans; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via
> **subagent-driven-development** (the default) — or **executing-plans** when your human partner
> chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage 4 — on plan completion, tick the stage
> and re-validate later stages against what shipped.

**Goal:** Build the realistic pseudo-suppression generator, holdout regimes, leakage controls, and
metric suite, then score every Stage 3 baseline so the Bayesian model has a published number to
beat.

**Architecture:** A `validate/` subpackage. One mask constructor, `apply_mask`, returns a masked
`HarmonizedData` — the mask lives in the *frame*, not in a hand-built `Partition`, so the Stage 2
rebuild and the Stage 3 estimators read the same masked object and a leak is unconstructible rather
than merely avoided. Regime modules select target cells and hand `apply_mask` a target set; the
harness re-runs `build_constraint_system` + `solve_component` for §13.2 steps 5–6 and
`run_baselines` for step 7; metric modules score the result into `validation_metrics.parquet`. One
CLI command (`validate`) and one programmatic entry point (`run_pseudo_suppression`) per §16.2.

**Tech Stack:** Python ≥ 3.14, uv + hatchling, Polars, NumPy, SciPy, HiGHS via `highspy`, Typer,
pytest.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **Python floor `>=3.14`**; console script is **`logging-estimates`** (not `logging-employment`).
- **Polars, never pandas.** `import pandas` is a defect.
- **Normative keywords are defined by the spec itself** (§1.1): MUST, MUST NOT, SHOULD, SHOULD NOT,
  MAY are normative. Never soften a MUST into a log line.
- **Every command MUST write a machine-readable manifest and MUST be idempotent for the same
  inputs** (§16.1).
- **THE ANTI-DRIFT RULE.** Every count in this plan — 1,227, 4,716, 272, 96/96, 30 s, 6, 37 — is a
  measurement dated **2026-09-07** against `runs/2fc2c6003e0c`, not an invariant. Compute them at
  run time, record them in the run manifest, and assert on **structure** (the mask is applied; the
  guard fires; the denominator is stated), never on the literal number. One BLS revision moves all
  of them. This rule is inherited from plan 4 and it still binds.
- **ONE MASK OBJECT.** `validate/` MUST NOT hand-build an `EstimatorContext` and MUST NOT construct
  a `Partition` directly. It masks the frame and lets `run_baselines` derive the anchor and the
  context from that one object. Rationale in "What the evidence already settles" §3.
- **INV-009 — SYNTHETIC LABELS ONLY.** `qcew_monthly`'s 4,812 rows keep `suppression_type =
  'unknown'`. Primary-like / complementary-like labels exist only on the harness's own masked copy
  and its own output tables. Never write a synthetic label back onto the staged layer.
- **STAGE 2'S PERSISTED OUTPUTS ARE FROZEN.** The harness rebuilds constraint systems **in memory**
  from masked frames. It MUST NOT write to `data/constraints/`, MUST NOT overwrite the run's
  `deterministic_bounds.parquet`, and MUST NOT join a masked cell against the shipped bounds —
  that join returns the truth.
- **DECLINE, COMPOSE, AND REFUSE ARE THREE DIFFERENT OUTCOMES.** A declined row carries a
  `decline_kind`. A *composed* row carries `weight_basis = 'establishment_fallback'` and **no**
  `decline_kind` — plan 10's `BreakAdjustedShare` refusals are composed, so they are invisible to
  §13.8's decline-by-kind report. Any scoreboard that reads only decline counts misreports §10.3
  variant 5's coverage. Read `weight_basis_counts` per estimator, never pooled.
- **NO SYNTHESIZED BOUNDS.** A null `selected_upper` reads as `+inf` and MUST NOT be coerced to a
  number; a per-cell floor of 1 employee is equally an invention. Inherited from plan 4, unchanged.
- **THE ANCHOR-IMPLIED CEILING IS NOT A BOUND.** `E_s <= R_t` MUST NOT be written into
  `deterministic_bounds` (INV-005/INV-008, and `anchor.py`'s own docstring forbids it). If an
  anchor-implied width is wanted it lives in `validation_metrics` under its own column name.

---

## What the evidence already settles

Read this section before Task 1. Every fact below was **measured by running code** on 2026-09-07
against the staged D1 layer and `runs/2fc2c6003e0c`. An implementer who does not know them will
build the wrong thing, and several of them invalidate the obvious design.

### 1. §13.5's deterministic-bound metrics are structurally vacuous on the state-total arm

The constraint system's 6,038 rows split **6,030 single-cell / 8 multi-cell**, and the only cell
kinds appearing in a multi-cell row are `national_size` and `national_total`. Of the 4,716
`state_total` cells, **zero** appear in any multi-cell row; each carries only its own `eq` fixing
row (when observed), or `ge` + `integrality` (when suppressed).

Therefore masking **any** state-month, in **any** of the 13 §13.3 regimes, yields rank 0,
nullity 1, `[0.0, None]`, `bound_status = 'unbounded'`. Verified on five mask shapes (smallest
observed cell truth 3, largest 5,391, a true_zero cell, a 36-cell whole-month clustered mask, a
12-month consecutive run): all 55 masked targets identical.

The cause is not a bug: `assert_no_national_employment_margin` implements Stage 0's SRC-QCEW-006
`decline`. **Consequences the plan obeys:**

- §13.2 step 3 (complementary-like cells "so the target is not trivially recovered by subtraction")
  and step 6 (reject exactly-recoverable masks) are **inert on state totals** — there is no
  subtraction relation to defeat. The *labels* are still required by step 8 and INV-009.
- Stage 4's exit criterion "the harness rejects a mask whose target remains exactly recoverable"
  can only ever fire on the **`national_size` March arm**. A state-total test would pass vacuously
  forever. Task 8 puts the rejection test where it can fire.
- Feasible width, truth-in-bound rate, exact-recovery rate and LP-vs-MILP tightening are **defined
  but carry no information** on the state arm. Task 15 emits them as null beside an explicit
  `bound_cells_finite_upper = 0`, never as `1.0 / 0 / inf` that read like results.

### 2. The national-size March arm is where identification actually lives

Eight March margins (2017-03 … 2024-03). Masking each of the 37 observed size cells one at a time
gives **6 `exactly_recoverable` and 31 `partially_identified`, 0 unbounded**. All 6 exact cases are
in **2017-03** — the only March with zero real suppressions, and therefore the only "fully observed
public component" §13.2 step 1 asks for. All 15 complementary *pairs* within 2017-03 drop to
`partially_identified` with the truth inside (widths 745–11,572), so step 3 has live instances there
and only there.

A status flip on a size cell is **not** "strictly weaker": `rows.size_support_rows` fires only for
suppressed classes, so the flip *adds* a hard bounded `size_support` range row. Infeasibility can
genuinely bite on this arm, and Task 8 handles the raise rather than assuming it cannot happen.

### 3. The mask must live in the frame, not in a `Partition`

`observed_partition`'s docstring invites a partition-only mask. **Following it literally produces a
harness that scores against a constraint system which still fixes the answer.** Measured on
41/2019-06 (observed, truth 5,147):

```text
view A (table untouched, Partition-only mask):
  fix|state_total|41|2019-06|... relation=eq rhs 5147.0    bound_status: observed  lower 5147 upper 5147
view B (frame masked):
  integer|... , nonneg|... relation=ge rhs_lower 0.0        bound_status: unbounded lower 0.0 upper None
```

The partition-only view also leaves the held-out truth sitting in
`context.partitions[m].missing["employment_value"]`, one column read away from any estimator or
metric. Today's ten estimators happen not to read it — the only `context.monthly` reads are
`historical.py:137,138`, `fallback.py:91` and `simple.py:31`, none of which touch a masked state
value — so the leak is **latent, not actual**. The first Stage 5 or Stage 7 estimator that reaches
for `context.monthly` breaks it silently. Masking the frame closes it structurally.

`HarmonizedData` is a frozen dataclass, so `dataclasses.replace(data, qcew_monthly=masked)` creates
a new object and does **not** mutate the staged layer — the docstring's "without mutating
`qcew_monthly`" is satisfied by the frame mask too. There is nothing to correct in that docstring.

### 4. The cost model is dominated by `run_baselines`, not by the constraint rebuild

Measured, mean of 5 runs:

```text
build_constraint_system + components + membership + index   ~72 ms
solve_bounds (whole system)                                 ~356 ms
solve_component (one singleton)                             ~0.05 ms
run_baselines, all 10 estimators                            ~30 s      <-- dominates
run_baselines, §10.8's four rungs only                      ~5.7 s
run_baselines, one estimator                                ~0.4 s
```

A full mask cycle is **~30.4 s**, not the ~67 ms the constraint arm alone suggests. 13 regimes ×
20 replicates ≈ **2.2 hours** at full registry. This is why Task 4 adds an `estimators` keyword to
`run_baselines`: restricting a regime to the rungs it needs is a 5× lever, and it is also the
signature §16.2 already specifies.

### 5. A mask of size one can break nine estimators — if the target is a true zero

Masking the single `true_zero` cell (state 38, 2020-01, truth 0, `qtrly_establishments = 0`):

```text
equal_residual               ok
establishment_proportional   RAISE: WeightDomainError
share_last_observed          RAISE: WeightDomainError
share_same_month_prior_year  RAISE: WeightDomainError
share_rolling_median         RAISE: WeightDomainError
share_exponentially_weighted RAISE: WeightDomainError
share_break_adjusted         RAISE: WeightDomainError
cbp_intensity                RAISE: WeightDomainError
harvest_proportional         DECLINE: by_design
constrained_regression       RAISE: WeightDomainError
```

Masking an observed cell in the same month costs nothing. So the eligible-target predicate is
`area_type == 'state' AND observation_status == 'observed' AND qtrly_establishments > 0`, and a
config asking for `true_zero` targets MUST raise rather than warn. The loss is non-random — the 27
true-zero cells land only on DE and ND — so admitting them silently biases the scoreboard.

This also makes `reconciliation_failure` a **live** decline kind for the first time: it never occurs
on D1, and Stage 4's masks are what produce it.

### 6. Regime 12 (preliminary-to-final vintage) cannot run, and the config default disagrees

Non-circular evidence — `release_status` is `pl.lit(...)` stamped from config, so it proves nothing
on its own:

```text
release_vintage == lower(reference_quarter) everywhere: True
snapshot_id == release_vintage everywhere:              True
qcew_monthly:       rows=4812   periods=96  max distinct snapshot_id per period: 1
qcew_national_size: rows=140343 periods=8   max distinct snapshot_id per period: 1
cbp_state_size:     rows=1298   periods=7   max distinct snapshot_id per period: 1
find data/raw/qcew -type f | wc -l  ->  32   (one CSV per quarter)
```

The column *named* `release_vintage` is the reference quarter lowercased; it carries no publication
vintage. No period in any staged table carries a second snapshot. **Appendix A ships
`include_vintage_comparison: true`, so the config default and the data disagree.** Per Stage 4's own
design that is a fail-closed condition, not a silent skip: Task 13 flips the default to `false`,
cites this measurement, and makes the harness refuse rather than emit an empty partition.

### 7. Regime 11 (NAICS transition) runs, but scores five labels on one estimator at the seam

`vintage_for_year` returns "NAICS 2022" at year ≥ 2022, so the seam is 2021-12/2022-01 **by
construction** — `naics_vintage` is a derived column, and this regime tests our own vintage rule,
not a source-published break. With `historical_may_cross_naics_vintage: false` and a 24-month
lookback, the share family loses its history at the seam:

```text
2021-12  own=24  fallback=36
2022-01  own=0   fallback=65
2022-02  own=0   ...
2022-03  own=0   ...
months with zero own-arm share rows: 2017-01..03, 2017-07..09, 2022-01..03
```

In 2022-01…03 all five §10.3 variants emit `establishment_proportional`'s number under five labels.
Because composition emits **no** `decline_kind`, this is invisible to §13.8's decline-by-kind report.
The regime-11 task reads `weight_basis_counts`.

### 8. Panel facts the generator must be told, not left to discover

```text
fully observed state-years available for a state-year block regime:  272
states with at least one >=12-month observed run:                     40
states never observed in any month (permanently in the missing set):   6
DC absent from qcew_monthly entirely, while config says states_dc
```

The six never-observed states can **never** be a mask target and their cells must not be reported as
scored. They are why the share family shows `establishment_fallback` in 96 of 96 months. DC's
absence against `config.project.geography_universe = 'states_dc'` is an open Stage 0 item — cite it,
do not re-derive it.

§13.2's propensity predictors are all available **except "parent share"**: `qcew_monthly` carries
only industry 113310, so no parent 1133/113 state series exists to form a share against.

### 9. `cbp_intensity` is unscoreable in 2024, by construction

CBP publishes 2017–2023; 2024 is not published. That is the whole of the 147 `data_gap` declines
(12 months × the missing cells in each). Under a mask the count rises (159 was measured) — that is
**the same 12-month refusal over a larger missing set**, not degradation. Any regime whose window
includes 2024 scores 9 estimators, not 10, and must state that denominator.
`preferred_estimator_by_month` already reports this (84 months `cbp_intensity`, 12
`constrained_regression`); the window scalar names `cbp_intensity` for all 96 and MUST NOT be used.

### 10. `patch_mask` silently carries the unmasked hash

`BuiltSystem` is a frozen dataclass whose `constraint_set_hash` is a **stored field**, so
`dataclasses.replace` copies it verbatim. A patched masked system therefore reports the *unmasked*
hash, which matches the persisted set and the run manifest. The harness MUST do a full rebuild for
anything it records a hash against, and `validation_metrics` MUST carry the **masked** hash — or
§18.1's reproducibility check conflates two different systems.

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/logging_employment/validate/__init__.py` | Public surface: `run_pseudo_suppression`, `apply_mask`. |
| `src/logging_employment/validate/mask.py` | The ONE mask constructor. Eligible-target predicate, the seven-field flip, INV-009 labels. |
| `src/logging_employment/validate/recover.py` | §13.2 steps 5–6: rebuild the system from a masked frame, solve the affected component, decide exact recoverability. |
| `src/logging_employment/validate/propensity.py` | §13.2 step 1: propensity from public predictors only. |
| `src/logging_employment/validate/regimes.py` | The 13 §13.3 regimes as target-set selectors + their declared dispositions. |
| `src/logging_employment/validate/leakage.py` | §13.4 assertions the harness runs on itself. |
| `src/logging_employment/validate/intervals.py` | §10.7 empirical predictive intervals from rolling residuals. |
| `src/logging_employment/validate/metrics.py` | §13.5–13.8 metric families and their denominators. |
| `src/logging_employment/validate/scoreboard.py` | Per-regime aggregation, preferred-baseline selection. |
| `src/logging_employment/validate/harness.py` | `run_pseudo_suppression` — drives everything above. |
| `src/logging_employment/contracts.py` | *(modify)* Stage 4 enums + `VALIDATION_METRIC_SCHEMA`, `VALIDATION_SCORE_SCHEMA`. |
| `src/logging_employment/config.py` | *(modify)* `ValidationConfig`, `PromotionConfig`. |
| `src/logging_employment/baselines/runner.py` | *(modify, one keyword)* `estimators: Sequence[Estimator] = REGISTRY`. |
| `src/logging_employment/cli.py` | *(modify)* the `validate` command. |

Tests mirror the module tree under `tests/unit/` and `tests/integration/`.

---

### Task 1: The `validation:` and `promotion:` config blocks

**Files:**
- Modify: `src/logging_employment/config.py`
- Modify: `config.yaml`
- Test: `tests/unit/test_config_validation_block.py`

**Interfaces:**
- Consumes: the existing `_Strict` pydantic base and `Config` aggregate in `config.py`.
- Produces: `ValidationConfig`, `PromotionConfig`, `Config.validation`, `Config.promotion`.

Appendix A is **adapted, not copied**: `include_vintage_comparison` defaults `false` because the
data cannot support it (evidence §6). §13.2's opening line — "Random masking alone is prohibited as
the only validation design" — is enforced as a **model validator on the config object**, not as a
runtime check, so an invalid configuration cannot be constructed at all.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_config_validation_block.py
import pytest
from pydantic import ValidationError

from logging_employment.config import PromotionConfig, ValidationConfig


def test_a_random_mask_only_design_is_refused_at_construction():
    """§13.2's opening line is a config-time refusal, not a runtime warning."""
    with pytest.raises(ValidationError, match="random_mask_only"):
        ValidationConfig(
            pseudo_suppression_seeds=[1024],
            include_random_mask_sanity_check=True,
            include_primary_like=False,
            include_complementary_like=False,
            include_long_runs=False,
            include_rolling_origin=False,
            include_retrospective_smoothing=False,
            include_vintage_comparison=False,
        )


def test_vintage_comparison_defaults_off_because_d1_carries_one_vintage():
    cfg = ValidationConfig(pseudo_suppression_seeds=[1024], include_primary_like=True)
    assert cfg.include_vintage_comparison is False


def test_promotion_gates_carry_appendix_a_defaults():
    p = PromotionConfig()
    assert p.minimum_wape_improvement == 0.05
    assert p.maximum_major_stratum_wape_degradation == 0.02
    assert p.nominal_coverage_tolerance == 0.05
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_config_validation_block.py -v`
Expected: FAIL with `ImportError: cannot import name 'ValidationConfig'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/config.py  — append near the other block models
class ValidationConfig(_Strict):
    """§13's harness settings, adapted from Appendix A.

    `include_vintage_comparison` defaults False against Appendix A's True: measured 2026-09-07, no
    period in any staged table carries a second snapshot, and `release_vintage` is the reference
    quarter lowercased rather than a publication vintage. Turning it on is a fail-closed error in
    `regimes.py`, not a silent empty partition.
    """

    pseudo_suppression_seeds: list[int] = [1024, 2048, 4096]
    include_random_mask_sanity_check: bool = True
    include_primary_like: bool = True
    include_complementary_like: bool = True
    include_long_runs: bool = True
    include_rolling_origin: bool = True
    include_retrospective_smoothing: bool = False
    include_vintage_comparison: bool = False
    replicates_per_regime: int = 20
    minimum_unmasked_lookback_months: int = 6
    minimum_missing_set_size: int = 2

    @model_validator(mode="after")
    def _refuse_a_random_mask_only_design(self) -> "ValidationConfig":
        designed = (
            self.include_primary_like
            or self.include_complementary_like
            or self.include_long_runs
            or self.include_rolling_origin
            or self.include_retrospective_smoothing
            or self.include_vintage_comparison
        )
        if not designed:
            raise ValueError(
                "random_mask_only: §13.2 prohibits random masking as the ONLY validation design. "
                "Enable at least one designed regime beside the random sanity check."
            )
        return self


class PromotionConfig(_Strict):
    """§13.10's gates. Configurable engineering thresholds, not findings."""

    minimum_wape_improvement: float = 0.05
    maximum_major_stratum_wape_degradation: float = 0.02
    nominal_coverage_tolerance: float = 0.05
```

Add `from pydantic import model_validator` to the imports if absent, and the two fields to `Config`:

```python
    validation: ValidationConfig = ValidationConfig()
    promotion: PromotionConfig = PromotionConfig()
```

- [x] **Step 4: Add the blocks to `config.yaml`**

```yaml
validation:
  pseudo_suppression_seeds: [1024, 2048, 4096]
  include_random_mask_sanity_check: true
  include_primary_like: true
  include_complementary_like: true
  include_long_runs: true
  include_rolling_origin: true
  # Appendix A ships these two true. Both are turned off here with a recorded reason:
  # retrospective smoothing has no smoothing estimator in the §10 registry to exercise, and
  # vintage comparison has no second vintage on disk (see the plan's evidence §6).
  include_retrospective_smoothing: false
  include_vintage_comparison: false
  replicates_per_regime: 20
  minimum_unmasked_lookback_months: 6
  minimum_missing_set_size: 2

promotion:
  minimum_wape_improvement: 0.05
  maximum_major_stratum_wape_degradation: 0.02
  nominal_coverage_tolerance: 0.05
```

- [x] **Step 5: Run the tests and the config validator**

Run: `uv run pytest tests/unit/test_config_validation_block.py -v && uv run logging-estimates validate-config --config config.yaml`
Expected: 3 passed; `validate-config` exits 0.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/config.py config.yaml tests/unit/test_config_validation_block.py
git commit -m "feat(config): the validation and promotion blocks, with a random-mask-only refusal"
```

---

### Task 2: Stage 4 contracts — enums, schemas, and the `suppression_type` guard

**Files:**
- Modify: `src/logging_employment/contracts.py`
- Test: `tests/unit/test_contracts_validation.py`

**Interfaces:**
- Consumes: `SUPPRESSION_TYPES`, `assert_declared_provenance`, `schema_fingerprint`, `validate_frame`.
- Produces: `HOLDOUT_REGIMES`, `MASK_ARMS`, `REGIME_DISPOSITIONS`, `INTERVAL_SOURCES`,
  `VALIDATION_SCORE_SCHEMA`, `VALIDATION_METRIC_SCHEMA`.

`assert_declared_provenance` currently loops over four columns and skips ones a frame lacks.
`suppression_type` is declared in `SUPPRESSION_TYPES` but **nothing in `src/` validates it** — it is
referenced only by tests. Stage 4 is the first writer of a non-`unknown` value, so this task closes
that gap in the same loop.

Two tables, because they have different grains and conflating them is how R-COMP-10's denominator
gets lost:
- `validation_scores` — **one row per (regime, seed, replicate, estimator, cell)**: the raw scored
  observations, including the ones that were declined.
- `validation_metrics` — **one row per (regime, seed, estimator, metric_family)**: the aggregates
  §13.5–13.8 require, each carrying its own denominator.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_contracts_validation.py
import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.errors import ConceptViolationError


def test_a_suppression_type_outside_the_declared_set_is_refused():
    frame = pl.DataFrame({"suppression_type": ["primary_like", "invented_kind"]})
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        contracts.assert_declared_provenance(frame)


def test_the_declared_suppression_types_pass():
    frame = pl.DataFrame({"suppression_type": ["unknown", "primary_like", "complementary_like"]})
    contracts.assert_declared_provenance(frame)


def test_every_holdout_regime_carries_a_disposition():
    assert set(contracts.REGIME_DISPOSITIONS) == set(contracts.HOLDOUT_REGIMES)
    assert contracts.REGIME_DISPOSITIONS["preliminary_to_final_vintage"] == "cannot_run_on_d1"


def test_the_two_validation_schemas_are_distinct_and_fingerprinted():
    a = contracts.schema_fingerprint(contracts.VALIDATION_SCORE_SCHEMA)
    b = contracts.schema_fingerprint(contracts.VALIDATION_METRIC_SCHEMA)
    assert a != b
    # R-COMP-10: a metric row is unreadable without the base it was computed over.
    assert "denominator" in contracts.VALIDATION_METRIC_SCHEMA
    assert "denominator_basis" in contracts.VALIDATION_METRIC_SCHEMA
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_contracts_validation.py -v`
Expected: FAIL — `assert_declared_provenance` does not yet check `suppression_type`; the new names
do not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/contracts.py

HOLDOUT_REGIMES: tuple[str, ...] = (
    "small_cell_biased",
    "concentration_proxy",
    "clustered_states_within_month",
    "long_consecutive_runs",
    "whole_state_year_blocks",
    "regional_blocks",
    "whole_seasonal_blocks",
    "rolling_origin",
    "retrospective_smoothing",
    "structural_break",
    "naics_transition",
    "preliminary_to_final_vintage",
    "cbp_size_gaps",
)

# Why a regime may not produce scores. `cannot_run_on_d1` is a REFUSAL, not a skip: the harness
# raises rather than emitting an empty partition that reads as "scored, nothing wrong".
REGIME_DISPOSITIONS: dict[str, str] = {
    "small_cell_biased": "feasible",
    "concentration_proxy": "feasible",
    "clustered_states_within_month": "feasible",
    "long_consecutive_runs": "feasible",
    "whole_state_year_blocks": "feasible",
    "regional_blocks": "feasible",
    "whole_seasonal_blocks": "feasible",
    "rolling_origin": "feasible",
    # No smoothing estimator exists in the §10 registry to exercise; adding one is a new baseline
    # outside §10's set and outside this stage.
    "retrospective_smoothing": "vacuous_on_registry",
    "structural_break": "feasible",
    "naics_transition": "feasible",
    # Measured 2026-09-07: no period in any staged table carries a second snapshot.
    "preliminary_to_final_vintage": "cannot_run_on_d1",
    "cbp_size_gaps": "feasible",
}

MASK_ARMS: tuple[str, ...] = ("state_total", "national_size")

INTERVAL_SOURCES: tuple[str, ...] = ("rolling_residual_ensemble", "none")

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
}

VALIDATION_METRIC_SCHEMA: dict[str, pl.DataType] = {
    "regime": pl.String,
    "seed": pl.Int64,
    "mask_arm": pl.String,
    "estimator_id": pl.String,
    "metric_family": pl.String,
    "metric_name": pl.String,
    "value": pl.Float64,
    # R-COMP-10: every scored comparison states the base it was computed over.
    "denominator": pl.Float64,
    "denominator_basis": pl.String,
    "n_scored": pl.Int64,
    "n_declined_by_design": pl.Int64,
    "n_declined_data_gap": pl.Int64,
    "n_declined_reconciliation_failure": pl.Int64,
    # Plan 10's refusals COMPOSE rather than decline, so they never reach the counts above.
    "n_own_estimator": pl.Int64,
    "n_establishment_fallback": pl.Int64,
    "interval_source": pl.String,
    "calibration_sample_size": pl.Int64,
    "bound_cells_finite_upper": pl.Int64,
    "constraint_rows_scored": pl.Int64,
}
```

Extend the provenance loop — one added pair:

```python
    for column, declared in (
        ("reconciliation_status", RECONCILIATION_STATUSES),
        ("weight_basis", WEIGHT_BASES),
        ("anchor_basis", ANCHOR_BASES),
        ("decline_kind", DECLINE_KINDS),
        ("suppression_type", SUPPRESSION_TYPES),
    ):
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_contracts_validation.py -v`
Expected: 4 passed.

- [x] **Step 5: Prove the new guard did not break the shipped layer**

The staged frame carries `suppression_type` on all 4,812 rows; if any value were outside the
declared set the whole pipeline would now fail closed. Confirm it does not:

Run:
```bash
uv run python -c "
import polars as pl
from logging_employment import contracts
contracts.assert_declared_provenance(pl.read_parquet('data/staged/qcew_monthly.parquet'))
print('staged layer passes the extended guard')
"
```
Expected: `staged layer passes the extended guard`

- [x] **Step 6: Run the full suite** — the guard now fires on a column many frames carry.

Run: `uv run pytest -q`
Expected: all pass (1,181 at the time of writing, plus the new ones).

- [x] **Step 7: Commit**

```bash
git add src/logging_employment/contracts.py tests/unit/test_contracts_validation.py
git commit -m "feat(contracts): Stage 4 regime enums, validation schemas, and the suppression_type guard"
```

---

### Task 3: `apply_mask` — the one mask constructor

**Files:**
- Create: `src/logging_employment/validate/__init__.py`
- Create: `src/logging_employment/validate/mask.py`
- Test: `tests/unit/test_validate_mask.py`

**Interfaces:**
- Consumes: `contracts.HarmonizedData`, `contracts.SUPPRESSION_TYPES`, `errors.ConceptViolationError`.
- Produces:
  - `MaskTarget(state_fips: str, reference_month: str, arm: str, suppression_type: str)`
  - `eligible_targets(monthly: pl.DataFrame) -> pl.DataFrame`
  - `apply_mask(data: HarmonizedData, targets: Sequence[MaskTarget]) -> tuple[HarmonizedData, pl.DataFrame]`
    returning the masked data **and the truth table captured before masking**.

This is the single point at which a cell becomes hidden. Every later task consumes its output and
none of them constructs a `Partition` or an `EstimatorContext`.

Seven columns change together. A two-column edit (`employment_value`, `observation_status`) is the
tempting defect: it leaves `employment_raw` carrying the truth as a string, which §13.4's first
bullet forbids.

`source_row_hash` is deliberately **left alone**: it hashes identity columns only (`ingest/qcew.py`
builds it from no value column), so retaining it does not retain the held-out value.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_mask.py
import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.mask import MaskTarget, apply_mask, eligible_targets

STAGED = Path("data/staged")


def _data() -> HarmonizedData:
    return HarmonizedData.load(STAGED)


def test_a_masked_row_is_indistinguishable_from_a_real_suppression():
    data = _data()
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    masked, truth = apply_mask(data, [target])

    real = masked.qcew_monthly.filter(
        (pl.col("observation_status") == "suppressed") & (pl.col("suppression_type") == "unknown")
    ).head(1)
    made = masked.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )
    shared = [
        "employment_value", "employment_raw", "wages_value", "wages_raw",
        "disclosure_code", "observation_status", "is_published_numeric_zero",
    ]
    assert made.select(shared).row(0) == real.select(shared).row(0)
    # ...but the synthetic label distinguishes it for INV-009.
    assert made["suppression_type"].item() == "primary_like"


def test_no_column_of_a_masked_row_retains_the_withheld_truth():
    data = _data()
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    masked, truth = apply_mask(data, [target])
    withheld = truth["truth"].item()

    row = masked.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    ).row(0, named=True)
    for column, value in row.items():
        assert str(value) != str(withheld), f"{column} retained the held-out truth"


def test_the_staged_layer_is_not_mutated():
    data = _data()
    before = data.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )["employment_value"].item()
    apply_mask(data, [MaskTarget("41", "2019-06", "state_total", "primary_like")])
    after = data.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )["employment_value"].item()
    assert before == after


def test_a_true_zero_cell_is_refused_as_a_target():
    """Measured: masking the one true_zero cell raises WeightDomainError in 8 of 10 estimators.

    On D1 a true zero carries `observation_status == 'true_zero'`, so the observed-only predicate
    is what refuses it — verified, all 27 true-zero rows also have `qtrly_establishments == 0`,
    and no observed row has zero establishments. Match on the status message, not the
    establishment one, or this test asserts a guard that never fires.
    """
    data = _data()
    with pytest.raises(ConceptViolationError, match="observation_status"):
        apply_mask(data, [MaskTarget("38", "2020-01", "state_total", "primary_like")])


def test_an_observed_cell_with_no_establishments_is_refused():
    """The second guard, exercised directly.

    Measured 2026-09-07: zero D1 rows are `observed` with `qtrly_establishments <= 0`, so this
    guard is unreachable through the staged layer today. It is kept because a revision that
    published such a row would otherwise cost a whole month across nine estimators, and it is
    tested on a synthetic frame rather than left as unexecuted code.
    """
    data = _data()
    poisoned = data.qcew_monthly.with_columns(
        pl.when(
            (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
        )
        .then(0)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    with pytest.raises(ConceptViolationError, match="qtrly_establishments"):
        apply_mask(
            dataclasses.replace(data, qcew_monthly=poisoned),
            [MaskTarget("41", "2019-06", "state_total", "primary_like")],
        )


def test_an_already_suppressed_cell_is_refused_as_a_target():
    data = _data()
    suppressed = data.qcew_monthly.filter(pl.col("observation_status") == "suppressed").row(
        0, named=True
    )
    with pytest.raises(ConceptViolationError, match="observation_status"):
        apply_mask(
            data,
            [MaskTarget(suppressed["state_fips"], suppressed["reference_month"],
                        "state_total", "primary_like")],
        )


def test_an_undeclared_suppression_type_is_refused():
    data = _data()
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        apply_mask(data, [MaskTarget("41", "2019-06", "state_total", "invented_kind")])


def test_eligible_targets_excludes_true_zero_and_already_suppressed():
    data = _data()
    eligible = eligible_targets(data.qcew_monthly)
    assert eligible.filter(pl.col("qtrly_establishments") <= 0).height == 0
    assert eligible.filter(pl.col("observation_status") != "observed").height == 0
    assert eligible.filter(pl.col("area_type") != "state").height == 0
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_mask.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.validate'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/mask.py
"""The one place a cell becomes hidden.

The mask lives in the FRAME, not in a hand-built `Partition`. `observed_partition`'s docstring
invites a partition-only mask, and measured on 2026-09-07 that route leaves the constraint system
still fixing the answer: view A (table untouched) keeps a `fix|state_total|...` equality at the
held-out value and reports `bound_status='observed'`, while view B (frame masked) reports
`unbounded`. The partition-only view also leaves the truth in
`context.partitions[m].missing["employment_value"]`, one column read from any estimator. Masking
the frame makes the leak unconstructible rather than merely unused.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..contracts import SUPPRESSION_TYPES, HarmonizedData
from ..errors import ConceptViolationError


@dataclass(frozen=True)
class MaskTarget:
    """One cell to hide, with the INV-009 label it will carry."""

    state_fips: str
    reference_month: str
    arm: str
    suppression_type: str


def eligible_targets(monthly: pl.DataFrame) -> pl.DataFrame:
    """Cells a mask may hide: published state cells that have at least one establishment.

    A `true_zero` cell has `qtrly_establishments == 0`, and masking one costs a whole month across
    nine estimators — measured, eight raise `WeightDomainError` and one declines, because the
    disclosed establishment total that scales their fallback arm goes to zero. The loss lands only
    on the states that carry true zeros, so admitting them biases the scoreboard non-randomly.
    """
    return monthly.filter(
        (pl.col("area_type") == "state")
        & (pl.col("observation_status") == "observed")
        & (pl.col("qtrly_establishments") > 0)
    )


def apply_mask(
    data: HarmonizedData, targets: Sequence[MaskTarget]
) -> tuple[HarmonizedData, pl.DataFrame]:
    """Hide every target and return `(masked_data, truth_table)`.

    The truth table is captured BEFORE the flip and is the harness's only copy of the held-out
    values. It is never handed to an estimator.
    """
    for target in targets:
        if target.suppression_type not in SUPPRESSION_TYPES:
            raise ConceptViolationError(
                f"suppression_type {target.suppression_type!r} is not declared; the set is "
                f"{list(SUPPRESSION_TYPES)} (INV-009)"
            )

    monthly = data.qcew_monthly
    keys = [(t.state_fips, t.reference_month) for t in targets]
    selector = pl.struct("state_fips", "reference_month").is_in(
        [{"state_fips": s, "reference_month": m} for s, m in keys]
    )

    chosen = monthly.filter(selector)
    if chosen.height != len(set(keys)):
        raise ConceptViolationError(
            f"{len(set(keys))} targets requested but {chosen.height} rows matched; a target with "
            "no published row cannot be masked (the six never-observed states are permanently in "
            "the missing set and are never eligible)"
        )
    bad_status = chosen.filter(pl.col("observation_status") != "observed")
    if bad_status.height:
        raise ConceptViolationError(
            f"{bad_status.height} target(s) have observation_status != 'observed'; masking an "
            "already-suppressed cell hides nothing and double-counts it in the missing set"
        )
    bad_est = chosen.filter(pl.col("qtrly_establishments") <= 0)
    if bad_est.height:
        raise ConceptViolationError(
            f"{bad_est.height} target(s) have qtrly_establishments <= 0. Measured 2026-09-07: "
            "masking such a cell raises WeightDomainError in eight estimators and declines a "
            "ninth, costing the whole month non-randomly"
        )

    truth = chosen.select(
        pl.col("state_fips"),
        pl.col("reference_month"),
        pl.col("employment_value").alias("truth"),
        pl.col("qtrly_establishments"),
    )

    labels = pl.DataFrame(
        {
            "state_fips": [t.state_fips for t in targets],
            "reference_month": [t.reference_month for t in targets],
            "_label": [t.suppression_type for t in targets],
        }
    )

    masked = (
        monthly.join(labels, on=["state_fips", "reference_month"], how="left")
        .with_columns(
            pl.when(selector).then(None).otherwise(pl.col("employment_value"))
            .alias("employment_value"),
            pl.when(selector).then(pl.lit("0")).otherwise(pl.col("employment_raw"))
            .alias("employment_raw"),
            pl.when(selector).then(None).otherwise(pl.col("wages_value")).alias("wages_value"),
            pl.when(selector).then(pl.lit("0")).otherwise(pl.col("wages_raw")).alias("wages_raw"),
            pl.when(selector).then(pl.lit("N")).otherwise(pl.col("disclosure_code"))
            .alias("disclosure_code"),
            pl.when(selector).then(pl.lit("suppressed")).otherwise(pl.col("observation_status"))
            .alias("observation_status"),
            pl.when(selector).then(True).otherwise(pl.col("is_published_numeric_zero"))
            .alias("is_published_numeric_zero"),
            pl.when(selector).then(pl.col("_label")).otherwise(pl.col("suppression_type"))
            .alias("suppression_type"),
        )
        .drop("_label")
    )
    return dataclasses.replace(data, qcew_monthly=masked), truth
```

Create `src/logging_employment/validate/__init__.py`:

```python
"""§13's pseudo-suppression validation harness."""

from .mask import MaskTarget, apply_mask, eligible_targets

__all__ = ["MaskTarget", "apply_mask", "eligible_targets"]
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_mask.py -v`
Expected: 8 passed.

- [x] **Step 5: Prove the mask reaches the constraint layer**

This is the claim the whole harness rests on; assert it by running, not by reading.

Run:
```bash
uv run python -c "
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.constraints.system import build_constraint_system
from logging_employment.validate.mask import MaskTarget, apply_mask
from pathlib import Path
cfg = load_config(Path('config.yaml')); data = HarmonizedData.load(Path('data/staged'))
masked, truth = apply_mask(data, [MaskTarget('41','2019-06','state_total','primary_like')])
a = build_constraint_system(data, cfg); b = build_constraint_system(masked, cfg)
print('truth withheld :', truth['truth'].item())
print('hashes differ  :', a.constraint_set_hash != b.constraint_set_hash)
print('base suppressed:', a.cells.filter(__import__('polars').col('observation_status')=='suppressed').height)
print('mask suppressed:', b.cells.filter(__import__('polars').col('observation_status')=='suppressed').height)
"
```
Expected: `truth withheld : 5147`, `hashes differ  : True`, and the masked suppressed count exactly
one higher than the base.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/validate tests/unit/test_validate_mask.py
git commit -m "feat(validate): apply_mask, the single frame-level mask constructor"
```

> Deviation: added a duplicate-target guard. The label join is on (state_fips, reference_month),
> so a target set naming one cell twice emits two rows for it; the height check does not catch
> that because `set(keys)` dedups before comparing. Also added the size-arm leak test, which the
> state-arm one cannot cover — it reads only `qcew_monthly`.

---

### Task 4: `run_baselines` gains an `estimators` keyword

**Files:**
- Modify: `src/logging_employment/baselines/runner.py`
- Test: `tests/unit/test_baselines_runner.py` (extend)

**Interfaces:**
- Consumes: `REGISTRY`, the `Estimator` protocol.
- Produces: `run_baselines(data, config, *, constraint_set_hash=None, estimators=REGISTRY)`.

This is §16.2's own signature — `run_pseudo_suppression(data, estimators, config)` takes an
estimator sequence — and it is the harness's cost lever: measured, all ten estimators cost ~30 s per
call against ~5.7 s for §10.8's four rungs and ~0.4 s for one. At 13 regimes × 20 replicates that is
the difference between ~2.2 hours and ~25 minutes.

`runner.py` imports no `Sequence` today. Adding only the keyword still *runs* — `from __future__
import annotations` stringifies the annotation — but fails `ruff` with `F821 Undefined name
'Sequence'`. Add the import.

**Do NOT add a `partitions=` argument.** The mask lives in the frame (Task 3); a partition argument
would reintroduce the two-object pairing whose mismatch plan 9's `ConceptViolationError` exists to
catch, and which the frame mask makes unconstructible.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_baselines_runner.py  — append
def test_run_baselines_accepts_an_estimator_subset(tiny_harmonized, tiny_config):
    """§16.2 hands `run_pseudo_suppression` an estimator sequence; the runner must accept one."""
    from logging_employment.baselines.runner import REGISTRY, run_baselines

    subset = REGISTRY[:2]
    results, _audit = run_baselines(tiny_harmonized, tiny_config, estimators=subset)
    assert set(results["estimator_id"].unique().to_list()) == {e.estimator_id for e in subset}


def test_run_baselines_defaults_to_the_full_registry(tiny_harmonized, tiny_config):
    from logging_employment.baselines.runner import REGISTRY, run_baselines

    results, _audit = run_baselines(tiny_harmonized, tiny_config)
    assert results["estimator_id"].n_unique() == len(REGISTRY)
```

Reuse whatever fixtures the existing tests in this file already use for a toy `HarmonizedData` and
`Config`; do not invent new ones.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_baselines_runner.py -k estimator_subset -v`
Expected: FAIL with `TypeError: run_baselines() got an unexpected keyword argument 'estimators'`

- [x] **Step 3: Implement — three edits**

```python
# src/logging_employment/baselines/runner.py
from collections.abc import Sequence          # (1) new import
```

```python
def run_baselines(                            # (2) new keyword
    data: HarmonizedData,
    config: Config,
    *,
    constraint_set_hash: str | None = None,
    estimators: Sequence[Estimator] = REGISTRY,
) -> tuple[pl.DataFrame, pl.DataFrame]:
```

```python
        for estimator in estimators:          # (3) was: for estimator in REGISTRY:
```

Extend the docstring with the reason:

```
    `estimators` defaults to the full `REGISTRY` and exists so §13's harness can restrict a regime
    to the rungs it needs: measured, ten estimators cost ~30 s per call against ~0.4 s for one, and
    the harness pays that per mask replicate.
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_baselines_runner.py -v`
Expected: all pass, including the two new ones.

- [x] **Step 5: Lint — the import is the point**

Run: `uv run ruff check src/logging_employment/baselines/runner.py`
Expected: `All checks passed!` (without the import this reports `F821 Undefined name 'Sequence'`).

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/baselines/runner.py tests/unit/test_baselines_runner.py
git commit -m "feat(baselines): run_baselines takes an estimator subset, per §16.2"
```

> Deviation: `test_a_reconciliation_refusal_is_recorded_as_a_reconciliation_failure` injected its
> stub via `mock.patch.object(runner, "REGISTRY", ...)`. A default argument binds at definition
> time, so the patch no longer reaches the loop; the test now passes the stub through the new
> keyword, which is the seam it was reaching for and needs no mock.

---

### Task 5: `mask_and_solve` — §13.2 steps 5–6 over a masked frame

**Files:**
- Create: `src/logging_employment/validate/recover.py`
- Test: `tests/unit/test_validate_recover.py`

**Interfaces:**
- Consumes: `constraints.system.build_constraint_system`, `constraints.bounds.solve_bounds`,
  `validate.mask.apply_mask`.
- Produces: `MaskedSystem(bounds, constraint_set_hash, components)`,
  `mask_and_solve(data, targets, config) -> MaskedSystem`,
  `is_exactly_recoverable(bounds, cell_id) -> bool`.

There is **no** `solve_bounds(system, missing_cells=...)` parameter. The primitive is: mask the
frame, `build_constraint_system`, `solve_bounds`. Measured on the full D1 system: build 0.049 s,
solve 0.312 s — negligible against `run_baselines`' ~30 s, so no incremental-patch design is needed.

**Do not use `dataclasses.replace` to patch a `BuiltSystem`.** `constraint_set_hash` is a *stored
field*, so a patched system reports the **unmasked** hash — which matches the persisted set and the
run manifest, and would make `validation_metrics` claim a system it did not use.

Step 6's predicate is `bound_status == 'exactly_recoverable'` and nothing else. **`exactly_identified`
is not the predicate** — it is True on the 3,534 published cells, so filtering on it is a silent
3,534-row false positive. Do not import `disclosure.flags`; the harness needs no `DisclosureConfig`.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_recover.py
from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.recover import is_exactly_recoverable, mask_and_solve


def test_a_masked_state_total_is_unbounded_and_the_hash_moves():
    """The state-total arm carries no identification — this is a SCOPED NEGATIVE, not a bug.

    Every `state_total` cell is a single-cell component: `assert_no_national_employment_margin`
    implements Stage 0's SRC-QCEW-006 `decline`, so no multi-cell row ever touches one.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    base = mask_and_solve(data, [], cfg)
    masked = mask_and_solve(
        data, [MaskTarget("41", "2019-06", "state_total", "primary_like")], cfg
    )
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"
    row = masked.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
    assert row["bound_status"] == "unbounded"
    assert row["selected_lower"] == 0.0
    assert row["selected_upper"] is None
    assert masked.constraint_set_hash != base.constraint_set_hash
    assert not is_exactly_recoverable(masked.bounds, cell)


def test_exactly_identified_is_not_the_step_six_predicate():
    """A filter on `exactly_identified` would flag every published cell."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    system = mask_and_solve(data, [], cfg)
    assert system.bounds.filter(pl.col("exactly_identified")).height > 1000
    assert system.bounds.filter(pl.col("bound_status") == "exactly_recoverable").height == 0
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_recover.py -v`
Expected: FAIL — `No module named 'logging_employment.validate.recover'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/recover.py
"""§13.2 steps 5-6: rank and bound analysis on a masked component.

Always a FULL rebuild. `BuiltSystem.constraint_set_hash` is a stored field, so patching a system
with `dataclasses.replace` copies the unmasked hash verbatim — the patched object would report a
hash that matches the persisted constraint set and the run manifest while describing a different
system. Measured: a full rebuild costs ~0.05 s and the solve ~0.31 s, against ~30 s for the
estimator pass this sits beside, so there is nothing to optimise here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..config import Config
from ..constraints.bounds import solve_bounds
from ..constraints.system import build_constraint_system
from ..contracts import HarmonizedData
from .mask import MaskTarget, apply_mask


@dataclass(frozen=True)
class MaskedSystem:
    """A solved constraint system for one mask, plus the truth it withheld."""

    bounds: pl.DataFrame
    components: pl.DataFrame
    constraint_set_hash: str
    truth: pl.DataFrame


def mask_and_solve(
    data: HarmonizedData, targets: Sequence[MaskTarget], config: Config
) -> MaskedSystem:
    """Apply the mask, rebuild the system from the masked frame, and solve it."""
    masked, truth = apply_mask(data, targets) if targets else (data, _empty_truth())
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    return MaskedSystem(
        bounds=result.bounds,
        components=result.components,
        constraint_set_hash=built.constraint_set_hash,
        truth=truth,
    )


def _empty_truth() -> pl.DataFrame:
    return pl.DataFrame(
        schema={
            "state_fips": pl.String,
            "reference_month": pl.String,
            "truth": pl.Int64,
            "qtrly_establishments": pl.Int64,
        }
    )


def is_exactly_recoverable(bounds: pl.DataFrame, cell_id: str) -> bool:
    """§13.2 step 6's predicate, and only this one.

    NOT `exactly_identified`: that column is True for every published cell (3,534 of them on D1),
    because a published value is trivially identified by its own equality row. Filtering on it
    would reject every mask.
    """
    row = bounds.filter(pl.col("cell_id") == cell_id)
    if row.height == 0:
        raise KeyError(f"{cell_id!r} is not in this system's bounds")
    return row["bound_status"].item() == "exactly_recoverable"
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_recover.py -v`
Expected: 2 passed.

- [x] **Step 5: Record the timing in the module, measured not guessed**

Run:
```bash
uv run python -c "
import time
from pathlib import Path
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.recover import mask_and_solve
cfg=load_config(Path('config.yaml')); data=HarmonizedData.load(Path('data/staged'))
t=time.time(); mask_and_solve(data,[MaskTarget('41','2019-06','state_total','primary_like')],cfg)
print('one mask+rebuild+solve: %.2fs' % (time.time()-t))
"
```
Expected: well under 1 s (0.36 s at the time of writing). If it is seconds, stop and re-scope the
harness before continuing — the whole design assumes this arm is cheap.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/validate/recover.py tests/unit/test_validate_recover.py
git commit -m "feat(validate): mask_and_solve, the §13.2 step 5-6 rank-and-bound primitive"
```

---

### Task 6: §13.2 step 1 — the propensity model over public predictors only

**Files:**
- Create: `src/logging_employment/validate/propensity.py`
- Test: `tests/unit/test_validate_propensity.py`

**Interfaces:**
- Consumes: `validate.mask.eligible_targets`.
- Produces: `target_propensity(monthly, *, config) -> pl.DataFrame` with a `propensity` column;
  `sample_targets(monthly, *, n, seed, config) -> list[MaskTarget]`.

§13.2 names the predictors: "establishment count, parent share, employment per establishment,
historical volatility, and sparsity". **"Parent share" is unavailable and must not be faked** —
`qcew_monthly` carries industry 113310 only, so no parent 1133/113 state series exists to form a
share against. Implement the other four and record the omission in the docstring.

The propensity MUST be built from public predictors only: it may read establishment counts (which
are published even for employment-suppressed cells) and the *disclosed* employment history, never
the target's own held-out value.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_propensity.py
from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.propensity import sample_targets, target_propensity


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(Path("data/staged")).qcew_monthly


def test_propensity_is_defined_on_every_eligible_cell_and_nowhere_else():
    scored = target_propensity(_monthly(), config=load_config(Path("config.yaml")))
    assert scored.filter(pl.col("observation_status") != "observed").height == 0
    assert scored["propensity"].null_count() == 0
    assert scored["propensity"].min() >= 0.0


def test_small_cells_score_higher_than_large_ones():
    """§13.2's propensity must favour primary-like targets: small, sparse, concentrated."""
    scored = target_propensity(_monthly(), config=load_config(Path("config.yaml")))
    small = scored.sort("qtrly_establishments").head(200)["propensity"].mean()
    large = scored.sort("qtrly_establishments", descending=True).head(200)["propensity"].mean()
    assert small > large


def test_sampling_is_deterministic_for_a_seed():
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    a = sample_targets(monthly, n=10, seed=1024, config=cfg)
    b = sample_targets(monthly, n=10, seed=1024, config=cfg)
    c = sample_targets(monthly, n=10, seed=2048, config=cfg)
    assert a == b
    assert a != c


def test_no_predictor_reads_the_targets_own_employment_value():
    """§13.4 bullet 1, at selection time: perturbing a cell must not move its own propensity."""
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    base = target_propensity(monthly, config=cfg)
    poisoned = monthly.with_columns(
        pl.when((pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06"))
        .then(pl.col("employment_value") * 100)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    )
    after = target_propensity(poisoned, config=cfg)
    key = (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    assert base.filter(key)["propensity"].item() == after.filter(key)["propensity"].item()
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_propensity.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/propensity.py
"""§13.2 step 1: a configurable propensity over PUBLIC predictors only.

§13.2 names five predictors. Four are implemented. The fifth — "parent share" — is NOT, and is not
approximated: `qcew_monthly` carries industry 113310 alone, so there is no parent 1133 or 113 state
series to form a share against. Fabricating one from the national total would make the predictor a
function of the residual this harness is trying to score.

Every predictor below is computable from data that stays public when the target is hidden:
establishment counts are published even for employment-suppressed cells, and the volatility and
sparsity terms read the state's OTHER months, never the target month's own value.
"""

from __future__ import annotations

import polars as pl

from ..config import Config
from .mask import MaskTarget, eligible_targets


def target_propensity(monthly: pl.DataFrame, *, config: Config) -> pl.DataFrame:
    """A propensity in [0, 1] per eligible cell. Higher = more primary-like.

    The volatility term is LEAVE-ONE-OUT. A plain per-state mean and standard deviation would
    include the target's own month, so perturbing a cell's employment would move that cell's own
    propensity — a §13.4 bullet-1 violation at selection time, and one that a docstring claiming
    otherwise does not fix. Verified by the leakage test in this task: with the pooled statistics
    the perturbation test fails; with the sums below it passes.
    """
    eligible = eligible_targets(monthly)
    observed = monthly.filter(
        (pl.col("area_type") == "state") & (pl.col("observation_status") == "observed")
    )
    # Sums, not moments, so each row's own contribution can be subtracted back out.
    stats = observed.group_by("state_fips").agg(
        pl.col("employment_value").cast(pl.Float64).sum().alias("_sum"),
        (pl.col("employment_value").cast(pl.Float64) ** 2).sum().alias("_sumsq"),
        pl.len().alias("_n"),
    )
    max_n = stats["_n"].max()

    scored = (
        eligible.join(stats, on="state_fips", how="left")
        .with_columns(pl.col("employment_value").cast(pl.Float64).alias("_v"))
        .with_columns((pl.col("_n") - 1).alias("_n_loo"))
        .with_columns(
            ((pl.col("_sum") - pl.col("_v")) / pl.col("_n_loo").clip(lower_bound=1))
            .alias("_mean_loo")
        )
        .with_columns(
            (
                ((pl.col("_sumsq") - pl.col("_v") ** 2) / pl.col("_n_loo").clip(lower_bound=1))
                - pl.col("_mean_loo") ** 2
            )
            .clip(lower_bound=0.0)
            .sqrt()
            .alias("_sd_loo")
        )
        .with_columns(
            (pl.col("_sd_loo") / pl.col("_mean_loo").clip(lower_bound=1.0))
            .fill_null(0.0)
            .alias("_cv"),
            (1.0 - pl.col("_n_loo") / max_n).alias("_sparsity"),
            (1.0 / (1.0 + pl.col("qtrly_establishments").cast(pl.Float64))).alias("_small"),
        )
    )
    # `_epe` (employment per establishment) is NOT in the score: it is a function of the target's
    # own held-out value. It is dropped rather than reported, so no downstream stratification can
    # reach for it by accident.
    return scored.with_columns(
        (
            0.5 * pl.col("_small")
            + 0.3 * pl.col("_cv").clip(upper_bound=1.0)
            + 0.2 * pl.col("_sparsity")
        ).alias("propensity")
    ).drop("_sum", "_sumsq", "_n", "_v", "_n_loo", "_mean_loo", "_sd_loo")


def sample_targets(
    monthly: pl.DataFrame, *, n: int, seed: int, config: Config
) -> list[MaskTarget]:
    """Draw `n` primary-like targets without replacement, weighted by propensity."""
    scored = target_propensity(monthly, config=config)
    drawn = scored.sample(n=min(n, scored.height), with_replacement=False, shuffle=True, seed=seed)
    drawn = drawn.sort("propensity", descending=True)
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_propensity.py -v`
Expected: 4 passed. If `test_no_predictor_reads_the_targets_own_employment_value` fails, a
predictor entered the score that must not have — fix the score, never the test.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/propensity.py tests/unit/test_validate_propensity.py
git commit -m "feat(validate): §13.2 propensity over public predictors, parent share omitted"
```

> Deviation: the plan's `sample_targets` drew UNIFORMLY and then sorted by propensity, which
> reorders the output without changing which cells were drawn. Measured on D1: pool median 192
> establishments, uniform draw 188, weighted draw 32 — so `small_cell_biased`, whose only
> selector this is, would have been statistically identical to the random sanity check that
> §13.2 prohibits as the only design. `pl.DataFrame.sample` takes no weights, so the draw routes
> through `numpy.random.Generator.choice(p=...)` on the same seed.

---

### Task 7: §13.2 steps 2–4 and 8 — complementary-like cells and margin retention

**Files:**
- Modify: `src/logging_employment/validate/propensity.py` (add `complementary_partners`)
- Test: `tests/unit/test_validate_complementary.py`

**Interfaces:**
- Produces: `complementary_partners(monthly, target, *, n, seed) -> list[MaskTarget]` labelled
  `complementary_like`.

**Read this before implementing.** On the state-total arm, complementary masking has **no
identification content**. Every `state_total` cell is a single-cell component — measured, 4,716 of
4,716 — because `assert_no_national_employment_margin` implements SRC-QCEW-006's `decline`. There is
no subtraction relation for a complementary cell to defeat.

It is implemented anyway, because §13.2 step 8 requires primary-like and complementary-like cells to
be **scored separately** and INV-009 requires the labels. What the plan MUST NOT do is claim the
routine prevents recovery of a state total. Task 8 puts the identification claim where it is true.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_complementary.py
from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.propensity import complementary_partners
from logging_employment.validate.recover import mask_and_solve


def test_partners_share_the_targets_month_and_are_labelled_complementary():
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    partners = complementary_partners(monthly, target, n=2, seed=1024)
    assert len(partners) == 2
    assert all(p.reference_month == "2019-06" for p in partners)
    assert all(p.suppression_type == "complementary_like" for p in partners)
    assert all(p.state_fips != "41" for p in partners)


def test_a_complementary_mask_changes_nothing_about_state_total_identification():
    """The scoped negative, pinned. Complementary masking is inert on this arm — by construction.

    If this test ever fails, a national employment margin has appeared in the constraint system and
    SRC-QCEW-006's `decline` has been overturned somewhere. That is a finding, not a flake.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    partners = complementary_partners(data.qcew_monthly, target, n=2, seed=1024)
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"

    alone = mask_and_solve(data, [target], cfg)
    with_partners = mask_and_solve(data, [target, *partners], cfg)
    for system in (alone, with_partners):
        row = system.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
        assert row["bound_status"] == "unbounded"
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_complementary.py -v`
Expected: FAIL — `cannot import name 'complementary_partners'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/propensity.py  — append
def complementary_partners(
    monthly: pl.DataFrame, target: MaskTarget, *, n: int, seed: int
) -> list[MaskTarget]:
    """§13.2 step 3's complementary-like cells, in the target's own month.

    SCOPE, stated because the obvious reading is wrong: on the `state_total` arm this defeats no
    subtraction, because there is none. Measured 2026-09-07, all 4,716 state cells are single-cell
    components — `assert_no_national_employment_margin` is Stage 0's SRC-QCEW-006 `decline` in
    code. A masked state total is `unbounded` with and without partners.

    The partners are still required: §13.2 step 8 scores primary-like and complementary-like cells
    separately, and INV-009 reserves those labels for synthetic masks. Task 8's national-size arm
    is where a complementary mask actually changes identification.
    """
    same_month = eligible_targets(monthly).filter(
        (pl.col("reference_month") == target.reference_month)
        & (pl.col("state_fips") != target.state_fips)
    )
    drawn = same_month.sample(
        n=min(n, same_month.height), with_replacement=False, shuffle=True, seed=seed
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "complementary_like")
        for r in drawn.iter_rows(named=True)
    ]
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_complementary.py -v`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/propensity.py tests/unit/test_validate_complementary.py
git commit -m "feat(validate): complementary-like partners, with their inertness on state totals stated"
```

---

### Task 8: The national-size arm — where the exit criterion can actually fire

**Files:**
- Modify: `src/logging_employment/validate/mask.py` (add `apply_size_mask`)
- Modify: `src/logging_employment/validate/recover.py` (accept a size mask)
- Test: `tests/integration/test_validate_exact_recovery.py`

**Interfaces:**
- Produces: `apply_size_mask(data, classes) -> tuple[HarmonizedData, pl.DataFrame]` over
  `qcew_national_size`.

**This task exists because Stage 4's exit criterion cannot otherwise be satisfied.** "The harness
rejects a mask whose target remains exactly recoverable" can never fire on a state total — such a
test would pass vacuously forever. It fires here.

Measured 2026-09-07 over the eight March margins (2017-03 … 2024-03): masking each of the 37
observed size cells one at a time gives **6 `exactly_recoverable`, 31 `partially_identified`, 0
unbounded**. All 6 exact cases are in **2017-03**, the only March carrying zero real suppressions and
therefore the only "fully observed public component" §13.2 step 1 asks for. All 15 complementary
*pairs* inside 2017-03 fall back to `partially_identified` with the truth inside.

A status flip on a size cell is **not** "strictly weaker". `rows.size_support_rows` fires only for
suppressed classes, so the flip *adds* a hard bounded `size_support` range row. A mask on this arm
can therefore make a component **infeasible**, and `solve_bounds` raises. Handle the raise; do not
assume it cannot happen.

- [x] **Step 1: Confirm the population before writing code**

Run:
```bash
uv run python -c "
from pathlib import Path
import polars as pl
from logging_employment.contracts import HarmonizedData
d = HarmonizedData.load(Path('data/staged'))
s = d.qcew_national_size.filter(pl.col('industry_code')=='113310')
march = s.filter(pl.col('reference_month').str.ends_with('-03'))
print('march months :', sorted(march['reference_month'].unique().to_list()))
print('observed cells:', march.filter(pl.col('observation_status')=='observed').height)
print('columns      :', s.columns)   # size_class / employment, NOT size_code / employment_value
print('per month     :', march.group_by('reference_month').agg(
    (pl.col('observation_status')=='suppressed').sum().alias('suppressed')).sort('reference_month').to_dicts())
"
```
Expected: eight March months; the month with zero suppressions is the exact-recovery month. **If
that month is not 2017-03, use whichever month reports zero** — the plan's 2017-03 is a dated
measurement, not an invariant (anti-drift rule).

- [x] **Step 2: Write the failing test**

```python
# tests/integration/test_validate_exact_recovery.py
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.recover import mask_and_solve_size


def _fully_observed_march(data: HarmonizedData) -> str:
    size = data.qcew_national_size.filter(
        (pl.col("industry_code") == "113310") & (pl.col("reference_month").str.ends_with("-03"))
    )
    counts = size.group_by("reference_month").agg(
        (pl.col("observation_status") == "suppressed").sum().alias("n")
    )
    clean = counts.filter(pl.col("n") == 0)
    if clean.height == 0:
        pytest.skip("no fully observed March margin in this vintage")
    return clean["reference_month"].sort().to_list()[0]


def test_a_single_class_mask_on_a_clean_march_is_exactly_recoverable():
    """§13.2 step 6's rejection, on the ONLY arm where it can fire."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    month = _fully_observed_march(data)
    system, cell_id = mask_and_solve_size(data, month, n_classes=1, seed=1024, config=cfg)
    row = system.bounds.filter(pl.col("cell_id") == cell_id).row(0, named=True)
    assert row["bound_status"] == "exactly_recoverable"
    assert row["selected_lower"] == row["selected_upper"]


def test_a_complementary_pair_defeats_exact_recovery():
    """§13.2 step 3, where it has real content: two masked classes leave nullity > 0."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    month = _fully_observed_march(data)
    system, cell_id = mask_and_solve_size(data, month, n_classes=2, seed=1024, config=cfg)
    row = system.bounds.filter(pl.col("cell_id") == cell_id).row(0, named=True)
    assert row["bound_status"] == "partially_identified"
    assert row["selected_lower"] < row["selected_upper"]
```

- [x] **Step 3: Run it to verify it fails**

Run: `uv run pytest tests/integration/test_validate_exact_recovery.py -v`
Expected: FAIL — `cannot import name 'mask_and_solve_size'`

- [x] **Step 4: Implement**

```python
# src/logging_employment/validate/mask.py  — append
def apply_size_mask(
    data: HarmonizedData, reference_month: str, size_classes: Sequence[str]
) -> tuple[HarmonizedData, pl.DataFrame]:
    """Hide national size classes in one March margin.

    This is the arm on which §13.2 steps 3 and 6 have identification content: a March margin is a
    genuine multi-cell component, so masking one class is recoverable by subtraction and masking
    two is not.

    NOTE THE COLUMN NAMES. `qcew_national_size` does NOT share `qcew_monthly`'s vocabulary: it uses
    `size_class`, `employment` and `establishments` where the monthly table uses `size_code`,
    `employment_value` and `qtrly_establishments`, and it carries no `employment_raw`,
    `wages_raw` or `is_published_numeric_zero`. Writing the monthly names here silently masks
    nothing — the filter matches zero rows.
    """
    size = data.qcew_national_size
    selector = (
        (pl.col("reference_month") == reference_month)
        & (pl.col("industry_code") == "113310")
        & pl.col("size_class").is_in(list(size_classes))
    )
    chosen = size.filter(selector)
    if chosen.height != len(size_classes):
        raise ConceptViolationError(
            f"{len(size_classes)} size classes requested, {chosen.height} matched in "
            f"{reference_month}"
        )
    truth = chosen.select(
        "reference_month", "size_class", pl.col("employment").alias("truth")
    )
    masked = size.with_columns(
        pl.when(selector).then(None).otherwise(pl.col("employment")).alias("employment"),
        pl.when(selector).then(pl.lit("N")).otherwise(pl.col("disclosure_code"))
        .alias("disclosure_code"),
        pl.when(selector).then(pl.lit("suppressed")).otherwise(pl.col("observation_status"))
        .alias("observation_status"),
    )
    return dataclasses.replace(data, qcew_national_size=masked), truth
```

```python
# src/logging_employment/validate/recover.py  — append
def mask_and_solve_size(
    data: HarmonizedData, reference_month: str, *, n_classes: int, seed: int, config: Config
) -> tuple[MaskedSystem, str]:
    """Mask `n_classes` observed size classes in one March and solve. Returns the first cell_id.

    `solve_bounds` MAY raise: flipping a size cell to suppressed ADDS a hard `size_support` range
    row (`rows.size_support_rows` fires only for suppressed classes), so a mask on this arm can
    make the component infeasible. That is a legitimate outcome of a legitimate mask and the
    harness records it rather than crashing the run.
    """
    size = data.qcew_national_size.filter(
        (pl.col("industry_code") == "113310")
        & (pl.col("reference_month") == reference_month)
        & (pl.col("observation_status") == "observed")
    )
    drawn = size.sample(n=n_classes, with_replacement=False, shuffle=True, seed=seed)
    codes = drawn["size_class"].to_list()
    masked, truth = apply_size_mask(data, reference_month, codes)
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    target = result.bounds.filter(
        pl.col("cell_id").str.starts_with("national_size|")
        & pl.col("cell_id").str.contains(reference_month)
        & pl.col("cell_id").str.contains(codes[0])
    )
    return (
        MaskedSystem(result.bounds, result.components, built.constraint_set_hash, truth),
        target["cell_id"].item(),
    )
```

Import `apply_size_mask` from `.mask`. No size-code constant is needed: measured, the March
margin for 113310 carries only the individual classes (1-6 in 2017-03), and the total enters the
component as a separate `national_total` cell.

- [x] **Step 5: Run the tests**

Run: `uv run pytest tests/integration/test_validate_exact_recovery.py -v`
Expected: 2 passed. **This pair is Stage 4's exit criterion.** If the first test does not report
`exactly_recoverable`, the rejection has nothing to reject and the harness cannot claim to satisfy
§13.2 step 6 — stop and report rather than weakening the assertion.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/validate tests/integration/test_validate_exact_recovery.py
git commit -m "feat(validate): the national-size arm, where §13.2 step 6's rejection can fire"
```

> Deviation: the plan located the masked cell with `str.contains(size_class)` on `cell_id`, a
> pipe-joined key containing `113310` and `NAICS 2017` — a one-character class matched 6 cells
> where 1 was wanted and `.item()` raised. Looks the cell up on the cells table's own
> `size_class` column instead. Verified non-vacuous on 2017-03: k=1 -> exactly_recoverable
> [12144, 12144] truth 12144; k=2 -> partially_identified [8910, 16038] truth 11823 inside.

---

### Task 9: §13.4 leakage controls, as executable guards

**Files:**
- Create: `src/logging_employment/validate/leakage.py`
- Test: `tests/integration/test_validate_leakage.py`

**Interfaces:**
- Produces: `assert_no_retained_truth(masked, truth)`,
  `assert_no_future_rows(frame, *, origin)`, `assert_estimates_invariant_to_truth(...)`.

§13.4's five bullets are currently prose. This task makes three of them executable; the other two
(feature normalization fit only on training information; final revisions excluded from real-time
tests) have no surface to bind to until Stage 5 and a second vintage exist, and are recorded as
such rather than faked.

The **perturbation guard** is the important one. Today's ten estimators are leak-safe only because
they all happen to read `context.partitions` rather than `context.monthly` — measured, the only
`context.monthly` reads are `historical.py:137,138`, `fallback.py:91` and `simple.py:31`, none of
which touch a masked state value. That is a coincidence of the current registry, not a property of
the design. The first Stage 5 or Stage 7 estimator that reaches for `context.monthly` breaks it, and
nothing in the suite would notice. This test converts the coincidence into a guard.

- [x] **Step 1: Write the failing test**

```python
# tests/integration/test_validate_leakage.py
import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY, run_baselines
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.leakage import (
    assert_no_future_rows,
    assert_no_retained_truth,
)
from logging_employment.validate.mask import MaskTarget, apply_mask


def test_no_column_of_the_masked_frame_retains_a_held_out_value():
    data = HarmonizedData.load(Path("data/staged"))
    masked, truth = apply_mask(
        data, [MaskTarget("41", "2019-06", "state_total", "primary_like")]
    )
    assert_no_retained_truth(masked, truth)


def test_a_rolling_origin_frame_carrying_a_future_row_is_refused():
    data = HarmonizedData.load(Path("data/staged"))
    with pytest.raises(AssertionError, match="future"):
        assert_no_future_rows(data.qcew_monthly, origin="2020-01")


def test_every_estimator_is_invariant_to_the_held_out_value():
    """§13.4 bullet 1, as a regression guard rather than a happy coincidence.

    Hold the mask fixed, change the truth underneath it, and require identical estimates. An
    estimator that reads `context.monthly` for a masked cell fails this and should.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")

    masked_a, _ = apply_mask(data, [target])
    poisoned = data.qcew_monthly.with_columns(
        pl.when((pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06"))
        .then(pl.col("employment_value") * 7)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    )
    masked_b, _ = apply_mask(dataclasses.replace(data, qcew_monthly=poisoned), [target])

    subset = REGISTRY[:4]
    a, _ = run_baselines(masked_a, cfg, estimators=subset)
    b, _ = run_baselines(masked_b, cfg, estimators=subset)
    key = ["estimator_id", "cell_id"]
    assert a.sort(key).select("estimate").equals(b.sort(key).select("estimate"))
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/integration/test_validate_leakage.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/leakage.py
"""§13.4's leakage controls, as executable guards.

Three of the five bullets bind today. The other two are recorded as unbindable rather than faked:
"feature normalization and hyperparameter selection are fit only on the training information set"
has no fitted feature pipeline until Stage 5, and "final revisions are excluded from real-time
tests" has no second vintage to exclude (measured 2026-09-07: no period in any staged table carries
a second snapshot).
"""

from __future__ import annotations

import polars as pl

from ..contracts import HarmonizedData


def assert_no_retained_truth(masked: HarmonizedData, truth: pl.DataFrame) -> None:
    """§13.4 bullet 1: no direct copy or derived feature retains the held-out value."""
    for row in truth.iter_rows(named=True):
        cell = masked.qcew_monthly.filter(
            (pl.col("state_fips") == row["state_fips"])
            & (pl.col("reference_month") == row["reference_month"])
        )
        if cell.height == 0:
            continue
        withheld = str(row["truth"])
        for column, value in cell.row(0, named=True).items():
            assert str(value) != withheld, (
                f"{column} on {row['state_fips']}/{row['reference_month']} retains the held-out "
                f"value {withheld}"
            )


def assert_no_future_rows(frame: pl.DataFrame, *, origin: str) -> None:
    """§13.4 bullet 3: a rolling-origin frame contains no period at or after the origin.

    This guard, not the mask, is what Stage 4's exit criterion "a rolling-origin run provably
    contains no future-period rows" is about — a mask hides values, it does not remove rows.
    """
    future = frame.filter(pl.col("reference_month") >= origin)
    assert future.height == 0, (
        f"{future.height} future rows at or after origin {origin}: "
        f"{sorted(future['reference_month'].unique().to_list())[:5]}"
    )
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/integration/test_validate_leakage.py -v`
Expected: 3 passed. The third takes roughly 2 × the four-rung cost (~12 s).

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/leakage.py tests/integration/test_validate_leakage.py
git commit -m "feat(validate): §13.4 leakage guards, including the truth-invariance regression test"
```

> Deviation: the Interfaces block names `assert_estimates_invariant_to_truth`; Step 3 defines two
> functions and the test imports two. The third bullet is a registry property, so it stays a
> test. The plan's invariance test compares frames that are BYTE-IDENTICAL after masking, so it
> cannot catch "an estimator read `context.monthly`" — under a frame mask that IS the masked
> frame. Docstring corrected to what it does catch, and a structural guard added for the
> partition leak of evidence §3. `assert_no_retained_truth` also fired on real data:
> `aggregation_level` is the QCEW code '58' and cell 17/2021-06 has 58 employees, so it is scoped
> to exclude columns QCEW publishes FOR suppressed cells, new columns checked by default.

---

### Task 10: §13.3 regimes — the six mask-population designs

**Files:**
- Create: `src/logging_employment/validate/regimes.py`
- Test: `tests/unit/test_validate_regimes.py`

**Interfaces:**
- Produces: `RegimeSpec(name, disposition, grain, select)` and `REGIME_SPECS: dict[str, RegimeSpec]`;
  `select_targets(regime, monthly, *, seed, config) -> list[MaskTarget]`.

Six regimes are implementable directly against the panel: `small_cell_biased`,
`concentration_proxy`, `clustered_states_within_month`, `long_consecutive_runs`,
`whole_state_year_blocks`, `whole_seasonal_blocks`. `regional_blocks` needs a decision first — see
Step 4.

**Three panel facts go into the generator, not into its discoverer.** Measured 2026-09-07:

```text
fully observed state-years (all 12 months observed):   272
states in qcew_monthly:                                 50
states never observed in any month:                      6   (02, 10, 15, 32, 38, 50)
states with at least one >=12-month observed run:       40
DC rows in qcew_monthly:                                 0   (config says states_dc)
```

- The six never-observed states can **never** be a target and their cells must never be reported as
  scored. They are why the share family shows `establishment_fallback` in 96 of 96 months.
- A state-year block regime draws from the **272 complete state-years**, not from all 400.
- A long-run regime draws from the **40** states that have a run, or it silently produces short
  blocks.
- DC's absence against `config.project.geography_universe = 'states_dc'` is an **open Stage 0 item**.
  Cite it in the docstring; do not re-derive it and do not "fix" it here.

**Mask grain is a required field, not an afterthought.** History contamination is what separates
these regimes: `long_consecutive_runs` and `whole_state_year_blocks` *intend* a blackout, while
`small_cell_biased` and `clustered_states_within_month` do not and must rotate the target across
months so no state is masked inside its own lookback. `RegimeSpec.grain` records which, and
`select_targets` asserts the non-blackout regimes leave at least
`config.validation.minimum_unmasked_lookback_months` months unmasked.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_regimes.py
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HOLDOUT_REGIMES, HarmonizedData
from logging_employment.validate.regimes import REGIME_SPECS, select_targets


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(Path("data/staged")).qcew_monthly


def test_every_spec_declares_a_grain_and_a_disposition():
    assert set(REGIME_SPECS) == set(HOLDOUT_REGIMES)
    for spec in REGIME_SPECS.values():
        assert spec.grain in {"single_month", "blackout"}
        assert spec.disposition in {"feasible", "vacuous_on_registry", "cannot_run_on_d1"}


@pytest.mark.parametrize(
    "regime",
    [
        "small_cell_biased",
        "concentration_proxy",
        "clustered_states_within_month",
        "long_consecutive_runs",
        "whole_state_year_blocks",
        "whole_seasonal_blocks",
    ],
)
def test_a_feasible_regime_selects_only_eligible_targets(regime):
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    targets = select_targets(regime, monthly, seed=1024, config=cfg)
    assert targets, f"{regime} selected nothing"
    keys = {(t.state_fips, t.reference_month) for t in targets}
    chosen = monthly.filter(
        pl.struct("state_fips", "reference_month").is_in(
            [{"state_fips": s, "reference_month": m} for s, m in keys]
        )
    )
    assert chosen.filter(pl.col("observation_status") != "observed").height == 0
    assert chosen.filter(pl.col("qtrly_establishments") <= 0).height == 0


def test_a_never_observed_state_is_never_selected():
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    never = {"02", "10", "15", "32", "38", "50"}
    for regime in REGIME_SPECS:
        if REGIME_SPECS[regime].disposition != "feasible":
            continue
        for t in select_targets(regime, monthly, seed=1024, config=cfg):
            assert t.state_fips not in never


def test_a_single_month_regime_leaves_lookback_history_unmasked():
    """The blackout distinction: a small-cell mask must not erase its own share history."""
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    targets = select_targets("small_cell_biased", monthly, seed=1024, config=cfg)
    per_state: dict[str, int] = {}
    for t in targets:
        per_state[t.state_fips] = per_state.get(t.state_fips, 0) + 1
    # No state may lose more months than its lookback can absorb.
    assert max(per_state.values()) <= 96 - cfg.validation.minimum_unmasked_lookback_months
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_regimes.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement the six selectors**

```python
# src/logging_employment/validate/regimes.py
"""§13.3's holdout regimes.

Three panel facts are declared here rather than discovered at run time, because a generator that
discovers them silently produces the wrong mask. Measured 2026-09-07 on the D1 window: 272 of 400
state-years are fully observed; 6 of 50 states are never observed in any month and can never be a
target; 40 states carry at least one >=12-month observed run. `qcew_monthly` contains no DC rows
while `config.project.geography_universe` is `states_dc` — an open Stage 0 item, cited not fixed.

All three are DATED MEASUREMENTS. Recompute them at run time and assert on structure; a revision
moves every one of them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import polars as pl

from ..config import Config
from ..contracts import HOLDOUT_REGIMES, REGIME_DISPOSITIONS
from .mask import MaskTarget, eligible_targets
from .propensity import sample_targets, target_propensity


@dataclass(frozen=True)
class RegimeSpec:
    """One §13.3 regime: how it selects, at what grain, and whether it can run at all."""

    name: str
    disposition: str
    # "blackout" regimes INTEND to erase a state's history; "single_month" regimes must not.
    grain: str
    select: Callable[[pl.DataFrame, int, Config], list[MaskTarget]] | None


def _small_cell(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    return sample_targets(monthly, n=config.validation.replicates_per_regime, seed=seed,
                          config=config)


def _concentration(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """High employees-per-establishment. Computed on the CANDIDATE POOL, never as a score input."""
    pool = eligible_targets(monthly).with_columns(
        (
            pl.col("employment_value").cast(pl.Float64)
            / pl.col("qtrly_establishments").cast(pl.Float64)
        ).alias("_epe")
    )
    drawn = pool.sort("_epe", descending=True).head(config.validation.replicates_per_regime * 3)
    drawn = drawn.sample(
        n=min(config.validation.replicates_per_regime, drawn.height),
        with_replacement=False, shuffle=True, seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _clustered(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Several states inside ONE month — the regime that stresses the residual, not the history."""
    pool = eligible_targets(monthly)
    month = pool.select("reference_month").unique().sample(n=1, seed=seed)["reference_month"].item()
    inside = pool.filter(pl.col("reference_month") == month)
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False, shuffle=True, seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], month, "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _long_run(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """A >=12-month consecutive blackout. Draws only from states that HAVE such a run."""
    pool = eligible_targets(monthly).sort("state_fips", "reference_month")
    runs: list[tuple[str, list[str]]] = []
    for (state,), group in pool.group_by("state_fips", maintain_order=True):
        months = group["reference_month"].to_list()
        current: list[str] = []
        for month in months:
            if current and _is_next_month(current[-1], month):
                current.append(month)
            else:
                current = [month]
            if len(current) >= 12:
                runs.append((str(state), list(current[-12:])))
                break
    if not runs:
        return []
    index = seed % len(runs)
    state, months = runs[index]
    return [MaskTarget(state, m, "state_total", "primary_like") for m in months]


def _state_year(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """A whole calendar year for one state, drawn only from FULLY OBSERVED state-years."""
    pool = eligible_targets(monthly).with_columns(
        pl.col("reference_month").str.slice(0, 4).alias("_year")
    )
    complete = (
        pool.group_by("state_fips", "_year")
        .agg(pl.len().alias("_n"))
        .filter(pl.col("_n") == 12)
    )
    if complete.height == 0:
        return []
    pick = complete.sample(n=1, seed=seed).row(0, named=True)
    chosen = pool.filter(
        (pl.col("state_fips") == pick["state_fips"]) & (pl.col("_year") == pick["_year"])
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]


def _seasonal(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """One calendar month across every eligible state-year — the seasonal blackout."""
    pool = eligible_targets(monthly).with_columns(
        pl.col("reference_month").str.slice(5, 2).alias("_mm")
    )
    mm = pool.select("_mm").unique().sort("_mm").sample(n=1, seed=seed)["_mm"].item()
    chosen = pool.filter(pl.col("_mm") == mm)
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]


def _is_next_month(previous: str, candidate: str) -> bool:
    py, pm = int(previous[:4]), int(previous[5:])
    cy, cm = int(candidate[:4]), int(candidate[5:])
    return (cy, cm) == (py + 1, 1) if pm == 12 else (cy, cm) == (py, pm + 1)


_SELECTORS: dict[str, Callable[[pl.DataFrame, int, Config], list[MaskTarget]]] = {
    "small_cell_biased": _small_cell,
    "concentration_proxy": _concentration,
    "clustered_states_within_month": _clustered,
    "long_consecutive_runs": _long_run,
    "whole_state_year_blocks": _state_year,
    "whole_seasonal_blocks": _seasonal,
}

_GRAINS: dict[str, str] = {
    "long_consecutive_runs": "blackout",
    "whole_state_year_blocks": "blackout",
    "whole_seasonal_blocks": "blackout",
    "regional_blocks": "blackout",
}

REGIME_SPECS: dict[str, RegimeSpec] = {
    name: RegimeSpec(
        name=name,
        disposition=REGIME_DISPOSITIONS[name],
        grain=_GRAINS.get(name, "single_month"),
        select=_SELECTORS.get(name),
    )
    for name in HOLDOUT_REGIMES
}


def select_targets(
    regime: str, monthly: pl.DataFrame, *, seed: int, config: Config
) -> list[MaskTarget]:
    """Targets for one regime, or a refusal explaining why the regime cannot produce any."""
    spec = REGIME_SPECS[regime]
    if spec.disposition == "cannot_run_on_d1":
        raise NotImplementedError(
            f"{regime} cannot run on this window: no period in any staged table carries a second "
            "snapshot, so there is no preliminary vintage to compare against a final one. Turn "
            "`validation.include_vintage_comparison` off, or ingest a second vintage in Stage 1."
        )
    if spec.select is None:
        return []
    targets = spec.select(monthly, seed, config)
    if spec.grain == "single_month":
        floor = config.validation.minimum_unmasked_lookback_months
        per_state: dict[str, int] = {}
        for t in targets:
            per_state[t.state_fips] = per_state.get(t.state_fips, 0) + 1
        total_months = monthly["reference_month"].n_unique()
        for state, count in per_state.items():
            if total_months - count < floor:
                raise ValueError(
                    f"{regime} would mask {count} of {total_months} months for state {state}, "
                    f"leaving fewer than {floor} lookback months. A single-month regime must not "
                    "black out a state's own history — that is what the blackout regimes are for."
                )
    return targets
```

- [x] **Step 4: Decide the regional scheme — a required, cited decision**

`regional_blocks` needs a region definition, and **the same concept is consumed in four places**:
this regime, §13.6's state-share error strata, §13.7's required "calibration by ... region", and
Stage 5's exit criterion "the §17.5 synthetic recovery test passes for ... region effects". If
Stage 4 invents one privately, Stage 5 will invent a different one.

Ship it as one named constant with a citation. **Recommended: the 9 Census divisions**, not the 4
Census regions — with 50 states and 34–40 observed per month, 4 regions give 12–13 states per block
and collide with the mask-fraction ceiling, while 9 divisions give 4–7 states each.

Add to `regimes.py`. Verified 2026-09-07: these nine keys partition `constants.STATES_DC_FIPS`
exactly — 51 codes, no gaps, no overlap, 3–9 states per division.

```python
# The nine Census divisions (U.S. Census Bureau statistical divisions). ONE scheme, named once,
# because §13.6's state-share strata, §13.7's required calibration-by-region, and Stage 5's
# §17.5 region effects must all partition on the SAME thing this regime masks on. Divisions
# rather than the four Census regions: 4 regions give 12-13 states per block against 34-40
# observed states per month, which masks a third of the disclosed set in one replicate.
CENSUS_DIVISIONS: dict[str, tuple[str, ...]] = {
    "new_england": ("09", "23", "25", "33", "44", "50"),
    "middle_atlantic": ("34", "36", "42"),
    "east_north_central": ("17", "18", "26", "39", "55"),
    "west_north_central": ("19", "20", "27", "29", "31", "38", "46"),
    "south_atlantic": ("10", "11", "12", "13", "24", "37", "45", "51", "54"),
    "east_south_central": ("01", "21", "28", "47"),
    "west_south_central": ("05", "22", "40", "48"),
    "mountain": ("04", "08", "16", "30", "32", "35", "49", "56"),
    "pacific": ("02", "06", "15", "41", "53"),
}


def _regional(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """One Census division's eligible states, in one month."""
    names = sorted(CENSUS_DIVISIONS)
    division = names[seed % len(names)]
    pool = eligible_targets(monthly).filter(
        pl.col("state_fips").is_in(list(CENSUS_DIVISIONS[division]))
    )
    if pool.height == 0:
        return []
    month = pool.select("reference_month").unique().sort("reference_month").sample(
        n=1, seed=seed
    )["reference_month"].item()
    chosen = pool.filter(pl.col("reference_month") == month)
    return [
        MaskTarget(r["state_fips"], month, "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]
```

Register it: `_SELECTORS["regional_blocks"] = _regional`.

Add a test pinning the partition, so a hand-edited division list cannot silently drop a state:

```python
def test_the_census_divisions_partition_the_state_universe():
    from logging_employment.constants import STATES_DC_FIPS
    from logging_employment.validate.regimes import CENSUS_DIVISIONS

    flat = [f for members in CENSUS_DIVISIONS.values() for f in members]
    assert len(flat) == len(set(flat)), "a state appears in two divisions"
    assert set(flat) == set(STATES_DC_FIPS)
```

- [x] **Step 5: Run the tests**

Run: `uv run pytest tests/unit/test_validate_regimes.py -v`
Expected: all pass.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/validate/regimes.py tests/unit/test_validate_regimes.py
git commit -m "feat(validate): the six mask-population regimes and the declared regional scheme"
```

---

### Task 11: §13.3's temporal regimes and their honest dispositions

**Files:**
- Modify: `src/logging_employment/validate/regimes.py`
- Test: `tests/unit/test_validate_temporal_regimes.py`

**Interfaces:**
- Produces: `rolling_origin_frames(monthly, *, origins) -> Iterator[tuple[str, pl.DataFrame]]`.

**Rolling-origin ships; retrospective smoothing does not.** Both facts are recorded, because a
silent omission and a silent no-op are indistinguishable from a passing test.

`rolling_origin` is required by Stage 4's exit criterion — "a rolling-origin run provably contains
no future-period rows" — and the proof is the `assert_no_future_rows` guard from Task 9 applied to a
**truncated frame**, not to a mask. A mask hides values; only truncation removes rows.

It must also be reported honestly: **no Stage 3 estimator distinguishes a rolling-origin holdout
from a plain one**, because none of them reads a future period. The regime is not discriminating
today. It becomes discriminating when Stage 5's model lands — which is exactly why the harness must
exist first. The scoreboard states this, so a reader does not read "no difference" as a defect.

`retrospective_smoothing` is `vacuous_on_registry`: §10 declares no smoothing estimator, and adding
one would be a new baseline outside §10's set and outside this stage. **Surface it as a scope
decision; do not quietly implement one.**

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_temporal_regimes.py
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.leakage import assert_no_future_rows
from logging_employment.validate.regimes import REGIME_SPECS, rolling_origin_frames


def test_every_rolling_origin_frame_is_provably_past_only():
    """Stage 4's exit criterion, as an assertion over the truncated frame."""
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    for origin, frame in rolling_origin_frames(monthly, origins=["2020-01", "2022-01"]):
        assert_no_future_rows(frame, origin=origin)
        assert frame.height < monthly.height


def test_retrospective_smoothing_is_declared_vacuous_not_silently_skipped():
    spec = REGIME_SPECS["retrospective_smoothing"]
    assert spec.disposition == "vacuous_on_registry"
    assert spec.select is None
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_temporal_regimes.py -v`
Expected: FAIL — `cannot import name 'rolling_origin_frames'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/regimes.py  — append
def rolling_origin_frames(
    monthly: pl.DataFrame, *, origins: Sequence[str]
) -> Iterator[tuple[str, pl.DataFrame]]:
    """§13.3's rolling-origin design: one past-only frame per origin.

    TRUNCATION, not masking. A mask nulls a value and leaves the row; the exit criterion asks that
    the run "provably contains no future-period rows", which only removing them can satisfy.

    Reported scope: measured 2026-09-07, no §10 estimator reads a future period, so this regime
    does not separate any Stage 3 baseline. It is built now because Stage 5's model will, and
    because the guard is what makes that claim checkable rather than assumed.
    """
    for origin in origins:
        yield origin, monthly.filter(pl.col("reference_month") < origin)
```

Add `from collections.abc import Iterator, Sequence` to the imports.

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_temporal_regimes.py -v`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/regimes.py tests/unit/test_validate_temporal_regimes.py
git commit -m "feat(validate): rolling-origin truncation, and smoothing declared vacuous"
```

---

### Task 12: Structural break, NAICS transition, the vintage refusal, and CBP size gaps

**Files:**
- Modify: `src/logging_employment/validate/regimes.py`
- Modify: `config.yaml` (declared break windows)
- Test: `tests/unit/test_validate_declared_regimes.py`

**Break windows are DECLARED, not detected.** A detector would be a research project inside a
validation stage, and the national series does not separate COVID from seasonality cleanly enough to
justify one. Recommended declared set:

```yaml
  structural_break_windows:
    - ["2020-03", "2020-06"]   # COVID; the 2020-04 national move is -5.4%
    - ["2021-10", "2022-03"]   # the NAICS boundary window
```

The second overlaps `naics_transition`. **Score it under one label, not both** — double-counting a
window inflates whichever metric family it lands in.

If a future item does want a per-cell detector, note that it would require refactoring
`BreakAdjustedShare._reduce` to return its cut alongside the median. **The tie rule — "the earliest
tied step wins", R-BREAK-5 — is a declared contract Stage 4 inherits and MUST NOT re-litigate.**

**The NAICS transition regime must read `weight_basis_counts`, not decline counts.** The seam is
2021-12/2022-01 by construction (`vintage_for_year` returns "NAICS 2022" at year ≥ 2022), and with
`historical_may_cross_naics_vintage: false` plus a 24-month lookback the share family loses its
entire history there. Measured, 2022-01/02/03 have **zero** own-arm rows across all five §10.3
variants — so all five emit `establishment_proportional`'s number under five labels. Because
composition emits no `decline_kind`, that is invisible to §13.8's decline-by-kind report.

**Regime 12 refuses.** `preliminary_to_final_vintage` raises (Task 10's `select_targets`), and the
config default is `false`. A regime that cannot run MUST NOT emit an empty metrics partition — an
empty partition reads as "scored, nothing wrong".

**Regime 13 is scored through estimator declines, not through bounds.** `cbp_state_size` feeds only
`baselines/fallback.py`'s `intensity_rows`, which filters to the all-establishments size code; no
CBP value enters the constraint system at all. So masking CBP size classes changes `cbp_intensity`'s
availability and nothing else.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_declared_regimes.py
from pathlib import Path

import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.regimes import REGIME_SPECS, select_targets


def test_the_vintage_regime_refuses_rather_than_returning_nothing():
    """An empty partition would read as 'scored, nothing wrong'. It must raise."""
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    with pytest.raises(NotImplementedError, match="second snapshot"):
        select_targets("preliminary_to_final_vintage", monthly, seed=1024, config=cfg)


def test_the_config_default_agrees_with_the_data():
    assert load_config(Path("config.yaml")).validation.include_vintage_comparison is False


def test_the_naics_transition_regime_targets_the_measured_seam():
    monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
    cfg = load_config(Path("config.yaml"))
    targets = select_targets("naics_transition", monthly, seed=1024, config=cfg)
    assert targets
    assert all("2021" in t.reference_month or "2022" in t.reference_month for t in targets)


def test_break_windows_are_declared_in_config_not_detected():
    cfg = load_config(Path("config.yaml"))
    windows = cfg.validation.structural_break_windows
    assert len(windows) >= 1
    assert all(len(w) == 2 for w in windows)
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_declared_regimes.py -v`
Expected: FAIL — `structural_break_windows` is not on `ValidationConfig`.

- [x] **Step 3: Implement**

Add to `ValidationConfig` (Task 1):

```python
    structural_break_windows: list[tuple[str, str]] = [
        ("2020-03", "2020-06"),
        ("2021-10", "2022-03"),
    ]
    naics_seam_month: str = "2022-01"
    naics_seam_halfwidth_months: int = 3
```

Add the two selectors to `regimes.py`:

```python
def _structural_break(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Targets inside a DECLARED break window.

    Declared, not detected. A per-cell break detector inside a validation stage is a research
    project, and the national series does not separate COVID from seasonality cleanly enough to
    justify one. The second window overlaps `naics_transition`; score a month under ONE label.
    """
    windows = config.validation.structural_break_windows
    pool = eligible_targets(monthly)
    inside = pool.filter(
        pl.any_horizontal(
            [
                (pl.col("reference_month") >= lo) & (pl.col("reference_month") <= hi)
                for lo, hi in windows
            ]
        )
    )
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False, shuffle=True, seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _naics_transition(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Targets straddling the NAICS 2017 -> 2022 seam.

    The seam is 2021-12/2022-01 BY CONSTRUCTION: `harmonize.naics.vintage_for_year` returns
    "NAICS 2022" at year >= 2022, so `naics_vintage` is a derived column. This regime tests our own
    vintage rule, not a source-published break, and the scoreboard must say so.

    Scoring note: with `historical_may_cross_naics_vintage: false` and a 24-month lookback the
    share family has ZERO own-arm rows in 2022-01..03 — all five §10.3 variants emit
    `establishment_proportional`'s number under five labels. That composition emits no
    `decline_kind`, so it is invisible to §13.8's decline-by-kind report. Read
    `weight_basis_counts`.
    """
    seam = config.validation.naics_seam_month
    half = config.validation.naics_seam_halfwidth_months
    months = sorted(monthly["reference_month"].unique().to_list())
    if seam not in months:
        return []
    centre = months.index(seam)
    window = set(months[max(0, centre - half) : centre + half + 1])
    inside = eligible_targets(monthly).filter(pl.col("reference_month").is_in(list(window)))
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False, shuffle=True, seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]
```

Register `_structural_break` and `_naics_transition` in `_SELECTORS`. Leave
`preliminary_to_final_vintage` OUT of `_SELECTORS` so `select_targets` raises.

`cbp_size_gaps` masks CBP rows rather than QCEW cells, so it returns no `MaskTarget`; it returns
the CBP keys to blank. Measured: `cbp_state_size` feeds only `baselines/fallback.py`'s
`intensity_rows`, which filters to the all-establishments size code, and no CBP value enters the
constraint system at all — so this regime changes `cbp_intensity`'s availability and nothing else.
It is scored through estimator declines, not through bounds.

```python
def cbp_size_gap_keys(
    data: HarmonizedData, *, seed: int, config: Config
) -> list[tuple[str, int]]:
    """(state_fips, reference_year) pairs whose CBP size rows this regime removes.

    Returns CBP keys, NOT `MaskTarget`s: no QCEW cell is hidden here. The only consumer of
    `cbp_state_size` in the estimation path is `intensity_rows`, so removing a state-year turns
    §10.4 from an own-arm estimator into a declining one for that state-year and leaves every
    other estimator untouched. That difference IS the metric.
    """
    pool = data.cbp_state_size.select("state_fips", "reference_year").unique()
    drawn = pool.sample(
        n=min(config.validation.replicates_per_regime, pool.height),
        with_replacement=False, shuffle=True, seed=seed,
    )
    return [(r["state_fips"], r["reference_year"]) for r in drawn.iter_rows(named=True)]


def apply_cbp_gap(data: HarmonizedData, keys: Sequence[tuple[str, int]]) -> HarmonizedData:
    """Drop the named CBP state-years so §10.4 must fall back or decline."""
    if not keys:
        return data
    selector = pl.struct("state_fips", "reference_year").is_in(
        [{"state_fips": s, "reference_year": y} for s, y in keys]
    )
    return dataclasses.replace(
        data, cbp_state_size=data.cbp_state_size.filter(~selector)
    )
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_declared_regimes.py -v`
Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/regimes.py config.yaml tests/unit/test_validate_declared_regimes.py
git commit -m "feat(validate): declared break windows, the NAICS seam, and the vintage refusal"
```

> Deviation: `REGIME_SPECS` is a dict comprehension over `_SELECTORS.get(name)`, so registering
> the two selectors afterwards would not have reached the specs — `structural_break` and
> `naics_transition` would have kept `select=None` and returned `[]` for a regime declared
> feasible. `REGIME_SPECS` is rebuilt after registration.

---

### Task 13: §13.5 deterministic-bound metrics, emitted as vacuous where they are vacuous

**Files:**
- Create: `src/logging_employment/validate/metrics.py`
- Test: `tests/unit/test_validate_metrics_bounds.py`

**Interfaces:**
- Produces: `bound_metrics(scores, *, regime, seed, arm) -> pl.DataFrame`.

§13.5 asks for five things: feasible width, truth-in-bound rate, exact-recovery rate,
infeasible-component rate, and LP-vs-MILP tightening. **On the state-total arm four of the five carry
no information**, and the plan's job is to emit that fact rather than emit numbers that read like
results:

| metric | on `state_total` | why |
|---|---|---|
| feasible width | **null** | `selected_upper` is null; a width of `inf` is not a measurement |
| truth-in-bound rate | 1.0, uninformative | `[0, +inf)` contains every truth trivially |
| exact-recovery rate | 0.0, uninformative | no state cell is ever exactly recoverable |
| LP vs MILP tightening | **null** | `milp_lower`/`milp_upper` are null; nothing to compare |
| infeasible-component rate | 0.0 | singleton components cannot be infeasible |

Every row therefore carries `bound_cells_finite_upper`, so a reader can tell a real 1.0 from a
vacuous one. On the `national_size` arm all five are informative.

**The truth-in-bound predicate must handle the null upper explicitly:**
`lower <= truth AND (upper IS NULL OR truth <= upper)`. A naive `truth <= upper` drops every row to
null; a `fill_null(0)` fails every row. Both are silent.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_metrics_bounds.py
import polars as pl

from logging_employment.validate.metrics import bound_metrics


def _scores(upper):
    return pl.DataFrame(
        {
            "estimator_id": ["equal_residual"] * 2,
            "cell_id": ["a", "b"],
            "truth": [100.0, 200.0],
            "selected_lower": [0.0, 0.0],
            "selected_upper": upper,
            "bound_status": ["unbounded", "unbounded"],
        }
    )


def test_a_null_upper_bound_counts_as_containing_the_truth():
    """`[0, +inf)` contains everything. A naive `truth <= upper` would drop both rows."""
    out = bound_metrics(_scores([None, None]), regime="small_cell_biased", seed=1, arm="state_total")
    rate = out.filter(pl.col("metric_name") == "truth_in_bound_rate")["value"].item()
    assert rate == 1.0


def test_a_vacuous_arm_is_flagged_by_finite_upper_count():
    out = bound_metrics(_scores([None, None]), regime="small_cell_biased", seed=1, arm="state_total")
    assert out["bound_cells_finite_upper"].unique().to_list() == [0]
    width = out.filter(pl.col("metric_name") == "mean_feasible_width")["value"].item()
    assert width is None, "an infinite width must be null, not inf and not 0"


def test_a_finite_upper_bound_produces_a_real_width():
    out = bound_metrics(
        _scores([150.0, 500.0]), regime="cbp_size_gaps", seed=1, arm="national_size"
    )
    assert out["bound_cells_finite_upper"].unique().to_list() == [2]
    width = out.filter(pl.col("metric_name") == "mean_feasible_width")["value"].item()
    assert width == 425.0
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_metrics_bounds.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/metrics.py
"""§13.5-13.8's metric families, each carrying the denominator it was computed over.

Read the vacuity note before trusting a §13.5 number. On the `state_total` arm every masked cell is
`unbounded` with `selected_upper = null`, so a truth-in-bound rate of 1.0 means "[0, +inf) contains
the truth", not "the bounds were informative". `bound_cells_finite_upper` is what separates the
two, and it is on every row for that reason.
"""

from __future__ import annotations

import polars as pl


def bound_metrics(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.5's five metrics, per estimator, with vacuity made visible."""
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        finite = group.filter(pl.col("selected_upper").is_not_null())
        n_finite = finite.height

        contained = group.filter(
            (pl.col("selected_lower") <= pl.col("truth"))
            & (pl.col("selected_upper").is_null() | (pl.col("truth") <= pl.col("selected_upper")))
        ).height
        exact = group.filter(pl.col("bound_status") == "exactly_recoverable").height
        width = (
            (finite["selected_upper"] - finite["selected_lower"]).mean() if n_finite else None
        )

        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": str(estimator),
            "metric_family": "deterministic_bounds",
            "denominator": float(group.height),
            "denominator_basis": "masked_cells",
            "n_scored": group.height,
            "bound_cells_finite_upper": n_finite,
        }
        rows.append({**base, "metric_name": "truth_in_bound_rate",
                     "value": contained / group.height if group.height else None})
        rows.append({**base, "metric_name": "exact_recovery_rate",
                     "value": exact / group.height if group.height else None})
        # None, never inf and never 0: an unbounded cell has no width to average.
        rows.append({**base, "metric_name": "mean_feasible_width", "value": width})
    return pl.DataFrame(rows)
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_metrics_bounds.py -v`
Expected: 3 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/metrics.py tests/unit/test_validate_metrics_bounds.py
git commit -m "feat(validate): §13.5 bound metrics, with vacuity reported rather than hidden"
```

> Deviation: the plan's third test asserted a mean feasible width of 425.0 over bounds [0,150]
> and [0,500], whose widths are 150 and 500 and whose mean is 325. The implementation was right;
> the expectation is now written as its own derivation rather than as a literal.

---

### Task 14: §13.6 point metrics and the denominator R-COMP-10 demands

**Files:**
- Modify: `src/logging_employment/validate/metrics.py`
- Test: `tests/unit/test_validate_metrics_point.py`

**Interfaces:**
- Produces: `point_metrics(scores, *, regime, seed, arm) -> pl.DataFrame`.

**A declined cell has no estimate, so no point metric is computable for it.** That is precisely why
§13.8's final paragraph exists: "A method whose months drop out of the scored set drops out
non-randomly, so an unreported data-driven decline can make a broken implementation's point and
probabilistic metrics look better than a correct one's."

Every point metric therefore reports `n_scored` (rows with a non-null estimate) alongside
`denominator` (rows masked) and the three decline counts. The denominator basis is **cell-rows**,
not months.

`harvest_proportional` declines by design in every month — it will show `n_scored = 0` and every
metric null. That is correct and must not be special-cased into a zero.

MAPE is reported only where the truth is safely non-zero; §13.6 says "where denominators are safe".
On a small-cell regime a truth of 5–8 employees makes WAPE > 1 unremarkable, so the scoreboard
reports a magnitude-stratified breakdown beside the headline.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_metrics_point.py
import polars as pl

from logging_employment.validate.metrics import point_metrics


def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["a", "a", "a", "b", "b", "b"],
            "cell_id": ["c1", "c2", "c3"] * 2,
            "truth": [100.0, 200.0, 300.0] * 2,
            "estimate": [110.0, 180.0, None, None, None, None],
            "decline_kind": [None, None, "data_gap", "by_design", "by_design", "by_design"],
        }
    )


def test_a_declined_row_is_excluded_from_the_numerator_but_not_the_denominator():
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    a = out.filter(pl.col("estimator_id") == "a")
    assert a["n_scored"].unique().to_list() == [2]
    assert a["denominator"].unique().to_list() == [3.0]
    assert a["n_declined_data_gap"].unique().to_list() == [1]


def test_an_all_declining_estimator_reports_null_not_zero():
    """`harvest_proportional` declines by design; a 0.0 WAPE would read as perfect accuracy."""
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    b = out.filter((pl.col("estimator_id") == "b") & (pl.col("metric_name") == "wape"))
    assert b["value"].item() is None
    assert b["n_scored"].item() == 0
    assert b["n_declined_by_design"].item() == 3


def test_wape_is_computed_over_the_scored_rows_only():
    out = point_metrics(_scores(), regime="r", seed=1, arm="state_total")
    wape = out.filter(
        (pl.col("estimator_id") == "a") & (pl.col("metric_name") == "wape")
    )["value"].item()
    # (|110-100| + |180-200|) / (100 + 200) = 30 / 300
    assert abs(wape - 0.1) < 1e-12
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_metrics_point.py -v`
Expected: FAIL — `cannot import name 'point_metrics'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/metrics.py  — append
_POINT_NAMES = ("mae", "rmse", "bias", "wape", "median_ape")


def point_metrics(scores: pl.DataFrame, *, regime: str, seed: int, arm: str) -> pl.DataFrame:
    """§13.6's point metrics over the SCORED rows, with the declined rows counted beside them.

    The denominator is masked cell-rows; the numerator is rows carrying an estimate. Reporting only
    the numerator is the failure §13.8's closing paragraph names: a method that declines its hard
    months looks better than one that attempts them.
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        scored = group.filter(pl.col("estimate").is_not_null())
        counts = {
            kind: group.filter(pl.col("decline_kind") == kind).height
            for kind in ("by_design", "data_gap", "reconciliation_failure")
        }
        base = {
            "regime": regime,
            "seed": seed,
            "mask_arm": arm,
            "estimator_id": str(estimator),
            "metric_family": "point",
            "denominator": float(group.height),
            "denominator_basis": "masked_cell_rows",
            "n_scored": scored.height,
            "n_declined_by_design": counts["by_design"],
            "n_declined_data_gap": counts["data_gap"],
            "n_declined_reconciliation_failure": counts["reconciliation_failure"],
        }
        if scored.height == 0:
            # Null, never 0.0. A zero error over zero rows reads as perfect accuracy.
            rows.extend({**base, "metric_name": n, "value": None} for n in _POINT_NAMES)
            continue

        err = scored["estimate"] - scored["truth"]
        abs_err = err.abs()
        values = {
            "mae": abs_err.mean(),
            "rmse": float((err**2).mean() ** 0.5),
            "bias": err.mean(),
            "wape": float(abs_err.sum() / scored["truth"].abs().sum())
            if scored["truth"].abs().sum() else None,
            "median_ape": float(
                (abs_err / scored["truth"].abs()).median()
            ) if scored.filter(pl.col("truth").abs() > 0).height == scored.height else None,
        }
        rows.extend({**base, "metric_name": n, "value": values[n]} for n in _POINT_NAMES)
    return pl.DataFrame(rows)
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_metrics_point.py -v`
Expected: 3 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/metrics.py tests/unit/test_validate_metrics_point.py
git commit -m "feat(validate): §13.6 point metrics with R-COMP-10 denominators and decline counts"
```

---

### Task 15: §13.7 probabilistic metrics and §10.7's empirical predictive intervals

**Files:**
- Create: `src/logging_employment/validate/intervals.py`
- Modify: `src/logging_employment/validate/metrics.py`
- Test: `tests/unit/test_validate_intervals.py`

**Interfaces:**
- Produces: `residual_ensemble(residuals, point) -> np.ndarray`,
  `empirical_interval(ensemble, level) -> tuple[float, float]`, `crps(ensemble, truth) -> float`;
  `probabilistic_metrics(scores, *, regime, seed, arm) -> pl.DataFrame`.

§10.7: "at least the historical-share, CBP-intensity, and constrained-regression baselines SHOULD
produce empirical predictive intervals from rolling pseudo-suppression residuals. A point-only
baseline cannot be compared fairly on probabilistic metrics."

**One object, not two.** Build the residual-shifted ensemble once and derive both the quantiles and
the CRPS from it, so the interval and the score cannot disagree.

**Leakage:** the residual pool for a target MUST come from *other* replicates — a residual computed
on the target's own cell is the truth in disguise. Pool by regime and estimator, excluding the
target's own `cell_id`.

**`interval_source` and `calibration_sample_size` are columns**, so a point-only baseline is
*visibly* point-only rather than silently absent from the coverage table. §10.7 names three
families; the others carry `interval_source = 'none'`.

**Report the clip.** Shifted draws can go negative; clipping at 0 changes nominal coverage. Record
`n_clipped` rather than letting the clip absorb silently. **Log score is NOT emitted** — an
empirical ensemble puts zero density outside its own range, so log score is `-inf` whenever the
truth falls outside, which is an artifact of the estimator, not of the model. CRPS is reported
instead, and the omission is recorded here.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_intervals.py
import numpy as np

from logging_employment.validate.intervals import crps, empirical_interval, residual_ensemble


def test_the_ensemble_is_the_point_shifted_by_every_residual():
    ens = residual_ensemble(np.array([-10.0, 0.0, 10.0]), point=100.0)
    assert sorted(ens.tolist()) == [90.0, 100.0, 110.0]


def test_a_wider_level_gives_a_wider_interval():
    ens = residual_ensemble(np.linspace(-50, 50, 201), point=100.0)
    lo50, hi50 = empirical_interval(ens, 0.50)
    lo90, hi90 = empirical_interval(ens, 0.90)
    assert (hi90 - lo90) > (hi50 - lo50)


def test_crps_is_zero_for_a_point_mass_at_the_truth():
    assert crps(np.array([7.0] * 100), truth=7.0) < 1e-9


def test_crps_grows_as_the_ensemble_moves_away():
    ens = np.array([10.0] * 100)
    assert crps(ens, truth=20.0) > crps(ens, truth=12.0)
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_intervals.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/intervals.py
"""§10.7's empirical predictive intervals, from rolling pseudo-suppression residuals.

ONE object: the residual-shifted ensemble. Both the quantiles and the CRPS are derived from it, so
an interval and a score can never disagree about the same predictive distribution.

Log score is deliberately NOT offered. An empirical ensemble assigns zero density outside its own
range, so a log score is -inf whenever the truth falls outside — a property of the density
estimator, not of the method being scored. §13.7 permits "CRPS or log score"; this package reports
CRPS.
"""

from __future__ import annotations

import numpy as np


def residual_ensemble(residuals: np.ndarray, point: float) -> np.ndarray:
    """The point estimate shifted by every pooled residual.

    The residual pool MUST exclude the target's own cell: a residual computed on the cell being
    scored is the withheld truth in another form (§13.4 bullet 1).
    """
    return np.asarray(residuals, dtype=float) + float(point)


def clip_at_zero(ensemble: np.ndarray) -> tuple[np.ndarray, int]:
    """Employment cannot be negative. Returns the clipped ensemble AND the count clipped.

    The count is returned rather than discarded because clipping shifts nominal coverage; a
    coverage number computed over a clipped ensemble with an unreported clip rate is not
    interpretable.
    """
    clipped = np.maximum(ensemble, 0.0)
    return clipped, int((ensemble < 0.0).sum())


def empirical_interval(ensemble: np.ndarray, level: float) -> tuple[float, float]:
    """A central `level` interval from the ensemble's own quantiles."""
    tail = (1.0 - level) / 2.0
    return (
        float(np.quantile(ensemble, tail)),
        float(np.quantile(ensemble, 1.0 - tail)),
    )


def crps(ensemble: np.ndarray, truth: float) -> float:
    """CRPS by the energy form: E|X - y| - 0.5 * E|X - X'|."""
    x = np.asarray(ensemble, dtype=float)
    term_one = np.abs(x - float(truth)).mean()
    term_two = np.abs(x[:, None] - x[None, :]).mean()
    return float(term_one - 0.5 * term_two)
```

Then add `probabilistic_metrics` to `metrics.py`:

```python
# src/logging_employment/validate/metrics.py  — append
import numpy as np

from .intervals import clip_at_zero, crps, empirical_interval, residual_ensemble

_LEVELS = (0.50, 0.80, 0.90, 0.95)
# §10.7 names exactly three families that SHOULD carry intervals. Everything else is point-only,
# and says so in `interval_source` rather than being silently absent from the coverage table.
_INTERVAL_FAMILIES = ("share_", "cbp_intensity", "constrained_regression")


def probabilistic_metrics(
    scores: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.7's coverage, width and CRPS from §10.7's residual-shifted ensembles."""
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        name = str(estimator)
        eligible = any(name.startswith(f) or name == f for f in _INTERVAL_FAMILIES)
        scored = group.filter(pl.col("estimate").is_not_null())
        base = {
            "regime": regime, "seed": seed, "mask_arm": arm, "estimator_id": name,
            "metric_family": "probabilistic",
            "denominator": float(group.height), "denominator_basis": "masked_cell_rows",
            "n_scored": scored.height,
        }
        if not eligible or scored.height < 2:
            rows.append({**base, "metric_name": "coverage_0.90", "value": None,
                         "interval_source": "none", "calibration_sample_size": 0})
            continue

        residual_pool = (scored["estimate"] - scored["truth"]).to_numpy()
        covered = {level: 0 for level in _LEVELS}
        widths: list[float] = []
        crps_values: list[float] = []
        clipped_total = 0
        for row in scored.iter_rows(named=True):
            # LEAVE-ONE-OUT: a residual computed on this cell IS the withheld truth (§13.4).
            others = np.array(
                [r for r in residual_pool if r != (row["estimate"] - row["truth"])],
                dtype=float,
            )
            if others.size < 2:
                continue
            ensemble, n_clipped = clip_at_zero(residual_ensemble(others, row["estimate"]))
            clipped_total += n_clipped
            for level in _LEVELS:
                lo, hi = empirical_interval(ensemble, level)
                if lo <= row["truth"] <= hi:
                    covered[level] += 1
                if level == 0.90:
                    widths.append(hi - lo)
            crps_values.append(crps(ensemble, row["truth"]))

        n = len(crps_values)
        common = {**base, "interval_source": "rolling_residual_ensemble",
                  "calibration_sample_size": n}
        for level in _LEVELS:
            rows.append({**common, "metric_name": f"coverage_{level:.2f}",
                         "value": covered[level] / n if n else None})
        rows.append({**common, "metric_name": "mean_interval_width_0.90",
                     "value": float(np.mean(widths)) if widths else None})
        rows.append({**common, "metric_name": "crps",
                     "value": float(np.mean(crps_values)) if n else None})
        # The clip is REPORTED, not absorbed: it shifts nominal coverage.
        rows.append({**common, "metric_name": "n_clipped_at_zero", "value": float(clipped_total)})
    return pl.DataFrame(rows)
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_intervals.py -v`
Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/intervals.py src/logging_employment/validate/metrics.py tests/unit/test_validate_intervals.py
git commit -m "feat(validate): §10.7 empirical intervals and §13.7 probabilistic metrics"
```

> Deviation: the leave-one-out excluded the target's residual by float equality, which also drops
> every other cell sharing that residual; excluded by position instead. Separately, `crps` was
> the harness's DOMINANT cost, not `run_baselines` as evidence §4 states — it is O(n^2) per cell
> and O(n^3) per estimator, and `whole_seasonal_blocks` masks 291 cells. Replaced with the exact
> sorted-ensemble identity (O(n log n)), pinned against the pairwise definition.

---

### Task 16: §13.8 constraint metrics and the R-COMP-10 report

**Files:**
- Modify: `src/logging_employment/validate/metrics.py`
- Test: `tests/unit/test_validate_metrics_constraint.py`

**Interfaces:**
- Produces: `constraint_metrics(...)`, `decline_and_basis_report(scores, *, regime, seed) -> pl.DataFrame`.

Two rules that are easy to get silently wrong:

1. **An empty row set produces `null`, not `0.0`.** A residual norm of 0.0 over zero constraint rows
   reads as a perfect pass. `constraint_rows_scored` sits beside the norms so a reader can tell.
2. **The anchor's adding-up residual is its OWN column**, outside `‖Ax−y‖`. The anchor is a
   `modeling_assumption`, never a constraint row (INV-004/INV-005) — folding it into the constraint
   norm would report a modelling choice as a constraint violation.

**R-COMP-10 is the load-bearing part of §13.8 for this stage**, because on the state-total arm four
of the five sub-metrics carry no information. The report emits, per method **and per regime**, with
the denominator stated:

- decline counts by each of the three kinds, and
- `n_own_estimator` / `n_establishment_fallback` from `weight_basis`.

**The second is not redundant with the first.** Plan 10's `BreakAdjustedShare` refusals *compose*
rather than decline, so they never appear in a decline count. Measured, `share_break_adjusted` is
226 own / 1,001 fallback against its three siblings' 327/900 — a scoreboard reading decline counts
alone reports it as fully covered.

`WEIGHT_BASES` is the closed triple `own_estimator | establishment_fallback | none`, so
`baseline_results.parquet` **cannot** distinguish a variant-5 refusal from a cell with no share
history at all. Do not plan a column that claims to; recompute it from the share history if a later
item needs the split.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_metrics_constraint.py
import polars as pl

from logging_employment.validate.metrics import decline_and_basis_report


def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["share_break_adjusted"] * 4 + ["harvest_proportional"] * 2,
            "cell_id": ["c1", "c2", "c3", "c4", "c1", "c2"],
            "estimate": [1.0, 2.0, 3.0, 4.0, None, None],
            "decline_kind": [None] * 4 + ["by_design"] * 2,
            "weight_basis": [
                "own_estimator", "establishment_fallback",
                "establishment_fallback", "establishment_fallback",
                "none", "none",
            ],
        }
    )


def test_a_composed_refusal_is_invisible_to_decline_counts_but_visible_in_weight_basis():
    """Plan 10's refusals compose. Decline counts alone report full coverage."""
    out = decline_and_basis_report(_scores(), regime="r", seed=1)
    row = out.filter(pl.col("estimator_id") == "share_break_adjusted").row(0, named=True)
    assert row["n_declined_by_design"] == 0
    assert row["n_declined_data_gap"] == 0
    assert row["n_own_estimator"] == 1
    assert row["n_establishment_fallback"] == 3


def test_every_report_row_states_its_denominator():
    out = decline_and_basis_report(_scores(), regime="r", seed=1)
    assert out["denominator"].null_count() == 0
    assert set(out["denominator_basis"].unique().to_list()) == {"masked_cell_rows"}


def test_a_fully_declining_estimator_is_reported_as_declining_not_absent():
    out = decline_and_basis_report(_scores(), regime="r", seed=1)
    row = out.filter(pl.col("estimator_id") == "harvest_proportional").row(0, named=True)
    assert row["n_declined_by_design"] == 2
    assert row["n_scored"] == 0
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_metrics_constraint.py -v`
Expected: FAIL — `cannot import name 'decline_and_basis_report'`

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/metrics.py  — append
def decline_and_basis_report(scores: pl.DataFrame, *, regime: str, seed: int) -> pl.DataFrame:
    """§13.8's R-COMP-10 report: decline counts by kind AND weight basis, per method per regime.

    The weight-basis half is not redundant. Plan 10's `BreakAdjustedShare` refusals reuse the
    `None` path, so the cell is COMPOSED onto the §10.2 fallback rather than declined: it carries
    `weight_basis = 'establishment_fallback'` and NO `decline_kind`. A report built from decline
    counts alone therefore shows §10.3 variant 5 as fully covered. Measured on D1,
    `share_break_adjusted` is 226 own / 1,001 fallback against its three siblings' 327/900.
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        rows.append(
            {
                "regime": regime,
                "seed": seed,
                "estimator_id": str(estimator),
                "metric_family": "declines",
                "denominator": float(group.height),
                "denominator_basis": "masked_cell_rows",
                "n_scored": group.filter(pl.col("estimate").is_not_null()).height,
                "n_declined_by_design": group.filter(
                    pl.col("decline_kind") == "by_design").height,
                "n_declined_data_gap": group.filter(
                    pl.col("decline_kind") == "data_gap").height,
                "n_declined_reconciliation_failure": group.filter(
                    pl.col("decline_kind") == "reconciliation_failure").height,
                "n_own_estimator": group.filter(
                    pl.col("weight_basis") == "own_estimator").height,
                "n_establishment_fallback": group.filter(
                    pl.col("weight_basis") == "establishment_fallback").height,
            }
        )
    return pl.DataFrame(rows)


def constraint_metrics(
    scores: pl.DataFrame, anchor_residuals: pl.DataFrame, *, regime: str, seed: int, arm: str
) -> pl.DataFrame:
    """§13.8's residual norms and violation counts.

    Two rules that are silent when broken. (1) An empty row set yields NULL, never 0.0 — a norm of
    zero over zero rows reads as a perfect pass, so `constraint_rows_scored` rides alongside.
    (2) The anchor's adding-up residual is its OWN column, outside the norms: the anchor is a
    `modeling_assumption` and never a constraint row (INV-004/INV-005), so folding it in would
    report a modelling choice as a constraint violation.
    """
    rows: list[dict[str, object]] = []
    for (estimator,), group in scores.group_by("estimator_id", maintain_order=True):
        scored = group.filter(pl.col("estimate").is_not_null())
        n = scored.height
        negatives = scored.filter(pl.col("estimate") < 0).height
        integer_violations = scored.filter(
            pl.col("estimate_integer").is_not_null()
            & ((pl.col("estimate_integer") - pl.col("estimate")).abs() > 1.0)
        ).height
        anchor = anchor_residuals.filter(pl.col("estimator_id") == estimator)
        base = {
            "regime": regime, "seed": seed, "mask_arm": arm, "estimator_id": str(estimator),
            "metric_family": "constraint",
            "denominator": float(group.height), "denominator_basis": "masked_cell_rows",
            "n_scored": n, "constraint_rows_scored": n,
        }
        rows.append({**base, "metric_name": "negative_outputs", "value": float(negatives)})
        rows.append({**base, "metric_name": "integerization_violations",
                     "value": float(integer_violations)})
        rows.append({
            **base, "metric_name": "anchor_adding_up_max_abs",
            "value": float(anchor["residual_abs"].max()) if anchor.height else None,
        })
    return pl.DataFrame(rows)
```

`constraint_rows_scored` is added to `VALIDATION_METRIC_SCHEMA` in Task 2 alongside the other
counters.

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_metrics_constraint.py -v`
Expected: 3 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/metrics.py tests/unit/test_validate_metrics_constraint.py
git commit -m "feat(validate): §13.8 constraint metrics and the R-COMP-10 decline/basis report"
```

---

### Task 17: The scoreboard and the preferred transparent baseline

**Files:**
- Create: `src/logging_employment/validate/scoreboard.py`
- Test: `tests/unit/test_validate_scoreboard.py`

**Interfaces:**
- Produces: `build_scoreboard(metrics) -> pl.DataFrame`,
  `preferred_baseline(scoreboard, *, regime) -> str | None`.

This is the number Stage 5's promotion gate compares against, so its provenance must be legible.
**Every scoreboard row carries:** its regime, its target-selection rule, its denominator, `n`, and
the own/fallback split **per estimator** — never pooled.

Four rules, each from a measured trap:

1. **Use `preferred_estimator_by_month`, never the window scalar.** The scalar names
   `cbp_intensity` for all 96 months; measured, `cbp_intensity` produces nothing in the 12 months of
   2024 because CBP is published only through 2023. The per-month function reports 84
   `cbp_intensity` / 12 `constrained_regression`.
2. **A regime whose window includes 2024 scores 9 estimators, not 10.** State that denominator per
   regime rather than letting `cbp_intensity` look like a silent failure.
3. **A rising decline count under a mask is not degradation.** `cbp_intensity` declined 147 times
   unmasked and 159 under one measured mask — the same 12-month refusal over a larger missing set.
4. **`preferred_estimator` raises on a subset lacking all four §10.8 rungs.** A regime restricted
   to fewer estimators must either include the rungs or handle the `ValueError`.

Report a magnitude-stratified breakdown beside the headline WAPE. On a small-cell regime the
denominator can be 5–8 employees, which makes WAPE > 1 unremarkable and uninformative alone.

- [x] **Step 1: Write the failing test**

```python
# tests/unit/test_validate_scoreboard.py
import polars as pl
import pytest

from logging_employment.validate.metrics import decline_and_basis_report, point_metrics
from logging_employment.validate.scoreboard import build_scoreboard, preferred_baseline


def _scores():
    """Built by the emitters, never by hand.

    A hand-written metrics frame carrying all thirteen columns on point rows is a frame the harness
    never produces, and it hides the defect this fixture exists to catch: the two emitters have
    disjoint column sets, so a scoreboard that SELECTS the basis columns off point rows gets null.
    """
    truth = [100.0, 200.0]
    return pl.DataFrame(
        {
            "estimator_id": ["cbp_intensity"] * 2 + ["harvest_proportional"] * 2,
            "cell_id": ["c1", "c2"] * 2,
            "truth": truth * 2,
            "estimate": [110.0, 180.0, None, None],
            "decline_kind": [None, None, "by_design", "by_design"],
            "weight_basis": [
                "own_estimator", "establishment_fallback", "none", "none",
            ],
        }
    )


def _metrics():
    scores = _scores()
    return pl.concat(
        [
            point_metrics(scores, regime="small_cell_biased", seed=1024, arm="state_total"),
            decline_and_basis_report(scores, regime="small_cell_biased", seed=1024),
        ],
        how="diagonal",
    )


def test_the_preferred_baseline_is_the_best_scoring_estimator_that_scored_anything():
    board = build_scoreboard(_metrics())
    assert preferred_baseline(board, regime="small_cell_biased") == "cbp_intensity"


def test_an_estimator_that_scored_nothing_can_never_be_preferred():
    """A null WAPE must not sort to the front as if it were zero error."""
    board = build_scoreboard(_metrics())
    assert preferred_baseline(board, regime="small_cell_biased") != "harvest_proportional"


def test_every_scoreboard_row_carries_its_denominator_and_basis_split():
    board = build_scoreboard(_metrics())
    for column in ("denominator", "n_scored", "n_own_estimator", "n_establishment_fallback"):
        assert column in board.columns
    assert board["denominator"].null_count() == 0


def test_the_own_fallback_split_survives_the_concat():
    """The regression guard. Before the join, these were null on every row.

    `point_metrics` does not emit the basis columns and `decline_and_basis_report` does not emit
    `metric_name`; a diagonal concat leaves each null on the other's rows. A scoreboard that
    selects rather than joins reports `n_own_estimator = None` for every estimator, which is
    exactly the signal §10.3 variant 5's composed refusals need.
    """
    board = build_scoreboard(_metrics())
    assert board["n_own_estimator"].null_count() == 0
    assert board["n_establishment_fallback"].null_count() == 0
    row = board.filter(pl.col("estimator_id") == "cbp_intensity").row(0, named=True)
    assert row["n_own_estimator"] == 1
    assert row["n_establishment_fallback"] == 1


def test_a_regime_with_no_scoring_estimator_has_no_preferred_baseline():
    empty = _metrics().with_columns(pl.lit(None, dtype=pl.Float64).alias("value"))
    assert preferred_baseline(build_scoreboard(empty), regime="small_cell_biased") is None
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/unit/test_validate_scoreboard.py -v`
Expected: FAIL — module does not exist.

- [x] **Step 3: Implement**

```python
# src/logging_employment/validate/scoreboard.py
"""The number Stage 5's §13.10 promotion gate compares against.

Provenance rules, each from a measured trap:
  - the preferred baseline is read PER MONTH, never from the window scalar: measured, the scalar
    names `cbp_intensity` for all 96 months while CBP is published only through 2023, so it names
    an estimator that produced nothing in 12 of them;
  - a null metric never sorts ahead of a real one — an estimator that declined every cell has no
    error, not zero error;
  - the own/fallback split rides on every row, per estimator, because §10.3 variant 5's refusals
    COMPOSE rather than decline and are invisible to decline counts.
"""

from __future__ import annotations

import polars as pl


def build_scoreboard(metrics: pl.DataFrame) -> pl.DataFrame:
    """One row per (regime, estimator) for the headline metric, with its provenance attached.

    The own/fallback split is JOINED, not selected. `point_metrics` and `decline_and_basis_report`
    emit different column sets and the harness concatenates them with `how="diagonal"`, so
    `n_own_estimator` is null on every point row. Selecting it straight off the filtered point rows
    returns null for all of them — silently dropping the one column that makes §10.3 variant 5's
    composed refusals visible, which is the whole reason the report exists.
    """
    headline = metrics.filter(
        (pl.col("metric_family") == "point") & (pl.col("metric_name") == "wape")
    ).select(
        "regime",
        "seed",
        "mask_arm",
        "estimator_id",
        pl.col("value").alias("wape"),
        "denominator",
        "denominator_basis",
        "n_scored",
        "n_declined_by_design",
        "n_declined_data_gap",
        "n_declined_reconciliation_failure",
    )
    basis = metrics.filter(pl.col("metric_family") == "declines").select(
        "regime", "seed", "estimator_id", "n_own_estimator", "n_establishment_fallback"
    )
    return headline.join(
        basis, on=["regime", "seed", "estimator_id"], how="left"
    ).sort("regime", "estimator_id")


def preferred_baseline(scoreboard: pl.DataFrame, *, regime: str) -> str | None:
    """The best-scoring estimator that actually scored something, or None.

    `n_scored > 0` is a filter, not a tiebreak: an all-declining estimator has a null WAPE, and a
    sort that treats null as smallest would crown `harvest_proportional`, which declines by design
    in every month of the window.
    """
    candidates = scoreboard.filter(
        (pl.col("regime") == regime) & (pl.col("n_scored") > 0) & pl.col("wape").is_not_null()
    )
    if candidates.height == 0:
        return None
    return candidates.sort("wape")["estimator_id"].to_list()[0]
```

- [x] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_validate_scoreboard.py -v`
Expected: 5 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/validate/scoreboard.py tests/unit/test_validate_scoreboard.py
git commit -m "feat(validate): the baseline scoreboard and its preferred-estimator rule"
```

---

### Task 18: `run_pseudo_suppression`, the `validate` CLI, and the manifest

**Files:**
- Create: `src/logging_employment/validate/harness.py`
- Modify: `src/logging_employment/validate/__init__.py`
- Modify: `src/logging_employment/cli.py`
- Test: `tests/integration/test_validate_cli.py`

**Interfaces:**
- Produces: `run_pseudo_suppression(data, estimators, config) -> ValidationResult` per §16.2, and
  `logging-estimates validate --config config.yaml`.

§16.2 fixes the signature: `run_pseudo_suppression(data: HarmonizedData, estimators:
Sequence[Estimator], config: ValidationConfig)`.

> **Deviation, stated rather than silent:** the third parameter is typed `Config`, not
> `ValidationConfig`. The harness needs `config.constraints` for `solve_bounds` and the whole
> `Config` for `run_baselines`, and `ValidationConfig` carries neither. Narrowing the argument
> would force the harness to reach for a second config object it was not handed. The parameter
> name and position match §16.2; only the type is wider. `config.validation` is where every
> §13 setting is still read from.

**Budget.** One replicate costs ~30 s, dominated by `run_baselines`. 13 regimes × 20 replicates ≈
**2.2 hours** at full registry. Restrict `estimators` per regime where the regime does not need all
ten — that is what Task 4's keyword buys. Mark the CLI integration test `slow`.

Per §16.1 the command MUST write a machine-readable manifest and MUST be idempotent for identical
inputs. The manifest records, per regime: the disposition, the seeds, replicate count, targets
masked, the **masked** `constraint_set_hash` per replicate, the estimators actually run, and the
preferred baseline.

**Do not join a masked cell against the run's shipped `deterministic_bounds.parquet`** — that join
returns the truth. Bounds for a masked cell come only from `mask_and_solve`.

- [x] **Step 1: Write the failing test**

```python
# tests/integration/test_validate_cli.py
import json
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from logging_employment.cli import app

pytestmark = pytest.mark.slow


def test_validate_writes_metrics_and_a_manifest(tmp_path):
    result = CliRunner().invoke(app, ["validate", "--config", "config.yaml"])
    assert result.exit_code == 0, result.output

    run_dirs = sorted(Path("runs").glob("*/validation_metrics.parquet"))
    assert run_dirs, "no validation_metrics.parquet written"
    metrics = pl.read_parquet(run_dirs[-1])
    assert metrics.height > 0
    assert metrics["denominator"].null_count() == 0

    manifest = json.loads((run_dirs[-1].parent / "validation_manifest.json").read_text())
    assert "regimes" in manifest
    assert manifest["regimes"]["preliminary_to_final_vintage"]["disposition"] == "cannot_run_on_d1"
    # A refused regime records WHY and emits no scores — never an empty partition.
    assert manifest["regimes"]["preliminary_to_final_vintage"]["n_scored"] == 0


def test_validate_is_idempotent_for_identical_inputs():
    runner = CliRunner()
    first = runner.invoke(app, ["validate", "--config", "config.yaml"])
    assert first.exit_code == 0
    path = sorted(Path("runs").glob("*/validation_metrics.parquet"))[-1]
    before = path.read_bytes()
    second = runner.invoke(app, ["validate", "--config", "config.yaml"])
    assert second.exit_code == 0
    assert path.read_bytes() == before
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/integration/test_validate_cli.py -v`
Expected: FAIL — no `validate` command.

- [x] **Step 3: Implement `run_pseudo_suppression`**

```python
# src/logging_employment/validate/harness.py
"""§16.2's `run_pseudo_suppression`.

Cost: one replicate is ~30 s, essentially all of it `run_baselines` (the mask-and-solve arm is
~0.36 s). 13 regimes x 20 replicates is ~2.2 hours at the full registry, which is why
`run_baselines` takes an estimator subset and why regimes declare the estimators they need.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import polars as pl

from ..baselines.interfaces import Estimator
from ..baselines.runner import REGISTRY, run_baselines
from ..config import Config
from ..contracts import HarmonizedData, assert_declared_provenance
from .leakage import assert_no_retained_truth
from .mask import apply_mask
from ..errors import ConceptViolationError
from .metrics import (
    bound_metrics,
    constraint_metrics,
    decline_and_basis_report,
    point_metrics,
    probabilistic_metrics,
)
from .recover import mask_and_solve
from .regimes import REGIME_SPECS, select_targets
from .scoreboard import build_scoreboard


@dataclass(frozen=True)
class ValidationResult:
    """§16.2's return: the scored rows, the metric rows, the scoreboard, and the manifest."""

    scores: pl.DataFrame
    metrics: pl.DataFrame
    scoreboard: pl.DataFrame
    manifest: dict[str, object]


def run_pseudo_suppression(
    data: HarmonizedData,
    estimators: Sequence[Estimator] = REGISTRY,
    config: Config | None = None,
) -> ValidationResult:
    """Every enabled regime, every seed. Refuses rather than skipping.

    `config` is keyword-optional only so the §16.2 argument ORDER survives; it is required in
    fact. A bare `assert` would vanish under `python -O`, and this package raises typed errors for
    caller mistakes everywhere else.
    """
    if config is None:
        raise ConceptViolationError(
            "run_pseudo_suppression requires a Config: the harness needs `config.constraints` for "
            "solve_bounds and the full object for run_baselines"
        )
    all_scores: list[pl.DataFrame] = []
    all_metrics: list[pl.DataFrame] = []
    manifest: dict[str, object] = {"regimes": {}}

    for name, spec in REGIME_SPECS.items():
        entry: dict[str, object] = {"disposition": spec.disposition, "grain": spec.grain,
                                    "n_scored": 0, "replicates": 0, "hashes": []}
        if spec.disposition != "feasible":
            entry["reason"] = (
                "no second snapshot in any staged table"
                if spec.disposition == "cannot_run_on_d1"
                else "no smoothing estimator in the §10 registry"
            )
            manifest["regimes"][name] = entry
            continue

        for seed in config.validation.pseudo_suppression_seeds:
            targets = select_targets(name, data.qcew_monthly, seed=seed, config=config)
            if not targets:
                continue
            masked, truth = apply_mask(data, targets)
            assert_no_retained_truth(masked, truth)
            system = mask_and_solve(data, targets, config)
            results, _audit = run_baselines(masked, config, estimators=estimators)
            scored = _join_truth(results, truth, system, regime=name, seed=seed)
            assert_declared_provenance(scored)
            all_scores.append(scored)
            all_metrics.append(point_metrics(scored, regime=name, seed=seed, arm="state_total"))
            all_metrics.append(
                bound_metrics(scored, regime=name, seed=seed, arm="state_total")
            )
            all_metrics.append(decline_and_basis_report(scored, regime=name, seed=seed))
            all_metrics.append(
                probabilistic_metrics(scored, regime=name, seed=seed, arm="state_total")
            )
            all_metrics.append(
                constraint_metrics(
                    scored, _anchor_residuals(scored), regime=name, seed=seed, arm="state_total"
                )
            )
            entry["replicates"] = int(entry["replicates"]) + 1
            entry["n_scored"] = int(entry["n_scored"]) + scored.height
            entry["hashes"].append(system.constraint_set_hash)
        manifest["regimes"][name] = entry

    scores = pl.concat(all_scores, how="vertical") if all_scores else pl.DataFrame()
    metrics = pl.concat(all_metrics, how="diagonal") if all_metrics else pl.DataFrame()
    board = build_scoreboard(metrics) if metrics.height else pl.DataFrame()
    return ValidationResult(scores, metrics, board, manifest)
```

```python
# src/logging_employment/validate/harness.py  — append
def _join_truth(
    results: pl.DataFrame,
    truth: pl.DataFrame,
    system: "MaskedSystem",
    *,
    regime: str,
    seed: int,
) -> pl.DataFrame:
    """Attach truth, masked bounds, the INV-009 label, and the MASKED hash to the estimator rows.

    The bounds come from `system`, never from the run directory's shipped
    `deterministic_bounds.parquet` — that table still carries the published value for a masked
    cell, so joining it would hand the harness the answer.

    `suppression_type` is re-attached here because `baseline_results` does not carry it, and
    §13.2 step 8 scores primary-like and complementary-like cells separately.
    """
    labelled = truth.select(
        "state_fips", "reference_month", "truth"
    )
    bounds = system.bounds.select(
        "cell_id", "selected_lower", "selected_upper", "bound_status"
    )
    return (
        results.join(labelled, on=["state_fips", "reference_month"], how="inner")
        .join(bounds, on="cell_id", how="left")
        .with_columns(
            pl.lit(regime).alias("regime"),
            pl.lit(seed).alias("seed"),
            pl.lit(system.constraint_set_hash).alias("masked_constraint_set_hash"),
        )
    )


def _anchor_residuals(scored: pl.DataFrame) -> pl.DataFrame:
    """Per-estimator adding-up residual, kept OUTSIDE the constraint norms (INV-004/INV-005)."""
    return (
        scored.filter(pl.col("estimate").is_not_null())
        .group_by("estimator_id", "reference_month")
        .agg(
            (pl.col("estimate").sum() - pl.col("residual").first()).abs().alias("residual_abs")
        )
        .group_by("estimator_id")
        .agg(pl.col("residual_abs").max())
    )
```

The `inner` join on truth is deliberate: it drops every cell the mask did not hide, so a scored
row that was never masked is impossible by construction rather than by assertion.

- [x] **Step 4: Add the CLI command**

```python
# src/logging_employment/cli.py  — append, mirroring `run-baselines`
@app.command("validate")
def validate_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Run §13's pseudo-suppression harness and persist its metrics and scoreboard."""
    import json

    from .baselines.runner import REGISTRY
    from .build import write_parquet_deterministic
    from .contracts import HarmonizedData
    from .runs import run_dir, run_id
    from .validate.harness import run_pseudo_suppression

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    run.mkdir(parents=True, exist_ok=True)

    result = run_pseudo_suppression(data, REGISTRY, cfg)

    hashes = {
        "validation_scores": write_parquet_deterministic(
            result.scores, run / "validation_scores.parquet"
        ),
        "validation_metrics": write_parquet_deterministic(
            result.metrics, run / "validation_metrics.parquet"
        ),
        "validation_scoreboard": write_parquet_deterministic(
            result.scoreboard, run / "validation_scoreboard.parquet"
        ),
    }
    manifest = {**result.manifest, "output_hashes": hashes}
    (run / "validation_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    for regime, entry in sorted(result.manifest["regimes"].items()):
        typer.echo(f"{regime} {entry['disposition']} scored={entry['n_scored']}")
```

`write_parquet_deterministic` sorts on every column, which is what makes the idempotence test in
Step 1 meaningful: two runs with identical inputs produce byte-identical files even though the
in-memory row order depends on `Partition.missing`'s order.

- [x] **Step 5: Run the tests**

Run: `uv run pytest tests/integration/test_validate_cli.py -v -m slow`
Expected: 2 passed. Budget real time — this exercises the full harness.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/validate src/logging_employment/cli.py tests/integration/test_validate_cli.py
git commit -m "feat(validate): run_pseudo_suppression and the validate CLI command"
```

> Deviation, three defects and two additions. (1) `_anchor_residuals(scored)` summed the masked
> SUBSET against the month's whole-missing-set residual: 4134.4 / 2833.2 employees of apparent
> violation against a true 4.5e-13, which would have shipped as §13.8's
> `anchor_adding_up_max_abs` forever. Takes the full frame now. (2) `_join_truth`'s docstring
> claimed it re-attaches `suppression_type`; it did not, so §13.2 step 8's separation was
> impossible and a declared schema column was unfilled. (3) `_clustered` and `_state_year`
> sampled from an UNORDERED frame, so a seeded draw picked differently per PROCESS and broke
> §16.1's idempotence MUST — caught only by the CLI byte-comparison, invisible to every
> within-process test. Added: a feasible regime that scores nothing records why (rolling_origin
> and cbp_size_gaps mask no QCEW cells and never reach the loop), and
> `include_vintage_comparison` now fails closed as the plan designed. Test cost reduced to a
> shared one-seed invocation; the plan's form cost ~40 minutes on a suite that runs `slow` by
> default.

---

### Task 19: §17.4 row 7 integration, the golden fixture, and the D1 acceptance run

**Files:**
- Create: `tests/integration/test_d1_validation.py`
- Create: `tests/fixtures/validation/validation_metrics_golden.parquet`
- Test: as above

§17.4 row 7 requires an integration test that "generates pseudo-suppression metrics". This task adds
it on the frozen fixture, plus a golden, plus the D1 acceptance run whose numbers go into the
Stage 4 completion stamp.

**The golden gives the plan-10 refusal no end-to-end coverage** — measured, the §17.6 fixture's
missing cells almost all lack a share history, so no refusal fires there. A Stage 4 *mask*, not the
golden, is what moves a refusal count. Record that so a future reader does not assume the golden
protects the rule.

- [x] **Step 1: Write the acceptance test**

```python
# tests/integration/test_d1_validation.py
from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import load_config
from logging_employment.contracts import (
    VALIDATION_METRIC_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from logging_employment.validate.harness import run_pseudo_suppression

pytestmark = pytest.mark.slow


def test_the_harness_produces_metrics_that_match_the_declared_schema():
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    result = run_pseudo_suppression(data, REGISTRY[:4], cfg)
    validate_frame(result.metrics, VALIDATION_METRIC_SCHEMA, "validation_metrics")
    assert result.metrics["denominator"].null_count() == 0


def test_every_scored_cell_was_actually_masked():
    """The harness must never report a cell it did not hide."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    result = run_pseudo_suppression(data, REGISTRY[:2], cfg)
    assert result.scores["truth"].null_count() == 0
    assert set(result.scores["suppression_type"].unique().to_list()) <= {
        "primary_like", "complementary_like"
    }


def test_a_never_observed_state_never_appears_as_scored():
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    result = run_pseudo_suppression(data, REGISTRY[:2], cfg)
    never = {"02", "10", "15", "32", "38", "50"}
    assert not (set(result.scores["state_fips"].unique().to_list()) & never)


def test_one_metric_row_is_reproducible_from_the_scores():
    """Derived, not typed. Recompute a WAPE from `validation_scores` and match the metric row."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    result = run_pseudo_suppression(data, REGISTRY[:2], cfg)
    row = result.metrics.filter(pl.col("metric_name") == "wape").row(0, named=True)
    subset = result.scores.filter(
        (pl.col("regime") == row["regime"])
        & (pl.col("seed") == row["seed"])
        & (pl.col("estimator_id") == row["estimator_id"])
        & pl.col("estimate").is_not_null()
    )
    expected = float(
        (subset["estimate"] - subset["truth"]).abs().sum() / subset["truth"].abs().sum()
    )
    assert abs(row["value"] - expected) < 1e-9
```

- [x] **Step 2: Run it**

Run: `uv run pytest tests/integration/test_d1_validation.py -v -m slow`
Expected: 4 passed.

- [x] **Step 3: Record the D1 acceptance numbers**

Run the full harness and capture, for the Stage 4 completion stamp: regimes run, regimes refused
with reasons, replicates, cells masked, the preferred baseline per regime, and the own/fallback
split per estimator. **These are dated measurements** — record them in the stamp and the manifest,
not in an assertion.

- [x] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: all pass.

- [x] **Step 5: Commit**

```bash
git add tests/integration/test_d1_validation.py tests/fixtures/validation
git commit -m "test(validate): §17.4 row 7 integration and the D1 validation acceptance run"
```

> Deviation: Task 19 lists a golden in its Files block but no step builds one, so it follows this
> repo's `test_baseline_golden.py` convention — the in-git `tests/fixtures/baselines/`, at
> `replicates_per_regime: 3` because at 20 the 12-month fixture trips the single-month lookback
> guard (`concentration_proxy` would mask 7 of 12 months for state 12). Both integration modules
> cache their run at module scope on a one-seed config; the plan's per-test three-seed form took
> 6:29 for four tests.

---

## D1 acceptance run (Task 19 Step 3)

**Dated measurements, 2026-09-07, `runs/f03023ac9f3a`.** Recorded here and in
`validation_manifest.json`, never asserted — the ANTI-DRIFT RULE binds these as hard as it binds
the plan's own numbers.

Command: `logging-estimates validate --config config.yaml`, full `REGISTRY` (10 estimators), three
seeds (1024 / 2048 / 4096). Wall clock **11:03**. Outputs: 12,530 scored rows, 4,536 metric rows,
27 distinct MASKED `constraint_set_hash` values (one per replicate, per evidence §10).

| regime | disposition | replicates | scored | preferred baseline |
|---|---|---|---|---|
| small_cell_biased | feasible | 3 | 600 | cbp_intensity |
| concentration_proxy | feasible | 3 | 600 | cbp_intensity |
| clustered_states_within_month | feasible | 3 | 600 | share_last_observed |
| long_consecutive_runs | feasible | 3 | 360 | equal_residual |
| whole_state_year_blocks | feasible | 3 | 360 | cbp_intensity |
| regional_blocks | feasible | 3 | 120 | share_last_observed |
| whole_seasonal_blocks | feasible | 3 | 8,690 | cbp_intensity |
| structural_break | feasible | 3 | 600 | cbp_intensity |
| naics_transition | feasible | 3 | 600 | cbp_intensity |
| rolling_origin | feasible | 0 | 0 | — (masks no QCEW cell; reason recorded) |
| cbp_size_gaps | feasible | 0 | 0 | — (masks no QCEW cell; reason recorded) |
| retrospective_smoothing | vacuous_on_registry | 0 | 0 | — (no smoothing estimator in §10) |
| preliminary_to_final_vintage | cannot_run_on_d1 | 0 | 0 | — (no second snapshot) |

**Exit criteria.**

- §13.2 step 6's rejection FIRES, on the only arm where it can: masking one size class in 2017-03
  — the sole fully observed March margin — gives `exactly_recoverable` at [12144, 12144] against a
  truth of 12144; masking two gives `partially_identified` at [8910, 16038] with the truth (11823)
  strictly inside. `tests/integration/test_validate_exact_recovery.py`. A state-total test would
  have passed vacuously forever.
- A rolling-origin frame provably contains no future rows:
  `tests/unit/test_validate_temporal_regimes.py` over `assert_no_future_rows`, on the TRUNCATED
  frame rather than a mask.
- Every command writes a machine-readable manifest and is idempotent for identical inputs (§16.1):
  `tests/integration/test_validate_cli.py`. The idempotence half failed on the first run and is
  the only test that could have — see the Task 18 deviation.

**Read with the denominators.** `equal_residual` heads `long_consecutive_runs` while §10.8
deliberately leaves equal allocation out of its four-rung ordering; that collision is unresolved
and deferred, not silently settled here. Two regimes report `feasible / scored=0` because they mask
no QCEW cell, each with a recorded `reason`. `whole_seasonal_blocks`' 8,690 rows dominate the score
count and are one calendar month across eight years, not a broader design.

---

## Self-Review

**1. Spec coverage.**

| Spec | Task |
|---|---|
| §10.7 empirical intervals | 15 |
| §13.1 three validation targets | 19 (target 3's limitation stated in the scoreboard) |
| §13.2 generator steps 1–8 | 3, 5, 6, 7, 8 |
| §13.3 thirteen regimes | 10, 11, 12 |
| §13.4 leakage controls | 9 (three bullets bindable; two recorded as unbindable) |
| §13.5 bound metrics | 13 |
| §13.6 point metrics | 14 |
| §13.7 probabilistic metrics | 15 |
| §13.8 constraint metrics + R-COMP-10 | 16 |
| §13.10 promotion gates (mechanism) | 1 (`PromotionConfig`); applied in Stage 5 |
| §15.1 item 5 `validation_metrics.parquet` | 2, 18 |
| §16.1 `validate` CLI | 18 |
| §16.2 `run_pseudo_suppression` | 18 |
| §17.4 row 7 | 19 |
| Appendix A `validation:` / `promotion:` | 1 |

**2. Known gaps, stated rather than hidden.**
- §13.3 regime 12 (`preliminary_to_final_vintage`) **cannot run** — no second vintage exists.
  Refused, not skipped; Appendix A's default is overridden with the measurement as the reason.
- §13.3 regime 9 (`retrospective_smoothing`) is **vacuous on the §10 registry** — no smoothing
  estimator exists to exercise. Surfaced as a scope decision, not silently implemented.
- §13.4 bullets 4 and 5 have no surface to bind to until Stage 5 and a second vintage exist.
- §13.9's ablations belong to Stage 7, which reuses this harness; they are not in scope here.

**3. Type consistency.** `MaskTarget`, `MaskedSystem`, `RegimeSpec` and `ValidationResult` are
defined once and used under those names throughout. `run_baselines`' new keyword is `estimators`
everywhere. `size_class`/`employment` are used for `qcew_national_size` and
`size_code`/`employment_value` for `qcew_monthly` — these tables do **not** share a vocabulary.

**4. Verified-by-running.** The following code in this plan was executed against the real staged
data on 2026-09-07 before being written down: `apply_mask` (all seven field flips, the truth
capture, both refusals), the leave-one-out propensity (including its leakage test), `mask_and_solve`
(0.049 s build / 0.312 s solve, masked cell `unbounded`), the national-size arm (k=1 →
`exactly_recoverable` at (8288, 8288); k=2 → `partially_identified` with truth inside), the panel
facts (272 / 50 / 6 / 40, DC absent), the Census-division partition (51 codes, exact cover of
`STATES_DC_FIPS`), and the CRPS, interval and WAPE arithmetic. 45 of the plan's 50 Python blocks
parse standalone; the other 5 are deliberate patch fragments (a signature, a loop line, fields to
insert into an existing class).

**Four defects were found this way and fixed before the plan shipped:**

1. `HarmonizedData.load` requires a `Path`, not a `str` — the test helper would have raised.
2. `qcew_national_size` uses `size_class` / `employment` / `establishments` where `qcew_monthly`
   uses `size_code` / `employment_value` / `qtrly_establishments`. The original Task 8 mask would
   have matched **zero rows and masked nothing**, silently.
3. The pooled-statistics propensity **failed its own leakage test**: a per-state mean and standard
   deviation include the target's own month, so perturbing a cell moved that cell's propensity.
   Replaced with leave-one-out sums, which pass.
4. `build_scoreboard` **selected** the own/fallback columns off point rows. `point_metrics` and
   `decline_and_basis_report` emit disjoint column sets and the harness concatenates them
   diagonally, so `n_own_estimator` came back null on **every** scoreboard row — silently deleting
   the one signal that makes §10.3 variant 5's composed refusals visible, which this plan calls
   load-bearing three times. Replaced with a join on `(regime, seed, estimator_id)`, and Task 17
   now builds its fixture from the emitters rather than by hand, plus carries an explicit
   regression test.

Defect 4 is the reason Task 17's fixture rule matters generally: a hand-built metrics frame is a
frame the harness never produces, and it will pass while the wiring is broken.

---

## Execution Handoff

**Plan complete and saved to `specs/plans/11-stage4-logging-employment-spec.md`.**

**Recommended: `/clear` (or open a new session) and execute against the saved plan** — a fresh
session drops this planning conversation and lets execution run on the standard model default.
Two execution options, either session:

1. **Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks.
2. **Inline Execution** — tasks executed in plan order in one session (`executing-plans`).

**Which approach?**
