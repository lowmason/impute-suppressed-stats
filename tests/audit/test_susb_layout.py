"""Judgment-logic tests for `susb_layout` (SRC-OTH-001 / INV-010), pinned against real bytes
fetched live from `www2.census.gov` during this task -- not from memory.

Three defects were confirmed live and are pinned here, matching the numbering in
`susb_layout.py`'s module docstring:

1. **Both target .txt files are Windows-1252, not UTF-8.** `pl.read_csv` with the brief's
   implicit `encoding="utf8"` raises `polars.exceptions.ComputeError` on real
   `us_state_naics_detailedsizes_2022.txt` bytes at the first "Men's and Boys'..." industry
   title (byte `0x92`). `decode_susb_text`/`read_table`'s .txt branch fix this; pinned below
   with a synthetic fixture carrying the same byte.
2. **The brief's size-column regex never matches `ENTRSIZE`**, the real column name in both
   target files. `find_column` replaces it; pinned against the real SUSB column list.
3. **`has_113310` computed over a whole file is a different (here false) claim from
   `has_113310_at_state`.** `us_state_naics_detailedsizes_2022.txt` carries `113310` only at
   `STATE == "00"` (confirmed live: 0 of 23,887 state-level rows, all 19 matching rows at
   `STATE == "00"`); `us_state_6digitnaics_2022.txt` carries it at 45 real states (46 distinct
   `STATE` values, one of which is `"00"`, the national row, not a state). `describe_layout`
   is pinned below against two small fixtures reproducing exactly this shape, through the same
   code path, so the asymmetry is not a coincidence of two separately-written checks.

`susb_layout` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.

This suite never calls `pl.read_excel` / `read_table`'s .xlsx branch: fastexcel is not in the
documented test command (`PYTHONPATH=scripts/audit uv run --no-project --with httpx --with
polars --with pytest pytest tests/audit -q`), only in the script's own PEP 723 dependency
block. `choose_file` (pure filename selection) and `read_table`'s .txt branch (plain
`pl.read_csv`, no fastexcel) are both fully testable without it.
"""

from __future__ import annotations

import polars as pl

import susb_layout as m

# A faithful excerpt of the real record layout document fetched live from
# https://www2.census.gov/programs-surveys/susb/technical-documentation/
# record_layout_us_and_state_2007_to_present.txt -- STATE through EMPL, byte-for-byte
# (including the mixed tabs/spaces and the stray whitespace-only line after NAICS's block).
# Deliberately includes ESTB ("Number of Establishments") alongside ENTRSIZE ("Enterprise
# Employment Size Code") -- both words appear in this excerpt, which is exactly what makes the
# block-isolation tests below meaningful rather than vacuous.
RECORD_LAYOUT_EXCERPT = (
    "Statistics of U.S. Businesses\n2007-present Record Layout \n"
    "ANNUAL DATA - United States & States                                \n\n\n"
    "               Data  \nName           Type     Description\n\n"
    "STATE       \tC       Geographic Area Code\n"
    "\t\t\t  U.S. = 00\n"
    "                          FIPS State 2-digit codes\n\n"
    "NAICS           C       Industry Code \n"
    "\t\t          6-digit, North American Industry Classification System (NAICS)\n"
    "   \n"
    "ENTRSIZE\tC\tEnterprise Employment Size Code\n"
    "\t\t\tEnterprise Receipt Size Code * years ending in 2 and 7 only\n\n"
    "FIRM\t\tN\tNumber of Firms\n\n"
    "ESTB\t\tN\tNumber of Establishments\n\n"
    "EMPL\t\tN\tEmployment with Noise\n"
)

# The real column order/names from both us_state_naics_detailedsizes_2022.txt and
# us_state_6digitnaics_2022.txt's header rows -- identical between the two files.
SUSB_REAL_COLUMNS = [
    "STATE", "NAICS", "ENTRSIZE", "FIRM", "ESTB", "EMPL", "EMPLFL_N", "PAYR", "PAYRFL_N",
    "RCPT", "RCPTFL_N", "STATEDSCR", "NAICSDSCR", "ENTRSIZEDSCR",
]

