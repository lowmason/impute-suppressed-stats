# `validate/` — §13's pseudo-suppression harness

Hides cells QCEW actually published, re-runs the §10 baselines and rebuilds and re-solves the §9
constraint system on the masked frame, then scores the estimates against the withheld truth. Spec
map: §13.2 → `propensity` + `regimes`, §13.3 → `regimes`, §13.4 → `leakage`, §13.5-13.8 →
`metrics`, §13.10 → `scoreboard`; also §10.7 → `intervals`, §10.8 → `scoreboard`'s hierarchy
restriction, §16.2 → `harness.run_pseudo_suppression`.

## Read this first: the config knobs do not do what they look like

- **No `include_*` flag decides which regimes run.** That is `contracts.REGIME_DISPOSITIONS` plus
  membership in `regimes._SELECTORS`; `include_long_runs: false` does not stop
  `long_consecutive_runs` being masked and scored. Only `include_vintage_comparison` is read at run
  time (`harness.py::run_pseudo_suppression`). Five more — `primary_like`, `complementary_like`, `long_runs`,
  `rolling_origin`, `retrospective_smoothing` — are read *only* by
  `ValidationConfig._refuse_a_random_mask_only_design` (`config.py::ValidationConfig`-218`), which raises at
  config-load time if every designed regime is off (§13.2 forbids random masking as the only
  design). `include_random_mask_sanity_check` (`config.py::ValidationConfig`) is read nowhere at all, and no
  random-mask regime exists in `contracts.HOLDOUT_REGIMES`.
- **`replicates_per_regime` sizes the MASK, not the loop.** It is the target count a selector
  draws; the harness loops once per entry in `pseudo_suppression_seeds`. An earlier docstring read
  it the other way and the correction is recorded in `harness.py`'s module docstring.
- **`REGIME_SPECS` is built twice in `regimes.py`** (`:218` and again at `:373`) — the second
  build exists because `structural_break` and `naics_transition` are registered into `_SELECTORS`
  after the first comprehension. Registering a selector without rebuilding leaves `select=None`,
  and the harness then reports the regime as "does not mask QCEW cells" — a silent no-op wearing a
  reason string.

## The boundary

One entry point: `run_pseudo_suppression(data, estimators, config) -> ValidationResult(scores,
metrics, scoreboard, manifest)`. The only production caller is `cli.py::validate_command`
(`logging-estimates validate`), which writes `validation_scores.parquet`,
`validation_metrics.parquet`, `validation_scoreboard.parquet` and `validation_manifest.json` into
`runs/<id>/`.

- **§16.2's signature is deviated from deliberately.** The spec writes `config: ValidationConfig`;
  the implementation takes the whole `Config` (it needs `config.constraints` for `solve_bounds` and
  the full object for `run_baselines`) and defaults it to `None` only so §16.2's argument *order*
  survives. A `None` raises `ConceptViolationError` — a bare `assert` would vanish under `-O`.
- **Schema enforcement is asymmetric.** `metrics` is gated by `validate_frame(...,
  VALIDATION_METRIC_SCHEMA, ...)` in `cli.py` before the write; `scores` deliberately is not.
  `contracts.VALIDATION_SCORE_SCHEMA` declares `replicate`, `mask_arm` and
  `lookback_months_masked` and the scores frame carries none of them — `_join_truth` emits
  `run_baselines`' columns plus `truth`, `suppression_type`, the masked bounds, `regime`, `seed`,
  `masked_constraint_set_hash`. Narrowing it is a deferred decision, and that deferred item is
  itself stale: it says *both* tables are ungated.
- **The mask arm is the literal `"state_total"` at every call site** — `harness.py` passes
  `arm="state_total"` at `:135`, `:136`, `:139`, `:152`. `national_size` is declared in
  `contracts.MASK_ARMS` and implemented (`recover.mask_and_solve_size`, `mask.apply_size_mask`) but
  nothing scores it: the §10 baselines estimate state totals, not size classes. `scoreboard._best`'s
  two-arm refusal guards a future wiring, not a live branch.
- **A regime that scores nothing must say why.** Every manifest entry with `n_scored == 0` carries
  a `reason`, pinned by
  `test_d1_validation.py::test_no_regime_reports_zero_scores_without_saying_why`. The empty
  partition reading as "scored, nothing wrong" is the failure mode this package is shaped around.

## Implemented but not wired — do not "fix" by inventing a design

- `rolling_origin` and `cbp_size_gaps` are `feasible` and legitimately score zero: neither hides a
  QCEW cell (one truncates the frame, one drops CBP state-years), so neither produces a
  `MaskTarget`. `harness` short-circuits on `spec.select is None` *before* calling `select_targets`,
  so that function's own `return []` is unreachable for them and a fix aimed there would never run.
  `specs/deferred_items.md` has the open item "Wire `rolling_origin` and `cbp_size_gaps` into the
  harness scoring loop".
- `regimes.cbp_size_gap_keys` and `regimes.apply_cbp_gap` have **no caller and no
  test** anywhere in `src/`, `tests/` or `scripts/`; the only mention is a comment at
  `harness.py::run_pseudo_suppression`. `propensity.complementary_partners` has no production caller either (only
  `tests/unit/test_validate_complementary.py`), and
  `scoreboard.assert_scored_cells_are_primary_like` would refuse its output. That refusal message
  names the four edits that would make a second label legal; do them, or leave it unwired.
- `retrospective_smoothing` is `vacuous_on_registry` (no smoothing estimator in §10);
  `preliminary_to_final_vintage` is `cannot_run_on_d1` (no second snapshot in any staged table) and
  *raises* from `select_targets`.
- Do not read a green run as full §13 coverage. `metrics.py`'s emitters produce exactly
  `_POINT_NAMES`, three bound metrics, four coverage levels + width + CRPS + clip count, and three
  constraint metrics — so §13.5's infeasible-component rate and LP-vs-MILP tightening, §13.6's
  state-share / size-share / rank metrics, §13.7's calibration by state size, region, gap duration
  and propensity, and §13.9's sensitivity and ablation are **not** covered by this module.

## Invariants a fresh agent gets wrong

- **Mask the FRAME, never a hand-built `Partition`** (`mask.py` module docstring). A partition-only
  mask leaves the constraint system pinning the answer with a `fix|state_total|...` equality *and*
  leaves the truth in `context.partitions[m].missing["employment_value"]`.
- **A scored row's bounds come from `recover.mask_and_solve`, never from the run directory's
  `deterministic_bounds.parquet`** — that table still holds the published value for a cell this
  harness just hid. `MaskedSystem` is always a full rebuild, because `constraint_set_hash` is a
  stored field and `dataclasses.replace` would copy the unmasked hash onto a different system.
- **The truth join is INNER**, so a scored row that was never masked is impossible by construction
  rather than by assertion.
- **Eligibility is `area_type == 'state' & observed & qtrly_establishments > 0`.** Admitting a
  `true_zero` cell costs the whole month non-randomly and biases the scoreboard toward states
  without true zeros; `eligible_targets`' docstring has the measurement.
- **`_anchor_residuals` reads the FULL `run_baselines` frame, not `scored`**, and stays in its own
  column outside the constraint norms (INV-004/INV-005). Summing the masked subset against the
  month's whole residual reports violation where there is none — `harness.py` has the numbers.
- **Null, never 0.0, for an empty row set** in every emitter — a zero error over zero rows reads as
  perfect accuracy. Same rule for `mean_feasible_width` on unbounded cells.
- **§13.5 numbers on `state_total` are vacuous by construction.** Every masked state cell is
  `unbounded` with a null `selected_upper`, so `truth_in_bound_rate == 1.0` means "[0, +inf)
  contains the truth". `bound_cells_finite_upper` rides on every row to separate the two.
- **Leave-one-out is by POSITION, not by value**, in `metrics.probabilistic_metrics`; and
  `propensity.target_propensity` accumulates sums, not moments, so a cell's own month can be
  subtracted back out. Both are §13.4 bullet 1 at two different layers.
- **Scoreboard ranks pooled scores, never rows.** One row per (regime, seed, estimator), so a row
  argmin is an order statistic that rewards variance. Pooling is `denominator`-weighted and is an
  approximation — WAPE's own denominator (`sum|truth|`) is not on the frame. `preferred_baseline`
  (restricted to §10.8's `PREFERRABLE` rungs) is §13.10's comparand; `best_scoring_baseline` is the
  §10.1 sanity check and **gates nothing**.
- **Selectors must sort before sampling.** `unique()` and `group_by()` give no order guarantee, so
  a seeded `sample` over them is not reproducible and breaks §16.1's idempotence MUST. Two
  selectors were fixed; `cbp_size_gap_keys` (`regimes.py::cbp_size_gap_keys`-351`) still has the bug. The source
  docstrings scope it "per process" and that understates it: re-measured 2026-09-09 on the
  committed `tests/fixtures/baselines/cbp_state_size.parquet`, six consecutive `unique().sample()`
  calls in a **single** process at one seed gave six distinct key sets. It is per *call*, so a
  three-iteration in-process loop witnesses it — no subprocess needed.
