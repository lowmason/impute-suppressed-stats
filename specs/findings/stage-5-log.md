# Stage 5 — log

Dated corrections and measurements for Stage 5's roadmap block. Stage 5 is
unticked; this file exists because its `RE-VALIDATED` text already carried a
stale code pin (roadmap `## Stages`, stage-block rules 1 and 2).

## 2026-09-10 — `assert_declared_provenance` caller count and line were both wrong

**Superseded reading** (roadmap Stage 5 `RE-VALIDATED`, until `1be5bbf`):

> but its only `src/` caller is `baselines/runner.py:218`.

**Why it changed.** There are two callers, and neither is at that line:
`baselines/runner.py:312` and `validate/harness.py:165` (line numbers as recorded at `1be5bbf` and left
as the historical record; both have since drifted, so find the calls by symbol — `run_baselines`
and `run_pseudo_suppression`). The second arrived with
the Stage 4 harness and the block was never re-validated against it.

**Why it mattered.** The clause was load-bearing for the argument that followed
it — that a sixth reconciliation status invented by Stage 5 would go unchecked.
With two callers, one of them inside the validation harness, the blast radius of
a new status is larger than the block claimed.

**Standing hazard.** This is the pattern `specs/logging-employment-spec.md` and
this repo's `CLAUDE.md` both warn about: a `file:line` pin is a dated witness.
Prefer naming the symbol and letting the reader grep.

## 2026-09-11 — the §9.3 settle-before trigger was attached to the wrong stage

**Superseded reading** (roadmap Stage 6 `Consumes`, until this plan):

> if any margin is wanted it must be settled BEFORE this stage consumes `deterministic_bounds`

**Why it changed.** The sentence was true of Stage 6 and also of Stage 5, and only
Stage 6 carried it. Stage 5's own `Consumes` already reads "Stage 2's
`deterministic_bounds`", so a Stage 5 planner reading the artifact they are told to
read could not see the precondition attached to it. R-S5G-7.

**Why it mattered.** The trigger guards an ORDER, and a trigger one stage late does
not guard anything: by the time Stage 6 reads it, Stage 5 has already been gated
against the identification set the measurement might change.

## 2026-09-11 — the §9.3 margins, measured: a bound exists on 252 of 409

**Measurement** (R-S5G-5; `scripts/audit/qcew_parent_margins.py`, 128/128 slices at 200,
rendered in full at `specs/findings/qcew-parent-margins.md`):

| | |
|---|---|
| private `113310` state-quarters / suppressed | 1,572 / 409 — the 2026-09-11 witness holds |
| `113` disclosed where the child is `N` | **252** (61.6%; 756 of the 1,227 months) |
| `1133`, `11331` disclosed where the child is `N` | **0** each |
| `own_code 0` rows at state x 6-digit | **0** — a measured absence, `fetched: true` beside it |
| `exact` / `upper_bound` / `none` | **0 / 252 / 157** |

**Superseded reading** (`specs/completed/stage5-gate-inputs.md` §1.2, and `D-092` as filed):

> With that single-child chain, a disclosed `1133`, `11331` or total-ownership `113310` cell
> where `113310` private is `N` is an **exact reconstruction** of the suppressed value

**Why it changed.** The inference was sound and its antecedent is false. `1133` and `11331` are
disclosed on 1,163 of 1,572 state-quarters — and on **zero** of the 409 where the child is
suppressed. A 1:1 chain is suppressed *together*: that is what makes the chain safe for BLS to
publish at all. The exact-reconstruction hazard the spec anticipated does not arise through ANY MEASURED margin
on D1. It is not ruled out: `113 - 1131 - 1132` was not measured (`D-110`), so on the 252 bounded
quarters `REQ-027`'s status is unknown rather than absent.

**What is real instead.** `113` aggregates `1131` and `1132` as well, so it survives the
suppression that kills the chain below it, and it is disclosed on 252 of the 409. By
nonnegativity of the two siblings that is `113310 <= 113` — §9.3's parent-total constraint
doing real work on **61.6%** of the cells the engine currently leaves at `[0, +inf)`.

