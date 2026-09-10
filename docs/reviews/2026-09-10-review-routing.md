# Routing the 2026-09-09 system review into the roadmap (2026-09-10)

**Question.** What must change in `specs/logging-employment-spec-roadmap.md` to implement the
findings of `docs/reviews/2026-09-09-system-review.md`, and does a second roadmap need to exist?

**Method.** Seven extraction agents, one per dimension of the question, each followed by an
adversarial verifier instructed to refute against the tree at `115807f`. 164 items survived
verification. Every claim below was re-checked against the current files; the review was written
at `c4bbf4e`, so its own citations were treated as suspect (this repo has a documented
`spec:NNN` citation-rot problem, and the verifiers found fresh instances — including one in the
review itself: R-03 cites `roadmap:219` for a heading that is at `:225`).

---

## 1. No second roadmap. Amend this one.

Three independent supports, any one of which is sufficient:

1. **`derive-roadmap` §3 forbids it.** "Before writing, scan `specs/` for any file carrying the
   roadmap header that names this spec as its source. If one exists, **STOP — do not write** —
   and surface it: the right move is Resume (§5)." The roadmap carries that header and names the
   spec as its source.
2. **The roadmap already specifies the mechanism.** Its `## Completion` section: "Unmet rows exit
   exactly two ways: a new stage, leaving the roadmap live, or a conscious deferral with a written
   reason." Amendment is the designed path, not a workaround.
3. **A roadmap derives from a source spec, and a review is not one.** The skill's three entry
   conditions admit no path from a findings document to a fresh roadmap.

The review agrees on substance (§7.5): "The remaining roadmap is the right order."

## 2. But most of the review does not belong in the roadmap either

The repo runs **two requirement channels**, and only one of them is the roadmap:

| Channel | Artifact | Plans |
|---|---|---|
| Roadmap stages | `specs/plans/completed/N-stageM-*.md` | 1–4, 11 |
| **Sub-project specs** | `specs/completed/*.md` → its own plan | 5–10, 12 (7 of 12) |

Each sub-project spec opens with a header that settles the question directly:

> REQUIRED SKILL: writing-plans — this spec is the requirements input; it has **no roadmap stage
> of its own and must not be folded into one**.

**This is the right home for the review's R-01…R-11 bundle**, and no agent proposed it.
The channel is a genuine spec→plan cycle, not a retrospective writeup — measured, the spec's
add-commit precedes its plan's in all three cases (`e5d4bdd` 18:01 → `5a3fe38` 18:34; `bf73a1a`
09-06 17:13 → `10d9295` 09-07 10:01; `56511c2` 12:27 → `fc40495` 12:55). The review
offers only "a short 'Stage 4.5' (or a Stage 5 precondition list)". A fractional stage has two
costs the sub-project channel avoids: it breaks the `Stage N` stamp protocol (`### Stage stamps`
in the spec, and `roadmap-format.md`'s stamp text), and it puts remediation work into a sequence
that is otherwise a dependency graph, not a chronology.

**Correction to the review, verified:** §7.5 calls that bundle "record-only" and sizes it at "a day
of work". Both halves are wrong. R-01 (`pyproject.toml:28` — `python-dotenv` is under
`[dependency-groups] dev`, absent from `[project].dependencies`), R-02 (no `skipif` in any
`tests/unit/test_validate_*.py` nor in `tests/conftest.py`), R-05 (`baselines/runner.py:253`
allocates with no bounds join), R-06 (`fetching.py` bare `continue` at `:120, :141, :163, :171`)
and R-07 (`code_commit` / `uv_lock_sha256` grep empty) are **code** changes. Measured effort:
1 × minutes + 8 × hours + 2 conditional → **days, and `ROUTING: writing-plans`**.

The "R1, R5, R7, R9" tokens in that same sentence are **risk-register ids from §6**, not
recommendation ids. And the claim that the bundle "removes R1" is overclaimed: R1 cites F-003,
whose fix is R-12, which the review itself files under Stage 5 at effort `days`. The bundle
**reduces** R1; it does not remove it.

## 3. What genuinely changes in the roadmap

Of 164 verified items, **82 touch the roadmap** and 82 do not.

### 3.1 Stage 5 is the urgent one (17 items land here alone, 30+ counting shared)

The review's loudest message (exec summary point 1, R-13, risk R1) is "do not plan Stage 5 from
the roadmap's Stage 4 block or the spec's §13." Verified at HEAD, independently re-measured:

- `uv.lock` holds **38 packages and no PPL** — no `jax`, no `numpyro`. Stage 5 cannot start.
- `PromotionConfig` is **read by no code** in `src/`.
- `preferred_baseline` returns **`str | None`** (`validate/scoreboard.py:134`, empty-candidates
  `None` at `:119`) — the §13.10 comparand can be absent, and the spec has no `None` case.
- **1,227 of 1,227** state cells are `unbounded`, `selected_upper` null.
- Two `assert_declared_provenance` callers (`runner.py:312`, `harness.py:165`) against
  `roadmap:241`'s "only caller is runner.py:218" — **the Stage 5 block is already stale**.
- `harness.py:157` computes `arm = _mask_arm(targets)` against `roadmap:235`'s "hardcodes arm" —
  **stale too**.

