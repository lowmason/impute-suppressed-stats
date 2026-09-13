# Stage 5 Parent Margin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: COMPLETE (2026-09-13)** — executed via executing-plans; deferred items in specs/deferred_items.md

> Deviation (whole plan): every code block was checked out from `verify/plan-15-v2`, the branch the
> provenance note above describes, after its red step had been observed; each task commit's diff
> against that branch was the run-id pin alone, apart from Task 7 Step 7's rewrite. Blocks this plan
> never executed ran first here, with `data/` present, so their deviations are recorded below.
>
> Final review (code-reviewer, Opus): with fixes, all landed after Task 10 — `f4ed4d0` (§12.3's
> bisection shared its stopping rule with `reconcile`'s gate), `78ae889` (a named CBP refusal),
> `a9659b6` (§13.5 before step 6, and the D-087 wiring pinned against a leak), `0e473e9` (notes the
> branch had falsified without editing), and `f413a1e` (R-PM-7 re-measured on the final code).
> Deferred items for this plan: `D-115`..`D-119`.

**Goal:** Turn the disclosed private `113` parent into a hard §9.3 upper bound on the suppressed `113310` state cells it covers, make every consumer of `deterministic_bounds` honour that bound instead of halting on it, decide the parent's visibility under §13.2's synthetic mask, and re-run the Stage 5 comparand against the bounded identification set.

**Architecture:** A fifth harmonized table, `qcew_state_parent`, carries the private `113` state series, fetched through `ingest/qcew.py`'s slice route under a new `qcew_parent` source and parsed by the existing QCEW parser at the level `113` is served at. `constraints/` adds a `state_parent` cell kind and one `child - parent <= 0` row per published parent over a suppressed child. `baselines/runner.py` reallocates by §12.3 bounded proportional scaling when §12.2's allocation leaves a finite interval, and `validate/` hides a parent exactly where it has no other establishments, enforces §13.5's out-of-bounds rule, rejects exactly recoverable targets and hands the masked bounds to the baselines (`D-087`).

**Tech Stack:** Python >= 3.14, uv + hatchling, polars, pydantic v2, typer, httpx, highspy (HiGHS), pytest, ruff, interrogate.

**Requirements input:** `specs/stage5-parent-margin.md` (R-PM-1..8 and §4's done-when 1-6), selected as `D-111` under `/deferred` on 2026-09-12. That spec names this skill in its header and has no roadmap stage of its own. The branch this plan executes on, `feat/stage5-parent-margin`, is **stacked on `fix/deferred-quick-fixes-2026-09-12`**: Tasks 2 and 3 edit code that branch changed (`D-100`'s `source_publication_date`, `D-097`'s CBP metadata rows, `D-098`'s stamp comment) and Task 5 extends its `configured_highs` (`D-099`). If that branch merges first, rebase onto `main` before Task 1.

**Provenance of the code in this plan.** Every code block in Tasks 1-8 was executed before this plan was committed, in plan order, in an isolated git worktree branched from `9b18a85`. Each red step was run and its failures read against the Expected text, the implementation applied, each green step and gate run (`ruff format src tests`, `ruff check src tests`, `interrogate src`), then the whole suite, then a commit. Blocks were sliced out of this file by script rather than retyped, so what ran is what is written, and the quoted outputs are transcribed from those runs. Tasks 1 and 2 were re-run from their red steps after their tests changed; Task 3's tests did not change, so its red step stands from the first pass. Three earlier passes ran Tasks 1-3, 5-6 and 7-8 separately against the first draft of this plan, and with the in-order pass they found defects in every one of Tasks 1-8, each fixed here. Existing tests in four files the plan never touched break under Tasks 2, 4 and 6, so those gates would have halted: `test_registry.py`, `test_constraint_cli.py`, two table sets and a table count in `test_build_harmonized.py`, and `test_baseline_cli.py`. The count was found only by the in-order pass, after three passes and a search for the table names had missed it. Task 8's red command could not produce its own Expected. Two were code defects no test caught: an unserved sibling read as zero on every quarter, and an integer bound check stricter than the integer cut it checks. Each now has a test that fails without its fix, and the in-order pass checked that removing the tolerance fix, the constraint-CLI table name or `mask_and_solve`'s §13.5 call each reddens a test. The rest were false or unwitnessed prose, ambiguous anchors, and blocks `ruff format` rewrote. This repo has a documented history of plan code blocks that parse but do not run.

**Suite counts are stated as deltas, and every task's delta was measured.** The pre-plan baseline at `9b18a85` is `1476 passed` with `data/` and `1406 passed, 70 skipped` without it, and `1406 + 70 = 1476`. Every test this plan adds runs without `data/`, so the deltas are the same either way. Measured in plan order without `data/`, the passed count after each of Tasks 1-8 is `1416`, `1421`, `1428`, `1434`, `1436`, `1439`, `1449` and `1459`, with `70 skipped` throughout. **The delta is the check; a mismatch there means halt.**

**What was NOT executed, and why:**

- **Task 1 Steps 11-14 and Task 2 Step 7:** live requests to `data.bls.gov`, 192 and 38. Task 1's `main()` was run offline instead, with a mocked transport and a temporary audit root, including a variant where `1132` is never served; that variant is how Step 4's fix was found, and Step 13's block ran against its synthetic summary. Task 1 Step 1 did run, in the main checkout: the renderer reproduced the committed finding exactly. Task 2 Step 7's claim that every stored quarter carries a `Last-Modified` stamp is unverified.
- **Task 4 Steps 8-10, the data half:** rebuilding `data/staged/` from the real store, deriving the new run id and moving the pin. The expected `parent rows 4764 months 96` is 1,588 private state-quarters times three, and `756` is the committed finding's count; these commands have never printed either.
- **Every `requires_staged` test from Task 4 on,** including Task 7 Step 7's four rewritten D1 tests. They were collected, linted and skipped. That they pass is first observed at execution, and so is the claim that the rank-cache test needs no change.
- **The regeneration script in `tests/fixtures/national_size_margin/README.md`,** which Task 4 Step 1 extends: it reads `data/staged/`.
- **Task 9, entirely:** it re-runs the pipeline over the rebuilt layer. Its two scripts ran read-only against `runs/f03023ac9f3a` while this plan was written, which exercises their code and none of their expected values.
- **Task 10's apply:** its check mode matched all 22 edits and the roadmap span in the verification worktree after Task 8. A matched edit is not an applied one.

---

## Decisions this plan makes

The spec leaves these open or did not anticipate them. Each is stated with the evidence that decides it, so a reviewer can reject the decision rather than rediscover it. Every number below was measured on 2026-09-12 against the stored audit extracts (`data/raw/audit/qcew_parent_margins/`, digest `e620bb5e…`), `data/staged/` and `runs/f03023ac9f3a/`.

1. **The parent is a table of its own, not extra rows in `qcew_monthly`.** Parsed at agglvl 55 its rows get `area_type = "other"`, which keeps them out of every `area_type`-keyed consumer, but two consumers select a cell by `(state_fips, reference_month)` alone and a parent row shares both keys with its child: `validate/mask.apply_mask` would match two rows per target and refuse the mask, and `validate/leakage.assert_no_retained_truth` reads `cell.row(0)` from an ambiguous match. A fifth table isolates the series by construction, re-ids the run exactly as extra rows would, and costs one `HarmonizedData` field with an empty default (so the 20 direct constructors in `tests/` stay untouched) plus one empty parquet in each of three fixture directories.
2. **A parent cell exists only where the parent is published and its child is suppressed, and the row is `child - parent <= 0` with the parent pinned by its own `fix|` row.** A margin over a published child restricts nothing, and `size_margin_rows` sets the precedent of never lifting a published number into a right-hand side. Expected on D1: 756 two-cell components, 756 bounded state cells and 471 still `unbounded` — Task 7's D1 tests derive both counts from the staged tables rather than typing them.
3. **Production reallocates into a finite bound instead of halting on it, and that lands here.** `cli.py::run_baselines_command` passes `deterministic_bounds`, and `runner.assert_within_bounds` raises `BoundViolationError`. Against the parent values, **2,184 of the 6,702 estimates `runs/f03023ac9f3a` shipped on parent-bounded cells sit above the parent, in 850 of 852 estimator-months, for all nine estimators** (median estimate-to-parent ratio 1.10 to 3.50 among them). So the moment `solve-bounds` writes a finite `selected_upper`, `run-baselines` would halt on its first month. Task 6 applies §12.3's bounded proportional scaling, the method `reconciliation.single_margin_method` already names, only where §12.2's allocation leaves an interval, so every other month stays bit-identical. §12.3's infeasibility arm cannot fire on D1: no month has every missing cell parent-bounded (at most 7 of 9), so every month's summed upper is infinite.
4. **The parent's visibility under the mask is a deterministic rule on public establishment counts, not a propensity.** Hide the parent exactly when `parent qtrly_establishments - child qtrly_establishments <= 0`. On D1's 409 real suppressions BLS hid the parent on **123 of 123** such quarters, and on all **336** published month-values with no sibling establishments the parent employment **equals** the child. So this is precisely where a visible parent would recover the target exactly (§13.2 step 6), and the rule coincides with BLS's own complementary suppression. Everywhere else the rule leaves the parent visible, and BLS hid it on **34 of 286** (21 of 95 with one sibling establishment, 13 of 191 with two or more). The rule never hides a parent BLS published; its error is optimism, on 34 of 409 (8.3%). On the synthetic path the one-sibling stratum cannot reach a visible parent, because a published child with one sibling establishment never has a published parent (0 of 49), so the optimism is confined to the two-or-more stratum. On `runs/f03023ac9f3a`'s 5,932 scored estimate rows the rule leaves 4,520 parents visible and hides 631; 781 are hidden in reality.
5. **§13.2 step 6 REJECTS an exactly recoverable target from scoring and counts it; §13.5's out-of-bounds rule HALTS.** `bound_status` already rides on scored rows, but no emitter reads it to change a number (`D-085`). Expected rejections on D1: zero, since no published parent equals its child where other establishments exist (0 of 2,742 month-values).
6. **`D-087` is ruled: the harness passes `state_total_bounds(MaskedSystem.bounds)` to `run_baselines`.** With Decision 3 the runner scales into those bounds exactly as production does, so an out-of-interval estimate cannot reach a scored row. A residual that cannot fit raises `InfeasibleResidualError`; that is unreachable on D1 by Decision 3's measurement, and on the masked path every withheld truth sits inside its interval or §13.5 halts first. A value that still escapes after scaling is a defect and raises `BoundViolationError`. Leaving the harness bound-blind would rank estimates production never releases.
7. **`D-093` is answered with `mip_rel_gap = 0`, set in `configured_highs` for every solver.** §9.1's bounds are exact optima. The first models to reach MILP on D1 are the parent components under width 25 (107 month-values in 43 quarters), where a one-employee miss is a relative gap of at least 1/25, so the default 1e-4 could not bind on them. The option is set for the engine rather than for that case: a concrete four-column model at employment magnitudes, found by a seeded search while this plan was written, stops at 30,528 under the default and reports `kOptimal`, against a true minimum of 30,526, and Task 5 pins it. Task 9 records `milp_*` against `lp_*` on the D1 cells.
8. **R-PM-5 is measured by the same script and ladder before R-PM-4 is ruled (Task 1).** A pre-plan probe of the 32 `1131` and 32 `1132` slices found **0** exact reconstructions on the 252 bounded quarters, and **0** again when a missing sibling row is read as zero establishments. One sibling is published on 17 of them, which tightens the bound to `113 - sibling` without closing it. Task 1 re-derives all three through the committed script and renderer, and the ruling is made on that output, not on the probe.
9. **R-PM-7: the comparand is re-run, and WAPE, coverage and the scoreboard DO move.** `run_id` hashes `data/staged/*.parquet`, so Task 4's fifth table re-ids every run regardless. The spec expected only §13.5's metrics and the `selected_*` columns to move, because "baselines never read masked bounds". Decisions 3 and 6 make both paths read bounds, so estimates change on every month a bound binds. Task 9 measures what moved by join and records it.
10. **Scope riders.** `D-114` (CBP's vintage stamp) rides this rebuild, as its own text asks. `D-094` (harmonized `snapshot_id` is a filename stem) does not: its trigger fired with `D-100`, but it is a plan-sized identity change across three tables and the §7.2 join, so the next rebuild re-ids once more, which is accepted. The establishment-count "parent share" predictor that R-PM-1 says this ingest *unblocks* is not added: it would change `target_propensity`, re-draw every regime's mask and confound Task 9's comparison, so it is filed at completion. Committed fixture goldens get an EMPTY parent table, so no golden moves (§17.6); the parent path is exercised by unit tests and by the D1 acceptance tests.

## Global Constraints

- `requires-python = ">=3.14"`; author `Lowell Mason <mason.lowell@mac.com>`; MIT (Rollout D4).
- **`run_id` changes exactly once, in Task 4, and deliberately.** A fifth staged table and `D-114`'s rewrite of `cbp_state_size.parquet` both feed `runs.run_id`. **No task adds a pydantic field to `Config` or edits `config.yaml`**, so `tests/unit/test_config.py`'s config-only canary (`39d1d0859838`) stays green throughout. Task 4 moves the acceptance pin in `tests/integration/test_stage4_acceptance.py`, and no later task moves it again. `runs/f03023ac9f3a` is never overwritten: new inputs land in a new run directory.
- **Execute in the main checkout.** `data/` (~564 MB) is gitignored; Tasks 1, 2, 4 and 9 read or write it, and data-bound tests skip silently in a worktree.
- **Network steps: Task 1 Step 11 (192 requests) and Task 2 Step 7 (38 requests), both to `data.bls.gov`.** Both read `BLS_CONTACT_EMAIL` from `./.env` through code. Never type an address or a key into a command, a commit or an artifact. `CENSUS_API_KEY` is not needed by this plan.
- **Never run `scripts/audit/cbp_metadata.py`** (destructive-first). **Re-running `scripts/audit/qcew_parent_margins.py` overwrites its extracts in place**; Task 1 Step 1 verifies them against the committed finding and copies them aside first.
- **Format and lint scope is `src tests`, never `.`**: `uv run ruff format src tests`, `uv run ruff check src tests`. Task 1 formats its two `scripts/audit/` files by name.
- **`uv run interrogate src` is `fail-under = 100`.** Every new callable carries a docstring saying why this and not the obvious alternative; each is written out in its code block.
- **Fail closed with a named error.** Task 8 adds `ConstraintDataError`; everything else raises an existing `errors.py` class.
- **Suite arithmetic is the check, stated as deltas.** The pre-plan baseline at `9b18a85`, with `data/`, is `1476 passed`. Each gate names the tests added and rewritten: `passed` rises by exactly the added count, `skipped` does not move, and a rewritten test passes.
- **Schemas are ordered literals, and this plan adds no column.** The parent table reuses `QCEW_MONTHLY_SCHEMA` unchanged.
- **Roadmap stage blocks are single ~7 KB lines** and a known merge hazard; Task 10 edits one and verifies by `grep -c`, never by eye.
- **Commit per task on `feat/stage5-parent-margin`; never push.** Cite deferred items by `D-nnn`. This plan closes `D-111`, `D-093`, `D-110` and `D-114`, and rules `D-087`. It discharges `D-085`'s state-total arm and rewrites the `1,227` sites `D-111` falsifies; `D-056` stays open for the rest.

## File Structure

| File | Task | Responsibility |
|---|---|---|
| `scripts/audit/qcew_parent_margins.py` | 1 | R-PM-5: fetches `1131`/`1132`, adds the sibling rung to `identification`, counts `sibling_exact` |
| `scripts/audit/render_parent_margins.py` | 1 | guards and renders the sibling section of the finding |
| `tests/audit/test_qcew_parent_margins.py`, `tests/audit/test_render_parent_margins.py` | 1 | the ladder, `sibling_exact`, the new premises |
| `specs/findings/qcew-parent-margins.md` | 1 | regenerated by the renderer, never by hand |
| `src/logging_employment/constants.py` | 2 | `QCEW_PARENT_INDUSTRY`, `QCEW_PARENT_STATE_AGGLVL`, as measured facts |
| `src/logging_employment/registry/sources.yaml` | 2 | the `qcew_parent` row |
| `src/logging_employment/fetching.py` | 2, 3 | `qcew_parent` on the shared slice route; CBP rows stamped from the predicate |
| `src/logging_employment/cli.py` | 2 | `fetch --source qcew_parent` |
| `tests/unit/test_fetching.py` | 2, 3 | the new source, registry coverage, the CBP stamp |
| `tests/unit/test_registry.py` | 2 | the seed registry's exact source set |
| `src/logging_employment/ingest/cbp.py` | 3 | `vintage_for_predicate` |
| `src/logging_employment/build.py` | 3, 4 | the CBP stamp; `state_parent_rows` and the fifth table |
| `tests/unit/test_cbp.py`, `tests/integration/test_build_harmonized.py` | 3, 4 | the stamp, the parent table, its refusals |
| `src/logging_employment/ingest/qcew.py` | 4 | `parse_qcew_monthly(..., state_agglvl=)` |
| `src/logging_employment/contracts.py` | 4 | `_HARMONIZED_TABLES`, `HarmonizedData.qcew_state_parent` |
| `tests/unit/test_qcew_parser.py`, `tests/unit/test_contracts.py` | 4 | the parser level, the five-table load |
| `tests/fixtures/qcew/slice_113_2017q1.csv`, `tests/fixtures/qcew/README.md` | 4 | a state-and-national cut of the real 2017q1 `113` slice |
| `tests/fixtures/{baselines,constraints,national_size_margin}/qcew_state_parent.parquet` | 4 | empty parent tables, so no golden moves |
| `tests/fixtures/national_size_margin/README.md`, `tests/integration/{test_constraint_cli,test_national_size_margin_golden,test_baseline_golden}.py` | 4 | every hand-written list of the staged tables |
| `tests/integration/conftest.py`, `tests/integration/test_stage4_acceptance.py` | 4, 8 | the staged-table list; the moved pin; the `D-087` wiring test |
| `src/logging_employment/constraints/bounds.py` | 5 | `mip_rel_gap = 0` |
| `src/logging_employment/baselines/runner.py` | 6, 8 | §12.3 scaling where §12.2 leaves an interval; integer bounds; the harness as a second caller |
| `tests/integration/test_baseline_cli.py` | 6 | the production path scales an estimate rather than halting |
| `tests/unit/test_baselines_bounds.py`, `tests/unit/test_constraint_bounds.py` | 5, 6, 7 | the gap, the scaling, the parent bound end to end |
| `src/logging_employment/constraints/{cells,rows,compat,system}.py` | 7 | `state_parent` cells, `parent_margin_rows`, `assert_parent_margin_compatible` |
| `tests/unit/test_constraint_builders.py`, `tests/unit/test_constraint_compat.py` | 7 | the builder and the gate |
| `tests/integration/test_d1_acceptance.py`, `tests/unit/test_validate_recover.py`, `tests/unit/test_validate_complementary.py` | 7 | the four D1 assertions `D-111` falsifies, rewritten as derived invariants |
| `src/logging_employment/validate/{mask,leakage,recover,harness}.py`, `src/logging_employment/errors.py` | 8 | the parent rule, its leakage guard, §13.5, step 6, `D-087` |
| `tests/unit/test_validate_parent_mask.py` | 8 | the rule, the guard, both §13 checks, the rejection |
| `specs/findings/stage-5-log.md` | 1, 9 | R-PM-4's ruling; R-PM-7's measured comparison |
| the documents listed in Task 10 | 10 | every note that treats `D-111` as pending |

---

### Task 1: Measure the sibling path with the same script and ladder, then rule R-PM-4

**Implements:** R-PM-5; R-PM-4's ruling; §4 done-when 4.

R-PM-5 requires "the same script and the same ladder", so the two committed audit files grow rather than a new probe appearing beside them. This task runs first because it is the only one whose *result* could change the rest: if the sibling path reconstructed a suppressed quarter exactly, R-PM-4 would bind and Tasks 7-8 would need an exactness path this plan does not contain.

**Files:**
- Modify: `scripts/audit/qcew_parent_margins.py` (`INDUSTRIES`, `identification`, new `SIBLINGS` / `Key` / `present_keys` / `sibling_exact`, `main`)
- Modify: `scripts/audit/render_parent_margins.py` (`summary_premises`, `render`)
- Test: `tests/audit/test_qcew_parent_margins.py`, `tests/audit/test_render_parent_margins.py`
- Regenerate: `specs/findings/qcew-parent-margins.md` (by the renderer only)
- Modify: `specs/findings/stage-5-log.md`

**Interfaces:**
- Consumes: nothing from this plan.
- Produces: `summary.json` gains `findings.siblings = {"industries": {"1131": {...}, "1132": {...}}, "exact_where_child_suppressed": int, "exact_where_child_suppressed_if_absent_is_zero": int, "a_sibling_published_where_113_bounds": int}`; `qcew_parent_margins.sibling_exact(parent: set[Key], siblings: Mapping[str, set[Key]], present: Mapping[str, set[Key]], *, absent_is_zero: bool) -> set[Key]`, with `Key = tuple[str, str, str]`.

- [x] **Step 1: Prove the stored extracts still produce the committed finding, then copy them aside**

The renderer re-hashes every extract against the summary before it writes, so an unchanged finding is the digest check.

```bash
(cd scripts/audit && uv run --no-project render_parent_margins.py)
git diff --exit-code specs/findings/qcew-parent-margins.md
cp -Rp data/raw/audit/qcew_parent_margins /tmp/qcew_parent_margins.before-rpm5
```

Expected: `wrote …/specs/findings/qcew-parent-margins.md`, then `git diff` exits 0. **If it does not, stop:** the extracts no longer match digest `e620bb5ead34003d5f4324dc8fe16a7fa3738c62124c4de5b0bf56baf282477b`, and every number in this plan needs re-measuring before any task runs.

- [x] **Step 2: Write the failing ladder and `sibling_exact` tests**

In `tests/audit/test_qcew_parent_margins.py`, replace `NOTHING` and the first test with:

```python
NOTHING = {
    "parent_113_disclosed": False,
    "parent_1133_disclosed": False,
    "parent_11331_disclosed": False,
    "sibling_1131_disclosed": False,
    "sibling_1132_disclosed": False,
    "ownership_total_disclosed": False,
    "ownership_siblings_disclosed": False,
}


def test_no_disclosed_margin_is_the_status_quo():
    """Nothing published identifies nothing: the ladder's floor is NONE."""
    assert m.identification(NOTHING) == m.NONE
```

Then add, directly after `test_exact_outranks_a_bound_when_both_are_available`:

```python
def test_a_disclosed_113_with_both_siblings_disclosed_is_exact():
    """R-PM-5: `113 - 1131 - 1132 = 1133`, and `1133 -> 11331 -> 113310` is single-child."""
    row = {
        **NOTHING,
        "parent_113_disclosed": True,
        "sibling_1131_disclosed": True,
        "sibling_1132_disclosed": True,
    }
    assert m.identification(row) == m.EXACT


@pytest.mark.parametrize("sibling", ["sibling_1131_disclosed", "sibling_1132_disclosed"])
def test_one_disclosed_sibling_under_a_disclosed_113_still_only_bounds(sibling):
    """The other sibling stays unknown and nonnegative: a tighter bound, never an exact value."""
    assert (
        m.identification({**NOTHING, "parent_113_disclosed": True, sibling: True}) == m.UPPER_BOUND
    )


def test_disclosed_siblings_without_their_parent_identify_nothing():
    row = {**NOTHING, "sibling_1131_disclosed": True, "sibling_1132_disclosed": True}
    assert m.identification(row) == m.NONE


ALABAMA = ("01000", "2019", "1")
OREGON = ("41000", "2019", "1")
WASHINGTON = ("53000", "2019", "1")


def test_sibling_exact_needs_the_parent_and_both_siblings_published():
    exact = m.sibling_exact(
        {ALABAMA, OREGON},
        {"1131": {ALABAMA, OREGON}, "1132": {ALABAMA}},
        {"1131": {ALABAMA, OREGON}, "1132": {ALABAMA, OREGON}},
        absent_is_zero=False,
    )
    assert exact == {ALABAMA}


def test_an_absent_sibling_row_counts_as_zero_only_under_the_sensitivity_reading():
    """No row at all means no establishments; a row coded `N` is a suppression, never a zero."""
    parent = {OREGON, WASHINGTON}
    siblings = {"1131": {OREGON, WASHINGTON}, "1132": set()}
    present = {"1131": {OREGON, WASHINGTON}, "1132": {OREGON}}
    assert m.sibling_exact(parent, siblings, present, absent_is_zero=False) == set()
    assert m.sibling_exact(parent, siblings, present, absent_is_zero=True) == {WASHINGTON}


def test_a_sibling_the_route_never_served_is_never_read_as_zero():
    """An unserved sibling has no `present` entry: no row to be absent from, so never a zero."""
    parent = {OREGON}
    siblings = {"1131": {OREGON}, "1132": set()}
    present = {"1131": {OREGON}}
    assert m.sibling_exact(parent, siblings, present, absent_is_zero=True) == set()
```

- [x] **Step 3: Run them and watch the three that encode new behaviour fail**

Run: `uv run pytest tests/audit/test_qcew_parent_margins.py -q`
Expected: `4 failed` — the exact test (`assert 'upper_bound' == 'exact'`) and the three `sibling_exact` tests (`AttributeError: module 'qcew_parent_margins' has no attribute 'sibling_exact'`). The one-sibling and no-parent tests pass already: the current ladder ignores keys it does not read, and those two pin behaviour the change must keep.

- [x] **Step 4: Implement the sibling rung and the counts**

In `scripts/audit/qcew_parent_margins.py`, change the module docstring's last line to `113310 state cell on D1 (R-S5G-5), and whether 113 - 1131 - 1132 reconstructs one (R-PM-5)."""`. Replace `identification` with:

```python
def identification(row: Mapping[str, bool]) -> str:
    """Which §9.3 margin, if any, identifies one suppressed private 113310 state-quarter.

    The ladder is EXACT before UPPER_BOUND before NONE, because the three have different
    consequences and the strongest one wins. An exact margin is a live `REQ-027` / §14.4 case: the
    `1133 -> 11331 -> 113310` chain is single-child in both the 2017 and 2022 vintages (D6,
    measured against the official structure files), so a disclosed private parent at either level
    is the suppressed value itself and not a bound on it.

    `113` ALONE is deliberately not in the exact branch. Forestry and Logging aggregates `1131`,
    `1132` and `1133`, so a disclosed `113` plus nonnegativity of the two siblings gives
    `113310 <= 113`. That is §9.3's parent-total constraint doing real work, but it is a bound, and
    recording it as exact would put a modelled cell into the release path §14.4 guards. `113` WITH
    BOTH SIBLINGS published is exact (R-PM-5): `113 - 1131 - 1132 = 1133`, which the chain above
    makes the suppressed value. One sibling leaves the other unknown, which tightens the bound
    without closing it.

    Ownership splits the same way. `own_code 0` is Total Covered over the ownerships present, which
    Stage 0 measured as `3` (Local Government) and `5` (Private) for this industry. With the
    sibling disclosed, private is total minus sibling and therefore exact; with it suppressed, the
    sibling is only known to be nonnegative and the total is an upper bound.
    """
    if row["parent_1133_disclosed"] or row["parent_11331_disclosed"]:
        return EXACT
    if (
        row["parent_113_disclosed"]
        and row["sibling_1131_disclosed"]
        and row["sibling_1132_disclosed"]
    ):
        return EXACT
    if row["ownership_total_disclosed"] and row["ownership_siblings_disclosed"]:
        return EXACT
    if row["parent_113_disclosed"] or row["ownership_total_disclosed"]:
        return UPPER_BOUND
    return NONE
```

Replace `INDUSTRIES = ("113310", "113", "1133", "11331")` with:

```python
INDUSTRIES = ("113310", "113", "1133", "11331", "1131", "1132")
# R-PM-5's two siblings: `113 - 1131 - 1132 = 1133`. Walked and judged exactly like the parents, so
# a sibling the route does not serve is a measured absence (`fetched: false`), never a silent zero.
SIBLINGS = ("1131", "1132")
Key = tuple[str, str, str]
```

Add directly after `disclosed_keys`:

```python
def present_keys(rows: pl.DataFrame, own_code: str) -> set[Key]:
    """`(area_fips, year, qtr)` for every row at one ownership, whatever its disclosure code.

    The complement `sibling_exact` needs: a key missing from this set is a state-quarter the slice
    publishes NO row for, which is a different fact from a row coded `N`.
    """
    at_ownership = rows.filter(pl.col("own_code") == own_code).select("area_fips", "year", "qtr")
    return set(zip(*at_ownership.to_dict().values(), strict=True))


def sibling_exact(
    parent: set[Key],
    siblings: Mapping[str, set[Key]],
    present: Mapping[str, set[Key]],
    *,
    absent_is_zero: bool,
) -> set[Key]:
    """The quarters where `113 - 1131 - 1132` publishes `113310` exactly (R-PM-5).

    `parent` holds the keys where `113` is published, `siblings[i]` those where sibling `i` is, and
    `present[i]` those where sibling `i` has a row at all. Under the ladder's own reading a sibling
    is known only when it is PUBLISHED. `absent_is_zero` adds the sensitivity reading: a
    state-quarter with no sibling row has no sibling establishments and so no sibling employment.
    It is reported beside the strict count and never folded into `identification`, because a
    missing row is an inference and a published zero is a fact, and R-PM-4's ruling must not turn
    on which of the two a reader prefers.

    `present` carries only the siblings the route served. A sibling it never served has no row to
    be absent from, so neither reading makes it known: an unfetched `1132` would otherwise read as
    zero on every quarter and turn the sensitivity count into the whole bounded set.
    """
    exact = set(parent)
    for industry, published in siblings.items():
        known = set(published)
        if absent_is_zero and industry in present:
            known |= {key for key in parent if key not in present[industry]}
        exact &= known
    return exact
```

In `main`, change the docstring to `"""Fetch the six industries across D1 and count who identifies whom."""`, then insert this block immediately before the line `    total_own = disclosed_keys(child, TOTAL_COVERED)`:

```python
    # R-PM-5. Only a quarter a published `113` already bounds can be made exact by its siblings, so
    # every sibling count is taken over those quarters.
    bounded = disclosed["113"] & suppressed
    siblings: dict[str, dict[str, object]] = {}
    sibling_published: dict[str, set[Key]] = {}
    sibling_present: dict[str, set[Key]] = {}
    for industry in SIBLINGS:
        if industry not in stacked:
            siblings[industry] = {"fetched": False, "outcomes": outcomes[industry]}
            sibling_published[industry] = set()
            continue
        rows = state_rows(stacked[industry], industry)
        sibling_published[industry] = disclosed_keys(rows, PRIVATE)
        sibling_present[industry] = present_keys(rows, PRIVATE)
        siblings[industry] = {
            "fetched": True,
            "agglvl_codes_present": sorted(set(rows["agglvl_code"].to_list())),
            "state_quarter_rows_private": rows.filter(pl.col("own_code") == PRIVATE).height,
            "disclosed_private": len(sibling_published[industry]),
            "disclosed_where_113_bounds": len(sibling_published[industry] & bounded),
        }

```

In the tally's row dict, add after the `"parent_11331_disclosed": key in disclosed["11331"],` line:

```python
                    "sibling_1131_disclosed": key in sibling_published["1131"],
                    "sibling_1132_disclosed": key in sibling_published["1132"],
```

In `c.write_summary(... findings={...})`, add after the `"parents": parents,` line:

```python
            "siblings": {
                "industries": siblings,
                "exact_where_child_suppressed": len(
                    sibling_exact(bounded, sibling_published, sibling_present, absent_is_zero=False)
                ),
                "exact_where_child_suppressed_if_absent_is_zero": len(
                    sibling_exact(bounded, sibling_published, sibling_present, absent_is_zero=True)
                ),
                "a_sibling_published_where_113_bounds": len(
                    (sibling_published["1131"] | sibling_published["1132"]) & bounded
                ),
            },
```

- [x] **Step 5: Run the ladder tests green**

Run: `uv run pytest tests/audit/test_qcew_parent_margins.py -q`
Expected: all pass, 7 more than before Step 2.

- [x] **Step 6: Write the failing renderer-premise tests**

In `tests/audit/test_render_parent_margins.py`, replace `CLEAN`'s `"slice_outcomes"` entry and add a `"siblings"` entry after `"parents"`:

```python
    "slice_outcomes": {
        i: {"ok": 32, "not_found": 0, "unparseable": 0}
        for i in ("113310", "113", "1133", "11331", "1131", "1132")
    },
```

```python
    "siblings": {
        "industries": {
            "1131": {"fetched": True, "agglvl_codes_present": ["56"]},
            "1132": {"fetched": True, "agglvl_codes_present": ["56"]},
        },
        "exact_where_child_suppressed": 0,
        "exact_where_child_suppressed_if_absent_is_zero": 0,
        "a_sibling_published_where_113_bounds": 17,
    },
```

Append three cases to `test_each_broken_summary_premise_halts_by_naming_its_sentence`'s parametrize list:

```python
        (lambda f: f["siblings"]["industries"]["1131"].update(fetched=False), "1131 was fetched"),
        (
            lambda f: f["siblings"].update(exact_where_child_suppressed=2),
            "reconstructs no suppressed quarter",
        ),
        (
            lambda f: f["siblings"].update(exact_where_child_suppressed_if_absent_is_zero=1),
            "absent sibling",
        ),
```

- [x] **Step 7: Run them and watch the three new cases fail**

Run: `uv run pytest tests/audit/test_render_parent_margins.py -q`
Expected: `3 failed`, each an `AssertionError` on an empty `broken` list; `test_the_measured_summary_supports_every_guarded_sentence` still passes.

- [x] **Step 8: Guard and render the sibling section**

In `scripts/audit/render_parent_margins.py::summary_premises`, insert after the two lines that append `"'none carries an exact reconstruction' is false"`:

```python
    sib = findings["siblings"]
    for industry in ("1131", "1132"):
        if not sib["industries"].get(industry, {}).get("fetched"):
            broken.append(f"the sibling section assumes {industry} was fetched; it was not")
    if sib["exact_where_child_suppressed"]:
        broken.append("'the sibling path reconstructs no suppressed quarter' is false")
    if sib["exact_where_child_suppressed_if_absent_is_zero"]:
        broken.append("'reading an absent sibling row as zero reconstructs nothing' is false")
```

In `render`, add after `n_sup = child_f["suppressed_rows"]`:

```python
    sib = findings["siblings"]
    sib_table = "\n".join(
        f"| `{i}` | {s['agglvl_codes_present'][0]} | {s['state_quarter_rows_private']} | "
        f"{s['disclosed_private']} | {s['disclosed_where_113_bounds']} |"
        for i, s in sorted(sib["industries"].items())
    )
```

In the template, replace `` `not_found` and `unparseable` are 0 for all four industries, so no count below is short a quarter. `` with `` `not_found` and `unparseable` are 0 for all {len(findings["slice_outcomes"])} industries, so no count below is short a quarter. `` (keep the line break where the original has it). The paragraph after the bound percentage points at the section this step deletes, so replace

```
parent. None carries an exact reconstruction through a MEASURED margin — see *What this does not
measure*.
```

with

```
parent. None carries an exact reconstruction through a MEASURED margin — see *The sibling path
(R-PM-5)*.
```

Then replace the template's whole final section, from `## What this does not measure` to the closing `"""`, with:

```
## The sibling path (R-PM-5)

`113 - 1131 - 1132 = 1133`, and the chain below `1133` is 1:1 — so a quarter with `113`, `1131`
and `1132` all published is an **exact** reconstruction of `113310`. Both siblings were walked with
the industries above and judged by the same ladder.

| sibling | agglvl | private state-quarters | published | published where `113` bounds a suppressed `113310` |
|---|---|---|---|---|
{sib_table}

On the {parents["113"]["disclosed_where_child_suppressed"]} suppressed quarters where `113` is
published, all three are published on **{sib["exact_where_child_suppressed"]}**, and on
**{sib["exact_where_child_suppressed_if_absent_is_zero"]}** when a state-quarter with no sibling row
at all is read as zero establishments — an inference, reported beside the strict count rather than
folded into the ladder. **The sibling path reconstructs no suppressed quarter**, so `REQ-027` /
§14.4 has no live instance through any margin measured here, and `specs/stage5-parent-margin.md`
R-PM-4 does not bind (`D-110`). One sibling is published on
**{sib["a_sibling_published_where_113_bounds"]}** of those quarters, which tightens the bound to
`113 - sibling` without closing it; no constraint row builds that tighter bound.
"""
```

- [x] **Step 9: Run every audit test green**

Run: `uv run pytest tests/audit -q`
Expected: all pass; the two files carry 10 more tests than before Step 2.

- [x] **Step 10: Format, lint and commit the code**

```bash
uv run ruff format scripts/audit/qcew_parent_margins.py scripts/audit/render_parent_margins.py
uv run ruff format src tests
uv run ruff check src tests
grep -nE '^\s*except [A-Za-z_.]+, ' scripts/audit/qcew_parent_margins.py scripts/audit/render_parent_margins.py || echo "no PEP 758 except syntax"
uv run pytest tests/audit -q
git add scripts/audit/qcew_parent_margins.py scripts/audit/render_parent_margins.py tests/audit/test_qcew_parent_margins.py tests/audit/test_render_parent_margins.py
git commit -m "feat(audit): measure R-PM-5's sibling path with the parent-margin ladder"
```

Expected: `ruff check` clean, the grep prints `no PEP 758 except syntax` (both files declare `>=3.12`), the audit tests pass.

- [x] **Step 11: Run the measurement (network, 192 requests) and render it**

```bash
(cd scripts/audit && set -a && source ../../.env && set +a && uv run --no-project qcew_parent_margins.py && uv run --no-project render_parent_margins.py)
```

Expected: the renderer prints `wrote …/qcew-parent-margins.md`. **If it halts naming "the sibling path reconstructs no suppressed quarter" or "reading an absent sibling row as zero", stop and escalate:** R-PM-4 binds, and Tasks 7-8 need an exactness path this plan does not contain.

- [x] **Step 12: Check that the four original industries' bytes did not move, and read the numbers off the summary**

```bash
for i in 113310 113 1133 11331; do diff -rq /tmp/qcew_parent_margins.before-rpm5/$i data/raw/audit/qcew_parent_margins/$i && echo "$i unchanged"; done
uv run python -c "import json; f = json.load(open('data/raw/audit/qcew_parent_margins/summary.json'))['findings']; print(f['identification']); print({k: v for k, v in f['siblings'].items() if k != 'industries'})"
git diff --stat specs/findings/qcew-parent-margins.md
```

Expected: four `unchanged` lines; `{'exact': 0, 'months_identified': 756, 'none': 157, 'upper_bound': 252}`; `{'a_sibling_published_where_113_bounds': 17, 'exact_where_child_suppressed': 0, 'exact_where_child_suppressed_if_absent_is_zero': 0}`, both in sorted-key order because `write_summary` sorts keys. The 17 is a union: 7 bounded quarters publish `1131` and 10 publish `1132`, and no quarter publishes both, because such a quarter would be exact and the exact count is 0. If a BLS revision moved an original extract, the regenerated finding is authoritative: carry its numbers into Tasks 4, 7 and 9 in place of 252, 756 and 107, and say so in Step 13's entry.

- [x] **Step 13: Record the R-PM-4 ruling in the Stage 5 log, derived from the summary**

```bash
uv run python - <<'EOF'
import datetime
import json
from pathlib import Path

findings = json.loads(Path("data/raw/audit/qcew_parent_margins/summary.json").read_text())["findings"]
sib, ident = findings["siblings"], findings["identification"]
bounded = findings["parents"]["113"]["disclosed_where_child_suppressed"]
section = f"""
## {datetime.date.today().isoformat()} — R-PM-5 measured: the sibling path reconstructs nothing, so R-PM-4 does not bind

`scripts/audit/qcew_parent_margins.py` now walks `1131` and `1132` with the other four industries and
judges them with the same ladder (plan 15 Task 1); `specs/findings/qcew-parent-margins.md` is the
rendering. On the {bounded} suppressed private `113310` state-quarters a published `113` bounds, all of
`113`, `1131` and `1132` are published on **{sib["exact_where_child_suppressed"]}**, and on
**{sib["exact_where_child_suppressed_if_absent_is_zero"]}** when a missing sibling row is read as zero
establishments. The ladder's tally is exact {ident["exact"]}, upper bound {ident["upper_bound"]}, none
{ident["none"]}.

**Ruling on R-PM-4:** no measured margin, whether parent, ownership or sibling, reconstructs a suppressed
state-quarter, so `exact_reconstruction_flag` keeps no live instance and the parent margin enters the
constraint system as a bound only. `D-110` closes on this measurement. One sibling is published on
{sib["a_sibling_published_where_113_bounds"]} of the bounded quarters, which would tighten the bound to
`113 - sibling`; no row builds it, and plan 15's completion files that as its own item.
"""
with Path("specs/findings/stage-5-log.md").open("a", encoding="utf-8") as log:
    log.write(section)
print(section)
EOF
```

- [x] **Step 14: Commit the finding and the ruling**

```bash
git add specs/findings/qcew-parent-margins.md specs/findings/stage-5-log.md
git commit -m "docs(findings): record R-PM-5's sibling measurement and rule R-PM-4"
```

---

### Task 2: Fetch the private `113` state series as the `qcew_parent` source

**Implements:** R-PM-1 (registry row, fetch route, the agglvl as a measured fact).

**Files:**
- Modify: `src/logging_employment/constants.py` (append two constants)
- Modify: `src/logging_employment/registry/sources.yaml` (append one row; the header's source count)
- Modify: `src/logging_employment/fetching.py` (`KNOWN_SOURCES`, the QCEW slice branch, `merge_source_manifest`'s docstring)
- Modify: `src/logging_employment/cli.py` (`fetch`)
- Test: `tests/unit/test_fetching.py`; Modify: `tests/unit/test_registry.py` (`test_the_seed_registry_is_sound`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `constants.QCEW_PARENT_INDUSTRY = "113"`, `constants.QCEW_PARENT_STATE_AGGLVL = "55"`; `fetching.KNOWN_SOURCES` including `"qcew_parent"`; stored objects under `data/raw/qcew_parent/<sha256>/{year}q{quarter}.csv` with `source_id = "qcew_parent"` rows in `runs/source_manifest.parquet`.

- [x] **Step 1: Write the failing tests**

In `tests/unit/test_fetching.py`, extend the fetching import block and add the registry loader:

```python
from logging_employment.fetching import (
    KNOWN_SOURCES,
    fetch_source,
    merge_source_manifest,
    write_source_manifest,
)
from logging_employment.registry.loader import load_registry
```

Change all three `@pytest.mark.parametrize("source", ["qcew", "qcew_size", "cbp"])` decorators to `@pytest.mark.parametrize("source", ["qcew", "qcew_parent", "qcew_size", "cbp"])`. They sit on `test_a_pre_2017_window_is_refused_before_anything_is_requested_or_stored` (`D-081`) and on the two `D-100` tests, `test_source_publication_date_carries_the_last_modified_header_verbatim` and `test_a_response_without_last_modified_records_null_rather_than_an_empty_string`. Every test that sweeps the fetchable sources gains the new one; the `D-081` case pins that the pre-2017 refusal still runs before any source branch. Append to the end of the file:

```python
def _recording_slice_handler(seen: list[str]):
    """Serve the 2017q1 slice for every request, recording each URL the fetch actually asked for."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, content=SLICE)

    return handler


def test_the_parent_source_fetches_the_113_slice_into_its_own_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-PM-1: the private `113` series rides `ingest/qcew.py`'s slice route under its own source id.

    Every request names `industry/113.csv` -- the boundary probe included, because a route property
    measured for `113310` is not a measurement for `113` -- and nothing lands in `qcew`'s store.
    """
    seen: list[str] = []
    _mock_transport(monkeypatch, _recording_slice_handler(seen))
    rows = fetch_source(
        "qcew_parent",
        _cfg(),
        env_path=None,
        raw_root=tmp_path,
        output_root=tmp_path,
        years=[2017],
        quarters=[1],
    )
    assert [row["source_id"] for row in rows] == ["qcew_parent"]
    assert seen and all(url.endswith("/industry/113.csv") for url in seen)
    assert len(list((tmp_path / "qcew_parent").rglob("2017q1.csv"))) == 1
    assert not (tmp_path / "qcew").exists()
    manifest = pl.read_parquet(tmp_path / "source_manifest.parquet")
    assert manifest["source_id"].to_list() == ["qcew_parent"]


def test_every_fetchable_source_has_a_registry_row() -> None:
    """§7.1: a source the pipeline can fetch is a source the registry describes."""
    registry = load_registry(REPO / "src" / "logging_employment" / "registry" / "sources.yaml")
    assert set(KNOWN_SOURCES) <= {row.source_id for row in registry}
```

In `tests/unit/test_registry.py::test_the_seed_registry_is_sound`, the seed registry's exact source set gains the new row:

```python
    assert {r.source_id for r in rows} == {"qcew", "qcew_parent", "qcew_size", "cbp"}
```

- [x] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/unit/test_fetching.py tests/unit/test_registry.py -q`
Expected: `5 failed`. Four are the parent-source test and the three `[qcew_parent]` parametrizations, each with `ValueError: unknown source 'qcew_parent'; known: ('qcew', 'qcew_size', 'cbp')`. The fifth is `test_the_seed_registry_is_sound`, because the registry has no `qcew_parent` row yet. The registry-coverage test passes already: it pins that today's three sources are described, and it must keep passing once `qcew_parent` joins `KNOWN_SOURCES`.

- [x] **Step 3: Record the parent level as a measured constant**

Append to `src/logging_employment/constants.py`:

```python

# The parent series that bounds `113310` from above (§9.3; `specs/stage5-parent-margin.md` R-PM-1).
# MEASURED, not documented: `specs/findings/qcew-parent-margins.md` found private `113` state rows on
# all 32 D1 slices of `industry/113.csv`, every one at agglvl 55 -- NOT at `QCEW_STATE_AGGLVL`, the
# 6-digit level. A route filtering on 58 reads zero parent rows as a clean absence, which is why
# `build.state_parent_rows` halts on an empty result instead of trusting this value.
QCEW_PARENT_INDUSTRY = "113"
QCEW_PARENT_STATE_AGGLVL = "55"
```

- [x] **Step 4: Put `qcew_parent` on the shared slice route**

In `src/logging_employment/fetching.py`, add `from .constants import QCEW_PARENT_INDUSTRY` directly below `from .config import SECRET_ENV_VARS, Config, credentials`, and change `KNOWN_SOURCES` to:

```python
KNOWN_SOURCES = ("qcew", "qcew_parent", "qcew_size", "cbp")
```

Replace the whole `if source == "qcew":` branch — from that line down to, not including, `        elif source == "qcew_size":` — with:

```python
        if source in ("qcew", "qcew_parent"):
            # ONE CLIENT, TWO SERIES (R-PM-1). The private `113` state series is the same QCEW
            # product on the same route as `113310`, so it reuses the boundary probe and
            # `qcew.fetch_slice` rather than a second client; only the industry and the store it
            # lands in differ. The boundary is probed for the industry being fetched, because a
            # route property measured for one industry is not a measurement for another (§5.4).
            # `release_status` is QCEW's own key: the parent is that product, over that window.
            industry = cfg.project.industry_code_used if source == "qcew" else QCEW_PARENT_INDUSTRY
            boundary = qcew.probe_slice_boundary(
                fetcher,
                industry,
                range(min(window_years) - 5, min(window_years) + 1),
            )
            for year in window_years:
                for quarter in list(quarters or (1, 2, 3, 4)):
                    route = qcew.route_for_year(year, boundary)
                    if route == "slice":
                        fetched = qcew.fetch_slice(fetcher, year, quarter, industry)
                        name = f"{year}q{quarter}.csv"
                    else:
                        fetched = fetcher.get(qcew.bulk_url(year))
                        name = f"{year}_qtrly_by_industry.zip"
                    if not _usable(
                        fetched, source_id=source, year=year, reference=f"{year}q{quarter}"
                    ):
                        continue
                    stored = store.put(source, fetched, name)
                    rows.append(
                        snapshot_row(
                            source_id=source,
                            fetched=fetched,
                            stored=stored,
                            reference_start=f"{year}-{(quarter - 1) * 3 + 1:02d}",
                            reference_end=f"{year}-{quarter * 3:02d}",
                            release_status=cfg.sources.qcew.release_status,
                            naics_vintage=vintage_for_year(year),
                            schema_fingerprint=schema_fingerprint(QCEW_MONTHLY_SCHEMA),
                            parser_version=qcew.PARSER_VERSION,
                            source_publication_date=fetched.last_modified,
                            secrets=secrets,
                        )
                    )
```

In `merge_source_manifest`'s docstring, a fourth source makes one count false. Change `` `fetch` runs once per source, and all three invocations name the same artifact. `` to `` `fetch` runs once per source, and every invocation names the same artifact. ``

- [x] **Step 5: Accept the source at the CLI and describe it in the registry**

In `src/logging_employment/cli.py`, replace the `fetch` command with:

```python
@app.command("fetch")
def fetch(
    source: str = typer.Option(..., "--source", help="qcew, qcew_parent, qcew_size, or cbp"),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Acquire raw bytes for one source into the immutable store and record a snapshot row."""
    from .fetching import KNOWN_SOURCES, fetch_source

    if source not in KNOWN_SOURCES:
        raise typer.BadParameter(f"unknown source {source!r}")

    cfg = load_config(config)
    rows = fetch_source(source, cfg, env_path=Path(".env"))
    typer.echo(f"{source}: {len(rows)} snapshot row(s) -> {cfg.storage.raw_uri}")
```

Append this row to the end of `src/logging_employment/registry/sources.yaml`, with the `cbp` row's indentation. The file already ends with a blank line, which becomes the separator, and the row's own trailing blank line keeps that ending:

```yaml
  - source_id: "qcew_parent"
    agency: "BLS"
    dataset: "Quarterly Census of Employment and Wages, quarterly industry data: the private 113 (Forestry and Logging) state series"
    landing_url: "https://www.bls.gov/cew/"
    endpoint_pattern: "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/113.csv"
    access_status: "verified"
    frequency: "quarterly"
    reference_period: "calendar quarter; employment arrives as three monthly columns, as for qcew. All 32 D1 quarters answered 200 with a parsable CSV (qcew_parent_margins.findings.slice_outcomes)"
    geography: "state rows at agglvl 55, measured (qcew_parent_margins.findings.parents.113.agglvl_codes_present) -- NOT agglvl 58, the 113310 state level, so a route filtering on 58 reads a false absence"
    industry_detail: "NAICS 3-digit 113, which aggregates 1131, 1132 and 1133; 1133 -> 11331 -> 113310 is single-child, so 113 >= 113310 wherever both are published [documented: NAICS structure]"
    ownership: "private (own_code 5) is the series used: 1588 private state-quarter rows over D1 (qcew_parent_margins.findings.parents.113.state_quarter_rows_private)"
    statistical_unit: "establishment (reporting unit) [documented]"
    employment_concept: "jobs covered by state UI and UCFE programs, counted for the pay period including the 12th of the month [documented]"
    size_dimension: "all establishment sizes only, as for the qcew slice route; not separately measured for 113 [documented-not-measured]"
    disclosure_regime: "qcew_disclosure_code_v1"
    revision_policy: "a quarter is finalized with the following year's Q1 release [documented]"
    model_role: "hard constraint source: a published private 113 state value bounds the suppressed 113310 cell of the same state-month from above (§9.3 parent-total constraint; specs/stage5-parent-margin.md R-PM-2)"
    limitations: "published on 1278 of 1588 private state-quarters and on 252 of the 409 where 113310 is suppressed (qcew_parent_margins.findings.parents.113). A bound, never an exact value: the sibling path 113 - 1131 - 1132 reconstructs no suppressed quarter (qcew_parent_margins.findings.siblings, plan 15 Task 1)"

```

Then correct the file's first line, which counts the sources. Change `# The §7.1 source registry, seeded for the three sources Stage 1 ingests.` to `# The §7.1 source registry, seeded for the three sources Stage 1 ingests and plan 15's qcew_parent.`

- [x] **Step 6: Run the tests and the gates**

```bash
uv run pytest tests/unit/test_fetching.py tests/unit/test_registry.py -q
uv run logging-estimates registry verify --config config.yaml
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: the fetch and registry tests pass; `OK: registry verified`; ruff and interrogate clean. Suite: **+5 passed** (the parent test, the registry test and the three `[qcew_parent]` parametrizations), 0 failed.

- [x] **Step 7: Fetch the parent series (network, 38 requests)**

```bash
uv run logging-estimates fetch --source qcew_parent --config config.yaml
uv run python -c "import polars as pl; m = pl.read_parquet('runs/source_manifest.parquet').filter(pl.col('source_id') == 'qcew_parent'); print(m.height, m['reference_start'].min(), m['reference_end'].max(), m['source_publication_date'].null_count())"
```

Expected: `qcew_parent: 32 snapshot row(s) -> data/raw`, then `32 2017-01 2024-12 0` — every quarter stored, each with the `Last-Modified` stamp `D-100` records.

- [x] **Step 8: Commit**

```bash
git add src/logging_employment/constants.py src/logging_employment/registry/sources.yaml src/logging_employment/fetching.py src/logging_employment/cli.py tests/unit/test_fetching.py tests/unit/test_registry.py
git commit -m "feat(fetch): add the qcew_parent source for the private 113 state series (R-PM-1)"
```

---

### Task 3: Stamp CBP's vintage from the predicate its own metadata serves (`D-114`)

**Implements:** `D-114`. It rides this plan's rebuild, as the item asks, so the run id moves once.

**Files:**
- Modify: `src/logging_employment/ingest/cbp.py` (new `vintage_for_predicate`)
- Modify: `src/logging_employment/build.py` (the CBP stamp in `build_harmonized`)
- Modify: `src/logging_employment/fetching.py` (both CBP snapshot rows)
- Test: `tests/unit/test_cbp.py`, `tests/integration/test_build_harmonized.py`, `tests/unit/test_fetching.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `cbp.vintage_for_predicate(predicate: str) -> str` — `"NAICS2017"` gives `"NAICS 2017"`; a predicate naming no four-digit year raises `ValueError`.

- [x] **Step 1: Write the failing tests**

Append to `tests/unit/test_cbp.py`:

```python
def test_the_vintage_is_the_one_the_stored_metadata_serves() -> None:
    """D-114: CBP's 2023 metadata serves `NAICS2017`, labelled "2017 NAICS code", so its rows are
    NAICS 2017 rows, whatever BLS's rule for QCEW says about 2023."""
    variables = json.loads((FIX / "variables_2023.json").read_text())
    assert cbp.vintage_for_predicate(cbp.discover_naics_predicate(variables)) == "NAICS 2017"


@pytest.mark.parametrize("predicate", ["NAICS", "NAICS17", "NAICS2017_LABEL", "SIC1987"])
def test_a_predicate_that_names_no_vintage_is_refused(predicate: str) -> None:
    with pytest.raises(ValueError, match="names no NAICS vintage"):
        cbp.vintage_for_predicate(predicate)
```

Append to `tests/integration/test_build_harmonized.py`:

```python
def test_cbp_rows_carry_the_vintage_their_own_metadata_serves(
    frozen_raw: Path, tmp_path: Path
) -> None:
    """D-114: the 2023 response is coded in NAICS 2017 by its own metadata, not NAICS 2022."""
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path)
    stamped = pl.read_parquet(tmp_path / "cbp_state_size.parquet")["naics_vintage"].unique()
    assert stamped.to_list() == ["NAICS 2017"]
```

Append to `tests/unit/test_fetching.py`:

```python
def test_both_cbp_snapshot_rows_record_the_vintage_the_metadata_serves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-114: the metadata row and the data row both stamp the vintage CBP's predicate names."""
    _mock_transport(monkeypatch, _dated_handler(None))
    monkeypatch.setenv("CENSUS_API_KEY", "SECRET-CENSUS-KEY")
    rows = _fetch_one_period("cbp", tmp_path)
    assert len(rows) == 2
    assert {row["naics_vintage"] for row in rows} == {"NAICS 2017"}
```

- [x] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/unit/test_cbp.py tests/unit/test_fetching.py tests/integration/test_build_harmonized.py -q`
Expected: `7 failed` — five `AttributeError: module 'logging_employment.ingest.cbp' has no attribute 'vintage_for_predicate'`, the build test with `['NAICS 2022'] == ['NAICS 2017']` false, the fetch test with `{'NAICS 2022'} == {'NAICS 2017'}` false.

- [x] **Step 3: Read the vintage off the predicate**

In `src/logging_employment/ingest/cbp.py`, add directly after `discover_naics_predicate` (the module already imports `re`):

```python
_PREDICATE_VINTAGE = re.compile(r"NAICS(\d{4})")


def vintage_for_predicate(predicate: str) -> str:
    """The NAICS vintage a CBP response is coded in, read off the predicate its metadata served.

    CBP names its industry variable after the vintage it serves -- `NAICS2017` for every year
    2017-2023, labelled "2017 NAICS code" in each year's stored metadata -- so the vintage is read
    from that name, not computed from the reference year (`D-114`). `harmonize.naics.
    vintage_for_year` is BLS's rule for QCEW; applied here it stamped CBP's 2022 and 2023 rows with
    a vintage their own source contradicts. A predicate naming no four-digit year is refused rather
    than guessed.
    """
    found = _PREDICATE_VINTAGE.fullmatch(predicate)
    if found is None:
        raise ValueError(
            f"CBP predicate {predicate!r} names no NAICS vintage; expected NAICS<year>"
        )
    return f"NAICS {found.group(1)}"
```

Do not write a 2022 predicate literal anywhere in this module: `tests/unit/test_cbp.py::test_no_naics2022_predicate_is_ever_constructed` greps the file for it.

- [x] **Step 4: Stamp the harmonized CBP rows from the predicate**

In `src/logging_employment/build.py::build_harmonized`, replace the `cbp_frames.append(...)` call — including the `DELIBERATELY QCEW-DERIVED, AND WRONG FOR 2022 AND 2023 (D-098)` comment block inside it — with:

```python
        predicate = predicate_from_stored_metadata(
            raw_root / "cbp", year, manifest_path=manifest_path
        )
        cbp_frames.append(
            cbp.parse_cbp_state_size(
                json.loads(path.read_text()),
                snapshot_id=path.stem,
                reference_year=year,
                predicate=predicate,
                # READ OFF CBP'S OWN METADATA (D-114), not `vintage_for_year`, which is BLS's rule
                # for QCEW. The stored metadata serves `NAICS2017`, labelled "2017 NAICS code", for
                # every window year, so that rule stamped the 2022 and 2023 rows with a vintage
                # their own source contradicts. Nothing reads the column -- every CBP consumer keys
                # on `reference_year` -- which is why the correction waited for a rebuild that
                # re-ids the run anyway (plan 15).
                naics_vintage=cbp.vintage_for_predicate(predicate),
                regime=regime,
            )
        )
```

- [x] **Step 5: Stamp both CBP snapshot rows from the predicate**

In `src/logging_employment/fetching.py`'s CBP branch, move the predicate discovery up so it directly follows `stored_variables = store.put("cbp", variables, cbp.metadata_filename(year))`, and derive the stamp once:

```python
                stored_variables = store.put("cbp", variables, cbp.metadata_filename(year))
                predicate = cbp.discover_naics_predicate(json.loads(variables.content))
                # Both CBP rows record the vintage CBP's own predicate names (D-114), for the reason
                # `build.build_harmonized` gives at its stamp; QCEW's year rule does not apply here.
                vintage = cbp.vintage_for_predicate(predicate)
```

Delete the later `predicate = cbp.discover_naics_predicate(json.loads(variables.content))` line, which now duplicates this one, and change `naics_vintage=vintage_for_year(year),` to `naics_vintage=vintage,` in BOTH CBP `snapshot_row(...)` calls (the metadata row and the data row), which are the last two of that string's four occurrences in the file. The QCEW and QCEW-by-size rows keep `vintage_for_year(year)`.

Then correct `src/logging_employment/ingest/cbp.py`'s module docstring, which Steps 4 and 5 make false. Replace its second paragraph, from `` `naics_vintage` is a caller-supplied stamp `` to `` (`D-098`, `D-114`). ``, with:

```
`naics_vintage` is a caller-supplied stamp this module passes through untouched. Since `D-114`
both callers derive it from CBP's own metadata through `vintage_for_predicate`, not from QCEW's
reference-year rule, because the two disagree for two window years: measured 2026-09-12, every
stored `{year}_variables.json` for 2017-2023 serves exactly one NAICS variable, `NAICS2017`,
labelled "2017 NAICS code", including 2022 and 2023, which QCEW's rule stamps "NAICS 2022".
```

- [x] **Step 6: Run the tests and the gates**

```bash
uv run pytest tests/unit/test_cbp.py tests/unit/test_fetching.py tests/integration/test_build_harmonized.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: targeted tests pass; ruff and interrogate clean. Suite: **+7 passed**, 0 failed. `data/staged/` is not rebuilt here, so no run id moves yet.

- [x] **Step 7: Commit**

```bash
git add src/logging_employment/ingest/cbp.py src/logging_employment/build.py src/logging_employment/fetching.py tests/unit/test_cbp.py tests/unit/test_fetching.py tests/integration/test_build_harmonized.py
git commit -m "fix(cbp): stamp CBP's NAICS vintage from its own predicate (D-114)"
```

---

### Task 4: Add the harmonized parent table, rebuild the staged layer, move the acceptance pin

**Implements:** R-PM-1 (the ingest path, the level as a fail-closed measured fact); Decision 1.

**Files:**
- Modify: `src/logging_employment/ingest/qcew.py` (`parse_qcew_monthly`)
- Modify: `src/logging_employment/contracts.py` (`_HARMONIZED_TABLES`, new `_no_state_parent`, `HarmonizedData`)
- Modify: `src/logging_employment/build.py` (new `state_parent_rows`; `build_harmonized`)
- Create: `tests/fixtures/qcew/slice_113_2017q1.csv`; Modify: `tests/fixtures/qcew/README.md`
- Create: `tests/fixtures/baselines/qcew_state_parent.parquet`, `tests/fixtures/constraints/qcew_state_parent.parquet`, `tests/fixtures/national_size_margin/qcew_state_parent.parquet`
- Modify: `tests/fixtures/national_size_margin/README.md` (the table count and listing), `tests/integration/test_national_size_margin_golden.py` (`FIXTURE_TABLES`, one docstring count)
- Modify: `tests/integration/conftest.py` (`STAGED_TABLES`), `tests/integration/test_constraint_cli.py` (`workspace`), `tests/integration/test_baseline_golden.py` (the tracked-fixture list)
- Test: `tests/unit/test_qcew_parser.py`, `tests/unit/test_contracts.py`, `tests/integration/test_build_harmonized.py`
- Modify: `tests/integration/test_stage4_acceptance.py` (the V1 pin)

**Interfaces:**
- Consumes: `constants.QCEW_PARENT_INDUSTRY`, `constants.QCEW_PARENT_STATE_AGGLVL` and the stored `qcew_parent` slices (Task 2); `cbp.vintage_for_predicate` (Task 3).
- Produces: `qcew.parse_qcew_monthly(frame, *, snapshot_id, release_vintage, release_status, naics_vintage, state_agglvl: str = QCEW_STATE_AGGLVL)`; `HarmonizedData.qcew_state_parent: pl.DataFrame` in `QCEW_MONTHLY_SCHEMA`, empty by default; `build.state_parent_rows(raw: bytes, *, snapshot_id: str, release_status: str, naics_vintage: str) -> pl.DataFrame`; `data/staged/qcew_state_parent.parquet`.

- [x] **Step 1: Create the fixtures**

```bash
uv run python - <<'EOF'
from pathlib import Path

source = Path("data/raw/audit/qcew_parent_margins/113/2017q1.csv")
lines = source.read_bytes().splitlines(keepends=True)
kept = [lines[0]] + [
    line for line in lines[1:] if line.split(b",", 1)[0].strip(b'"').endswith(b"000")
]
Path("tests/fixtures/qcew/slice_113_2017q1.csv").write_bytes(b"".join(kept))
print(len(lines) - 1, "rows in the extract;", len(kept) - 1, "kept")
EOF
uv run python - <<'EOF'
from pathlib import Path

import polars as pl

from logging_employment.build import write_parquet_deterministic
from logging_employment.contracts import QCEW_MONTHLY_SCHEMA

for directory in ("baselines", "constraints", "national_size_margin"):
    path = Path("tests/fixtures") / directory / "qcew_state_parent.parquet"
    print(path, write_parquet_deterministic(pl.DataFrame(schema=QCEW_MONTHLY_SCHEMA), path))
EOF
```

Expected: `2005 rows in the extract; 62 kept` (a 12,015-byte fixture), then three paths each followed by the same digest, `e5d575c06bd15002ea5a3e4c19d5eb3f14b4b9e8ac9dd04877379426910be233`: an empty table written deterministically is one byte string wherever it lands. Stage the three now, because `tests/integration/test_national_size_margin_golden.py` asks git's index which fixture files are tracked:

```bash
git add tests/fixtures/baselines/qcew_state_parent.parquet tests/fixtures/constraints/qcew_state_parent.parquet tests/fixtures/national_size_margin/qcew_state_parent.parquet
```

Append to `tests/fixtures/qcew/README.md`:

````markdown

## `slice_113_2017q1.csv` — audited bytes, cut to state and national rows

The private `113` parent series behind `tests/integration/test_build_harmonized.py`'s parent-table
tests (`specs/stage5-parent-margin.md` R-PM-1). It is
`data/raw/audit/qcew_parent_margins/113/2017q1.csv`, one of the extracts
`specs/findings/qcew-parent-margins.md` pins, with every row whose `area_fips` does not end in `000`
removed. Kept lines are byte-identical: the header, and the state and national rows at every
ownership. County and MSA rows bound no state cell, and the whole extract is 304,909 bytes.

```bash
uv run python - <<'PY'
from pathlib import Path
source = Path("data/raw/audit/qcew_parent_margins/113/2017q1.csv")
lines = source.read_bytes().splitlines(keepends=True)
kept = [lines[0]] + [
    line for line in lines[1:] if line.split(b",", 1)[0].strip(b'"').endswith(b"000")
]
Path("tests/fixtures/qcew/slice_113_2017q1.csv").write_bytes(b"".join(kept))
PY
```
````

`tests/fixtures/national_size_margin/README.md` counts the tables `HarmonizedData.load` expects, and this task makes it five. Change `These four parquet files are that input, tracked.` to `These five parquet files are that input, tracked.`. Change `` Four tables, because `HarmonizedData.load` expects all four. Two carry rows; two carry schema `` to `` Five tables, because `HarmonizedData.load` expects all five. Two carry rows; three carry schema ``. Add a row directly under the `bridge.parquet` row:

```markdown
| `qcew_state_parent.parquet` | 0 | schema only |
```

In the same README's regeneration script, the schema-only loop must write the new table too: change `for name in ("cbp_state_size", "bridge"):` to `for name in ("cbp_state_size", "bridge", "qcew_state_parent"):`.

In `tests/integration/test_national_size_margin_golden.py::test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data`'s docstring, change `If these four tables were sliced out of it at test time` to `If these tables were sliced out of it at test time`.

- [x] **Step 2: Write the failing tests**

Append to `tests/unit/test_qcew_parser.py`:

```python
def test_a_parent_slice_is_read_at_the_state_level_its_caller_names() -> None:
    """R-PM-1: `113` is served at agglvl 55, so read at the default 58 its state rows are `other`."""
    frame = _row(industry_code="113", agglvl_code="55")
    kwargs = {
        "snapshot_id": "snap",
        "release_vintage": "2017Q1",
        "release_status": "final",
        "naics_vintage": "NAICS 2017",
    }
    assert set(qcew.parse_qcew_monthly(frame, **kwargs)["area_type"]) == {"other"}
    assert set(qcew.parse_qcew_monthly(frame, **kwargs, state_agglvl="55")["area_type"]) == {
        "state"
    }
```

In `tests/unit/test_contracts.py`, replace `test_harmonized_data_loads_the_four_stage_one_tables` with these three tests:

```python
def test_harmonized_data_loads_the_five_stage_one_tables(tmp_path) -> None:
    for name, schema in (
        ("qcew_monthly", {"reference_month": pl.String}),
        ("qcew_national_size", {"reference_year": pl.Int64}),
        ("cbp_state_size", {"reference_year": pl.Int64}),
        ("bridge", {"bridge_id": pl.String}),
        ("qcew_state_parent", {"reference_month": pl.String}),
    ):
        pl.DataFrame(schema=schema).write_parquet(tmp_path / f"{name}.parquet")
    data = contracts.HarmonizedData.load(tmp_path)
    assert data.qcew_monthly.height == 0
    assert data.bridge.columns == ["bridge_id"]
    assert data.qcew_state_parent.columns == ["reference_month"]


def test_a_staged_layer_without_the_parent_table_halts_by_path(tmp_path) -> None:
    """R-PM-1: an old four-table layer must not load as a layer with no parent margin."""
    for name in ("qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge"):
        pl.DataFrame({"x": [1]}).write_parquet(tmp_path / f"{name}.parquet")
    with pytest.raises(FileNotFoundError, match="qcew_state_parent.parquet"):
        contracts.HarmonizedData.load(tmp_path)


def test_a_directly_built_layer_carries_an_empty_parent_table_in_the_monthly_schema() -> None:
    data = contracts.HarmonizedData(
        qcew_monthly=pl.DataFrame(),
        qcew_national_size=pl.DataFrame(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    assert data.qcew_state_parent.height == 0
    assert data.qcew_state_parent.schema == pl.Schema(contracts.QCEW_MONTHLY_SCHEMA)
```

In `tests/integration/test_build_harmonized.py`, change the imports to:

```python
from logging_employment import build
from logging_employment.build import build_harmonized, write_parquet_deterministic
from logging_employment.config import load_config
from logging_employment.errors import ConceptViolationError, UnknownDisclosureRegimeError
```

add the parent slice to `frozen_raw`, directly before its `return raw`:

```python
    (raw / "qcew_parent" / "frozen").mkdir(parents=True)
    shutil.copy(
        FIXTURES / "qcew" / "slice_113_2017q1.csv", raw / "qcew_parent" / "frozen" / "2017q1.csv"
    )
```

change the set in `test_rebuild_is_byte_identical` (`set(first)`) and the identical four-table set in `test_the_run_manifest_names_which_metadata_copy_the_build_reads` (`set(hashes)`) to this five-table set, which ruff lays out one name per line:

```python
    assert set(first) == {
        "qcew_monthly",
        "qcew_national_size",
        "cbp_state_size",
        "bridge",
        "qcew_state_parent",
    }
```

and append:

```python
def test_the_parent_table_is_the_private_113_state_series(frozen_raw: Path, tmp_path: Path) -> None:
    """R-PM-1: only private state rows of `113`, read at the level `113` is served at."""
    build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path)
    parent = pl.read_parquet(tmp_path / "qcew_state_parent.parquet")
    assert parent.height > 0
    assert set(parent["industry_code"]) == {"113"}
    assert set(parent["aggregation_level"]) == {"55"}
    assert set(parent["area_type"]) == {"state"}
    assert set(parent["ownership_code"]) == {"5"}


def test_a_parent_slice_read_at_the_wrong_level_halts_rather_than_building_nothing(
    frozen_raw: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The level is a measurement: a changed one must halt, never read as a clean absence."""
    monkeypatch.setattr(build, "QCEW_PARENT_STATE_AGGLVL", "58")
    with pytest.raises(ConceptViolationError, match="agglvl 58"):
        build_harmonized(_cfg(), raw_root=frozen_raw, out_root=tmp_path)


def test_a_raw_store_with_no_parent_slice_halts_before_writing_anything(
    frozen_raw: Path, tmp_path: Path
) -> None:
    shutil.rmtree(frozen_raw / "qcew_parent")
    out = tmp_path / "out"
    with pytest.raises(FileNotFoundError, match="fetch --source qcew_parent"):
        build_harmonized(_cfg(), raw_root=frozen_raw, out_root=out)
    assert not list(out.glob("*.parquet"))
```

- [x] **Step 3: Run them and watch them fail**

Run: `uv run pytest tests/unit/test_qcew_parser.py tests/unit/test_contracts.py tests/integration/test_build_harmonized.py -q`
Expected: `9 failed` — the parser test (`TypeError: ... unexpected keyword argument 'state_agglvl'`), the three contracts tests (`AttributeError` on `qcew_state_parent`, or `DID NOT RAISE`), `test_rebuild_is_byte_identical` and `test_the_run_manifest_names_which_metadata_copy_the_build_reads` (set mismatch), and the three new build tests (`FileNotFoundError` reading the parquet, `AttributeError` from `monkeypatch.setattr`, `DID NOT RAISE`).

- [x] **Step 4: Let the parser read state rows at a named level**

In `src/logging_employment/ingest/qcew.py`, change `parse_qcew_monthly`'s signature to:

```python
def parse_qcew_monthly(
    frame: pl.DataFrame,
    *,
    snapshot_id: str,
    release_vintage: str,
    release_status: str,
    naics_vintage: str,
    state_agglvl: str = QCEW_STATE_AGGLVL,
) -> pl.DataFrame:
```

add this paragraph to its docstring, after the `source_row_hash` paragraph:

```
    `state_agglvl` names the aggregation level whose rows are this frame's STATE rows. It defaults to
    `constants.QCEW_STATE_AGGLVL` (58, the 6-digit level `113310` is served at). The private `113`
    parent is served at its own digit-depth level, `constants.QCEW_PARENT_STATE_AGGLVL`, so its
    caller names that level rather than this parser learning a second industry (R-PM-1).
```

and change `.when(pl.col("agglvl_code") == QCEW_STATE_AGGLVL)` to `.when(pl.col("agglvl_code") == state_agglvl)`.

- [x] **Step 5: Add the table to the harmonized contract**

In `src/logging_employment/contracts.py`, change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`, then replace `_HARMONIZED_TABLES` and the head of `HarmonizedData` down to, not including, `    @classmethod` with:

```python
_HARMONIZED_TABLES = (
    "qcew_monthly",
    "qcew_national_size",
    "cbp_state_size",
    "bridge",
    "qcew_state_parent",
)


def _no_state_parent() -> pl.DataFrame:
    """The parent table a directly built `HarmonizedData` carries when its caller supplies none."""
    return pl.DataFrame(schema=QCEW_MONTHLY_SCHEMA)


@dataclass(frozen=True)
class HarmonizedData:
    """The Stage 1 harmonized layer, as §16.2's `build_constraint_system` receives it.

    Every downstream stage reads only this layer, never a source endpoint. Loading is eager and
    fails on the first missing file rather than deferring to a Polars error at first use, so a run
    started before `build-harmonized` halts with the path it wanted.

    `qcew_state_parent` is the private `113` state series (`specs/stage5-parent-margin.md` R-PM-1),
    in `QCEW_MONTHLY_SCHEMA` because it is the same QCEW product through the same parser. It is a
    TABLE OF ITS OWN rather than extra rows in `qcew_monthly` because two consumers select a cell
    from that table by `(state_fips, reference_month)` alone -- `validate/mask.apply_mask` and
    `validate/leakage.assert_no_retained_truth` -- and a parent row shares both keys with its
    child. It defaults to an EMPTY frame only for a directly constructed instance, which is how
    every fixture-built test predates it; `load` still requires the file, so a staged layer
    without it halts rather than silently building no parent margin.
    """

    qcew_monthly: pl.DataFrame
    qcew_national_size: pl.DataFrame
    cbp_state_size: pl.DataFrame
    bridge: pl.DataFrame
    qcew_state_parent: pl.DataFrame = field(default_factory=_no_state_parent)

```

and change `load`'s docstring to `"""Read the five Stage 1 tables from a `data/staged`-shaped directory."""`.

- [x] **Step 6: Build the table, halting on a missing or empty series**

In `src/logging_employment/build.py`, add `from .constants import QCEW_PARENT_INDUSTRY, QCEW_PARENT_STATE_AGGLVL` below `from .config import Config`, and change the errors import to `from .errors import AmbiguousSnapshotError, ConceptViolationError, UnknownDisclosureRegimeError`. Add this function directly before `build_harmonized`:

```python
def state_parent_rows(
    raw: bytes, *, snapshot_id: str, release_status: str, naics_vintage: str
) -> pl.DataFrame:
    """The private `113` state rows of one stored parent slice (R-PM-1).

    Parsed at `QCEW_PARENT_STATE_AGGLVL`, universe-filtered exactly as the `113310` table is
    (REQ-002), then kept to state rows of the parent industry: the slice also carries national, MSA
    and county rows, none of which bounds a state cell. AN EMPTY RESULT HALTS. The level is a
    measurement, not a documented constant, and a changed level would otherwise build a table with
    no rows -- a margin that silently vanished rather than one measured absent.
    """
    parsed = qcew.apply_universe_filter(
        qcew.parse_qcew_monthly(
            qcew.read_slice_csv(raw),
            snapshot_id=snapshot_id,
            release_vintage=snapshot_id,
            release_status=release_status,
            naics_vintage=naics_vintage,
            state_agglvl=QCEW_PARENT_STATE_AGGLVL,
        )
    )
    rows = parsed.filter(
        (pl.col("area_type") == "state") & (pl.col("industry_code") == QCEW_PARENT_INDUSTRY)
    )
    if rows.is_empty():
        raise ConceptViolationError(
            f"{snapshot_id}: the stored parent slice carries no private {QCEW_PARENT_INDUSTRY} "
            f"state row at agglvl {QCEW_PARENT_STATE_AGGLVL}; the level is measured, not "
            "documented, so a changed one halts rather than building an empty parent table (R-PM-1)"
        )
    return rows
```

In `build_harmonized`, insert directly after `    hashes: dict[str, str] = {}`:

```python
    # Resolved BEFORE the first table is written. A raw store without the parent series would
    # otherwise leave a partial staged layer behind -- one whose digests re-id a run from inputs no
    # build ever completed.
    parent_paths = snapshot_paths("qcew_parent", raw_root, "*.csv", manifest_path=manifest_path)
    if not parent_paths:
        raise FileNotFoundError(
            f"no stored qcew_parent slice under {raw_root / 'qcew_parent'}; the §9.3 parent margin "
            "needs the private 113 state series -- run `logging-estimates fetch --source "
            "qcew_parent` first"
        )
```

and insert directly after the `hashes["qcew_monthly"] = write_parquet_deterministic(...)` statement:

```python
    hashes["qcew_state_parent"] = write_parquet_deterministic(
        pl.concat(
            [
                state_parent_rows(
                    path.read_bytes(),
                    snapshot_id=path.stem,
                    release_status=cfg.sources.qcew.release_status,
                    naics_vintage=vintage_for_year(int(path.stem[:4])),
                )
                for path in parent_paths
            ]
        ),
        out_root / "qcew_state_parent.parquet",
    )
```

In `tests/integration/conftest.py`, change `STAGED_TABLES` to:

```python
STAGED_TABLES = (
    "qcew_monthly",
    "qcew_national_size",
    "cbp_state_size",
    "bridge",
    "qcew_state_parent",
)
```

Four more sites restate the staged tables. Two fail once `HarmonizedData.load` expects five, and two stay green but would stop checking the new file. In `tests/integration/test_constraint_cli.py`'s `workspace` fixture, change the loop header to:

```python
    for name in (
        "qcew_monthly",
        "qcew_national_size",
        "cbp_state_size",
        "bridge",
        "qcew_state_parent",
    ):
```

In `tests/integration/test_national_size_margin_golden.py`, change `FIXTURE_TABLES` to:

```python
FIXTURE_TABLES = (
    "qcew_monthly",
    "qcew_national_size",
    "cbp_state_size",
    "bridge",
    "qcew_state_parent",
)
```

In `tests/integration/test_baseline_golden.py::test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data`, add `"qcew_state_parent",` directly after `"bridge",` in the name list.

The fourth counts the tables instead of naming them, so a search for the names never finds it. In `tests/integration/test_build_harmonized.py::test_the_run_manifest_resolves_which_snapshot_the_build_reads`, change `assert len(hashes) == 4` to `assert len(hashes) == 5`. It passes at Step 3, because the build still writes four tables there, and fails from this step on until it is changed.

- [x] **Step 7: Run the targeted tests and the fixture-based goldens green**

> Deviation: with `data/` present the second command does not all pass: `tests/integration/test_stage4_acceptance.py::test_the_guard_is_binding_on_the_d1_panel` is `requires_staged` and fails in this red window on the missing fifth staged table (the contract expects five while `data/staged` still holds four); the plan's run had no `data/` and skipped it. It passed in Step 10's suite (1504 passed, 0 failed).

```bash
uv run pytest tests/unit/test_qcew_parser.py tests/unit/test_contracts.py tests/integration/test_build_harmonized.py -q
uv run pytest tests/integration/test_constraint_golden.py tests/integration/test_baseline_golden.py tests/integration/test_national_size_margin_golden.py tests/integration/test_validation_golden.py tests/integration/test_stage4_acceptance.py -q
```

Expected: both pass. The goldens pass UNCHANGED because every fixture directory carries an empty parent table. Do not run the whole suite yet: until Step 8 rebuilds `data/staged/`, every data-bound test that calls `HarmonizedData.load(STAGED)` fails on the missing fifth file.

- [x] **Step 8: Rebuild the staged layer**

```bash
shasum -a 256 data/staged/*.parquet | tee /tmp/staged-before-plan15.sha256
uv run logging-estimates build-harmonized --config config.yaml
shasum -a 256 data/staged/*.parquet
uv run python - <<'EOF'
import polars as pl

parent = pl.read_parquet("data/staged/qcew_state_parent.parquet")
child = pl.read_parquet("data/staged/qcew_monthly.parquet").filter(pl.col("area_type") == "state")
print("parent rows", parent.height, "months", parent["reference_month"].n_unique())
joined = child.join(parent, on=["state_fips", "reference_month"], how="left", suffix="_parent")
print("state rows with no parent row", joined.filter(pl.col("industry_code_parent").is_null()).height)
bounded = joined.filter(
    (pl.col("observation_status") == "suppressed")
    & pl.col("observation_status_parent").is_in(["observed", "true_zero"])
)
print("suppressed state months with a published parent", bounded.height)
print("CBP vintages", pl.read_parquet("data/staged/cbp_state_size.parquet")["naics_vintage"].unique().to_list())
EOF
```

Expected: `qcew_monthly`, `qcew_national_size` and `bridge` digests unchanged against `/tmp/staged-before-plan15.sha256`; `cbp_state_size` changed (`D-114`); `qcew_state_parent` new. Then `parent rows 4764 months 96`, `state rows with no parent row 0`, `suppressed state months with a published parent 756` (Task 1's figure), `CBP vintages ['NAICS 2017']`.

- [x] **Step 9: Move the acceptance pin to the new run id**

In `tests/integration/test_stage4_acceptance.py`, replace `test_the_shipped_config_still_resolves_to_the_stage_4_acceptance_run` with:

```python
@requires_staged
def test_the_shipped_config_resolves_to_the_parent_margin_comparand_run():
    """V1: the sharpest single check that no config field and no staged input changed unnoticed.

    `run_id` hashes `resolved_dict(cfg)` — the whole pydantic model — and the input digests. This
    cannot use the `staged_repo` fixture: that rewrites every `storage.*_uri` into a tmp path and
    copies the smaller fixture parquets, so both halves of the payload differ by construction. It
    needs the real `config.yaml` and the real staged layer.

    MOVED ONCE, deliberately, by plan 15 Task 4: the fifth staged table (`qcew_state_parent`) and
    `D-114`'s rewrite of `cbp_state_size.parquet` re-id every run. The previous pin, `f03023ac9f3a`,
    is Stage 4's acceptance run; it stays on disk as the comparand plan 15 Task 9 measures against.
    """
    cfg = load_config(REPO / "config.yaml")
    assert run_id(cfg, _input_digests(cfg)) == "PLAN15_RUN_ID"
```

then substitute the derived id for the token:

```bash
NEW_ID=$(uv run python -c "from pathlib import Path; from logging_employment.cli import _input_digests; from logging_employment.config import load_config; from logging_employment.runs import run_id; cfg = load_config(Path('config.yaml')); print(run_id(cfg, _input_digests(cfg)))")
echo "$NEW_ID"
sed -i '' "s/PLAN15_RUN_ID/$NEW_ID/" tests/integration/test_stage4_acceptance.py
grep -c "$NEW_ID" tests/integration/test_stage4_acceptance.py
```

Expected: a 12-character hex id that is not `f03023ac9f3a`, and a count of `1`.

- [x] **Step 10: Run the gates**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; suite **+6 passed** (parser 1, contracts 2 net, build 3), 0 failed. The renamed contracts test and the moved pin are rewrites, not additions.

- [x] **Step 11: Commit**

```bash
git add src/logging_employment/ingest/qcew.py src/logging_employment/contracts.py src/logging_employment/build.py tests/fixtures/qcew/slice_113_2017q1.csv tests/fixtures/qcew/README.md tests/fixtures/baselines/qcew_state_parent.parquet tests/fixtures/constraints/qcew_state_parent.parquet tests/fixtures/national_size_margin/qcew_state_parent.parquet tests/integration/conftest.py tests/unit/test_qcew_parser.py tests/unit/test_contracts.py tests/integration/test_build_harmonized.py tests/integration/test_stage4_acceptance.py tests/fixtures/national_size_margin/README.md tests/integration/test_national_size_margin_golden.py tests/integration/test_constraint_cli.py tests/integration/test_baseline_golden.py
git commit -m "feat(harmonize): stage the private 113 state series as qcew_state_parent (R-PM-1)"
```

---

### Task 5: Accept a MILP bound only at zero relative gap (`D-093`)

**Implements:** R-PM-6; `D-093`; the gap half of §4 done-when 3. Decision 7 records why this is the answer and why it moves no D1 bound.

**Files:**
- Modify: `src/logging_employment/constraints/bounds.py` (`configured_highs`)
- Test: `tests/unit/test_constraint_bounds.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: every `configured_highs(config)` instance carries `mip_rel_gap = 0.0`.

- [x] **Step 1: Write the failing tests**

In `tests/unit/test_constraint_bounds.py`, add `import highspy` and `import numpy as np` to the third-party imports in sorted order, and append:

```python
def test_every_solver_accepts_a_milp_answer_only_at_zero_relative_gap() -> None:
    """D-093: §9.1's L and U are exact optima, and HiGHS's default `mip_rel_gap` is 1e-4.

    At the default a minimum may stop up to 1e-4 of its own magnitude above the true optimum --
    about four employees at the national total -- and still report `kOptimal`, which `_optimize`
    accepts. At zero relative gap the only slack left is `mip_abs_gap`, whose 1e-6 default is below
    the unit step of an integer objective.
    """
    model = bounds.configured_highs(load_config(REPO / "config.yaml").constraints)
    _, relative = model.getOptionValue("mip_rel_gap")
    _, absolute = model.getOptionValue("mip_abs_gap")
    assert relative == 0.0
    assert absolute < 1.0


def test_a_milp_minimum_is_the_true_optimum_not_one_inside_the_default_gap() -> None:
    """D-093, reproduced: four integer columns at employment magnitudes and two equality rows.

    Under HiGHS's default `mip_rel_gap` of 1e-4 this minimum stops at 30,528 and still reports
    `kOptimal`; the true optimum is 30,526. A seeded search found the model while plan 15 was
    written, and the model itself is the witness. The assertion is the exact optimum, which stays
    right whatever a later HiGHS does with the default.
    """
    model = bounds.configured_highs(load_config(REPO / "config.yaml").constraints)
    model.addVars(
        4,
        np.array([30526.0, 41059.0, 30922.0, 35067.0]),
        np.array([34113.0, 43223.0, 31221.0, 38993.0]),
    )
    for columns, values, rhs in (
        ([0, 1, 3], [2.0, 13.0, 7.0], 870253.0),
        ([0, 1, 2, 3], [1.0, 7.0, 13.0, 13.0], 1214441.0),
    ):
        model.addRow(rhs, rhs, len(columns), np.array(columns, dtype=np.int32), np.array(values))
    model.changeColsIntegrality(
        4, np.arange(4, dtype=np.int32), np.array([highspy.HighsVarType.kInteger] * 4)
    )
    model.changeColsCost(1, np.array([0], dtype=np.int32), np.array([1.0]))
    model.changeObjectiveSense(highspy.ObjSense.kMinimize)
    model.run()
    assert model.getModelStatus() == highspy.HighsModelStatus.kOptimal
    assert model.getInfo().objective_function_value == pytest.approx(30526.0, abs=1e-6)
```

- [x] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/unit/test_constraint_bounds.py -q -k "zero_relative_gap or true_optimum"`
Expected: `2 failed` — `assert 0.0001 == 0.0`, and the minimum coming back as 30528 up to float noise (`30527.99999999998` when this plan was written) against `30526.0 ± 1.0e-06`.

- [x] **Step 3: Set the gap where every solver is built**

In `src/logging_employment/constraints/bounds.py::configured_highs`, add after the `mip_feasibility_tolerance` line:

```python
    model.setOptionValue("mip_rel_gap", 0.0)
```

and append this paragraph to its docstring:

```
    `mip_rel_gap` is ZERO, not HiGHS's 1e-4 (`D-093`). §9.1 defines each bound as the exact
    optimum, and `_optimize` accepts `kOptimal`, which HiGHS also returns when branch-and-bound
    stops inside the relative gap: `tests/unit/test_constraint_bounds.py` pins a four-column model
    whose default-gap minimum sits two employees above the true one. `mip_abs_gap` keeps its 1e-6
    default, below the unit step of an integer objective, so it cannot accept a non-optimal
    integer. The first D1 models to reach MILP are the parent components under
    `use_milp_when_lp_interval_width_below`, where a one-employee miss is a relative gap of at least
    1/25, so the default could not have bound on them; the option is set for the engine, not for
    that case.
```

- [x] **Step 4: Run the tests and the gates**

```bash
uv run pytest tests/unit/test_constraint_bounds.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; suite **+2 passed**, 0 failed. No D1 bound moves: MILP still runs on 0 components until Task 7 builds the parent rows.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/constraints/bounds.py tests/unit/test_constraint_bounds.py
git commit -m "fix(bounds): accept a MILP bound only at zero relative gap (D-093)"
```

---

### Task 6: Scale a baseline estimate into a finite bound instead of halting on it

**Implements:** Decision 3 (INV-002's per-cell half under finite bounds, via §12.3); the production half of R-PM-7's re-check.

This lands BEFORE the parent rows (Task 7) so no commit on this branch ever ships a `solve-bounds` that `run-baselines` cannot follow.

**Files:**
- Modify: `src/logging_employment/baselines/runner.py` (new `assert_bounds_cover`, `month_bounds`, `leaves_its_interval`, `integer_bounds`; `assert_within_bounds`, `state_total_bounds`'s docstring, `run_baselines`)
- Test: `tests/unit/test_baselines_bounds.py`; Rewrite: `tests/integration/test_baseline_cli.py` (one test)

**Interfaces:**
- Consumes: `reconcile.scaling.scale_into_bounds(anchor, weights, bounds, *, tolerance, max_iterations)` (existing).
- Produces: `runner.assert_bounds_cover(values, bounds, *, cell_ids, estimator_id, reference_month) -> None`; `runner.month_bounds(bounds, *, cell_ids, cells) -> Bounds` (keyed by bare state); `runner.leaves_its_interval(values, bounds, *, tolerance) -> bool`; `runner.integer_bounds(bounds, *, tolerance) -> dict[str, dict[str, int | None]]`. `run_baselines(..., bounds=...)` now reallocates a month §12.2 puts outside an interval and raises `InfeasibleResidualError` (bounds cannot hold the residual), `integerize`'s `ValueError` (the integer cut of the bounds cannot hold the integer total) or `BoundViolationError` (a value escaped after scaling).

- [x] **Step 1: Write the failing tests**

In `tests/unit/test_baselines_bounds.py`, replace the module docstring with:

```python
"""INV-002's per-cell half on the baseline production path (R-S5P-3, then D-111).

The adding-up half has been enforced since Stage 3. The bounds half was not: nothing in
`baselines/` read `deterministic_bounds`, so an estimate above a solved upper bound shipped as
`anchored_and_reconciled`. Since `D-111` a published private `113` parent bounds most suppressed
state cells above, and §12.2's unbounded allocation sits above that parent on almost every month,
so the runner no longer HALTS on a binding bound: it reallocates by §12.3's bounded proportional
scaling. What still halts is a month whose bounds cannot hold its residual, and a value that escapes
its interval after scaling.

No `data/` is touched. The runner is driven on `harmonized_toy`. Its 2023-01 missing set is the
single state '04' against a residual of 50, so one finite upper of 10.0 cannot be scaled into; its
2023-02 missing set is '04' and '06' against 80, split 20/60 by establishments, so a cap of 50 on
'06' binds and '04' takes the remainder.
"""
```

change the imports to:

```python
from logging_employment.baselines.runner import (
    REGISTRY,
    assert_within_bounds,
    run_baselines,
    state_total_bounds,
)
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA
from logging_employment.errors import (
    BoundViolationError,
    ConceptViolationError,
    InfeasibleResidualError,
)
from logging_employment.reconcile.scaling import Bounds
```

replace `test_an_estimate_above_its_solved_upper_bound_halts_the_run` with:

```python
def test_a_bound_its_months_residual_cannot_fit_under_halts_the_run(
    harmonized_toy, appendix_a_config
) -> None:
    """January's only missing cell is capped at 10 against a residual of 50: §12.3 refuses.

    Scaling cannot help a month whose uppers sum below its residual, and §12.3 forbids approximating
    that away, so this still HALTS -- as `InfeasibleResidualError`, not as a decline row.
    """
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config)
    target = _january_cell(unchecked)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (10.0 if cell == target else None) for cell in _cell_ids(unchecked)},
    )
    with pytest.raises(InfeasibleResidualError, match="fall below residual"):
        run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)


def test_an_estimate_above_its_upper_bound_is_scaled_into_it_rather_than_halting(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.3: February's residual of 80 splits 20/60 by establishments; capped at 50, '06' takes 50.

    The cap binds, so the scaling factor rises until the uncapped cell absorbs the rest: '04' goes
    from 20 to 30, the month still sums to its residual, and the integer release honours the cap.
    """
    proportional = [e for e in REGISTRY if e.estimator_id == "establishment_proportional"]
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config, estimators=proportional)
    february = unchecked.filter(pl.col("reference_month") == "2023-02")
    before = dict(zip(february["state_fips"], february["estimate"], strict=True))
    assert before == pytest.approx({"04": 20.0, "06": 60.0})
    capped = february.filter(pl.col("state_fips") == "06")["cell_id"].item()
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (50.0 if cell == capped else None) for cell in _cell_ids(unchecked)},
    )
    checked, _ = run_baselines(
        harmonized_toy, appendix_a_config, estimators=proportional, bounds=bounds
    )
    after = checked.filter(pl.col("reference_month") == "2023-02")
    estimates = dict(zip(after["state_fips"], after["estimate"], strict=True))
    assert estimates == pytest.approx({"04": 30.0, "06": 50.0})
    integers = dict(zip(after["state_fips"], after["estimate_integer"], strict=True))
    assert integers == {"04": 30, "06": 50}


def test_an_upper_a_solver_tolerance_below_an_integer_still_admits_that_integer(
    harmonized_toy, appendix_a_config
) -> None:
    """HiGHS reports an integer bound only to within `feasibility_tolerance`: 49.99999995 is 50.

    `integer_bounds` cuts the release with that tolerance, so '06' may carry 50. The integer check
    must admit what that cut admits, or a bound the solver could not tell from 50 halts the run.
    """
    proportional = [e for e in REGISTRY if e.estimator_id == "establishment_proportional"]
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config, estimators=proportional)
    february = unchecked.filter(pl.col("reference_month") == "2023-02")
    capped = february.filter(pl.col("state_fips") == "06")["cell_id"].item()
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (50.0 - 5e-8 if cell == capped else None) for cell in _cell_ids(unchecked)},
    )
    checked, _ = run_baselines(
        harmonized_toy, appendix_a_config, estimators=proportional, bounds=bounds
    )
    after = checked.filter(pl.col("reference_month") == "2023-02")
    integers = dict(zip(after["state_fips"], after["estimate_integer"], strict=True))
    assert integers == {"04": 30, "06": 50}


def test_a_month_whose_allocation_sits_inside_every_bound_is_left_bit_identical(
    harmonized_toy, appendix_a_config
) -> None:
    """§12.2's fast path survives: a finite upper that does not bind moves nothing, not one bit."""
    unchecked, unchecked_audit = run_baselines(harmonized_toy, appendix_a_config)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper=dict.fromkeys(_cell_ids(unchecked), 1_000_000.0),
    )
    checked, checked_audit = run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    assert_frame_equal(checked, unchecked)
    assert_frame_equal(checked_audit, unchecked_audit)
