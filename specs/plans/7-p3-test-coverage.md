# P3 Test-Coverage Batch — Implementation Plan

**Status: COMPLETE (2026-09-06)** — executed via executing-plans; five new items deferred in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: **executing-plans** — inline execution was chosen at
> the handoff on 2026-09-05, so run the tasks yourself in plan order rather than dispatching
> subagents. Its stop-and-ask rules and completion chain apply. Steps use checkbox (`- [ ]`) syntax
> for tracking.

> Branch: `p3-test-coverage`, off `main` at `78d933f` (which is level with `origin/main`).
> Do not work on `main`.

> Source: `specs/deferred_items.md`. There is no spec — **five deferred items ARE the
> requirements**, and they were grouped as the "P3 — test-coverage batch" by a `/deferred` triage
> on 2026-09-05. The five, by their line anchors in that file at `78d933f`:
> | # | line | item |
> |---|---|---|
> | A | 130 | `scripts/audit/qcew_routes.py`: the multi-year bulk-disagreement branch is unexercised |
> | B | 204 | Two gate-work fixes ship without tests (`ces_levels` rewording; `cbp_regime`'s `max()` guard) |
> | C | 250 | The bulk-route branch is exercised only under a synthetic boundary |
> | D | 489 | `BreakAdjustedShare` collapses to `RollingMedianShare` below four shares |
> | E | 504 | Task 18's property tests and four of the five cross-cutting audit units never ran |
>
> On plan completion, tick all five per the Plan Completion Protocol. **Item A ticks with no task
> — see "What the recon corrected" below.**

**Goal:** Close the five P3 test-coverage items by adding tests only — no source change in any
task except one docstring reword whose falseness a new test would otherwise expose — so that every
behaviour these items name is held by an assertion that fails when the behaviour goes away.

**Architecture:** Five items, four tasks, five test files, zero production-source behaviour
changes. Task boundaries follow the items, except that A needs no task and B splits in two
because its sub-items share nothing but a sentence in `deferred_items.md`. Every task is
**mutation-gated**: its final step reverts the behaviour under test and confirms the new tests go
red. That gate is the point of the batch — four of these five items exist because a shipped
behaviour had no test that could fail, and a new test that cannot fail would repeat the defect
rather than close it.

**Tech Stack:** Python ≥ 3.12 (PEP 723 audit scripts) on a ≥ 3.14 project, uv, Polars, NumPy,
httpx, pytest.

---

## Global Constraints

- The scripts under `scripts/audit/` are standalone PEP 723 files declaring
  `requires-python = ">=3.12"`. Anything added must parse under 3.12 —
  `ast.parse(src, feature_version=(3, 12))` is the check. **This plan adds no code to those
  scripts**, only to `tests/audit/`, which is not subject to the floor.
- `line-length = 100` for `ruff` and `black`; `[tool.black] target-version = ["py312"]`.
- `interrogate` runs at `fail-under = 100` over `src/` only. This plan touches `src/` in exactly
  one place (Task 4, Step 6: a docstring reword) and adds no function there.
- **Baseline, measured at `78d933f` on 2026-09-05 with `data/staged/`, `data/raw/audit/` and
  `runs/` present:**
  | command | result |
  |---|---|
  | `uv run pytest -q` | **1123 passed**, 0 failed, 143 s |
  | `uv run pytest tests/audit -q` | **680 passed**, 0.61 s |
  | `uv run pytest tests/unit -q` | **400 passed**, 2.09 s |
  | `uv run black --check .` | clean, **137 files** |
  | `uv run ruff check .` | **24 errors** — ISC004 9, TRY004 5, UP037 4, RUF100 3, RET501 2, UP047 1 |
  A fresh clone reports fewer, with skips: `data/` and `runs/` are gitignored.
- **Iterate on the subsets, not the full suite.** `tests/audit` is 0.61 s and `tests/unit` is
  2.09 s; the 143 s figure is dominated by `tests/integration`, which no task here changes.
- The **24** `ruff` count must be unchanged at the end. Run the **full** `ruff check .`, never
  `--select I` — a previous batch introduced a FURB167 by checking only the import rules.

---

## Artifact and network rules — read before touching anything

**`data/` and `runs/` are gitignored in their entirety.** `git ls-files specs/findings data runs`
returns exactly four paths, all under `specs/findings/`: `source-audit.md`,
`source-audit-notes.md`, `source-audit-extracts.csv`, `stage3-plan-audit.md`. Every
`summary.json`, all 175 extracts, and every `runs/<id>/` parquet are local-only.

**This plan regenerates no artifact and needs no network.** Every task is test-only. If you find
yourself about to re-run an audit script, you have misread a task — stop and re-read it.

> ### 🚨 NEVER RUN `scripts/audit/cbp_metadata.py`
>
> Its `main()` is **destructive-first**: `shutil.rmtree(year_dir)` runs for all eight window years
> **before** any fetch. It also requires `CENSUS_API_KEY` and live `api.census.gov`. An offline or
> keyless attempt **deletes 3.6 MB of gitignored, git-unrecoverable extracts and then fails.**
> Nothing in this plan requires it. Task 2 tests `cbp_regime.py`, which is a different script.

> ### 🚨 DO NOT RUN `scripts/audit/cbp_regime.py` EITHER
>
> Task 2 tests it, but never by running it as a script. It is **also destructive-first**
> (`cbp_regime.py:544-549` does `shutil.rmtree` on its own `docs/` and `variables/` directories
> before any fetch) and it fetches six `DOC_URLS` plus a variable definition per flag per year.
> Task 2 drives `main()` **in-process** with `_common.AUDIT_ROOT` monkeypatched to `tmp_path` and
> `_common.build_client` monkeypatched to an `httpx.MockTransport`, so nothing under `data/` and
> nothing on the network is touched. The precedent is
> `tests/audit/test_cbp_metadata.py:674 test_main_wipes_a_year_directory_before_the_probe_can_skip_it`.

**Hand-editing a `summary.json` is forbidden.** `_common.write_summary` is the only writer — it
stamps `generated_utc` itself, so a hand-edited summary carries a timestamp no run ever produced.
`specs/findings/source-audit-notes.md` states the rule: a value "copied by hand into a tracked
document is a transcription defect waiting to happen, and no test compares prose to prose."

**Two tests in this plan read gitignored artifacts and MUST skip when they are absent** (Task 3
Step 5 reads the 460 MB audited bulk archive). The established idiom is
`tests/audit/test_qcew_codes.py:389-400` — resolve the path, `pytest.skip(...)` if it does not
exist. A fresh clone must stay green. Every *other* new test here reads only tracked files or
synthetic data and must never skip.

**A `PYTHONPATH` mutant can be silently shadowed.** Several tasks end with a mutation gate run as
`PYTHONPATH=/tmp/<dir> uv run pytest ...`. Two known traps:
- `scripts/audit/assemble_finding.py:66` does `sys.path.insert(0, str(Path(__file__).parent))`,
  which puts the real `scripts/audit` **ahead of** `PYTHONPATH`. Never run a whole-directory
  `tests/audit` collection for an audit-script mutation gate — alphabetical collection loads
  `test_assemble_finding.py` first and you get a false "no test caught it". Name the one test
  file.
- Stale scratch package copies under `/tmp` from earlier sessions can shadow the real package.
  **Every mutation gate below asserts the mutant is the module actually loaded.** Do not delete
  that assertion to save a line; it is the difference between a gate and a decoration.

---

## What the recon corrected — read this before implementing any item

Each item below was reproduced against the shipped tree at `78d933f` before this plan was
written, then independently re-verified by two adversarial reviewers per item. **Do not implement
the items as literally worded — four of the five are wrong in a way that changes the work.**

**1. Item A is STALE. It was already closed 93 minutes before it was filed.** The item asks for "a
synthetic dict through the reduction". `tests/audit/test_qcew_routes.py:45`
(`test_identical_is_false_when_the_bulk_years_disagree_with_each_other`) and `:61`
(`test_a_bulk_disagreement_is_recorded_rather_than_picked_around`) each pass
`{2017: SHARED, 2018: [*SHARED, "month2_emplvl"]}` — two bulk years whose headers differ, with the
reference year matching the slice exactly, so bulk non-uniformity is the only conjunct driving
`identical` False. `git log -S'def column_parity'` returns `c075e33` (2026-09-04 18:52:22), whose
message says `column_parity` was "extracted from `main()` as a pure function so the fix could be
tested at all"; `git log -S'multi-year bulk-disagreement branch' -- specs/deferred_items.md`
returns `1defbf0` (2026-09-04 20:25:21), a batch bookkeeping commit. The item was drafted against
the pre-`c075e33` inline code and recorded afterwards. A `sys.settrace` line trace over the six
tests confirms every executable line of `column_parity` (`qcew_routes.py:61-86`) is reached,
including `:79`, this item's else arm. **Item A gets no task. It ticks in Task 5 with those two
tests as its witness.** Its *premise* — `bulk_years_required` is `[]` — is still true and is
separately pinned: `scripts/audit/verify_extracts.py:125-128` lists
`("qcew_routes", "bulk_years_required")` first in `LEGITIMATELY_EMPTY_FINDINGS`.

**2. Item C's premise is false, and its literal obligation is satisfiable after all — the item is
wrong in both directions.** It says the bulk branch "is exercised only under a synthetic boundary",
which implies a production path that merely lacks exercise. There is no production bulk path:
- `read_bulk_zip` has **zero callers in `src/`** — only its `def` at `ingest/qcew.py:107` and five
  call sites in `tests/unit/test_qcew_routes.py`.
- `fetch_source`'s bulk arm at `fetching.py:117-118` is **structurally dead for every input**, not
  merely unreached by tests. `probe_slice_boundary` (`qcew.py:72-90`) returns `served[0]`, the
  earliest year drawn from `range(min(window_years) - 5, min(window_years) + 1)`
  (`fetching.py:106`), whose largest element is `min(window_years)`. So
  `boundary <= min(window_years) <= y` for every window year, and `route_for_year(y, boundary)`
  returns `"slice"` unconditionally. No probe outcome reaches the bulk arm.
- `build_harmonized` (`build.py:174-183`) calls `read_slice_csv` unconditionally over
  `snapshot_paths("qcew", raw_root, "*.csv", ...)`. There is no route dispatch on the build side.

And the item's "run against a real bulk download" is **not** unimplementable. The audited archive
is **on disk right now**: `data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip`,
460,476,363 bytes, sha256 `1579539204...5227c`, matching the **tracked** row at
`specs/findings/source-audit-extracts.csv:123`. Gitignored is not absent. Task 3 Step 5 uses it,
skip-if-absent. It buys the one property the 4-member reduced fixture cannot establish: against
the real 2,232 members, `113310` matches exactly 1 and `11331` matches exactly 3 (verified). The
source-side defect becomes a **new deferred item**, not a task here.

**3. Item D's "111 of 360" figure is a conflation of two different numbers, and neither
reproduces.** Its source, `specs/findings/stage3-plan-audit.md:451`, says **108** of 360 take the
`<4` branch and **111** of 360 produce a numerically identical value; the item attributes 111 to
the branch. Against shipped code and current `data/staged` the recon measured 342 cells with a
history, 99 below four shares, 117 identical. The audit predates the partition-based history and
the published-zero fix, and `data/` is gitignored, so its snapshot is unrecoverable. **Do not
restate 111/360 anywhere, and pin no data-derived count in any assertion.** Item D's headline
claim is nonetheless exactly right and bitwise: `historical.py:223-224` is
`if len(shares) < 4: return statistics.median(shares)`, character-identical to
`RollingMedianShare._reduce`'s body at `:196`. Verified: at n=2 and n=3 both return
`0x1.0000000000000p-1`, identical in `float.hex()`.

**4. Item D's `<4` branch is not unreached — it is reached, by a passing test, and
undiscriminated.** `tests/unit/test_baselines_historical.py:78` drives it at three shares and
asserts only `> 0.0` and `== OWN`. The gap is assertions, not reach; an implementer who "verifies"
this item with a coverage tool will close it without writing anything. **Reach counts are
machine-local — quote none of them:** over `tests/unit` alone the arm is entered 9 times (len 1 ×8,
len 3 ×1, never len 2); the several hundred further entries come from
`tests/integration/test_d1_baselines.py`, whose five tests are `skipif`-guarded on `data/staged` and
do not run in a clean clone.

**Item D also mis-attributes itself.** It ends "(Whole-branch review, Minor.)", but the only source
in the repo is `specs/findings/stage3-plan-audit.md:449-455`, tagged **[NIT]** against
`plan:3187-3189` in the **pre-execution** plan audit. Do not carry the parenthetical forward.

**5. Item E's premise holds, and the audit it asks for has now been run.** Task 18's twelve tests
were mutation-audited (24 source mutations). Three real holes came back, all mutation-proven, and
Task 5 closes them. The largest is not in Task 18's file at all: deleting §12.3's `Σ U < R_t`
refusal at `scaling.py:83-87` leaves the **entire suite green**, because the bracket-exhaustion
`for...else` at `:100-103` raises the *same* `InfeasibleResidualError` type and every test asserts
only the type. That `for...else` carries `# pragma: no cover - ... unreachable in practice`; under
the mutant it silently becomes the live path.

**6. Item B is accurate as worded — the only one of the five that is.** Both sub-items were
mutation-proven un-witnessed: reverting `ces_levels.py:180` to `"States {states} publish"` leaves
`tests/audit/test_ces_levels.py` at 37 passed / 3 skipped / **0 failed**, and stripping all three
`if years_available else ""` guards from `cbp_regime.py` leaves all 37 of its tests passing.

---

### Task 1: pin the `ces_levels` "sm.state codes" clause (item B, sub-item 1)

**Files:**
- Test: `tests/audit/test_ces_levels.py` (append; add `import re` to the existing imports)
- Read-only: `scripts/audit/ces_levels.py:142-186`, `specs/findings/source-audit.md`

**Interfaces:**
- Consumes: `ces_levels.broader_code_note(excluded: list[dict], near_miss: list[dict]) -> str`,
  already shipped at `scripts/audit/ces_levels.py:142`. Row shapes, from
  `near_miss_sm_state_codes` at `:111-138` and the existing tests at `:308-315`: an `excluded` row
  is `{"industry_code", "industry_name"}`; a `near_miss` row is
  `{"state_code", "industry_code", "series_id"}`.
- Produces: no source. Three tests.

**Why two and not one.** The clause is prose in a tracked deliverable, and this repo has a recorded
trap for that: a test that asserts the sentence exists pins its letter, not its truth, and keeps
passing after the sentence goes false. Plan 6's Task 1 set the standard — "one pins the sentence,
one pins that it is true of the artifact." Test 1 is the sentence; Test 2 is the truth.

**Why not three.** A third test pinning the *warrant* — that the codes the clause can name come
from a universe wider than `states_dc` — was drafted and then dropped, because it re-hosts coverage
that already exists. `test_publication_level_map_really_does_span_more_than_states_dc`
(`tests/audit/test_ces_levels.py:544`) already asserts
`non_state = coded - set(_common.STATES_DC_FIPS)` is non-empty **and** that it equals
`{row["code"] for row in findings["non_state_codes"]}`; and
`test_near_miss_rows_are_keyed_by_codes_the_publication_map_left_at_none` (`:556`) asserts the
near-miss keying more strongly than a subset check would. Both read the **gitignored** summary via
`_ces_summary()` and therefore skip in a clean clone — that is a real weakness, but it is
skip-proofing, a separate concern from this item, and it belongs in its own deferred item rather
than smuggled in here. **Do not add a third test.**

**What "true" means here.** `sm.state` carries 55 codes; D1's `states_dc` is 51.
`specs/findings/source-audit.md:1635` names `sm.state codes 10, 11, 15, 78`, and `78` is the
Virgin Islands — in `non_state_codes`, not in `_common.STATES_DC_FIPS`. So "States 10, 11, 15, 78"
would be a **false sentence in a tracked deliverable**: it promotes a territory to statehood.

- [x] **Step 1: Confirm the gap by mutation, before writing anything**

```bash
rm -rf /tmp/p3t1 && mkdir -p /tmp/p3t1
cp /Users/lowell/Projects/impute-suppressed-stats/scripts/audit/ces_levels.py /tmp/p3t1/
python3 -c "
import pathlib
p = pathlib.Path('/tmp/p3t1/ces_levels.py'); s = p.read_text()
old = 'sm.state codes {states} publish'
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, 'States {states} publish'))
print('mutant applied')
"
PYTHONPATH=/tmp/p3t1 uv run pytest tests/audit/test_ces_levels.py -q
```

Expected: **37 passed, 3 skipped, 0 failed** — the reword is invisible to the whole file. (The 3
skips are the artifact tests at `:534`/`:544`/`:556`, which resolve the repo from `m.__file__` and
skip when it points at `/tmp`.) Untouched, the same file is **40 passed**.

Name only this file, never the `tests/audit` directory — see the `assemble_finding.py` shadowing
trap in the artifact rules above.

- [x] **Step 2: Write the two failing tests**

Add `import re` to the imports at the top of `tests/audit/test_ces_levels.py`. The file already
imports `json`, `pathlib`, `_common`, `ces_levels as m`, `polars as pl` and `pytest`. **Do not
import `assemble_finding` here** — its `sys.path.insert` at `assemble_finding.py:66` would change
module resolution for the whole session. Use `_common.FINDINGS_DIR`.

Append Test 1 immediately after the existing `broader_code_note` tests (which end at
`tests/audit/test_ces_levels.py:337`):

```python
def test_broader_code_note_calls_them_sm_state_codes_not_states():
    """The clause the docstring at ces_levels.py:148 exists to defend, held by nothing until now:
    reverting it to "States {states}" leaves all 40 tests in this file passing. The sm.state
    universe is wider than D1's states_dc -- 78 is the Virgin Islands -- so "States 78 publish ..."
    promotes a territory to statehood in a tracked deliverable."""
    excluded = [{"industry_code": "15000000", "industry_name": "Mining, Logging and Construction"}]
    near_miss = [{"state_code": "78", "industry_code": "15000000", "series_id": "X1"}]
    note = m.broader_code_note(excluded, near_miss)
    assert "sm.state codes 78 publish" in note
    assert "States 78 publish" not in note
```

Append the helper and Tests 2 and 3 at the end of the file, in the shipped-findings section beside
`test_publication_level_map_really_does_span_more_than_states_dc` (`:544`):

```python
def _ces_findings_from_the_shipped_document() -> dict:
    """The tracked document, not data/raw/audit/ces/summary.json: data/ is gitignored in its
    entirety, so a truth pin written against the summary is a silent skip in a clean clone --
    which is exactly what the `_ces_summary` helper above does."""
    document = (_common.FINDINGS_DIR / "source-audit.md").read_text(encoding="utf-8")
    (ces,) = [
        b for b in re.split(r"^### `", document, flags=re.MULTILINE)[1:] if b.startswith("ces`")
    ]
    return json.loads(ces.split("**findings**:\n\n```json\n", 1)[1].split("\n```", 1)[0])


def test_the_shipped_note_is_recomputable_from_the_findings_it_sits_beside():
    """The sentence pin above holds the clause's letter; this holds that the clause is TRUE of the
    artifact -- the shipped sentence is exactly what broader_code_note returns for the
    excluded_broader_codes and near_miss_sm_state_codes rendered beside it, not a hand-typed
    restatement. A prose pin alone keeps passing on a sentence that has gone false."""
    findings = _ces_findings_from_the_shipped_document()
    recomputed = m.broader_code_note(
        findings["excluded_broader_codes"], findings["near_miss_sm_state_codes"]
    )
    assert recomputed in findings["notes"]
```

`findings["notes"]` is a single joined string (`ces_levels.py:463` builds it with `" ".join(...)`),
so `recomputed in findings["notes"]` is a substring test, not a membership test over a list. Both
tests were run against the shipped tree while this plan was written: `notes` is a `str`,
`recomputed in notes` is `True`, and Test 1's two assertions hold.

Do **not** build the truth pin by regexing the clause back out of the notes string. That couples
both tests to the same words, so a reword fails them for the same reason and the pair proves
nothing the sentence pin did not already prove. Recompute the sentence from the findings instead,
as above.

- [x] **Step 3: Run them against the shipped tree**

Run: `uv run pytest tests/audit/test_ces_levels.py -q`
Expected: **42 passed** (40 + 2).

- [x] **Step 4: Mutation gate — confirm the new tests actually fail on the reword**

```bash
PYTHONPATH=/tmp/p3t1 uv run pytest tests/audit/test_ces_levels.py -q 2>&1 | tail -5
```

Expected: **2 failed** — `test_broader_code_note_calls_them_sm_state_codes_not_states` and
`test_the_shipped_note_is_recomputable_from_the_findings_it_sits_beside`. Both were run against
this exact mutant while the plan was written and both go red.

If either passes here, the mutant was shadowed rather than loaded. Note that `/tmp/p3t1` must hold
`ces_levels.py` **alone** for the truth pin to be mutation-testable: `_common.FINDINGS_DIR` derives
from `_common.__file__` (`_common.py:38-40`), so copying `_common.py` into the mutant directory
points the pin at a findings directory that does not exist. Copy only `ces_levels.py` and let
`_common` resolve to the real one via `tests/conftest.py`'s path append.

- [x] **Step 5: Commit**

```bash
rm -rf /tmp/p3t1
git add tests/audit/test_ces_levels.py
git commit -m "test(audit): hold the ces_levels sm.state-codes clause, and hold that it is true

Reverting the clause to \"States {states} publish\" left all 40 tests in the file green.
One test pins the sentence; one recomputes it from the findings it sits beside, so the
pair fails when the clause goes false rather than only when it goes missing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: pin `cbp_regime`'s empty-`max()` guard (item B, sub-item 2)

**Files:**
- Test: `tests/audit/test_cbp_regime.py` (append; add `import json` and `import httpx`)
- Read-only: `scripts/audit/cbp_regime.py:524-673`

**Interfaces:**
- Consumes: `cbp_regime.main()`. The file already imports `_common as c`, `cbp_regime as m` and
  `pytest`.
- Produces: no source. One test plus one module-level helper.

**The item says "no pure seam" and that is literally true — but it does not follow that the guard
is untestable.** The three guards are at `cbp_regime.py:617` (`latest_year`), `:632`
(`published_start`, with `min`) and `:633` (`published_end`); `:617` and `:633` are the *identical*
right-hand expression `str(max(years_available)) if years_available else ""`. All three live inside
`main()`, and no test in `tests/audit/test_cbp_regime.py` drives `main()`.

**Recommendation: do NOT extract a helper.** Deduplicating the expression would be a source change
to a script whose `main()` cannot be re-run without the network, in a batch that is otherwise
test-only, to save one line. Drive `main()` instead — it is drivable offline, and there is
precedent at `tests/audit/test_cbp_metadata.py:674`.

**What the guard is for.** The comment at `cbp_regime.py:613-616` says it: an unguarded `max([])`
raises `ValueError` **before** `write_summary` can record the very outcome the empty case exists to
report. The script would die instead of documenting that no window year returned a dataset
document.

- [x] **Step 1: Confirm the gap by mutation**

```bash
rm -rf /tmp/p3t2 && mkdir -p /tmp/p3t2
cp /Users/lowell/Projects/impute-suppressed-stats/scripts/audit/cbp_regime.py /tmp/p3t2/
cp /Users/lowell/Projects/impute-suppressed-stats/scripts/audit/_common.py /tmp/p3t2/
python3 -c "
import pathlib
p = pathlib.Path('/tmp/p3t2/cbp_regime.py'); s = p.read_text()
n = s.count(' if years_available else \"\"')
assert n == 3, n
p.write_text(s.replace(' if years_available else \"\"', ''))
print('mutant applied: 3 guards stripped')
"
PYTHONPATH=/tmp/p3t2 uv run pytest tests/audit/test_cbp_regime.py -q
```

Expected: **37 passed** — every shipped test passes with all three guards removed.

- [x] **Step 2: Write the failing test**

Add `import json` and `import httpx` to `tests/audit/test_cbp_regime.py`. Add this module-level
helper and test:

```python
def _meta(years: list[int], probe: dict[str, int]) -> dict:
    """A minimal cbp_metadata summary shaped as cbp_regime.main() reads it: findings for the two
    keys it branches on, and the coverage_span fields it copies through at cbp_regime.py:637-638."""
    return {
        "source": "cbp_metadata",
        "generated_utc": "2026-01-01T00:00:00Z",
        "coverage_span": {
            "window_start": c.WINDOW_START,
            "window_end": c.WINDOW_END,
            "covered": "",
            "uncovered": "2017-2024",
        },
        "access": {"status": "verified"},
        "extracts": [],
        "findings": {"years_available": years, "dataset_probe_status_by_year": probe},
    }


def test_main_writes_empty_published_bounds_when_no_window_year_is_available(tmp_path, monkeypatch):
    """The guard at cbp_regime.py:617 and :633. Unguarded, `max([])` raises ValueError before
    write_summary can record the very outcome the empty case exists to report -- the script would
    die instead of documenting that no window year returned a dataset document. Removing either
    guard makes this fail; :617 raises first."""
    monkeypatch.setattr(c, "AUDIT_ROOT", tmp_path)
    monkeypatch.setenv("CENSUS_API_KEY", "placeholder-key-never-sent-anywhere")
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "audit-suite@example.invalid")
    (tmp_path / "cbp_metadata").mkdir(parents=True)
    (tmp_path / "cbp_metadata" / "summary.json").write_text(
        json.dumps(_meta([], {})), encoding="utf-8"
    )
    monkeypatch.setattr(
        c,
        "build_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html/>"))
        ),
    )

    m.main()

    written = json.loads((tmp_path / "cbp_regime" / "summary.json").read_text(encoding="utf-8"))
    assert written["coverage_span"]["published_start"] == ""
    assert written["coverage_span"]["published_end"] == ""
