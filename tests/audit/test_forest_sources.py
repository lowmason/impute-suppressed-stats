"""Judgment-logic coverage for `forest_sources`, pinned before the live FIA/TPO probes run.

The brief's illustrative code inherits a `not_obtainable` verdict for TPO from a prior review's
inability to find a raw URL, and hardcodes a regex whitelist of FIADB-API `/fullreport`
parameter names (`wc|snum|sdenom|rselected|cselected|outputFormat|schemaName|whereClause`) for
`doc_parameters`. Both are wrong, verified against the live pages during this task's
investigation, not from memory:

- `schemaName` and `whereClause` do not appear anywhere on the live `/fiadb-api/` doc page
  (grepped: zero hits) -- they are not real parameters of this API.
- The doc page's own `<table title="Parameter descriptions">` documents 19 real parameters;
  the brief's whitelist names only 6 of them and misses 13 (`lat`, `lon`, `radius`,
  `pselected`, `rtime`, `ctime`, `ptime`, `strFilter`, `wf`, `wnum`, `wnumdenom`, `estOnly`,
  `FIAorRPA`).
- The brief's own `/fullreport` probe (`params={"outputFormat": "JSON"}`) omits every
  parameter the doc page marks required (`wc*`, `snum*`, `rselected*`, `cselected*`) and gets
  back a 200 status EVALIDator *error* page ("Received an Error: can only join an iterable"),
  not a report -- a 200 that is not usable data, exactly the outcome-1/outcome-3 distinction
  the dispatch requires this script keep visible.
- TPO *is* reachable: `research.fs.usda.gov/programs/nrum` links to a
  `national-resource-use-monitoring-data-downloads` page (not in the brief's candidate list),
  which links to a public Box folder. Box's modern share URL and its embedded
  `authenticated_download_url` both require a browser session (200 HTML app shell / 401
  respectively), but Box's legacy `index.php?rm=box_download_shared_file` redirect -- found by
  reading the share page's own JS bundle, not documented anywhere -- returns the raw file. A
  real per-state-year workbook fetched this way (Ohio, 2021) has sheets `County Production`,
  `State Production`, `Regional Production` (harvest origin) *and* `Receipts`, `Mill Locations`
  (mill receipts) in the same workbook, as distinct sheets -- direct evidence for SRC-FOR-001.

`forest_sources` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is
inert: the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import pytest

import forest_sources as m

# --- classify_probe ---------------------------------------------------------------------


def test_classify_probe_zero_status_is_transport_failure():
    # `_common.probe`'s `(0, 0)` sentinel: no response reached us at all. Reproduced live
    # against `apps.fs.usda.gov/fia/datamart/CSV/` this session -- three independent attempts,
    # 3 s apart, all `(0, 0)` -- while `/fiadb-api/` on the same host answered 200 throughout.
    assert m.classify_probe(0, 0) == "transport_failure"


def test_classify_probe_404_is_not_found():
    assert m.classify_probe(404, 4177) == "not_found"


def test_classify_probe_200_is_reachable():
    assert m.classify_probe(200, 27844) == "reachable"


def test_classify_probe_other_status_is_labelled_distinctly():
    # 403 (EVALIDator legacy path, reproduced live this session) must not collapse into either
    # of the two categories above -- it is neither "no response" nor "the resource is absent".
    assert m.classify_probe(403, 914) == "other_status"
    assert m.classify_probe(403, 914) != m.classify_probe(404, 4177)
    assert m.classify_probe(403, 914) != m.classify_probe(0, 0)


# --- is_machine_readable -----------------------------------------------------------------


def test_html_content_type_is_not_machine_readable():
    assert not m.is_machine_readable("text/html; charset=utf-8")


def test_json_content_type_is_machine_readable():
    assert m.is_machine_readable("application/json")


def test_xlsx_office_content_type_is_machine_readable():
    # The real content-type Box served for Ohio_2021.xlsx this session -- "spreadsheet" is a
    # substring of "spreadsheetml", so this must match without a dedicated xlsx branch.
    ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert m.is_machine_readable(ctype)


def test_docx_content_type_is_not_machine_readable_as_data():
    # The real content-type for the NRUM data dictionary (a Word doc, not a data file).
    ctype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert not m.is_machine_readable(ctype)


def test_empty_content_type_is_not_machine_readable():
    assert not m.is_machine_readable("")


# --- parse_fia_doc_parameters -------------------------------------------------------------

# Verbatim excerpt of the live `/fiadb-api/` doc page's `<table title="Parameter
# descriptions">`, fetched during this task's investigation -- three of the 19 real rows,
# including one FOR-CIRCULAR-ESTIMATES-ONLY row (`lat*`) whose asterisk is conditional, not a
# blanket requirement, and the two-line `wc*` row that also carries a nested link.
FIA_DOC_EXCERPT = """
<html><body>
<h3>Parameter Descriptions</h3>
<table title="Parameter descriptions">
    <tbody>
    <tr>
        <th scope="row"><strong>lat*</strong></th>
        <td><strong> FOR CIRCULAR ESTIMATES ONLY * - Otherwise not required</strong><br>
            The latitude in decimal degrees for a circular estimate centroid
        </td>
    </tr>
    <tr>
        <th scope="row"><strong>wc*</strong></th>
        <td>Evaluation group code(s) for inventory(ies) of interest. <br>
            Typically consists of the state FIPS code concatenated with the 4 digit inventory
            year. <br>
            Valid values can be found in the "EVALID" column here: <a
                    class="full-report-link"
                    data-link="/fullreport/parameters/wc"
                    target="_blank"
                    rel="noopener"
                >/fullreport/parameters/wc</a>
        </td>
    </tr>
    <tr>
        <th scope="row"><strong>pselected</strong></th>
        <td>Page estimate grouping definition, translates to pages in traditional EVALIDator
            table format.
        </td>
    </tr>
    </tbody>
