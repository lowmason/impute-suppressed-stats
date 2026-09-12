> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# The §9.3 parent-industry margin: turning a measured disclosure into a bound

**Status:** NOT STARTED — requirements input for `writing-plans`.

**Measured input.** `specs/findings/qcew-parent-margins.md` (2026-09-11), produced by
`scripts/audit/qcew_parent_margins.py` over 128 QCEW slices, all 200 and all parsable. Its three
load-bearing numbers:

- **252 of the 409** suppressed private `113310` state-quarters — **756 of the 1,227 suppressed
  monthly cells** — have a **disclosed private `113` parent**. By nonnegativity of `1131` and
  `1132`, that is `113310 <= 113`: a finite upper bound where the shipped
  `deterministic_bounds.parquet` carries `+inf`.
- **0** are exactly reconstructed. `1133` and `11331` are disclosed on **0 of 409** (a 1:1 chain
  is suppressed together), `own_code 0` does not exist at state x 6-digit, and no disclosed `113`
  parent on a suppressed quarter is a `'-'` true zero. No MEASURED margin gives `REQ-027`/§14.4 a live instance (`D-110`) — but
  the `113 - 1131 - 1132` path was NOT measured (R-PM-5), so on the 252 bounded quarters exactness
  is **unknown**, not absent. This spec must neither assume an exact case nor rule one out.
- The bound is **not vacuous on the published distribution**. On the 3,069 month-observations
  where `113310` and `113` are BOTH disclosed, `113310 / 113` has median **0.916** (5th pct 0.659).
  That describes disclosed pairs. The bounded cells are suppressed ones — a different population,
  since small cells are the ones suppressed — so R-PM-8 forbids reading 0.916 as the bound's
  tightness on them.

**Routed from** `specs/stage5-gate-inputs.md` R-S5G-6/8 and plan 14 Task 8. It is NOT absorbed
into plan 14 because R-S5G-8's own scope line is "the flag is actually set from the new margin,
not that a new mechanism is built", and a bound *is* a new mechanism: new source rows, new cell
kinds, a new constraint builder, a change to §13.2's mask, and a re-check of what
the comparand depends on (R-PM-7).

**Consumed by:** Stage 5. **Stage 5 MUST NOT consume `deterministic_bounds` as
identification-complete until this lands** — the roadmap's Stage 5 `Consumes` says so.

**Closes (on completion):** `D-111`. Makes `D-093` reachable for the bounded cells whose LP width
falls below §9.6's MILP threshold (R-PM-6).

---

## 1. Why this is not a small change

Every consequence below follows from one fact: today **no state cell has a finite upper bound**,
and a great deal of shipped behaviour is latent because of it.

- **MILP has run on 0 of 4,775 rows** (`milp_lower`/`milp_upper` null everywhere; `solver_status`
  is `unbounded` 1,227 / `not_solved` 3,534 / `optimal` 14). `_needs_milp` has three gates, not
  one: `enforce_integrality`, a finite `lower` AND `upper` on an integer cell, and an LP width
  below `use_milp_when_lp_interval_width_below` (25 in `config.yaml`). The 1,227 state cells fail
  the second; the 14 finite national cells fail the third (widths 130–894). A parent bound opens
  the second gate on the bounded cells, and only those whose new width is under 25 reach MILP —
  `specs/findings/qcew-parent-margins.md` derives how many that is on the measured `113` values.
- §13.2's mask in `validate/recover.py` knows nothing about a parent, and §13.2 step 4 says to
  "retain only the margins that would remain public under the synthetic pattern". On D1 a
  private `113` stays public on 252 of the 409 real suppressions. A mask that ALWAYS hides `113`
  with the child is therefore as wrong as one that never does: the first scores methods under harder identification than production (on today's call
  graph that moves §13.5's bound metrics and `validation_scores`' `selected_*` columns, not WAPE,
  coverage or the scoreboard, because baselines never read masked bounds — `D-087`), and the second can
  leave an exactly-recoverable case (a visible parent with disclosed siblings) unlabelled, which
  step 6 forbids. A visible `113` alone gives `113310 <= 113` and recovers nothing, so it is not a
  §13.4 leak.
