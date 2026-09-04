# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-OTH-003: determine, per state, the finest CES/SAE industry level at which a statewide
all-employees series covering the D1 window is published for Logging."""

from __future__ import annotations

import io

import polars as pl

import _common as c

SOURCE = "ces"
BASE = "https://download.bls.gov/pub/time.series/sm/"
FILES = ("sm.industry", "sm.series", "sm.state", "sm.data_type", "sm.area")


def sole_code(df: pl.DataFrame, code_col: str, text_col: str, pattern: str, what: str) -> str:
    """Derive a code from its published title. Global Constraints forbid hardcoding a code
    that the fetched metadata can supply — the same rule that governs QCEW's own_code."""
    hits = df.filter(pl.col(text_col).str.contains(pattern))
    if hits.height != 1:
        raise RuntimeError(
            f"expected exactly one {what} row matching {pattern!r}, got "
            f"{hits.select(code_col, text_col).to_dicts()}")
    return hits[code_col][0]


def read_tsv(content: bytes) -> pl.DataFrame:
    """BLS flat files pad both headers and values with spaces — verified on the live
    sm.series file this run fetched: series_id is fixed-width, space-padded on both the header
    and every data row. `truncate_ragged_lines` is defensive: none of the five files this run
    fetched actually has a ragged row (every row in each carries the same field count as its
    header), but a parse that assumed that would stay true is exactly the kind of claim a
    future BLS layout change could falsify silently."""
    df = pl.read_csv(io.BytesIO(content), separator="\t", infer_schema_length=0,
                     truncate_ragged_lines=True)
    # Rename first, then strip values off the RENAMED frame — reusing the pre-rename
    # `df.columns` here looks up padded names that no longer exist.
    df = df.rename({col: col.strip() for col in df.columns})
    return df.with_columns(pl.col(pl.Utf8).str.strip_chars())


def embedded_naics(industry_code: str) -> str:
    return industry_code[2:8].rstrip("0")


def level_of(industry_code: str) -> str:
    naics = embedded_naics(industry_code)
    # Zero-padding makes 11331 and 113310 indistinguishable after rstrip("0") — both come out
    # "11331" — but both denote Logging at its finest published level, so catch them first.
    # That collapse is licensed by D6's claim that 113310 is the only six-digit industry under
    # 1133, verified for this task directly against the classification-codes skill's
    # naics_2017.csv and naics_2022.csv (also true in naics_2012.csv): each carries exactly one
    # level-6 row under 1133 -> 11331 -> 113310. In the sm.industry file this script actually
    # fetches, CES/SAE never reaches this branch at all — the one Logging code it publishes,
    # 10113300, embeds only the 4-digit "1133" (see logging_industry_codes in the summary this
    # run writes) — but the branch stays as a defensive rule for a finer code BLS could add.
    if naics.startswith("1133") and len(naics) > 4:
        return "113310"
    if naics == "1133":
        return "1133"
    if naics == "113":
        return "113"
    if naics == "":
        return "supersector"
    return "other"


FINEST = {"113310": 0, "1133": 1, "113": 2, "supersector": 3, "other": 4, "none": 5}

# Loose net for finding every candidate; sole_code (above) narrows it to exactly one supersector
# code with an anchored title match. Kept separate from that anchor so the codes it excludes are
# still visible to excluded_broader_codes.
LOGGING_NAME_PATTERN = r"(?i)logging"


def qualifying_series(
    series: pl.DataFrame, codes: set[str], all_employees: str, statewide_area: str
) -> pl.DataFrame:
    """Rows of sm.series for the given industry codes, restricted to the statewide
    all-employees series overlapping the D1 window. Used for both the target candidate codes
    and the excluded broader codes, so the near-miss check can never define "qualifying"
    differently than the main query does."""
    return series.filter(
        pl.col("industry_code").is_in(sorted(codes))
        & (pl.col("data_type_code") == all_employees)
        & (pl.col("area_code") == statewide_area)
        & (pl.col("begin_year").cast(pl.Int32) <= max(c.WINDOW_YEARS))
        & (pl.col("end_year").cast(pl.Int32) >= min(c.WINDOW_YEARS))
    )