```

and replace the docstring of `test_the_d1_shape_of_every_upper_null_changes_nothing` with:

```python
    """A cell with no finite upper -- every suppressed state cell before `D-111`, and every one
    without a published private `113` parent after it -- must leave the run bit-identical."""
```

In `tests/integration/test_baseline_cli.py`, delete `from logging_employment.errors import BoundViolationError`, which nothing else in the module uses, and replace `test_a_finite_upper_below_the_estimate_halts_the_production_path` with:

```python
def test_the_production_path_scales_an_estimate_into_a_finite_upper_below_it(staged_repo) -> None:
    """The wiring is not vacuous: the bounds the CLI loads really do reach the estimates.

    Every `selected_upper` this fixture solves is null -- its parent table is empty -- so the
    passing run above cannot distinguish a working check from one whose mapping is keyed wrong and
    matches nothing. Tightening ONE cell's upper below the estimate that cell already received is
    the difference. Since `D-111` that no longer halts the run: §12.3 scales the month into the
    bound, so the run succeeds and the cell's released estimate, float and integer, sits at or
    under the new upper. The estimate is read out of the first run rather than assumed.
    """
    assert (
        runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)]).exit_code
        == 0
    )
    results = pl.read_parquet(
        staged_repo.run_dir / "baseline_results" / "baseline_results.parquet"
    ).filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    row = results.sort(["cell_id", "estimator_id"]).to_dicts()[0]
    bounds_path = staged_repo.run_dir / "deterministic_bounds.parquet"
    bounds = pl.read_parquet(bounds_path)
    assert bounds.filter(pl.col("cell_id") == row["cell_id"]).height == 1
    bounds.with_columns(
        pl.when(pl.col("cell_id") == row["cell_id"])
        .then(pl.lit(row["estimate"] / 2.0))
        .otherwise(pl.col("selected_upper"))
        .alias("selected_upper")
    ).write_parquet(bounds_path)
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code == 0, result.output
    rerun = pl.read_parquet(
        staged_repo.run_dir / "baseline_results" / "baseline_results.parquet"
    ).filter(
        (pl.col("cell_id") == row["cell_id"]) & (pl.col("estimator_id") == row["estimator_id"])
    )
    assert rerun["estimate"].item() <= row["estimate"] / 2.0 < row["estimate"]
    assert rerun["estimate_integer"].item() <= row["estimate"] / 2.0