**A verifier inverted one recommendation, correctly.** The natural fix — stuff all this into
Stage 5's `Consumes` — violates `roadmap-format.md`, which defines `Consumes` as "what this stage
assumes already exists **from prior stages**". "No PPL installed" and "adding a `model:` block
re-ids every run directory" are not prior-stage outputs; the second is a consequence of Stage 5's
own first act. These belong in a **precondition artifact**, not in `Consumes` — which is the same
conclusion as §2 above.

**The Stage 5 gate: recommend the spec amendment plus an explicit re-gate, not a 5a/5b split.**
The dependency problem is real and confirmed: `roadmap:250` Stage 6 (Phase 4) consumes Stage 5's
`PosteriorDraws` and precedes Stage 7 (Phase 5a), so the gate's inputs (§10.5 harvest baseline,
the H component) arrive after Stage 6 already needs the draws. §7.5 offers two fixes and picks
neither:

- **Split into 5a (fit) / 5b (gate)** — makes the dependency honest, but reorders the roadmap to
  5a, 6, 7, 5b, 8 and creates a stage whose only job is to re-read a scoreboard.
- **Amend §11.1/§13.10 so the first promotion decision is provisional** — cheaper, and touches
  the spec rather than the stage sequence. But on its own it leaves the re-gate unowned, which is
  exactly F-028's complaint and Q-08's open question.

**Recommended (a synthesis of the two, which the review does not state):** take the amendment,
*and* add the re-gate to **Stage 7's** `Produces`/`Exit` — Stage 7 is the stage that delivers the
missing inputs, so it is the natural owner. This closes F-028 and Q-08, costs one spec amendment
plus one stage-block edit, and leaves the stage sequence intact. Prefer the 5a/5b split only if
the gate turns out to be a separate deliverable rather than a re-run.

### 3.2 The gap table: a scope extension, not a bug fix

36 post-synthesis requirement ids exist — R-COMP-1…11, R-BREAK-1…5, R-S4C-1…20 — minted by the
three sub-project specs in `specs/completed/`. **None is in the `## Gap analysis` table.** The
only roadmap mentions of any of them sit at lines 223, 230 and 235, *inside* the 6.6–13.2 KB
single-line `SHIPPED` / `RE-VALIDATED` blocks.

Two corrections to that framing, both from verifiers:

- The R-S4C **substance** is partly in `roadmap:235` (it carries "SUPERSEDED 2026-09-09 by plan
  12", the four-switch fact, the §7.14/§7.15 field lists) even though the **ids** are absent. So
  the ownership gap is narrower than "36 requirements untracked" — but it is recorded in exactly
  the accretion-prone prose the review wants dismantled.
- `gap-rubric.md` scopes the table to "EVERY numbered spec requirement" **of the source spec**.
  The 36 R-* ids are not that. Adding them is a **deliberate extension of the rubric's declared
  scope** and must be recorded as a decision, not slipped in as a correction.

**F-023's unnumbered MUSTs shrink from six to three.** Two are already in the visible backlog
(the §16.1 manifest MUST and the §7.8/§9.3 soft-constraint classes), and `gap-rubric.md` folds
unticked deferred entries into the partition on resume — so F-023's impact clause is false for
those. Only three are recorded nowhere: **§7 preamble's `run_id` + schema-version MUST, §17.2's
ninth property, and §13.6's share/rank metrics.**

**One item no agent's brief asked for, found anyway:** `roadmap:202` — a *ticked* stage's
`Produces` line — claims all four Stage 1 commands write a manifest. False at HEAD. It must be
corrected in the same commit, or the roadmap will simultaneously assert that Stage 1 produced
them and that they are missing.

### 3.3 Stage-block format: a return to the canonical format, not a departure

`roadmap-format.md` says a stage carries "exactly these fields and nothing else" and lists eight.
The current roadmap adds `SHIPPED`, `RE-VALIDATED` and `UPDATED`. So §7.4 item 3 is a **return to
the skill's own format** plus a new sidecar (`specs/findings/stage-N-log.md`) — `specs/findings/`
already exists and holds four files.

**Attribution correction.** I and the review both associated the malformed Stage 4 block (its
blank line splits the block instead of terminating it: `:233` ROUTING / `:234` blank / `:235`
SHIPPED / `:236` Stage 5) with the `be70360` "keep both" merge. **False.** `git show
771dabe:specs/...` shows the identical structure a full day earlier — it is authoring damage from
the Stage 4 tick commit, the same commit Q-02 flags for the missing stamp. The merge hazard is
independently real (`be70360` carried two `SHIPPED (2026-09-07` lines, 6,863 B and 6,376 B, for
2 h 06 m on main) but did not cause this.

**A proposed 120-character line cap does not survive measurement** — 60 of 85 non-blank stage
lines exceed it, across all ten stages including seven untouched ones. Scope the rule to the log
file and the lines the migration actually rewrites.

### 3.4 The retirement gate is compromised

`## Completion` gates retirement on "confirming the Appendix B scenario runs end-to-end from a
clean environment", and F-013 shows Appendix B is unsatisfiable as written (`spec:2281-2282`
unamended at HEAD). So **nothing currently defines what "done" means for the roadmap as a whole.**
Do not copy Stage 8's Exit text into `## Completion` — `derive-roadmap` §3 warns that a roadmap
restating a constraint becomes "a second source of truth that will drift". Point at it instead.

