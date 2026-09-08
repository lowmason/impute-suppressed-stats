# Stage 3 plan audit — findings

Machine audit of `specs/plans/4-stage3-logging-employment-spec.md` run before execution, on
2026-09-05. 19 of 24 planned audit units reported (19 per-task + 5 cross-cutting; the run was
stopped early — see the note at the end). Findings are raw auditor output: the adversarial
verification pass did not complete, so each is a claim to check, not a confirmed defect.

Counts: 67 total — 13 blocker, 25 defect, 29 nit.

## Disposition (added 2026-09-05, after execution)

Every finding below was raw auditor output. This section records what happened to each class of
them. **No finding was acted on without first reproducing it**, and every fix was mutation-tested
— the code was reverted and the new test confirmed to fail — so a fix that asserted nothing would
have been caught.

### Confirmed and fixed

| Task | Defect | Commit |
|---|---|---|
| 2 | Test block referenced names the file never imports | `627c736` |
| 3 | Closure audit driven by partition keys, so a national month with no state rows escaped the gate | `cc90061` |
| 3 | `fill_null(0)` a no-op, so a null in `disclosed` inflated R_t | `cc90061` |
| 3 | §5.5 warrant enumerated eight dimensions while claiming nine | `cc90061` |
| 3 | `implied_intensity` doubt-trigger fires in 96 of 96 months | `cc90061` |
| 4 | `Weights` docstring's 762/1,227 and 1,041/1,080 coverage figures | `1b480c4` |
| 5 | Float accumulation rejected the degenerate `Σ L = R_t` case | `ea784f2` |
| 5 | Null-upper test passed identically under a 1e15 sentinel | `ea784f2` |
| 6 | Non-indicator margins silently minimized a different objective | `ba63c69` |
| 6 | Degenerate branch skipped the bound clip | `ba63c69` |
| 6 | `weighted_quadratic` refusal promised in a docstring, absent in code | `ba63c69` |
| 7 | Matrix reconciliation returned non-converged margins silently | `400b19e` |
| 8 | Shrinking loop bound left units unplaced on 72% of feasible inputs | `e0e768f` |
| 9 | `max(value, floor)` turned a negative draw into a legal weight | `bb84302` |
| 9 | `general_method` guard on a path governed by `single_margin_method` | `bb84302` |
| 9 | `PosteriorDraws` cited §16.2 for a §15.4 requirement | `bb84302` |
| 10/12/13 | Composite arms in incommensurable units (one defect, three sites) | `4fb5230`, `1b480c4`, `f9700da` |
| 11 | Test asserted the opposite of its own name | `3a9c0e2` |
| 12 | NAICS-vintage test vacuous — fixture lacked a national row | `1b480c4` |
| 12 | `.tail(n)` bounded the lookback in rows, not months | `1b480c4` |
| 13 | Shrinkage test asserted unreachable unshrunk values | `f9700da` |
| 15 | Missing docstring below the `interrogate` gate; "appears twice" was once | `86f971c` |
| 16 | Three-field `cell_id` that could never join Stage 2's tables | `75934fa` |
| 16 | §10.8 hierarchy resolved once for the window rather than per month | `75934fa` |
| 16 | Integerization recheck used `assert`, which vanishes under `-O` | `75934fa` |
| 17 | `reconcile` wrote no manifest, against §16.1's MUST | `eb54ad1` |
| 17 | `weight_basis_counts` pooled across estimators | `eb54ad1` |
| 17 | `staged_repo` fixture required by five tests and defined nowhere | `eb54ad1` |
| 19 | Golden fixture sliced from gitignored `data/` at test time | `038c3af` |
| 19 | `.equals` compared emission order against a sorted golden | `038c3af` |
| 19 | `slow` claimed to exclude the D1 file; no marker filter exists | `038c3af` |
| 19 | Universe-gate assertion compared audit to results, not to the panel | `038c3af` |

### Not acted on

* **Task 1's two defects are plan-prose errors, not code.** The expected `bound_status` tally and
  the re-key literal `e04604e5dbce` are both wrong in the plan; the correct values (`observed`
  largest, run id `320caf9c8934`) were measured during execution and recorded in commit `3b54a31`
  and in the plan's Task 1 deviation note. Nothing shipped was affected.
* **Nits** were reviewed in aggregate. Those that made a docstring or comment false were folded
  into the commit for their task; the rest were judged cosmetic and left.

### Never audited

Task 18 and four of the five cross-cutting units died with the workflow. The four cross-cutting
checks — mask-signature violations, call-site arity, anti-drift in test blocks, and §17.3 vacuity
— were re-run inline by hand. Task 18 was never machine-audited; see specs/deferred_items.md.

**CORRECTION (after the whole-branch review): the mask-signature check's "clean" verdict was
wrong.** It was scoped to the plan's `reconcile/` tasks (plan lines 1084-2399), but the Global
Constraint binds *every function downstream* of `national_residual`, and the baselines are
downstream. `historical.py`'s `observed_share_history` read `observation_status` from the table
and, under a pseudo-suppression mask, returned a held-out cell's own published value through the
share. The whole-branch reviewer found it; the inline check did not. Fixed in `65c4480`.

The lesson generalises past this branch: an audit's scope is part of its result. "Clean" recorded
without the scope beside it reads as a stronger claim than was actually tested, which is the
failure mode this very document was written to prevent.

---

## Cross-task pattern worth naming

Tasks 10, 12 and 13 carry the same blocker in three places: `compose` unions an own-weight
vector with the establishment fallback vector without putting them on a common scale. §10.3's
own weights are dimensionless national shares (~1e-3), §10.4's are employees, and the fallback
is a raw establishment count (1..282). Because `allocate` normalizes by Σq, whichever arm has
the larger magnitude absorbs nearly the whole residual. Fixing this once in the composite
machinery (Task 10) is the right move; patching it per-baseline is not.

---

## Cross-cutting

### [NIT] plan:4946

**Claim.** Self-review claim 3 ("Every estimator's `weights` returns `Weights | Decline`") is not literally true — `EqualAllocation.weights` and `EstablishmentProportional.weights` are annotated `-> Weights` — but this is loose prose, not a defect: a covariant return type satisfies the Protocol. Claims 1, 2, and 4 verified clean across every site in the plan.

**Evidence.** Claim 1 (`Weights` is `(values, basis)`): definition at plan:1219-1230; every construction site (plan:1131, 1170, 1176, 1367, 2318, 2576, 2594, 2829, 2842, 4524, 4533, 4675) uses exactly those two fields in that order, and every access is `.values` / `.basis`. Claim 2 (`Anchor` is `(reference_month, residual, missing_cells, anchor_basis)`): definition at plan:733-741 and shipped verbatim in src/logging_employment/reconcile/anchor.py; all 21 construction sites in the plan (keyword at plan:972, 1122; positional at plan:1363, 2183, 2444, 2684, 2958, 2970, 3307, 3327, 3518, 3540, 3673, 3722, 4532, 4543, 4565, 4578, 4595, 4596, 4612, 4669, 4674) match the arity and order. Claim 4 (`establishment_weights` returns a bare dict): every caller — plan:2724, 2738 (tests, using `set(w)`, `w.values()`, `"38" not in w`), 2841 (`EstablishmentProportional`), 3120 (§10.3 compose), 3441 (§10.4), 3807 (§10.6) — treats it as a plain mapping; no caller accesses `.values` or `.basis` as attributes on it. Claim 3's only exceptions are the two annotations at plan:2828 and plan:2840, whose bodies return `Weights` unconditionally, so the runner's `isinstance(outcome, Decline)` branch at plan:3835 is simply never taken for them.

**Proposed fix.** No code change needed. If the Self-review note is meant to be exact, reword it to "every estimator's `weights` satisfies `Weights | Decline`; §10.1 and §10.2 narrow it to `Weights` because their inputs are complete on every suppressed cell."

## Task 1

### [DEFECT] plan:476-477

**Claim.** Step 7's "Expected" for `solve-bounds` says `unbounded` far exceeds every other `bound_status`, but `observed` is ~3x larger, so the tally the plan tells the implementer to expect cannot be produced.

**Evidence.** I ran the rebuild's output through Polars: `runs/320caf9c8934/deterministic_bounds.parquet` groups to `observed 3534`, `partially_identified 14`, `unbounded 1227`. The plan's own evidence section forces this: §3 says |D_t| = 3,489 and §1 says only 14 national size-class cells are `partially_identified`, so observed = 3,489 state cells + 37 national_size + 8 national_total = 3,534 against 1,227 unbounded (3,534 + 14 + 1,227 = 4,775 = 4,716 + 51 + 8). `cli.py:211-213` echoes the group_by tally sorted by `bound_status`, so the printed order is `observed`, `partially_identified`, `unbounded` — the first line is the largest. The `flagged N narrow, 0 exact` half of the claim is correct (measured narrow=1, exact=0).

**Proposed fix.** Replace the Expected with what the code actually prints and keep it ANTI-DRIFT-compliant: "three statuses appear — `observed`, `partially_identified`, `unbounded` — with `unbounded` equal to |M_t| computed at run time and `observed` the largest of the three; plus a `flagged N narrow, 0 exact` line."

### [DEFECT] plan:198-199

**Claim.** The stated re-key measurement `e1e20b583449 → e04604e5dbce` is wrong for the config Task 1 actually prescribes; Steps 4-5 as written produce run id `320caf9c8934`.

**Evidence.** I reproduced both ends with the shipped hasher. Old: stripping only `reconciliation` and `baselines` from `resolved_dict(cfg)` and rehashing with the current staged digests gives exactly `e1e20b583449`, so the input digests are unchanged and this is not drift. New: `run_id(load_config('config.yaml'), _input_digests)` with Step 4's + Step 5's blocks gives `320caf9c8934` — which is also the directory the rebuild actually created (`runs/320caf9c8934/`, mtime 16:17). I then bisected the discrepancy: `e04604e5dbce` is reproduced only by a config carrying Appendix A's three-key `reconciliation:` block with no `baselines:` block and none of the five originated keys (measured variants: recon-only `e81b8221cf40`, baselines-only `d3535f04ef30`, 3-key recon + baselines `a40c3f262cb1`, 3-key recon alone `e04604e5dbce`). The measurement predates the plan's final config design.

**Proposed fix.** Change the parenthetical at plan:199 to `e1e20b583449 → 320caf9c8934`, or drop the literal "after" id and say only that the directory re-keys and the new id must be read off the `build-constraints` output — otherwise an implementer who gets `320caf9c8934` and trusts the "measured" label will try to make the hash match by deleting the `baselines:` block or the five originated keys.

### [NIT] plan:205-207

**Claim.** §6 claims "an idempotence test pins" `schema_manifest.json`'s bytes. No such test exists — the safety net the plan cites to justify "never edit `schema_manifest.json`" is not in the shipped suite.

**Evidence.** `tests/integration/test_constraint_cli.py:66` and `:71` build the idempotence comparison from `sorted(run.glob("*.parquet"))` only, so the JSON manifest is never digested. `grep -rn schema_manifest tests/` returns exactly one hit, `test_constraint_cli.py:56`, which does `json.loads(...)` and asserts two keys are truthy. The precondition-gate half of the claim is real (`cli.py:194-199`), and `solve-bounds` reads the parsed JSON's `constraint_set_hash`, not "its bytes". Separately verified that the rebuild is safe: `cmp runs/e1e20b583449/schema_manifest.json runs/320caf9c8934/schema_manifest.json` reports the two files byte-identical, so the Global Constraint that `constraint_set_hash` and `data/constraints/` stay byte-identical holds. [Both run directories were retired 2026-09-08, so that `cmp` no longer runs as written. The finding stands and its witness survives: `schema_manifest.json` was byte-identical across those two and `f03023ac9f3a`, whose copy remains.]

**Proposed fix.** Drop "and an idempotence test pins them" (and the same phrasing at plan:4358), or have Task 17 add the missing assertion — extend `test_both_commands_are_idempotent_for_identical_inputs` to digest `schema_manifest.json` alongside the parquet files — before any later task relies on that guard.

## Task 2

### [DEFECT] plan:511-533, plan:539, plan:653

**Claim.** Task 2's Step 1 test block references `BASELINE_RESULT_SCHEMA` and `RECONCILIATION_STATUSES` as bare module-level names, but the file it is appended to imports the module (`from logging_employment import contracts`) and never these symbols; no step in the task adds an import, so Step 6's "Expected: PASS" is unreachable and the tests fail with the same `NameError` Step 2 predicts, even after Steps 3-5 land.

**Evidence.** `/Users/lowell/Projects/impute-suppressed-stats/tests/unit/test_contracts.py` imports exactly `import polars as pl`, `import pytest`, `from logging_employment import contracts`, `from logging_employment.errors import SchemaMismatchError` — every one of its 14 existing tests uses the `contracts.X` prefix (e.g. `assert contracts.BOUND_STATUSES == (...)`). I ran a fixture mimicking the plan's block verbatim under that import set: `uv run pytest` gives `E NameError: name 'OBSERVATION_STATUSES' is not defined` — defining the symbol inside `contracts.py` cannot bind a bare name in the test module. Ruff independently flags it: `pyproject.toml:40-42` sets only `line-length`/`src` under `[tool.ruff]` with no lint `select` override, so the default `["E4","E7","E9","F"]` applies and `uv run ruff check` on the same fixture reports `F821 Undefined name`. Corroboration: while auditing, the executor's on-disk `tests/unit/test_contracts.py:177-196` already carries `contracts.BASELINE_RESULT_SCHEMA` / `contracts.RECONCILIATION_STATUSES` on all six references — a silent deviation from the plan text that was required to make it run. Contrast the plan's own later tasks, which do import explicitly (plan:3891 `from logging_employment.contracts import BASELINE_RESULT_SCHEMA, HarmonizedData`).

