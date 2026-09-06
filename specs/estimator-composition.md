> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# Estimator composition: the declared two-arm weight vector

**Status:** design-approved, awaiting plan
**Closes:** `specs/deferred_items.md` — `MAX_SCALE_RATIO = 100.0 is an originated tripwire with no
spec warrant` and `§10.3's fallback scales by the DISCLOSED intensity; §10.4's uses the NATIONAL
one`
**Amends:** `specs/logging-employment-spec.md` §7 (`baseline_result` schema), §10 (new subsection),
§13.5–13.8 (one scoreboard requirement)
**Consumed by:** Stage 4, which scores every Stage 3 baseline and must not be planned before this
lands

---

## 1. Why this exists

Two deferred items read as separate complaints about unwarranted constants. They are not. Both are
consequences of one step that `specs/logging-employment-spec.md` never describes.

§10 describes each baseline as producing a single weight vector, and §12.2 asks only that weights
be positive. Normalization is scale-invariant for one vector, so the spec never needs to name a
unit. The package does something else: `baselines/interfaces.py::compose` merges an **own arm**
with an **establishment fallback arm** per cell, and `reconcile.allocate` normalizes the union.
That step is legitimate and load-bearing — six D1 states have zero observed employment months
(AK, DE, HI, ND, NV, VT) and two have no CBP row in any year (HI, RI), and every month's missing
set contains at least one of each, so an all-or-nothing rule would make §10.3 and §10.4 decline in
96 of 96 months and leave §10.8's rungs 1 and 3 permanently empty, including the "preferred
transparent baseline" slot Stage 4 must fill with numbers.

But because the spec never names the step, everything the step needs was originated in the
package: that both arms are in employees, what enforces it, which intensity converts
establishments into employees, and what a violation means. §10 contains three normative sentences
in 62 lines and attaches no REQ or INV id to any of them, so none of this is drift from a
requirement — it is design in a vacuum.

This spec names the step and gives it a contract.

## 2. What the current enforcement does and does not catch

Measured on the D1 window and on `tests/fixtures/baselines/`, 2026-09-06:

`_assert_comparable_scales` compares the medians of the two arms over cells where both are
positive and refuses a ratio outside `[1/100, 100]`. Over 660 `compose` calls it evaluated 495
times, and the honest ratio spans 0.947 to 4.996.

It catches a dimensionless-share-against-raw-count pairing (9,050 to 39,870) and a
thousands-against-employees prefix error (947–4,996 high, or 9.5e-4–5.0e-3 low, the low direction
clearing the 0.01 floor by only 2.0x).

**It cannot catch the case its own callers were written to prevent.** Substituting a raw
establishment count for the scaled fallback — the exact error the fallback scaling in
`historical.py`, `simple.py` and `intensity.py` each says it exists to fix — produces ratios of
0.182–0.811 for the share family and 0.160–0.316 for §10.4, entirely inside the honest range, and
inside it by a wider margin once Stage 4's masking widens that range to 0.603–3.223. Reintroduced
on D1, that bug produced **zero guard trips** while shipping own-cell estimates up to 6.12x too
large and fallback-cell estimates 0.25x too small, up to 986 employees of absolute shift against
residuals near 1,589 — every value positive, every month summing exactly to the residual.

A magnitude tripwire is therefore the wrong instrument, and no threshold repairs it: the honest
range and the bug's range overlap.

## 3. Requirements

### 3.1 The unit is carried by the type, not checked after the fact

**R-COMP-1.** A weight vector handed to composition MUST be a declared employees-valued type. The
unit claim is made once, where the vector is constructed, and is not re-derived from the values. A
type annotation alone does not satisfy this: nothing in this project runs a static type checker,
so the claim has to be carried by a constructed value that a plain `dict[str, float]` cannot
impersonate at the call site.

**R-COMP-2.** `compose` MUST accept only that type for both arms. It MUST permit an empty own arm:
§10.6's estimator legitimately composes entirely from the fallback, and an empty own arm is a
valid composite rather than an error.

