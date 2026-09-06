# Stage 0 Audit-Script Hardening — Implementation Plan

**Status: COMPLETE (2026-09-05)** — executed via executing-plans; one item deferred (the `emplvl_raw_nonzero_rows` rename, see specs/deferred_items.md)

> **For agentic workers:** REQUIRED SUB-SKILL: **executing-plans** — inline execution was chosen
> at the handoff on 2026-09-05, so run the tasks yourself in plan order rather than dispatching
> subagents. Its stop-and-ask rules and completion chain apply. Steps use checkbox (`- [ ]`)
> syntax for tracking.

> Branch: `stage0-audit-hardening`, off `main` at 4360554 (which is 13 commits ahead of
> `origin/main`, unpushed).

> Source: `specs/deferred_items.md`, section `## 1-stage0-logging-employment-spec — 2026-09-04`,
> subsection `### Reviewer Minors triaged as defer`. There is no spec — the eight deferred items
> ARE the requirements. On plan completion, tick those eight per the Plan Completion Protocol.

**Goal:** Close the eight Stage 0 reviewer-Minor items in `scripts/audit/` — over-collecting
predicates, a counter that misses the one case it exists to catch, a duplicated helper that has
already drifted, four unguarded request sites, and three gate defects — without re-running any
script that needs the network.

**Architecture:** Eight items across five scripts, sequenced so the artifact-changing one is
isolated and the riskiest one is last. Seven are output-neutral and land bare. One (Task 5) adds
a key to a `summary.json` and carries a three-script offline regeneration chain. `cbp_metadata.py`
is split across two tasks because fixing its guard helper is a **prerequisite** for routing
anything else through it.

**Tech Stack:** Python ≥ 3.12 (PEP 723 scripts) on a ≥ 3.14 project, uv, Polars, httpx, pytest.

---

## Global Constraints

- The scripts under `scripts/audit/` are standalone PEP 723 files declaring
  `requires-python = ">=3.12"`. Everything added must parse under 3.12 —
  `ast.parse(src, feature_version=(3, 12))` is the check.
- `line-length = 100` for `ruff` and `black`; `[tool.black] target-version = ["py312"]`.
- `interrogate` runs at `fail-under = 100` over `src/` only — audit scripts are outside it, but
  every existing function here has a docstring and new ones should match.
- **Baseline: 1111 passed, 0 failed** (`uv run pytest -q`, ~172s) on a machine with
  `data/staged/` and `data/raw/audit/` present. A fresh clone reports fewer with skips — `data/`
  is gitignored. **Iterate on `uv run pytest tests/audit -q` — 668 tests in 0.66s**, which covers
  every script this plan touches.
- Repo-wide `ruff check .` reports **24 pre-existing** violations (ISC004 9, TRY004 5, UP037 4,
  RUF100 3, RET501 2, UP047 1). That count must be unchanged at the end. Run the FULL `ruff check`,
  not `--select I` — a previous batch introduced a FURB167 by checking only the import rules.

---

## Artifact and network rules — read before touching anything

**`data/` is gitignored in its entirety.** `git ls-files specs/findings data` returns exactly four
paths, all under `specs/findings/`: `source-audit.md`, `source-audit-notes.md`,
`source-audit-extracts.csv`, `stage3-plan-audit.md`. Every `summary.json` and all 175 extracts are
local-only. A change that moves a number in a summary is **invisible to review** until
`assemble_finding.py` re-renders it into the tracked document.

**Which scripts can be re-run offline:** `qcew_identity.py`, `qcew_panel.py`,
`assemble_finding.py` and `verify_extracts.py` fetch nothing — they read cached bytes under
`data/raw/audit/`. Only Task 5 needs a re-run, and it is offline.

> ### 🚨 NEVER RUN `scripts/audit/cbp_metadata.py`
>
> Its `main()` is **destructive-first**: `shutil.rmtree(year_dir)` runs for all eight window years
> **before** any fetch. It also requires `CENSUS_API_KEY` and live `api.census.gov`. An offline or
> keyless attempt **deletes 3.6 MB of gitignored, git-unrecoverable extracts and then fails.**
> It cascades further: a fresh run re-probes 2024 (currently a confirmed 404), and
> `cbp_regime.main()` raises `RuntimeError` outright if 2024 comes back available.
>
> Tasks 9 and 10 are therefore constrained to be **output-neutral**: they add guards on failure
> paths that cannot fire against the recorded data. Verification is by unit tests on extracted
> pure helpers plus `httpx.MockTransport`, never end-to-end. Precedent for landing a
> `cbp_metadata.py` change with no regeneration: `1fa0b38` and `52b87d6` are docstring-only
> commits to this file, and the summary's `generated_utc` (2026-09-04T14:06:01) predates both.

**Hand-editing a `summary.json` is forbidden.** The rule is in the repo, not just convention:
`source-audit-notes.md` says a value "copied by hand into a tracked document is a transcription
defect waiting to happen, and no test compares prose to prose", and `_common.write_summary` is the
only writer — it stamps `generated_utc` itself, so a hand-edited summary carries a timestamp no
run ever produced.

---

## What the recon corrected — three items are not what they say

Each was reproduced against the shipped code before this plan was written. Do not implement the
items as literally worded.

**1. Item "build_panel and main are two independent call sites" — its stated remedy is
unimplementable.** "Having `build_panel` return `(panel, predicates)` removes the seam" is false:
`main` also needs the **pre-`_conform`** `long` frame for `disclosure_code_values(long)` at
`qcew_panel.py:452`, because `emplvl_raw` exists only there. The minimum sufficient return is
three values. Task 3 introduces a `PanelBuild` NamedTuple instead, which leaves all eight existing
`build_panel("5")` test call sites untouched.

**2. Item "`html_title` exists in three byte-identical copies" — the copies are NOT identical, and
the drift it warns about has already happened.** The four executable lines and the `_TITLE_RE`
line are identical across all three. The **docstrings are not**: `susb_layout.py`'s has already
dropped the "including when `body` isn't HTML at all" clause that the other two carry. Task 1 is
therefore repairing existing drift, not preventing hypothetical drift.

**3. Item "three request sites remain unguarded by `fetch_json_or_none`" — understates the defect
and mislocates the helper.** `fetch_json_or_none` is at `cbp_metadata.py:288`, not in `_common.py`.
More importantly **the helper itself still reaches the orphan state it was written to prevent**:
`extracts.append(c.record_extract(...))` runs at line 308 **before** `resp.json()` at line 309, and
it catches only `httpx.HTTPStatusError`. On a 200-with-HTML-error-body — which this project has
recorded Census as returning — the file is written and registered, then `resp.json()` raises
`JSONDecodeError`. Routing the three sites through today's helper would **convert a silent-
corruption path into a new crash.** Task 9 must land before Task 10.