**Proposed fix.** In the Step 1 block, prefix all six references with `contracts.` (matching the file's house idiom): `contracts.BASELINE_RESULT_SCHEMA` in the three assertions of the first test and the two of the third, and `contracts.RECONCILIATION_STATUSES` in the three of the second. Alternatively add `from logging_employment.contracts import BASELINE_RESULT_SCHEMA, RECONCILIATION_STATUSES` to the file's imports, but the prefix form matches every existing test in that module. Step 2's `Expected: FAIL with NameError` stays correct either way; Step 6's `Expected: PASS` only becomes reachable after this change.

## Task 3

### [DEFECT] plan:988 (code), plan:983 (docstring)

**Claim.** `closure_audit` iterates `sorted(partitions)` rather than the months present in `monthly`, so any month that has a national row but no state rows is silently absent from the audit and `assert_universe_closes` then passes vacuously on it.

**Evidence.** Reproduced against the shipped module. Frame: national rows for 2024-03 (6 estabs) and 2024-04 (999 estabs), state rows only for 2024-03. `observed_partition` yields one key, so `closure_audit(...)` returns `audit.height == 1` with `reference_month == ['2024-03']`, and `assert_universe_closes(audit)` returns cleanly — the 999-establishment national month is never gated. This violates the invariant the codebase states verbatim for the analogous function in `src/logging_employment/harmonize/universe.py:20-25`: "Every per-month mapping is keyed by every month in the frame, including the months with nothing to report. A month absent from `suppressed_state_cells_by_month` would read as 'no suppressed cells' to a caller." Stage 1 already tracks `national_row_present_by_month`, so a month with an incomplete state side is a case the package treats as reachable.

**Proposed fix.** Drive the loop from the months in `monthly` (e.g. `for month in sorted(monthly['reference_month'].unique().to_list())`) and look the partition up with a default empty `Partition`, so a month with no state rows produces `state_establishments_sum = 0`, a nonzero `establishment_gap`, and a halt. Keep `partitions` as the disclosed/missing source, not as the month index.

### [DEFECT] plan:970 (`national_residual`), plan:1004 (`closure_audit`)

**Claim.** `partition.disclosed["employment_value"].fill_null(0).sum()` reads as null handling but is a no-op — Polars' `sum()` already skips nulls — so a null-employment cell placed in `disclosed` contributes 0 instead of halting, silently inflating `R_t` in exactly the API the plan deliberately opens to arbitrary callers.

**Evidence.** `uv run python -c "import polars as pl; print(pl.Series([1,None,3]).sum())"` prints `4`, so `fill_null(0)` changes nothing. Reproduced the consequence: a `Partition` whose `disclosed` holds state 01 (employment 60) and state 02 (`observation_status='suppressed'`, `employment_value=None`), with `missing` empty and a national total of 100, returns `Anchor(residual=40.0, missing_cells=(), anchor_basis='declared_national_total')` — 40 employees with no cell to receive them and no error. This is the D_t/M_t confusion `test_the_disclosed_set_includes_true_zero_cells` exists to prevent, running in the opposite direction, and it contradicts the plan's own global constraint at plan:73-74 ("A silent NaN, a silently dropped cell, or a silently subset weight vector is forbidden"). On D1 it is inert (0 nulls among the 3,462 observed + 27 true_zero cells, measured), but Task 3's whole premise at plan:681-683 is that Stage 4 supplies its own partitions.

**Proposed fix.** Replace `fill_null(0)` with a fail-closed check in `national_residual`: raise if `partition.disclosed['employment_value'].null_count()` is nonzero, naming the offending `state_fips`. Do the same in `closure_audit`'s `disclosed_sum`. Keep `fill_null(0)` only on `qtrly_establishments`, where it is likewise a no-op but harmless.

### [DEFECT] plan:1011-1013

**Claim.** The `implied_intensity` comment installs a decision rule — drift from the disclosed states' intensity means "the completeness assumption is the first thing to doubt" — that fires in 96 of 96 months of the production window while the plan simultaneously concludes the anchor is admitted, with no stated threshold and no expected direction.

**Evidence.** Computed on `data/staged` with the shipped module: `implied_intensity` (residual / missing-set establishments) ranges 2.88–4.46, while the disclosed states' intensity (disclosed_sum / disclosed establishments) ranges 5.44–6.38. The ratio is 0.48–0.74 with median 0.58 — the implied intensity is 26–52% below the disclosed intensity in every one of the 96 months, in the same run where `establishment_gap == 0` in 96/96 and `assert_universe_closes` passes. An implementer or reviewer applying the comment as written would conclude the completeness assumption is doubtful on the entire production window. The benign reading (suppressed cells are suppressed because they are small — measured `qtrly_establishments` 1..282 on M_t vs 3..645 on D_t) is nowhere stated.

**Proposed fix.** State the expected direction in the comment — the missing set is systematically less employment-dense than the disclosed set, so a ratio below 1 is the normal case — and record the measured D1 band (roughly 0.5–0.75) as the reference, or drop the doubt-trigger sentence. If the comparison is meant to be evaluable from the artifact, add a `missing_establishments` (or `disclosed_establishments`) column to `ANCHOR_AUDIT_SCHEMA`; today it is only recoverable by inverting `residual / implied_intensity`, which is undefined whenever `implied_intensity` is null.

### [DEFECT] plan:860-864 (and the same claim at plan:88-92)

**Claim.** The module docstring's "Nine match by construction" enumeration does not cover nine of §5.5's ten dimensions: it splits one bullet into two and leaves `disclosure/noise regime` entirely unevaluated, so the module's stated §5.5 warrant does not discharge the §5.5 MUST it invokes.

**Evidence.** §5.5 (specs/logging-employment-spec.md:247-262) has exactly ten bullets: reference period; geography universe; industry code AND NAICS vintage (one bullet); ownership coverage; employment concept; statistical unit; size concept; release vintage and revision status; disclosure/noise regime; and exact/rounded/sampled/modeled. The docstring lists nine phrases — reference month, industry, NAICS vintage, ownership, employment concept, statistical unit, size concept, release vintage, exact published values — which map to only eight of those bullets (industry and NAICS vintage are one bullet), plus geography as the tenth. Disclosure/noise regime is never mentioned, and it is the dimension on which the two levels most visibly differ in the data (the national row is `observation_status='observed'` in 96/96 months while 1,227 state cells are `suppressed`).

**Proposed fix.** Add the disclosure/noise-regime dimension to the enumeration and say why it matches: both rows come from the same QCEW file under the same BLS disclosure regime, and the fact that the national cell survives suppression while 1,227 state cells do not is the project's premise, not a regime mismatch. Then the count reads correctly as nine matching bullets with geography as the tenth. Apply the same correction to the evidence section at plan:88-92.

### [NIT] plan:1048

**Claim.** The justification "It never fires on D1 (min residual 696) but Stage 4's masks reach it" is arithmetically false: a pseudo-suppression mask can only move cells from `disclosed` to `missing`, which weakly increases `R_t`, so no mask can drive the residual to zero or below.

**Evidence.** R_t' = N_t - sum over D_t' where D_t' is a subset of D_t. Every state employment value in the window is non-negative (measured: observed min 3, true_zero exactly 0, suppressed null), so sum(D_t') <= sum(D_t) and therefore R_t' >= R_t >= 696 for every month and every mask. The `residual < 0` branch of `assert_universe_closes` is unreachable from any Stage 4 partition built over this window.

**Proposed fix.** Keep the `< 0` guard (the strictness argument at plan:1044-1047 is correct and worth stating), but replace the reachability claim with the truth: masking only enlarges the residual, so this branch is unreachable on D1 and on any mask over it; it exists for a future vintage or a synthetic fixture.

### [NIT] plan:983 (docstring) vs plan:947-952 and plan:989

**Claim.** `closure_audit`'s docstring promises the audit is "written whether or not the gate passes, so a failing run leaves the evidence", but `_national_row` raises `UniverseClosureError` from inside the loop, before the DataFrame is built — and it raises the same exception type the gate raises, so a caller cannot tell a gate failure (audit present) from a malformed month (no audit).

**Evidence.** Reproduced: a frame with one state row and no national row gives `closure_audit(...)` -> `UniverseClosureError: 2024-03: expected exactly one national row, found 0`, and no DataFrame is returned. Stage 1 already treats a missing national row as possible (`national_row_present_by_month` in `src/logging_employment/harmonize/universe.py:47`).

**Proposed fix.** Either record the month as a failing audit row (national fields null, `anchored=False`) and let `assert_universe_closes` halt on it, or raise a distinct exception class for a malformed/absent national row so the two failure modes are separable by type. Narrow the docstring if neither is done.

### [NIT] plan:794 vs plan:812

**Claim.** `test_the_gate_is_evaluated_for_every_month_not_only_failing_ones`'s docstring says the assertion is on structure, "never on the gap being zero — the anti-drift rule", but the test's last line asserts `audit["anchored"].all()`, and `anchored` is defined as `establishment_gap == 0 and residual >= 0`.

**Evidence.** plan:1010 defines the column as `"anchored": national_est - state_est == 0 and residual >= 0`; plan:812 asserts `audit["anchored"].all()`. The test is harmless in practice because its inputs are synthetic, but the docstring states the opposite of what the code does, and the anti-drift rule is a global constraint (plan:44-49) a later reader will apply.

**Proposed fix.** Either drop the `anchored` assertion and keep only the structural ones, or amend the docstring to say the gap-zero assertion is safe here because the fixture is synthetic; the anti-drift rule binds assertions on live data.

### [NIT] plan:815-816 vs plan:972-977; plan:667

**Claim.** `test_a_month_with_no_missing_cells_yields_no_anchor` and its docstring ("a month that needs no anchor") contradict the code, which unconditionally returns an `Anchor` labelled `anchor_basis='declared_national_total'`; and the Interfaces block declares `ANCHOR_BASES` consumed from Task 2 while the module never imports it, hardcoding the string instead.

**Evidence.** plan:976 sets `anchor_basis=DECLARED_NATIONAL_TOTAL` on every return path, including the empty-missing-set path the test exercises; running the shipped code on that fixture returns `Anchor(residual=0.0, missing_cells=(), anchor_basis='declared_national_total')`. plan:667 lists `ANCHOR_BASES` under Consumes, but the code block at plan:893-895 imports only `ANCHOR_AUDIT_SCHEMA` and `UniverseClosureError` and defines `DECLARED_NATIONAL_TOTAL` locally.

**Proposed fix.** Rename the test to what it checks (an empty missing set yields a zero residual, not "no anchor"), or return `anchor_basis` from `ANCHOR_BASES`' `'none'` when `partition.missing` is empty. Either way, import the constant from `contracts` rather than re-declaring the literal, or drop `ANCHOR_BASES` from the Consumes list.

## Task 4

### [DEFECT] plan:1224 (source row plan:171)

**Claim.** The `Weights` docstring in `allocate.py` states §10.4 runs "1,041/1,080" own-weight over its 84 covered months; that ratio is arithmetically impossible given the plan's own §10.4 facts, and the measured figure is at most 918/1,080.

**Evidence.** Internal arithmetic: 1,080 − 1,041 = 39 fallback cells, but the same table row (plan:171) says the §10.4 fallback is "186 cells (HI, RI)", and 1,041 = 1,227 − 186 — a whole-window numerator paired with a covered-window denominator. Measured against the shipped staged data (`uv run python` over `HarmonizedData.load(Path('data/staged'))`): 1,227 suppressed state cells total; 1,080 of them fall in 2017-01..2023-12 (the CBP-covered months); 162 of those 1,080 belong to state_fips '15' (HI) or '44' (RI), and `cbp_state_size` carries rows for 48 states, neither of them. Since the plan itself says HI/RI have no CBP row in any published year, at least 162 of the 1,080 covered-window cells must take the §10.2 fallback, so own-weight ≤ 918/1,080 — 1,041 is unreachable. (186 is the HI+RI count over all 96 months, confirmed by the same query.)

**Proposed fix.** Replace "1,041/1,080" with the covered-window figure (≤918/1,080), or better, drop the numerals — the docstring only needs to say that §10.4 composes and therefore needs a per-cell basis; the ANTI-DRIFT rule forbids typing counts into source at all. The same wrong pairing is in the evidence table at plan:171 and belongs to Task 13's auditor.

### [DEFECT] plan:1223 (source row plan:170)

**Claim.** The same docstring states §10.3 runs "762/1,227" own-weight; 762 counts states that have any observed month anywhere in the window, which contradicts the lookback rule Task 12 actually ships — under that rule only 360/1,227 cells get an own weight.

**Evidence.** Task 12's `observed_share_history` (plan:3072-3086) filters `observation_status == 'observed'` AND `reference_month < before` (with `before=anchor.reference_month`, plan:3106) AND, when `historical_may_cross_naics_vintage` is false — the declared default at plan:406-408 and plan:447-448 — `naics_vintage == vintage` where `vintage = _vintage_at(monthly, anchor.reference_month)`. So a cell has own weight only if its state has a strictly-prior observed month in the SAME NAICS vintage. Measured on staged `qcew_monthly`: cells whose state has any prior observed month in the same vintage = 360; allowing the vintage crossing = 546; ignoring time order entirely (state observed anywhere in the window) = 762. Only the last matches the plan's number, and that is not the rule the plan adopts. 360 is itself an upper bound, since `_reduce` further drops cells whose reduced share is null or ≤ 0.

