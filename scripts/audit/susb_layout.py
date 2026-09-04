# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0", "fastexcel>=0.11"]
# ///
"""SRC-OTH-001 / INV-010: measure whether SUSB's state x industry x size cross-tabs actually
reach six-digit NAICS (113310, Logging) at the state level, and read the size dimension's
concept (enterprise vs. establishment) from the fetched files rather than assuming it.

Deviations from the plan's illustrative code, established empirically against the live static
files during this task (not from memory or the reference repo):

1. **The .txt files are Windows-1252, not UTF-8, and the brief's plain
   `pl.read_csv(io.BytesIO(content), infer_schema_length=0)` crashes on the real file.** Both
   `us_state_naics_detailedsizes_2022.txt` and `us_state_6digitnaics_2022.txt` encode industry
   titles with a right single quotation mark ("Men's and Boys' Cut and Sew Apparel
   Manufacturing") as byte `0x92` -- an invalid UTF-8 start byte. Polars' default
   `encoding="utf8"` raises `polars.exceptions.ComputeError: invalid utf-8 sequence` on both
   files this run, before a single row is read. `decode_susb_text` decodes as cp1252 (which
   covers this run's actual byte, `0x92`, as U+2019 RIGHT SINGLE QUOTATION MARK) with
   `errors="replace"`, and re-encodes to UTF-8 before handing the text to `pl.read_csv`. cp1252
   itself leaves five byte values (`0x81`, `0x8D`, `0x8F`, `0x90`, `0x9D`) undefined and raises
   `UnicodeDecodeError` on them with the default strict error handler -- confirmed by this
   script's own test suite, not assumed; `errors="replace"` is what actually makes this decode
   step unable to raise, not cp1252 alone.

2. **The brief's `size_column` regex never matches either target file's real header.** Both
   files' size-classification column is literally named `ENTRSIZE`, paired with an
   `ENTRSIZEDSCR` description column -- confirmed live from both files' header rows. The
   brief's regex `(?i)(enterprise|establishment).*size|empl?size` requires the word
   "enterprise"/"establishment" spelled out, or the literal substring "empsize"/"emplsize";
   `ENTRSIZE` matches none of those, so the brief's `describe()` would report `size_column:
   None` and `size_values: []` for a file that plainly carries a size dimension. `find_column`
   replaces it with a plain `(?i)size` search that prefers the code column over its `*DSCR`
   label twin -- the same preference this script also applies to the NAICS and geography
   column lookups, made explicit here rather than left to depend on column ordering.

3. **`has_113310` computed over a file's whole NAICS column is a different claim from
   `has_113310_at_state`, and here a wrong one.** `us_state_naics_detailedsizes_2022.txt`
   carries `113310` ONLY on its national/US-total rows (`STATE == "00"`); at the state level
   (`STATE` in the states_dc universe) its industry detail never goes past the NAICS sector
   level (two-digit codes, plus a handful of combined-sector labels like `3133` for sectors
   31-33) -- confirmed live: zero of its 23,887 state-level rows carry `113310`, while all 19
   rows that do carry it have `STATE == "00"`. The brief's `describe()` computes `has_113310`
   over the ENTIRE NAICS column with no geography filter, so a transcription of the brief would
   report `has_113310_at_state.detailed_sizes: true` and
   `detailed_sizes_reaches_six_digit_at_state: true` -- exactly the false claim the Copilot
   review that opened this task warns against: `detailed_sizes` reaches six-digit NAICS
   nationally, not at the state level its own finding name promises.
   `us_state_6digitnaics_2022.txt` DOES carry `113310` at the state level (46 states, confirmed
   live), so this defect would not be caught by any check that only asks whether a file
   mentions `113310` at all. `state_scope`/`has_target_industry`/`code_lengths` filter to
   `STATE`-column values in `_common.STATES_DC_FIPS` before checking, so every "_at_state"
   field answers the question its own name asks.

Ruling D-B (raw retention of non-200 bodies on an access-verdict probe) does not add machinery
here -- see `compose_retention_rule`'s docstring for why this script's shape doesn't have the
repeated-candidate probe D-B was written for.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import polars as pl

import _common as c

SOURCE = "susb"
ROOT = "https://www2.census.gov/programs-surveys/susb/tables/"
RECORD_LAYOUT_URL = (
    "https://www2.census.gov/programs-surveys/susb/technical-documentation/"
    "record_layout_us_and_state_2007_to_present.txt"
)
TARGETS = ("us_state_naics_detailedsizes", "us_state_6digitnaics")

_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


# --- directory-listing parsing ----------------------------------------------------------------


def html_title(body: bytes) -> str:
    """The HTML `<title>` text, lowercased and stripped, or `""` if there isn't one. Same
    approach as `cbp_metadata.py`'s and `bds_detail.py`'s function of the same name -- audit
    scripts are standalone PEP 723 files with no import between them, so this is a deliberate
    duplicate of that approach, not a divergence from it."""
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return match.group(1).decode("utf-8", "replace").strip().lower()


def is_directory_listing(body: bytes) -> bool:
    """True iff `body` carries the Apache-style "Index of ..." `<title>` this run confirmed
    live for both the SUSB tables root and its year directories (and confirmed absent from a
    genuine 404's title, "U.S. Census Bureau: Page not found"). The task's general warning --
    never conclude from an HTTP status alone -- bites hardest on `latest_year`: a 200 response
    whose body is a relocated page or a CDN interstitial could still hand `year_dirs`/
    `filenames` a body to regex-search, silently yielding a plausible-but-wrong year or file
    list. This does not defend against every such body (a coincidentally matching title would
    still pass), but it catches the shape of failure the task names."""
    return html_title(body).startswith("index of")


def year_dirs(html: str) -> list[int]:
    return sorted({int(y) for y in re.findall(r'href="(\d{4})/"', html)})


def filenames(html: str) -> list[str]:
    return sorted(set(re.findall(r'href="([^"/]+\.(?:txt|xlsx|zip))"', html)))


def choose_file(candidates: list[str]) -> str | None:
    """Prefer the .txt variant: it is plain CSV with one header row (once decoded correctly --
    module docstring point 1). The .xlsx fallback often carries title rows above the header,
    which `read_table`'s .xlsx branch does not attempt to skip; this run found a .txt match for
    both target stems, so that branch was never exercised live (see the task report). Pure
    filename selection -- no bytes are read here -- so it is testable without fastexcel, which
    the documented test command does not install."""
    txt = next((n for n in candidates if n.endswith(".txt")), None)
    if txt:
        return txt
    return next((n for n in candidates if n.endswith(".xlsx")), None)


# --- table parsing ----------------------------------------------------------------------------


def decode_susb_text(content: bytes) -> str:
    """SUSB's .txt exports are Windows-1252, not UTF-8 -- confirmed live (module docstring
    point 1): industry titles like "Men's and Boys' Cut and Sew Apparel..." encode the right
    single quotation mark as byte 0x92, an invalid UTF-8 start byte, which cp1252 covers.
    cp1252 itself still leaves five byte values (0x81, 0x8D, 0x8F, 0x90, 0x9D) undefined and
    raises UnicodeDecodeError on them by default; `errors="replace"` is what makes this
    function unable to raise on arbitrary bytes, not cp1252 alone -- a parse failure this early
    would abort the whole run before any layout finding is derived, so this must never raise
    regardless of what a future year's file happens to contain."""
    return content.decode("cp1252", errors="replace")


