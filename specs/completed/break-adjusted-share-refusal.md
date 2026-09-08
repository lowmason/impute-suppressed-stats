> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# The break-adjusted share refuses a degenerate cut

**Status:** COMPLETE (2026-09-07) — implemented by
`specs/plans/completed/10-break-adjusted-share-refusal.md`; R-BREAK-1 through R-BREAK-5
shipped, and §4's prediction held: `baseline_results_golden.parquet` is byte-identical

**Closes:** `specs/deferred_items.md` — ``BreakAdjustedShare`'s `<4` fallback is a design choice
nobody chose`. This is the surviving third of the D1 triage group; its other two items became
`specs/completed/estimator-composition.md` and shipped as plan 9.

**Amends:** nothing. §10.3's entire text on this variant is "a robust break-adjusted share", which
neither defines a threshold nor requires the five variants to differ. The rule below is originated
by this package, and §10.3 is not amended to say otherwise — the declaration lives in the code.

**Consumed by:** Stage 4, which scores exactly these five §10.3 variants and must not be planned
against a scoreboard in which two of them are the same estimator.

---

## 1. Why this exists

§10.3 declares five historical-share variants. `BreakAdjustedShare` is variant 5, "robust to a
level break in the share series": it takes the median of the most recent segment after the largest
single-step change, so one reclassification or one plant closure does not drag the estimate toward
a regime that ended.

It has no way to refuse. When the history cannot evidence a break, it returns a number anyway —
and that number is another variant's. Measured on the D1 window against the current tree:

- **99 of 342 own-weight cells have a history shorter than four**, where the code short-circuits to
  `statistics.median(shares)`. That is character-identical to `RollingMedianShare._reduce`, so
  variant 5 ships variant 3's number under variant 5's label. 91 of the 99 are exactly length 3.
- **97 cells have their largest step at the final position**, leaving a one-point recent segment.
  The median of one point is the last observation, so those cells ship `LastObservedShare`'s number
  under variant 5's label. **28 of them have histories of length ≥ 4**, six of them length 12.

The second collapse is not recorded anywhere and no length-based threshold can see it. Both are the
same defect: the variant emitting a value it has no evidence for, wearing a name that claims it does.

**The rule this package already follows, in the same file.** `SameMonthPreviousYearShare` returns
`None` when the same month one year earlier was not observed, and its docstring gives the reason:
"substituting a different month would make this variant indistinguishable from `LastObservedShare`
exactly when it matters." That is the principle. Variant 5 is the one variant that breaks it, so
this spec is a consistency fix against an established local convention rather than a new idea.

## 2. What is NOT the requirement

**Five distinct numbers is not achievable and is not required.** Any reduction of a one-element list
is that element, so on a length-1 history last-observed, rolling-median, exponentially-weighted and
break-adjusted all return the same value, and no implementation prevents it. Distinctness is a
property the data admits or does not. The requirement is that each variant does what it says **or
refuses** — coincidental agreement is fine, structural impersonation is not.

## 3. Requirements

**R-BREAK-1.** `BreakAdjustedShare._reduce` MUST return `None` unless the cut it selects leaves at
least two points in the recent segment. A history of fewer than two points admits no cut at all —
there are no steps to take a maximum over — and MUST also return `None`; an implementation that
computes `max(steps)` before checking this raises `ValueError` on an empty sequence. A one-point segment is the last observation, which is
variant 1; a segment equal to the whole history is the plain median, which is variant 3.

**R-BREAK-2.** The threshold MUST be expressed as a property of the selected cut, not of the
history length. A length-3 history whose largest step falls at position 1 leaves a two-point
segment and MUST be kept; a length-12 history whose largest step falls at the final position leaves
a one-point segment and MUST be refused. A length-based rule gets both cases wrong.

**R-BREAK-3.** Refusal MUST reuse the existing `None` path. `_reduce` returning `None` already
causes `_ShareBaseline.weights` to omit the cell from the own arm, which sends it to the declared
§10.2 fallback through `compose_with_declared_fallback`. No new code path, no new config key, and
no new decline reason: the cell is composed, not declined, and `weight_basis` records
`establishment_fallback` for it as it already does for 885 cells.

**R-BREAK-4.** The class docstring MUST stop asserting the behaviour this change removes. It
currently reads "At four or more shares this is not a plain median over the whole lookback; below
four it is exactly that, because a segment split needs points on both sides." Both halves become
false: the threshold is no longer four, and the below-threshold behaviour is no longer a plain
median. The replacement MUST state the refusal and its reason, and MUST NOT restate the D1 counts —
those are measurements a revision moves, and this package's convention is to report the own/fallback
split from the run manifest rather than write it into a docstring.

**R-BREAK-5.** The tie rule MUST be declared, and MUST NOT change. `steps.index(max(steps))` takes
the earliest tied step; 15 D1 cells have a tied largest step and are decided by it today. This is a
second undeclared origination sitting in the same four lines, and the spec's position is that it is
written down, not altered — changing it would move cells for a reason this spec has not argued. A
future item may revisit whether the latest tied step is the better reading of "a regime that ended".

