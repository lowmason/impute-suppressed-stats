> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# Stage 4 harness completion: an honest scoreboard

**Status:** COMPLETE (2026-09-09) — implemented by plan 12
(`specs/plans/completed/12-stage4-harness-completion.md`).

**It closed TWO of the three deferred items named below, not three.** `Appendix A's include_*
switches gate no regime selection` and `validation_scores / validation_metrics are written without
validate_frame` are ticked. `Wire rolling_origin and cbp_size_gaps into the harness scoring loop`
is NOT: that item's own closure condition is "decide what each regime scores", and this spec's
design deliberately does not — R-S4C-1 to R-S4C-3 make each regime state honestly why it scores
nothing, which is a different deliverable, and the plan's V2 asserts that no regime gained or lost
a score. The item stays open with its stale premises corrected. Read the `Closes:` line below as
the spec's intent at approval, not as what shipped.

**Closes:** `specs/deferred_items.md` — `Wire rolling_origin and cbp_size_gaps into the harness
scoring loop`, `Appendix A's include_* switches gate no regime selection`, and
`validation_scores / validation_metrics are written without validate_frame`. Three items from the
`11-stage4-logging-employment-spec` section, folded into one design because all three turn on the
same axis: what a scored row's **arm** and **mask label** are.

**Amends:** `specs/logging-employment-spec.md` Appendix A (the `validation` block gains declared
switch KINDS) and §7 (`validation_score` field list, plus a `validation_scoreboard` field list that
§15.1 names but §7 never declared).

**Consumed by:** Stage 5, whose §13.10 promotion gate reads the Stage 4 scoreboard and must not be
planned against a comparand whose non-scoring regimes are explained by a deferral rather than a
measurement.

---

## 1. Why this exists

Plan 11 shipped Stage 4 with three declared-but-unwired surfaces. Each was recorded honestly as a
deferred item, and each item's recorded premise has since been measured false in at least one
respect. This spec exists because fixing them requires one decision, not three: **what does Stage 4
owe Stage 5 — a complete scoreboard, or an honest one?**

The answer taken here is **honest, not complete.** A regime scores where scoring separates
baselines. Where it provably does not, the harness records a measured reason and the regime's
disposition says so. Nothing is declared that is not produced, and nothing is produced that is not
declared.

That answer is available because of a measurement plan 11 did not have: on the Stage 3 estimator
registry, `rolling_origin` separates **zero** baselines. Wiring it would produce numbers identical
to an unmasked run. A scoreboard entry that cannot discriminate is worse than an absent one,
because it reads as evidence.

## 2. What was measured

These facts were established 2026-09-08 against `b73bb05`, each re-verified by an independent
adversarial pass. **A plan built on this spec should not re-derive them, but should re-confirm any
it depends on, because several of the claims they replace were themselves true-when-written.**

**M1 — `rolling_origin` separates nothing.** No §10 estimator's pre-origin estimate moves under
frame truncation. `rolling_origin_frames` removes 1,788 of 4,812 rows at origin `2022-01`, the
widest blackout in the file, and every estimator returns what it returned unmasked.

**M2 — `assert_no_future_rows` has never run in a shipped run.** Zero callers in `src/`; it
executes only inside two test modules. Stage 4's exit criterion "a rolling-origin run provably
contains no future-period rows" is therefore discharged by nothing on the live path. It also
cannot detect a malformed origin: `rolling_origin_frames(monthly, origins=['banana'])` returns all
4,812 rows untruncated and the guard passes.

**M3 — `cbp_size_gaps` is a state-YEAR gap, not a size gap.** `apply_cbp_gap` keys on
`(state_fips, reference_year)` and removes the state-year across all seven size codes — 86 rows for
a 20-key draw.

**M4 — its docstring is false.** `regimes.py:341-343` says removal "turns §10.4 from an own-arm
estimator into a declining one for that state-year". Measured: **zero** additional declines (147
declined rows before and after). `CbpIntensity.weights` declines only when the entire
`reference_year` is absent. The cell moves to the declared **fallback arm**.

**M5 — the gap is not local.** `national_march_intensity` is a pooled ratio over surviving rows, so
dropping one state's row moves every state's shrunk intensity in that year. Measured: all 1,080
non-declined `cbp_intensity` estimates across 2017–2023 moved, max |Δ| 421 employees.

