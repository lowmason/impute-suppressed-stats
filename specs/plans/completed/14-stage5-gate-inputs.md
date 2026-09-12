# Stage 5 Gate Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status: COMPLETE (2026-09-12)** — executed via executing-plans; deferred items in specs/deferred_items.md

> Deviation (whole plan): suite absolutes in this plan were measured WITHOUT `data/`; this checkout
> has it. Every per-task delta matched — 1388 → 1393 → 1396 → 1401 → 1402 (+5/+3/+5/+1) — and both
> golden sha256s reproduced byte-for-byte. After execution, a whole-branch review (27 confirmed
> findings, 2 critic gaps) and two verification passes led to commits `542ed37`, `5c484c0`,
> `96fdda5` and the fix commit that precedes retirement; they also surfaced `D-112`, a PRE-EXISTING
> Stage 4 residual-sign defect in §13.7's ensemble, filed rather than fixed.
> *Resolution after retirement (2026-09-12): `D-112` was fixed in `19fbdec`. The golden this plan froze at
> `2bec94b0…` is superseded by `a544559f…`, and the hand-derived oracle's `covered == 33` by `covered == 31`;
> the coverage caveat recorded at retirement no longer binds.*

**Goal:** Make §13.10's two "major stratum" gates evaluable from a shipped artifact, emit §13.6's missing state-share metric, and measure — rather than assume — whether any §9.3 margin identifies a suppressed state cell, so Stage 5 is planned against a gate that reads something and an identification set that was counted.

**Architecture:** Eight remediations against a shipped, green codebase. Four touch code, one adds a standalone measurement script, three are record-only. No new module boundary: the metric work lands inside `validate/metrics.py`, `contracts.py` and `validate/scoreboard.py`, and the measurement lands in `scripts/audit/`, which is outside the package by design. Task 1 comes first because it is one sentence and its whole purpose is to make Task 2 visible to the person who needs it; Task 2 comes next because it is the only network-bound task and the only one whose *result* can change later tasks.

**Tech Stack:** Python >= 3.14, uv + hatchling, polars, pydantic v2, typer, httpx, pytest, ruff, interrogate.

**Requirements input:** `specs/stage5-gate-inputs.md` (R-S5G-1..8). The plan argument at the handoff was `specs/plans/completed/13-stage5-preconditions.md`, which is COMPLETE and retired; it is this plan's predecessor, not its requirements. The §12.2/§15.2 anchor amendment and Appendix A's residue remain owned by `specs/completed/stage5-preconditions.md` §6 and are out of scope here, per gate-inputs §3.

**Provenance of the code in this plan.** Every code block in **Tasks 4, 5, 6 and the test half of Task 2** was executed in an isolated git worktree at `795a467` before being written here — test run red, implementation applied, test run green, then `ruff format src tests`, `ruff check src tests` and `interrogate src` all clean, then the whole suite. The red steps of Tasks 4 and 5 were each *observed*, not inferred: Task 5's required rebuilding the post-Task-4 tree and running the new tests against it. The observed outputs are quoted in each task and are transcribed from those runs, not retyped. This repo has a documented history of plan code blocks that parse but do not run.

**Suite counts are stated as DELTAS, and every absolute is anchored.** The verification ran in the order metrics → config → script; this plan executes in the order script → metrics → config, so an absolute transcribed from one order is wrong in the other. Each gate step below states the delta, which is order-independent, and then the plan-order absolute — re-measured in plan order at `795a467`. **The delta is the check; a mismatch there means halt. The absolute is a convenience and moves the moment the baseline does.** The pre-plan baseline is `1318 passed, 70 skipped` in a checkout without `data/`.

**What was NOT executed, and why**, stated in the same place plan 13 stated it:

- **Task 1, 3, 7, 8** — record-only; they have no code to run.
- **Task 2's `main()` and its fetch path** — 128 live requests against `data.bls.gov`. Its one piece of judgment, `identification`, was extracted and *is* verified (5 tests, green); everything around it is `_common`'s already-tested fetch machinery.

---

## Global Constraints

- `requires-python = ">=3.14"`; author `Lowell Mason <mason.lowell@mac.com>`; MIT (Rollout D4).
- **`run_id` MUST NOT change.** `runs.run_id` = sha256 of `{config: resolved_dict(cfg), inputs: {stem: sha256}}`. **No task here adds a pydantic field to `Config`** — Task 6 deliberately records the three existing `PromotionConfig` keys rather than adding a fourth. Nothing in this plan writes to `data/staged/`, so `runs/f03023ac9f3a` — Stage 5's promotion comparand — keeps its id.
- **Format and lint scope is `src tests`, never `.`** — `uv run ruff format src tests`, `uv run ruff check src tests`. A bare `.` rewrites `except (A, B):` into PEP 758 syntax in `scripts/audit/` files whose PEP 723 headers declare `>=3.12`, where it does not parse. Task 2 adds a file to `scripts/`, so it names that file **explicitly** (`ruff format scripts/audit/qcew_parent_margins.py`) rather than widening the scope.
- **`uv run interrogate src` is `fail-under = 100`.** Every new callable needs a docstring, and the house style says *why this and not the obvious alternative*, citing `§` / `INV-` / `REQ-` / `SRC-` / `R-` ids. Every docstring this plan needs is written out in its code block.
- **Fail closed with a named error.** Everything raisable subclasses `LoggingEmploymentError` in `errors.py` and carries the offending value.
- Run pytest from the repo root. Committed fixtures live in `tests/fixtures/`; tests never read `data/`. **Every test this plan adds is fixture-based and needs no `data/`** — verify by arithmetic after each task: *skipped* must not move and *passed* must rise by exactly the number of tests added.
- **Schemas are ordered `dict[str, pl.DataType]` literals and the order is load-bearing** — `schema_fingerprint` hashes the ordered pairs. Task 5 **appends**; it never inserts.
- Cite deferred items by `D-nnn`, never by title. This plan closes `D-091` and `D-092`.
- **Roadmap stage blocks are single ~7 KB lines and are a known merge hazard.** A "keep both" merge has already duplicated one. Task 1 and Task 3 edit them; both verify by `grep -c`, never by eye.

## File Structure

| File | Task | Responsibility |
|---|---|---|
| `specs/logging-employment-spec-roadmap.md` | 1, 3 | the settle-before trigger moves from the Stage 6 block to the Stage 5 block; Stage 5's `Consumes` gains the measured margin ruling |
| `specs/findings/stage-5-log.md` | 1, 3 | where the dated measurement and the superseded reading go — stage-block rule 2 keeps them out of the block itself |
| `scripts/audit/qcew_parent_margins.py` | 2 | standalone PEP 723 measurement of the §9.3 parent-industry and ownership margins; writes a summary, mutates nothing |
| `tests/audit/test_qcew_parent_margins.py` | 2 | the script's only judgment, tested without the network |
| `specs/findings/qcew-parent-margins.md` | 3 | the committed, human-readable rendering of Task 2's summary |
| `src/logging_employment/validate/metrics.py` | 4, 5 | `state_share_absolute_error`; the `overall`/`census_division` emission |
| `src/logging_employment/validate/harness.py` | 4, 5 | passes the national denominator; runs the closed-set guard over the metrics frame |
| `src/logging_employment/validate/regimes.py` | 5 | `DIVISION_OF`, the single partition inverted once |
| `src/logging_employment/contracts.py` | 5 | `STRATUM_KINDS`, the two appended schema columns, the non-null declaration |
| `src/logging_employment/validate/scoreboard.py` | 5 | the headline filter that keeps the board's grain |
| `src/logging_employment/config.py` | 6 | `PromotionConfig`'s per-key inertness record |
| `specs/logging-employment-spec.md` | 7 | §13.10's Status, only under R-S5G-2 Option B |
| `specs/stage5-gate-inputs.md` | 7 | the Status line carrying the ruling either way |
| `specs/deferred_items.md` | 6, 8 | the new inert-key item; `D-091` / `D-092` ticked |

---

### Task 1: Re-point the settle-before trigger to the stage that consumes the artifact

**Implements:** R-S5G-7

R-S5G-7 is the cheapest requirement in the spec and explicitly MUST NOT be deferred behind Task 2's measurement: its entire purpose is to make that measurement visible to the Stage 5 planner, who is told to read `deterministic_bounds` and today cannot see the precondition attached to it.

**Files:**
- Modify: `specs/logging-employment-spec-roadmap.md` (the `- [ ] Stage 5:` and `- [ ] Stage 6:` blocks)
- Modify: `specs/findings/stage-5-log.md`

**Interfaces:**
- Consumes: nothing.
- Produces: a Stage 5 `Consumes` clause naming the margin precondition. Task 3 amends that same clause with the measured answer.

- [x] **Step 1: Confirm the sentence is where this task thinks it is, and appears once**

```bash
grep -c "if any margin is wanted it must be settled BEFORE this stage consumes" \
  specs/logging-employment-spec-roadmap.md
grep -n "^- \[ \] Stage 5:\|^- \[ \] Stage 6:" specs/logging-employment-spec-roadmap.md
```
Expected: `1`, then two line numbers. Measured 2026-09-11: the sentence appears once, inside the Stage 6 block; Stage 5 is line 288 and Stage 6 is line 298. If the count is not 1, STOP — a duplicated stage block is the merge hazard the stage-block rules were written for, and reconciling it comes before this edit.

- [x] **Step 2: Delete the sentence from Stage 6's `Consumes`**

In the `- [ ] Stage 6:` block, remove exactly this trailing sentence from the `Consumes:` line:

```text
 Finally, the §9.3 parent-industry, ownership and region margins were never fetched, declined or owned: every one of the 1,227 suppressed state cells is `[0, +inf)`, so if any margin is wanted it must be settled BEFORE this stage consumes `deterministic_bounds`.
```

A correction REPLACES the sentence it corrects (stage-block rule 1). Do not leave it behind with a `MOVED` marker: two readings of one precondition, in two stages, is the defect.

- [x] **Step 3: Add the replacement to Stage 5's `Consumes`**

Append to the `- [ ] Stage 5:` block's `Consumes:` line:

```text
 **The §9.3 margins are a precondition of THIS stage, not Stage 6's.** Every one of the 1,227 suppressed state cells is `[0, +inf)` — `selected_upper` null on all 1,227 — because the parent-industry, ownership and region margins were never fetched, declined or measured. This stage consumes `deterministic_bounds`, so the question is settled before it, by `specs/stage5-gate-inputs.md` R-S5G-5; `specs/findings/stage-5-log.md` carries the measurement.
```

- [x] **Step 4: Verify by count, not by eye**

```bash
grep -c "if any margin is wanted it must be settled BEFORE this stage consumes" specs/logging-employment-spec-roadmap.md
grep -c "The §9.3 margins are a precondition of THIS stage" specs/logging-employment-spec-roadmap.md
awk '/^- \[ \] Stage 5:/,/ROUTING: writing-plans/' specs/logging-employment-spec-roadmap.md | grep -c "R-S5G-5"
```
Expected: `0`, `1`, `1`. The third command is what proves the sentence landed in the Stage 5 block rather than merely somewhere in the file.

