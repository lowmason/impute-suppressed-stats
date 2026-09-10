> For agentic workers: REQUIRED SKILL: writing-plans — this spec is the
> requirements input; it has no roadmap stage of its own and must not be
> folded into one.

# Stage 5 preconditions: make the system runnable and the record true

**Status:** NOT STARTED — requirements input for `writing-plans`.

**Source:** `docs/reviews/2026-09-09-system-review.md` §7.1 (R-01..R-11) and §7.5's first
bullet, routed here rather than to a roadmap stage by
`docs/reviews/2026-09-10-review-routing.md` §2.

**Closes (on completion):** `specs/deferred_items.md` `D-057` is either implemented or its
decline recorded; `D-071` gets a ruling (R-S5P-9); every open item gains a target and a `Size:`
line (R-S5P-8).

**Amends:** nothing in `specs/logging-employment-spec.md`. Every requirement here is code, tests
or the deferral register. The spec amendments the review also asks for (§12.2's anchor, Appendix
A's missing blocks, §13.10's metric list) are deliberately NOT here — see §6.

## 1. Why this exists

Stage 5 fits the state-total Bayesian model. It cannot start, and the reasons are not about
Bayesian modelling:

- **No inference library is installed.** `uv.lock` holds 38 packages and none of them is `jax`,
  `numpyro` or `pymc`.
- **A clean environment cannot run any command.** `python-dotenv` is a dev-only dependency and
  `config.py` imports it at module scope, so `uv sync --no-dev` produces a package whose CLI
  raises on import.
- **The suite is red on a clean clone.** Six test modules load the gitignored `data/staged` with
  no skip guard, so "is the suite green?" has depended on an untracked 564 MB directory.
- **Two fail-closed guarantees are latent**, and both first bite when the data or the stage
  changes rather than today.

The review's §7.5 calls this bundle "record-only" and sizes it at "a day of work". Both halves are
wrong and this spec does not inherit them. Five of the nine requirements below are code changes.
Measured from §7.1's own per-item efforts: one `minutes`, eight `hours`, two conditional. The
honest size is **days**.

The review's "R1, R5, R7, R9" in that sentence are risk-register ids from its §6, not
recommendation ids. This work REDUCES R1; it does not remove it — R1 also cites F-003, whose fix
(R-12, stratified metrics) the review itself files under Stage 5 at effort `days`.

## 2. What was measured

Every verdict below was re-derived at `f4393d3` on 2026-09-10, not copied from the review.