---

### Task 1: move `html_title` into `_common`

**Files:**
- Modify: `scripts/audit/_common.py` (add `html_title` and `_TITLE_RE`)
- Modify: `scripts/audit/cbp_metadata.py`, `bds_detail.py`, `susb_layout.py` (delete the copies)
- Test: `tests/audit/test_common.py`, `test_cbp_metadata.py`, `test_bds_detail.py`,
  `test_susb_layout.py`

**Interfaces:**
- Produces: `_common.html_title(body: bytes) -> str`. The three scripts call it as `c.html_title`.

**Coverage note:** 12 assertions call `m.html_title` across the three test files (5 in
`test_cbp_metadata`, 5 in `test_bds_detail`, 3 in `test_susb_layout`), plus `susb_layout`'s
`is_directory_listing` calls it internally, so 4 more tests exercise it transitively.

- [x] **Step 1: Write the failing test**

Append to `tests/audit/test_common.py`:

```python
def test_html_title_reads_the_title_case_insensitively_and_lowercases_it() -> None:
    """One implementation, one test. It lived in three scripts and the copies had already
    drifted: susb_layout's docstring dropped the "isn't HTML at all" clause the other two
    carried, which is the propagation failure the duplication was flagged for."""
    assert _common.html_title(b"<html><TITLE>  Census Bureau  </TITLE></html>") == "census bureau"
    assert _common.html_title(b"<title>A\nB</title>") == "a\nb"
    assert _common.html_title(b'{"json": true}') == ""
    assert _common.html_title(b"") == ""
```

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_common.py -q -k html_title`
Expected: FAIL with `AttributeError: module '_common' has no attribute 'html_title'`.

- [x] **Step 3: Add it to `_common.py`**

Add near the other module-level regexes, with `import re` if absent:

```python
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def html_title(body: bytes) -> str:
    """The HTML `<title>` text, lowercased and stripped, or `""` if there isn't one (including
    when `body` isn't HTML at all). Case-insensitive on the tag itself (`<TITLE>` matches too).

    Lives here because three audit scripts need it. The copies it replaces justified themselves
    as "audit scripts are standalone PEP 723 files with no import between them" -- true of
    script-to-script imports, but every one of those scripts already imports `_common`, so the
    premise never applied to this module. The copies had in fact already drifted: susb_layout's
    docstring had lost the "isn't HTML at all" clause. That is the propagation failure, observed
    rather than predicted.
    """
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return match.group(1).decode("utf-8", "replace").strip().lower()
```

- [x] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/audit/test_common.py -q -k html_title`
Expected: PASS.

- [x] **Step 5: Delete the three copies and repoint their callers**

In each of `cbp_metadata.py`, `bds_detail.py`, `susb_layout.py`: delete the `def html_title(...)`
block and its `_TITLE_RE` assignment, then change every internal call from `html_title(` to
`c.html_title(`.

**Delete only the three FUNCTION docstrings. Do not touch any MODULE docstring.** Two of the three
modules carry pinned prose in theirs: `test_susb_layout.py:162-163` asserts `"45 real states" in
m.__doc__` and `"46 states, confirmed" not in m.__doc__` — and that pin does NOT whitespace-flatten,
so it is the most fragile in the suite. `test_cbp_metadata.py:701-702` pins two more (flattened).
The corrected "all three already import `_common`" claim belongs in the surviving `_common`
docstring written in Step 3, not in any module docstring here. The internal callers are `bds_detail.py:123` (`classify_probe_body`) and
`susb_layout.py:106` (`is_directory_listing`); grep each file for `html_title(` to catch the rest.
Leave the PEP 723 headers alone — `re` is stdlib and `_common` is already imported.

- [x] **Step 6: Repoint the 12 test assertions**

In `test_cbp_metadata.py`, `test_bds_detail.py` and `test_susb_layout.py`, change every
`m.html_title(` to `_common.html_title(`. `test_cbp_metadata.py` already does `import _common` at
line 51; add that import to the other two if missing.

> Deviation: **13** assertions, not 12 (5 + 5 + 3). `import _common` was added to
> `test_bds_detail.py` and `test_susb_layout.py`. `re` became unused in `bds_detail.py` once
> its copy went, so that import was dropped too. The edit introduced an I001 and an F401,
> both fixed before the commit; the isort fix was `--select I` only, so the three deliberate
> `# noqa: E402` markers survived.

- [x] **Step 7: Verify and commit**

Run: `uv run pytest tests/audit -q` → expect **669 passed** (668 + one new test; the four
assertions inside it collect as one).

```bash
uv run ruff check scripts/audit tests/audit && uv run black --check scripts/audit tests/audit
git add scripts/audit/_common.py scripts/audit/cbp_metadata.py scripts/audit/bds_detail.py \
        scripts/audit/susb_layout.py tests/audit/
git commit -m "refactor(audit): move html_title into _common, where all three callers already import from

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `emplvl_raw_nonzero_rows` must not count an unparseable value as a published zero

**Files:**
- Modify: `scripts/audit/qcew_panel.py:253-255`
- Test: `tests/audit/test_panel_flags.py`

**Why "fix the comparison", not "narrow the docstring":** the counter feeds an interpolated note
at `qcew_panel.py:369` into the **committed** `specs/findings/source-audit.md`, so the defect
lands in a published artifact. Narrowing the docstring would make the counter literally true and
useless for its stated purpose.

**The asymmetry that makes this the only silent path:** a non-numeric raw value on an
*unsuppressed* row makes `build_long` raise at line 173 (a strict cast inside `.otherwise(...)`,
which Polars evaluates only on the `otherwise` rows). On a *suppressed* row it sails through and
the counter reports 0 — precisely the case the docstring says the counter exists to catch.

**Artifact-neutral, measured:** all 4,836 live retained rows parse (0 nulls, 0 unparseable), so old
and new counters both give 3558/0/0, and the regenerated `notes` string is byte-identical to the
one committed in `source-audit.md`. No regeneration step.

- [x] **Step 1: Write the failing test**

Append to `tests/audit/test_panel_flags.py`:

```python
def test_an_unparseable_raw_value_on_a_suppressed_row_is_not_counted_as_a_published_zero() -> None:
    """The one case the counter exists to catch was the one case it missed.

    `cast(strict=False)` turns an unparseable token into null and `fill_null(0)` then makes it
    indistinguishable from a published zero, so `!= 0` reports False. An unsuppressed row with
    the same token raises in `build_long` instead, so the suppressed row is the only silent
    path -- and it is the one the docstring says the counter is for.
    """
    long = pl.DataFrame(
        {
            "disclosure_code": ["N", "N", "N", "N"],
            "area_class": ["states_dc"] * 4,
            "emplvl_raw": ["-", "0", "5", None],
            "emplvl": [None, None, None, None],
            "qtrly_estabs": [1, 1, 1, 1],
        }
    )
    by_code = {row["disclosure_code"]: row for row in disclosure_code_values(long)}
    # The unparseable "-" and the genuine "5". NOT the published "0", and NOT the row that
    # published nothing -- the second of those is what a bare `fill_null(True)` gets wrong.
    assert by_code["N"]["emplvl_raw_nonzero_rows"] == 2
