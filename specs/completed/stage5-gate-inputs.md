> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# Stage 5 gate inputs: §13.10's strata and §9.3's margins

**Status:** COMPLETE (2026-09-12) — implemented by plan 14
(`specs/plans/completed/14-stage5-gate-inputs.md`). Retired to `specs/completed/`. **R-S5G-2 ruled Option A: §13.10 stands as
written and is not amended.** Both stratum gates now read
`validation_metrics.parquet`'s `stratum_kind = 'census_division'` rows — a per-division WAPE and a
per-division 90% coverage over the nine Census divisions — and §13.6's state-share absolute error
is emitted. The three `PromotionConfig` keys are recorded inert per key rather than read (R-S5G-3,
`D-109`); no evaluator is built before the stage that produces the candidate. §13.10's gate remains
applied over NINE of the thirteen regimes (`D-071`). The shipped artifact matches: `runs/f03023ac9f3a/validation_metrics.parquet` was regenerated under this schema on 2026-09-12 (6,932 rows, 2,132 stratified, at `542ed37`;
first regenerated 2026-09-11, before the review's `n_scored` fix), and its `validation_scoreboard.parquet` came back byte-identical at (270, 13) — see `specs/findings/stage-5-log.md`.
**Evaluable is not yet correct for coverage:** a pre-existing residual-sign defect in §13.7's ensemble
(`D-112`, found 2026-09-12) under-covers biased estimators — down to 0.00 when the bias dominates the residual
spread — so the coverage gate — overall
and per division — MUST NOT be applied until `D-112` lands. WAPE is unaffected.
*→ Resolved 2026-09-12, after retirement: `D-112` landed in `19fbdec` (`residual_ensemble` subtracts the pool), so
the coverage gate no longer waits on it. `runs/f03023ac9f3a` was re-run at `19fbdec`: `validation_metrics.parquet`
kept its 6,932 rows (2,132 stratified) and moved `value` on 1,488, all `probabilistic`; `validation_scores` and the
(270, 13) scoreboard came back byte-identical. The paragraph above is left as written.*

**R-S5G-5's measurement refuted §1.2 below, and R-S5G-8 is therefore NOT closed here.** §1.2
predicted that a disclosed `1133` / `11331` / total-ownership parent would be an EXACT
reconstruction. Measured across all 32 D1 quarters: those parents are disclosed on **0** of the
409 suppressed private state-quarters (a 1:1 chain is suppressed together) and `own_code 0` does
not exist at state x 6-digit — so no MEASURED margin gives `REQ-027`/§14.4 a live instance (`D-110`;
the `113 - 1131 - 1132` path is unmeasured, R-PM-5). What does exist
is a **bound**: `113` is disclosed on **252 of 409** (756 of the 1,227 months), giving
`113310 <= 113`. That is routed to `specs/stage5-parent-margin.md` (`D-111`), not absorbed, and
**Stage 5 MUST NOT consume `deterministic_bounds` as identification-complete until it lands.**
See `specs/findings/qcew-parent-margins.md`.

**§1.4 below overstates what a finite bound activates**, and is corrected here (§1.4 carries an in-place marker):
`D-032` needs `enforce_integrality = false`, and `_needs_milp` also needs an LP width under 25, so a bound sends only its narrow under-threshold subset to MILP (`specs/stage5-parent-margin.md` R-PM-6). Likewise §1.2's
"exact reconstruction" premise did not survive measurement (above).

**Source:** `docs/reviews/2026-09-11-stage14-revisit.md`, items 1 and 2 of its ranked verdict.
That document re-measured both 2026-09-09/10 reviews against `d6591b6` and found these the only
two Stage 1–4 gaps that must be settled before Stage 5 rather than after it. It routes here
rather than to a roadmap stage for the reason `docs/reviews/2026-09-10-review-routing.md` §2
gives: remediation work belongs in the sub-project channel, not in a sequence that is a
dependency graph rather than a chronology.

**Closes (on completion):** `specs/deferred_items.md` `D-091` (the stratum gates) and `D-092`
(the §9.3 margin measurement) are either implemented or their declines recorded.

**Amends:** possibly `specs/logging-employment-spec.md` §13.10 — but only under R-S5G-2's
Option B, and only as that requirement's own recorded output. Nothing here amends the spec
unconditionally.

**Consumed by:** Stage 5, which cannot evaluate §13.10 without R-S5G-1..3 and cannot know its
own identification set without R-S5G-4..6.

---

## 1. Why this exists

Stage 5 fits the state-total Bayesian model and promotes it only if it beats the Stage 4
scoreboard on §13.10's gates. Two of those gates cannot be evaluated at all, and the
identification set the model will be gated against may be wrong by an unmeasured amount. Neither
problem is about Bayesian modelling, and neither is visible from the Stage 5 roadmap block.

**Everything below was measured at `d6591b6` on 2026-09-11.** Re-measure before relying on a
number: this repo treats a written count as a dated witness, not a guarantee.

### 1.1 Two of §13.10's six gates read nothing

§13.10 requires that 90% interval coverage "does not fail catastrophically in any major stratum"
and that "no major stratum degrades by more than 2% WAPE". Measured:

- `validate/metrics.py` emits **18** metric names and not one is stratified —
  `anchor_adding_up_max_abs`, `bias`, `coverage_0.50/0.80/0.90/0.95`, `crps`,
  `exact_recovery_rate`, `integerization_violations`, `mae`, `mean_feasible_width`,
  `mean_interval_width_0.90`, `median_ape`, `n_clipped_at_zero`, `negative_outputs`, `rmse`,
  `truth_in_bound_rate`, `wape`.
- `grep -rn 'stratum\|strat' src/logging_employment/validate/ src/logging_employment/config.py`
  returns three hits, none of them a computation: two comments and
  `PromotionConfig.maximum_major_stratum_wape_degradation`.
- All three `PromotionConfig` fields — `minimum_wape_improvement`,
  `maximum_major_stratum_wape_degradation`, `nominal_coverage_tolerance` — have **zero** `src/`
  consumers. Their only other appearance is `tests/unit/test_config_validation_block.py`
  asserting the literal defaults.

So `config.resolved.yaml` ships a promotion policy no code can apply, and the class docstring
calls them "§13.10's gates. Configurable engineering thresholds, not findings" — a claim the
absence of any reader falsifies.

The strata themselves are not missing from the data. `validate/regimes.py` already carries the
comment that "§13.6's state-share strata, §13.7's required calibration-by-region ... must all
partition on the SAME thing", and state, region and gap-duration exist as columns. What is
missing is the aggregation.

**Why this is Stage 4's gap and not Stage 5's to absorb.** Stage 4's roadmap `Produces` line
claims the §13.5–13.8 metric families, and `REQ-023` is credited to Stage 4 in the gap table.
`specs/completed/stage5-preconditions.md` §2 and §6 explicitly declined to inherit it, filing it
as "R-12, filed under Stage 5" — which is how it came to be owned by a retired document and by
nothing live.

### 1.2 The §9.3 margins were never fetched, declined, or measured

The identification engine bounds no state cell. Measured on the shipped run:

- `deterministic_bounds.parquet`: **1,227** `unbounded` (`selected_upper` null on all 1,227),
  3,534 `observed`, 14 `partially_identified` (national size classes only).
- Re-derived from raw bytes independently of the run directory: `agglvl 58`, `own 5`, excluding
  `area_fips 72000` → 1,572 quarter-rows, of which **409** carry `disclosure_code 'N'`;
  1,572 × 3 = 4,716 cells and 409 × 3 = 1,227 suppressed. The arithmetic closes exactly.
- The raw store holds industry `113310` **only** (59,112 rows, one industry code) and ownership
  codes 3 and 5 only; `own_code 0` row count is **0**. `registry/sources.yaml`'s QCEW endpoint is
  `.../industry/{industry}.csv` and `constants.INDUSTRY_CODE` is the single value `"113310"`.

So §9.3's parent-industry, ownership and region margins were never fetched. Nothing records a
decision either way: the only source-level decline in the system is `SRC-QCEW-006` (the national
state-sum identity), enforced by `constraints/rows.py::assert_no_national_employment_margin`, and
it covers a different margin. `DECLINE_KINDS` is a baseline-row concept, not a source one.

**The consequence is a disclosure question, not a modelling one.** `113310` is the only six-digit
industry under `1133` in both the 2017 and 2022 vintages, and both concordances mark it `1:1`.
With that single-child chain, a disclosed `1133`, `11331` or total-ownership `113310` cell where
`113310` private is `N` is an **exact reconstruction** of the suppressed value, not merely a
bound — a live `REQ-027` / §14.4 case. Suppression is applied per quarter, so one disclosed
parent quarter identifies three months at once.

### 1.3 The settle-before trigger is one stage late

The roadmap does own this, as of `0e186be`. But the sentence — "if any margin is wanted it must
be settled BEFORE this stage consumes `deterministic_bounds`" — sits in the **Stage 6** block,
while the **Stage 5** block's own `Consumes` already reads "Stage 2's `deterministic_bounds`".
A Stage 5 planner reading the artifact they are told to read cannot see the precondition.

### 1.4 What makes the order matter

Both items are cheap now and expensive later, for the same reason: they feed the comparand.

- Measuring a margin after Stage 5 re-opens three things at once — §13.2 step 4's mask in
  `validate/recover.py` (which must retain a parent margin it currently knows nothing about),
  Stage 4's scoreboard numbers, and the §13.10 comparand the model was gated against.
- A finite bound also activates a cluster of latent Stage 2 behaviour that cannot fire today.
  `_needs_milp` skips any cell whose `lower` or `upper` is `None`, so MILP ran on **0 of 4,775**
  rows (`milp_lower` and `milp_upper` are null everywhere; `solver_status` is `unbounded` 1,227 /
  `not_solved` 3,534 / `optimal` 14). `D-093` (the HiGHS `mip_rel_gap`), `D-032` and the §9.6
  width trigger all become reachable the first time a bound is finite. *(Overstated — corrected in the paragraph beneath the Status line: `D-032` needs `enforce_integrality = false`, and MILP also needs an LP width under
  25.)* That is a reason to
  measure the margins *early*, while their consequences are still cheap to absorb.

## 2. Requirements

**R-S5G-1.** A per-stratum WAPE and a per-stratum 90% coverage MUST be computable from what
`validate/` emits, for the strata §13.10's gates name. The stratum definition MUST be the one
`validate/regimes.py` already says all three of §13.6/§13.7/§13.10 must share — do not introduce a
second partition. Emitting the metric is preferred over changing the gate; R-S5G-2 exists for the
case where it is not feasible.

*Why not "let Stage 5 compute it":* Stage 4's `Produces` line claims the §13.5–13.8 families, and
a gate whose input is built by the stage being gated is not an independent test.

**R-S5G-2.** This is a DECISION requirement; its output is a written ruling, not code. Either
(a) the metrics of R-S5G-1 ship and §13.10 stands as written, or (b) §13.10 is amended to the
gates that can be evaluated and the stratum clauses are struck or deferred with a named owner.
The ruling MUST be recorded in `specs/logging-employment-spec.md` (if B) and in this spec's
Status line (either way). A third outcome — shipping Stage 5 with two gates silently unevaluated —
is explicitly refused.

**R-S5G-3.** `PromotionConfig`'s three fields MUST either be read by the promotion code path or be
recorded as inert in the same manner `D-064` records its four keys. A config key that reaches
`config.resolved.yaml` and `run_id` while governing nothing is the defect `F-025` and `D-064`
already name; three more MUST NOT be added to that set silently.

**R-S5G-4.** §13.6's **state-share absolute error** MUST be emitted. It is required "at minimum"
by §13.6, it is meaningful on the `state_total` arm Stage 4 actually scores, and
`validate/metrics.py::_POINT_NAMES` is `("mae", "rmse", "bias", "wape", "median_ape")`. The other
two absentees — size-share absolute error and top-size-class/rank accuracy — are size-class
concepts that §13.6 qualifies "where meaningful"; Stage 4 scores no size arm, so those are
honestly Stage 6's and MUST NOT be built here.

**R-S5G-5.** The §9.3 margin question MUST be **measured**, not ruled on from the armchair. Fetch
the D1 state slices for industries `113`, `1133` and `11331`, and for total ownership
(`own_code 0`) at `113310`, and count month by month how often each is disclosed where private
`113310` is `N`. The measurement is hours of work and is the only open item that can change the
product from 1,227 model-only estimates to some cells identified from public accounting facts.

*Why measure before deciding:* a decline is free to record and costs nothing if wrong in the
conservative direction, but a decline recorded without the measurement is an assertion, and this
repo has a written rule against those (`D-002`'s "no-retabulation premise carried by no cited
source" is the precedent).

**R-S5G-6.** The outcome of R-S5G-5 MUST be recorded in a form a later stage will actually read —
a `Consumes` clause on the affected stage, or a spec amendment, not only a findings file. If the
answer is "no usable margin exists on D1", that sentence MUST state the measured disclosure
pattern that supports it. If a margin does exist, the record MUST name what it changes:
registry rows, new cell kinds, a `size_margin_rows`-style builder, and §13.2 step-4 parent
masking in `validate/recover.py`.

**R-S5G-7.** The settle-before trigger MUST be re-pointed from the Stage 6 block to the Stage 5
block, because Stage 5 is already a `deterministic_bounds` consumer. This is a roadmap edit of one
sentence and is the cheapest requirement here; it MUST NOT be deferred behind R-S5G-5's
measurement, since its whole purpose is to make the measurement visible to the reader who needs it.

**R-S5G-8.** If R-S5G-5 finds a disclosed parent, the `REQ-027` consequence MUST be handled
before any release path can reach those cells: an exactly-reconstructed `N`-flagged cell cannot
reach `release_observed` or `release_model_estimate` without a recorded reviewer decision (§14.4).
`disclosure/` already owns `exact_reconstruction_flag`; this requirement is that the flag is
actually set from the new margin, not that a new mechanism is built.

## 3. Out of scope

- **Everything else the 2026-09-11 re-measurement found.** It is filed as `D-091`..`D-101` in
  `specs/deferred_items.md` with sizes and triggers. In particular `D-093`'s MILP gap and
  `D-095`'s EWMA half-life are NOT requirements here; both are unreachable or non-binding today
  (see §1.4, and `D-095`'s own note that the estimator never wins `preferred_baseline`).
- **The §12.2/§15.2 anchor amendment and Appendix A's residue.** Still owned by
  `specs/completed/stage5-preconditions.md` §6 as normative-text work deserving its own pass.
- **Stage 6's inheritances.** `D-085`, the size-share and rank metrics, and `reconcile_matrix`'s
  missing bounds parameter are correctly Stage 6's and must not be pulled forward.

## 4. How to know this is done

1. A per-stratum WAPE and coverage exist in `validation_metrics.parquet`, or §13.10 no longer
   asks for them and the amendment cites this spec.
2. `PromotionConfig`'s three keys are read by code, or recorded inert beside `D-064`'s four.
3. `state_share_absolute_error` appears in the emitted metric-name set.
4. A sentence somewhere a stage will read states the measured §9.3 disclosure pattern and the
   ruling it supports.
5. The Stage 5 roadmap block names the margin precondition.
6. `uv run pytest` is green, and the validation golden's regeneration (if any) is justified by a
   named behaviour change rather than absorbing one.
