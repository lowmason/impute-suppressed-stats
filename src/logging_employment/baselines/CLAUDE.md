# `baselines/` — the §10 transparent baselines

Ten estimators that weight each month's suppressed state cells, plus the runner that executes them
over the window and ranks what ran by §10.8's hierarchy. Built in Stage 3, consumed by Stage 4's
validation harness. Spec: `specs/logging-employment-spec.md` §10 (§10.1–10.9), output contract
§7.13, programmatic signature §16.2. Composition is elaborated in
`specs/completed/estimator-composition.md` (R-COMP-1..11), §10.3's variant-5 refusal in
`specs/completed/break-adjusted-share-refusal.md`.

Module docstrings here are ALL-CAPS-headed argument paragraphs, unusually long, and are the source
wherever this file is thin. Vocabulary: `errors.ConceptViolationError` = a concept is violated,
`errors.WeightDomainError` = the vector cannot cover the missing set, and a `Decline` is an
estimator's considered refusal — never an exception.

## What a fresh agent gets wrong

1. **Never call `interfaces.compose` from an estimator.** `__init__.py` exports it, which is a
   trap: no estimator calls it, and all seven composites go through
   `fallback.compose_with_declared_fallback` (`fallback.py::compose_with_declared_fallback`). §10.9 / R-COMP-5 require
   *exactly one* construction turning §10.2 exposure into an employees-valued arm
   (`fallback.establishment_fallback`), taking the intensity as an argument. Building or scaling a
   fallback arm inside an estimator is a spec violation, not a style choice. Verified: `compose`
   has no caller outside `fallback.py` and `tests/unit/test_baseline_interfaces.py`.
2. **Two rung structures exist and are not derived from each other.** `FALLBACK_ORDER`
   (`runner.py`) is a flat 4-tuple naming one representative per rung, used only by
   `preferred_estimator` / `preferred_estimator_by_month`. `FALLBACK_RUNGS` (`runner.py`)
   spells out full rung *membership* — rung 3 is all five §10.3 variants — and `PREFERRABLE` /
   `RUNG_OF` derive from it for `validate/scoreboard.py`'s §13.10 gate and tie-break. Adding or
   moving a rung member means editing **both**; editing one changes either the manifest's preferred
   estimator or the promotion comparand, not both.
3. **`simple.establishment_weights` omits unweightable cells, it does not zero them.** The
   omission is load-bearing: the returned domain then falls short of the missing set and
   `check_domain` refuses the month by name instead of normalizing a partial vector.