```

This frame is verified against the real function: `disclosure_code_values` returns a **list of
dicts**, not a DataFrame, and the dict-comprehension above is the idiom the existing test at
`test_panel_flags.py:237` already uses. The five columns supplied are exactly what it reads —
`ESTABS_PRESENT` (`qcew_panel.py:50`) is `pl.col("qtrly_estabs").fill_null(0) > 0`, which the
frame covers. Running it against the shipped implementation returns
`emplvl_raw_nonzero_rows: 1` — the defect — so the red is the assertion, not a fixture error.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_panel_flags.py -q -k unparseable_raw_value`
Expected: FAIL, `assert 0 == 1` — the unparseable `"-"` was counted as a zero.

- [x] **Step 3: Move the null-fill after the comparison**

CURRENT (`scripts/audit/qcew_panel.py:253-255`, verbatim):

```python
            emplvl_raw_nonzero_rows=(
                pl.col("emplvl_raw").cast(pl.Int64, strict=False).fill_null(0) != 0
            ).sum(),
```

PROPOSED:

```python
            # Three cases, and the old chain collapsed two of them. An unparseable token casts to
            # null under strict=False; `fill_null(0)` BEFORE the comparison then made it compare
            # equal to a published zero, so the one case this counter exists to catch -- a value
            # that does not parse on a suppressed row -- was the one case it reported as absent.
            # Filling True AFTER the comparison fixes that, but on its own it over-corrects: a
            # row that published NOTHING is also null and would be counted as nonzero. The
            # explicit `is_not_null()` keeps the three apart -- nothing published is not counted,
            # an unparseable token is, and a published 0 is not.
            emplvl_raw_nonzero_rows=(
                pl.col("emplvl_raw").is_not_null()
                & (pl.col("emplvl_raw").cast(pl.Int64, strict=False) != 0).fill_null(True)
            ).sum(),
```

Measured on the four-case frame `["-", "0", "5", None]`: the old chain gives **1** (misses the
unparseable `"-"`), the `fill_null(True)`-only version gives **3** (also counts the absent row),
and the expression above gives **2** — the unparseable and the genuine nonzero. On live data all
three agree, because zero of the 4,836 retained rows are null or unparseable.

- [x] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/audit/test_panel_flags.py -q`
Expected: all pass.

- [x] **Step 5: Prove artifact-neutrality before committing**

The counter feeds a note in the tracked document. Confirm the live value is unchanged, so no
regeneration is owed:

The direct check is on the live counts, read through the same function the note interpolates:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'scripts/audit')
import qcew_panel as m, _common as c
own = c.load_summary('qcew_codes')['findings']['private_own_code']
long, _ = m.build_long(own)
nulls = long['emplvl_raw'].null_count()
unparseable = (long['emplvl_raw'].cast(int, strict=False).is_null().sum()) - nulls
print('nulls', nulls, '| unparseable', unparseable)
for row in m.disclosure_code_values(long):
    print(row['disclosure_code'], row['emplvl_raw_nonzero_rows'])
"
```

Expect **0 nulls and 0 unparseable**. That is the condition under which old and new counters agree,
and it is why this task owes no regeneration. If either is nonzero, STOP: the counter's live value
moves, the interpolated note in the tracked `source-audit.md` is now wrong, and this task inherits
Task 5's regeneration chain (`qcew_panel.py` → `qcew_identity.py` → `assemble_finding.py` →
`verify_extracts.py`, in that order, all offline) plus a one-cell change to
`source-audit-extracts.csv` from `panel.parquet`'s restamped `retrieved_utc`.

`build_long` re-reads the cached raw QCEW files rather than the built panel, so this takes a few
seconds. It makes no network request.

- [x] **Step 6: Commit**

```bash
git add scripts/audit/qcew_panel.py tests/audit/test_panel_flags.py
git commit -m "fix(audit): count an unparseable raw employment value as nonzero, not as a published zero

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: one composition site for `build_long` → `_conform`

**Files:**
- Modify: `scripts/audit/qcew_panel.py:186-187` and `:421-424`
- Test: `tests/audit/test_panel_flags.py`

**Interfaces:**
- Produces: `PanelBuild = NamedTuple("PanelBuild", [("long", pl.DataFrame), ("panel",
  pl.DataFrame), ("predicates", ...)])` and `build(own_code: str) -> PanelBuild`.
  `build_panel(own_code) -> pl.DataFrame` stays, as `build(own_code).panel`, so all eight existing
  `build_panel("5")` call sites are untouched.

**Three values, not two** — see "What the recon corrected", point 1.

- [x] **Step 1: Write the failing test**

```python
def test_the_panel_and_the_long_frame_come_from_one_composition_site() -> None:
    """`build_panel` and `main` each performed `build_long` -> `_conform` independently. They
    agreed, but nothing enforced it, and `main` additionally needs the pre-`_conform` frame for
    `disclosure_code_values` -- so the seam could only close on a three-value return."""
    built = build("5")
    assert built.panel.equals(build_panel("5"))
    assert "emplvl_raw" in built.long.columns
    assert "emplvl_raw" not in built.panel.columns
```

Add `build` and `PanelBuild` to the test module's imports.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_panel_flags.py -q -k one_composition_site`
Expected: FAIL, `ImportError`/`NameError` on `build`.

- [x] **Step 3: Introduce `PanelBuild` and `build`**

CURRENT (`qcew_panel.py:186-187`, verbatim):

```python
def build_panel(own_code: str) -> pl.DataFrame:
    return _conform(build_long(own_code)[0])
```

PROPOSED — add `from typing import NamedTuple` to the imports, then:

```python
class PanelBuild(NamedTuple):
    """The three frames one build produces, so nothing recomposes them independently.

    `long` is pre-`_conform` and is the only frame carrying `emplvl_raw`; `disclosure_code_values`
    needs it. `panel` is the conformed frame everything else reads. Returning only
    `(panel, predicates)` would not have closed the seam, because `main` reads all three.
    """

    long: pl.DataFrame
    panel: pl.DataFrame
    predicates: list


def build(own_code: str) -> PanelBuild:
    """The single `build_long` -> `_conform` composition site."""
    long, predicates = build_long(own_code)
    return PanelBuild(long=long, panel=_conform(long), predicates=predicates)


def build_panel(own_code: str) -> pl.DataFrame:
    """The conformed panel alone. Kept so the eight existing call sites need no change."""
    return build(own_code).panel
```

Type `predicates` to whatever `build_long` actually returns — read line 183's `return long,
recorded` and give it the real annotation rather than `list`.

- [x] **Step 4: Repoint `main`**

CURRENT (`qcew_panel.py:421-424`, verbatim):

```python
    own_code = c.load_summary("qcew_codes")["findings"]["private_own_code"]
    long, predicates = build_long(own_code)
    panel = _conform(long)
```

PROPOSED:

```python
    own_code = c.load_summary("qcew_codes")["findings"]["private_own_code"]
    long, panel, predicates = build(own_code)
```

- [x] **Step 5: Verify and commit**

Run: `uv run pytest tests/audit -q` → all pass, and confirm the eight `build_panel("5")` call
sites were not edited (`git diff --stat tests/audit/test_panel_flags.py` should show only the new
test and its import).

> Deviation: confirmed — the diff was +17/-0. Inserting `build` into the import list broke
> isort ordering (it sorts before `build_long`); fixed with `--select I --fix`.

```bash
git add scripts/audit/qcew_panel.py tests/audit/test_panel_flags.py
git commit -m "refactor(audit): give qcew_panel one build_long -> _conform composition site

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: rename `NO_OTHER_AREA` to what it measures

**Files:**
- Modify: `scripts/audit/qcew_identity.py:98` and `:403`
- Test: `tests/audit/test_identity_rule.py:31` and `:291`

**Artifact-neutral, measured:** `grep -c 'no_non_state_area_present'` returns **0** in both
`data/raw/audit/qcew_identity/summary.json` and `specs/findings/source-audit.md` — the shipped
verdict is `outside_national_total` on 8 discriminating quarters, so the string appears in no
artifact.

**Rename both sites in one commit.** `test_identity_rule.py:31` does
`from qcew_identity import (... NO_OTHER_AREA ...)`, so renaming only the script gives an
`ImportError` — a collection-time failure of the whole module, not one test. Changing only the
string *value* would leave the test green and the misleading Python name in place.

- [x] **Step 1: Rename the constant and its use**

CURRENT (`qcew_identity.py:94-98`, verbatim):

```python
# Where a non-state area sits relative to the national total, as measured from establishments.
INSIDE = "inside_national_total"
OUTSIDE = "outside_national_total"
INDETERMINATE = "indeterminate"
NO_OTHER_AREA = "no_non_state_area_present"
```

PROPOSED:

```python
# Where a non-state area sits relative to the national total, as measured from establishments.
INSIDE = "inside_national_total"
OUTSIDE = "outside_national_total"
INDETERMINATE = "indeterminate"
# Not "no such area". `measure_containment` reaches this whenever no quarter can discriminate the
# two readings, which is equally the case for a panel whose non-state area publishes 0 in every
# quarter and for one whose non-state amount is withheld in every quarter it appears --
# `_resolve_reference` maps an ABSENT group to 0 and a PRESENT-but-unpublished one to null, and
# the filter discards both alike. `quarters_discriminating` and
# `quarters_non_state_amount_unpublished`, returned in the same dict, are what say which a run is
# in; the verdict string must not pre-empt them.
NO_DISCRIMINATING_QUARTER = "no_discriminating_quarter"
```

Then change `qcew_identity.py:403` from `verdict = NO_OTHER_AREA` to
`verdict = NO_DISCRIMINATING_QUARTER`.

- [x] **Step 2: Rename in the test**

`tests/audit/test_identity_rule.py:31` (the import list) and `:291`
(`assert out["verdict"] == NO_OTHER_AREA`, inside
`test_a_zero_contribution_quarter_cannot_discriminate` — the test that pins precisely the
mislabelled case).

- [x] **Step 3: Add the test that pins why the rename was needed**

```python
def test_a_withheld_non_state_amount_is_not_reported_as_no_such_area() -> None:
    """A panel that HAS a non-state area whose establishment count was withheld reached the same
    verdict as one with no such area, and the returned dict then contradicted itself: the verdict
    said the area was absent while its sibling counter said one quarter had it unpublished."""
    out = measure_containment(_raw_quarter(other_published=None, estab_gap=0))
    assert out["verdict"] == NO_DISCRIMINATING_QUARTER
    assert out["quarters_non_state_amount_unpublished"] == 1
```

Build `_raw_quarter` from the shape the existing tests use at `test_identity_rule.py:291` — read
that test and mirror its fixture rather than inventing one.

- [x] **Step 4: Verify and commit**

Run: `uv run pytest tests/audit/test_identity_rule.py -q` → all pass.
Confirm artifact-neutrality: `grep -c no_non_state_area_present specs/findings/source-audit.md`
→ `0`.

```bash
git add scripts/audit/qcew_identity.py tests/audit/test_identity_rule.py
git commit -m "fix(audit): name the identity verdict for what it measures, not for one of its causes

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: report states+DC areas with no rows at all — THE ONLY ARTIFACT-CHANGING TASK

**Files:**
- Modify: `scripts/audit/qcew_identity.py` (after `:540`, at `:562`, and the note at `:587-600`)
- Test: `tests/audit/test_identity_rule.py`
- Regenerate: `data/raw/audit/qcew_identity/summary.json` (gitignored),
  `specs/findings/source-audit.md` (tracked)

**Why the existing key cannot report it:** `short_span` groups rows that exist. Polars emits one
group per key value present and the smallest group is one row, so `pl.len() == 0` is unreachable
and `months < n_months` is never evaluated for an absent area. **DC (`11000`, 96 absent months) is
missing from this summary while `qcew_panel`'s own summary records it** in
`state_month_cell_coverage.areas_with_no_rows`.

- [x] **Step 1: Write the failing test**

```python
def test_an_area_with_no_rows_at_all_is_reported_rather_than_silently_dropped() -> None:
    """`states_dc_short_span_areas` groups rows that exist, so its smallest group is one row and
    a zero-row area can never appear in it however the filter is written. DC is exactly that
    case: 96 absent months, recorded by qcew_panel and absent from this summary."""
    panel = _toy_panel(present={"01000": 3, "10000": 1})  # 3-month universe; 11000 has no rows
    out = structural_findings(panel, n_months=3)
    assert [a["area_fips"] for a in out["states_dc_short_span_areas"]] == ["10000"]
    assert "11000" in out["states_dc_areas_with_no_rows"]