def excluded_broader_codes(
    logging_named_rows: list[dict], candidate_codes: set[str]
) -> list[dict]:
    """Every logging-named industry code this run's precise selector did not pick as a
    candidate — i.e. every code whose title happens to mention "logging" but which is neither
    embedded-NAICS-113-prefixed nor exactly titled 'Mining and Logging'. An unanchored
    substring match on the industry title (the brief's illustrative filter) would have folded
    these into the same 'supersector' level as the true target; kept visible here instead of
    silently disappearing."""
    return sorted(
        (row for row in logging_named_rows if row["industry_code"] not in candidate_codes),
        key=lambda r: r["industry_code"],
    )


def near_miss_states(
    excluded_series_rows: list[dict], level_by_state: dict[str, str]
) -> list[dict]:
    """States/areas whose only D1-window-overlapping statewide all-employees series among all
    logging-named codes sits at an excluded, broader code — exactly the states a looser,
    unanchored title match would have promoted from 'none' to 'supersector'. `level_by_state`
    is already computed against the precise candidate set, so every state named here already
    shows 'none' there; this function only explains why, from the excluded codes' own series."""
    return sorted(
        (
            {"state_code": row["state_code"], "industry_code": row["industry_code"],
             "series_id": row["series_id"]}
            for row in excluded_series_rows
            if level_by_state.get(row["state_code"]) == "none"
        ),
        key=lambda r: r["state_code"],
    )


def broader_code_note(excluded: list[dict], near_miss: list[dict]) -> str:
    """Computed sentence for `findings.notes`, stating what the precise title match excluded
    and, where relevant, which sm.state codes that kept out of a coarser classification — so a
    future run against a renamed or retired code describes itself instead of repeating this
    run's 'Mining, Logging and Construction' finding.

    "sm.state codes", not "States", in the composed sentence: the codes come from the fetched
    sm.state file, whose universe is wider than D1's `states_dc` — it also carries 00 (All
    States), 72 (Puerto Rico), 78 (Virgin Islands) and 99 (All MSAs), as `main`'s
    `denominator_note` records a few hundred characters earlier in the same `notes` string.
    Calling all of them states contradicted that sentence and promoted a territory to
    statehood in a tracked deliverable. This function is handed no name map, so the codes are
    rendered bare rather than with their fetched titles; `non_state_codes` in the same summary
    is where a reader resolves the non-state ones. The level a looser match would have assigned
    is derived from `level_of` on each excluded code, never typed as 'supersector' — a future
    excluded code that embeds e.g. NAICS 1131 would resolve to 'other', not 'supersector', and
    this sentence must say so instead of repeating today's wording."""
    if not excluded:
        return (
            "No SAE industry code mentioning 'logging' in its title fell outside the precise "
            "candidate selection this run — the anchored 'Mining and Logging' supersector "
            "match and the embedded-NAICS-113 match together account for every such code."
        )
    codes = "; ".join(f"{r['industry_code']} ({r['industry_name']!r})" for r in excluded)
    if not near_miss:
        return (
            "Excluded from the target industry codes because their titles merely mention "
            f"'logging' without being embedded-NAICS-113-prefixed or exactly titled 'Mining and "
            f"Logging': {codes}. No state's only D1-window-overlapping statewide all-employees "
            "series among the logging-named codes sits at one of these, so no state's level "
            "would change under a looser, unanchored title match."
        )
    states = ", ".join(sorted({r["state_code"] for r in near_miss}))
    levels = sorted({level_of(r["industry_code"]) for r in near_miss})
    level_phrase = levels[0] if len(levels) == 1 else " or ".join(levels)
    return (
        "Excluded from the target industry codes because their titles merely mention "
        f"'logging' without being embedded-NAICS-113-prefixed or exactly titled 'Mining and "
        f"Logging': {codes}. sm.state codes {states} publish a D1-window-overlapping statewide "
        "all-employees series only at one of these excluded codes — an unanchored substring "
        f"match on 'logging' would have promoted them from 'none' to {level_phrase!r}, which "
        "is not what the fetched sm.industry file actually supports for them."
    )


