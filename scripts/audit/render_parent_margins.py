# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]   # _common imports httpx
# ///
"""Render `specs/findings/qcew-parent-margins.md` from `qcew_parent_margins`'s summary (R-S5G-6).

Committed for one reason: `data/raw/audit/` is gitignored, so the summary this reads is not in the
repository and the finding is. Without this script the finding's numbers would have no producer
any checkout can reach -- the "audit notes must be derived, not typed" failure in its most literal
form. `assemble_finding.py` is the precedent.

Three disciplines, each answering a way a rendered finding can lie:

1. **It renders ONE measurement or nothing.** It reads exactly the extracts `summary.json` lists and
   refuses any whose bytes no longer hash to what the summary recorded. `_common.record_extract`
   rewrites a slice in place, so a partial re-fetch leaves two vintages side by side that a glob
   would stack silently. The finding pins a digest over what was read.
2. **Its conclusions are guarded, not just its numbers.** Sentences such as "neither yields an exact
   reconstruction" are fixed prose. `summary_premises` and `extract_premises` state each as a
   condition on the data, and `main` halts rather than render a finding whose tables contradict its
   text. The witness pair and Stage 0's agglvl inventory are QUOTED references, not measurements
   of this run, and the finding says so.
3. **Two things come from the extracts rather than the summary**, because they answer objections the
   summary's tally cannot: the `'-'` true-zero intersection (which makes `exact = 0` measured rather
   than an artefact of `identification`'s ladder), and the widths a parent bound would give (which
   says how many bounded cells could reach §9.6's MILP threshold at all).

Idempotent: re-running without re-running the audit writes the same bytes.
"""

from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import _common as c
import polars as pl

SOURCE = "qcew_parent_margins"
MONTHS = ("month1_emplvl", "month2_emplvl", "month3_emplvl")
PRIVATE, PUERTO_RICO = "5", "72000"
REPO_ROOT = Path(__file__).resolve().parents[2]
MILP_KEY = "use_milp_when_lp_interval_width_below"
# What "nothing in the published data suggests 113 routinely dwarfs 113310" is taken to mean: a
# median disclosed-pair ratio at or above one half. It encodes a SENTENCE in `render`, not a finding;
# change the sentence and this together.
RATIO_FLOOR = 0.5


def load_extracts(summary: dict) -> tuple[dict[str, pl.DataFrame], str, int]:
    """Exactly the extracts the summary lists, each checked against its recorded sha256.

    NOT a glob, for the reason in the module docstring. Each path is REBUILT under this checkout's
    `data/raw/audit/<source>/` from the part the summary recorded below that directory, so a clone at
    another root reads its own bytes rather than failing on, or silently reading, the absolute path
    the audit ran at. A missing file raises FileNotFoundError and a changed one halts; either way no
    finding is written from bytes the summary did not measure. Returns the frames by industry, a
    digest over the sorted `(sha256, relative path)` pairs, and the count.
    """
    frames: dict[str, list[pl.DataFrame]] = {}
    pairs: list[str] = []
    root = c.AUDIT_ROOT / SOURCE
    for rec in summary["extracts"]:
        parts = Path(rec["path"]).parts
        if SOURCE not in parts:
            raise SystemExit(f"{rec['path']} is not under a {SOURCE}/ directory; not this audit's")
        rel = Path(*parts[len(parts) - parts[::-1].index(SOURCE) :])
        data = (root / rel).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != rec["sha256"]:
            raise SystemExit(f"{root / rel} no longer hashes to the summary's {rec['sha256']}")
        pairs.append(f"{digest}  {rel.as_posix()}")
        frames.setdefault(rel.parts[0], []).append(
            pl.read_csv(io.BytesIO(data), infer_schema_length=0)
        )
    manifest = "\n".join(sorted(pairs)) + "\n"
    stacked = {i: pl.concat(f, how="vertical_relaxed") for i, f in frames.items()}
    return stacked, hashlib.sha256(manifest.encode()).hexdigest(), len(pairs)


