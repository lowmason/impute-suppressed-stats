# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Inventory the QCEW code values actually present on 113310 rows, join published titles, and
record the SRC-QCEW-007 national/state alignment statement."""

from __future__ import annotations

import io
import re

import polars as pl

import _common as c

SOURCE = "qcew_codes"
# Anchored on purpose, and the anchoring is the point. The slice header carries three
# families built on the same stem: the monthly employment levels themselves
# (`month1/2/3_emplvl`), their location quotients (`lq_month1/2/3_emplvl`), and six
# over-the-year change columns (`oty_month{1,2,3}_emplvl_chg` / `_pct_chg`). An unanchored
# "month" or "emplvl" substring test collects all twelve, and a sentence derived from it
# would report twelve monthly employment columns -- a predicate over-collecting the set it
# names, which is the defect the derivation below exists to avoid, not to commit.
MONTHLY_EMPLOYMENT_COLUMN = re.compile(r"^month(\d+)_emplvl$")
TITLES = {
    "agglvl_code": "https://data.bls.gov/cew/doc/titles/agglevel/agglevel_titles.csv",
    "own_code": "https://data.bls.gov/cew/doc/titles/ownership/ownership_titles.csv",
    "size_code": "https://data.bls.gov/cew/doc/titles/size/size_titles.csv",
    "area_fips": "https://data.bls.gov/cew/doc/titles/area/area_titles.csv",
    "industry_code": "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv",
    # `None` means this script requests no titles file for this column, so its codes come from
    # the observed values alone. It is not a claim that BLS publishes none: no request in this
    # run tests that, and `titles_available` (which persists this map) records what was
    # fetched, not what exists. A later task that finds such a file should add the URL here.
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
) -> tuple[bool, str]:
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
    records what it finds in `notes`.

    Returns the verdict *and* a rendered clause naming the branch that produced it, because
    `notes` has to state the outcome rather than assert one. The three False branches are not
    interchangeable -- a cardinality failure, a title missing from the fetched file, and two
    clauses that genuinely differ are three different findings, and only the third one is about
    the clauses at all -- so a single "identical/different" rendering would let a run report a
    clause comparison it never performed."""
    if len(nat_agglvl) != 1 or len(st_agglvl) != 1:
        return False, (
            "the clause comparison was not reached: it needs exactly one agglvl code at each "
            f"geography level, but {len(nat_agglvl)} national and {len(st_agglvl)} state codes "
            "are observed"
        )
    nat_title = agglvl_titles.get(nat_agglvl[0])
    st_title = agglvl_titles.get(st_agglvl[0])
    missing = [
        code for code, title in ((nat_agglvl[0], nat_title), (st_agglvl[0], st_title))
        if title is None
    ]
    if missing:
        return False, (
            "the clause comparison was not reached: the fetched agglvl titles file carries no "
            f"entry for code(s) {', '.join(missing)}"
        )
    nat_detail, st_detail = _agglvl_detail(nat_title), _agglvl_detail(st_title)
    if nat_detail != st_detail:
        return False, (
            "stripping the leading geography clause leaves different detail clauses at the two "
            f"levels -- national {nat_detail!r} vs state {st_detail!r}"
        )
    return True, (
        "stripping the leading geography clause leaves an identical detail clause at both "
        f"levels ({nat_detail!r})"
    )


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
    frame *before* the own_code filter is applied; the sentence therefore describes every
    `c.INDUSTRY_CODE` row at whatever ownership codes are present, not the private-only subset
    that nat/state_like carry, and names that frame rather than counting its ownership codes --
    a cardinality would be one more typed claim free to go stale. The geography names are read
    out of the fetched titles too, never typed, so they cannot claim a level the data does not
    contain."""
    by_detail: dict[str, list[str]] = {}
    for row in agglvl_present:
        title = row["title"]
        detail = _agglvl_detail(title) if title is not None else "<no fetched title>"
        geo = _agglvl_geography(title) if title is not None else ""
        by_detail.setdefault(detail, []).append(f"{row['code']} ({geo})" if geo else row["code"])
    rendered = "; ".join(
        f"{detail!r} at codes {', '.join(codes)}" for detail, codes in sorted(by_detail.items())
    )
    # Neutral lead, prefixed to both returns: it must not name an outcome, because the branch
    # below decides which outcome there is. "Scope of that agreement" read as a contradiction
    # on the disagreement branch, and had no antecedent at all when title_evidence_note placed
    # a "comparison was not reached" clause immediately before it.
    lead = (
        f"Scope of the fetched-title comparison, computed from the {len(agglvl_present)} "
        f"agglvl codes observed on {c.INDUSTRY_CODE} rows before the own_code filter: "
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
    The exception is the closing US000-composition argument: a BLS documentation quotation, an
    unquoted premise about which jurisdictions the national universe contains, and the
    conclusion that needs both. This script fetches none of the three and cannot re-derive any
    of them, so all three say so about themselves inline -- the premise and the conclusion as
    explicitly as the quotation, because the conclusion is the part a later task consumes and a
    marking scoped to the quotation alone would leave it looking checked. The DC-absence
    paragraph that follows on the absent branch reads that conclusion against `_dc_sentence`'s
    measured absence, which is a further step past the composition argument's own scope, so it
    carries its own `INFERENCE MARKER, OPENING`/`CLOSING` pair rather than sheltering under the
    marking above it. What it names is a residual *channel* and where that channel would be
    observed; it claims no magnitude for it, and in particular does not assert that DC has any
    private-ownership activity to contribute -- nothing fetched here establishes that, and the
    establishment margin is measured by `qcew_identity`, not by this script. States only what the
    data and BLS's published documentation show -- never which way SRC-QCEW-006's branch should
    resolve. That verdict is Task 5's, reached test-first against toy panels before the real
    scan (plan Architecture), not reverse-engineered from this finding."""
    dc_gap = ""
    if not dc_detail["present"]:
        dc_gap = (
            " DC's complete row-level absence is a genuine states_dc coverage gap: a "
            "private-ownership Logging panel over this window will have no DC series at all, "
            "which a later task should expect rather than mistake for a bug. INFERENCE "
            "MARKER, OPENING: what follows to the closing marker is a reading of that absence "
            "against the hand-authored membership premise recorded above, not a further "
            "measurement. It is supplied by hand, carries no extract hash, and is re-checked "
            "by no later run. On that premise US000 includes DC, while no DC state row is "
            "published, so nothing at the state level observes whatever DC contributes to the "
            "national total: a potential national-vs-sum-of-states residual channel, distinct "
            "from and additional to cell-level suppression. That is a channel, not a "
            "quantity. Its magnitude is not measured here and no value is claimed for it -- "
            "not even that it is nonzero, which would need DC to carry private "
            f"{c.INDUSTRY_CODE} activity at all, and nothing this script fetched shows "
            "whether it does. Where the channel would show up, if it is open at all, is the "
            "national-minus-sum-of-states difference qcew_identity measures quarter by "
            "quarter: quarter_table's estab_gap and estab_gap_after_other on the "
            "establishment margin, and evidence's clean_months on the employment one. Read "
            "the two findings together rather than either alone. On a margin where "
            "qcew_identity finds that difference closing exactly, its own recorded reading -- "
            "that an area adding zero establishments to a quarterly total which closes "
            "exactly can add no employment in that quarter's months -- rules this channel out "
            "for that margin, and what is left open here is only the margin qcew_identity "
            "could not evaluate. INFERENCE MARKER, CLOSING."
        )
    nat_label = f"agglvl-{'/'.join(nat_agglvl)}" if nat_agglvl else "national-agglvl"
    return (
        "Geography-universe finding for SRC-QCEW-007 / Sec 3.2: across all "
        f"{n_quarters} quarters in which {c.INDUSTRY_CODE} rows appear, the state-like "
        f"predicate above yields exactly {len(state_like_areas)} distinct area codes. "
        f"{_extraneous_area_sentence(extraneous_detail)} "
        f"{_dc_sentence(dc_detail, n_quarters)} "
        "The US000 composition argument that follows is hand-authored in all three of its "
        "parts -- quotation, premise and conclusion. This script fetches none of them, so none "
        "carries an extract hash and no later run re-checks any of them. Quoted, hand-"
        "transcribed from BLS's QCEW Aggregation Level Codes page "
        "(https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm, footnote "
        "b): 'National level aggregations exclude Puerto Rico and Virgin Islands from the "
        "totals'. Unquoted premise, supplied by hand and carried by neither that quotation nor "
        "any other source cited here: the jurisdictions QCEW aggregates into a national total "
        "are "
        "the 50 states, DC, Puerto Rico and the Virgin Islands, and nothing else. Conclusion, "
        f"which needs both: read against the national agglvl code computed above ({nat_label}), "
        "the US000 national total is definitionally 50 states + DC, the same composition as "
        "geography_universe: 'states_dc'. The exclusion quotation on its own says only what is "
        "removed, never what remains -- the membership premise is what closes the argument, and "
        f"it is the part a later task should re-source before relying on this.{dc_gap}"
    )