def _month_grain(year: str, period: str) -> str:
    """"2017", "M01" -> "2017-01" — the same "YYYY-MM" shape as c.WINDOW_START/c.WINDOW_END, so
    the two compare lexicographically as chronologically. SAE periods observed on the live
    sm.series file are all "M01".."M12" (two digits after the "M"); a differently-shaped period
    would produce a string that still sorts sanely against "YYYY-MM" as long as it starts with
    two digits, and would look visibly wrong in `window_coverage_note`'s output otherwise."""
    return f"{year}-{period[1:]}"


def window_coverage_note(series: pl.DataFrame) -> tuple[bool, str]:
    """Whether every D1-window-overlapping qualifying series actually spans the *entire* D1
    window (2017-01 through 2024-12) at MONTH grain — reading begin_period/end_period
    (sm.series columns 11 and 13), not just begin_year/end_year. `qualifying_series` selects on
    year-level overlap only; a series with begin_year=2017, begin_period='M06' would pass that
    filter while not actually covering January 2017. This is what actually backs the persisted
    `coverage_span.covered` claim — a year-grain check here would itself be an unverified claim
    about how much it proves, wearing the same 'verified' framing as the parts that really are."""
    if series.height == 0:
        return False, "no qualifying series exist to check window coverage against"
    rows = series.select("series_id", "begin_year", "begin_period", "end_year",
                         "end_period").to_dicts()
    for row in rows:
        row["start_month"] = _month_grain(row["begin_year"], row["begin_period"])
        row["end_month"] = _month_grain(row["end_year"], row["end_period"])
    latest_start = max(row["start_month"] for row in rows)
    earliest_end = min(row["end_month"] for row in rows)
    fully_covered = latest_start <= c.WINDOW_START and earliest_end >= c.WINDOW_END
    if fully_covered:
        return True, (
            f"every one of the {len(rows)} qualifying series begins at or before "
            f"{c.WINDOW_START} (latest start observed, at month grain via begin_year/"
            f"begin_period: {latest_start}) and ends at or after {c.WINDOW_END} (earliest end "
            f"observed, via end_year/end_period: {earliest_end}), so the full D1 window "
            f"{c.WINDOW_START}-{c.WINDOW_END} is covered wherever a qualifying series exists, "
            "verified at month grain, not merely at the year-level overlap qualifying_series "
            "filters on"
        )
    names = ", ".join(sorted(
        row["series_id"] for row in rows
        if row["start_month"] > c.WINDOW_START or row["end_month"] < c.WINDOW_END
    ))
    return False, (
        f"at least one qualifying series only partially overlaps the D1 window "
        f"{c.WINDOW_START}-{c.WINDOW_END} at month grain (begin_year/begin_period, end_year/"
        f"end_period), even though it passed qualifying_series' year-level overlap filter: "
        f"{names}"
    )


def select_candidates(industry: pl.DataFrame, supersector: str) -> pl.DataFrame:
    """The precise candidate selector this task's finding rests on: every SAE industry code
    whose embedded NAICS begins '113', plus the one code equal to the anchored Mining-and-
    Logging supersector title match. Extracted out of `main()` so the defect this task found
    and fixed — an unanchored substring match on the industry title silently admitting the
    broader '15000000 Mining, Logging and Construction' code alongside the true target,
    '10000000 Mining and Logging' — has a regression test that runs without a live fetch."""
    return industry.with_columns(
        embedded=pl.col("industry_code").map_elements(embedded_naics, return_dtype=pl.Utf8),
        level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8),
    ).filter(
        pl.col("embedded").str.starts_with("113") | (pl.col("industry_code") == supersector)
    )


def states_dc_level_tally(
    level_by_state: dict[str, str], states_dc_fips: tuple[str, ...]
) -> dict[str, int]:
    """The six-way tally restricted to D1's own states_dc universe. Raises loudly if a
    states_dc code is missing from `level_by_state` (i.e. absent from the fetched sm.state
    file this run) instead of silently dropping it out of every bucket: `.get(st) == lvl`
    would return None for a missing code and match no branch, undercounting without a trace
    while `denominator_note` kept asserting the full states_dc count."""
    missing = sorted(set(states_dc_fips) - set(level_by_state))
    if missing:
        raise RuntimeError(
            f"states_dc code(s) {missing} are absent from level_by_state (i.e. from the "
            "fetched sm.state file this run) — refusing to silently under-count them out of "
            "states_dc_tally"
        )
    tally = {lvl: sum(1 for st in states_dc_fips if level_by_state[st] == lvl)
             for lvl in ("113310", "1133", "113", "supersector", "other", "none")}
    assert sum(tally.values()) == len(states_dc_fips), (
        f"states_dc_tally {tally} sums to {sum(tally.values())}, not "
        f"len(states_dc_fips)={len(states_dc_fips)}"
    )
    return tally