**Why `exact = 0` is measured, not constructed.** `identification` maps a disclosed `113` to
`UPPER_BOUND` by its ladder, which would understate a `'-'` parent — a published true zero forces
the child to exactly 0. Derived from the stored extracts: 3 of the 1,278 disclosed `113` private
state-quarters carry `'-'`, and **0** of those falls on a suppressed quarter. The ladder is not
hiding an exact case.

**Why it mattered.** Stage 4's scoreboard and `runs/f03023ac9f3a` were computed against an
identification set with no finite state upper bound anywhere. A finite upper bound on 756 months
makes those cells ELIGIBLE for MILP, which has run on 0 of 4,775 rows. `_needs_milp` also requires
the LP width to fall below 25, so `D-093`'s gap binds only on the narrow subset the finding derives.

**Not measured, and named rather than assumed.** `113 - 1131 - 1132 = 1133`, and the chain below
`1133` is 1:1 — so a quarter with all three disclosed is an *exact* reconstruction. `1131` and
`1132` are outside R-S5G-5's named scope and were not fetched. `specs/completed/stage5-parent-margin.md`
owns that measurement.

## 2026-09-11 — `runs/f03023ac9f3a` validation artifacts regenerated under the stratum schema

**Command:** `uv run logging-estimates validate --config config.yaml` (11 min wall clock), after
plan 14 Task 5 appended `stratum_kind` / `stratum_value` to `VALIDATION_METRIC_SCHEMA`. The run id
did not move — `run_id` hashes config and inputs, not source — so the same directory was
overwritten. The prior four validation files were backed up first and compared by join, not by
position.

| artifact | before | after |
|---|---|---|
| `validation_scoreboard.parquet` | (270, 13) | **byte-identical** |
| `validation_scores.parquet` | — | **byte-identical** |
| `validation_metrics.parquet` | (4,530, 19) | (6,929, 21): 4,800 `overall` + 2,129 `census_division` |

On the 4,530 pre-existing rows, joined on the six-field key with `nulls_equal=True`: 0 unmatched on
either side, and exactly one column moved.

**The column that moved was stale, not regressed.** `interval_source` read
`rolling_residual_ensemble` on 1,190 rows before and `leave_one_out_residual_ensemble` on the same
1,190 after. That rename is `e17b1f0` (plan 13, R-S5P-7, 2026-09-10). **The §13.10 comparand's
metrics file had therefore been stale with respect to the code since plan 13**, carrying the label
R-S5P-7 exists to retire, and nothing noticed — the standing hazard of a run id that ignores
source. The `null` count rose 3,240 -> 3,510, i.e. +270, exactly the new
`state_share_absolute_error` rows, which carry no interval.

**Why the scoreboard matters most.** Its byte-identity is Task 5's fan-out guard holding on D1
rather than on the fixture: 2,129 stratified rows entered the metrics frame and the board did not
grow a single row. §13.10's promotion comparand is unchanged.

**Provenance caveat.** The new `validation_manifest.json` records
`code_commit = c5bb7ca…-dirty`. The dirt was one untracked file,
`scripts/audit/render_parent_margins.py`, outside `src/`; no package code differed from `c5bb7ca`.

## 2026-09-12 — regenerated again under the review's `n_scored` fix

**Command:** `uv run logging-estimates validate --config config.yaml` at `542ed37`, whose manifest
records a CLEAN `code_commit` (no `-dirty`). The four validation files were backed up first and
compared by join on the eight-field key (the six old fields plus `stratum_kind`/`stratum_value`).

| artifact | at `c5bb7ca-dirty` (entry above) | at `542ed37` |
|---|---|---|
| `validation_scoreboard.parquet` | (270, 13) | **byte-identical** |
| `validation_scores.parquet` | — | **byte-identical** |
| `validation_metrics.parquet` | (6,929, 21) | (6,932, 21): 4,800 `overall` + 2,132 `census_division` |

