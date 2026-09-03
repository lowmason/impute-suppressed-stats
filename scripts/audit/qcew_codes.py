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
    df = pl.concat(frames, how="vertical")
    # Cheap coverage guard: Task 2's bulk route never persists an extracted .csv member (only
    # the .zip), so if a future Task 2 re-run finds the slice route no longer serving the full
    # D1 window, this function would otherwise silently hand back an incomplete panel. Cast
    # both sides to str explicitly rather than trusting today's infer_schema_length=0 dtype, so
    # a future polars behavior change surfaces as a failed guard, not a silently-empty set diff.
    years_present = {str(y) for y in df["year"].unique().to_list()}
    years_wanted = {str(y) for y in c.WINDOW_YEARS}
    missing = sorted(years_wanted - years_present)
    if missing:
        raise RuntimeError(
            f"loaded slice CSVs are missing window years {missing}; Task 2's slice route no "
            "longer serves the full c.WINDOW_YEARS panel -- re-run Task 2, or extend "
            "load_slices() to also load its recorded bulk-route .csv extracts"
        )
    return df


def title_map(content: bytes, code_col: str, title_col: str) -> dict[str, str]:
    df = pl.read_csv(io.BytesIO(content), infer_schema_length=0)
    return dict(zip(df[code_col].to_list(), df[title_col].to_list(), strict=True))


def _agglvl_detail(title: str) -> str:
    """QCEW agglvl titles carry the shape '<Geography>, <detail clause>'. Splitting on the
    first comma isolates the industry-detail / ownership-scope clause so it is comparable
    across geography levels. This docstring deliberately names no code and quotes no title:
    which agglvl codes are observed, and what their fetched titles say, is computed each run
    and recorded in the `national_agglvl` / `state_agglvl` findings and in `notes` -- a typed
    example here would be a second, unchecked copy of that, free to go stale."""
    return title.split(",", 1)[1].strip() if "," in title else title.strip()


def _same_industry_detail(
    nat_agglvl: list[str], st_agglvl: list[str], agglvl_titles: dict[str, str]
) -> bool:
    """SRC-QCEW-007: true only when exactly one agglvl_code is observed at each geography
    level, and their titles agree once the leading geography clause is stripped -- i.e. both
    describe the same NAICS-digit detail and the same by-ownership breakout. This defends
    against a titles-metadata inconsistency (the fetched agglvl_code titles disagreeing with
    what industry_code and own_code already pinned upstream): it is a real check on the fetched
    file, not a tautology, and returns False if the titles for the two observed codes disagree.
    It is not, however, guaranteed to add discriminating power beyond the cardinality-of-one
    checks above -- wherever the two observed codes are the same industry-detail row at two
    different geographies, their agreement is close to expected. Whether that is so on any
    given run is computed rather than asserted here: a docstring cannot re-check itself, so
    `_observed_detail_sentence` groups the codes actually observed by their stripped clause and
    records what it finds in `notes`."""
    if len(nat_agglvl) != 1 or len(st_agglvl) != 1:
        return False
    nat_title = agglvl_titles.get(nat_agglvl[0])
    st_title = agglvl_titles.get(st_agglvl[0])
    if nat_title is None or st_title is None:
        return False
    return _agglvl_detail(nat_title) == _agglvl_detail(st_title)


def _agglvl_geography(title: str) -> str:
    """The leading clause `_agglvl_detail` strips off: the geography level the code sits at."""
    return title.split(",", 1)[0].strip() if "," in title else ""


def _agglvl_title_list(codes: list[str], agglvl_titles: dict[str, str]) -> str:
    """Render observed agglvl codes with their fetched titles for `notes` -- pulled from the
    titles mapping fetched this run so this can never drift from what was actually fetched,
    for however many codes are observed (not assumed to be exactly one)."""
    return "; ".join(f"code {code} = {agglvl_titles.get(code)!r}" for code in codes)