# A compact reconstruction of the real hrefs observed on
# https://www2.census.gov/programs-surveys/susb/tables/ -- includes the non-year navigation
# links (parent dir, Apache sort-order links, the time-series/ sibling directory, absolute
# census.gov URLs, a stylesheet link) that a naive regex could mismatch against.
ROOT_INDEX_HTML = (
    "<title>Index of /programs-surveys/susb/tables</title>"
    '<a href="/programs-surveys/susb/">Parent Directory</a>'
    '<a href="?C=D;O=A">Name</a> <a href="?C=M;O=A">Last modified</a>'
    '<a href="?C=N;O=D">Size</a> <a href="?C=S;O=A">Description</a>'
    '<a href="1992/">1992/</a> <a href="1997/">1997/</a> <a href="1998/">1998/</a>'
    '<a href="2021/">2021/</a> <a href="2022/">2022/</a>'
    '<a href="time-series/">time-series/</a>'
    '<a href="https://www.census.gov">census.gov</a>'
    '<link rel="stylesheet" href="/main/css/all_header_styles.css">'
)

# A compact reconstruction of the real hrefs observed on
# https://www2.census.gov/programs-surveys/susb/tables/2022/.
YEAR_DIR_HTML = (
    "<title>Index of /programs-surveys/susb/tables/2022</title>"
    '<a href="/programs-surveys/susb/tables/">Parent Directory</a>'
    '<a href="?C=D;O=A">Name</a>'
    '<a href="OLD-msa_3digitnaics_2022.xlsx">OLD-msa_3digitnaics_2022.xlsx</a>'
    '<a href="cd_naicssector_2022.xlsx">cd_naicssector_2022.xlsx</a>'
    '<a href="county_3digitnaics_2022.xlsx">county_3digitnaics_2022.xlsx</a>'
    '<a href="us_6digitnaics_rcptsize_2022.xlsx">us_6digitnaics_rcptsize_2022.xlsx</a>'
    '<a href="us_state_6digitnaics_2022.txt">us_state_6digitnaics_2022.txt</a>'
    '<a href="us_state_6digitnaics_2022.xlsx">us_state_6digitnaics_2022.xlsx</a>'
    '<a href="us_state_naics_detailedsizes_2022.txt">us_state_naics_detailedsizes_2022.txt</a>'
    '<a href="us_state_naics_detailedsizes_2022.xlsx">'
    "us_state_naics_detailedsizes_2022.xlsx</a>"
    '<link rel="stylesheet" href="/main/css/all_header_styles.css">'
)

# The real <title> text of a genuine 404 from this host (confirmed live for a nonexistent
# year directory) -- distinct from any "Index of ..." title.
REAL_404_TITLE_HTML = "<title>U.S. Census Bureau: Page not found</title>"


def detailedsizes_shaped_df() -> pl.DataFrame:
    """Reproduces, in miniature, the real asymmetry confirmed live in
    us_state_naics_detailedsizes_2022.txt: the target industry (113310) appears only on the
    national/US-total row (STATE == "00"); the state-level rows never carry it, and their NAICS
    detail stops at the sector level ("11") or a combined-sector label ("3133", for the real
    sectors-31-33 label observed live)."""
    return pl.DataFrame({
        "STATE": ["00", "00", "01", "01"],
        "NAICS": ["--", "113310", "11", "3133"],
        "ENTRSIZE": ["01", "01", "01", "01"],
        "ENTRSIZEDSCR": ["01: Total", "01: Total", "01: Total", "01: Total"],
    })


