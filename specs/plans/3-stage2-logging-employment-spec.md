# Stage 2: Deterministic Identification Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via
> subagent-driven-development (the default) — or executing-plans when your human partner chose
> inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage 2 — on plan completion, tick the stage
> and re-validate later stages against what shipped.

**Goal:** Turn the harmonized QCEW tables into a sparse public-accounting constraint system and
compute sharp LP/MILP bounds, rank, components, and infeasibility diagnostics for every suppressed
target cell.

**Architecture:** A `constraints/` subpackage builds an immutable `ConstraintSystem` (cells, rows,
sparse coefficients) from the Stage 1 harmonized Parquet, decomposes it into connected components,
computes structural and numerical rank per component, and solves two HiGHS optimizations per
unknown cell to obtain sharp feasible bounds. Nothing predictive enters: no history, no proxies,
no priors (§9.1). A `disclosure/flags.py` module reads the bounds and raises the two Stage 2 flags.
Two CLI commands (`build-constraints`, `solve-bounds`) persist the four Parquet tables and a
manifest, both idempotent for identical inputs.

**Tech Stack:** Python ≥ 3.14, uv + hatchling, Polars, HiGHS via `highspy`, SciPy sparse
(`connected_components`, `structural_rank`), NumPy, Typer, pytest.

---

## What the evidence already settles

Read this section before Task 1. Three measured facts from Stage 0 and Stage 1 determine what this
engine can and cannot do, and an implementer who does not know them will build the wrong thing.

**1. There is no national employment margin. `SRC-QCEW-006` came back `decline`.**
`specs/findings/source-audit.md` states the consequence in one sentence: *"Stage 2 therefore MUST
NOT create a national employment margin constraint out of this identity."* The reason is
unverifiability, not geography — every one of the window's 96 months carries between 9 and 15
suppressed states+DC cells, so no month ever offered a complete published state sum to test the
identity against. The establishment identity does close exactly (32 of 32 quarters), but every
establishment cell is published, so it constrains no unknown.

The consequence for this stage is blunt and must not be softened: **every one of the 1,227
suppressed state-month employment cells is bounded below by 0 and not bounded above at all.** They
will come back `bound_status = 'unbounded'`. That is the honest deterministic answer and it is
exactly why Stages 3–5 exist. Do not invent a cap to make the output look better; §9.3 forbids
"arbitrary top-class caps" by name.

**2. The identifying content lives in `qcew_national_size`.** Filtered to 113310 the window holds
51 rows: 37 observed and 14 suppressed, in the 7 years 2018–2024 (2017 has none). Each year's size
classes sum to the published national all-sizes total from `qcew_monthly`, and each suppressed
class publishes its establishment count. That is a real margin over real unknowns, and it is where
the LP does work.

**3. The size-support rule is measured, not assumed.** A class titled "50 to 99 employees per
establishment" holding `n` establishments implies class employment in `[n·50, n·99]` — §9.3's
"documented size support at the valid reference period". This was verified against published data
before this plan was written: **all 37 observed rows satisfy `n·lower ≤ employment ≤ n·upper`**,
with no violations on either side. Task 4 re-runs that check in code as a fail-closed gate, so the
premise stays measured rather than becoming folklore. If a future vintage breaks it, the run halts
rather than shipping a hard constraint that published data contradicts.

**The bounds this produces are known in advance.** These are the sharp LP bounds implied by
(margin, support, nonnegativity), computed analytically from the staged tables while this plan was
written, and reproduced by HiGHS. Task 16 asserts them.

| Year | Residual | Suppressed classes | Support | Sharp bounds | Width |
|---|---|---|---|---|---|
| 2017 | 0 | none | — | — | — |
| 2018 | 3884 | 5, 6 | [2300, 4554], [900, 2241] | [2300, 2984], [900, 1584] | 684 |
| 2019 | 3904 | 5, 6 | [2450, 4851], [600, 1494] | [2450, 3304], [600, 1454] | 854 |
| 2020 | 3901 | 5, 6 | [2400, 4752], [600, 1494] | [2407, 3301], [600, 1494] | 894 |
| 2021 | 3519 | 5, 6 | [2250, 4455], [500, 1245] | [2274, 3019], [500, 1245] | 745 |
| 2022 | 803 | 6, 7 | [400, 996], [250, 499] | [400, 553], [250, 403] | 153 |
| 2023 | 1134 | 6, 7 | [700, 1743], [250, 499] | [700, 884], [250, 434] | 184 |
| 2024 | 780 | 6, 7 | [400, 996], [250, 499] | [400, 530], [250, 380] | 130 |

Two consequences follow, and both belong in the plan rather than in a surprised implementer's
report at Task 16:

- **`exact_reconstruction_flag` cannot fire on real D1 data.** No year has exactly one suppressed
  class — it is zero in 2017 and two in each of the other seven. Exact recovery is exercised on the
  toy and golden fixtures only (Task 15). Do not treat its absence at Task 16 as a defect.
- **`narrow_feasible_interval_flag` fires once**, on 2023 class 6: width 184 against a midpoint of
  792, a relative width of 0.232, which clears the 0.25 threshold fixed in Global Constraints. Every
  other real cell is wider in both absolute and relative terms.

---

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the
spec's Rollout note, Stage 0's finding, and Stage 1's stage stamp.

- **D1 Historical period:** pilot `2017-01` → `2024-12`, as in Appendix A. Eight reference years.
- **D2 Scope ceiling:** Phases 0–5 are in scope. This stage is Phase 2a.
- **D4 Toolchain:** one installable package, `src/logging_employment/`, hatchling + uv,
  `requires-python >= 3.14`, ruff and black at line length 100, pytest markers `network` and
  `slow`, interrogate at 100%. `highspy` and `scipy` were already checked for CPython 3.14 wheels
  by plan 2 (highspy 1.15.1, scipy 1.18.1, both resolved and installed as wheels). **Do not repeat
  that check.**
- **This stage is offline.** No task fetches anything. Every input is Stage 1 harmonized Parquet.
  No task carries the `network` marker.
- **`qcew_monthly` is already universe-filtered.** Stage 1's stamp: private ownership, states+DC
  and the national row only. **Do not re-apply REQ-002.** A Puerto Rico or county row appearing
  downstream is a bug, not data.
- **`qcew_national_size` carries every industry — 140,343 rows, ~99% of them not Logging.** Every
  read of that table filters to `cfg.project.industry_code_used` **first**. There is no task in
  which the unfiltered table is the right input.
- **`harmonize.universe.assert_definitional_alignment(qcew_monthly)` MUST be called before any
  constraint is created.** Stage 1 deliberately left it out of the build path because it guards
  constraint construction, not ingestion (SRC-QCEW-007). Task 4 is where it is called.
- **No national employment margin, in any form.** Not hard, not soft, not as a recorded
  `modeling_assumption` row for a later stage to pick up. Stage 3 names its own substitute anchor.
- **Narrowness threshold (resolves the §21 "Disclosure thresholds" row):** a feasible interval is
  narrow when its width is `<= 10` employees **or** its width divided by its midpoint is `<= 0.25`.
  These ship as `disclosure.narrow_interval_absolute_width` and
  `disclosure.narrow_interval_relative_width` in `config.yaml`. **They are not
  `constraints.use_milp_when_lp_interval_width_below`** — that is a solver switch, and reusing it
  would turn a performance knob into privacy policy.
- **Non-goal: do not amend Stage 1's schemas.** `QCEW_NATIONAL_SIZE_SCHEMA` has no
  `ownership_code` column and §7.4 does not list one. The ownership universe of the size table is
  established by the Task 4 gate, not by adding a column and re-running the Stage 1 build.
- **Base branch.** This plan assumes Stage 1 is merged and `src/logging_employment/contracts.py`
  exists on the branch you start from. Task 1 Step 1 verifies that; if it fails, stop and merge
  `stage1-foundation-ingestion` before continuing.

---

## File structure

| Path | Responsibility |
|---|---|
| `src/logging_employment/constraints/__init__.py` | Package marker. |
| `src/logging_employment/constraints/cells.py` | `target_cell` construction and `cell_id` format. |
| `src/logging_employment/constraints/compat.py` | The two fail-closed compatibility gates (§5.5, INV-007). |
| `src/logging_employment/constraints/rows.py` | The row factory, its three negative guards, and every constraint builder. |
| `src/logging_employment/constraints/system.py` | `ConstraintSystem`, `build_constraint_system`, `constraint_set_hash`. |
| `src/logging_employment/constraints/graph.py` | CON-001/002: bipartite graph and connected components. |
| `src/logging_employment/constraints/rank.py` | CON-003/005: structural and numerical rank, nullity, hierarchy cache. |
| `src/logging_employment/constraints/bounds.py` | §9.6: HiGHS LP/MILP bounds, `bound_status` classification, `solve_bounds`. |
| `src/logging_employment/constraints/diagnostics.py` | §9.7: IIS or minimum-slack diagnostics on an infeasible component. |
| `src/logging_employment/disclosure/__init__.py` | Package marker. |
| `src/logging_employment/disclosure/flags.py` | §9.8: the two Stage 2 disclosure flags. |
| `src/logging_employment/runs.py` | Deterministic `run_id` and the `runs/<run_id>/` layout (§6.2). |
| `src/logging_employment/contracts.py` | *Modify:* add the four Stage 2 schemas, the enums, and `HarmonizedData`. |
| `src/logging_employment/config.py` | *Modify:* add `ConstraintsConfig` and `DisclosureConfig`. |
| `src/logging_employment/errors.py` | *Modify:* add three fail-closed errors. |
| `src/logging_employment/cli.py` | *Modify:* add `build-constraints` and `solve-bounds`. |
| `config.yaml` | *Modify:* add the `constraints:` and `disclosure:` blocks. |
| `pyproject.toml` | *Modify:* add `highspy` and `scipy`. |
| `tests/unit/test_constraint_cells.py` … | One unit module per source module. |
| `tests/unit/test_constraint_properties.py` | The eight §17.2 property tests on toy tables. |
| `tests/integration/test_constraint_engine.py` | §17.4 row 3 and the §17.6 golden bounds. |
| `tests/integration/test_d1_acceptance.py` | The full-window run, `slow`, skipped without `data/staged/`. |

`constraints/system.py` is not in §6.1's suggested module list. It is added because §16.2 names
`ConstraintSystem` and `build_constraint_system` as one interface and neither `cells.py` nor
`rows.py` is their natural home; §6.1 is a recommendation, not a contract.

---

### Task 1: Dependencies, the `constraints:` and `disclosure:` config blocks, and the base guard

**Files:**
- Modify: `pyproject.toml` (dependencies)
- Modify: `src/logging_employment/config.py`
- Modify: `config.yaml`
- Test: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: Stage 1's `Config`, `_Strict`, `load_config` from `src/logging_employment/config.py`.
- Produces: `ConstraintsConfig` with fields `enforce_integrality: bool`,
  `use_milp_when_lp_interval_width_below: float`, `solver: Literal["highs"]`,
  `feasibility_tolerance: float`, `rank_tolerance: float`; `DisclosureConfig` with
  `exact_reconstruction_action: str`, `narrow_interval_action: str`, `publish_label_required: bool`,
  `narrow_interval_absolute_width: float`, `narrow_interval_relative_width: float`; and two new
  required attributes `Config.constraints` and `Config.disclosure`.

- [ ] **Step 1: Verify you are on a base that carries Stage 1**

```bash
test -f src/logging_employment/contracts.py \
  && test -f src/logging_employment/harmonize/universe.py \
  && echo "BASE OK" || echo "BASE MISSING — merge stage1-foundation-ingestion first"
```

Expected: `BASE OK`. If it prints the other line, stop: this plan consumes Stage 1's harmonized
layer and nothing here works without it.

- [ ] **Step 2: Write the failing test**

Append to `tests/unit/test_config.py`. First extend the module's existing `APPENDIX_A` constant by
adding these two blocks to the end of that string — Appendix A ships both, so the constant was
incomplete for its own name:

```python
APPENDIX_A = APPENDIX_A + """
constraints:
  enforce_integrality: true
  use_milp_when_lp_interval_width_below: 25
  solver: 'highs'
  feasibility_tolerance: 1.0e-7
  rank_tolerance: 1.0e-10
disclosure:
  exact_reconstruction_action: 'withhold'
  narrow_interval_action: 'manual_review'
  publish_label_required: true
  narrow_interval_absolute_width: 10
  narrow_interval_relative_width: 0.25
"""
```

Then add the tests:

```python
def test_the_constraints_block_parses_with_appendix_a_values(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.constraints.enforce_integrality is True
    assert cfg.constraints.solver == "highs"
    assert cfg.constraints.use_milp_when_lp_interval_width_below == 25
    assert cfg.constraints.feasibility_tolerance == 1.0e-7
    assert cfg.constraints.rank_tolerance == 1.0e-10


def test_the_narrowness_thresholds_are_separate_keys_from_the_milp_switch(tmp_path: Path) -> None:
    # The §21 "Disclosure thresholds" row is governance policy; the MILP switch is a solver knob.
    # Reusing one for the other is the failure this test exists to prevent.
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.disclosure.narrow_interval_absolute_width == 10
    assert cfg.disclosure.narrow_interval_relative_width == 0.25
    assert (
        cfg.disclosure.narrow_interval_absolute_width
        != cfg.constraints.use_milp_when_lp_interval_width_below
    )


def test_an_unknown_solver_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("'highs'", "'glpk'")))


def test_the_shipped_config_carries_both_new_blocks() -> None:
    cfg = load_config(Path(__file__).resolve().parents[2] / "config.yaml")
    assert cfg.constraints.solver == "highs"
    assert cfg.disclosure.narrow_interval_relative_width == 0.25
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL with `AttributeError: 'Config' object has no attribute 'constraints'` on the new
tests, and `ValidationError: Extra inputs are not permitted` on the pre-existing ones (the extended
`APPENDIX_A` now carries blocks `Config` does not model).

- [ ] **Step 4: Add the two dependencies**

```bash
uv add highspy scipy
```

Expected: `pyproject.toml` gains `highspy` and `scipy` under `[project] dependencies`, and
`uv.lock` updates. Both were checked for CPython 3.14 wheels by plan 2 (highspy 1.15.1, scipy
1.18.1); do not re-verify.

- [ ] **Step 5: Add the two config models**

In `src/logging_employment/config.py`, after `SourcesConfig`:

```python
class ConstraintsConfig(_Strict):
    """The deterministic engine's solver settings (Appendix A `constraints:`).

    `use_milp_when_lp_interval_width_below` is a *performance* switch: it decides when an integer
    re-solve is worth its cost, never whether a cell is disclosive. The disclosure thresholds live
    in `DisclosureConfig` and are a governance decision (§21).
    """

    enforce_integrality: bool
    use_milp_when_lp_interval_width_below: float
    solver: Literal["highs"]
    feasibility_tolerance: float
    rank_tolerance: float


class DisclosureConfig(_Strict):
    """Disclosure actions and the narrowness thresholds (Appendix A `disclosure:`, §21).

    The two width keys resolve §21's "Disclosure thresholds" row, which the spec leaves to the
    governance owner. A cell is narrow when its feasible width is at most
    `narrow_interval_absolute_width` employees, or when width divided by midpoint is at most
    `narrow_interval_relative_width`. §14.2 asks for both an absolute and a relative test, so both
    are configured and either one alone is sufficient to route a cell to review.
    """

    exact_reconstruction_action: Literal["withhold", "manual_review", "release"]
    narrow_interval_action: Literal["withhold", "manual_review", "release"]
    publish_label_required: bool
    narrow_interval_absolute_width: float
    narrow_interval_relative_width: float
```

Then extend `Config`:

```python
class Config(_Strict):
    """The whole resolved configuration."""

    project: ProjectConfig
    storage: StorageConfig
    sources: SourcesConfig
    constraints: ConstraintsConfig
    disclosure: DisclosureConfig
```

- [ ] **Step 6: Add both blocks to `config.yaml`**

Extract the two Appendix A blocks rather than retyping them, then append the two governance keys:

```bash
{ echo; sed -n '2065,2070p' specs/logging-employment-spec.md; \
  echo; sed -n '2105,2108p' specs/logging-employment-spec.md; \
  echo "  # Resolves §21's \"Disclosure thresholds\" row: policy, not evidence. See plan 3."; \
  echo "  narrow_interval_absolute_width: 10"; \
  echo "  narrow_interval_relative_width: 0.25"; } >> config.yaml
head -c 0 /dev/null && sed -n '/^constraints:/,$p' config.yaml
```

Expected: the tail of `config.yaml` now reads exactly the `constraints:` block from Appendix A,
then the `disclosure:` block with its three Appendix A keys plus the two width keys.

- [ ] **Step 7: Run the full unit suite**

Run: `uv run pytest tests/unit -q`
Expected: PASS. Nothing outside `test_config.py` reads either new block yet.

- [ ] **Step 8: Stamp the spec**

Add this line to the `### Stage stamps` list in `specs/logging-employment-spec.md`'s Rollout note,
after Stage 1's block, matching the wording the roadmap's "Stage-spec stamp" section prescribes:

```markdown
- Roadmap: specs/logging-employment-spec-roadmap.md, Stage 2 — on plan completion, tick the stage and re-validate later stages against what shipped.
```

It lands here rather than at plan-writing time because Stage 1's stamps live on
`stage1-foundation-ingestion`, and adding Stage 2's before that merge would conflict.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock config.yaml src/logging_employment/config.py tests/unit/test_config.py specs/logging-employment-spec.md
git commit -m "feat(config): add the constraints and disclosure blocks, and the HiGHS dependency

The two narrowness widths resolve §21's disclosure-thresholds row, which the spec
leaves to the governance owner. They are deliberately separate keys from
constraints.use_milp_when_lp_interval_width_below, which is a solver switch.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Stage 2 table contracts, enums, and `HarmonizedData`

**Files:**
- Modify: `src/logging_employment/contracts.py`
- Modify: `src/logging_employment/errors.py`
- Test: `tests/unit/test_contracts.py`

**Interfaces:**
- Consumes: `schema_fingerprint`, `validate_frame`, `SchemaMismatchError` from Stage 1's
  `contracts.py`; `LoggingEmploymentError` from `errors.py`.
- Produces: `TARGET_CELL_SCHEMA`, `CONSTRAINT_ROW_SCHEMA`, `CONSTRAINT_COEFFICIENT_SCHEMA`,
  `DETERMINISTIC_BOUNDS_SCHEMA` (all `dict[str, pl.DataType]`); the tuples `CONSTRAINT_CLASSES`,
  `HARD_ELIGIBLE_CLASSES`, `RELATIONS`, `BOUND_STATUSES`, `EVIDENCE_KINDS`; the frozen dataclass
  `HarmonizedData` with fields `qcew_monthly`, `qcew_national_size`, `cbp_state_size`, `bridge`
  and classmethod `load(staged_root: Path) -> HarmonizedData`; and the errors
  `IncompatibleMarginError`, `InfeasibleComponentError`, `HardConstraintClassError`,
  `SolverError`.

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_contracts.py`:

```python
import polars as pl
import pytest

from logging_employment.contracts import (
    BOUND_STATUSES,
    CONSTRAINT_CLASSES,
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    DETERMINISTIC_BOUNDS_SCHEMA,
    EVIDENCE_KINDS,
    HARD_ELIGIBLE_CLASSES,
    RELATIONS,
    TARGET_CELL_SCHEMA,
    HarmonizedData,
    schema_fingerprint,
)


def test_the_four_schemas_carry_exactly_the_fields_the_spec_lists() -> None:
    assert list(TARGET_CELL_SCHEMA) == [
        "cell_id", "state_fips", "reference_month", "size_concept", "size_class",
        "ownership_code", "industry_code", "naics_vintage", "observation_status",
        "observed_value", "source_snapshot_id", "qcew_disclosure_code",
    ]
    assert list(CONSTRAINT_ROW_SCHEMA) == [
        "constraint_id", "component_id", "constraint_class", "relation", "rhs_lower",
        "rhs_upper", "is_hard", "period_scope", "geography_scope", "industry_scope",
        "ownership_scope", "source_snapshot_ids", "provenance_text",
        "vintage_compatibility_status",
    ]
    assert list(CONSTRAINT_COEFFICIENT_SCHEMA) == ["constraint_id", "cell_id", "coefficient"]
    assert list(DETERMINISTIC_BOUNDS_SCHEMA) == [
        "cell_id", "component_id", "rank", "nullity", "lp_lower", "lp_upper", "milp_lower",
        "milp_upper", "selected_lower", "selected_upper", "bound_status", "exactly_identified",
        "integer_exactly_identified", "solver_status", "solver_tolerance", "constraint_set_hash",
    ]


def test_only_the_first_two_constraint_classes_may_be_hard() -> None:
    # §7.8: "Only the first two may have is_hard=true."
    assert CONSTRAINT_CLASSES == (
        "public_accounting_fact",
        "definitional_support",
        "empirical_measurement",
        "modeling_assumption",
        "sensitivity_assumption",
    )
    assert HARD_ELIGIBLE_CLASSES == CONSTRAINT_CLASSES[:2]


def test_the_seven_bound_statuses_are_the_ones_7_10_suggests() -> None:
    assert BOUND_STATUSES == (
        "observed",
        "exactly_recoverable",
        "partially_identified",
        "model_estimable",
        "model_only",
        "unbounded",
        "infeasible",
    )


def test_an_assumed_threshold_is_an_evidence_kind_so_it_can_be_refused_by_name() -> None:
    assert "assumed_threshold" in EVIDENCE_KINDS
    assert RELATIONS == ("eq", "le", "ge", "range", "integrality")


def test_harmonized_data_loads_the_four_stage_one_tables(tmp_path) -> None:
    for name, schema in (
        ("qcew_monthly", {"reference_month": pl.String}),
        ("qcew_national_size", {"reference_year": pl.Int64}),
        ("cbp_state_size", {"reference_year": pl.Int64}),
        ("bridge", {"bridge_id": pl.String}),
    ):
        pl.DataFrame(schema=schema).write_parquet(tmp_path / f"{name}.parquet")
    data = HarmonizedData.load(tmp_path)
    assert data.qcew_monthly.height == 0
    assert data.bridge.columns == ["bridge_id"]


def test_a_missing_harmonized_table_names_the_path_rather_than_raising_from_polars(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="qcew_monthly.parquet"):
        HarmonizedData.load(tmp_path)


def test_the_new_schemas_have_distinct_fingerprints() -> None:
    prints = {
        schema_fingerprint(s)
        for s in (
            TARGET_CELL_SCHEMA,
            CONSTRAINT_ROW_SCHEMA,
            CONSTRAINT_COEFFICIENT_SCHEMA,
            DETERMINISTIC_BOUNDS_SCHEMA,
        )
    }
    assert len(prints) == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_contracts.py -v`
Expected: FAIL with `ImportError: cannot import name 'TARGET_CELL_SCHEMA'`.

- [ ] **Step 3: Add the schemas, enums, and `HarmonizedData`**

Append to `src/logging_employment/contracts.py` (and add `from dataclasses import dataclass` and
`from pathlib import Path` to its imports):

```python
# §7.8's five constraint classes, in the spec's own order. The order is load-bearing: §7.8 says
# "Only the first two may have is_hard=true", so `HARD_ELIGIBLE_CLASSES` is a slice of this tuple
# rather than a second literal that could drift away from it.
CONSTRAINT_CLASSES: tuple[str, ...] = (
    "public_accounting_fact",
    "definitional_support",
    "empirical_measurement",
    "modeling_assumption",
    "sensitivity_assumption",
)
HARD_ELIGIBLE_CLASSES: tuple[str, ...] = CONSTRAINT_CLASSES[:2]

# §7.8 does not enumerate `relation`, so these five are this package's decision. `integrality` is
# not a relation in the algebraic sense; it is here because INV-004 requires *every* restriction to
# carry a label, and a restriction recorded only as a column attribute would carry none.
RELATIONS: tuple[str, ...] = ("eq", "le", "ge", "range", "integrality")

# §7.10's suggested `bound_status` values, verbatim. Stage 2 emits five of the seven: it never
# emits `model_estimable` or `model_only`, because deciding that a cell is estimable requires a
# model and §9.1 forbids one at this stage.
BOUND_STATUSES: tuple[str, ...] = (
    "observed",
    "exactly_recoverable",
    "partially_identified",
    "model_estimable",
    "model_only",
    "unbounded",
    "infeasible",
)

# What licenses a constraint, as a closed set rather than free prose. §7.8 has no column for it, so
# the row factory writes it into `provenance_text` behind an `evidence_kind=` prefix. It exists so
# that §9.3's forbidden forms can be refused *by name*: a restriction whose warrant is an assumed
# disclosure threshold can never be hard, whatever class a caller asks for.
EVIDENCE_KINDS: tuple[str, ...] = (
    "published_value",
    "class_definition",
    "unit_definition",
    "rounding_documentation",
    "empirical_fit",
    "assumed_threshold",
)
EVIDENCE_PREFIX = "evidence_kind="

TARGET_CELL_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "state_fips": pl.String,
    "reference_month": pl.String,
    "size_concept": pl.String,
    "size_class": pl.String,
    "ownership_code": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "observation_status": pl.String,
    "observed_value": pl.Int64,
    "source_snapshot_id": pl.String,
    "qcew_disclosure_code": pl.String,
}

CONSTRAINT_ROW_SCHEMA: dict[str, pl.DataType] = {
    "constraint_id": pl.String,
    "component_id": pl.String,
    "constraint_class": pl.String,
    "relation": pl.String,
    "rhs_lower": pl.Float64,
    "rhs_upper": pl.Float64,
    "is_hard": pl.Boolean,
    "period_scope": pl.String,
    "geography_scope": pl.String,
    "industry_scope": pl.String,
    "ownership_scope": pl.String,
    "source_snapshot_ids": pl.String,
    "provenance_text": pl.String,
    "vintage_compatibility_status": pl.String,
}

