# `reconcile/` — the §12 exact reconciliation layer

Maps every estimate or draw into the deterministic feasible set. Spec §12
(`specs/logging-employment-spec.md:1342-1432`): §12.1 principle, §12.2 `allocate`, §12.3 `scaling`,
§12.4 `projection`, §12.5 `matrix`, §12.6 `integerize`, §12.7/§16.2 `draws`. §17.3 lists exactly
seven properties and `tests/unit/test_reconcile_properties.py` names them `test_property_1` through
`test_property_7` (plus `3b`, `7b` and §17.1's rows 8-10). §12.1 says this layer "is not optional
post-hoc cosmetic adjustment" — there is no config key to skip it.

## Read this first: most of this package has no production caller yet

Nothing outside `baselines/` calls into this package. `baselines/runner.py::run_baselines`-277` is the
production path and calls, in order: `observed_partition` → `closure_audit` →
`assert_universe_closes` → `national_residual` → `allocate` → `integerize`.
`baselines/fallback.py::_assert_the_partition_is_the_anchors` also calls `national_residual`, to re-derive the residual from the
context's partition and refuse an anchor that disagrees. The other six `baselines/` modules import
`Weights` / `Anchor` / `Partition` as types only.

Everything else is implemented, tested, and **dead until a later stage wires it**:

- `scaling.scale_into_bounds` — reached only from `reconcile_draws` (Stage 5).
- `draws.reconcile_draws` — no caller; Stage 5 builds `ReconciliationInputs` from
  `deterministic_bounds` plus the anchor.
- `matrix.reconcile_matrix` / `projection.kl_project` — no caller; Stage 6, when `target_cell` first
  carries a state×size cell. `matrix.py`'s docstring says so explicitly: "NO REAL INPUT UNTIL STAGE
  6."
- `projection.require_supported_method` — called from **nowhere** in `src/`: the only references are
  its definition, two docstrings and the `__init__` re-export (`tests/unit/test_projection.py::test_weighted_quadratic_is_refused_as_unimplemented`
  is the sole caller anywhere). So `general_method: weighted_quadratic` currently passes config
  validation and is refused by nothing at runtime. Open item: see "The `general_method` guard lives
  at the CLI, not in the reconciliation layer" in `specs/deferred_items.md`.

Do not "fix" the empty call sites by inventing one. Do not delete them as dead code either.

**Name collision:** the `logging-estimates reconcile` CLI command (`cli.py`) imports nothing
from this package. It re-sums persisted `baseline_results.parquet` estimates against each month's
recorded residual and reports drift — a verifier, not a producer.

## The anchor is a modeling assumption, not a constraint

`anchor.py`'s module docstring is the authoritative argument; read it before touching anything here.
The load-bearing points:

- §12.2 says "for a compatible national total $N_t$" and never defines *compatible*. §5.5 does. Nine
  of its ten dimensions match by construction (same field, same QCEW file); the tenth — geography
  universe — is what `closure_audit` measures.
- The gate tests the **establishment universe, not employment**: national `qtrly_establishments`
  minus the sum over *all* published state rows (suppression hides employment, not establishment
  counts) must be exactly 0. `assert_universe_closes` (`anchor.py::assert_universe_closes`) halts the **whole run**, not
  one month, and also refuses any negative residual.
- `SRC-QCEW-006` came back `decline` (the argument is in `constraints/CLAUDE.md`), so no national
  employment margin may ever become a constraint row. The anchor is `anchor_basis =
  'declared_national_total'`, a `modeling_assumption` under INV-004/INV-005. The implied ceiling
  `E_{s,t} <= R_t` **must never be written back into `deterministic_bounds`**.
- Honest caveat already in the docstring: `qtrly_establishments` is constant within a quarter, so
  the per-month gate is quarterly-resolution evidence in a monthly shape.

## Contracts a fresh agent gets wrong

- **The partition argument is authoritative; `national_residual` must not read
  `observation_status`.** That is what lets Stage 4's pseudo-suppression mask supply a different
  partition without mutating `qcew_monthly`. Pinned by `tests/unit/test_anchor.py::test_national_residual_never_reads_observation_status`.
  `observed_partition` is only the default builder; `true_zero` belongs in `disclosed` (a published
  value), not `missing`.
- **`closure_audit` iterates the months in `monthly`, not the keys of `partitions`**
  (`anchor.py::closure_audit`-171`). A month with a national row and no state rows — the shape a truncated
  ingest produces — would otherwise be skipped in silence.
- **`check_domain` runs before the empty-missing-set shortcut** in both `allocate`
  (`allocate.py::allocate`-88`) and `scale_into_bounds` (`scaling.py::scale_into_bounds`-67`). Reversing that order lets a
  populated weight vector against an empty missing set return `{}` instead of raising. Weights must
  be *exactly* the missing set, positive, finite, and every cell must carry a `basis` — silent
  subsetting reallocates absent cells' share onto the covered ones and looks well-formed. `Weights`
  deliberately carries no employees unit (`baselines.interfaces.EmployeeWeights` does); do not add
  unit validation here.