```

- [x] **Step 2: Run them and watch the new behaviour fail**

Run: `uv run pytest tests/unit/test_baselines_bounds.py tests/integration/test_baseline_cli.py -q`
Expected: `4 failed`. The infeasible test raises `BoundViolationError` where `InfeasibleResidualError` was expected. The scaled test and the solver-tolerance test raise `BoundViolationError` on the unscaled float. The rewritten CLI test fails `assert 1 == 0`, because the second `run-baselines` still halts on `BoundViolationError`. The bit-identical test passes already; it pins the fast path the change must keep.

- [x] **Step 3: Split out the coverage check and add the month helpers**

In `src/logging_employment/baselines/runner.py`, add `import math` above `from collections.abc import Mapping, Sequence`, and change `from ..reconcile.scaling import Bounds` to `from ..reconcile.scaling import Bounds, scale_into_bounds`.

In `state_total_bounds`'s docstring, replace

```
    with no lower bound at all means the solver did not answer for it -- whereas a null upper is
    the documented D1 state on 1,227 of 1,241 cells and `Bounds.upper_of` already reads it as
    positive infinity.
```

with

```
    with no lower bound at all means the solver did not answer for it -- whereas a null upper is
    the state of every suppressed cell no public fact bounds above -- since `D-111`, every one
    without a published private `113` parent -- and `Bounds.upper_of` already reads it as positive
    infinity.
