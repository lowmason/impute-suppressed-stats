# Stage 4 — log

Dated corrections and measurements for Stage 4's roadmap block (roadmap
`## Stages`, stage-block rules 1 and 2).

## 2026-09-10 — `Exit` described enforcement the harness does not do

**Superseded reading** (roadmap Stage 4 `Exit`, from derivation until `1be5bbf`):

> the harness rejects a mask whose target remains exactly recoverable; a
> pseudo-hidden truth falling outside the deterministic bounds fails the run as a
> constraint-data bug (§13.5); the scoreboard covers every §13.3 regime and scores
> primary-like and complementary-like cells separately; a rolling-origin run
> provably contains no future-period rows; …

**Why it changed.** Four of those five clauses were false at the tick.

- **No rejection, no failure.** `is_exactly_recoverable` (`validate/recover.py:67`)
  and `mask_and_solve_size` (`:80`) have no caller anywhere in `src/`.
  `validate/harness.py` raises only `ConceptViolationError` (`:76`, `:296`),
  never on recoverability or on a bound violation. What ships is *measurement*:
  `validate/metrics.py:45,52` emit `truth_in_bound_rate` and
  `exact_recovery_rate` as metric rows, both present in
  `runs/f03023ac9f3a/validation_metrics.parquet`.
- **Not every regime.** Nine of thirteen score, measured from
  `runs/f03023ac9f3a/validation_scoreboard.parquet`: `clustered_states_within_month`,
  `concentration_proxy`, `long_consecutive_runs`, `naics_transition`,
  `regional_blocks`, `small_cell_biased`, `structural_break`,
  `whole_seasonal_blocks`, `whole_state_year_blocks`. The other four score
  nothing — `rolling_origin` and `cbp_size_gaps` (`D-071`),
  `retrospective_smoothing` and `preliminary_to_final_vintage` (`D-086`).
- **One arm, one label.** `validation_metrics.parquet`'s `mask_arm` column holds
  exactly one value, `state_total`, and only primary-like cells are scored.

The unenforced rules are now owned: `D-085` targets Stage 6, the first stage with
a size-class estimator, where both can first fire. Note they cannot fire on D1 at
all — every state cell is `unbounded` with a null `selected_upper`.

## 2026-09-10 — `SHIPPED` said the metric arm is hardcoded

**Superseded reading** (roadmap Stage 4 `SHIPPED`, until `1be5bbf`):

> every metric emit site in `validate/harness.py` hardcodes `arm="state_total"`
> and neither wrapper has a caller in `src/`, so no shipped run has produced a
> two-arm scoreboard.

**Why it changed.** `validate/harness.py:157` computes `arm = _mask_arm(targets)`
and passes it to all four emit sites (`:170-173`). The *conclusion* was right and
survives — no shipped run has produced a two-arm scoreboard — but for a different
reason: the size-arm wrappers have no caller, so `_mask_arm` only ever sees
state-total targets.

## 2026-09-10 — the heading carried no completion suffix

Stages 0–3 carry `— COMPLETE <date>, plan N`; Stage 4's heading carried none from
the tick (`771dabe`, 2026-09-07 17:34) until `1be5bbf`. It now reads
`— COMPLETE 2026-09-09, plans 11 and 12`, taken from the spec stamp, which
derive-roadmap §5 makes authoritative. The plural is deliberate and is the first
in this roadmap: two plans shipped this stage.

This resolves the review's Q-02 ("which of the three completion dates is
authoritative"): the stamp's, 2026-09-09. The `SHIPPED` line's `2026-09-07` is the
date plan 11 retired, not the date the stage completed.

## 2026-09-10 — Stage 4's `Gap closed:` claimed REQ-022, which it did not close

**Superseded claim** (roadmap Stage 4 `Gap closed:`, until this entry):

> REQ-013 (§10.7 intervals), REQ-021, REQ-022, REQ-023, REQ-024 (scoreboard)

**Why it changed.** REQ-022 (`specs/logging-employment-spec.md:2142`) is *"Separate
rolling forecasts and retrospective smoothing."* Measured from
`runs/f03023ac9f3a/validation_manifest.json`, BOTH of its named regimes score zero:

| Regime | Disposition | `n_scored` |
|---|---|---|
| `rolling_origin` | `feasible` | 0 |
| `retrospective_smoothing` | `vacuous_on_registry` | 0 |
| `cbp_size_gaps` | `feasible` | 0 |
| `preliminary_to_final_vintage` | `cannot_run_on_d1` | 0 |
| the other nine | `feasible` | 120–8,690 |

The stage's own `Exit:` line was already honest — it says nine of thirteen score and
names `rolling_origin` and `cbp_size_gaps`. Only `Gap closed:` disagreed, and a
requirement listed there is one a reader takes as discharged.

**The ruling (2026-09-10, Option B of plan 13 Task 9).** REQ-022 is struck from
Stage 4's `Gap closed:` and named in Stage 5's `Consumes:` as still open. The four
regimes are **declared-but-unscored by decision**, not by oversight: `rolling_origin`
would need a target selector applied to the truncated frame, and `cbp_size_gaps` the
CBP gap composed with a QCEW mask, since dropping CBP alone changes only
`cbp_intensity`'s availability and produces no scored cell on its own. Both are
design work, and neither was worth blocking Stage 5's planning on.

**Consequence to carry forward:** Stage 5's §13.10 promotion gate is applied over
NINE regimes, and the record now says so rather than implying thirteen. `D-071` and
`D-086` are closed by this ruling.
