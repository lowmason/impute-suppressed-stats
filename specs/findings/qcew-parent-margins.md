# §9.3 parent-industry and ownership margins on D1 — measured

**Measured:** 2026-09-11T16:24:31+00:00 (R-S5G-5, plan 14 Task 2). **Derived from
`data/raw/audit/qcew_parent_margins/summary.json`, not retyped** — by
`scripts/audit/render_parent_margins.py`, which is committed because the summary it reads is
gitignored, and which refuses to render if a conclusion its `summary_premises` or `extract_premises`
guards stops matching the data. The witness pair and Stage 0's agglvl inventory below are quoted
references, not measurements of this run.

**Extracts read:** 128, each verified against the sha256 the summary recorded, pinned
together by digest `e620bb5ead34003d5f4324dc8fe16a7fa3738c62124c4de5b0bf56baf282477b` over their sorted `(sha256, path)` pairs.
`_common.record_extract` rewrites a slice in place, so **compare against this digest, or copy the
directory aside, before re-running the audit.**

```bash
cd scripts/audit && set -a && source ../../.env && set +a && uv run --no-project qcew_parent_margins.py
uv run --no-project render_parent_margins.py   # rewrites this file from the stored summary; no network
```

## What was fetched

128 slices of `https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv` —
industries `113`, `1133`, `11331`, `113310` across 2017-Q1..2024-Q4
(8 years x 4 quarters). Every one answered 200 with a parsable CSV:
`not_found` and `unparseable` are 0 for all four industries, so no count below is short a quarter.

**Region margins were not fetched and need not be.** QCEW publishes no region level; Stage 0's
measured agglvl inventory for `113310` is 18 National / 48 MSA / 58 State / 78 County. A
Census-division total does not exist to fetch.

## The baseline this run re-derived

| | value |
|---|---|
| private `113310` state-quarter rows (states+DC, ex. PR) | 1572 |
| of those, `disclosure_code = 'N'` | 409 |
| matches the 2026-09-11 witness (1,572 / 409) | `true` |

409 x 3 = 1227 suppressed monthly cells — equal to the 1,227 that
`deterministic_bounds.parquet` reported `unbounded` on 2026-09-11 (a quoted reference).

## Parent industries, private ownership

Each parent is served at **its own digit-depth agglvl code**, not at `58`
(`constants.QCEW_STATE_AGGLVL`). Filtering on `58` would have returned zero parent rows and
"measured" a false absence.

| industry | agglvl | private state-quarters | disclosed | **disclosed where child is `N`** |
|---|---|---|---|---|
| `113` | 55 | 1588 | 1278 | **252** |
| `1133` | 56 | 1572 | 1163 | **0** |
| `11331` | 57 | 1572 | 1163 | **0** |

`1133` is disclosed on 1163 of 1572
state-quarters and `11331` on 1163 of
1572, and each on **zero** of the 409 where the child is
suppressed. That is the single-child chain behaving as it must: `1133 -> 11331 -> 113310` is 1:1 in
both vintages, so BLS suppresses the whole chain together. **Neither yields an exact
reconstruction.**

`113` is different, and it is the finding. Forestry and Logging also aggregates `1131` and `1132`,
so `113` stays disclosable where its grandchild does not — on
**252 of the 409** suppressed state-quarters.

## Ownership

`own_code 0` (Total Covered) **does not exist** at state x 6-digit for this industry: the observed
ownership set is `3`, `5`, and `own_code_0_rows` is
0. This is a *measured absence*, not an unfetched one — `fetched` is
`true` beside it. The local-government sibling (`own_code 3`) is disclosed
on 0 of the suppressed quarters, so the
subtraction route is closed from both ends.

## Identification tally

| outcome | suppressed state-quarters | months |
|---|---|---|
| `exact` | 0 | 0 |
| `upper_bound` | 252 | 756 |
| `none` | 157 | 471 |
| **identified at all** | **252** | **756** |

**61.6%** of the suppressed state-quarters carry a finite upper bound from a disclosed `113`
parent. None carries an exact reconstruction through a MEASURED margin — see *What this does not
measure*.

### Why `exact` is 0 by measurement, not by construction

`identification` maps a disclosed `113` to `UPPER_BOUND` by its ladder, so a reader may object that
the zero is an artefact. It is not. `disclosure_code == '-'` is a published **true zero**
(`ingest/qcew.py::_check_dash_rows_carry_no_establishments`), and a true-zero `113` would force
`113310` to exactly 0 — an exact case the ladder would understate as a bound. Derived from the
stored extracts: **3** of the 1278 disclosed `113`
private state-quarters carry `'-'`, and **0** of them falls on a quarter
where `113310` private is `N`. The renderer refuses to run if that ever becomes non-zero.

## Is the bound informative?

Unanswerable on a suppressed cell by definition, so this is measured where `113310` and `113` are
**both** published with a value, over all three monthly columns (3,069
month-observations):

| `113310 / 113` on disclosed pairs | |
|---|---|
| median | **0.916** |
| 5th percentile | 0.659 |
| 95th percentile | 1.000 |
| share at or above 0.5 | 97.8% |

**Not vacuous on the published distribution** — where both are published, `113310` is a median
92% of `113`. That describes DISCLOSED pairs. The bounded cells are suppressed ones,
a different population (small cells are the ones suppressed), so this is **not** the bound's
tightness on them, and `specs/stage5-parent-margin.md` R-PM-8 forbids quoting it as such. It
establishes only that nothing in the published data suggests `113` routinely dwarfs `113310` (the
renderer halts if that median falls below 0.5).

## How many bounded cells could reach MILP?

A parent row alone would give each bounded month the LP interval `[0, 113]`, so its width is the
`113` value itself. `_needs_milp` re-solves only where that width falls below
`use_milp_when_lp_interval_width_below` (25 in `config.yaml`). Of the **756** bounded month-values, **107**
are below it, touching **43** of the 252 bounded quarters. The rest become
finite but stay LP-only, so `D-093`'s MILP gap binds on that subset, not on all 756. (This
assumes the parent row is the only restriction added; another margin could narrow widths further.)

## What this does not measure

`113 - 1131 - 1132 = 1133`, and the chain below `1133` is 1:1 — so a quarter with `113`, `1131`
and `1132` all disclosed is an **exact** reconstruction of `113310`. `1131` and `1132` are outside
R-S5G-5's named scope and were not fetched. On the 252
quarters where `113` is disclosed, REQ-027's status is therefore **unknown**, not absent (`D-110`),
and `specs/stage5-parent-margin.md` R-PM-5 owns measuring it.