```

**Assert nothing else.** In particular do not also assert on `findings["emp_n_f_caveat"]`'s opening
words — that is an incidental prose pin on an unrelated sentence and would break on a reword that
has nothing to do with this guard.

**One test covers all three guard sites.** With `years_available == []`, `:617` raises first; a
mutant that strips only `:632`/`:633` and leaves `:617` intact fails the same test with
`ValueError: min() iterable argument is empty` at `:632`. Both were run separately — the
all-three-stripped mutant alone does **not** establish the `:632`/`:633` case, because `:617`
raises before the interpreter reaches it.

**Why `years_available == []` and not a populated list.** The blanket "200 for everything"
`MockTransport` is sufficient **only** for the empty case. With a non-empty `years_available`,
`fetch_variable_definition` (`cbp_regime.py:506-522`) calls `resp.json()` and catches only
`httpx.HTTPStatusError`, so a `200` carrying `b"<html/>"` raises `JSONDecodeError`. If you extend
this test to a populated year list, the transport must return JSON on the variables URLs. Keep the
test to the empty case; it is the case the guard exists for.

**The two `setenv` lines, accurately.** `CENSUS_API_KEY` is load-bearing:
`_common.assert_no_secrets_bytes` scans recorded bytes for the value of each `SECRET_ENV_VARS`
entry, so a placeholder neutralises a developer's real exported key. `BLS_CONTACT_EMAIL` is **not**
load-bearing here — `_common.contact_email()` is only reached through `build_client`, which this
test replaces with a lambda. Verified: with both variables unset and both `setenv` lines deleted,
the test still passes. Keep it anyway for symmetry with the `test_cbp_metadata.py:674` precedent,
but do not repeat a rationale that is false for this test.

**Two things this test must not trip.** `cbp_regime.py:531-538` raises `RuntimeError` outright if
`2024 in years_available` **or** `probe_status.get("2024") == 200` — two trigger conditions, not
one. `_meta([], {})` satisfies neither. And `_common.write_summary` validates
`coverage_span.window_start`/`window_end` against `c.WINDOW_START`/`c.WINDOW_END`
(`_common.py:384-387`), which is why the helper copies them rather than inventing values.

- [x] **Step 3: Run it against the shipped tree**

Run: `uv run pytest tests/audit/test_cbp_regime.py -q`
Expected: **38 passed**.

Also confirm nothing escaped the `tmp_path` sandbox:
`git status --porcelain` (empty) and `ls data/raw/audit/cbp_regime` (unchanged: `docs`,
`variables`, `summary.json`).

- [x] **Step 4: Mutation gate**

```bash
PYTHONPATH=/tmp/p3t2 uv run pytest tests/audit/test_cbp_regime.py -q 2>&1 | tail -12
```

Expected: **1 failed** with `ValueError: max() iterable argument is empty` raised from
`/tmp/p3t2/cbp_regime.py:617`. Confirm the traceback names `/tmp/p3t2/`, not `scripts/audit/` — if
it names the real path the mutant was shadowed.

- [x] **Step 5: Commit**

```bash
rm -rf /tmp/p3t2
git add tests/audit/test_cbp_regime.py
git commit -m "test(audit): drive cbp_regime.main() offline to hold the empty-max guard