```

Build `_toy_panel` to match what `structural_findings` reads — `area_fips`, `area_title`,
`area_class` (`"states_dc"`), and whatever else it touches. Read the function first.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_identity_rule.py -q -k no_rows_at_all`
Expected: FAIL, `KeyError: 'states_dc_areas_with_no_rows'`.

- [x] **Step 3: Add the sibling binding**

After the `short_span = (...)` block ending at `qcew_identity.py:540`, add:

```python
    # `short_span` groups rows that exist, so its smallest group is one row: an area with no row
    # at all forms no group and can never appear in it, however the filter is written. The
    # configured universe is the only place such an area is named, so the absent codes come from
    # `c.STATE_AREAS` directly. Codes and not titles, because an area with no row carries no
    # `area_title` to report. `area_class == "states_dc"` is assigned upstream by membership of
    # `c.STATE_AREAS`, so the difference is exactly the zero-row areas.
    no_rows = sorted(c.STATE_AREAS - set(states["area_fips"].unique().to_list()))
```

At `:562`, add the key beside its sibling:

```python
        "states_dc_short_span_areas": short_span,
        "states_dc_areas_with_no_rows": no_rows,
```

The name deliberately mirrors `qcew_panel`'s `state_month_cell_coverage.areas_with_no_rows` so the
two summaries read against each other.

- [x] **Step 4: Make the derived note see it**

`states_dc_areas` (`:551`, = 50) and `states_dc_area_months_absent` (`:561`, = 84) are **both
denominated against present areas**, so a zero-row area is in neither figure. The note must say so
rather than leave 51 and 50/84 to be reconciled by the reader. In `absent_state_months_note`, bind
after `areas`:

```python
    no_rows = ", ".join(structural["states_dc_areas_with_no_rows"]) or "none"
```

and replace the `:600` f-string line with:

```python
        f"areas. The area(s) whose span is shorter than the panel's: {areas}. Of the "
        f"{len(c.STATE_AREAS)} configured states+DC area code(s), the one(s) carrying no row in "
        f"any month, and so counted in neither figure above: {no_rows}. Also measured: "
```

- [x] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/audit/test_identity_rule.py -q`
Expected: all pass.

- [x] **Step 6: Run the offline regeneration chain, in this order**

All three are network-free. **Order is load-bearing** — the gate must run last, because if a
changed `verdict_sentence` reached it before the document was re-rendered, `check_verdict` fails
E2 and a failing gate refuses to write the manifest at all.

```bash
uv run --no-project scripts/audit/qcew_identity.py
uv run --no-project scripts/audit/assemble_finding.py
uv run --no-project scripts/audit/verify_extracts.py
```

Expect the gate to end `EXIT CRITERIA: PASS`.

**If E1 fails with `states_dc_areas_with_no_rows … is empty`:** `check_findings_filled` iterates
every findings key and flags `[]`. On today's data the value is `['11000']`, so this should not
fire — if it does, the panel changed, and the fix is an entry in `LEGITIMATELY_EMPTY_FINDINGS`,
not a silenced check.

- [x] **Step 7: Review the regenerated document deliberately**

`git diff specs/findings/source-audit.md` should show: the new key in `qcew_identity`'s findings
fence, the reworded absent-months note, `qcew_identity`'s per-source `generated_utc` line, and the
document header's "newest `generated_utc`". Nothing else. If `access.route` changed, you
regenerated from a different checkout — that field embeds an absolute path.

`source-audit-extracts.csv` must **not** move: `qcew_identity` registers `extracts=[]`.

- [x] **Step 8: Commit as two commits, per house precedent**

The convention is a separate `chore(audit): regenerate …` commit (see `164afc8`/`438cb44`,
`54a3f24`/`c709ce2`, `b4afadb`/`7128144`).

```bash
git add scripts/audit/qcew_identity.py tests/audit/test_identity_rule.py
git commit -m "fix(audit): report states+DC areas carrying no row at all

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git add specs/findings/source-audit.md
git commit -m "chore(audit): regenerate the finding document for the zero-row area key

verify_extracts.py: EXIT CRITERIA: PASS

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `enabled` must distinguish "declared false" from "not declared"

**Files:**
- Modify: `scripts/audit/verify_extracts.py:566`
- Modify: `scripts/audit/assemble_finding.py:145` (the only renderer)
- Test: `tests/audit/test_verify_extracts.py:553` (the test that affirms the defect)

**Artifact-neutral, measured:** all ten Appendix A sources carry an explicit `enabled:` line, and
running the real renderer over the real appendix reproduces `source-audit.md:42-51` byte-for-byte.

- [x] **Step 1: Change the affirming test first**

`tests/audit/test_verify_extracts.py:553` currently asserts a `"mystery"` source with no
`enabled:` line equals `False`. That assertion **is** the defect. Change it to `is None` and
rename the test to say what it now pins:

```python
def test_parse_appendix_a_sources_reports_a_missing_enabled_line_as_not_declared() -> None:
    """A source with no `enabled:` line is not a source declared disabled. Typing `False` for it
    made the two indistinguishable in the shipped table, with this test affirming it."""
```

Keep the existing `{"qcew": True, "cbp": False}` expectations; only `"mystery"` changes.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_verify_extracts.py -q -k not_declared`
Expected: FAIL, `assert False is None`.

- [x] **Step 3: Widen the type**

CURRENT (`verify_extracts.py:566`): `enabled.setdefault(current, False)`
PROPOSED: `enabled.setdefault(current, None)`

Widen the function's annotation from `dict[str, bool]` to `dict[str, bool | None]` and add a line
to its docstring saying `None` means the spec declared the source without an `enabled:` line.

- [x] **Step 4: Handle `None` in the renderer**

`assemble_finding.py:145` currently renders `"true" if enabled else "false"`, which maps `None` to
`"false"` — the exact conflation. Change it to a three-way:

```python
        "not declared" if enabled is None else ("true" if enabled else "false"),
