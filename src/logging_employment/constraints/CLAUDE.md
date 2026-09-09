# `constraints/` — the deterministic identification engine (§9)

Turns the harmonized QCEW tables into a labelled constraint system (§7.7 cells, §7.8 rows, §7.9
coefficients) and solves two LPs per suppressed cell for §9.1's sharp bounds `L_j`/`U_j`, persisted
as §7.10 `deterministic_bounds`. §9.1 forbids any model, prior, or borrowing here: every restriction
is a published accounting fact or a definition. Spec map: §9.3 permitted/forbidden hard
constraints · §9.4 rounding · §9.5 `CON-001`..`005` · §9.6 LP/MILP · §9.7 diagnostics · §9.8
classification · §5.5 compatibility gate · §18.1 hash · §17.2/§17.6 tests.

## What a fresh agent gets wrong

**1. There is no state-sum margin, and adding one is the failure mode.** `SRC-QCEW-006` (§8.1) came
back **`decline`** (verdict in the spec's Rollout → Stage stamps): all 96 testable months carry at
least one suppressed states+DC cell, so the national/state employment identity is untestable.
`rows.assert_no_national_employment_margin` refuses *both* shapes — states coupled to each other,
states coupled to the national row — and `build_constraint_system` runs it over the drafts before
they become frames. `cells.national_total_cells` separately restricts national cells to the months
a size margin needs, so no orphan national cell reads as a state/national link. The only margin
built here is `size_margin|<month>`: national classes minus the national all-sizes cell = 0, so
INV-001 pins that total through its own fixing row instead of an rhs literal.

**2. Every solve-path function has two execution paths.** `bounds.column_specs`,
`bounds.matrix_rows`, `rank.equality_matrix`, `bounds.solve_component`, `diagnostics.diagnose` all
take `index: SystemIndex | None`; the `None` branch re-filters the frames. Production always passes
the index, so the filter path is the one that stops being exercised (`diagnose` runs only on an
infeasible component, and `tests/unit/test_constraint_index.py`'s header records that the D1
window has none). **Order is the contract**:
`index.cells_by_component` becomes the model's column indices (`_model` builds `at` from
`list(specs)`), `index.coefficients_by_constraint` becomes `addRow`'s index array. Editing one
branch and not the other, or permuting either structure, leaves the suite green and every bound
bit-identical — on this window every hard coefficient is ±1 (the golden matrix CSV holds only
`1.0`/`-1.0`). The one guard is `tests/unit/test_constraint_index.py`, asserting *list* equality
between the paths. Touch either path, run that file.

**3. The null-closed filter idiom is not redundancy.** `is_null() | ~str.ends_with(...)` in
`compat.assert_size_margin_compatible`, `compat.assert_size_support_holds`,
`rows.size_support_rows`; `ne_missing` rather than `!=` in the vintage check. Polars drops a null
predicate in `filter`, so the "simpler" form passes exactly the malformed row the gate exists to
catch. Do not simplify these.

**4. Fail-closed lives in small mechanics** (REQ-029, §18.3). `bounds._optimize` reads
`getInfo().objective_function_value` *before* clearing the cost vector — swap those two lines and
every bound in the engine returns 0.0. A HiGHS status that is neither `kOptimal` nor `kUnbounded`
raises `SolverError` instead of returning `None`, because `None` already means "unbounded".
`bounds._entries` subscripts the index dict rather than `.get(..., ([], []))`: an empty group would
reach `addRow` as a constraint on nothing and narrow nothing, silently.

**5. `index.build_index` must get the post-`assign_components` system.** Pre-decomposition rows all
carry a null `component_id`, so every per-component row list comes back empty — and §18.1 excludes
`component_id` from `constraint_set_hash`, so both objects share a hash and no hash check catches
it. `solve_bounds` decomposes first and indexes `built`, never `system`.

## Contracts at the boundary

- **Assembly order**: `system.build_constraint_system` is gates → cells → rows.
  `compat.run_compatibility_gates` (`harmonize.universe.assert_definitional_alignment` =
  SRC-QCEW-007 §8.1, then `assert_size_margin_compatible`; §5.5) runs *first* because it guards
  construction — a gate running after the rows exist checks a system that already happened.
  `graph.assign_components` is applied by the caller (CLI, `solve_bounds`), not by the build.
- `cells.cell_id` builds the cross-package join key (format in the project `CLAUDE.md`), kinds
  `state_total`/`national_total`/`national_size`; `baselines/runner.py` and `validate/recover.py`
  rebuild ids through it rather than formatting their own. **Never substring-match a `cell_id`** —
  a one-character `size_class` matches inside `113310` and `NAICS 2017`, and `validate/recover.py`
  records that doing so measurably returned 6 rows where 1 was wanted.
- `component_id` lands on **rows only**: §7.7's field list has no such column and `validate_frame`
  rejects extras, so cell membership is *derived* by `graph.component_membership`. Labels are
  ordered by the smallest `cell_id` per component, never by SciPy's traversal order.