- [x] **Step 5: Log the move**

Append to `specs/findings/stage-5-log.md`:

```markdown
## 2026-09-11 — the §9.3 settle-before trigger was attached to the wrong stage

**Superseded reading** (roadmap Stage 6 `Consumes`, until this plan):

> if any margin is wanted it must be settled BEFORE this stage consumes `deterministic_bounds`

**Why it changed.** The sentence was true of Stage 6 and also of Stage 5, and only
Stage 6 carried it. Stage 5's own `Consumes` already reads "Stage 2's
`deterministic_bounds`", so a Stage 5 planner reading the artifact they are told to
read could not see the precondition attached to it. R-S5G-7.

**Why it mattered.** The trigger guards an ORDER, and a trigger one stage late does
not guard anything: by the time Stage 6 reads it, Stage 5 has already been gated
against the identification set the measurement might change.
```

- [x] **Step 6: Commit**

```bash
git add specs/logging-employment-spec-roadmap.md specs/findings/stage-5-log.md
git commit -m "docs(specs): move the §9.3 settle-before trigger to Stage 5, which consumes the artifact"
```

---

### Task 2: Measure the §9.3 parent-industry and ownership margins

**Implements:** R-S5G-5

R-S5G-5 requires a MEASUREMENT, not a ruling from the armchair: "a decline recorded without the measurement is an assertion, and this repo has a written rule against those". This task produces the numbers; Task 3 records what they mean.

**Files:**
- Create: `scripts/audit/qcew_parent_margins.py`
- Create: `tests/audit/test_qcew_parent_margins.py`

**Interfaces:**
- Consumes: `scripts/audit/_common.py`'s `build_client`, `request`, `write_summary` — the same fetch and summary machinery every Stage 0 audit script uses. `_common.contact_email()` reads `BLS_CONTACT_EMAIL` (D3); `bls.gov` admits scripted clients only when the User-Agent carries a contact address.
- Produces: `data/raw/audit/qcew_parent_margins/summary.json` with the `findings` block Step 6 specifies. Task 3 renders it; nothing in `src/` imports this script.

**Three properties this script must have, each from a recorded trap:**

1. **NOT destructive-first.** `scripts/audit/cbp_metadata.py` `rmtree`s each year's extract directory *before* it probes, and those extracts are gitignored. This script deletes nothing and overwrites only its own summary.
2. **Classify on CONTENT, not status.** Government APIs answer 200 with an error body. `_common.request` already returns the response for the caller to classify; a CSV that does not parse is a failure even at 200.
3. **A measured absence is a result.** `own_code 0` may not exist at state × 6-digit at all. The summary must distinguish "fetched, no such row" from "not fetched" — that distinction is the whole difference between a measurement and the assertion `D-002` forbids.

- [x] **Step 1: Write the failing test for the script's only judgment**

Everything else in this script is fetching and counting. The one decision — which margin identifies a suppressed cell, and how strongly — is extracted so it can be tested without the network, which is the convention `tests/audit/test_qcew_routes.py` established for `column_parity`.

Create `tests/audit/test_qcew_parent_margins.py`:

```python
"""Judgment-logic tests for `qcew_parent_margins` (R-S5G-5).

Nothing here touches the network or `data/raw/audit/`. The script's only decision is which margin
identifies a suppressed cell and how strongly; the fetching around it is `_common`'s and is tested
there. `qcew_parent_margins` is imported bare, like `_common`, per `tests/conftest.py`; importing
it is inert because its side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import qcew_parent_margins as m

NOTHING = {
    "parent_113_disclosed": False,
    "parent_1133_disclosed": False,
    "parent_11331_disclosed": False,
    "ownership_total_disclosed": False,
    "ownership_siblings_disclosed": False,
}


def test_no_disclosed_margin_is_the_status_quo():
    """Today's measured state: every one of the 1,227 suppressed cells is `[0, +inf)`."""
    assert m.identification(NOTHING) == m.NONE


def test_a_disclosed_single_child_parent_is_exact_not_a_bound():
    """D6: `1133 -> 11331 -> 113310` is single-child in both vintages, so the parent IS the cell."""
    for level in ("parent_1133_disclosed", "parent_11331_disclosed"):
        assert m.identification({**NOTHING, level: True}) == m.EXACT


def test_a_disclosed_113_bounds_rather_than_identifies():
    """`113` aggregates 1131, 1132 and 1133; nonnegativity of the siblings gives an upper bound."""
    assert m.identification({**NOTHING, "parent_113_disclosed": True}) == m.UPPER_BOUND


def test_total_ownership_is_exact_only_when_the_sibling_is_disclosed_too():
    total = {**NOTHING, "ownership_total_disclosed": True}
    assert m.identification(total) == m.UPPER_BOUND
    assert m.identification({**total, "ownership_siblings_disclosed": True}) == m.EXACT


def test_exact_outranks_a_bound_when_both_are_available():
    """The strongest margin wins: a cell with both is a REQ-027 case, not a bounded one."""
    both = {**NOTHING, "parent_113_disclosed": True, "parent_1133_disclosed": True}
    assert m.identification(both) == m.EXACT
```

- [x] **Step 2: Run it to make sure it fails**

```bash
uv run pytest tests/audit/test_qcew_parent_margins.py -q
```
Expected: collection error, `ModuleNotFoundError: No module named 'qcew_parent_margins'`.

- [x] **Step 3: Write the judgment**