**Proposed fix.** Drop the numerals from the docstring (preferred, per the ANTI-DRIFT rule) or state ≤360/1,227 under the default `historical_may_cross_naics_vintage: false`. The evidence table at plan:170 carries the same pre-rule measurement and should be re-measured under Task 12's rule by Task 12's auditor — this also affects the §10.8 rung-population argument at plan:174-179.

### [NIT] plan:1277

**Claim.** Step 4's Expected line says "PASS, all eight tests (the parametrized one counts three)"; pytest collects nine.

**Evidence.** I extracted the Task 4 test block (plan:1110-1183) and the `allocate.py` block (plan:1194-1271) verbatim into a shadow copy of the package with stub Task 2/3 symbols and ran them: `9 passed in 0.05s` — six plain test functions plus the three-case parametrization. The block has 6 non-parametrized tests (`sums_exactly`, `missing_a_cell`, `extra_cell`, `zero_residual`, `empty_missing_set`, `declared_composite`), not 5.

**Proposed fix.** Change "all eight tests" to "all nine tests". Everything else in the step is correct — Step 2's expected `ModuleNotFoundError: No module named 'logging_employment.reconcile.allocate'` reproduces exactly, and every numeric assertion in the block follows from its inputs (100 over weights 1/2/1 → 25/50/25; residual 0 → all values exactly 0.0).

### [NIT] plan:1183

**Claim.** `test_a_declared_composite_is_permitted_and_its_basis_survives` cannot fail for the reason its name states: the final assertion re-reads the input object, and `allocate` returns `dict[str, float]` carrying no basis at all.

**Evidence.** `assert weights.basis["04"] == "establishment_fallback"` asserts on the `Weights` literal constructed four lines above; nothing about `out` is checked for provenance, and `allocate`'s return annotation (plan:1258) is `dict[str, float]`, so there is no basis to survive. The test would still pass if `allocate` discarded or corrupted every basis. The preceding two lines (`check_domain` does not raise; the sum is 100.0) are what actually carry the test.

**Proposed fix.** Either drop the trailing assertion as decorative, or make it non-vacuous by asserting the surviving structure the runner depends on — e.g. `assert set(out) == set(weights.basis)` — so the test fails if the allocation and the provenance map ever diverge.

## Task 5

### [DEFECT] plan:1431-1435

**Claim.** `test_a_null_upper_bound_is_infinite_and_never_becomes_a_number` has zero detection power against the thing it names: it passes unchanged if `Bounds.upper_of` coerces a null upper to a large finite float, which is exactly the "arbitrary top-class cap" the Global Constraints and §9.3 forbid.