- Stage 4's scoreboard and `runs/f03023ac9f3a` were computed against the unbounded set. Their
  numbers are the §13.10 comparand Stage 5 is promoted against.

## 2. Requirements

**R-PM-1 (registry and ingest).** Each new slice MUST get a `registry/sources.yaml` row carrying
the same measured-or-`[documented]` provenance every existing row carries, and the fetch route
MUST reuse `ingest/qcew.py`'s dual-route interface rather than introduce a second client. Note
that the parents are served at **their own digit-depth agglvl codes** — measured `55` for `113`,
`56` for `1133`, `57` for `11331` — and NOT at `constants.QCEW_STATE_AGGLVL` (`58`). A route that
filters on `58` returns zero parent rows and reads as a clean absence; the audit script discovers
the level instead, and the ingest path MUST do the same or record the codes as measured facts. Ingesting the state `113`
series also unblocks §13.2 step 1's "parent share" predictor, which `validate/propensity.py`
declines today for want of it. An EMPLOYMENT share contains the hidden target (§13.4) and would
need a leave-one-out form; an establishment-count share needs only the ingest, because establishment
counts are published even where employment is suppressed.

**R-PM-2 (constraints).** New cell kinds for the parent margins, and a builder in the shape of
`constraints/rows.py::size_support_rows` / `size_margin_rows`. The parent row is a
`published_value` restriction, not an `assumed_threshold`. `assert_no_national_employment_margin`
guards a **different** margin (`SRC-QCEW-006`, the national/state-sum identity) and MUST keep
guarding it — this spec does not weaken it and must not be read as doing so.

**R-PM-3 (§13.2 steps 4 and 6).** `validate/recover.py` MUST decide the parent's visibility under the
synthetic pattern, per step 4 — NOT hide it unconditionally. A visible `113` gives only
`113310 <= 113` and does not recover the held-out value, so leaving it public is not a §13.4 leak:
it reproduces what production sees on 252 of 409 real suppressions, and hiding it always would score methods under harder identification than production. On today's call graph that moves §13.5's bound metrics and `validation_scores`' `selected_*`
columns, not WAPE, coverage or the scoreboard — baselines never read masked bounds (`D-087`) — but any method that clips to them, such as Stage 5's reconciled draws, would be
handicapped. The pattern MUST be stated and justified — e.g. a co-suppression propensity on public
predictors fitted to the measured pattern (157 of 409 real suppressions have no disclosed `113`); a flat rate must justify why co-suppression would be independent of the child's share of the
parent, which nothing measured yet supports.
Step 3's complementary cells MUST be chosen so parent-minus-siblings does not trivially recover the
target; where a visible parent plus disclosed siblings still recovers the child EXACTLY (R-PM-5),
step 6 applies: reject or separately label the case. Once the bound is finite, §13.5's out-of-bounds
rule — a pseudo-hidden truth outside `deterministic_bounds` fails the run as a constraint-data bug —
becomes live on the state-total arm too, and is this requirement's to wire, not Stage 6's. `D-087` (bounds unenforced on the validation path) is adjacent
and should be settled in the same pass.

