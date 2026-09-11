# Do Stages 1-4 need revisiting? — re-measured at `d6591b6` (2026-09-11)

**Question.** `docs/reviews/2026-09-09-system-review.md` and
`docs/reviews/2026-09-10-review-routing.md` identified issues with Stages 1-4. Stages 0-4 are
ticked and Stage 5 is cleared. Does anything in those stages need to be revisited?

**Method.** Both reviews predate ~30 commits of remediation — most importantly plan 13
(`specs/completed/stage5-preconditions.md` → `specs/plans/completed/13-stage5-preconditions.md`,
merged `58a9cd9`), which *is* the "Stage 4.5" the routing doc's §6 recommended, plus the record
corrections in PRs #22 and #23. Every claim below was therefore **re-measured at `d6591b6`**;
no citation was carried over from either review. Two passes:

1. **Re-measure + adversarially challenge.** 12 claim clusters covering the reviews' F-/R-/Q-/D-
   items, each surviving "rework" verdict then attacked by two independent refuters with
   different lenses (ownership, consequence). 41 agents.
2. **Blind spec-vs-code audit.** 9 lenses over the Stage 1-4 deliverables against
   `specs/logging-employment-spec.md`, with the review documents withheld, then a novelty
   cross-check of each divergence against both reviews, the D-nnn register and the roadmap.

`data/` and `runs/` are present on this machine, so bounds, scoreboard and manifest claims were
re-measured against real artifacts rather than reasoned about.

**Buckets.** `rework` = live at HEAD, in a ticked stage's own deliverable, owned by nothing.
`record` = code is right, a document claims otherwise. `owned` = an open `D-nnn` or an unticked
stage carries it. `later` = not Stage 1-4 work. `closed` = fixed since the review.


---

## Verdict

**Yes — a short list, and one item gates Stage 5.** But the list is far shorter than either review
implies, and for a reason worth stating up front: most of what they found is either already
discharged or structurally unreachable on the D1 window.

Measured, not inherited: pass 1 returned **91** partitioned items (41 agents); pass 2 returned
**68** raw divergences, **36** surviving independent re-verification, of which **6** had no prior
art anywhere (49 agents). The suite is green at `d6591b6` — `uv run pytest -q` → **1388 passed**
in 423 s, matching the root `CLAUDE.md`'s count at `4cc0dfe`, so that claim needs no correction.

Three structural facts shape the answer:

1. **Most of it is discharged.** Plan 13 closed R-01..R-11; PRs #19/#22/#23 corrected the record.
   14 items measure `closed`.
2. **Nearly every surviving defect is latent on D1.** The adversarial pass refuted the
   *consequence* of almost every confirmed fact. One property explains it: all 1,227 suppressed
   state cells are `unbounded` with a null `selected_upper`, so every path gated on a finite bound
   is unreached.
3. **The remainder is owned** — 22 items sit on an open `D-nnn`, an unticked stage's `Consumes`,
   or the recorded scope boundary of `specs/completed/stage5-preconditions.md`.

### The latent cluster, and the single event that activates it

`_needs_milp` skips any cell whose `lower` or `upper` is `None`, so the MILP path never runs on D1:
`milp_lower`/`milp_upper` are null on **0 of 4,775** rows; `solver_status` is `unbounded` 1,227 /
`not_solved` 3,534 / `optimal` 14. That one fact makes `F-016` (the width trigger), the
newly-found **1e-4 HiGHS `mip_rel_gap`** (bounds accepted as `kOptimal` that are not §9.1's exact
optimum), the MILP-infeasible diagnostic gap, and `D-032` all unreachable today.

They go live together the moment any bound becomes finite — which is exactly what fetching the
§9.3 margins would do. **The margin question is not one open item; it is the gate on a cluster.**

### Ranked

| # | Item | Stage | Act? | Why |
|---|---|---|---|---|
| 1 | **§13.10 stratum gates** (`S3-02`) | 4 | **Before Stage 5** | The one genuine blocker. Two of six §13.10 promotion gates have no data source: nothing in `validate/` computes a per-stratum anything (18 shipped metric names, all pooled), and all three `PromotionConfig` keys have **zero** `src/` consumers — so `config.resolved.yaml` ships a promotion policy no code can apply. Stage 4's `Produces` claimed the §13.5-13.8 families. Decide: emit them, or amend §13.10. |
| 2 | **§9.3 margins unmeasured** (`F-005`/`Q-09`/`R-16`/`Q-22`) | 2 | **Before Stage 5** | Hours of work; the only item that can move the product off 1,227 model-only estimates. With `1133 → 11331 → 113310` single-child, a disclosed parent is an **exact reconstruction** — a live REQ-027 disclosure case, not a modelling improvement. Done after Stage 5 it re-opens the mask, the gate comparand and the scoreboard. Owned, but **mis-scheduled**: `roadmap:302` puts the settle-before trigger on Stage 6 while Stage 5 already consumes `deterministic_bounds` (`roadmap:292`) and its own block is silent. Re-point it at Stage 5 — that edit alone is minutes. |
| 3 | Provenance pair: `F-010` + CBP metadata rows | 1 | Backlog | `snapshot_id` is a filename stem; the declared §7.2 join returns 0 rows on all three tables and on `target_cell`. **Contested**: the fact resolves today via `raw_path`, bijectively 47/47, so it is a naming defect, not a lost fact. Stage 8's §18.1 package is the first consumer that needs the join. Separately, 7 CBP `variables.json` retrievals get no `source_snapshot` row at all, and `predicate_from_stored_metadata` picks among copies by sha256 sort order where `snapshot_paths` refuses that same ambiguity by name. |
| 4 | `scale_into_bounds` inversion | 3 | Backlog | Returns below a declared lower on an inverted `(L > U)` pair while its sibling `integerize` refuses the same shape with a named error. §12.3's guards are on **sums**, so no configuration catches a per-cell inversion. *Caveat, from the verifier:* §17.3 scopes its property to "random feasible inputs", so `L > U` does not literally bind — this is a fail-closed asymmetry inside one package, not a spec violation. |
| 5 | `S3-EWMA-HALFLIFE` | 3 | Backlog | **Demoted after a direct check.** `ExponentiallyWeightedShare` decays by list *index*, not month distance, and `shares` is built from `partition.disclosed` only — confirmed by reading `baselines/historical.py:206-214` — so with gaps normal at 26% suppression the realized half-life reaches 66 months against a docstring claiming 12. Moves 49 of 327 shipped cells >1% (max 7.18%). *But:* `preferred_baseline` was called for real on all nine scoring regimes and returns `share_last_observed` (3) or `cbp_intensity` (6) — **never** `share_exponentially_weighted`. It cannot move Stage 5's comparand today. *Caveat:* §10.3 names no decay form, so this is a docstring-vs-code divergence in a repo that treats docstrings as the design record — not a spec violation. |

