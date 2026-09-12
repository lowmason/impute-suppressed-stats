# Stage 5 — log

Dated corrections and measurements for Stage 5's roadmap block. Stage 5 is
unticked; this file exists because its `RE-VALIDATED` text already carried a
stale code pin (roadmap `## Stages`, stage-block rules 1 and 2).

## 2026-09-10 — `assert_declared_provenance` caller count and line were both wrong

**Superseded reading** (roadmap Stage 5 `RE-VALIDATED`, until `1be5bbf`):

> but its only `src/` caller is `baselines/runner.py:218`.

**Why it changed.** There are two callers, and neither is at that line:
`baselines/runner.py:312` and `validate/harness.py::run_pseudo_suppression`. The second arrived with
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

**Superseded reading** (`specs/stage5-gate-inputs.md` §1.2, and `D-092` as filed):

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
`1132` are outside R-S5G-5's named scope and were not fetched. `specs/stage5-parent-margin.md`
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