**Evidence.** I extracted Task 4's `allocate.py` and Task 5's `scaling.py` + `test_scaling.py` verbatim from the plan into a scratch package (with an `Anchor` matching Task 3's field order and the Task 2 error classes) and ran pytest: 9 passed. I then mutated the single line `return math.inf if value is None else float(value)` to `return 1.0e15 if value is None else float(value)` and re-ran: still `9 passed in 0.01s`. The test's only assertion is `clipped_sum(1e12, weights{1.0,1.0}, open_bounds, cells) == pytest.approx(2e12)`; under the 1e15 cap the clip evaluates `min(max(1e12*1.0, 0.0), 1e15) = 1e12` per cell, so the sum is still exactly 2e12 and the assertion holds. Any finite sentinel at or above 1e12 (1e15, 1e30, `sys.float_info.max`) survives. Corroborating tell: the test module imports `math` at plan:1349 and never uses it anywhere in the file (`ruff check` on the extracted file reports `F401 'math' imported but unused`) — the intended `isinf` assertion was evidently dropped and the import left behind. The docstring at plan:1432 states the guarantee the assertion does not deliver: "a null upper must stay open, not become a big float."

**Proposed fix.** Assert the representation directly rather than a downstream sum. Replace the body's assertion (or add ahead of it) with `assert math.isinf(bounds.upper_of("01"))` — which consumes the otherwise-unused `math` import and fails on every finite coercion. Keep the `clipped_sum(1e12, ...) == approx(2e12)` line only as the behavioural companion.

### [NIT] plan:1541-1545, 1552-1553

**Claim.** The strict `if lower_sum > anchor.residual: raise` is evaluated *before* the `math.isclose(lower_sum, anchor.residual, abs_tol=tolerance)` early return, so the tolerance can only rescue an undershoot; a float-rounding overshoot of `Σ L` over `R_t` raises `InfeasibleResidualError` on precisely the degenerate case the task's own prose says MUST succeed.

**Evidence.** The task spends a labelled paragraph on it (plan:1327-1330): "`R_t = Σ L` is FEASIBLE. The degenerate case where every cell sits at its lower bound MUST succeed." Reproduced against the verbatim extracted `scaling.py`: seven cells with `lower = 0.1` each and `residual = 0.7` — mathematically `Σ L = R_t` exactly — gives `sum(lower.values()) = 0.7000000000000001`, so `lower_sum > anchor.residual` is True and the call raises `2024-03: summed lower bounds 0.7000000000000001 exceed residual 0.7; §12.3 forbids approximating this away`. The `isclose(..., abs_tol=1e-9)` at plan:1552 would have accepted it but is unreachable, sitting eight lines below the raise. (Control: three cells at `lower = 0.1/0.2/0.3` with `residual = 0.6` sums to exactly 0.6 and succeeds — the failure is summation-order dependent, not universal.) Latent on everything the plan itself generates: D1's `selected_lower` is 0.0 on all 1,227 cells, and Task 18's `test_property_3b` fixture uses `dict.fromkeys(cells, 10.0)` with `residual=30.0`, which is exact in binary. Reachable from Stage 4 masks or any generator that computes `R_t` by a different summation path than `Σ L`.

**Proposed fix.** Hoist the equality test above the strict raises: evaluate `if math.isclose(lower_sum, anchor.residual, rel_tol=0.0, abs_tol=tolerance): return {cell: bounds.lower[cell] for cell in cells}` (and the symmetric `upper_sum` equality, if wanted) before `if lower_sum > anchor.residual: raise`, so the originated tolerance governs the boundary in both directions rather than only on undershoot.

## Task 6

### [DEFECT] plan:1617-1619, plan:1712-1715

**Claim.** Task 6's prose and the module docstring both state that this task's code raises `NotImplementedError` for `general_method='weighted_quadratic'`, but the Step 3 code block contains no raise and `kl_project` never sees the config at all.

**Evidence.** plan:1618-1619 says "this task implements `kl_projection` only and leaves `weighted_quadratic` unimplemented, raising `NotImplementedError` naming the config key", and the docstring at plan:1714-1715 says "the code path raises rather than quietly running KL under a different name". The code at plan:1730-1762 has no `raise` and no `method`/`config` parameter — the signature is `(seed, margins, targets, *, lower, upper, floor, tolerance, max_iterations)`. `grep -n NotImplementedError` over the whole plan returns exactly one reconciliation guard, at plan:2303-2306, inside Task 9's `reconcile_draws`. Task 7's `reconcile_matrix` calls `kl_project` directly (plan:1920-1929) with no method check, and `general_method` is a legal `Literal["kl_projection", "weighted_quadratic"]` (plan:381), so with that config value the matrix path silently runs KL — the exact outcome the docstring claims is prevented.

**Proposed fix.** Either reword the docstring paragraph to say the version-marker guard lives at the `reconcile_draws` entry point (Task 9) and note the matrix path is unguarded, or make the claim true here: add a `method: Literal["kl_projection", "weighted_quadratic"]` keyword to `kl_project` that raises `NotImplementedError` naming `reconciliation.general_method`, and have Task 7 pass `config.reconciliation.general_method` through.

### [NIT] plan:1753-1757

**Claim.** The `current <= 0.0` branch's comment describes a case that cannot reach it, and the branch `continue`s past the `np.clip`, so on the only input that does reach it the function returns a vector violating `upper`.

**Evidence.** The comment says "Every touched cell is at the floor; a multiplicative update cannot move them". That is false: with a non-negative margin row and `x >= floor > 0` (guaranteed by plan:1742 and the clip at plan:1759), `current = row @ x >= floor * k > 0`. Ran it: `kl_project([0.0, 0.0], [[1,1]], [10.0], floor=1e-12)` returns `[5., 5.]` via the multiplicative path — the branch is never entered. The branch is reachable only for a margin row with negative coefficients, and because it `continue`s before line 1759 the clip is skipped: `kl_project([1.0, 5.0], [[1., -1.]], [10.0], lower=[0,0], upper=[2,2])` returns `[5., 5.]`, violating `upper`. Separately, `x[touched] = target / touched.sum()` divides by a cell count, so for any row with non-unit coefficients it does not satisfy `row @ x == target`. No in-plan call site passes a signed row (Task 7 builds 0/1 incidence rows at plan:1908-1919), so this is latent, not live.

**Proposed fix.** Delete the branch — it is unreachable for the 0/1 incidence margins this stage uses. If it is kept, move `x = np.clip(x, np.maximum(lower, floor), upper)` below the `if/else` so both paths clip, and fix the comment to name the actual trigger (a margin row with negative coefficients).

### [NIT] plan:1702-1703

**Claim.** The docstring's claim that the update "is exactly IPF and converges to the I-projection" holds only for 0/1 incidence margins, while the signature accepts arbitrary float coefficients.

**Evidence.** The I-projection onto a single hyperplane `Σ a_i x_i = t` is `x_i = x̃_i · exp(λ a_i)`; the code's update (plan:1758) is the uniform scaling `x[touched] *= target / current`, which equals `exp(λ a_i)` only when every nonzero `a_i` is the same value. For `a = [2, 1]` the uniform scaling still lands on the hyperplane (`c·(2s₁+s₂) = t`), so the function converges to a feasible point but not the I-divergence minimizer — a silently different objective, which is what the docstring's `weighted_quadratic` paragraph says must not happen. Every call site in the plan builds 0/1 rows (plan:1908-1919), so nothing is wrong today.

**Proposed fix.** State the restriction in the docstring ("the multiplicative update is the I-projection only for 0/1 incidence rows; margins MUST be indicator rows"), or assert `np.isin(margins, (0.0, 1.0)).all()` at entry so a later stage cannot pass weighted margins and get a non-KL answer.

## Task 7

### [BLOCKER] plan:1874, 1897-1903, 1922-1932 (specs/plans/4-stage3-logging-employment-spec.md)

**Claim.** `reconcile_matrix` silently returns a matrix whose row sums do not equal `row_totals` whenever the seed's zero pattern differs across rows — the only feasibility check is the up-front `sum(row_totals) == sum(column_totals)` test, and nothing verifies the achieved margins before returning, so §12.5's "fail and diagnose rather than forcing convergence" is not enforced.

**Evidence.** I extracted plan:1697-1762 (`projection.py`) and plan:1863-1932 (`matrix.py`) verbatim into a scratch package and ran them under the repo's interpreter. All four Task 7 tests pass, so "Expected: PASS, all four tests" is true — but the guarantee is not. `reconcile_matrix(np.array([[0.0, 3.0], [2.0, 0.0]]), np.array([10.0, 20.0]), np.array([25.0, 5.0]), tolerance=1e-9, max_iterations=1000, floor=1e-12)` returns `[[1.04e-11, 5.0], [25.0, 2e-12]]` — row sums `[5.0, 25.0]`, not `[10.0, 20.0]` — with no exception. The margins pass the plan's own consistency check (both sum to 30) AND are feasible: `[[7.5, 2.5], [17.5, 2.5]]` satisfies rows `[10, 20]` and columns `[25, 5]` exactly. Mechanism (instrumented): the floor pins the zero cells at 1e-12, their multiplicative updates move them only at ~1e-10 magnitude, and the large cells return to the same values each pass — so `kl_project`'s break test `np.max(np.abs(x - previous)) <= tolerance` (plan:1762), which tests STEP SIZE rather than constraint violation, fires on iteration 2 with rows off by 150%. This directly contradicts spec:1342 ("For each state-month, row sums must equal reconciled state totals") and matrix.py's own docstring at plan:1874, which asserts the up-front check prevents the loop from returning "whichever half-step the iteration cap happened to stop on"; the sum check catches only SUM inconsistency, not non-convergence. Scale: over 200 random 4x3 seeds at 40% sparsity (normal for a state x size-class grid) with consistent, feasible margins, 6 silently violated their margins, worst violation 9.76 jobs. Negative control, so the trigger is stated precisely: the plan's own test-4 seed `[[0.0, 0.0], [1.0, 1.0]]` combined with test-2's columns `[12.0, 18.0]` DOES work (returns `[[4, 6], [8, 12]]`) — a row-uniform zero pattern is harmless; a zero pattern that differs across rows is not. No test in the plan can catch this: Task 7's only two-margin test uses the all-positive seed `[[1, 3], [2, 1]]`, and Task 18's §17.3 property 5 (plan:4638) draws `seed = rng.uniform(0.1, 10.0, size=(rows, cols))`, strictly positive, so it never enters the regime. The task is marked green with the defect shipped, and Stage 6 — whose state x size-class seeds will certainly contain zeros, as Task 7's own zero-seed test anticipates — inherits it.

**Proposed fix.** In `matrix.py`, after `flat = kl_project(...)` and before `return flat.reshape(...)`, verify the achieved margins and raise rather than return a non-converged result. Task 7's own Interfaces block (plan:1786) already declares the task consumes `constraint_violation`, but the code never imports it — the plan named the exact function needed and then omitted the check. Add `from .projection import constraint_violation, kl_project`, then: `A = np.vstack(margins); b = np.array(targets); violation = constraint_violation(flat, A, b)` and raise if `violation > max(tolerance, 1e-6) * max(1.0, float(np.abs(b).max()))`, with a message reporting the achieved vs. requested margins and the iteration count. Raise `SolverError` (shipped, `src/logging_employment/errors.py:54`), NOT `IncompatibleMarginError` — the margins are compatible; the solver failed to converge, and `IncompatibleMarginError`'s shipped docstring is scoped to the §5.5 compatibility gate (INV-007). Root cause is shared with Task 6 (`kl_project` breaks on step size, plan:1762) but the guarantee is Task 7's to make, so the post-check belongs in `matrix.py`. Add a regression test to `tests/unit/test_matrix.py` using the `[[0.0, 3.0], [2.0, 0.0]]` / `[10, 20]` / `[25, 5]` case, asserting either exact margins or a raised `SolverError` — never a silent wrong answer.

## Task 8

### [BLOCKER] plan:2091 (and its guard at plan:2098-2101)

**Claim.** The remainder-distribution loop's termination bound `index < len(order) * (remaining + 1)` recomputes `remaining` on every iteration, so the bound shrinks as units are placed; once any cell is skipped for sitting at its integer upper bound, the loop exits with units still unplaced and `integerize` raises `ValueError("... could not be placed without breaching an integer upper bound")` on inputs that are perfectly feasible — defeating §12.6 step 4, the only reason the `upper` parameter exists.

**Evidence.** I extracted the plan's `integerize.py` (plan:2038-2102) and its test file (plan:1975-2027) verbatim to /tmp/aud8 and ran them: all seven of the task's own tests PASS, so nothing in the task catches this. Then I ran a randomized scan over 11,966 *feasible* bounded inputs (feasibility checked independently: sum(floors) <= total <= sum(floors)+capacity): the plan's code raised on 8,628 of them (72.1%). Minimal reproductions: `integerize({'01':0.0,'02':0.0,'03':10.0}, total=13, upper={'01':0,'02':0,'03':None})` -> raises "1 unit(s) could not be placed" although cell 03 is uncapped; `integerize({'01':2.2,'02':2.2,'03':2.2,'04':2.2,'05':2.2}, total=15, upper={'01':2,'02':2,'03':2,'04':None,'05':None})` -> raises "1 unit(s)". Hand-trace of the first: base=10, remaining=3, order=['01','02','03']; idx0/1 skip the capped cells, idx2 places (remaining 2), idx3/4 skip, idx5 places (remaining 1), then at idx6 the bound is len(order)*(1+1)=6 and `6 < 6` is False, so the loop exits with a unit unplaced. It also fires with no caps at all when `total` exceeds sum(values) by more than ~len(values): `integerize({'01':0.0}, total=10)` raises "4 unit(s) could not be placed". Task 9 (plan:4127) calls `integerize(allocated, total=integer_total)` with no `upper`, and Task 18's property 6 (plan:4649-4656) builds values that sum exactly to `total` with no bounds, so neither call site exercises the broken branch — this ships green.

**Proposed fix.** Hoist the bound above the loop so it is computed once from the initial remainder: insert `limit = len(order) * (remaining + 1)` after `index = 0` and change the condition to `while remaining > 0 and index < limit:`. Verified drop-in: with that single change the same randomized scan succeeds on all 11,966 feasible cases (0 failures), and all seven of the task's own tests still pass unchanged (including test 4, whose binding cap on '01' still yields {'01':4,'02':3,'04':3}).

### [NIT] plan:1956 vs plan:1957 and plan:2056-2062

**Claim.** The Interfaces block declares `Consumes: ReconciliationConfig.integerization_tiebreak`, but the `Produces` signature has no config parameter and the module body never reads config — the tie-break is hardcoded in the sort key.

**Evidence.** plan:1956 says `- Consumes: \`ReconciliationConfig.integerization_tiebreak\`.` The signature at plan:1957-1958 and the definition at plan:2056-2062 are `integerize(values, total, *, lower=None, upper=None)` — no config argument. `grep -n integerization_tiebreak` shows the field exists in shipped code (src/logging_employment/config.py, `Literal["largest_remainder"] = "largest_remainder"`) and is validated by a Task 1 test (plan:351), but nothing in Task 8 reads it. Behaviour is unaffected because the Literal admits one value; the risk is that an implementer following the Interfaces line adds a required `config` parameter, which would break Task 9's call `integerize(allocated, total=integer_total)` at plan:4127.

**Proposed fix.** Drop the `Consumes:` line, or restate it as "the hardcoded ordering realises `integerization_tiebreak = 'largest_remainder'`; the function takes no config argument" so the signature and the interface note agree.

### [NIT] plan:1965-1966

**Claim.** The motivating arithmetic in the task prose is wrong: three cells at 3.4 sum to 10.2, not 10.

**Evidence.** plan:1965-1966 reads "three cells at 3.4 each round to 9, not the 10 they summed to". 3.4 * 3 = 10.2. The shipped module docstring (plan:2041-2042) states the same example correctly — "three cells at 3.4 rounded independently give 9" — without asserting a sum, and the test at plan:1985 uses 3.4 + 3.3 + 3.3 = 10.0, so no test asserts anything false; only the prose types a number that does not follow.

**Proposed fix.** Change the prose to match the test that illustrates it: "three cells at 3.4, 3.3 and 3.3 round to 9, not the 10 they summed to" (or say "10.2").

## Task 9

### [DEFECT] plan:2319-2323

**Claim.** The `max(float(value), config.zero_seed_floor)` seed floor silently rescues *negative* draws, not just zero draws, so an out-of-domain posterior draw is converted into a legal weight and reconciled away with no signal — and the comment two lines above says the floor exists only for "a raw draw of exactly 0".

**Evidence.** I ran the plan's code verbatim (scratch reimplementation of Tasks 3/4/5/9, Python 3.14 / numpy 2.5.2). With `values=np.array([[-300.0, 2.0, 1.0]])`, residual 100, open bounds, `reconcile_draws` returns `[[3.33e-11, 66.67, 33.33]]` summing to 100.0 — the -300 vanishes with no error. `max(-5.0, 1e-12) == 1e-12` confirms the coercion. The comment at plan:2319-2320 claims the floor's only job is "§12.2 requires positive raw weights, and a raw draw of exactly 0 is not one", and spec:1337 (§12.4) authorizes only "a small positive floor for zero raw seeds" — nothing about negatives. `check_domain` (plan:1220-1234) refuses non-finite and non-positive weights, so NaN and +inf draws *are* caught; only negatives slip through, because the floor is applied before the guard sees them. This also contradicts the plan's own Global Constraint at plan:70 ("A silent NaN, a silently dropped cell, or a silently subset weight vector is forbidden").

**Proposed fix.** Guard negatives explicitly before flooring, e.g. inside the dict comprehension's producing loop raise a named error (`WeightDomainError`) when `value < 0.0`, and apply `max(value, config.zero_seed_floor)` only to values already known to be `>= 0.0`. Then either keep the comment as written or extend it to state that negatives are refused rather than floored.

### [NIT] plan:2281

**Claim.** The `PosteriorDraws` docstring attributes the draw/chain index-preservation requirement to §16.2; the requirement is actually §15.4, and §16.2 contains no storage language at all.

**Evidence.** specs/logging-employment-spec.md:1635-1637 — "### 15.4 Posterior draws ... The storage must preserve draw, chain, state, month, and size indexes." §16.2 runs from spec:1667 to spec:1692 and contains only the `ConstraintSystem` Protocol, the five function stubs (including `reconcile_draws`), and the sentence about PPL-specific objects staying behind model interfaces — no store, no index requirement. The docstring as written would ship a false citation into `src/logging_employment/reconcile/draws.py`.

**Proposed fix.** Change the docstring to `"""Joint draws over cells, with the chain and draw indexes §15.4's store must preserve."""` (spec:1637).

### [NIT] plan:2303-2308

**Claim.** The `weighted_quadratic` refusal is attached to `general_method`, a setting `reconcile_draws` never consults — the function always takes the §12.3 single-margin `scale_into_bounds` path — so a legal config value disables draw reconciliation for the wrong reason while leaving the objective it actually governs unguarded.

**Evidence.** `reconcile_draws` reads `config.general_method` only in the guard at plan:2303; the body then calls `scale_into_bounds` (plan:2326-2332), which is §12.3 bounded proportional scaling, i.e. `config.single_margin_method`. `general_method` governs §12.4/§12.5 (spec:1320-1348), implemented in `projection.py`. The shipped `ReconciliationConfig` admits the value (`general_method: Literal["kl_projection", "weighted_quadratic"]`, src/logging_employment/config.py:115, already committed at 3b54a31), so setting `general_method: 'weighted_quadratic'` in config.yaml makes every `reconcile_draws` call raise NotImplementedError even though no general-method projection is performed. Meanwhile Task 6's prose (plan:1618-1622) says the raise belongs in `projection.py` — "this task implements `kl_projection` only and leaves `weighted_quadratic` unimplemented, raising `NotImplementedError` naming the config key" — but the `projection.py` code block at plan:1712-1778 contains no such raise and `kl_project` takes no config, so `kl_project` would still run KL silently under the `weighted_quadratic` label.

**Proposed fix.** Move the `NotImplementedError` into `projection.py` where `general_method` is actually consulted (give `kl_project` the check, or add a thin dispatcher), and drop it from `reconcile_draws`. If a guard is wanted in `reconcile_draws`, key it on `config.single_margin_method`, which is the setting that path implements.

## Task 10

### [BLOCKER] plan:2557-2594 (esp. 2592), prose at plan:2502-2510

**Claim.** `compose` unions the own-weight vector and the establishment-fallback vector without putting them on a common scale, so `allocate`'s normalization (E = R·q/Σq) is dominated by whichever arm happens to have the larger units; on §10.3 the fallback arm outweighs the own arm by ~4 orders of magnitude and the own-weighted cells receive essentially zero employment.

**Evidence.** The code is unit-blind: `values = dict(usable) | {cell: fallback[cell] for cell in gaps}` (plan:2592), and `allocate` (plan:1265-1270) normalizes across that union. The two arms are in different units by construction: Task 12's `_ShareBaseline` passes own weights that are shares of the national total (plan:3086, `employment_value / national_value`, O(1e-3)), while the fallback is `establishment_weights`, raw `qtrly_establishments` (Task 11, plan:2790-2800; measured range 1..282). I ran the real composition on data/staged/qcew_monthly.parquet for LastObservedShare. 2024-03: R_t = 1589, |M_t| = 13, own cells {08: 0.00292, 46: 0.00185, 49: 0.00075, 55: 0.01557}, gaps get establishment counts {02:16, 09:3, 15:2, 32:1, 33:77, 34:2, 35:9, 44:2, 50:72}. Σq = 184.02, of which the own arm contributes 0.021 (0.011%). Result: WI (55), whose last observed share implies 0.01557 × 41,668 ≈ 649 employees, is allocated 0.134 employees; the four own cells together get 0.18 of the 1,589 residual while the nine fallback cells absorb 99.99%. Over the whole 96-month window the own-weighted §10.3 cells receive 9.6 employees in total against a share-implied 57,431 (ratio 0.000167; worst month 2017-12 at 7e-5). The same defect biases the §10.8 rung-1 estimator in the other direction: Task 13's own weight is intensity × exposure (plan:3438-3442), so on a ~5.4 employees-per-establishment universe (41,668/7,684, 2024-03) the fallback cells — HI and RI, the exact cells the composite exists to cover — get ~1/5.4 of the weight per establishment that own cells get. Task 10's own test block never exercises scale: `test_partial_own_coverage...` uses own {1.0, 2.0} against fallback 7.0, all the same order of magnitude, so it passes while hiding the bug.

**Proposed fix.** Make `compose` scale-invariant instead of unit-blind. Rescale the fallback block into the own arm's units before the union — e.g. k = (Σ_{c∈usable} own[c]) / (Σ_{c∈usable} fallback[c]) computed over the cells where both are defined (falling back to an all-fallback vector when `usable` is empty, which is already the §10.6 path), then use k·fallback[cell] for the gap cells. Add a property test that the composed allocation is invariant when the own vector is multiplied by any positive constant (own → 1000·own must not change any cell's estimate); the current implementation fails that test, and it is the check that would have caught this. Whatever normalization is chosen, state it in the docstring and record the scale factor in the manifest alongside the weight_basis counts, since it is a modeling decision the spec does not supply.

### [NIT] plan:2564, 2569-2573, 2588-2591

**Claim.** The docstring promises "Own weight where it is positive and finite" but the code tests only positivity, so a non-finite own or fallback weight passes `compose` and detonates later inside `check_domain` with a message that blames the domain rather than the estimator.

**Evidence.** `usable` filters on `value is not None and value > 0.0` (plan:2571-2573) with no `math.isfinite`, and the fallback coverage test is `fallback.get(cell, 0.0) <= 0.0` (plan:2588), which is False for both inf and NaN. I ran it: `compose({'01': inf, '02': 2.0, '04': 3.0}, ...)` returns a Weights carrying inf, and the failure only surfaces one call later in Task 4's `check_domain`, which does test `math.isfinite` (plan:1246-1256) and raises "§12.2 requires positive raw weights; non-positive or non-finite at ['01']". A NaN own weight, by contrast, silently routes to the fallback rung because `nan > 0.0` is False — that is the intended-looking behavior, but it is undocumented and inconsistent with the inf path.