def granularity_note(candidate_rows: list[dict]) -> str:
    """Distinguishes, for `findings.notes`, why `states_with_113310` reads 0 — a Stage 7 reader
    could otherwise take the weaker reading ("no state happens to publish there") when the
    stronger one holds ("no such code exists to publish at all"). Computed entirely from
    `candidate_rows` (the same rows written to `logging_industry_codes`), including which
    specific code(s) sit below the supersector — never a typed code literal, so a future run
    where CES/SAE adds or renumbers a code describes what it actually finds."""
    levels_present = {r["level"] for r in candidate_rows}
    if "113310" in levels_present:
        return (
            "The fetched sm.industry file does define an SAE industry code at the 113310 "
            "(NAICS 6-digit) level for Logging, so a states_with_113310 count of 0 would mean "
            "no state's D1-window-overlapping statewide all-employees series happens to be "
            "published there, not that the code is absent."
        )
    below_supersector = sorted(
        (r for r in candidate_rows if r["level"] != "supersector"),
        key=lambda r: r["industry_code"],
    )
    codes = "; ".join(f"{r['industry_code']} ({r['level']})" for r in below_supersector)
    return (
        "The fetched sm.industry file defines no SAE industry code at the NAICS 5- or 6-digit "
        "depth for Logging at all — the Logging-related code(s) it defines below the "
        f"supersector, this run: {codes or '(none)'} (see logging_industry_codes). "
        "states_with_113310 is 0 because CES/SAE itself stops short of 113310 for every state, "
        "not because some state declines to publish at a level that exists."
    )