```

Add directly before `assert_within_bounds`:

```python
def assert_bounds_cover(
    values: Mapping[str, float],
    bounds: Bounds,
    *,
    cell_ids: Mapping[str, str],
    estimator_id: str,
    reference_month: str,
) -> None:
    """Refuse a month whose cells have no deterministic bound, before anything is scaled into one.

    Split out of `assert_within_bounds`, which calls it, because §12.3's scaling now runs BETWEEN
    the allocation and that comparison and reads `bounds.lower` by cell. A `Bounds` keyed by bare
    state would otherwise surface as a `KeyError` inside `month_bounds` rather than as this named
    refusal.
    """
    uncovered = sorted(cell for cell in values if cell_ids[cell] not in bounds.lower)
    if uncovered:
        raise ConceptViolationError(
            f"{reference_month}: {estimator_id} has no deterministic bound for "
            f"{[cell_ids[cell] for cell in uncovered]}; INV-002 cannot be checked against a "
            "bound that is absent, and an absent bound is not an unbounded one"
        )


def month_bounds(bounds: Bounds, *, cell_ids: Mapping[str, str], cells: Sequence[str]) -> Bounds:
    """One month's bounds keyed by bare state, the key §12.3's `scale_into_bounds` reads.

    `state_total_bounds` keys by the seven-field `cell_id` because `run_baselines` walks the whole
    window in one call; `scale_into_bounds` and `integerize` see one month's missing set, keyed by
    `anchor.missing_cells`. Projected per month here, so neither convention leaks into the other.
    """
    return Bounds(
        lower={cell: bounds.lower[cell_ids[cell]] for cell in cells},
        upper={cell: bounds.upper.get(cell_ids[cell]) for cell in cells},
    )