**Proposed fix.** Add `and math.isfinite(value)` to the `usable` comprehension and `math.isfinite(fallback.get(cell, 0.0))` to the coverage test (importing `math`), so a non-finite own weight falls back exactly like a non-positive one and a non-finite fallback is reported by `compose`'s own WeightDomainError naming the estimator's month.

### [NIT] plan:2408, 2414-2415

**Claim.** The task's Interfaces block contradicts its own code: it declares `compose(...) -> Weights` and lists `WEIGHT_BASES` and `BaselinesConfig` as consumed, while the code returns `Weights | Decline` and imports neither symbol.

**Evidence.** plan:2414-2415 declares `-> Weights`, but plan:2557-2563 declares `-> Weights | Decline` and `test_composition_refused_by_config_yields_a_decline_not_a_silent_subset` (plan:2465-2469) asserts `isinstance(out, Decline)`. plan:2408 lists `WEIGHT_BASES` and `BaselinesConfig` as consumed; `interfaces.py` instead hardcodes `OWN = "own_estimator"` / `FALLBACK = "establishment_fallback"` (plan:2515-2516) and imports the whole `Config` (plan:2523). The literals do currently match Task 2's `WEIGHT_BASES = ("own_estimator", "establishment_fallback", "none")` (plan:562), so nothing is wrong today — but the duplication is exactly the drift the `weight_basis` column exists to prevent.

**Proposed fix.** Correct the Interfaces block to `-> Weights | Decline`, and either import `WEIGHT_BASES` from `contracts` and derive `OWN`/`FALLBACK` from it (`OWN, FALLBACK, NONE = WEIGHT_BASES`) or drop `WEIGHT_BASES`/`BaselinesConfig` from the Consumes list so it matches what the module actually depends on.

## Task 11

### [DEFECT] plan:2729-2739

**Claim.** The test named `..._is_not_silently_dropped`, whose docstring says the cell "must surface, not vanish from the weight vector", asserts the exact opposite — that the cell vanishes from the weight vector — and never exercises the code path that actually surfaces it, so §10.2 ships with no coverage of the partial-weight-vector refusal.

**Evidence.** I reconstructed Tasks 3, 4, 10 and 11 verbatim from the plan's code blocks against the shipped `contracts.py`/`errors.py`/`config.yaml` (Tasks 1–2 are already committed at 3b54a31/627c736) and ran the block: all 4 tests pass. Hand-executing this one: `make_monthly` emits only state `01`; `_anchor(("01","38"))`; `establishment_weights` returns `{'01': 4.0}` (I ran it — printed `weights: {'01': 4.0}`). The assertion `assert "38" not in weights` is therefore TRUE, i.e. the test passes precisely because "38" DID vanish from the weight vector — which is what the docstring forbids. The surfacing actually happens one layer up, in Task 4's `check_domain` (plan:1226-1233): I ran `allocate(anchor, EstablishmentProportional().weights(ctx, anchor))` on the same inputs and got `WeightDomainError: 2024-03: weight domain does not match the missing set; absent=['38'] unexpected=[]`. Nothing in Task 11 calls that path. An implementer who trusts the prose over the assertion will make `establishment_weights` emit `"38"` with a sentinel/zero and then be unable to reconcile the failing assertion with the docstring; an implementer who trusts the assertion ships §10.2 with zero tests for the global "DECLINE, NEVER FABRICATE" guarantee.

**Proposed fix.** Keep `assert "38" not in weights` (it matches the design: absence is omitted from the dict), and add the surfacing half to the same test so the name and docstring become true — import `WeightDomainError` and `EstablishmentProportional` and append:

    with pytest.raises(WeightDomainError, match="38"):
        allocate(anchor, EstablishmentProportional().weights(_context(monthly, appendix_a_config), anchor))

Then Step 4's "Expected: PASS, all four tests" still holds (still four tests), and the docstring should be reworded to say the cell surfaces as a domain refusal at `allocate`, not inside the weight vector.

### [NIT] plan:2808-2815

**Claim.** `establishment_weights`'s docstring justifies omitting an absent cell on the grounds that "absence and a published zero are different facts, and `compose` must be able to tell them apart", but neither half is true of the code as planned: the function itself collapses the two, and `compose` cannot distinguish them either.

**Evidence.** The comprehension filter on plan:2815 is `if row["qtrly_establishments"] is not None and row["qtrly_establishments"] > 0`, so a published zero is dropped from the returned dict by the same rule as an absent row — both simply do not appear as keys. Task 10's `compose` (plan:2578) then classifies gaps with `uncovered = [cell for cell in gaps if fallback.get(cell, 0.0) <= 0.0]`, which maps a missing key and a zero value to the identical branch. So the stated reason for the design choice is false as written. Behaviour is unaffected on D1 (I measured `data/staged/qcew_monthly.parquet`: on all 1,227 suppressed state cells `qtrly_establishments` is non-null with min 1, max 282), so nothing downstream breaks.

**Proposed fix.** Reword the docstring to state what the code does — a cell with no usable published establishment count (absent row, null, or non-positive) is omitted so the domain check at `allocate` refuses the month rather than letting a partial vector normalize — or, if the distinction is genuinely wanted, keep published zeros as explicit `0.0` entries and let `compose`/`check_domain` reject them by value.

## Task 12

### [BLOCKER] plan:3118-3123

**Claim.** The composite mixes two incommensurable units: §10.3's own weights are dimensionless national shares (~1e-3) while `establishment_weights` returns raw establishment counts (1..282), and `allocate` normalizes the merged vector as a whole — so on every month that has any fallback cell, the cells that actually have a historical share receive essentially none of R_t.

**Evidence.** I assembled the plan's `historical.py` (plan:3019-3193) verbatim with Task 10's `compose`, Task 11's `establishment_weights`, and Task 4's `allocate`, and ran it on data/staged/qcew_monthly.parquet. 2024-03: R_t = 1589 over 13 missing cells. Own weights are 0.015574 (WI '55'), 0.002920 ('08'), 0.001852 ('46'), 0.000755 ('49'); fallback weights are 77, 72, 16, 9, 3, 2, 2, 2, 1. Allocation: WI = 0.13 employees, '08' = 0.03, '46' = 0.02, '49' = 0.01 — the four own cells take 0.0115% of R_t, the nine fallback cells take 99.9885%. Over all 96 months the own-weighted cells receive 0.0067% of the 142,658-employee residual (best single month 0.017%). WI's own last-observed share of 1.56% implies ~650 employees; the composite hands it 0.13, which integerizes to 0. Max |composite − pure §10.2| is 906 employees, so the family is not even a faithful §10.2 — it is §10.2 with the own cells zeroed out. §10.8's rung 3 would ship these numbers.

**Proposed fix.** Put both arms in the same unit before calling `compose`. Simplest: in `_ShareBaseline.weights` return `reduced * N_t` (N_t = the published national employment row at `anchor.reference_month`) so the own weight is a predicted employee level, and supply the fallback as `A_{s,t} × (disclosed employment / disclosed establishments)` for that month rather than raw `A_{s,t}`. Equivalently, rescale the fallback subvector so its mean weight matches the own subvector's before merging. Add a test with one own cell and one fallback cell whose allocations are both O(R_t/|M_t|) — nothing in this task's 13 tests exercises a mixed-basis vector.

### [BLOCKER] plan:3118-3123

**Claim.** `_ShareBaseline.weights` composes own weights that are national *shares* (dimensionless, O(0.01)) with fallback weights that are raw *establishment counts* (O(1)-O(100)), so after `allocate` normalizes them the establishment-fallback cells absorb essentially the entire residual.

**Evidence.** Measured on data/staged/qcew_monthly.parquet: observed state shares of the national total run 6.0e-05 .. 0.110 (median 0.0155); `qtrly_establishments` on suppressed cells runs 1..282. `own[cell] = reduced` (plan:3117) is a share; the second arm is `establishment_weights(context, anchor)` (plan:3120), raw A. `compose` (plan:2588-2594) unions them with no rescaling, and `allocate` normalizes: `R * q_c / sum(q)`. Ran the shipped code:
  Weights(values={'41':0.0155,'53':0.0155,'02':20.0}), Anchor residual 1480.0
  -> {'41': 1.1452, '53': 1.1452, '02': 1477.7096}
The single fallback cell takes 99.85% of the residual; the two own-share cells get ~1 employee each. This is not a corner case: states 02, 10, 15, 32, 38, 50 are never observed in the window, and all 96 of 96 months contain both own-capable and fallback cells (sample (own, fallback) counts per month: (9,5), (8,5), (10,5), (8,5), (9,4)). The plan itself measures 465 of 1,227 cells on the fallback arm. No Task 12 test catches it — both composite tests use single-cell anchors (("01",) at plan:2958, ("02",) at plan:2970) where normalization makes scale unobservable — and Task 16's `test_every_running_estimator_sums_to_the_residual` (plan:3943) still passes, because the allocation does sum to R_t; it is merely concentrated on the wrong cells. None of the four deliberate deviations in the Self-review notes (plan:4931-4936) covers this: deviation 3 is about §10.4's shrinkage form and k, not about the units of the fallback arm.

**Proposed fix.** Put both arms on the same scale before `compose`. Either (a) convert the own arm to the establishment scale — `own[cell] = reduced_share * N_t / A_cell` is not it; use `own[cell] = reduced_share * N_t` (an employment level) and set `fallback[cell] = A_cell * (median over own cells of own_j / A_j)`, i.e. scale the fallback onto the own arm's units; or (b) make `compose` reject arms whose medians differ by more than a declared factor so the mismatch cannot ship silently. Whichever is chosen, add a Task 12 test with a multi-cell anchor mixing one own cell and one fallback cell that asserts the *allocation*, not just the basis labels.

### [DEFECT] plan:2976-2991

**Claim.** `test_a_lookback_stops_at_the_naics_vintage_break` does not test the vintage rule. Its fixture has no national row at 2021-12, so `observed_share_history`'s inner join on the national frame empties the history before the vintage filter is ever reached; the test passes for the wrong reason.

**Evidence.** Ran the helper on that exact fixture: `may_cross_vintage=False` -> [] and `may_cross_vintage=True` -> [] (printed both). Then I deleted the `if not may_cross_vintage: rows = rows.filter(pl.col("naics_vintage") == vintage)` block from `historical.py` and re-ran the task's whole test file: 13 passed. The classification-consistency rule is the one mechanism this task exists to introduce ("Task 12 sets that rule", plan:230) and no test in the file constrains it.

**Proposed fix.** Add a national row for 2021-12 to the fixture so the 2021-12 share is well defined, then assert both branches off that single fixture: `may_cross_vintage=False` -> `[]` and `may_cross_vintage=True` -> `["2021-12"]`. (`test_crossing_the_break_is_possible_only_when_config_permits` already builds the correct fixture; sharing it makes the pair meaningful.)

### [DEFECT] plan:2891

**Claim.** The stated coverage split "762 of 1,227 cells own-weight, 465 establishment-fallback" does not follow from the code shown. It counts cells whose state has an observed month anywhere in the window, ignoring both the strict `reference_month < before` filter and the classification-consistency filter this same task imposes.

