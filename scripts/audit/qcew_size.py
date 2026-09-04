# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-QSIZE-002: prove from file contents whether QCEW publishes state x 113310 x
establishment size simultaneously, and record what the by-size product does carry."""

from __future__ import annotations

import io
import re
import zipfile

import httpx
import polars as pl

import _common as c

SOURCE = "qcew_size"
SIZE_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip"
# STATES_DC_FIPS / STATE_AREAS come from _common (Task 1) — shared, not re-declared, because
# audit scripts do not import one another except through summaries.


ALL_SIZES_TITLE = re.compile(r"^all\b.*\bsizes?\b", re.IGNORECASE)


def all_sizes_code(titles: dict[str, str]) -> str:
    """The size_code standing for the all-sizes aggregate, DERIVED from the fetched
    size_code titles file rather than hardcoded.

    Task 9 states the general rule this follows: a code's meaning comes from the titles file
    the run fetched, never from memory. Hardcoding "0" here would have made this script assert
    a code-to-meaning mapping it never checked -- and the aggregate code is load-bearing,
    because it is the one value the simultaneity predicate must exclude. Raises unless exactly
    one title matches, so an ambiguous or renamed vocabulary fails loudly instead of silently
    counting the aggregate as a real size class."""
    hits = sorted(code for code, title in titles.items() if ALL_SIZES_TITLE.match(title or ""))
    if len(hits) != 1:
        raise RuntimeError(
            f"expected exactly one all-sizes title in the fetched size_code titles, got "
            f"{len(hits)}: {[(h, titles[h]) for h in hits]}"
        )
    return hits[0]


def has_simultaneous_state_industry_size(
    df: pl.DataFrame, *, industry: str, state_areas: set[str], all_sizes: str
) -> bool:
    """True iff a single row carries a state-level area, the target industry, and a real size
    class at once. `all_sizes` is the aggregate code -- it carries no size breakdown, so it
    never counts. Pass the code `all_sizes_code` derived from the fetched titles file; the
    caller supplies it rather than this function assuming a literal."""
    return df.filter(
        pl.col("area_fips").is_in(sorted(state_areas))
        & (pl.col("industry_code") == industry)
        & (pl.col("size_code") != all_sizes)
    ).height > 0


def area_pattern(areas: list[str]) -> str:
    national = {c.NATIONAL_AREA}
    kinds = set()
    for a in areas:
        if a in national:
            kinds.add("national")
        elif a in c.STATE_AREAS:
            kinds.add("state_level")
        else:
            kinds.add("sub_state")
    if len(kinds) == 1:
        return kinds.pop()
    return "mixed"


def read_zip(path: str) -> pl.DataFrame:
    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".csv"))
        return pl.read_csv(io.BytesIO(zf.read(member)), infer_schema_length=0)


def probe_other_quarters(client: httpx.Client, years: tuple[int, ...]) -> list[dict]:
    """Probe Q2-Q4 of every window year for a by-size file, so the coverage_span's "Q1-only"
    claim is measured this run rather than asserted from memory. The illustrative brief wrote
    that claim as a typed string with no request behind it -- the Global Constraints' rule on
    persisted prose says a factual sentence must be interpolated from data in scope during the
    run, and "no other quarter is published" is exactly the kind of claim a later BLS schedule
    change could falsify. A 404 across the board is what the by-size product's Q1-only design
    would produce; any 200 means it is not Q1-only and the note below must say so instead."""
    rows = []
    for year in years:
        for qtr in (2, 3, 4):
            url = f"https://data.bls.gov/cew/data/files/{year}/csv/{year}_q{qtr}_by_size.zip"
            status, nbytes = c.probe(client, url)
            rows.append({"year": year, "qtr": qtr, "http_status": status, "bytes": nbytes})
    return rows


def main() -> None:
    client = c.build_client()
    extracts, frames = [], []
    for year in c.WINDOW_YEARS:
        url = SIZE_URL.format(year=year)
        rec = c.download_extract(client, SOURCE, url, f"{year}_q1_by_size.zip")
        extracts.append(rec)
        frames.append(read_zip(rec.path).with_columns(pl.lit(year).alias("ref_year")))
    df = pl.concat(frames, how="vertical")

    quarter_probe = probe_other_quarters(client, c.WINDOW_YEARS)
    other_quarters_served = any(row["http_status"] == 200 for row in quarter_probe)

    # The titles file is loaded BEFORE the verdict because the verdict depends on it: the
    # aggregate size_code the predicate excludes is derived from it, not assumed.
    tpath = next(e["path"] for e in c.load_summary("qcew_codes")["extracts"]
                 if e["path"].endswith("titles/size_code.csv"))
    tdf = pl.read_csv(tpath, infer_schema_length=0)
    titles = dict(zip(tdf[tdf.columns[0]].to_list(), tdf[tdf.columns[1]].to_list(),
                      strict=True))
    all_sizes = all_sizes_code(titles)

    verdict = has_simultaneous_state_industry_size(
        df, industry=c.INDUSTRY_CODE, state_areas=c.STATE_AREAS, all_sizes=all_sizes)

    inventory = []
    for (agglvl,), grp in df.group_by(["agglvl_code"], maintain_order=True):
        inventory.append({
            "agglvl_code": agglvl,
            "row_count": grp.height,
            "has_113310": bool((grp["industry_code"] == c.INDUSTRY_CODE).any()),
            "area_pattern": area_pattern(grp["area_fips"].unique().to_list()),
            "size_codes": sorted(grp["size_code"].unique().to_list()),
        })
    inventory.sort(key=lambda r: r["agglvl_code"])

    logging_rows = df.filter(pl.col("industry_code") == c.INDUSTRY_CODE)
    finest = (
        "state x 113310 x establishment size IS published simultaneously"
        if verdict else
        "the finest simultaneous combination observed for 113310 is "
        f"{area_pattern(logging_rows['area_fips'].unique().to_list())} geography x 113310 x "
        f"size codes {sorted(logging_rows['size_code'].unique().to_list())}"
    )

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": f"{min(c.WINDOW_YEARS)}-Q1",
            "published_end": f"{max(c.WINDOW_YEARS)}-Q1",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": "first quarter of each window year only",
            "uncovered": (
                f"Q2-Q4 of every window year: probed ({len(quarter_probe)} requests) and none "
                "returned a by-size file, so the product is Q1-only for every year checked"
                if not other_quarters_served else
                "Q2-Q4 of every window year: NOT purely Q1-only -- at least one non-Q1 by-size "
                "file was found this run; see findings.quarter_probe for which year/quarter"
            ),
        },
        access={"route": SIZE_URL, "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "simultaneous_state_industry_size": verdict,
            "agglvl_inventory": inventory,
            "what_the_file_does_carry": finest,
            "all_sizes_code": {"code": all_sizes, "title": titles[all_sizes]},
            "size_codes_with_titles": [
                {"code": s, "title": titles.get(s)}
                for s in sorted(logging_rows["size_code"].unique().to_list())
            ],
            "years_checked": list(c.WINDOW_YEARS),
            "stage6_reroute_required": verdict,
            "quarter_probe": quarter_probe,
        },
    )
    print(f"SRC-QSIZE-002 simultaneous state x 113310 x size: {verdict}")
    print(finest)
    if verdict:
        print("!! Stage 6 must be re-routed to brainstorming: §2.2 row 3's premise no longer holds")


if __name__ == "__main__":
    main()