def read_table(chosen: str, content: bytes) -> pl.DataFrame:
    """Parse a chosen file's bytes into a DataFrame, dispatching on its extension. The .txt
    branch decodes as cp1252 and re-encodes to UTF-8 before `pl.read_csv` (module docstring
    point 1); `infer_schema_length=0` keeps every column Utf8, matching `qcew_routes.py`'s
    `read_csv_bytes` -- `STATE` and `NAICS` both carry leading zeros / literal dashes that a
    numeric or date inference would corrupt. The .xlsx branch needs fastexcel, absent from the
    documented test command (see `choose_file`'s docstring) -- untested by `tests/audit`,
    exercised only by the live run described in the task report."""
    if chosen.endswith(".txt"):
        text = decode_susb_text(content)
        return pl.read_csv(text.encode("utf-8"), infer_schema_length=0)
    return pl.read_excel(io.BytesIO(content))  # no infer_schema_length kwarg on read_excel


def find_column(cols: list[str], pattern: str) -> str | None:
    """First column (in `cols`' original order) matching `pattern`, preferring a code column
    over its paired `*DSCR` description twin when both match -- SUSB pairs a coded field (e.g.
    `ENTRSIZE`, `NAICS`, `STATE`) with a `*DSCR` column carrying the same information as text,
    and every caller here needs the code column: `code_lengths`/`has_target_industry` need real
    NAICS codes to measure string length and equality against, not their titles. Returns `None`
    if `pattern` matches nothing in `cols`."""
    hits = [col for col in cols if re.search(pattern, col)]
    non_descr = [col for col in hits if not re.search(r"(?i)dscr", col)]
    if non_descr:
        return non_descr[0]
    return hits[0] if hits else None