CONSTRAINT_COEFFICIENT_SCHEMA: dict[str, pl.DataType] = {
    "constraint_id": pl.String,
    "cell_id": pl.String,
    "coefficient": pl.Float64,
}

DETERMINISTIC_BOUNDS_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "component_id": pl.String,
    "rank": pl.Int64,
    "nullity": pl.Int64,
    "lp_lower": pl.Float64,
    "lp_upper": pl.Float64,
    "milp_lower": pl.Float64,
    "milp_upper": pl.Float64,
    "selected_lower": pl.Float64,
    "selected_upper": pl.Float64,
    "bound_status": pl.String,
    "exactly_identified": pl.Boolean,
    "integer_exactly_identified": pl.Boolean,
    "solver_status": pl.String,
    "solver_tolerance": pl.Float64,
    "constraint_set_hash": pl.String,
}

_HARMONIZED_TABLES = ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge")


@dataclass(frozen=True)
class HarmonizedData:
    """The Stage 1 harmonized layer, as §16.2's `build_constraint_system` receives it.

    Every downstream stage reads only this layer, never a source endpoint. Loading is eager and
    fails on the first missing file rather than deferring to a Polars error at first use, so a run
    started before `build-harmonized` halts with the path it wanted.
    """

    qcew_monthly: pl.DataFrame
    qcew_national_size: pl.DataFrame
    cbp_state_size: pl.DataFrame
    bridge: pl.DataFrame

    @classmethod
    def load(cls, staged_root: Path) -> "HarmonizedData":
        """Read the four Stage 1 tables from a `data/staged`-shaped directory."""
        frames = {}
        for name in _HARMONIZED_TABLES:
            path = staged_root / f"{name}.parquet"
            if not path.exists():
                raise FileNotFoundError(
                    f"{path} is missing; run `logging-estimates build-harmonized` first"
                )
            frames[name] = pl.read_parquet(path)
        return cls(**frames)
```

Append to `src/logging_employment/errors.py`:

```python
class IncompatibleMarginError(LoggingEmploymentError):
    """Two source margins failed the §5.5 compatibility gate and must not be stacked (INV-007)."""


class InfeasibleComponentError(LoggingEmploymentError):
    """A constraint component has no feasible point; §9.6 forbids silently relaxing it."""


class HardConstraintClassError(LoggingEmploymentError):
    """A caller asked for `is_hard=true` on a restriction that is not eligible for it."""


class SolverError(LoggingEmploymentError):
    """The solver returned a status that is neither an optimum nor a recognised refusal."""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_contracts.py -v`
Expected: PASS, all tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/contracts.py src/logging_employment/errors.py tests/unit/test_contracts.py
git commit -m "feat(contracts): declare the four Stage 2 tables, their enums, and HarmonizedData

HARD_ELIGIBLE_CLASSES is a slice of CONSTRAINT_CLASSES rather than a second
literal, so §7.8's 'only the first two' cannot drift. EVIDENCE_KINDS exists so
§9.3's forbidden warrants can be refused by name rather than by review.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: The target-cell index

**Files:**
- Create: `src/logging_employment/constraints/__init__.py`
- Create: `src/logging_employment/constraints/cells.py`
- Create: `tests/unit/conftest.py`
- Test: `tests/unit/test_constraint_cells.py`

**Interfaces:**
- Consumes: `HarmonizedData`, `TARGET_CELL_SCHEMA` (Task 2); `QCEW_MONTHLY_SCHEMA`,
  `QCEW_NATIONAL_SIZE_SCHEMA`, `ConceptViolationError` (Stage 1).
- Produces: the constants `KIND_STATE_TOTAL = "state_total"`,
  `KIND_NATIONAL_TOTAL = "national_total"`, `KIND_NATIONAL_SIZE = "national_size"`,
  `NATIONAL_STATE_FIPS = "US"`, `TOTAL_SIZE_CLASS = "ALL"`; the function
  `cell_id(kind: str, *, state_fips: str, reference_month: str, ownership_code: str,
  industry_code: str, naics_vintage: str, size_class: str) -> str`; the three builders
  `state_total_cells`, `national_total_cells`, `national_size_cells`; and
  `build_target_cells(data: HarmonizedData, *, industry_code: str, ownership_code: str,
  size_concept: str) -> pl.DataFrame` returning a frame matching `TARGET_CELL_SCHEMA`, sorted by
  `cell_id`.

- [ ] **Step 1: Write the shared test frame factories**

Create `tests/unit/conftest.py`:

```python
"""Frame factories for the Stage 2 unit suite.

A `qcew_monthly` row literal means filling 24 columns, most of which no constraint builder reads.
These factories fill every column, so the frame matches the shipped schema exactly, and let a test
name only the fields its assertion is about.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.contracts import QCEW_MONTHLY_SCHEMA, QCEW_NATIONAL_SIZE_SCHEMA

_MONTHLY_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2024q1",
    "release_vintage": "2024q1",
    "release_status": "final",
    "reference_quarter": "2024Q1",
    "reference_month": "2024-03",
    "area_fips": "01000",
    "area_type": "state",
    "state_fips": "01",
    "industry_code": "113310",
    "naics_vintage": "NAICS 2022",
    "ownership_code": "5",
    "aggregation_level": "58",
    "size_code": "0",
    "qtrly_establishments": 10,
    "employment_raw": "100",
    "employment_value": 100,
    "wages_raw": "1000",
    "wages_value": 1000,
    "disclosure_code": "",
    "observation_status": "observed",
    "is_published_numeric_zero": False,
    "is_true_zero": False,
    "source_row_hash": "deadbeef",
    "suppression_type": "unknown",
}

_SIZE_DEFAULTS: dict[str, object] = {
    "snapshot_id": "2024_q1_by_size",
    "reference_year": 2024,
    "reference_quarter": "2024Q1",
    "reference_month": "2024-03",
    "industry_code": "113310",
    "naics_vintage": "NAICS 2022",
    "size_class": "1",
    "size_lower": 0,
    "size_upper": 4,
    "establishments": 100,
    "employment": 200,
    "disclosure_code": "",
    "observation_status": "observed",
}


@pytest.fixture()
def make_monthly() -> Callable[..., pl.DataFrame]:
    """Build a `qcew_monthly` frame from partial row dicts."""

    def _build(*rows: dict[str, object]) -> pl.DataFrame:
        return pl.DataFrame(
            [_MONTHLY_DEFAULTS | dict(row) for row in rows], schema=QCEW_MONTHLY_SCHEMA
        )

    return _build


@pytest.fixture()
def make_size() -> Callable[..., pl.DataFrame]:
    """Build a `qcew_national_size` frame from partial row dicts."""

    def _build(*rows: dict[str, object]) -> pl.DataFrame:
        return pl.DataFrame(
            [_SIZE_DEFAULTS | dict(row) for row in rows], schema=QCEW_NATIONAL_SIZE_SCHEMA
        )

    return _build
```

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_constraint_cells.py`:

```python
"""§7.7 target cells: the key, the two families, and what makes them distinguishable."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.constraints import cells
from logging_employment.contracts import TARGET_CELL_SCHEMA, HarmonizedData
from logging_employment.errors import ConceptViolationError


def _data(monthly: pl.DataFrame, size: pl.DataFrame) -> HarmonizedData:
    empty = pl.DataFrame()
    return HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size, cbp_state_size=empty, bridge=empty
    )


def test_the_string_builder_and_the_expression_agree(
    make_monthly: Callable[..., pl.DataFrame]
) -> None:
    frame = make_monthly({})
    built = cells.state_total_cells(frame, size_concept="march_reference")
    assert built["cell_id"][0] == cells.cell_id(
        cells.KIND_STATE_TOTAL,
        state_fips="01",
        reference_month="2024-03",
        ownership_code="5",
        industry_code="113310",
        naics_vintage="NAICS 2022",
        size_class=cells.TOTAL_SIZE_CLASS,
    )