### Record corrections (the code is right; a document is not)

`F-036`/`Q-14` belongs here, not in rework: the CBP `naics_vintage` column has **no reader** —
`reconcile/` contains zero occurrences of "cbp", and all five read sites key on `reference_year` —
so no number moves, and the `113310` crosswalk is `1:1` across both vintages. What must change is
the false premise in `ingest/cbp.py` asserting CBP 2022/2023 "carry the NAICS 2022 vintage",
contradicted by all seven stored `variables.json` (`NAICS2017`, labelled "2017 NAICS code"). A
false sentence recorded as a Stage 0 measurement is the harder half to fix, because it reads as
justified. Also here: `F-001`, `F-019`, `F-030`, `F-031`, `F-034`, and the plan-13 record drift.

### Overturned — do not act on these

- **`F-035`** (no ownership column) — **contract conformance.** §7.4 is a 13-field list with no
  ownership field; adding one would deviate from what Stage 1 was told to build. The Stage 2 guard
  already halts on mixed ownership, so the review's "silently" was false when written.
- **`F-023`** (§7 preamble MUST) — not unowned but **unimplementable**: `run_id` is a sha256 over
  the bytes of `data/staged/*.parquet`, so a `run_id` column inside a staged table is a fixed point.
- **`F-018`** sub-claim 2 — the bare `KeyError` is the deliberate fail-closed mechanism; the
  realistic miskeying raises before any upper is read. Sub-claims 1 and 3 are owned (Stage 6; `D-041`).
- **`F-024`**, **`F-003`** — owned by `D-085` + Stage 6 `Exit`, and by the stage5-preconditions
  scope note respectively.
- **`R-15`**, **`F-026`**, **`F-032`**, **`F-017`** — facts confirmed, consequences refuted.
  `F-032` cannot fire (0 of 3,462 eligible targets have zero employment; min is 3). `F-026`'s 39
  builtin raises change no control flow — all of `src/` has six `except` clauses and none catches
  a builtin. `F-017`'s uncompared residual is caught downstream by a hard equality whose §9.7
  diagnostic names the margin and quantifies the slack.

### The process finding that outlasts the rest

35 of the review's 36 `F-` ids are cited nowhere outside `docs/reviews/`, and **no roadmap stage
block references that directory**. `derive-roadmap`'s resume step reads the gap table and the stage
blocks — so anything recorded only in a review is invisible to a roadmap resume. Items 1, 3, 4 and
5 above are in exactly that category today. Whatever is not acted on should be filed as a `D-nnn`
with a `Size:` and a trigger before these reviews are retired.


---

## Appendix — full partition

### REWORK (19)

- **F-010** [S1] blocks5=no CONTESTED
  Holds in full and is worse than the review said: harmonized snapshot_id is the filename stem while source_snapshot.snapshot_id is the content sha256, an inner join returns 0 rows on all three harmonized tables AND on target_cell, and no D-nnn was ever filed for it.
- **F-036** [S1] blocks5=no CONTESTED
  Live at HEAD and untouched since the review: build.py stamps naics_vintage="NAICS 2022" on all 367 cbp_state_size rows for 2022-2023, while the stored Census metadata for both years serves exactly one NAICS predicate named NAICS2017 labelled "2017 NAICS code" -- but the CBP naics_vintage column is r
- **Q-14** [S1] blocks5=no CONTESTED
  Answered by measurement: the CBP API serves NO NAICS2022 variable for reference years 2022 or 2023 -- the single NAICS predicate in the stored metadata for every window year 2017-2023 is named NAICS2017 and labelled "2017 NAICS code", while the harmonized rows for 2022-2023 are stamped "NAICS 2022";