**0 rows lost, 3 added, one column moved.** The 3 added rows are null `coverage_0.90` rows for
divisions whose masked cells never reached a leave-one-out ensemble — the whole-branch review found
the coverage family omitting divisions the WAPE family emitted. The column that moved is `n_scored`,
on **717 of the 782** division coverage rows: those rows had inherited the estimator-wide scored
count, and `n_scored > denominator` held on 717 of them before and on **0** after.

**This supersedes the counts in the entry above.** Its 6,929 / 2,129 were the defect's shape — the
right rows with a wrong column — not a correct artifact. The byte-identical scoreboard is again the
check that matters: §13.10's promotion comparand did not move across either regeneration.

## 2026-09-12 — §13.7's residual ensemble has the wrong sign (`D-112`)

**Found by** plan 14's review-verification pass, while checking whether plan 14's new per-division
coverage oracle was independent of the code. **Not introduced by plan 14:** present since `8939026`
(2026-09-07, Stage 4).

`probabilistic_metrics` pools `estimate - truth`, and `residual_ensemble` ADDS the pool to the point
estimate, so cell i's ensemble is `estimate_i + (estimate_j - truth_j)`. The predictive distribution of
`truth_i` is `estimate_i - (estimate_j - truth_j)`. Measured with the shipped `intervals` helpers on a
synthetic 40-cell method (`default_rng(0)`,
truth ~ U(80, 120), estimate = 1.25 x truth + N(0, 3)): 90% coverage **0.00** as shipped, **0.85** with
the sign corrected. On an unbiased method the two agree to sampling noise (0.90 vs
0.85). The oracles do not pass because of symmetry — both COPY the code's expression. On the golden
fixture the residuals are one-sided (62.2% positive in the oracle group), and the corrected sign
changes `coverage_0.90` in 37 of 43 interval-bearing groups, the hand-derived oracle's from 33 to 31
of 37.

**Why it matters for Stage 5.** Plan 14 made §13.10's coverage gate evaluable; this makes its values
untrustworthy for exactly the estimators a gate exists to catch. WAPE and the (270, 13) scoreboard are
unaffected. Recorded as a Stage 5 precondition in the roadmap block rather than fixed in plan 14,
because the fix changes Stage 4's shipped probabilistic numbers.

## 2026-09-12 — `D-112` fixed: the residual ensemble subtracts the residual

**Fixed in** `19fbdec` (`fix/d112-residual-sign`). `intervals.residual_ensemble` returns `point - residual`;
the pool in `probabilistic_metrics` stays `estimate - truth`, so the orientation has one owner. The failing
tests were written first from `truth = estimate - residual` and observed red on the old sign: a one-sided
helper pool, a constant +25 bias (coverage 0.0 on the old sign, 1.0 corrected, at every level) and a
hand-derived zero-clip count (0 old, 3 corrected). **Every probabilistic value in the artifacts the entries
above describe was computed on the old sign;** those entries quote none apart from `D-112`'s own, whose
golden predictions are confirmed below.

**Golden** `2bec94b0…` → `a544559f…`, by join on the eight-field key: 0 key-only rows, and only `value`
moved, on 279 of 1,490 rows, all `probabilistic`; the fixture run's scores and scoreboard are
byte-identical. `coverage_0.90` moved in 37 of 43 interval-bearing groups and the hand-derived oracle went
33 → 31 of 37, both as `D-112` predicted; it also moved in 40 of 72 division rows.

**`runs/f03023ac9f3a`** re-run at `19fbdec` (clean tree, 12 min 08 s), its artifacts backed up first:

| artifact | before (`542ed37`) | after (`19fbdec`) |
|---|---|---|
| `validation_scores.parquet` | `4d9912fb…` | byte-identical |
| `validation_scoreboard.parquet` | `d4e1187b…`, (270, 13) | byte-identical |
| `validation_metrics.parquet` | `9f6b6a75…` | `049ecbec…` |