def test_a_state_total_and_a_national_size_cell_never_share_an_id(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # §7.7: "Size cells and total cells MUST have distinct IDs."
    built = cells.build_target_cells(
        _data(
            make_monthly({}, {"area_fips": "US000", "area_type": "national", "state_fips": None}),
            make_size({}),
        ),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert built["cell_id"].n_unique() == built.height == 3
    kinds = {cid.split("|")[0] for cid in built["cell_id"]}
    assert kinds == {"state_total", "national_total", "national_size"}


def test_a_national_cell_carries_US_rather_than_a_null_state_fips(
    make_monthly: Callable[..., pl.DataFrame]
) -> None:
    # A null would be indistinguishable from a missing value in a join; "US" cannot collide with
    # any two-character FIPS.
    built = cells.national_total_cells(
        make_monthly({"area_fips": "US000", "area_type": "national", "state_fips": None}),
        size_concept="march_reference",
        reference_months=["2024-03"],
    )
    assert built["state_fips"].to_list() == ["US"]


def test_a_suppressed_cell_carries_a_null_value_and_a_true_zero_carries_zero(
    make_monthly: Callable[..., pl.DataFrame]
) -> None:
    built = cells.state_total_cells(
        make_monthly(
            {"state_fips": "02", "observation_status": "suppressed", "employment_value": None,
             "disclosure_code": "N"},
            {"state_fips": "04", "observation_status": "true_zero", "employment_value": 0,
             "disclosure_code": "-"},
        ),
        size_concept="march_reference",
    )
    by_state = dict(zip(built["state_fips"], built["observed_value"], strict=True))
    assert by_state["02"] is None
    assert by_state["04"] == 0


def test_only_the_target_industry_reaches_the_size_family(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # qcew_national_size carries every industry; 99% of its rows are not Logging.
    built = cells.build_target_cells(
        _data(make_monthly({}), make_size({}, {"industry_code": "111110"})),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert set(built["industry_code"]) == {"113310"}


def test_two_release_vintages_for_one_cell_halt_rather_than_stack(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # INV-007: constraints from incompatible release vintages are never stacked silently.
    with pytest.raises(ConceptViolationError, match="release vintage"):
        cells.build_target_cells(
            _data(
                make_monthly({}, {"release_vintage": "2024q1r2", "snapshot_id": "2024q1r2"}),
                make_size({}),
            ),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_a_status_no_builder_covers_halts_rather_than_reaching_the_solver(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # `absent` is in contracts.OBSERVATION_STATUSES and is written by no parser. A cell carrying it
    # would get no fixing row and no nonnegativity row, and would reach the solver unconstrained.
    with pytest.raises(ConceptViolationError, match="absent"):
        cells.build_target_cells(
            _data(make_monthly({}, {"state_fips": "02", "observation_status": "absent"}),
                  make_size({})),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_a_published_cell_with_no_parseable_value_halts(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    with pytest.raises(ConceptViolationError, match="no parseable value"):
        cells.build_target_cells(
            _data(make_monthly({"employment_value": None}), make_size({})),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_the_built_frame_matches_the_shipped_schema(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    built = cells.build_target_cells(
        _data(make_monthly({}), make_size({})),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert built.schema == pl.Schema(TARGET_CELL_SCHEMA)
    assert built["cell_id"].to_list() == sorted(built["cell_id"].to_list())
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_cells.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.constraints'`.

- [ ] **Step 4: Write the implementation**

Create `src/logging_employment/constraints/__init__.py`:

```python
"""The deterministic identification engine (§9)."""
```

Create `src/logging_employment/constraints/cells.py`:

```python
"""§7.7 target cells: one row per atomic cell in the constraint universe.

§9.2 fixes the atomic key at state x month x ownership x NAICS x release_vintage for state totals,
and adds the March-reference size class for the size universe. `cell_id` encodes that key
literally, with the family as its first field, because §7.7 requires size cells and total cells to
have distinct IDs and a shared prefix would leave that to luck.

`qcew_national_size` carries no ownership column -- §7.4's field list has none -- so the ownership
code stamped on a size cell comes from configuration. What licenses that stamp is
`compat.assert_size_margin_compatible`, which must have passed before these cells are used; the
stamp records a decision the gate justified, not one this module verified.
"""

from __future__ import annotations

from collections.abc import Iterable

import polars as pl

from ..contracts import TARGET_CELL_SCHEMA, HarmonizedData
from ..errors import ConceptViolationError

KIND_STATE_TOTAL = "state_total"
KIND_NATIONAL_TOTAL = "national_total"
KIND_NATIONAL_SIZE = "national_size"

# `state_fips` on a national cell. Not a FIPS code, and deliberately not null: a null would be
# indistinguishable from a missing value in a join, and no two-character FIPS can collide with it.
NATIONAL_STATE_FIPS = "US"

# §7.7: "For the state-total model, use a synthetic total size class such as `ALL`."
TOTAL_SIZE_CLASS = "ALL"

_ID_FIELDS = (
    "state_fips",
    "reference_month",
    "ownership_code",
    "industry_code",
    "naics_vintage",
    "size_class",
)


def cell_id(
    kind: str,
    *,
    state_fips: str,
    reference_month: str,
    ownership_code: str,
    industry_code: str,
    naics_vintage: str,
    size_class: str,
) -> str:
    """The identifier for one atomic cell: family first, then §9.2's key, pipe-separated."""
    return "|".join(
        (
            kind,
            state_fips,
            reference_month,
            ownership_code,
            industry_code,
            naics_vintage,
            size_class,
        )
    )


def _cell_id_expr(kind: str) -> pl.Expr:
    """`cell_id` as an expression over columns already named for the key.

    Kept beside the string form, and pinned equal to it by a test: two encodings of one identifier
    that drift apart would produce cells no coefficient row could find.

    `concat_str` returns null when any input is null, which is the behaviour to keep: a null key
    field must surface as a build failure -- `validate_frame` and the duplicate check both see a
    null `cell_id` -- rather than as a cell whose identifier `replace_strict` later reports as a
    missing key from three modules away.
    """
    return pl.concat_str(
        [pl.lit(kind), *(pl.col(name) for name in _ID_FIELDS)], separator="|"
    ).alias("cell_id")


def _select(frame: pl.DataFrame, kind: str, size_concept: str, value_column: str) -> pl.DataFrame:
    """Project a source frame onto §7.7's twelve fields, in the spec's order."""
    return frame.select(
        _cell_id_expr(kind),
        pl.col("state_fips"),
        pl.col("reference_month"),
        pl.lit(size_concept).alias("size_concept"),
        pl.col("size_class"),
        pl.col("ownership_code"),
        pl.col("industry_code"),
        pl.col("naics_vintage"),
        pl.col("observation_status"),
        pl.col(value_column).alias("observed_value"),
        pl.col("snapshot_id").alias("source_snapshot_id"),
        pl.col("disclosure_code").alias("qcew_disclosure_code"),
    ).cast(TARGET_CELL_SCHEMA)  # type: ignore[arg-type]


def state_total_cells(monthly: pl.DataFrame, *, size_concept: str) -> pl.DataFrame:
    """One cell per published state-month, whatever its observation status."""
    rows = monthly.filter(pl.col("area_type") == "state").with_columns(
        pl.lit(TOTAL_SIZE_CLASS).alias("size_class")
    )
    return _select(rows, KIND_STATE_TOTAL, size_concept, "employment_value")


def national_total_cells(
    monthly: pl.DataFrame, *, size_concept: str, reference_months: Iterable[str]
) -> pl.DataFrame:
    """One cell per national month that a size margin needs.

    Restricted to the months named by the caller rather than emitting all 96. A national cell that
    no constraint touches would add an isolated observed cell to the system and, worse, would read
    as a national/state link that `SRC-QCEW-006`'s `decline` forbids.
    """
    rows = monthly.filter(
        (pl.col("area_type") == "national")
        & pl.col("reference_month").is_in(list(reference_months))
    ).with_columns(
        pl.lit(NATIONAL_STATE_FIPS).alias("state_fips"),
        pl.lit(TOTAL_SIZE_CLASS).alias("size_class"),
    )
    return _select(rows, KIND_NATIONAL_TOTAL, size_concept, "employment_value")


def national_size_cells(
    size_rows: pl.DataFrame, *, ownership_code: str, size_concept: str
) -> pl.DataFrame:
    """One cell per published national size class. Caller filters to the target industry first."""
    rows = size_rows.with_columns(
        pl.lit(NATIONAL_STATE_FIPS).alias("state_fips"),
        pl.lit(ownership_code).alias("ownership_code"),
    )
    return _select(rows, KIND_NATIONAL_SIZE, size_concept, "employment")


def _assert_one_vintage_per_cell(monthly: pl.DataFrame) -> None:
    """Halt if one area-month is published under more than one release vintage (INV-007)."""
    offending = (
        monthly.group_by(["area_fips", "reference_month"])
        .agg(pl.col("release_vintage").n_unique().alias("vintages"))
        .filter(pl.col("vintages") > 1)
    )
    if offending.height:
        first = offending.row(0, named=True)
        raise ConceptViolationError(
            f"{offending.height} area-month(s) carry more than one release vintage, e.g. "
            f"{first['area_fips']} {first['reference_month']}; stacking them into one cell would "
            "merge two vintages of the same published value (INV-007)"
        )


# The three statuses every constraint builder covers. `contracts.OBSERVATION_STATUSES` also allows
# `absent`, which Stage 1's parser never writes: DC publishes no row at all rather than an absent
# one, so absence shows up as a missing row, not as a cell. A cell carrying `absent` would receive
# neither a fixing row (which covers observed and true_zero) nor a nonnegativity row (which covers
# suppressed), would reach the solver with an unbounded box in both directions, and would match no
# branch of `classify_bound_status`.
_CONSTRAINABLE_STATUSES = frozenset({"observed", "true_zero", "suppressed"})


def _assert_every_cell_is_constrainable(cells: pl.DataFrame) -> None:
    """Halt on a cell no builder would cover, or a published cell with no parseable value.

    Both conditions are measured absent from the D1 window -- 0 rows carry a fourth status and 0
    non-suppressed rows carry a null value -- and both are §18.3 conditions rather than rows to
    skip: a published cell whose value did not parse is a parser defect, and silently dropping it
    would remove a public accounting fact from the system.
    """
    unhandled = sorted(
        set(cells["observation_status"].to_list()) - _CONSTRAINABLE_STATUSES
    )
    if unhandled:
        raise ConceptViolationError(
            f"observation status(es) {unhandled} reached the cell index; no constraint builder "
            f"covers them, so those cells would reach the solver unconstrained"
        )
    unparsed = cells.filter(
        (pl.col("observation_status") != "suppressed") & pl.col("observed_value").is_null()
    )
    if unparsed.height:
        raise ConceptViolationError(
            f"{unparsed.height} published cell(s) carry no value, e.g. "
            f"{unparsed['cell_id'][0]}; a published cell with no parseable value is a parser "
            "defect, not a cell to skip (§18.3)"
        )


def build_target_cells(
    data: HarmonizedData, *, industry_code: str, ownership_code: str, size_concept: str
) -> pl.DataFrame:
    """The whole §7.7 target-cell index, sorted by `cell_id`."""
    _assert_one_vintage_per_cell(data.qcew_monthly)
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry_code)
    months = sorted(set(size["reference_month"].to_list()))
    built = pl.concat(
        [
            state_total_cells(data.qcew_monthly, size_concept=size_concept),
            national_total_cells(
                data.qcew_monthly, size_concept=size_concept, reference_months=months
            ),
            national_size_cells(size, ownership_code=ownership_code, size_concept=size_concept),
        ]
    ).sort("cell_id")
    duplicates = built.group_by("cell_id").len().filter(pl.col("len") > 1)
    if duplicates.height:
        raise ConceptViolationError(
            f"{duplicates.height} duplicate cell_id(s), e.g. {duplicates['cell_id'][0]}; §9.2 "
            "requires every atomic key to be mutually exclusive within a constraint system"
        )
    _assert_every_cell_is_constrainable(built)
    return built
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_cells.py -v`
Expected: PASS, all nine tests.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/constraints tests/unit/conftest.py tests/unit/test_constraint_cells.py
git commit -m "feat(constraints): build the §7.7 target-cell index for both cell families

cell_id leads with the family, so §7.7's 'size cells and total cells MUST have
distinct IDs' holds by construction rather than by luck. National cells carry
'US' rather than a null state_fips.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: The two compatibility gates

**Files:**
- Create: `src/logging_employment/constraints/compat.py`
- Test: `tests/unit/test_constraint_compat.py`

**Interfaces:**
- Consumes: `harmonize.universe.assert_definitional_alignment` (Stage 1); `HarmonizedData`
  (Task 2); `IncompatibleMarginError`, `ConceptViolationError` (Tasks 2 and Stage 1).
- Produces: `assert_size_support_holds(size_rows: pl.DataFrame) -> int` returning the number of
  observed rows checked; `assert_size_margin_compatible(monthly: pl.DataFrame,
  size_rows: pl.DataFrame) -> dict[str, object]` returning a report with keys `years_checked`,
  `establishment_gap_by_year`, `employment_checkable_years`, `observed_support_rows_checked`; and
  `run_compatibility_gates(data: HarmonizedData, *, industry_code: str) -> dict[str, object]`,
  which is the single entry point Task 7 calls before any row is created.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_compat.py`:

```python
"""The §5.5 gates that must pass before a constraint row exists."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.constraints import compat
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError, IncompatibleMarginError


def _real_2024(make_monthly, make_size):
    """The real published 2024 margin: seven classes, two suppressed, 7713 establishments."""
    monthly = make_monthly(
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "qtrly_establishments": 7713,
            "employment_value": 41668,
            "employment_raw": "41668",
        }
    )
    published = [
        ("1", 5007, 7630, 0, 4, "", "observed"),
        ("2", 1501, 9955, 5, 9, "", "observed"),
        ("3", 803, 10480, 10, 19, "", "observed"),
        ("4", 357, 10316, 20, 49, "", "observed"),
        ("5", 40, 2507, 50, 99, "", "observed"),
        ("6", 4, None, 100, 249, "N", "suppressed"),
        ("7", 1, None, 250, 499, "N", "suppressed"),
    ]
    size = make_size(
        *[
            {
                "size_class": k,
                "establishments": n,
                "employment": e,
                "size_lower": lo,
                "size_upper": hi,
                "disclosure_code": code,
                "observation_status": status,
            }
            for k, n, e, lo, hi, code, status in published
        ]
    )
    return monthly, size


def test_the_real_2024_margin_passes_both_gates(make_monthly, make_size) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    report = compat.assert_size_margin_compatible(monthly, size)
    assert report["years_checked"] == [2024]
    assert report["establishment_gap_by_year"] == {2024: 0}
    assert report["employment_checkable_years"] == []
    assert report["observed_support_rows_checked"] == 5


def test_a_year_with_no_suppressed_class_is_reported_as_employment_checkable(
    make_monthly, make_size
) -> None:
    # 2017 is the one such year in the window, and its residual is exactly 0.
    monthly = make_monthly(
        {
            "area_fips": "US000", "area_type": "national", "state_fips": None,
            "aggregation_level": "18", "reference_month": "2017-03",
            "qtrly_establishments": 60, "employment_value": 300, "employment_raw": "300",
        }
    )
    size = make_size(
        {"reference_year": 2017, "reference_month": "2017-03", "size_class": "1",
         "establishments": 50, "employment": 100, "size_lower": 0, "size_upper": 4},
        {"reference_year": 2017, "reference_month": "2017-03", "size_class": "2",
         "establishments": 10, "employment": 200, "size_lower": 5, "size_upper": 99},
    )
    report = compat.assert_size_margin_compatible(monthly, size)
    assert report["employment_checkable_years"] == [2017]


def test_an_establishment_gap_halts_rather_than_stacking_two_universes(
    make_monthly, make_size
) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    monthly = monthly.with_columns(pl.lit(9999).alias("qtrly_establishments"))
    with pytest.raises(IncompatibleMarginError, match="establishment"):
        compat.assert_size_margin_compatible(monthly, size)


def test_two_rows_for_one_year_and_class_halt(make_monthly, make_size) -> None:
    monthly, size = _real_2024(make_monthly, make_size)
    with pytest.raises(IncompatibleMarginError, match="more than one row"):
        compat.assert_size_margin_compatible(monthly, pl.concat([size, size.head(1)]))


def test_a_non_march_size_row_halts_before_any_support_is_built(make_monthly, make_size) -> None:
    # INV-011: a March-reference class bound is not imposed outside its valid reference period.
    monthly, size = _real_2024(make_monthly, make_size)
    with pytest.raises(ConceptViolationError, match="March"):
        compat.assert_size_margin_compatible(
            monthly, size.with_columns(pl.lit("2024-06").alias("reference_month"))
        )


def test_the_support_rule_is_checked_against_every_observed_row(make_size) -> None:
    # Measured while this plan was written: all 37 observed window rows satisfy the band. A row
    # that does not means the class titles do not describe published data, and the support
    # constraint must not be built as hard.
    good = make_size({"size_class": "5", "establishments": 40, "employment": 2507,
                      "size_lower": 50, "size_upper": 99})
    assert compat.assert_size_support_holds(good) == 1
    bad = make_size({"size_class": "5", "establishments": 40, "employment": 100,
                     "size_lower": 50, "size_upper": 99})
    with pytest.raises(ConceptViolationError, match="size support"):
        compat.assert_size_support_holds(bad)


def test_an_open_ended_class_is_checked_on_its_lower_side_only(make_size) -> None:
    # Class 9 is "1000 or more employees per establishment"; `size_upper` is null and no number
    # may be invented to close it (§9.3 forbids arbitrary top-class caps).
    rows = make_size({"size_class": "9", "establishments": 2, "employment": 999_999,
                      "size_lower": 1000, "size_upper": None})
    assert compat.assert_size_support_holds(rows) == 1


def test_the_entry_point_calls_stage_ones_alignment_check(make_monthly, make_size) -> None:
    # SRC-QCEW-007 requires the alignment check before a constraint is created, and Stage 1 left
    # it off the build path for exactly that reason.
    monthly, size = _real_2024(make_monthly, make_size)
    misaligned = pl.concat(
        [monthly, make_monthly({"industry_code": "111110", "area_type": "state"})]
    )
    data = HarmonizedData(
        qcew_monthly=misaligned,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    with pytest.raises(ConceptViolationError, match="definitionally aligned"):
        compat.run_compatibility_gates(data, industry_code="113310")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_compat.py -v`
Expected: FAIL with `ImportError: cannot import name 'compat'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/compat.py`:

```python
"""The §5.5 compatibility gates that run before any constraint row is created.

Two checks, and the asymmetry between them is the point of this module.

`assert_definitional_alignment` is Stage 1's. SRC-QCEW-007 requires it here rather than on the
build path, because it guards constraint construction: a misaligned national/state pair must never
reach the point where it could become a hard equation.

`assert_size_margin_compatible` is this stage's, and it is what licenses treating the national
by-size file and the national all-sizes row as one universe. §7.4's field list carries no ownership
column, so the harmonized layer cannot grant that licence by itself. What the gate can and cannot
show, stated rather than assumed: the *establishment* margin is checkable in all eight window
years, because every establishment cell is published; the *employment* margin is checkable in
exactly one, 2017, the only year with no suppressed class. A passing gate therefore rests mostly on
establishments, and reading it as proof that the two employment universes agree year by year would
be reading more than it measures. `employment_checkable_years` in the report is what keeps that
distinction visible to a caller.
"""

from __future__ import annotations

import polars as pl

from ..contracts import HarmonizedData
from ..errors import ConceptViolationError, IncompatibleMarginError
from ..harmonize.universe import assert_definitional_alignment

MARCH_SUFFIX = "-03"


def assert_size_support_holds(size_rows: pl.DataFrame) -> int:
    """Halt unless every observed size row lies inside its own class band.

    The rule under test is `n * lower <= employment <= n * upper`: a class of `n` establishments
    each holding between `lower` and `upper` employees can hold no more and no less in total. That
    is what makes the support a §9.3 "documented size support" rather than an assumption, and
    checking it against published rows is what keeps it measured. A null `size_upper` is an
    open-ended top class, checked on its lower side only.

    Returns the number of observed rows checked, so a caller can record that the gate had something
    to check rather than passing vacuously.
    """
    observed = size_rows.filter(pl.col("observation_status") == "observed")
    violations = observed.filter(
        (pl.col("employment") < pl.col("establishments") * pl.col("size_lower"))
        | (
            pl.col("size_upper").is_not_null()
            & (pl.col("employment") > pl.col("establishments") * pl.col("size_upper"))
        )
    )
    if violations.height:
        first = violations.row(0, named=True)
        raise ConceptViolationError(
            f"{violations.height} observed row(s) fall outside their own size support, e.g. "
            f"{first['reference_year']} class {first['size_class']}: {first['employment']} "
            f"employees across {first['establishments']} establishments in band "
            f"[{first['size_lower']}, {first['size_upper']}]. The class titles do not describe "
            "published data, so the support may not be built as a hard constraint"
        )
    return observed.height


def assert_size_margin_compatible(
    monthly: pl.DataFrame, size_rows: pl.DataFrame
) -> dict[str, object]:
    """Halt unless the national by-size rows and the national all-sizes row are one universe.

    Four conditions, each a §5.5 gate item: one row per year and class (statistical unit and
    ownership coverage -- a second ownership universe in the file would show up here as a duplicate
    key); the published establishment sum equals the all-sizes establishment count (geography and
    ownership); every size row is March-referenced (reference period, INV-011); and the size rows'
    NAICS vintage matches the national row's for that month (industry vintage).
    """
    off_march = size_rows.filter(~pl.col("reference_month").str.ends_with(MARCH_SUFFIX))
    if off_march.height:
        raise ConceptViolationError(
            f"{off_march.height} size row(s) are not March-referenced, e.g. "
            f"{off_march['reference_month'][0]}; a March-reference class bound may not be built "
            "for another month (INV-011, §11.9)"
        )

    duplicates = size_rows.group_by(["reference_year", "size_class"]).len().filter(pl.col("len") > 1)
    if duplicates.height:
        first = duplicates.row(0, named=True)
        raise IncompatibleMarginError(
            f"{duplicates.height} (year, size_class) key(s) carry more than one row, e.g. "
            f"{first['reference_year']} class {first['size_class']}; a second ownership or "
            "geography universe in the by-size file would look exactly like this (INV-007)"
        )

    national = monthly.filter(
        (pl.col("area_type") == "national") & pl.col("reference_month").str.ends_with(MARCH_SUFFIX)
    ).select(["reference_month", "naics_vintage", "qtrly_establishments", "employment_value"])
    joined = (
        size_rows.group_by(["reference_year", "reference_month"])
        .agg(
            pl.col("establishments").sum().alias("size_establishments"),
            pl.col("naics_vintage").n_unique().alias("size_vintages"),
            pl.col("naics_vintage").first().alias("size_vintage"),
            pl.col("employment").sum().alias("observed_employment"),
            (pl.col("observation_status") == "suppressed").sum().alias("suppressed_classes"),
        )
        .join(national, on="reference_month", how="left")
        .sort("reference_year")
    )

    missing = joined.filter(pl.col("qtrly_establishments").is_null())
    if missing.height:
        raise IncompatibleMarginError(
            f"{missing.height} size year(s) have no national all-sizes row to close against, "
            f"e.g. {missing['reference_month'][0]}; the margin has no right-hand side"
        )

    gaps = joined.with_columns(
        (pl.col("qtrly_establishments") - pl.col("size_establishments")).alias("estab_gap")
    )
    bad = gaps.filter((pl.col("estab_gap") != 0) | (pl.col("size_vintages") > 1))
    if bad.height:
        first = bad.row(0, named=True)
        raise IncompatibleMarginError(
            f"{bad.height} year(s) fail the establishment check, e.g. {first['reference_year']}: "
            f"by-size sum {first['size_establishments']} against all-sizes "
            f"{first['qtrly_establishments']} (gap {first['estab_gap']}), size vintages "
            f"{first['size_vintages']}. Stacking these would join two universes (INV-007)"
        )

    vintage_conflict = gaps.filter(pl.col("size_vintage") != pl.col("naics_vintage"))
    if vintage_conflict.height:
        first = vintage_conflict.row(0, named=True)
        raise IncompatibleMarginError(
            f"{vintage_conflict.height} year(s) pair NAICS vintages that differ, e.g. "
            f"{first['reference_year']}: size {first['size_vintage']} against national "
            f"{first['naics_vintage']} (INV-007)"
        )

    return {
        "years_checked": gaps["reference_year"].to_list(),
        "establishment_gap_by_year": dict(
            zip(gaps["reference_year"].to_list(), gaps["estab_gap"].to_list(), strict=True)
        ),
        "employment_checkable_years": gaps.filter(pl.col("suppressed_classes") == 0)[
            "reference_year"
        ].to_list(),
        "observed_support_rows_checked": assert_size_support_holds(size_rows),
    }


def run_compatibility_gates(data: HarmonizedData, *, industry_code: str) -> dict[str, object]:
    """Every gate, in the order a constraint builder needs them. Returns the margin report."""
    assert_definitional_alignment(data.qcew_monthly)
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry_code)
    return assert_size_margin_compatible(data.qcew_monthly, size)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_compat.py -v`
Expected: PASS, all eight tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/compat.py tests/unit/test_constraint_compat.py
git commit -m "feat(constraints): gate the size margin on compatibility before any row exists

The by-size table carries no ownership column, so the establishment identity is
what licenses treating it as the private universe. The report keeps the
asymmetry visible: establishments are checkable in eight years, employment in one.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: The constraint-row factory and its three negative guards

**Files:**
- Create: `src/logging_employment/constraints/rows.py`
- Test: `tests/unit/test_constraint_rows.py`

**Interfaces:**
- Consumes: `CONSTRAINT_CLASSES`, `HARD_ELIGIBLE_CLASSES`, `RELATIONS`, `EVIDENCE_KINDS`,
  `EVIDENCE_PREFIX`, `CONSTRAINT_ROW_SCHEMA`, `CONSTRAINT_COEFFICIENT_SCHEMA` (Task 2);
  `HardConstraintClassError`, `IncompatibleMarginError` (Task 2); `KIND_STATE_TOTAL`,
  `KIND_NATIONAL_TOTAL` (Task 3).
- Produces: the frozen dataclass `ConstraintDraft` with fields `constraint_id`,
  `constraint_class`, `relation`, `rhs_lower`, `rhs_upper`, `is_hard`, `period_scope`,
  `geography_scope`, `industry_scope`, `ownership_scope`, `source_snapshot_ids`,
  `provenance_text`, `vintage_compatibility_status`, `coefficients: tuple[tuple[str, float], ...]`;
  the factory `constraint(...) -> ConstraintDraft`; `vintage_status(vintages: Iterable[str]) -> str`;
  `assert_no_national_employment_margin(drafts: Sequence[ConstraintDraft], kinds: Mapping[str, str])
  -> None`; and `to_frames(drafts: Sequence[ConstraintDraft]) -> tuple[pl.DataFrame, pl.DataFrame]`
  returning `(constraint_row, constraint_coefficient)` frames.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_rows.py`:

```python
"""The row factory: what it accepts, and the three things it must refuse."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.constraints import cells, rows
from logging_employment.contracts import CONSTRAINT_ROW_SCHEMA
from logging_employment.errors import HardConstraintClassError, IncompatibleMarginError


def _kwargs(**overrides):
    base = dict(
        constraint_id="fix|x",
        constraint_class="public_accounting_fact",
        relation="eq",
        coefficients=(("cell-a", 1.0),),
        rhs_lower=5.0,
        rhs_upper=5.0,
        is_hard=True,
        evidence_kind="published_value",
        period_scope="2024-03",
        geography_scope="01",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="2024q1",
        provenance_text="published QCEW value",
        vintage_compatibility_status="compatible",
    )
    return base | overrides


def test_a_well_formed_hard_row_is_accepted_and_carries_its_evidence_kind() -> None:
    draft = rows.constraint(**_kwargs())
    assert draft.is_hard is True
    assert draft.provenance_text.startswith("evidence_kind=published_value; ")


# --- Guard 1: §7.8, only the first two classes may be hard -------------------------------------


def test_a_hard_row_outside_the_two_eligible_classes_is_refused() -> None:
    for ineligible in ("empirical_measurement", "modeling_assumption", "sensitivity_assumption"):
        with pytest.raises(HardConstraintClassError, match=ineligible):
            rows.constraint(**_kwargs(constraint_class=ineligible))


def test_the_same_class_is_accepted_when_it_is_not_hard() -> None:
    draft = rows.constraint(**_kwargs(constraint_class="empirical_measurement", is_hard=False))
    assert draft.is_hard is False


# --- Guard 2: SRC-QCEW-006's `decline` -- no national employment margin -------------------------


def test_a_row_linking_the_national_row_to_state_cells_is_refused() -> None:
    # Stage 0's verdict is `decline`: "Stage 2 therefore MUST NOT create a national employment
    # margin constraint out of this identity." This guard is what makes that structural.
    kinds = {
        "nat": cells.KIND_NATIONAL_TOTAL,
        "st1": cells.KIND_STATE_TOTAL,
        "st2": cells.KIND_STATE_TOTAL,
    }
    draft = rows.constraint(
        **_kwargs(
            constraint_id="national_identity|2024-03",
            coefficients=(("st1", 1.0), ("st2", 1.0), ("nat", -1.0)),
            rhs_lower=0.0,
            rhs_upper=0.0,
        )
    )
    with pytest.raises(IncompatibleMarginError, match="SRC-QCEW-006"):
        rows.assert_no_national_employment_margin([draft], kinds)


def test_a_row_summing_two_state_cells_is_refused_even_without_the_national_cell() -> None:
    kinds = {"st1": cells.KIND_STATE_TOTAL, "st2": cells.KIND_STATE_TOTAL}
    draft = rows.constraint(
        **_kwargs(coefficients=(("st1", 1.0), ("st2", 1.0)), rhs_lower=9.0, rhs_upper=9.0)
    )
    with pytest.raises(IncompatibleMarginError, match="SRC-QCEW-006"):
        rows.assert_no_national_employment_margin([draft], kinds)


def test_the_size_margin_passes_the_same_guard() -> None:
    kinds = {"k1": cells.KIND_NATIONAL_SIZE, "k2": cells.KIND_NATIONAL_SIZE,
             "nat": cells.KIND_NATIONAL_TOTAL}
    draft = rows.constraint(
        **_kwargs(
            coefficients=(("k1", 1.0), ("k2", 1.0), ("nat", -1.0)), rhs_lower=0.0, rhs_upper=0.0
        )
    )
    rows.assert_no_national_employment_margin([draft], kinds)  # does not raise


# --- Guard 3: §9.3, no hard constraint from an assumed disclosure threshold ---------------------


def test_a_constraint_warranted_by_an_assumed_threshold_can_never_be_hard() -> None:
    # The Gemini review's §7 item 5 derives a hard bound from an asserted "80/3" disclosure
    # threshold. §9.3 forbids it, and the refusal is by evidence kind rather than by review.
    with pytest.raises(HardConstraintClassError, match="assumed_threshold"):
        rows.constraint(**_kwargs(evidence_kind="assumed_threshold", relation="le",
                                  rhs_lower=None, rhs_upper=26.0))


def test_the_same_warrant_is_allowed_as_a_labelled_sensitivity_assumption() -> None:
    draft = rows.constraint(
        **_kwargs(
            constraint_class="sensitivity_assumption",
            evidence_kind="assumed_threshold",
            relation="le",
            rhs_lower=None,
            rhs_upper=26.0,
            is_hard=False,
        )
    )
    assert draft.is_hard is False
    assert "assumed_threshold" in draft.provenance_text


# --- Guard 4: INV-007, a hard row may not span incompatible vintages ----------------------------


def test_a_hard_row_spanning_two_naics_vintages_is_refused() -> None:
    assert rows.vintage_status(["NAICS 2017", "NAICS 2017"]) == "compatible"
    assert rows.vintage_status(["NAICS 2017", "NAICS 2022"]) == "incompatible"
    with pytest.raises(IncompatibleMarginError, match="vintage"):
        rows.constraint(**_kwargs(vintage_compatibility_status="incompatible"))


# --- Shape checks -------------------------------------------------------------------------------


def test_relation_and_rhs_must_agree() -> None:
    with pytest.raises(ValueError, match="eq"):
        rows.constraint(**_kwargs(relation="eq", rhs_lower=1.0, rhs_upper=2.0))
    with pytest.raises(ValueError, match="ge"):
        rows.constraint(**_kwargs(relation="ge", rhs_lower=None, rhs_upper=None))
    with pytest.raises(ValueError, match="integrality"):
        rows.constraint(**_kwargs(relation="integrality", rhs_lower=1.0, rhs_upper=1.0))


def test_to_frames_matches_both_schemas_and_is_sorted() -> None:
    drafts = [
        rows.constraint(**_kwargs(constraint_id="b")),
        rows.constraint(**_kwargs(constraint_id="a", coefficients=(("cell-b", 1.0),))),
    ]
    row_frame, coefficient_frame = rows.to_frames(drafts)
    assert row_frame.schema == pl.Schema(CONSTRAINT_ROW_SCHEMA)
    assert row_frame["constraint_id"].to_list() == ["a", "b"]
    assert coefficient_frame["constraint_id"].to_list() == ["a", "b"]
    assert row_frame["component_id"].null_count() == row_frame.height
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_rows.py -v`
Expected: FAIL with `ImportError: cannot import name 'rows'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/rows.py`:

```python
"""§7.8 constraint rows: the factory, and the four restrictions it refuses to build.

Every restriction in the system passes through `constraint`. That is deliberate: INV-004 requires
each one to carry a label, and §9.3 names forms that must never become hard equations. A guard
placed at the single construction point cannot be bypassed by a builder written later, which a
review checklist can.

`evidence_kind` is what licenses a restriction, and §7.8's field list has no column for it, so the
factory writes it into `provenance_text` behind a fixed `evidence_kind=` prefix. That keeps the
warrant queryable in the persisted table rather than only in this module's arguments.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from ..contracts import (
    CONSTRAINT_CLASSES,
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    EVIDENCE_KINDS,
    EVIDENCE_PREFIX,
    HARD_ELIGIBLE_CLASSES,
    RELATIONS,
)
from ..errors import HardConstraintClassError, IncompatibleMarginError
from .cells import KIND_NATIONAL_TOTAL, KIND_STATE_TOTAL


@dataclass(frozen=True)
class ConstraintDraft:
    """One §7.8 row and its §7.9 coefficients, before a component has been assigned."""

    constraint_id: str
    constraint_class: str
    relation: str
    rhs_lower: float | None
    rhs_upper: float | None
    is_hard: bool
    period_scope: str
    geography_scope: str
    industry_scope: str
    ownership_scope: str
    source_snapshot_ids: str
    provenance_text: str
    vintage_compatibility_status: str
    coefficients: tuple[tuple[str, float], ...]


def vintage_status(vintages: Iterable[str]) -> str:
    """`compatible` when every participating cell shares one NAICS vintage, else `incompatible`."""
    return "compatible" if len(set(vintages)) <= 1 else "incompatible"


def _check_relation(relation: str, rhs_lower: float | None, rhs_upper: float | None,
                    coefficients: tuple[tuple[str, float], ...]) -> None:
    """Halt unless the right-hand side has the shape the relation implies."""
    if relation == "eq" and (rhs_lower is None or rhs_lower != rhs_upper):
        raise ValueError(f"relation 'eq' needs rhs_lower == rhs_upper, got {rhs_lower}/{rhs_upper}")
    if relation == "ge" and (rhs_lower is None or rhs_upper is not None):
        raise ValueError(f"relation 'ge' needs rhs_lower only, got {rhs_lower}/{rhs_upper}")
    if relation == "le" and (rhs_upper is None or rhs_lower is not None):
        raise ValueError(f"relation 'le' needs rhs_upper only, got {rhs_lower}/{rhs_upper}")
    if relation == "range" and (rhs_lower is None or rhs_upper is None):
        raise ValueError(f"relation 'range' needs both ends, got {rhs_lower}/{rhs_upper}")
    if relation == "integrality":
        if rhs_lower is not None or rhs_upper is not None:
            raise ValueError("relation 'integrality' carries no right-hand side")
        if len(coefficients) != 1:
            raise ValueError("relation 'integrality' applies to exactly one cell")


def constraint(
    *,
    constraint_id: str,
    constraint_class: str,
    relation: str,
    coefficients: tuple[tuple[str, float], ...],
    rhs_lower: float | None,
    rhs_upper: float | None,
    is_hard: bool,
    evidence_kind: str,
    period_scope: str,
    geography_scope: str,
    industry_scope: str,
    ownership_scope: str,
    source_snapshot_ids: str,
    provenance_text: str,
    vintage_compatibility_status: str,
) -> ConstraintDraft:
    """Build one labelled restriction, or refuse.

    Four refusals, each naming what it protects:

    1. §7.8 -- only `public_accounting_fact` and `definitional_support` may be hard.
    2. §9.3 -- a restriction warranted by an assumed disclosure threshold may never be hard,
       whatever class the caller asks for.
    3. INV-007 -- a hard restriction may not span incompatible release or NAICS vintages.
    4. Shape -- the right-hand side must match the relation.
    """
    if constraint_class not in CONSTRAINT_CLASSES:
        raise ValueError(f"unknown constraint_class {constraint_class!r}")
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}")
    if evidence_kind not in EVIDENCE_KINDS:
        raise ValueError(f"unknown evidence_kind {evidence_kind!r}")
    if not coefficients:
        raise ValueError(f"{constraint_id}: a constraint with no coefficients restricts nothing")
    named = [cell for cell, _ in coefficients]
    if len(set(named)) != len(named):
        raise ValueError(f"{constraint_id}: a cell appears twice in one constraint")

    if is_hard and constraint_class not in HARD_ELIGIBLE_CLASSES:
        raise HardConstraintClassError(
            f"{constraint_id}: class {constraint_class!r} may not be hard; §7.8 allows "
            f"is_hard=true only for {list(HARD_ELIGIBLE_CLASSES)}"
        )
    if is_hard and evidence_kind == "assumed_threshold":
        raise HardConstraintClassError(
            f"{constraint_id}: warranted by evidence_kind='assumed_threshold', which §9.3 forbids "
            "as a hard constraint. Record it as a sensitivity_assumption with is_hard=false"
        )
    if is_hard and vintage_compatibility_status != "compatible":
        raise IncompatibleMarginError(
            f"{constraint_id}: vintage_compatibility_status={vintage_compatibility_status!r}; "
            "INV-007 forbids stacking incompatible vintages into a hard equation"
        )
    _check_relation(relation, rhs_lower, rhs_upper, coefficients)

    return ConstraintDraft(
        constraint_id=constraint_id,
        constraint_class=constraint_class,
        relation=relation,
        rhs_lower=rhs_lower,
        rhs_upper=rhs_upper,
        is_hard=is_hard,
        period_scope=period_scope,
        geography_scope=geography_scope,
        industry_scope=industry_scope,
        ownership_scope=ownership_scope,
        source_snapshot_ids=source_snapshot_ids,
        provenance_text=f"{EVIDENCE_PREFIX}{evidence_kind}; {provenance_text}",
        vintage_compatibility_status=vintage_compatibility_status,
        coefficients=tuple(coefficients),
    )


def assert_no_national_employment_margin(
    drafts: Sequence[ConstraintDraft], kinds: Mapping[str, str]
) -> None:
    """Halt if any restriction couples state employment cells to each other or to the national row.

    Stage 0's `SRC-QCEW-006` verdict is `decline`, and the finding's consequence paragraph is
    explicit: no national employment margin may be created out of that identity. Both shapes are
    refused, because the identity can be written either way -- as a sum of states equalling the
    national row, or as a sum of states equalling a number lifted from it.
    """
    for draft in drafts:
        touched = [kinds[cell] for cell, _ in draft.coefficients]
        states = touched.count(KIND_STATE_TOTAL)
        if states > 1 or (states and KIND_NATIONAL_TOTAL in touched):
            raise IncompatibleMarginError(
                f"{draft.constraint_id} couples {states} state-total cell(s) "
                f"{'to the national row ' if KIND_NATIONAL_TOTAL in touched else ''}"
                "-- SRC-QCEW-006 came back `decline`, so no national employment margin may be "
                "created out of that identity"
            )


def to_frames(drafts: Sequence[ConstraintDraft]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Project drafts onto the §7.8 and §7.9 tables, sorted, with `component_id` still null."""
    row_records = [
        {
            "constraint_id": d.constraint_id,
            "component_id": None,
            "constraint_class": d.constraint_class,
            "relation": d.relation,
            "rhs_lower": d.rhs_lower,
            "rhs_upper": d.rhs_upper,
            "is_hard": d.is_hard,
            "period_scope": d.period_scope,
            "geography_scope": d.geography_scope,
            "industry_scope": d.industry_scope,
            "ownership_scope": d.ownership_scope,
            "source_snapshot_ids": d.source_snapshot_ids,
            "provenance_text": d.provenance_text,
            "vintage_compatibility_status": d.vintage_compatibility_status,
        }
        for d in drafts
    ]
    coefficient_records = [
        {"constraint_id": d.constraint_id, "cell_id": cell, "coefficient": value}
        for d in drafts
        for cell, value in d.coefficients
    ]
    row_frame = pl.DataFrame(row_records, schema=CONSTRAINT_ROW_SCHEMA).sort("constraint_id")
    coefficient_frame = pl.DataFrame(
        coefficient_records, schema=CONSTRAINT_COEFFICIENT_SCHEMA
    ).sort(["constraint_id", "cell_id"])
    return row_frame, coefficient_frame
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_rows.py -v`
Expected: PASS, all eleven tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/rows.py tests/unit/test_constraint_rows.py
git commit -m "feat(constraints): add the row factory and its four refusals

One construction point, four guards: §7.8's hard-eligible classes, §9.3's ban on
a hard constraint warranted by an assumed disclosure threshold, INV-007's vintage
check, and SRC-QCEW-006's decline. A builder written later cannot bypass them.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: The constraint builders

**Files:**
- Modify: `src/logging_employment/constraints/rows.py`
- Test: `tests/unit/test_constraint_builders.py`

**Interfaces:**
- Consumes: `ConstraintDraft`, `constraint`, `vintage_status` (Task 5); the `target_cell` frame
  (Task 3); the industry-filtered `qcew_national_size` frame.
- Produces, all returning `list[ConstraintDraft]`:
  `observed_value_rows(cells: pl.DataFrame)`, `nonnegativity_rows(cells: pl.DataFrame)`,
  `integrality_rows(cells: pl.DataFrame)`,
  `size_margin_rows(cells: pl.DataFrame)`,
  `size_support_rows(cells: pl.DataFrame, size_rows: pl.DataFrame)`; plus the single-row helper
  `rounding_interval_row(constraint_id: str, cell_id: str, *, published_value: float,
  grid_width: float, endpoint_rule: str, **scope) -> ConstraintDraft`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_builders.py`:

```python
"""What each builder emits, and the two things it must not."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.constraints import cells, rows
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError


def _built(make_monthly, make_size, size_spec):
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "observed", "employment_value": 700},
        {"state_fips": "02", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 1000,
         "qtrly_establishments": sum(int(row["establishments"]) for row in size_spec)},
    )
    size = make_size(*size_spec)
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cell_frame = cells.build_target_cells(
        data, industry_code="113310", ownership_code="5", size_concept="march_reference"
    )
    return cell_frame, size


_TWO_CLASSES = (
    {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0, "size_upper": 4},
    {"size_class": "6", "establishments": 4, "employment": None, "size_lower": 100,
     "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
)


def test_observed_and_true_zero_cells_are_pinned_to_their_published_values(
    make_monthly, make_size
) -> None:
    # INV-001: a disclosed QCEW target cell is preserved exactly.
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.observed_value_rows(cell_frame)
    pinned = {d.coefficients[0][0]: d.rhs_lower for d in drafts}
    assert all(d.relation == "eq" and d.is_hard for d in drafts)
    assert 700.0 in pinned.values() and 1000.0 in pinned.values() and 100.0 in pinned.values()
    assert not any("state_total|02" in cid for cid in pinned)


def test_only_suppressed_cells_receive_nonnegativity_and_integrality(
    make_monthly, make_size
) -> None:
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    nonneg = rows.nonnegativity_rows(cell_frame)
    integral = rows.integrality_rows(cell_frame)
    assert len(nonneg) == len(integral) == 2  # the suppressed state cell and the suppressed class
    assert {d.relation for d in nonneg} == {"ge"}
    assert {d.rhs_lower for d in nonneg} == {0.0}
    assert {d.relation for d in integral} == {"integrality"}
    assert all(d.constraint_class == "definitional_support" and d.is_hard for d in nonneg)


def test_the_size_margin_links_every_class_to_the_national_row_of_the_same_month(
    make_monthly, make_size
) -> None:
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.size_margin_rows(cell_frame)
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.relation == "eq" and draft.rhs_lower == 0.0 and draft.rhs_upper == 0.0
    weights = dict(draft.coefficients)
    assert sorted(weights.values()) == [-1.0, 1.0, 1.0]
    assert draft.constraint_class == "public_accounting_fact" and draft.is_hard


def test_a_suppressed_class_gets_a_support_row_from_its_published_establishment_count(
    make_monthly, make_size
) -> None:
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.size_support_rows(cell_frame, size)
    assert len(drafts) == 1
    support = drafts[0]
    assert support.relation == "range"
    assert (support.rhs_lower, support.rhs_upper) == (400.0, 996.0)  # 4 estabs in [100, 249]
    assert support.constraint_class == "definitional_support" and support.is_hard


def test_an_open_ended_top_class_emits_a_lower_bound_only(make_monthly, make_size) -> None:
    # §9.3 forbids arbitrary top-class caps; inventing a number to close class 9's band is
    # exactly that.
    spec = (
        {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0,
         "size_upper": 4},
        {"size_class": "9", "establishments": 2, "employment": None, "size_lower": 1000,
         "size_upper": None, "disclosure_code": "N", "observation_status": "suppressed"},
    )
    cell_frame, size = _built(make_monthly, make_size, spec)
    support = rows.size_support_rows(cell_frame, size)[0]
    assert support.relation == "ge"
    assert support.rhs_lower == 2000.0
    assert support.rhs_upper is None


def test_a_non_march_size_row_cannot_produce_a_support_row(make_monthly, make_size) -> None:
    # INV-011, enforced where the constraint is created rather than trusted from the data. Stage 6
    # inherits this builder.
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    june = size.with_columns(pl.lit("2024-06").alias("reference_month"))
    with pytest.raises(ConceptViolationError, match="March"):
        rows.size_support_rows(cell_frame, june)


def test_a_rounding_interval_becomes_a_range_and_records_its_endpoint_rule() -> None:
    # §9.4. No QCEW field this stage reads is rounded, so this helper is exercised by the property
    # tests rather than by the D1 run; it exists because §9.4 requires the encoding to be
    # field-specific and available.
    draft = rows.rounding_interval_row(
        "round|x", "cell-a", published_value=1200.0, grid_width=100.0,
        endpoint_rule="lower closed, upper open per source documentation",
        period_scope="2024-03", geography_scope="01", industry_scope="113310",
        ownership_scope="5", source_snapshot_ids="s1",
    )
    assert (draft.relation, draft.rhs_lower, draft.rhs_upper) == ("range", 1150.0, 1250.0)
    assert draft.constraint_class == "definitional_support"
    assert "upper open" in draft.provenance_text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_builders.py -v`
Expected: FAIL with `AttributeError: module 'logging_employment.constraints.rows' has no attribute
'observed_value_rows'`.

- [ ] **Step 3: Write the implementation**

Append to `src/logging_employment/constraints/rows.py` (and add
`from ..errors import ConceptViolationError` and `from .cells import KIND_NATIONAL_SIZE,
TOTAL_SIZE_CLASS, NATIONAL_STATE_FIPS` to its imports):

```python
def _scope(cell: dict[str, object]) -> dict[str, str]:
    """The four §7.8 scope fields for a restriction that touches exactly one cell."""
    return {
        "period_scope": str(cell["reference_month"]),
        "geography_scope": str(cell["state_fips"]),
        "industry_scope": str(cell["industry_code"]),
        "ownership_scope": str(cell["ownership_code"]),
    }


def observed_value_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """Pin every observed and true-zero cell to its published value (INV-001, §9.3 first bullet).

    True zeros are pinned alongside observed values because Stage 1 established them with a
    source-specific rule (INV-003): a cell with no establishments has no employment. A cell whose
    zero was never established that way carries `observation_status = 'suppressed'` and is left
    free here.
    """
    published = cells_frame.filter(pl.col("observation_status").is_in(["observed", "true_zero"]))
    return [
        constraint(
            constraint_id=f"fix|{cell['cell_id']}",
            constraint_class="public_accounting_fact",
            relation="eq",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=float(cell["observed_value"]),
            rhs_upper=float(cell["observed_value"]),
            is_hard=True,
            evidence_kind="published_value",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text=(
                f"published QCEW value {cell['observed_value']} for {cell['cell_id']}, "
                f"disclosure code {cell['qcew_disclosure_code']!r}"
            ),
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in published.iter_rows(named=True)
    ]


def nonnegativity_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """`x >= 0` for every unknown cell (§9.1, §9.3 nonnegativity bullet).

    Emitted per cell rather than declared once for the system: §7.9's coefficient table is the
    single source of truth for what the solver sees, and a restriction that lives only in a
    docstring carries no INV-004 label.
    """
    return [
        constraint(
            constraint_id=f"nonneg|{cell['cell_id']}",
            constraint_class="definitional_support",
            relation="ge",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=0.0,
            rhs_upper=None,
            is_hard=True,
            evidence_kind="unit_definition",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text="employment is a count of jobs and cannot be negative",
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in cells_frame.filter(
            pl.col("observation_status") == "suppressed"
        ).iter_rows(named=True)
    ]


def integrality_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """Integrality for every unknown cell (§9.3 integrality bullet, §9.6 step 2)."""
    return [
        constraint(
            constraint_id=f"integer|{cell['cell_id']}",
            constraint_class="definitional_support",
            relation="integrality",
            coefficients=((str(cell["cell_id"]), 1.0),),
            rhs_lower=None,
            rhs_upper=None,
            is_hard=True,
            evidence_kind="unit_definition",
            source_snapshot_ids=str(cell["source_snapshot_id"]),
            provenance_text="QCEW employment is an integer count of jobs",
            vintage_compatibility_status="compatible",
            **_scope(cell),
        )
        for cell in cells_frame.filter(
            pl.col("observation_status") == "suppressed"
        ).iter_rows(named=True)
    ]


def size_margin_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """One equality per March: the published size classes sum to the published all-sizes total.

    Written as `sum(classes) - total = 0` rather than `sum(classes) = <number>`, so the national
    all-sizes cell is a cell of the system and INV-001 pins it through its own fixing row. A number
    lifted into a right-hand side would leave that value unpinned and unauditable.

    This is the *only* margin this stage builds. There is no state-sum equivalent:
    `SRC-QCEW-006` came back `decline`.
    """
    drafts: list[ConstraintDraft] = []
    size_cells = cells_frame.filter(pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_SIZE}|"))
    total_cells = {
        cell["reference_month"]: cell
        for cell in cells_frame.filter(
            pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_TOTAL}|")
        ).iter_rows(named=True)
    }
    for month, group in size_cells.group_by("reference_month", maintain_order=True):
        reference_month = str(month[0])
        total = total_cells[reference_month]
        members = group.sort("size_class")
        coefficients = tuple(
            (str(cell["cell_id"]), 1.0) for cell in members.iter_rows(named=True)
        ) + ((str(total["cell_id"]), -1.0),)
        snapshots = sorted(
            {*members["source_snapshot_id"].to_list(), str(total["source_snapshot_id"])}
        )
        drafts.append(
            constraint(
                constraint_id=f"size_margin|{reference_month}",
                constraint_class="public_accounting_fact",
                relation="eq",
                coefficients=coefficients,
                rhs_lower=0.0,
                rhs_upper=0.0,
                is_hard=True,
                evidence_kind="published_value",
                period_scope=reference_month,
                geography_scope=NATIONAL_STATE_FIPS,
                industry_scope=str(total["industry_code"]),
                ownership_scope=str(total["ownership_code"]),
                source_snapshot_ids=",".join(snapshots),
                provenance_text=(
                    f"published national size classes {members['size_class'].to_list()} sum to the "
                    f"published all-sizes national total for {reference_month}"
                ),
                vintage_compatibility_status=vintage_status(
                    [*members["naics_vintage"].to_list(), str(total["naics_vintage"])]
                ),
            )
        )
    return drafts


def size_support_rows(
    cells_frame: pl.DataFrame, size_rows: pl.DataFrame
) -> list[ConstraintDraft]:
    """The §9.3 "documented size support" for every suppressed class.

    A class of `n` establishments each holding between `lower` and `upper` employees holds between
    `n * lower` and `n * upper` in total. `compat.assert_size_support_holds` measures that rule
    against every observed row before this builder runs, so the support is documented rather than
    assumed.

    INV-011 is enforced here rather than trusted from the data: this builder refuses a non-March
    row outright, so a later stage that reuses it cannot produce a March class bound for June.
    An open-ended top class emits its lower bound only -- §9.3 forbids arbitrary top-class caps,
    and a number invented to close the band would be one.
    """
    off_march = size_rows.filter(~pl.col("reference_month").str.ends_with("-03"))
    if off_march.height:
        raise ConceptViolationError(
            f"{off_march.height} size row(s) are not March-referenced, e.g. "
            f"{off_march['reference_month'][0]}; a March-reference class support may not be built "
            "outside its valid reference period (INV-011)"
        )
    by_cell = {
        cell["cell_id"]: cell
        for cell in cells_frame.filter(
            pl.col("cell_id").str.starts_with(f"{KIND_NATIONAL_SIZE}|")
            & (pl.col("observation_status") == "suppressed")
        ).iter_rows(named=True)
    }
    drafts: list[ConstraintDraft] = []
    for row in size_rows.filter(pl.col("observation_status") == "suppressed").iter_rows(named=True):
        identifier = None
        for cell_id, cell in by_cell.items():
            if (
                cell["reference_month"] == row["reference_month"]
                and cell["size_class"] == row["size_class"]
            ):
                identifier = cell_id
                break
        if identifier is None:
            continue
        lower = float(row["establishments"] * row["size_lower"])
        upper = None if row["size_upper"] is None else float(
            row["establishments"] * row["size_upper"]
        )
        drafts.append(
            constraint(
                constraint_id=f"size_support|{identifier}",
                constraint_class="definitional_support",
                relation="range" if upper is not None else "ge",
                coefficients=((identifier, 1.0),),
                rhs_lower=lower,
                rhs_upper=upper,
                is_hard=True,
                evidence_kind="class_definition",
                source_snapshot_ids=str(row["snapshot_id"]),
                provenance_text=(
                    f"{row['establishments']} published establishment(s) in class "
                    f"{row['size_class']} ([{row['size_lower']}, {row['size_upper']}] employees "
                    "per establishment, March reference)"
                ),
                vintage_compatibility_status="compatible",
                **_scope(by_cell[identifier]),
            )
        )
    return drafts


def rounding_interval_row(
    constraint_id: str,
    cell_id: str,
    *,
    published_value: float,
    grid_width: float,
    endpoint_rule: str,
    period_scope: str,
    geography_scope: str,
    industry_scope: str,
    ownership_scope: str,
    source_snapshot_ids: str,
) -> ConstraintDraft:
    """§9.4: a value rounded to grid width `r` enters as `[y - r/2, y + r/2]`, never as an equality.

    §9.4 writes the upper endpoint as strictly open. A linear program has no strict inequality, so
    the interval is encoded closed and `endpoint_rule` records what the source documents. That is a
    conservative widening -- it can only make a bound looser, never falsely exact, which is the
    direction INV-006 cares about.

    No QCEW field this stage reads is rounded, so nothing in the D1 run calls this. It exists
    because §9.4 requires rounding rules to be field-specific and encodable, and the §17.2 property
    "rounding intervals avoid false exact recovery" exercises it.
    """
    return constraint(
        constraint_id=constraint_id,
        constraint_class="definitional_support",
        relation="range",
        coefficients=((cell_id, 1.0),),
        rhs_lower=published_value - grid_width / 2,
        rhs_upper=published_value + grid_width / 2,
        is_hard=True,
        evidence_kind="rounding_documentation",
        period_scope=period_scope,
        geography_scope=geography_scope,
        industry_scope=industry_scope,
        ownership_scope=ownership_scope,
        source_snapshot_ids=source_snapshot_ids,
        provenance_text=(
            f"published value {published_value} rounded to grid width {grid_width}; "
            f"endpoint behaviour: {endpoint_rule}"
        ),
        vintage_compatibility_status="compatible",
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_builders.py -v`
Expected: PASS, all seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/rows.py tests/unit/test_constraint_builders.py
git commit -m "feat(constraints): build fixings, bounds, the size margin, and class supports

The margin is written as sum(classes) - total = 0 so the national all-sizes cell
is pinned by its own fixing row rather than dissolved into a right-hand side.
size_support_rows refuses a non-March row, so Stage 6 inherits INV-011 enforced.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `ConstraintSystem`, `build_constraint_system`, and the deterministic run id

**Files:**
- Create: `src/logging_employment/constraints/system.py`
- Create: `src/logging_employment/runs.py`
- Test: `tests/unit/test_constraint_system.py`

**Interfaces:**
- Consumes: everything from Tasks 3–6; `Config` (Task 1); `validate_frame` (Stage 1).
- Produces: the type aliases `CellTable`, `ConstraintRowTable`, `SparseCoefficientTable`; the
  `ConstraintSystem` Protocol of §16.2; the frozen dataclass `BuiltSystem(cells, rows,
  coefficients, constraint_set_hash, compatibility_report)`;
  `build_constraint_system(data: HarmonizedData, config: Config) -> BuiltSystem`;
  `constraint_set_hash(cells, rows, coefficients) -> str`; and, in `runs.py`,
  `run_id(config: Config, input_digests: Mapping[str, str]) -> str` and
  `run_dir(config: Config, identifier: str) -> Path`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_system.py`:

```python
"""The assembled system: what it contains, and what makes its hash and its run id stable."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment import runs
from logging_employment.config import load_config
from logging_employment.constraints import system
from logging_employment.contracts import (
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    TARGET_CELL_SCHEMA,
    HarmonizedData,
)
from logging_employment.errors import ConceptViolationError

REPO = Path(__file__).resolve().parents[2]


def _data(make_monthly, make_size) -> HarmonizedData:
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "observed", "employment_value": 700},
        {"state_fips": "02", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 1000, "qtrly_establishments": 54},
    )
    size = make_size(
        {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0,
         "size_upper": 4},
        {"size_class": "6", "establishments": 4, "employment": None, "size_lower": 100,
         "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
    )
    return HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )


def _cfg():
    return load_config(REPO / "config.yaml")


def test_the_system_matches_all_three_schemas(make_monthly, make_size) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    assert built.cells.schema == pl.Schema(TARGET_CELL_SCHEMA)
    assert built.rows.schema == pl.Schema(CONSTRAINT_ROW_SCHEMA)
    assert built.coefficients.schema == pl.Schema(CONSTRAINT_COEFFICIENT_SCHEMA)


def test_the_system_holds_one_row_family_per_builder(make_monthly, make_size) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    prefixes = [cid.split("|")[0] for cid in built.rows["constraint_id"]]
    assert prefixes.count("fix") == 3        # two observed state/national cells, one observed class
    assert prefixes.count("nonneg") == 2     # the suppressed state cell and the suppressed class
    assert prefixes.count("integer") == 2
    assert prefixes.count("size_margin") == 1
    assert prefixes.count("size_support") == 1


def test_no_row_couples_state_cells_to_each_other_or_to_the_national_row(
    make_monthly, make_size
) -> None:
    # The structural form of SRC-QCEW-006's `decline`, asserted on the assembled system rather
    # than only inside the factory.
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    kinds = {
        cid: cid.split("|")[0] for cid in built.cells["cell_id"]
    }
    touched = built.coefficients.join(
        pl.DataFrame({"cell_id": list(kinds), "kind": list(kinds.values())}), on="cell_id"
    )
    per_row = touched.group_by("constraint_id").agg(
        (pl.col("kind") == "state_total").sum().alias("states"),
        (pl.col("kind") == "national_total").any().alias("national"),
    )
    assert per_row.filter((pl.col("states") > 1) | ((pl.col("states") > 0) & pl.col("national"))).height == 0


def test_the_hash_is_stable_across_builds_and_moves_when_a_value_moves(
    make_monthly, make_size
) -> None:
    data = _data(make_monthly, make_size)
    first = system.build_constraint_system(data, _cfg())
    second = system.build_constraint_system(data, _cfg())
    assert first.constraint_set_hash == second.constraint_set_hash

    moved = HarmonizedData(
        qcew_monthly=data.qcew_monthly.with_columns(
            pl.when(pl.col("state_fips") == "01")
            .then(701)
            .otherwise(pl.col("employment_value"))
            .alias("employment_value")
        ),
        qcew_national_size=data.qcew_national_size,
        cbp_state_size=data.cbp_state_size,
        bridge=data.bridge,
    )
    assert system.build_constraint_system(moved, _cfg()).constraint_set_hash != first.constraint_set_hash


def test_the_hash_ignores_component_id_because_components_are_derived(
    make_monthly, make_size
) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    relabelled = built.rows.with_columns(pl.lit("c000042").alias("component_id"))
    assert (
        system.constraint_set_hash(built.cells, relabelled, built.coefficients)
        == built.constraint_set_hash
    )


def test_the_compatibility_gate_runs_before_any_row_is_built(make_monthly, make_size) -> None:
    data = _data(make_monthly, make_size)
    misaligned = HarmonizedData(
        qcew_monthly=pl.concat(
            [data.qcew_monthly, make_monthly({"industry_code": "111110", "area_type": "state"})]
        ),
        qcew_national_size=data.qcew_national_size,
        cbp_state_size=data.cbp_state_size,
        bridge=data.bridge,
    )
    with pytest.raises(ConceptViolationError):
        system.build_constraint_system(misaligned, _cfg())


def test_the_run_id_is_a_function_of_the_config_and_the_inputs_only() -> None:
    cfg = _cfg()
    digests = {"qcew_monthly": "aaa", "qcew_national_size": "bbb"}
    assert runs.run_id(cfg, digests) == runs.run_id(cfg, digests)
    assert runs.run_id(cfg, digests) != runs.run_id(cfg, {**digests, "qcew_monthly": "ccc"})
    assert len(runs.run_id(cfg, digests)) == 12


def test_the_run_directory_sits_under_the_configured_output_root() -> None:
    cfg = _cfg()
    assert runs.run_dir(cfg, "abc123abc123") == Path(cfg.storage.output_uri) / "abc123abc123"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_system.py -v`
Expected: FAIL with `ImportError: cannot import name 'runs'`.

- [ ] **Step 3: Write `runs.py`**

Create `src/logging_employment/runs.py`:

```python
"""The `runs/<run_id>/` layout of §6.2, with a run id derived from inputs rather than a clock.

§16.1 requires every command to be idempotent for the same inputs. A timestamp or a UUID would
make each invocation land in a new directory, so "idempotent" could only ever mean "wrote the same
bytes somewhere else". Deriving the id from the resolved configuration and the input digests makes
a repeated run land on its own previous output, where byte-identity is checkable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .config import Config, resolved_dict

RUN_ID_LENGTH = 12


def run_id(config: Config, input_digests: Mapping[str, str]) -> str:
    """A stable identifier for one run: the resolved config plus every input's digest."""
    payload = json.dumps(
        {"config": resolved_dict(config), "inputs": dict(sorted(input_digests.items()))},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:RUN_ID_LENGTH]


def run_dir(config: Config, identifier: str) -> Path:
    """The directory this run's outputs belong in."""
    return Path(config.storage.output_uri) / identifier
```

- [ ] **Step 4: Write `system.py`**

Create `src/logging_employment/constraints/system.py`:

```python
"""§16.2's `ConstraintSystem` and `build_constraint_system`.

Assembly order is load-bearing and matches §5.5 and SRC-QCEW-007: the compatibility gates run
first, then cells, then rows. A gate that ran after the rows were built would be checking a system
that already existed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from ..config import Config
from ..contracts import (
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    TARGET_CELL_SCHEMA,
    HarmonizedData,
    validate_frame,
)
from . import cells as cells_module
from . import compat, rows as rows_module

CellTable = pl.DataFrame
ConstraintRowTable = pl.DataFrame
SparseCoefficientTable = pl.DataFrame


class ConstraintSystem(Protocol):
    """§16.2's structural interface: cells, rows, and sparse coefficients."""

    cells: CellTable
    rows: ConstraintRowTable
    coefficients: SparseCoefficientTable


@dataclass(frozen=True)
class BuiltSystem:
    """A concrete `ConstraintSystem`, plus the hash and the gate report it was built under."""

    cells: CellTable
    rows: ConstraintRowTable
    coefficients: SparseCoefficientTable
    constraint_set_hash: str
    compatibility_report: dict[str, object]


def _frame_digest(frame: pl.DataFrame) -> str:
    """A sha256 over a frame's columns and its rows in total order."""
    ordered = frame.sort(by=frame.columns)
    payload = json.dumps(
        {"columns": ordered.columns, "rows": ordered.rows()}, default=str, sort_keys=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def constraint_set_hash(
    cells: CellTable, rows: ConstraintRowTable, coefficients: SparseCoefficientTable
) -> str:
    """The §18.1 constraint-set hash.

    `component_id` is excluded: components are *derived* from the coefficient pattern, so a system
    hashed before and after decomposition is the same system. Including it would make the hash
    change when only the labelling did, and §18.1 wants the hash to identify the constraint set.
    """
    without_components = rows.drop("component_id")
    digests = [_frame_digest(f) for f in (cells, without_components, coefficients)]
    return hashlib.sha256("|".join(digests).encode("utf-8")).hexdigest()


def build_constraint_system(data: HarmonizedData, config: Config) -> BuiltSystem:
    """Assemble the whole deterministic system from the harmonized layer (§16.2)."""
    industry = config.project.industry_code_used
    report = compat.run_compatibility_gates(data, industry_code=industry)

    cell_frame = cells_module.build_target_cells(
        data,
        industry_code=industry,
        ownership_code=PRIVATE_OWN_CODE,
        size_concept=config.project.size_concept,
    )
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry)

    drafts = [
        *rows_module.observed_value_rows(cell_frame),
        *rows_module.nonnegativity_rows(cell_frame),
        *rows_module.integrality_rows(cell_frame),
        *rows_module.size_margin_rows(cell_frame),
        *rows_module.size_support_rows(cell_frame, size),
    ]
    kinds = {cid: cid.split("|")[0] for cid in cell_frame["cell_id"].to_list()}
    rows_module.assert_no_national_employment_margin(drafts, kinds)

    row_frame, coefficient_frame = rows_module.to_frames(drafts)
    validate_frame(cell_frame, TARGET_CELL_SCHEMA, "target_cell")
    validate_frame(row_frame, CONSTRAINT_ROW_SCHEMA, "constraint_row")
    validate_frame(coefficient_frame, CONSTRAINT_COEFFICIENT_SCHEMA, "constraint_coefficient")

    return BuiltSystem(
        cells=cell_frame,
        rows=row_frame,
        coefficients=coefficient_frame,
        constraint_set_hash=constraint_set_hash(cell_frame, row_frame, coefficient_frame),
        compatibility_report=report,
    )
```

Add `from ..constants import PRIVATE_OWN_CODE` to the imports. The ownership code comes from
`constants`, not from a literal, because `config.project.ownership` is the word `private` while
QCEW's `own_code` is `'5'`, and the mapping between them is Stage 1's.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_system.py -v`
Expected: PASS, all eight tests.

- [ ] **Step 6: Commit**

```bash
git add src/logging_employment/constraints/system.py src/logging_employment/runs.py tests/unit/test_constraint_system.py
git commit -m "feat(constraints): assemble the system, hash it, and derive a run id from inputs

The constraint-set hash excludes component_id: components are derived from the
coefficient pattern, so labelling them is not a change to the constraint set.
run_id is a function of the config and the input digests, which is what lets
§16.1's idempotence claim be checked rather than asserted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Graph decomposition into connected components (CON-001, CON-002, CON-004)

**Files:**
- Create: `src/logging_employment/constraints/graph.py`
- Test: `tests/unit/test_constraint_graph.py`

**Interfaces:**
- Consumes: `BuiltSystem` (Task 7).
- Produces: `assign_components(built: BuiltSystem) -> BuiltSystem` returning a system whose
  `rows.component_id` is filled; `component_membership(built) ->
  pl.DataFrame` with columns `cell_id`, `component_id`; and `component_provenance(built) ->
  pl.DataFrame` with columns `component_id`, `cell_count`, `constraint_count`, `constraint_ids`,
  `source_snapshot_ids`, `hard_constraint_count`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_graph.py`:

```python
"""CON-001/002/004: the bipartite graph, its components, and what explains each one."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import graph, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]


def _built(make_monthly, make_size):
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        {"state_fips": "02", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 1000, "qtrly_establishments": 54},
    )
    size = make_size(
        {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0,
         "size_upper": 4},
        {"size_class": "6", "establishments": 4, "employment": None, "size_lower": 100,
         "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
    )
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    return system.build_constraint_system(data, load_config(REPO / "config.yaml"))


def test_the_two_suppressed_state_cells_are_their_own_components(make_monthly, make_size) -> None:
    # Nothing couples them: SRC-QCEW-006 came back `decline`, so there is no state-sum margin.
    assigned = graph.assign_components(_built(make_monthly, make_size))
    membership = graph.component_membership(assigned)
    by_cell = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    state_components = {v for k, v in by_cell.items() if k.startswith("state_total|")}
    assert len(state_components) == 2


def test_the_size_classes_and_the_national_row_share_one_component(
    make_monthly, make_size
) -> None:
    assigned = graph.assign_components(_built(make_monthly, make_size))
    membership = graph.component_membership(assigned)
    by_cell = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    coupled = {
        v for k, v in by_cell.items()
        if k.startswith("national_size|") or k.startswith("national_total|")
    }
    assert len(coupled) == 1


def test_component_ids_are_stable_across_runs_and_ordered_by_their_smallest_cell(
    make_monthly, make_size
) -> None:
    first = graph.component_membership(graph.assign_components(_built(make_monthly, make_size)))
    second = graph.component_membership(graph.assign_components(_built(make_monthly, make_size)))
    assert first.equals(second)
    smallest = (
        first.group_by("component_id").agg(pl.col("cell_id").min()).sort("component_id")
    )
    assert smallest["cell_id"].to_list() == sorted(smallest["cell_id"].to_list())


def test_every_row_receives_a_component_id_and_the_cells_table_keeps_its_shape(
    make_monthly, make_size
) -> None:
    # §7.7's field list has no component_id; membership is derived, never stored on the cells.
    built = _built(make_monthly, make_size)
    assigned = graph.assign_components(built)
    assert assigned.rows["component_id"].null_count() == 0
    assert assigned.cells.columns == built.cells.columns
    assert graph.component_membership(assigned)["cell_id"].n_unique() == assigned.cells.height


def test_provenance_names_the_constraints_and_snapshots_behind_each_component(
    make_monthly, make_size
) -> None:
    # CON-004: store enough provenance to explain which public margins identify or narrow a cell.
    assigned = graph.assign_components(_built(make_monthly, make_size))
    provenance = graph.component_provenance(assigned)
    coupled = provenance.filter(pl.col("cell_count") > 1).row(0, named=True)
    assert "size_margin|2024-03" in coupled["constraint_ids"]
    assert coupled["hard_constraint_count"] == coupled["constraint_count"]
    assert "2024_q1_by_size" in coupled["source_snapshot_ids"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_graph.py -v`
Expected: FAIL with `ImportError: cannot import name 'graph'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/graph.py`:

```python
"""CON-001, CON-002 and CON-004: the sparse bipartite graph and its connected components.

Nodes are cells and constraint rows; an edge is a non-zero coefficient. Two cells are in the same
component when a chain of constraints connects them, which is exactly the condition under which
solving one can change the bounds of the other -- so components are the unit §9.6 batches over.

Component labels are ordered by the smallest `cell_id` each component contains. SciPy's labelling
is an implementation detail of its traversal order; a run whose component ids moved because SciPy
changed would look like a data change in every manifest that records them.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.csgraph import connected_components

from .system import BuiltSystem

COMPONENT_ID_FORMAT = "c{:06d}"


def _labels(built: BuiltSystem) -> dict[str, str]:
    """One component label per cell id, ordered by the smallest cell id in each component."""
    cell_ids = built.cells["cell_id"].to_list()
    row_ids = built.rows["constraint_id"].to_list()
    cell_at = {cell: i for i, cell in enumerate(cell_ids)}
    row_at = {row: len(cell_ids) + i for i, row in enumerate(row_ids)}

    left = np.array([cell_at[c] for c in built.coefficients["cell_id"].to_list()], dtype=np.int64)
    right = np.array(
        [row_at[r] for r in built.coefficients["constraint_id"].to_list()], dtype=np.int64
    )
    size = len(cell_ids) + len(row_ids)
    adjacency = coo_matrix((np.ones(left.size), (left, right)), shape=(size, size))
    _, raw = connected_components(csr_matrix(adjacency + adjacency.T), directed=False)

    smallest: dict[int, str] = {}
    for cell, label in zip(cell_ids, raw[: len(cell_ids)].tolist(), strict=True):
        if label not in smallest or cell < smallest[label]:
            smallest[label] = cell
    ordered = sorted(smallest, key=lambda label: smallest[label])
    names = {label: COMPONENT_ID_FORMAT.format(i) for i, label in enumerate(ordered)}
    return {
        cell: names[label]
        for cell, label in zip(cell_ids, raw[: len(cell_ids)].tolist(), strict=True)
    }


def assign_components(built: BuiltSystem) -> BuiltSystem:
    """Return the same system with `component_id` filled on every constraint row.

    The label lands on rows only. §7.7's field list has no `component_id`, and a `target_cell`
    frame carrying an extra column would fail `validate_frame` -- so cell membership is *derived*
    by `component_membership` rather than stored, which also keeps one authority for it.
    """
    by_cell = _labels(built)
    row_component = (
        built.coefficients.with_columns(
            pl.col("cell_id").replace_strict(by_cell).alias("component_id")
        )
        .group_by("constraint_id")
        .agg(pl.col("component_id").first())
    )
    rows = (
        built.rows.drop("component_id")
        .join(row_component, on="constraint_id", how="left")
        .select(built.rows.columns)
        .sort("constraint_id")
    )
    return replace(built, rows=rows)


def component_membership(built: BuiltSystem) -> pl.DataFrame:
    """`cell_id` to `component_id`, derived through the rows that touch each cell.

    Every cell carries at least one row -- an observed cell its fixing, a suppressed cell its
    nonnegativity -- so this covers the whole index rather than the coupled part of it.
    """
    return (
        built.coefficients.join(
            built.rows.select(["constraint_id", "component_id"]), on="constraint_id", how="left"
        )
        .select(["cell_id", "component_id"])
        .unique()
        .sort("cell_id")
    )


def component_provenance(built: BuiltSystem) -> pl.DataFrame:
    """CON-004: what explains each component, in one row per component."""
    per_cell = component_membership(built).group_by("component_id").agg(
        pl.len().alias("cell_count")
    )
    per_row = built.rows.group_by("component_id").agg(
        pl.len().alias("constraint_count"),
        pl.col("is_hard").sum().alias("hard_constraint_count"),
        pl.col("constraint_id").sort().str.join(",").alias("constraint_ids"),
        pl.col("source_snapshot_ids").unique().sort().str.join(",").alias("source_snapshot_ids"),
    )
    return per_cell.join(per_row, on="component_id", how="left").sort("component_id")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_graph.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/graph.py tests/unit/test_constraint_graph.py
git commit -m "feat(constraints): decompose the system into components with stable ids

Component labels are ordered by their smallest cell id rather than taken from
SciPy's traversal order, so a SciPy upgrade cannot look like a data change in
every manifest that records them.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: Structural and numerical rank, nullity, and the hierarchy cache (CON-003, CON-005)

**Files:**
- Create: `src/logging_employment/constraints/rank.py`
- Test: `tests/unit/test_constraint_rank.py`

**Interfaces:**
- Consumes: `BuiltSystem` and `component_membership` (Tasks 7–8).
- Produces: the frozen dataclass `RankRecord(component_id, cell_count, equality_row_count,
  structural_rank, numerical_rank, nullity, cache_hit)`; `equality_matrix(built, component_id,
  membership) -> tuple[np.ndarray, list[str]]`; `component_rank(built, component_id, membership, *,
  rank_tolerance, cache) -> RankRecord`; and `rank_table(built, *, rank_tolerance) -> pl.DataFrame`
  with one row per component and the `RankRecord` fields as columns.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_rank.py`:

```python
"""CON-003 and CON-005: two ranks per component, and one computation per distinct shape."""

from __future__ import annotations

import numpy as np
import polars as pl

from logging_employment.constraints import rank


def test_a_matrix_can_be_structurally_full_rank_and_numerically_deficient() -> None:
    # The two ranks answer different questions, which is why CON-003 asks for both. Two identical
    # rows have a perfect matching in the bipartite pattern and one linearly independent row.
    matrix = np.array([[1.0, 1.0], [1.0, 1.0]])
    assert rank.structural_rank_of(matrix) == 2
    assert rank.numerical_rank_of(matrix, tolerance=1e-10) == 1


def test_a_component_with_no_equality_carries_rank_zero_and_full_nullity() -> None:
    # Every suppressed state cell is this shape: nonnegativity and integrality, no equality.
    matrix = np.zeros((0, 1))
    assert rank.structural_rank_of(matrix) == 0
    assert rank.numerical_rank_of(matrix, tolerance=1e-10) == 0


def test_the_size_component_has_one_degree_of_freedom_per_pair_of_unknowns(
    make_monthly, make_size, built_size_component
) -> None:
    table = built_size_component
    coupled = table.filter(pl.col("cell_count") > 1).row(0, named=True)
    assert coupled["cell_count"] == 7          # six classes plus the national all-sizes cell
    assert coupled["equality_row_count"] == 6  # the margin, four class fixings, one total fixing
    assert coupled["numerical_rank"] == 6
    assert coupled["nullity"] == 1


def test_two_structurally_identical_components_are_computed_once(
    make_monthly, make_size, two_identical_years
) -> None:
    # CON-005: cache reusable hierarchy matrices across periods when definitions are unchanged.
    table = two_identical_years
    coupled = table.filter(pl.col("cell_count") > 1).sort("component_id")
    assert coupled.height == 2
    assert coupled["cache_hit"].to_list() == [False, True]
    assert coupled["numerical_rank"].n_unique() == 1


def test_every_component_appears_exactly_once_in_the_table(single_year_table) -> None:
    assert single_year_table["component_id"].n_unique() == single_year_table.height
```

Add these fixtures to the same module (they build the systems the assertions read):

```python
import pytest

from pathlib import Path

from logging_employment.config import load_config
from logging_employment.constraints import graph, system
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]

_CLASSES_2024 = (
    {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0, "size_upper": 4},
    {"size_class": "2", "establishments": 20, "employment": 120, "size_lower": 5, "size_upper": 9},
    {"size_class": "3", "establishments": 10, "employment": 130, "size_lower": 10,
     "size_upper": 19},
    {"size_class": "4", "establishments": 5, "employment": 150, "size_lower": 20,
     "size_upper": 49},
    {"size_class": "5", "establishments": 4, "employment": None, "size_lower": 50,
     "size_upper": 99, "disclosure_code": "N", "observation_status": "suppressed"},
    {"size_class": "6", "establishments": 2, "employment": None, "size_lower": 100,
     "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
)


def _system(monthly_rows, size_rows):
    data = HarmonizedData(
        qcew_monthly=monthly_rows, qcew_national_size=size_rows,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    return graph.assign_components(system.build_constraint_system(data, cfg)), cfg


def _national(month: str, employment: int, establishments: int) -> dict[str, object]:
    return {
        "area_fips": "US000", "area_type": "national", "state_fips": None,
        "aggregation_level": "18", "reference_month": month, "reference_quarter": month[:4] + "Q1",
        "employment_value": employment, "employment_raw": str(employment),
        "qtrly_establishments": establishments,
    }


@pytest.fixture()
def single_year_table(make_monthly, make_size) -> pl.DataFrame:
    """One March, six classes, two suppressed, plus one suppressed state cell."""
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        _national("2024-03", 1000, 91),
    )
    built, cfg = _system(monthly, make_size(*_CLASSES_2024))
    return rank.rank_table(built, rank_tolerance=cfg.constraints.rank_tolerance)


@pytest.fixture()
def built_size_component(single_year_table) -> pl.DataFrame:
    return single_year_table


@pytest.fixture()
def two_identical_years(make_monthly, make_size) -> pl.DataFrame:
    """Two Marches with the same class structure and the same suppression pattern."""
    def _year(year: int) -> list[dict[str, object]]:
        return [
            row | {"reference_year": year, "reference_month": f"{year}-03",
                   "reference_quarter": f"{year}Q1", "snapshot_id": f"{year}_q1_by_size"}
            for row in _CLASSES_2024
        ]

    monthly = make_monthly(_national("2023-03", 1000, 91), _national("2024-03", 1000, 91))
    size = make_size(*_year(2023), *_year(2024))
    built, cfg = _system(monthly, size)
    return rank.rank_table(built, rank_tolerance=cfg.constraints.rank_tolerance)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_rank.py -v`
Expected: FAIL with `ImportError: cannot import name 'rank'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/rank.py`:

```python
"""CON-003 and CON-005: rank, nullity, and one computation per distinct component shape.

Rank is computed over the component's *equality* rows. Inequalities -- nonnegativity, class
supports, rounding intervals -- narrow a feasible set without removing a degree of freedom, so
counting them would report a cell as identified when it is only bounded. Nullity is therefore the
number of free directions the equalities leave, which is what CON-003 records and what a reader
uses to explain why a cell is or is not pinned.

Both ranks are computed because they answer different questions. Structural rank is a property of
the sparsity pattern -- the largest matching between rows and columns -- and cannot be fooled by
cancellation; numerical rank is a property of the values, and is the one that changes when two
margins say the same thing. A component where they disagree is a component where the pattern
promises identification the numbers do not deliver.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import structural_rank

from .graph import component_membership
from .system import BuiltSystem


@dataclass(frozen=True)
class RankRecord:
    """CON-003's record for one component."""

    component_id: str
    cell_count: int
    equality_row_count: int
    structural_rank: int
    numerical_rank: int
    nullity: int
    cache_hit: bool


def structural_rank_of(matrix: np.ndarray) -> int:
    """The largest row-column matching in the matrix's sparsity pattern."""
    if matrix.size == 0 or matrix.shape[0] == 0:
        return 0
    return int(structural_rank(csr_matrix(matrix)))


def numerical_rank_of(matrix: np.ndarray, *, tolerance: float) -> int:
    """The number of linearly independent rows at the configured tolerance."""
    if matrix.size == 0 or matrix.shape[0] == 0:
        return 0
    return int(np.linalg.matrix_rank(matrix, tol=tolerance))


def equality_matrix(
    built: BuiltSystem, component_id: str, membership: pl.DataFrame
) -> tuple[np.ndarray, list[str]]:
    """The dense equality matrix for one component, with its column order.

    Dense because a component here is at most a few dozen cells; the whole system is sparse, but no
    single component is large enough for a sparse rank routine to pay for itself.

    Soft equalities are excluded. Rank here answers "how many degrees of freedom does the feasible
    set leave", and INV-005 says a soft restriction is not part of that set.
    """
    cells = sorted(
        membership.filter(pl.col("component_id") == component_id)["cell_id"].to_list()
    )
    equality_ids = built.rows.filter(
        (pl.col("component_id") == component_id)
        & (pl.col("relation") == "eq")
        & pl.col("is_hard")  # INV-005: rank describes the feasible set, so only hard rows count
    )["constraint_id"].sort().to_list()
    matrix = np.zeros((len(equality_ids), len(cells)))
    at_row = {name: i for i, name in enumerate(equality_ids)}
    at_column = {name: i for i, name in enumerate(cells)}
    for entry in built.coefficients.filter(
        pl.col("constraint_id").is_in(equality_ids)
    ).iter_rows(named=True):
        matrix[at_row[entry["constraint_id"]], at_column[entry["cell_id"]]] = entry["coefficient"]
    return matrix, cells


def _shape_key(matrix: np.ndarray) -> str:
    """CON-005's cache key: the matrix itself, positionally, with no cell identity in it.

    Two Marches whose class structure and suppression pattern are unchanged produce the same key,
    which is exactly the "definitions are unchanged" condition CON-005 names.
    """
    payload = f"{matrix.shape}|{np.array2string(matrix, precision=12, threshold=matrix.size + 1)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def component_rank(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    *,
    rank_tolerance: float,
    cache: dict[str, tuple[int, int]],
) -> RankRecord:
    """Rank and nullity for one component, reusing a cached shape when one matches."""
    matrix, cells = equality_matrix(built, component_id, membership)
    key = _shape_key(matrix)
    hit = key in cache
    if not hit:
        cache[key] = (
            structural_rank_of(matrix),
            numerical_rank_of(matrix, tolerance=rank_tolerance),
        )
    structural, numerical = cache[key]
    return RankRecord(
        component_id=component_id,
        cell_count=len(cells),
        equality_row_count=matrix.shape[0],
        structural_rank=structural,
        numerical_rank=numerical,
        nullity=len(cells) - numerical,
        cache_hit=hit,
    )


def rank_table(built: BuiltSystem, *, rank_tolerance: float) -> pl.DataFrame:
    """One `RankRecord` per component, in component order."""
    membership = component_membership(built)
    cache: dict[str, tuple[int, int]] = {}
    records = [
        component_rank(
            built, component_id, membership, rank_tolerance=rank_tolerance, cache=cache
        )
        for component_id in sorted(set(membership["component_id"].to_list()))
    ]
    return pl.DataFrame([record.__dict__ for record in records])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_rank.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/rank.py tests/unit/test_constraint_rank.py
git commit -m "feat(constraints): compute structural and numerical rank per component

Rank runs over equality rows only: an inequality narrows a feasible set without
removing a degree of freedom, and counting it would report a cell as identified
when it is merely bounded. The CON-005 cache keys on the positional matrix, so
two Marches with unchanged definitions compute once.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: LP bounds on HiGHS

**Files:**
- Create: `src/logging_employment/constraints/bounds.py`
- Test: `tests/unit/test_constraint_bounds.py`

**Interfaces:**
- Consumes: `BuiltSystem`, `component_membership`, `rank_table` (Tasks 7–9); `ConstraintsConfig`
  (Task 1).
- Produces: `BoundConfig = ConstraintsConfig` (the §16.2 name); the frozen dataclass
  `ColumnSpec(lower, upper, is_integer)`; `column_specs(built, component_id, membership) ->
  dict[str, ColumnSpec]`; `matrix_rows(built, component_id) -> list[dict]`;
  `solve_component(built, component_id, membership, config, *, integer: bool) ->
  dict[str, tuple[float | None, float | None, str]]` mapping each unknown cell to
  `(lower, upper, solver_status)`, raising `SolverError` on any other solver status.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_bounds.py`:

```python
"""§9.6: what HiGHS returns for each component shape this stage produces."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from dataclasses import replace

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, rows, system
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]


def _built(monthly, size):
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    return graph.assign_components(system.build_constraint_system(data, cfg)), cfg


def _national(month, employment, establishments):
    return {
        "area_fips": "US000", "area_type": "national", "state_fips": None,
        "aggregation_level": "18", "reference_month": month,
        "employment_value": employment, "employment_raw": str(employment),
        "qtrly_establishments": establishments,
    }


_REAL_2024 = (
    {"size_class": "1", "establishments": 5007, "employment": 7630, "size_lower": 0,
     "size_upper": 4},
    {"size_class": "2", "establishments": 1501, "employment": 9955, "size_lower": 5,
     "size_upper": 9},
    {"size_class": "3", "establishments": 803, "employment": 10480, "size_lower": 10,
     "size_upper": 19},
    {"size_class": "4", "establishments": 357, "employment": 10316, "size_lower": 20,
     "size_upper": 49},
    {"size_class": "5", "establishments": 40, "employment": 2507, "size_lower": 50,
     "size_upper": 99},
    {"size_class": "6", "establishments": 4, "employment": None, "size_lower": 100,
     "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
    {"size_class": "7", "establishments": 1, "employment": None, "size_lower": 250,
     "size_upper": 499, "disclosure_code": "N", "observation_status": "suppressed"},
)


def test_the_real_2024_size_component_reproduces_its_published_sharp_bounds(
    make_monthly, make_size
) -> None:
    # Residual 41668 - 40888 = 780, with supports [400, 996] and [250, 499]. Computed analytically
    # while this plan was written and reproduced by HiGHS.
    built, cfg = _built(
        make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024)
    )
    membership = graph.component_membership(built)
    coupled = (
        membership.filter(pl.col("cell_id").str.starts_with("national_size|"))["component_id"][0]
    )
    solved = bounds.solve_component(
        built, coupled, membership, cfg.constraints, integer=False
    )
    by_class = {cell.rsplit("|", 1)[1]: value for cell, value in solved.items()}
    assert by_class["6"][:2] == (400.0, 530.0)
    assert by_class["7"][:2] == (250.0, 380.0)
    assert by_class["6"][2] == "optimal"


def test_a_suppressed_state_cell_is_bounded_below_and_unbounded_above(
    make_monthly, make_size
) -> None:
    # The whole consequence of SRC-QCEW-006's `decline`, in one assertion.
    built, cfg = _built(
        make_monthly(
            {"state_fips": "01", "observation_status": "suppressed", "employment_value": None,
             "disclosure_code": "N"},
            _national("2024-03", 200, 60),
        ),
        make_size({"size_class": "1", "establishments": 60, "employment": 200, "size_lower": 0,
                   "size_upper": 4}),
    )
    membership = graph.component_membership(built)
    lonely = membership.filter(pl.col("cell_id").str.starts_with("state_total|"))["component_id"][0]
    solved = bounds.solve_component(built, lonely, membership, cfg.constraints, integer=False)
    (lower, upper, status), = solved.values()
    assert lower == 0.0
    assert upper is None
    assert status == "unbounded"


def test_an_infeasible_component_raises_rather_than_relaxing(make_monthly, make_size) -> None:
    # §9.6 step 4: stop and emit diagnostics on infeasibility; do not silently relax. The residual
    # here is 600 against supports that need at least 650.
    perturbed = tuple(
        row | {"employment": row["employment"] + 180} if row["size_class"] == "1" else row
        for row in _REAL_2024
    )
    built, cfg = _built(
        make_monthly(_national("2024-03", 41668, 7713)), make_size(*perturbed)
    )
    membership = graph.component_membership(built)
    coupled = (
        membership.filter(pl.col("cell_id").str.starts_with("national_size|"))["component_id"][0]
    )
    with pytest.raises(InfeasibleComponentError, match=coupled):
        bounds.solve_component(built, coupled, membership, cfg.constraints, integer=False)


def test_a_soft_row_is_recorded_but_never_narrows_a_bound(make_monthly, make_size) -> None:
    # INV-005: only public accounting facts and valid definitional restrictions enter the
    # deterministic feasible set. Nothing in D1 builds a soft row, so this is the test that keeps
    # the filter honest until Stage 3 adds CBP as an empirical measurement.
    built, cfg = _built(
        make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024)
    )
    membership = graph.component_membership(built)
    coupled = (
        membership.filter(pl.col("cell_id").str.starts_with("national_size|"))["component_id"][0]
    )
    class_six = next(
        c for c in membership.filter(pl.col("component_id") == coupled)["cell_id"]
        if c.endswith("|6")
    )
    soft = rows.constraint(
        constraint_id=f"soft|{class_six}",
        constraint_class="empirical_measurement",
        relation="le",
        coefficients=((class_six, 1.0),),
        rhs_lower=None,
        rhs_upper=450.0,  # would cut the upper bound from 530 to 450 if it entered the model
        is_hard=False,
        evidence_kind="empirical_fit",
        period_scope="2024-03",
        geography_scope="US",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="toy",
        provenance_text="a soft measurement that must not narrow a deterministic bound",
        vintage_compatibility_status="compatible",
    )
    soft_rows, soft_coefficients = rows.to_frames([soft])
    widened = replace(
        built,
        rows=pl.concat(
            [built.rows, soft_rows.with_columns(pl.lit(coupled).alias("component_id"))]
        ),
        coefficients=pl.concat([built.coefficients, soft_coefficients]),
    )
    solved = bounds.solve_component(widened, coupled, membership, cfg.constraints, integer=False)
    assert {c.rsplit("|", 1)[1]: v[:2] for c, v in solved.items()}["6"] == (400.0, 530.0)


def test_column_specs_fold_single_cell_rows_into_bounds_and_leave_the_margin_in_the_matrix(
    make_monthly, make_size
) -> None:
    built, _ = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024))
    membership = graph.component_membership(built)
    coupled = (
        membership.filter(pl.col("cell_id").str.starts_with("national_size|"))["component_id"][0]
    )
    specs = bounds.column_specs(built, coupled, membership)
    class_six = next(spec for cell, spec in specs.items() if cell.endswith("|6"))
    assert (class_six.lower, class_six.upper) == (400.0, 996.0)
    assert class_six.is_integer is True
    assert len(bounds.matrix_rows(built, coupled)) == 1  # the size margin only
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_bounds.py -v`
Expected: FAIL with `ImportError: cannot import name 'bounds'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/bounds.py`:

```python
"""§9.6: sharp LP bounds for every unknown cell, one HiGHS model per component.

Two optimizations per unknown cell -- a minimize and a maximize -- give `L_j` and `U_j` of §9.1.
They are sharp feasible bounds under the encoded public information, and they are not confidence
or credible intervals; §7.10 keeps them in columns that Stage 5's posterior intervals never share
(INV-008).

Model construction folds single-cell rows into column bounds and leaves everything else in the
matrix. That is not an optimization: it is §9.1's own form, where `x >= 0` and the box constraints
sit outside `Bx = c`. A row qualifies only when it touches one cell with coefficient exactly 1.0,
so a scaled single-cell restriction still reaches the matrix rather than being silently divided.

Every component gets a feasibility probe before any objective is solved, including components with
no unknown cell. Without it, a component whose published values contradict each other -- 2017's
size margin, if BLS ever revised one class and not the total -- would pass unexamined because there
was nothing to optimize.
"""

from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np
import polars as pl

from ..config import ConstraintsConfig
from ..errors import InfeasibleComponentError, SolverError
from .system import BuiltSystem

# §16.2 names this type `BoundConfig`. It is the `constraints:` block, under the name the spec's
# signature uses.
BoundConfig = ConstraintsConfig

INFINITY = highspy.kHighsInf


@dataclass(frozen=True)
class ColumnSpec:
    """One decision variable: its box, and whether it is an integer count."""

    lower: float
    upper: float
    is_integer: bool


def _single_cell(entries: pl.DataFrame) -> bool:
    """True when a row touches exactly one cell with coefficient 1.0."""
    return entries.height == 1 and entries["coefficient"][0] == 1.0


def column_specs(
    built: BuiltSystem, component_id: str, membership: pl.DataFrame
) -> dict[str, ColumnSpec]:
    """The box and integrality of every cell in one component."""
    cells = sorted(membership.filter(pl.col("component_id") == component_id)["cell_id"].to_list())
    box: dict[str, list[float]] = {cell: [-INFINITY, INFINITY] for cell in cells}
    integer = dict.fromkeys(cells, False)
    # INV-005: only public accounting facts and valid definitional restrictions enter the
    # deterministic feasible set, and `is_hard` is exactly that predicate (§7.8 restricts it to
    # those two classes). A soft row stays in the graph and in the persisted table -- it is part of
    # the recorded system -- but it must not move a bound. Stage 3 adds CBP as
    # `empirical_measurement`, which is when this filter starts doing visible work.
    rows = built.rows.filter((pl.col("component_id") == component_id) & pl.col("is_hard"))
    for row in rows.iter_rows(named=True):
        entries = built.coefficients.filter(pl.col("constraint_id") == row["constraint_id"])
        if row["relation"] == "integrality":
            integer[entries["cell_id"][0]] = True
            continue
        if not _single_cell(entries):
            continue
        cell = entries["cell_id"][0]
        if row["rhs_lower"] is not None:
            box[cell][0] = max(box[cell][0], float(row["rhs_lower"]))
        if row["rhs_upper"] is not None:
            box[cell][1] = min(box[cell][1], float(row["rhs_upper"]))
    return {
        cell: ColumnSpec(lower=box[cell][0], upper=box[cell][1], is_integer=integer[cell])
        for cell in cells
    }


def matrix_rows(built: BuiltSystem, component_id: str) -> list[dict[str, object]]:
    """Every hard row of this component that couples two or more cells.

    Soft rows are excluded here for the same INV-005 reason `column_specs` states. Both filters
    have to agree: a soft row admitted by one and rejected by the other would put half a
    restriction in the model.
    """
    kept: list[dict[str, object]] = []
    for row in built.rows.filter(
        (pl.col("component_id") == component_id)
        & (pl.col("relation") != "integrality")
        & pl.col("is_hard")  # INV-005; see `column_specs`
    ).iter_rows(named=True):
        entries = built.coefficients.filter(pl.col("constraint_id") == row["constraint_id"])
        if _single_cell(entries):
            continue
        kept.append(
            {
                "constraint_id": row["constraint_id"],
                "lower": -INFINITY if row["rhs_lower"] is None else float(row["rhs_lower"]),
                "upper": INFINITY if row["rhs_upper"] is None else float(row["rhs_upper"]),
                "cells": entries["cell_id"].to_list(),
                "values": [float(v) for v in entries["coefficient"].to_list()],
            }
        )
    return kept


def _model(
    specs: dict[str, ColumnSpec],
    rows: list[dict[str, object]],
    config: BoundConfig,
    *,
    integer: bool,
) -> tuple[highspy.Highs, dict[str, int]]:
    """A HiGHS model for one component, and the column index of each cell."""
    order = list(specs)
    at = {cell: i for i, cell in enumerate(order)}
    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("primal_feasibility_tolerance", config.feasibility_tolerance)
    model.setOptionValue("dual_feasibility_tolerance", config.feasibility_tolerance)
    model.setOptionValue("mip_feasibility_tolerance", config.feasibility_tolerance)
    model.addVars(
        len(order),
        np.array([specs[cell].lower for cell in order]),
        np.array([specs[cell].upper for cell in order]),
    )
    for row in rows:
        indices = np.array([at[cell] for cell in row["cells"]], dtype=np.int32)
        model.addRow(row["lower"], row["upper"], indices.size, indices, np.array(row["values"]))
    if integer:
        marked = [i for cell, i in at.items() if specs[cell].is_integer]
        if marked:
            model.changeColsIntegrality(
                len(marked),
                np.array(marked, dtype=np.int32),
                np.array([highspy.HighsVarType.kInteger] * len(marked)),
            )
    return model, at


def _optimize(model: highspy.Highs, index: int, sense: object) -> tuple[float | None, str]:
    """One objective solve, returning the optimum or `None` when that direction is unbounded."""
    model.changeColsCost(1, np.array([index], dtype=np.int32), np.array([1.0]))
    model.changeObjectiveSense(sense)
    model.run()
    status = model.getModelStatus()
    model.changeColsCost(1, np.array([index], dtype=np.int32), np.array([0.0]))
    if status == highspy.HighsModelStatus.kOptimal:
        return float(model.getInfo().objective_function_value), "optimal"
    if status == highspy.HighsModelStatus.kUnbounded:
        return None, "unbounded"
    # REQ-029 names the solver among the things this system fails closed on. `kIterationLimit`,
    # `kTimeLimit` and `kUnknown` are not answers, and returning `None` for them would be
    # indistinguishable from `kUnbounded` two lines up -- a cell the solver gave up on would ship
    # as a cell public data cannot bound.
    raise SolverError(
        f"HiGHS returned {model.modelStatusToString(status)} while optimizing column {index}; "
        "that is neither an optimum nor an unbounded direction, so no bound can be recorded"
    )


def solve_component(
    built: BuiltSystem,
    component_id: str,
    membership: pl.DataFrame,
    config: BoundConfig,
    *,
    integer: bool,
) -> dict[str, tuple[float | None, float | None, str]]:
    """Sharp bounds for every unknown cell in one component.

    Observed cells are not solved: INV-001 pins them to their published values, and an equality
    already in the model would return that value at some solver cost. The feasibility probe below
    is what still exercises those equalities.
    """
    specs = column_specs(built, component_id, membership)
    rows = matrix_rows(built, component_id)
    model, at = _model(specs, rows, config, integer=integer)

    model.run()
    probe = model.getModelStatus()
    if probe == highspy.HighsModelStatus.kInfeasible:
        raise InfeasibleComponentError(
            f"component {component_id} has no feasible point across {len(specs)} cell(s) and "
            f"{len(rows)} coupling row(s); §9.6 forbids relaxing a production constraint to "
            "continue. Run `solve-bounds` diagnostics for the conflicting rows"
        )

    unknown = set(
        built.cells.filter(pl.col("observation_status") == "suppressed")["cell_id"].to_list()
    )
    solved: dict[str, tuple[float | None, float | None, str]] = {}
    for cell, index in at.items():
        if cell not in unknown:
            continue
        lower, lower_status = _optimize(model, index, highspy.ObjSense.kMinimize)
        upper, upper_status = _optimize(model, index, highspy.ObjSense.kMaximize)
        status = "optimal" if lower_status == upper_status == "optimal" else (
            "unbounded" if "unbounded" in (lower_status, upper_status) else lower_status
        )
        solved[cell] = (lower, upper, status)
    return solved
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_bounds.py -v`
Expected: PASS, all five tests. The first is the important one: `(400.0, 530.0)` and
`(250.0, 380.0)` are the published-data bounds, and a mismatch means the margin or the support is
wrong, not that the solver is.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/bounds.py tests/unit/test_constraint_bounds.py
git commit -m "feat(constraints): solve sharp LP bounds per component on HiGHS

Single-cell rows fold into column bounds only when their coefficient is exactly
1.0, so a scaled restriction still reaches the matrix. Every component gets a
feasibility probe, including components with no unknown cell -- otherwise a
contradiction among published values would pass unexamined.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: MILP tightening, exactness, `bound_status`, and `solve_bounds`

**Files:**
- Modify: `src/logging_employment/constraints/bounds.py`
- Test: `tests/unit/test_bound_status.py`

**Interfaces:**
- Consumes: everything from Task 10; `rank_table` (Task 9); `DETERMINISTIC_BOUNDS_SCHEMA`,
  `BOUND_STATUSES` (Task 2).
- Produces: `classify_bound_status(*, observation_status: str, lower: float | None,
  upper: float | None, is_integer: bool, tolerance: float) -> tuple[str, bool, bool]` returning
  `(bound_status, exactly_identified, integer_exactly_identified)`; the frozen dataclass
  `BoundResult(bounds, components, diagnostics)`; and
  `solve_bounds(system: ConstraintSystem, config: BoundConfig, *,
  quarantined: Collection[str] = ()) -> BoundResult` with `bounds` matching
  `DETERMINISTIC_BOUNDS_SCHEMA`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_bound_status.py`:

```python
"""One classification function, one test per label it can return."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, system
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA, HarmonizedData

REPO = Path(__file__).resolve().parents[2]
TOLERANCE = 1.0e-7


def test_a_published_cell_is_observed() -> None:
    status, exact, integer_exact = bounds.classify_bound_status(
        observation_status="observed", lower=700.0, upper=700.0, is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "observed"
    # True because the interval *is* a point. Whether that point may be re-published is a
    # disclosure question, and `disclosure.flags` answers it -- this field does not.
    assert exact is True and integer_exact is True


def test_an_integer_cell_pinned_between_two_consecutive_bounds_is_exactly_recoverable() -> None:
    status, exact, integer_exact = bounds.classify_bound_status(
        observation_status="suppressed", lower=41.2, upper=41.9, is_integer=True,
        tolerance=TOLERANCE,
    )
    # ceil(41.2) == floor(41.9) == 42 -- §9.6's integer exactness rule.
    assert status == "exactly_recoverable"
    assert integer_exact is True


def test_the_same_width_on_a_continuous_cell_is_only_partially_identified() -> None:
    status, exact, _ = bounds.classify_bound_status(
        observation_status="suppressed", lower=41.2, upper=41.9, is_integer=False,
        tolerance=TOLERANCE,
    )
    assert status == "partially_identified"
    assert exact is False


def test_a_finite_interval_wider_than_tolerance_is_partially_identified() -> None:
    status, _, _ = bounds.classify_bound_status(
        observation_status="suppressed", lower=400.0, upper=530.0, is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "partially_identified"


def test_a_cell_with_no_upper_bound_is_unbounded() -> None:
    status, exact, _ = bounds.classify_bound_status(
        observation_status="suppressed", lower=0.0, upper=None, is_integer=True,
        tolerance=TOLERANCE,
    )
    assert status == "unbounded"
    assert exact is False


def test_stage_two_never_emits_a_model_dependent_status() -> None:
    # `model_estimable` and `model_only` say something about a model, and §9.1 forbids one here.
    # Stage 8's §15.3 mapping is where a released cell acquires a model-dependence level.
    returned = {
        bounds.classify_bound_status(
            observation_status=obs, lower=lo, upper=hi, is_integer=True, tolerance=TOLERANCE
        )[0]
        for obs in ("observed", "suppressed", "true_zero")
        for lo, hi in ((0.0, None), (1.0, 1.0), (1.0, 9.0))
    }
    assert returned & {"model_estimable", "model_only"} == set()


def test_a_narrow_component_triggers_the_integer_resolve(make_monthly, make_size) -> None:
    # The MILP *switch*, not the tightening: two classes of one establishment each, in [0, 4] and
    # [5, 9], summing to 11. The LP gives [2, 4] and [7, 9] -- widths of 2, below the configured
    # threshold of 25 -- so an integer re-solve runs and its values are the ones selected. That
    # integrality can actually move a bound is §17.2's property, tested on a toy in Task 15.
    monthly = make_monthly(
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 11, "employment_raw": "11",
         "qtrly_establishments": 2}
    )
    size = make_size(
        {"size_class": "1", "establishments": 1, "employment": None, "size_lower": 0,
         "size_upper": 4, "disclosure_code": "N", "observation_status": "suppressed"},
        {"size_class": "2", "establishments": 1, "employment": None, "size_lower": 5,
         "size_upper": 9, "disclosure_code": "N", "observation_status": "suppressed"},
    )
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    result = bounds.solve_bounds(system.build_constraint_system(data, cfg), cfg.constraints)
    unknown = result.bounds.filter(pl.col("bound_status") != "observed")
    assert unknown.height == 2
    assert unknown["milp_lower"].null_count() == 0  # width 2 < the configured MILP threshold of 25
    assert unknown["selected_lower"].to_list() == unknown["milp_lower"].to_list()


def test_solve_bounds_returns_one_row_per_cell_in_the_shipped_schema(
    make_monthly, make_size
) -> None:
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "suppressed", "employment_value": None,
         "disclosure_code": "N"},
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 200, "qtrly_establishments": 60},
    )
    size = make_size({"size_class": "1", "establishments": 60, "employment": 200,
                      "size_lower": 0, "size_upper": 4})
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    built = system.build_constraint_system(data, cfg)
    result = bounds.solve_bounds(built, cfg.constraints)
    assert result.bounds.schema == pl.Schema(DETERMINISTIC_BOUNDS_SCHEMA)
    assert result.bounds.height == built.cells.height
    assert set(result.bounds["constraint_set_hash"]) == {built.constraint_set_hash}
    assert result.components["component_id"].n_unique() == result.components.height
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_bound_status.py -v`
Expected: FAIL with `AttributeError: module 'logging_employment.constraints.bounds' has no
attribute 'classify_bound_status'`.

- [ ] **Step 3: Write the implementation**

Append to `src/logging_employment/constraints/bounds.py` (adding `import math`,
`from collections.abc import Collection`, `from ..contracts import DETERMINISTIC_BOUNDS_SCHEMA`,
`from .graph import assign_components, component_membership`, `from .rank import rank_table`).
Note that `diagnostics` is imported *inside* `solve_bounds`, not at module scope:
`constraints.diagnostics` imports `column_specs` and `matrix_rows` from this module, so a
top-level import here would be a cycle.

```python
def classify_bound_status(
    *,
    observation_status: str,
    lower: float | None,
    upper: float | None,
    is_integer: bool,
    tolerance: float,
) -> tuple[str, bool, bool]:
    """§7.10's `bound_status`, plus the two exactness flags, from solver output alone.

    One function with one rule table, because a status typed at five call sites is a status that
    will disagree with itself. Two of §7.10's seven values are never returned here:
    `model_estimable` and `model_only` are claims about what a model can do, and §9.1 forbids a
    model at this stage. Stage 8's §15.3 mapping assigns a model-dependence level to a released
    cell; that is a different question asked later.

    `exactly_identified` means the sharp interval is a point. On a published cell that is trivially
    true, and it is left true rather than special-cased: whether a point may be *re-published* is a
    disclosure question, and `disclosure.flags` is what answers it.
    """
    if observation_status != "suppressed":
        return "observed", True, True
    if lower is None or upper is None:
        return "unbounded", False, False
    if is_integer:
        exact = math.ceil(lower - tolerance) == math.floor(upper + tolerance)
        return ("exactly_recoverable" if exact else "partially_identified"), exact, exact
    exact = (upper - lower) <= tolerance
    return ("exactly_recoverable" if exact else "partially_identified"), exact, False


@dataclass(frozen=True)
class BoundResult:
    """§16.2's `solve_bounds` return: the §7.10 table, the rank records, and any diagnostic."""

    bounds: pl.DataFrame
    components: pl.DataFrame
    diagnostics: tuple[object, ...]


def _needs_milp(
    solved: dict[str, tuple[float | None, float | None, str]],
    specs: dict[str, ColumnSpec],
    config: BoundConfig,
) -> bool:
    """Whether an integer re-solve of this component can change anything, at a price worth paying.

    Component-level rather than cell-level (§9.6 step 3): one integer model serves every unknown
    cell in the component, and building it once is cheaper than deciding cell by cell.
    """
    if not config.enforce_integrality:
        return False
    for cell, (lower, upper, _) in solved.items():
        if lower is None or upper is None or not specs[cell].is_integer:
            continue
        if (upper - lower) < config.use_milp_when_lp_interval_width_below:
            return True
    return False


def solve_bounds(
    system: "BuiltSystem", config: BoundConfig, *, quarantined: Collection[str] = ()
) -> BoundResult:
    """Sharp bounds for every cell in the system (§16.2, §9.6).

    A component that is infeasible halts the run with the §9.7 diagnostic attached, unless it was
    explicitly named in `quarantined`. Nothing in the D1 window is quarantined; the parameter
    exists because §9.7 makes quarantine the only alternative to a hard failure, and an
    undocumented way to continue past an infeasibility is worse than a named one.
    """
    built = system if system.rows["component_id"].null_count() == 0 else assign_components(system)
    membership = component_membership(built)
    components = rank_table(built, rank_tolerance=config.rank_tolerance)
    rank_by_component = {
        row["component_id"]: (row["numerical_rank"], row["nullity"])
        for row in components.iter_rows(named=True)
    }
    cell_component = dict(zip(membership["cell_id"], membership["component_id"], strict=True))
    observation = dict(
        zip(built.cells["cell_id"], built.cells["observation_status"], strict=True)
    )
    observed_value = dict(zip(built.cells["cell_id"], built.cells["observed_value"], strict=True))

    records: list[dict[str, object]] = []
    reports: list[object] = []
    for component_id in sorted(set(membership["component_id"].to_list())):
        specs = column_specs(built, component_id, membership)
        try:
            lp = solve_component(built, component_id, membership, config, integer=False)
        except InfeasibleComponentError as failure:
            from . import diagnostics as diagnostics_module  # local: breaks an import cycle

            report = diagnostics_module.diagnose(built, component_id, membership, config)
            reports.append(report)
            if component_id not in quarantined:
                raise InfeasibleComponentError(
                    f"{failure}\n{diagnostics_module.render(report)}"
                ) from failure
            lp = {cell: (None, None, "infeasible") for cell in specs if
                  observation.get(cell) == "suppressed"}

        milp: dict[str, tuple[float | None, float | None, str]] = {}
        if lp and _needs_milp(lp, specs, config) and component_id not in quarantined:
            milp = solve_component(built, component_id, membership, config, integer=True)

        numerical_rank, nullity = rank_by_component[component_id]
        for cell in specs:
            status_word = observation[cell]
            if status_word == "suppressed" and component_id in quarantined:
                bound_status, exact, integer_exact = "infeasible", False, False
                lp_lower = lp_upper = milp_lower = milp_upper = None
                selected_lower = selected_upper = None
                solver_status = "infeasible"
            elif status_word == "suppressed":
                lp_lower, lp_upper, solver_status = lp[cell]
                milp_lower, milp_upper = milp.get(cell, (None, None, ""))[:2] if milp else (
                    None, None
                )
                selected_lower = milp_lower if milp_lower is not None else lp_lower
                selected_upper = milp_upper if milp_upper is not None else lp_upper
                bound_status, exact, integer_exact = classify_bound_status(
                    observation_status=status_word,
                    lower=selected_lower,
                    upper=selected_upper,
                    is_integer=specs[cell].is_integer,
                    tolerance=config.feasibility_tolerance,
                )
            else:
                value = None if observed_value[cell] is None else float(observed_value[cell])
                lp_lower = lp_upper = milp_lower = milp_upper = None
                selected_lower = selected_upper = value
                solver_status = "not_solved"
                bound_status, exact, integer_exact = classify_bound_status(
                    observation_status=status_word,
                    lower=value,
                    upper=value,
                    is_integer=specs[cell].is_integer,
                    tolerance=config.feasibility_tolerance,
                )
            records.append(
                {
                    "cell_id": cell,
                    "component_id": cell_component[cell],
                    "rank": numerical_rank,
                    "nullity": nullity,
                    "lp_lower": lp_lower,
                    "lp_upper": lp_upper,
                    "milp_lower": milp_lower,
                    "milp_upper": milp_upper,
                    "selected_lower": selected_lower,
                    "selected_upper": selected_upper,
                    "bound_status": bound_status,
                    "exactly_identified": exact,
                    "integer_exactly_identified": integer_exact,
                    "solver_status": solver_status,
                    "solver_tolerance": config.feasibility_tolerance,
                    "constraint_set_hash": built.constraint_set_hash,
                }
            )
    return BoundResult(
        bounds=pl.DataFrame(records, schema=DETERMINISTIC_BOUNDS_SCHEMA).sort("cell_id"),
        components=components,
        diagnostics=tuple(reports),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_bound_status.py -v`
Expected: PASS, all eight tests. Task 12 supplies `diagnostics.diagnose` and
`diagnostics.render`; write a two-line stub for them first if you are running this task in
isolation, and delete the stub when Task 12 lands.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/bounds.py tests/unit/test_bound_status.py
git commit -m "feat(constraints): tighten with MILP, classify bound_status, and ship solve_bounds

One classification function with one rule table. Stage 2 never returns
model_estimable or model_only: both are claims about a model, and §9.1 forbids
one here.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: Infeasibility diagnostics (§9.7)

**Files:**
- Create: `src/logging_employment/constraints/diagnostics.py`
- Test: `tests/unit/test_constraint_diagnostics.py`

**Interfaces:**
- Consumes: `BuiltSystem`, `column_specs`, `matrix_rows`, `BoundConfig` (Tasks 7, 10).
- Produces: the frozen dataclass `InfeasibilityDiagnostic(component_id, cell_ids,
  source_snapshot_ids, iis_constraint_ids, iis_cell_ids, minimum_slack,
  largest_slack_constraints, candidate_conflicts)`;
  `diagnose(built, component_id, membership, config) -> InfeasibilityDiagnostic`; and
  `render(report: InfeasibilityDiagnostic) -> str`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_constraint_diagnostics.py`:

```python
"""§9.7: what an infeasible component must say before the run stops."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, diagnostics, graph, system
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]


def _infeasible(make_monthly, make_size):
    """2024's real margin, with the residual moved from 780 to 600.

    x6 + x7 = 600 with x6 >= 400 and x7 >= 250 has no solution: the supports need 650. This is the
    shape §9.6 step 5 and §9.7 are written for -- a rounding, revision or vintage conflict between
    a published total and published components -- and it is a two-line perturbation of real data
    rather than an invented toy.
    """
    monthly = make_monthly(
        {"area_fips": "US000", "area_type": "national", "state_fips": None,
         "aggregation_level": "18", "employment_value": 41488, "employment_raw": "41488",
         "qtrly_establishments": 7713}
    )
    size = make_size(
        {"size_class": "1", "establishments": 5007, "employment": 7630, "size_lower": 0,
         "size_upper": 4},
        {"size_class": "2", "establishments": 1501, "employment": 9955, "size_lower": 5,
         "size_upper": 9},
        {"size_class": "3", "establishments": 803, "employment": 10480, "size_lower": 10,
         "size_upper": 19},
        {"size_class": "4", "establishments": 357, "employment": 10316, "size_lower": 20,
         "size_upper": 49},
        {"size_class": "5", "establishments": 40, "employment": 2507, "size_lower": 50,
         "size_upper": 99},
        {"size_class": "6", "establishments": 4, "employment": None, "size_lower": 100,
         "size_upper": 249, "disclosure_code": "N", "observation_status": "suppressed"},
        {"size_class": "7", "establishments": 1, "employment": None, "size_lower": 250,
         "size_upper": 499, "disclosure_code": "N", "observation_status": "suppressed"},
    )
    data = HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size,
        cbp_state_size=pl.DataFrame(), bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(system.build_constraint_system(data, cfg))
    membership = graph.component_membership(built)
    component = membership.filter(
        pl.col("cell_id").str.starts_with("national_size|")
    )["component_id"][0]
    return built, membership, component, cfg


def test_the_diagnostic_reports_the_minimum_slack_and_the_row_carrying_it(
    make_monthly, make_size
) -> None:
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert report.minimum_slack == pytest.approx(50.0)
    assert report.largest_slack_constraints[0][0].startswith("size_margin|")


def test_the_diagnostic_names_every_snapshot_involved(make_monthly, make_size) -> None:
    # §9.7: "all source snapshots involved".
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert "2024_q1_by_size" in report.source_snapshot_ids
    assert "2024q1" in report.source_snapshot_ids


def test_an_irreducible_subsystem_is_reported_when_the_solver_supplies_one(
    make_monthly, make_size
) -> None:
    built, membership, component, cfg = _infeasible(make_monthly, make_size)
    report = diagnostics.diagnose(built, component, membership, cfg.constraints)
    assert report.iis_constraint_ids or report.minimum_slack > 0


def test_the_run_halts_with_the_diagnostic_rather_than_relaxing(make_monthly, make_size) -> None:
    built, _, component, cfg = _infeasible(make_monthly, make_size)
    with pytest.raises(InfeasibleComponentError) as failure:
        bounds.solve_bounds(built, cfg.constraints)
    assert "minimum slack" in str(failure.value)
    assert component in str(failure.value)


def test_an_explicitly_quarantined_component_records_infeasible_instead_of_halting(
    make_monthly, make_size
) -> None:
    built, _, component, cfg = _infeasible(make_monthly, make_size)
    result = bounds.solve_bounds(built, cfg.constraints, quarantined=[component])
    assert set(
        result.bounds.filter(pl.col("component_id") == component)
        .filter(pl.col("bound_status") != "observed")["bound_status"]
    ) == {"infeasible"}
    assert len(result.diagnostics) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_constraint_diagnostics.py -v`
Expected: FAIL with `ImportError: cannot import name 'diagnostics'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/constraints/diagnostics.py`:

```python
"""§9.7: everything an infeasible component must report before the run stops.

Two independent accounts of the same failure, because §9.7 asks for an irreducible infeasible
subsystem "when supported; otherwise a minimum-slack diagnostic solution", and neither alone is
enough to act on. The IIS names a set of restrictions that cannot hold together; the minimum-slack
solution says by how much, which is what distinguishes a rounding disagreement of a few employees
from a universe mismatch of thousands.

Slack is added to coupling rows only. Column bounds -- nonnegativity and the class supports -- are
definitional, and a diagnostic that "fixed" the infeasibility by letting employment go negative
would be describing a different problem than the one the run hit.
"""

from __future__ import annotations

from dataclasses import dataclass

import highspy
import numpy as np
import polars as pl

from .bounds import INFINITY, BoundConfig, column_specs, matrix_rows
from .system import BuiltSystem

MAX_REPORTED_SLACK_ROWS = 5


@dataclass(frozen=True)
class InfeasibilityDiagnostic:
    """§9.7's required content for one infeasible component."""

    component_id: str
    cell_ids: tuple[str, ...]
    source_snapshot_ids: tuple[str, ...]
    iis_constraint_ids: tuple[str, ...]
    iis_cell_ids: tuple[str, ...]
    minimum_slack: float
    largest_slack_constraints: tuple[tuple[str, float], ...]
    candidate_conflicts: tuple[str, ...]


def _candidate_conflicts(rows: pl.DataFrame) -> tuple[str, ...]:
    """The mixed-vintage and mixed-universe readings §9.7 asks a diagnostic to offer."""
    found: list[str] = []
    for column, label in (
        ("vintage_compatibility_status", "vintage compatibility"),
        ("ownership_scope", "ownership universe"),
        ("geography_scope", "geography universe"),
        ("industry_scope", "industry scope"),
    ):
        values = sorted(set(rows[column].to_list()))
        if len(values) > 1:
            found.append(f"{label}: {values}")
    return tuple(found)


def diagnose(
    built: BuiltSystem, component_id: str, membership: pl.DataFrame, config: BoundConfig
) -> InfeasibilityDiagnostic:
    """Build both accounts of one component's infeasibility."""
    specs = column_specs(built, component_id, membership)
    coupling = matrix_rows(built, component_id)
    rows = built.rows.filter(pl.col("component_id") == component_id)
    order = list(specs)
    at = {cell: i for i, cell in enumerate(order)}

    # --- account one: an irreducible infeasible subsystem, if HiGHS offers one ------------------
    plain = highspy.Highs()
    plain.setOptionValue("output_flag", False)
    plain.addVars(
        len(order),
        np.array([specs[c].lower for c in order]),
        np.array([specs[c].upper for c in order]),
    )
    for row in coupling:
        indices = np.array([at[c] for c in row["cells"]], dtype=np.int32)
        plain.addRow(row["lower"], row["upper"], indices.size, indices, np.array(row["values"]))
    plain.run()
    iis_constraints: tuple[str, ...] = ()
    iis_cells: tuple[str, ...] = ()
    status, iis = plain.getIis()
    if status == highspy.HighsStatus.kOk and iis.valid_:
        iis_constraints = tuple(
            str(coupling[i]["constraint_id"]) for i in list(iis.row_index_) if i < len(coupling)
        )
        iis_cells = tuple(order[i] for i in list(iis.col_index_) if i < len(order))

    # --- account two: the minimum total slack, and where it lands -------------------------------
    slack = highspy.Highs()
    slack.setOptionValue("output_flag", False)
    slack.addVars(
        len(order),
        np.array([specs[c].lower for c in order]),
        np.array([specs[c].upper for c in order]),
    )
    costs = [0.0] * len(order)
    for offset, row in enumerate(coupling):
        slack.addVars(2, np.array([0.0, 0.0]), np.array([INFINITY, INFINITY]))
        positive = len(order) + 2 * offset
        indices = np.array(
            [at[c] for c in row["cells"]] + [positive, positive + 1], dtype=np.int32
        )
        values = np.array([*row["values"], 1.0, -1.0])
        slack.addRow(row["lower"], row["upper"], indices.size, indices, values)
        costs.extend([1.0, 1.0])
    slack.changeColsCost(
        len(costs), np.array(range(len(costs)), dtype=np.int32), np.array(costs)
    )
    slack.changeObjectiveSense(highspy.ObjSense.kMinimize)
    slack.run()
    total = float(slack.getInfo().objective_function_value)
    values = list(slack.getSolution().col_value)
    per_row = [
        (str(row["constraint_id"]), values[len(order) + 2 * i] + values[len(order) + 2 * i + 1])
        for i, row in enumerate(coupling)
    ]
    per_row.sort(key=lambda pair: pair[1], reverse=True)

    return InfeasibilityDiagnostic(
        component_id=component_id,
        cell_ids=tuple(order),
        source_snapshot_ids=tuple(
            sorted({s for joined in rows["source_snapshot_ids"] for s in joined.split(",")})
        ),
        iis_constraint_ids=iis_constraints,
        iis_cell_ids=iis_cells,
        minimum_slack=total,
        largest_slack_constraints=tuple(per_row[:MAX_REPORTED_SLACK_ROWS]),
        candidate_conflicts=_candidate_conflicts(rows),
    )


def render(report: InfeasibilityDiagnostic) -> str:
    """The diagnostic as the run's final message. §9.7's list, in order."""
    lines = [
        f"component: {report.component_id}",
        f"cells: {len(report.cell_ids)}",
        f"source snapshots: {', '.join(report.source_snapshot_ids)}",
        f"candidate conflicts: {'; '.join(report.candidate_conflicts) or 'none detected'}",
        f"irreducible infeasible subsystem: {', '.join(report.iis_constraint_ids) or 'unavailable'}",
        f"minimum slack: {report.minimum_slack:.6g}",
        "largest required slack: "
        + ", ".join(f"{name}={value:.6g}" for name, value in report.largest_slack_constraints),
    ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_constraint_diagnostics.py tests/unit/test_bound_status.py -v`
Expected: PASS. Both modules, because Task 11's stub is now replaced by the real module.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/diagnostics.py tests/unit/test_constraint_diagnostics.py
git commit -m "feat(constraints): report an IIS and a minimum-slack solution on infeasibility

Slack is added to coupling rows only: relaxing a class support or nonnegativity
would describe a different problem than the one the run hit. The fixture is
2024's real margin with its residual moved by 180, not an invented toy.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: The two Stage 2 disclosure flags (§9.8)

**Files:**
- Create: `src/logging_employment/disclosure/__init__.py`
- Create: `src/logging_employment/disclosure/flags.py`
- Test: `tests/unit/test_disclosure_flags.py`

**Interfaces:**
- Consumes: the `deterministic_bounds` frame (Task 11); the `target_cell` frame (Task 3);
  `DisclosureConfig` (Task 1).
- Produces: `FLAG_SCHEMA: dict[str, pl.DataType]` with columns `cell_id`, `bound_status`,
  `feasible_width`, `relative_width`, `exact_reconstruction_flag`,
  `narrow_feasible_interval_flag`; and `build_flags(bounds: pl.DataFrame, cells: pl.DataFrame,
  config: DisclosureConfig) -> pl.DataFrame`.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_disclosure_flags.py`:

```python
"""§9.8: which cells go to disclosure review, and which must never be sent there."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA, TARGET_CELL_SCHEMA
from logging_employment.disclosure import flags

REPO = Path(__file__).resolve().parents[2]


def _frames(*rows: tuple[str, str, float | None, float | None]):
    cells = pl.DataFrame(
        [
            {
                "cell_id": cell_id, "state_fips": "US", "reference_month": "2024-03",
                "size_concept": "march_reference", "size_class": "6", "ownership_code": "5",
                "industry_code": "113310", "naics_vintage": "NAICS 2022",
                "observation_status": status, "observed_value": None,
                "source_snapshot_id": "s", "qcew_disclosure_code": "N",
            }
            for cell_id, status, _, _ in rows
        ],
        schema=TARGET_CELL_SCHEMA,
    )
    bounds = pl.DataFrame(
        [
            {
                "cell_id": cell_id, "component_id": "c000000", "rank": 1, "nullity": 1,
                "lp_lower": lower, "lp_upper": upper, "milp_lower": None, "milp_upper": None,
                "selected_lower": lower, "selected_upper": upper,
                "bound_status": "observed" if status != "suppressed" else (
                    "unbounded" if upper is None else "partially_identified"
                ),
                "exactly_identified": False, "integer_exactly_identified": False,
                "solver_status": "optimal", "solver_tolerance": 1e-7,
                "constraint_set_hash": "h",
            }
            for cell_id, status, lower, upper in rows
        ],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    return bounds, cells


def _cfg():
    return load_config(REPO / "config.yaml").disclosure


def test_a_published_cell_is_never_flagged_even_though_its_interval_is_a_point() -> None:
    # The trap this test exists for: an observed cell has width 0, which passes every narrowness
    # test ever written. Flagging it would send 3,462 already-public state-months to review.
    bounds, cells = _frames(("observed-cell", "observed", 700.0, 700.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["exact_reconstruction_flag"].to_list() == [False]
    assert built["narrow_feasible_interval_flag"].to_list() == [False]


def test_an_exactly_recoverable_suppressed_cell_raises_both_flags() -> None:
    bounds, cells = _frames(("exact-cell", "suppressed", 42.0, 42.0))
    built = flags.build_flags(
        bounds.with_columns(
            pl.lit("exactly_recoverable").alias("bound_status"),
            pl.lit(True).alias("exactly_identified"),
        ),
        cells,
        _cfg(),
    )
    assert built["exact_reconstruction_flag"].to_list() == [True]
    assert built["narrow_feasible_interval_flag"].to_list() == [True]


def test_the_one_real_D1_cell_that_clears_the_relative_threshold_is_flagged() -> None:
    # 2023 class 6: [700, 884]. Width 184, midpoint 792, relative width 0.2323 <= 0.25.
    bounds, cells = _frames(("narrow-cell", "suppressed", 700.0, 884.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["relative_width"][0] == pytest.approx(184 / 792)
    assert built["narrow_feasible_interval_flag"].to_list() == [True]
    assert built["exact_reconstruction_flag"].to_list() == [False]


def test_the_next_widest_real_cell_is_not_flagged() -> None:
    # 2024 class 6: [400, 530]. Width 130, midpoint 465, relative width 0.2796 > 0.25.
    bounds, cells = _frames(("wider-cell", "suppressed", 400.0, 530.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["narrow_feasible_interval_flag"].to_list() == [False]


def test_the_absolute_test_alone_is_sufficient() -> None:
    # §14.2 asks for "narrow in absolute or relative terms". Width 10 on a midpoint of 10,000 is
    # relatively enormous and absolutely disclosive.
    bounds, cells = _frames(("absolute-cell", "suppressed", 9995.0, 10005.0))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["narrow_feasible_interval_flag"].to_list() == [True]


def test_an_unbounded_cell_carries_no_width_and_no_flag() -> None:
    bounds, cells = _frames(("open-cell", "suppressed", 0.0, None))
    built = flags.build_flags(bounds, cells, _cfg())
    assert built["feasible_width"][0] is None
    assert built["narrow_feasible_interval_flag"].to_list() == [False]
```

Add `import pytest` at the top of that module.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/unit/test_disclosure_flags.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logging_employment.disclosure'`.

- [ ] **Step 3: Write the implementation**

Create `src/logging_employment/disclosure/__init__.py`:

```python
"""Disclosure-risk governance (§14). Stage 2 contributes the two identification flags."""
```

Create `src/logging_employment/disclosure/flags.py`:

```python
"""§9.8: "Exactly recoverable and unusually narrow cells MUST be sent to disclosure review."

Both flags are computed for suppressed cells only, and that guard is the whole reason this module
exists rather than the two predicates living inline. A published cell's feasible interval is a
point -- it was pinned to its own value by INV-001 -- so every width test ever written passes on it.
Flagging those would route thousands of already-public state-months to review and bury the handful
of cells that carry real reconstruction risk.

"Unusually narrow" is a governance decision, not a measurement: §21 leaves disclosure thresholds to
the owner. The two widths come from configuration, and §14.2's "narrow in absolute or relative
terms" is read as a disjunction -- either test alone routes the cell to review.

Stage 8 widens this into §7.12's `disclosure_decision`, whose other three flags need a posterior,
an employer linkage judgement, and an analytic-sufficiency judgement that Stage 2 cannot make.
"""

from __future__ import annotations

import polars as pl

from ..config import DisclosureConfig

FLAG_SCHEMA: dict[str, pl.DataType] = {
    "cell_id": pl.String,
    "bound_status": pl.String,
    "feasible_width": pl.Float64,
    "relative_width": pl.Float64,
    "exact_reconstruction_flag": pl.Boolean,
    "narrow_feasible_interval_flag": pl.Boolean,
}


def build_flags(
    bounds: pl.DataFrame, cells: pl.DataFrame, config: DisclosureConfig
) -> pl.DataFrame:
    """One row per cell, with both Stage 2 flags and the widths that decided them."""
    suppressed = pl.col("observation_status") == "suppressed"
    width = pl.col("selected_upper") - pl.col("selected_lower")
    midpoint = (pl.col("selected_upper") + pl.col("selected_lower")) / 2
    return (
        bounds.join(cells.select(["cell_id", "observation_status"]), on="cell_id", how="left")
        .with_columns(
            width.alias("feasible_width"),
            pl.when(midpoint > 0).then(width / midpoint).otherwise(None).alias("relative_width"),
        )
        .with_columns(
            (suppressed & (pl.col("bound_status") == "exactly_recoverable")).alias(
                "exact_reconstruction_flag"
            ),
            (
                suppressed
                & pl.col("feasible_width").is_not_null()
                & (
                    (pl.col("feasible_width") <= config.narrow_interval_absolute_width)
                    | (
                        pl.col("relative_width").is_not_null()
                        & (pl.col("relative_width") <= config.narrow_interval_relative_width)
                    )
                )
            ).alias("narrow_feasible_interval_flag"),
        )
        .select(list(FLAG_SCHEMA))
        .cast(FLAG_SCHEMA)  # type: ignore[arg-type]
        .sort("cell_id")
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/unit/test_disclosure_flags.py -v`
Expected: PASS, all six tests.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/disclosure tests/unit/test_disclosure_flags.py
git commit -m "feat(disclosure): flag exactly recoverable and unusually narrow suppressed cells

Both flags are guarded on observation_status. A published cell's interval is a
point, so every width test passes on it; flagging those would route thousands of
already-public cells to review and bury the ones that matter.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: The `build-constraints` and `solve-bounds` commands

**Files:**
- Modify: `src/logging_employment/cli.py`
- Modify: `src/logging_employment/constraints/system.py` (add `load_system`)
- Test: `tests/integration/test_constraint_cli.py`

**Interfaces:**
- Consumes: everything from Tasks 3–13; `build.write_parquet_deterministic` (Stage 1);
  `runs.run_id`, `runs.run_dir` (Task 7).
- Produces: `system.load_system(constraints_dir: Path, *, constraint_set_hash: str | None = None)
  -> BuiltSystem`; CLI commands `build-constraints --config` and `solve-bounds --config`; the
  artifacts `data/constraints/{target_cell,constraint_row,constraint_coefficient}.parquet`,
  `runs/<run_id>/config.resolved.yaml`, `runs/<run_id>/schema_manifest.json`,
  `runs/<run_id>/constraint_manifest.parquet`, `runs/<run_id>/deterministic_bounds.parquet`,
  `runs/<run_id>/component_rank.parquet`, `runs/<run_id>/disclosure_flags.parquet`.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_constraint_cli.py`:

```python
"""§16.1: both commands write a machine-readable manifest and are idempotent for equal inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl
import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import app
from logging_employment.config import load_config

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "constraints"


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """A config whose storage roots point inside tmp_path, with the golden staged tables."""
    staged = tmp_path / "staged"
    staged.mkdir()
    for name in ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge"):
        pl.read_parquet(FIXTURES / f"{name}.parquet").write_parquet(staged / f"{name}.parquet")
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["staged_uri"] = str(staged)
    raw["storage"]["raw_uri"] = str(tmp_path / "raw")
    raw["storage"]["output_uri"] = str(tmp_path / "runs")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw))
    return path


def _run(config: Path, *args: str) -> None:
    result = CliRunner().invoke(app, [*args, "--config", str(config)])
    assert result.exit_code == 0, result.output


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_constraints_writes_all_three_tables_and_a_manifest(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    cfg = load_config(workspace)
    constraints = Path(cfg.storage.staged_uri).parent / "constraints"
    for name in ("target_cell", "constraint_row", "constraint_coefficient"):
        assert (constraints / f"{name}.parquet").exists()
    run_root = Path(cfg.storage.output_uri)
    run = next(run_root.iterdir())
    assert (run / "constraint_manifest.parquet").exists()
    assert (run / "config.resolved.yaml").exists()
    manifest = json.loads((run / "schema_manifest.json").read_text())
    assert manifest["constraint_set_hash"]
    assert manifest["compatibility_report"]["establishment_gap_by_year"]


def test_both_commands_are_idempotent_for_identical_inputs(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    first = {p.name: _digest(p) for p in sorted(run.glob("*.parquet"))}
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    runs_now = list(Path(cfg.storage.output_uri).iterdir())
    assert len(runs_now) == 1, "a second run created a second directory, so it was not idempotent"
    assert {p.name: _digest(p) for p in sorted(run.glob("*.parquet"))} == first


def test_solve_bounds_writes_bounds_ranks_and_flags(workspace: Path) -> None:
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    bounds = pl.read_parquet(run / "deterministic_bounds.parquet")
    assert bounds.filter(pl.col("bound_status") == "partially_identified").height == 2
    assert (run / "component_rank.parquet").exists()
    assert (run / "disclosure_flags.parquet").exists()


def test_solve_bounds_without_a_prior_build_names_what_is_missing(workspace: Path) -> None:
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    assert "build-constraints" in str(result.output) + str(result.exception)


def test_solve_bounds_refuses_inputs_that_did_not_produce_the_constraint_tables(
    workspace: Path,
) -> None:
    # The run id is derived from the harmonized inputs; the constraint tables come from
    # data/constraints/. Without a check, moving a staged value and re-running `solve-bounds`
    # alone would write bounds into a directory keyed to inputs that never produced them. The
    # idempotence test above runs both commands in order, so it cannot see this.
    _run(workspace, "build-constraints")
    cfg = load_config(workspace)
    staged = Path(cfg.storage.staged_uri) / "qcew_monthly.parquet"
    pl.read_parquet(staged).with_columns(
        pl.when(pl.col("state_fips") == "01")
        .then(2501)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    ).write_parquet(staged)
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    message = str(result.output) + str(result.exception)
    assert "build-constraints" in message or "constraint_set_hash" in message
    assert not list(Path(cfg.storage.output_uri).rglob("deterministic_bounds.parquet"))
```

- [ ] **Step 2: Build the golden staged fixture**

The fixture is 2024's real published margin plus two state cells, small enough to commit and
public in every value. Write and run this script once, then commit the four Parquet files:

```bash
mkdir -p tests/fixtures/constraints
uv run python - <<'PY'
from pathlib import Path

import polars as pl

from logging_employment.contracts import (
    BRIDGE_SCHEMA, CBP_STATE_SIZE_SCHEMA, QCEW_MONTHLY_SCHEMA, QCEW_NATIONAL_SIZE_SCHEMA,
)

OUT = Path("tests/fixtures/constraints")
OUT.mkdir(parents=True, exist_ok=True)

monthly_defaults = {
    "snapshot_id": "2024q1", "release_vintage": "2024q1", "release_status": "final",
    "reference_quarter": "2024Q1", "reference_month": "2024-03", "industry_code": "113310",
    "naics_vintage": "NAICS 2022", "ownership_code": "5", "size_code": "0",
    "wages_raw": "0", "wages_value": 0, "is_published_numeric_zero": False,
    "is_true_zero": False, "suppression_type": "unknown",
}
monthly = pl.DataFrame(
    [
        monthly_defaults | {
            "area_fips": "US000", "area_type": "national", "state_fips": None,
            "aggregation_level": "18", "qtrly_establishments": 7713,
            "employment_raw": "41668", "employment_value": 41668, "disclosure_code": "",
            "observation_status": "observed", "source_row_hash": "us000",
        },
        monthly_defaults | {
            "area_fips": "01000", "area_type": "state", "state_fips": "01",
            "aggregation_level": "58", "qtrly_establishments": 300,
            "employment_raw": "2500", "employment_value": 2500, "disclosure_code": "",
            "observation_status": "observed", "source_row_hash": "01000",
        },
        monthly_defaults | {
            "area_fips": "02000", "area_type": "state", "state_fips": "02",
            "aggregation_level": "58", "qtrly_establishments": 120,
            "employment_raw": "0", "employment_value": None, "disclosure_code": "N",
            "observation_status": "suppressed", "source_row_hash": "02000",
        },
    ],
    schema=QCEW_MONTHLY_SCHEMA,
)

size_defaults = {
    "snapshot_id": "2024_q1_by_size", "reference_year": 2024, "reference_quarter": "2024Q1",
    "reference_month": "2024-03", "industry_code": "113310", "naics_vintage": "NAICS 2022",
}
published = [
    ("1", 5007, 7630, 0, 4), ("2", 1501, 9955, 5, 9), ("3", 803, 10480, 10, 19),
    ("4", 357, 10316, 20, 49), ("5", 40, 2507, 50, 99),
]
size = pl.DataFrame(
    [
        size_defaults | {
            "size_class": k, "size_lower": lo, "size_upper": hi, "establishments": n,
            "employment": e, "disclosure_code": "", "observation_status": "observed",
        }
        for k, n, e, lo, hi in published
    ]
    + [
        size_defaults | {
            "size_class": "6", "size_lower": 100, "size_upper": 249, "establishments": 4,
            "employment": None, "disclosure_code": "N", "observation_status": "suppressed",
        },
        size_defaults | {
            "size_class": "7", "size_lower": 250, "size_upper": 499, "establishments": 1,
            "employment": None, "disclosure_code": "N", "observation_status": "suppressed",
        },
    ],
    schema=QCEW_NATIONAL_SIZE_SCHEMA,
)

monthly.write_parquet(OUT / "qcew_monthly.parquet")
size.write_parquet(OUT / "qcew_national_size.parquet")
pl.DataFrame(schema=CBP_STATE_SIZE_SCHEMA).write_parquet(OUT / "cbp_state_size.parquet")
pl.DataFrame(schema=BRIDGE_SCHEMA).write_parquet(OUT / "bridge.parquet")
print(monthly.height, size.height, "rows;", 7713 - size["establishments"].sum(), "estab gap")
PY
```

Expected: `3 7 rows; 0 estab gap`. A non-zero gap means a typo in the published numbers, and the
Task 4 gate would reject the fixture.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/integration/test_constraint_cli.py -v`
Expected: FAIL with `Error: No such command 'build-constraints'`.

- [ ] **Step 4: Add `load_system` to `system.py`**

```python
def load_system(constraints_dir: Path, *, expected_hash: str | None = None) -> BuiltSystem:
    """Rebuild a system from the three persisted tables, optionally pinned to a known hash.

    `solve-bounds` runs as a separate invocation, so it reads what `build-constraints` wrote rather
    than reassembling from the harmonized layer. Recomputing the constraint set here would make the
    two commands two implementations of one contract, and §17.6's golden constraint matrices would
    only ever check one of them.

    `expected_hash` closes the gap that separation opens. The run id is derived from the
    *harmonized* inputs while these tables come from `data/constraints/`, so nothing else stops a
    `solve-bounds` run from writing bounds into a directory keyed to inputs that did not produce
    them. Passing the hash the build recorded is what makes §18.1's `constraint_set_hash`
    load-bearing rather than decorative.
    """
    frames = {}
    for name in ("target_cell", "constraint_row", "constraint_coefficient"):
        path = constraints_dir / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing; run `build-constraints` first")
        frames[name] = pl.read_parquet(path)
    digest = constraint_set_hash(
        frames["target_cell"], frames["constraint_row"], frames["constraint_coefficient"]
    )
    if expected_hash is not None and digest != expected_hash:
        raise IncompatibleMarginError(
            f"constraint_set_hash mismatch: {constraints_dir} holds {digest}, the run manifest "
            f"records {expected_hash}. These tables were not built from the harmonized inputs "
            "this run is keyed to; re-run `build-constraints`"
        )
    return BuiltSystem(
        cells=frames["target_cell"],
        rows=frames["constraint_row"],
        coefficients=frames["constraint_coefficient"],
        constraint_set_hash=digest,
        compatibility_report={},
    )
```

Add `from pathlib import Path` and `from ..errors import IncompatibleMarginError` to
`system.py`'s imports.

- [ ] **Step 5: Add both commands to `cli.py`**

```python
def _constraints_dir(cfg: "Config") -> Path:
    """§6.2's `data/constraints/`, resolved beside the configured staged root."""
    return Path(cfg.storage.staged_uri).parent / "constraints"


def _input_digests(cfg: "Config") -> dict[str, str]:
    """A sha256 per harmonized input, which is what makes the run id a function of the data."""
    import hashlib

    staged = Path(cfg.storage.staged_uri)
    return {
        path.stem: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(staged.glob("*.parquet"))
    }


@app.command("build-constraints")
def build_constraints_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Assemble the constraint system from the harmonized layer and persist it."""
    import json

    import yaml

    import highspy

    from .build import write_parquet_deterministic
    from .config import resolved_dict
    from .constraints import graph
    from .constraints.system import build_constraint_system
    from .contracts import (
        CONSTRAINT_COEFFICIENT_SCHEMA,
        CONSTRAINT_ROW_SCHEMA,
        TARGET_CELL_SCHEMA,
        HarmonizedData,
        schema_fingerprint,
    )
    from .runs import run_dir, run_id

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    built = graph.assign_components(build_constraint_system(data, cfg))

    out = _constraints_dir(cfg)
    hashes = {
        "target_cell": write_parquet_deterministic(built.cells, out / "target_cell.parquet"),
        "constraint_row": write_parquet_deterministic(built.rows, out / "constraint_row.parquet"),
        "constraint_coefficient": write_parquet_deterministic(
            built.coefficients, out / "constraint_coefficient.parquet"
        ),
    }

    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    run.mkdir(parents=True, exist_ok=True)
    (run / "config.resolved.yaml").write_text(yaml.safe_dump(resolved_dict(cfg), sort_keys=True))
    (run / "schema_manifest.json").write_text(
        json.dumps(
            {
                "constraint_set_hash": built.constraint_set_hash,
                "output_hashes": hashes,
                "schema_fingerprints": {
                    "target_cell": schema_fingerprint(TARGET_CELL_SCHEMA),
                    "constraint_row": schema_fingerprint(CONSTRAINT_ROW_SCHEMA),
                    "constraint_coefficient": schema_fingerprint(CONSTRAINT_COEFFICIENT_SCHEMA),
                },
                "compatibility_report": built.compatibility_report,
                # REQ-029 names the solver among the fail-closed surfaces, and §18.1 wants a run
                # reproducible from its manifest. `config.resolved.yaml` records that the solver is
                # HiGHS; only this records which HiGHS.
                "solver": cfg.constraints.solver,
                "solver_version": highspy.Highs().version(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    write_parquet_deterministic(
        graph.component_provenance(built), run / "constraint_manifest.parquet"
    )
    typer.echo(f"constraint_set_hash {built.constraint_set_hash}")
    for table, digest in sorted(hashes.items()):
        typer.echo(f"{table} {digest}")


@app.command("solve-bounds")
def solve_bounds_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Solve sharp LP/MILP bounds for every target cell and flag the disclosive ones."""
    from .build import write_parquet_deterministic
    from .constraints.bounds import solve_bounds
    from .constraints.system import load_system
    from .disclosure.flags import build_flags
    from .runs import run_dir, run_id

    import json

    cfg = load_config(config)
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    manifest = run / "schema_manifest.json"
    if not manifest.exists():
        raise typer.BadParameter(
            f"{manifest} is missing: no `build-constraints` run matches the harmonized inputs "
            "currently in the staged directory. Run `build-constraints` first"
        )
    built = load_system(
        _constraints_dir(cfg),
        expected_hash=json.loads(manifest.read_text())["constraint_set_hash"],
    )
    result = solve_bounds(built, cfg.constraints)
    flags = build_flags(result.bounds, built.cells, cfg.disclosure)

    run.mkdir(parents=True, exist_ok=True)
    write_parquet_deterministic(result.bounds, run / "deterministic_bounds.parquet")
    write_parquet_deterministic(result.components, run / "component_rank.parquet")
    write_parquet_deterministic(flags, run / "disclosure_flags.parquet")
    counts = result.bounds.group_by("bound_status").len().sort("bound_status")
    for row in counts.iter_rows(named=True):
        typer.echo(f"{row['bound_status']} {row['len']}")
    typer.echo(f"flagged {flags['narrow_feasible_interval_flag'].sum()} narrow, "
               f"{flags['exact_reconstruction_flag'].sum()} exact")
```

Add `from .config import Config` under `TYPE_CHECKING` in `cli.py` for the two helper annotations.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/integration/test_constraint_cli.py -v`
Expected: PASS, all five tests. The second is the §16.1 idempotence criterion (one run
directory, identical bytes); the fifth is the guard that makes the hash load-bearing.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/cli.py src/logging_employment/constraints/system.py tests/integration/test_constraint_cli.py tests/fixtures/constraints
git commit -m "feat(cli): add build-constraints and solve-bounds with deterministic run dirs

solve-bounds reads what build-constraints wrote rather than reassembling from the
harmonized layer, so the two commands are one contract rather than two
implementations of it.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15: The eight §17.2 property tests and the §17.6 golden fixtures

**Files:**
- Create: `tests/unit/test_constraint_properties.py`
- Create: `tests/integration/test_constraint_golden.py`
- Create: `tests/fixtures/constraints/golden_constraint_matrix.csv`
- Create: `tests/fixtures/constraints/golden_bounds.csv`

**Interfaces:**
- Consumes: everything from Tasks 3–13.
- Produces: no source module. This task is the acceptance evidence for §19 Phase 2's "toy and
  fixture constraints pass".

§17.2 lists nine properties. Eight of them are Stage 2's, and this task covers all eight. The
ninth — "every reconciled draw lies within bounds and satisfies margins" — needs a reconciliation
layer and a draw, both of which are Stage 3's; the roadmap's Stage 2 exit line names only the
eight, and this is why.

The toy systems are built from `ConstraintDraft`s directly, not from QCEW frames. Parent-child
hierarchies and overlapping row/column margins do not exist in the harmonized layer — Stage 1
ingested one industry at one ownership — so a test that waited for real data to exercise them would
never run. §17.2 says "use generated toy tables" for exactly this reason.

- [ ] **Step 1: Write the property tests**

Create `tests/unit/test_constraint_properties.py`:

```python
"""§17.2's eight Stage 2 constraint properties, on generated toy systems."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, rows, system
from logging_employment.contracts import TARGET_CELL_SCHEMA
from logging_employment.errors import IncompatibleMarginError, InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]
CONFIG = load_config(REPO / "config.yaml")


def _cells(values: dict[str, float | None], vintages: dict[str, str] | None = None):
    """A `target_cell` frame from `{cell_id: observed value or None}`."""
    vintages = vintages or {}
    return pl.DataFrame(
        [
            {
                "cell_id": cell_id,
                "state_fips": "US",
                "reference_month": "2024-03",
                "size_concept": "march_reference",
                "size_class": cell_id,
                "ownership_code": "5",
                "industry_code": "113310",
                "naics_vintage": vintages.get(cell_id, "NAICS 2022"),
                "observation_status": "observed" if value is not None else "suppressed",
                "observed_value": value,
                "source_snapshot_id": "toy",
                "qcew_disclosure_code": "" if value is not None else "N",
            }
            for cell_id, value in values.items()
        ],
        schema=TARGET_CELL_SCHEMA,
    )


def _margin(name: str, weights: dict[str, float], *, vintages: list[str] | None = None):
    """One equality coupling several cells, summing to zero."""
    return rows.constraint(
        constraint_id=name,
        constraint_class="public_accounting_fact",
        relation="eq",
        coefficients=tuple(weights.items()),
        rhs_lower=0.0,
        rhs_upper=0.0,
        is_hard=True,
        evidence_kind="published_value",
        period_scope="2024-03",
        geography_scope="US",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="toy",
        provenance_text=f"toy margin {name}",
        vintage_compatibility_status=rows.vintage_status(vintages or ["NAICS 2022"]),
    )


def _solve(values, drafts, vintages=None):
    cells = _cells(values, vintages)
    all_drafts = [
        *rows.observed_value_rows(cells),
        *rows.nonnegativity_rows(cells),
        *rows.integrality_rows(cells),
        *drafts,
    ]
    row_frame, coefficient_frame = rows.to_frames(all_drafts)
    built = graph.assign_components(
        system.BuiltSystem(
            cells=cells,
            rows=row_frame,
            coefficients=coefficient_frame,
            constraint_set_hash=system.constraint_set_hash(cells, row_frame, coefficient_frame),
            compatibility_report={},
        )
    )
    result = bounds.solve_bounds(built, CONFIG.constraints)
    return {
        row["cell_id"]: (row["selected_lower"], row["selected_upper"], row["bound_status"])
        for row in result.bounds.iter_rows(named=True)
    }


def test_parent_equals_children() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": 40.0, "c": 30.0},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert all(status == "observed" for _, _, status in solved.values())
    with pytest.raises(InfeasibleComponentError):
        _solve(
            {"P": 100.0, "a": 30.0, "b": 40.0, "c": 31.0},
            [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
        )


def test_one_missing_child_is_exactly_recoverable() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": 40.0, "c": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert solved["c"] == (30.0, 30.0, "exactly_recoverable")


def test_two_missing_children_are_only_partially_identified_under_nonnegativity() -> None:
    solved = _solve(
        {"P": 100.0, "a": 30.0, "b": None, "c": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "c": 1.0, "P": -1.0})],
    )
    assert solved["b"] == (0.0, 70.0, "partially_identified")
    assert solved["c"] == (0.0, 70.0, "partially_identified")


def test_overlapping_margins_identify_a_cell_despite_two_suppressions_per_row() -> None:
    # A 2x2 table: row 1 holds two suppressed cells, so its own margin identifies neither. The
    # column margin does, because the other member of column 1 is published.
    solved = _solve(
        {"x11": None, "x12": None, "x21": 20.0, "x22": 30.0,
         "r1": 50.0, "r2": 50.0, "c1": 25.0, "c2": 75.0},
        [
            _margin("row1", {"x11": 1.0, "x12": 1.0, "r1": -1.0}),
            _margin("row2", {"x21": 1.0, "x22": 1.0, "r2": -1.0}),
            _margin("col1", {"x11": 1.0, "x21": 1.0, "c1": -1.0}),
            _margin("col2", {"x12": 1.0, "x22": 1.0, "c2": -1.0}),
        ],
    )
    assert solved["x11"] == (5.0, 5.0, "exactly_recoverable")
    assert solved["x12"] == (45.0, 45.0, "exactly_recoverable")


def test_a_rounding_interval_blocks_a_recovery_an_exact_parent_would_allow() -> None:
    exact = _solve(
        {"P": 100.0, "a": 30.0, "b": None},
        [_margin("m", {"a": 1.0, "b": 1.0, "P": -1.0})],
    )
    assert exact["b"] == (70.0, 70.0, "exactly_recoverable")

    rounded = _solve(
        {"P": None, "a": 30.0, "b": None},
        [
            _margin("m", {"a": 1.0, "b": 1.0, "P": -1.0}),
            rows.rounding_interval_row(
                "round|P", "P", published_value=100.0, grid_width=100.0,
                endpoint_rule="lower closed, upper open per source documentation",
                period_scope="2024-03", geography_scope="US", industry_scope="113310",
                ownership_scope="5", source_snapshot_ids="toy",
            ),
        ],
    )
    assert rounded["b"] == (20.0, 120.0, "partially_identified")


def test_integrality_tightens_a_bound_the_lp_leaves_fractional() -> None:
    # 2x - y = 0 with y in [1, 3]: the LP allows x in [0.5, 1.5], integrality pins x to 1.
    solved = _solve(
        {"x": None, "y": None},
        [
            _margin("m", {"x": 2.0, "y": -1.0}),
            rows.rounding_interval_row(
                "round|y", "y", published_value=2.0, grid_width=2.0,
                endpoint_rule="toy grid", period_scope="2024-03", geography_scope="US",
                industry_scope="113310", ownership_scope="5", source_snapshot_ids="toy",
            ),
        ],
    )
    assert solved["x"] == (1.0, 1.0, "exactly_recoverable")


def test_a_margin_spanning_two_naics_vintages_is_detected_rather_than_stacked() -> None:
    with pytest.raises(IncompatibleMarginError, match="vintage"):
        _solve(
            {"P": 100.0, "a": 30.0, "b": None},
            [
                _margin(
                    "m", {"a": 1.0, "b": 1.0, "P": -1.0},
                    vintages=["NAICS 2017", "NAICS 2022"],
                )
            ],
            vintages={"a": "NAICS 2017"},
        )


def test_components_solve_independently() -> None:
    together = _solve(
        {"P": 100.0, "a": 30.0, "b": None, "Q": 60.0, "c": 10.0, "d": None},
        [
            _margin("m1", {"a": 1.0, "b": 1.0, "P": -1.0}),
            _margin("m2", {"c": 1.0, "d": 1.0, "Q": -1.0}),
        ],
    )
    alone = _solve(
        {"P": 100.0, "a": 30.0, "b": None},
        [_margin("m1", {"a": 1.0, "b": 1.0, "P": -1.0})],
    )
    assert together["b"] == alone["b"] == (70.0, 70.0, "exactly_recoverable")
    assert together["d"] == (50.0, 50.0, "exactly_recoverable")
```

- [ ] **Step 2: Run the property tests**

Run: `uv run pytest tests/unit/test_constraint_properties.py -v`
Expected: PASS, all eight tests. Every one of §17.2's eight Stage 2 bullets is now covered by a
named test; if one fails, the engine is wrong, not the toy.

- [ ] **Step 3: Generate the two golden fixtures**

```bash
uv run python - <<'PY'
from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, system
from logging_employment.contracts import HarmonizedData

FIXTURES = Path("tests/fixtures/constraints")
cfg = load_config(Path("config.yaml"))
built = graph.assign_components(
    system.build_constraint_system(HarmonizedData.load(FIXTURES), cfg)
)
built.coefficients.sort(["constraint_id", "cell_id"]).write_csv(
    FIXTURES / "golden_constraint_matrix.csv"
)
bounds.solve_bounds(built, cfg.constraints).bounds.select(
    ["cell_id", "selected_lower", "selected_upper", "bound_status", "exactly_identified"]
).sort("cell_id").write_csv(FIXTURES / "golden_bounds.csv")
print(pl.read_csv(FIXTURES / "golden_bounds.csv"))
PY
```

Expected: a table in which the two suppressed national size cells read `400.0, 530.0` and
`250.0, 380.0`, both `partially_identified`, and the suppressed state cell reads a null upper bound
with `unbounded`. **If those three rows read anything else, stop and fix the engine — do not
regenerate the golden.**

- [ ] **Step 4: Write the golden test**

Create `tests/integration/test_constraint_golden.py`:

```python
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
    return graph.assign_components(
        system.build_constraint_system(HarmonizedData.load(FIXTURES), cfg)
    ), cfg


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
```

- [ ] **Step 5: Run every test written so far**

Run: `uv run pytest tests/unit tests/integration -q`
Expected: PASS. This is the first run over the whole Stage 2 suite together.

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_constraint_properties.py tests/integration/test_constraint_golden.py tests/fixtures/constraints
git commit -m "test(constraints): cover §17.2's eight properties and pin the §17.6 goldens

Toy systems are built from ConstraintDrafts, not QCEW frames: parent-child and
overlapping row/column margins do not exist in the harmonized layer, so a test
waiting for real data to exercise them would never run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 16: The D1 acceptance run

**Files:**
- Create: `tests/integration/test_d1_acceptance.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: the whole engine, and the real `data/staged/` tables Stage 1's live run produced.
- Produces: no source module. This task discharges the roadmap's Stage 2 `Exit:` line on real data.

This test is marked `slow` and skips when `data/staged/` is absent, because those tables are
gitignored: 562 MB of source bytes rebuild them, and no CI runner has them. It is the criterion the
roadmap states, so it must exist and must have been run on the owner's machine before the stage is
called complete — record the run's output in the completion notes.

- [ ] **Step 1: Write the acceptance test**

Create `tests/integration/test_d1_acceptance.py`:

```python
"""The roadmap's Stage 2 exit criteria, on the real D1 window.

Skipped when `data/staged/` is absent. Those tables are gitignored and rebuilt from 562 MB of
frozen source bytes, so this runs where the data lives rather than in CI.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, graph, system
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

# The sharp bounds for all 14 suppressed national size cells, derived analytically from the
# published margin and supports before this engine existed. Keys are (reference year, size class).
EXPECTED_BOUNDS: dict[tuple[int, str], tuple[float, float]] = {
    (2018, "5"): (2300.0, 2984.0), (2018, "6"): (900.0, 1584.0),
    (2019, "5"): (2450.0, 3304.0), (2019, "6"): (600.0, 1454.0),
    (2020, "5"): (2407.0, 3301.0), (2020, "6"): (600.0, 1494.0),
    (2021, "5"): (2274.0, 3019.0), (2021, "6"): (500.0, 1245.0),
    (2022, "6"): (400.0, 553.0), (2022, "7"): (250.0, 403.0),
    (2023, "6"): (700.0, 884.0), (2023, "7"): (250.0, 434.0),
    (2024, "6"): (400.0, 530.0), (2024, "7"): (250.0, 380.0),
}


@pytest.fixture(scope="module")
def solved():
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(
        system.build_constraint_system(HarmonizedData.load(STAGED), cfg)
    )
    result = bounds.solve_bounds(built, cfg.constraints)
    flags = build_flags(result.bounds, built.cells, cfg.disclosure)
    return built, result, flags


def test_every_suppressed_state_month_carries_a_bound_status(solved) -> None:
    built, result, _ = solved
    suppressed = built.cells.filter(
        (pl.col("observation_status") == "suppressed")
        & pl.col("cell_id").str.starts_with("state_total|")
    )
    assert suppressed.height == 1227  # Stage 1's stamp: 1,227 of 4,716 states+DC cells
    joined = result.bounds.join(suppressed.select("cell_id"), on="cell_id", how="semi")
    assert joined.height == 1227
    assert set(joined["bound_status"]) == {"unbounded"}


def test_the_national_size_bounds_match_the_hand_derived_values(solved) -> None:
    _, result, _ = solved
    produced = {}
    for row in result.bounds.filter(
        pl.col("cell_id").str.starts_with("national_size|")
        & (pl.col("bound_status") != "observed")
    ).iter_rows(named=True):
        _, _, month, _, _, _, size_class = row["cell_id"].split("|")
        produced[(int(month[:4]), size_class)] = (
            row["selected_lower"], row["selected_upper"]
        )
    assert produced == EXPECTED_BOUNDS


def test_no_real_cell_is_exactly_recoverable_and_exactly_one_is_narrow(solved) -> None:
    # Stated in advance rather than discovered here: no window year has exactly one suppressed
    # class, so exact recovery cannot fire. 2023 class 6 is the single cell whose relative width
    # (184/792 = 0.232) clears the configured 0.25 threshold.
    _, _, flags = solved
    assert flags["exact_reconstruction_flag"].sum() == 0
    narrow = flags.filter(pl.col("narrow_feasible_interval_flag"))
    assert narrow.height == 1
    assert narrow["cell_id"][0].endswith("|6")
    assert "2023-03" in narrow["cell_id"][0]


def test_the_component_decomposition_and_the_rank_cache_behave_at_scale(solved) -> None:
    _, result, _ = solved
    # 4,716 state cells and 8 size components: the state cells are singletons because
    # SRC-QCEW-006 came back `decline`.
    assert result.components.filter(pl.col("cell_count") == 1).height >= 4716
    assert result.components.filter(pl.col("cell_count") > 1).height == 8
    assert result.components["cache_hit"].sum() > 4000  # CON-005 doing real work


def test_no_hard_constraint_rests_on_an_assumed_threshold(solved) -> None:
    # §9.3's final bullets, asserted on the shipped artifact rather than only in the factory.
    built, _, _ = solved
    hard = built.rows.filter(pl.col("is_hard"))
    assert set(hard["constraint_class"]) <= {"public_accounting_fact", "definitional_support"}
    assert hard.filter(pl.col("provenance_text").str.contains("assumed_threshold")).height == 0
```

- [ ] **Step 2: Run it**

```bash
uv run pytest tests/integration/test_d1_acceptance.py -v -m slow
```

Expected: PASS, all five tests. Record the output in the completion notes — this is the evidence
for the roadmap's Stage 2 `Exit:` line.

- [ ] **Step 3: Run the two commands end to end on the real window**

```bash
uv run logging-estimates build-constraints --config config.yaml
uv run logging-estimates solve-bounds --config config.yaml
```

Expected from `solve-bounds`, in some order: `observed` for the published cells, `unbounded 1227`,
`partially_identified 14`, and `flagged 1 narrow, 0 exact`.

- [ ] **Step 4: Run the whole suite and the linters**

```bash
uv run pytest tests/unit tests/integration -q
uv run ruff check src tests/unit tests/integration
uv run black --check src tests/unit tests/integration
uv run interrogate -c pyproject.toml src
```

Expected: all green. `tests/audit/` is excluded from the ruff and black commands on purpose:
plan 2 recorded that 14 files there fail both, and sweeping them is not this stage's work.

- [ ] **Step 5: Document the two commands in the README**

Add to the README's usage section:

```markdown
### Deterministic identification (Stage 2)

    logging-estimates build-constraints --config config.yaml
    logging-estimates solve-bounds --config config.yaml

`build-constraints` writes `data/constraints/` and a run directory under `runs/`;
`solve-bounds` writes `deterministic_bounds.parquet`, `component_rank.parquet` and
`disclosure_flags.parquet` beside it. Both are idempotent: the run id is derived from the
resolved configuration and the harmonized inputs, so re-running lands on the same directory.

On the pilot window the engine bounds 14 suppressed national size classes to intervals 130–894
employees wide, and reports every one of the 1,227 suppressed state-month cells as `unbounded`.
That is not a gap in the engine: `SRC-QCEW-006` came back `decline`, so no national employment
margin exists to constrain a state cell, and nonnegativity is the only public fact that touches
one. Stages 3–5 are what narrow them.
```

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_d1_acceptance.py README.md
git commit -m "test(constraints): discharge the Stage 2 exit criteria on the real D1 window

All 14 suppressed national size cells match bounds derived by hand from the
published margin and supports. All 1,227 suppressed state cells are unbounded,
which is what SRC-QCEW-006's decline implies rather than an engine gap.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review notes

**Spec coverage.** Every roadmap Stage 2 `Produces` item maps to a task: `target_cell` (3),
`constraint_row` / `constraint_coefficient` (5–6), `deterministic_bounds` (11), the §7.8
`constraint_class` enum and the `is_hard` restriction (2, 5), `ConstraintSystem` and
`build_constraint_system` / `solve_bounds` on HiGHS (7, 10, 11), `bound_status` per cell (11),
component / rank / nullity records with CON-004 provenance (8, 9), the §9.7 diagnostic (12),
`disclosure/flags.py` (13), `constraint_set_hash` (7), and the two CLI commands (14). Every
roadmap `Exit` clause maps to a named test: the eight §17.2 properties (15), the infeasibility
halt (12), a `bound_status` on every suppressed state-month and a flag on every exact or narrow
cell (16), and the assumed-threshold refusal (5 and 16).

**Gap-closed walkthrough.** The roadmap names 26 IDs for this stage. One task per row:

| ID | Task | Note |
|---|---|---|
| REQ-002 (`target_cell`) | 3 | Stage 1 applied the universe filter; every cell inherits it and this stage does not re-apply it. |
| REQ-009 | 5, 6 | Sparse public accounting constraints, one factory and five builders. |
| REQ-010 | 8, 9 | Components, structural and numerical rank, nullity. |
| REQ-011 | 10, 11 | LP bounds, MILP tightening, §9.6's exactness rules. |
| REQ-012 (bounds table) | 2, 11 | `deterministic_bounds` has no posterior column and never gains one. The other half of "kept separate" needs a posterior to be separate *from*, so it is testable only at Stage 5. |
| REQ-017 (constraint scope) | 4, 6 | Two independent March refusals: the gate rejects a non-March row, the builder refuses to build from one. |
| REQ-026 (flags) | 13 | The two identification flags. Release actions are Stage 8's. |
| REQ-029 (compat/solver) | 4, 10, 11, 14 | Compatibility gates halt; `SolverError` halts on any status that is neither an optimum nor an unbounded direction; the run manifest records the solver and its version. |
| INV-001 | 6, 11 | Observed and true-zero cells are pinned by equality and never solved for. |
| INV-004 | 5 | Every restriction carries a class *and* an `evidence_kind`; the factory is the only construction point. |
| INV-005 | 9, 10 | Only `is_hard` rows reach the box, the matrix, and the rank computation. Task 10 has a test proving a soft row cannot narrow a bound. |
| INV-006 (rounding intervals) | 6, 15 | `rounding_interval_row` plus the §17.2 property that a rounded parent blocks a recovery an exact one allows. |
| INV-007 (compatibility status) | 3, 4, 5 | One release vintage per cell, the size-margin gate, and the factory's refusal to make a cross-vintage row hard. |
| INV-008 (feasible half) | 2, 11 | Same as REQ-012: the columns exist and carry only deterministic values. |
| INV-011 (constraint half) | 4, 6 | As REQ-017. Enforced where the constraint is created, so Stage 6 inherits it. |
| SRC-QCEW-006 (constraint half) | 5, 7, 16 | The `decline` as a structural refusal, asserted at the factory, on the assembled system, and on real data. |
| SRC-QCEW-007 (constraint half) | 4 | Stage 1's `assert_definitional_alignment`, called before any row exists. |
| SRC-QSIZE-003 (hard-control eligibility) | 4 | The verdict is *eligible*, on the establishment identity closing in 8 of 8 years. |
| CON-001, CON-002 | 8 | Bipartite graph and connected components. |
| CON-003 | 9 | Both ranks and nullity. |
| CON-004 | 8 | `component_provenance`. |
| CON-005 | 9 | The shape-keyed rank cache, which the D1 run hits over 4,000 times. |

**Two spec items this stage deliberately does not discharge.** CON-005's cache covers the
equality-pattern reuse §9.5 names; it does not cache across *runs*, which nothing requires.
And §17.2's ninth property is Stage 3's, as Task 15 states.

**Two roadmap wordings that do not match the spec, resolved in favour of the spec.** The roadmap
says "component, rank, and nullity records with the §9.4 provenance"; §9.4 is rounding and CON-004
is provenance, so Task 8 implements CON-004. The roadmap lists `SRC-QSIZE-003` (hard-control
eligibility) under this stage: Task 4's gate is where that eligibility is decided, and its answer
is yes for the national size margin, on the establishment identity closing in 8 of 8 years.

**One §7.8 field this stage stretches.** `evidence_kind` has no column, so it is written into
`provenance_text` behind a fixed prefix. That is queryable but stringly typed; adding the column
to §7.4-style contracts is a spec amendment, and this plan does not make one. Record it as a
deferred item at completion.

**Known-empty results, stated so they are not read as defects.** No cell is exactly recoverable on
real D1 data; no MILP re-solve fires on real D1 data (every real width is at least 130, far above
the configured threshold of 25); no rounding-interval row is built on real D1 data (no QCEW field
this stage reads is rounded); and no component is infeasible. All four paths are exercised by Task
15's toy systems and Task 12's perturbed fixture, which is why those tasks exist.

---

## Execution handoff

**Plan complete and saved to `specs/plans/3-stage2-logging-employment-spec.md`.**

**Recommended: `/clear` (or open a new session) and execute against the saved plan** — a fresh
session drops this planning conversation and lets execution run on the standard model default.
Two execution options, either session:

**1. Subagent-Driven (recommended)** — a fresh subagent per task, two-stage review between tasks.

**2. Inline Execution** — the tasks executed here, in plan order (executing-plans).

Continuing in THIS session works too, but costs more on a long plan: every execution turn re-reads
the full planning history and inherits this session's model. **Which approach?**

Before either: **merge `stage1-foundation-ingestion` into `main`**, then branch for Stage 2. Task 1
Step 1 fails fast on a base without it, but a merge decided deliberately is better than a merge
discovered by a failing guard.
