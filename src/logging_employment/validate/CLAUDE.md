# `validate/` — §13's pseudo-suppression harness

Hides cells QCEW actually published, re-runs the §10 baselines and rebuilds and re-solves the §9
constraint system on the masked frame, then scores the estimates against the withheld truth. Spec
map: §13.2 → `propensity` + `regimes`, §13.3 → `regimes`, §13.4 → `leakage`, §13.5-13.8 →
`metrics`, §13.10 → `scoreboard`; also §10.7 → `intervals`, §10.8 → `scoreboard`'s hierarchy
restriction, §16.2 → `harness.run_pseudo_suppression`.

## Read this first: the config knobs do not do what they look like

- **FOUR of the seven `include_*` flags gate their regime; the other three do not, and the
  difference is declared.** CORRECTED 2026-09-09 (plan 12) — this bullet used to say no flag
  decided anything, which is no longer true. `contracts.VALIDATION_SWITCH_KINDS` classifies all
  seven into three kinds, and `tests/unit/test_validation_switch_kinds.py` derives the switch set
  from `ValidationConfig.model_fields`, so a new flag fails until it is classified.
  - **regime switches** (`include_long_runs`, `include_rolling_origin`,
    `include_retrospective_smoothing`, `include_vintage_comparison`) — mapped regime→switch in
    `contracts.REGIME_SWITCHES` and read by `harness.py::run_pseudo_suppression`.
    `include_long_runs: false` now DOES stop `long_consecutive_runs` scoring. **Excluded is not
    absent**: the regime keeps its manifest entry, with a reason naming the switch. The switch is
    checked BEFORE the fail-closed refusal, so turning `include_vintage_comparison` ON still
    raises rather than returning a config-derived note.
  - **mask-label switches** (`include_primary_like`, `include_complementary_like`) — §13.2 steps 3
    and 8. They name the INV-009 LABEL a masked cell carries, not a regime, and gate no selection.
  - **design-validity operand** (`include_random_mask_sanity_check`) — read only by
    `ValidationConfig._refuse_a_random_mask_only_design`, and the ONLY flag absent from that
    validator's disjunction: it names the design §13.2 prohibits, not one of the designed regimes
    that satisfies it. No implementation, and no random-mask regime in `contracts.HOLDOUT_REGIMES`.
  Nine of the thirteen regimes have no switch at all, so the set was never a partition of §13.3.
  NO FIELD MAY BE ADDED OR REMOVED — `runs.run_id` hashes `resolved_dict` over the whole model, so
  either direction orphans every run directory.
- **`replicates_per_regime` sizes the MASK, not the loop.** It is the target count a selector
  draws; the harness loops once per entry in `pseudo_suppression_seeds`. An earlier docstring read
  it the other way and the correction is recorded in `harness.py`'s module docstring.
- **`REGIME_SPECS` is built ONCE**, at the foot of `regimes.py`, after every selector is
  registered. CORRECTED 2026-09-09 (plan 12) — it used to be built twice, and the first dict was
  always stale. `RegimeSpec.__post_init__` now refuses a spec whose mechanism, selector and reason
  disagree, which is an IMPORT-TIME invariant rather than a test: the stale first pass would raise
  at import, so deleting it was forced rather than tidying. Registering a selector without a
  matching `mechanism` is therefore no longer a silent no-op wearing a reason string — it is an
  `ConceptViolationError` before the module finishes loading.

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
- **ALL THREE persisted tables are gated, on schema AND on nullity.** CORRECTED 2026-09-09 (plan
  12) — enforcement used to be asymmetric, with `scores` ungated on the grounds that its columns
  were "a superset" of the declared schema. That was false in both directions: 23 produced against
  20 declared, 17 in common. `cli.py::validate_command` now loops over `validation_scores`,
  `validation_metrics` and `validation_scoreboard`, calling `validate_frame` and then
  `assert_required_columns_present`. The scores frame carries all 26 declared columns, `replicate`,
  `mask_arm` and `lookback_months_masked` among them.
  **The nullity pass is separate on purpose**: `validate_frame` compares names and dtypes, and
  `dict[str, pl.DataType]` has no nullability slot — which is how a NULL `mask_arm` on every
  `declines` row passed a gate it was already subject to. `contracts.VALIDATION_REQUIRED_NON_NULL`
  is a second, NARROWER declaration beside the schemas, not an extension of them; adding
  nullability to every schema in `contracts.py` is explicitly out of scope.
- **`constraint_set_hash` is null on every scored row, and that is the data, not a bug.** It rides
  in from `run_baselines`, which does not populate it on this path — measured 2026-09-09, 12,530 of
  12,530 nulls on D1. `masked_constraint_set_hash` is the one that carries a value (0 nulls) and is
  the hash of the masked system this replicate actually solved. The two are DIFFERENT columns and
  neither is a rename of the other, so neither is dropped as a duplicate; but do not read
  `constraint_set_hash` as an available join key. `VALIDATION_REQUIRED_NON_NULL` correctly omits
  it.