def private_state_rows(frame: pl.DataFrame, industry: str) -> pl.DataFrame:
    """The private state rows, at whatever agglvl serves this industry.

    Repeats `qcew_parent_margins.state_rows`'s predicate rather than importing it, and the two must
    agree -- `tests/audit/test_render_parent_margins.py` pins that they do. Importing would make this
    renderer depend on the measurement script at import time.
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
    """`113310 / 113` wherever BOTH are published with a value, over all three monthly columns.

    Measured on disclosed pairs because it is unmeasurable on a suppressed one. It therefore
    describes the PUBLISHED joint distribution and is NOT the bound's tightness on the bounded
    cells: those are suppressed cells, a different population, and small cells are exactly the ones
    suppressed. `specs/stage5-parent-margin.md` R-PM-8 forbids reading it otherwise.
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


def bound_widths(parent: pl.DataFrame, suppressed: set[tuple[str, str, str]]) -> pl.DataFrame:
    """The monthly `113` values on suppressed quarters where `113` is disclosed, one row per quarter.

    Each value IS the LP width a parent row would give that month's cell -- `[0, 113]` -- on the
    assumption that the parent row is the only restriction added: nonnegativity supplies the lower
    endpoint, and no other margin touches a state cell today. `_needs_milp` compares that width with
    `use_milp_when_lp_interval_width_below`, so this is what sizes `D-093`'s reachable subset.
    """
    on = ["area_fips", "year", "qtr"]
    wanted = pl.DataFrame(sorted(suppressed), schema=on, orient="row")
    return (
        parent.filter(pl.col("disclosure_code") != "N")
        .join(wanted, on=on)
        .select(*on, *[pl.col(m).cast(pl.Float64) for m in MONTHS])
    )


def milp_threshold() -> float:
    """§9.6's MILP width trigger, read from `config.yaml` rather than typed here."""
    text = (REPO_ROOT / "config.yaml").read_text(encoding="utf-8")
    found = re.search(rf"^\s*{MILP_KEY}:\s*([0-9.]+)\s*$", text, re.MULTILINE)
    if not found:
        raise SystemExit(f"{MILP_KEY} not found in config.yaml")
    return float(found.group(1))


def summary_premises(findings: dict, *, expected_slices: int) -> list[str]:
    """The template's conclusions the SUMMARY alone decides, as conditions; the broken ones.

    Checked BEFORE any extract is indexed, so a parent the route never served halts here by name
    rather than as a KeyError further down. Nothing here is a threshold on the data -- each line is a
    sentence in `render`.
    """
    broken: list[str] = []
    for industry, got in findings["slice_outcomes"].items():
        if got["ok"] != expected_slices:
            broken.append(f"'every slice answered 200 with a parsable CSV' is false for {industry}")
    parents = findings["parents"]
    for industry in ("113", "1133", "11331"):
        parent = parents.get(industry, {})
        if not parent.get("fetched"):
            broken.append(f"the parent table assumes {industry} was fetched; it was not")
            continue
        codes = parent.get("agglvl_codes_present", [])
        if len(codes) != 1 or "58" in codes:
            broken.append(
                f"'each parent has its own agglvl, not 58' is false for {industry}: {codes}"
            )
    for industry in ("1133", "11331"):
        if parents.get(industry, {}).get("disclosed_where_child_suppressed"):
            broken.append(
                f"'neither yields an exact reconstruction' is false: {industry} is disclosed"
            )
    if not parents.get("113", {}).get("disclosed_where_child_suppressed"):
        broken.append("'113 stays disclosable where its grandchild does not' is false")
    own = findings["total_ownership_113310"]
    if own["own_code_0_rows"]:
        broken.append("'own_code 0 does not exist at state x 6-digit' is false")
    if own["sibling_own_3_disclosed_where_child_suppressed"]:
        broken.append("'the subtraction route is closed from both ends' is false")
    if findings["identification"]["exact"]:
        broken.append("'none carries an exact reconstruction' is false")
    return broken


def extract_premises(*, dash_hit: int, median_ratio: float) -> list[str]:
    """The template's conclusions only the EXTRACTS decide, as conditions; the broken ones."""
    broken: list[str] = []
    if dash_hit:
        broken.append(
            "a '-' 113 falls on a suppressed quarter: `identification` needs a true-zero rung"
        )
    if median_ratio < RATIO_FLOOR:
        broken.append(f"'113 does not routinely dwarf 113310' is false: median {median_ratio:.3f}")
    return broken


def _halt(broken: list[str]) -> None:
    if broken:
        raise SystemExit(
            "the finding's prose no longer matches the data; rewrite render() first:\n- "
            + "\n- ".join(broken)
        )


