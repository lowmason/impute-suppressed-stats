# Stage 5 — log

Dated corrections and measurements for Stage 5's roadmap block. Stage 5 is
unticked; this file exists because its `RE-VALIDATED` text already carried a
stale code pin (roadmap `## Stages`, stage-block rules 1 and 2).

## 2026-09-10 — `assert_declared_provenance` caller count and line were both wrong

**Superseded reading** (roadmap Stage 5 `RE-VALIDATED`, until `1be5bbf`):

> but its only `src/` caller is `baselines/runner.py:218`.

**Why it changed.** There are two callers, and neither is at that line:
`baselines/runner.py:312` and `validate/harness.py:165`. The second arrived with
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