- **The mask arm is DERIVED from the mask, not a literal.** CORRECTED 2026-09-09 (plan 12) — every
  emit site used to pass `arm="state_total"` verbatim. `harness._mask_arm(targets)` now reads
  `MaskTarget.arm` (its first consumer anywhere in the package) and refuses a replicate spanning
  two arms, and the scores frame carries the arm PER ROW. The VALUE does not change, because every
  selector still builds `state_total` targets — which is exactly why the literal survived so long.
  `national_size` is declared in `contracts.MASK_ARMS` and implemented
  (`recover.mask_and_solve_size`, `mask.apply_size_mask`) but nothing scores it: the §10 baselines
  estimate state totals, not size classes. `scoreboard._best`'s two-arm refusal guards a future
  wiring, not a live branch. NOTE `contracts.assert_declared_provenance` still does NOT check
  `mask_arm` against `MASK_ARMS` — an open item in `specs/deferred_items.md`.
- **A regime that scores nothing must say why.** Every manifest entry with `n_scored == 0` carries
  a `reason`, pinned by
  `test_d1_validation.py::test_no_regime_reports_zero_scores_without_saying_why`. The empty
  partition reading as "scored, nothing wrong" is the failure mode this package is shaped around.

## Implemented but not wired — do not "fix" by inventing a design

- `rolling_origin` and `cbp_size_gaps` are `feasible` and legitimately score zero: neither hides a
  QCEW cell (one truncates the frame, one drops CBP state-years), so neither produces a
  `MaskTarget`. `harness` short-circuits on `spec.select is None` *before* calling `select_targets`,
  so that function's own `return []` is unreachable for them and a fix aimed there would never run.
  `specs/deferred_items.md` had the open item "Wire `rolling_origin` and `cbp_size_gaps` into the
  harness scoring loop". **CLOSED 2026-09-10 as `D-071`:** both regimes are declared-but-unscored
  BY DECISION, REQ-022 is struck from Stage 4's `Gap closed:` line, and the §13.10 gate is applied
  over nine of thirteen regimes.
  UPDATED 2026-09-09 (plan 12): each now states its OWN measured reason from
  `RegimeSpec.no_score_reason` rather than a `{name}` template shared between them (the shared one
  asserted of both that they are "exercised through their own entry point", which was true of one
  and false of the other, and shipped verbatim in `runs/f03023ac9f3a/validation_manifest.json`).
  And `rolling_origin` is no longer inert on the live path: the harness runs
  `leakage.assert_no_future_rows` at each origin from `regimes.rolling_origins` and records them as
  `origins_checked` in the manifest — seven on D1, `[]` on the 12-month fixture. READ THAT GUARD
  FOR WHAT IT IS: `_truncated` filters `reference_month < origin` and the guard refuses
  `>= origin`, so on this composition it cannot fail. Its value is as a regression detector over
  the truncation, not as an independent check, and `origins_checked` is what distinguishes a guard
  that ran nowhere from one that ran everywhere.
- `regimes.cbp_size_gap_keys` and `regimes.apply_cbp_gap` have **no production caller** in `src/`.
  They DO have a test as of 2026-09-09 — `tests/unit/test_validate_cbp_gap.py`, which pins §16.1
  idempotence across processes, the state-year grain, and the empty-key identity. CORRECTED: this
  bullet used to say "no caller and no test", and the missing test is why the nondeterminism below
  survived two sibling fixes. `propensity.complementary_partners` has no production caller either (only
  `tests/unit/test_validate_complementary.py`), and
  `scoreboard.assert_scored_cells_are_primary_like` would refuse its output. That refusal message
  names the four edits that would make a second label legal; do them, or leave it unwired.
- `retrospective_smoothing` is `vacuous_on_registry` (no smoothing estimator in §10);
  `preliminary_to_final_vintage` is `cannot_run_on_d1` (no second snapshot in any staged table) and
  *raises* from `select_targets`.