Create `scripts/audit/qcew_parent_margins.py` with the header and this function. **Verified: these exact 5 tests pass against this exact function.**

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Measure whether any §9.3 parent-industry or ownership margin identifies a suppressed private
113310 state cell on D1 (R-S5G-5)."""

from __future__ import annotations

from collections.abc import Mapping

EXACT = "exact"
UPPER_BOUND = "upper_bound"
NONE = "none"


def identification(row: Mapping[str, bool]) -> str:
    """Which §9.3 margin, if any, identifies one suppressed private 113310 state-quarter.

    The ladder is EXACT before UPPER_BOUND before NONE, because the three have different
    consequences and the strongest one wins. An exact margin is a live `REQ-027` / §14.4 case: the
    `1133 -> 11331 -> 113310` chain is single-child in both the 2017 and 2022 vintages (D6,
    measured against the official structure files), so a disclosed private parent at either level
    is the suppressed value itself and not a bound on it.

    `113` is DIFFERENT and is deliberately not in the exact branch. Forestry and Logging aggregates
    `1131`, `1132` and `1133`, so a disclosed `113` plus nonnegativity of the two siblings gives
    `113310 <= 113`. That is §9.3's parent-total constraint doing real work -- today every
    suppressed state cell is `[0, +inf)` -- but it is a bound, and recording it as exact would put
    a modelled cell into the release path §14.4 guards.

    Ownership splits the same way. `own_code 0` is Total Covered over the ownerships present, which
    Stage 0 measured as `3` (Local Government) and `5` (Private) for this industry. With the
    sibling disclosed, private is total minus sibling and therefore exact; with it suppressed, the
    sibling is only known to be nonnegative and the total is an upper bound.
    """
    if row["parent_1133_disclosed"] or row["parent_11331_disclosed"]:
        return EXACT
    if row["ownership_total_disclosed"] and row["ownership_siblings_disclosed"]:
        return EXACT
    if row["parent_113_disclosed"] or row["ownership_total_disclosed"]:
        return UPPER_BOUND
    return NONE
```

- [x] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/audit/test_qcew_parent_margins.py -q
```
Expected, verified: `5 passed in 0.01s`.

- [x] **Step 5: Write the fetch and count half**

> Deviation: `main()` corrected against reality — `io`/`httpx` imports; a 404 is recorded as a measured absence; any unparseable 200 or partial fetch halts (`fetch_verdict`, extracted after review); `agglvl_code` joined the required-column guard; `slice_outcomes` is recorded.

Append to `scripts/audit/qcew_parent_margins.py`. `INDUSTRIES` carries `113310` as well as the three parents so the script re-derives its own baseline rather than trusting a written count.

```python
import _common as c
import polars as pl

SOURCE = "qcew_parent_margins"
SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
INDUSTRIES = ("113310", "113", "1133", "11331")
YEARS = range(2017, 2025)
QUARTERS = (1, 2, 3, 4)
PRIVATE, LOCAL_GOVERNMENT, TOTAL_COVERED = "5", "3", "0"
PUERTO_RICO = "72000"
# The 2026-09-11 witness this run re-derives rather than assumes. A DATED PAIR, not a threshold:
# a BLS revision moves it and that is not this script's failure, so a mismatch is RECORDED in
# `matches_2026_09_11_witness` and never raised. Refusing here would make the script break on a
# revision it is supposed to measure.
WITNESS_STATE_QUARTER_ROWS, WITNESS_SUPPRESSED_ROWS = 1572, 409


def state_rows(frame: pl.DataFrame, industry: str) -> pl.DataFrame:
    """The state rows for one industry-quarter, at whatever aggregation level serves them.

    The agglvl code is DISCOVERED, not asserted. `constants.QCEW_STATE_AGGLVL` is `58` -- "State,
    NAICS 6-digit -- by ownership sector" -- which is the level for `113310` and is the WRONG level
    for `113`, `1133` and `11331`, each of which is served at its own digit-depth code. Filtering
    on the industry and the area shape instead reaches all four without a table of codes this
    script would have to keep true. §5.4's instruction not to hard-code a route property applies.
    """
    return frame.filter(
        (pl.col("industry_code") == industry)
        & pl.col("area_fips").str.ends_with("000")
        & (pl.col("area_fips") != PUERTO_RICO)
        & (pl.col("area_fips") != "US000")
    )


def disclosed_keys(rows: pl.DataFrame, own_code: str) -> set[tuple[str, str, str]]:
    """`(area_fips, year, qtr)` for rows published with a value, at one ownership.

    Keyed on the QUARTER because that is the grain QCEW suppresses at. One disclosed parent quarter
    therefore identifies three months at once, which is why the month counts below are the quarter
    counts times three rather than a separate measurement.
    """
    published = rows.filter((pl.col("own_code") == own_code) & (pl.col("disclosure_code") != "N"))
    return set(zip(*published.select("area_fips", "year", "qtr").to_dict().values(), strict=True))
```

Then `main()`. **NOT EXECUTED — 128 live requests against `data.bls.gov`.** Everything it calls is
already tested (`_common`'s fetch and summary machinery in `tests/audit/test_common.py`,
`identification` in Step 1), but this orchestration itself has not been run; correct it against
reality rather than trusting it.

```python
def main() -> None:
    """Fetch the four industries across D1 and count who identifies whom."""
    frames: dict[str, list[pl.DataFrame]] = {industry: [] for industry in INDUSTRIES}
    extracts: list[c.ExtractRecord] = []
    with c.build_client() as client:
        for industry in INDUSTRIES:
            for year in YEARS:
                for qtr in QUARTERS:
                    url = SLICE_URL.format(year=year, qtr=qtr, industry=industry)
                    body = c.request(client, url).content
                    # CLASSIFY ON CONTENT, NOT STATUS. These endpoints answer 200 with an error
                    # body; `raise_for_status` inside `c.request` therefore cannot be the check.
                    # A body that does not parse into the expected columns is a failure at 200.
                    frame = pl.read_csv(io.BytesIO(body), infer_schema_length=0)
                    missing = {"area_fips", "own_code", "industry_code", "disclosure_code"} - set(
                        frame.columns
                    )
                    if missing:
                        raise SystemExit(f"{url} returned 200 without {sorted(missing)}")
                    frames[industry].append(
                        frame.with_columns(
                            pl.lit(str(year)).alias("year"), pl.lit(str(qtr)).alias("qtr")
                        )
                    )
                    # `record_extract(source, url, rel_path, content)` -- it writes the bytes
                    # and the hash sidecar itself; it does not take a digest.
                    extracts.append(
                        c.record_extract(SOURCE, url, f"{industry}/{year}q{qtr}.csv", body)
                    )

    stacked = {i: pl.concat(f, how="vertical_relaxed") for i, f in frames.items()}
    child = state_rows(stacked["113310"], "113310")
    private_child = child.filter(pl.col("own_code") == PRIVATE)
    suppressed = set(
        zip(
            *private_child.filter(pl.col("disclosure_code") == "N")
            .select("area_fips", "year", "qtr")
            .to_dict()
            .values(),
            strict=True,
        )
    )

    parents = {}
    for industry in ("113", "1133", "11331"):
        rows = state_rows(stacked[industry], industry)
        parents[industry] = {
            "fetched": True,
            "agglvl_codes_present": sorted(set(rows["agglvl_code"].to_list())),
            "own_codes_present": sorted(set(rows["own_code"].to_list())),
            "disclosed_where_child_suppressed": len(
                disclosed_keys(rows, PRIVATE) & suppressed
            ),
        }

    total_own = disclosed_keys(child, TOTAL_COVERED)
    sibling_own = disclosed_keys(child, LOCAL_GOVERNMENT)
    exact_113310 = disclosed_keys(state_rows(stacked["1133"], "1133"), PRIVATE)
    exact_11331 = disclosed_keys(state_rows(stacked["11331"], "11331"), PRIVATE)
    bounding_113 = disclosed_keys(state_rows(stacked["113"], "113"), PRIVATE)

    tally = {EXACT: 0, UPPER_BOUND: 0, NONE: 0}
    for key in suppressed:
        tally[
            identification(
                {
                    "parent_113_disclosed": key in bounding_113,
                    "parent_1133_disclosed": key in exact_113310,
                    "parent_11331_disclosed": key in exact_11331,
                    "ownership_total_disclosed": key in total_own,
                    "ownership_siblings_disclosed": key in sibling_own,
                }
            )
        ] += 1

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": f"{min(YEARS)}-Q1",
            "published_end": f"{max(YEARS)}-Q4",
            "window_start": c.WINDOW_START,
            "window_end": c.WINDOW_END,
            "covered": sorted(str(y) for y in YEARS),
            "uncovered": [],
        },
        access={"status": "verified"},
        extracts=extracts,
        findings={
            "private_113310": {
                "state_quarter_rows": private_child.height,
                "suppressed_rows": len(suppressed),
                # RECORDED, never raised. A BLS revision moves this pair, and a script that
                # refused on a mismatch would break on exactly the change it exists to measure.
                "matches_2026_09_11_witness": (
                    private_child.height == WITNESS_STATE_QUARTER_ROWS
                    and len(suppressed) == WITNESS_SUPPRESSED_ROWS
                ),
            },
            "parents": parents,
            "total_ownership_113310": {
                "fetched": True,
                # A MEASURED ABSENCE is the result. `own_code 0` missing here is an answer to
                # R-S5G-5, not a gap in it -- which is why `fetched` rides alongside.
                "own_codes_present": sorted(set(child["own_code"].to_list())),
                "own_code_0_rows": child.filter(pl.col("own_code") == TOTAL_COVERED).height,
            },
            "identification": {**tally, "months_identified": 3 * (tally[EXACT] + tally[UPPER_BOUND])},
        },
    )


if __name__ == "__main__":
    main()
```

`io` joins the imports. Note `months_identified` is `3 x` the quarter count: QCEW suppresses per
quarter and each quarter carries three monthly employment columns, so one disclosed parent quarter
reaches three months at once.

- [x] **Step 6: Run the measurement**

```bash
cd scripts/audit && uv run --no-project qcew_parent_margins.py
```
Expected: 128 requests, then `data/raw/audit/qcew_parent_margins/summary.json` with a `findings` block of this SHAPE — the zeros below are placeholders for the measurement, **except** that `state_quarter_rows` and `suppressed_rows` should come back `1572` and `409` if the 2026-09-11 witness still holds, which is what `matches_2026_09_11_witness` records:

```json
{
  "private_113310": {"state_quarter_rows": 0, "suppressed_rows": 0,
                     "matches_2026_09_11_witness": true},
  "parents": {"113": {"fetched": true, "agglvl_codes_present": [], "own_codes_present": [],
                      "disclosed_where_child_suppressed": 0},
              "1133": {}, "11331": {}},
  "total_ownership_113310": {"fetched": true, "own_codes_present": [], "own_code_0_rows": 0},
  "identification": {"exact": 0, "upper_bound": 0, "none": 0, "months_identified": 0}
}
```

**Region margins are NOT fetched and need not be.** QCEW publishes no region level: Stage 0's measured agglvl inventory for `113310` is `18 National / 48 MSA / 58 State / 78 County`, recorded in `registry/sources.yaml`'s `geography` field with the summary key it came from. A Census-division total does not exist to fetch, so R-S5G-5's region component is answered by a shipped measurement and Task 3 records it as such.

- [x] **Step 7: Format, lint, and run the suite**

```bash
uv run ruff format scripts/audit/qcew_parent_margins.py
uv run ruff check scripts/audit/qcew_parent_margins.py tests/audit/test_qcew_parent_margins.py
uv run ruff format src tests && uv run ruff check src tests
uv run pytest -q
```
Expected, verified for the judgment half: `1 file left unchanged`, `All checks passed!`, and **passed up by exactly 5, skipped unchanged**. In plan order this is the first task to touch the suite, so the absolute is `1318 + 5` = **`1323 passed, 70 skipped`**. Note the first command names the file: `ruff format .` would rewrite `except (A, B):` into PEP 758 syntax in two other `scripts/audit/` files whose headers declare `>=3.12`.

- [x] **Step 8: Commit**

```bash
git add scripts/audit/qcew_parent_margins.py tests/audit/test_qcew_parent_margins.py
git commit -m "feat(audit): measure whether any §9.3 parent or ownership margin identifies a suppressed cell"
```

---

### Task 3: Record the measurement where a stage will read it

**Implements:** R-S5G-6

R-S5G-6 is specific about form: the outcome goes somewhere "a later stage will actually read — a `Consumes` clause on the affected stage, or a spec amendment, **not only a findings file**". A findings file alone is how `D-091` came to be owned by a retired document.

**Files:**
- Create: `specs/findings/qcew-parent-margins.md`
- Modify: `specs/findings/stage-5-log.md`
- Modify: `specs/logging-employment-spec-roadmap.md` (Stage 5 `Consumes`, the clause Task 1 added)

**Interfaces:**
- Consumes: Task 2's `summary.json`.
- Produces: the sentence Task 8 branches on.

- [x] **Step 1: Render the summary into a committed finding**

> Deviation: the finding is rendered by a committed script, `scripts/audit/render_parent_margins.py` (hash-verified extracts, a digest pin, prose premises that halt a stale render), not written by hand; it also measures bound informativeness and the MILP-reachable subset (107 of 756 bounded month-values), which the plan did not ask for.

`data/raw/audit/` is gitignored, so the summary itself is not the record. Create `specs/findings/qcew-parent-margins.md` with the run date, the exact command, the four industries and 32 quarters covered, the re-derived `1,572 / 409` pair with its `matches_2026_09_11_witness` verdict, the per-parent disclosed-where-child-suppressed counts, the observed `own_code` set, and the `exact` / `upper_bound` / `none` tally. **Every number derived from the summary, none retyped from this plan** — this repo has ten recorded instances of audit prose that was typed rather than derived.

- [x] **Step 2: Write the contract sentence into Stage 5's `Consumes`**

> Deviation: Branch B, not the Branch A the plan expected — a disclosed private `113` bounds 252 of 409 suppressed quarters (756 months), 0 exact. Task 1's causal clause was replaced, not annotated (stage-block rule 1).

Amend the clause Task 1 added. Use **Branch A** or **Branch B** according to what Task 2 measured; write one, not both.

**Branch A — no usable margin.** R-S5G-6 requires that this sentence state the measured pattern that supports it, not merely the conclusion:

```text
 MEASURED 2026-09-11 and DECLINED: no §9.3 margin identifies a suppressed private 113310 state cell on D1. Of the 409 suppressed state-quarters, <N> have a disclosed private parent at 1133 or 11331, <N> at 113, and `own_code 0` <appears N times / appears nowhere> at state x 6-digit; QCEW publishes no region level at all (agglvl inventory: 18 National, 48 MSA, 58 State, 78 County). `deterministic_bounds` therefore stays `[0, +inf)` on all 1,227 cells and this stage's identification set is the one Stage 2 shipped. See `specs/findings/qcew-parent-margins.md`.
```

**Branch B — a margin exists.** Then the record MUST name what it changes, which R-S5G-6 enumerates:

```text
 MEASURED 2026-09-11: <N> of the 409 suppressed state-quarters (<3N> months) carry a disclosed margin — <N> exact via <1133|11331|own 0>, <N> bounded above via 113. This is NOT absorbed here. It changes: a `registry/sources.yaml` row per new slice; new cell kinds and a `rows.size_margin_rows`-style parent-margin builder in `constraints/`; §13.2 step-4 parent masking in `validate/recover.py`, which must hide the parent whenever it hides the child; and `disclosure/`'s `exact_reconstruction_flag` on the exact cases (REQ-027, §14.4). Routed to its own spec by Task 8; Stage 5 MUST NOT consume `deterministic_bounds` as identification-complete until it lands.
```

- [x] **Step 3: Log the measurement**

Append the dated measurement to `specs/findings/stage-5-log.md` — stage-block rule 2 puts measurements in the log and the current *contract* in the block, which is what Step 2 wrote.

- [x] **Step 4: Verify the record is where a reader will hit it**

```bash
awk '/^- \[ \] Stage 5:/,/ROUTING: writing-plans/' specs/logging-employment-spec-roadmap.md \
  | grep -c "MEASURED 2026-09-11"
grep -c "qcew-parent-margins.md" specs/logging-employment-spec-roadmap.md
```
Expected: `1` and `1`.

- [x] **Step 5: Tick `D-092`**

In `specs/deferred_items.md`, tick `D-092` with a pointer: `- [x] ... → done in plan 14`. Never delete it.

- [x] **Step 6: Commit**

```bash
git add specs/findings/ specs/logging-employment-spec-roadmap.md specs/deferred_items.md
git commit -m "docs(specs): record the measured §9.3 margin pattern in Stage 5's Consumes"
```

---

### Task 4: Emit §13.6's state-share absolute error

**Implements:** R-S5G-4

This task comes **before** Task 5 deliberately. It adds a metric *name* to an existing family and changes no schema; Task 5 adds *columns*. Sequenced this way, each golden regeneration is attributable to exactly one named behaviour change, which is what gate-inputs §4 item 6 demands. Combined, one diff would carry two changes and the requirement could not be honoured per-change.

§13.6's other two absentees — size-share absolute error and top-size-class/rank accuracy — are size-class concepts §13.6 qualifies "where meaningful", and Stage 4 scores no size arm. R-S5G-4 says they are honestly Stage 6's and **MUST NOT be built here**.

**Files:**
- Modify: `src/logging_employment/validate/metrics.py`
- Modify: `src/logging_employment/validate/harness.py`
- Modify: `tests/unit/test_validate_metrics_point.py`
- Modify: `tests/unit/test_validate_scoreboard.py` — **not optional, and not Task 5's.** `national_totals` becomes REQUIRED here, and this file calls `point_metrics` twice. Measured in plan order: skipping it leaves **19 failed** in that one file, and Task 4 cannot reach green.
- Modify: `tests/fixtures/validation/validation_metrics_golden.parquet` (regenerated)

**Interfaces:**
- Consumes: `contracts.HarmonizedData.qcew_monthly`'s `area_type` / `reference_month` / `employment_value`.
- Produces: `national_monthly_totals(monthly: pl.DataFrame) -> pl.DataFrame` with columns `("reference_month", "national_employment")`; `point_metrics` gains a **required** keyword `national_totals: pl.DataFrame`. Task 5 restructures the same function — read both tasks before editing either.

- [x] **Step 1: Write the failing tests**

Replace `tests/unit/test_validate_metrics_point.py`'s `_scores()` and add three tests. The fixture gains `state_fips` and `reference_month`, which Task 5 also needs.

```python
def _scores():
    return pl.DataFrame(
        {
            "estimator_id": ["a", "a", "a", "b", "b", "b"],
            "cell_id": ["c1", "c2", "c3"] * 2,
            "state_fips": ["06", "41", "23"] * 2,
            "reference_month": ["2019-03", "2019-03", "2019-04"] * 2,
            "truth": [100.0, 200.0, 300.0] * 2,
            "estimate": [110.0, 180.0, None, None, None, None],
            "decline_kind": [None, None, "data_gap", "by_design", "by_design", "by_design"],
        }
    )


def _national():
    return pl.DataFrame(
        {
            "reference_month": ["2019-03", "2019-04"],
            "national_employment": [1000.0, 2000.0],
        }
    )


def test_state_share_absolute_error_divides_each_cell_by_its_own_month_national_total():
    """§13.6's state-share absolute error, R-S5G-4.

    Both scored cells fall in 2019-03, whose national total is 1000: |110-100|/1000 = 0.01 and
    |180-200|/1000 = 0.02, so the mean is 0.015. Computing it against a pooled denominator instead
    would let a large month dominate a small one, which is the comparison a SHARE metric exists to
    avoid.
    """
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    value = out.filter(
        (pl.col("estimator_id") == "a") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert abs(value - 0.015) < 1e-12


def test_state_share_absolute_error_is_null_when_nothing_scored():
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    value = out.filter(
        (pl.col("estimator_id") == "b") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert value is None


def test_a_month_with_no_national_row_is_excluded_rather_than_counted_as_zero_error():
    """Null, never 0.0 — the module rule. A cell whose month has no denominator has no share."""
    out = point_metrics(
        _scores(),
        regime="r",
        seed=1,
        arm="state_total",
        national_totals=_national().filter(pl.col("reference_month") == "2019-04"),
    )
    value = out.filter(
        (pl.col("estimator_id") == "a") & (pl.col("metric_name") == "state_share_absolute_error")
    )["value"].item()
    assert value is None
```

The three existing tests in this file also gain `national_totals=_national()` at their `point_metrics(...)` call — the parameter is required, so they will not run otherwise.

- [x] **Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/unit/test_validate_metrics_point.py -q
```
Expected, verified: `6 failed in 0.16s`, every failure `TypeError: point_metrics() got an unexpected keyword argument 'national_totals'` (message text verified against the pre-task signature).

- [x] **Step 3: Implement**

In `metrics.py`, extend `_POINT_NAMES` and add the denominator builder and the metric:

```python
_POINT_NAMES = ("mae", "rmse", "bias", "wape", "median_ape", "state_share_absolute_error")


def national_monthly_totals(monthly: pl.DataFrame) -> pl.DataFrame:
    """The published national employment level per month, as `state_share_absolute_error`'s base.

    Derived from the MASKED frame by its only caller, not from the unmasked one. The two agree --
    every mask this harness applies hides a state cell and leaves the national row alone -- so the
    choice buys no different number; it buys a §13.4 leakage argument that is structural instead of
    verbal. A denominator read out of the unmasked frame would have to be argued safe; one read out
    of a frame `assert_no_retained_truth` has already cleared cannot carry withheld truth at all.

    This is NOT `SRC-QCEW-006`'s declined national/state identity. That decline forbids a hard
    CONSTRAINT ROW equating the national level to the state sum, and
    `constraints/rows.py::assert_no_national_employment_margin` still enforces it. A metric
    denominator asserts no identity and enters no constraint system: it rescales an error that was
    already computed, so §9.3's prohibition is untouched.
    """
    return (
        monthly.filter(pl.col("area_type") == "national")
        .select("reference_month", pl.col("employment_value").cast(pl.Float64))
        .rename({"employment_value": "national_employment"})
    )


def _state_share_absolute_error(scored: pl.DataFrame) -> float | None:
    """§13.6's state-share absolute error: mean |estimate - truth| / national employment.

    PER MONTH, not pooled. The share is of the month the cell belongs to, so a 2017 error and a
    2024 error are made comparable before they are averaged; dividing the pooled absolute error by
    a pooled national total instead would weight each month by its own size, which is what `mae`
    and `wape` already do. Stated because the metric is otherwise easy to read as a rescaled MAE:
    it is a rescaled MAE only on a window whose national level is constant, and D1's is not.

    A cell whose month carries no national row is EXCLUDED, and an all-excluded set yields None --
    the module's "Null, never 0.0" rule. Measured 2026-09-11 on `data/staged/qcew_monthly.parquet`,
    all 96 national rows are `observed` with a non-null `employment_value`, so no cell is dropped
    on D1; the branch guards a revision, not today's data.
    """
    usable = scored.filter(
        pl.col("national_employment").is_not_null() & (pl.col("national_employment") > 0)
    )
    if usable.is_empty():
        return None
    errors = (usable["estimate"] - usable["truth"]).abs() / usable["national_employment"]
    return float(errors.mean())
```

Change `point_metrics`' signature to

```python
def point_metrics(
    scores: pl.DataFrame,
    *,
    regime: str,
    seed: int,
    arm: str,
    national_totals: pl.DataFrame,
) -> pl.DataFrame:
```

append this paragraph to its docstring —

```text
    `national_totals` is REQUIRED rather than defaulted to None (R-S5G-4). §13.6 lists state-share
    absolute error "at minimum", so an overload that silently emits it as null whenever a caller
    forgets the argument would reinstate the absence this requirement exists to close -- and it
    would do so on the artifact, where nothing downstream can tell "no denominator" from "no
    error". `national_monthly_totals` builds the frame.
```

— join the denominator on before the loop (`joined = scores.join(national_totals, on="reference_month", how="left")`, iterating `joined` instead of `scores`), and add one entry to the `values` dict:

```python
            "state_share_absolute_error": _state_share_absolute_error(scored),
```

- [x] **Step 4: Run the tests to verify they pass**

```bash
uv run pytest tests/unit/test_validate_metrics_point.py -q
```
Expected, verified: `6 passed in 0.12s`.

- [x] **Step 5: Wire the harness**

Add `national_monthly_totals` to the `from .metrics import (...)` block, and replace the `point_metrics` call in `run_pseudo_suppression`'s scoring loop:

```python
            all_metrics.append(
                point_metrics(
                    scored,
                    regime=name,
                    seed=seed,
                    arm=arm,
                    # From the MASKED frame: a denominator taken from `data` would have to be
                    # argued leak-free, and this one has already passed
                    # `assert_no_retained_truth` three lines above.
                    national_totals=national_monthly_totals(masked.qcew_monthly),
                )
            )
```

- [x] **Step 6: Repair the scoreboard test fixtures the required parameter breaks**

`national_totals` is now required and `tests/unit/test_validate_scoreboard.py` calls `point_metrics`
twice. **Measured in plan order: without this step the suite is `19 failed`, all in this one file.**
The helper frames also need the two columns the join and Task 5 read.

Add the denominator helper above `_metrics()`:

```python
def _national():
    """R-S5G-4's denominator. One month, so every scored cell shares it."""
    return pl.DataFrame({"reference_month": ["2019-03"], "national_employment": [1000.0]})
