# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Measure whether any §9.3 parent-industry or ownership margin identifies a suppressed private
113310 state cell on D1 (R-S5G-5)."""

from __future__ import annotations

import io
from collections.abc import Mapping

import _common as c
import httpx
import polars as pl

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


SOURCE = "qcew_parent_margins"
SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
INDUSTRIES = ("113310", "113", "1133", "11331")
YEARS = range(2017, 2025)
QUARTERS = (1, 2, 3, 4)
PRIVATE, LOCAL_GOVERNMENT, TOTAL_COVERED = "5", "3", "0"
PUERTO_RICO = "72000"
REQUIRED_COLUMNS = frozenset(
    {"area_fips", "own_code", "industry_code", "agglvl_code", "disclosure_code"}
)
# The 2026-09-11 witness this run re-derives rather than assumes. A DATED PAIR, not a threshold:
# a BLS revision moves it and that is not this script's failure, so a mismatch is RECORDED in
# `matches_2026_09_11_witness` and never raised. Refusing here would make the script break on a
# revision it is supposed to measure.
WITNESS_STATE_QUARTER_ROWS, WITNESS_SUPPRESSED_ROWS = 1572, 409


def state_rows(frame: pl.DataFrame, industry: str) -> pl.DataFrame:
    """The state rows for one industry-quarter, at whatever aggregation level serves them.

    The agglvl code is DISCOVERED, not asserted. `constants.QCEW_STATE_AGGLVL` is `58` -- "State,
    NAICS 6-digit -- by ownership sector" -- which is the level for `113310` and is the WRONG level
    for `113`, `1133` and `11331`, each of which is served at its own digit-depth code (measured
    2026-09-11 on 2019q1: `55`, `56` and `57` respectively). Filtering on the industry and the area
    shape instead reaches all four without a table of codes this script would have to keep true.
    §5.4's instruction not to hard-code a route property applies.
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

    `disclosure_code != "N"` admits both `''` and `'-'`, the other two codes
    `constants.QCEW_DISCLOSURE_CODES` measures on this industry. `'-'` is a published TRUE ZERO
    (`ingest/qcew.py::_check_dash_rows_carry_no_establishments` halts if one carries
    establishments), so a `'-'` parent is the most informative disclosure there is: it forces the
    child to zero. Treating it as suppressed would discard an identification.
    """
    published = rows.filter((pl.col("own_code") == own_code) & (pl.col("disclosure_code") != "N"))
    return set(zip(*published.select("area_fips", "year", "qtr").to_dict().values(), strict=True))


def fetch_slice(client: httpx.Client, url: str) -> bytes | None:
    """The slice's bytes, or `None` when this route does not serve it.

    A 404 is ANSWERED, not raised. `_common.request` calls `raise_for_status` and
    `_is_retryable_status` fails fast on every 4xx but 429, so the plain call kills the whole
    128-request walk on the first unserved quarter and saves nothing -- and an industry this route
    does not serve is a RESULT for R-S5G-5, not a crash. Every other status keeps `_common`'s
    behaviour: a 5xx backs off and retries, and an unexpected 4xx is still a finding that halts.
    """
    try:
        return c.request(client, url).content
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None
        raise


def parse_slice(url: str, body: bytes) -> pl.DataFrame | None:
    """The slice as a frame, or `None` when a 200 carried something that is not this CSV.

    CLASSIFY ON CONTENT, NOT STATUS. These endpoints answer 200 with an error body, so
    `raise_for_status` inside `_common.request` cannot be the check; a body missing the columns
    this script reads is a failure at 200. Returned rather than raised for the same reason
    `fetch_slice` swallows a 404: `main` decides, once it can see whether the whole industry
    answered this way (a measured absence) or only one quarter did (an anomaly that halts).
    """
    frame = pl.read_csv(io.BytesIO(body), infer_schema_length=0)
    return None if REQUIRED_COLUMNS - set(frame.columns) else frame


def main() -> None:
    """Fetch the four industries across D1 and count who identifies whom."""
    frames: dict[str, list[pl.DataFrame]] = {industry: [] for industry in INDUSTRIES}
    outcomes = {i: {"ok": 0, "not_found": 0, "unparseable": 0} for i in INDUSTRIES}
    extracts: list[c.ExtractRecord] = []
    with c.build_client() as client:
        for industry in INDUSTRIES:
            for year in YEARS:
                for qtr in QUARTERS:
                    url = SLICE_URL.format(year=year, qtr=qtr, industry=industry)
                    body = fetch_slice(client, url)
                    if body is None:
                        outcomes[industry]["not_found"] += 1
                        continue
                    frame = parse_slice(url, body)
                    if frame is None:
                        outcomes[industry]["unparseable"] += 1
                        continue
                    outcomes[industry]["ok"] += 1
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

    # A UNIFORM absence is a measurement and is recorded; a PARTIAL one is not. An industry served
    # for some of D1 and not the rest under-counts its disclosures by exactly the quarters that
    # went missing, and nothing downstream can see the shortfall -- so it halts here rather than
    # reporting a smaller identification set than the route actually supports.
    expected = len(YEARS) * len(QUARTERS)
    partial = {i: o for i, o in outcomes.items() if 0 < o["ok"] < expected}
    if partial:
        raise SystemExit(f"partial fetch, counts would be wrong: {partial}")
    if outcomes["113310"]["ok"] != expected:
        raise SystemExit(f"113310 is the denominator and must be complete: {outcomes['113310']}")

    stacked = {i: pl.concat(f, how="vertical_relaxed") for i, f in frames.items() if f}
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

    parents: dict[str, dict[str, object]] = {}
    disclosed: dict[str, set[tuple[str, str, str]]] = {}
    for industry in ("113", "1133", "11331"):
        if industry not in stacked:
            # A MEASURED ABSENCE is a result. `fetched: false` beside the outcome counts is what
            # distinguishes "this route serves no such industry" from "we did not look".
            parents[industry] = {"fetched": False, "outcomes": outcomes[industry]}
            disclosed[industry] = set()
            continue
        rows = state_rows(stacked[industry], industry)
        disclosed[industry] = disclosed_keys(rows, PRIVATE)
        parents[industry] = {
            "fetched": True,
            "agglvl_codes_present": sorted(set(rows["agglvl_code"].to_list())),
            "own_codes_present": sorted(set(rows["own_code"].to_list())),
            "state_quarter_rows_private": rows.filter(pl.col("own_code") == PRIVATE).height,
            "disclosed_private": len(disclosed[industry]),
            "disclosed_where_child_suppressed": len(disclosed[industry] & suppressed),
        }

    total_own = disclosed_keys(child, TOTAL_COVERED)
    sibling_own = disclosed_keys(child, LOCAL_GOVERNMENT)

    tally = {EXACT: 0, UPPER_BOUND: 0, NONE: 0}
    for key in suppressed:
        tally[
            identification(
                {
                    "parent_113_disclosed": key in disclosed["113"],
                    "parent_1133_disclosed": key in disclosed["1133"],
                    "parent_11331_disclosed": key in disclosed["11331"],
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
            "slice_outcomes": outcomes,
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
                "disclosed_where_child_suppressed": len(total_own & suppressed),
                "sibling_own_3_disclosed_where_child_suppressed": len(sibling_own & suppressed),
            },
            "identification": {
                **tally,
                "months_identified": 3 * (tally[EXACT] + tally[UPPER_BOUND]),
            },
        },
    )


if __name__ == "__main__":
    main()