**R-COMP-3.** `MAX_SCALE_RATIO` and `_assert_comparable_scales` are removed. §2 establishes that
the guard cannot detect the mismatch its callers describe, and no threshold fixes the overlap.

**R-COMP-4.** Removing the guard leaves the frozen baseline golden as the only remaining check on
a *data* pathology a type cannot see — a corrupt source column, or a CBP vintage that moves an
intensity. The spec therefore requires that coverage to be explicit: the golden's role as the
units-and-magnitude regression net MUST be stated where the golden is defined, so that a future
re-pin is a decision rather than an accident.

### 3.2 One fallback constructor, with a declared intensity

Today each baseline builds and scales its own fallback arm, which is why two of them scale by the
disclosed intensity (§10.3 and §10.6) and one by the national intensity (§10.4) with no section
asking for either. The values are close on D1 — disclosed 5.442–6.380, national 5.914–6.139 — so
this is not a numerical problem. It is an unexplained divergence in a layer Stage 4 is about to
score.

**R-COMP-5.** There MUST be exactly one construction that turns §10.2 establishment exposure into
an employees-valued fallback arm. It takes the intensity as a named argument and returns the
declared type. No estimator builds or scales a fallback arm itself.

**R-COMP-6.** Each estimator MUST declare which intensity scales its fallback arm, as a property
of the estimator rather than a line inside its body, and that declaration MUST be recorded in
`baseline_manifest.json` beside the existing `weight_basis_counts` key, so the choice is readable
from a run's output without reading source.

**R-COMP-7.** The divergence is permitted and is not to be standardised away. §10.4's national
value is exactly its own shrinkage limit as the CBP cell count goes to zero, which is a derivation
§10.3 and §10.6 have nothing equivalent to appeal to. R-COMP-6 makes the difference a declared,
reviewable property; it does not make it an accident.

**R-COMP-8.** The intensity MUST be derived from the same partition the anchor's residual was
derived from. `baselines/simple.py::disclosed_intensity` currently reads
`context.partitions[anchor.reference_month]` while the residual arrives as the anchor argument,
and nothing enforces that the two agree — under a Stage 4 pseudo-suppression mask they agree only
if the harness rebuilds `EstimatorContext.partitions` from the same mask it handed the anchor.
Making the intensity an explicit argument to one constructor is what lets this be required rather
than hoped for.

> Note on `specs/deferred_items.md`: R-COMP-8 states the requirement that item asks for, but the
> item is scoped to Stage 4 *enforcing* it in the harness and is cited from the roadmap's Stage 4
> entry as that stage's own reading. It stays unticked here. Stage 4's plan closes it, and should
> record that this spec supplies the requirement it enforces.

### 3.3 A decline carries a kind

`baselines/runner.py` funnels three different situations into one row shape — a data problem at
`:131`, an estimator's considered refusal at `:138`, and a reconciliation failure at `:152` — all
producing `estimate = None`, `weight_basis = 'none'`, `reconciliation_status = 'declined'` and a
free-text `decline_reason`. Nothing downstream can tell them apart without reading prose.

That matters for Stage 4 specifically. §13.5–13.8 score estimates against truth and define no
decline metric, so an estimator whose months drop out of the scored set drops out non-randomly,
and a data bug can make a baseline's WAPE look **better** than a correct implementation's.

**R-COMP-9.** `BASELINE_RESULT_SCHEMA` gains a `decline_kind` column beside `decline_reason`, with
exactly three values: `by_design` (the estimator refused; §10.5's harvest baseline is the
archetype), `data_gap` (an input the estimator needed was absent), and `reconciliation_failure`.
`decline_reason` stays and stays free text. `baseline_manifest.json` already carries a `declines`
key; it gains the breakdown by kind rather than a second key beside it.