def main() -> None:
    client = c.build_client()
    extracts, frames = [], {}
    for name in FILES:
        resp = c.request(client, BASE + name)
        extracts.append(c.record_extract(SOURCE, BASE + name, name, resp.content))
        frames[name] = read_tsv(resp.content)

    # Anchored on the full published title: a looser "^all employees" also matches the
    # 3-month-average-change series.
    all_employees = sole_code(frames["sm.data_type"], "data_type_code", "data_type_text",
                              r"(?i)^all employees, in thousands$", "sm.data_type")
    statewide_area = sole_code(frames["sm.area"], "area_code", "area_name",
                               r"(?i)^statewide$", "sm.area")
    # Same anchored discipline for the industry title. A bare substring match on "logging"
    # also matches "15000000 Mining, Logging and Construction" — a real, broader CES
    # supersector, verified present in the live sm.industry/sm.series files fetched this run —
    # which is not the Mining-and-Logging supersector D6 and this task mean.
    supersector = sole_code(frames["sm.industry"], "industry_code", "industry_name",
                            r"(?i)^mining and logging$", "sm.industry")

    industry = frames["sm.industry"]
    logging_named = industry.filter(pl.col("industry_name").str.contains(LOGGING_NAME_PATTERN))

    candidates = select_candidates(industry, supersector)
    candidate_codes = set(candidates["industry_code"].to_list())

    excluded = excluded_broader_codes(logging_named.to_dicts(), candidate_codes)
    excluded_codes = {row["industry_code"] for row in excluded}

    series = qualifying_series(
        frames["sm.series"], candidate_codes, all_employees, statewide_area
    ).with_columns(level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8))

    by_state: dict[str, list[dict]] = {}
    for row in series.iter_rows(named=True):
        by_state.setdefault(row["state_code"], []).append({
            "series_id": row["series_id"], "industry_code": row["industry_code"],
            "level": row["level"], "begin_year": int(row["begin_year"]),
            "end_year": int(row["end_year"]),
        })

    all_states = sorted(frames["sm.state"]["state_code"].to_list())
    level_by_state = {
        st: min((s["level"] for s in by_state.get(st, [])), key=lambda x: FINEST[x],
                default="none")
        for st in all_states
    }
    tally = {lvl: sum(1 for v in level_by_state.values() if v == lvl)
             for lvl in ("113310", "1133", "113", "supersector", "other", "none")}

    excluded_series_rows = qualifying_series(
        frames["sm.series"], excluded_codes, all_employees, statewide_area
    ).to_dicts() if excluded_codes else []
    near_miss = near_miss_states(excluded_series_rows, level_by_state)

    # D1 Appendix A's own geography universe (50 states + DC, 51 codes) is a strict subset of
    # sm.state's 55 codes (it also carries "00" All States, "72" Puerto Rico, "78" Virgin
    # Islands, "99" All Metropolitan Statistical Areas — none of them a D1 state). Both the
    # code list and the tally below are computed from the fetched sm.state file and
    # c.STATES_DC_FIPS, never typed, so a future change to either denominator shows up here.
    non_state_codes = sorted(set(all_states) - set(c.STATES_DC_FIPS))
    state_names = dict(zip(frames["sm.state"]["state_code"].to_list(),
                           frames["sm.state"]["state_name"].to_list(), strict=True))
    states_dc_tally = states_dc_level_tally(level_by_state, c.STATES_DC_FIPS)

    states_dc_summary = ", ".join(f"{lvl}: {n}" for lvl, n in states_dc_tally.items())
    denominator_note = (
        f"The six states_with_* counts below sum to {len(all_states)}, the number of codes in "
        "the fetched sm.state file, not 51 — sm.state also carries "
        + "; ".join(f"{code} ({state_names.get(code)!r})" for code in non_state_codes)
        + f", none of which is a D1 'states_dc' jurisdiction. Restricted to D1's own "
        f"geography_universe ('states_dc', the {len(c.STATES_DC_FIPS)} codes in "
        f"c.STATES_DC_FIPS, also recorded in the states_dc_tally finding): {states_dc_summary}."
    )

    fully_covered, coverage_note = window_coverage_note(series)
    candidate_rows = candidates.select(
        "industry_code", "industry_name", "embedded", "level"
    ).rename({"embedded": "embedded_naics"}).to_dicts()

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(series["begin_year"].cast(pl.Int32).min() or ""),
            "published_end": str(series["end_year"].cast(pl.Int32).max() or ""),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": (
                f"{c.WINDOW_START}-{c.WINDOW_END} for states with a qualifying series — "
                f"verified at month grain, not assumed, from every qualifying series' own "
                f"begin_year/begin_period and end_year/end_period: {coverage_note}"
            ) if fully_covered else (
                f"partial only — {coverage_note}; do not read "
                f"'{c.WINDOW_START}-{c.WINDOW_END} for states with a qualifying series' as "
                "true without checking this run's coverage_note again"
            ),
            "uncovered": f"{tally['none']} sm.state code(s) publish no Logging-related statewide "
                         f"all-employees series overlapping the window, of which "
                         f"{states_dc_tally['none']} are D1 'states_dc' jurisdictions (see "
                         "states_dc_tally and non_state_codes for the rest of the denominator)",
        },
        access={"route": BASE + "<file>", "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "logging_industry_codes": candidate_rows,
            "publication_level_by_state": level_by_state,
            "series_by_state": by_state,
            "states_with_113310": tally["113310"],
            "states_with_1133": tally["1133"],
            "states_with_113_only": tally["113"],
            "states_with_supersector_only": tally["supersector"],
            "states_with_other": tally["other"],
            "states_with_none": tally["none"],
            "derived_codes": {"all_employees_data_type": all_employees,
                              "statewide_area": statewide_area},
            "excluded_broader_codes": excluded,
            "near_miss_states": near_miss,
            "states_dc_tally": states_dc_tally,
            "non_state_codes": [{"code": code, "name": state_names.get(code)}
                                for code in non_state_codes],
            "notes": " ".join([
                denominator_note, broader_code_note(excluded, near_miss),
                granularity_note(candidate_rows),
            ]),
        },
    )
    print("CES publication level tally:", tally)
    print("derived codes — data_type:", all_employees, "| area:", statewide_area,
          "| supersector:", supersector)


if __name__ == "__main__":
    main()