def _period_basis(slice_columns: list[str]) -> str:
    """`alignment_srcqcew007.period_basis`, in two halves a reader can tell apart.

    The first half is measured this run. It comes from the header of the concatenated slice
    frame `load_slices()` already returns -- no extra fetch, and no re-read of anything: the
    column names are in hand by the time this is called. Both the period-keying columns and
    the monthly employment level columns are reported as found, never as a typed "three", so a
    future QCEW layout carrying two or four of them says two or four here.

    The second half is not measured and cannot be. A column *named* `month1_emplvl` fixes a
    column name; it says nothing about which days of the month the value in it counts. No byte
    this script fetches states that reference period -- not the titles CSVs, not the slice
    files -- so it is quoted from documentation, labelled as fetched by nothing here, and the
    step from that general statement onto these particular columns is delimited by the
    `INFERENCE MARKER, OPENING`/`CLOSING` pair `qcew_identity.absent_state_months_note`
    established. The quotation itself sits outside the marker, as in
    `_geography_universe_note`: transcribing a documented sentence is not the same act as
    reading it onto this run's columns, and only the second is an inference.
    """
    period_cols = [col for col in ("year", "qtr") if col in slice_columns]
    monthly = sorted(col for col in slice_columns
                     if MONTHLY_EMPLOYMENT_COLUMN.fullmatch(col))
    measured = (
        "Measured this run, from the header of the concatenated slice frame load_slices() "
        "returns -- pl.concat(how='vertical') raises on a schema mismatch, so that one header "
        "is the header every slice CSV qcew_routes recorded carries. Period-keying columns "
        f"present, of 'year' and 'qtr': {', '.join(period_cols) or '(none)'}. Monthly "
        f"employment level columns present: {len(monthly)} "
        f"({', '.join(monthly) or 'none'}), matched on the anchored pattern "
        "^month(\\d+)_emplvl$, which is what keeps the location-quotient (lq_) and "
        "over-the-year (oty_) columns built on those same names out of the count. That is the "
        "whole of what the header establishes here: which columns exist and what they are "
        "called."
    )
    if monthly:
        reading = (
            f"The {len(monthly)} column(s) named above are read here as the QCEW monthly "
            "employment counts that statement describes, so each is taken to count over the "
            "pay period including the 12th day of its own month. The fetched slice files do "
            "not say so: their header supplies column names and their rows supply counts, and "
            "neither records a reference period."
        )
    else:
        reading = (
            "No column in this run's header matches ^month(\\d+)_emplvl$, so there is no "
            "column here for that statement to be read onto, and none is claimed to count "
            "over that pay period. The quotation is retained as the program-wide "
            "documentation it is, describing QCEW monthly employment rather than anything "
            "this run measured."
        )
    documented = (
        "Documented, not measured: the reference period a monthly employment column counts "
        "over. Hand-transcribed from the local bls-data-context skill's QCEW reference "
        "(~/.claude/skills/bls-data-context/references/qcew.md, section 'Employment "
        "concept'), which reads: 'QCEW monthly employment counts covered workers who worked "
        "during, or received pay for, the pay period including the 12th day of the month.' "
        "That reference is itself hand-authored and carries no per-section citation -- its "
        "own 'Source pages reviewed' header lists the BLS Handbook of Methods QCEW pages it "
        "drew on without tying any one of them to this sentence -- so no single BLS page is "
        "named for it here. The quotation is not among this run's own fetches: this script's "
        "extracts are the code/title CSVs TITLES names, and none of them states a reference "
        "period. So the quotation carries no extract hash and no later run re-checks it. "
        "INFERENCE MARKER, OPENING: what follows to the closing marker is a "
        "reading of that general statement onto the columns measured above, not a further "
        "measurement; it is supplied by hand, carries no extract hash and is re-checked by no "
        f"later run. {reading} INFERENCE MARKER, CLOSING."
    )
    return f"{measured} {documented}"


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
    # derivable one. Hand-authored (Step 3) from two BLS classification pages plus one unquoted
    # premise -- that QCEW does not retabulate prior reference years onto a new NAICS vintage --
    # which is what turns each page's "introduced with Q1 <year> data" into a claim about what
    # vintage the *earlier* years still carry. Quotations and premise alike are labelled
    # hand-authored in `notes` below; no later run re-checks either. Granting the premise, both
    # switch years fall on QCEW reference-year boundaries, so the mapping is a clean per-year
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
    same_detail, detail_outcome = _same_industry_detail(
        nat_agglvl, st_agglvl, maps["agglvl_code"]
    )

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
        f"{_agglvl_title_list(st_agglvl, maps['agglvl_code'])}; {detail_outcome}, so the "
        f"same-industry-detail conjunct of aligned above is {same_detail} (see "
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
        "fetches. Everything from here to the end of this note is hand-authored -- the "
        "quotations, the premises drawn on alongside them, and the conclusions that need both, "
        "equally. This script fetches none of it, so none of it carries an extract hash and no "
        "later run re-checks any of it. Quoted verbatim from two BLS classification pages: "
        "https://www.bls.gov/cew/classifications/industry/naics-2017.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) with the release of first "
        "quarter 2017 Quarterly Census of Employment and Wages (QCEW) data.' "
        "https://www.bls.gov/cew/classifications/industry/naics-2022.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) on September 7, 2022, with the "
        "full data release of first quarter 2022 Quarterly Census of Employment and Wages "
        "(QCEW) data.' Unquoted premise, and the load-bearing one: QCEW does not retabulate "
        "prior reference years onto a new NAICS vintage. The two quotations establish only the "
        "quarter at which each vintage is introduced; without that premise they say nothing "
        "about what vintage 2017-2021 data carry today, and the entire per-year "
        "naics_vintage_by_year mapping rests on it. It is supplied by hand, is carried by "
        "neither quotation and by no other source cited in this note, and is the single claim "
        "here a later task should re-source first. Granting it, the switch is a hard boundary "
        "at reference year 2022, giving the clean per-year split recorded above. Also "
        "hand-checked out-of-band, against the local classification-codes skill's derived "
        "NAICS data rather than against anything fetched here, and reported with its two "
        f"caveats. That skill's concordance CSVs pair {c.INDUSTRY_CODE} to itself with the "
        "title 'Logging' unchanged in both the 2012-to-2017 and the 2017-to-2022 direction, "
        f"and its NAICS structure CSVs carry an empty change_indicator on {c.INDUSTRY_CODE} in "
        "all three of the 2012, 2017 and 2022 vintages, which that skill documents as meaning "
        "unchanged from the prior vintage at that level. Caveat one: the concordance link_type "
        "of 1:1 is not a Census column. Census ships four columns -- source code, source title, "
        "target code, target title -- flags partial flows by cell formatting the parse "
        "discards, and publishes no allocation weights; link_type is derived by that skill "
        "from code multiplicities after deduplication. Caveat two, following from the first: "
        f"1:1 establishes only that {c.INDUSTRY_CODE} neither split nor merged in the "
        "six-digit code pairing, which is not a statement about the industry's definitional "
        "content. It is the unchanged title and the empty structure-file change_indicator, not "
        "the 1:1, that carry the continuity claim, and even they are titles and markers rather "
        "than a comparison of the two vintages' definitional text."
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
                # `loaded`, not `df`: the industry_code filter changes which rows are present,
                # never which columns are, and the header is what this derivation reads.
                "period_basis": _period_basis(loaded.columns),
                "aligned": aligned,
                "notes": notes,
            },
        },
    )
    print(f"private own_code={private_own}; national agglvl={nat_agglvl}; "
          f"state agglvl={st_agglvl}; aligned={aligned}")


if __name__ == "__main__":
    main()