**R-COMP-10.** §13's scoreboard MUST report decline counts by kind, per estimator and per holdout
regime, and a scored comparison MUST state the denominator it was computed over. This is a new
requirement on Stage 4 and is the reason this spec is sequenced before Stage 4 is planned.

**R-COMP-11.** Declines remain rows, never absences. The existing rule — an absent row is
indistinguishable from a bug — is unchanged.

## 4. Amendments to `logging-employment-spec.md`

1. **New §10.9, "Composition and the fallback arm."** States that a baseline may compose an own
   arm with the §10.2 fallback; that composition MUST be visible per cell (`weight_basis`); that
   both arms are employees-valued and that the unit is carried structurally; that there is one
   fallback construction whose intensity each estimator declares; and that the intensity comes
   from the same partition as the residual. §10.8's rank-1 phrasing — "employee-per-establishment
   with robust historical adjustment" — is the spec's own precedent that a composed estimator is
   legitimate, and §10.9 should cite it as such.
2. **§7 `baseline_result`.** Add `decline_kind`. This is a schema fingerprint change and requires
   the golden regeneration in §5.
3. **§13.5–13.8.** Add the decline-reporting requirement of R-COMP-10.

Nothing else in §10 changes. §10.2's formula is closed and is not touched; §10.3's and §10.4's
holes are not filled beyond what R-COMP-5 to R-COMP-8 require.

## 5. Testing

**T-1 (the decisive one).** Reintroduce the raw-establishment-count substitution measured in §2
and assert it now fails at construction. Today that substitution passes the shipped guard silently
and moves D1 estimates by up to 6.12x, so this test is the difference between the two designs and
must not be satisfied by a magnitude assertion.

**T-2.** An empty own arm composes successfully into an all-fallback composite (R-COMP-2), so the
type does not break §10.6.

**T-3.** One test per `decline_kind`, driving each of the three `runner.py` call sites and
asserting the kind rather than the prose.

**T-4.** Each estimator's declared fallback intensity is the one its fallback arm was actually
built with (R-COMP-6), asserted per estimator rather than for the registry in aggregate.

**T-5.** The intensity and the residual come from the same partition (R-COMP-8): a context whose
partition disagrees with the anchor's must fail rather than silently scale off the wrong one.

**T-6.** `baseline_results_golden.parquet` is regenerated for the new column. §17.6 requires a
documented reason and reviewer approval for a golden update; the reason is R-COMP-9 and it belongs
in the commit that regenerates it, not only in this spec.

Note for whoever plans this: the existing suite cannot see a change in weight *ordering* or a
units substitution — that is recorded in `specs/deferred_items.md` and was re-measured on
2026-09-06. T-1 is written against a construction failure precisely so it does not inherit that
blindness.

## 6. Out of scope

- **`BreakAdjustedShare`'s `<4` fallback.** An independent hole inside §10.3's undefined "robust
  break-adjusted share", with its own fixture problem: `tests/fixtures/baselines/` contains three
  cells with any history, all length 6 and all one state-08 series, so no `<4` cell exists to
  validate against. It gets its own spec.
- **Standardising the two intensities onto one value.** Explicitly refused by R-COMP-7.
- **Stage 4's harness, masks, metrics and scoreboard**, except for the single reporting
  requirement R-COMP-10 places on it.

## 7. Exit criteria

- A raw-establishment fallback arm cannot be constructed or passed to `compose`, demonstrated by
  T-1 rather than argued.
- `MAX_SCALE_RATIO` does not appear in the codebase.
- Exactly one construction converts establishment exposure into employees, and each estimator's
  choice of intensity is readable from the run output without reading source.
- Every declined row carries a `decline_kind`, and no code path produces a decline without one.
- The full suite passes with no new skips, and the baseline golden's regeneration is accompanied
  by its documented reason.
- `specs/deferred_items.md` has both composition items ticked by this plan's completion protocol.
  The `disclosed_intensity` partition item stays unticked and is Stage 4's to close.