## 4. What must NOT go in the roadmap

| Destination | Items | Home |
|---|---|---|
| `deferred-item` | 29 | `specs/deferred_items.md` |
| `spec-amendment` | 21 | `specs/logging-employment-spec.md` (§7.4 item 1) |
| `fix-now-code` | 12 | a sub-project spec + plan |

**A blocker for all 29 deferred items:** `deferred_items.md` carries **no `D-nnn` ids at HEAD**
(`grep -c "D-0[0-9][0-9]"` → 0). The review's D-057/D-069/D-071 are *review-local indexes into the
file*, not ids in it. Until §7.4 item 5 lands, no roadmap line, stage block or spec note can
cross-reference a deferred item — which is why the review had to invent its own numbering.

Also: `tests/unit/test_specs.py` **does not exist**, and no test reads the roadmap. §7.4 item 4's
stamp-protocol test would be a new file, not an edit.

## 5. Already fixed — do not re-do

| Item | Evidence |
|---|---|
| **F-014** (missing prompt source; `.md.md` citation names) | Resolved by `c7abb05` + `115807f`; all five source files present, Appendix C cites tracked names |
| **§7.13 gap row** | Already implemented (`contracts.py:341`); its MUST is `spec:752-753` |
| **Q-13** (comparand byte-identity) | Only one commit touched `src/` since the stamp (`c4bbf4e`), and it is 100 % comment/docstring |
| **Q-06** (rung-1 omissions unrecorded) | Refuted — 8 hits, 3 load-bearing |
| **Q-19** (`runs/_baseline_pre_stage4c/`) | Answered by its own `DIGESTS.txt`; gitignored |
| **Q-02** (which completion date) | Spec stamp `:2502-2506` reads "implemented by plan 11 … and completed by plan 12" |

Still true and still unfixed at HEAD: **124 of 164** items; 30 partly; 4 unverifiable.

## 6. Recommended sequence

1. **One sub-project spec** — `specs/stage5-preconditions.md`, carrying the standard
   "no roadmap stage of its own" header — covering R-01…R-11. Routes to `writing-plans`.
   Effort: days. This is the review's "Stage 4.5" without a fractional stage.
2. **Roadmap amendments, in one commit** (they interlock): Stage 4 heading suffix + Exit
   correction; `roadmap:202`'s false manifest claim; Stage 5's two stale claims (`:241`, `:235`);
   the Stage 7 re-gate (§3.1); Stage 6 `Consumes`; Stage 8 Exit; `## Completion`; the gap-table
   scope decision; the stage-block format rule. **Not** the Stage 5 planning hazards — those
   violate `roadmap-format.md`'s `Consumes` definition and belong in step 1's artifact (§3.1).
3. **Give `deferred_items.md` stable ids** before anything tries to cite one.
4. **Then** re-run `derive-roadmap`'s Resume step and route Stage 5.

Steps 1 and 3 are independent of step 2 and can run in parallel.

---

## Appendix — full routing table

164 verified items. `still?` is whether the claim holds at `115807f`.