- `is_hard` is INV-005's predicate, with one chokepoint at `bounds._hard_rows` so `column_specs`
  and `matrix_rows` cannot drift about which rows they split; a soft row stays in the graph and the
  persisted table but must never move a bound. Those two partition the hard non-integrality rows:
  a row becomes a column box only when it touches one cell with coefficient **exactly 1.0**, so a
  scaled single-cell row reaches the matrix rather than being silently divided through.
- `rows.constraint` is the only construction point, and refuses: a non-eligible class asking to be
  hard (§7.8 allows only `public_accounting_fact`, `definitional_support`);
  `evidence_kind='assumed_threshold'` asking to be hard (§9.3); a hard row whose
  `vintage_compatibility_status != "compatible"` (INV-007); an rhs shape contradicting the relation.
  `evidence_kind` has no §7.8 column, so it lands in `provenance_text` behind
  `contracts.EVIDENCE_PREFIX`.
- `system.load_system(dir, expected_hash=...)`: `solve-bounds` is a separate CLI invocation reading
  what `build-constraints` wrote; that hash is what stops a solve from writing bounds into a run
  directory keyed to inputs that did not produce those tables.

## Gotchas, and guarantees that are routinely overstated

- **INV-007 is narrower than it sounds.** This module sees `naics_vintage` only. `release_vintage`
  is guarded separately and far more narrowly by `cells._assert_one_vintage_per_cell` (one
  area-month published under two vintages). Neither covers a row spanning two area-months whose
  release vintages differ, and here that silence is correct: `qcew_monthly` carries 32 *distinct
  `release_vintage` values*, one per reference quarter — which is a reference key, not 32
  publication vintages (`ingest/CLAUDE.md` explains why). `rows.py`'s header is the source for
  that count; neither guard is a general INV-007 guarantee.
- **The size-margin gate rests mostly on establishments.** `compat.py`'s header records that the
  establishment margin is checkable in all eight window years and the employment margin in exactly
  one, 2017 — the only year with no suppressed class. `employment_checkable_years` in the returned
  report keeps that visible.
- Quarantine ≠ infeasible: `solve_bounds` tracks a local `infeasible` flag, because re-testing
  `component_id in quarantined` in the record branch once blanked every bound of a *feasible*
  quarantined component with no diagnostic to show for it. MILP-infeasible also raises a
  deliberately different message than LP-infeasible: the §9.7 slack diagnostic is built on the LP
  relaxation and would report zero slack — "nothing is wrong" about a run that just halted.
- `rank` uses hard **equality** rows only (INV-005); inequalities bound without removing a degree of
  freedom. Both ranks are computed (CON-003) — disagreement means the sparsity pattern promises
  identification the values do not deliver. CON-005's cache key is the matrix itself, so which
  component records `cache_hit=False` depends on `rank_table`'s iteration order.
- `rows.rounding_interval_row` is unreachable in production (no QCEW field this stage reads is
  rounded); it exists for §9.4 and is exercised by a §17.2 property. Not dead code.
- `rows.size_support_rows` matches a size row to a cell on `(reference_month, size_class)` and
  **never on industry**, so it needs a frame already filtered to one; it also refuses non-March
  rows outright (INV-011, `rows.py::size_support_rows`).
- `bounds.classify_bound_status` returns **four** of §7.10's seven statuses (`observed`,
  `unbounded`, `exactly_recoverable`, `partially_identified`). `model_estimable`/`model_only` are
  model claims §9.1 forbids here; `infeasible` is stamped by `solve_bounds` (`bounds.py::solve_bounds`,
  `:427`), not by the classifier — its own docstring's "two of seven" undercounts by one. §9.8's
  six suppressed-cell classes are a *different* list from §7.10's domain; keep the citations apart.
- National size cells get their ownership code stamped on (see `ingest/CLAUDE.md` for why the
  source table has none). It is `constants.PRIVATE_OWN_CODE`, passed at
  `system.build_constraint_system` — not read from `Config` — and it is
  `compat.assert_size_margin_compatible` that licenses the stamp. Read `cells.py`'s header first.

## Commands

One §16.2 alias worth knowing before you go looking for a type that does not exist:
`bounds.BoundConfig` *is* `config.ConstraintsConfig` (`bounds.py`), renamed to the spec's
signature name.

```bash
# 107 tests, all off committed fixtures — passes with data/ absent (e.g. in a worktree).
uv run pytest tests/unit/test_constraint_*.py tests/unit/test_bound_status.py \
  tests/integration/test_constraint_golden.py tests/integration/test_national_size_margin_golden.py

logging-estimates build-constraints --config config.yaml   # needs data/staged/*.parquet
logging-estimates solve-bounds     --config config.yaml    # needs that build's run dir + hash
```

Goldens in `tests/fixtures/constraints/` are **not** regenerated: §17.6 requires a documented reason
and reviewer approval, and `test_the_golden_carries_the_two_hand_derived_bounds` pins classes 6 and
7 to `[400, 530]` and `[250, 380]`, derived by hand before this code existed — a golden regenerated
from a broken engine still equals itself.