def leaves_its_interval(values: Mapping[str, float], bounds: Bounds, *, tolerance: float) -> bool:
    """Whether any value sits outside its own `[L, U]` by more than `tolerance`."""
    return any(
        value < bounds.lower[cell] - tolerance or value > bounds.upper_of(cell) + tolerance
        for cell, value in values.items()
    )


def integer_bounds(bounds: Bounds, *, tolerance: float) -> dict[str, dict[str, int | None]]:
    """A month's float bounds as `integerize`'s integer `lower` and `upper` keywords.

    `tolerance` is the SOLVER's (`constraints.feasibility_tolerance`), not reconciliation's: these
    endpoints came out of HiGHS, which reports an integer optimum such as 17 only to within that
    tolerance, and flooring 16.9999999 would cap a cell one employee below its own bound.
    """
    return {
        "lower": {cell: math.ceil(low - tolerance) for cell, low in bounds.lower.items()},
        "upper": {
            cell: None if high is None else math.floor(high + tolerance)
            for cell, high in bounds.upper.items()
        },
    }
```

In `assert_within_bounds`, replace its inline `uncovered = …` block and the `if uncovered:` raise with:

```python
    assert_bounds_cover(
        values,
        bounds,
        cell_ids=cell_ids,
        estimator_id=estimator_id,
        reference_month=reference_month,
    )
```

and in its docstring replace the paragraph that begins `` `tolerance` is the caller's `` with:

```
    `tolerance` is the caller's. For the float estimate production passes
    `reconciliation.tolerance` rather than `constraints.feasibility_tolerance`.
    `ReconciliationConfig`'s docstring gives the reason: "a bound solved to 1e-7 and a residual
    reconciled to 1e-9 are different obligations", and reusing the solver's number here would let a
    solver tuning change move what counts as a violation. The integer release is the exception and
    gets the solver's number: `integer_bounds` cut it at that tolerance, which admits 50 under an
    upper HiGHS reported as 49.99999995, and a stricter check would refuse what the cut allowed.
```

- [x] **Step 4: Scale where §12.2 leaves an interval**

> Deviation (final review): the runner passed reconciliation's acceptance tolerance as the bisection's stopping rule, so D1 shipped a max residual drift of 9.93e-10 against the 1e-9 gate `reconcile` re-applies. `f4ed4d0` bisects to a double's resolution and refuses a result off its residual; the re-run's drift is 4.547e-13.

In `run_baselines`, replace everything from the first `            if bounds is not None:` after `allocated = allocate(anchor, outcome)` through the end of the `integers = (...)` expression with:

```python
            scoped: Bounds | None = None
            if bounds is not None:
                assert_bounds_cover(
                    allocated,
                    bounds,
                    cell_ids=ids,
                    estimator_id=estimator.estimator_id,
                    reference_month=month,
                )
                scoped = month_bounds(bounds, cell_ids=ids, cells=anchor.missing_cells)
                # §12.3, ONLY WHERE §12.2 LEAVES AN INTERVAL. `allocate` is bounded proportional
                # scaling's no-bound fast path: where no bound binds, lambda = R / sum(q) clips
                # nothing and the two agree exactly, so calling `allocate` first keeps every such
                # month bit-identical while a month a finite upper binds on is scaled into it.
                # Halting here instead, as before `D-111`, would stop every run: measured
                # 2026-09-12, 2,184 of the 6,702 estimates `runs/f03023ac9f3a` shipped on
                # parent-bounded cells sit above the parent, in 850 of 852 estimator-months.
                if leaves_its_interval(
                    allocated, scoped, tolerance=config.reconciliation.tolerance
                ):
                    allocated = scale_into_bounds(
                        anchor,
                        outcome,
                        scoped,
                        tolerance=config.reconciliation.tolerance,
                        max_iterations=config.reconciliation.max_bisection_iterations,
                    )
                assert_within_bounds(
                    allocated,
                    bounds,
                    cell_ids=ids,
                    estimator_id=estimator.estimator_id,
                    reference_month=month,
                    tolerance=config.reconciliation.tolerance,
                    quantity="estimate",
                )
            # The margin the integers must honour is the anchor's residual -- the published
            # quantity being allocated -- so it is taken from the anchor rather than re-derived
            # from the allocation. `allocate` and `scale_into_bounds` both make the values sum to
            # R_t, so the two candidates cannot disagree; naming the anchor is the honest source.
            integer_total = round(anchor.residual)
            integers = (
                integerize(
                    allocated,
                    total=integer_total,
                    **(
                        {}
                        if scoped is None
                        else integer_bounds(
                            scoped, tolerance=config.constraints.feasibility_tolerance
                        )
                    ),
                )
                if config.reconciliation.integerize_release
                else dict.fromkeys(allocated, None)
            )