| Review item | State at `f4393d3` | Becomes |
|---|---|---|
| R-01 `python-dotenv` dev-only | OPEN — absent from `[project].dependencies` | R-S5P-1 |
| R-02 unguarded data tests | OPEN — 6 modules load `data/staged` with no `skipif` | R-S5P-2 |
| R-03 Stage 4 record | **DONE** — heading suffix, `Exit` and `D-085` shipped in PR #19 | — |
| R-04 name the anchor | **PARTLY DONE in code** — `Anchor.anchor_basis` exists (`reconcile/anchor.py:76`), is in `ANCHOR_BASES` (`contracts.py:241`) and reaches two frames. The remainder is spec text | see §6 |
| R-05 bounds on the baseline path | OPEN — nothing in `baselines/` loads bounds. The single `deterministic_bounds` hit in `runner.py` is inside a docstring about `cell_id` construction | R-S5P-3 |
| R-06 `fetch` fails closed | OPEN — 4 bare `continue` sites in `fetching.py` | R-S5P-4 |
| R-07 code identity in manifests | OPEN — no `code_commit` or `uv_lock_sha256` anywhere in `src/` | R-S5P-5 |
| R-08 Appendix A does not load | OPEN — exactly 11 validation errors (breakdown in R-S5P-6) | R-S5P-6 |
| R-09 what `rolling_origin` scores | OPEN — `D-071` unticked | R-S5P-9 |
| R-10 `§10.7` interval mislabelled | OPEN — `metrics.py:180` writes `rolling_residual_ensemble` for a leave-one-out **by position** | R-S5P-7 |
| R-11 re-triage the backlog | **PARTLY DONE** — all 86 items carry `D-nnn` ids (PR #19); 33 of 41 open items still lack a `Size:` line | R-S5P-8 |

## 3. Requirements

**R-S5P-1.** `python-dotenv` MUST move to `[project].dependencies`. `config.py` imports it at
module scope, so this is not an optional convenience — without it `uv sync --no-dev` yields a CLI
that cannot start. Verify with `uv sync --no-dev && uv run logging-estimates validate-config
--config config.yaml`, which MUST print its normal output rather than raise `ModuleNotFoundError`.

**R-S5P-2.** The suite MUST be green on a checkout with no `data/`. One guard belongs in
`tests/conftest.py` and MUST be applied in all six modules that load the staged layer. The guard
MUST key on a file's existence, not on an environment variable, so it cannot be switched off by
accident. Each `HarmonizedData.load(Path("data/staged"))` MUST also become an absolute path
derived from `__file__`: those calls are cwd-relative today, so the suite's result depends on
where pytest was invoked from. This makes the current de facto state explicit rather than changing
it — the tests are already not running for anyone without the gitignored directory, and a suite
that is red by construction trains reviewers to ignore a module.

**R-S5P-3.** Every baseline estimate MUST be checked against its per-cell bounds before it is
written, and a violation MUST raise a named error from the `LoggingEmploymentError` hierarchy.
This is INV-002's bounds half, unenforced since Stage 3. On D1 the change MUST be behaviour-neutral
and the test MUST assert that: all 1,227 suppressed state cells are `unbounded` with a null
`selected_upper`, so nothing can currently violate. The point is the first cell that CAN — a
retired anchor, a Stage 6 state x size cell, or a size-arm mask — at which point today's code
writes `anchored_and_reconciled` over an out-of-bounds number and says nothing. A unit test with
one finite upper MUST fail without the change.

**R-S5P-4.** `fetch` MUST NOT silently drop a quarter or year. A non-200 response or an empty body
MUST either fail the command with a named error, or be recorded as a declared, configured absence.
The four bare `continue` statements in `fetching.py` are the current behaviour: a transient
failure narrows the window, the run takes a new `run_id` because its inputs changed, and every
later stage proceeds on the shorter window with nothing in any manifest to say so. The known CBP
2024 absence MUST become an explicit declaration rather than an incidental pass — it is the one
case that must keep working, and it is exactly the case that currently hides the bug.

**R-S5P-5.** Every `*_manifest.json` under `runs/<id>/` MUST carry the code commit and the lock
hash. `run_id` MUST NOT change: it hashes config and inputs, and adding source identity to it
would re-id every run directory on every commit. The point is that staleness becomes DETECTABLE,
not that it becomes impossible — a run directory can currently be regenerated by different code
under the same id, with nothing recording which code produced it. `solve-bounds` MUST also write
the `bounds_manifest.json` it does not write today, with the sha256 of each output it produced.

**R-S5P-6.** Appendix A's configuration MUST load through `Config.model_validate`. It produces
exactly 11 errors, in three groups, and they do not have one cause:

- **7 x "Extra inputs are not permitted"** — `sources.{tpo,fia,ces,susb,bds,nonemployer,bea}`.
  `SourcesConfig` is `_Strict` and does not know the inactive sources the spec ships. This is the
  code half and it is this requirement's scope: `SourcesConfig` MUST accept them carrying
  `enabled: false`. That is the smaller change and it keeps the spec's picture of the system.
- **1 x "Extra inputs are not permitted"** — `model`. This is Stage 5's own block and MUST NOT be
  added here; adding it re-ids every run directory (see §4).
- **3 x "Field required"** — `baselines`, `disclosure.narrow_interval_absolute_width`,
  `disclosure.narrow_interval_relative_width`. These are missing from Appendix A, not extra in it,
  so they CANNOT be fixed in code without giving the fields defaults the spec never states. They
  are a spec amendment and are out of scope (§6).

So this requirement makes 8 of 11 go away, and MUST NOT claim to have fixed the other three. The
test `test_config.py::test_appendix_a_config_parses` MUST be changed to read the Appendix A fence
out of the spec file rather than parse a literal shaped by the code, and MUST be marked
`xfail` — or assert the exact remaining three errors — until the spec amendment lands.

**R-S5P-7.** `interval_source` MUST name what is computed. `metrics.py:180` writes
`rolling_residual_ensemble`, but the ensemble comes from `np.delete(residual_pool, position)` —
leave-one-out **by position within a replicate**, with no time ordering at all; the code's own
comment says "LEAVE-ONE-OUT BY POSITION". Relabelling is the scope here, NOT implementing a
time-ordered version. §13.10's coverage gate reads these intervals, so Stage 5 must know what it
is reading. Changing the value changes `INTERVAL_SOURCES` and a golden, both of which MUST be
regenerated with a hand-derived oracle row rather than from the code under test.

**R-S5P-8.** Every open item in `specs/deferred_items.md` MUST carry a target stage or a named
trigger, and a `Size:` line. 33 of 41 lack the latter today. Ids landed in PR #19; this is the
half that makes the register triageable rather than merely citable. Items whose originating stage
is complete and which name no target MUST get one or be closed with a reason — the review counts
22 such items, nine of them against Stages 1-3.

**R-S5P-9.** `D-071` MUST get a ruling, and this is a DECISION requirement: its output is a
written answer, not necessarily code. Either `rolling_origin` and `cbp_size_gaps` are given a
defined thing to score, or REQ-022 is declared not closed by Stage 4 and named in Stage 5's
`Consumes`. The roadmap currently says REQ-022 is closed while four of thirteen regimes score
nothing. `D-086` MUST be answered in the same pass: `retrospective_smoothing` and
`preliminary_to_final_vintage` are in the same position and are owned by nothing. Whichever way
it goes, it MUST be recorded before Stage 5's plan is written, because Stage 5's promotion gate
reads this scoreboard.

## 4. What this does NOT do

- **It does not add the `model:` config block.** That is Stage 5's first act and it re-ids every
  run directory, including the Stage 4 comparand `runs/f03023ac9f3a`. The decision between
  accepting a one-time re-id and versioning the config in `run_id` belongs to Stage 5's plan.
- **It does not implement a time-ordered rolling interval.** R-S5P-7 relabels; building the real
  thing is a design question §13.10 depends on and is not scoped here.
- **It does not enforce §13.2 step 6 or §13.5.** Those are `D-085`, owned by Stage 6, where a
  size-class estimator makes them able to fire at all.
- **It does not add the §13.5-13.8 metric families** the §13.10 gate needs. That is R-12, filed
  under Stage 5.

## 5. Verification

- `uv sync --no-dev && uv run logging-estimates validate-config --config config.yaml` succeeds.
- `mv data data.bak && uv run pytest -q` reports 0 failed; restore afterwards.
- A unit test giving one cell a finite `selected_upper` and an estimate above it fails without
  R-S5P-3 and passes with it.
- A `MockTransport` returning 500 for one quarter makes `fetch --source qcew` exit non-zero and
  write no manifest row; the CBP 2024 case passes only when declared.
- Every `*_manifest.json` in a fresh run carries `code_commit` and `uv_lock_sha256`;
  `bounds_manifest.json` exists and carries three output hashes.
- The Appendix A fence, read from the spec file, produces exactly 3 validation errors, all
  `Field required`.
- `grep -rn "rolling_residual_ensemble" src/` returns nothing.
- Every open item in `specs/deferred_items.md` matches both a target/trigger and a `Size:` line.
- `D-071` and `D-086` are ticked or carry a recorded ruling.
- The full suite passes with no new skips beyond the data guard of R-S5P-2.

## 6. Out of scope: the spec amendments

The review's §7.4 item 1 asks for amendments to `specs/logging-employment-spec.md` that this spec
deliberately does not make, because they change the normative contract and deserve their own
review pass rather than a ride-along:

- **§12.2 and §15.2 — name the anchor** (R-04's remainder). The normative text still requires a
  "compatible national total" that SRC-QCEW-006 declined, and never names the establishment-closure
  anchor that replaced it. The code half is largely done; the text is not.
- **Appendix A's three missing blocks** (R-S5P-6's remainder).
- **Appendix B** — unsatisfiable as written; recorded as a Stage 8 precondition in the roadmap.
- **§13.10 and §11.1** — the promotion gate's comparand can be `None`, and the first decision
  should be declared provisional. The roadmap now routes the re-gate to Stage 7.

## 7. The strongest candidate for the next spec

Not a requirement here; recorded so it is not lost. The review's **R-16** asks whether any §9.3
margin exists on D1: fetch state rows for `113`, `1133`, `11331` and total-ownership (`own_code 0`)
`113310`, and count how often each is disclosed where `113310` is `N`. It is hours of work and it
is the only open item that could change the product from 1,227 model-only estimates to some cells
identified from public accounting facts.

It carries a disclosure consequence that is easy to miss: with `1133 -> 11331 -> 113310`
single-child on D1, a disclosed parent cell is an EXACT RECONSTRUCTION of the suppressed value, not
merely a bound — a live REQ-027 case, not a modelling improvement.
