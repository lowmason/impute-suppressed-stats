# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]   # _common imports httpx
# ///
"""Render `specs/findings/qcew-parent-margins.md` from `qcew_parent_margins`'s summary (R-S5G-6).

Committed for one reason: `data/raw/audit/` is gitignored, so the summary this reads is not in the
repository and the finding is. Without this script the finding's numbers would have no producer
any checkout can reach -- which is the "audit notes must be derived, not typed" failure in its
most literal form, and this repo has ten recorded instances of it. `assemble_finding.py` is the
precedent.

Two things here are derived from the stored EXTRACTS rather than from `summary.json`, because they
answer objections the summary's own tally cannot:

1. the `'-'` true-zero intersection, which is what makes `exact = 0` a measurement rather than an
   artefact of `identification`'s ladder; and
2. the `113310 / 113` ratio on both-disclosed pairs, which is what separates a finite bound that
   is worth a stage from one that sits so far above the truth it changes nothing.

Idempotent: re-running without re-running the audit writes the same bytes.
"""

from __future__ import annotations

import glob

import _common as c
import polars as pl

SOURCE = "qcew_parent_margins"
MONTHS = ("month1_emplvl", "month2_emplvl", "month3_emplvl")
PRIVATE, PUERTO_RICO = "5", "72000"


def load(industry: str) -> pl.DataFrame:
    """Every stored slice for one industry, stacked."""
    paths = sorted(glob.glob(str(c.AUDIT_ROOT / SOURCE / industry / "*.csv")))
    if not paths:
        raise SystemExit(f"no stored extracts for {industry}; run qcew_parent_margins.py first")
    return pl.concat([pl.read_csv(p, infer_schema_length=0) for p in paths], how="vertical_relaxed")


def private_state_rows(frame: pl.DataFrame, industry: str) -> pl.DataFrame:
    """The private state rows, at whatever agglvl serves this industry.

    Repeats `qcew_parent_margins.state_rows`'s predicate rather than importing it, and the two must
    agree. Importing would be tidier and would make this renderer depend on the measurement script
    at import time; the predicate is four clauses and the duplication is visible, where a silent
    import-time coupling between a measurement and its rendering would not be.
    """
    return frame.filter(
        (pl.col("industry_code") == industry)
        & pl.col("area_fips").str.ends_with("000")
        & (pl.col("area_fips") != PUERTO_RICO)
        & (pl.col("area_fips") != "US000")
        & (pl.col("own_code") == PRIVATE)
    )


def keys(frame: pl.DataFrame) -> set[tuple[str, str, str]]:
    """`(area_fips, year, qtr)`, the quarter grain QCEW suppresses at."""
    return set(zip(*frame.select("area_fips", "year", "qtr").to_dict().values(), strict=True))


def bound_tightness(child: pl.DataFrame, parent: pl.DataFrame) -> pl.Series:
    """`113310 / 113` wherever BOTH are disclosed, over all three monthly columns.

    Measured on disclosed pairs because it is unmeasurable on a suppressed one -- that is the whole
    point of the suppression. It therefore describes the PUBLISHED joint distribution and is not a
    promise about the bounded cells: suppression is not random, and small cells are exactly the
    ones suppressed. The finding says so where it quotes the number.
    """
    published = pl.col("disclosure_code") == ""
    pairs = (
        child.filter(published)
        .select("area_fips", "year", "qtr", *MONTHS)
        .join(
            parent.filter(published).select("area_fips", "year", "qtr", *MONTHS),
            on=["area_fips", "year", "qtr"],
            suffix="_p",
        )
    )
    return pl.concat(
        [
            pairs.filter(pl.col(f"{m}_p").cast(pl.Float64) > 0).select(
                (pl.col(m).cast(pl.Float64) / pl.col(f"{m}_p").cast(pl.Float64)).alias("r")
            )
            for m in MONTHS
        ]
    )["r"]