- **`Bounds.upper = None` means +inf, not "missing"** (`Bounds.upper_of`, `scaling.py::upper_of`). On D1,
  `selected_upper` is null on almost every unknown cell, so the `sum U < R_t` arm of §12.3's
  predicate is vacuous. Coercing null to a large finite number would manufacture the "arbitrary
  top-class cap" §9.3 forbids by name.
- **§12.3's strict predicate is compared against `tolerance`, not in exact float arithmetic**
  (`scaling.py::scale_into_bounds`,83`). Equality is feasible — every cell exactly on its bound must succeed — and
  seven lower bounds of 0.1 sum to 0.7000000000000001.
- **`kl_project` breaks on step size, not on violation, and never raises.** It returns
  `(x, violation)`; a caller needing convergence checks the second element. Re-verified against its
  own docstring example — seed `[1,1]`, margin `[[1,1]]`, target `[10]`, `upper=[1,1]` gives
  `[1., 1.]` with violation `8.0` (everything after `targets` is keyword-only, `lower`, `floor`,
  `tolerance` and `max_iterations` included). §17.3's property tests feed jointly infeasible systems
  on purpose, so raising here would break a spec-mandated test — the ruling is the checked
  `kl_project` item in `specs/deferred_items.md`. `reconcile_matrix` compensates with its own
  post-check (`matrix.py::reconcile_matrix`).
- **Margins must be 0/1 indicator rows**, asserted at entry (`projection.py::_require_indicator_margins`). The uniform
  multiplicative update reproduces the I-projection only for incidence rows; a weighted row still
  lands on the hyperplane while minimizing a different objective than §12.4 names.
- **`reconcile_matrix` needs both checks, not one**: margin sums equal *before* iterating
  (`matrix.py::reconcile_matrix`), and achieved margins verified *after* (`matrix.py::reconcile_matrix`). Equal sums can still be
  unreachable from a seed's zero pattern, and IPF does not diverge loudly — it settles. §12.5: "fail
  and diagnose rather than forcing convergence."
- **`integerize` takes no config argument by design.** `integerization_tiebreak`'s `Literal` admits
  one value; ties break by `cell_id` ascending so §16.1 idempotence holds. Verified:
  `integerize({"04": 1.5, "01": 1.5}, total=3)` → `{"04": 1, "01": 2}`. Bounds are read per *cell
  that has a value*, never by iterating `upper` (a cap for an absent cell used to create a phantom
  entry), and the placement budget is computed once before the loop (`integerize.py::integerize`).
- **`reconcile_draws` never reduces the draw axis** (§12.7): negative dependence lives only in the
  joint object. A negative draw raises `WeightDomainError`; only a *zero* seed is floored — §12.4's
  floor covers zero, not sign.

## Config and conventions

`ReconciliationConfig` (`config.py::ReconciliationConfig`-135`): Appendix A supplies three keys; `tolerance` (1e-9),
`max_bisection_iterations`, `max_projection_iterations`, `zero_seed_floor`,
`integerization_tiebreak` are originated by this package because §12 specifies none. **Do not reuse
`constraints.feasibility_tolerance` (1e-7) here** — coupling them would let a solver tuning change
move a published total.

This package's errors, in `..errors`: `UniverseClosureError` (whole-run halt),
`InfeasibleResidualError`, `WeightDomainError`, `ConceptViolationError`, `IncompatibleMarginError`.
Cells are keyed by `state_fips` strings throughout; `Anchor.missing_cells` is a tuple and defines
iteration order for every downstream array.

`scaling.py` and several test files carry hand-typed D1 counts ("1,227 of 1,241") that are
undated and unrecomputed; `specs/deferred_items.md` has an open item on the five remaining `1,227`
sites — read it before citing or copying one.

## Commands

```bash
uv run pytest tests/unit/test_allocate.py tests/unit/test_anchor.py tests/unit/test_scaling.py \
  tests/unit/test_projection.py tests/unit/test_matrix.py tests/unit/test_integerize.py \
  tests/unit/test_reconcile_draws.py tests/unit/test_reconcile_properties.py
# 82 passed in 0.21s. Every reconcile unit test is pure — no `data/`, no network.

logging-estimates run-baselines --config config.yaml   # the only production path; needs data/
logging-estimates reconcile --config config.yaml       # drift verifier; does NOT call this package
```

Only the pytest line was executed for this file; both CLI commands need the gitignored `data/` and a
prior `build-constraints` run.

`anchor_audit.parquet` (schema `contracts.ANCHOR_AUDIT_SCHEMA`, `contracts.py`) lands in
`runs/<id>/baseline_results/` — **but only on a run that finished.** `assert_universe_closes` raises
inside `run_baselines` (`baselines/runner.py::run_baselines`) before it returns, and the write is downstream at
`cli.py::run_baselines_command`, so a failed gate persists no audit table at all. What a failing run leaves is the
`UniverseClosureError` message (month, national and state establishment counts, gap,
publishing-area count); for the frame itself, call `closure_audit` directly.