# --- layout derivation ------------------------------------------------------------------------


def code_lengths(df: pl.DataFrame, naics_col: str | None) -> list[int]:
    """Distinct lengths of `naics_col`'s values with internal dashes stripped (SUSB spells a
    combined-sector code as e.g. "31-33" at the national level), EXCLUDING the "--"
    all-industries aggregate placeholder: dash-stripped, "--" becomes the empty string, and an
    empty string's length (0) is not a NAICS code length -- it would otherwise appear as a
    phantom 0 entry in a field whose entire purpose is describing real code granularity.
    Returns `[]` if `naics_col` is `None` (no NAICS-like column was found in this file)."""
    if naics_col is None:
        return []
    codes = df[naics_col].drop_nulls().cast(pl.Utf8).str.replace_all("-", "")
    return sorted({len(v) for v in codes.to_list() if v != ""})


def state_scope(
    df: pl.DataFrame, *, geo_col: str | None, state_fips: tuple[str, ...]
) -> pl.DataFrame:
    """Rows whose `geo_col` value is a states_dc FIPS code -- excludes the national/US-total row
    (`"00"`) and anything else outside the states_dc universe. Raises if `geo_col` is missing,
    or if the filter matches zero rows: a genuine state-level SUSB file always has state rows,
    so zero here is almost certainly a schema/type mismatch (e.g. a geography column that lost
    its leading zero to numeric inference, so `"01"` never equals the string `"01"` in
    `state_fips`) rather than a real finding -- and a state-scoped boolean silently derived from
    an empty frame would read as `False`, the same answer a genuine "not published at the state
    level" finding produces, for an entirely different and wrong reason."""
    if geo_col is None:
        raise RuntimeError(
            "no geography column found; cannot restrict rows to the states_dc universe"
        )
    scoped = df.filter(pl.col(geo_col).cast(pl.Utf8).is_in(list(state_fips)))
    if scoped.height == 0:
        raise RuntimeError(
            f"state-scoping on {geo_col!r} against the states_dc FIPS universe matched zero "
            f"rows out of {df.height} -- refusing to derive a state-level finding from an "
            "empty frame; check whether the geography column kept its string type "
            "(infer_schema_length=0) rather than losing leading zeros to numeric inference"
        )
    return scoped


def has_target_industry(df: pl.DataFrame, *, naics_col: str | None, target: str) -> bool:
    """True iff `target` (e.g. "113310") appears, dash-stripped, anywhere in `df`'s NAICS
    column. Takes whatever frame it is given -- the caller decides whether that frame is a
    whole file or an already state-scoped subset; this function makes no geography claim of its
    own, which is what keeps a whole-file check and `has_113310_at_state` from silently sharing
    one answer whose scope depends on which frame happened to be passed in."""
    if naics_col is None:
        return False
    codes = df[naics_col].drop_nulls().cast(pl.Utf8).str.replace_all("-", "")
    return bool((codes == target).any())