def _observed_detail_sentence(agglvl_present: list[dict]) -> str:
    """Computed replacement for a prose claim about the fetched agglvl titles file as a whole.

    Groups the agglvl codes actually observed on `c.INDUSTRY_CODE` rows by the detail clause
    their fetched titles strip to, and states what that grouping shows -- so a future run whose
    codes strip to more than one clause says so instead of repeating today's agreement. Its
    input is `codes_present['agglvl_code']`, which is built on the `c.INDUSTRY_CODE`-filtered
    frame across *both* ownership codes; the sentence therefore describes every `c.INDUSTRY_CODE`
    row, not the private-only subset that nat/state_like carry, and says so. The geography names
    are read out of the fetched titles too, never typed, so they cannot claim a level the data
    does not contain."""
    by_detail: dict[str, list[str]] = {}
    for row in agglvl_present:
        title = row["title"]
        detail = _agglvl_detail(title) if title is not None else "<no fetched title>"
        geo = _agglvl_geography(title) if title is not None else ""
        by_detail.setdefault(detail, []).append(f"{row['code']} ({geo})" if geo else row["code"])
    rendered = "; ".join(
        f"{detail!r} at codes {', '.join(codes)}" for detail, codes in sorted(by_detail.items())
    )
    lead = (
        f"Scope of that agreement, computed from the {len(agglvl_present)} agglvl codes "
        f"observed on {c.INDUSTRY_CODE} rows (both ownerships): "
    )
    if len(by_detail) == 1:
        return (
            f"{lead}all of them strip to one detail clause -- {rendered}. So the "
            "identical-clause property is established across exactly the geography levels "
            "present here, which is all this run shows; it is not a claim about every title "
            "in the fetched agglvl_code.csv, whose other codes were not examined."
        )
    return (
        f"{lead}they strip to {len(by_detail)} distinct detail clauses -- {rendered} -- so the "
        "clause is not uniform across the codes present on these rows."
    )


def _extraneous_area_sentence(detail: list[dict]) -> str:
    """One sentence per state-like area code absent from c.STATE_AREAS, entirely from computed
    detail and the fetched area_fips titles -- never a typed figure, so a future re-run with a
    different extraneous set describes itself instead of silently repeating today's numbers."""
    if not detail:
        return "No state-like area code fell outside c.STATE_AREAS."
    return " ".join(
        f"{d['area_fips']} ({d['title']!r}, {d['row_count']} rows, in "
        f"{', '.join(d['years'])}) is present in state-like rows but absent from c.STATE_AREAS."
        for d in detail
    )


def _dc_sentence(detail: dict, n_quarters: int) -> str:
    """States what state_like actually shows about area_fips '11000' (DC) -- computed, not
    assumed absent, so a future re-run where DC starts publishing describes that instead of
    silently repeating today's absence claim."""
    if detail["present"]:
        return (
            f"District of Columbia (11000) is present in the state-like rows: "
            f"{detail['row_count']} rows, in {', '.join(detail['years'])}."
        )
    return (
        f"District of Columbia (11000) carries zero private-ownership {c.INDUSTRY_CODE} rows "
        f"in any of the {n_quarters} quarters in which {c.INDUSTRY_CODE} rows appear at all: "
        "it is entirely absent from this panel, not merely cell-suppressed within a published "
        "row."
    )