- **F-017** [S2 (constraints/compat.py, whos] blocks5=no CONTESTED
  Confirmed and reproduced: `observed_employment` is aggregated at compat.py:117 and read by nothing, so a 233% employment-margin disagreement passes the gate in the very year the gate's own report labels `employment_checkable`.
- **F-026** [S1 owns `errors.py` and the ing] blocks5=no CONTESTED
  Confirmed and unchanged — the builtin-raise surface is byte-identical to the review commit (39 `raise ValueError`, 4 `FileNotFoundError`, 3 `KeyError`, 3 `NotImplementedError`), the project's own §18.3 fail-closed inventory lists a bare `ValueError`, and `grep LoggingEmploymentError tests/` is still
- **F-032** [S4] blocks5=no CONTESTED
  The null-the-whole-estimator behaviour survives verbatim at HEAD (metrics.py:107-111, unmoved since the review), is owned by no D-nnn, and moves no shipped number — 0 of 3,462 eligible D1 targets have zero employment (min 3), and all 46 null median_ape rows come from the separate n_scored==0 path.
- **F-025** [S1, 3, 4] blocks5=no CONTESTED
  The inert-key count is wrong in both directions -- measured 17 unread keys at HEAD, not 14 -- one key the review called unread has been read since Stage 1, and plan 13's seven new fields add zero; the propensity half holds exactly as written and is unowned Stage 4 rework.
- **PLAN13-a** [SStage 1-4 deliverable (src/log] blocks5=no sweep
  `runs.code_provenance` anchors on the nearest `uv.lock`, which in a uv-managed consuming project is the CONSUMER's — so every run manifest can be stamped with a foreign commit rather than "unknown"
- **S2-DIAG-TOL** [SStage 2 (identification engine] blocks5=no sweep
  §9.7's infeasibility diagnostic accepts `config: BoundConfig` and reads it zero times, so a configured `feasibility_tolerance` moves the bounds but not the diagnosis that explains them — live in Stage 2's own deliverable, owned by nothing
- **S3-EWMA-HALFLIFE** [SStage 3 (transparent baselines] blocks5=unclear sweep
  `ExponentiallyWeightedShare` discounts per OBSERVATION while its own docstring claims a one-year half-life; the shipped histories are gappy (median 6 observations over 9 months, worst 4 over 22), so the realized half-life reaches 66 months and 49 of 327 shipped cells move >1%
- **S1-CROSSWALK-NOT-IN-ETL** [SStage 1 (ingestion/harmonizati] blocks5=no sweep
  §3.1's "The ETL MUST verify the 113310 mapping mechanically" is unmet: `assert_113310_survives_the_window` has zero production callers and runs only under pytest — the roadmap is honest about this, the spec MUST is not met
- **S1-PUBDATE-EMPTY** [SStage 1 (ingestion, ticked)] blocks5=no sweep
  §7.2's `source_publication_date` is the empty string on every snapshot row ever written — three hardcoded `""` call sites, 47 of 47 manifest rows blank, and no deferred item or roadmap stage owns it
- **S1-RELEASE-STATUS-STAMPED** [SStage 1 (ingestion, ticked)] blocks5=no sweep
  SRC-QCEW-005's MUST to "distinguish preliminary and final observations" is met by a config literal, not by parsing: `release_status` is stamped from `cfg.sources.qcew.release_status` (and the literal `"final"` for the other two sources), and Stage 1's Gap-closed line credits SRC-QCEW-001–005
- **S1-STORAGE-62** [SStage 1 (storage layout, ticke] blocks5=no sweep
  §6.2's storage layout and its no-re-download MUST both diverge at HEAD and split three ways — the layout and the MUST are live and unrecorded (Stage 1), while the missing `run_manifest.json` is legitimately owned by unticked Stage 8
- **S2-QUARANTINE-NO-PATH** [SStage 2 (identification engine] blocks5=no sweep
  §9.7's quarantine is reachable from no command — `solve_bounds`'s `quarantined` parameter is never passed by the CLI — and while `constraints/CLAUDE.md` documents the semantics, nothing records that no path reaches them
- **S3-02** [SStage 4 (validation harness / ] blocks5=yes sweep
  §13.10's two 'major stratum' promotion gates have no data source: nothing in validate/ computes a per-stratum WAPE, and all three PromotionConfig keys are read by no src/ code
- **S3-03** [SStage 4 (validation harness)] blocks5=no sweep
  §13.6's state-share absolute error is required 'at minimum' and is not emitted; validate/metrics.py ships five of the eight §13.6 point metrics
- **S3-04** [SStage 1 (ingestion/harmonizati] blocks5=no sweep
  Harmonized snapshot_id is a filename stem, so zero harmonized rows join source_snapshot by its declared key - and the §9.7 diagnostic prints those stems as 'source snapshots'
- **S3-05** [SStage 4 (validation harness)] blocks5=no sweep
  median_ape is nulled for the entire estimator when any single scored truth is zero, instead of being computed over the safe subset §13.6 asks for

## RECORD (18)

- **F-019** [S4] blocks5=no 
  Half the finding is closed — `interval_source` no longer says "rolling" — but the mechanism is unchanged and the divergence from §10.7's SHOULD is recorded only in `src/` and in a retired sub-project spec; the roadmap cites §10.7 in Stage 4's `Spec:` line and credits REQ-013 (§10.7 intervals) with n
- **roadmap-stage3-shipped-1-8** [S3] blocks5=no 
  Items (1)-(6) of the Stage 3 SHIPPED block are true at HEAD and their line pins still land — including the whole compose / WeightDomainError / MAX_SCALE_RATIO passage — but item (7) enumerates four checked enums where the code checks five, and item (8)'s dated witness about `runs/f03023ac9f3a`'s con
- **F-030** [S4] blocks5=no 
  The concentration reproduces exactly at HEAD (whole_seasonal_blocks 8,690 of 12,530 = 69.4%, next largest 600), and the code is correct — but the claim's "unrecorded" is only partly true now: stage-4-log.md:81 carries the 8,690 maximum in a range, while the concentration itself and the pooling cauti
- **F-001** [S4] blocks5=no 
  Three of the four sub-questions answer clean at HEAD (Exit line true, heading suffix present, stamp lapse filed, enforcement owned by open D-085 → Stage 6), but the SAME Stage 4 block's SHIPPED text still quotes an Exit clause 1be5bbf deleted and still asserts the exactly-recoverable rejection is "d
- **F-034** [S1] blocks5=no 
  Every tooling sub-claim holds at HEAD (no type checker, no coverage, no xdist, no `select`, `network` applied zero times), and measuring it surfaced a false record entry: spec decision D4 still says "python-dotenv in the `dev` dependency group", which 861abb7 falsified.
- **F-031** [Sn/a] blocks5=no 
  Partly live: sub-claims 1 and 3 were closed by 9b88a32/D-065 and sub-claim 4 is out of F-031's scope, but sub-claim 2 (ingest/CLAUDE.md spec line pins) is live and joined at HEAD by five more doc defects — the root CLAUDE.md's own internal contradiction (line 20 says the suite is NOT green without d
- **PLAN13-rec-1** [Sroadmap §Post-synthesis requir] blocks5=no sweep
  Roadmap's post-synthesis requirement channel and its retirement scope both still say THREE sub-project specs / 36 requirements; plan 13 made it four / 45, so R-S5P-1..9 are audited by nothing at retirement
- **PLAN13-rec-2** [SStage 1 (roadmap Produces) + s] blocks5=no sweep
  Stage 1's ticked `Produces` promises "a `pyproject.toml` per D4", and plan 13 falsified D4: python-dotenv is no longer in the dev dependency group
- **PLAN13-rec-3** [SStage 3/Stage 4 (root CLAUDE.m] blocks5=unclear sweep
  Root CLAUDE.md says plan 13 made it so "every estimate is checked against its §9 interval" — the validation harness is explicitly exempt, which is D-087's whole subject
- **PLAN13-rec-4** [SStage 4 (roadmap SHIPPED block] blocks5=no sweep
  Plan 13's `e17b1f0` aged `runs/f03023ac9f3a/validation_metrics.parquet` a fifth time — 1,190 rows carry an `interval_source` value HEAD no longer declares — and neither the roadmap Stage 4 block nor the Stage 4 stamp records it
- **PLAN13-rec-5** [SStage 3 SHIPPED point (7) and ] blocks5=no sweep
  Plan 13 widened `assert_declared_provenance` by one line; the roadmap's two `contracts.py:229-253` pins now end inside the raise's f-string
- **PLAN13-rec-6** [SStage 1 (ingest/CLAUDE.md) and] blocks5=no sweep
  Four rotted `spec line NNNN` pins and five mangled `` `-NNN `` citation artifacts survive in ingest/ and reconcile/ CLAUDE.md; plan 13 rewrote one of those very paragraphs and fixed its sibling pin only
- **S2-QSIZE003-RECORD** [SStage 2 (identification engine] blocks5=no sweep
  Stage 2's `Gap closed:` line credits "SRC-QSIZE-003 (hard-control eligibility)" unqualified while half that eligibility condition — the release vintage — cannot be evaluated, because `qcew_national_size` carries no `release_vintage` column
- **PREF-EST-BY-MONTH** [SStage 3 (baselines, ticked)] blocks5=no sweep
  The review's §3.4/§4.2 verdict that `preferred_estimator_by_month` is an UNTRACKED no-consumer symbol is false at HEAD — roadmap Stage 3's RE-VALIDATED block records both that it has no Stage 4 consumer and why — but its other sub-claim, "read by no test", still holds
- **S3-01** [SRecord defect in specs/logging] blocks5=no sweep
  Roadmap's post-synthesis channel and retirement gate both omit the fourth sub-project spec (R-S5P-1..9), so plan 13's nine requirements are audited by nothing
- **S3-09** [SRecord defect in specs/deferre] blocks5=no sweep
  D-072's revisit trigger names the wrong config key and is already satisfied at HEAD: replicates_per_regime is 20, and the '3 seeds' it means is pseudo_suppression_seeds
- **S3-10** [SRecord defect in submodule CLA] blocks5=no sweep
  Four submodule CLAUDE.md sites cite deferred items by TITLE, which the register's own header explicitly forbids
- **S3-14** [SRoadmap gap table, INV-002 row] blocks5=no sweep
  INV-002's Note names Stage 3 and Stage 8 only; the validation-harness exposure D-087 records is a Stage 4 half the Note does not carry

## OWNED (22)

- **D-049** [S1] blocks5=no 
  Every factual half holds at HEAD -- the bulk arm is reachable from fetch but structurally never taken for ANY input, read_bulk_zip has zero callers in src/, and build_harmonized globs only *.csv -- and open D-049 names all of it by file and symbol.
- **F-005** [S2] blocks5=no 
  Two of the three verbs still hold — nothing at 113/1133/11331 or own_code 0 was ever fetched, and no decline was ever recorded — but "never owned" is FALSE at HEAD: the unticked Stage 6 roadmap block explicitly inherits the gap as of 0e186be (2026-09-10), one day after the review.
- **Q-09** [S2] blocks5=no 
  Still unanswered at HEAD — no ruling exists anywhere that either records a decline or commissions the fetch — but the question is no longer unowned: the record now leans explicitly toward 'measure', and Stage 6 carries the settle-before trigger.
- **R-16** [S2] blocks5=no 
  Partly discharged: the RECORD half landed on 2026-09-10 in two places, the MEASUREMENT half was not done at all, and the SCHEDULING half landed one stage late — R-16 required the amendment to be scheduled before STAGE 5 consumes deterministic_bounds, and the roadmap put the trigger on STAGE 6, while
- **Q-22** [S2] blocks5=no 
  Confirmed unmeasured at HEAD, and the claim's stated reason is exactly right — the registry fetches industry/113310.csv at private ownership only; I narrowed the ownership half with a new raw-store measurement but the question itself cannot be answered without a network fetch.
- **F-016** [S2] blocks5=no 
  Confirmed live at HEAD: _needs_milp gates the integer re-solve on LP width alone, so an integer cell with a wide fractional LP interval ships raw fractional LP endpoints — but roadmap Stage 6's Consumes block already inherits it verbatim as item (3), so it is owned, not rework.
- **F-018** [S3] blocks5=yes REFUTED b
  All three sub-claims hold at HEAD, but they do NOT share a bucket: sub-claim 1 (reconcile_matrix takes no bounds) is owned by roadmap Stage 6 item (1), sub-claim 3 (dead general_method guard) is owned by open D-041, and sub-claim 2 (Bounds reads an absent upper as +inf and an absent lower as a bare 
- **D-032** [S2] blocks5=no 
  Live at HEAD and correctly deferred: classify_bound_status does label an integer-free interval partially_identified, and the item's unreachability premise is not merely still true but structurally guaranteed — any integer-free interval has width < 1, and the MILP threshold is 25, so the re-solve alw
- **D-033** [S2] blocks5=no 
  Live at HEAD and correctly deferred: the §9.7 minimum-slack model adds slack variables to coupling rows only, never to the column box, so a component made infeasible by its own bounds reports minimum slack 0 — and the shipped builders still cannot emit such a component.
- **D-034** [S2] blocks5=no 
  Live at HEAD and correctly deferred: rank._shape_key still hashes np.array2string(..., precision=12) and numerical_rank_of still passes rank_tolerance as an absolute singular-value threshold; the reachability premise is re-measured true — every coefficient in the live constraint system is ±1.
- **D-036** [S2] blocks5=no 
  Live at HEAD and correctly deferred, and stronger than the item states: the two flags agree on all 4,775 D1 rows, and the item's own consolation that agreement 'is correct when the MILP ran' is vacuous — the MILP has never run on D1 (milp_lower non-null = 0), while all 1,241 suppressed cells carry a
- **D-061** [S2] blocks5=no 
  Live at HEAD and correctly deferred: bounds.py:75-76 still tells a reader 'Stage 3 adds CBP as empirical_measurement', a stage that shipped and added no such row, and the live constraint table confirms three of contracts.CONSTRAINT_CLASSES' five values have no producer and is_hard has never discrimi
- **D-087** [S4] blocks5=no 
  D-087 holds exactly as written — validate/harness.py:161 still calls run_baselines with no `bounds`, so an out-of-interval harness estimate is unnoticed — but its stated blocker is a DESIGN RULING, not missing input, and I measured the consequence on D1 to be literally zero: all 12,530 scored rows c
- **D-064** [S3] blocks5=no 
  Live at HEAD and properly owned: the register item is open, carries `Size: plan` and a Done-when, and its first key (`baselines.composite_fallback`) is still inert in Stage 3's own code — which is exactly what keeps it out of rework.
- **F-003** [S4] blocks5=no REFUTED b
  Exactly 18 metric names ship at HEAD and the eleven the review enumerated are still absent, with no D-nnn and no roadmap stage owning them; but two of the claim's three clauses are overstated — 6 of the 11 ARE tracked (in validate/CLAUDE.md, a paragraph that predates the review), and §13.10's strata
- **F-002** [S4] blocks5=no 
  The substance is unchanged and live at HEAD (13 regimes, 9 score; §13.2 steps 3 and 6 still have no `src/` caller; every scored row is single-arm, primary-like, unbounded), but the false closure CLAIM is gone — 8a55e59 struck REQ-022 from Stage 4's Gap-closed line, re-scoped the gap-table row, named
- **F-008** [S1] blocks5=no 
  One of the four Produces claims was corrected (the manifest claim — 1be5bbf then 67c5251); the other three are unmet AND still asserted verbatim in a ticked stage's Produces line, but open, sized deferred items carry them (D-058 explicitly including the record remedy; D-049 for the dual route).
- **F-024** [S2, 3, 4] blocks5=no REFUTED b
  Seven of eight sub-items are live at HEAD; (a) is half-closed (the VALIDATION golden gained a hand-derived oracle in plan 13's e17b1f0, the BASELINE golden still has none), and (h) is false as a coverage statement and was already false when the review was written.
- **D-064** [S1, 3] blocks5=no 
  All four of D-064's keys are still unread at HEAD, so the item is live and correctly owns them -- but its headline count is an undercount: the register says four, the review said fourteen, I measure seventeen, and no document reconciles the three numbers.
- **F-013** [Sn/a] blocks5=no 
  Holds in the spec — Appendix B step 6 is unsatisfiable by design and step 7 is vacuous — but the review's impact clause is dead: the roadmap's ## Completion was amended to say Appendix B cannot gate anything and to hand the amendment to Stage 8, whose Exit carries it as a named PRECONDITION.
- **PLAN13-owned-1** [SStage 3 deliverable; remedy ow] blocks5=no sweep
  Plan 13 added a bounds check on the §12.6 integer release but `integerize` is still called without those bounds, so the checker enforces a constraint the producer cannot see
- **S3-08** [SOwned by open D-090 (Size: qui] blocks5=no sweep
  D-090 is open and records that this very enforcement test and the shared backlog reference disagree, so the ledger's schema contract is itself disputed at HEAD

## LATER (17)

- **F-035** [S1 (ingest parser); §5.5's "own] blocks5=no REFUTED b
  The column and the Stage-1 guard are genuinely absent, but the review's load-bearing word "silently" is false at HEAD: a mixed-ownership by-size file does double-count in the Stage 1 table, and then halts `build-constraints` with a named `IncompatibleMarginError` before any constraint row exists.
- **F-004** [Sn/a] blocks5=no 
  The code's anchor is sound, fully implemented and fully recorded in plan 4 / the roadmap / §7.13-§7.14, but §12.2 and §15.2 are byte-for-byte unchanged since the review commit and still name nothing — so the claim's central half holds and is a pure spec-text amendment, not Stage 3 rework.
- **F-020** [S3] blocks5=no 
  The narrowness holds — §10.4's intensity is a plain mean ratio shrunk to the national value only, with no robust estimator, no regional level and no historical adjustment — but §10.4/§10.8 carry no RFC-2119 keyword, so this is a spec-definition gap, not a provable non-conformance; two of the finding
- **Q-06** [S3] blocks5=no 
  The routing doc's "Refuted" overstates: the shrinkage form, k, and the toward-national target ARE recorded (and §10.8 rung 1's "robust historical adjustment" is reinterpreted as composition NORMATIVELY, in spec §10.9) — but "robust" itself is recorded in zero places, so the clause is half-true.
- **R-10** [S4] blocks5=no 
  The relabel half shipped (e17b1f0, as R-S5P-7); the re-implement half did not, its verify criterion "§10.7/§13.7 say which one the coverage gate reads" is unmet, and NOTHING in the record owns building it — while `intervals.py` tells the reader Stage 5 does, citing a section that explicitly declines
- **Q-04** [S4] blocks5=no 
  Still open in the normative text: the repo has answered "rolling means time-ordered" in two prose places, but §10.7 is unamended and no spec or roadmap text records the answer.
- **Q-12** [Sn/a] blocks5=no 
  Answered by measurement and the review's open alternative is settled: the ~415 rules are ruff's BUILT-IN DEFAULTS (413 on 0.16.6), not a config file anywhere -- `--isolated` enables the identical set -- but the reproducibility gap the question was really about is live, because `ruff>=0.9` is unbound
- **R-15** [S2, 3, 4] blocks5=no REFUTED b
  Open and untouched: plan 13 added three new test modules but every one of them pins a DIFFERENT fail-closed arm than R-15's six, and five of the six remain both unpinned and unowned (the sixth, INV-004's class refusal, is carried by open D-061).
- **F-012** [Sn/a] blocks5=yes 
  Partly holds: Appendix A still does not load (4 errors, down from the review's 11), but that residue is now deliberately pinned by a test that reads the spec fence itself, and config.yaml's header cites the heading, not lines — the live half is normative-text work.
- **F-015** [Sn/a] blocks5=yes 
  Holds: the spec moved +5/-2 lines since the review commit and none of it touched these contradictions, so both sides of every one are still in the normative text — but in each case the CODE follows one side and says so in a docstring, so every item is a spec amendment, and four already have an open 
- **F-022** [S3, 4] blocks5=no 
  The historical half is confirmed and unchangeable (the spec sections were written after the code they describe), but the rot it warns of has NOT occurred at HEAD: every code symbol Appendix A names resolves, the dated 12,530-row measurement still holds, and all three field lists match contracts.py e
- **F-023** [S1, 2] blocks5=no REFUTED b
  The routing doc's narrowing to three is PARTLY right — its premise holds (D-057/D-059 and D-061 are open and own two of the six) but its own tables list §10.9 as a seventh survivor, and §13.8 is not a survivor at all. Of the three, two are live, unowned gaps in ticked stages' own code: no table carr
- **S3-07** [SProcess/tooling (register enfo] blocks5=no sweep
  test_deferred_register.py's three assertions are invisible to any open item that lacks a backticked D-nnn id, and nothing enforces the id rules the register's own header states
- **S3-11** [SRoadmap/backlog process, not S] blocks5=no sweep
  24 of 43 open items carry Done when: and therefore no trigger at all - nothing will ever surface them except a full read of the register
- **S3-16** [SStage 5 (unticked) inherits it] blocks5=no sweep
  REFUTED: the routing doc's claim that §17.2's ninth property is 'recorded nowhere' is false - Stage 5's Exit carries the equivalent obligation
- **S3-17** [SSpec-text amendment (§7 preamb] blocks5=no sweep
  The spec contradicts itself on §7's 'every table MUST include run_id and a schema version' - the per-table field lists omit both, and contracts.py conforms to the more specific one
- **S3-18** [SRoadmap/review process] blocks5=no sweep
  35 of the review's 36 F-ids are cited nowhere outside docs/reviews/, so retiring the reviews erases the only handle on findings that were never routed

## CLOSED (14)

- **F-011** [S3] blocks5=no 
  Both halves of the code defect are fixed at HEAD (f3b0db9 added runs.code_provenance + bounds_manifest.json), but the claim's conclusion is still literally true of the only run directory on disk: runs/f03023ac9f3a carries no code_commit in any manifest and has no bounds_manifest.json at all.
- **F-006** [S3] blocks5=no 
  The production half of F-006 — the half the claim names — is CLOSED at dc84958: cli.py now loads deterministic_bounds and run_baselines raises BoundViolationError on any released float or integer outside its solved interval; only the harness half survives, and it is carried by open D-087.
- **D-038** [S3] blocks5=no 
  Closed and correctly closed — the ticked item's closure text matches the code exactly: MAX_SCALE_RATIO is deleted rather than re-derived, and the unit is carried by the EmployeeWeights type.
- **Q-03** [S4] blocks5=no 
  Answered by ruling: `rolling_origin` and `cbp_size_gaps` score NOTHING, by decision — not by oversight — and the roadmap now matches; D-071's own closure condition was written to accept exactly this answer.
- **R-09** [S4] blocks5=no 
  Discharged verbatim: R-09's own verify clause ("the roadmap's Gap-closed line for Stage 4 drops REQ-022 and Stage 5's Consumes names it") is satisfied by 8a55e59, taking the cheap re-scope option R-09 itself offered.
- **F-033** [S1] blocks5=no 
  Closed at a6fcdfb: `tests/unit/test_config.py::appendix_a_fence()` now parses the `## Appendix A` fence out of `specs/logging-employment-spec.md` itself and three tests validate it; the review's citation looks dangling only because the old test was renamed.
- **CLOSED-1** [SStage 3] blocks5=no sweep
  Review R-05 ("nothing in baselines/ loads bounds") is closed: INV-002's per-cell half is enforced on the production path, and it is behaviour-neutral on D1 exactly as R-S5P-3 required
- **CLOSED-2** [SStage 1-4 test suite] blocks5=no sweep
  Review R-02 ("the suite is red on a clean clone") is closed, and CLAUDE.md's arithmetic is exactly right at HEAD — measured, not repeated
- **F-009** [SStage 1 (ingestion, ticked)] blocks5=no sweep
  CLOSED at 4161db9 (plan 13, R-S5P-4) — `fetch` no longer drops a non-200 or empty body silently; it raises `SourceFetchError` unless the absence is declared, and the fix is tested with real 500s and 404s
- **F-007** [Scross-cutting tooling (Stage 8] blocks5=no sweep
  CLOSED — `python-dotenv` is a runtime dependency at HEAD, so the review's "a clean environment cannot run any command" no longer holds
- **S3-06** [SDeferred register schema (proc] blocks5=no sweep
  The Size/Revisit premise is wrong: b8ef669 required Size plus (Done when OR Revisit if), and 43/43 open items satisfy that - zero violations
- **S3-12** [SStage 1-4 backlog ownership (t] blocks5=no sweep
  F-027's '22 of 39 open items are overdue, nine against ticked Stages 1-3' is not re-measurable at HEAD - the metric lost its definition when Size/Revisit fields landed; substitute measurement supplied
- **S3-13** [SRoadmap gap table, Stages 1-5 ] blocks5=no sweep
  Every REQ-/INV- row's Note names an owning stage, and the three Notes the task flagged as suspect (REQ-022, REQ-024, INV-014) are TRUE at HEAD
- **S3-19** [SStages 1-4, various] blocks5=no sweep
  Negative result with its scope: six further review findings that looked like orphans are in fact recorded in code or in the roadmap, and are not rework

## UNVERIFIABLE (1)

- **S3-15** [SReview bookkeeping] blocks5=no sweep
  '82 of 164 items touch the roadmap' is a property of the review's own item ledger, not of the roadmap, and is not independently measurable at HEAD
## Blind audit — surviving divergences (36 of 68 raw; 6 novel)

- [rework] blocks5=no — Harmonized `snapshot_id` is the raw file's filename stem, not the §7.2 retrieval identity, so no harmonized/target/constraint row joins to `source_snapshot` by its declared key
  (prior: F-010 (docs/reviews/2026-09-09-system-review.md:633) — same title, sam)
- [record] blocks5=no — §7 preamble's blanket `run_id` + schema-version MUST is unmet by all fifteen contracts — but the spec's own per-table field lists contradict the preamble
  (prior: F-023 bullet 1 and Q-10 (docs/reviews/2026-09-09-system-review.md:671,)
- [rework] blocks5=no — CBP 2022/2023 rows stamped `naics_vintage = "NAICS 2022"` from BLS QCEW's era rule, while Census's own metadata for those datasets labels the code column "2017 NAICS code"
  (prior: F-036 (docs/reviews/2026-09-09-system-review.md:699), with Q-14 (:868))
- [owned] blocks5=no — source_snapshot.schema_fingerprint records our destination-table schema, so it is constant per source and cannot witness upstream drift
  (prior: roadmap Stage 8 (unticked): Spec "§18 (all)", Produces "the §18.2 moni)
- [rework] blocks5=no — CBP `variables.json` retrievals get no `source_snapshot` row (§7.2), and `build.predicate_from_stored_metadata` picks among copies by sha256 sort order where `snapshot_paths` refuses the same ambiguit
  (NOVEL)
- [record] blocks5=no — `source_manifest.parquet` sits at `runs/` root, not in `runs/<run_id>/` as §6.2's tree shows, and is rewritten in place per source
  (prior: docs/reviews/2026-09-09-system-review.md — §3.3 divergences row 19 and)
- [record] blocks5=no — compat.py's INV-007 NAICS-vintage branch compares two applications of the same era rule, so it cannot fire in production — and no document scopes it the way the cells/rows guards are scoped
  (NOVEL)
- [owned] blocks5=no — `source_publication_date` is `""` at all three fetch sites and `release_status` is a literal `"final"` at two of three, so §7.2's release provenance is constant
  (prior: docs/reviews/2026-09-09-system-review.md §3.3 divergences table (Stage)
- [rework] blocks5=no — Harmonized `snapshot_id` is the filename stem, not the retrieval sha256, so no staged or constraint row joins to `source_snapshot` by its declared key
  (prior: F-010)
- [rework] blocks5=no — CBP 2022/2023 rows are stamped naics_vintage="NAICS 2022" from QCEW's era rule while Census serves and labels those datasets as 2017 NAICS
  (prior: F-036 (docs/reviews/2026-09-09-system-review.md:699) + Q-14 (:868); ro)
- [owned] blocks5=no — `release_status` is stamped from config on every QCEW row and never derived, so SRC-QCEW-005's preliminary/final distinction is a contract column with no producer and no consumer
  (prior: docs/reviews/2026-09-09-system-review.md §3.2 (line 249): "| SRC-QCEW-)
- [owned] blocks5=no — cbp_state_size drops EMP_N_F (CBP's per-cell noise band); employment_noise_range carries the constant EMP_N='0'
  (prior: D-026 (OPEN, specs/deferred_items.md:361) — "`cbp_state_size` has no c)
- [rework] blocks5=no — §5.5 size-margin gate computes an employment residual it never compares — real (= F-017), but confined to 2017, the one year that produces no bound and is already zero-slack at solve-bounds
  (prior: F-017)
- [owned] blocks5=unclear — §9.3's unbuilt margins: the parent/ownership/region core is F-005 + R-16 + Q-09/Q-22; the one new, measured increment is the sub-state county margin — 558 of 1,227 suppressed state cells would gain a 
  (prior: F-005 (docs/reviews/2026-09-09-system-review.md:613) — "The identifica)
- [owned] blocks5=no — §9.2's size universe is built at national geography only; no state×size target cell exists at Stage 2
  (prior: docs/reviews/2026-09-09-system-review.md §3.3 divergence #3 (cell-cons)
- [owned] blocks5=no — `_needs_milp` gates the integer re-solve on an LP interval-width threshold, not on §9.6 step 2's "integer feasibility can change the result", so a wide fractional LP interval on an integer cell ships 
  (prior: F-016)
- [owned] blocks5=no — `classify_bound_status` labels an integer-empty interval `partially_identified` instead of `infeasible`
  (prior: D-032 (specs/deferred_items.md:457, OPEN `- [ ]`) — "`classify_bound_s)
- [rework] blocks5=no — MILP bounds are accepted at HiGHS's default 1e-4 relative MIP gap, so a recorded selected_lower/selected_upper need not be the sharp §9.1 optimum
  (NOVEL)
- [record] blocks5=no — MILP-infeasible branch in constraints/bounds.py omits §9.7's snapshot list and candidate-conflict list (component id and hard halt ARE produced); its quarantine arm swallows the failure, but both arms
  (NOVEL)
- [owned] blocks5=no — `Bounds` cannot distinguish an absent cell from an explicitly unbounded one: absent `upper` reads as +inf, absent `lower` raises a bare `KeyError` in `scale_into_bounds`
  (prior: F-018 (docs/reviews/2026-09-09-system-review.md), plus its §3.3 diverg)
- [owned] blocks5=no — scale_into_bounds' bisection loop returns a non-converged allocation silently (no `else`, no post-check), unlike its own bracket loop and unlike reconcile_matrix
  (prior: roadmap Stage 5 (unticked) Exit line; secondary: 2026-09-09 system rev)
- [record] blocks5=no — reconcile_matrix's achieved-margin post-check gates on a hardcoded rtol=1e-6, not on the configured reconciliation.tolerance
  (NOVEL)
- [owned] blocks5=no — `reconcile.projection.require_supported_method` is dead code, and its module docstring glosses "wherever `general_method` is actually read" as "the CLI commands" — which read only `reconciliation.tole
  (prior: D-041 (OPEN, `specs/deferred_items.md:610-625`) — title "The `general_)
- [owned] blocks5=no — §12.6 step 4's bounded arms are unexercised on the production path: `run_baselines` calls `integerize` with no `lower`/`upper` and substitutes a post-hoc `BoundViolationError` halt
  (prior: roadmap Stage 6 (unticked) RE-VALIDATED point (2); corroborated by roa)
- [rework] blocks5=no — `scale_into_bounds` clamps a contradictory (lower > upper) pair to the cap and returns below the declared lower, while its package sibling `integerize` refuses the same shape with a named error
  (NOVEL)
- [record] blocks5=no — §10.8 rung 1's "robust historical adjustment" is absent from CbpIntensity — already carried by F-020, and the §13.10 consequence is overstated
  (prior: F-020 (docs/reviews/2026-09-09-system-review.md:665), with the same cl)
- [rework] blocks5=unclear — §10.4's shrinkage target is national-only; the "regional" half is unimplemented and unrecorded
  (prior: F-020 (docs/reviews/2026-09-09-system-review.md:665) — "The rung-1 bas)
- [owned] blocks5=no — Baselines reconcile via §12.2's unbounded fast path only; a binding bound raises BoundViolationError instead of applying §12.3's bounded scaling
  (prior: F-006 (primary); Q-07 carries the still-open half; R-05 is the recomme)
- [owned] blocks5=no — §10.7's predictive intervals are a cross-sectional leave-one-out residual pool, not the "rolling" pseudo-suppression residuals the section names
  (prior: F-019 (docs/reviews/2026-09-09-system-review.md:663; also its §3.3 div)
- [rework] blocks5=no — §10.4's "robust" March intensity has no outlier-resistant implementation and no recorded decision declining one
  (prior: F-020)
- [owned] blocks5=no — §10.5 harvest-proportional baseline is an unconditional decline stub (HarvestProportional.weights ignores both arguments)
  (prior: Roadmap Stage 7 (unticked, `specs/logging-employment-spec-roadmap.md:3)
- [record] blocks5=no — §10.9 (composition) was back-ported into the spec after Stage 3 shipped the mechanism, so a §10.9 conformance check is not independent evidence
  (prior: F-023 (bullet 3; routing row `F-023-c-§10.9`, still? = yes) — "§10.9 w)
- [record] blocks5=no — Three objects share the name "the preferred baseline"; baseline_manifest.json publishes the availability-resolved one
  (prior: F-015 (primary); also Q-05, the review's §2.2 terminology bullet (line)
- [owned] blocks5=no — §13.10's comparand `preferred_baseline` returns an undifferentiated `None` and has no `src/` caller; `PromotionConfig`'s three thresholds are read by nothing
  (prior: D-074 (cost-of-the-choice (1), specs/deferred_items.md — closed); also)
- [rework] blocks5=yes — `whole_seasonal_blocks` masks every eligible state cell in the drawn calendar month, emptying the disclosed set; the six `disclosed_qcew`-fallback estimators decline 100% of the regime that supplies 6
  (prior: F-030 (docs/reviews/2026-09-09-system-review.md:687) — carries the 69%)
- [rework] blocks5=no — §13.8's two residual norms are never computed and the §13.8 constraint family emits three per-cell counts instead; two of the four named quantities (row-sum, class-margin) are Stage 6-infeasible
  (prior: F-003 (docs/reviews/2026-09-09-system-review.md:605-608), corroborated)