```

In `_scores()`, after `"cell_id"`:

```python
            "state_fips": ["06", "41"] * 2,
            "reference_month": ["2019-03", "2019-03"] * 2,
```

In `_seed_metrics`, add `"state_fips": []` and `"reference_month": []` to the `rows` dict and append
to them in the loop:

```python
            rows["state_fips"].append("06")
            rows["reference_month"].append("2019-03")
```

Then pass the denominator at both `point_metrics` call sites:

```python
            point_metrics(
                scores,
                regime="small_cell_biased",
                seed=1024,
                arm="state_total",
                national_totals=_national(),
            ),
```

```python
            point_metrics(
                scores, regime=regime, seed=seed, arm="state_total", national_totals=_national()
            ),
```

Run: `uv run pytest tests/unit/test_validate_scoreboard.py -q` — expected, verified: `25 passed`.

- [x] **Step 7: Characterize the golden delta BEFORE regenerating it**

§17.6 requires a documented reason for re-pinning a golden, and "the tests went green" is not one. Run this and read the output:

```bash
uv run python -c "
import polars as pl
from pathlib import Path
from logging_employment.baselines.runner import REGISTRY
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.harness import run_pseudo_suppression
REPO = Path('.').resolve()
cfg = load_config(REPO/'config.yaml')
cfg = cfg.model_copy(update={'validation': cfg.validation.model_copy(
    update={'replicates_per_regime': 3, 'pseudo_suppression_seeds': [1024]})})