def describe_layout(
    df: pl.DataFrame, *, state_fips: tuple[str, ...], target_industry: str
) -> dict:
    """One file's shape: columns, row count, the detected size/NAICS/geography columns and
    their values, and both a file-wide and a state-scoped read of NAICS code granularity and
    target-industry presence. `size_values`/`geography_levels` are reported in full, not
    sampled -- SUSB's real cardinalities here (at most 26 size buckets; 52 geography codes: 50
    states + D.C. + the national total) are small enough that a sampling cap would hide data
    rather than summarize it. The brief capped both at 40/10; seeing the actual file made the
    52-item geography column the deciding case (a 10-item cap would have discarded 42 of 52
    codes under a key literally named "geography_levels") -- see the task report.

    Caution for a reader of `industry_code_lengths_at_state`: a length of 4 there is NOT
    evidence of real 4-digit NAICS industry detail. Confirmed live in
    `us_state_naics_detailedsizes_2022.txt`'s state-level rows: the only length-4 values are
    `3133`, `4445`, `4849` -- dash-stripped NAICS SECTOR-RANGE labels (e.g. "31-33" for
    Manufacturing), not 4-digit subsector codes. This script measures string length, not
    NAICS-code semantics, and does not distinguish the two."""
    cols = df.columns
    size_col = find_column(cols, r"(?i)size")
    naics_col = find_column(cols, r"(?i)naics")
    geo_col = find_column(cols, r"(?i)state|geo")

    state_rows = state_scope(df, geo_col=geo_col, state_fips=state_fips)

    return {
        "columns": cols,
        "row_count": df.height,
        "size_column": size_col,
        "size_values": (
            sorted(set(df[size_col].drop_nulls().cast(pl.Utf8).to_list())) if size_col else []
        ),
        "industry_code_lengths": code_lengths(df, naics_col),
        "industry_code_lengths_at_state": code_lengths(state_rows, naics_col),
        "geography_levels": (
            sorted(set(df[geo_col].drop_nulls().cast(pl.Utf8).to_list())) if geo_col else []
        ),
        "has_113310_at_state": has_target_industry(
            state_rows, naics_col=naics_col, target=target_industry
        ),
    }


# --- size_concept: read from the record-layout document, never assumed from a column name -----


def field_description(doc_text: str, column_name: str) -> str:
    """The record-layout's own block for `column_name`: the line beginning with the field name
    (matching the "Name / Type / Description" table's layout) through to the next blank line.
    Every field block this script looks up (STATE, NAICS, ENTRSIZE, FIRM, ESTB) in
    `record_layout_us_and_state_2007_to_present.txt` is exactly this shape -- a field-name line
    plus zero or more continuation lines, terminated by a blank line before the next field.
    Returns `""` if `column_name` never starts a line in `doc_text`, so a caller can distinguish
    "the field isn't documented here" from a real, if uninformative, description."""
    lines = doc_text.splitlines()
    pattern = re.compile(rf"^{re.escape(column_name)}\b")
    start = next((i for i, line in enumerate(lines) if pattern.match(line)), None)
    if start is None:
        return ""
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if not line.strip():
            break
        block.append(line)
    return "\n".join(block)


def classify_size_concept(description: str) -> str:
    """"enterprise" or "establishment" if exactly one of those words appears in `description`
    (case-insensitively); "unclear" otherwise -- including when neither appears, and,
    deliberately, when BOTH appear. The record layout document as a whole contains both words
    (ENTRSIZE's own block says "Enterprise ... Size"; ESTB's block, a few fields away, says
    "Number of Establishments"), so classifying the WHOLE document rather than one field's
    isolated block would always return "unclear" regardless of the real answer.
    `field_description` isolating a single field's block first is what lets this function
    resolve a real concept instead of always landing on the fail-safe default."""
    lower = description.lower()
    has_enterprise = "enterprise" in lower
    has_establishment = "establishment" in lower
    if has_enterprise and not has_establishment:
        return "enterprise"
    if has_establishment and not has_enterprise:
        return "establishment"
    return "unclear"