Apart from `code_commit` and the metrics digest in the table, the manifest is unchanged. By join on the same key: 6,932 rows and 2,132
stratified on both sides, 0 key-only rows, and only `value` moved — on 1,488 of the 2,072 `probabilistic`
rows and on no other family. Overall `coverage_0.90` moved in 154 of 170 interval-bearing groups (rose 132,
fell 22) and in 455 of 782 division rows; `crps` in all 170; `n_clipped_at_zero` in 103;
`mean_interval_width_0.90` beyond 1e-9 in 104, every one where the zero clip binds on either side (elsewhere
at most 7.4e-13). Coverage stays monotone in level in all 170 groups.

**What Stage 5's coverage gate will see.** The corrected intervals still UNDER-cover. Over the 170 groups,
overall 90% coverage moved from mean 0.35 to 0.76 and median 0.25 to 0.80, and its maximum is now exactly
0.90, so no group over-covers. Counted exactly — coverage is hits over `calibration_sample_size`, a rational
— 51 groups sit within `nominal_coverage_tolerance` (0.05) of nominal, 44 of them on the boundary at 17/20,
against 25 under the old sign (14 at 17/20, one at 19/20); strictly inside the band it is 7 against 10, and
119 groups sit more than 0.05 below nominal (145 before). **A float comparison miscounts this:**
`abs(0.85 - 0.9)` is `0.05000000000000004`, so `abs(c - 0.9) <= 0.05` drops all 44 boundary groups and
reports 7 (recorded against `D-109`, which owns the unbuilt gate). The seven interval-bearing estimators'
means land between 0.75 and 0.77, where the old sign spread them from 0.16 to 0.68. The intervals are cross-sectional leave-one-out rather than §10.7's
rolling ones (`R-S5P-7`), which this fix does not change.

## 2026-09-13 — R-PM-5 measured: the sibling path reconstructs nothing, so R-PM-4 does not bind

`scripts/audit/qcew_parent_margins.py` now walks `1131` and `1132` with the other four industries and
judges them with the same ladder (plan 15 Task 1); `specs/findings/qcew-parent-margins.md` is the
rendering. On the 252 suppressed private `113310` state-quarters a published `113` bounds, all of
`113`, `1131` and `1132` are published on **0**, and on
**0** when a missing sibling row is read as zero
establishments. The ladder's tally is exact 0, upper bound 252, none
157.

**Ruling on R-PM-4:** no measured margin, whether parent, ownership or sibling, reconstructs a suppressed
state-quarter, so `exact_reconstruction_flag` keeps no live instance and the parent margin enters the
constraint system as a bound only. `D-110` closes on this measurement. One sibling is published on
17 of the bounded quarters, which would tighten the bound to
`113 - sibling`; no row builds it, and plan 15's completion files that as its own item.

## 2026-09-13 — R-PM-7: the comparand re-run against the bounded identification set

`runs/4cf47a918dd8` (plan 15 Task 9) against `runs/f03023ac9f3a`, compared by join on each table's key,
never by position. R-PM-7's answer is that the comparand IS re-run: Task 4 re-ids every run, and both
the production runner and the harness now read bounds (Decisions 3 and 6), so every estimate a bound
binds on moves. The rows below are that movement, derived. `runs/f03023ac9f3a` stays on disk as Stage 4's
acceptance run; Stage 5's §13.10 promotion compares against `runs/4cf47a918dd8`.

| `baseline_results` | value |
|---|---|
| rows old / new | 12270 / 12270 |
| key-only rows old / new | 0 / 0 |
| estimates moved beyond 1e-09 | 10870 |
| estimator-months with a moved estimate | 850 |
| estimates now exactly at a finite upper bound | 3391 |

Moved estimates by estimator: `cbp_intensity` 1054, `constrained_regression` 1227, `equal_residual` 1227, `establishment_proportional` 1227, `share_break_adjusted` 1227, `share_exponentially_weighted` 1227, `share_last_observed` 1227, `share_rolling_median` 1227, `share_same_month_prior_year` 1227.