produced = run_pseudo_suppression(HarmonizedData.load(REPO/'tests'/'fixtures'/'baselines'), REGISTRY, cfg).metrics
golden = pl.read_parquet(REPO/'tests'/'fixtures'/'validation'/'validation_metrics_golden.parquet')
keys = ['regime','seed','mask_arm','estimator_id','metric_family','metric_name']
old = produced.filter(pl.col('metric_name').is_null() | (pl.col('metric_name') != 'state_share_absolute_error'))
j = old.join(golden, on=keys, how='full', suffix='_g', nulls_equal=True)
print('columns identical:', produced.columns == golden.columns)
print('rows', golden.height, '->', produced.height)
print('columns moved on pre-existing rows:', [c for c in golden.columns if c not in keys and j.filter(~(pl.col(c).eq_missing(pl.col(c+'_g')))).height])
"
```
Expected, verified: `columns identical: True`, `rows 1168 -> 1238`, `columns moved on pre-existing rows: []`.

**`nulls_equal=True` is load-bearing, not decoration.** `decline_and_basis_report` emits no `metric_name`, so it is NULL on 70 of the golden's rows; without it those 70 fail to join on both sides and read as 8 moved columns — a false positive that looks exactly like the regression this step exists to catch. (`join_nulls` is the pre-1.24 spelling and is deprecated.)

- [x] **Step 8: Regenerate the golden**

```bash
uv run python -c "
from pathlib import Path
from logging_employment.baselines.runner import REGISTRY
from logging_employment.build import write_parquet_deterministic
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.harness import run_pseudo_suppression
REPO = Path('.').resolve()
cfg = load_config(REPO/'config.yaml')
cfg = cfg.model_copy(update={'validation': cfg.validation.model_copy(
    update={'replicates_per_regime': 3, 'pseudo_suppression_seeds': [1024]})})
out = run_pseudo_suppression(HarmonizedData.load(REPO/'tests'/'fixtures'/'baselines'), REGISTRY, cfg).metrics
print('rows', out.height, 'sha256', write_parquet_deterministic(out, REPO/'tests'/'fixtures'/'validation'/'validation_metrics_golden.parquet'))
"
uv run pytest tests/integration/test_validation_golden.py tests/unit/test_validate_metrics_point.py -q
```
Expected, verified: `rows 1238 sha256 5caaa3dbaa8ac8dfd3f0205b0fad0d4e8406297e420691f29b1cd5680757e91b`, then `13 passed in 12.30s`.

- [x] **Step 9: Commit, with the reason in the message**

```bash
git add src/logging_employment/validate/ tests/unit/test_validate_metrics_point.py tests/unit/test_validate_scoreboard.py tests/fixtures/validation/validation_metrics_golden.parquet
git commit -m "feat(validate): emit §13.6's state-share absolute error

R-S5G-4. Golden regenerated: 1168 -> 1238 rows, all 70 new rows are
state_share_absolute_error, zero columns moved on the pre-existing 1168
(verified by join, nulls_equal=True). No schema change."
```

---

### Task 5: Emit §13.10's per-stratum WAPE and coverage

**Implements:** R-S5G-1

The stratum is `validate/regimes.py::CENSUS_DIVISIONS` and **no second partition is introduced** — R-S5G-1 forbids one, and that module's own comment already requires §13.6's state-share strata, §13.7's calibration-by-region and Stage 5's §17.5 region effects to partition on the same thing. §13.7's *other* calibration strata — state size, gap duration, suppression propensity — are **not built here**, the same scoping move R-S5G-4 makes for the size metrics.

**Files:**
- Modify: `src/logging_employment/contracts.py`
- Modify: `src/logging_employment/validate/regimes.py`
- Modify: `src/logging_employment/validate/metrics.py`
- Modify: `src/logging_employment/validate/scoreboard.py`
- Modify: `src/logging_employment/validate/harness.py`
- Modify: `tests/unit/test_validate_metrics_point.py`, `tests/unit/test_validate_scoreboard.py`, `tests/unit/test_contracts_validation.py`, `tests/integration/test_validation_golden.py`
- Modify: `tests/fixtures/validation/validation_metrics_golden.parquet` (regenerated)

**Interfaces:**
- Consumes: Task 4's `point_metrics` signature and `_state_share_absolute_error`.
- Produces: `contracts.STRATUM_KINDS = ("overall", "census_division")`; `VALIDATION_METRIC_SCHEMA` gains `stratum_kind: pl.String` and `stratum_value: pl.String`, **appended**; `regimes.DIVISION_OF: dict[str, str]`; `metrics.with_census_division(scores) -> pl.DataFrame`. Stage 5's gate reads the stratified rows from `validation_metrics.parquet`, **never from the scoreboard**.

**The two traps this task is shaped around**, both found by running it:

1. **`build_scoreboard` fans out.** Its headline filter is `metric_family == "point" & metric_name == "wape"`. Per-division rows match both clauses, the left join to `basis` multiplies, and `validate_frame` compares names and dtypes — it cannot see a row count. §13.10's comparand is `runs/f03023ac9f3a/validation_scoreboard.parquet` at `(270, 13)`; a fan-out there corrupts the number Stage 5 is promoted against. The filter gains `stratum_kind == "overall"` **in this task**, not later.
2. **The golden's sort key stops being total.** `wape` and `coverage_0.90` now appear once as `overall` and once per division under otherwise identical key values, so a sort on the old six fields leaves them tied and `.equals` compares whatever order each side happened to emit.

- [x] **Step 1: Write the failing tests**

Append to `tests/unit/test_validate_metrics_point.py`:

```python
def test_wape_is_emitted_per_census_division_with_that_division_s_own_denominator():
    """R-S5G-1: §13.10's per-stratum gate needs a WAPE it can read, with its own base.

    `06` and `41` are both `pacific` and both scored: (|110-100| + |180-200|) / (100 + 200) = 0.1,
    over a denominator of 2 masked cell-rows rather than the estimator's 3.
    """
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    pacific = out.filter(
        (pl.col("estimator_id") == "a")
        & (pl.col("stratum_kind") == "census_division")
        & (pl.col("stratum_value") == "pacific")
    )
    assert pacific["metric_name"].to_list() == ["wape"]
    assert abs(pacific["value"].item() - 0.1) < 1e-12
    assert pacific["denominator"].item() == 2.0
    assert pacific["n_scored"].item() == 2


def test_only_the_divisions_present_in_the_replicate_are_emitted():
    """A division this mask never touched has no row, rather than a null one a gate would read."""
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    divisions = set(out.filter(pl.col("stratum_kind") == "census_division")["stratum_value"])
    assert divisions == {"pacific", "new_england"}


def test_an_unstratified_row_carries_the_overall_sentinel_and_never_a_null():
    """The `mask_arm` defect, refused by construction: `validate_frame` cannot see a null."""
    out = point_metrics(
        _scores(), regime="r", seed=1, arm="state_total", national_totals=_national()
    )
    assert out["stratum_kind"].null_count() == 0
    assert out["stratum_value"].null_count() == 0
    overall = out.filter(pl.col("stratum_kind") == "overall")
    assert overall["stratum_value"].unique().to_list() == ["all"]


def test_a_state_outside_the_census_partition_is_refused_rather_than_bucketed():
    """`72` is Puerto Rico: a REQ-002 universe violation, not a stratum needing a home."""
    import pytest

    from logging_employment.errors import ConceptViolationError

    rogue = _scores().with_columns(
        pl.when(pl.col("cell_id") == "c1")
        .then(pl.lit("72"))
        .otherwise(pl.col("state_fips"))
        .alias("state_fips")
    )
    with pytest.raises(ConceptViolationError, match="72"):
        point_metrics(rogue, regime="r", seed=1, arm="state_total", national_totals=_national())
```

And append the grain guard to `tests/unit/test_validate_scoreboard.py`:

```python
def test_the_board_keeps_one_row_per_group_when_the_metrics_carry_strata():
    """R-S5G-1's fan-out guard: the board's grain must not follow the partition.

    `build_scoreboard` selects `metric_family == 'point' & metric_name == 'wape'`. Per-division
    WAPE rows match both clauses, so without the `stratum_kind == 'overall'` filter the left join
    to `basis` returns a row per division per group and the board silently multiplies --
    `validate_frame` compares names and dtypes and cannot see a row count. §13.10's comparand is a
    (270, 13) board; a fan-out there corrupts the number Stage 5 is promoted against.
    """
    metrics = _metrics()
    stratified = metrics.filter(pl.col("stratum_kind") == "census_division")
    assert stratified.height > 0, "fixture must actually carry stratified rows"
    board = build_scoreboard(metrics)
    assert board.height == metrics.filter(
        (pl.col("metric_family") == "point")
        & (pl.col("metric_name") == "wape")
        & (pl.col("stratum_kind") == "overall")
    ).height
    assert board.select("regime", "seed", "estimator_id").n_unique() == board.height
```

- [x] **Step 2: Run them to verify they fail**

```bash
uv run pytest tests/unit/test_validate_metrics_point.py tests/unit/test_validate_scoreboard.py -q
```
Expected, verified against the reconstructed post-Task-4 tree: **`5 failed, 31 passed in 0.48s`** — four with

```text
polars.exceptions.ColumnNotFoundError: unable to find column "stratum_kind"; valid columns: ["regime", "seed", "mask_arm", "estimator_id", "metric_family", "denominator", "denominator_basis", "n_scored", "n_declined_by_design", "n_declined_data_gap", "n_declined_reconciliation_failure", "metric_name", "value"]
```

and one `Failed: DID NOT RAISE ConceptViolationError` — the Puerto Rico test, because `with_census_division` does not exist yet and so nothing refuses.

- [x] **Step 3: Declare the closed set, the columns, and the partition inverse**

In `contracts.py`, immediately after `MASK_ARMS`:

```python
# §13.10's "major stratum", as a closed set (R-S5G-1). `overall` is a VALUE, never a null: an
# unstratified row carrying a null `stratum_kind` is precisely the `mask_arm` defect this package
# already paid for once -- `validate_frame` compares names and dtypes, `dict[str, pl.DataType]` has
# no nullability slot, and 70 null-armed rows persisted through a gate they were already subject to.
# The partition is `validate/regimes.py::CENSUS_DIVISIONS` and NOT a second one: that module's own
# comment requires §13.6's state-share strata, §13.7's calibration-by-region and Stage 5's §17.5
# region effects to partition on the SAME thing, and this is that thing.
STRATUM_KINDS: tuple[str, ...] = ("overall", "census_division")
```

At the **end** of `VALIDATION_METRIC_SCHEMA`:

```python
    # APPENDED, not inserted (R-S5G-1). `schema_fingerprint` hashes the ORDERED pairs, so placing
    # these beside the columns they qualify would re-fingerprint every field after them for no
    # gain; appended, the diff is two pairs at the end.
    "stratum_kind": pl.String,
    "stratum_value": pl.String,