- Do not read a green run as full §13 coverage. `metrics.py`'s emitters produce exactly
  `_POINT_NAMES` (six, including §13.6's `state_share_absolute_error` since plan 14), three bound
  metrics, four coverage levels + width + CRPS + clip count, and three constraint metrics, plus —
  on the `state_total` arm only — a per-Census-division `wape` and `coverage_0.90` (R-S5G-1). So
  §13.5's infeasible-component rate and LP-vs-MILP tightening, §13.6's size-share / rank metrics,
  §13.7's calibration by state size, gap duration, propensity and distance from the nearest
  CBP anchor year (region IS covered, for 90% coverage only), §13.8's residual norms and row-sum and
  class-margin violations, and §13.9's sensitivity and ablation are **not** covered by this module.

## Invariants a fresh agent gets wrong

- **Mask the FRAME, never a hand-built `Partition`** (`mask.py` module docstring). A partition-only
  mask leaves the constraint system pinning the answer with a `fix|state_total|...` equality *and*
  leaves the truth in `context.partitions[m].missing["employment_value"]`.
- **A scored row's bounds come from `recover.mask_and_solve`, never from the run directory's
  `deterministic_bounds.parquet`** — that table still holds the published value for a cell this
  harness just hid. `MaskedSystem` is always a full rebuild, because `constraint_set_hash` is a
  stored field and `dataclasses.replace` would copy the unmasked hash onto a different system.
  **Corollary, and why this package calls `run_baselines` WITHOUT bounds** (plan 13, R-S5P-3):
  the production path checks every estimate against §9's interval and RAISES on a violation —
  **nothing clips**, `assert_within_bounds` never modifies a value. Handing the harness the RUN
  DIRECTORY's intervals would make the check's own verdict depend on the truth this harness hid,
  which is a leak in the signal. Masked bounds would not leak and **already exist** —
  `mask_and_solve` returns `MaskedSystem.bounds`, solved from the masked system, one line before
  the `run_baselines` call. So the gap is not a missing input: it is that raising is the wrong
  response on a SCORING path, where one estimator missing one interval would abort the whole run.
  That ruling is `D-087`.
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
  selectors were fixed, and `regimes.cbp_size_gap_keys` was the third — FIXED 2026-09-09 (plan 12),
  after surviving both earlier sweeps because it had no test. The defect was per *CALL*, not merely
  per process: six consecutive `unique().sample()` calls in a SINGLE process at one seed gave six
  distinct key sets on the committed `tests/fixtures/baselines/cbp_state_size.parquet`. It now
  sorts on `("state_fips", "reference_year")` between `.unique()` and `.sample()`, and
  `tests/unit/test_validate_cbp_gap.py` pins it across three processes. Any figure measured from
  that selector BEFORE the sort is unreproducible and must be re-measured, not quoted — the
  docstring's own max-|delta| number was replaced for exactly that reason.
- **The stratum pair is part of the metric key, and the board reads only `overall`.**
  `validation_metrics` rows carry `stratum_kind` / `stratum_value` — `overall`/`all` or
  `census_division`/<division> — never null. `wape` and `coverage_0.90` repeat once per division
  under otherwise identical keys, so a sort or join on the six old key fields is not total, and a
  filter on `metric_name == "wape"` alone fans out. `scoreboard.build_scoreboard` filters
  `stratum_kind == "overall"`; §13.10's stratum gates read the division rows from
  `validation_metrics`, never from the board. Each division row carries ITS division's
  `denominator` and `n_scored`, and a division COVERAGE row also its `calibration_sample_size` (WAPE
  rows carry none); the leave-one-out calibration POOL stays estimator-wide. The two families do NOT
  always share strata: `point_metrics` emits division WAPE for every estimator, while
  `probabilistic_metrics` emits division coverage only for an interval family with at least two
  scored cells (null where a division's cells never reached an ensemble). A gate reading both must
  OUTER-join them on the division.
  **`D-112`'s residual-sign defect is in the whole `probabilistic` family** — the ensemble
  adds `estimate - truth` to the estimate instead of subtracting it. It moves coverage, CRPS and
  `n_clipped_at_zero`, and `mean_interval_width_0.90` only where the zero clip binds. Do not gate on
  any of them until it lands. WAPE is unaffected. The `national_size` arm is not stratified (`state_fips = "US"`).
- `intervals` offers CRPS and refuses log score on purpose: an empirical ensemble gives -inf
  whenever the truth falls outside its range. §13.7 permits either.

## Tests, commands, and the environment

```bash
uv run pytest tests/unit/test_validate_scoreboard.py tests/unit/test_validate_intervals.py \
  tests/unit/test_validate_metrics_point.py tests/unit/test_validate_metrics_probabilistic.py \
  tests/unit/test_validate_metrics_bounds.py tests/unit/test_validate_metrics_constraint.py
  # 59 passed (measured 2026-09-12 after plan 14's review fixes; was 40 over the five modules before it) — no data/ needed
uv run pytest tests/integration/test_validation_golden.py   # 7 passed, 11s — in-git fixtures
uv run logging-estimates validate --config config.yaml [--estimators id,id]
```

- **Every `tests/unit/test_validate_*.py` module that loads `data/staged` is now guarded**
  (R-S5P-2, 2026-09-10). The seven that used to load it through a bare cwd-relative path with no
  `skipif` — `complementary`, `declared_regimes`, `mask`, `propensity`, `recover`, `regimes`,
  `temporal_regimes` — now import `STAGED` (absolute) and `requires_staged` from `tests/conftest.py`.
  Four take a module-level `pytestmark`; the three MIXED ones (`declared_regimes`, `regimes`,
  `temporal_regimes`) decorate per test, because a blanket mark there would skip five tests that
  pass in a bare checkout. *Superseded reading, so a stale citation stays recognisable:* this bullet
  used to say those seven had no `skipif` and that a dataless `pytest tests/unit/test_validate_*.py`
  was **34 failed, 45 passed, 0 skipped**. Whole-suite measurement at 4cc0dfe: **1388 passed** with
  `data/`, **1318 passed + 70 skipped + 0 failed** without. The *integration*
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