All three guards could be stripped with every one of the 37 existing tests still green.
main() is driven in-process with AUDIT_ROOT and build_client monkeypatched, per the
precedent in test_cbp_metadata.py:674 -- the script itself is destructive-first and is
never run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: exercise the QCEW bulk ingest chain, including against the real archive (item C)

**Files:**
- Test: `tests/unit/test_qcew_routes.py` (append; add `import json`, `import re`)
- Read-only: `src/logging_employment/ingest/qcew.py`, `specs/findings/source-audit.md`,
  `specs/findings/source-audit-extracts.csv`

**Interfaces:**
- Consumes: `qcew.route_for_year(year: int, earliest_slice_year: int) -> Literal["slice","bulk"]`
  (`:102`); `qcew.bulk_url(year: int) -> str` (`:97`);
  `qcew.read_bulk_zip(raw: bytes, industry: str) -> pl.DataFrame` (`:107`);
  `qcew.read_slice_csv(raw: bytes) -> pl.DataFrame` (`:62`);
  `qcew.parse_qcew_monthly(frame, *, snapshot_id, release_vintage, release_status, naics_vintage)`
  (`:200`); `qcew.apply_universe_filter(frame) -> pl.DataFrame` (`:295`).
- Existing module-level names in the test file: `FIXTURE` (`slice_2017q1.csv`), `BULK`
  (`bulk_2017.zip`), `TARGET_MEMBER`, `_fetcher`, and the imports `constants`, `qcew`,
  `HttpFetcher`, `hashlib`, `io`, `zipfile`, `Path`, `httpx`, `pl`, `pytest`.
- Produces: no source. Four tests.

**Read "What the recon corrected" §2 first.** The narrowed obligation this task takes, and what it
leaves open, is stated there. Paste this line into the tick note in Task 5:

> These tests run the bulk ingest chain over the real audited archive's bytes where that archive is
> present, and over the byte-identical reduced member always; what they do not prove is that any
> production caller composes them, because `read_bulk_zip` has no caller in `src/` and
> `build_harmonized` reads only `*.csv` through `read_slice_csv`.

**Do not write any of these at `fetch_source` level.** It cannot reach the bulk arm (see §2), and a
test that asserts a `MockTransport` request count would pin `probe_slice_boundary`'s full-sweep
behaviour and foreclose the early exit contemplated by the separate open item at
`specs/deferred_items.md:232`. Keep everything at the ingest-function level: bytes in, frame out.
`tests/unit/test_qcew_routes.py:35-42` already asserts the returned boundary value and not a
request count — preserve that.

**Do not write the literal `2014` into `src/logging_employment/ingest/qcew.py`.**
`test_boundary_probe_does_not_hard_code_a_year` (`:45-50`) greps that module's source for it. Step
4 reads the boundary from the tracked findings document at runtime, which is also why it is the
right form on the merits.

- [x] **Step 1: Write the cross-route equality test**

Append to `tests/unit/test_qcew_routes.py`:

```python
def _parsed(raw_frame: pl.DataFrame) -> pl.DataFrame:
    """Both routes through the same normalization, so the comparison is of data and not of
    call arguments."""
    return qcew.apply_universe_filter(
        qcew.parse_qcew_monthly(
            raw_frame,
            snapshot_id="fixture",
            release_vintage="2026-09-05",
            release_status="final",
            naics_vintage="2017",
        )
    )


def test_the_bulk_route_yields_the_same_rows_as_the_slice_route() -> None:
    """The two routes are alternatives for the same data, and nothing composed them end to end
    until now: route_for_year and read_bulk_zip were each tested alone, and read_bulk_zip's output
    had never been fed to parse_qcew_monthly anywhere in the suite. Asserts the rows agree, not
    merely that the chain ran -- a smoke chain would pass without testing what its name claims."""
    assert qcew.route_for_year(2017, earliest_slice_year=2020) == "bulk"

    bulk = _parsed(qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE))
    slice_ = _parsed(qcew.read_slice_csv(FIXTURE.read_bytes()))

    # The bulk member carries q1-q4 in one file; the slice fixture is one quarter.
    bulk_q1 = bulk.filter(pl.col("reference_month") <= "2017-03")
    assert bulk_q1.height == slice_.height

    joined = bulk_q1.join(slice_, on=["area_fips", "reference_month"], how="inner", suffix="_s")
    assert joined.height == slice_.height
    for column in ("employment_value", "observation_status", "source_row_hash"):
        assert joined.filter(pl.col(column) != pl.col(f"{column}_s")).height == 0
```

Assert on the *filtered* counts only. `apply_universe_filter` cuts the bulk side from 21,720 rows
to 600 and the slice side from 5,430 to 150; a pre-filter count pins a number that means nothing.
Note also that the 600 filtered bulk rows span 50 areas and `US000` is one of them — `11000` (DC)
and `38000` (ND) are absent on **both** routes. Do not assert 51 or 52.

- [x] **Step 2: Close `bulk_url`'s zero coverage**