**R-PM-4 (disclosure).** `disclosure/`'s `exact_reconstruction_flag` MUST be set from **exact**
cases only. No MEASURED margin yields one today (R-PM-5's sibling path is unmeasured), so this requirement is
**conditional and must not invent one**:
an `upper_bound` case is a bound, and a bound MUST NOT reach `release_observed` or
`release_model_estimate` through this route (§14.4). If R-PM-5 finds an exact case, this
requirement binds for real.

**R-PM-5 (the unmeasured sibling path).** `113 - 1131 - 1132 = 1133`, and `1133 -> 11331 ->
113310` is 1:1 — so a state-quarter with `113`, `1131` and `1132` **all** disclosed is an *exact*
reconstruction of `113310`. `1131` and `1132` were outside R-S5G-5's named scope and were **not
fetched**. This MUST be measured before R-PM-4 is ruled on, by the same script and the same
ladder. It is the one path that could still produce a live `REQ-027` case.

**R-PM-6 (`D-093` and the MILP gap).** A finite upper bound makes a cell ELIGIBLE for `_needs_milp`;
it reaches MILP only if its LP width also falls below `use_milp_when_lp_interval_width_below`
(§9.6's width trigger, 25 today). Where it does, HiGHS's default `mip_rel_gap = 1e-4` binds —
`D-093` measured 124 of 298 models returning a minimum above the true optimum at this engine's
variable count. The spec MUST size this work against the derived count of bounded cells under the
threshold (`specs/findings/qcew-parent-margins.md`), not against all 756. `D-032` is NOT activated
by this spec: it is reachable only when `enforce_integrality` is `false`. Cited as **scope**, not
discovered later.

**R-PM-7 (whether the comparand moves — the spec must say).** Stage 4's `validation_scoreboard`
and `runs/f03023ac9f3a` were computed against an identification set with no finite state upper
bound. On today's call graph baselines never read masked bounds (`D-087`), so a finite state bound
changes §13.5's bound metrics and the scored rows' `selected_*` columns but not WAPE, coverage or
the scoreboard; that MUST be re-checked once `D-087` is ruled. The spec MUST state explicitly whether they are re-run, and if not, why a §13.10 promotion
against a stale comparand is still sound. Silence here is the failure mode: `run_id` hashes config
and inputs but **not source**, so re-running overwrites the same directory and the change leaves
no trace.

**R-PM-8 (the bound's value is measured, not assumed).** The 0.916 median above is measured on
**disclosed** pairs, and suppression is not random — small cells are exactly the ones suppressed,
so the suppressed cells' ratio distribution may differ. The spec MUST NOT quote 0.916 as a
property of the bounded cells. What it MAY claim is that the bound is finite and that the
published joint distribution gives no reason to expect it vacuous.

## 3. Out of scope

- The §12.2/§15.2 anchor amendment and Appendix A's residue (`specs/completed/stage5-preconditions.md` §6).
- Stage 6's inheritances: `D-085`'s size-class arm, the size-share and rank metrics, and
  `reconcile_matrix`'s missing bounds parameter. `D-085`'s state-total half — §13.2 step 6 on a cell a
  parent makes exactly recoverable — is R-PM-3's, not Stage 6's.
- Region margins. QCEW publishes no region level — Stage 0's measured agglvl inventory for
  `113310` is 18 National / 48 MSA / 58 State / 78 County — so there is nothing to fetch, and
  R-S5G-5 already answered this with a shipped measurement.

## 4. How to know this is done

1. `deterministic_bounds.parquet` carries a finite `selected_upper` on the cells the measurement
   identified, and the count matches `specs/findings/qcew-parent-margins.md` (or the difference is
   explained).
2. `validate/recover.py` decides the parent's visibility under a stated synthetic pattern (R-PM-3)
   and labels exactly-recoverable cases per §13.2 step 6, with a test that fails if either is dropped.
3. `solver_status` is no longer `unbounded` on those cells, and — for the ones under the MILP width
   threshold — `D-093`'s gap question has a recorded answer rather than a default.
4. R-PM-5's sibling measurement has a recorded outcome, and R-PM-4 is ruled on that basis.
5. The Stage 5 roadmap block's "MUST NOT consume as identification-complete" clause is lifted, by
   the same stage-block rule that put it there.
6. Every note that treats `D-111` as pending is updated in the same change, found by grepping rather
   than from a list: `grep -rn 'D-111\|756 of the 1,227' src specs README.md`, plus the §13.5
   vacuity notes that do not name it — `validate/metrics.py`'s module docstring and
   `validate/CLAUDE.md`.
