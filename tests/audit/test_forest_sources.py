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
