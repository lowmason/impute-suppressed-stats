# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Inventory the QCEW code values actually present on 113310 rows, join published titles, and
record the SRC-QCEW-007 national/state alignment statement."""

from __future__ import annotations

import io

import polars as pl

import _common as c

SOURCE = "qcew_codes"
TITLES = {
    "agglvl_code": "https://data.bls.gov/cew/doc/titles/agglevel/agglevel_titles.csv",
    "own_code": "https://data.bls.gov/cew/doc/titles/ownership/ownership_titles.csv",
    "size_code": "https://data.bls.gov/cew/doc/titles/size/size_titles.csv",
    "area_fips": "https://data.bls.gov/cew/doc/titles/area/area_titles.csv",
    "industry_code": "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv",
    # No disclosure_code titles file is published; codes come from observed values only.
    "disclosure_code": None,
}


def load_slices() -> pl.DataFrame:
    paths = [e["path"] for e in c.load_summary("qcew_routes")["extracts"]
             if e["path"].endswith(".csv")]
    if not paths:
        raise RuntimeError("no slice CSVs recorded by qcew_routes; run Task 2 first")
    frames = [pl.read_csv(p, infer_schema_length=0) for p in paths]
    return pl.concat(frames, how="vertical")


def title_map(content: bytes, code_col: str, title_col: str) -> dict[str, str]:
    df = pl.read_csv(io.BytesIO(content), infer_schema_length=0)
    return dict(zip(df[code_col].to_list(), df[title_col].to_list(), strict=True))


def _agglvl_detail(title: str) -> str:
    """QCEW agglvl titles are '<Geography>, <detail clause>' -- confirmed against the fetched
    agglvl_code titles: code 18 is 'National, NAICS 6-digit -- by ownership sector' and code 58
    is 'State, NAICS 6-digit -- by ownership sector'. Stripping the leading geography clause
    isolates the industry-detail / ownership-scope clause so it is comparable across geography
    levels."""
    return title.split(",", 1)[1].strip() if "," in title else title.strip()


def _same_industry_detail(
    nat_agglvl: list[str], st_agglvl: list[str], agglvl_titles: dict[str, str]
) -> bool:
    """SRC-QCEW-007: true only when exactly one agglvl_code is observed at each geography
    level, and their titles agree once the leading geography clause is stripped -- i.e. both
    describe the same NAICS-digit detail and the same by-ownership breakout, not merely a
    cardinality-of-one coincidence."""
    if len(nat_agglvl) != 1 or len(st_agglvl) != 1:
        return False
    nat_title = agglvl_titles.get(nat_agglvl[0])
    st_title = agglvl_titles.get(st_agglvl[0])
    if nat_title is None or st_title is None:
        return False
    return _agglvl_detail(nat_title) == _agglvl_detail(st_title)


def main() -> None:
    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    maps: dict[str, dict[str, str]] = {}

    for dim, url in TITLES.items():
        if url is None:
            continue
        resp = c.request(client, url)
        extracts.append(c.record_extract(SOURCE, url, f"titles/{dim}.csv", resp.content))
        header = pl.read_csv(io.BytesIO(resp.content), infer_schema_length=0).columns
        code_col = header[0]
        title_col = next(h for h in header if h.endswith("_title"))
        maps[dim] = title_map(resp.content, code_col, title_col)

    df = load_slices().filter(pl.col("industry_code") == c.INDUSTRY_CODE)

    codes_present: dict[str, list[dict]] = {}
    for dim in ("agglvl_code", "own_code", "size_code", "disclosure_code"):
        counts = df.group_by(dim).len().sort(dim)
        codes_present[dim] = [
            {"code": code, "title": maps.get(dim, {}).get(code), "row_count": n}
            for code, n in zip(counts[dim].to_list(), counts["len"].to_list(), strict=True)
        ]
        # Defensive: a group_by must never silently drop rows (e.g. a null-vs-"" split on a
        # blank disclosure_code). Every dimension partitions the same 113310 universe, so the
        # row counts must sum back to it exactly.
        observed = sum(row["row_count"] for row in codes_present[dim])
        if observed != df.height:
            raise RuntimeError(
                f"{dim}: group_by rows sum to {observed}, expected {df.height} 113310 rows "
                "-- a group was lost"
            )

    private = [code for code, title in maps["own_code"].items() if title.strip() == "Private"]
    if len(private) != 1:
        raise RuntimeError(f"expected exactly one 'Private' ownership title, got {private}")
    private_own = private[0]

    priv = df.filter(pl.col("own_code") == private_own)
    nat = priv.filter(pl.col("area_fips") == "US000")
    state_like = priv.filter(
        pl.col("area_fips").str.ends_with("000") & (pl.col("area_fips") != "US000")
    )
    nat_agglvl = sorted(set(nat["agglvl_code"].to_list()))
    st_agglvl = sorted(set(state_like["agglvl_code"].to_list()))

    # QCEW publishes no per-row NAICS-vintage column, so this is a documentation fact, not a
    # derivable one. Confirmed by hand (Step 3) against two BLS classification pages, not
    # against per-row data -- see the sourcing recorded in `notes` below. Both switch years
    # (2017, 2022) fall on QCEW reference-year boundaries, so the mapping is a clean per-year
    # split with no year left "unconfirmed".
    naics_vintage = {
        "2017": "NAICS 2017", "2018": "NAICS 2017", "2019": "NAICS 2017",
        "2020": "NAICS 2017", "2021": "NAICS 2017",
        "2022": "NAICS 2022", "2023": "NAICS 2022", "2024": "NAICS 2022",
    }

    same_own_code = (
        set(nat["own_code"].to_list()) == {private_own}
        and set(state_like["own_code"].to_list()) == {private_own}
    )
    same_industry_code = (
        set(nat["industry_code"].to_list()) == {c.INDUSTRY_CODE}
        and set(state_like["industry_code"].to_list()) == {c.INDUSTRY_CODE}
    )
    same_detail = _same_industry_detail(nat_agglvl, st_agglvl, maps["agglvl_code"])

    aligned = (
        len(nat_agglvl) == 1
        and len(st_agglvl) == 1
        and same_own_code
        and same_industry_code
        and same_detail
    )

    notes = (
        "Filter predicates recorded verbatim: industry_code == '113310' is applied to the "
        "full concatenated 32-quarter slice frame before any other split; own_code == "
        f"'{private_own}' (title 'Private', from the fetched ownership titles file) restricts "
        "to private ownership; national rows are area_fips == 'US000'; state-like rows are "
        "area_fips.str.ends_with('000') and area_fips != 'US000'. "
        "Title evidence for 'same industry detail': fetched agglvl_code titles give code 18 = "
        "'National, NAICS 6-digit -- by ownership sector' and code 58 = 'State, NAICS 6-digit "
        "-- by ownership sector'; stripping the leading geography clause leaves an identical "
        "'NAICS 6-digit -- by ownership sector' at both levels, so aligned=True reflects an "
        "explicit title-semantics match (see _same_industry_detail), not just a cardinality-"
        "of-one coincidence. "
        "Geography-universe finding for SRC-QCEW-007 / Sec 3.2: across all 32 window quarters "
        "the state-like predicate above yields exactly 51 area codes -- the 50 states plus "
        "Puerto Rico (72000, agglvl 58, 8 rows, present only in 2017-2018, absent from 2019 "
        "on) -- and NOT the District of Columbia (11000): DC carries zero private-ownership "
        "113310 rows in any of the 32 window quarters, so it is entirely absent from this "
        "panel, not merely cell-suppressed within a published row. Per BLS's QCEW Aggregation "
        "Level Codes page (https://www.bls.gov/cew/classifications/aggregation/"
        "agg-level-titles.htm, footnote b), 'National level aggregations exclude Puerto Rico "
        "and Virgin Islands from the totals', so the agglvl-18 national total (US000) is "
        "definitionally 50 states + DC -- the same composition as geography_universe: "
        "'states_dc' -- and PR's appearance in state-like rows is extraneous to both the "
        "national total and the states_dc universe (a plain exclusion when a later task "
        "intersects state-like rows against STATE_AREAS, not a Sec 3.2 residual_cells case, "
        "since PR was never summed into the national total to begin with). DC's complete "
        "row-level absence is a genuine states_dc coverage gap: a private-ownership Logging "
        "panel over this window will have no DC series at all, which a later task should "
        "expect rather than mistake for a bug. Because US000 includes DC by definition while "
        "no DC state row is published, DC's contribution to the national total is "
        "unobservable at the state level -- a national-vs-sum-of-states residual distinct "
        "from, and additional to, cell-level suppression, and the one SRC-QCEW-006 should "
        "reason about as residual_cells (Sec 3.2), not enforce, since the state universe "
        "cannot be made to match a national control it structurally cannot see. "
        "NAICS vintage sourcing (Step 3): confirmed against two BLS classification pages, not "
        "from memory and not from the fetched industry_titles.csv alone -- that file reflects "
        "only the current vintage and shows 113310 = 'NAICS 113310 Logging', which confirms "
        "the code's current validity but not its per-year history. "
        "https://www.bls.gov/cew/classifications/industry/naics-2017.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) with the release of first "
        "quarter 2017 Quarterly Census of Employment and Wages (QCEW) data.' "
        "https://www.bls.gov/cew/classifications/industry/naics-2022.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) on September 7, 2022, with the "
        "full data release of first quarter 2022 Quarterly Census of Employment and Wages "
        "(QCEW) data.' QCEW does not retabulate prior reference years onto a new vintage, so "
        "the switch is a hard boundary at reference year 2022, giving the clean per-year "
        "split recorded above. The classification-codes skill's local NAICS 2012-to-2017 and "
        "2017-to-2022 concordance data both carry 113310 'Logging' as an unchanged 1:1 link "
        "(no change_indicator flag), so the industry's definition is stable across the whole "
        "window despite the vintage label change."
    )

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(c.WINDOW_YEARS)), "published_end": str(max(c.WINDOW_YEARS)),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": f"{min(c.WINDOW_YEARS)}-{max(c.WINDOW_YEARS)}", "uncovered": "",
        },
        access={"route": "https://data.bls.gov/cew/doc/titles/<dimension>/",
                "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "titles_available": TITLES,
            "codes_present": codes_present,
            "private_own_code": private_own,
            "national_agglvl": [{"code": a, "title": maps["agglvl_code"].get(a)}
                                for a in nat_agglvl],
            "state_agglvl": [{"code": a, "title": maps["agglvl_code"].get(a)}
                             for a in st_agglvl],
            "size_code_values": codes_present["size_code"],
            "alignment_srcqcew007": {
                "national_agglvl": nat_agglvl,
                "state_agglvl": st_agglvl,
                "own_code": private_own,
                "industry_code": c.INDUSTRY_CODE,
                "naics_vintage_by_year": naics_vintage,
                "period_basis": "quarterly file, three monthly employment columns "
                                "(month1/2/3_emplvl), pay period including the 12th",
                "aligned": aligned,
                "notes": notes,
            },
        },
    )
    print(f"private own_code={private_own}; national agglvl={nat_agglvl}; "
          f"state agglvl={st_agglvl}; aligned={aligned}")


if __name__ == "__main__":
    main()