def sixdigit_shaped_df() -> pl.DataFrame:
    """Reproduces, in miniature, the real shape confirmed live in
    us_state_6digitnaics_2022.txt: the target industry (113310) appears on a real state row
    (STATE == "01"), not only the national/US-total row."""
    return pl.DataFrame({
        "STATE": ["00", "00", "01", "01"],
        "NAICS": ["--", "113310", "11", "113310"],
        "ENTRSIZE": ["01", "01", "01", "01"],
        "ENTRSIZEDSCR": ["01: Total", "01: Total", "01: Total", "01: Total"],
    })


# --- module docstring: the 45-vs-46-states count (fix round 1, finding 1) ------------------------


def test_module_docstring_states_the_real_state_count_not_the_national_row_inflated_one():
    """Fix round 1, finding 1: the shipped docstring claimed `us_state_6digitnaics_2022.txt`
    carries `113310` in "46 states, confirmed live". The controller verified directly against
    the fetched file that the real count is 45 real states -- 46 is 45 states plus the
    national/US-total row (`STATE == "00"`) counted as a 46th state, the exact `has_113310` vs.
    `has_113310_at_state` collision this module's defect 3 exists to catch, now recurring inside
    defect 3's own explanatory paragraph. No function returns this count (it is prose only, not
    a computed finding -- `summary.json` stores only the boolean `has_113310_at_state.six_digit`
    per module docstring point 3, so this pins `m.__doc__` directly, the only place the claim
    lives), so the corrected text and the absence of the false phrase are both asserted here."""
    assert "45 real states" in m.__doc__
    assert "46 states, confirmed" not in m.__doc__


# --- html_title / is_directory_listing -----------------------------------------------------------


def test_html_title_reads_the_real_root_index_title():
    assert m.html_title(ROOT_INDEX_HTML.encode()) == "index of /programs-surveys/susb/tables"


def test_html_title_reads_the_real_year_dir_title():
    assert m.html_title(YEAR_DIR_HTML.encode()) == "index of /programs-surveys/susb/tables/2022"


def test_html_title_returns_empty_string_when_no_title_tag():
    assert m.html_title(b"<html><body>no title here</body></html>") == ""


def test_is_directory_listing_true_for_the_real_root_index_page():
    assert m.is_directory_listing(ROOT_INDEX_HTML.encode()) is True


def test_is_directory_listing_true_for_the_real_year_dir_page():
    assert m.is_directory_listing(YEAR_DIR_HTML.encode()) is True


def test_is_directory_listing_false_for_the_real_404_title():
    """Confirmed live: a genuine 404 from this host titles itself "U.S. Census Bureau: Page not
    found", never "Index of ..." -- must not be mistaken for a directory listing."""
    assert m.is_directory_listing(REAL_404_TITLE_HTML.encode()) is False


def test_is_directory_listing_false_when_no_title_at_all():
    assert m.is_directory_listing(b"<html><body>nothing here</body></html>") is False


# --- year_dirs -------------------------------------------------------------------------------


def test_year_dirs_reads_only_the_four_digit_year_links():
    assert m.year_dirs(ROOT_INDEX_HTML) == [1992, 1997, 1998, 2021, 2022]


def test_year_dirs_ignores_the_apache_sort_order_links():
    """?C=D;O=A / ?C=M;O=A / etc. are Apache's column-sort links, present on the real page --
    must never be mistaken for a year directory."""
    html = '<a href="?C=D;O=A">Name</a><a href="?C=M;O=A">Last modified</a>'
    assert m.year_dirs(html) == []


def test_year_dirs_ignores_the_time_series_sibling_directory():
    assert m.year_dirs('<a href="time-series/">time-series/</a>') == []


def test_year_dirs_ignores_absolute_census_gov_links():
    assert m.year_dirs('<a href="https://www.census.gov">census.gov</a>') == []


def test_year_dirs_ignores_the_parent_directory_link():
    assert m.year_dirs('<a href="/programs-surveys/susb/">Parent Directory</a>') == []


def test_year_dirs_dedupes_and_sorts():
    html = '<a href="2022/">x</a><a href="1992/">y</a><a href="2022/">x again</a>'
    assert m.year_dirs(html) == [1992, 2022]


