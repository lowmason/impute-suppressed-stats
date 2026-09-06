# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# # httpx is required at run time even though this script makes no HTTP call of its own:
# # `import _common as c` imports httpx at module scope. Dropping it from this list
# # breaks `uv run --no-project`. Not a stale dependency -- do not "clean it up".
# ///
"""Build the 113310 private state/national monthly panel and measure the suppression share.

Reads nothing from the network: every input is an extract another audit script already
recorded (Task 2's slice CSVs, Task 3's fetched titles and derived `private_own_code`), so the
panel is reproducible from the artifacts on disk. The panel itself is registered through
`record_extract` under a `derived://` URL, which is why it re-hashes like any fetched file --
and with `http_status=None`, because nothing was fetched over HTTP to carry a status.

This script measures. It records no verdict on any SRC-QCEW finding: the geography and
suppression counts below state what the retained rows contain, and nothing about what they
imply for a national identity.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from itertools import pairwise
from typing import Any, NamedTuple

import _common as c
import polars as pl

SOURCE = "qcew_panel"

# STATES_DC_FIPS / STATE_AREAS / NATIONAL_AREA come from _common (Task 1) — shared, not
# re-declared, because audit scripts do not import one another except through summaries.

# The `*000` suffix is what makes an area_fips national or state-level rather than a county or
# an MSA; named once so the predicate string in `filter_predicates` cannot drift from the
# predicate that was actually applied.
AREA_SUFFIX = "000"
SUPPRESSION_CODE = "N"

# The panel key. `_conform` enforces it, because every share below divides by a count of
# these cells and a duplicate would inflate that denominator silently.
PANEL_KEY = ("area_fips", "year", "month")

# "This cell kept a published establishment count." fill_null before comparing: a null
# qtrly_estabs is otherwise dropped from a .mean() denominator instead of counting as
# "not > 0" (the same hazard as `suppressed`). Written once so the three readings of it
# -- the per-code tally, estabs_survival and the note -- cannot drift apart.
ESTABS_PRESENT = pl.col("qtrly_estabs").fill_null(0) > 0

# The panel contract Task 5 reads. Enforced on the frame before it is serialized (see
# `_conform`), so a renamed column or a narrowed integer fails here rather than downstream.
PANEL_SCHEMA: dict[str, pl.DataType] = {
    "area_fips": pl.String,
    "area_title": pl.String,
    "area_class": pl.String,
    "year": pl.Int32,
    "qtr": pl.Int8,
    "month": pl.Int8,
    "emplvl": pl.Int64,
    "qtrly_estabs": pl.Int64,
    "disclosure_code": pl.String,
    "suppressed": pl.Boolean,
}


def area_titles() -> dict[str, str]:
    path = next(
        e["path"]
        for e in c.load_summary("qcew_codes")["extracts"]
        if e["path"].endswith("titles/area_fips.csv")
    )
    df = pl.read_csv(path, infer_schema_length=0)
    return dict(zip(df[df.columns[0]].to_list(), df[df.columns[1]].to_list(), strict=True))


def slice_paths() -> list[str]:
    """Task 2 recorded 32 quarterly slice CSVs and, alongside them, a bulk ZIP it fetched to
    compare headers. Only the CSVs are panel input; the ZIP is a different file format and a
    different column vocabulary (`qtrly_estabs_count`, not `qtrly_estabs`)."""
    return [
        e["path"] for e in c.load_summary("qcew_routes")["extracts"] if e["path"].endswith(".csv")
    ]


def predicate_exprs(own_code: str) -> list[tuple[str, pl.Expr]]:
    """The filters this script applies, paired with the text recorded for each one.

    Global Constraints require every predicate to be recorded in the summary because the raw
    files were stored unfiltered. Pairing the text with the expression here is what keeps the
    recorded predicate and the applied predicate the same object.
    """
    return [
        (f"industry_code == '{c.INDUSTRY_CODE}'", pl.col("industry_code") == c.INDUSTRY_CODE),
        (
            f"own_code == '{own_code}' (qcew_codes.findings.private_own_code)",
            pl.col("own_code") == own_code,
        ),
        (
            f"area_fips.str.ends_with('{AREA_SUFFIX}')",
            pl.col("area_fips").str.ends_with(AREA_SUFFIX),
        ),
    ]


def apply_predicates(raw: pl.DataFrame, own_code: str) -> tuple[pl.DataFrame, list[str]]:
    """Filter in the listed order, annotating each predicate with what it retained."""
    df, before, recorded = raw, raw.height, []
    for label, expr in predicate_exprs(own_code):
        df = df.filter(expr)
        recorded.append(f"{label}; retained {df.height} of {before} rows")
        before = df.height
    return df, recorded


def _conform(long: pl.DataFrame) -> pl.DataFrame:
    """Project onto PANEL_SCHEMA — column order included — and refuse anything else.

    "Anything else" includes a repeated `PANEL_KEY`. Nothing upstream guarantees one row per
    (area_fips, year, month): the predicates filter on industry, ownership and the area suffix
    only, so uniqueness rests on the source's shape. A duplicated area-quarter would inflate
    the suppression share's denominator — a count of rows — while `absent_months_by_area`,
    which counts distinct months, went on reporting that area as complete, and every derived
    sentence in the summary would still read as self-consistent. That silent failure lands on
    the headline number, so it is refused here rather than reported.
    """
    panel = long.select(*PANEL_SCHEMA)
    if list(panel.schema.items()) != list(PANEL_SCHEMA.items()):
        raise RuntimeError(f"panel schema {dict(panel.schema)} != {PANEL_SCHEMA}")
    repeated = panel.group_by(PANEL_KEY).len().filter(pl.col("len") > 1).sort(PANEL_KEY)
    if repeated.height:
        raise RuntimeError(
            f"panel key {PANEL_KEY} is not unique: {repeated.height} repeated key(s), "
            f"first {repeated.head(3).to_dicts()}"
        )
    return panel


def build_long(own_code: str) -> tuple[pl.DataFrame, list[str]]:
    """The monthly frame before `_conform` projects it onto PANEL_SCHEMA.

    Kept separate because `emplvl_raw` — what the source published in the month columns,
    before INV-003 nulls it out on a suppressed row — exists only here, and
    `disclosure_code_values` has to measure it to report it.
    """
    raw = pl.concat([pl.read_csv(p, infer_schema_length=0) for p in slice_paths()], how="vertical")
    titles = area_titles()
    df, recorded = apply_predicates(raw, own_code)

    long = (
        df.unpivot(
            index=["area_fips", "year", "qtr", "disclosure_code", "qtrly_estabs"],
            on=["month1_emplvl", "month2_emplvl", "month3_emplvl"],
            variable_name="month_col",
            value_name="emplvl_raw",
        )
        .with_columns(
            year=pl.col("year").cast(pl.Int32),
            qtr=pl.col("qtr").cast(pl.Int8),
            month_in_qtr=pl.col("month_col").str.extract(r"month(\d)_emplvl").cast(pl.Int8),
            qtrly_estabs=pl.col("qtrly_estabs").cast(pl.Int64),
            # fill_null before comparing: `null == "N"` is null in polars, and a null
            # `suppressed` would be dropped from every .mean() denominator below.
            suppressed=pl.col("disclosure_code").fill_null("").str.strip_chars()
            == SUPPRESSION_CODE,
        )
        .with_columns(month=(pl.col("qtr") - 1) * 3 + pl.col("month_in_qtr"))
        .with_columns(
            # INV-003: a value paired with a suppression code is never a true zero.
            emplvl=pl.when(pl.col("suppressed"))
            .then(None)
            .otherwise(pl.col("emplvl_raw").cast(pl.Int64)),
            area_class=pl.when(pl.col("area_fips") == c.NATIONAL_AREA)
            .then(pl.lit("national"))
            .when(pl.col("area_fips").is_in(sorted(c.STATE_AREAS)))
            .then(pl.lit("states_dc"))
            .otherwise(pl.lit("other_state_level")),
            area_title=pl.col("area_fips").replace_strict(titles, default=""),
        )
        .sort("area_fips", "year", "month")
    )
    return long, recorded


class PanelBuild(NamedTuple):
    """The three frames one build produces, so nothing recomposes them independently.

    `long` is pre-`_conform` and is the only frame carrying `emplvl_raw`, which
    `disclosure_code_values` reads; `panel` is the conformed frame everything else reads;
    `predicates` is the retention record. Returning only `(panel, predicates)` would not have
    closed the seam, because `main` reads all three.
    """

    long: pl.DataFrame
    panel: pl.DataFrame
    predicates: list[str]


def build(own_code: str) -> PanelBuild:
    """The single `build_long` -> `_conform` composition site."""
    long, predicates = build_long(own_code)
    return PanelBuild(long=long, panel=_conform(long), predicates=predicates)


def build_panel(own_code: str) -> pl.DataFrame:
    """The conformed panel alone. Kept so the existing call sites need no change."""
    return build(own_code).panel


def month_index(year: int, month: int) -> int:
    """Months since year 0 — a single ordinal so adjacency survives a year boundary."""
    return year * 12 + month


def run_lengths(months: Sequence[int], flags: Sequence[bool]) -> list[int]:
    """Maximal runs of consecutive suppressed months, over `month_index` values.

    A run ends at an unsuppressed month and equally at an absent one: two suppressed spans
    either side of a month with no published row are two runs, because the panel says nothing
    about the months in between. Stage 4's §13.3 "long runs" regime is sized from this
    histogram, so a merged run would overstate it.
    """
    runs: list[int] = []
    current = 0
    previous: int | None = None
    for month, flag in zip(months, flags, strict=True):
        contiguous = previous is not None and month == previous + 1
        if current and not contiguous:
            runs.append(current)
            current = 0
        if flag:
            current += 1
        elif current:
            runs.append(current)
            current = 0
        previous = month
    if current:
        runs.append(current)
    return runs


def _state_runs(states: pl.DataFrame) -> tuple[dict[int, int], int]:
    """Run-length histogram over states_dc areas, plus the count of interior month gaps."""
    hist: dict[int, int] = {}
    gaps = 0
    ordered = states.sort("year", "month")
    for _key, group in ordered.group_by(["area_fips"], maintain_order=True):
        grp = group.sort("year", "month")
        months = [month_index(y, m) for y, m in zip(grp["year"], grp["month"], strict=True)]
        gaps += sum(1 for a, b in pairwise(months) if b != a + 1)
        for length in run_lengths(months, grp["suppressed"].to_list()):
            hist[length] = hist.get(length, 0) + 1
    return hist, gaps


def disclosure_code_values(long: pl.DataFrame) -> list[dict[str, Any]]:
    """What the published disclosure_code column actually carries on the retained rows.

    Takes the pre-`_conform` frame so `emplvl_raw` is still present: `emplvl_raw_nonzero_rows`
    counts what the source published in the month columns *before* INV-003 nulls it out, and
    `emplvl_published_nonzero_rows` counts what survives into the panel. Without the first of
    those, the note's claim about what a suppressed row publishes would be untestable — and a
    nonzero employment level published under a suppression code would surface here instead of
    disappearing into the null-out.

    §2.2 row 1 forbids encoding any numerical confidentiality threshold, so the suppression
    flag is the published code and nothing else. Enumerating every observed value — with what
    each one carries in the employment and establishment columns — is what makes the
    `== 'N'` predicate auditable instead of asserted.
    """
    return (
        long.group_by(pl.col("disclosure_code").fill_null("").str.strip_chars())
        .agg(
            panel_rows=pl.len(),
            states_dc_rows=(pl.col("area_class") == "states_dc").sum(),
            # Three cases, and the old chain collapsed two of them. An unparseable token casts
            # to null under strict=False; `fill_null(0)` BEFORE the comparison then made it
            # compare equal to a published zero, so the one case this counter exists to catch --
            # a value that does not parse on a suppressed row -- was the one case it reported as
            # absent. Filling True AFTER the comparison fixes that, but on its own it
            # over-corrects: a row that published NOTHING is also null and would be counted as
            # nonzero. The explicit `is_not_null()` keeps the three apart -- nothing published is
            # not counted, an unparseable token is, and a published 0 is not.
            emplvl_raw_nonzero_rows=(
                pl.col("emplvl_raw").is_not_null()
                & (pl.col("emplvl_raw").cast(pl.Int64, strict=False) != 0).fill_null(True)
            ).sum(),
            emplvl_published_rows=pl.col("emplvl").is_not_null().sum(),
            emplvl_published_nonzero_rows=(pl.col("emplvl") > 0).sum(),
            qtrly_estabs_positive_rows=ESTABS_PRESENT.sum(),
        )
        .sort("disclosure_code")
        .to_dicts()
    )


def estabs_survival(supp_rows: pl.DataFrame) -> float | None:
    """Fraction of suppressed cells whose `qtrly_estabs` is above zero, or None if there are
    none to measure.

    §2.2 row 2 says establishment counts may remain available when employment is suppressed,
    and Task 5's universe test depends on it, so it is measured rather than assumed. `None`
    rather than `0.0` on an empty frame for the same reason `suppression_share_overall` is:
    0.0 is the measurable result "no suppressed cell kept its establishment count", and a
    panel with nothing suppressed must not be reported as having produced it.
    """
    if not supp_rows.height:
        return None
    return float(supp_rows.select(ESTABS_PRESENT).to_series().mean())


def cell_coverage(states: pl.DataFrame, interior_month_gaps: int) -> dict[str, Any]:
    """How many states_dc monthly cells the shares are actually divided by.

    The shares below have a denominator of cells present in the panel, not of a full
    universe x window grid: an area with no published row for a month contributes to neither
    numerator nor denominator. This records the difference so the headline share is readable.

    `interior_month_gaps` is computed by `_state_runs`, in the same traversal that builds the
    run-length histogram, because it is the evidence that no run in that histogram spans an
    absence. It is recorded here, next to the rest of the coverage arithmetic, so a consumer
    reads it as a number rather than parsing it out of the note.
    """
    window_months = len(c.WINDOW_YEARS) * 12
    # Distinct months, not row count: an area's absent-month arithmetic must not depend on
    # `_conform`'s key check having run, even though it makes the two the same.
    present = dict(
        states.group_by("area_fips")
        .agg(pl.struct("year", "month").n_unique())
        .sort("area_fips")
        .iter_rows()
    )
    absent = {
        area: window_months - present.get(area, 0)
        for area in sorted(c.STATE_AREAS)
        if present.get(area, 0) < window_months
    }
    return {
        # The share's actual denominator, so a row count by construction.
        "cells_present": states.height,
        "grid_areas": len(c.STATE_AREAS),
        "grid_months": window_months,
        "grid_cells": len(c.STATE_AREAS) * window_months,
        "absent_months_by_area": absent,
        "areas_with_no_rows": sorted(a for a in c.STATE_AREAS if a not in present),
        "interior_month_gaps": interior_month_gaps,
    }


def titles_provenance(titles_available: dict[str, Any]) -> str:
    """What this audit fetched for the disclosure_code column's titles -- not what BLS
    publishes.

    `qcew_codes.TITLES` maps each dimension to a titles URL, and `qcew_codes.main` requests
    exactly the ones that are not `None`; the resulting map is persisted as
    `titles_available`. So a `None` there records that this audit sent no titles request for
    that column, which is a fact about this audit's requests. Whether BLS publishes such a file
    is a different claim, tested by no request in either script, and this sentence must not
    make it -- the earlier wording ("records the published titles file for this column as
    None") did, by reading a key name as a measurement across a task boundary.

    Still derived from the loaded value rather than typed: a future `qcew_codes` run that does
    fetch a titles file for this column makes the other branch true, and this sentence then
    describes that run instead of repeating this one's absence.
    """
    url = titles_available.get("disclosure_code")
    if url is None:
        return (
            "This audit fetched no titles file for this column: qcew_codes.findings."
            "titles_available carries null for disclosure_code, which records that "
            "qcew_codes sent no titles request for it -- not that no such file is published, "
            "which no request in either script tests. The code values below therefore come "
            "from the retained rows alone."
        )
    return (
        f"This audit fetched a titles file for this column: qcew_codes.findings."
        f"titles_available records {url!r}, and qcew_codes' own extract of it is what any "
        f"code-to-label reading of the values below should be checked against."
    )


def notes(
    *,
    panel: pl.DataFrame,
    states: pl.DataFrame,
    supp_rows: pl.DataFrame,
    codes: list[dict[str, Any]],
    coverage: dict[str, Any],
    others: list[dict[str, str]],
    titles_available: dict[str, Any],
) -> str:
    """Every sentence here is interpolated from this run's frames; a re-run against revised
    data restates it rather than repeating it."""
    by_class = dict(panel.group_by("area_class").len().sort("area_class").iter_rows())
    code_counts = ", ".join(
        f"{row['disclosure_code']!r} on {row['panel_rows']} monthly rows "
        f"({row['states_dc_rows']} states_dc, {row['qtrly_estabs_positive_rows']} with "
        f"qtrly_estabs > 0, {row['emplvl_raw_nonzero_rows']} with a nonzero employment level "
        f"in the source month columns, {row['emplvl_published_nonzero_rows']} with one "
        f"published into the panel)"
        for row in codes
    )
    other_desc = ", ".join(f"{row['area_fips']} ({row['area_title']})" for row in others) or "none"
    missing = coverage["areas_with_no_rows"]
    partial = {a: n for a, n in coverage["absent_months_by_area"].items() if a not in missing}
    return (
        f"Panel construction. {len(slice_paths())} recorded slice CSVs contribute the raw "
        f"frame; the predicates in filter_predicates are applied to it in the order listed "
        f"there, each one recording what it retained, and the surviving quarterly rows "
        f"unpivot to {panel.height} monthly rows "
        f"({', '.join(f'{n} {cls}' for cls, n in by_class.items())}). "
        f"Suppression flag. `suppressed` is true where the published disclosure_code strips "
        f"to {SUPPRESSION_CODE!r}, and false for every other value, including an empty one: "
        f"the flag is the published code alone, and no cell-count or concentration threshold "
        f"enters it (Global Constraints, §2.2 row 1). "
        f"{titles_provenance(titles_available)} Values observed on the retained rows, "
        f"with what each carries: {code_counts}. Employment on a suppressed row is written "
        f"null in the panel (INV-003), so of the two counts above, "
        f"emplvl_raw_nonzero_rows is taken before that null-out and "
        f"emplvl_published_nonzero_rows after it; the difference between those two per code "
        f"is measured here, not assumed from what a suppressed row is expected to publish. "
        f"Denominator. suppression_share_overall, _by_state and _by_month divide by the "
        f"{coverage['cells_present']} states_dc monthly cells present in the panel, not by "
        f"the {coverage['grid_cells']} cells of a {coverage['grid_areas']}-area x "
        f"{coverage['grid_months']}-month grid; state_month_cell_coverage decomposes the "
        f"difference. states_dc areas with no retained row in any quarter: {len(missing)} "
        f"({', '.join(missing) or 'none'}). states_dc areas with rows for part of the window "
        f"only: {len(partial)} "
        f"({'; '.join(f'{a}: {n} months absent' for a, n in partial.items()) or 'none'}). "
        f"A per-state share for any of those areas is over the months it publishes. "
        f"Run lengths. suppressed_run_lengths counts maximal runs of consecutive suppressed "
        f"months within one states_dc area, where a run ends at an unsuppressed month and "
        f"equally at an absent one. Counted across the states_dc areas over the "
        f"{coverage['grid_months']}-month window, the number of interior month gaps falling "
        f"inside an area's own span of published rows is "
        f"{coverage['interior_month_gaps']} (state_month_cell_coverage.interior_month_gaps). "
        f"Establishment survival. estabs_survive_suppression_share is measured over the "
        f"{supp_rows.height} suppressed states_dc monthly cells, of which "
        f"{int(supp_rows.select(ESTABS_PRESENT).to_series().sum())} report "
        f"qtrly_estabs > 0. "
        f"Geography. states_covered counts the distinct states_dc area codes present, "
        f"{states['area_fips'].n_unique()} of the {len(c.STATE_AREAS)} in _common.STATE_AREAS; "
        f"other_state_level_areas enumerates every non-national area ending "
        f"'{AREA_SUFFIX}' that is outside that set: {other_desc}. This script draws no "
        f"conclusion from either count about the composition of the "
        f"{c.NATIONAL_AREA} national total."
    )


def main() -> None:
    own_code = c.load_summary("qcew_codes")["findings"]["private_own_code"]
    long, panel, predicates = build(own_code)

    states = panel.filter(pl.col("area_class") == "states_dc")
    n_cells = states.height
    n_suppressed = int(states["suppressed"].sum())

    by_state = states.group_by("area_fips").agg(share=pl.col("suppressed").mean()).sort("area_fips")
    by_month = (
        states.with_columns(
            ym=pl.format("{}-{}", pl.col("year"), pl.col("month").cast(pl.Utf8).str.zfill(2))
        )
        .group_by("ym")
        .agg(share=pl.col("suppressed").mean())
        .sort("ym")
    )

    hist, interior_gaps = _state_runs(states)

    supp_rows = states.filter(pl.col("suppressed"))
    estabs_survive = estabs_survival(supp_rows)

    others = (
        panel.filter(pl.col("area_class") == "other_state_level")
        .select("area_fips", "area_title")
        .unique()
        .sort("area_fips")
        .to_dicts()
    )
    codes = disclosure_code_values(long)
    coverage = cell_coverage(states, interior_gaps)

    window_months = {(y, m) for y in c.WINDOW_YEARS for m in range(1, 13)}
    covered_months = set(panel.select("year", "month").unique().iter_rows())
    uncovered = ", ".join(f"{y}-{m:02d}" for y, m in sorted(window_months - covered_months))
    # Derived from the months the panel holds, not from its years: QCEW publishes quarter by
    # quarter, so a run whose last quarter is 2025q2 must not report a December end date.
    first_month, last_month = min(covered_months), max(covered_months)

    buf = io.BytesIO()
    panel.write_parquet(buf)
    # `http_status=None`, not `record_extract`'s 200 default: this parquet was never fetched
    # over HTTP, so there is no status to record. A status is a measurement a run made, not a
    # property of a route, and typing 200 here would put a fabricated measurement into the one
    # artifact a fresh clone keeps (`specs/findings/source-audit-extracts.csv`, where the field
    # renders empty for this row). `0` was rejected: `_common.probe` already spends it as the
    # "no response at all" sentinel, so a reader could not tell a derived file from a transport
    # failure. `_common.validate_summary` requires the key's presence, not its type, so `None`
    # validates and the exit gate carries it through as an empty manifest field.
    rec = c.record_extract(
        SOURCE, "derived://qcew_routes/slices", "panel.parquet", buf.getvalue(), http_status=None
    )

    span_start, span_end = (f"{y}-{m:02d}" for y, m in (first_month, last_month))
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": span_start,
            "published_end": span_end,
            "window_start": c.WINDOW_START,
            "window_end": c.WINDOW_END,
            "covered": f"{span_start}..{span_end}",
            "uncovered": uncovered,
        },
        access={
            "route": "derived from qcew_routes slice extracts",
            "status": "verified",
            "reason": None,
        },
        extracts=[rec],
        findings={
            "filter_predicates": predicates,
            "panel_rows": panel.height,
            "months_covered": states.select("year", "month").unique().height,
            "states_covered": states["area_fips"].n_unique(),
            "other_state_level_areas": others,
            "suppression_share_overall": n_suppressed / n_cells if n_cells else None,
            "suppression_share_by_state": dict(
                zip(by_state["area_fips"].to_list(), by_state["share"].to_list(), strict=True)
            ),
            "suppression_share_by_month": dict(
                zip(by_month["ym"].to_list(), by_month["share"].to_list(), strict=True)
            ),
            "suppressed_run_lengths": {str(k): v for k, v in sorted(hist.items())},
            "estabs_survive_suppression_share": estabs_survive,
            "disclosure_code_values": codes,
            "state_month_cell_coverage": coverage,
            "notes": notes(
                panel=panel,
                states=states,
                supp_rows=supp_rows,
                codes=codes,
                coverage=coverage,
                others=others,
                titles_available=c.load_summary("qcew_codes")["findings"]["titles_available"],
            ),
        },
    )
    print(
        f"panel rows={panel.height}; states={states['area_fips'].n_unique()}; "
        f"suppressed share={n_suppressed / n_cells if n_cells else 'n/a'}"
    )


if __name__ == "__main__":
    main()