**M6 — `cbp_size_gap_keys` is nondeterministic across processes.** `regimes.py:345-351` uses the
unordered `unique()` / `group_by()`-then-seeded-`sample` construction that was diagnosed and fixed
twice in this same file (`:85-87`, `:141-143`) for breaking §16.1 idempotence. It is untested,
which is why it was never caught.

**M7 — the harness never calls `select_targets` for either regime.** `harness.py:112-119`
short-circuits on `spec.select is None` **before** the call at `:122`. A fix aimed at
`select_targets` would not run.

**M8 — the harness's non-scoring reason is templated on `{name}` and is false for one of the two.**
It asserts of both regimes that the regime "is exercised through its own entry point in
`validate.regimes`". True for `rolling_origin` (a unit test calls it); false for `cbp_size_gaps`,
whose entry points `cbp_size_gap_keys` and `apply_cbp_gap` have **no caller and no test anywhere**
in `src/`, `tests/` or `scripts/`. The shipped `runs/f03023ac9f3a/validation_manifest.json` carries
this false sentence verbatim.

**M9 — the switches were never a regime partition.** Of seven: four name regimes
(`include_long_runs` → `long_consecutive_runs`, `include_rolling_origin` → `rolling_origin`,
`include_retrospective_smoothing` → `retrospective_smoothing`, `include_vintage_comparison` →
`preliminary_to_final_vintage`); two name INV-009 mask LABELS, not regimes (`include_primary_like`,
`include_complementary_like`); one names a design with **no implementation anywhere in the package**
(`include_random_mask_sanity_check`). Nine of thirteen regimes have no switch at all. Only
`include_vintage_comparison` is read (`harness.py:95`), and only to fail closed.

**M10 — changing a `ValidationConfig` default does NOT orphan the run.** `config.yaml:74-97` pins
all fourteen `ValidationConfig` keys, so no default reaches the resolved config that `runs.run_id`
hashes. **Removing a field** is what re-hashes it. Both `specs/deferred_items.md` and
`specs/logging-employment-spec-roadmap.md:229` asserted the opposite until `8ed7ecd`.

**M11 — `validation_scores` and its schema disagree in both directions.** 23 produced, 20 declared,
17 overlap. Declared-but-never-produced: `mask_arm`, `replicate`, `lookback_months_masked`.
Produced-but-undeclared: `anchor_basis`, `constraint_set_hash`, `decline_reason`, `raw_weight`,
`reconciliation_status`, `residual`. `cli.py:444-445` calls this "a superset", which it is not.
The disagreement is three-dimensional, not two: `seed` is declared `pl.Int64` and produced as
`Int32`, so `validate_frame` would raise on dtype even if both column sets were reconciled. Note
also that `constraint_set_hash` and `masked_constraint_set_hash` are BOTH produced and are
different columns — the second is not a rename of the first, and neither may be dropped as a
duplicate.

**M12 — the `declines` metric family carries a NULL `mask_arm` on every row.** 270 of 270, against
zero nulls in each of the other four families, because `decline_and_basis_report`
(`metrics.py:206`) takes no `arm` parameter. `validation_metrics` **is** gated by `validate_frame`
and the gate does not see this: it checks columns and dtypes, not nullity.

**M13 — `validation_scoreboard` is declared nowhere.** No scoreboard schema exists in
`contracts.py`; §15.1 names the artifact and §7 never gave it a field list.

**M14 — the primary leakage guard is already strippable.** `assert_no_retained_truth` is a bare
`assert` (`leakage.py:82`) called from `src/` at `harness.py:126`, inside the scoring loop, so it
vanishes under `python -O` on the live path today. `assert_no_future_rows` (`leakage.py:95`) has
the same shape and becomes live under R-S4C-4. The package states the opposite convention at
`harness.py:63-73`.

## 3. Requirements

### 3.1 A regime says why it does not score

**R-S4C-1.** `RegimeSpec` MUST distinguish the reasons a regime has no selector. Today
`select is None` conflates three unrelated situations — `retrospective_smoothing`'s vacuity on the
registry, `preliminary_to_final_vintage`'s refusal, and the two regimes that use a different
mechanism entirely — and the harness's `reason` is templated on `{name}` across all of them, which
is how M8's false sentence reached a shipped artifact. The harness MUST derive each regime's
`reason` from its declared kind, not from a shared template.