`bulk_url` is the one function in the trio with no test at all — only its `def` line executes, at
import. Mirror `test_slice_url_interpolates_year_quarter_and_industry` (`:29-32`):

```python
def test_bulk_url_interpolates_the_reference_year() -> None:
    """The third function of the bulk trio, and the only one no test called: route_for_year's bulk
    outcome and read_bulk_zip were both asserted, bulk_url never was."""
    assert (
        qcew.bulk_url(2017)
        == "https://data.bls.gov/cew/data/files/2017/csv/2017_qtrly_by_industry.zip"
    )
```

- [x] **Step 3: Run steps 1-2**

Run: `uv run pytest tests/unit/test_qcew_routes.py -q`
Expected: **13 passed** (11 + 2).

> Deviation: actual **14 passed**. The file held 12 tests at `78d933f`, not 11; the plan
> miscounted the baseline. Both new tests pass.

- [x] **Step 4: Make the item's own condition self-monitoring**

The item ends in a condition — "if the boundary ever moves past a window year, treat that path as
unproven". Prose conditions are not re-read. Derive it instead, from the tracked findings document,
so a re-audit that moves the boundary turns this red on its own:

```python
def _qcew_routes_findings() -> tuple[dict, dict]:
    """The tracked findings document, not data/raw/audit/: data/ is gitignored in its entirety, so
    a boundary pin written against the summary is a silent skip in a clean clone."""
    document = (
        Path(__file__).resolve().parents[2] / "specs" / "findings" / "source-audit.md"
    ).read_text(encoding="utf-8")
    (block,) = [
        b
        for b in re.split(r"^### `", document, flags=re.MULTILINE)[1:]
        if b.startswith("qcew_routes`")
    ]

    def fenced(label: str) -> dict:
        return json.loads(block.split(f"**{label}**:\n\n```json\n", 1)[1].split("\n```", 1)[0])

    return fenced("findings"), fenced("coverage_span")


def test_every_window_year_still_routes_to_the_slice_endpoint() -> None:
    """Derived, not typed: the measured boundary and the window both come out of the tracked
    findings document at runtime, so a re-audit that moves the boundary past a window year turns
    this red instead of leaving a prose condition nobody re-reads. What production would then do is
    not take the bulk route -- probe_slice_boundary would face an all-404 candidate range and raise
    ValueError -- which is why this is a monitor and not a coverage claim."""
    findings, span = _qcew_routes_findings()
    earliest = int(findings["earliest_year_served"])
    window = range(int(span["window_start"][:4]), int(span["window_end"][:4]) + 1)

    assert findings["bulk_years_required"] == []
    assert {qcew.route_for_year(year, earliest) for year in window} == {"slice"}
```

Verified against the shipped document while this plan was written: the parse yields
`earliest_year_served = 2014`, `bulk_years_required = []`, window `2017-01`–`2024-12`, and every
year in 2017–2024 routes to `"slice"`.

- [x] **Step 5: Run the chain against the real audited archive, skip-if-absent**

This is the one deliverable that answers the item's own words — "the branch having run end-to-end
against a real bulk download" — and it needs no network. The archive is on disk and its digest is
tracked. It buys what the 4-member fixture cannot: the unanchored-substring selector's uniqueness
against 2,232 real members.

```python
REAL_BULK = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "raw"
    / "audit"
    / "qcew_routes"
    / "bulk"
    / "2017_qtrly_by_industry.zip"
)


def _recorded_digest() -> str:
    """From the tracked extracts manifest, never hard-coded: a typed digest is a transcription
    defect, and this one is 64 characters of it."""
    rows = (
        Path(__file__).resolve().parents[2] / "specs" / "findings" / "source-audit-extracts.csv"
    ).read_text(encoding="utf-8").splitlines()
    (row,) = [
        r
        for r in rows
        if r.startswith("qcew_routes,") and "bulk/2017_qtrly_by_industry.zip," in r
    ]
    return row.split(",")[3]


@pytest.mark.slow
def test_the_member_selector_is_unique_in_the_real_archive_not_just_the_fixture() -> None:
    """tests/fixtures/qcew/README.md concedes of the unanchored substring selector that the target
    "really is unique here -- but that is a fact about this data, not a guarantee from the code."
    A four-member fixture cannot establish otherwise; the 2,232-member archive can. Skips where the
    gitignored archive is absent, per the tests/audit/test_qcew_codes.py:389 idiom."""
    if not REAL_BULK.exists():
        pytest.skip(f"{REAL_BULK} not present; run scripts/audit/qcew_routes.py first")

    raw = REAL_BULK.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == _recorded_digest()

    names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    assert len(names) == 2232
    assert len([n for n in names if constants.INDUSTRY_CODE in n]) == 1
    assert len([n for n in names if "11331" in n]) == 3

    real = qcew.read_bulk_zip(raw, constants.INDUSTRY_CODE)
    assert real.equals(qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE))

    with pytest.raises(ValueError):
        qcew.read_bulk_zip(raw, "11331")
```

All four counts were verified while this plan was written: 460,476,363 bytes, digest
`1579539204...5227c` matching `source-audit-extracts.csv:123`, 2,232 members, `113310` matching 1
and `11331` matching 3.

The final `.equals` is the strongest fidelity statement available and is why the earlier tests are
not weakened by using the reduced fixture: only the **container** was reduced, not the data — the
target member's bytes are identical in both (already pinned by digest at
`tests/unit/test_qcew_routes.py:96`).

`slow` is already a registered marker (`pyproject.toml:67`, "takes more than a few seconds"), so
the decorator needs no config change. It is not excluded from the default run — it is a label, and
this test is about a second of zip-directory reads.

- [x] **Step 6: Run the whole file, then confirm the skip path**

```bash
uv run pytest tests/unit/test_qcew_routes.py -q
```
Expected: **15 passed** (11 + 4).

> Deviation: actual **16 passed**, same off-by-one baseline miscount. All four new tests pass,
> including the real-archive one — the 460 MB archive is present on this machine.

Confirm the skip-if-absent branch works without moving the archive — point the resolver at a
missing path in a throwaway subprocess:

```bash
uv run python -c "
import pathlib, sys
sys.path.insert(0, 'tests/unit')
import test_qcew_routes as t
print('archive present:', t.REAL_BULK.exists())
print('digest row parses:', len(t._recorded_digest()) == 64)
"
```

- [x] **Step 7: Commit**

```bash
git add tests/unit/test_qcew_routes.py
git commit -m "test(ingest): compose the bulk chain, and run it against the real audited archive

route_for_year and read_bulk_zip were each tested alone and never composed; bulk_url had
no test at all. Adds the cross-route row-equality chain, a bulk_url pin, a findings-derived
monitor that reddens if the measured boundary ever moves past a window year, and a
skip-if-absent pass over the 2,232-member audited archive for the member-selector
uniqueness a four-member fixture cannot establish.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: discriminate §10.3's five share variants (item D)

**Files:**
- Test: `tests/unit/test_baselines_historical.py` (append)
- Modify: `src/logging_employment/baselines/historical.py:211-217` (class docstring only)

**Interfaces:**
- Consumes: the five variant classes already imported at the top of the test file
  (`LastObservedShare`, `SameMonthPreviousYearShare`, `RollingMedianShare`,
  `ExponentiallyWeightedShare`, `BreakAdjustedShare`), the `ALL_FIVE` list, `Anchor`, `OWN`, and
  the file's own `_context(monthly, cfg)` helper (`:71`) plus the `make_monthly` and
  `appendix_a_config` fixtures.
- Produces: no new source symbol. Three tests and one reworded docstring.

**Scope ruling.** The `<4` threshold itself is **not** changed here. Moving it would push 99 of 342
cells in the shipped D1 run from `OWN` to `FALLBACK` and would re-pin the frozen golden parquet —
a design change, filed as a new deferred item in Task 5, not a test-coverage fix.

**Five traps, all measured. Read them before writing a fixture.**
1. **Do not reuse the `_history` fixture** (`tests/unit/test_baselines_historical.py:34`). It
   yields a 3-month history on which the five variants produce only **three** distinct numbers —
   `last == smpy == 42.0` and `median == break == 41.0`. It is precisely the wrong shape. The new
   test needs its own ≥4-share, break-bearing history spanning ≥13 months.
2. **Build fixtures from integer employment over an integer national total.** On tenths, e.g.
   `[0.1, 0.2, 0.3, 0.4]`, the three steps are `0.1`, `0.09999999999999998` and
   `0.10000000000000003`, so the argmax lands on the *last* step, the segment is one point, and
   `break == last`. A fixture built from tenths behaves randomly.
3. **A history that breaks down to zero silently tests the wrong arm.** `reduced > 0.0` at
   `historical.py:151` drops the cell and flips the basis to `FALLBACK`, so the assertion lands on
   `establishment_fallback_in_employees` while its author believes it is testing the reducer.
4. **Assert the five values individually, then distinctness — not distinctness alone.** The
   twelve-month span exists so `SameMonthPreviousYearShare` can resolve `2023-03`. If
   `historical_lookback_months` (`config.yaml:62-63`, currently 24) ever drops below 12, `smpy`
   returns `None` and a bare distinctness assert fails for a **config** reason wearing a collapse
   reason's clothes. This repo already shipped one vacuous test of that family
   (`stage3-plan-audit.md:440`).
5. **`segment = shares[cut:] or shares` (`historical.py:227`) is unreachable by construction.** For
   n ≥ 4, `steps` has n−1 entries and `steps.index(max(...))` is in `[0, n-2]`, so `cut` is in
   `[1, n-1]` and `shares[cut:]` always has at least one element. **Budget no test for it** — a
   branch-coverage chase will burn the task. It is filed as a new deferred item in Task 6.
6. **Do not write a discrimination test over `baseline_results` or the tracked golden.** That is the
   most natural reading of "nothing detects two variants computing the same number", and it cannot
   be written as an inequality: in the golden's 138 reconciled cells all five share variants produce
   the identical `estimate` on 105, because in a month where no missing cell has an own history
   every §10.3 variant *is* §10.2's estimator, numerically and by design. The discrimination test
   belongs at the `weights` level on a fixture where the missing cell carries an own history — which
   is what Step 2 builds.

- [x] **Step 1: Confirm the collapse is bitwise, and that nothing detects it**

```bash
uv run python -c "
from logging_employment.baselines.historical import RollingMedianShare, BreakAdjustedShare
r, b = RollingMedianShare(), BreakAdjustedShare()
for sh in ([0.4, 0.6], [0.4, 0.5, 0.9], [0.10, 0.11, 0.90]):
    x, y = r._reduce(sh, None, None), b._reduce(sh, None, None)
    print(len(sh), x.hex(), y.hex(), x.hex() == y.hex())
"
grep -rn "share_break_adjusted\|share_rolling_median" tests/ src/ | grep -v historical.py
```

Expected: `True` on all three rows, and the `grep` returns **nothing** — no test anywhere in the
repo compares two variants' numbers. `test_section_10_3_ships_exactly_five_variants`
(`tests/unit/test_baselines_historical.py:28-31`) asserts only `len(ALL_FIVE) == 5` and five
distinct `estimator_id`s.

- [x] **Step 2: Write the discrimination test**

Append to `tests/unit/test_baselines_historical.py`:

Row shape matters and is easy to get wrong: `make_monthly` fills from `_MONTHLY_DEFAULTS`
(`tests/unit/conftest.py`), so a national row must override `area_type`, `area_fips`, `state_fips`
and `aggregation_level`, and `area_fips` is the **five-digit** form (`"01000"`, not `"01"`) while
the anchor's `missing_cells` uses the bare `state_fips` (`"01"`). Copy `_history`'s shape at
`tests/unit/test_baselines_historical.py:34-68` rather than inventing one. Both helpers below were
executed green before being written here.

```python
def _share_rows(months: list[str], employment: list[int]) -> list[dict]:
    """A national row and one state-01 row per month, then the suppressed anchor month. Integer
    employment over an integer national total, because on tenths the largest-step argmax is decided
    by float noise: on [0.1, 0.2, 0.3, 0.4] the steps are 0.1, 0.09999999999999998 and
    0.10000000000000003, so the cut lands last and the segment is one point."""
    rows: list[dict] = []
    for month, value in zip(months, employment, strict=True):
        rows.append(
            {
                "area_type": "national",
                "area_fips": "US000",
                "state_fips": None,
                "aggregation_level": "18",
                "reference_month": month,
                "employment_value": 1000,
                "qtrly_establishments": 100,
            }
        )
        rows.append(
            {
                "state_fips": "01",
                "area_fips": "01000",
                "reference_month": month,
                "employment_value": value,
                "qtrly_establishments": 4,
                "observation_status": "observed",
            }
        )
    rows.append(
        {
            "area_type": "national",
            "area_fips": "US000",
            "state_fips": None,
            "aggregation_level": "18",
            "reference_month": "2024-03",
            "employment_value": 1000,
            "qtrly_establishments": 100,
        }
    )
    rows.append(
        {
            "state_fips": "01",
            "area_fips": "01000",
            "reference_month": "2024-03",
            "employment_value": None,
            "qtrly_establishments": 4,
            "observation_status": "suppressed",
        }
    )
    return rows


def _breaking_history(make_monthly) -> pl.DataFrame:
    """Twelve months of history plus the anchor month, with a level break between month 8 and
    month 9. Twelve so SameMonthPreviousYearShare can resolve 2023-03; a break in the interior so
    BreakAdjustedShare's segment has more than one point; state 02 disclosed at the anchor month so
    the establishment fallback has an intensity if a variant declines."""
    months = [f"2023-{m:02d}" for m in range(3, 13)] + ["2024-01", "2024-02"]
    rows = _share_rows(months, [20, 10, 11, 9, 10, 11, 9, 10, 30, 31, 29, 34])
    rows.append(
        {
            "state_fips": "02",
            "area_fips": "02000",
            "reference_month": "2024-03",
            "employment_value": 800,
            "qtrly_establishments": 80,
            "observation_status": "observed",
        }
    )
    return make_monthly(*rows)


def test_the_five_variants_compute_five_different_numbers_on_one_history(
    make_monthly, appendix_a_config
) -> None:
    """test_section_10_3_ships_exactly_five_variants checks that five estimator ids exist; nothing
    checked that five estimators exist. Below four shares BreakAdjustedShare is bitwise identical
    to RollingMedianShare, and the suite's only all-variants fixture is a three-month history on
    which the five produce three distinct numbers -- so a duplicate variant was undetectable."""
    monthly = _breaking_history(make_monthly)
    context = _context(monthly, appendix_a_config)
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")

    values = {}
    for cls in ALL_FIVE:
        out = cls().weights(context, anchor)
        assert out.basis["01"] == OWN, f"{cls.__name__} fell back; fix the fixture, not this"
        values[cls().estimator_id] = out.values["01"]

    # Stated as arithmetic over the fixture's own numbers, so a failure names the culprit rather
    # than reporting that five numbers stopped being five numbers.
    assert values["share_last_observed"] == pytest.approx(34.0)
    assert values["share_same_month_prior_year"] == pytest.approx(20.0)
    assert values["share_rolling_median"] == pytest.approx(11.0)
    assert values["share_break_adjusted"] == pytest.approx(30.5)
    assert len(set(values.values())) == 5
```

`share_break_adjusted` is `30.5` because the largest single step is `10 -> 30`, so the segment is
`[30, 31, 29, 34]` and its median is `(30 + 31) / 2`. `share_exponentially_weighted` is deliberately
left unpinned — it is held by the distinctness assertion, and pinning
`19.280980144966627` would be a magic constant with no arithmetic story.

Run against the shipped tree while this plan was written, the five values came back exactly:
`{last: 34.0, smpy: 20.0, median: 11.0, ewma: 19.280980144966627, break: 30.5}` — five distinct
numbers, all on basis `OWN`.

- [x] **Step 3: Pin the `<4` collapse as intentional current behaviour**

**Say "current", never "intentional".** Task 6 files a deferred item arguing the `<4` fallback is a
design choice nobody chose; a test in this batch that ratifies it as intended would contradict that
item and have to be undone when it is taken up. Pin the behaviour, describe the mechanism, and stop
there.

**Derive the counterfactual, do not narrate it.** A docstring sentence like "the post-break median
would have been 90.0" is a number returned by no function — the exact prose-pin trap this batch
exists to close. The third assertion gets 90.0 out of `LastObservedShare` instead.

```python
def test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median(
    make_monthly, appendix_a_config
) -> None:
    """Documents the degeneracy rather than hiding it, and takes no position on whether it is
    right: with three shares there is no segment to split, so the variant returns the whole-history
    median and ignores a violent break at the most recent observation. The deferred item that
    revisits the threshold must change this test."""
    monthly = make_monthly(*_share_rows(["2023-12", "2024-01", "2024-02"], [10, 11, 90]))
    context = _context(monthly, appendix_a_config)
    anchor = Anchor("2024-03", 50.0, ("01",), "declared_national_total")

    broken = BreakAdjustedShare().weights(context, anchor).values["01"]
    median = RollingMedianShare().weights(context, anchor).values["01"]
    assert broken == median
    assert broken == pytest.approx(11.0)
    # The break this variant exists to follow is derived, not asserted in prose: the most recent
    # observation is 90, and a variant that segmented on it would return that instead of 11.
    assert LastObservedShare().weights(context, anchor).values["01"] == pytest.approx(90.0)
```

- [x] **Step 4: Run steps 2-3**

Run: `uv run pytest tests/unit/test_baselines_historical.py -q`
Expected: all pass, count = the file's current total + 2.

If `test_the_five_variants...` fails on the `basis == OWN` assertion, the anchor's `missing_cells`
or the suppressed row is wrong — fix the fixture, never weaken the assertion (trap 3).

- [x] **Step 5: Reword the docstring the new test contradicts**

`src/logging_employment/baselines/historical.py:216` currently ends:

> A plain median over the whole lookback is what this variant exists NOT to be.

That sentence is **false below four shares** — which Step 3 now asserts is exactly what happens.
Shipping Step 3 while leaving line 216 alone would leave the module contradicting its own suite.
That, and not "zero behaviour change", is why this reword is in scope. Replace the class docstring
at `historical.py:211-217` with:

```python
class BreakAdjustedShare(_ShareBaseline):
    """§10.3 variant 5: robust to a level break in the share series.

    Uses the median of the most recent segment after the largest single-step change, so one
    reclassification or one plant closure does not drag the estimate toward a regime that ended.
    At four or more shares this is not a plain median over the whole lookback; below four it is
    exactly that, because a segment split needs points on both sides.
    """
```

- [x] **Step 6: Pin the reworded sentence, and let Steps 2-3 be the pin that it is true**

This is Plan 6's two-test shape. Steps 2 and 3 already hold the *behaviour* — the sentence's two
clauses are exactly what they assert — so only the sentence pin is missing:

> Deviation: the assertion as planned FAILED on the shipped tree. `below four it is exactly that`
> spans a line break in the reworded docstring, so the raw substring is not present. Shipped
> whitespace-normalized instead — `" ".join(BreakAdjustedShare.__doc__.split())` — which is also
> the better pin: re-wrapping the docstring should not redden a test about its claim.

```python
def test_the_break_adjusted_docstring_scopes_its_own_claim() -> None:
    """The sentence half of the pair: the two tests above hold that the claim is TRUE, this holds
    that the claim is still MADE. Before this batch the docstring said a plain median "is what this
    variant exists NOT to be", full stop, which is false on every history shorter than four."""
    doc = BreakAdjustedShare.__doc__
    assert "below four it is exactly that" in doc
    assert "At four or more shares this is not a plain median" in doc
```

- [x] **Step 7: Mutation gate**

```bash
rm -rf /tmp/p3t4 && mkdir -p /tmp/p3t4
cp -R /Users/lowell/Projects/impute-suppressed-stats/src/logging_employment /tmp/p3t4/
python3 -c "
import pathlib
p = pathlib.Path('/tmp/p3t4/logging_employment/baselines/historical.py'); s = p.read_text()
old = '''        if len(shares) < 4:
            return statistics.median(shares)
        steps = [abs(shares[i + 1] - shares[i]) for i in range(len(shares) - 1)]
        cut = steps.index(max(steps)) + 1
        segment = shares[cut:] or shares
        return statistics.median(segment)'''
assert s.count(old) == 1, s.count(old)
p.write_text(s.replace(old, '        return statistics.median(shares)'))
print('mutant applied: BreakAdjustedShare collapsed into RollingMedianShare everywhere')
"
PYTHONPATH=/tmp/p3t4 uv run python -c "
import logging_employment, inspect
from logging_employment.baselines.historical import BreakAdjustedShare
assert '/tmp/p3t4/' in logging_employment.__file__, logging_employment.__file__
assert 'steps.index' not in inspect.getsource(BreakAdjustedShare)
print('mutant is the module actually loaded')
"
PYTHONPATH=/tmp/p3t4 uv run pytest tests/unit/test_baselines_historical.py -q 2>&1 | tail -5
```

Expected: `test_the_five_variants_compute_five_different_numbers_on_one_history` **fails** —
`share_break_adjusted` comes back `11.0` instead of `30.5` and the distinctness assert drops to 4.
`test_below_four_shares_...` still passes, correctly: it pins behaviour the mutant preserves.

The identity assertion in the middle command is not optional. A stale `logging_employment` copy
under `/tmp` from an earlier session will otherwise shadow the real package and report a
false pass.

- [x] **Step 8: Commit**