**Evidence.** On data/staged/qcew_monthly.parquet: 1,227 suppressed cells; 762 belong to a state with >=1 observed month ANYWHERE in the window (and 465 is exactly its complement — that is where the plan's pair comes from). But only 546 have an observed month strictly BEFORE their own month, and only 360 have one that is both strictly before and in the same NAICS vintage. Running the plan's code end to end over all 96 months: LastObservedShare / RollingMedianShare / ExponentiallyWeightedShare / BreakAdjustedShare each give own=360, fallback=867; SameMonthPreviousYearShare gives own=129, fallback=1,098. Two further structural consequences the number hides: 2017-01 and 2022-01 have no prior in-vintage month at all, so every cell in those months falls back, and the five variants do not share one split.

**Proposed fix.** Correct the figure to 360/1,227 own-weight (867 fallback) for the four order-statistic variants and 129/1,227 for the same-month-prior-year variant, or drop the literal per the anti-drift rule and record it in the run manifest. Apply the same correction to the module docstring (plan:3035, "762 of 1,227 cells get an own share; 465 take the declared establishment fallback") and the test docstring (plan:2968, "465 of 1,227 cells fall here"), and state that the same-month variant has its own, much lower, coverage.

### [DEFECT] plan:3086

**Claim.** `.tail(lookback_months)` keeps the last N *rows* of an observed-only series, not the last N *months*, so `historical_lookback_months = 24` does not bound the lookback to 24 months and the estimator is not the one the prose describes.

**Evidence.** Task 1 declares `historical_lookback_months: int = 24` and this task's docstring (plan:3028) describes "a 24-month lookback from 2022-06" — a calendar window. Running the shipped code over the real window, the retained history spans a median of 12 and a maximum of 48 calendar months, and 102 of the 360 own-weight histories span more than 24 calendar months. A state suppressed in most months therefore has its "24-month" share built from observations up to four years old, which is exactly what the recency-weighted variants (last observed, exponentially weighted) are supposed to prevent.

**Proposed fix.** Bound the window by month as well as by row count: derive the first admissible month from `before` minus `lookback_months` and add `.filter(pl.col("reference_month") >= first_month)` before the `.tail(...)`. If the row-count semantics is actually intended, rename the config key to `historical_lookback_observations` and say so in both the docstring and Task 1.

### [DEFECT] plan:2976-2991

**Claim.** `test_a_lookback_stops_at_the_naics_vintage_break` is vacuous: its fixture has no national row at 2021-12, so `observed_share_history`'s inner join on `reference_month` empties the frame before the `naics_vintage` filter ever runs. The test passes whether or not the classification-consistency rule exists.

**Evidence.** The fixture (plan:2978-2986) supplies national rows only for 2022-03. `observed_share_history` (plan:3060-3080) filters state rows to `reference_month < before` (leaving only 2021-12), then does `.join(national, on='reference_month', how='inner')` — which drops 2021-12 because no national row carries that month. The vintage filter at plan:3074-3075 then operates on an already-empty frame. Reproduced the function against the exact fixture with the vintage filter present and with it deleted: both print `[]`. The companion test at plan:2994-3011 does include a 2021-12 national row, which is what makes it non-vacuous — so the omission in this one is an oversight, not a design.

**Proposed fix.** Add the missing national row to the fixture: `{"area_type": "national", "area_fips": "US000", "state_fips": None, "aggregation_level": "18", "reference_month": "2021-12", "employment_value": 100, "qtrly_establishments": 4}`. With it, the assertion `history["reference_month"].to_list() == []` fails if the vintage filter is removed, which is what the test claims to check.

### [NIT] plan:3187-3189

**Claim.** `BreakAdjustedShare._reduce` returns the plain median whenever the history has fewer than four points — precisely the behaviour its own docstring says the variant exists NOT to be — so variant 5 silently duplicates variant 3 on a large share of real cells.

**Evidence.** Measured over the 96 months with the code as written: of the 360 cells that get an own share, 108 have a history shorter than 4 and take the short-circuit path, and `BreakAdjustedShare` produces a numerically identical value to `RollingMedianShare` on 111 of the 360 (they differ on 249). `test_section_10_3_ships_exactly_five_variants` only checks that five distinct `estimator_id` strings exist, so nothing detects the duplication.

**Proposed fix.** Either document the short-history degeneracy in the docstring (replacing the flat "what this variant exists NOT to be" claim), or return `None` below the minimum segment length so the cell takes the declared §10.2 fallback instead of silently re-emitting variant 3's number under variant 5's label.

## Task 13

### [BLOCKER] plan:3442-3449

**Claim.** The composite hands `compose` two weight vectors in different units — own weights are `intensity × A` (employees) while the fallback vector is bare `A` (establishments) — so after `allocate` normalizes the merged vector, the fallback states are allocated as if their employee-per-establishment intensity were exactly 1.0.

**Evidence.** I built the plan's Task 10/11/13 modules verbatim on top of the already-shipped `reconcile/anchor.py` and `reconcile/allocate.py` and ran them against `data/staged/`. For 2023-06 (R_t = 1453, national March intensity 5.914): the merged weight vector is {'33': 374.6, '55': 746.4, ..., '15': 3.0, '44': 2.0} — the two fallback cells carry raw establishment counts while every own cell carries employees. Allocation gives HI ('15', A = 3) **2.8 employees**, i.e. 0.93 employees per establishment. Pure §10.2 gives HI 10.2; using the estimator's own n→0 limit (national intensity × A) gives 16.4. This hits 303 of the 1,080 cells in the 84 months that run. Task 16's runner does not rescale — it calls `estimator.weights(context, anchor)` then `allocate(anchor, outcome)` directly (plan:4110, plan:4118), so nothing downstream corrects it. Two of the plan's own statements are contradicted by this behaviour: intensity.py's docstring says those cells "take the declared establishment fallback" (they do not get §10.2's share — 2.8 vs 10.2), and the Global Constraints forbid exactly the artefact produced here ("every suppressed cell has ≥ 1 establishment, which invites a floor of 1 employee per cell. That is as much an invention as a cap").

**Proposed fix.** Put both arms of the composite in the same units: give the uncovered cells `national_intensity * exposure[cell]` rather than `exposure[cell]`. That is the estimator's own n→0 shrinkage limit (`weight = n/(n+k) → 0` ⇒ the shrunk intensity is the national intensity), so it introduces no new number. Compute `national_intensity` once in `march_intensity` and return it alongside the per-state dict, or expose it as a second helper. Also add a line to Task 10's `compose` docstring stating that `own` and `fallback` must be in the same units, since a normalized vector makes the mismatch invisible.

### [BLOCKER] plan:3282-3283

**Claim.** `test_intensity_is_employment_over_establishments_per_state` asserts 5.0 and 3.0, but `march_intensity` shrinks by default (`shrink_strength: float = DEFAULT_SHRINK_STRENGTH`, 5.0), so the shown code returns 4.5 and 3.0714. Step 4's "Expected: PASS, all five tests" (plan:3455) is unattainable.

**Evidence.** Ran the plan's exact test file against the plan's exact `intensity.py`: `1 failed, 4 passed`, with `assert 4.5 == 5.0 ± 5.0e-06`. Hand-derivation for the test's inputs (state 01: 50/10, state 02: 90/30): national intensity = 140/40 = 3.5; state 01 weight = 10/15 = 0.6667 → 0.6667·5.0 + 0.3333·3.5 = 4.5; state 02 weight = 30/35 = 0.8571 → 0.8571·3.0 + 0.1429·3.5 = 3.0714. `pytest.approx` default rel tolerance is 1e-6, so both assertions fail. The risk is not that this goes unnoticed but that an implementer who trusts "Expected: PASS" loosens the assertion (e.g. to `abs=1.0`) instead of fixing the call, destroying the only test that pins the raw employment/establishments ratio.

**Proposed fix.** Pass `shrink_strength=0.0` in this test so it checks the unshrunk ratio the test name claims (`weight = n/(n+0) = 1.0`; safe because the filter guarantees `establishments > 0`), leaving 5.0 and 3.0 correct. Test 5 already covers the shrunk path and its arithmetic checks out (02 → 25.74 < 100; 01 → 10.042 ≈ 10.0 ± 1.0).

### [BLOCKER] plan:3282-3283

**Claim.** `test_intensity_is_employment_over_establishments_per_state` asserts the unshrunk ratios 5.0 and 3.0, but `march_intensity` always applies shrinkage (`shrink_strength` defaults to 5.0 and there is no unshrunk path), so it returns 4.5 and 3.0714285714. Step 4's "Expected: PASS, all five tests" is impossible.

**Evidence.** Hand-executed the shipped formula from plan:3396-3420 on the test's own inputs (state 01: emp 50 / est 10; state 02: emp 90 / est 30):
  national_intensity = (50+90)/(10+30) = 3.5
  01: n=10, raw=5.0, w=10/15=0.6667 -> 0.6667*5.0 + 0.3333*3.5 = 4.5
  02: n=30, raw=3.0, w=30/35=0.8571 -> 0.8571*3.0 + 0.1429*3.5 = 3.0714285714
Ran it: `{'01': 4.5, '02': 3.071428571428571}`. `pytest.approx(5.0)` and `pytest.approx(3.0)` use the default rel=1e-6, so both assertions fail. The test name ("employment over establishments") describes the raw ratio, but the function the plan writes never returns one.

**Proposed fix.** Either call it with `shrink_strength=0.0` (matching the test's name and intent, and leaving the shrinkage to `test_shrinkage_pulls_a_thin_state_toward_the_national_intensity`), or change the expected values to `pytest.approx(4.5)` and `pytest.approx(3.0714285714)` and rename the test to say it is the shrunk intensity.

### [DEFECT] plan:3235, plan:3366

**Claim.** The measured-coverage claim is wrong in both magnitude and composition: HI and RI are not the only states without a CBP row, and 186 is not the number of cells that take the fallback.

**Evidence.** Measured by running the plan's own `CbpIntensity` over `data/staged/qcew_monthly.parquet` + `cbp_state_size.parquet`: 12 months decline, 84 run, and over those 84 months own weight covers **777 of 1,080** cells with **303** taking the establishment fallback — HI 84, RI 78, NV 72, DE 39, ND 30. `cbp_state_size` at `size_code '001'` carries NV ('32') only in 2023, DE ('10') only in 2017 (null employment) and 2018, ND ('38') only in 2017 (null employment); years publish 45–47 states, not 48. The plan's 186 is HI 96 + RI 90 — it counts the 12 declined 2024 months, which take no fallback at all because the whole month declines. The related "1,041/1,080" in the coverage table is also wrong and has already shipped, in `src/logging_employment/reconcile/allocate.py:30-32`.

**Proposed fix.** Replace both the plan bullet and the intensity.py docstring with: 84 of 96 months run; own weight 777/1,080; 303 cells take the establishment fallback, in five states — HI (84) and RI (78) absent from CBP in every year, plus NV (72), DE (39) and ND (30), which are absent in some years and present in others. State explicitly that CBP coverage is per state-year, not per state, so a state can flip between own and fallback across the window. Correct `allocate.py:30-32` in the same pass.

### [DEFECT] plan:3441-3449

**Claim.** `CbpIntensity.weights` builds own weights as `intensity * exposure` but hands `compose` a fallback arm of bare `exposure`, so the 186 HI/RI cells are systematically under-weighted by roughly the median shrunk intensity (~4.5x) — and the plan's own shrinkage machinery already contains the right answer for a state with no CBP row.

**Evidence.** plan:3442-3446 sets `own[cell] = intensity[cell] * exposure[cell]`; plan:3447-3449 passes `exposure` (bare A) as the fallback arm. Measured on data/staged/cbp_state_size.parquet for reference year 2023 (46 states): shrunk intensity ranges 2.363 .. 9.399, median 4.455, national 5.914. So an own cell contributes q ~= 4.5*A while a fallback cell contributes q = A. Two cells with A=10, one own and one fallback: own gets 44.6/54.6 = 82% and fallback gets 18%, where §10.2 alone would split 50/50. Confirmed HI ('15') and RI ('44') appear in no `cbp_state_size` row in any published year, so this path is taken on every one of the plan's stated 186 cells. `test_a_state_absent_from_cbp_takes_the_declared_fallback` (plan:3313-3330) is the plan's only multi-cell composite test and it asserts only `out.basis[...]`, never the allocation, so it passes with the wrong numbers.

**Proposed fix.** A state with no CBP row is the n=0 limit of the plan's own shrinkage weight `w = n/(n+k)`, which gives w=0 and intensity = `national_intensity`. Compute `national_intensity` inside `march_intensity` (it already does) and return it, so the fallback arm for §10.4 becomes `national_intensity * exposure[cell]` — commensurable with the own arm by construction, no unit mismatch, and no bare-A fallback needed. Keep `weight_basis = 'establishment_fallback'` for provenance if the composed label is wanted.

### [NIT] plan:3219

**Claim.** The declared Interfaces signature for `march_intensity` omits the `shrink_strength` parameter that the task's own test calls by keyword.

**Evidence.** plan:3219 declares `def march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> dict[str, float]`, but plan:3336 calls `march_intensity(cbp, reference_year=2023, shrink_strength=5.0)`, and the Step 3 code block does define `shrink_strength: float = DEFAULT_SHRINK_STRENGTH`. An implementer who writes to the Interfaces contract rather than the code block gets `TypeError: march_intensity() got an unexpected keyword argument 'shrink_strength'`.

**Proposed fix.** Update the Interfaces line to `def march_intensity(cbp: pl.DataFrame, *, reference_year: int, shrink_strength: float = DEFAULT_SHRINK_STRENGTH) -> dict[str, float]`.

## Task 14

### [NIT] plan:3473

**Claim.** Task 14's Interfaces block declares it consumes `NoHarvestFactorError`, but the module it produces neither imports nor raises it — it returns `Decline`.

**Evidence.** plan:3473 reads "- Consumes: `NoHarvestFactorError`, `Decline`." Step 3's `harvest.py` (plan:3575-3593) imports only `Weights`, `Anchor`, `Decline`, `EstimatorContext`, and its `weights()` body is a bare `return Decline(reason=...)`. `grep -rn NoHarvestFactorError src tests` returns exactly one hit — the shipped declaration at /Users/lowell/Projects/impute-suppressed-stats/src/logging_employment/errors.py:81 — and the plan mentions the name only at lines 505 and 640 (Task 2), never at a raise site anywhere in the 4970-line plan. I reconstructed the upstream modules from the plan's own code blocks (reconcile/allocate.py from Task 4, baselines/interfaces.py and __init__.py from Task 10) into a scratch tree, added Step 3's harvest.py and Step 1's test file verbatim against the shipped tests/unit/conftest.py `make_monthly` fixture and the real `load_config(config.yaml)`, and ran pytest: both tests PASS with the `Decline`-returning code, and ruff is clean. So the code and tests are correct; only the Interfaces line is wrong. Every other factual claim in this task verified against primary source: Appendix A ships `tpo: enabled: false` / `fia: enabled: false` (spec:2050-2053); config.yaml has no tpo/fia entry; the roadmap Stage 3 exit text is verbatim (roadmap:215); the §10.5 two-sentence quote is verbatim (spec:984); §17.4's 4th bullet is "run every baseline on a small frozen fixture" (spec:1748); the shipped `Anchor(reference_month, residual, missing_cells, anchor_basis)` and `observed_partition(monthly)` in src/logging_employment/reconcile/anchor.py match the test's positional call exactly.

**Proposed fix.** Delete `NoHarvestFactorError` from Task 14's Consumes list (leave `Decline`). Returning a `Decline` is what the Global Constraints require ("declines the month with a reason string written as a `declined` row in `baseline_results/`") and what both tests assert; an implementer who follows the Consumes line and writes `raise NoHarvestFactorError(...)` fails `assert isinstance(out, Decline)` in both tests and breaks Task 16's runner, which expects a returned decline. If the Consumes line is kept as-is, Task 2's `NoHarvestFactorError` should instead be dropped from errors.py, since Stage 3 ships it with no raise site.

## Task 15

### [NIT] plan:3625, plan:3740

**Claim.** The task prose and the shipped module docstring both assert that "training-visible" appears twice in the spec, both inside §10; it appears exactly once.

**Evidence.** `grep -cioE "training.{0,3}visible" specs/logging-employment-spec.md` returns 1. The single hit is spec:988 (§10.6, "Fit a regularized model for log employment intensity using only training-visible cells..."). The only other occurrence of the bare word "visible" in the spec is spec:2284 ("where that filter starts doing visible work"), unrelated. Plan:3625 reads "it appears twice, both in §10" and plan:3740 puts the same false count into the `regression.py` module docstring an implementer types verbatim into shipped source.

**Proposed fix.** Change both to "it appears once, in §10.6" (plan:3625 and the module docstring at plan:3740). The argument the sentence supports — that the term is undefined and Stage 3 must define it via `EstimatorContext.partitions` — is unaffected and correct.

### [NIT] plan:3805

**Claim.** `ConstrainedRegression.weights` carries no docstring, which drops `src/` below the repo's configured `interrogate` gate of `fail-under = 100`.

**Evidence.** `pyproject.toml` sets `[tool.interrogate] fail-under = 100` with `exclude = ["tests"]` only. `uv run interrogate src` on the current tree reports `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)`. Running interrogate over the plan's extracted `regression.py` gives `regression.py | 5 | 1 | 4 | 80%` — the one miss is `weights` at plan:3805 (module, `fit_log_intensity`, the class, and `training_rows` all have docstrings). Adding this file as written takes `src/` off 100%. (The plan never invokes interrogate itself, so nothing in the task's own Step 4 fails; the break surfaces on the next project-wide docstring check.)