# --- filenames -------------------------------------------------------------------------------


def test_filenames_reads_the_real_year_dir_file_list():
    names = m.filenames(YEAR_DIR_HTML)
    assert "us_state_naics_detailedsizes_2022.txt" in names
    assert "us_state_naics_detailedsizes_2022.xlsx" in names
    assert "us_state_6digitnaics_2022.txt" in names
    assert "OLD-msa_3digitnaics_2022.xlsx" in names


def test_filenames_excludes_the_stylesheet_link():
    assert m.filenames(YEAR_DIR_HTML) == sorted(set(m.filenames(YEAR_DIR_HTML)))
    assert "all_header_styles.css" not in "".join(m.filenames(YEAR_DIR_HTML))


def test_filenames_excludes_the_apache_sort_order_and_parent_links():
    html = (
        '<a href="?C=D;O=A">Name</a>'
        '<a href="/programs-surveys/susb/tables/">Parent Directory</a>'
        '<a href="real_file_2022.txt">real_file_2022.txt</a>'
    )
    assert m.filenames(html) == ["real_file_2022.txt"]


# --- choose_file -----------------------------------------------------------------------------


def test_choose_file_prefers_txt_over_xlsx():
    candidates = [
        "us_state_naics_detailedsizes_2022.xlsx", "us_state_naics_detailedsizes_2022.txt",
    ]
    assert m.choose_file(candidates) == "us_state_naics_detailedsizes_2022.txt"


def test_choose_file_falls_back_to_xlsx_when_no_txt():
    assert m.choose_file(["us_state_naics_detailedsizes_2022.xlsx"]) == (
        "us_state_naics_detailedsizes_2022.xlsx"
    )


def test_choose_file_returns_none_for_no_candidates():
    assert m.choose_file([]) is None


def test_choose_file_ignores_a_zip_candidate():
    """Only txt/xlsx are ever preferred/fallen-back-to; a .zip candidate (not observed live for
    these two stems, but filenames() itself would pass one through) is neither."""
    assert m.choose_file(["some_file_2022.zip"]) is None


# --- require_chosen_file (fix round 1, finding 3) ---------------------------------------------


def test_require_chosen_file_returns_the_chosen_filename_when_one_matches():
    candidates = ["us_state_naics_detailedsizes_2022.txt"]
    assert m.require_chosen_file(candidates, stem="us_state_naics_detailedsizes", ydir="X/") == (
        "us_state_naics_detailedsizes_2022.txt"
    )


def test_require_chosen_file_raises_immediately_when_no_candidate_matches():
    """Fix round 1, finding 3: `main()` used to build a `{"filename": None, "note": "not
    obtainable -- ..."}` placeholder for exactly this case, then raise on it in a second loop
    before `write_summary` was ever reached -- dead code, since nothing could ever read `note`.
    `require_chosen_file` raises here directly instead; this is the reachable replacement for
    that dead branch, not the branch itself."""
    try:
        m.require_chosen_file([], stem="us_state_6digitnaics", ydir="https://example/2022/")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "us_state_6digitnaics" in str(exc)
        assert "https://example/2022/" in str(exc)


# --- decode_susb_text / read_table (.txt branch only -- no fastexcel) --------------------------


def test_decode_susb_text_reads_the_real_windows_1252_right_single_quote():
    """Byte 0x92 in cp1252 is U+2019 RIGHT SINGLE QUOTATION MARK -- confirmed live in
    us_state_naics_detailedsizes_2022.txt's "Men's and Boys' Cut and Sew Apparel..." NAICS
    title. This same byte is an invalid UTF-8 start byte, which is exactly why the brief's
    implicit UTF-8 decode crashes on the real file (module docstring point 1)."""
    body = "United States,Men’s and Boys’ Apparel".encode("cp1252")
    assert b"\x92" in body  # confirms this fixture actually carries the byte that broke UTF-8
    assert m.decode_susb_text(body) == "United States,Men’s and Boys’ Apparel"