```

At the end of `VALIDATION_REQUIRED_NON_NULL["validation_metrics"]`:

```python
        # Non-null BY CONSTRUCTION: every emitter writes the `overall`/`all` sentinel pair onto
        # rows it does not stratify, so there is no path that leaves either null.
        "stratum_kind",
        "stratum_value",
```

In `assert_declared_provenance`, add the sixth pair and correct the docstring's count (`The five tuples` → `The six tuples ... , SUPPRESSION_TYPES, STRATUM_KINDS`):

```python
        # R-S5G-1. Added with a CALLER: `validate/harness.py` runs this over the assembled metrics
        # frame. `INTERVAL_SOURCES` is declared and checked by nothing at runtime, and
        # `validate/CLAUDE.md` already carries that as an open item -- a second undeclared-in-
        # practice set is the thing this addition exists not to become.
        ("stratum_kind", STRATUM_KINDS),
```

In `validate/regimes.py`, directly after the `CENSUS_DIVISIONS` literal:

```python
# The same partition, inverted once at import rather than per metric row (R-S5G-1). Derived from
# CENSUS_DIVISIONS rather than typed out: a second literal is a second partition the moment one of
# them is edited, and R-S5G-1 forbids a second partition.
DIVISION_OF: dict[str, str] = {
    fips: division for division, members in CENSUS_DIVISIONS.items() for fips in members
}
```

Check it, verified: `set(DIVISION_OF) == set(constants.STATES_DC_FIPS)` is `True` at 51 keys.

- [x] **Step 4: Emit the strata**

> Deviation: per-division coverage rows first shipped inheriting the estimator's `n_scored` (51 of 72 golden rows had `n_scored > denominator`); fixed after review with an independent unit module. Stratification is `state_total`-only, and division coverage exists only on the ensemble branch, so the WAPE and coverage families do not always share strata — gates must outer-join.

In `metrics.py`, add the imports `from ..errors import ConceptViolationError` and `from .regimes import DIVISION_OF` (no cycle: `regimes` imports `mask` and `propensity`, never `metrics`), then above `bound_metrics`:

```python
# The sentinel pair an unstratified row carries. A VALUE, never a null -- see `STRATUM_KINDS`.
_OVERALL: dict[str, object] = {"stratum_kind": "overall", "stratum_value": "all"}


def with_census_division(scores: pl.DataFrame) -> pl.DataFrame:
    """Attach §13.10's stratum to each scored row, refusing a FIPS the partition does not cover.

    Fail-closed rather than an `unassigned` bucket: `DIVISION_OF` covers states+DC exactly
    (measured, 51 of 51 against `constants.STATES_DC_FIPS`), so an uncovered value means a
    territory or a malformed code reached the scoring frame -- the REQ-002 universe violation
    `harmonize/universe.py` exists to prevent, not a stratum that needs a home. Bucketing it would
    put a row §13.10 must not gate on into a stratum §13.10 gates on.
    """
    out = scores.with_columns(
        pl.col("state_fips").replace_strict(DIVISION_OF, default=None).alias("census_division")
    )
    unknown = sorted(set(out.filter(pl.col("census_division").is_null())["state_fips"].to_list()))
    if unknown:
        raise ConceptViolationError(
            f"state_fips {unknown} falls in no Census division; the partition is "
            f"validate/regimes.py::CENSUS_DIVISIONS and covers states+DC only"
        )
    return out
```

Add `**_OVERALL,` as the first entry of the `base` / row dict in **all four** of `bound_metrics`, `probabilistic_metrics`, `decline_and_basis_report` and `constraint_metrics`.

Split `point_metrics`' body so the same computation serves both emissions:

```python
    rows: list[dict[str, object]] = []
    joined = with_census_division(scores.join(national_totals, on="reference_month", how="left"))
    for (estimator,), group in joined.group_by("estimator_id", maintain_order=True):
        rows.extend(
            _point_rows(
                group, base=_base(regime, seed, arm, str(estimator)), names=_POINT_NAMES, **_OVERALL
            )
        )
        # §13.10's per-stratum gate needs WAPE and nothing else, so only WAPE is stratified
        # (R-S5G-1). Emitting all six per division would multiply the table by the partition for
        # five metrics no gate reads. The divisions PRESENT are enumerated, never the nine: a
        # division this replicate did not mask has no rows, and a zero-row WAPE of null would be
        # indistinguishable from a division that scored and failed.
        for division in sorted(set(group["census_division"].to_list())):
            rows.extend(
                _point_rows(
                    group.filter(pl.col("census_division") == division),
                    base=_base(regime, seed, arm, str(estimator)),
                    names=("wape",),
                    stratum_kind="census_division",
                    stratum_value=division,
                )
            )
    return pl.DataFrame(rows)


def _base(regime: str, seed: int, arm: str, estimator: str) -> dict[str, object]:
    """The identifying half of a point row, shared by the overall and the stratified emissions."""
    return {
        "regime": regime,
        "seed": seed,
        "mask_arm": arm,
        "estimator_id": estimator,
        "metric_family": "point",
    }


def _point_rows(
    group: pl.DataFrame,
    *,
    base: dict[str, object],
    names: tuple[str, ...],
    stratum_kind: str,
    stratum_value: str,
) -> list[dict[str, object]]:
    """`names` computed over `group`, which is a whole estimator's rows or one stratum's.

    EVERY row carries the denominator of the set it was computed over, stratified or not (R-COMP-10
    and §13.10's "no major stratum degrades by more than 2% WAPE"). A stratified WAPE reported
    against the pooled denominator would make a two-cell division and a two-hundred-cell division
    read as equally solid evidence for failing a promotion.
    """
    scored = group.filter(pl.col("estimate").is_not_null())
    counts = {
        kind: group.filter(pl.col("decline_kind") == kind).height
        for kind in ("by_design", "data_gap", "reconciliation_failure")
    }
    row = {
        **base,
        "stratum_kind": stratum_kind,
        "stratum_value": stratum_value,
        "denominator": float(group.height),
        "denominator_basis": "masked_cell_rows",
        "n_scored": scored.height,
        "n_declined_by_design": counts["by_design"],
        "n_declined_data_gap": counts["data_gap"],
        "n_declined_reconciliation_failure": counts["reconciliation_failure"],
    }
    if scored.height == 0:
        # Null, never 0.0. A zero error over zero rows reads as perfect accuracy.
        return [{**row, "metric_name": n, "value": None} for n in names]

    err = scored["estimate"] - scored["truth"]
    abs_err = err.abs()
    values = {
        "mae": abs_err.mean(),
        "rmse": float((err**2).mean() ** 0.5),
        "bias": err.mean(),
        "wape": (
            float(abs_err.sum() / scored["truth"].abs().sum())
            if scored["truth"].abs().sum()
            else None
        ),
        "median_ape": (
            float((abs_err / scored["truth"].abs()).median())
            if scored.filter(pl.col("truth").abs() > 0).height == scored.height
            else None
        ),
        "state_share_absolute_error": _state_share_absolute_error(scored),
    }
    return [{**row, "metric_name": n, "value": values[n]} for n in names]
```

In `probabilistic_metrics`, iterate `with_census_division(scores).group_by(...)`, add `by_division: dict[str, list[int]] = {}` beside `scored`, bucket inside the existing per-cell loop, and emit after the `n_clipped_at_zero` row:

```python
            for level in _LEVELS:
                lo, hi = empirical_interval(ensemble, level)
                hit = lo <= row["truth"] <= hi
                if hit:
                    covered[level] += 1
                if level == 0.90:
                    widths.append(hi - lo)
                    # BUCKETED HERE, not recomputed in a second pass (R-S5G-1). The ensemble is
                    # the harness's dominant cost and is superlinear in scored cells, so a
                    # per-division pass would multiply the expensive half by the partition to
                    # learn something this loop already knows. The CALIBRATION POOL stays global:
                    # leave-one-out over every scored residual, never over the division's alone.
                    # Stratifying the pool would shrink each sample to a handful of cells and
                    # report the resulting noise as miscalibration.
                    tally = by_division.setdefault(row["census_division"], [0, 0])
                    tally[0] += 1
                    tally[1] += int(hit)
```

```python
        for division, (seen, hits) in sorted(by_division.items()):
            rows.append(
                {
                    **common,
                    "stratum_kind": "census_division",
                    "stratum_value": division,
                    "metric_name": "coverage_0.90",
                    "value": hits / seen if seen else None,
                    "denominator": float(
                        group.filter(pl.col("census_division") == division).height
                    ),
                    "calibration_sample_size": seen,
                }
            )