**Proposed fix.** Add a one-line docstring to `ConstrainedRegression.weights` in the Step 3 code block, e.g. `"""Predicted employment levels as weights, composed with the establishment fallback."""`.

## Task 16

### [BLOCKER] plan:4137, plan:4162

**Claim.** The runner writes a three-field `cell_id` (`state_total|{state_fips}|{month}`) that does not match the shipped seven-field `cell_id` convention, so `baseline_results.cell_id` can never join Stage 2's `target_cell` / `constraint_coefficient` / `deterministic_bounds`.

**Evidence.** Shipped `src/logging_employment/constraints/cells.py:53-67` builds `f"{kind}|{state_fips}|{reference_month}|{ownership_code}|{industry_code}|{naics_vintage}|{size_class}"`. Reading the shipped table confirms the on-disk values: `uv run python -c "...pl.read_parquet('data/constraints/target_cell.parquet')..."` prints `['state_total|01|2017-01|5|113310|NAICS 2017|ALL', 'state_total|01|2017-02|5|113310|NAICS 2017|ALL']`. The runner emits `state_total|01|2017-01`. Both row builders use the literal `state_total|` prefix (= `KIND_STATE_TOTAL`), so they are trying to be the shipped identifier and are truncating four fields. `DETERMINISTIC_BOUNDS_SCHEMA` (contracts.py:273-289) is keyed on `cell_id`, and the runner's own docstring says `constraint_set_hash` is threaded in so "§18.1's reproducibility check needs these estimates tied to the Stage 2 system they sit beside" — that tie is exactly the join that returns zero rows. No test in Tasks 16-19 joins on `cell_id`, so nothing catches it.

**Proposed fix.** Build the id with the shipped helper: `from ..constraints.cells import KIND_STATE_TOTAL, TOTAL_SIZE_CLASS, cell_id`. Note this is not a format-string edit: `anchor.missing_cells` is a tuple of bare `state_fips`, and `_decline_rows` receives only `anchor`, so neither builder has `ownership_code`, `industry_code`, or `naics_vintage`. Thread `partitions[month].missing` (or a `dict[state_fips, key_fields]` derived from it) into both row builders. Two concrete gotchas an implementer will otherwise get wrong: `naics_vintage` on disk is the literal `"NAICS 2017"` / `"NAICS 2022"` (with a space), not `"2017"`; and `size_class` is `TOTAL_SIZE_CLASS = "ALL"`, not null. Add a test that inner-joins `baseline_results` to `target_cell` on `cell_id` and asserts the join height equals the baseline row count.

### [DEFECT] plan:4180-4195, plan:3958-3962

**Claim.** `preferred_estimator` resolves §10.8's hierarchy once for the whole window, so on D1 it returns `"cbp_intensity"` even though that estimator has no estimate in 12 of 96 months; the manifest records the scalar with no coverage field, and no test detects the gap.

**Evidence.** `CbpIntensity.weights` (plan:3429-3438) returns a `Decline` when `reference_year not in context.cbp['reference_year']`. Measured on the shipped staged data: `uv run python -c "...HarmonizedData.load(Path('data/staged'))..."` prints `months 96`, `cbp years [2017, 2018, 2019, 2020, 2021, 2022, 2023]`, and 2024 carrying 147 suppressed state cells across its 12 months. `preferred_estimator` takes `ran` as a set over the entire results frame and returns the first `FALLBACK_ORDER` member present anywhere, so it returns `"cbp_intensity"`; Task 17 (plan:4362) writes that scalar into `baseline_manifest.json` as `preferred_estimator`. A Stage 4 consumer filtering `estimator_id == preferred` and `reconciliation_status == 'anchored_and_reconciled'` gets 84 months of numbers and nothing for 2024, while `test_the_preferred_estimator_follows_the_fallback_order` only asserts the return value is a member of `FALLBACK_ORDER` and so passes regardless. The plan's own coverage table (plan:~176) already records "§10.4 CBP intensity | 84/96 months".

**Proposed fix.** Resolve the hierarchy per month rather than per window: add `def preferred_estimator_by_month(results) -> dict[str, str]` that applies `FALLBACK_ORDER` to the set of estimators with `anchored_and_reconciled` rows *within each* `reference_month`, keep the scalar only as a summary, and have Task 17's manifest record both the per-month mapping (or at minimum a `preferred_estimator_month_coverage` count). Replace the membership-only test with one asserting the preferred estimator (or its per-month fallback) has estimates in every month present in `results`.

### [DEFECT] plan:4119-4132, plan:3966-3982

**Claim.** The rationale for deriving `integer_total` from the allocation is false — the two candidate totals cannot diverge the way the comment describes — and the resulting `assert` labelled "§12.6 step 5: recheck the margin" is a tautology, as is the test that claims to guard it.

**Evidence.** `allocate` (plan:1275-1281) returns `{cell: anchor.residual * w[cell] / total}`, so `sum(allocated.values()) == anchor.residual` by construction for any residual, fractional or not; the runner uses that no-bound path unconditionally. A 200,000-case random check (`uv run python -c ...` over random residuals in [0,3000) and 2-15 random positive weights) found `max |sum(allocated) - residual| = 9.09e-13` and zero cases where `int(round(sum(allocated))) != int(round(residual))`, so the comment's "they diverge the moment a Stage 4 mask produces a fractional residual" is wrong (the only conceivable split is fp noise at an exact half-integer under banker's rounding, which cuts against the comment's rationale rather than for it). Consequently `assert sum(integers.values()) == integer_total` cannot fail: `integerize` (plan:2056-2094) either returns `floors + placed` summing exactly to `total` or raises, and `base > total` is impossible here because `sum(floors) <= floor(S) <= round(S)`. Likewise `test_the_integer_estimates_balance_to_the_allocations_own_total` asserts `int(round(S)) == round(S)` and passes under either implementation, so it does not guard the distinction its docstring claims.

**Proposed fix.** Delete or correct the comment at plan:4119-4124, and make the margin recheck independent by asserting the integers against the anchor rather than against their own source: `expected = int(round(anchor.residual)); assert sum(integers.values()) == expected` (raise a package error rather than `assert`, which `python -O` strips). Change the test to compare `estimate_integer` sum against the row's `residual` column, not against the `estimate` sum, so it would actually fail if `allocate` stopped summing to the residual.

## Task 17

### [BLOCKER] plan:4249-4291

**Claim.** All five integration tests depend on a `staged_repo` fixture that is defined nowhere — not in the repo, not in this task, not in any other task — so the file errors at setup instead of running, and Steps 2 and 4 can never produce their stated outcomes.

**Evidence.** `grep -n staged_repo` over the whole plan returns only the five usages inside Task 17 (lines 4252-4290); no task creates it. In the repo, `find tests -name conftest.py` returns only `tests/conftest.py` (which only appends `scripts/audit` to sys.path) and `tests/unit/conftest.py`; there is no `tests/integration/conftest.py` (Task 19, at plan:4884, is the first to create one, and it defines `frozen_harmonized`, not `staged_repo`). pytest conftest scoping is directory-based, so Task 16's `harmonized_toy` in `tests/unit/conftest.py` is invisible to `tests/integration/`. The obvious substitute also fails: the only staged fixture in the repo is `tests/fixtures/constraints/`, and running the shipped gate on it — `uv run python -c "...closure_audit(m, observed_partition(m)); assert_universe_closes(a)"` — raises `UniverseClosureError: establishment universes do not close in 1 month(s); first 2024-03: national 7713 minus state sum 420 = 7293 across 2 publishing areas`, because that fixture is 3 rows (1 national, 2 states) for one month with an empty `cbp_state_size`. So `run-baselines` would halt on it before writing anything.

**Proposed fix.** Add a Step (and a Files entry for `tests/integration/conftest.py`) that builds `staged_repo` explicitly, the way Task 16 spells out `harmonized_toy`: write staged parquets whose national `qtrly_establishments` equals the state sum exactly in every fixture month, with at least one suppressed cell per month and enough history/CBP structure to make both `own_estimator` and `establishment_fallback` reachable; invoke `build-constraints` inside the fixture so `schema_manifest.json` exists in the run dir; and expose `.config_path` and `.run_dir` (the latter computed with `run_dir(cfg, run_id(cfg, _input_digests(cfg)))`). Also correct Step 2's expectation — with no fixture the tests ERROR at setup rather than failing on an unregistered command.

### [DEFECT] plan:4388-4424

**Claim.** The `reconcile` command writes no manifest at all, violating §16.1's MUST, and the task's prose quotes only the idempotence half of that sentence.

**Evidence.** spec:1665 reads: "Every command MUST write a machine-readable manifest and MUST be idempotent for the same inputs." The plan's own Global Constraints repeat it verbatim ("**Every command MUST write a machine-readable manifest and MUST be idempotent for the same inputs** (§16.1, spec:1663)") and add "Never soften a MUST into a log line." Task 17's prose at plan:4231 says only "§16.1 requires both commands to be idempotent for identical inputs", dropping the manifest clause, and the `reconcile` body (plan:4402-4424) writes nothing to disk — it echoes two lines and exits. I confirmed the behaviour by appending the plan's exact code (sed -n '4304,4424p') to a sandbox copy of `cli.py` and invoking it: `checked 2 (estimator, month) pairs / max residual drift 0.000e+00`, exit 0, and no file created. No test in this task covers `reconcile` either, so nothing catches the omission.

**Proposed fix.** Have `reconcile` write a sibling `reconcile_manifest.json` in the run dir recording, at minimum, the checked (estimator, month) pair count, the max drift, the tolerance it was compared against, the pass/fail verdict, and the digest of the `baseline_results.parquet` it read — and add a test asserting the file exists and that a second run writes identical bytes.

### [DEFECT] plan:4346-4351

**Claim.** `weight_basis_counts` pools `weight_basis` across all ten estimators, so the per-estimator composite split that Task 19 instructs the implementer to read off this command's output is not present in the manifest or the echo.

**Evidence.** The manifest builds `basis_counts = {row['weight_basis']: row['len'] for row in ran.group_by('weight_basis').len().iter_rows(named=True)}` — a single pooled dict, e.g. `{'own_estimator': N, 'establishment_fallback': M}` (verified by running that exact expression on a synthetic BASELINE_RESULT_SCHEMA frame: it returns `{'establishment_fallback': 2, 'own_estimator': 4}` with no estimator key), and the echo loop at plan:4382 prints the same pooled pairs. But Task 19 Step 5 (plan:4855) says "Record from the output, for the completion report: ... the own-weight versus establishment-fallback counts **per estimator**", and Task 19's D1 test groups by `["estimator_id", "weight_basis"]`. Under the pooled form, §10.3's 465 fallback cells and §10.4's 186 are summed into one number and cannot be separated, so the field cannot answer the question its own test docstring poses ("Stage 4 must not report a composite's score as a pure estimator's").

**Proposed fix.** Group by `["estimator_id", "weight_basis"]` and store a nested dict (`{estimator_id: {basis: count}}`) in `weight_basis_counts`, echoing one line per (estimator, basis). The test can then assert `set(counts[preferred]) >= {...}` rather than the pooled `set(counts)`.

### [NIT] plan:4264-4268

**Claim.** `test_run_baselines_does_not_touch_the_stage_2_manifest` never checks the command's exit code, so it passes when `run-baselines` crashes or does not exist — it is green during Step 2's red phase.