def test_decode_susb_text_never_raises_on_any_byte_value():
    """cp1252 itself leaves five byte values (0x81, 0x8D, 0x8F, 0x90, 0x9D) undefined and would
    raise UnicodeDecodeError on them under the default strict error handler -- confirmed by
    this test failing before decode_susb_text used errors="replace". A full 0x00-0xFF byte
    string exercises all five; this must not raise regardless."""
    m.decode_susb_text(bytes(range(256)))  # must not raise


def test_read_table_txt_branch_does_not_crash_on_a_windows_1252_smart_quote():
    """Regression pin for defect 1: the brief's plain pl.read_csv(io.BytesIO(content),
    infer_schema_length=0) raises polars.exceptions.ComputeError on this exact byte shape."""
    csv_bytes = "STATE,NAICS,ENTRSIZE\n01,113310,01\n".encode("cp1252") + (
        "00,--,01  # Men’s Apparel note\n".encode("cp1252")
    )
    df = m.read_table("us_state_naics_detailedsizes_2022.txt", csv_bytes)
    assert df.height == 2


def test_read_table_txt_branch_keeps_state_as_a_zero_padded_string():
    """infer_schema_length=0 keeps every column Utf8 -- a numeric inference would turn "01"
    into the integer 1 and silently break every STATES_DC_FIPS string-equality/is_in check
    downstream."""
    csv_bytes = b"STATE,NAICS,ENTRSIZE\n01,113310,01\n"
    df = m.read_table("us_state_6digitnaics_2022.txt", csv_bytes)
    assert df["STATE"].to_list() == ["01"]
    assert df.schema["STATE"] == pl.Utf8


# --- find_column -----------------------------------------------------------------------------


def test_find_column_size_finds_entrsize_on_the_real_column_list():
    """The brief's size-column regex (enterprise|establishment).*size|empl?size never matches
    ENTRSIZE (defect 2) -- this plain (?i)size search does."""
    assert m.find_column(SUSB_REAL_COLUMNS, r"(?i)size") == "ENTRSIZE"


def test_find_column_naics_finds_naics_not_naicsdscr():
    assert m.find_column(SUSB_REAL_COLUMNS, r"(?i)naics") == "NAICS"


def test_find_column_geo_finds_state_not_statedscr():
    assert m.find_column(SUSB_REAL_COLUMNS, r"(?i)state|geo") == "STATE"


def test_find_column_prefers_the_code_column_even_when_dscr_appears_first():
    """Column-order independence: the preference for a non-DSCR column must not be an accident
    of STATE/NAICS/ENTRSIZE happening to precede their *DSCR twins in SUSB's real header."""
    cols = ["ENTRSIZEDSCR", "ENTRSIZE"]
    assert m.find_column(cols, r"(?i)size") == "ENTRSIZE"


def test_find_column_falls_back_to_the_dscr_column_when_it_is_the_only_match():
    assert m.find_column(["ENTRSIZEDSCR"], r"(?i)size") == "ENTRSIZEDSCR"


def test_find_column_returns_none_when_nothing_matches():
    assert m.find_column(SUSB_REAL_COLUMNS, r"(?i)zzz_nonexistent") is None


# --- code_lengths ------------------------------------------------------------------------------


def test_code_lengths_excludes_the_all_industries_aggregate_placeholder():
    """"--" (the all-industries aggregate) dash-strips to the empty string; its length (0) must
    not appear in a field describing real NAICS code granularity."""
    df = pl.DataFrame({"NAICS": ["--", "11", "1133", "113310"]})
    assert m.code_lengths(df, "NAICS") == [2, 4, 6]


def test_code_lengths_strips_internal_dashes_before_measuring():
    """Confirmed live: us_state_naics_detailedsizes_2022.txt spells a combined-sector code as
    "31-33" at the national level -- must count as length 4 (3133), not 5."""
    df = pl.DataFrame({"NAICS": ["31-33", "44-45"]})
    assert m.code_lengths(df, "NAICS") == [4]