## 4. Consequences, measured

Against the current tree on the D1 window, of 342 own-weight cells:

| | Refuse below 4 (the audit's option) | R-BREAK-1 |
|---|---|---|
| Cells refused | 99 | **101** (29.5%) |
| — short (`<4`) | 99 | 73 |
| — long (`≥4`) | 0 | **28** |
| Length-3 cells kept with a genuine break | 0 | **26** |

The cost is within two cells of the blunt rule and lands on a better-chosen set. `BreakAdjustedShare`
becomes substantially more fallback-heavy — 241 own cells against the 342 it carried before the
refusal — which is the honest consequence of it being the most demanding, and is already visible per
estimator in `baseline_manifest.json`'s `weight_basis_counts`. CORRECTED 2026-09-08: this sentence
used to call it "the most fallback-heavy of the five variants" and to put "the other variants" at
342. Both overreach, and the manifest this sentence points at is what refutes them. Measured on
`runs/2fc2c6003e0c` (a SUPERSEDED run id — a dated measurement; see the roadmap's Stage 3 point (8)),
`weight_basis_counts` gives `share_same_month_prior_year` 129 own / 1,098 fallback against this
variant's 226 / 1,001, so variant 5 is the SECOND most fallback-heavy of the five, not the first —
`share_same_month_prior_year` is, for its own reason and not through any refusal. Only THREE of the
four siblings sit at the comparison count (327 in the manifest frame, 342 in this section's
share-history frame); the 342 frame was not re-measured per variant.

**The frozen golden does not change.** All three cells with a history in
`tests/fixtures/baselines/` are length 6 with the cut at position 3, leaving a three-point segment,
so every one is kept. No §17.6 re-pin, no reviewer approval for a golden update, and
`baseline_results_golden.parquet` MUST be byte-identical after this change. A plan that finds
otherwise has changed something this spec did not ask for.

## 5. Testing

The rule is a pure reduction over a list of floats, so it is tested directly rather than through a
fixture. `_reduce` is called with `(shares, anchor, history)` and reads only `shares`, so the anchor
and history arguments may be stubs for these cases.

**T-1.** A length-1 history returns `None` — no steps exist, so no cut does.

**T-2.** A length-2 history returns `None` — the only cut leaves one point.

**T-3.** A length-3 history whose largest step is at position 1 returns the median of the last two
points, NOT the median of all three. Pins R-BREAK-2's keep half and the 26 recovered cells.

**T-4.** A length-3 history whose largest step is at position 2 returns `None`, because the segment
would be one point. Pins that a short history is not automatically refused and not automatically
kept — the cut decides.

**T-5.** A LONG history (length ≥ 4) whose largest step is at the final position returns `None`.
This is the case no existing test reaches and no length threshold can catch; it is the 28 cells.

**T-6.** A long history with an interior break returns the median of the recent segment, on data
chosen so that value differs from the plain median of the whole history — the variant still does
its job where the evidence supports it. The inequality is a property of the fixture, not an
invariant: 18 of the 243 D1 cells with a length-≥4 history agree with the plain median by
coincidence, and that is permitted per §2.

**T-7.** A cell refused by R-BREAK-1 takes the establishment fallback rather than declining the
month: driven through `BreakAdjustedShare().weights(...)`, the cell's `weight_basis` is
`establishment_fallback` and the returned object is `Weights`, not `Decline`.

**T-8.** `tests/integration/test_baseline_golden.py` passes unchanged, and
`baseline_results_golden.parquet` is not regenerated.

**Replaced:** `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median` asserts the
behaviour R-BREAK-1 removes and MUST be deleted rather than adjusted — its premise is the defect.
Its sibling `test_the_break_adjusted_docstring_scopes_its_own_claim` pins docstring wording that
R-BREAK-4 rewrites and MUST be updated to pin the new claim.

## 6. Out of scope

- **Changing the tie rule** (R-BREAK-5 declares it, deliberately unchanged).
- **Changing any other §10.3 variant.** The length-1 coincidence among four variants is a property
  of one-element lists, not a defect, per §2.
- **Amending §10.3.** The spec text supports this reading and does not need to be narrowed to it.
- **Any Stage 4 scoreboard change.** Stage 4 consumes the corrected estimator; it is not planned here.

## 7. Exit criteria

- A length-12 history whose largest step is at the final position yields no own weight, demonstrated
  by T-5. This is the case the `<4` threshold cannot see.
- A length-3 history with an interior break still yields an own weight, demonstrated by T-3.
- `grep -n "below four" src/logging_employment/baselines/historical.py` returns nothing.
- `tests/fixtures/baselines/baseline_results_golden.parquet` is unchanged in the diff.
- The full suite passes with no new skips.
- `specs/deferred_items.md`'s `BreakAdjustedShare` item is ticked with a `→ done in plan <id>`
  pointer. Done by the Plan Completion Protocol, not by the implementing task.