```bash
rm -rf /tmp/p3t4
git add tests/unit/test_baselines_historical.py src/logging_employment/baselines/historical.py
git commit -m "test(baselines): discriminate the five share variants, and scope variant 5's claim

Below four shares BreakAdjustedShare returns statistics.median(shares), bitwise identical
to RollingMedianShare, and the only test over all five checked that five estimator ids
exist. Adds a twelve-month break-bearing history on which all five differ, pins the short
history collapse as current behaviour, and rewords the docstring that claimed the variant
is never a plain median -- a claim the new test proves false.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: close §17.3's three mutation-proven holes (item E)

**Files:**
- Modify: `tests/unit/test_scaling.py:80` (add `match=`)
- Modify: `tests/unit/test_reconcile_properties.py:117-131` (split the two anchors, add `match=`),
  `:188-189` (tighten property 5's tolerance)
- Test: `tests/unit/test_reconcile_properties.py` (append two tests),
  `tests/unit/test_integerize.py` (append one)

**Interfaces:**
- Consumes: `scale_into_bounds`, `Bounds`, `kl_project`, `constraint_violation`,
  `reconcile_matrix`, `InfeasibleResidualError`, `Anchor` — all already imported by the two files,
  plus the module-level `SEED`, `TOL`, `ITERS`, `FLOOR`, `TRIALS` constants
  (`test_reconcile_properties.py:26-30`) and the `_cells(n)` / `_weights(cells, rng)` helpers
  (`:33-39`). **There is no `_bounds()` helper** — bounds are built inline as
  `Bounds(lower=..., upper=...)`. `_cells` already returns a tuple, so `Anchor`'s third argument
  takes `cells` directly, never `tuple(cells)`.
- `kl_project` is keyword-only past `targets` and returns a **2-tuple**:
  `kl_project(seed, margins, targets, *, lower, upper, floor, tolerance, max_iterations) -> (x, violation)`.
- Produces: no source.

**Every code block in this task was executed against the shipped tree while the plan was written
(5 passed), and against both mutants below to confirm it reddens.**

**The item names TWO obligations and both have now been discharged as machine audits.** Read this
whole block before starting — it is the item's witness, and the tick note in Task 6 depends on it.

**(a) Task 18's unit.** Run: twelve tests, 24 source mutations. Scope **covered** — the twelve
shipped tests in `tests/unit/test_reconcile_properties.py` judged against `spec:1714-1716` and
`spec:1737-1743`; a full `pytest tests` run for each mutant that survived the unit suite;
verification of the file's two derived docstring numbers against `runs/320caf9c8934` and
`data/constraints/target_cell.parquet`; and an AST-normalized diff of the plan's Step 1 block
against the shipped file. Scope **not covered** — the correctness of the reconcile implementations
beyond what these mutants probe, `reconcile_draws`, the CLI, and the manifest. **Result: three
holes, all closed by Steps 2-6 below.**

**(b) The remaining cross-cutting units.** Of the item's four, `§17.3 vacuity` is (a) above and
`mask-signature` was settled by the whole-branch review and fixed in `65c4480`. The other two had
only ever been hand-checked — by the same method whose one recorded failure is documented at
`stage3-plan-audit.md:69-80`. Both have now been machine-run:

- **call-site arity — CLEAN.** Scope: 943 call sites bound with `inspect.Signature.bind()` against
  262 definitions across the **whole** package (not scoped to `reconcile/` — that narrowing is
  exactly what made the mask-signature verdict wrong), plus 326 return-arity checks against
  `tuple[...]` annotations, all 84 construction sites of the 7 plan-named dataclasses checked for
  field-order divergence, 10/10 registry estimators checked against the `Estimator` Protocol, the
  Typer command/flag surface, and 242 calls plus 315 plan-internal calls from the plan's 46 python
  fences. A positive control caught 5/5 planted mismatches. Not covered: other plans' code blocks
  and modules outside the package. **No task.**
- **anti-drift in test blocks — 6 findings, none in this plan's path.** Four DEFECTs, all
  data-derived counts asserted as bare literals against the gitignored `data/staged/` tree, and all
  in `tests/integration/test_d1_acceptance.py` (`:67`/`:69`, `:84`, `:100-102`, and
  `assert produced == EXPECTED_BOUNDS` at **`:81`**); plus two NITs. The plan's own 46 python
  fences and 23 bash fences are **clean**. Scope not covered: `tests/audit/`'s ~136 numeric assert
  sites were swept but not individually classified, and `src/` docstrings only by targeted regex.
  **These are filed as a new deferred item in Task 6 and are NOT work for this plan** — they are
  assertions that are too tight, which is the opposite problem from the one a test-coverage batch
  closes, and deciding what "structural" means for each is an application of the anti-drift rule
  rather than a mechanical test addition.

**What came back clean, so that no one re-litigates it:** property 2 is **not** vacuous — its
synthetic finite uppers bind in 140 of 200 trials (366 of 1,043 cells at cap), so the plan's
mandate at `plan:4508-4512` was honoured. Property 3 raises 200/200 with both arms firing.
Property 6's remainder loop runs every trial. Properties 3b, 7b, and §17.1 rows 8-10 all kill their
mutants. **Do not rewrite property 2 or 3's fixtures.**

**Also not a defect, do not spend a step on it:** the plan's Step 1 block at `plan:4661` reads
`out = kl_project(...)` while the shipped file reads `out, _ =`. That is later staleness from
`18f7160` (plan 5), documented at `specs/plans/completed/5-reconciliation-correctness.md:73`, in a
retired plan.

- [x] **Step 1: Reproduce the largest hole**

```bash
rm -rf /tmp/p3t5 && mkdir -p /tmp/p3t5
cp -R /Users/lowell/Projects/impute-suppressed-stats/src/logging_employment /tmp/p3t5/
python3 -c "
import pathlib
p = pathlib.Path('/tmp/p3t5/logging_employment/reconcile/scaling.py'); s = p.read_text()
guard = '''    if anchor.residual - upper_sum > tolerance:
        raise InfeasibleResidualError(
            f\"{anchor.reference_month}: summed upper bounds {upper_sum} fall below residual \"
            f\"{anchor.residual}; §12.3 forbids approximating this away\"
        )
'''
assert s.count(guard) == 1, s.count(guard)
p.write_text(s.replace(guard, ''))
print('mutant applied: §12.3 upper-sum refusal deleted')
"
PYTHONPATH=/tmp/p3t5 uv run python -c "
import logging_employment, inspect
from logging_employment.reconcile import scaling
assert '/tmp/p3t5/' in logging_employment.__file__, logging_employment.__file__
assert 'fall below residual' not in inspect.getsource(scaling)
print('mutant is the module actually loaded')
"
PYTHONPATH=/tmp/p3t5 uv run pytest tests -q 2>&1 | tail -3
```

Expected: **1123 passed, 0 failed.** §12.3's `Σ U < R_t` refusal — a MUST that the Stage 3 plan
singles out at `plan:4508-4512` as the thing property 3 exists to test — is killed by no test in
the repo. It survives because the bracket-exhaustion `for...else` at `scaling.py:100-103` raises
the **same** `InfeasibleResidualError` type, and both tests that could catch it assert only the
type. That `for...else` carries `# pragma: no cover - the upper_sum check above makes this
unreachable in practice`; under the mutant it becomes the live path and nothing notices.

- [x] **Step 2: Pin the guard at BOTH seams**

The seam is two files, not one. `tests/unit/test_scaling.py:80` is the test whose *name* claims
this behaviour (`test_a_residual_above_the_summed_upper_bounds_fails`) and it has the identical
bare-`pytest.raises` weakness. A task scoped to "the Task 18 file" leaves the mis-named test in
place.

In `tests/unit/test_scaling.py`, change the bare context manager inside
`test_a_residual_above_the_summed_upper_bounds_fails` (`:80`) to carry the message:

```python
    with pytest.raises(InfeasibleResidualError, match="fall below residual"):