def test_code_lengths_returns_empty_list_when_no_naics_column():
    df = pl.DataFrame({"STATE": ["00", "01"]})
    assert m.code_lengths(df, None) == []


def test_code_lengths_all_aggregate_rows_yields_empty_list_not_a_phantom_zero():
    df = pl.DataFrame({"NAICS": ["--", "--"]})
    assert m.code_lengths(df, "NAICS") == []


# --- state_scope ---------------------------------------------------------------------------------


def test_state_scope_excludes_the_national_total_row():
    df = pl.DataFrame({"STATE": ["00", "01", "02"], "NAICS": ["113310", "11", "11"]})
    scoped = m.state_scope(df, geo_col="STATE", state_fips=("01", "02"))
    assert sorted(scoped["STATE"].to_list()) == ["01", "02"]


def test_state_scope_raises_when_geo_col_is_none():
    df = pl.DataFrame({"NAICS": ["113310"]})
    try:
        m.state_scope(df, geo_col=None, state_fips=("01",))
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "no geography column" in str(exc)


def test_state_scope_raises_on_a_geography_type_mismatch_not_a_silent_empty_frame():
    """The live hazard this pins: if a geography column ever lost its leading zero to numeric
    inference, STATE "01" arrives as the integer 1 -- and pl.lit(1).cast(pl.Utf8) yields "1",
    not "01", so is_in(STATES_DC_FIPS) (string "01"/"02") still matches zero rows even after
    state_scope's own cast(pl.Utf8). The cast does not save this case; the raise does. This
    fixture is genuinely Int64 (not a string column holding "00"), which is what actually
    exercises the type-mismatch failure mode rather than a same-typed all-national frame."""
    df = pl.DataFrame({"STATE": [0, 1, 2], "NAICS": ["113310", "11", "11"]})
    try:
        m.state_scope(df, geo_col="STATE", state_fips=("01", "02"))
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "matched zero rows" in str(exc)


# --- has_target_industry -------------------------------------------------------------------------


def test_has_target_industry_true_when_present():
    df = pl.DataFrame({"NAICS": ["11", "113310"]})
    assert m.has_target_industry(df, naics_col="NAICS", target="113310") is True


def test_has_target_industry_false_when_absent():
    df = pl.DataFrame({"NAICS": ["11", "1133"]})
    assert m.has_target_industry(df, naics_col="NAICS", target="113310") is False


def test_has_target_industry_false_when_no_naics_column_not_a_crash():
    df = pl.DataFrame({"STATE": ["01"]})
    assert m.has_target_industry(df, naics_col=None, target="113310") is False


def test_has_target_industry_strips_dashes_before_comparing():
    df = pl.DataFrame({"NAICS": ["31-33"]})
    assert m.has_target_industry(df, naics_col="NAICS", target="3133") is True


# --- describe_layout: the central asymmetry (defect 3) --------------------------------------------


def test_describe_layout_detailedsizes_shaped_has_no_state_level_six_digit_reach():
    """Reproduces the real, live-confirmed finding: detailedsizes carries 113310 only at the
    national row, so has_113310_at_state must be False even though the file-wide NAICS column
    plainly contains 113310 somewhere."""
    layout = m.describe_layout(
        detailedsizes_shaped_df(), state_fips=("01", "02"), target_industry="113310"
    )
    assert layout["has_113310_at_state"] is False


def test_describe_layout_detailedsizes_shaped_reaches_six_digit_file_wide_but_not_at_state():
    layout = m.describe_layout(
        detailedsizes_shaped_df(), state_fips=("01", "02"), target_industry="113310"
    )
    assert 6 in layout["industry_code_lengths"]
    assert 6 not in layout["industry_code_lengths_at_state"]