def resolve_size_concept(record_layout_text: str, detailed: dict, six: dict) -> dict:
    """`size_concept`'s value plus the column and record-layout text that established it.
    INV-010 depends on this being read from the fetched record-layout text, not assumed from
    the column name's abbreviation -- "ENTR" is suggestive but is not itself the record layout's
    own word for the concept. `note` (pre-authorized per the dispatch's D-3-style ruling on this
    task) always carries the deciding evidence, whichever way the concept resolves, not only
    when it is "unclear". Both target files' detected size columns agreed (`ENTRSIZE`) for the
    year this task ran against; if they ever disagree, that disagreement is recorded in `note`
    rather than silently resolved by picking one file's column over the other's."""
    detailed_col, six_col = detailed["size_column"], six["size_column"]
    if detailed_col and six_col and detailed_col != six_col:
        return {
            "value": "unclear",
            "column": None,
            "note": (
                f"detailed_sizes_layout.size_column ({detailed_col!r}) and "
                f"six_digit_state_layout.size_column ({six_col!r}) disagree; each file's size "
                "concept must be read separately rather than assumed to match."
            ),
        }
    column = detailed_col or six_col
    if column is None:
        return {
            "value": "unclear",
            "column": None,
            "note": "no size-classification column was detected in either target file.",
        }
    evidence = field_description(record_layout_text, column)
    if not evidence:
        return {
            "value": "unclear",
            "column": column,
            "note": (
                f"{column!r} does not appear as a field name in the fetched record-layout "
                "document."
            ),
        }
    return {"value": classify_size_concept(evidence), "column": column, "note": evidence}


# --- raw retention (ruling D-B) ---------------------------------------------------------------


def compose_retention_rule(extract_statuses: list[int]) -> dict:
    """Ruling D-B, applied to this script's actual shape. Unlike `bds_detail.py`'s
    five-candidate NAICS probe or the year x quarter boundary walk in `qcew_routes.py`, this
    script never probes multiple candidate URLs expecting some of them to answer non-200 --
    every fetch here (the tables root, the year directory, the record-layout document, and each
    chosen data file) is a single, specific GET for a resource whose presence a preceding fetch
    already established. `_common.request` and `_common.download_extract` raise rather than
    return on a non-retryable 4xx or an exhausted 5xx/429 retry budget, so a failure on any of
    those fetches aborts this run before `write_summary` is ever reached and registers no
    extract for the failed resource -- there is no partial summary and no non-200 body left to
    retain, matching `bds_detail.py`'s own precedent for its single, non-probed
    `variables.json` fetch. The counters below therefore describe only a completed, successful
    run; their being zero is not evidence that a non-200 response is impossible for this
    script, only that every fetch which reached `write_summary` this run answered 200."""
    return {
        "rule": (
            "This script makes no repeated multi-candidate access-verdict probe (contrast "
            "bds_detail.py's five-candidate NAICS probe or qcew_routes.py's year x quarter "
            "boundary walk); every fetch here -- the tables root, the year directory, the "
            "record-layout document, and each chosen data file -- is a single GET for a "
            "resource whose presence a preceding fetch already established. "
            "_common.request and _common.download_extract raise rather than return on a "
            "non-retryable 4xx or an exhausted 5xx/429 retry budget, so a failure on any of "
            "those fetches aborts this run before write_summary is reached and registers no "
            "extract for the failed resource -- there is no partial summary and no non-200 "
            "body left to retain, matching bds_detail.py's own precedent for its single "
            "non-probed variables.json fetch. Every extract this script does register "
            "therefore carries http_status 200; the counters below describe only a completed, "
            "successful run, and their being zero is not evidence that a non-200 response is "
            "impossible here, only that this run's every fetch that reached write_summary "
            "answered 200."
        ),
        "extracts_recorded": len(extract_statuses),
        "extracts_with_non_200_status": sum(1 for s in extract_statuses if s != 200),
        "non_200_statuses_recorded": sorted({s for s in extract_statuses if s != 200}),
    }