</table>
</body></html>
"""


def test_parse_fia_doc_parameters_reads_every_row():
    params = m.parse_fia_doc_parameters(FIA_DOC_EXCERPT)
    assert [p["parameter"] for p in params] == ["lat", "wc", "pselected"]


def test_parse_fia_doc_parameters_strips_the_asterisk_from_the_name():
    params = m.parse_fia_doc_parameters(FIA_DOC_EXCERPT)
    wc = next(p for p in params if p["parameter"] == "wc")
    assert "*" not in wc["parameter"]


def test_parse_fia_doc_parameters_flags_required_from_the_trailing_asterisk():
    params = m.parse_fia_doc_parameters(FIA_DOC_EXCERPT)
    by_name = {p["parameter"]: p for p in params}
    assert by_name["wc"]["required"] is True
    assert by_name["pselected"]["required"] is False


def test_parse_fia_doc_parameters_collapses_nested_markup_and_whitespace_in_the_description():
    params = m.parse_fia_doc_parameters(FIA_DOC_EXCERPT)
    wc = next(p for p in params if p["parameter"] == "wc")
    assert "<a" not in wc["description"]
    assert "  " not in wc["description"]
    assert "Evaluation group code(s) for inventory(ies) of interest." in wc["description"]


def test_parse_fia_doc_parameters_returns_empty_list_when_table_is_absent():
    assert m.parse_fia_doc_parameters("<html><body>no table here</body></html>") == []


def test_parse_fia_doc_parameters_never_invents_a_name_the_table_does_not_contain():
    # The defect this function structurally cannot repeat: the brief's hardcoded whitelist
    # named `schemaName` and `whereClause`, neither of which appears on the live page.
    params = m.parse_fia_doc_parameters(FIA_DOC_EXCERPT)
    names = {p["parameter"] for p in params}
    assert "schemaName" not in names
    assert "whereClause" not in names


# --- sampling_error_field / evaluation_vintage_field --------------------------------------

# Trimmed from the real `/fullreport` JSON response this session (wc=102020, snum=79,
# rselected="Land Use - Major", cselected="Land use", outputFormat=NJSON -- the doc page's own
# documented Python-GET example).
REAL_ESTIMATE_ROW = {
    "ESTIMATE": 338396.7231259111,
    "GRP1": "`0001 Timberland",
    "GRP2": "`0001 Timberland",
    "PLOT_COUNT": 126,
    "SE": 14124.919149564656,
    "SE_PERCENT": 4.174070900890206,
    "VARIANCE": 199513340.98173833,
}
REAL_METADATA = {
    "FIAorRPA": "FIADEF",
    "dataRetrieved": True,
    "dbVersion": "FIADB_1.9.4.00",
    "evalGrps": ["Delaware 102020"],
    "stateCd": "10",
}


def test_sampling_error_field_finds_se_in_the_real_response():
    assert m.sampling_error_field([REAL_ESTIMATE_ROW]) == "SE"


def test_sampling_error_field_is_none_for_empty_estimates():
    assert m.sampling_error_field([]) is None


def test_sampling_error_field_is_none_when_no_candidate_key_present():
    assert m.sampling_error_field([{"ESTIMATE": 1.0, "GRP1": "x"}]) is None


def test_evaluation_vintage_field_finds_evalgrps_in_the_real_response():
    # Not "EVALID" -- the brief's candidate list (`EVALID|evalid|EVAL_GRP|INVYR|SURVEY_CYCLE`)
    # would have missed this: the live response's actual metadata key is `evalGrps`, verified
    # by fetching and inspecting the real JSON this session, not assumed from documentation.
    assert m.evaluation_vintage_field(REAL_METADATA) == "evalGrps"


def test_evaluation_vintage_field_is_none_for_empty_metadata():
    assert m.evaluation_vintage_field({}) is None


def test_evaluation_vintage_field_is_none_when_no_candidate_key_present():
    assert m.evaluation_vintage_field({"dbVersion": "x"}) is None


# --- parse_wc_evaluation_index -------------------------------------------------------------

# Verbatim excerpt of the live `/fullreport/parameters/wc` page fetched this session. Note:
# every row opens with `<th scope=row ...>`, never `<tr>` -- the live page has 1139 `</tr>`
# closers and zero `<tr>` openers (grepped directly), so a row-recovery approach that requires
# a matching `<tr>...</tr>` pair would silently find nothing, which is exactly the failure mode
# `test_parse_wc_evaluation_index_recovers_rows_with_no_tr_opener` below pins.
WC_TABLE_EXCERPT = """
<table border="1" aria-label="wc table" class="dataframe table-wrapper">
  <thead>
    <tr><th scope="col">STATE</th><th scope="col">STATECD</th><th scope="col">EVALID</th>
    <th scope="col">EVAL_GRP</th><th scope="col">REPORT_YEAR_NM</th>
    <th scope="col">GROWTH_ACCT</th><th scope="col">INVENTORY</th>
    <th scope="col">MOST_RECENT</th></tr>
  </thead>
  <tbody>
      <th scope=row style='font-size:16px; text-align:left'>Alabama</td>
      <td>1</td>
      <td>012025 ALABAMA</td>
      <td>12025</td>
      <td>2016;2017;2018;2019;2020;2021;2022;2023;2024;2025</td>
      <td>Y</td>
      <td>012025Y ALABAMA 2016;2017;2018;2019;2020;2021;2022;2023;2024;2025</td>
      <td>Y</td>
    </tr>
      <th scope=row style='font-size:16px; text-align:left'>Alaska</td>
      <td>2</td>
      <td>022019 ALASKA</td>
      <td>22019</td>
      <td>2004;2005;2006;2007;2008;2009;2010;2011</td>
      <td>N</td>
      <td>022019N ALASKA 2004;2005;2006;2007;2008;2009;2010;2011</td>
      <td>N</td>
    </tr>
  </tbody>