```

Note its sibling above it already pins its own message (`assert "150" in str(excinfo.value)`), so
this brings the pair into line rather than inventing a convention.

In `tests/unit/test_reconcile_properties.py`, property 3 already builds both anchors but loops them
through **one** bare `pytest.raises`, so neither arm can assert its own message. Replace the body
of `test_property_3_bounded_scaling_fails_on_infeasible_residuals` (`:117-131`) with:

```python
def test_property_3_bounded_scaling_fails_on_infeasible_residuals() -> None:
    """SYNTHETIC: the `sum U < R_t` half cannot fire on D1, where every upper is null.

    The `match=` is the property, not decoration. scaling.py's bracket-exhaustion `for...else`
    raises the same InfeasibleResidualError type, so with §12.3's `sum U < R_t` refusal deleted the
    bare form passed and the whole 1123-test suite stayed green.
    """
    rng = np.random.default_rng(SEED + 2)
    for _ in range(TRIALS // 2):
        cells = _cells(int(rng.integers(2, 8)))
        lower = {c: float(rng.uniform(1.0, 10.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 10.0)) for c in cells}
        anchor_low = Anchor("2024-03", sum(lower.values()) - 1.0, cells, "declared_national_total")
        anchor_high = Anchor("2024-03", sum(upper.values()) + 1.0, cells, "declared_national_total")
        bounds = Bounds(lower=lower, upper=upper)
        weights = _weights(cells, rng)
        with pytest.raises(InfeasibleResidualError, match="exceed residual"):
            scale_into_bounds(anchor_low, weights, bounds, tolerance=TOL, max_iterations=ITERS)
        with pytest.raises(InfeasibleResidualError, match="fall below residual"):
            scale_into_bounds(anchor_high, weights, bounds, tolerance=TOL, max_iterations=ITERS)
```

Two deliberate departures from the shipped body, both required: `_weights(cells, rng)` is hoisted
out of the two calls so both anchors get the **same** weights (the shipped version draws twice
inside the loop), and the `for anchor in (anchor_low, anchor_high)` loop is unrolled so each arm
can carry its own `match=`.

- [x] **Step 3: Give property 4 mutation strength, without touching property 4**

Property 4 passes under an **identity** `kl_project` (`for _ in range(0)`, returning the seed
untouched), because `after == before` satisfies `after <= before + 1e-6`.

Keep `test_property_4_projection_never_increases_constraint_violation` **exactly as it is** — it is
faithful to `spec:1740`, and non-increase is the right claim for the jointly-infeasible systems it
feeds. Add a deterministic companion in the same file:

```python
def test_projection_actually_reaches_a_feasible_system_s_margins() -> None:
    """Property 4's companion. "Never increases" is satisfied by an implementation that does
    nothing: an identity kl_project passes test_property_4 on all 100 trials, because
    after == before clears `after <= before + 1e-6`. On a system that IS feasible the projection
    must arrive, not merely not-diverge."""
    seed = np.array([1.0, 2.0, 3.0, 4.0])
    margins = np.vstack([np.ones(4), np.array([1.0, 1.0, 0.0, 0.0])])
    targets = np.array([20.0, 8.0])

    out, _ = kl_project(
        seed,
        margins,
        targets,
        lower=np.zeros(4),
        upper=np.full(4, np.inf),
        floor=FLOOR,
        tolerance=TOL,
        max_iterations=1000,
    )

    assert constraint_violation(out, margins, targets) == pytest.approx(0.0, abs=1e-8)
```

`kl_project` has **no defaults** past `targets` — `lower`, `upper`, `floor`, `tolerance` and
`max_iterations` are all keyword-only and all required, and it returns `(x, violation)`. The kwargs
above mirror property 4's own call at `:163-172` so the two tests differ in the system they feed,
not in how they call the function. The margins are indicator (0/1) as
`_require_indicator_margins` demands, and the system is feasible: `x = [6, 2, 6, 6]` satisfies both
rows.

**Do not** add a strict-decrease assertion inside property 4's loop — 3 of its 100 trials
legitimately have `before == after`, so it would be flaky by construction. **Do not** assert a
trial-count threshold such as "≥ 90 trials decreased": that is a derived number typed into an
assertion, this repo's own trap.

- [x] **Step 4: Make property 5 not strictly weaker than the function it calls**

Property 5 is named "row and column reconciliation is exact" but asserts `rel=1e-4`, while
`reconcile_matrix` itself raises `IncompatibleMarginError` unless `np.allclose(..., rtol=1e-6)`
(`matrix.py:83-90`). The test is 100× looser than the callee's own guard, so if the function
returns at all the assertion cannot fail: a mutant that drops the guard and returns a result 5e-5
off the margins leaves property 5 **passing**. The measured true error is 2.74e-11.

Tighten both assertions in `test_property_5_row_and_column_reconciliation_is_exact` from `rel=1e-4`
to `rel=1e-9`, which is comfortably above the measured 2.74e-11 error and three orders below the
callee's `rtol`. The two lines at `:188-189` become:

```python
        assert out.sum(axis=1) == pytest.approx(row_totals, rel=1e-9)
        assert out.sum(axis=0) == pytest.approx(column_totals, rel=1e-9)
```

Change only the two `rel=` values. Leave the `reconcile_matrix(...)` call, the margin-consistency
rescale at `:186`, and the loop bound `TRIALS // 4` exactly as they are. Verified: the tightened
form passes on the shipped tree.

- [x] **Step 5: Cover the tolerance half of `spec:1743`**

Property 7 covers only half its bullet — "ordering **or solver tolerances** do not create material
instability". It varies cell order and never the tolerance. Repo-wide, **no** test varies a
reconcile tolerance: `TOL` is a module constant pinned at `1.0e-9` in
`test_reconcile_properties.py:27`, `test_scaling.py:14`, `test_projection.py:15` and
`test_matrix.py:11`. This is the "or solver tolerances" clause the item's own §17.3 unit was meant
to cover, so it belongs in this batch:

```python
@pytest.mark.parametrize("tolerance", [1.0e-9, 1.0e-6])
def test_property_7_solver_tolerance_does_not_move_the_solution(tolerance: float) -> None:
    """The second half of §17.3's last bullet -- "ordering or solver tolerances do not create
    material instability". Property 7 varies cell order only, and no test in the repo varies a
    reconcile tolerance at all: TOL is a pinned module constant in all four reconcile test files."""
    rng = np.random.default_rng(SEED + 6)
    for _ in range(20):
        cells = _cells(int(rng.integers(2, 10)))
        lower = {c: float(rng.uniform(0.0, 5.0)) for c in cells}
        upper = {c: lower[c] + float(rng.uniform(1.0, 200.0)) for c in cells}
        residual = float(rng.uniform(sum(lower.values()), sum(upper.values())))
        anchor = Anchor("2024-01", residual, cells, "declared_national_total")
        weights = _weights(cells, rng)
        bounds = Bounds(lower=lower, upper=upper)

        tight = scale_into_bounds(anchor, weights, bounds, tolerance=TOL, max_iterations=ITERS)
        loose = scale_into_bounds(
            anchor, weights, bounds, tolerance=tolerance, max_iterations=ITERS
        )
        for cell in cells:
            assert tight[cell] == pytest.approx(loose[cell], abs=1e-5)
```

Compare against the **looser** tolerance, never tighter than the looser solve can promise — an
`abs` at `1e-9` here would be asserting that a `1e-6` solve is a `1e-9` solve. Note the residual is
drawn strictly inside `[Σ L, Σ U]`, so property 3's refusals never fire here; the bounds mirror
property 2's generator (`:99-102`) for the same reason.

- [x] **Step 6: Close the integerize lower-bound gap the audit turned up**

`tests/unit/test_integerize.py:39` is named `test_integer_lower_and_upper_bounds_are_respected` and
**passes no `lower=` argument at all** — its body is
`integerize({"01": 5.5, "02": 2.5, "04": 2.0}, total=10, upper={"01": 4, ...})` asserting only
`sum == 10` and `out["01"] <= 4`. That is a name-vs-body mismatch, the same defect family the audit
already fixed once (Task 11, "Test asserted the opposite of its own name", commit `3a9c0e2`).
`test_every_feasible_bounded_input_places_all_its_units` (`:73`) passes only `upper=` too.

The gap is real and mutation-proven: changing `integerize.py:67` from
`seat = max(math.floor(value), lower.get(cell, 0))` to `seat = math.floor(value)` leaves
`uv run pytest tests/unit -q` at **400 passed**. It is not an equivalent mutant — verified:

| input | shipped | mutant |
|---|---|---|
| `integerize({"01": 0.4, "02": 9.6}, total=11, lower={"01": 2})` | `{"01": 2, "02": 9}` | `{"01": 1, "02": 10}` |

Both sum to 11, so a totals-only assertion cannot see it, and `"01"` comes back **below the lower
bound the caller declared**. Add beside it:

```python
def test_a_lower_bound_seats_a_cell_its_raw_value_would_round_below() -> None:
    """test_integer_lower_and_upper_bounds_are_respected passes no `lower=` at all, so the seat
    floor at integerize.py:67 was pinned by nothing: dropping it leaves all 400 unit tests green.
    Both results here sum to 11, so a totals-only assertion cannot tell them apart -- the point is
    WHICH cell holds the units, not how many were placed."""
    out = integerize({"01": 0.4, "02": 9.6}, total=11, lower={"01": 2})
    assert sum(out.values()) == 11
    assert out["01"] == 2
```

Why this belongs here rather than in a new deferred item: it is a pure test addition, and it is the
same shape as Step 2 — a test whose name claims a behaviour its body never exercises. Scoping this
task to "the Task 18 file" would leave both.

- [x] **Step 7: Run all three files**

```bash
uv run pytest tests/unit/test_reconcile_properties.py tests/unit/test_scaling.py tests/unit/test_integerize.py -q
```
Expected: all pass. `test_reconcile_properties.py` goes 12 → 15 (the property-4 companion plus the
tolerance test's two parametrizations); `test_integerize.py` goes 12 → 13; `test_scaling.py` is
unchanged in count.

- [x] **Step 8: Mutation gate — against the same mutants that survived before**

```bash
PYTHONPATH=/tmp/p3t5 uv run pytest tests/unit/test_reconcile_properties.py tests/unit/test_scaling.py -q 2>&1 | tail -6
```

Expected with the §12.3 guard still deleted from `/tmp/p3t5`: **2 failed** —
`test_property_3_bounded_scaling_fails_on_infeasible_residuals` and
`test_a_residual_above_the_summed_upper_bounds_fails`, both on the `match=`, with the actual
message reading `no bracket reaches residual <n>` where "fall below residual" was expected. Before
this task the same command was **0 failed**, which is the whole finding. This was run while the
plan was written: the property-3 rewrite alone reddens, and the shipped bare-`pytest.raises` tests
alongside it stayed green.

Then the identity and margin-guard mutants:

```bash
rm -rf /tmp/p3t5b && mkdir -p /tmp/p3t5b
cp -R /Users/lowell/Projects/impute-suppressed-stats/src/logging_employment /tmp/p3t5b/
python3 -c "
import pathlib, re
p = pathlib.Path('/tmp/p3t5b/logging_employment/reconcile/projection.py'); s = p.read_text()
s2 = re.sub(r'for _ in range\(max_iterations\)', 'for _ in range(0)', s, count=1)
assert s2 != s
p.write_text(s2); print('mutant applied: kl_project is the identity')
"
PYTHONPATH=/tmp/p3t5b uv run pytest tests/unit/test_reconcile_properties.py -q 2>&1 | tail -4
```

Expected: **3 failed** —
`test_projection_actually_reaches_a_feasible_system_s_margins`, plus **both** the tightened
`test_property_5_row_and_column_reconciliation_is_exact` and its `IncompatibleMarginError`. The
property-5 failures are correct and expected: `reconcile_matrix` delegates to `kl_project`
(`matrix.py:71`), so an identity projection makes its own `np.allclose` guard at `:83-90` refuse.

The decisive observation is what does **not** fail: `test_property_4_...` still passes under the
identity mutant (verified — `1 passed` under `-k property_4`). That is the whole point of adding a
companion rather than strengthening property 4, and if property 4 ever *does* fail here, someone
has edited it against this task's instruction.

If the `re.sub` does not match `projection.py`'s actual loop header, read the file and patch the
iteration count by hand; the mutant only has to make `kl_project` return its seed untouched.

- [x] **Step 9: Commit**

```bash
rm -rf /tmp/p3t5 /tmp/p3t5b
git add tests/unit/test_reconcile_properties.py tests/unit/test_scaling.py
git commit -m "test(reconcile): make §17.3's properties fail when the behaviour they name goes away

Deleting §12.3's Σ U < R_t refusal left the whole 1123-test suite green: the bracket
exhaustion for/else raises the same exception type and both candidate tests asserted only
the type. Adds match= at both seams, a deterministic companion property 4 cannot pass under
an identity projection, tightens property 5 below the rtol of the guard it rides on, and
covers the tolerance half of §17.3's last bullet, which no test in the repo varied.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: gates and completion

- [x] **Step 1: Run every gate**

```bash
uv run pytest -q
uv run black --check .
uv run ruff check .
uv run --no-project scripts/audit/verify_extracts.py
```

Expected: **1137 passed** — 1123 plus 14 new test items (Task 1: 2, Task 2: 1, Task 3: 4, Task 4:
3, Task 5: 4 = the property-4 companion, two parametrizations of the tolerance test, and the
integerize lower-bound test). On a
machine without `data/raw/audit/qcew_routes/bulk/`, Task 3 Step 5 skips and it reads **1136 passed,
1 skipped**. Both are green; only a *failure* is a gate breach.

`black` reports all files unchanged; `ruff check .` still reports exactly **24** violations — run
the FULL check, not `--select I`; the extracts gate ends `EXIT CRITERIA: PASS`.

If the count is short, find the missing test rather than adjusting this number — the per-task Run
steps give each file's expected total, so the shortfall localises to one task.

- [x] **Step 2: Confirm no unintended working-tree changes**

Run: `git status --porcelain`. Expected: empty after the five commits.

This repo has a recorded incident of audit subagents writing into the working tree — one reverted
committed fixes. **Check before committing, not after.** Also confirm the gitignored trees are
intact, since three tasks read them:

```bash
ls data/raw/audit/cbp_metadata | wc -l
ls data/raw/audit/cbp_regime
ls -l data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip
rm -rf /tmp/p3t1 /tmp/p3t2 /tmp/p3t4 /tmp/p3t5 /tmp/p3t5b
```

- [x] **Step 3: Confirm the PEP 723 scripts still parse at their declared floor**

This plan adds no code to `scripts/audit/`, so this should be a no-op — run it anyway, because
Tasks 1 and 2 copy those files to `/tmp` and a stray edit to the original would be invisible
otherwise.

```bash
uv run python -c "
import ast, pathlib
scripts = sorted(pathlib.Path('scripts/audit').glob('*.py'))
bad = []
for p in scripts:
    try: ast.parse(p.read_text(), feature_version=(3, 12))
    except SyntaxError as e: bad.append((p.name, e.msg))
print(f'{len(scripts)} scripts, {len(bad)} broken', bad)
"
git diff --stat 78d933f -- scripts/
```

Expected: `0 broken`, and the `git diff` over `scripts/` is **empty**.

- [x] **Step 4: Run the Plan Completion Protocol**

Resolve-before-defer gate, then mark up this file with a status header, then tick the **five**
source items in `specs/deferred_items.md` with `- [x] … → done in plan 7`, then `git mv` this file
to `specs/plans/completed/` in a `chore(specs): retire plan 7` commit. There is no spec to retire.

**Item A ticks with a witness and no task.** Its tick note must be checkable rather than typed:

> **→ already closed by `c075e33` (2026-09-04 18:52), 93 minutes BEFORE `1defbf0` (20:25) recorded
> this item.** `column_parity` was extracted from `main()` in that same commit specifically so the
> branch could be tested, and it shipped with the synthetic dict this item asks for:
> `test_identical_is_false_when_the_bulk_years_disagree_with_each_other`
> (`tests/audit/test_qcew_routes.py:45`) passes two bulk years whose headers differ while the
> reference year matches the slice exactly, so bulk non-uniformity is the only conjunct driving
> `identical` False. A `sys.settrace` line trace over the six tests reaches every executable line
> of `column_parity` (`qcew_routes.py:61-86`), including `:79`, this branch's else arm. The
> item's *premise* stands — `bulk_years_required` is still `[]` — and is pinned separately at
> `verify_extracts.py:125-128`.

**Item C ticks as narrowed, not as closed to its own words.** Use the "what this does not prove"
line quoted at the head of Task 3.

**Three premises the items got wrong, to record in the tick notes:**
- Item C's premise is false in both directions: there is no production bulk path at all
  (`read_bulk_zip` has no caller in `src/`; `fetch_source`'s bulk arm is structurally dead for
  every probe outcome), *and* its "real bulk download" is on disk and was used.
- Item D's "111 of 360" conflates two numbers from `stage3-plan-audit.md:451` — 108 take the
  branch, 111 agree — and neither reproduces against shipped code.
- Item D's `<4` branch was never unreached — a passing test at
  `tests/unit/test_baselines_historical.py:78` already drives it. The gap was assertions.
- Item D's "(Whole-branch review, Minor.)" attribution is wrong: its source is the pre-execution
  plan audit, `specs/findings/stage3-plan-audit.md:449-455`, tagged [NIT].

**Six new deferred items to append** (none belongs in a test-coverage batch):

1. **`tests/audit/test_ces_levels.py`'s three artifact tests skip in a clean clone.** `:534`,
   `:544` and `:556` read `data/raw/audit/ces/summary.json` through `_ces_summary()`, and `data/` is
   gitignored in its entirety, so none of them runs on a fresh checkout or in CI. Plan 7 Task 1
   deliberately reads the **tracked** `specs/findings/source-audit.md` instead, which is why its
   truth pin never skips; converting the three existing tests to the same source is the residual.
   Check the sibling audit test files for the same pattern before fixing just this one.

2. **The bulk route has no build-side consumer, and its fetch arm is unreachable.** `fetch_source`
   can acquire and store a bulk zip (`fetching.py:117-121`), but `build_harmonized` reads only
   `*.csv` through `read_slice_csv` (`build.py:174-183`) and `read_bulk_zip` has no caller in
   `src/`. The arm is unreachable for **any** probe outcome, not merely at today's boundary:
   `probe_slice_boundary` draws from `range(min(window_years) - 5, min(window_years) + 1)`
   (`fetching.py:106`) and returns its earliest served element, so `boundary <= min(window_years)`
   always and `route_for_year` returns `"slice"` for every window year. Were it reachable, three
   defects would be live, all measured: without a run manifest a bulk-routed year is silently
   dropped from `qcew_monthly.parquet`; with one, `snapshot_paths` ignores its `pattern` argument
   (`build.py:116-134`), returns the zip path, and `read_slice_csv` raises
   `ComputeError: invalid utf-8 sequence`; and the quarter loop fetches the year-level zip four
   times, producing four manifest rows against one content-addressed `raw_path` that
   `sorted(listed)` returns four times (INV-007 stacking). This is a delete-or-fix decision on
   dead code, not a condition to wait on.
3. **`BreakAdjustedShare`'s `<4` fallback is a design choice nobody chose.** The audit's own two
   options (`stage3-plan-audit.md:451`): scope the docstring — done in plan 7 Task 4 — or return
   `None` below a minimum segment length so the cell takes the declared §10.2 fallback. Whoever
   takes it needs a new fixture: `tests/fixtures/baselines/` has only three cells with a history
   and **all three are length 6**, so the frozen golden contains no `<4` cell and cannot validate
   the change, while the shipped D1 run would move roughly 99 of 342 cells from `OWN` to
   `FALLBACK`. Plan 7's `test_below_four_shares_the_break_adjusted_variant_is_the_rolling_median`
   is the test that must change.
4. **`historical.py:227`'s `segment = shares[cut:] or shares` — the `or shares` arm is
   unreachable.** For n ≥ 4, `cut ∈ [1, n-1]`, so the slice is never empty; below 4 the early
   return fires first. Delete the arm or state why it stays.
5. **Four anti-drift breaches in `tests/integration/test_d1_acceptance.py`.** Found by plan 7's
   machine run of the `anti-drift in test blocks` cross-cutting unit. The Stage 3 plan's Global
   Constraint says every count is a measurement dated 2026-09-05 — compute at run time, assert on
   structure, never on the literal. These assert literals against the gitignored `data/staged/`
   tree: `suppressed.height == 1227` and `joined.height == 1227` (`:67`, `:69`); a data-derived
   tally encoded in a test's own NAME plus the identity of the single narrow cell (`:84`, `:91-93`);
   `>= 4716`, `== 8` and `> 4000` on consecutive lines (`:100-102`); and
   `assert produced == EXPECTED_BOUNDS` (`:81`) against 14 hand-typed pairs. The last is the
   arguable one and should be argued rather than assumed: `EXPECTED_BOUNDS` is described in the file
   as derived analytically from the published margin before this engine existed, which is an
   independent oracle and the strongest form of golden — but a golden freezes its **input**, and
   this one reads live gitignored data, so its cardinality-14 assertion still moves with a
   revision. Two NITs alongside: `tests/unit/test_anchor.py:174` ships the plan-level NIT recorded
   at `stage3-plan-audit.md:191-195` verbatim, and `src/logging_employment/reconcile/anchor.py:9`
   types "1,227" into a docstring where it is load-bearing on nothing. **Not test-coverage work** —
   these are over-tight assertions, and each needs a ruling on what its structural form is.
   Related: `tests/integration/test_d1_baselines.py` is plan-authored (`038c3af`) and carries one
   breach of the same family, so the fix is not confined to inherited Stage 2 code.

6. **`projection.py:98`'s zero-seed floor is redundant with the clip at `:118`.** Deleting
   `x = np.maximum(np.asarray(seed, dtype=float), floor)` leaves 1123 passed — but that is the
   correct answer, **not** a hole. `:118` is `x = np.clip(x, np.maximum(lower, floor), upper)` and
   runs on the full vector after every margin row, so §12.4's floor is re-imposed each iteration by
   a second line. Verified directly: on an all-zero seed, a one-zero seed and a two-zero seed the
   shipped and floor-deleted versions return **bitwise-comparable identical output**
   (`[5.0, 5.0, 5.0, 5.0]`, `[0.0, 8.0, 5.142857143, 6.857142858]`, `[4.0, 4.0, 5.142857143,
   6.857142857]`) with identical violations. No test can kill this mutant, and none should try —
   the finding is a redundancy, not a missing test. Remedy: delete one of the two lines, or
   document why both stand. **This was very nearly filed as "a real MUST-level hole"; it is not,
   and filing it that way would have put an aged claim into the tracked record.**

---

## Self-Review

**Item coverage.** A → no task, ticks in Task 6 Step 4 with two named witness tests and a line
trace. B → Tasks 1 (sub-item 1) and 2 (sub-item 2). C → Task 3, narrowed, with the narrowing
stated. D → Task 4. E → Task 5. All five reach a tick.

**Placeholders.** None. Every code step carries the code; every mutation gate carries the exact
patch command and the exact expected failure.

**Every test in this plan was executed before it was written down.** Plans 1-4 were written by
reasoning about the code and shipped 9 defective task code blocks in 10 tasks, then 7 in 13; plans
5 and 6 ran a recon first and the rate collapsed. This plan ran the tests. What that caught, all
in first drafts that would otherwise have shipped:
- Task 5 referenced a `_bounds(cells, lower, upper)` helper that **does not exist** — the file
  builds `Bounds(lower=..., upper=...)` inline;
- Task 5 called `kl_project` without its four required keyword-only arguments, and named property
  5's assertions `achieved_rows`/`achieved_columns` instead of `out.sum(axis=1)`/`out.sum(axis=0)`;
- Task 4's fixture used a two-digit `area_fips` and omitted `state_fips`, `aggregation_level` and
  `qtrly_establishments`, none of which `_MONTHLY_DEFAULTS` supplies for a national row.

**Verification record**, all on `78d933f`:
| block | result |
|---|---|
| Task 1's three assertions | green; `notes` is a `str`, `recomputed in notes` is `True`, `coded - STATES_DC_FIPS == {"00","72","78","99"}` |
| Task 1 mutant (`States {states} publish`) | shipped file 37 passed / 3 skipped / **0 failed** |
| Task 2's test | green; writes `published_start == published_end == ""`, `data/` untouched |
| Task 2 mutant (3 guards stripped) | 37 shipped tests pass; new test fails `ValueError: max() iterable argument is empty` at `:617` |
| Task 3's four tests | 4 passed; bulk-q1 150 rows = slice 150, 0 mismatches; real archive digest matches, 2,232 members, `113310`→1, `11331`→3 |
| Task 4's two tests | 2 passed; `{last 34.0, smpy 20.0, median 11.0, ewma 19.2809…, break 30.5}` |
| Task 4 mutant (collapse everywhere) | `break` → 11.0, discrimination test fails, collapse pin still passes |
| Task 5's five blocks | 5 passed |
| Task 5 mutant 1 (§12.3 guard deleted) | **full suite 1123 passed**; new property 3 fails on `match=` |
| Task 5 mutant 2 (identity `kl_project`) | new companion fails, property 5 fails via `matrix.py:71`, **property 4 still passes** |
| Task 5 mutant 3 (integerize seat ignores `lower`) | `tests/unit` **400 passed**; shipped returns `{"01": 2, "02": 9}`, mutant `{"01": 1, "02": 10}` |
| The zero-seed-floor "hole" | **disproved** — floor-deleted and shipped return identical output on all-zero, one-zero and two-zero seeds |

**A claim this plan nearly shipped and did not.** The recon proposed filing §12.4's zero-seed floor
as "a real MUST-level hole, killed by no test in the repo". The 1123-passed result was real; the
inference was not. The clip at `projection.py:118` already folds `floor` into its lower argument and
runs every iteration, so the mutant is behaviourally equivalent and no test could kill it. Filing it
would have put an aged claim into the tracked deferred record — the failure mode this repo's
whole-branch gate exists to catch. It is filed instead as a redundancy.

No `python` code block in this plan exceeds the 100-character line limit.

**Type consistency.** `_parsed` (Task 3 Step 1) is used only in that step.
`_qcew_routes_findings`/`_recorded_digest`/`REAL_BULK` (Task 3 Steps 4-5) are used only there.
`_ces_findings_from_the_shipped_document` (Task 1) is used by Tests 2 and 3.
`_meta` (Task 2) is used by the one test. `_breaking_history` (Task 4 Step 2) is used by the one
test; Step 3 builds its own rows inline because a three-month history shares nothing with a
twelve-month one. `ALL_FIVE`, `Anchor`, `OWN`, `_context`, `make_monthly` and `appendix_a_config`
all already exist in `tests/unit/test_baselines_historical.py`.

**Verified before writing, not asserted:** items A/C/D's decisive claims were each reproduced
against the shipped tree (`git log -S`, the archive's size and tracked digest, the 2,232-member
substring counts, `float.hex()` on the collapse, and the structural argument for `fetching.py:117`),
and all three of Task 1's assertions plus Task 3 Step 4's document parse were executed green.
Task 5 Step 1's mutation was run against the full suite.