```

Then replace the `estimate_integer` check further down, from `            if bounds is not None and config.reconciliation.integerize_release:` through the `)` that closes its `assert_within_bounds(` call, with:

```python
            if bounds is not None and config.reconciliation.integerize_release:
                # §12.6's integers are released too. `integerize` is now cut to the month's bounds,
                # so this is defence in depth: checking only the float would leave the number
                # actually published unchecked, which is the half INV-002 names. The tolerance is
                # the one `integer_bounds` cut with -- the solver's -- so the check admits exactly
                # what that cut was allowed to produce.
                assert_within_bounds(
                    {cell: float(value) for cell, value in integers.items() if value is not None},
                    bounds,
                    cell_ids=ids,
                    estimator_id=estimator.estimator_id,
                    reference_month=month,
                    tolerance=config.constraints.feasibility_tolerance,
                    quantity="estimate_integer",
                )
```

In `run_baselines`' docstring, replace the three paragraphs that begin `` `bounds` turns on INV-002's per-cell half``, `Passing the RUN DIRECTORY's` and `Passing MASKED bounds would not leak` with:

```
    `bounds` turns on INV-002's per-cell half, and defaults to `None` -- no bound known, no check --
    for unit tests, which build a `HarmonizedData` with no Stage 2 run behind it. `cli.py` passes
    the run directory's `deterministic_bounds`.

    A month §12.2's allocation keeps inside every interval is left bit-identical. A month it does
    not is reallocated by §12.3's bounded proportional scaling, the method
    `reconciliation.single_margin_method` names, so an estimate is moved INTO its interval rather
    than a run halting on it. Three refusals remain, all raises. `InfeasibleResidualError` when a
    month's bounds cannot hold its residual at all: unreachable on D1, where no month has every
    missing cell bounded above (measured 2026-09-12, at most 7 of 9). `integerize`'s `ValueError`
    when the integer cut of those bounds cannot hold the integer total, which takes a fractional
    bound. And `BoundViolationError` if a value still escapes after scaling, which would be a defect
    here rather than a property of an estimator. §12.6's integers are cut to the same bounds, so the
    number actually published honours the interval too.
```

- [x] **Step 5: Run the tests and the gates**

```bash
uv run pytest tests/unit/test_baselines_bounds.py tests/unit/test_baselines_runner.py tests/integration/test_baseline_cli.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; suite **+3 passed** (four tests replace one; `test_baseline_cli.py`'s halting test is rewritten, not added), 0 failed. D1 cannot tell the difference yet: until Task 7 no state cell has a finite upper, so no production month takes the scaling branch.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/baselines/runner.py tests/unit/test_baselines_bounds.py tests/integration/test_baseline_cli.py
git commit -m "feat(baselines): scale an estimate into a finite bound by §12.3 instead of halting"
```

---

### Task 7: Build the parent cells, the parent-margin rows and their compatibility gate

**Implements:** R-PM-2; §4 done-when 1 and the status half of 3; Decision 2.

**Files:**
- Modify: `src/logging_employment/constraints/cells.py` (`KIND_STATE_PARENT`, new `state_parent_cells`, `build_target_cells`)
- Modify: `src/logging_employment/constraints/rows.py` (new `parent_margin_rows`)
- Modify: `src/logging_employment/constraints/compat.py` (new `assert_parent_margin_compatible`, `run_compatibility_gates`)
- Modify: `src/logging_employment/constraints/system.py` (`build_constraint_system`)
- Test: `tests/unit/test_constraint_builders.py`, `tests/unit/test_constraint_compat.py`, `tests/unit/test_constraint_bounds.py`
- Rewrite: `tests/integration/test_d1_acceptance.py` (two tests), `tests/unit/test_validate_recover.py` (one test), `tests/unit/test_validate_complementary.py` (one test)

**Interfaces:**
- Consumes: `HarmonizedData.qcew_state_parent` (Task 4); `configured_highs`' zero gap (Task 5); the runner's §12.3 scaling (Task 6).
- Produces: `cells.KIND_STATE_PARENT = "state_parent"`; `cells.state_parent_cells(parent: pl.DataFrame, monthly: pl.DataFrame, *, size_concept: str) -> pl.DataFrame`; `rows.parent_margin_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]`, ids `parent_margin|<child cell_id>`; `compat.assert_parent_margin_compatible(monthly: pl.DataFrame, parent: pl.DataFrame) -> dict[str, int]`; `run_compatibility_gates`' report gains a `"parent_margin"` entry.

- [x] **Step 1: Write the failing builder, gate and solve tests**

In `tests/unit/test_constraint_builders.py`, add `import dataclasses` in the standard-library group directly after `from __future__ import annotations`, change the errors import to `from logging_employment.errors import ConceptViolationError, IncompatibleMarginError`, and append:

```python
PARENT_ID = "state_parent|41|2024-03|5|113|NAICS 2022|ALL"
CHILD_ID = "state_total|41|2024-03|5|113310|NAICS 2022|ALL"


def _parent_layer(make_monthly, make_size, *, child_status, parent_status, parent_value):
    """One state-month: a `113310` child and its private `113` parent, in the statuses named."""
    child = {
        "state_fips": "41",
        "area_fips": "41000",
        "observation_status": child_status,
        "employment_value": None if child_status == "suppressed" else 90,
        "disclosure_code": "N" if child_status == "suppressed" else "",
    }
    parent = {
        "state_fips": "41",
        "area_fips": "41000",
        "industry_code": "113",
        "aggregation_level": "55",
        "qtrly_establishments": 12,
        "observation_status": parent_status,
        "employment_value": parent_value,
        "disclosure_code": "N" if parent_status == "suppressed" else "",
    }
    data = HarmonizedData(
        qcew_monthly=make_monthly(child),
        qcew_national_size=make_size(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
        qcew_state_parent=make_monthly(parent),
    )
    return cells.build_target_cells(
        data, industry_code="113310", ownership_code="5", size_concept="march_reference"
    )


def test_a_published_parent_over_a_suppressed_child_becomes_one_cell_and_one_row(
    make_monthly, make_size
) -> None:
    """R-PM-2: `child - parent <= 0`, the parent pinned by its own fixing row, never an rhs literal."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status="suppressed",
        parent_status="observed",
        parent_value=150,
    )
    parents = frame.filter(pl.col("cell_id").str.starts_with("state_parent|"))
    assert parents["cell_id"].to_list() == [PARENT_ID]
    (draft,) = rows.parent_margin_rows(frame)
    assert draft.constraint_id == f"parent_margin|{CHILD_ID}"
    assert (draft.relation, draft.rhs_lower, draft.rhs_upper) == ("le", None, 0.0)
    assert draft.coefficients == ((CHILD_ID, 1.0), (PARENT_ID, -1.0))
    assert draft.is_hard and draft.constraint_class == "public_accounting_fact"
    assert draft.provenance_text.startswith("evidence_kind=published_value; ")
    fixing = {d.constraint_id: d for d in rows.observed_value_rows(frame)}
    assert fixing[f"fix|{PARENT_ID}"].rhs_upper == 150.0


@pytest.mark.parametrize(
    ("child_status", "parent_status", "parent_value"),
    [("observed", "observed", 150), ("suppressed", "suppressed", None)],
)
def test_no_parent_cell_without_both_a_published_parent_and_a_suppressed_child(
    make_monthly, make_size, child_status, parent_status, parent_value
) -> None:
    """A parent over a published child restricts nothing; a suppressed parent publishes nothing."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status=child_status,
        parent_status=parent_status,
        parent_value=parent_value,
    )
    assert frame.filter(pl.col("cell_id").str.starts_with("state_parent|")).is_empty()
    assert rows.parent_margin_rows(frame) == []


def test_the_parent_row_couples_one_state_cell_so_the_national_guard_still_admits_it(
    make_monthly, make_size
) -> None:
    """R-PM-2: SRC-QCEW-006's guard is untouched -- a state cell and its parent are not a state sum."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status="suppressed",
        parent_status="observed",
        parent_value=150,
    )
    drafts = rows.parent_margin_rows(frame)
    kinds = {cid: cid.split("|")[0] for cid in frame["cell_id"].to_list()}
    rows.assert_no_national_employment_margin(drafts, kinds)
    other = "state_total|06|2024-03|5|113310|NAICS 2022|ALL"
    widened = dataclasses.replace(drafts[0], coefficients=(*drafts[0].coefficients, (other, 1.0)))
    with pytest.raises(IncompatibleMarginError):
        rows.assert_no_national_employment_margin([widened], {**kinds, other: "state_total"})
```

Append to `tests/unit/test_constraint_compat.py`:

```python
def _parent_pair(make_monthly, *, child: dict, parent: dict):
    """A `113310` state row and its private `113` parent row in one state-month."""
    at = {"state_fips": "41", "area_fips": "41000"}
    parent_defaults = {
        "industry_code": "113",
        "aggregation_level": "55",
        "qtrly_establishments": 12,
        "employment_value": 200,
    }
    return make_monthly(at | child), make_monthly(at | parent_defaults | parent)


def test_a_published_parent_below_its_published_child_is_refused(make_monthly) -> None:
    """Both published and the parent smaller: `child - parent <= 0` would be infeasible there."""
    monthly, parent = _parent_pair(
        make_monthly, child={"employment_value": 120}, parent={"employment_value": 100}
    )
    with pytest.raises(IncompatibleMarginError, match="below"):
        compat.assert_parent_margin_compatible(monthly, parent)


def test_a_parent_with_fewer_establishments_than_its_child_is_refused(make_monthly) -> None:
    """A NAICS parent holds every establishment of its children, and counts are public."""
    monthly, parent = _parent_pair(
        make_monthly, child={"qtrly_establishments": 10}, parent={"qtrly_establishments": 9}
    )
    with pytest.raises(IncompatibleMarginError, match="fewer establishments"):
        compat.assert_parent_margin_compatible(monthly, parent)


def test_a_parent_published_under_another_vintage_is_refused(make_monthly) -> None:
    monthly, parent = _parent_pair(make_monthly, child={}, parent={"naics_vintage": "NAICS 2017"})
    with pytest.raises(IncompatibleMarginError, match="INV-007"):
        compat.assert_parent_margin_compatible(monthly, parent)


def test_the_parent_gate_reports_what_it_checked(make_monthly) -> None:
    monthly, parent = _parent_pair(
        make_monthly,
        child={
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        parent={},
    )
    assert compat.assert_parent_margin_compatible(monthly, parent) == {
        "parent_pairs_checked": 1,
        "published_pairs_checked": 0,
        "suppressed_cells_with_a_published_parent": 1,
    }
```

Append to `tests/unit/test_constraint_bounds.py`:

```python
def _parent_bounded(make_monthly, make_size, parent_value: int):
    """A suppressed `113310` state cell under a published private `113` parent, built and solved."""
    at = {"state_fips": "41", "area_fips": "41000"}
    data = HarmonizedData(
        qcew_monthly=make_monthly(
            at
            | {"observation_status": "suppressed", "employment_value": None, "disclosure_code": "N"}
        ),
        qcew_national_size=make_size(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
        qcew_state_parent=make_monthly(
            at
            | {
                "industry_code": "113",
                "aggregation_level": "55",
                "qtrly_establishments": 12,
                "employment_value": parent_value,
            }
        ),
    )
    cfg = load_config(REPO / "config.yaml")
    built = graph.assign_components(system.build_constraint_system(data, cfg))
    return bounds.solve_bounds(built, cfg.constraints)


def _state_row(result) -> dict:
    return result.bounds.filter(pl.col("cell_id").str.starts_with("state_total|")).row(
        0, named=True
    )


def test_a_published_parent_bounds_its_suppressed_child_from_above(make_monthly, make_size) -> None:
    """R-PM-2 end to end: `[0, +inf)` becomes `[0, 150]`, in one two-cell component."""
    result = _parent_bounded(make_monthly, make_size, 150)
    child = _state_row(result)
    assert (child["selected_lower"], child["selected_upper"]) == (0.0, 150.0)
    assert child["bound_status"] == "partially_identified"
    assert child["milp_upper"] is None  # width 150 is over the MILP trigger of 25
    assert result.components["cell_count"].to_list() == [2]


def test_a_parent_under_the_milp_width_reaches_the_integer_solve(make_monthly, make_size) -> None:
    """R-PM-6: a finite width under `use_milp_when_lp_interval_width_below` opens `_needs_milp`."""
    child = _state_row(_parent_bounded(make_monthly, make_size, 12))
    assert (child["milp_lower"], child["milp_upper"]) == (0.0, 12.0)
    assert (child["selected_lower"], child["selected_upper"]) == (0.0, 12.0)
```

- [x] **Step 2: Run them and watch them fail**

Run: `uv run pytest tests/unit/test_constraint_builders.py tests/unit/test_constraint_compat.py tests/unit/test_constraint_bounds.py -q`
Expected: `10 failed` — the builders and compat tests on `AttributeError` (`parent_margin_rows`, `assert_parent_margin_compatible`) or an empty parent-cell list, the first solve test on `selected_upper` being `None` (`assert (0.0, None) == (0.0, 150.0)`), the second on the MILP pair (`assert (None, None) == (0.0, 12.0)`).

- [x] **Step 3: Emit the parent cells**

In `src/logging_employment/constraints/cells.py`, add `KIND_STATE_PARENT = "state_parent"` directly below `KIND_NATIONAL_SIZE = "national_size"`, add this function directly below `national_size_cells`:

```python
def state_parent_cells(
    parent: pl.DataFrame, monthly: pl.DataFrame, *, size_concept: str
) -> pl.DataFrame:
    """One cell per published private `113` state-month whose `113310` child is suppressed (R-PM-2).

    Only those. A parent over a PUBLISHED child restricts nothing that child's own fixing row has
    not already pinned, and a SUPPRESSED parent publishes no value to bound anything with, so a cell
    for either adds a variable and no information -- the reason `national_total_cells` emits only
    the months a size margin needs. The parent is an observed cell: INV-001 pins it through its own
    `fix|` row, and `rows.parent_margin_rows` never lifts its value into a right-hand side.
    """
    suppressed = monthly.filter(
        (pl.col("area_type") == "state") & (pl.col("observation_status") == "suppressed")
    ).select("state_fips", "reference_month")
    rows = (
        parent.filter(
            (pl.col("area_type") == "state")
            & pl.col("observation_status").is_in(["observed", "true_zero"])
        )
        .join(suppressed, on=["state_fips", "reference_month"], how="semi")
        .with_columns(pl.lit(TOTAL_SIZE_CLASS).alias("size_class"))
    )
    return _select(rows, KIND_STATE_PARENT, size_concept, "employment_value")
```

and in `build_target_cells`, add `_assert_one_vintage_per_cell(data.qcew_state_parent)` directly after `_assert_one_vintage_per_cell(data.qcew_monthly)`, and add this as the last element of the `pl.concat([...])` list:

```python
            state_parent_cells(
                data.qcew_state_parent, data.qcew_monthly, size_concept=size_concept
            ),
```

- [x] **Step 4: Build one `parent_margin` row per parent cell**

In `src/logging_employment/constraints/rows.py`, add `KIND_STATE_PARENT,` to the `from .cells import (...)` block, between `KIND_NATIONAL_TOTAL,` and `KIND_STATE_TOTAL,` and add this function directly after `size_support_rows`:

```python
def parent_margin_rows(cells_frame: pl.DataFrame) -> list[ConstraintDraft]:
    """`child - parent <= 0` for every published private `113` parent over a suppressed child.

    §9.3's parent-total constraint (`specs/stage5-parent-margin.md` R-PM-2). Forestry and Logging
    `113` is `1131 + 1132 + 1133`, and `1133 -> 11331 -> 113310` is single-child, so with both
    siblings nonnegative `113310 <= 113` in the same state, month and ownership. Written with the
    parent as a CELL pinned by its own fixing row, rather than as `child <= <number>`, for the
    reason `size_margin_rows` gives: a number lifted into a right-hand side is a value no INV-001
    row pins and no audit can trace.

    A `published_value` restriction, not an `assumed_threshold`: both cells are published QCEW
    facts and the hierarchy is NAICS's own. It couples exactly one `state_total` cell to one
    `state_parent` cell of the same state-month, so `assert_no_national_employment_margin` --
    SRC-QCEW-006's guard against state sums -- admits it and still refuses everything it refused.
    """
    children = {
        (cell["state_fips"], cell["reference_month"]): cell
        for cell in cells_frame.filter(
            pl.col("cell_id").str.starts_with(f"{KIND_STATE_TOTAL}|")
        ).iter_rows(named=True)
    }
    drafts: list[ConstraintDraft] = []
    for parent in cells_frame.filter(
        pl.col("cell_id").str.starts_with(f"{KIND_STATE_PARENT}|")
    ).iter_rows(named=True):
        child = children.get((parent["state_fips"], parent["reference_month"]))
        if child is None or child["observation_status"] != "suppressed":
            raise ConceptViolationError(
                f"{parent['cell_id']} has no suppressed state_total cell in its state-month; "
                "`cells.state_parent_cells` emits a parent only over one, so this is a builder defect"
            )
        drafts.append(
            constraint(
                constraint_id=f"parent_margin|{child['cell_id']}",
                constraint_class="public_accounting_fact",
                relation="le",
                coefficients=((str(child["cell_id"]), 1.0), (str(parent["cell_id"]), -1.0)),
                rhs_lower=None,
                rhs_upper=0.0,
                is_hard=True,
                evidence_kind="published_value",
                source_snapshot_ids=",".join(
                    sorted({str(child["source_snapshot_id"]), str(parent["source_snapshot_id"])})
                ),
                provenance_text=(
                    f"published private 113 employment {parent['observed_value']} bounds 113310 "
                    f"above in {parent['state_fips']} {parent['reference_month']}: 113 = 1131 + "
                    "1132 + 1133, 1133 -> 11331 -> 113310 is single-child, and both siblings are "
                    "nonnegative"
                ),
                vintage_compatibility_status=vintage_status(
                    [str(child["naics_vintage"]), str(parent["naics_vintage"])]
                ),
                **_scope(child),
            )
        )
    return drafts
```

- [x] **Step 5: Gate the pair before any row exists, and wire the builder in**

In `src/logging_employment/constraints/compat.py`, add directly before `run_compatibility_gates`:

```python
def assert_parent_margin_compatible(monthly: pl.DataFrame, parent: pl.DataFrame) -> dict[str, int]:
    """Halt unless every private `113` state row can bound its `113310` child (§5.5, R-PM-2).

    Checked over EVERY state-month the two tables share, not only the suppressed ones a row is built
    for, because the published pairs are where the premise is testable. Three conditions: the pair
    shares ownership and NAICS vintage (INV-007); the parent holds at least as many establishments
    as the child (the NAICS hierarchy, public even where employment is suppressed); and where both
    employment values are published the parent is not below the child. The last is what the row
    asserts, and a pair violating it would otherwise surface as an infeasible component with a far
    less specific message. Measured 2026-09-12 on the audit extracts: 0 of 3,078 published
    month-value pairs put the child above the parent.
    """
    child = monthly.filter(pl.col("area_type") == "state").select(
        "state_fips",
        "reference_month",
        "ownership_code",
        "naics_vintage",
        pl.col("qtrly_establishments").alias("child_establishments"),
        pl.col("employment_value").alias("child_employment"),
        pl.col("observation_status").alias("child_status"),
    )
    pairs = (
        parent.filter(pl.col("area_type") == "state")
        .select(
            "state_fips",
            "reference_month",
            pl.col("ownership_code").alias("parent_ownership"),
            pl.col("naics_vintage").alias("parent_vintage"),
            pl.col("qtrly_establishments").alias("parent_establishments"),
            pl.col("employment_value").alias("parent_employment"),
            pl.col("observation_status").alias("parent_status"),
        )
        .join(child, on=["state_fips", "reference_month"], how="inner")
    )

    misaligned = pairs.filter(
        pl.col("parent_ownership").ne_missing(pl.col("ownership_code"))
        | pl.col("parent_vintage").ne_missing(pl.col("naics_vintage"))
    )
    if misaligned.height:
        first = misaligned.row(0, named=True)
        raise IncompatibleMarginError(
            f"{misaligned.height} parent row(s) differ from their child in ownership or NAICS "
            f"vintage, e.g. {first['state_fips']} {first['reference_month']}: "
            f"{first['parent_ownership']}/{first['parent_vintage']} against "
            f"{first['ownership_code']}/{first['naics_vintage']} (INV-007)"
        )

    # `is_null() |` first, as in the size gates: a null count makes `<` null, `filter` drops a null
    # predicate, and a pair with no establishment count would pass the check that exists to halt it.
    fewer = pairs.filter(
        pl.col("parent_establishments").is_null()
        | pl.col("child_establishments").is_null()
        | (pl.col("parent_establishments") < pl.col("child_establishments"))
    )
    if fewer.height:
        first = fewer.row(0, named=True)
        raise IncompatibleMarginError(
            f"{fewer.height} parent row(s) carry fewer establishments than their child, or no count, "
            f"e.g. {first['state_fips']} {first['reference_month']}: "
            f"{first['parent_establishments']} against {first['child_establishments']}; a NAICS "
            "parent holds every establishment of its children"
        )

    published = pairs.filter(
        (pl.col("child_status") != "suppressed") & (pl.col("parent_status") != "suppressed")
    )
    below = published.filter(pl.col("parent_employment") < pl.col("child_employment"))
    if below.height:
        first = below.row(0, named=True)
        raise IncompatibleMarginError(
            f"{below.height} published parent value(s) sit below their published child, e.g. "
            f"{first['state_fips']} {first['reference_month']}: {first['parent_employment']} "
            f"against {first['child_employment']}; `child - parent <= 0` would make that "
            "component infeasible"
        )
    bounding = pairs.filter(
        (pl.col("child_status") == "suppressed") & (pl.col("parent_status") != "suppressed")
    )
    return {
        "parent_pairs_checked": pairs.height,
        "published_pairs_checked": published.height,
        "suppressed_cells_with_a_published_parent": bounding.height,
    }
```

and replace `run_compatibility_gates` with:

```python
def run_compatibility_gates(data: HarmonizedData, *, industry_code: str) -> dict[str, object]:
    """Every gate, in the order a constraint builder needs them. Returns the margin report."""
    assert_definitional_alignment(data.qcew_monthly)
    size = data.qcew_national_size.filter(pl.col("industry_code") == industry_code)
    report = assert_size_margin_compatible(data.qcew_monthly, size)
    return {
        **report,
        "parent_margin": assert_parent_margin_compatible(data.qcew_monthly, data.qcew_state_parent),
    }
```

In `src/logging_employment/constraints/system.py::build_constraint_system`, add `*rows_module.parent_margin_rows(cell_frame),` as the last element of the `drafts` list.

- [x] **Step 6: Run the new tests green**

Run: `uv run pytest tests/unit/test_constraint_builders.py tests/unit/test_constraint_compat.py tests/unit/test_constraint_bounds.py tests/unit/test_constraint_system.py -q`
Expected: all pass, 10 more than before Step 1.

- [x] **Step 7: Rewrite the four D1 assertions `D-111` falsifies, as derived invariants**

> Deviation: a fifth D1 assertion also fell and is rewritten here: `test_each_size_margin_month_is_one_component_holding_that_month_s_national_cells` selected national cells as `_KIND != "state_total"`, which took in Task 7's `state_parent` kind (`{5, ..., 11} == {1}`). It now names `national_total` and `national_size` and derives the parent side from the component decomposition, not from a cell count; mutation-checked, then Step 8's suite matched (1519).

In `tests/integration/test_d1_acceptance.py`, in `test_every_suppressed_state_month_carries_a_bound_status`, append to the docstring:

```
    Since `D-111` the endpoints split on one public fact. A suppressed state cell whose private
    `113` parent is published is bounded above by exactly that value; every other suppressed state
    cell is still `unbounded`. The split is read from the STAGED parent table, never typed --
    measured 2026-09-12 it is 756 bounded and 471 open.
```

and replace its last two statements (`assert covered.filter(pl.col("selected_upper").is_not_null()).is_empty()` and `assert set(covered["bound_status"]) == {"unbounded"}`) with:

```python
    published_parent = (
        pl.read_parquet(STAGED / "qcew_state_parent.parquet")
        .filter(pl.col("observation_status").is_in(["observed", "true_zero"]))
        .select(
            "state_fips",
            "reference_month",
            pl.col("employment_value").cast(pl.Float64).alias("parent_value"),
        )
    )
    located = covered.join(
        suppressed.select("cell_id", "state_fips", "reference_month"), on="cell_id", how="inner"
    ).join(published_parent, on=["state_fips", "reference_month"], how="left")
    bounded = located.filter(pl.col("parent_value").is_not_null())
    open_above = located.filter(pl.col("parent_value").is_null())
    assert bounded.height > 0 and open_above.height > 0
    off_parent = bounded.filter(
        pl.col("selected_upper").is_null()
        | ((pl.col("selected_upper") - pl.col("parent_value")).abs() > 1e-6)
    )
    assert off_parent.is_empty(), sorted(off_parent["cell_id"].to_list())[:3]
    assert bounded.filter(
        (pl.col("bound_status") == "exactly_recoverable") != (pl.col("parent_value") == 0.0)
    ).is_empty()
    assert set(bounded["bound_status"]) <= {"partially_identified", "exactly_recoverable"}
    assert open_above.filter(pl.col("selected_upper").is_not_null()).is_empty()
    assert set(open_above["bound_status"]) == {"unbounded"}
```

Replace `test_no_coupling_row_touches_a_state_cell_so_each_state_cell_is_its_own_component` with:

```python
def test_the_only_rows_coupling_a_state_cell_are_parent_margins_within_one_state_month(
    solved,
) -> None:
    """SRC-QCEW-006 came back `decline`, so no row couples a state cell to another state or the nation.

    Since `D-111` exactly one kind of row couples a state cell to anything: `parent_margin`, which
    pairs one suppressed `state_total` cell with the `state_parent` cell of the same state and month.
    So a state cell's component holds one cell, or two when its parent is published -- counted from
    the cell index, never typed. `rows.assert_no_national_employment_margin` enforces the decline;
    the decomposition is where it shows up.
    """
    built, result, _ = solved
    coupled = built.coefficients.join(
        _coupling_rows(built), on="constraint_id", how="semi"
    ).with_columns(_KIND.alias("kind"))
    touching = sorted(
        set(coupled.filter(pl.col("kind") == "state_total")["constraint_id"].to_list())
    )
    assert {identifier.split("|")[0] for identifier in touching} == {"parent_margin"}
    per_row = (
        coupled.filter(pl.col("constraint_id").is_in(touching))
        .with_columns(
            pl.col("cell_id").str.split("|").list.get(1).alias("state"),
            pl.col("cell_id").str.split("|").list.get(2).alias("month"),
        )
        .group_by("constraint_id")
        .agg(
            pl.len().alias("cells"),
            pl.col("kind").sort().str.join(",").alias("kinds"),
            pl.col("state").n_unique().alias("states"),
            pl.col("month").n_unique().alias("months"),
        )
    )
    assert per_row.filter(
        (pl.col("cells") != 2) | (pl.col("states") != 1) | (pl.col("months") != 1)
    ).is_empty()
    assert set(per_row["kinds"].to_list()) == {"state_parent,state_total"}

    parents = built.cells.filter(_KIND == "state_parent")
    membership = graph.component_membership(built)
    state_cells = built.cells.filter(_KIND == "state_total").select("cell_id")
    state_components = membership.join(state_cells, on="cell_id", how="semi").join(
        result.components.select("component_id", "cell_count"), on="component_id", how="left"
    )
    assert state_components.height == state_cells.height
    assert set(state_components["cell_count"].to_list()) == {1, 2}
    assert state_components.filter(pl.col("cell_count") == 2).height == parents.height
    assert parents.height == len(touching)
    assert (
        result.components.filter(pl.col("cell_count") == 1).height
        == state_cells.height - parents.height
    )
```

In `tests/unit/test_validate_recover.py`, replace `test_a_masked_state_total_is_unbounded_and_the_hash_moves` with:

```python
def test_a_masked_state_total_is_bounded_by_its_published_parent_and_the_hash_moves():
    """Oregon 2019-06: a published `113` parent with other establishments bounds the masked cell.

    Before `D-111` this was a scoped negative -- every state cell a single-cell component and the
    masked cell `[0, +inf)`. The parent's value and its establishment count are read off the staged
    tables, never typed; the precondition that it has other establishments is what keeps it public
    under §13.2 step 4's rule once plan 15 Task 8 lands.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    base = mask_and_solve(data, [], cfg)
    masked = mask_and_solve(data, [MaskTarget("41", "2019-06", "state_total", "primary_like")], cfg)
    at = (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    parent = data.qcew_state_parent.filter(at).row(0, named=True)
    child = data.qcew_monthly.filter(at & (pl.col("area_type") == "state")).row(0, named=True)
    assert parent["observation_status"] == "observed"
    assert parent["qtrly_establishments"] > child["qtrly_establishments"]
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"
    row = masked.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
    assert row["bound_status"] == "partially_identified"
    assert row["selected_lower"] == 0.0
    assert row["selected_upper"] == float(parent["employment_value"])
    assert masked.constraint_set_hash != base.constraint_set_hash
    assert not is_exactly_recoverable(masked.bounds, cell)
```

In `tests/unit/test_validate_complementary.py`, replace `test_a_complementary_mask_changes_nothing_about_state_total_identification` with:

```python
def test_a_complementary_mask_changes_nothing_about_state_total_identification():
    """The scoped negative, pinned. Complementary masking is inert on this arm — by construction.

    Partners are other states in the target's month, and no row couples two state cells, so the
    target's interval is the same with and without them. Since `D-111` that interval is the target's
    own parent bound rather than `[0, +inf)`: the invariant is the equality, not the label. If this
    test ever fails, a row coupling two state cells has appeared and SRC-QCEW-006's `decline` has
    been overturned somewhere. That is a finding, not a flake.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    partners = complementary_partners(data.qcew_monthly, target, n=2, seed=1024)
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"
    columns = ["selected_lower", "selected_upper", "bound_status"]

    alone = mask_and_solve(data, [target], cfg)
    with_partners = mask_and_solve(data, [target, *partners], cfg)
    intervals = [
        system.bounds.filter(pl.col("cell_id") == cell).select(columns).row(0)
        for system in (alone, with_partners)
    ]
    assert intervals[0] == intervals[1]
    assert intervals[0][1] is not None
```

- [x] **Step 8: Run the gates**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; suite **+10 passed**, 0 failed. Four data-bound tests were rewritten in Step 7 and pass against the staged layer: they are the D1 witnesses of done-when 1 and the status half of done-when 3. `test_the_rank_cache_computes_once_per_shape_rather_than_once_per_component` needs no change: its ceiling counts coupled components, and every parent component has one shape.

- [x] **Step 9: Commit**

```bash
git add src/logging_employment/constraints/cells.py src/logging_employment/constraints/rows.py src/logging_employment/constraints/compat.py src/logging_employment/constraints/system.py tests/unit/test_constraint_builders.py tests/unit/test_constraint_compat.py tests/unit/test_constraint_bounds.py tests/integration/test_d1_acceptance.py tests/unit/test_validate_recover.py tests/unit/test_validate_complementary.py
git commit -m "feat(constraints): bound suppressed state cells by their published 113 parent (R-PM-2)"
```

---

### Task 8: Decide the parent's visibility under the mask, enforce §13.5 and §13.2 step 6, and rule `D-087`

**Implements:** R-PM-3 (steps 4 and 6, §13.5's out-of-bounds rule on the state-total arm, `D-087` settled in the same pass); §4 done-when 2; Decisions 4, 5 and 6.

**Files:**
- Modify: `src/logging_employment/errors.py` (new `ConstraintDataError`)
- Modify: `src/logging_employment/validate/mask.py` (new `parents_to_hide`, `_hide`; `apply_mask`)
- Modify: `src/logging_employment/validate/leakage.py` (`assert_no_retained_truth`)
- Modify: `src/logging_employment/validate/recover.py` (`MaskedSystem.recoverable`, new `_no_recoverable`, `locate_withheld`, `assert_truth_within_bounds`, `exactly_recoverable`; `mask_and_solve`)
- Modify: `src/logging_employment/validate/harness.py` (bounds into `run_baselines`, new `reject_exactly_recoverable`, the per-regime counter)
- Modify: `src/logging_employment/baselines/runner.py` (`run_baselines`' docstring names the harness as its second caller)
- Create: `tests/unit/test_validate_parent_mask.py`
- Modify: `tests/integration/test_stage4_acceptance.py` (the `D-087` wiring test)

**Interfaces:**
- Consumes: `HarmonizedData.qcew_state_parent` (Task 4); `runner.state_total_bounds` and the runner's scaling (Task 6); the parent rows (Task 7).
- Produces: `mask.parents_to_hide(parent: pl.DataFrame, chosen: pl.DataFrame) -> pl.DataFrame` (sorted `state_fips`, `reference_month` keys); `apply_mask` also returns a masked `qcew_state_parent`; `errors.ConstraintDataError`; `recover.locate_withheld(truth, cells, bounds) -> pl.DataFrame`; `recover.assert_truth_within_bounds(located, *, tolerance: float) -> None`; `recover.exactly_recoverable(located) -> pl.DataFrame`; `MaskedSystem.recoverable: pl.DataFrame`; `harness.reject_exactly_recoverable(scored, recoverable) -> tuple[pl.DataFrame, int]`; each regime's manifest entry gains `rejected_exactly_recoverable: int`.

- [x] **Step 1: Write the failing tests**

Create `tests/unit/test_validate_parent_mask.py`:

```python
"""§13.2 steps 4 and 6 and §13.5 for the §9.3 parent margin (R-PM-3).

No `data/`. Every test builds a one-month layer with three published states and their private `113`
parents. '01' has two establishments besides its `113310` child, so its parent stays public under a
mask; '02' has none, so its parent equals the child and must be hidden with it; '06' is never masked.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConstraintDataError, LeakageError
from logging_employment.validate.harness import reject_exactly_recoverable
from logging_employment.validate.leakage import assert_no_retained_truth
from logging_employment.validate.mask import MaskTarget, apply_mask
from logging_employment.validate.recover import assert_truth_within_bounds, mask_and_solve

REPO = Path(__file__).resolve().parents[2]
MONTH = "2024-03"


def _layer(make_monthly, make_size, *, value_01: int = 100, parent_01: int = 150) -> HarmonizedData:
    """Three published states and the nation in one month, each state under a private `113` parent."""
    at = {"reference_month": MONTH}
    states = (("01", value_01, 10), ("02", 50, 5), ("06", 250, 15))
    national = {
        "area_type": "national",
        "area_fips": "US000",
        "state_fips": None,
        "aggregation_level": "18",
        "employment_value": sum(value for _, value, _ in states),
        "employment_raw": str(sum(value for _, value, _ in states)),
        "qtrly_establishments": sum(count for _, _, count in states),
    }
    monthly = make_monthly(
        at | national,
        *[
            at
            | {
                "state_fips": state,
                "area_fips": f"{state}000",
                "employment_value": value,
                "employment_raw": str(value),
                "qtrly_establishments": count,
            }
            for state, value, count in states
        ],
    )
    parents = (("01", parent_01, 12), ("02", 50, 5), ("06", 300, 18))
    parent = make_monthly(
        *[
            at
            | {
                "state_fips": state,
                "area_fips": f"{state}000",
                "industry_code": "113",
                "aggregation_level": "55",
                "employment_value": value,
                "employment_raw": str(value),
                "qtrly_establishments": count,
            }
            for state, value, count in parents
        ]
    )
    return HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=make_size(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
        qcew_state_parent=parent,
    )


def _target(state: str, label: str = "primary_like") -> MaskTarget:
    return MaskTarget(state, MONTH, "state_total", label)


def test_a_parent_with_other_establishments_stays_published_under_the_mask(make_monthly, make_size):
    """Step 4: '01''s parent is public in reality and stays public, as on 252 of 409 real cases."""
    data = _layer(make_monthly, make_size)
    masked, _ = apply_mask(data, [_target("01")])
    assert masked.qcew_state_parent.equals(data.qcew_state_parent)


def test_a_parent_whose_establishments_are_all_the_masked_cells_is_hidden_with_it(
    make_monthly, make_size
):
    """Step 4: '02''s parent equals the withheld value, so leaving it public would hand it back."""
    data = _layer(make_monthly, make_size)
    masked, truth = apply_mask(data, [_target("02")])
    parent = data.qcew_state_parent.filter(pl.col("state_fips") == "02")
    assert parent["employment_value"].item() == truth["truth"].item()
    hidden = masked.qcew_state_parent.filter(pl.col("state_fips") == "02").row(0, named=True)
    assert hidden["observation_status"] == "suppressed"
    assert hidden["employment_value"] is None
    assert hidden["disclosure_code"] == "N"
    assert hidden["suppression_type"] == "complementary_like"
    others = pl.col("state_fips") != "02"
    assert masked.qcew_state_parent.filter(others).equals(data.qcew_state_parent.filter(others))


def test_the_leakage_guard_refuses_a_masked_layer_that_left_such_a_parent_published(
    make_monthly, make_size
):
    """§13.4 bullet 2: the guard re-applies the rule, so a mask that skipped it cannot pass."""
    data = _layer(make_monthly, make_size)
    masked, truth = apply_mask(data, [_target("02")])
    assert_no_retained_truth(masked, truth)
    leaky = dataclasses.replace(masked, qcew_state_parent=data.qcew_state_parent)
    with pytest.raises(LeakageError, match="02/2024-03"):
        assert_no_retained_truth(leaky, truth)


def test_a_masked_cell_is_bounded_by_its_visible_parent_and_not_by_a_hidden_one(
    make_monthly, make_size
):
    """Steps 4-5: '01' comes back `[0, 150]`; '02', its parent hidden with it, stays `unbounded`."""
    system = mask_and_solve(
        _layer(make_monthly, make_size),
        [_target("01"), _target("02", "complementary_like")],
        load_config(REPO / "config.yaml"),
    )
    state = {
        row["cell_id"].split("|")[1]: row
        for row in system.bounds.filter(
            pl.col("cell_id").str.starts_with("state_total|")
        ).iter_rows(named=True)
    }
    assert (state["01"]["selected_lower"], state["01"]["selected_upper"]) == (0.0, 150.0)
    assert state["02"]["bound_status"] == "unbounded"
    assert system.recoverable.is_empty()


def test_a_target_its_visible_parent_pins_is_returned_for_rejection(make_monthly, make_size):
    """Step 6: a parent published at 0 with other establishments pins its child to exactly 0."""
    system = mask_and_solve(
        _layer(make_monthly, make_size, value_01=0, parent_01=0),
        [_target("01")],
        load_config(REPO / "config.yaml"),
    )
    assert system.recoverable.rows() == [("01", MONTH)]


def test_a_truth_above_its_visible_parent_halts_mask_and_solve(make_monthly, make_size):
    """§13.5 through `mask_and_solve`: the check runs on every masked solve, not only when called.

    '01' is withheld at 200 under a published parent of 150, so its masked bound `[0, 150]`
    excludes the truth. The direct tests below pin what `assert_truth_within_bounds` refuses; this
    one pins that `mask_and_solve` calls it.
    """
    data = _layer(make_monthly, make_size, value_01=200, parent_01=150)
    with pytest.raises(ConstraintDataError, match="outside their masked deterministic bounds"):
        mask_and_solve(data, [_target("01")], load_config(REPO / "config.yaml"))


def _located(truth: int, lower: float | None, upper: float | None) -> pl.DataFrame:
    """One withheld cell beside its masked bounds, in the shape `locate_withheld` returns."""
    found = lower is not None
    return pl.DataFrame(
        {
            "state_fips": ["01"],
            "reference_month": [MONTH],
            "truth": [truth],
            "cell_id": ["state_total|01|2024-03|5|113310|NAICS 2022|ALL" if found else None],
            "selected_lower": [lower],
            "selected_upper": [upper],
            "bound_status": ["partially_identified" if found else None],
        },
        schema={
            "state_fips": pl.String,
            "reference_month": pl.String,
            "truth": pl.Int64,
            "cell_id": pl.String,
            "selected_lower": pl.Float64,
            "selected_upper": pl.Float64,
            "bound_status": pl.String,
        },
    )


def test_a_withheld_truth_outside_its_masked_bounds_halts_the_run():
    """§13.5: a known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug."""
    assert_truth_within_bounds(_located(150, 0.0, 150.0), tolerance=1e-7)
    assert_truth_within_bounds(_located(9_999, 0.0, None), tolerance=1e-7)
    with pytest.raises(ConstraintDataError, match="outside their masked deterministic bounds"):
        assert_truth_within_bounds(_located(151, 0.0, 150.0), tolerance=1e-7)


def test_a_withheld_cell_with_no_masked_bound_halts_rather_than_passing_unchecked():
    with pytest.raises(ConstraintDataError, match="no masked bound"):
        assert_truth_within_bounds(_located(10, None, None), tolerance=1e-7)


def test_rejected_cells_leave_the_scored_rows_and_are_counted():
    scored = pl.DataFrame(
        {
            "state_fips": ["01", "01", "06"],
            "reference_month": [MONTH] * 3,
            "estimator_id": ["a", "b", "a"],
        }
    )
    kept, rejected = reject_exactly_recoverable(
        scored, pl.DataFrame({"state_fips": ["01"], "reference_month": [MONTH]})
    )
    assert (kept["state_fips"].to_list(), rejected) == (["06"], 1)
    untouched, none = reject_exactly_recoverable(
        scored, pl.DataFrame(schema={"state_fips": pl.String, "reference_month": pl.String})
    )
    assert untouched.equals(scored) and none == 0
```

In `tests/integration/test_stage4_acceptance.py`, add `from logging_employment.reconcile.scaling import Bounds` directly before `from logging_employment.runs import run_id` and `from logging_employment.validate import harness` directly before `from logging_employment.validate.harness import run_pseudo_suppression`, and append:

```python
def test_the_harness_hands_the_baselines_the_masked_bounds_it_solved(monkeypatch):
    """D-087: every scoring call to `run_baselines` carries bounds, never `None`.

    A bound-blind harness would score estimates production rescales before release. This fixture
    layer carries no parent margin, so no bound binds here and no score moves; the wiring is what is
    pinned.
    """
    seen: list[object] = []
    real = harness.run_baselines

    def spy(data, config, **kwargs):
        seen.append(kwargs.get("bounds"))
        return real(data, config, **kwargs)

    monkeypatch.setattr(harness, "run_baselines", spy)
    run_pseudo_suppression(HarmonizedData.load(FIXTURE), REGISTRY[:1], _fixture_config())
    assert seen
    assert all(isinstance(bounds, Bounds) and bounds.lower for bounds in seen)
```

- [x] **Step 2: Run them and watch them fail**

Run the two separately, because a collection error stops pytest before any other file runs:

```bash
uv run pytest tests/unit/test_validate_parent_mask.py -q
uv run pytest tests/integration/test_stage4_acceptance.py::test_the_harness_hands_the_baselines_the_masked_bounds_it_solved -q
```

Expected: the first stops at collection with `ImportError: cannot import name 'ConstraintDataError'` and `1 error`; count the module's nine tests as failing. The second is `1 failed`, on `assert False` where `False = all(<genexpr>)`: every scoring call passes no bounds.

- [x] **Step 3: Add the error**

Append to `src/logging_employment/errors.py`:

```python


class ConstraintDataError(LoggingEmploymentError):
    """A known value lies outside the deterministic bounds solved for its cell (§13.5).

    §13.5: "A known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug
    until proven otherwise." A RAISE, because the harness would otherwise score estimates against a
    constraint system that provably excludes the value being scored, and every bound metric it
    emitted would describe a system that is wrong about the data. Distinct from
    `BoundViolationError`, which is an ESTIMATE outside its interval; this is the TRUTH outside it.
    """
```

- [x] **Step 4: Hide a parent exactly where it has no other establishments**

In `src/logging_employment/validate/mask.py`, add directly after `eligible_targets`:

```python
def parents_to_hide(parent: pl.DataFrame, chosen: pl.DataFrame) -> pl.DataFrame:
    """§13.2 step 4 for the §9.3 parent: the masked cells whose published parent is hidden too.

    THE RULE: hide a parent exactly when it holds no establishments besides the masked cell's own --
    parent `qtrly_establishments` minus child `qtrly_establishments` at most 0 -- and leave every
    other parent as public as it really is. Establishment counts are published even for suppressed
    cells, so the rule reads nothing a real suppression would withhold.

    Why this rule and not a propensity, measured 2026-09-12 (`specs/stage5-parent-margin.md` R-PM-3):

    * Where the child is all of the parent's establishments BLS hid the parent on 123 of 123 real
      suppressions, and on all 336 published month-values with no sibling establishments the parent
      EQUALS the child. That is the one case where a visible parent recovers the target exactly
      (§13.2 step 6), and there the rule and BLS's own complementary suppression coincide.
    * Everywhere else the rule leaves the parent visible, and BLS hid it on 34 of 286 real
      suppressions: 21 of 95 with one sibling establishment, 13 of 191 with two or more. The rule
      never hides a parent BLS published; its error is optimism, on 34 of 409 (8.3%). A pseudo-target
      cannot reach the one-sibling case with its parent visible -- a published child with one sibling
      establishment never has a published parent (0 of 49) -- so on the synthetic path the optimism
      is confined to the two-or-more stratum.

    A flat co-suppression rate would ignore the one public variable that measurably drives it, and a
    propensity fitted to 34 events would describe noise. Returns sorted `(state_fips,
    reference_month)` keys, so the leakage guard can re-apply the rule to a masked layer.
    """
    published = parent.filter(pl.col("observation_status") != "suppressed").select(
        "state_fips",
        "reference_month",
        pl.col("qtrly_establishments").alias("parent_establishments"),
    )
    return (
        chosen.select(
            "state_fips",
            "reference_month",
            pl.col("qtrly_establishments").alias("child_establishments"),
        )
        .join(published, on=["state_fips", "reference_month"], how="inner")
        .filter(pl.col("parent_establishments") - pl.col("child_establishments") <= 0)
        .select("state_fips", "reference_month")
        .sort("state_fips", "reference_month")
    )


def _hide(frame: pl.DataFrame, selector: pl.Expr, label: pl.Expr) -> pl.DataFrame:
    """Rewrite the selected rows exactly as a real `N` suppression publishes them, labelled `label`.

    One rewrite for the `113310` target and its `113` parent, so a hidden parent is
    indistinguishable from a real suppressed one in precisely the columns a hidden child is.
    """
    return frame.with_columns(
        pl.when(selector)
        .then(None)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value"),
        pl.when(selector)
        .then(pl.lit("0"))
        .otherwise(pl.col("employment_raw"))
        .alias("employment_raw"),
        pl.when(selector).then(None).otherwise(pl.col("wages_value")).alias("wages_value"),
        pl.when(selector).then(pl.lit("0")).otherwise(pl.col("wages_raw")).alias("wages_raw"),
        pl.when(selector)
        .then(pl.lit("N"))
        .otherwise(pl.col("disclosure_code"))
        .alias("disclosure_code"),
        pl.when(selector)
        .then(pl.lit("suppressed"))
        .otherwise(pl.col("observation_status"))
        .alias("observation_status"),
        pl.when(selector)
        .then(True)
        .otherwise(pl.col("is_published_numeric_zero"))
        .alias("is_published_numeric_zero"),
        pl.when(selector)
        .then(label)
        .otherwise(pl.col("suppression_type"))
        .alias("suppression_type"),
    )
```

In `apply_mask`, replace the whole `masked = (...)` expression and the final `return` with:

```python
    masked = _hide(
        monthly.join(labels, on=["state_fips", "reference_month"], how="left"),
        selector,
        pl.col("_label"),
    ).drop("_label")

    # §13.2 step 4 for the §9.3 parent: hide exactly the parents `parents_to_hide` names and leave
    # every other one as public as it really is. `complementary_like` because the parent is hidden
    # to protect the target, which is what that INV-009 label means.
    hidden = parents_to_hide(data.qcew_state_parent, chosen)
    parent = data.qcew_state_parent
    if hidden.height:
        parent = _hide(
            parent,
            pl.struct("state_fips", "reference_month").is_in(hidden.to_dicts()),
            pl.lit("complementary_like"),
        )
    return dataclasses.replace(data, qcew_monthly=masked, qcew_state_parent=parent), truth
```

and append this closing paragraph to `apply_mask`'s docstring:

```
    The private 113 parent of a target is hidden too exactly when `parents_to_hide` names it
    (§13.2 step 4); every other parent keeps its real visibility.
```

- [x] **Step 5: Make the leakage guard re-apply the rule**

In `src/logging_employment/validate/leakage.py`, add `from .mask import parents_to_hide` below `from ..errors import LeakageError`, and append to the end of `assert_no_retained_truth`:

```python
    # §13.4 bullet 2 for the §9.3 parent: "overlapping margins must reflect the intended synthetic
    # suppression pattern". A parent the mask's own rule hides equals the withheld value, so a
    # masked layer still publishing one hands the truth back through a margin. Checked by
    # re-applying `parents_to_hide` to the masked layer, not by comparing values: a public parent
    # that merely coincides with a truth is not a leak. The guard shares the rule, so it catches a
    # mask that skipped the rule, never a wrong rule; the rule's own tests pin that.
    if not masked.qcew_state_parent.is_empty():
        exposed = parents_to_hide(masked.qcew_state_parent, truth)
        if exposed.height:
            first = exposed.row(0, named=True)
            raise LeakageError(
                f"the private 113 parent on {first['state_fips']}/{first['reference_month']} is "
                "still published although the masked cell holds all of its establishments, so it "
                f"equals the held-out value ({exposed.height} such parent(s))"
            )
```

- [x] **Step 6: Check the truth and find the exactly recoverable targets on every masked solve**

In `src/logging_employment/validate/recover.py`: change the module docstring's first line to `"""§13.2 steps 5-6 and §13.5: rank, bound and check analysis on a masked component.`; change `from dataclasses import dataclass` to `from dataclasses import dataclass, field`; change `from ..constraints.cells import KIND_NATIONAL_SIZE` to `from ..constraints.cells import KIND_NATIONAL_SIZE, KIND_STATE_TOTAL`; add `from ..errors import ConstraintDataError` below the contracts import. Replace `MaskedSystem` and `mask_and_solve` with:

```python
def _no_recoverable() -> pl.DataFrame:
    """The step-6 frame of a mask with nothing exactly recoverable: rowless but SHAPED."""
    return pl.DataFrame(schema={"state_fips": pl.String, "reference_month": pl.String})


@dataclass(frozen=True)
class MaskedSystem:
    """A solved constraint system for one mask, the truth it withheld, and what still recovers it.

    `recoverable` holds the `(state_fips, reference_month)` of every withheld state cell the masked
    system still pins to one value -- §13.2 step 6's cases, which `harness.reject_exactly_recoverable`
    drops from scoring. It defaults to empty for the size arm, whose step-6 rule is `D-085`'s.
    """

    bounds: pl.DataFrame
    components: pl.DataFrame
    constraint_set_hash: str
    truth: pl.DataFrame
    recoverable: pl.DataFrame = field(default_factory=_no_recoverable)


def mask_and_solve(
    data: HarmonizedData, targets: Sequence[MaskTarget], config: Config
) -> MaskedSystem:
    """Apply the mask, rebuild the system from the masked frame, solve it, and check it.

    Two checks run on every solve, because a masked system is the only place either can be seen. A
    withheld truth outside its masked bounds HALTS (§13.5, `assert_truth_within_bounds`), and a
    withheld cell the masked system still recovers exactly is returned in `recoverable` for the
    harness to reject (§13.2 step 6). Before `D-111` neither could fire on the state-total arm,
    because every masked state cell was `[0, +inf)`.
    """
    masked, truth = apply_mask(data, targets) if targets else (data, _empty_truth())
    built = build_constraint_system(masked, config)
    result = solve_bounds(built, config.constraints)
    located = locate_withheld(truth, built.cells, result.bounds)
    assert_truth_within_bounds(located, tolerance=config.constraints.feasibility_tolerance)
    return MaskedSystem(
        bounds=result.bounds,
        components=result.components,
        constraint_set_hash=built.constraint_set_hash,
        truth=truth,
        recoverable=exactly_recoverable(located),
    )


def locate_withheld(truth: pl.DataFrame, cells: pl.DataFrame, bounds: pl.DataFrame) -> pl.DataFrame:
    """Each withheld state cell beside its `cell_id` and masked bounds, joined on key columns.

    Joined on the cells table's own `state_fips` and `reference_month`, never by parsing `cell_id`
    (`mask_and_solve_size` records what substring matching on it measured). LEFT joins, so a
    withheld cell the system somehow lacks survives as nulls for `assert_truth_within_bounds` to
    refuse, rather than vanishing from the check.
    """
    ids = cells.filter(pl.col("cell_id").str.starts_with(f"{KIND_STATE_TOTAL}|")).select(
        "cell_id", "state_fips", "reference_month"
    )
    return truth.join(ids, on=["state_fips", "reference_month"], how="left").join(
        bounds.select("cell_id", "selected_lower", "selected_upper", "bound_status"),
        on="cell_id",
        how="left",
    )


def assert_truth_within_bounds(located: pl.DataFrame, *, tolerance: float) -> None:
    """§13.5: "A known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug".

    `tolerance` is the solver's `feasibility_tolerance`, because the endpoints came out of HiGHS at
    that tolerance. A withheld cell with no located bound halts too: a check that silently skips the
    cells it cannot find passes exactly the case it exists to catch.
    """
    unchecked = located.filter(pl.col("cell_id").is_null() | pl.col("selected_lower").is_null())
    if unchecked.height:
        first = unchecked.row(0, named=True)
        raise ConstraintDataError(
            f"{unchecked.height} withheld cell(s) have no masked bound to check, e.g. "
            f"{first['state_fips']}/{first['reference_month']}; §13.5's rule cannot pass a cell it "
            "never compared"
        )
    outside = located.filter(
        (pl.col("truth") < pl.col("selected_lower") - tolerance)
        | (
            pl.col("selected_upper").is_not_null()
            & (pl.col("truth") > pl.col("selected_upper") + tolerance)
        )
    )
    if outside.height:
        first = outside.row(0, named=True)
        raise ConstraintDataError(
            f"{outside.height} withheld truth(s) fall outside their masked deterministic bounds, "
            f"e.g. {first['cell_id']}: truth {first['truth']} against [{first['selected_lower']}, "
            f"{first['selected_upper']}]. §13.5 treats this as a constraint-data bug until proven "
            "otherwise, so the run halts rather than scoring against a system that excludes the truth"
        )


def exactly_recoverable(located: pl.DataFrame) -> pl.DataFrame:
    """§13.2 step 6's cases: the withheld state cells the masked system still pins to one value."""
    return (
        located.filter(pl.col("bound_status") == "exactly_recoverable")
        .select("state_fips", "reference_month")
        .sort("state_fips", "reference_month")
    )
```

Keep `_empty_truth`, `is_exactly_recoverable` and `mask_and_solve_size` exactly as they are.

- [x] **Step 7: Score with the masked bounds and reject what they recover**

> Deviation (final review): §13.5's bound metrics were computed after step 6 had removed the rows they count, so `exact_recovery_rate` read 0 whenever the rejection worked, and the D-087 wiring test could not see bounds leaked from the unmasked layer. `a9659b6` fixes the ordering and pins the wiring; both are mutation-checked. Step 6 itself cannot fire end to end on the state arm (`D-118`).

In `src/logging_employment/validate/harness.py`, change the runner import to `from ..baselines.runner import REGISTRY, run_baselines, state_total_bounds`; add `"rejected_exactly_recoverable": 0,` as the last key of the `entry` dict literal; and in the seed loop replace

```python
            system = mask_and_solve(data, targets, config)
            results, _audit = run_baselines(masked, config, estimators=estimators)
            scored = _join_truth(
                results, truth, system, targets, regime=name, seed=seed, replicate=replicate
            )
```

with

```python
            system = mask_and_solve(data, targets, config)
            # D-087: the MASKED bounds, never the run directory's, which still contain the truth
            # this replicate hid (§13.4). `run_baselines` scales an estimate a finite bound binds on
            # back into it (§12.3) exactly as production does, so the scoreboard ranks the
            # estimates a release would publish rather than ones production would have rescaled.
            results, _audit = run_baselines(
                masked, config, estimators=estimators, bounds=state_total_bounds(system.bounds)
            )
            scored, rejected = reject_exactly_recoverable(
                _join_truth(
                    results, truth, system, targets, regime=name, seed=seed, replicate=replicate
                ),
                system.recoverable,
            )
            entry["rejected_exactly_recoverable"] = (
                int(entry["rejected_exactly_recoverable"]) + rejected
            )
```

In `src/logging_employment/baselines/runner.py`, `run_baselines`' docstring still names `cli.py` as its only caller. Replace

```
    for unit tests, which build a `HarmonizedData` with no Stage 2 run behind it. `cli.py` passes
    the run directory's `deterministic_bounds`.
```

with

```
    for unit tests, which build a `HarmonizedData` with no Stage 2 run behind it. Both production
    callers pass one: `cli.py` the run directory's `deterministic_bounds`, and `validate/harness.py`
    `MaskedSystem.bounds`, solved from the masked system and NEVER the run directory's, whose
    intervals still contain the truth the harness hid (§13.4). That second caller is `D-087`'s
    ruling.
```

Add directly before `_join_truth`:

```python
def reject_exactly_recoverable(
    scored: pl.DataFrame, recoverable: pl.DataFrame
) -> tuple[pl.DataFrame, int]:
    """§13.2 step 6: drop every scored row whose withheld cell the masked system recovers exactly.

    REJECTED, not merely labelled. `bound_status` already rides on each scored row, but a label no
    metric emitter reads changes no number, and a method scored on a cell the constraints already
    pin is scored on arithmetic, not estimation. Returns the kept rows and how many CELLS were
    rejected, which the regime's manifest entry accumulates so a rejection is never silent. On D1
    the expected count is zero: no published parent equals its child where other establishments
    exist (0 of 2,742 month-values, measured 2026-09-12).
    """
    if recoverable.is_empty():
        return scored, 0
    kept = scored.join(recoverable, on=["state_fips", "reference_month"], how="anti")
    return kept, recoverable.height
```

- [x] **Step 8: Run the tests and the gates**

```bash
uv run pytest tests/unit/test_validate_parent_mask.py tests/integration/test_stage4_acceptance.py tests/unit/test_validate_leakage_guards.py tests/unit/test_validate_mask.py tests/unit/test_validate_recover.py -q
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; suite **+10 passed** (nine in the new module, the wiring test), 0 failed. The fixture goldens stay byte-identical: their layers carry no parent margin, so every scored bound is open and `run_baselines` takes the bit-identical path.

- [x] **Step 9: Commit**

```bash
git add src/logging_employment/errors.py src/logging_employment/baselines/runner.py src/logging_employment/validate/mask.py src/logging_employment/validate/leakage.py src/logging_employment/validate/recover.py src/logging_employment/validate/harness.py tests/unit/test_validate_parent_mask.py tests/integration/test_stage4_acceptance.py
git commit -m "feat(validate): mask the 113 parent by its establishments and enforce §13.5 and step 6 (R-PM-3, D-087)"
```

---

### Task 9: Rebuild the chain and re-run the comparand (R-PM-7)

**Implements:** R-PM-7 (re-run, measured by join, recorded); §4 done-when 1 and 3 on the shipped artifacts; the D1 half of Decision 7.

No code changes. Every number recorded here is printed by a script over the run directories, never typed.

**Files:**
- Modify: `specs/findings/stage-5-log.md`

**Interfaces:**
- Consumes: everything above; `runs/f03023ac9f3a/` as the comparand, read-only.
- Produces: `runs/<new id>/` holding `schema_manifest.json`, `deterministic_bounds.parquet`, `disclosure_flags.parquet`, `baseline_results/`, and the three `validation_*` tables.

- [x] **Step 1: Build and solve the bounded system, and check done-when 1 and 3**

```bash
uv run logging-estimates build-constraints --config config.yaml
uv run logging-estimates solve-bounds --config config.yaml
uv run python - <<'EOF'
from pathlib import Path

import polars as pl

from logging_employment.cli import _input_digests
from logging_employment.config import load_config
from logging_employment.runs import run_dir, run_id

cfg = load_config(Path("config.yaml"))
run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
bounds = pl.read_parquet(run / "deterministic_bounds.parquet")
state = bounds.filter(
    pl.col("cell_id").str.starts_with("state_total|") & (pl.col("solver_status") != "not_solved")
)
milp = bounds.filter(pl.col("milp_upper").is_not_null())
moved = milp.filter(
    (pl.col("milp_lower") != pl.col("lp_lower")) | (pl.col("milp_upper") != pl.col("lp_upper"))
)
flags = pl.read_parquet(run / "disclosure_flags.parquet")
print("run", run.name)
print("suppressed state cells", state.height)
print("finite selected_upper", state["selected_upper"].is_not_null().sum())
print("solver_status", sorted(state["solver_status"].value_counts().rows()))
print("bound_status", sorted(state["bound_status"].value_counts().rows()))
print("MILP rows", milp.height, "- MILP moved an LP endpoint on", moved.height)
print("exact_reconstruction_flag", flags["exact_reconstruction_flag"].sum())
EOF
```

Expected: the run name matches the pin Task 4 wrote; `suppressed state cells 1227`; `finite selected_upper 756` (done-when 1, equal to `specs/findings/qcew-parent-margins.md`'s 756); `solver_status [('optimal', 756), ('unbounded', 471)]` (done-when 3); `bound_status [('partially_identified', 756), ('unbounded', 471)]`; `MILP rows 107 - MILP moved an LP endpoint on 0` (done-when 3's gap question: the MILP ran at zero gap and agreed with LP everywhere, as Decision 7 derives); `exact_reconstruction_flag 0` (R-PM-4). **If `finite selected_upper` differs from the finding, stop and explain the difference before going on** — done-when 1 allows a difference only if it is explained.

- [x] **Step 2: Run the baselines against the bounds, and verify the adding-up identity**

```bash
uv run logging-estimates run-baselines --config config.yaml
uv run logging-estimates reconcile --config config.yaml
```

Expected: both exit 0. `run-baselines` no longer halts on the first parent-bounded month (Task 6); `reconcile` reports every month's estimates re-summing to its residual.

- [x] **Step 3: Re-run the harness (12 minutes or more)**

```bash
time uv run logging-estimates validate --config config.yaml
```

Expected: exit 0, the per-regime `scored=` lines, nine regimes scoring. The shipped run took 12 min 08 s before this plan; every masked system now carries parent rows and some MILP components, so a longer run is not a hang. A `ConstraintDataError` here would mean a withheld truth outside its masked bounds (§13.5): stop and diagnose, never relax the check.

- [x] **Step 4: Measure what moved, by join, and append it to the Stage 5 log**

> Deviation (final review): the section this step appended was replaced by its re-measurement on the final code (`f413a1e`), with a derived addendum: the disclosure flags, what the WAPE movement is, §13.10's comparability caveat, and what the review's fixes moved.

```bash
uv run python - <<'EOF' | tee /tmp/plan15-rpm7.md
import datetime
import json
from pathlib import Path

import polars as pl

from logging_employment.cli import _input_digests
from logging_employment.config import load_config
from logging_employment.runs import run_dir, run_id
from logging_employment.validate.scoreboard import preferred_baseline

cfg = load_config(Path("config.yaml"))
new = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
old = new.parent / "f03023ac9f3a"
TOL = 1e-9


def moved(before: pl.DataFrame, after: pl.DataFrame, key: list[str], column: str) -> pl.DataFrame:
    """Rows present on both sides whose `column` changed: nullness, or by more than TOL.

    Keys join with `nulls_equal=True`. `validation_metrics` carries null key fields, and a default
    join reads those rows as present on one side only -- 270 of 6,932 when the table is joined to
    itself, measured while this plan was written.
    """
    joined = before.join(after, on=key, how="inner", suffix="_new", nulls_equal=True)
    return joined.filter(
        (pl.col(column).is_null() != pl.col(f"{column}_new").is_null())
        | ((pl.col(column) - pl.col(f"{column}_new")).abs() > TOL)
    )


def key_only(before: pl.DataFrame, after: pl.DataFrame, key: list[str]) -> str:
    """How many rows each side holds that the other lacks, as `old / new`."""
    left = before.join(after, on=key, how="anti", nulls_equal=True).height
    right = after.join(before, on=key, how="anti", nulls_equal=True).height
    return f"{left} / {right}"


def listing(pairs: list[tuple[str, int]]) -> str:
    """`name count` pairs as prose, or `none` when there are none."""
    return ", ".join(f"`{name}` {count}" for name, count in pairs) or "none"


out = [
    f"\n## {datetime.date.today().isoformat()} — R-PM-7: the comparand re-run against the bounded identification set\n",
    f"`runs/{new.name}` (plan 15 Task 9) against `runs/{old.name}`, compared by join on each table's key,",
    "never by position. R-PM-7's answer is that the comparand IS re-run: Task 4 re-ids every run, and both",
    "the production runner and the harness now read bounds (Decisions 3 and 6), so every estimate a bound",
    "binds on moves. The rows below are that movement, derived. `runs/f03023ac9f3a` stays on disk as Stage 4's",
    f"acceptance run; Stage 5's §13.10 promotion compares against `runs/{new.name}`.\n",
]

b_old = pl.read_parquet(old / "baseline_results" / "baseline_results.parquet")
b_new = pl.read_parquet(new / "baseline_results" / "baseline_results.parquet")
b_key = ["estimator_id", "cell_id"]
b_moved = moved(b_old, b_new, b_key, "estimate")
caps = pl.read_parquet(new / "deterministic_bounds.parquet").select("cell_id", "selected_upper")
at_cap = b_new.join(caps, on="cell_id", how="inner").filter(
    pl.col("selected_upper").is_not_null()
    & ((pl.col("estimate") - pl.col("selected_upper")).abs() <= TOL)
)
out += [
    "| `baseline_results` | value |",
    "|---|---|",
    f"| rows old / new | {b_old.height} / {b_new.height} |",
    f"| key-only rows old / new | {key_only(b_old, b_new, b_key)} |",
    f"| estimates moved beyond {TOL:g} | {b_moved.height} |",
    f"| estimator-months with a moved estimate | {b_moved.select('estimator_id', 'reference_month').unique().height} |",
    f"| estimates now exactly at a finite upper bound | {at_cap.height} |",
    "",
    "Moved estimates by estimator: "
    + listing(b_moved.group_by("estimator_id").len().sort("estimator_id").rows())
    + ".\n",
]

s_old = pl.read_parquet(old / "validation_scores.parquet")
s_new = pl.read_parquet(new / "validation_scores.parquet")
s_key = ["regime", "seed", "replicate", "estimator_id", "cell_id"]
out += [
    "| `validation_scores` | value |",
    "|---|---|",
    f"| rows old / new | {s_old.height} / {s_new.height} |",
    f"| key-only rows old / new | {key_only(s_old, s_new, s_key)} |",
    f"| scored rows with a finite `selected_upper`, old / new | {s_old['selected_upper'].is_not_null().sum()} / {s_new['selected_upper'].is_not_null().sum()} |",
    f"| estimates moved beyond {TOL:g} | {moved(s_old, s_new, s_key, 'estimate').height} |",
    "",
]

sb_old = pl.read_parquet(old / "validation_scoreboard.parquet")
sb_new = pl.read_parquet(new / "validation_scoreboard.parquet")
sb_key = ["regime", "seed", "mask_arm", "estimator_id"]
delta = sb_old.join(sb_new, on=sb_key, how="inner", suffix="_new", nulls_equal=True).select(
    (pl.col("wape_new") - pl.col("wape")).alias("change")
)["change"]
out += [
    "| `validation_scoreboard` | value |",
    "|---|---|",
    f"| rows old / new | {sb_old.height} / {sb_new.height} |",
    f"| key-only rows old / new | {key_only(sb_old, sb_new, sb_key)} |",
    f"| WAPE moved beyond {TOL:g} | {moved(sb_old, sb_new, sb_key, 'wape').height} |",
    f"| WAPE change, min / median / max | {delta.min():.4f} / {delta.median():.4f} / {delta.max():.4f} |",
    "",
    "| regime | preferred baseline, old | new |",
    "|---|---|---|",
]
for regime in sorted(set(sb_old["regime"].to_list()) | set(sb_new["regime"].to_list())):
    out.append(
        f"| `{regime}` | `{preferred_baseline(sb_old, regime=regime)}` | `{preferred_baseline(sb_new, regime=regime)}` |"
    )

m_old = pl.read_parquet(old / "validation_metrics.parquet")
m_new = pl.read_parquet(new / "validation_metrics.parquet")
m_key = ["regime", "seed", "mask_arm", "estimator_id", "metric_family", "stratum_kind", "stratum_value", "metric_name"]
m_moved = moved(m_old, m_new, m_key, "value")
manifest = json.loads((new / "validation_manifest.json").read_text())
rejected = sum(int(entry.get("rejected_exactly_recoverable", 0)) for entry in manifest["regimes"].values())
out += [
    "",
    f"`validation_metrics`: {m_old.height} / {m_new.height} rows, key-only {key_only(m_old, m_new, m_key)}; `value` moved on "
    f"{m_moved.height}: "
    + listing(m_moved.group_by("metric_family").len().sort("metric_family").rows())
    + ".",
    f"Exactly recoverable targets rejected from scoring (§13.2 step 6): {rejected}. "
    f"`validation_manifest.json` records `code_commit` `{manifest['code_commit']}`.",
]
print("\n".join(out))
EOF
cat /tmp/plan15-rpm7.md >> specs/findings/stage-5-log.md
```

Expected: the script prints a markdown section and it is appended to the log. Read it before committing: `key-only rows` should be `0 / 0` for `baseline_results`, the scoreboard and `validation_metrics` (the same cells, estimators and strata ran), the scored-rows count should not fall unless `rejected` is non-zero, and `code_commit` must not end in `-dirty`.

- [x] **Step 5: Run the gates on the re-run tree**

```bash
uv run pytest -q
```

Expected: 0 failed, the same passed count as after Task 8. The acceptance pin Task 4 moved names this run directory, which now exists.

- [x] **Step 6: Commit the record**

```bash
git add specs/findings/stage-5-log.md
git commit -m "docs(findings): record R-PM-7's re-run of the Stage 5 comparand against the bounded set"
```

---

### Task 10: Land `D-111` in every note that treats it as pending, and lift the roadmap clause

**Implements:** §4 done-when 5 and 6.

**Files:**
- Modify: `specs/logging-employment-spec-roadmap.md` (the Stage 5 block), `specs/findings/stage-5-log.md` (the superseded reading), `README.md`, `CLAUDE.md`, `specs/logging-employment-spec.md` (three stage-stamp notes)
- Modify: `src/logging_employment/reconcile/scaling.py`, `src/logging_employment/reconcile/allocate.py`, `src/logging_employment/reconcile/CLAUDE.md`, `src/logging_employment/baselines/CLAUDE.md`, `src/logging_employment/validate/CLAUDE.md`, `src/logging_employment/validate/metrics.py`, `src/logging_employment/validate/propensity.py`, `src/logging_employment/constraints/CLAUDE.md`
- Modify: `tests/unit/test_scaling.py`, `tests/unit/test_reconcile_properties.py` (docstrings only)

**Interfaces:**
- Consumes: the re-run directory from Task 9.
- Produces: no code.

One script applies every edit, for two reasons: the counts and the run id the new text quotes are read off Task 9's artifacts rather than typed, and each edit must match its passage exactly once or nothing is written. Stage-block rule 1 governs the roadmap: the correction REPLACES the pending sentences, and the superseded reading goes to `specs/findings/stage-5-log.md`.

- [x] **Step 1: Save the rewrite script**

Save this as `/tmp/plan15_task10_docs.py`. It is a one-off and is not committed.

```python
"""Plan 15 Task 10: rewrite every note that treats `D-111` as pending (done-when 6).

Derived, not typed: the counts and the run id come from the re-run's own artifacts. Each edit must
match EXACTLY ONCE or the script halts before writing anything. `--check` verifies the matches only.
"""

import datetime
import sys
from pathlib import Path

import polars as pl

CHECK = "--check" in sys.argv
TODAY = datetime.date.today().isoformat()

if CHECK:
    NEW_ID, SUPPRESSED, BOUNDED, OPEN = "000000000000", 0, 0, 0
else:
    from logging_employment.cli import _input_digests
    from logging_employment.config import load_config
    from logging_employment.runs import run_dir, run_id

    cfg = load_config(Path("config.yaml"))
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    NEW_ID = run.name
    state = pl.read_parquet(run / "deterministic_bounds.parquet").filter(
        pl.col("cell_id").str.starts_with("state_total|") & (pl.col("solver_status") != "not_solved")
    )
    SUPPRESSED = state.height
    BOUNDED = int(state["selected_upper"].is_not_null().sum())
    OPEN = SUPPRESSED - BOUNDED

ROADMAP = Path("specs/logging-employment-spec-roadmap.md")
ROADMAP_START = "**The §9.3 margins are a precondition of THIS stage, not Stage 6's.**"
ROADMAP_END = (
    "See `specs/findings/qcew-parent-margins.md`; `specs/findings/stage-5-log.md` carries the history."
)
ROADMAP_NEW = (
    "**The §9.3 parent margin is in the identification set** (plan 15, `specs/stage5-parent-margin.md`). "
    "A published private `113` state value bounds its suppressed `113310` child above through a "
    "`parent_margin` row, so this stage consumes `deterministic_bounds` as identification-complete for "
    f"every margin measured to date: on the plan-15 re-run {BOUNDED} of the {SUPPRESSED} suppressed state "
    f"cells carry a finite upper and {OPEN} stay `[0, +inf)`. No measured margin, the `113 - 1131 - 1132` "
    "sibling path included, reconstructs a suppressed cell exactly, so REQ-027/§14.4 has no live instance "
    "(`D-110`). Both the runner and the harness scale estimates into finite bounds by §12.3 (`D-087`), and "
    f"the §13.10 comparand is `runs/{NEW_ID}`, not Stage 4's acceptance run `runs/f03023ac9f3a`. " + ROADMAP_END
)

EDITS: list[tuple[str, str, str]] = [
    (
        "README.md",
        """On the pilot window the engine bounds 14 suppressed national size classes to intervals 130–894
employees wide, and reports every one of the 1,227 suppressed state-month cells as `unbounded`.
`SRC-QCEW-006` came back `decline`, so no national employment margin exists to constrain a state
cell. A disclosed private `113` parent publishes an upper bound on 756 of those 1,227 cells
(measured 2026-09-11, `specs/findings/qcew-parent-margins.md`) that is not yet a constraint row;
`specs/stage5-parent-margin.md` owns wiring it in.
""",
        f"""On the pilot window the engine bounds 14 suppressed national size classes to intervals 130–894
employees wide. `SRC-QCEW-006` came back `decline`, so no national employment margin constrains a
state cell, but a published private `113` parent does: on the {TODAY} re-run {BOUNDED} of the
{SUPPRESSED} suppressed state-month cells carry that parent as a finite upper bound and {OPEN} stay
`unbounded` (`specs/findings/qcew-parent-margins.md`, `specs/findings/stage-5-log.md`).
""",
    ),
    (
        "specs/logging-employment-spec.md",
        """>   *Qualified 2026-09-12 (plan 14; measured 2026-09-11): true of what the engine CONSUMES, not of what is published — a
>   disclosed private `113` parent bounds 756 of the 1,227 above (`specs/findings/qcew-parent-margins.md`),
>   not yet a constraint row (`D-111`).*""",
        f""">   *Qualified 2026-09-12 (plan 14) and closed by plan 15 (`D-111`, {TODAY}): the published private
>   `113` parent is now a constraint row, so {BOUNDED} of these {SUPPRESSED} carry a finite upper and
>   {OPEN} stay `unbounded` (`specs/findings/stage-5-log.md`).*""",
    ),
    (
        "specs/logging-employment-spec.md",
        """>   *Until `D-111` lands (measured 2026-09-11): a disclosed private `113` parent publishes an upper
>   endpoint on 756 of the 1,227, and once it is a constraint row those cells are clipped from above.*""",
        f""">   *Since `D-111` (plan 15, {TODAY}): the parent row clips {BOUNDED} of the {SUPPRESSED} from above;
>   `model_sensitivity_high` stays model-set on the other {OPEN}.*""",
    ),
    (
        "specs/logging-employment-spec.md",
        """*(Scoped 2026-09-12, plan 14: through any
>   measured margin. The `113 - 1131 - 1132` path is unmeasured on 252 quarters — `D-110`.)*""",
        """*(Scoped 2026-09-12, plan 14: through any
>   measured margin. Completed by plan 15: the `113 - 1131 - 1132` path is measured too and reconstructs no suppressed quarter — `D-110` closed.)*""",
    ),
    (
        "src/logging_employment/reconcile/scaling.py",
        """WHY NULL UPPERS ARE INFINITE. On the D1 window `selected_upper` is null on 1,227 of 1,241 unknown
cells, because `SRC-QCEW-006` came back `decline` and no other public fact has been made a
constraint row. (One exists: a disclosed private `113` parent bounds 756 of the 1,227 above, measured
2026-09-11 and routed to `specs/stage5-parent-margin.md`; until it lands every such upper is null.)
`None` maps to `math.inf`, which makes the clip's upper arm a no-op and the
`sum U < R_t` half of §12.3's predicate vacuous.""",
        """WHY NULL UPPERS ARE INFINITE. A null `selected_upper` means no public fact bounds the cell above.
On D1 that is true of every suppressed state cell without a published private `113` parent: plan
15 made that parent a constraint row, and `SRC-QCEW-006` came back `decline`, so nothing else bounds
a state cell. `None` maps to `math.inf`, which makes the clip's upper arm a no-op for such a cell,
and every D1 month's missing set holds at least one, so the `sum U < R_t` half of §12.3's predicate
cannot fire there.""",
    ),
    (
        "src/logging_employment/reconcile/allocate.py",
        """    The required no-bound fast path, kept as its own code path rather than folded into §12.3's
    bounded scaling. On the D1 window every state cell is unbounded above, so this path carries
    the whole production load and deserves to be readable on its own.""",
        """    The required no-bound fast path, kept as its own code path rather than folded into §12.3's
    bounded scaling. `baselines/runner.run_baselines` calls it first on every month and falls
    through to `scale_into_bounds` only where this allocation leaves a finite interval (plan 15),
    so it still carries most of the production load and deserves to be readable on its own.""",
    ),
    (
        "src/logging_employment/reconcile/CLAUDE.md",
        "reads `scaling.Bounds` so `runner.assert_within_bounds` can enforce INV-002's per-cell half.",
        "reads `scaling.Bounds` so `runner.assert_within_bounds` can enforce INV-002's per-cell half. Since\n"
        "plan 15 it also calls `scaling.scale_into_bounds` wherever `allocate` leaves a finite interval.",
    ),
    (
        "src/logging_employment/reconcile/CLAUDE.md",
        "- `scaling.scale_into_bounds` — reached only from `reconcile_draws` (Stage 5).\n",
        "",
    ),
    (
        "src/logging_employment/reconcile/CLAUDE.md",
        """On D1,
  `selected_upper` is null on almost every unknown cell, so the `sum U < R_t` arm of §12.3's
  predicate is vacuous.""",
        """On D1 it
  is null on every suppressed state cell without a published private `113` parent, and every
  month's missing set holds one, so the `sum U < R_t` arm of §12.3's predicate cannot fire.""",
    ),
    (
        "src/logging_employment/reconcile/CLAUDE.md",
        """`scaling.py` and several test files carry hand-typed D1 counts ("1,227 of 1,241") that are
undated and unrecomputed; `specs/deferred_items.md` has an open item on the five remaining `1,227`
sites — read it before citing or copying one.""",
        """Plan 15 rewrote the null-upper D1 counts that `D-111` made false, in `scaling.py` and the tests
that copied them; `specs/deferred_items.md` (`D-056`) still governs the other undated `1,227`
sites — read it before citing or copying one.""",
    ),
    (
        "src/logging_employment/baselines/CLAUDE.md",
        """**The runner enforces INV-002's per-cell half** (plan 13, R-S5P-3). `run_baselines` takes an
optional keyword-only `bounds: Bounds | None`; `runner.state_total_bounds` turns §7.10's
`deterministic_bounds` table into it and `runner.assert_within_bounds` raises
`errors.BoundViolationError` for a released value outside its own `[L, U]` — a RAISE, not a
`Decline` row, because unlike `WeightDomainError` this is not a data gap. Keyed by the seven-field
`cell_id`, NOT `state_fips`: `scale_into_bounds` keys the same type by bare state, but that object
is one month's feasible set while `run_baselines` walks the whole window in one call. Both the
float and §12.6's integer release are checked, and a violation HALTS — nothing clips, so no
estimate is ever silently moved into range. `cli.py` passes bounds; `validate/harness.py`
deliberately does NOT, because halting is the wrong response on a scoring path and because the
run directory's intervals were solved with the truth the harness hid still in the system (masked
bounds do exist there — see `validate/CLAUDE.md` and `D-087`).""",
        """**The runner enforces INV-002's per-cell half** (plan 13, R-S5P-3; reallocation since plan 15).
`run_baselines` takes an optional keyword-only `bounds: Bounds | None`; `runner.state_total_bounds`
turns §7.10's `deterministic_bounds` table into it, keyed by the seven-field `cell_id`, NOT
`state_fips`, and `runner.month_bounds` projects one month's missing set onto the bare-state keys
`scale_into_bounds` and `integerize` read. A month §12.2's `allocate` keeps inside every interval
is left bit-identical; a month it does not is reallocated by §12.3's `scale_into_bounds`, and
§12.6's integers are cut to the same bounds. Two raises remain: `InfeasibleResidualError` when a
month's bounds cannot hold its residual, and `errors.BoundViolationError` if a value still escapes
after scaling — a defect, never a `Decline` row. `cli.py` passes the run directory's bounds;
`validate/harness.py` passes `MaskedSystem.bounds`, never the run directory's (`D-087`, see
`validate/CLAUDE.md`).""",
    ),
    (
        "src/logging_employment/validate/CLAUDE.md",
        """  **Corollary, and why this package calls `run_baselines` WITHOUT bounds** (plan 13, R-S5P-3):
  the production path checks every estimate against §9's interval and RAISES on a violation —
  **nothing clips**, `assert_within_bounds` never modifies a value. Handing the harness the RUN
  DIRECTORY's intervals would make the check's own verdict depend on the truth this harness hid,
  which is a leak in the signal. Masked bounds would not leak and **already exist** —
  `mask_and_solve` returns `MaskedSystem.bounds`, solved from the masked system, one line before
  the `run_baselines` call. So the gap is not a missing input: it is that raising is the wrong
  response on a SCORING path, where one estimator missing one interval would abort the whole run.
  That ruling is `D-087`.""",
        """  **Corollary, and why this package passes `run_baselines` the MASKED bounds** (`D-087`, ruled by
  plan 15): the RUN DIRECTORY's intervals would make the estimates depend on the truth this harness
  hid, so the harness passes `state_total_bounds(MaskedSystem.bounds)`, solved from the masked
  system one line earlier. `run_baselines` scales an estimate a finite bound binds on back into it
  (§12.3) exactly as production does, so an out-of-interval estimate never reaches a scored row.
  `mask_and_solve` also HALTS on a withheld truth outside its masked bounds (§13.5,
  `ConstraintDataError`) and returns `recoverable`, the targets it still pins exactly, which
  `harness.reject_exactly_recoverable` drops from scoring and counts per regime (§13.2 step 6).""",
    ),
    (
        "src/logging_employment/validate/CLAUDE.md",
        "- **The truth join is INNER**",
        """- **A masked cell's private `113` parent is hidden exactly when it holds no other establishments**
  (`mask.parents_to_hide`, §13.2 step 4) and keeps its real visibility otherwise;
  `leakage.assert_no_retained_truth` re-applies the rule to the masked layer. The docstring carries
  the measurements and the rule's one-sided error: optimism on 34 of 409 real suppressions.
- **The truth join is INNER**""",
    ),
    (
        "src/logging_employment/validate/CLAUDE.md",
        """- **§13.5 numbers on `state_total` are vacuous by construction.** Every masked state cell is
  `unbounded` with a null `selected_upper`, so `truth_in_bound_rate == 1.0` means "[0, +inf)
  contains the truth". `bound_cells_finite_upper` rides on every row to separate the two.""",
        """- **§13.5 numbers on `state_total` inform only where a parent stays visible.** Since plan 15 a
  masked state cell whose private `113` parent stays public is bounded `[0, 113]`; every other masked
  state cell is still `[0, +inf)`, where `truth_in_bound_rate == 1.0` means nothing.
  `bound_cells_finite_upper` rides on every row to separate the two.""",
    ),
    (
        "src/logging_employment/validate/metrics.py",
        """Read the vacuity note before trusting a §13.5 number. On the `state_total` arm every masked cell is
`unbounded` with `selected_upper = null`, so a truth-in-bound rate of 1.0 means "[0, +inf) contains
the truth", not "the bounds were informative". `bound_cells_finite_upper` is what separates the
two, and it is on every row for that reason.""",
        """Read the vacuity note before trusting a §13.5 number. On the `state_total` arm a masked cell is
bounded above only where its private `113` parent stays public under the mask (plan 15); every other
masked cell is `unbounded` with `selected_upper = null`, where a truth-in-bound rate of 1.0 means
"[0, +inf) contains the truth", not "the bounds were informative". `bound_cells_finite_upper` is
what separates the two, and it is on every row for that reason.""",
    ),
    (
        "src/logging_employment/validate/propensity.py",
        """`target_propensity`), and the fifth -- "parent share" -- is NOT implemented and is not approximated: the STATE-level staged tables (`qcew_monthly`, `cbp_state_size`) carry industry 113310
alone, so the pipeline has no parent 1133 or 113 state series to form a share against
(`qcew_national_size` carries 113, 1133 and 11331, but only nationally). A private 113 state series
IS published -- measured 2026-09-11 in `specs/findings/qcew-parent-margins.md` -- and is not
ingested (`D-111`). Ingesting it is all an ESTABLISHMENT-count share needs,
since establishment counts are published even where employment is suppressed.""",
        """`target_propensity`), and the fifth -- "parent share" -- is NOT implemented and is not approximated.
The private 113 state series it would divide by IS staged since plan 15 (`qcew_state_parent`), and
an ESTABLISHMENT-count share needs nothing more, since establishment counts are published even
where employment is suppressed. It is left out by decision: a new predictor re-draws every regime's
mask, and plan 15 re-ran the §13.10 comparand on the masks as they stood.""",
    ),
    (
        "src/logging_employment/validate/propensity.py",
        """    SCOPE, stated because the obvious reading is wrong: on the `state_total` arm this defeats no
    subtraction, because there is none. Measured 2026-09-07, all 4,716 state cells are single-cell
    components — `assert_no_national_employment_margin` is Stage 0's SRC-QCEW-006 `decline` in
    code. A masked state total is `unbounded` with and without partners.""",
        """    SCOPE, stated because the obvious reading is wrong: on the `state_total` arm this defeats no
    subtraction, because there is none. `assert_no_national_employment_margin` is Stage 0's
    SRC-QCEW-006 `decline` in code, so no row couples two state cells; since plan 15 the one row
    touching a state cell is its `parent_margin`, which couples it to its own private `113` parent
    and to nothing a partner could change. A masked state total's interval is the same with and
    without partners.""",
    ),
    (
        "src/logging_employment/constraints/CLAUDE.md",
        """The only margin
built here is `size_margin|<month>`: national classes minus the national all-sizes cell = 0, so
INV-001 pins that total through its own fixing row instead of an rhs literal.""",
        """The first margin
built here is `size_margin|<month>`: national classes minus the national all-sizes cell = 0, so
INV-001 pins that total through its own fixing row instead of an rhs literal. The second, since
plan 15, is `parent_margin|<child cell_id>`: a suppressed `state_total` cell minus its published
private `113` `state_parent` cell <= 0, one state-month at a time. It couples a state cell to its
own parent, never to another state or the nation, so the guard above admits it.""",
    ),
    (
        "CLAUDE.md",
        "logging-estimates fetch --source qcew --config config.yaml   # or qcew_size / cbp; network +",
        "logging-estimates fetch --source qcew --config config.yaml   # or qcew_parent / qcew_size / cbp; network +",
    ),
    ("CLAUDE.md", "four harmonized Parquet tables", "five harmonized Parquet tables"),
    (
        "tests/unit/test_scaling.py",
        '    """1,227 of 1,241 D1 cells have this shape, so this is the production path."""',
        '    """Open bounds are still a production shape: every suppressed state cell with no published\n'
        '    private `113` parent has them (plan 15)."""',
    ),
    (
        "tests/unit/test_reconcile_properties.py",
        """On the D1 window
`selected_upper` is null on 1,227 of 1,241 unknown cells, so a finite upper bound never binds and
`sum U < R_t` never fires;""",
        """On the D1 window
a finite upper binds only through the §9.3 parent margin (plan 15), and `sum U < R_t` never fires
because every month's missing set holds a cell no parent bounds;""",
    ),
]

texts: dict[str, str] = {}
for path, old, new in EDITS:
    text = texts.setdefault(path, Path(path).read_text(encoding="utf-8"))
    found = text.count(old)
    if found != 1:
        raise SystemExit(f"{path}: expected exactly one match, found {found}: {old[:70]!r}")
    texts[path] = text.replace(old, new)

roadmap = ROADMAP.read_text(encoding="utf-8")
start, end = roadmap.find(ROADMAP_START), roadmap.find(ROADMAP_END)
if roadmap.count(ROADMAP_START) != 1 or roadmap.count(ROADMAP_END) != 1 or not 0 <= start < end:
    raise SystemExit("the Stage 5 roadmap span's markers do not each occur once, in order")
superseded = roadmap[start : end + len(ROADMAP_END)]

if CHECK:
    print(f"all {len(EDITS)} edits and the roadmap span match exactly once")
    raise SystemExit(0)

for path, text in texts.items():
    Path(path).write_text(text, encoding="utf-8")
ROADMAP.write_text(roadmap.replace(superseded, ROADMAP_NEW), encoding="utf-8")
with Path("specs/findings/stage-5-log.md").open("a", encoding="utf-8") as log:
    log.write(
        f"\n## {TODAY} — superseded Stage 5 roadmap reading (stage-block rule 1)\n\n"
        "Plan 15 Task 10 replaced this span of the Stage 5 block, which treated `D-111` as pending:\n\n"
        f"> {superseded}\n"
    )
print(f"rewrote {len(texts)} files and the Stage 5 roadmap block; run {NEW_ID}: {BOUNDED} bounded, {OPEN} open")
```

- [x] **Step 2: Check every match, then apply**

```bash
uv run python /tmp/plan15_task10_docs.py --check
uv run python /tmp/plan15_task10_docs.py
grep -c '^- \[ \] Stage 5:' specs/logging-employment-spec-roadmap.md
```

Expected: `all 22 edits and the roadmap span match exactly once`; then `rewrote 13 files and the Stage 5 roadmap block; run <the Task 4 id>: 756 bounded, 471 open`; then `1`, so the Stage 5 block is still exactly one line. If `--check` names a passage, an earlier task or a merge changed it: re-read that file and correct the script's `old` text. Never loosen the exactly-once rule.

- [x] **Step 3: Find anything the script did not reach**

> Deviation: at this step the second grep was not empty. It matched six gitignored `__pycache__` binaries compiled before Step 2's edits, while text files were clean (`grep -rnI` printed nothing). After Step 4's suite regenerated the caches, the literal grep printed nothing. Every `D-111` hit outside the history files reads as landed.

```bash
grep -rn 'D-111\|756 of the 1,227' src specs README.md CLAUDE.md --include='*.py' --include='*.md' | cut -d: -f1 | sort | uniq -c
grep -rn '1,227 of 1,241' src tests
```

Expected: every remaining `D-111` hit either reads as landed ("since `D-111`", "before `D-111`", "closed by plan 15") or sits in a history file: `specs/deferred_items.md` (ticked by the completion protocol), `specs/findings/stage-5-log.md`, `specs/completed/`, `specs/plans/`, and `specs/stage5-parent-margin.md` itself, which the completion protocol retires. Rewrite any hit that still reads as pending, under the same exactly-once rule. The second grep prints nothing. Two `1,227 of … 1,241` sentences stay in `specs/logging-employment-spec.md`: they are dated Stage 3 and Stage 7 re-validation records of what Stage 2 shipped, not claims about today.

- [x] **Step 4: Run the gates**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
uv run pytest -q
```

Expected: clean; `passed` unchanged from Task 9, since only docstrings and documents moved.

- [x] **Step 5: Commit**

```bash
git add specs/logging-employment-spec-roadmap.md specs/findings/stage-5-log.md README.md CLAUDE.md specs/logging-employment-spec.md src/logging_employment/reconcile/scaling.py src/logging_employment/reconcile/allocate.py src/logging_employment/reconcile/CLAUDE.md src/logging_employment/baselines/CLAUDE.md src/logging_employment/validate/CLAUDE.md src/logging_employment/validate/metrics.py src/logging_employment/validate/propensity.py src/logging_employment/constraints/CLAUDE.md tests/unit/test_scaling.py tests/unit/test_reconcile_properties.py
git commit -m "docs: land D-111 across the roadmap, the spec's stage stamps and the module notes"
```

---

## Spec coverage

| Requirement | Where it is implemented |
|---|---|
| R-PM-1: registry row, reuse of the dual-route interface, the agglvl as a measured fact | Task 2 (row, route, constants); Task 4 (parser level, empty-result halt) |
| R-PM-1: the establishment-share predictor this ingest unblocks | Task 4 stages the series; the predictor is deliberately not added (Decision 10) |
| R-PM-2: cell kind, builder, `published_value` restriction, guard untouched | Task 7 |
| R-PM-3: step 4's visibility rule, stated and justified | Task 8 (`parents_to_hide`); Decision 4 |
| R-PM-3: step 6's exact cases rejected or labelled | Task 8 (`recoverable`, `reject_exactly_recoverable`); Decision 5 |
| R-PM-3: §13.5's out-of-bounds rule on the state-total arm | Task 8 (`assert_truth_within_bounds`) |
| R-PM-3: `D-087` settled in the same pass | Task 8 Step 7 and Decision 6; its production half is Task 6 |
| R-PM-4: conditional on R-PM-5 and ruled on its outcome | Task 1 Steps 11-13 |
| R-PM-5: measured by the same script and the same ladder | Task 1 |
| R-PM-6: sized against the under-threshold count, `D-093` answered | Task 5; Decision 7; Task 9 Step 1 |
| R-PM-7: whether the comparand moves, stated and measured | Decision 9; Task 9 |
| R-PM-8: the disclosed-pair ratio is never quoted as the bound's tightness | nowhere in this plan is it quoted at all |
| Done-when 1: finite `selected_upper` matches the finding | Task 4 Step 8; Task 7's rewritten D1 test; Task 9 Step 1 |
| Done-when 2: visibility and labelling, with tests that fail if dropped | Task 8 Steps 1-2 |
| Done-when 3: `solver_status` and the gap answer | Task 7's rewritten D1 test; Task 5; Task 9 Step 1 |
| Done-when 4: the sibling outcome and R-PM-4's ruling | Task 1 |
| Done-when 5: the roadmap clause lifted by the stage-block rule | Task 10 |
| Done-when 6: every pending note found by grep | Task 10 Step 3 |