- `intervals` offers CRPS and refuses log score on purpose: an empirical ensemble gives -inf
  whenever the truth falls outside its range. §13.7 permits either.

## Tests, commands, and the environment

```bash
uv run pytest tests/unit/test_validate_scoreboard.py tests/unit/test_validate_intervals.py \
  tests/unit/test_validate_metrics_point.py tests/unit/test_validate_metrics_bounds.py \
  tests/unit/test_validate_metrics_constraint.py        # 40 passed, 0.2s — no data/ needed
uv run pytest tests/integration/test_validation_golden.py   # 3 passed, 11s — in-git fixtures
uv run logging-estimates validate --config config.yaml [--estimators id,id]
```

- **Seven of the twelve `tests/unit/test_validate_*.py` modules load `data/staged` through a bare
  relative path with no `skipif`**: `complementary`, `declared_regimes`, `mask`, `propensity`,
  `recover`, `regimes`, `temporal_regimes`. Measured without `data/`,
  `pytest tests/unit/test_validate_*.py` is **34 failed, 45 passed, 0 skipped**. The *integration*
  modules that need it (`test_d1_validation.py`, `test_validate_cli.py`) do carry a `skipif`;
  `test_validation_golden.py` runs on `tests/fixtures/baselines/` and needs nothing. It also sets
  `replicates_per_regime: 3`, because at 20 the 12-month fixture trips `select_targets`' own
  lookback guard.
- **CRPS, not `run_baselines`, is the harness's dominant cost**, and it is superlinear in an
  estimator's scored-cell count. `harness.py`'s module docstring holds the measured breakdown.
  `--estimators` is the lever, and a subset gets its own run directory rather than overwriting a
  full pass.
- **`storage.output_uri` in the shipped `config.yaml` is the relative string `runs`**, resolved
  against the process CWD, so a real `validate` from the repo root writes into the checkout.
  Redirecting it to a temp dir *moves the run id* — derive the run path rather than typing it
  (`tests/integration/test_validate_cli.py::_metrics_path`).
- The dated D1 numbers this package quotes (4,716 single-cell state components, 272/400 fully
  observed state-years, the six never-observed FIPS, `runs/f03023ac9f3a`) live in the docstrings
  and in `tests/unit/test_validate_regimes.py`. Recompute before citing one.