def main() -> None:
    client = c.build_client()
    extracts: list[c.ExtractRecord] = []

    root = c.request(client, ROOT)
    if not is_directory_listing(root.content):
        raise RuntimeError(
            f"SUSB tables root at {ROOT} did not return a directory-listing page (title: "
            f"{html_title(root.content)!r}); refusing to parse year links from unexpected "
            "content"
        )
    extracts.append(c.record_extract(SOURCE, ROOT, "tables_index.html", root.content))
    years = year_dirs(root.text)
    if not years:
        raise RuntimeError("no year directories parsed from the SUSB tables index")
    latest = years[-1]

    ydir = f"{ROOT}{latest}/"
    ylist = c.request(client, ydir)
    if not is_directory_listing(ylist.content):
        raise RuntimeError(
            f"SUSB year directory at {ydir} did not return a directory-listing page (title: "
            f"{html_title(ylist.content)!r}); refusing to parse file links from unexpected "
            "content"
        )
    extracts.append(c.record_extract(SOURCE, ydir, f"{latest}_index.html", ylist.content))
    names = filenames(ylist.text)
    if not names:
        raise RuntimeError(f"no data files parsed from the SUSB year directory at {ydir}")

    layouts: dict[str, dict] = {}
    for stem in TARGETS:
        candidates = [n for n in names if n.startswith(stem)]
        chosen = choose_file(candidates)
        if chosen is None:
            layouts[stem] = {
                "filename": None,
                "note": f"not obtainable -- no matching file under {ydir}",
            }
            continue
        url = ydir + chosen
        rec = c.download_extract(client, SOURCE, url, chosen)
        extracts.append(rec)
        df = read_table(chosen, Path(rec.path).read_bytes())
        layouts[stem] = {
            "filename": chosen,
            **describe_layout(df, state_fips=c.STATES_DC_FIPS, target_industry=c.INDUSTRY_CODE),
        }

    for stem in TARGETS:
        if layouts[stem]["filename"] is None:
            raise RuntimeError(
                f"target file for stem {stem!r} not found under {ydir}; cannot derive "
                "state-level findings without it"
            )

    detailed = layouts["us_state_naics_detailedsizes"]
    six = layouts["us_state_6digitnaics"]

    layout_resp = c.request(client, RECORD_LAYOUT_URL)
    extracts.append(
        c.record_extract(SOURCE, RECORD_LAYOUT_URL, "record_layout.txt", layout_resp.content)
    )
    size_concept = resolve_size_concept(layout_resp.text, detailed, six)

    has_113310_at_state = {
        "detailed_sizes": detailed["has_113310_at_state"],
        "six_digit": six["has_113310_at_state"],
    }
    reaches_six_digit_at_state = bool(
        detailed["has_113310_at_state"] and 6 in detailed["industry_code_lengths_at_state"]
    )

    covered_years = [y for y in c.WINDOW_YEARS if y <= latest]
    covered = f"{covered_years[0]}-{covered_years[-1]}" if covered_years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y > latest)

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(years[0]),
            "published_end": str(latest),
            "window_start": c.WINDOW_START,
            "window_end": c.WINDOW_END,
            "covered": covered,
            "uncovered": uncovered,
        },
        access={"route": ROOT + "{year}/", "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "latest_year": latest,
            "files_found": names,
            "detailed_sizes_layout": detailed,
            "six_digit_state_layout": six,
            "size_concept": size_concept,
            "has_113310_at_state": has_113310_at_state,
            "detailed_sizes_reaches_six_digit_at_state": reaches_six_digit_at_state,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
        },
    )
    print("SUSB latest year:", latest, "| size concept:", size_concept["value"])
    print("detailed-sizes reaches six-digit at state:", reaches_six_digit_at_state)


if __name__ == "__main__":
    main()