**Evidence.** The test discards `runner.invoke(...)`'s result and only compares `schema_manifest.json` bytes before and after. `typer.testing.CliRunner.invoke` defaults to `catch_exceptions=True`, so an exception inside the command becomes a non-zero exit code rather than a raised error; a command that aborts (or is unregistered, as at Step 2) writes nothing, so the byte comparison holds and the test passes without ever exercising the behaviour it names. The repo's own house style does the opposite: `tests/integration/test_constraint_cli.py` routes every invocation through `_run`, which asserts `result.exit_code == 0, result.output`.

**Proposed fix.** Capture the result and assert `result.exit_code == 0, result.output` before the byte comparison (same for the other three tests that discard the result).

### [NIT] plan:4392-4396, plan:4413

**Claim.** The `reconcile` docstring says the command "re-runs the allocation", which it does not do; the `HarmonizedData.load(...)` call that would have supported that is dead code.

**Evidence.** The docstring (plan:4394-4396) reads "it reloads the results, re-runs the allocation, and reports the largest difference." The body reads the persisted parquet and re-sums `estimate` per (estimator, month) against the `residual` column already stored in those rows — it never imports `allocate`, `national_residual`, or any estimator, and the loaded `HarmonizedData` at plan:4413 is assigned to nothing and never used. Confirmed by running the plan's verbatim code in a sandbox: it produced `max residual drift 0.000e+00` from the file alone, with a synthetic parquet whose staged tables were unrelated fixture rows.

**Proposed fix.** Reword to what the code does — "re-sums the persisted estimates against each month's recorded residual and reports the largest difference" — and delete the unused `HarmonizedData.load(Path(cfg.storage.staged_uri))` line and its import.

## Task 19

### [BLOCKER] plan:4750-4784

**Claim.** All three golden tests request the `appendix_a_config` fixture, but that fixture is added to `tests/unit/conftest.py`, which pytest does not expose to `tests/integration/`; every test errors at setup, so Step 4's "Expected: PASS, all three tests" cannot happen.

**Evidence.** Task 11 Step 1 (plan:2742-2757) says "Add the shared config fixture to `tests/unit/conftest.py`" and defines `appendix_a_config` there. conftest.py is directory-scoped. I probed the shipped repo by dropping a file into tests/integration/ that requests `make_monthly` (also defined only in tests/unit/conftest.py): `uv run pytest tests/integration/test_fixture_scope_probe.py -q` → `E fixture 'make_monthly' not found ... available fixtures: anyio_backend, cache, capfd, ...` (1 error). Step 3 only instructs wiring `frozen_harmonized` into `tests/integration/conftest.py` (plan:4884) and never mentions `appendix_a_config`.

**Proposed fix.** In Step 3, define `appendix_a_config` in `tests/integration/conftest.py` alongside `frozen_harmonized` (or move it up to the root `tests/conftest.py` so both suites see it).

### [BLOCKER] plan:4774-4776

**Claim.** `assert results.equals(golden)` compares the frame in `run_baselines` emission order against a golden that `write_parquet_deterministic` re-sorted on write, so the assertion is False even when the values are identical.

**Evidence.** Shipped `src/logging_employment/build.py:45-66` sorts before writing: `ordered = frame.sort(by=natural + [...])` with `natural = [c for c in ("area_fips","state_fips","reference_month","size_code") if c in frame.columns]` → for BASELINE_RESULT_SCHEMA that is `state_fips, reference_month, estimator_id, cell_id, ...`. The plan's own runner (plan:4104-4152) appends rows as `for month in sorted(partitions): for estimator in REGISTRY: for cell in anchor.missing_cells`. I hand-ran it: an 8-row frame in runner order round-tripped through `write_parquet_deterministic` gives run order `[('02','2022-01','equal_residual'),('15','2022-01','equal_residual'),('02','2022-01','establishment_proportional'),...]` vs golden order `[('02','2022-01','equal_residual'),('02','2022-01','establishment_proportional'),('02','2022-02',...),...]`; `df.equals(g)` → **False**, `df.sort(['state_fips','reference_month','estimator_id']).equals(g)` → True. The shipped house pattern the task tells you to follow already does this — `tests/integration/test_constraint_golden.py` asserts `built.coefficients.sort(["constraint_id","cell_id"]).equals(golden)`.

**Proposed fix.** Sort before comparing: `assert results.sort(["state_fips","reference_month","estimator_id","cell_id"]).equals(golden)`. Scope this to the results golden only — `test_the_anchor_audit_matches_its_golden_fixture` is correct as written, because ANCHOR_AUDIT_SCHEMA's only natural key is the row-unique `reference_month`, so the deterministic sort collapses to months-ascending, which is exactly `closure_audit`'s `for month in sorted(partitions)` order.

### [BLOCKER] plan:4860-4885

**Claim.** The "frozen fixture" is not frozen and is never committed: it is sliced out of gitignored `data/staged` at test time, so the committed golden is pinned to untracked, rebuildable live data and the (unmarked, default-suite) golden test cannot pass in a fresh clone.

**Evidence.** `.gitignore` contains `data/` and `runs/`; `git ls-files data` returns nothing. The Step 3 script reads `HarmonizedData.load(Path(cfg.storage.staged_uri))` (= `data/staged`, config.yaml storage block) and writes only the two golden outputs; Step 7 runs `git add tests/integration/ tests/fixtures/baselines/` (plan:4916), so no input is tracked. `frozen_harmonized` (plan:4884) must therefore re-slice live data at test time. The shipped house pattern does the opposite: `tests/fixtures/constraints/{qcew_monthly,qcew_national_size,cbp_state_size,bridge}.parquet` are all in `git ls-files`, and `test_constraint_golden.py` loads `HarmonizedData.load(FIXTURES)`. This also violates the plan's own ANTI-DRIFT rule (plan:50-56) — the next `build-harmonized` or QCEW revision breaks the golden for the wrong reason, and no reviewer can regenerate it.

**Proposed fix.** In Step 3, after building `sliced`, write its four frames to `tests/fixtures/baselines/*.parquet` with `write_parquet_deterministic`; make `frozen_harmonized` return `HarmonizedData.load(REPO / 'tests' / 'fixtures' / 'baselines')`; add those parquet files in Step 7's `git add`.

### [DEFECT] plan:4812-4816

**Claim.** `assert audit.height == results["reference_month"].n_unique()` is not the structural check its docstring claims; it holds only because every D1 month happens to carry suppressed cells, and it fails — reporting a skipped gate — the moment a month is fully disclosed, which is precisely the case the shipped anchor module documents as reachable.

**Evidence.** `closure_audit` (src/logging_employment/reconcile/anchor.py:125-160) emits one row per month in `partitions`, unconditionally. The plan's runner (plan:4106-4109) does `for month in sorted(partitions): anchor = national_residual(...); if not anchor.missing_cells: continue` — so a fully-disclosed month produces an audit row and zero result rows, and the two counts diverge (96 vs 95) even though the gate ran on all 96. The shipped anchor.py docstring names this future explicitly: "RETIREMENT CONDITION. If a future QCEW vintage ever yields a month with no suppressed state cell...". The test's own docstring invokes the anti-drift rule, which forbids exactly this coupling.

**Proposed fix.** Assert the audit against the panel rather than against the results: have `_run()` also return `data` and assert `audit.height == data.qcew_monthly.filter(pl.col("area_type") == "state")["reference_month"].n_unique()`, plus `set(results["reference_month"]).issubset(set(audit["reference_month"]))` for the containment the current line was reaching for.

### [DEFECT] plan:4730

**Claim.** "marked `slow` and excluded from the default run, like `test_d1_acceptance.py`" is false for this repo — no marker filter exists — and acting on it omits the `skipif` guard the shipped D1 file carries, so the new file errors instead of skipping wherever the gitignored `data/staged` is absent.

**Evidence.** `pyproject.toml` `[tool.pytest.ini_options]` sets `addopts = "--import-mode=importlib"` only; `markers` merely declares `slow: takes more than a few seconds`. Verified: `uv run pytest --collect-only -q` collects 986 tests, and `uv run pytest --collect-only -q tests/integration/test_d1_acceptance.py` collects its 5 slow tests — nothing is excluded by default. `test_d1_acceptance.py:22-28` is not protected by a marker filter but by `pytestmark = [pytest.mark.slow, pytest.mark.skipif(not (STAGED / "qcew_monthly.parquet").exists(), reason="data/staged/ is gitignored; run `build-harmonized` first")]`. The plan's file (plan:4803) has `pytestmark = pytest.mark.slow` alone, so Step 6's `uv run pytest -q` will collect and run it, and it raises `FileNotFoundError` from `HarmonizedData.load` rather than skipping when the data is absent.

**Proposed fix.** Copy the shipped guard: `REPO = Path(__file__).resolve().parents[2]`, `STAGED = REPO / "data" / "staged"`, `pytestmark = [pytest.mark.slow, pytest.mark.skipif(not (STAGED / "qcew_monthly.parquet").exists(), reason=...)]`, and drop the "excluded from the default run" claim (or add `-m "not slow"` to addopts, which would change the shipped suite).

### [NIT] plan:4900-4903

**Claim.** Step 5 tells the implementer to record "the own-weight versus establishment-fallback counts per estimator" from the run output, but neither command emits a per-estimator split — the manifest and the echoed lines aggregate over all estimators.

**Evidence.** Task 17's `run-baselines` (plan:4344-4348) computes `basis_counts = {row["weight_basis"]: row["len"] for row in ran.group_by("weight_basis").len().iter_rows(named=True)}` — grouped on `weight_basis` alone — and echoes `f"{basis} {count}"` with no `estimator_id`. The D1 test does compute `ran.group_by(["estimator_id","weight_basis"]).len()` (plan:4844) but only asserts `counts.height > 0` and never prints it. The other four items Step 5 asks for (preferred estimator, decline counts, months gated/anchored, max drift) are genuinely emitted.

**Proposed fix.** Either group the manifest on `["estimator_id", "weight_basis"]` in Task 17, or reword Step 5 to "the own-weight versus establishment-fallback counts per basis".

### [NIT] plan:4747

**Claim.** The golden path and the config path are cwd-relative, contradicting the task's own instruction to follow `tests/integration/test_constraint_golden.py`, whose paths are anchored on the repo root; the tests fail from any working directory other than the repo root.

**Evidence.** plan:4747 `GOLDEN = "tests/fixtures/baselines/baseline_results_golden.parquet"`, plan:4783 `pl.read_parquet("tests/fixtures/baselines/anchor_audit_golden.parquet")`, plan:4807 `load_config(Path("config.yaml"))`. Shipped `test_constraint_golden.py:19-21` uses `REPO = Path(__file__).resolve().parents[2]` / `FIXTURES = REPO / "tests" / "fixtures" / "constraints"` and `load_config(REPO / "config.yaml")`; `test_d1_acceptance.py:19-20` does the same.

**Proposed fix.** Add `REPO = Path(__file__).resolve().parents[2]` to both new files and build every path from it.

### [NIT] plan:4870-4871

**Claim.** The generation script's comment says it freezes a two-year slice while the code freezes twelve months of 2022, and that window cannot exercise the §10.4/2024 decline the golden test's docstring names as one of its two motivating cases.

**Evidence.** plan:4870-4871: `# Freeze a two-year slice so the fixture stays small and readable.` immediately above `window = ['2022-%02d' % m for m in range(1, 13)]` — twelve months, one year. plan:4755 justifies the test with "§10.5 declines on this window by design and §10.4 declines for 2024", but the plan's own evidence section states §10.4 declines only for reference year 2024 (`cbp_state_size` publishes 2017–2023), so on a 2022-only fixture only `harvest_proportional` ever declines and the CBP decline path is never covered by the §17.4 test.

**Proposed fix.** Correct the comment to "a one-year slice". If the §10.4 decline should also be covered, add a 2024 month (e.g. `'2024-03'`, since §10.4 is a March intensity) to `window` — but note in the fixture docstring that 2024 is non-contiguous with 2022 there, so the historical-share estimators fall back inside the fixture where they use real history on the full window.

### [NIT] plan:4839

**Claim.** `assert preferred_estimator(results)` is a truthiness check that passes for any non-empty string, so the test that is supposed to discharge the roadmap's "named preferred transparent baseline slot" is strictly weaker than the unit test of the same function.

**Evidence.** plan:4839 `assert preferred_estimator(results)`; Task 16's unit test at plan:3962 asserts the stronger `preferred_estimator(results) in FALLBACK_ORDER`. As written the D1 test would pass on a returned name that is misspelled, absent from `FALLBACK_ORDER`, or belonged to an estimator that declined in every month.

**Proposed fix.** Assert `preferred_estimator(results) in FALLBACK_ORDER` and that the named estimator actually has `anchored_and_reconciled` rows in `results`.

---

## Why this run was stopped early

The audit subagents wrote into the live working tree rather than a scratch directory. One
overwrote committed `scaling.py` and `test_scaling.py` with the plan's verbatim versions,
reverting the fixes in `ea784f2`; another did the same to `projection.py` after `ba63c69`.
Others left unreviewed `matrix.py`, `integerize.py`, `draws.py` and test files for tasks not yet
executed, inflating the suite from 995 to 1010. Everything was recoverable because each task was
committed before the next began. The run was stopped after 19 units rather than risk further
reverts; Tasks 18 and the remaining cross-cutting units are therefore unaudited.