```

The ineligible / fewer-than-two-scored branch `continue`s before this and emits only its overall null row — a division-level coverage over an estimator with no ensemble would be a row whose value is null for a reason the gate cannot distinguish from failure.

- [x] **Step 5: Keep the scoreboard's grain**

In `scoreboard.build_scoreboard`, extend the headline filter:

```python
    headline = metrics.filter(
        (pl.col("metric_family") == "point")
        & (pl.col("metric_name") == "wape")
        # OVERALL ONLY (R-S5G-1). Without this clause the per-division WAPE rows match too, the
        # left join to `basis` fans out, and the board silently gains a row per division per
        # group -- `validate_frame` compares names and dtypes and would not see it. §13.10's
        # comparand is `runs/f03023ac9f3a/validation_scoreboard.parquet` at (270, 13); the gate
        # reads the stratified rows from `validation_metrics`, never from the board.
        & (pl.col("stratum_kind") == "overall")
    ).select(
```

- [x] **Step 6: Give `STRATUM_KINDS` a runtime caller**

In `harness.run_pseudo_suppression`, immediately before `board = build_scoreboard(metrics)`:

```python
    # The metrics frame gets the same closed-set gate the scores frame has had (R-S5G-1).
    # Declaring `STRATUM_KINDS` without a caller would repeat `INTERVAL_SOURCES`, which
    # `validate/CLAUDE.md` already records as declared-and-enforced-by-nothing.
    assert_declared_provenance(metrics)
```

- [x] **Step 7: Repair the two test fixtures the new columns break**

Each is a real consequence, not a chore, and each is named so the implementer does not mistake it for a regression. `tests/unit/test_validate_scoreboard.py` is NOT in this list: Task 4 Step 6 already gave it the columns and the denominator, and its `_metrics()` helper picks up the stratified rows for free — which is what Step 1's grain guard reads.

1. **`tests/unit/test_validate_metrics_point.py`** — the three *pre-existing* selectors now also match stratified rows. Scope each with `& (pl.col("stratum_kind") == "overall")`. This is the same defect `build_scoreboard` had; that it shows up here first is the test suite working.
2. **`tests/unit/test_contracts_validation.py::test_a_null_in_a_required_column_is_refused`** — its hand-built frame predates the two required columns, so the ABSENT-column branch fires first and masks the null branch the test is about. Add to the frame:

```python
            # Present so the ABSENT-column branch cannot fire first and mask the null branch this
            # test is about (R-S5G-1 added both to `VALIDATION_REQUIRED_NON_NULL`).
            "stratum_kind": ["overall", "overall"],
            "stratum_value": ["all", "all"],
```

- [x] **Step 8: Restore the golden's total sort order and scope its oracle**

In `tests/integration/test_validation_golden.py`, extend the key in `test_the_metrics_match_the_golden`:

```python
    # R-S5G-1 made the six-field key NON-TOTAL: `wape` and `coverage_0.90` now appear once as
    # `overall` and once per census division under otherwise identical values, so a sort on the old
    # key leaves those rows tied and `equals` compares whatever order each side happened to
    # produce. The stratum pair is what restores the total order.
    key = [
        "regime",
        "seed",
        "mask_arm",
        "estimator_id",
        "metric_family",
        "metric_name",
        "stratum_kind",
        "stratum_value",
    ]
```

and scope the hand-derived oracle in `test_a_hand_derived_row_reproduces_the_golden_interval`, adding to its `golden = ...filter(...)`:

```python
        # The oracle re-derives coverage over the WHOLE group's leave-one-out pool, which is the
        # overall row. A per-division row shares this row's `metric_name` and would make `_value`
        # ambiguous (R-S5G-1).
        & (pl.col("stratum_kind") == "overall")
```

- [x] **Step 9: Characterize the delta, then regenerate**

> Deviation: `765e43a1…` reproduced but carried the `n_scored` defect; the golden was regenerated after review to `2bec94b0…` (only `n_scored` moved, on 51 division coverage rows). The characterization's pre-existing-rows join could not see defects in the rows this task ADDED.

Run the Task 4 Step 7 snippet again with **two** changes — the `old` line, and the first `print`, which must now report the added columns rather than assert none were added:

```python
old = produced.filter(pl.col('stratum_kind') == 'overall').drop('stratum_kind','stratum_value')
```

```python
print('new columns:', [c for c in produced.columns if c not in golden.columns])
```

Left as `columns identical:` it prints `False` and tells you nothing about which columns moved,
which is the question this step exists to answer.

Expected, verified: `new columns: ['stratum_kind', 'stratum_value']`, `rows 1238 -> 1490` (`overall rows 1238`, `stratified rows 252`), `columns moved on pre-existing rows: []`, stratified metric names `['coverage_0.90', 'wape']`, all nine divisions present, and `0` nulls in both new columns. Then regenerate with the Task 4 Step 8 snippet — verified: `rows 1490 sha256 765e43a101795a465893d235dbb00d67c1a1198425979f14f6e6e6e4d43efa30`.

- [x] **Step 10: Run every gate**

```bash
uv run ruff format src tests && uv run ruff check src tests --fix && uv run ruff check src tests
uv run interrogate src
uv run pytest -q
```
Expected: `All checks passed!`, `RESULT: PASSED (minimum: 100.0%, actual: 100.0%)`, and **passed up by exactly 5 (four point tests plus the board-grain guard), skipped unchanged**. In plan order the absolute is `1326 + 5` = **`1331 passed, 70 skipped`**. The `--fix` is not optional: the new `metrics.py` imports trip `I001` and ruff fixes them. Every test added here is fixture-based and none is data-bound, which is why `skipped` must not move.

- [x] **Step 11: Commit**

```bash
git add src/logging_employment/ tests/ tests/fixtures/validation/validation_metrics_golden.parquet
git commit -m "feat(validate): emit §13.10's per-stratum WAPE and 90% coverage by Census division

R-S5G-1. Two columns appended to VALIDATION_METRIC_SCHEMA with the overall/all
sentinel, STRATUM_KINDS enforced through assert_declared_provenance, and
build_scoreboard scoped to overall so the (270, 13) comparand keeps its grain.
Golden 1238 -> 1490 rows; zero columns moved on the pre-existing 1238."
```

---

### Task 6: Record `PromotionConfig`'s three keys as inert, per key

**Implements:** R-S5G-3

R-S5G-3 offers two outcomes: the keys are read by the promotion code path, or they are recorded inert the way `D-064` records its four. **This plan takes the second**, and the reason is a fact about the repo rather than a preference: `§13.10` compares a model against the preferred transparent baseline, and *Stage 5 produces the model*. An evaluator written now would fix its primary argument by guessing Stage 5's output type, and three of §13.10's six gates — hard constraints on draws, convergence diagnostics, disclosure review — are Stage 5 and Stage 8 concepts it could not represent at all. `D-091`'s own closure text admits this route: "the three keys are read **or recorded inert**".

**Files:**
- Modify: `src/logging_employment/config.py`
- Modify: `tests/unit/test_config_validation_block.py`
- Modify: `specs/deferred_items.md`

**Interfaces:**
- Consumes: Task 5's stratified metrics — they are what makes two of the three keys inert for a *different* reason than the third, which is the whole content of this record.
- Produces: no symbol. A tripwire test that reddens the day Stage 5 wires a key.

- [x] **Step 1: Write the failing tripwire test**

Append to `tests/unit/test_config_validation_block.py` (and add `from pathlib import Path` to its imports):

```python
def test_the_promotion_keys_are_still_unread_and_the_docstring_still_says_so():
    """R-S5G-3: a TRIPWIRE, not a prohibition. It fails when Stage 5 wires these keys.

    `PromotionConfig`'s docstring records all three as inert. A docstring cannot notice when it
    stops being true, and the failure mode is specific: the day a promotion path reads one of
    these, the note becomes a false statement in the file a reader consults first. Derived by
    searching `src/` rather than asserting a sentence exists, so it tracks the code and not the
    prose. When it reddens, the fix is to update the docstring — not to delete this test.
    """
    src = Path(__file__).resolve().parents[2] / "src" / "logging_employment"
    for key in (
        "minimum_wape_improvement",
        "maximum_major_stratum_wape_degradation",
        "nominal_coverage_tolerance",
    ):
        readers = [
            path.relative_to(src).as_posix()
            for path in src.rglob("*.py")
            if key in path.read_text() and path.name != "config.py"
        ]
        assert readers == [], f"{key} is now read by {readers}; update PromotionConfig's docstring"
```

- [x] **Step 2: Run it**

```bash
uv run pytest tests/unit/test_config_validation_block.py -q
```
Expected, verified: `4 passed in 0.02s`. **This test passes immediately, and that is correct** — it pins today's truth so tomorrow's change is announced. It is the docstring in Step 3 that is the deliverable; the test is what keeps it honest. (Without the `Path` import it fails with `NameError`, which is the only red this step produces.)

- [x] **Step 3: Write the record**

Replace `PromotionConfig`'s docstring in `config.py`:

```python
class PromotionConfig(_Strict):
    """§13.10's gates. Configurable engineering thresholds, not findings.

    ALL THREE KEYS ARE INERT TODAY, and this note is the record R-S5G-3 requires rather than a
    disclaimer. Each reaches `config.resolved.yaml` and folds into `runs.run_id`, so an unread key
    is a claim in a run's record that no code backs -- the defect `D-064` names for four other
    keys. The convention there is to write inertness into the code (`constraints/matrix.py`'s "NO
    REAL INPUT UNTIL STAGE 6", `errors.py::NoHarvestFactorError`), which is what this is.

    They are inert for TWO different reasons, and the distinction is the useful half:

    - `maximum_major_stratum_wape_degradation` and `nominal_coverage_tolerance` have their INPUT as
      of R-S5G-1. `validate/metrics.py` now emits a per-census-division WAPE and a per-division
      90% coverage into `validation_metrics.parquet`, so both gates are evaluable from a shipped
      artifact. What is missing is the CANDIDATE to evaluate: §13.10 compares a model against the
      preferred transparent baseline and Stage 5 produces the model.
    - `minimum_wape_improvement` is missing both. Its comparison needs a second scoreboard, and
      `validation_scoreboard.parquet` exists in one copy -- the baseline one.

    NO EVALUATOR IS BUILT HERE, deliberately. A function whose primary argument is Stage 5's
    not-yet-designed output would fix that signature by guessing it, and three of §13.10's six
    gates (hard constraints on draws, convergence diagnostics, disclosure review) are Stage-5 and
    Stage-8 concepts an evaluator written now could not represent at all. Stage 5 wires these;
    `tests/unit/test_config_validation_block.py` fails the day it does, so this docstring cannot
    quietly outlive its truth.
    """

    minimum_wape_improvement: float = 0.05
    maximum_major_stratum_wape_degradation: float = 0.02
    nominal_coverage_tolerance: float = 0.05
```

- [x] **Step 4: File the deferred item beside `D-064`'s four**

Append to `specs/deferred_items.md`. **`D-091` is NOT ticked here** — its closure text is "R-S5G-1..3 ship", and R-S5G-2 is Task 7's ruling. Task 7 ticks it.

```markdown
- [ ] `D-109` **`PromotionConfig`'s three keys are recorded inert rather than read.** R-S5G-3 ruled
      2026-09-11 that no §13.10 evaluator is built before Stage 5 exists: `minimum_wape_improvement`
      needs a second `validation_scoreboard.parquet` and there is one,
      and `maximum_major_stratum_wape_degradation` / `nominal_coverage_tolerance` have their input
      as of R-S5G-1 but no candidate to evaluate. All three fold into `runs.run_id` via
      `resolved_dict`, so this is `D-064`'s shape with a recorded reason rather than silence.
      Size: quick-fix. Done when: Stage 5's promotion record reads all three —
      `tests/unit/test_config_validation_block.py::test_the_promotion_keys_are_still_unread_and_the_docstring_still_says_so`
      reddens on that day and names the keys that moved.
```

- [x] **Step 5: Run the gates**

```bash
uv run ruff format src tests && uv run ruff check src tests
uv run interrogate src && uv run pytest -q
```
Expected: `All checks passed!`, `RESULT: PASSED`, and **passed up by exactly 1, skipped unchanged** — in plan order **`1332 passed, 70 skipped`**.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/config.py tests/unit/test_config_validation_block.py specs/deferred_items.md
git commit -m "docs(config): record PromotionConfig's three keys inert, per key, with a tripwire

R-S5G-3. Files D-109; D-091 closes in Task 7, once R-S5G-2's ruling lands."
```

---

### Task 7: Rule on §13.10 and record it

**Implements:** R-S5G-2

R-S5G-2 is a DECISION requirement whose output is a written ruling. It refuses a third outcome explicitly: **shipping Stage 5 with two gates silently unevaluated is not available.**

**Files:**
- Modify: `specs/stage5-gate-inputs.md` (Status line — either way)
- Modify: `specs/logging-employment-spec.md` (§13.10 — only under Option B)

**Interfaces:**
- Consumes: Tasks 4, 5 and 6 as shipped.
- Produces: the sentence Stage 5's planner reads to know which gates bind.

- [x] **Step 1: Confirm which option the work actually landed on**

```bash
uv run python -c "
import polars as pl
g = pl.read_parquet('tests/fixtures/validation/validation_metrics_golden.parquet')
s = g.filter(pl.col('stratum_kind') == 'census_division')
print('stratified metric names:', sorted(set(s['metric_name'])))
print('divisions:', len(set(s['stratum_value'])))
print('state_share rows:', g.filter(pl.col('metric_name') == 'state_share_absolute_error').height)
"
```
Expected: `['coverage_0.90', 'wape']`, `9`, `70`. Both of §13.10's stratum gates now have an input, so **Option A holds and §13.10 stands as written.** Only if this output disagrees does Option B — amending §13.10 and striking or deferring the stratum clauses with a named owner — come into play.

- [x] **Step 2: Write the ruling into the Status line**

> Deviation: the Status line also records R-S5G-5's refutation of spec §1.2, the routed bound (`D-111`), the regenerated D1 artifact, and `D-112`'s caveat that the coverage gate must not be applied yet.

Replace `specs/stage5-gate-inputs.md`'s Status line:

```markdown
**Status:** COMPLETE (2026-09-11) — implemented by plan 14
(`specs/plans/completed/14-stage5-gate-inputs.md`). **R-S5G-2 ruled Option A: §13.10 stands as
written and is not amended.** Both stratum gates now read
`validation_metrics.parquet`'s `stratum_kind = 'census_division'` rows — a per-division WAPE and a
per-division 90% coverage over the nine Census divisions — and §13.6's state-share absolute error
is emitted. The three `PromotionConfig` keys are recorded inert per key rather than read (R-S5G-3,
`D-109`); no evaluator is built before the stage that produces the candidate. §13.10's gate remains
applied over NINE of the thirteen regimes (`D-071`).
```

- [x] **Step 3: Do NOT amend the spec under Option A**

The spec header says nothing here amends `specs/logging-employment-spec.md` unconditionally — only under Option B, and only as that requirement's recorded output. Under Option A, `specs/logging-employment-spec.md` is untouched by this task. Verify:

```bash
git diff --name-only HEAD -- specs/logging-employment-spec.md
```
Expected: empty.

- [x] **Step 4: Tick `D-091`**

Its closure condition is "R-S5G-1..3 ship", which is true only once this ruling is written: R-S5G-1
shipped in Task 5, R-S5G-3 in Task 6, R-S5G-2 here. In `specs/deferred_items.md`, tick it with
`→ done in plan 14`. Never delete it.

- [x] **Step 5: Commit**

```bash
git add specs/stage5-gate-inputs.md specs/deferred_items.md
git commit -m "docs(specs): rule R-S5G-2 Option A — §13.10 stands and both stratum gates now read"
```

---

### Task 8: Dispose of the REQ-027 consequence

**Implements:** R-S5G-8

R-S5G-8 binds **only if Task 2 found a disclosed parent**. It is a two-branch decision, and its scope is deliberately narrow: "this requirement is that the flag is actually set from the new margin, **not that a new mechanism is built**" — `disclosure/` already owns `exact_reconstruction_flag`.

**Files:**
- Modify: `specs/deferred_items.md`
- Create (Branch B only): `specs/stage5-parent-margin.md`

**Interfaces:**
- Consumes: Task 3's recorded ruling.
- Produces: either a closed requirement or a routed spec. Not code, either way.

- [x] **Step 1: Read the branch off the record, not off memory**

```bash
grep -o "MEASURED 2026-09-11[^.]*\." specs/logging-employment-spec-roadmap.md
```

- [x] **Step 2A — Branch A (no disclosed parent): close it and say what would reopen it**

> Deviation: applied only to the EXACT half, and scoped (`D-110`): no measured margin gives a live REQ-027 case, but the `113 - 1131 - 1132` path is unmeasured, so exactness is unknown on 252 quarters.

Append to `specs/deferred_items.md`:

```markdown
- [ ] `D-110` **`exact_reconstruction_flag` has no live instance, and the §9.3 measurement did not
      create one.** R-S5G-5 measured the parent-industry and ownership margins across all 32 D1
      quarters for `113`, `1133`, `11331` and total ownership at `113310`, and no suppressed
      private state-quarter carries a disclosed margin — the pattern is in
      `specs/findings/qcew-parent-margins.md`. `REQ-027`'s §14.4 route therefore stays exercisable
      only by constructed tests, as Stage 2's stamp already recorded.
      Size: quick-fix. Revisit if: a QCEW revision publishes a parent where the child is `N` —
      re-run `scripts/audit/qcew_parent_margins.py`, which re-derives its own 1,572 / 409 baseline
      and records whether the 2026-09-11 witness still holds.
```

Then tick `D-092` if Task 3 did not, and **stop**. Under Branch A nothing else in R-S5G-8 binds: there is no new margin for the flag to be set from.

- [x] **Step 2B — Branch B (a disclosed parent exists): route it, do not absorb it**

> Deviation: taken for the BOUND — routed to `specs/stage5-parent-margin.md` (R-PM-1..8, later corrected: a visible parent is retained per §13.2 step 4, and MILP reaches only the under-threshold subset) and `D-111`.

Setting the flag from a real margin is not a one-line change, and R-S5G-6 already enumerates why. Create `specs/stage5-parent-margin.md` with the header `> For agentic workers: REQUIRED SKILL: writing-plans`, this plan and `specs/findings/qcew-parent-margins.md` as its measured input, and requirements covering at minimum:

1. **Registry and ingest** — a `registry/sources.yaml` row per new slice, with the same measured-or-`[documented]` provenance every existing row carries; the fetch route reuses `ingest/qcew.py`'s dual-route interface rather than a second client.
2. **Constraints** — new cell kinds for the parent margins, and a builder in the shape of `rows.size_support_rows` / `rows.size_margin_rows`. `assert_no_national_employment_margin` guards a *different* margin (`SRC-QCEW-006`) and must keep guarding it.
3. **§13.2 step 4** — `validate/recover.py` must mask the parent whenever it masks the child. A harness that hides a state cell and leaves its identifying parent visible scores a cell that was never actually hidden, which is a §13.4 leak straight into the Stage 4 comparand.
4. **Disclosure** — `exact_reconstruction_flag` set from the exact cases only; the `upper_bound` cases are bounds and must not reach `release_observed` or `release_model_estimate` through this route (§14.4).
5. **`D-093` becomes reachable** — `_needs_milp` skips any cell whose `lower` or `upper` is `None`, so MILP ran on **0 of 4,775** rows. The first finite upper bound activates the HiGHS `mip_rel_gap` question, `D-032` and §9.6's width trigger together. That is cited as scope, not discovered later.
6. **The comparand moves.** Stage 4's scoreboard and `runs/f03023ac9f3a` were computed against an identification set with no finite state upper bound. The spec must say whether they are re-run.

File a deferred item pointing at it, tick `D-092`, and record in the Stage 5 roadmap block that the stage is blocked on it.

- [x] **Step 3: Commit**

```bash
git add specs/
git commit -m "docs(specs): dispose of R-S5G-8's REQ-027 consequence on the measured branch"
```

---

## Self-Review

**Spec coverage.** All eight requirements have a task: R-S5G-7 → Task 1, R-S5G-5 → Task 2, R-S5G-6 → Task 3, R-S5G-4 → Task 4, R-S5G-1 → Task 5, R-S5G-3 → Task 6, R-S5G-2 → Task 7, R-S5G-8 → Task 8. Gate-inputs §3's three out-of-scope groups (`D-093`/`D-095` and the rest of `D-091`..`D-101`; the §12.2/§15.2 anchor amendment; Stage 6's inheritances) are deliberately unimplemented and no task claims them — `D-093` appears only as *cited future scope* inside Task 8 Branch B, which is where R-S5G-6 requires the consequence to be named.