def test_describe_layout_sixdigit_shaped_has_state_level_six_digit_reach():
    """The other half of the asymmetry, through the same describe_layout code path: a file
    that genuinely does publish the target industry at the state level must report True."""
    layout = m.describe_layout(
        sixdigit_shaped_df(), state_fips=("01", "02"), target_industry="113310"
    )
    assert layout["has_113310_at_state"] is True
    assert 6 in layout["industry_code_lengths_at_state"]


def test_describe_layout_reports_the_detected_size_and_naics_columns():
    layout = m.describe_layout(
        sixdigit_shaped_df(), state_fips=("01", "02"), target_industry="113310"
    )
    assert layout["size_column"] == "ENTRSIZE"
    assert layout["columns"] == list(sixdigit_shaped_df().columns)
    assert layout["row_count"] == 4


def test_describe_layout_geography_levels_are_not_truncated():
    """The truncation ruling (see describe_layout's docstring): the brief capped
    geography_levels at 10; a fixture with more than 10 distinct geography codes must still
    report every one of them."""
    df = pl.DataFrame({
        "STATE": [f"{i:02d}" for i in range(1, 13)],
        "NAICS": ["11"] * 12,
        "ENTRSIZE": ["01"] * 12,
    })
    layout = m.describe_layout(df, state_fips=tuple(f"{i:02d}" for i in range(1, 13)),
                                target_industry="113310")
    assert len(layout["geography_levels"]) == 12


# --- field_description -------------------------------------------------------------------------


def test_field_description_isolates_the_entrsize_block_without_firm_or_estb():
    desc = m.field_description(RECORD_LAYOUT_EXCERPT, "ENTRSIZE")
    assert "Enterprise Employment Size Code" in desc
    assert "Number of Firms" not in desc
    assert "Number of Establishments" not in desc


def test_field_description_isolates_the_estb_block_without_entrsize():
    desc = m.field_description(RECORD_LAYOUT_EXCERPT, "ESTB")
    assert "Number of Establishments" in desc
    assert "Enterprise" not in desc


def test_field_description_returns_empty_string_for_an_undocumented_field():
    assert m.field_description(RECORD_LAYOUT_EXCERPT, "NOPE_NOT_A_FIELD") == ""


def test_field_description_does_not_match_a_field_name_that_is_a_strict_prefix():
    """"STAT" is a strict prefix of the real field "STATE" -- the trailing \\b in the match
    pattern must reject it: STATE's own line is "STATE\\tC...", so "STAT" immediately followed
    by "E" is not a word boundary, and the shorter string must not count as a match."""
    assert m.field_description(RECORD_LAYOUT_EXCERPT, "STAT") == ""


def test_field_description_does_not_match_a_field_name_appearing_mid_line():
    """"Enterprise" appears inside ENTRSIZE's own description line ("ENTRSIZE\\tC\\tEnterprise
    Employment Size Code"), but not at the START of that line -- a field name that merely
    occurs somewhere in the document must not be treated as a match; only a line that BEGINS
    with the field name counts (the ^ anchor, not just \\b)."""
    assert m.field_description(RECORD_LAYOUT_EXCERPT, "Enterprise") == ""


# --- classify_size_concept ------------------------------------------------------------------------


def test_classify_size_concept_enterprise_only_is_enterprise():
    assert m.classify_size_concept("Enterprise Employment Size Code") == "enterprise"


def test_classify_size_concept_establishment_only_is_establishment():
    assert m.classify_size_concept("Establishment Employment Size Code") == "establishment"


def test_classify_size_concept_neither_word_is_unclear():
    assert m.classify_size_concept("Number of Firms") == "unclear"


def test_classify_size_concept_both_words_is_unclear():
    """Deliberately fails safe rather than guessing which of two co-occurring words is the
    real concept."""
    assert m.classify_size_concept("Enterprise data include establishment-level detail") == (
        "unclear"
    )