def _geography_universe_note(
    n_quarters: int,
    state_like_areas: list[str],
    extraneous_detail: list[dict],
    dc_detail: dict,
    nat_agglvl: list[str],
) -> str:
    """SRC-QCEW-007 / Sec 3.2 geography-universe evidence for `notes`. Every figure and every
    area code in it is computed from state_like, nat_agglvl and the fetched area_fips titles.
    The one exception is a single BLS documentation quotation, which this script does not fetch
    and so cannot re-derive; the sentence carrying it says that about itself inline rather than
    leaving the reader to assume it was checked this run. States only what the data and BLS's
    published documentation show -- never which way SRC-QCEW-006's branch should resolve. That
    verdict is Task 5's, reached test-first against toy panels before the real scan (plan
    Architecture), not reverse-engineered from this finding."""
    dc_gap = ""
    if not dc_detail["present"]:
        dc_gap = (
            " DC's complete row-level absence is a genuine states_dc coverage gap: a "
            "private-ownership Logging panel over this window will have no DC series at all, "
            "which a later task should expect rather than mistake for a bug. Because US000 "
            "includes DC by definition while no DC state row is published, DC's contribution "
            "to the national total is unobservable at the state level -- a "
            "national-vs-sum-of-states residual distinct from, and additional to, cell-level "
            "suppression."
        )
    nat_label = f"agglvl-{'/'.join(nat_agglvl)}" if nat_agglvl else "national-agglvl"
    return (
        "Geography-universe finding for SRC-QCEW-007 / Sec 3.2: across all "
        f"{n_quarters} quarters in which {c.INDUSTRY_CODE} rows appear, the state-like "
        f"predicate above yields exactly {len(state_like_areas)} distinct area codes. "
        f"{_extraneous_area_sentence(extraneous_detail)} "
        f"{_dc_sentence(dc_detail, n_quarters)} "
        "Hand-transcribed from a BLS page this script does not fetch, so it carries no extract "
        "hash and cannot be re-derived on a later run: BLS's QCEW Aggregation Level Codes page "
        "(https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm, footnote b) "
        "states 'National level aggregations exclude Puerto Rico and Virgin Islands from the "
        f"totals'. Read against the national agglvl code computed above ({nat_label}), that "
        "makes the US000 national total definitionally 50 states + DC, the same composition as "
        f"geography_universe: 'states_dc'.{dc_gap}"
    )


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

    loaded = load_slices()
    df = loaded.filter(pl.col("industry_code") == c.INDUSTRY_CODE)
    # Two counts, not one. Both are computed, not typed, so `notes` below states actual quarter
    # counts rather than assuming the D1 window's nominal 32 -- distinct from load_slices()'s
    # year-only guard, so a single missing quarter within an otherwise-complete year still
    # shows up here. They are kept separate because they answer different questions and can
    # diverge: `n_quarters_loaded` counts the concatenated slice frame the industry_code filter
    # is applied *to*, while `n_quarters` counts the quarters that survive it. They coincide
    # only while every loaded quarter publishes at least one c.INDUSTRY_CODE row; using one
    # where the other belongs would silently attribute a post-filter count to the pre-filter
    # frame. Each `notes` sentence below names which of the two it is quoting.
    n_quarters_loaded = loaded.select(["year", "qtr"]).unique().height
    n_quarters = df.select(["year", "qtr"]).unique().height

    codes_present: dict[str, list[dict]] = {}
    for dim in ("agglvl_code", "own_code", "size_code", "disclosure_code"):
        counts = df.group_by(dim).len().sort(dim)
        codes_present[dim] = [
            {"code": code, "title": maps.get(dim, {}).get(code), "row_count": n}
            for code, n in zip(counts[dim].to_list(), counts["len"].to_list(), strict=True)
        ]
        # Defensive, not corrective: group_by(dim).len() cannot itself drop rows -- every row
        # lands in exactly one group, including a null-key group, so e.g. a null-vs-"" split on
        # a blank disclosure_code still produces two groups whose lengths sum back to
        # df.height. This guards the group_by -> list-comprehension pipeline as a whole (every
        # dimension partitions the same 113310 universe) against a future refactor that could
        # lose rows, not against a defect in group_by itself.
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

    # Geography-universe figures for `notes`, computed from state_like and the fetched
    # area_fips titles rather than typed, so a future re-run against revised or extended data
    # describes what it actually finds instead of silently repeating today's numbers.
    state_like_areas = sorted(set(state_like["area_fips"].to_list()))
    extraneous_detail = []
    for area in sorted(set(state_like_areas) - c.STATE_AREAS):
        sub = state_like.filter(pl.col("area_fips") == area)
        extraneous_detail.append({
            "area_fips": area,
            "title": maps["area_fips"].get(area),
            "row_count": sub.height,
            "years": sorted(set(sub["year"].to_list())),
        })
    dc_rows = state_like.filter(pl.col("area_fips") == "11000")
    dc_detail = {
        "present": dc_rows.height > 0,
        "row_count": dc_rows.height,
        "years": sorted(set(dc_rows["year"].to_list())),
    }

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

    # Neither same_own_code nor same_industry_code is computed as a separate check, for the one
    # reason: each is a single filter applied *before* the national/state-like geography split,
    # so both nat and state_like are sub-frames of an already-filtered frame. nat and state_like
    # both derive from priv = df.filter(own_code == private_own), and priv from
    # df = loaded.filter(industry_code == c.INDUSTRY_CODE), so their own_code values can only
    # ever be {private_own} and their industry_code values only {c.INDUSTRY_CODE} -- or, in
    # either case, the empty set when there are no rows. There is no possible dataset where
    # either differs from the len(nat_agglvl) == 1 / len(st_agglvl) == 1 cardinality checks
    # below, which already fail on the empty case. A dedicated boolean for either would look
    # like an independent verification without being one: it can return only True-when-nonempty,
    # so it can never contradict anything. Both properties still hold and are still required by
    # SRC-QCEW-007 -- they are established by the recorded filter predicates (see
    # filter_predicates_note) rather than by a check that cannot fail. same_detail below is the
    # opposite case and is genuinely computed: it reads the *fetched* agglvl titles, which no
    # filter in this script constrains, so it can and would return False on a titles-metadata
    # inconsistency between the two geography levels.
    same_detail = _same_industry_detail(nat_agglvl, st_agglvl, maps["agglvl_code"])

    aligned = (
        len(nat_agglvl) == 1
        and len(st_agglvl) == 1
        and same_detail
    )

    observed_detail_sentence = _observed_detail_sentence(codes_present["agglvl_code"])

    # The one derivable part of the NAICS-vintage evidence. maps["industry_code"] was fetched
    # and parsed above; reading it here means the note quotes the fetched file instead of a
    # literal typed to match it, and describes an absent code rather than asserting a present
    # one. Deliberately not raised as an error: absence would be a finding for Stage 1 to act
    # on, and it does not invalidate the row inventory this script is producing.
    industry_title = maps["industry_code"].get(c.INDUSTRY_CODE)
    if industry_title is None:
        industry_title_sentence = (
            f"the fetched industry titles file carries no entry for {c.INDUSTRY_CODE} at all, "
            "which is itself a finding to resolve before Stage 1 relies on the code."
        )
    else:
        industry_title_sentence = (
            f"the fetched industry titles file gives {c.INDUSTRY_CODE} = {industry_title!r}, "
            "confirming the code is valid in the vintage that file reflects."
        )

    filter_predicates_note = (
        "Filter predicates recorded verbatim, applied in this order: "
        f"industry_code == '{c.INDUSTRY_CODE}' is applied first, to the full concatenated "
        f"slice frame of {n_quarters_loaded} distinct year-quarters as loaded from Task 2's "
        f"recorded slice CSVs, before any other split; {n_quarters} of those "
        f"{n_quarters_loaded} loaded quarters carry at least one {c.INDUSTRY_CODE} row, and "
        "every per-quarter count quoted elsewhere in these notes names which of the two it "
        f"means. own_code == '{private_own}' (title 'Private', from the fetched ownership "
        "titles file) is applied next, restricting to private ownership; the national/"
        "state-like geography split comes last, so both sides of it are sub-frames of the "
        "already industry- and ownership-filtered frame. National rows are area_fips == "
        "'US000'; state-like rows are area_fips.str.ends_with('000') and area_fips != 'US000'."
    )
    title_evidence_note = (
        "Title evidence for 'same industry detail': fetched agglvl_code titles give national "
        f"{_agglvl_title_list(nat_agglvl, maps['agglvl_code'])} and state "
        f"{_agglvl_title_list(st_agglvl, maps['agglvl_code'])}; stripping the leading "
        "geography clause leaves an identical detail clause at both levels (see "
        "_same_industry_detail). This defends against a titles-metadata inconsistency between "
        "the two geography levels' fetched titles; it is not independent discriminating power, "
        "because digit-depth and ownership breakout are already pinned upstream by the queried "
        f"industry_code and the own_code filter. {observed_detail_sentence}"
    )
    naics_vintage_note = (
        "NAICS vintage sourcing (Step 3). One part of this is derived and the rest is "
        f"hand-authored; both are labelled as such. Derived: {industry_title_sentence} Either "
        "way that settles only the current vintage, never the per-year history: QCEW publishes "
        "no per-row NAICS-vintage column and the titles file reflects only the current "
        "vintage, so naics_vintage_by_year above cannot be computed from anything this script "
        "fetches. Hand-authored, and unavoidably so: the two quotations below were transcribed "
        "by hand from BLS classification pages this script does not fetch, so they carry no "
        "extract hash and no later run re-checks them. "
        "https://www.bls.gov/cew/classifications/industry/naics-2017.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) with the release of first "
        "quarter 2017 Quarterly Census of Employment and Wages (QCEW) data.' "
        "https://www.bls.gov/cew/classifications/industry/naics-2022.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) on September 7, 2022, with the "
        "full data release of first quarter 2022 Quarterly Census of Employment and Wages "
        "(QCEW) data.' QCEW does not retabulate prior reference years onto a new vintage, so "
        "the switch is a hard boundary at reference year 2022, giving the clean per-year split "
        "recorded above. Also hand-checked out-of-band, against the Census NAICS 2012-to-2017 "
        "and 2017-to-2022 concordance files rather than against anything fetched here: both "
        f"carry {c.INDUSTRY_CODE} 'Logging' with a link_type of 1:1 and an unchanged title, so "
        "the industry's definition is stable across the whole window despite the vintage label "
        "change. (Those files record a link_type, not a change indicator; neither carries a "
        "change_indicator column at all, so 'no change flag set' would misdescribe them.)"
    )

    notes = " ".join([
        filter_predicates_note,
        title_evidence_note,
        _geography_universe_note(
            n_quarters, state_like_areas, extraneous_detail, dc_detail, nat_agglvl
        ),
        naics_vintage_note,
    ])

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