| Destination | Id | still? | Effort | Claim |
|---|---|---|---|---|
| roadmap-new-stage | `F-005` | partly | days | The identification engine bounds no state cell, and the §9.3 margins (parent industry, ownership, region) that could change that were never fetched, … |
|  | `REVIEW-7.5-STAGE-4.5` | yes | days | Review §7.5's FIRST bullet recommends inserting a short record-only "Stage 4.5" (or a Stage 5 precondition list) covering R-01 to R-11 — the analyst'… |
|  | `a0-record-only-verdict` | yes | days | §7.5 bullet 1 calls the proposed pre-Stage-5 stage "record-only" and sizes it at "a day of work". |
|  | `a1-new-stage-block` | yes | days | §7.5 bullet 1: "Insert a short 'Stage 4.5' (or a Stage 5 precondition list) that is record-only: R-01 to R-11 above." |
| roadmap-stage-edit | `F-001` | partly | hours | Stage 4 is ticked COMPLETE against two exit criteria the code does not enforce; the heading lacks the completion suffix Stages 0-3 carry; the stamp l… |
|  | `F-002` | yes | hours | REQ-022 and four of §13.3's thirteen regimes are claimed closed while producing no score; §13.2 steps 3, 6 and 8 have no live content on the scoring … |
|  | `F-008` | yes | hours | Stage 1 is ticked COMPLETE with four Produces claims unmet (both QCEW routes; the source_registry and dimension tables; the §3.1 classification memo;… |
|  | `F-016` | yes | minutes | §9.6 step 2's MILP trigger is a width heuristic, so an integer cell with a wide fractional LP interval ships non-sharp, non-integer bounds. |
|  | `F-018` | yes | minutes | Stage 6's inherited reconciliation surface is overstated: reconcile_matrix takes no bounds, Bounds treats an absent upper as +inf and an absent lower… |
|  | `F-019` | yes | minutes | §10.7's predictive intervals are cross-sectional leave-one-out within a replicate, labelled rolling_residual_ensemble, and §13.10's coverage gate wou… |
|  | `F-020` | partly | minutes | The rung-1 baseline the model will be gated against is narrower than §10.4/§10.8 specify, and the omissions are recorded nowhere. |
|  | `F-023-c-§10.9` | yes | minutes | F-023 bullet 3 (surviving half): §10.9 was added post hoc and appears in no `Spec:` line. |
|  | `F-028` | yes | hours | A spec-required baseline and a "required" model component arrive after the gate that needs them, with no re-gate step; Stage 5's dependencies are abs… |
|  | `MECH-S3` | yes | hours | Mechanically, what must happen to Stage 3's 11,323-byte SHIPPED line. |
|  | `MECH-S4-REVALIDATED` | yes | hours | Mechanically, what must happen to Stage 4's 6,661-byte RE-VALIDATED line. |
|  | `MECH-S4-SHIPPED` | yes | hours | Mechanically, what must happen to Stage 4's 13,199-byte SHIPPED line — which is also structurally orphaned. |
|  | `Q-07` | yes | days | Is §10's "same hard bounds" clause for baselines deliberately deferred, or an unowned gap (F-006)? |
|  | `Q-08` | yes | hours | Will the promotion record be re-run after Stage 7 delivers the live §10.5 baseline and the harvest factor §11.1 calls "required", or is §11.1 wrong t… |
|  | `Q-11` | partly | hours | Which stage owns the §13.5–13.8 metrics the harness does not emit (F-003)? The roadmap assigns none; Stage 4 claims REQ-023. |
|  | `Q-15` | partly | hours | Does the QCEW national size benchmark's lack of classes 8–9 for 113310 reach Stage 6's design, given §11.8/§12.5 reconcile state-size draws to nation… |
|  | `Q-16` | yes | hours | What numeric tolerances does Stage 5's Exit ("within stated tolerances") refer to? §17.5 states none; §11.14 leaves ESS and the monitored-parameter l… |
|  | `Q5-existing-stage-block-edits` | partly | hours | Question 5: does extending the table force edits to existing stage blocks' `Gap closed:` lines? |
|  | `R-03` | partly | hours | Record the Stage 4 completion truthfully: amend the Exit line to what shipped, add the heading suffix, and file the stamp lapse. |
|  | `R-09` | yes | hours | Decide what rolling_origin scores before Stage 5, or re-scope REQ-022 explicitly. |
|  | `R-12` | yes | days | Add the metric families Stage 5's gate needs, or amend §13.10 to the metrics that exist. |
|  | `R-12/stratified-metrics-ownership` | yes | days | §13.10's stratum clauses and the mislabelled §10.7 interval have no owning stage. |
|  | `R-13` | yes | minutes | Write Stage 5's plan against the tree, not the roadmap block. |
|  | `R-13/consumes-bounds-key-semantics` | yes | minutes | Stage 5's Consumes must name `Bounds`'s key semantics. |
|  | `R-13/consumes-inert-promotionconf…` | yes | minutes | Stage 5's Consumes must name the inert `PromotionConfig`. |
|  | `R-13/consumes-missing-H` | yes | minutes | Stage 5's Consumes must name the missing H component. |
|  | `R-13/consumes-no-ppl-in-lock` | yes | minutes | Stage 5's Consumes must name the absence of jax/numpyro in the lock. |
|  | `R-13/consumes-none-comparand` | yes | minutes | Stage 5's Consumes must name the `None` comparand case. |
|  | `R-13/consumes-reconciliationinputs` | yes | minutes | Stage 5's Consumes must name `ReconciliationInputs`. |
|  | `REC3-REC4-CONFLICT` | yes | minutes | Rec 3 removes fields on canonicity grounds while rec 4 proposes a test entrenching a different non-canonical element; and Stage 4's heading is missin… |
|  | `SCOPE-S5-S6-REVALIDATED` | yes | minutes | Rec 3 names three blocks; two more non-canonical fields exist on the UNTICKED Stages 5 and 6 and the rule must cover them. |
|  | `a3-stage4-block-repair` | yes | hours | R-03: record the Stage 4 completion truthfully — amend the Exit line to what shipped, add the heading suffix, drop REQ-022. |
|  | `b1-stage5-produces-provisional` | yes | hours | §7.5 bullet 2: "Split Stage 5's promotion gate from Stage 5's model... Either make the gate a Stage 5b that runs after Stage 7 delivers §10.5 and H, … |
|  | `b2-stage7-regate` | yes | hours | F-028: "either the promotion record is re-run after Stage 7 or §11.1 is wrong — the roadmap says neither." |
|  | `c1-stage6-consumes` | yes | hours | §7.5 bullet 3: Stage 6's Consumes should inherit F-006, F-016, F-018 and D-071's cbp_size_gaps half, plus the §9.3 margin question and the size-arm h… |
|  | `c2-stage6-gap-and-exit` | yes | hours | Corollary of c1 and a4: Stage 6's Gap-closed and Exit lines must show the inherited obligations as observable outcomes, per roadmap-format.md ("Exit:… |
|  | `d2-stage8-exit` | yes | hours | Stage 8's Exit cites Appendix B as its clean-room criterion. |
|  | `omitted-Q-16-tolerances` | yes | minutes | (OMISSION, not a refutation.) Stage 5's Exit says 'within stated tolerances' and no tolerances are stated anywhere; the proposed Exit rewrite preserv… |
|  | `omitted-R-09-REQ-022` | yes | minutes | (OMISSION, not a refutation.) R-09 names REQ-022 / `rolling_origin` as a Stage 5 Consumes item and the list has no clause for it. |
|  | `omitted-spec-line-238` | yes | minutes | (OMISSION, not a refutation.) Stage 5's `Spec:` field carries the same stale '(gate applied)' parenthetical the list corrects on the `Gap closed:` fi… |
|  | `roadmap-202-manifest-claim` | yes | minutes | NEW ITEM (missing from the analysed list): roadmap:202, a TICKED stage's `Produces` line, asserts something false at HEAD. |
|  | `roadmap-stage4-stale-arm-claim` | yes | minutes | The Stage 4 block's inherited-contract text (roadmap:235) is stale at HEAD in a way that would mislead a Stage 5 planner about the two-arm scoreboard… |
|  | `stage5-consumes-bounds-vacuous` | yes | minutes | Stage 5 must be told the deterministic bounds are vacuous on its own target. |
|  | `stage5-consumes-model-block-reids` | yes | minutes | Stage 5's first act re-ids the run directory holding the comparand it gates against. |
|  | `stage5-consumes-replacement` | partly | minutes | Step 4 — the exact replacement text for Stage 5's Consumes line. |
|  | `stage5-delete-revalidated` | yes | minutes | Line 241's RE-VALIDATED field must be deleted, not kept beside the new Consumes. |
|  | `stage5-exit-replacement` | yes | minutes | Stage 5's Exit must say the promotion decision is provisional, must define the `None` branch, and must not let the bound check pass vacuously. |
|  | `stage5-gap-closed-replacement` | yes | minutes | Stage 5's `Gap closed:` line claims REQ-024 '(gate applied)' and INV-014 '(applied)' — neither is fully dischargeable at Stage 5 under the amendment. |
|  | `stage7-consumes-append` | yes | minutes | Stage 7 must explicitly consume Stage 5's provisional promotion record. |
|  | `stage7-exit-append` | yes | minutes | Stage 7's Exit must carry the re-gate as an observable outcome, and its Gap closed must own the re-gate half of REQ-024/INV-014. |
| roadmap-gap-table | `F-023` | yes | hours | Unnumbered MUSTs are owned by no stage; the gap table has never been extended past the 76 ids of 2026-09-03. |
|  | `F-023-a-§7-preamble` | yes | hours | F-023 bullet 1: §7 preamble MUST (`run_id` + a schema version on every table) is owned by no stage; no table has either. |
|  | `F-023-d-§17.2-ninth` | partly | minutes | F-023 bullet 4: §17.2's ninth property ("every reconciled draw lies within bounds and satisfies margins") was handed Stage 2 -> Stage 3 and implement… |
|  | `F-023-f-§13.6-metrics` | partly | hours | F-023 bullet 6: §13.6's size-share and rank metrics were assigned to Stage 4 by range and are infeasible before Stage 6. |
|  | `R-BREAK-1..5` | partly | hours | Add 5 gap rows for R-BREAK-1..5. |
|  | `R-COMP-1..11` | partly | hours | Add 11 gap rows for R-COMP-1..11 ("§10.9"). |
|  | `R-S4C-1..20` | partly | hours | Add 20 gap rows for R-S4C-1..20; the family has ZERO roadmap presence. |
|  | `a4-gap-table-req022` | yes | minutes | R-09 verify clause: "the roadmap's Gap-closed line for Stage 4 drops REQ-022 and Stage 5's Consumes names it." |
|  | `c3-inv002-gap-row` | yes | minutes | INV-002's gap-table row credits only Stage 3 and Stage 8, so a derive-roadmap resume reading the table alone cannot see that the bounds half is unenf… |
|  | `gap-table-INV-014` | yes | minutes | The gap table's INV-014 row assigns 'applied' wholly to Stage 5. |
|  | `gap-table-REQ-013-REQ-023` | yes | minutes | The gap table credits Stage 4 with §10.7's intervals unqualified, while the interval is mislabelled (F-019). |
|  | `gap-table-REQ-024` | yes | minutes | The gap table's REQ-024 row assigns 'gate applied' wholly to Stage 5. |
|  | `gap-table-companions` | yes | minutes | Five one-cell gap-table Note edits are required by F-002, F-003 and F-005 but were buried inside those rows' edit fields, leaving the roadmap-gap-tab… |
| roadmap-format | `7.4-2-premise` | partly | minutes | Review §7.4 item 2 (review:834) says to extend the roadmap gap table for "§10.9 R-COMP-1..11, §7.13, §13.8 decline paragraph, R-BREAK-1..5, R-S4C-1..… |
|  | `F-021` | yes | hours | The roadmap's completed-stage blocks are single lines of 6.6-13.2 KB that accrete dated corrections in place; nothing states how the markers compose. |
|  | `Q-02` | no | minutes | Is the Stage 4 tick without a spec stamp deliberate? Which of the three completion dates is authoritative? |
|  | `Q2-canonicity-verdict` | yes | minutes | Section 7.4 item 3 proposes changing the roadmap's stage-block format. Is that a return to the canonical format or a departure from it? |
|  | `Q3-FINDINGS-DIR` | yes | minutes | Rec 3: move measurements and corrections to a dated `specs/findings/stage-N-log.md`. Does specs/findings/ exist and would that fit? |
|  | `RULE-TEXT` | yes | minutes | Rec 3: 'Add one rule: a marker (CORRECTED, SUPERSEDED) replaces the sentence it corrects; it does not append to it.' |
|  | `a2-numbering` | yes | minutes | Does derive-roadmap's stage model permit a fractional "Stage 4.5"? The stamp protocol says "Stage N". |
|  | `blocker-note-column` | partly | minutes | Implicit in item 2: the gap table's Note column can name an owning stage for each new id. |
|  | `f1-stage4-stage5-blank-line` | yes | minutes | Format defect at the exact insertion point for the new stage: Stage 4's SHIPPED block runs straight into Stage 5's heading. |
|  | `g1-format-tension` | yes | hours | §7.4 item 3 asks to freeze a completed stage's block to a short "what a later stage inherits" list and move measurements into dated specs/findings/st… |
|  | `roadmap-format-stage-blocks` | partly | hours | Review §7.4 item 3: change the roadmap's stage-block format — freeze a completed stage to a short inherit list and move measurements to a dated `spec… |
| roadmap-completion | `F-027` | partly | minutes | Deferral hygiene is honest but the backlog is unowned: 22 of 39 open items are overdue, nine of them against ticked Stages 1-3; tracking is split acr… |
|  | `Q-03` | yes | days | What should `rolling_origin` and `cbp_size_gaps` score? Until decided REQ-022 is unmet in substance while the roadmap says it is closed. |
|  | `e1-completion-gate` | yes | hours | The roadmap's "## Completion" section gates retirement on the Appendix B scenario, which F-013 shows is unsatisfiable. |
|  | `evidence-cost-driver` | yes | hours | Sizing input: how much of the 36-row R-* backfill can be evidenced mechanically. |
| spec-amendment | `7.5/split-vs-amend-recommendation` | yes | hours | Step 5 — should Stage 5 be split into 5a (fit) and 5b (gate), or should §11.1/§13.10 be amended to make the first promotion decision provisional? |
|  | `F-004` | partly | hours | The required national-residual reconciliation rests on an anchor the normative spec never names; §12.2 was never amended after Stage 0's SRC-QCEW-006… |
|  | `F-012` | yes | hours | The reference configuration (Appendix A) does not load, and `config.yaml`'s header describes a different Appendix A than the one in the file. |
|  | `F-013` | yes | hours | Appendix B (the roadmap's retirement gate) cannot be satisfied as written. |
|  | `F-015` | yes | days | Nine papered-over contradictions remain in the normative text (both sides present, mutually inconsistent, resolved only in roadmap prose or code). |
|  | `F-022` | yes | hours | For three persisted tables and one config block the spec is a post-hoc description of code, and it now depends on code symbols and dated measurements. |
|  | `F-029` | yes | hours | Separation of duties for disclosure approval was dropped in synthesis. |
|  | `Q-01` | partly | minutes | Should §2.1 and Appendix C cite the source documents by their tracked file names? |
|  | `Q-04` | yes | minutes | Is §10.7's "rolling" meant as time-ordered? If yes the coverage/CRPS numbers need a redesign. |
|  | `Q-05` | partly | minutes | Which "preferred transparent baseline" governs §13.10 — §10.4's designation, §10.8 rung 1, or `preferred_baseline` (which may return `None`)? |
|  | `Q-10` | yes | minutes | Is §7's preamble (every table carries `run_id` and a schema version) still intended? No contract carries either and no stage owns it. |
|  | `Q-20` | yes | hours | Should the `config.yaml` toggle that can violate §10.3's MUST (`historical_may_cross_naics_vintage`) refuse, or be labelled sensitivity-only? |
|  | `R-04` | partly | hours | Amend §12.2 and §15.2 to name the anchor. |
|  | `R-08` | yes | hours | Fix Appendix A or stop calling it the reference: make it load. |
|  | `R-10` | yes | hours | Re-label or re-implement §10.7's intervals. |
|  | `R-14` | partly | hours | Decide the config-evolution policy before adding the model: block — accept a one-time re-id of every run directory, or version the config in run_id. |
|  | `SPEC-STAMPS-BLOCKER` | yes | hours | Not in the review's rec 3 — deleting the roadmap blocks orphans two spec stamps that the spec itself calls authoritative. |
|  | `b3-spec-1310-provisional` | yes | hours | §7.5 bullet 2's second option: "amend §11.1 and §13.10 to say the first promotion decision is provisional." |
|  | `d1-appendix-b-rewrite` | yes | hours | §7.5 trailing sentence: "Stage 8's exit needs the same treatment as Stage 4's had to have: the Appendix B scenario must be rewritten before it can be… |
|  | `spec-amend-11.1` | yes | minutes | §11.1 lists H as a required component with no provision for fitting before it exists. |
|  | `spec-amend-13.10` | yes | minutes | §13.10 contemplates neither an undefined comparand nor a gate whose inputs do not exist. |
| deferred-item | `BL-closed-sets` | yes | hours | §7.3 backlog: enforce mask_arm, bound_status, solver_status, interval_source closed sets in assert_declared_provenance. |
|  | `BL-publication-date` | yes | days | §7.3 backlog: populate source_publication_date from the response headers (Last-Modified) and make harmonized snapshot_id the retrieval digest, or add… |
|  | `BL-state-enumerations` | yes | hours | §7.3 backlog: derive the six D1 state enumerations from the run manifest (D-062's rule) in interfaces.py, historical.py, config.py. |
|  | `F-003` | yes | days | Eleven of §13.5-13.8's required metrics are not emitted and not tracked, and §13.10's stratum gates have no data source. |
|  | `F-009` | yes | hours | `fetch` silently drops any quarter or year whose response is non-200 or empty, recording nothing. |
|  | `F-010` | yes | days | Harmonized `snapshot_id` is a filename stem, so no harmonized or constraint row joins to `source_snapshot` by its declared key. |
|  | `F-011` | yes | hours | `run_id` excludes source code and §18.1's code commit and lock hash are recorded nowhere, so a stale run directory is undetectable from its manifests. |
|  | `F-023-b-soft-classes` | yes | hours | F-023 bullet 2: §7.8/§9.3's three soft constraint classes are declared and produced by nothing; `bounds.py:75-76` cites Stage 3 as the producer, and … |
|  | `F-023-e-§16.1-manifest` | yes | hours | F-023 bullet 5: §16.1's "Every command MUST write a machine-readable manifest" — four of nine implemented commands write none. |
|  | `F-024` | partly | days | Coverage is broad but several load-bearing witnesses cannot fail on a wrong answer (eight sub-items a through h). |
|  | `F-025` | yes | days | Fourteen config keys govern nothing yet fold into run_id and config.resolved.yaml; ValidationConfig is frozen by the run-id policy; propensity weight… |
|  | `F-026` | yes | days | Fail-closed paths raise builtins outside the LoggingEmploymentError hierarchy the conventions prescribe, and no test references the base class. |
|  | `F-030` | yes | minutes | One regime supplies 69% of all scored rows (whole_seasonal_blocks 8,690 of 12,530; the next largest 600); unrecorded. |
|  | `F-033` | yes | hours | test_config.py::test_appendix_a_config_parses parses a literal shaped by the code, not Appendix A. |
|  | `F-034` | yes | hours | No type checker, no coverage tooling, no pytest-xdist, and the 415-rule ruff set is declared nowhere; slow/network markers are declared and never des… |
|  | `F-035` | yes | hours | qcew_national_size has no ownership column and no ownership guard; a by-size file carrying total-covered or government rows would double-count silent… |
|  | `F-036` | partly | hours | CBP naics_vintage is stamped from QCEW's era rule; if CBP 2022/2023 are NAICS-2017-coded the INV-007 label on those rows is wrong. |
|  | `Q-09` | yes | days | Is a recorded decline the intended outcome for §9.3's parent-industry, ownership and region margins on D1 (F-005), or should someone fetch 113/all-ow… |
|  | `Q-14` | yes | hours | Are CBP 2022/2023 rows NAICS-2017-coded or NAICS-2022-coded (F-036)? |
|  | `Q-17` | unverifiable | hours | Has the full-window offline byte-identical rebuild been re-run since 2026-09-05? |
|  | `Q-21` | yes | hours | Are BEA `SAEMP25N`/`SAEMP27N` the same tables as the `SAEMP25`/`SAEMP27` that D6 records as discontinued 2024-09-27? SRC-OTH-005's deferral rests on … |
|  | `Q-22` | yes | days | In state-months where 113310 is `N`, how often does QCEW disclose 1133, 11331, 113 or the total-ownership 113310 cell? A disclosed parent would exact… |
|  | `R-06` | yes | hours | Make `fetch` fail closed on a non-200 or empty body, and record fetch failures. |
|  | `R-07` | yes | hours | Stamp code identity into every run manifest and record output hashes for `solve-bounds`. |
|  | `R-11` | partly | hours | Re-triage the 22 overdue deferred items with an owner each. |
|  | `R-16` | partly | hours | Measure, then record, the §9.3 margin decision — fetch the D1 state slices for industries 113, 1133, 11331 and for total ownership at 113310 and coun… |
|  | `TEST-ENFORCE` | yes | hours | Rec 4 proposes tests/unit/test_specs.py asserting heading suffix + matching spec stamp. The format rule needs enforcement in the same place or it wil… |
|  | `a5-dnnn-ids-are-dangling` | yes | hours | Every one of the five proposed edits, as the review phrases them, cites deferred items by D-nnn id (D-071, D-041, D-082, D-084...). |
|  | `e2-completion-srcoth005` | yes | minutes | The Completion section's SRC-OTH-005 retirement condition rests on a premise the 2026-09-10 addendum flags as unmeasured (Q-21). |
| fix-now-code | `BL-milp-tighten` | yes | hours | §7.3 backlog: tighten LP endpoints for integer cells when the MILP is skipped — ceil(lower - tol), floor(upper + tol) in classify_bound_status's call… |
|  | `BL-reconcile-bounds` | yes | minutes | §7.3 backlog: give reconcile_matrix a bounds parameter, or say in its docstring and the roadmap that it is unbounded. |
|  | `F-006` | yes | hours | INV-002's per-cell-bounds half is unenforced on the baseline production path; baselines and draws use different reconciliation entry points. |
|  | `F-007` | yes | minutes | A clean environment cannot run any command: `python-dotenv` is a dev-only dependency imported at module scope by `config.py`. |
|  | `F-017` | yes | hours | The §5.5 size-margin gate aggregates the employment sum and never compares it, even in the one year it says is checkable. |
|  | `F-031` | partly | minutes | Submodule CLAUDE.md files and the root file carry claims already false at HEAD (four sub-claims). |
|  | `F-032` | yes | hours | §13.6's median APE is nulled for the whole estimator if any scored truth is zero, rather than computed over the safe subset. |
|  | `Q-12` | partly | minutes | Where do ruff's ~415 enabled rules come from? `ruff check src tests` is clean may not reproduce on another binary. |
|  | `R-01` | yes | minutes | Move `python-dotenv` to runtime dependencies. |
|  | `R-02` | yes | hours | Guard the 42 data-dependent tests and make the suite green on a clean clone. |
|  | `R-05` | yes | hours | Enforce INV-002's bounds half on the baseline path. |
|  | `R-15` | partly | hours | Pin the fail-closed surface that mutation showed unpinned. |
| already-done | `F-014` | no | minutes | The spec cited a binding source document not in the repository, and its source citations use file names that do not exist. |
|  | `Q-13` | no | minutes | Is the Stage 4 promotion comparand still byte-identical under HEAD? |
|  | `spec-7.13` | no | minutes | Add a gap row for §7.13. |
| no-action | `BL-cross-process-idempotence` | unverifiable | hours | §7.3 backlog: add cross-process idempotence for one CLI command including its JSON manifest. |
|  | `BL-employment-sum` | yes | hours | §7.3 backlog: compare the employment sum in assert_size_margin_compatible for years with no suppressed class; one test. |
|  | `BL-golden-oracle` | yes | hours | §7.3 backlog: regenerate the baseline and validation goldens only with a hand-derived oracle row beside the whole-frame equals. |
|  | `BL-named-errors` | yes | days | §7.3 backlog: route the eighteen bare ValueErrors through named errors; add one test that every raised error in src/ subclasses LoggingEmploymentErro… |
|  | `BL-prose-pins` | yes | hours | §7.3 backlog: replace the twelve prose-pin tests with behavioural ones where a behaviour exists; delete the date pins. |
|  | `BL-tooling` | yes | hours | §7.3 backlog: add pytest-cov and a type checker; declare ruff's select explicitly so the 415-rule set is reproducible. |
|  | `CAVEAT-ROADMAP-FIELDS` | yes | minutes | Minor caveat found while checking what reads the roadmap. |
|  | `EFFORT-RESCOPE` | yes | days | Rec 3 reads as a format change; it is a content triage. |
|  | `M1-block-measurements` | yes | minutes | Review §2.3/F-021: the three completed-stage blocks are single lines of 11,323 / 6,661 / 13,199 bytes with markers CORRECTED 8, SUPERSEDED 4, UPDATED… |
|  | `Q-06` | no | minutes | Was the omission of "robust", "regional" and "historical adjustment" from the rung-1 baseline a decision? Nothing records it. |
|  | `Q-18` | unverifiable | minutes | Is "reviewer approval" for golden regenerations (§17.6) recorded anywhere outside the single-author commit bodies? |
|  | `Q-19` | no | minutes | What is `runs/_baseline_pre_stage4c/`? Not a run-id directory, referenced by no code. |
|  | `Q5-MERGE-HAZARD` | yes | minutes | Single multi-KB lines make git merges dangerous; a 'keep both' merge already duplicated the Stage 4 block once. Does the proposed change fix that? |
|  | `gap-table-REQ-012` | yes | minutes | REQ-012's gap-table row ('Stage 5 (`posterior_summary` carries both)') needs re-ownership. |
|  | `scope-not-verified` | unverifiable | minutes | What this verification does NOT establish. |
|  | `spec-13.8-decline` | partly | minutes | Add a gap row for "the §13.8 decline paragraph"; F-023 lists it as owned by no stage. |
|  | `stage5-block-verbatim` | yes | minutes | Step 1 — report the current Stage 5 block's Consumes / Produces / Exit / RE-VALIDATED verbatim. |

### Totals

| Destination | Items |
|---|---|
| roadmap-new-stage | 4 |
| roadmap-stage-edit | 50 |
| roadmap-gap-table | 13 |
| roadmap-format | 11 |
| roadmap-completion | 4 |
| spec-amendment | 21 |
| deferred-item | 29 |
| fix-now-code | 12 |
| already-done | 3 |
| no-action | 17 |
| **total** | **164** |