**R-S4C-2.** No regime may report `scored=0` without a reason that is a **measurement or a
declaration**, never a deferral. The existing pin
`tests/integration/test_d1_validation.py::test_no_regime_reports_zero_scores_without_saying_why`
MUST be strengthened accordingly: it currently accepts any non-empty reason, including the
"Wiring it into the loop is a deferred item" sentence this spec removes.

### 3.2 `rolling_origin`

**R-S4C-3.** `rolling_origin`'s recorded reason MUST state M1 — that truncation moves no §10
estimator's pre-origin estimate, so the regime separates no baselines on this registry — rather
than describing it as unwired. The reason MUST be scoped to the registry it was measured against,
so that adding a smoothing or autoregressive estimator later invalidates the reason rather than
silently inheriting it.

**R-S4C-4.** `assert_no_future_rows` MUST run inside `run_pseudo_suppression`, once per configured
origin, and the origins checked MUST appear in the run manifest. This is what discharges Stage 4's
exit criterion "a rolling-origin run provably contains no future-period rows"; per M2 nothing
discharges it today. The regime still scores nothing — the guard is the deliverable, not a score.

**R-S4C-5.** `assert_no_future_rows` MUST refuse an origin that matches no period in the frame.
Per M2 a malformed origin currently truncates nothing and passes.

### 3.3 `cbp_size_gaps`

**R-S4C-6.** The false docstring at `regimes.py:341-343` MUST be corrected to M4 and M5: removal
moves the cell to the declared fallback arm rather than causing a decline, and because
`national_march_intensity` pools over surviving rows the effect reaches every state in the year,
not only the holed state-year.

**R-S4C-7.** The regime MUST be described in prose as the state-**year** gap it is (M3). The
identifiers `cbp_size_gaps` / `cbp_size_gap_keys` are NOT renamed: `cbp_size_gaps` is a member of
`contracts.HOLDOUT_REGIMES` and appears in `REGIME_DISPOSITIONS`, and renaming it would change the
manifest's regime keys for no behavioural gain. The mismatch is recorded where it is read, not
erased.

**R-S4C-8.** `cbp_size_gap_keys` MUST be deterministic across processes, applying the same fix its
two siblings already carry (M6), and MUST gain the unit test the pair has never had. This is
load-bearing rather than incidental: R-S4C-9 records a **measured** reason for the regime, and a
measurement taken from a nondeterministic selector is not reproducible, against §16.1's idempotence
requirement.

**R-S4C-9.** `cbp_size_gaps`' recorded reason MUST state that the gap produces no scored QCEW cell
on its own — it changes `cbp_intensity`'s weight basis, not the set of masked cells — and MUST NOT
claim the regime is exercised through an entry point nothing calls (M8).

### 3.4 The Appendix A switches

**R-S4C-10.** Appendix A's `validation` block MUST declare which KIND each switch is: **regime
switch** (four), **mask-label switch** (two, whose real obligations are §13.2 steps 3 and 8), and
**design-validity operand** (one). Per M9 the seven were never a uniform set, and every restatement
that treated them as one has been wrong in a different way.

**R-S4C-11.** No `ValidationConfig` field may be removed. Per M10 removal re-hashes `run_id` and
orphans `runs/f03023ac9f3a`, whereas changing a default is free — so the cheap move is to keep
every field and make its role explicit.

**R-S4C-12.** The four regime switches MUST gate their regimes. A regime excluded by its switch
MUST still appear in the manifest with a reason naming the switch — it MUST NOT vanish. Note the
shipped `config.yaml` sets `include_retrospective_smoothing: false` and
`include_vintage_comparison: false`, so honoring the switches changes those two regimes' manifest
entries from a disposition-derived reason to a config-derived one. That is a manifest change with
no scoreboard change, and the plan must expect it.

**R-S4C-13.** The two mask-label switches MUST be documented against §13.2 steps 3 and 8 rather
than being treated as regime switches, and `include_random_mask_sanity_check` MUST be documented as
what it already is — an operand of `ValidationConfig._refuse_a_random_mask_only_design`. Neither is
wired to regime selection, and Appendix A must stop implying they are.

### 3.5 The three §15.1 validation tables

**R-S4C-14.** `VALIDATION_SCORE_SCHEMA` MUST declare the six provenance columns the harness already
writes (M11). They are what make a scored row auditable and MUST NOT be dropped to satisfy the
declaration.

**R-S4C-15.** The harness MUST produce the three declared columns nothing produces today:
`mask_arm`, `replicate` and `lookback_months_masked`. All three are known at the emit site — the
arm from the `MaskTarget`, the replicate from the seed loop index, the lookback from the regime's
configuration.