```

Read line 145 in context first and preserve the surrounding row construction exactly.

- [x] **Step 5: Verify, and prove the shipped table is unchanged**

Run: `uv run pytest tests/audit -q` → all pass.

```bash
uv run --no-project scripts/audit/assemble_finding.py && git diff --stat specs/findings/source-audit.md
```

Expect **no diff** — every Appendix A source declares `enabled:`, so no cell becomes
"not declared". If the document moves, stop and find out which source lost its line.

> Deviation: a second test was added beyond the plan, pinning that a `None` renders
> "not declared" in `appendix_a_rows`. The three-way branch is dead on today's spec, which is
> exactly the shape this repo has had to defer before, so it is demonstrated rather than
> reasoned. `appendix_a_rows`' annotation was widened to `dict[str, bool | None]` to match.

- [x] **Step 6: Commit**

```bash
git add scripts/audit/verify_extracts.py scripts/audit/assemble_finding.py tests/audit/test_verify_extracts.py
git commit -m "fix(audit): distinguish a spec-declared enabled:false from a source that declares neither

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: document `classification_block`'s replacement return value

**Files:**
- Modify: `scripts/audit/verify_extracts.py`, `classification_block`'s docstring only
- Test: `tests/audit/test_verify_extracts.py`

**Document the return; do NOT make it refuse.** Two committed constraints rule refusal out:

1. The obvious refusal — stop the closing-fence scan at the next heading — **reintroduces a defect
   already pinned** by `test_classification_block_keeps_a_hash_prefixed_line_inside_the_fence`
   (`test_verify_extracts.py:517`): inside a fence, a `#`-prefixed line is content.
2. A new raise would be an **uncaught traceback, not a FAIL line**. `main` calls
   `parse_classification_record` at `verify_extracts.py:778` with no `try/except`, before any
   check runs, so a raise prints no `FAIL [...]` and no `EXIT CRITERIA:` line at all.
   `assemble_finding.main:328` is the same.

**What actually happens on the unreachable path:** with an unclosed §3.1 fence and a later fence
present, it returns 9–12 lines spanning §3.2's heading and prose. In the sharper variant
`parse_classification_record` reads `classification_status = 'DRAFT_do_not_use'` out of §3.2 —
and that value reaches `assemble_finding.render_document`, which writes it into
`source-audit.md`'s Classification paragraph. So the consequence is a wrong value in a **tracked
deliverable**, not merely a confused gate.

- [x] **Step 1: Write the failing test that pins the documented behaviour**