def main() -> None:
    """Write the finding, or halt with the sentences the data no longer supports."""
    summary = c.load_summary(SOURCE)
    findings = summary["findings"]
    _halt(summary_premises(findings, expected_slices=len(summary["coverage_span"]["covered"]) * 4))
    frames, digest, n_extracts = load_extracts(summary)
    for needed in ("113310", "113"):
        if needed not in frames:
            raise SystemExit(f"the summary lists no verified extracts for {needed}")
    child = private_state_rows(frames["113310"], "113310")
    parent = private_state_rows(frames["113"], "113")
    suppressed = keys(child.filter(pl.col("disclosure_code") == "N"))
    dash = keys(parent.filter(pl.col("disclosure_code") == "-"))
    ratios = bound_tightness(child, parent)
    _halt(extract_premises(dash_hit=len(dash & suppressed), median_ratio=ratios.median()))
    dest = c.FINDINGS_DIR / "qcew-parent-margins.md"
    dest.write_text(
        render(
            summary,
            findings,
            suppressed=suppressed,
            dash=dash,
            ratios=ratios,
            widths=bound_widths(parent, suppressed),
            threshold=milp_threshold(),
            digest=digest,
            n_extracts=n_extracts,
        ),
        encoding="utf-8",
    )
    print(f"wrote {dest}")