**R-S4C-16.** `decline_and_basis_report` MUST take an `arm` argument, closing M12's 270-of-270 NULL
`mask_arm`. `MaskTarget.arm` is currently read by nothing anywhere in the package while every emit
site passes the literal `"state_total"`; this requirement is the first consumer, so the field stops
being decorative.

**R-S4C-17.** A `validation_scoreboard` field list MUST be added to §7 and a corresponding schema to
`contracts.py` (M13).

**R-S4C-18.** `validate_frame` MUST gate all three validation tables at the write site in
`cli.py::validate_command`. After R-S4C-14 and R-S4C-15 the scores frame's produced and declared
column sets are equal; the `seed` dtype disagreement (M11) MUST also be resolved, in the direction
of the declaration (`pl.Int64`) rather than by weakening the schema to `Int32`, since `seed` values
come from `config.validation.pseudo_suppression_seeds` and nothing bounds them to 32 bits.

**R-S4C-19.** The persisted validation tables MUST NOT ship a NULL in a column whose meaning
requires a value, and `mask_arm` is the case that motivates this (M12). `validate_frame` compares
columns and dtypes only, and `dict[str, pl.DataType]` has no nullability slot — so this requirement
MUST NOT be read as "add nullability to every schema in `contracts.py`". The obligation is
discharged by naming the columns that must be non-null for these three tables and asserting it,
whatever the mechanism. Extending the schema representation package-wide is explicitly out of
scope.

### 3.6 Leakage guards

**R-S4C-20.** `assert_no_retained_truth` and `assert_no_future_rows` MUST raise typed errors rather
than bare `assert`s (M14), matching the convention `harness.py:63-73` states and these two violate.
`assert_no_retained_truth` is on the shipped scoring path today, so this closes a live hole rather
than a prospective one.

## 4. What this does NOT do

- **It does not make the two regimes score.** That was the alternative considered and rejected: it
  would require inventing a scored quantity for each (a paired contrast for `cbp_size_gaps`, CBP
  truncation for `rolling_origin`), and per M1 the `rolling_origin` version would score numbers
  identical to an unmasked run.
- **It does not touch the nine regimes that already score,** their selectors, or their metrics.
- **It does not resolve the pooled-intensity contamination of M5.** Confining a CBP gap's effect to
  the holed state-year would require handing the estimator an ungapped national value, which
  `fallback.resolve_intensity` does not permit. Recorded, not fixed — and out of scope because this
  spec stops the regime from scoring rather than making it score.
- **It does not add CI, or apply the `network` / `slow` markers.** Separate deferred items.
- **It does not rename any regime, config key, or schema field.** Every identifier that appears in
  a persisted manifest or a run id is left alone (R-S4C-7, R-S4C-11).

## 5. Verification

**V1 — the run id must not move.** `runs.run_id` hashes the resolved config and the input digests.
No field is added or removed (R-S4C-11), so a `validate` run against the shipped `config.yaml` MUST
still resolve to `f03023ac9f3a`. This is the sharpest single check that R-S4C-12's wiring did not
change the config surface, and it MUST be asserted, not assumed.

**V2 — the scoreboard's scored regimes are unchanged.** Nine regimes score today; the same nine MUST
score after, with the same numbers. The `validation_scoreboard` output MUST be byte-identical.
Everything in this spec is a declaration, a guard, or a column addition.

**V3 — the golden fixture will change, and must change in one predictable way.**
`tests/fixtures/validation/validation_metrics_golden.parquet` gains `mask_arm` values on the 270
`declines` rows (R-S4C-16). No other cell may move. Regenerating it MUST be a deliberate, reviewed
step with the diff inspected, not a `--force-regen` convenience.

**V4 — the manifest changes for exactly four regimes.** `rolling_origin` and `cbp_size_gaps` gain
measured reasons (R-S4C-3, R-S4C-9); `retrospective_smoothing` and `preliminary_to_final_vintage`
gain config-derived reasons (R-S4C-12). No other regime's entry may change.

**V5 — `python -O` no longer disarms a leakage guard.** A test MUST demonstrate that feeding
retained truth to `assert_no_retained_truth` raises under `-O`, since it currently does not
(M14).

**V6 — determinism.** `cbp_size_gap_keys` MUST return the same keys for the same seed across
separate processes (R-S4C-8), which is the property its two siblings' fix was made for and which no
test covers today.