```python
def test_an_unclosed_section_31_fence_returns_later_sections_rather_than_raising() -> None:
    """Documented, not fixed. The closing fence is the next fence in the FILE, so an unclosed
    §3.1 fence borrows a later one and the block spans §3.2. Refusing instead would reintroduce
    the `#`-inside-a-fence defect pinned above, and a raise here is an uncaught traceback because
    main calls this before any check runs. The docstring now names this return."""
    spec = _spec_with_unclosed_31_fence()
    lines = m.classification_block(spec)
    assert any("3.2" in line for line in lines)
```

Build `_spec_with_unclosed_31_fence` by mirroring the fixtures already in this file — read
`test_parse_classification_record_raises_when_the_names_sit_outside_the_section_31_fence` and
reuse its spec shape.

- [x] **Step 2: Run it — it should already PASS**

Run: `uv run pytest tests/audit/test_verify_extracts.py -q -k unclosed_section_31`
Expected: PASS. This is a characterization test: it pins behaviour that already exists but was
undocumented. That is the point — the deliverable here is the docstring, and this test stops the
docstring going stale silently.

- [x] **Step 3: Extend the `Raises:` paragraph to name the return**

The current final paragraph ends: "That closing fence is the next fence line in the file rather
than the next one inside the section, so an unclosed §3.1 fence is reported as unclosed only when
no fence follows it anywhere."

Append, in the same paragraph:

```
    When a fence DOES follow it anywhere, there is no raise and no error: the block returned spans
    whatever lies between the unclosed opener and that later fence, which can include a following
    section's heading and prose. That return departs from this function's summary line -- the
    lines are not "inside the §3.1 fence" in any useful sense -- and it is what
    `parse_classification_record` then parses, so a `key = value` line in §3.2 can be read as a
    §3.1 value and reach the Classification paragraph of the finding document. Documented rather
    than refused: stopping the closing scan at the next heading reintroduces the
    `#`-inside-a-fence defect this module already pins, and a raise here is an uncaught traceback
    because `main` calls this before any check runs and outside any handler.
```

- [x] **Step 4: Verify and commit**

Run: `uv run pytest tests/audit -q` → all pass.

```bash
git add scripts/audit/verify_extracts.py tests/audit/test_verify_extracts.py
git commit -m "docs(audit): name the value classification_block returns when a fence is unclosed

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: scope the roadmap-field document check to the owning fence

**Files:**
- Modify: `scripts/audit/verify_extracts.py:612`
- Test: `tests/audit/test_verify_extracts.py`

**The over-match:** `if f'"{key}"' not in doc_text` tests the whole document, which inlines the
hand-written notes verbatim and every other source's fence. A document where `"branch"` appears
only in `cbp_regime`'s fence, with `qcew_identity`'s fence lacking it, currently returns `[]`.

**"Measured safe today" is a quoting convention, not a structural guarantee.** Zero ROADMAP_FIELDS
keys appear double-quoted in `source-audit-notes.md` — but **12 of the 20 appear there backticked**
(e.g. `` `qcew_identity.quarter_table` ``). One author writing `"branch"` instead of `` `branch` ``
moves the count off zero.

**This couples the gate to the assembler's markup.** The scoped check depends on three literals
emitted by `assemble_finding.render_document`: the `` ### `<name>` `` heading, the `**findings**:`
label, and the ```` ```json ```` fence. Rename any of them in the assembler and the exit gate
fails on correct work. Say so in the code comment.

- [x] **Step 1: Write the failing test**

`check_roadmap_fields` reads the module-level `ROADMAP_FIELDS` directly — use `monkeypatch`, and
do **not** add a `fields=` parameter that production never passes.

```python
def test_a_roadmap_key_in_another_sources_fence_does_not_satisfy_the_document_check(
    monkeypatch,
) -> None:
    """The presence test matched a quoted key anywhere in the document, including the inlined
    hand-written notes and every other source's fence. Only the owning source's findings fence
    should count."""
    monkeypatch.setattr(m, "ROADMAP_FIELDS", (("the branch", "qcew_identity", "branch"),))
    doc = _document_with_key_only_in(source="cbp_regime", key="branch")
    summaries = {"qcew_identity": {"findings": {"branch": "residual_cells"}}}
    failures = m.check_roadmap_fields(summaries, doc)
    assert [f.criterion for f in failures] == ["E1"]
```

Build `_document_with_key_only_in` to emit the assembler's real shape: a `` ### `<source>` ``
heading, a `**findings**:` line, and a ```` ```json ```` fence.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_verify_extracts.py -q -k another_sources_fence`
Expected: FAIL, `assert [] == ['E1']`.

- [x] **Step 3: Scope the match**

Add a helper beside `check_roadmap_fields` that extracts one source's findings fence, and use it
at `:612`. Read the assembler's `render_document` for the exact literals before writing it, and
carry this comment:

```python
    # Scoped to the owning source's `**findings**:` fence, not the whole document. The document
    # inlines the hand-written notes verbatim and carries every other source's fence, so a
    # document-wide match let one source's key satisfy another's presence test. Zero
    # ROADMAP_FIELDS keys appear double-quoted in the notes today, but twelve appear backticked,
    # so the old safety was a quoting convention rather than a structural guarantee.
    # THIS COUPLES THE GATE TO THE ASSEMBLER'S MARKUP: the heading, the `**findings**:` label and
    # the json fence are emitted by assemble_finding.render_document. Renaming any of them there
    # makes this gate fail on correct work.
```

- [x] **Step 4: Run the test, then prove the real gate still passes**

> Deviation: an EXISTING test had to be rewritten —
> `test_check_roadmap_fields_reports_a_field_absent_from_the_document` built its document as a
> bare space-joined list of quoted keys, which is not the assembler's shape and cannot satisfy
> a scoped check. It now constructs per-source fences. The plan did not anticipate it. A UP031
> was introduced by the new fixture's `%`-formatting and fixed before the commit.

Run: `uv run pytest tests/audit/test_verify_extracts.py -q` → all pass.
Then run the gate against the real document — the scoped predicate must return zero failures over
all 20 entries:

```bash
uv run --no-project scripts/audit/verify_extracts.py
```

Expected: `EXIT CRITERIA: PASS`.

- [x] **Step 5: Commit**

```bash
git add scripts/audit/verify_extracts.py tests/audit/test_verify_extracts.py
git commit -m "fix(audit): scope the roadmap-field presence check to the owning source's fence

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: close `fetch_json_or_none`'s own orphan window — PREREQUISITE for Task 10

**Files:**
- Modify: `scripts/audit/cbp_metadata.py:288-309`
- Test: `tests/audit/test_cbp_metadata.py`

**Do not skip ahead to Task 10.** Routing the three sites through today's helper converts a
silent-corruption path into a new crash.

**The defect:** `extracts.append(c.record_extract(...))` runs **before** `resp.json()`, and only
`httpx.HTTPStatusError` is caught. On a 200 whose body is Census's HTML error page, the file is
written and registered in the manifest, then `resp.json()` raises `JSONDecodeError` — the
unregistered/dangling-manifest state `cfe0c1f` was written to prevent, reached from a third angle.
This project has a recorded fact that Census and USDA both return 200 with an error body, so
status-only handling is insufficient by construction.

- [x] **Step 1: Write the failing test**

```python
def test_a_200_with_a_non_json_body_does_not_leave_a_registered_extract_behind(tmp_path) -> None:
    """`record_extract` ran before `resp.json()`, so an HTML error page served with status 200
    was written to disk and appended to `extracts`, and THEN raised JSONDecodeError -- the
    dangling-manifest state the guard exists to prevent, reached through the guard itself."""
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"<html><title>error</title></html>")
        )
    )
    extracts: list = []
    status, payload = m.fetch_json_or_none(
        client, m.SOURCE, "https://example.invalid/x.json", "x.json", extracts
    )
    assert payload is None
    assert extracts == []
```

Redirect `_common`'s extract root into `tmp_path` the way the existing tests in this file do —
read one and copy its fixture, so nothing is written into the real `data/`.

- [x] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/audit/test_cbp_metadata.py -q -k non_json_body`
Expected: FAIL with `json.JSONDecodeError` propagating out of `fetch_json_or_none`.

- [x] **Step 3: Parse before recording, and catch the decode error**

CURRENT (`cbp_metadata.py:305-309`, verbatim):

```python
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code, None
    extracts.append(c.record_extract(source, url, rel_path, resp.content))
    return resp.status_code, resp.json()
```

PROPOSED:

```python
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code, None
    # Parse BEFORE recording. `record_extract` used to run first, so a 200 carrying an HTML error
    # page -- which Census does serve -- was written to disk and appended to `extracts`, and only
    # then did `resp.json()` raise. That is the dangling-manifest state this function exists to
    # prevent, reached through the function itself. A body that is not JSON is not evidence, so
    # it is not recorded and the caller is told the route produced nothing usable.
    try:
        payload = resp.json()
    except ValueError:
        return resp.status_code, None
    extracts.append(c.record_extract(source, url, rel_path, resp.content))
    return resp.status_code, payload
```

`json.JSONDecodeError` subclasses `ValueError`; catching `ValueError` also covers httpx's own
decode failures.

- [x] **Step 4: Extend the docstring**

Add a paragraph naming the newly-covered case and, explicitly, the case still **not** covered:

```
    Covers a 200 whose body is not JSON as well as a non-200: neither records an extract, so the
    manifest never gains an entry for a body this run could not use. NOT covered, and out of this
    function's reach: `_common._retry` re-raises `httpx.TransportError` after three attempts, so a
    DNS failure or connection reset still propagates out of `main()` mid-loop and leaves the same
    unregistered-files state. Narrowing the orphan class is not closing it.
```

- [x] **Step 5: Verify and commit**

Run: `uv run pytest tests/audit/test_cbp_metadata.py -q` → all pass (58 + the new one).

```bash
git add scripts/audit/cbp_metadata.py tests/audit/test_cbp_metadata.py
git commit -m "fix(audit): parse before recording, so a 200 with a non-JSON body leaves no manifest entry

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: route the three unguarded sites through the fixed guard

**Files:**
- Modify: `scripts/audit/cbp_metadata.py:431`, `:438`, `:447`, `:518`
- Test: `tests/audit/test_cbp_metadata.py`

**All four sites are inside `main()`, which no test can reach** (it needs `CENSUS_API_KEY` and
live `api.census.gov`; the one test that calls it monkeypatches the probe to a 404). So **extract
each branch into a pure helper and unit-test the helper** — that extraction is part of the change,
not an optional tidy.

**DO NOT REORDER THE FETCHES.** Moving `geography.json` up beside `variables.json` is structurally
cleaner and is forbidden here: it changes the order of each year's entries in `summary.json`'s
`extracts` array, from which `source-audit-extracts.csv` is derived. No test would fail and no
datum would change, but the next live run would emit a diff that looks like a data change and is
not. Preserve the existing order at the cost of two separate guard sites.

**Output-neutral by construction:** every guard added here fires only on a failed or malformed
response. The recorded run has `access.status == "verified"` and every one of these routes
succeeded, so no recorded value moves. **Do not re-run the script** — see the boxed warning above.

- [x] **Step 1: Write the failing tests**

Three tests, one per site, each driving the extracted helper with `httpx.MockTransport`:

```python
def test_a_404_on_the_dataset_refetch_records_no_extract_and_does_not_crash() -> None: ...
def test_variables_json_lacking_a_variables_key_is_reported_not_a_keyerror() -> None: ...
def test_a_geography_document_that_is_unavailable_is_not_read_as_zero_states() -> None: ...
```

The third pins a **silent-wrong path the deferred item does not name**: `.get("fips", [])`
returning `[]` on a malformed body reaches `zero_pull_cause` as `state_available=False` and
persists `"geography_unavailable"` — a fetch failure recorded as a measured fact about CBP. It
must instead record that the document was unavailable.

**These three are signatures, not bodies, and that is deliberate — the one place this plan defers
real content.** The helper boundaries are not determined until Step 3, because each depends on what
the call site has in scope at its point in `main()`. Read the surrounding `main()` code first, extract
the helper, then write the body against the signature you actually created. Every other task in this
plan carries complete code; if you find yourself guessing here, stop and read `main()` again rather
than inventing a boundary.

- [x] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/audit/test_cbp_metadata.py -q -k "refetch or variables_key or geography_document"`
Expected: 3 failed — `ImportError`/`AttributeError` on the not-yet-extracted helpers.

- [x] **Step 3: Extract the helpers and route them through `fetch_json_or_none`**

Site by site. CURRENT at `:431` (the dataset re-fetch) is:

```python
        meta = c.request(client, f"{BASE.format(year=year)}.json")
        extracts.append(
            c.record_extract(
                SOURCE, f"{BASE.format(year=year)}.json", f"{year}/dataset.json", meta.content
            )
        )
```

This one never parses its body today, which is why it currently records silently rather than
crashing — and why Task 9 had to land first. Route it through `fetch_json_or_none` and handle a
`None` payload by appending a note rather than continuing as if the dataset document were read.

CURRENT at `:438-447` (variables.json plus the `KeyError`):

```python
        vresp = c.request(client, f"{BASE.format(year=year)}/variables.json")
        extracts.append(
            c.record_extract(
                SOURCE,
                f"{BASE.format(year=year)}/variables.json",
                f"{year}/variables.json",
                vresp.content,
            )
        )
        names = list(vresp.json()["variables"].keys())
```

Route through the guard, and replace `vresp.json()["variables"]` with a `.get("variables")` whose
absence is recorded as a named cause rather than raising `KeyError`.

CURRENT at `:518` (geography.json): the same shape — route it through the guard and record a
distinct cause when the document is unavailable, so `zero_pull_cause` cannot read it as
`state_available=False`.

**One new value enters a recorded vocabulary on the failure path:** a status such as
`"geography_document_unavailable"` in `working_query_by_year`, which feeds the derived
`failure_causes` set and from there into `access.reason` prose. `validate_summary` checks
structure rather than status values, so nothing rejects it — but Stage 1 reads this field, so name
it deliberately and record the addition in the commit message.

> Deviation: the extracted helpers are `variable_names` and `geography_levels`, and a THIRD
> recorded status was added beyond the plan's one — `variables_document_unavailable` alongside
> `geography_document_unavailable`, since the same "unreadable vs. genuinely empty" confusion
> applies to the variables document. The vocabulary went from three members to five, not four.

- [x] **Step 4: Run the three tests, then the whole file**

Run: `uv run pytest tests/audit/test_cbp_metadata.py -q`
Expected: all pass.

- [x] **Step 5: Prove you did not run the script**

```bash
python3 -c "import json;print(json.load(open('data/raw/audit/cbp_metadata/summary.json'))['generated_utc'])"
```

Expected: `2026-09-04T14:06:01...` — unchanged. If it moved, the script was run; the extracts it
deleted are unrecoverable and the tree must be assessed before going further.

- [x] **Step 6: Commit**

```bash
git add scripts/audit/cbp_metadata.py tests/audit/test_cbp_metadata.py
git commit -m "fix(audit): guard the last three cbp_metadata request sites and the variables KeyError

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: gates and completion

- [x] **Step 1: Run every gate**

```bash
uv run pytest -q
uv run black --check .
uv run ruff check .
uv run --no-project scripts/audit/verify_extracts.py
```

Expected: all tests pass with a count of 1111 + the tests this plan added — **actual: 1123**; `black` reports all
files unchanged; `ruff check .` still reports exactly **24** violations (run the FULL check, not
`--select I`); the gate ends `EXIT CRITERIA: PASS`.

- [x] **Step 2: Confirm the PEP 723 scripts still parse at their declared floor**

```bash
uv run python -c "
import ast, pathlib
bad = []
for p in sorted(pathlib.Path('scripts/audit').glob('*.py')):
    try: ast.parse(p.read_text(), feature_version=(3, 12))
    except SyntaxError as e: bad.append((p.name, e.msg))
print(f'{len(list(pathlib.Path(\"scripts/audit\").glob(\"*.py\")))} scripts, {len(bad)} broken', bad)
"
```

- [x] **Step 3: Confirm no unintended working-tree changes**

Run: `git status --porcelain`. Expected: only the files this plan names. This repo has a recorded
incident of audit subagents writing into the working tree — check before committing, not after.

Also confirm `data/raw/audit/cbp_metadata/` is intact: `ls data/raw/audit/cbp_metadata | wc -l`.

- [x] **Step 4: Run the Plan Completion Protocol**

Resolve-before-defer gate, then markup this file with a status header, then tick the **eight**
source items in `specs/deferred_items.md` with `- [x] … → done in plan 6`, then `git mv` this file
to `specs/plans/completed/` in a `chore(specs): retire plan 6` commit. There is no spec to retire.

Three things to record in the tick notes, because each is a premise the items got wrong:
- `build_panel` returning `(panel, predicates)` was not implementable — `main` needs the
  pre-`_conform` frame too, so it took a three-value `PanelBuild`.
- The three `html_title` copies were **not** byte-identical: the docstrings had already drifted.
- `fetch_json_or_none` was itself part of the defect, and lives in `cbp_metadata.py`, not
  `_common.py`.

**One new deferred item to append** (do not fold it into Task 2): after the comparison fix,
`emplvl_raw_nonzero_rows` means "not a published zero", but its name and the two interpolated
notes at `qcew_panel.py:369` and `:390` still say "nonzero". Renaming the key changes a shipped
artifact and so needs the regeneration chain; it was deliberately not bundled here.