| `validation_scores` | value |
|---|---|
| rows old / new | 12530 / 12530 |
| key-only rows old / new | 0 / 0 |
| scored rows with a finite `selected_upper`, old / new | 0 / 9690 |
| estimates moved beyond 1e-09 | 5917 |

| `validation_scoreboard` | value |
|---|---|
| rows old / new | 270 / 270 |
| key-only rows old / new | 0 / 0 |
| WAPE moved beyond 1e-09 | 224 |
| WAPE change, min / median / max | -0.6543 / -0.0969 / 8.0117 |

| regime | preferred baseline, old | new |
|---|---|---|
| `clustered_states_within_month` | `share_last_observed` | `share_last_observed` |
| `concentration_proxy` | `share_last_observed` | `constrained_regression` |
| `long_consecutive_runs` | `cbp_intensity` | `cbp_intensity` |
| `naics_transition` | `cbp_intensity` | `cbp_intensity` |
| `regional_blocks` | `share_last_observed` | `share_same_month_prior_year` |
| `small_cell_biased` | `cbp_intensity` | `share_last_observed` |
| `structural_break` | `cbp_intensity` | `share_exponentially_weighted` |
| `whole_seasonal_blocks` | `cbp_intensity` | `cbp_intensity` |
| `whole_state_year_blocks` | `cbp_intensity` | `cbp_intensity` |

`validation_metrics`: 6932 / 6932 rows, key-only 0 / 0; `value` moved on 3662: `deterministic_bounds` 250, `point` 2392, `probabilistic` 1020.
Exactly recoverable targets rejected from scoring (§13.2 step 6): 0. `validation_manifest.json` records `code_commit` `0e473e9dcadf645f8acb5e63ff6e2323d87b7615`.

### Added by plan 15's final review (derived from the run directories)

The tables above were re-measured after the review's fixes; `validation_manifest.json` records `code_commit` `0e473e9dcadf645f8acb5e63ff6e2323d87b7615`.

| `disclosure_flags` | `runs/f03023ac9f3a` | `runs/4cf47a918dd8` |
|---|---|---|
| `narrow_feasible_interval_flag`, by cell kind | `national_size` 1 | `national_size` 1, `state_total` 23 |
| `exact_reconstruction_flag` | 0 | 0 |

The new narrow flags are parent-bounded state cells with `selected_upper` between 2 and 10. A `[0, U]` interval's relative width is 2, so only the absolute arm fires (`narrow_interval_absolute_width: 10`), and `narrow_interval_action: manual_review` routes each to §9.8 review.

**What the WAPE movement is.** Over the 5932 scored rows with an estimate in both runs, the absolute error summed 2,180,827 before and 1,315,134 after, a net 537,515 employees of estimate moved INTO scored targets, and 0 estimates exceed a finite cap. By regime (a scoreboard row counts as worse or better when its WAPE moves by more than 0.05):

| regime | worse | better | median change | max change |
|---|---|---|---|---|
| `clustered_states_within_month` | 0 | 11 | -0.0300 | +0.0067 |
| `concentration_proxy` | 0 | 26 | -0.1473 | -0.0301 |
| `long_consecutive_runs` | 19 | 2 | +0.2669 | +0.8864 |
| `naics_transition` | 0 | 23 | -0.1017 | -0.0093 |
| `regional_blocks` | 0 | 14 | -0.0808 | +0.0372 |
| `small_cell_biased` | 0 | 21 | -0.1160 | +0.0041 |
| `structural_break` | 0 | 22 | -0.0892 | -0.0097 |
| `whole_seasonal_blocks` | 0 | 6 | -0.1858 | -0.0058 |
| `whole_state_year_blocks` | 3 | 20 | -0.1399 | +8.0117 |