4. **Visibility comes from `context.partitions`, never from `observation_status` or from
   `qcew_monthly` values** (`historical.py::observed_share_history`, `regression.ConstrainedRegression.training_rows`).
   Caveat on the stated motive: the shipped `validate/mask.py::apply_mask` *does* null
   `employment_value` and flip `observation_status`, and `run_baselines` rebuilds partitions from
   the masked frame — so the leak `historical.py`'s docstring describes ("the held-out cell still
   carries its published value") is not live through the harness path. The rule holds as defence in
   depth, since `national_residual` takes a `Partition` so a caller *can* mask partition-only (the
   unit tests do). R-COMP-8's residual cross-check is what actually fails a mismatch:
   `fallback.py::_assert_the_partition_is_the_anchors`::_assert_the_partition_is_the_anchors`.
5. **Cite the spec by § number, never by line.** Two shipped `spec:NNN` citations have drifted:
   `interfaces.py` cites `spec:942` for §10.1's "same ... reconciliation layer" sentence, which
   now sits at spec line 977 (942 is a bare code fence); `historical.py` cites `spec:968-972` for
   §10.3's five variants, which now sit at 1003-1007 (968 is a `bound_status` bullet). Do not trust
   either number, and do not add more.
6. **A decline is a row, not an absence** (§7.13). `run_baselines` writes one null-estimate row per
   missing cell with `decline_reason` and a `decline_kind` from the closed set
   `contracts.DECLINE_KINDS` (`by_design` / `data_gap` / `reconciliation_failure`). Three call
   sites in `runner.py` produce them; the kind is keyword-only with no default on purpose, and a
   decline is a *pass* in the golden test.
7. **One prose-pin test.** `tests/unit/test_baselines_historical.py::test_the_break_adjusted_docstring_declares_its_refusal` asserts three exact
   sentences exist in `BreakAdjustedShare.__doc__` (whitespace-normalized). Rewording that
   docstring reddens the suite; the sentences being *true* is pinned by seven other tests.

## The contract at the boundary

An estimator is a `Protocol` (`interfaces.py::Estimator`) with three members: `estimator_id`,
`fallback_intensity: str | None`, and `weights(context, anchor) -> Weights | Decline`.

**An estimator returns weights, never an estimate.** `reconcile.allocate.allocate` is the only
thing that turns q into employees; that is what makes §10's "same reconciliation layer as the full
model" structural rather than stated. `allocate.check_domain` (`reconcile/allocate.py::check_domain`) refuses
any vector whose domain is not exactly `anchor.missing_cells`, or that is non-positive/non-finite,
or that lacks a per-cell `basis`.

Consumers outside this package: `validate/harness.py` imports `Estimator` and
`runner.{REGISTRY, run_baselines}`; `validate/scoreboard.py` imports
`runner.{FALLBACK_RUNGS, PREFERRABLE, RUNG_OF}`; `cli.py` imports `runner.{REGISTRY,
run_baselines, resolve_estimators, preferred_estimator, preferred_estimator_by_month}`. Nothing
outside imports an estimator class directly.

## Adding an estimator

Append to `REGISTRY` (`runner.py`) — order is canonical and `resolve_estimators` re-imposes it,
so `a,b` and `b,a` name one run. Declare `fallback_intensity` as `None` or a member of
`FALLBACK_INTENSITIES` (`fallback.py`); `resolve_intensity` refuses anything else by name,
because the value reaches `baseline_manifest.json` as a reviewable claim. Compose only via
`compose_with_declared_fallback`. Decide rung membership in both structures from gotcha 2 — an
estimator in no rung still runs and is still scored, it just cannot become §13.10's comparand.
Expect `tests/integration/test_baseline_golden.py` to redden: it asserts the result's estimator set
equals `REGISTRY`'s and pins the whole frame against a committed golden parquet. Re-pinning needs
§17.6's documented reason, in the commit that regenerates the fixture.

## Commands (repo root)

```bash
# 85 passed
uv run pytest tests/unit/test_baseline_interfaces.py tests/unit/test_baselines_*.py
# 13 passed, 5 skipped — the skips are all test_d1_baselines, which needs data/staged
uv run pytest tests/integration/test_baseline_golden.py \
    tests/integration/test_baseline_cli.py tests/integration/test_d1_baselines.py
```

`test_d1_baselines` self-skips when the gitignored `data/staged/` is absent, so a fresh clone stays
green; the golden and CLI tests run off the committed fixture in `tests/fixtures/baselines/` — 12
months of 2023, CBP reference year 2023 only, 138 result rows for each of the 10 estimators.
`harvest_proportional` (§10.5) is the only one that declines there, and it declines on **all** 138
rows with `decline_kind = by_design`: Appendix A ships `tpo.enabled=false` and `fia.enabled=false`,
so no harvest-origin volume exists and §10.5 refuses a substitute proxy. That is the fixture's
expected shape, not a data gap — do not "fix" it.

`logging-estimates run-baselines --config <path>` takes **only** `--config` (the `--estimators`
subset option lives on `validate`), gates on an existing `runs/<id>/schema_manifest.json` from
`build-constraints`, and writes `baseline_results/{baseline_results,anchor_audit}.parquet` plus a
sibling `baseline_manifest.json` carrying `preferred_estimator`, `preferred_estimator_by_month`,
`weight_basis_counts`, `declines` by kind, and each estimator's `fallback_intensity`. Do not run it
to check a change — it writes into `runs/` under the real config.