def test_classify_size_concept_on_the_whole_document_is_unclear_not_enterprise():
    """The discriminating test for defect 2/INV-010: the WHOLE record layout excerpt contains
    both "enterprise" (ENTRSIZE's block) and "establishment" (ESTB's "Number of
    Establishments"). Classifying the whole document rather than one field's isolated block
    would always return "unclear" regardless of the real, resolvable answer -- this is exactly
    why resolve_size_concept isolates a block with field_description first."""
    assert m.classify_size_concept(RECORD_LAYOUT_EXCERPT) == "unclear"


# --- resolve_size_concept -----------------------------------------------------------------------


def _layout_with_size_column(col: str | None) -> dict:
    return {"size_column": col}


def test_resolve_size_concept_reads_enterprise_from_the_real_record_layout_text():
    result = m.resolve_size_concept(
        RECORD_LAYOUT_EXCERPT,
        _layout_with_size_column("ENTRSIZE"),
        _layout_with_size_column("ENTRSIZE"),
    )
    assert result["value"] == "enterprise"
    assert result["column"] == "ENTRSIZE"
    assert "Enterprise Employment Size Code" in result["note"]


def test_resolve_size_concept_records_evidence_even_though_it_is_not_unclear():
    """The dispatch's ruling: prefer recording the deciding evidence whichever way the concept
    resolves, not only when it lands on "unclear"."""
    result = m.resolve_size_concept(
        RECORD_LAYOUT_EXCERPT,
        _layout_with_size_column("ENTRSIZE"),
        _layout_with_size_column("ENTRSIZE"),
    )
    assert result["note"]


def test_resolve_size_concept_disagreeing_columns_is_unclear_with_a_note():
    result = m.resolve_size_concept(
        RECORD_LAYOUT_EXCERPT,
        _layout_with_size_column("ENTRSIZE"),
        _layout_with_size_column("ESTABSIZE"),
    )
    assert result["value"] == "unclear"
    assert result["column"] is None
    assert "disagree" in result["note"]


def test_resolve_size_concept_no_size_column_detected_anywhere_is_unclear():
    result = m.resolve_size_concept(
        RECORD_LAYOUT_EXCERPT, _layout_with_size_column(None), _layout_with_size_column(None)
    )
    assert result["value"] == "unclear"
    assert result["column"] is None


def test_resolve_size_concept_column_not_in_the_record_layout_document_is_unclear():
    result = m.resolve_size_concept(
        RECORD_LAYOUT_EXCERPT,
        _layout_with_size_column("NOT_A_REAL_FIELD"),
        _layout_with_size_column("NOT_A_REAL_FIELD"),
    )
    assert result["value"] == "unclear"
    assert "does not appear" in result["note"]


def test_resolve_size_concept_would_read_establishment_for_a_hypothetical_establishment_column():
    """Confirms the classifier is not hardcoded to "enterprise" -- a differently-named,
    differently-worded field would resolve the other way."""
    doc = RECORD_LAYOUT_EXCERPT + "\nESTABSIZE\tC\tEstablishment Employment Size Code\n"
    result = m.resolve_size_concept(
        doc, _layout_with_size_column("ESTABSIZE"), _layout_with_size_column("ESTABSIZE")
    )
    assert result["value"] == "establishment"


# --- compose_retention_rule ----------------------------------------------------------------------


def test_compose_retention_rule_counts_extracts():
    rule = m.compose_retention_rule([200, 200, 200])
    assert rule["extracts_recorded"] == 3
    assert rule["extracts_with_non_200_status"] == 0
    assert rule["non_200_statuses_recorded"] == []


def test_compose_retention_rule_states_why_no_repeated_probe_is_needed():
    rule = m.compose_retention_rule([200])
    assert "no repeated multi-candidate" in rule["rule"]


def test_compose_retention_rule_discloses_that_a_failure_aborts_the_run():
    rule = m.compose_retention_rule([200])
    assert "aborts this run" in rule["rule"]


def test_compose_retention_rule_zero_non_200_count_is_not_claimed_as_impossibility():
    rule = m.compose_retention_rule([200, 200])
    assert "not evidence" in rule["rule"]
