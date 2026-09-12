# §9.3 parent-industry and ownership margins on D1 — measured

**Measured:** 2026-09-11T16:24:31+00:00 (R-S5G-5, plan 14 Task 2). **Derived from
`data/raw/audit/qcew_parent_margins/summary.json`, not retyped** — by `scripts/audit/render_parent_margins.py`, which is committed because the
summary it reads is gitignored.

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

409 x 3 = 1227 suppressed monthly cells, the
`unbounded` count in `deterministic_bounds.parquet`.

## Parent industries, private ownership

Each parent is served at **its own digit-depth agglvl code**, not at `58`
(`constants.QCEW_STATE_AGGLVL`). Filtering on `58` would have returned zero parent rows and
"measured" a false absence.

| industry | agglvl | private state-quarters | disclosed | **disclosed where child is `N`** |
|---|---|---|---|---|
| `113` | 55 | 1588 | 1278 | **252** |
| `1133` | 56 | 1572 | 1163 | **0** |
| `11331` | 57 | 1572 | 1163 | **0** |

`1133` and `11331` are disclosed on 1163 of
1572 state-quarters, and on **zero** of the
409 where the child is suppressed. That is the single-child chain
behaving as it must: `1133 -> 11331 -> 113310` is 1:1 in both vintages, so BLS suppresses the
whole chain together. **There is no exact reconstruction from a parent.**

`113` is different, and it is the finding. Forestry and Logging also aggregates `1131` and `1132`,
which mask `113310`, so `113` stays disclosable where its grandchild does not — on
**252 of the 409**
suppressed state-quarters.

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
parent. None carries an exact reconstruction.

### Why `exact` is 0 by measurement, not by construction

`identification` maps a disclosed `113` to `UPPER_BOUND` by its ladder, so a reader may object that
the zero is an artefact. It is not. `disclosure_code == '-'` is a published **true zero**
(`ingest/qcew.py::_check_dash_rows_carry_no_establishments`), and a true-zero `113` would force
`113310` to exactly 0 — an exact case the ladder would understate as a bound. Derived from the
stored extracts: **3** of the 1278 disclosed
`113` private state-quarters carry `'-'`, and **0** of them falls on a quarter where
`113310` private is `N`. With 0 intersection the ladder cannot be understating, so
`exact = 0` is the measured answer.

## How tight is the bound?

A finite upper bound that sits far above the truth is worth little; one that sits just above it is
most of an estimate. Unanswerable on a suppressed cell by definition, so measured on the
state-quarters where `113310` and `113` are **both** disclosed, over all three monthly columns
(3,069 month-observations):

| `113310 / 113` | |
|---|---|
| median | **0.916** |
| 5th percentile | 0.659 |
| 95th percentile | 1.000 |
| share at or above 0.5 | 97.8% |

**The bound is tight.** The median suppressed cell's upper bound would sit about
9% above its true value, against the `+inf` it carries today. This is
the number that makes the routing in `specs/stage5-parent-margin.md` worth a stage rather than a
footnote: `[0, 113]` with `113310` typically at 92% of `113` is a different
estimation problem from `[0, +inf)`. It is measured on DISCLOSED pairs and is therefore a
description of the published joint distribution, not a promise about the suppressed cells --
suppression is not random, and small cells are exactly the ones suppressed.

**Re-check this on any re-run.** If a revision ever puts a `'-'` `113` row on a suppressed
quarter, `identification` needs a true-zero rung above `UPPER_BOUND` before its tally can be
trusted.

## What this does not measure

`113 - 1131 - 1132 = 1133`, and the chain below `1133` is 1:1 — so a quarter with `113`, `1131`
and `1132` all disclosed is an **exact** reconstruction of `113310`. `1131` and `1132` are outside
R-S5G-5's named scope and were not fetched. This is a named, unmeasured path to a REQ-027 case,
and `specs/stage5-parent-margin.md` owns measuring it.