def render(
    summary: dict,
    findings: dict,
    *,
    suppressed: set,
    dash: set,
    ratios: pl.Series,
    widths: pl.DataFrame,
    threshold: float,
    digest: str,
    n_extracts: int,
) -> str:
    """The finding's markdown.

    Every MEASURED number is interpolated; the 2026-09-11 witness pair (1,572 / 409) and Stage 0's
    agglvl inventory are quoted references, and the text labels them so. Every data-dependent
    conclusion is guarded by `summary_premises` or `extract_premises` before this runs.
    """
    cov, ident = summary["coverage_span"], findings["identification"]
    child_f, own, parents = (
        findings["private_113310"],
        findings["total_ownership_113310"],
        findings["parents"],
    )
    years = f"{cov['published_start']}..{cov['published_end']}"
    n_q = sum(o["ok"] for o in findings["slice_outcomes"].values())
    ids = ident["exact"] + ident["upper_bound"]
    pct = 100 * ids / child_f["suppressed_rows"]
    r_med, r_q05, r_q95 = ratios.median(), ratios.quantile(0.05), ratios.quantile(0.95)
    r_half = 100 * (ratios >= 0.5).sum() / len(ratios)
    month_values = widths.unpivot(index=["area_fips", "year", "qtr"], on=list(MONTHS))["value"]
    n_values = len(month_values)
    n_under = int((month_values < threshold).sum())
    q_under = widths.filter(pl.any_horizontal([pl.col(m) < threshold for m in MONTHS])).height
    table = "\n".join(
        f"| `{i}` | {p['agglvl_codes_present'][0]} | {p['state_quarter_rows_private']} | "
        f"{p['disclosed_private']} | **{p['disclosed_where_child_suppressed']}** |"
        for i, p in sorted(parents.items())
    )
    p1133, p11331 = parents["1133"], parents["11331"]
    n_sup = child_f["suppressed_rows"]
    return f"""# §9.3 parent-industry and ownership margins on D1 — measured

**Measured:** {summary["generated_utc"]} (R-S5G-5, plan 14 Task 2). **Derived from
`data/raw/audit/qcew_parent_margins/summary.json`, not retyped** — by
`scripts/audit/render_parent_margins.py`, which is committed because the summary it reads is
gitignored, and which refuses to render if a conclusion its `summary_premises` or `extract_premises`
guards stops matching the data. The witness pair and Stage 0's agglvl inventory below are quoted
references, not measurements of this run.

**Extracts read:** {n_extracts}, each verified against the sha256 the summary recorded, pinned
together by digest `{digest}` over their sorted `(sha256, path)` pairs.
`_common.record_extract` rewrites a slice in place, so **compare against this digest, or copy the
directory aside, before re-running the audit.**

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
| of those, `disclosure_code = 'N'` | {n_sup} |
| matches the 2026-09-11 witness (1,572 / 409) | `{str(child_f["matches_2026_09_11_witness"]).lower()}` |

{n_sup} x 3 = {3 * n_sup} suppressed monthly cells — the count `deterministic_bounds.parquet`
reported `unbounded` on 2026-09-11.

## Parent industries, private ownership

Each parent is served at **its own digit-depth agglvl code**, not at `58`
(`constants.QCEW_STATE_AGGLVL`). Filtering on `58` would have returned zero parent rows and
"measured" a false absence.

| industry | agglvl | private state-quarters | disclosed | **disclosed where child is `N`** |
|---|---|---|---|---|
{table}

`1133` is disclosed on {p1133["disclosed_private"]} of {p1133["state_quarter_rows_private"]}
state-quarters and `11331` on {p11331["disclosed_private"]} of
{p11331["state_quarter_rows_private"]}, and each on **zero** of the {n_sup} where the child is
suppressed. That is the single-child chain behaving as it must: `1133 -> 11331 -> 113310` is 1:1 in
both vintages, so BLS suppresses the whole chain together. **Neither yields an exact
reconstruction.**

`113` is different, and it is the finding. Forestry and Logging also aggregates `1131` and `1132`,
so `113` stays disclosable where its grandchild does not — on
**{parents["113"]["disclosed_where_child_suppressed"]} of the {n_sup}** suppressed state-quarters.

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
parent. None carries an exact reconstruction through a MEASURED margin — see *What this does not
measure*.

### Why `exact` is 0 by measurement, not by construction

`identification` maps a disclosed `113` to `UPPER_BOUND` by its ladder, so a reader may object that
the zero is an artefact. It is not. `disclosure_code == '-'` is a published **true zero**
(`ingest/qcew.py::_check_dash_rows_carry_no_establishments`), and a true-zero `113` would force
`113310` to exactly 0 — an exact case the ladder would understate as a bound. Derived from the
stored extracts: **{len(dash)}** of the {parents["113"]["disclosed_private"]} disclosed `113`
private state-quarters carry `'-'`, and **{len(dash & suppressed)}** of them falls on a quarter
where `113310` private is `N`. The renderer refuses to run if that ever becomes non-zero.

## Is the bound informative?

Unanswerable on a suppressed cell by definition, so this is measured where `113310` and `113` are
**both** published with a value, over all three monthly columns ({len(ratios):,}
month-observations):

| `113310 / 113` on disclosed pairs | |
|---|---|
| median | **{r_med:.3f}** |
| 5th percentile | {r_q05:.3f} |
| 95th percentile | {r_q95:.3f} |
| share at or above 0.5 | {r_half:.1f}% |

**Not vacuous on the published distribution** — where both are published, `113310` is a median
{100 * r_med:.0f}% of `113`. That describes DISCLOSED pairs. The bounded cells are suppressed ones,
a different population (small cells are the ones suppressed), so this is **not** the bound's
tightness on them, and `specs/stage5-parent-margin.md` R-PM-8 forbids quoting it as such. It
establishes only that nothing in the published data suggests `113` routinely dwarfs `113310` (the
renderer halts if that median falls below {RATIO_FLOOR:g}).

## How many bounded cells could reach MILP?

A parent row alone would give each bounded month the LP interval `[0, 113]`, so its width is the
`113` value itself. `_needs_milp` re-solves only where that width falls below
`{MILP_KEY}` ({threshold:g} in `config.yaml`). Of the **{n_values}** bounded month-values, **{n_under}**
are below it, touching **{q_under}** of the {ident["upper_bound"]} bounded quarters. The rest become
finite but stay LP-only, so `D-093`'s MILP gap binds on that subset, not on all {n_values}. (This
assumes the parent row is the only restriction added; another margin could narrow widths further.)

## What this does not measure

`113 - 1131 - 1132 = 1133`, and the chain below `1133` is 1:1 — so a quarter with `113`, `1131`
and `1132` all disclosed is an **exact** reconstruction of `113310`. `1131` and `1132` are outside
R-S5G-5's named scope and were not fetched. On the {parents["113"]["disclosed_where_child_suppressed"]}
quarters where `113` is disclosed, REQ-027's status is therefore **unknown**, not absent (`D-110`),
and `specs/stage5-parent-margin.md` R-PM-5 owns measuring it.
"""


if __name__ == "__main__":
    main()