**Gate-inputs §4's six "how to know this is done" items** map to Task 5 (1), Task 6 (2), Task 4 (3), Task 3 (4), Task 1 (5) and every task's final gate (6).

**Ordering.** Task 1 first because R-S5G-7 forbids deferring it behind Task 2 and its only purpose is to make Task 2 visible. Task 2 second because it is the only network-bound task and the only one whose *result* changes a later task (Task 8's branch). Task 4 before Task 5 so each golden regeneration carries exactly one named behaviour change. Task 6 after Task 5 because the two-reasons distinction it records is only true once the stratified metrics exist. Tasks 7 and 8 are rulings and read the shipped state.

**Type consistency.** `national_monthly_totals` returns `("reference_month", "national_employment")` in Task 4 and is consumed under those names in Tasks 4 and 5. `point_metrics`' keyword is `national_totals` at every call site — one in `harness.py`, six in `test_validate_metrics_point.py`, two in `test_validate_scoreboard.py` (`_metrics` and `_seed_metrics`) — and all of them are updated in **Task 4**, where the parameter becomes required, not in Task 5. `stratum_kind` / `stratum_value` are spelled identically in `contracts.STRATUM_KINDS`, the schema, `VALIDATION_REQUIRED_NON_NULL`, `_OVERALL`, `_point_rows`, `build_scoreboard`'s filter and all four repaired test fixtures. `identification` takes the same five `parent_*` / `ownership_*` keys in Task 2's function, its tests, and Task 3's Branch B sentence.

**What this plan does not verify.** Task 2's `main()`, which is written out and marked NOT EXECUTED at the block itself; Tasks 1, 3, 7 and 8, which have no code. Everything else was executed, including both red steps. The golden row counts and sha256s (`1238` / `5caaa3db…`, `1490` / `765e43a1…`) and the plan-order suite absolutes (`1323`, `1326`, `1331`, `1332`, each against `70` skipped) were measured at `795a467`. **They are dated witnesses. The DELTA at each gate is the check; the absolute moves the moment the baseline does** — re-derive rather than re-quote.

**One defect this plan had until it was executed in plan order.** Task 4's file list omitted `tests/unit/test_validate_scoreboard.py`, and the fixture repair sat in Task 5. Because `national_totals` becomes required in Task 4, that ordering leaves Task 4 at **19 failed** — a task that cannot reach its own green step. It is recorded here because the same trap applies to any later task that makes an existing keyword required: the callers are not only the ones in the file you are editing.

**One thing a reviewer should push back on if they disagree.** Task 6 declines to build a §13.10 evaluator. The argument is that its primary argument has no producer until Stage 5, and `D-091`'s closure text permits the inert route explicitly. If a reviewer thinks the evaluator belongs here, the counter-argument they need to defeat is the one R-S5G-1 itself makes about independence: a gate whose input is built by the stage being gated is not an independent test, and that objection applies to an evaluator whose *signature* is guessed from the stage being gated just as much as to its inputs.