</table>
"""


def test_parse_wc_evaluation_index_recovers_rows_with_no_tr_opener():
    index = m.parse_wc_evaluation_index(WC_TABLE_EXCERPT)
    assert index["row_count"] == 2


def test_parse_wc_evaluation_index_collects_distinct_states():
    index = m.parse_wc_evaluation_index(WC_TABLE_EXCERPT)
    assert index["states"] == ["Alabama", "Alaska"]


def test_parse_wc_evaluation_index_computes_year_span_from_report_year_nm():
    index = m.parse_wc_evaluation_index(WC_TABLE_EXCERPT)
    assert index["year_min"] == 2004
    assert index["year_max"] == 2025


def test_parse_wc_evaluation_index_on_absent_table_returns_empty_result():
    index = m.parse_wc_evaluation_index("<html><body>nothing here</body></html>")
    assert index == {"states": [], "year_min": None, "year_max": None, "row_count": 0}


def test_parse_wc_evaluation_index_district_of_columbia_absent_from_real_excerpt():
    # Verified live this session: "District of Columbia" does not appear anywhere in the
    # 344 KB `/fullreport/parameters/wc` response (grepped directly) -- FIA has no
    # state-level evaluation for D.C., unlike QCEW's states_dc universe.
    index = m.parse_wc_evaluation_index(WC_TABLE_EXCERPT)
    assert "District of Columbia" not in index["states"]


# --- extract_json_object -----------------------------------------------------------------


def test_extract_json_object_returns_the_balanced_object():
    text = 'Box.postStreamData = {"a": 1, "b": {"c": 2}};  more script here'
    assert m.extract_json_object(text, "Box.postStreamData = ") == '{"a": 1, "b": {"c": 2}}'


def test_extract_json_object_does_not_stop_at_a_brace_inside_a_string():
    # A naive scan that ignores string context would stop at the `}` inside the string value,
    # truncating the object before the trailing `"tail":true}` -- exactly the failure mode a
    # brace-count-only extractor would hit against Box's real page, whose payload can carry
    # literal `{`/`}` inside string values (e.g. SQL fragments, JS templates).
    text = 'Box.postStreamData = {"note": "contains a } brace", "tail": true};'
    result = m.extract_json_object(text, "Box.postStreamData = ")
    assert result == '{"note": "contains a } brace", "tail": true}'


def test_extract_json_object_handles_an_escaped_quote_inside_a_string():
    text = r'Box.postStreamData = {"note": "a \" quote", "n": 1};'
    result = m.extract_json_object(text, "Box.postStreamData = ")
    assert result == r'{"note": "a \" quote", "n": 1}'


def test_extract_json_object_raises_when_marker_is_absent():
    with pytest.raises(ValueError, match="not found"):
        m.extract_json_object("no marker in this text", "Box.postStreamData = ")


def test_extract_json_object_raises_when_braces_never_balance():
    with pytest.raises(ValueError, match="unbalanced"):
        m.extract_json_object('Box.postStreamData = {"a": 1', "Box.postStreamData = ")


# --- box_shared_folder_items --------------------------------------------------------------


def _box_page(payload: str) -> str:
    return (
        "<html><head><script> Box.config = {\"unrelated\": {}};"
        f" Box.postStreamData = {payload};"
        " Box.otherThing = {\"also\": \"unrelated\"};</script></head></html>"
    )


def test_box_shared_folder_items_returns_the_shared_folder_payload():
    payload = (
        '{"/app-api/enduserapp/shared-item":{"sharedName":"abc123"},'
        '"/app-api/enduserapp/shared-folder":{"currentFolderName":"NRUM Data",'
        '"currentFolderID":121486946349,"items":[{"type":"folder","id":1,"name":"2021"}]}}'
    )
    folder = m.box_shared_folder_items(_box_page(payload))
    assert folder["currentFolderName"] == "NRUM Data"
    assert folder["items"][0]["name"] == "2021"


# --- discover_box_share_url -----------------------------------------------------------------

# The real href from the live NRUM data-downloads page fetched this session, embedded in a
# realistic amount of surrounding unrelated markup (nav links, asset hrefs).
NRUM_DOWNLOADS_PAGE_EXCERPT = """
<html><body>
<a href="/products/dataandtools/patents">Patents</a>
<a href="https://www.facebook.com/fsresearch">Facebook</a>
<p>Online Resources</p>
<a href="https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id">
NRUM Data Downloads (External Folder)</a>
<a href="https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id/file/765951213652">
NRUM Data Download Dictionary</a>
</body></html>
"""


def test_discover_box_share_url_finds_the_real_share_link():
    url = m.discover_box_share_url(NRUM_DOWNLOADS_PAGE_EXCERPT)
    assert url == "https://usfs-public.app.box.com/s/y4ziirdb9v7zardus0cuajh7ziy9b2id"


def test_discover_box_share_url_ignores_a_deeper_file_link_and_takes_the_first_match():
    # The first href in the fetched page is the bare folder share, not the dictionary file
    # deep-link -- both match the box.com/s/ pattern, so order matters and is pinned here.
    url = m.discover_box_share_url(NRUM_DOWNLOADS_PAGE_EXCERPT)
    assert "/file/" not in url


def test_discover_box_share_url_returns_none_when_absent():
    assert m.discover_box_share_url("<html><body>no box link here</body></html>") is None


def test_box_shared_folder_items_raises_when_shared_folder_key_is_absent():
    payload = '{"/app-api/enduserapp/shared-item":{"sharedName":"abc123"}}'
    with pytest.raises(ValueError, match="shared-folder"):
        m.box_shared_folder_items(_box_page(payload))


# --- box_legacy_download_url ---------------------------------------------------------------


def test_box_legacy_download_url_matches_the_verified_working_pattern():
    # Verified live this session: this exact URL shape, GET'ed directly (no session, no
    # cookies), returned a real 21,360-byte "Microsoft Excel 2007+" xlsx body with status 200.
    url = m.box_legacy_download_url("y4ziirdb9v7zardus0cuajh7ziy9b2id", 944786629777)
    assert url == (
        "https://usfs-public.app.box.com/index.php?rm=box_download_shared_file"
        "&shared_name=y4ziirdb9v7zardus0cuajh7ziy9b2id&file_id=f_944786629777"
    )


# --- select_latest_window_year_folder / select_first_file ----------------------------------

WINDOW_YEARS = tuple(range(2017, 2025))


def test_select_latest_window_year_folder_picks_the_max_in_window():
    items = [
        {"type": "folder", "name": "2015"},
        {"type": "folder", "name": "2021"},
        {"type": "folder", "name": "2024"},
        {"type": "file", "name": "2024"},  # a same-named file must not be picked
    ]
    chosen = m.select_latest_window_year_folder(items, WINDOW_YEARS)
    assert chosen == {"type": "folder", "name": "2024"}


def test_select_latest_window_year_folder_ignores_years_outside_the_window():
    items = [{"type": "folder", "name": "2015"}, {"type": "folder", "name": "1997"}]
    assert m.select_latest_window_year_folder(items, WINDOW_YEARS) is None


def test_select_latest_window_year_folder_ignores_non_numeric_folder_names():
    items = [{"type": "folder", "name": "NRUM Data"}, {"type": "folder", "name": "2020"}]
    chosen = m.select_latest_window_year_folder(items, WINDOW_YEARS)
    assert chosen["name"] == "2020"


def test_select_latest_window_year_folder_on_empty_items_returns_none():
    assert m.select_latest_window_year_folder([], WINDOW_YEARS) is None


def test_select_first_file_sorts_alphabetically_and_skips_folders():
    items = [
        {"type": "folder", "name": "Alabama"},
        {"type": "file", "name": "Wisconsin_2021.xlsx"},
        {"type": "file", "name": "Ohio_2021.xlsx"},
    ]
    assert m.select_first_file(items) == {"type": "file", "name": "Ohio_2021.xlsx"}


def test_select_first_file_on_no_files_returns_none():
    assert m.select_first_file([{"type": "folder", "name": "2021"}]) is None


# --- xlsx_sheet_names / xlsx_shared_strings / xlsx_header_row ------------------------------

# Modeled on the real internal XML of Ohio_2021.xlsx, fetched via the legacy Box download
# route this session -- trimmed to the two relevant sheet entries and three shared strings.
WORKBOOK_XML = (
    '<?xml version="1.0"?><workbook><sheets>'
    '<sheet name="County Production" sheetId="1" r:id="rId1"/>'
    '<sheet name="Receipts" sheetId="3" r:id="rId3"/>'
    "</sheets></workbook>"
)
SHARED_STRINGS_XML = (
    '<?xml version="1.0"?><sst count="3" uniqueCount="3">'
    "<si><t>REGION</t></si><si><t>STATECD</t></si><si><t>COUNTY_NAME</t></si></sst>"
)
SHEET1_XML = (
    '<?xml version="1.0"?><worksheet><sheetData>'
    '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
    '<c r="C1" t="s"><v>2</v></c></row>'
    '<row r="2"><c r="A2" t="s"><v>0</v></c></row>'
    "</sheetData></worksheet>"
)


def test_xlsx_sheet_names_reads_names_in_order():
    assert m.xlsx_sheet_names(WORKBOOK_XML) == ["County Production", "Receipts"]


def test_xlsx_shared_strings_reads_strings_in_index_order():
    assert m.xlsx_shared_strings(SHARED_STRINGS_XML) == ["REGION", "STATECD", "COUNTY_NAME"]


def test_xlsx_header_row_resolves_row_one_string_cells_via_shared_strings():
    shared = m.xlsx_shared_strings(SHARED_STRINGS_XML)
    assert m.xlsx_header_row(SHEET1_XML, shared) == ["REGION", "STATECD", "COUNTY_NAME"]


def test_xlsx_header_row_does_not_read_past_row_one():
    shared = m.xlsx_shared_strings(SHARED_STRINGS_XML)
    header = m.xlsx_header_row(SHEET1_XML, shared)
    assert len(header) == 3  # row 2's single cell must not leak in


def test_xlsx_header_row_on_missing_row_one_returns_empty_list():
    empty_sheet = '<worksheet><sheetData><row r="2"><c r="A2"/></row></sheetData></worksheet>'
    assert m.xlsx_header_row(empty_sheet, []) == []


# --- distinguishes_harvest_origin_from_mill_receipts ---------------------------------------

# The real sheet names from Ohio_2021.xlsx, fetched via the legacy Box download route this
# session and inspected directly with `zipfile` (no new dependency: xlsx is a zip container).
REAL_TPO_SHEET_NAMES = [
    "County Production", "State Production", "Receipts", "Wood Movement-IMPORTS",
    "Wood Movement-EXPORTS", "Mill Locations", "Residue Use State", "Regional Production",
]


def test_distinguishes_harvest_origin_from_mill_receipts_on_the_real_workbook():
    assert m.distinguishes_harvest_origin_from_mill_receipts(REAL_TPO_SHEET_NAMES)


def test_distinguishes_harvest_origin_from_mill_receipts_false_without_a_receipts_sheet():
    sheets = [s for s in REAL_TPO_SHEET_NAMES if "Receipt" not in s and "Mill" not in s]
    assert not m.distinguishes_harvest_origin_from_mill_receipts(sheets)


def test_distinguishes_harvest_origin_from_mill_receipts_false_without_a_production_sheet():
    sheets = [s for s in REAL_TPO_SHEET_NAMES if "Production" not in s]
    assert not m.distinguishes_harvest_origin_from_mill_receipts(sheets)


def test_distinguishes_harvest_origin_from_mill_receipts_false_on_empty_list():
    assert not m.distinguishes_harvest_origin_from_mill_receipts([])


# --- probe_with_retries ---------------------------------------------------------------------


def test_probe_with_retries_stops_early_on_first_real_response():
    calls = iter([(0, 0), (200, 500)])
    sleeps = []
    result = m.probe_with_retries(
        lambda: next(calls), url="https://example/x", attempts=5, wait_seconds=3.0,
        sleep=sleeps.append, now=lambda: 0.0,
    )
    assert len(result["attempts"]) == 2
    assert result["attempts"][-1]["outcome"] == "reachable"
    assert sleeps == [3.0]  # slept once, between attempt 1 and attempt 2 -- never after success


def test_probe_with_retries_exhausts_the_bound_when_every_attempt_transport_fails():
    result = m.probe_with_retries(
        lambda: (0, 0), url="https://example/x", attempts=3, wait_seconds=1.0,
        sleep=lambda s: None, now=lambda: 0.0,
    )
    assert len(result["attempts"]) == 3
    assert all(a["outcome"] == "transport_failure" for a in result["attempts"])


def test_probe_with_retries_records_elapsed_seconds_from_the_injected_clock():
    clock = iter([100.0, 107.5])
    result = m.probe_with_retries(
        lambda: (200, 10), url="https://example/x", attempts=3, wait_seconds=1.0,
        sleep=lambda s: None, now=lambda: next(clock),
    )
    assert result["elapsed_seconds"] == 7.5


# --- parse_snum_estimate_attributes --------------------------------------------------------

# Verbatim excerpt of the live `/fullreport/parameters/snum` page fetched this session (the
# ruling D-A probe). Four of its 752 real rows, one per removals-flavoured estimate group plus
# an `Area` row, kept because the four group names are what the harvest/non-harvest predicate
# has to tell apart. Same malformed markup as the `wc` page: every row opens with
# `<th scope=row ...>` and closes with `</td>`, and the tbody emits no `<tr>` opener at all.
SNUM_TABLE_EXCERPT = """
<h1> Parameter Table snum</h1>
<table border="1" aria-label="snum table" class="dataframe table-wrapper">
  <thead>
    <tr style="text-align: left;">
      <th scope="col">ATTRIBUTE_NBR</th><th scope="col">ATTRIBUTE_DESCR</th>
      <th scope="col">CONDTREESEED</th><th scope="col">LAND_BASIS</th>
      <th scope="col">ESTIMATE_GRP_DESCR</th><th scope="col">EVAL_TYP</th>
      <th scope="col">ESTN_TREE_PORTION</th><th scope="col">ESTN_UNITS_ATTRIBUTE</th>
      <th scope="col">ESTN_UNITS_DISPLAY</th><th scope="col">ESTIMATE_GRP_NBR</th>
      <th scope="col">SORT_COL</th>
    </tr>
  </thead>
  <tbody>
      <th scope=row style='font-size:16px; text-align:left'>2</td>
      <td>Area of forest land, in acres</td>
      <td>COND</td><td>Forest land</td><td>Area</td><td>EXPCURR</td><td>None</td>
      <td>ACRES</td><td>acres</td><td>1</td><td>1</td>
    </tr>
      <th scope=row style='font-size:16px; text-align:left'>574159</td>
      <td>Average annual removals of sound bole wood volume of trees, in cubic feet</td>
      <td>PTREE</td><td>Forest land</td><td>Annual removals volume</td><td>EXPREMV</td>
      <td>BOLE_WOOD</td><td>CF</td><td>cubic feet</td><td>22</td><td>1</td>
    </tr>
      <th scope=row style='font-size:16px; text-align:left'>574161</td>
      <td>Average annual harvest removals of sound bole wood volume of trees, in cubic feet</td>
      <td>PTREE</td><td>Forest land</td><td>Annual harvest removals volume</td><td>EXPREMV</td>
      <td>BOLE_WOOD</td><td>CF</td><td>cubic feet</td><td>28</td><td>1</td>
    </tr>
      <th scope=row style='font-size:16px; text-align:left'>574201</td>
      <td>Average annual harvest removals dry weight of trees, in short tons</td>
      <td>PTREE</td><td>Forest land</td><td>Annual harvest removals dry weight</td>
      <td>EXPREMV</td><td>BOLE_WOOD</td><td>DRYBIO</td><td>short tons</td><td>29</td><td>1</td>
    </tr>
      <th scope=row style='font-size:16px; text-align:left'>574163</td>
      <td>Average annual other removals of sound bole wood volume of trees, in cubic feet</td>
      <td>PTREE</td><td>Forest land</td><td>Annual other removals volume</td><td>EXPREMV</td>
      <td>BOLE_WOOD</td><td>CF</td><td>cubic feet</td><td>34</td><td>1</td>
    </tr>
  </tbody>