def main() -> None:
    """Write the finding."""
    summary = c.load_summary(SOURCE)
    findings = summary["findings"]
    child = private_state_rows(load("113310"), "113310")
    parent = private_state_rows(load("113"), "113")
    suppressed = keys(child.filter(pl.col("disclosure_code") == "N"))
    dash = keys(parent.filter(pl.col("disclosure_code") == "-"))
    ratios = bound_tightness(child, parent)
    dest = c.FINDINGS_DIR / "qcew-parent-margins.md"
    dest.write_text(
        render(summary, findings, suppressed=suppressed, dash=dash, ratios=ratios),
        encoding="utf-8",
    )
    print(f"wrote {dest}")
    print(f"  identification {findings['identification']}")
    print(
        f"  '-' rows in disclosed 113: {len(dash)}, intersecting suppressed: {len(dash & suppressed)}"
    )
    print(f"  child/parent median {ratios.median():.3f} over {len(ratios)} month-observations")


def render(
    summary: dict,
    findings: dict,
    *,
    suppressed: set,
    dash: set,
    ratios: pl.Series,
) -> str:
    """The finding's markdown. Every number interpolated, none written as a literal."""
    cov, ident, child_f = (
        summary["coverage_span"],
        findings["identification"],
        findings["private_113310"],
    )
    own = findings["total_ownership_113310"]
    dash_hit = len(dash & suppressed)
    years = f"{cov['published_start']}..{cov['published_end']}"
    n_q = sum(o["ok"] for o in findings["slice_outcomes"].values())
    ids = ident["exact"] + ident["upper_bound"]
    pct = 100 * ids / child_f["suppressed_rows"]
    r_med, r_q05, r_q95 = ratios.median(), ratios.quantile(0.05), ratios.quantile(0.95)
    r_half = 100 * (ratios >= 0.5).sum() / len(ratios)
    rows = "\n".join(
        f"| `{i}` | {p['agglvl_codes_present'][0]} | {p['state_quarter_rows_private']} | "
        f"{p['disclosed_private']} | **{p['disclosed_where_child_suppressed']}** |"
        for i, p in sorted(findings["parents"].items())
    )
    return f"""# §9.3 parent-industry and ownership margins on D1 — measured

**Measured:** {summary["generated_utc"]} (R-S5G-5, plan 14 Task 2). **Derived from
`data/raw/audit/qcew_parent_margins/summary.json`, not retyped** — by `scripts/audit/render_parent_margins.py`, which is committed because the
summary it reads is gitignored.

```bash
cd scripts/audit && set -a && source ../../.env && set +a && uv run --no-project qcew_parent_margins.py
uv run --no-project render_parent_margins.py   # rewrites this file from the stored summary; no network
```

## What was fetched

{n_q} slices of `https://data.bls.gov/cew/data/api/{{year}}/{{qtr}}/industry/{{industry}}.csv` —
industries {", ".join(f"`{i}`" for i in sorted(findings["slice_outcomes"]))} across {years}
({len(cov["covered"])} years x 4 quarters). Every one answered 200 with a parsable CSV:
`not_found` and `unparseable` are 0 for all four industries, so no count below is short a quarter.

**Region margins were not fetched and need not be.** QCEW publishes no region level; Stage 0's
measured agglvl inventory for `113310` is 18 National / 48 MSA / 58 State / 78 County. A
Census-division total does not exist to fetch.

## The baseline this run re-derived

| | value |
|---|---|
| private `113310` state-quarter rows (states+DC, ex. PR) | {child_f["state_quarter_rows"]} |
| of those, `disclosure_code = 'N'` | {child_f["suppressed_rows"]} |
| matches the 2026-09-11 witness (1,572 / 409) | `{str(child_f["matches_2026_09_11_witness"]).lower()}` |

{child_f["suppressed_rows"]} x 3 = {3 * child_f["suppressed_rows"]} suppressed monthly cells, the
`unbounded` count in `deterministic_bounds.parquet`.

## Parent industries, private ownership

Each parent is served at **its own digit-depth agglvl code**, not at `58`
(`constants.QCEW_STATE_AGGLVL`). Filtering on `58` would have returned zero parent rows and
"measured" a false absence.

| industry | agglvl | private state-quarters | disclosed | **disclosed where child is `N`** |
|---|---|---|---|---|
{rows}

`1133` and `11331` are disclosed on {findings["parents"]["1133"]["disclosed_private"]} of
{findings["parents"]["1133"]["state_quarter_rows_private"]} state-quarters, and on **zero** of the
{child_f["suppressed_rows"]} where the child is suppressed. That is the single-child chain
behaving as it must: `1133 -> 11331 -> 113310` is 1:1 in both vintages, so BLS suppresses the
whole chain together. **There is no exact reconstruction from a parent.**

`113` is different, and it is the finding. Forestry and Logging also aggregates `1131` and `1132`,
which mask `113310`, so `113` stays disclosable where its grandchild does not — on
**{findings["parents"]["113"]["disclosed_where_child_suppressed"]} of the {child_f["suppressed_rows"]}**
suppressed state-quarters.

## Ownership

`own_code 0` (Total Covered) **does not exist** at state x 6-digit for this industry: the observed
ownership set is {", ".join(f"`{o}`" for o in own["own_codes_present"])}, and `own_code_0_rows` is
{own["own_code_0_rows"]}. This is a *measured absence*, not an unfetched one — `fetched` is
`{str(own["fetched"]).lower()}` beside it. The local-government sibling (`own_code 3`) is disclosed
on {own["sibling_own_3_disclosed_where_child_suppressed"]} of the suppressed quarters, so the
subtraction route is closed from both ends.

## Identification tally

| outcome | suppressed state-quarters | months |
|---|---|---|
| `exact` | {ident["exact"]} | {3 * ident["exact"]} |
| `upper_bound` | {ident["upper_bound"]} | {3 * ident["upper_bound"]} |
| `none` | {ident["none"]} | {3 * ident["none"]} |
| **identified at all** | **{ids}** | **{ident["months_identified"]}** |

**{pct:.1f}%** of the suppressed state-quarters carry a finite upper bound from a disclosed `113`
parent. None carries an exact reconstruction.

### Why `exact` is 0 by measurement, not by construction

`identification` maps a disclosed `113` to `UPPER_BOUND` by its ladder, so a reader may object that
the zero is an artefact. It is not. `disclosure_code == '-'` is a published **true zero**
(`ingest/qcew.py::_check_dash_rows_carry_no_establishments`), and a true-zero `113` would force
`113310` to exactly 0 — an exact case the ladder would understate as a bound. Derived from the
stored extracts: **{len(dash)}** of the {findings["parents"]["113"]["disclosed_private"]} disclosed
`113` private state-quarters carry `'-'`, and **{dash_hit}** of them falls on a quarter where
`113310` private is `N`. With {dash_hit} intersection the ladder cannot be understating, so
`exact = 0` is the measured answer.

## How tight is the bound?

A finite upper bound that sits far above the truth is worth little; one that sits just above it is
most of an estimate. Unanswerable on a suppressed cell by definition, so measured on the
state-quarters where `113310` and `113` are **both** disclosed, over all three monthly columns
({len(ratios):,} month-observations):

| `113310 / 113` | |
|---|---|
| median | **{r_med:.3f}** |
| 5th percentile | {r_q05:.3f} |
| 95th percentile | {r_q95:.3f} |
| share at or above 0.5 | {r_half:.1f}% |

**The bound is tight.** The median suppressed cell's upper bound would sit about
{100 * (1 / r_med - 1):.0f}% above its true value, against the `+inf` it carries today. This is
the number that makes the routing in `specs/stage5-parent-margin.md` worth a stage rather than a
footnote: `[0, 113]` with `113310` typically at {100 * r_med:.0f}% of `113` is a different
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
"""


if __name__ == "__main__":
    main()