The largest rise, +8.0117 on `whole_state_year_blocks` seed 4096 `equal_residual`, is 12 scored targets with a summed truth of 62, 0 of them with a finite upper bound and 12 above their truth, receiving +496.7 employees of estimate. Clamping an estimate to a valid bound cannot raise the absolute error summed over every suppressed cell of a month -- a capped cell loses exactly the mass the others gain, and stays at or above its truth -- but the harness scores only masked targets. A capped REAL suppression's improvement is unscored, while the mass it sheds lands on scored ones.

**§13.10 caveat.** A masked target's score now depends on which bounds bind on the other cells of its month, so masked-target WAPE is not comparable across runs with different identification sets: read `runs/f03023ac9f3a` and `runs/4cf47a918dd8` as different comparands, not as one comparand improved.

**What the review's fixes moved** (the pre-review run at `code_commit` `bc0498aa1f96e6ec765ae9d1eefabf5fdd98b169`, kept aside, against this one):

| quantity | pre-review / final |
|---|---|
| reconcile `max_residual_drift` | 9.932e-10 / 4.547e-13 (Stage 4's comparand: 4.547e-13) |
| `baseline_results` key-only rows | 0 / 0 |
| `baseline_results` estimates moved beyond 1e-09, largest change | 0, 7.637e-10 |
| `validation_scores` estimates moved beyond 1e-09, largest change | 0, 9.068e-10 |
| `validation_scoreboard` WAPE, largest change | 5.906e-12 |
| `validation_metrics` `value` moved beyond 1e-09, by family | `probabilistic` 1 |

## 2026-09-13 — superseded Stage 5 roadmap reading (stage-block rule 1)

Plan 15 Task 10 replaced this span of the Stage 5 block, which treated `D-111` as pending:

> **The §9.3 margins are a precondition of THIS stage, not Stage 6's.** Every one of the 1,227 suppressed state cells is `[0, +inf)` in the SHIPPED `deterministic_bounds` — `selected_upper` null on all 1,227 — because no parent-industry or ownership margin has ever entered the constraint system. This stage consumes `deterministic_bounds`, so the question is settled before it, by `specs/completed/stage5-gate-inputs.md` R-S5G-5. **MEASURED 2026-09-11: a margin EXISTS and the shipped identification set is therefore incomplete.** Of the 409 suppressed private state-quarters, **252 (61.6%, 756 of the 1,227 months) carry a disclosed private `113` parent**, which bounds `113310` above by nonnegativity of `1131` and `1132`; **0 are exactly reconstructed** — `1133` and `11331` are disclosed on 0 of 409 because the single-child chain is suppressed together, `own_code 0` does not exist at state x 6-digit (a measured absence, not an unfetched one), and no disclosed `113` parent on a suppressed quarter is a `'-'` true zero. No MEASURED margin therefore gives REQ-027/§14.4 a live instance (`D-110`) — but the `113 - 1131 - 1132` path was not measured, so on the 252 bounded quarters exactness is unknown rather than absent. The BOUND is not absorbed here: it needs a `registry/sources.yaml` row per new slice, new cell kinds and a `rows.size_margin_rows`-style parent-margin builder in `constraints/`, a §13.2 step-4 rule in `validate/recover.py` for when the parent stays visible under the synthetic pattern (it is public on 252 of 409 real suppressions, so hiding it always would score methods under harder identification than production — today that moves §13.5's bound metrics and `validation_scores`' `selected_*` columns, not WAPE, coverage or the scoreboard, since baselines never read masked bounds (`D-087`); step 6 labels any exact case), and it makes `D-093`'s MILP gap reachable for the bounded cells whose LP width falls below §9.6's threshold of 25 — `_needs_milp` needs a finite `upper` AND that width, which is why MILP has run on 0 of 4,775 rows. Routed to `specs/stage5-parent-margin.md`; **Stage 5 MUST NOT consume `deterministic_bounds` as identification-complete until that spec lands.** See `specs/findings/qcew-parent-margins.md`; `specs/findings/stage-5-log.md` carries the history.
