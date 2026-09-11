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
  parent on a suppressed quarter is a `'-'` true zero. `REQ-027`/§14.4 has **no live instance**
  (`D-110`), and this spec must not assume one.
- The bound is **tight**. On the 3,069 month-observations where both are disclosed, `113310 / 113`
  has median **0.916** (5th pct 0.659). The median suppressed cell's upper bound would sit roughly
  9% above its true value rather than at `+inf`.

**Routed from** `specs/stage5-gate-inputs.md` R-S5G-6/8 and plan 14 Task 8. It is NOT absorbed
into plan 14 because R-S5G-8's own scope line is "the flag is actually set from the new margin,
not that a new mechanism is built", and a bound *is* a new mechanism: new source rows, new cell
kinds, a new constraint builder, a change to §13.2's mask, and a moved comparand.

**Consumed by:** Stage 5. **Stage 5 MUST NOT consume `deterministic_bounds` as
identification-complete until this lands** — the roadmap's Stage 5 `Consumes` says so.

**Closes (on completion):** `D-111`. Makes `D-093` and `D-032` reachable for the first time.

---

## 1. Why this is not a small change

Every consequence below follows from one fact: today **no state cell has a finite upper bound**,
and a great deal of shipped behaviour is latent because of it.

- `_needs_milp` skips any cell whose `lower` or `upper` is `None`, so **MILP has run on 0 of
  4,775 rows** (`milp_lower`/`milp_upper` null everywhere; `solver_status` is `unbounded` 1,227 /
  `not_solved` 3,534 / `optimal` 14). The first finite upper bound turns that on.
- §13.2 step 4's mask in `validate/recover.py` hides a state cell and knows nothing about a
  parent. Once a parent identifies the child, a mask that hides the child and leaves the parent
  visible **scores a cell it never actually hid** — a §13.4 leak directly into the Stage 4
  comparand.
- Stage 4's scoreboard and `runs/f03023ac9f3a` were computed against the unbounded set. Their
  numbers are the §13.10 comparand Stage 5 is promoted against.

## 2. Requirements

**R-PM-1 (registry and ingest).** Each new slice MUST get a `registry/sources.yaml` row carrying
the same measured-or-`[documented]` provenance every existing row carries, and the fetch route
MUST reuse `ingest/qcew.py`'s dual-route interface rather than introduce a second client. Note
that the parents are served at **their own digit-depth agglvl codes** — measured `55` for `113`,
`56` for `1133`, `57` for `11331` — and NOT at `constants.QCEW_STATE_AGGLVL` (`58`). A route that
filters on `58` returns zero parent rows and reads as a clean absence; the audit script discovers
the level instead, and the ingest path MUST do the same or record the codes as measured facts.

**R-PM-2 (constraints).** New cell kinds for the parent margins, and a builder in the shape of
`constraints/rows.py::size_support_rows` / `size_margin_rows`. The parent row is a
`published_value` restriction, not an `assumed_threshold`. `assert_no_national_employment_margin`
guards a **different** margin (`SRC-QCEW-006`, the national/state-sum identity) and MUST keep
guarding it — this spec does not weaken it and must not be read as doing so.

**R-PM-3 (§13.2 step 4).** `validate/recover.py` MUST mask the parent whenever it masks the child.
This is the leakage requirement and it is not optional: a harness that hides `113310` and leaves a
disclosed `113` in the constraint system has not hidden the cell. `D-087` (bounds unenforced on
the validation path) is adjacent and should be settled in the same pass.

**R-PM-4 (disclosure).** `disclosure/`'s `exact_reconstruction_flag` MUST be set from **exact**
cases only. Today there are none, so this requirement is **conditional and must not invent one**:
an `upper_bound` case is a bound, and a bound MUST NOT reach `release_observed` or
`release_model_estimate` through this route (§14.4). If R-PM-5 finds an exact case, this
requirement binds for real.

**R-PM-5 (the unmeasured sibling path).** `113 - 1131 - 1132 = 1133`, and `1133 -> 11331 ->
113310` is 1:1 — so a state-quarter with `113`, `1131` and `1132` **all** disclosed is an *exact*
reconstruction of `113310`. `1131` and `1132` were outside R-S5G-5's named scope and were **not
fetched**. This MUST be measured before R-PM-4 is ruled on, by the same script and the same
ladder. It is the one path that could still produce a live `REQ-027` case.

**R-PM-6 (`D-093` and the MILP gap).** The first finite upper bound activates `_needs_milp`, and
with it HiGHS's default `mip_rel_gap = 1e-4`, `D-032`, and §9.6's width trigger — together, not
one at a time. `D-093` measured 124 of 298 models returning a minimum above the true optimum at
this engine's variable count. This is cited as **scope**, not discovered later.

**R-PM-7 (the comparand moves, and the spec must say how).** Stage 4's `validation_scoreboard`
and `runs/f03023ac9f3a` were computed against an identification set with no finite state upper
bound. The spec MUST state explicitly whether they are re-run, and if not, why a §13.10 promotion
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
- Stage 6's inheritances: `D-085`, the size-share and rank metrics, `reconcile_matrix`'s missing
  bounds parameter.
- Region margins. QCEW publishes no region level — Stage 0's measured agglvl inventory for
  `113310` is 18 National / 48 MSA / 58 State / 78 County — so there is nothing to fetch, and
  R-S5G-5 already answered this with a shipped measurement.

## 4. How to know this is done

1. `deterministic_bounds.parquet` carries a finite `selected_upper` on the cells the measurement
   identified, and the count matches `specs/findings/qcew-parent-margins.md` (or the difference is
   explained).
2. `validate/recover.py` masks the parent with the child, with a test that fails if it does not.
3. `solver_status` is no longer `unbounded` on those cells, and `D-093`'s gap question has a
   recorded answer rather than a default.
4. R-PM-5's sibling measurement has a recorded outcome, and R-PM-4 is ruled on that basis.
5. The Stage 5 roadmap block's "MUST NOT consume as identification-complete" clause is lifted, by
   the same stage-block rule that put it there.