</table>
"""


def test_parse_snum_estimate_attributes_counts_every_row():
    index = m.parse_snum_estimate_attributes(SNUM_TABLE_EXCERPT)
    assert index["row_count"] == 5


def test_parse_snum_estimate_attributes_groups_the_harvest_removals_attributes():
    index = m.parse_snum_estimate_attributes(SNUM_TABLE_EXCERPT)
    groups = {g["estimate_group"]: g for g in index["harvest_removals_groups"]}
    assert set(groups) == {"Annual harvest removals volume", "Annual harvest removals dry weight"}
    assert groups["Annual harvest removals volume"]["attribute_count"] == 1
    assert groups["Annual harvest removals volume"]["lowest_attribute_nbr"] == "574161"
    assert groups["Annual harvest removals volume"]["eval_typs"] == ["EXPREMV"]
    assert index["harvest_removals_attribute_count"] == 2


def test_parse_snum_estimate_attributes_keeps_other_removals_out_of_the_harvest_set():
    # SS2.2 wants harvest origin. "Annual other removals" is land-use-change/diversion-driven
    # and "Annual removals" is the two combined -- neither is a harvest-origin measure, so a
    # bare `removals` predicate would overstate what the catalog offers.
    index = m.parse_snum_estimate_attributes(SNUM_TABLE_EXCERPT)
    assert index["non_harvest_removals_groups"] == [
        "Annual other removals volume", "Annual removals volume",
    ]
    assert "574159" not in index["harvest_removals_attribute_nbrs"]
    assert "574163" not in index["harvest_removals_attribute_nbrs"]
    assert index["harvest_removals_attribute_nbrs"] == ["574161", "574201"]


def test_parse_snum_estimate_attributes_records_the_eval_typs_present():
    index = m.parse_snum_estimate_attributes(SNUM_TABLE_EXCERPT)
    assert index["eval_typs_present"] == ["EXPCURR", "EXPREMV"]


def test_parse_snum_estimate_attributes_on_absent_table_returns_an_empty_result():
    index = m.parse_snum_estimate_attributes("<html><body>nothing here</body></html>")
    assert index == {
        "row_count": 0, "harvest_removals_groups": [], "harvest_removals_attribute_count": 0,
        "harvest_removals_attribute_nbrs": [], "non_harvest_removals_groups": [],
        "eval_typs_present": [],
    }


# --- count_term_hits ------------------------------------------------------------------------


def test_count_term_hits_sums_word_boundary_matches_across_pages():
    pages = {"a.html": "land use and land use again", "b.json": "one land use here"}
    assert m.count_term_hits(pages, {"land use": r"(?i)\bland use\b"}) == {"land use": 3}


def test_count_term_hits_does_not_match_inside_a_longer_word():
    # The trap this replaces a naive substring scan to avoid: "SIC" occurs inside "BASIC" and
    # "PHYSIOGRAPHIC" in the real /fullreport response body.
    pages = {"probe.json": "BASIC PHYSIOGRAPHIC CLASSIC"}
    assert m.count_term_hits(pages, {"SIC": r"\bSIC\b"}) == {"SIC": 0}


def test_count_term_hits_reports_zero_rather_than_omitting_an_absent_term():
    pages = {"a.html": "forest inventory"}
    hits = m.count_term_hits(pages, {"NAICS": r"(?i)\bNAICS\b", "forest": r"(?i)\bforest\b"})
    assert hits == {"NAICS": 0, "forest": 1}


# --- proved_estimate_measure ------------------------------------------------------------------

# The real `metadata` keys this run's successful /fullreport call returned (trimmed).
REAL_METADATA_WITH_MEASURE = {
    "evalGrps": ["Delaware 102020"],
    "numEstDesc": "0079 Area of sampled land and water, in acres",
    "estMeta": (
        "Area estimate for land and water based on all sampled plots (hazardous and denied "
        "access plots are not included in the estimate).<br>"
    ),
}


def test_proved_estimate_measure_reads_both_metadata_fields():
    measure = m.proved_estimate_measure(REAL_METADATA_WITH_MEASURE)
    assert measure["num_est_desc"] == "0079 Area of sampled land and water, in acres"
    assert measure["est_meta"].startswith("Area estimate for land and water")
    assert "<br>" not in measure["est_meta"]


def test_proved_estimate_measure_extracts_the_attribute_number_snum_selects():
    # `numEstDesc`'s leading token is the zero-padded snum value the request sent (79), which
    # is what makes membership in the harvest-removals attribute set checkable rather than
    # asserted.
    measure = m.proved_estimate_measure(REAL_METADATA_WITH_MEASURE)
    assert measure["attribute_nbr"] == "79"


def test_proved_estimate_measure_is_none_when_metadata_names_no_measure():
    assert m.proved_estimate_measure({}) is None
    assert m.proved_estimate_measure({"dbVersion": "x"}) is None


# --- compose_fia_access -----------------------------------------------------------------------

SNUM_INDEX_WITH_HARVEST = {
    "row_count": 752,
    "harvest_removals_groups": [
        {"estimate_group": "Annual harvest removals dry weight", "attribute_count": 38,
         "lowest_attribute_nbr": "574201", "eval_typs": ["EXPREMV"]},
        {"estimate_group": "Annual harvest removals volume", "attribute_count": 17,
         "lowest_attribute_nbr": "574161", "eval_typs": ["EXPREMV"]},
    ],
    "harvest_removals_attribute_count": 55,
    "harvest_removals_attribute_nbrs": ["574161", "574201"],
    "non_harvest_removals_groups": ["Annual other removals volume", "Annual removals volume"],
    "eval_typs_present": ["EXPCURR", "EXPREMV"],
}
SNUM_INDEX_UNREADABLE = {
    "row_count": 0, "harvest_removals_groups": [], "harvest_removals_attribute_count": 0,
    "harvest_removals_attribute_nbrs": [], "non_harvest_removals_groups": [],
    "eval_typs_present": [],
}
SNUM_INDEX_NO_HARVEST = dict(SNUM_INDEX_WITH_HARVEST) | {
    "harvest_removals_groups": [], "harvest_removals_attribute_count": 0,
    "harvest_removals_attribute_nbrs": [],
}
MEASURE_AREA = {
    "num_est_desc": "0079 Area of sampled land and water, in acres",
    "est_meta": "Area estimate for land and water based on all sampled plots.",
    "attribute_nbr": "79",
}


def _fia_access(**overrides):
    kwargs = {
        "route": "https://apps.fs.usda.gov/fiadb-api/fullreport",
        "doc_params_parsed": True, "real_probe_parsed": True,
        "measure_proved": MEASURE_AREA, "snum_index": SNUM_INDEX_WITH_HARVEST,
    }
    return m.compose_fia_access(**(kwargs | overrides))


def test_compose_fia_access_verified_names_the_measure_actually_proved():
    # Finding 1: the old verified branch persisted `reason: None`, so nothing distinguished
    # "the endpoint returns data" from "the endpoint returns the measure this project needs".
    access = _fia_access()
    assert access["status"] == "verified"
    assert "0079 Area of sampled land and water, in acres" in access["reason"]
    assert "Area estimate for land and water" in access["reason"]


def test_compose_fia_access_verified_states_the_harvest_capability_is_catalogued_not_returned():
    access = _fia_access()
    assert "752" in access["reason"]
    assert "Annual harvest removals volume" in access["reason"]
    assert "not one of those harvest-removals attributes" in access["reason"]


def test_compose_fia_access_verified_says_so_when_the_proved_measure_is_a_harvest_removal():
    access = _fia_access(measure_proved={
        "num_est_desc": "574161 Average annual harvest removals, in cubic feet",
        "est_meta": "Harvest removals estimate.", "attribute_nbr": "574161"})
    assert "not one of those harvest-removals attributes" not in access["reason"]
    assert "is itself one of those harvest-removals attributes" in access["reason"]


def test_compose_fia_access_documented_branch_does_not_claim_the_doc_table_parsed():
    # Finding 2, first bullet: the old else-reason asserted BOTH "its parameter table parsed"
    # AND "the probe did not return a parsable report". When the doc table is what failed,
    # the first clause is false -- two of the three failure modes persisted a false sentence.
    access = _fia_access(doc_params_parsed=False)
    assert access["status"] == "documented"
    assert "did not parse" in access["reason"]
    assert "parameter table parsed" not in access["reason"]


def test_compose_fia_access_documented_branch_does_not_claim_the_probe_failed_when_it_did_not():
    access = _fia_access(doc_params_parsed=False)
    assert "did not return a report" not in access["reason"]
    assert "returned a report with both estimates and metadata" in access["reason"]


def test_compose_fia_access_documented_branch_names_a_failed_probe_without_blaming_the_doc_page():
    access = _fia_access(real_probe_parsed=False)
    assert access["status"] == "documented"
    assert "did not return a report" in access["reason"]
    assert "did not parse" not in access["reason"]


def test_compose_fia_access_is_not_verified_when_the_snum_catalog_could_not_be_read():
    # Ruling D-A: a failed enumeration is itself a finding, and `verified` would overstate a
    # capability nothing this run read.
    access = _fia_access(snum_index=SNUM_INDEX_UNREADABLE)
    assert access["status"] == "documented"
    assert "could not be read this run" in access["reason"]


def test_compose_fia_access_is_not_verified_when_no_harvest_attribute_is_catalogued():
    access = _fia_access(snum_index=SNUM_INDEX_NO_HARVEST)
    assert access["status"] == "documented"
    assert "none of them is a harvest-removals attribute" in access["reason"]


def test_compose_fia_access_reason_is_never_none():
    for kwargs in ({}, {"doc_params_parsed": False}, {"real_probe_parsed": False},
                   {"snum_index": SNUM_INDEX_UNREADABLE},
                   {"snum_index": SNUM_INDEX_NO_HARVEST}, {"measure_proved": None}):
        assert _fia_access(**kwargs)["reason"]


# --- compose_fia_uncovered --------------------------------------------------------------------

INDUSTRY_SCAN = {
    "pages_scanned": ["fiadb_api_doc.html", "snum_estimate_attributes.html"],
    "industry_classification_terms": {"NAICS": 0, "SIC": 0, "industry": 0},
    "fia_taxonomy_terms": {"land use": 2, "product": 52, "species": 282},
}


def test_compose_fia_uncovered_interpolates_the_measured_term_counts():
    # Finding 4: the shipped sentence ("FIA reports by species group, product, and land use,
    # not by industry code") was typed -- zero occurrences of NAICS/industry/species in
    # anything the run fetched. Every number below now comes from this run's own scan.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138)
    assert "NAICS=0" in text
    assert "species=282" in text
    assert "fiadb_api_doc.html" in text


def test_compose_fia_uncovered_delimits_the_unbacked_reading_with_the_marker_convention():
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138)
    assert text.count("INFERENCE MARKER, OPENING") == 1
    assert text.count("INFERENCE MARKER, CLOSING") == 1
    assert text.index("INFERENCE MARKER, OPENING") < text.index("INFERENCE MARKER, CLOSING")
    assert "carries no extract hash" in text


def test_compose_fia_uncovered_keeps_the_derived_dc_clause_outside_the_marked_reading():
    # Sub-trap (b): a marking's scope ends where the reader thinks it does. The D.C. clause is
    # interpolated from the fetched evaluation index and must not sit inside the marker.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138)
    assert "1138-row" in text
    assert text.index("1138-row") > text.index("INFERENCE MARKER, CLOSING")


def test_compose_fia_uncovered_omits_the_dc_clause_when_dc_has_an_evaluation():
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=True, wc_row_count=1138)
    assert "District of Columbia" not in text
    assert "NAICS=0" in text


# --- compose_tpo_access -----------------------------------------------------------------------

BOX_NAV_VERIFIED = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
    "probed_year": "2024",
    "sample_file": "Alabama_2024.xlsx",
    "sample_file_sheet_names": [
        "County Production", "State Production", "Receipts", "Mill Locations",
    ],
}
PROBES_ALL_ANSWERED = [
    {"url": "https://a/1", "outcome": "reachable"},
    {"url": "https://a/2", "outcome": "not_found"},
]
PROBES_WITH_TRANSPORT_FAILURE = PROBES_ALL_ANSWERED + [
    {"url": "https://a/3", "outcome": "transport_failure"},
]


def _tpo_access(**overrides):
    kwargs = {
        "route": "nrum -> box -> legacy download", "harvest_origin_available": True,
        "box_navigation": BOX_NAV_VERIFIED, "probes": PROBES_ALL_ANSWERED,
    }
    return m.compose_tpo_access(**(kwargs | overrides))


def test_compose_tpo_access_verified_marks_the_sheet_name_reading_as_an_inference():
    # Folded-in minor: `harvest_origin_available: true` is a regex match on sheet names from
    # one workbook. The inference that a sheet named "County Production" carries harvest-origin
    # attribution is drawn from a quotation and must be marked.
    access = _tpo_access()
    assert access["status"] == "verified"
    assert access["reason"].count("INFERENCE MARKER, OPENING") == 1
    assert access["reason"].count("INFERENCE MARKER, CLOSING") == 1
    assert "carries no extract hash" in access["reason"]


def test_compose_tpo_access_verified_names_the_one_workbook_the_reading_rests_on():
    access = _tpo_access()
    assert "Alabama_2024.xlsx" in access["reason"]
    assert "County Production" in access["reason"]
    assert "every state-year workbook" in access["reason"]


def test_compose_tpo_access_not_obtainable_without_a_share_url_claims_no_folder_was_entered():
    # Finding 2, second bullet: the shipped reason asserted "no probed route -- including the
    # Box folder discovered this run -- yielded a machine-readable file", which is false when
    # no folder was discovered at all.
    access = _tpo_access(harvest_origin_available=False,
                         box_navigation={"share_url_discovered": None})
    assert access["status"] == "not_obtainable"
    assert "no Box share link" in access["reason"]
    assert "discovered this run" not in access["reason"]


def test_compose_tpo_access_not_obtainable_with_a_share_url_says_the_folder_was_entered():
    access = _tpo_access(harvest_origin_available=False)
    assert "was entered" in access["reason"]
    assert "no Box share link" not in access["reason"]


def test_compose_tpo_access_not_obtainable_names_a_transport_failure_as_the_weakest_basis():
    # Finding 3: a transport failure collapsing into `not_obtainable` is what `classify_probe`'s
    # own docstring calls the weakest possible basis for that verdict; the reason must say so.
    access = _tpo_access(harvest_origin_available=False,
                         probes=PROBES_WITH_TRANSPORT_FAILURE)
    assert "transport_failure" in access["reason"]
    assert "https://a/3" in access["reason"]
    assert "weakest basis" in access["reason"]


def test_compose_tpo_access_not_obtainable_omits_the_transport_clause_when_every_route_answered():
    access = _tpo_access(harvest_origin_available=False, probes=PROBES_ALL_ANSWERED)
    assert "transport_failure" not in access["reason"]


# --- compose_pagination_note ------------------------------------------------------------------


def test_compose_pagination_note_reports_a_page_capped_listing():
    note = m.compose_pagination_note(
        {"probed_year": "2021", "files_listed_this_page": 20,
         "filescount_per_box_metadata": 37})
    assert "page-capped" in note
    assert "20" in note and "37" in note


def test_compose_pagination_note_reports_an_exact_match():
    note = m.compose_pagination_note(
        {"probed_year": "2024", "files_listed_this_page": 13,
         "filescount_per_box_metadata": 13})
    assert "exactly" in note
    # The caveat that a *different* year could still be page-capped is kept; what must not
    # appear is a claim that this year was.
    assert "page-capped for at least this year" not in note


def test_compose_pagination_note_does_not_claim_an_exact_match_when_listed_exceeds_claimed():
    # Finding 2, third bullet: the shipped else-branch said "matching that folder's filesCount
    # metadata exactly" but fired for `listed > claimed` too.
    note = m.compose_pagination_note(
        {"probed_year": "2024", "files_listed_this_page": 15,
         "filescount_per_box_metadata": 13})
    assert "exactly" not in note
    assert "matching" not in note
    assert "more rendered than claimed" in note


def test_compose_pagination_note_when_the_comparison_was_not_performed():
    assert "not performed" in m.compose_pagination_note({"probed_year": None})
    assert "not performed" in m.compose_pagination_note(
        {"files_listed_this_page": 13, "filescount_per_box_metadata": None})


# --- compose_cadence_claim --------------------------------------------------------------------


def test_compose_cadence_claim_full_window_contradicts_a_blanket_biennial_claim():
    nav = {"year_subfolders_found": [str(y) for y in range(2017, 2025)],
           "window_year_subfolders_found": [str(y) for y in range(2017, 2025)]}
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "every D1 window year" in claim
    assert "2024" in claim


def test_compose_cadence_claim_partial_window_says_coverage_is_incomplete():
    nav = {"year_subfolders_found": ["2017", "2019"],
           "window_year_subfolders_found": ["2017", "2019"]}
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "incomplete" in claim
    assert "every D1 window year" not in claim


def test_compose_cadence_claim_with_no_window_year_found():
    claim = m.compose_cadence_claim(
        {"year_subfolders_found": [], "window_year_subfolders_found": []},
        window_years=WINDOW_YEARS, window_start_year=2017)
    assert claim == "no D1 window year subfolder was found this run"


def test_compose_cadence_claim_appends_a_biennial_suffix_for_all_odd_pre_window_years():
    nav = {"year_subfolders_found": ["1997", "1999", "2001", "2017"],
           "window_year_subfolders_found": ["2017"]}
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "biennial cadence, verified this run" in claim
    assert "1997" in claim


def test_compose_cadence_claim_does_not_claim_biennial_when_pre_window_years_are_mixed():
    nav = {"year_subfolders_found": ["1998", "1999", "2017"],
           "window_year_subfolders_found": ["2017"]}
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "not strictly biennial" in claim
    assert "biennial cadence, verified this run" not in claim


# --- compose_retention_rule -------------------------------------------------------------------


def test_compose_retention_rule_counts_the_retained_non_200_bodies():
    # Ruling D-B: the 4,208-byte 404 body and the 914-byte 403 body are what distinguish
    # "404 not published" from "reachable but empty" from "blocked".
    rule = m.compose_retention_rule([200, 200, 404, 403])
    assert rule["extracts_recorded"] == 4
    assert rule["extracts_with_non_200_status"] == 2
    assert rule["non_200_statuses_recorded"] == [403, 404]


def test_compose_retention_rule_on_an_all_200_run_records_zero_without_omitting_the_rule():
    rule = m.compose_retention_rule([200, 200])
    assert rule["extracts_with_non_200_status"] == 0
    assert rule["non_200_statuses_recorded"] == []
    assert rule["rule"]


def test_compose_retention_rule_warns_the_reader_not_to_generalise_it_to_other_sources():
    rule = m.compose_retention_rule([200, 404])
    assert "is not evidence that no non-200 response occurred there" in rule["rule"]
