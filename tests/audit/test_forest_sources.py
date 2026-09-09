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

import json
from pathlib import Path

import _common
import forest_sources as m
import httpx
import pytest

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
        '<html><head><script> Box.config = {"unrelated": {}};'
        f" Box.postStreamData = {payload};"
        ' Box.otherThing = {"also": "unrelated"};</script></head></html>'
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


# --- xlsx_first_sheet_part -----------------------------------------------------------------

# The real xl/_rels/workbook.xml.rels of Alabama_2024.xlsx, trimmed to two relationships and
# left in the order the file stores them (rId8 first) -- relationship order in the rels part
# is not sheet order, which is exactly why the r:id has to be followed rather than assumed.
WORKBOOK_RELS_XML = (
    '<?xml version="1.0"?><Relationships>'
    '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/worksheet" Target="worksheets/sheet3.xml"/>'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    "</Relationships>"
)


def test_xlsx_first_sheet_part_resolves_the_first_sheet_through_its_relationship_id():
    assert m.xlsx_first_sheet_part(WORKBOOK_XML, WORKBOOK_RELS_XML) == (
        "County Production",
        "xl/worksheets/sheet1.xml",
    )


def test_xlsx_first_sheet_part_follows_the_rel_id_not_the_sheet_file_numbering():
    # Finding 1: reading xl/worksheets/sheet1.xml and calling it "the first sheet" is an
    # assumption about a mapping the workbook states explicitly. Here rId1 points at sheet7.
    rels = WORKBOOK_RELS_XML.replace(
        'Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'worksheet" Target="worksheets/sheet1.xml"',
        'Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'worksheet" Target="worksheets/sheet7.xml"',
    )
    assert m.xlsx_first_sheet_part(WORKBOOK_XML, rels) == (
        "County Production",
        "xl/worksheets/sheet7.xml",
    )


def test_xlsx_first_sheet_part_returns_none_when_the_relationship_is_absent():
    assert m.xlsx_first_sheet_part(WORKBOOK_XML, "<Relationships/>") is None


def test_xlsx_first_sheet_part_returns_none_when_there_are_no_sheets():
    assert m.xlsx_first_sheet_part("<workbook><sheets/></workbook>", WORKBOOK_RELS_XML) is None


# --- classify_header_row --------------------------------------------------------------------

# The real 22-column header row of Alabama_2024.xlsx's first sheet, as recorded in
# box_navigation.sample_file_first_sheet_headers by the run that fetched it.
REAL_FIRST_SHEET_HEADERS = [
    "REGION",
    "STATECD",
    "STATE_NAME",
    "COUNTYCD",
    "COUNTY_NAME",
    "YEAR",
    "OWNCD",
    "OWNER_MEANING",
    "SPGRPCD",
    "SPGRP_NAME",
    "REMCLASSCD",
    "REMCLASSCD_MEANING",
    "SOURCECD",
    "SOURCECD_MEANING",
    "PRODCD",
    "PRODCD_MEANING",
    "MCFVOL",
    "RPA_STD_AMOUNT",
    "RPA_STD_AMOUNT_UOM_CODE",
    "RPA_STD_AMOUNT_UOM_MEANING",
    "SAWREMVOL",
    "GREEN_TONS",
]


def test_classify_header_row_names_the_county_identifier_columns():
    classes = m.classify_header_row(REAL_FIRST_SHEET_HEADERS)
    assert classes["county_identifier_headers"] == ["COUNTYCD", "COUNTY_NAME"]


def test_classify_header_row_names_the_volume_measure_columns():
    classes = m.classify_header_row(REAL_FIRST_SHEET_HEADERS)
    assert classes["volume_measure_headers"] == ["MCFVOL", "SAWREMVOL", "GREEN_TONS"]


def test_classify_header_row_does_not_count_a_uom_code_column_as_a_measure():
    # RPA_STD_AMOUNT_UOM_CODE names a unit of measure, not a measured volume.
    classes = m.classify_header_row(REAL_FIRST_SHEET_HEADERS)
    assert "RPA_STD_AMOUNT_UOM_CODE" not in classes["volume_measure_headers"]


def test_classify_header_row_on_an_unread_header_row_reports_empty_lists():
    assert m.classify_header_row([]) == {
        "county_identifier_headers": [],
        "volume_measure_headers": [],
    }


# --- scannable_text_page ---------------------------------------------------------------------


def test_scannable_text_page_accepts_a_200_with_a_body():
    assert m.scannable_text_page({"http_status": 200, "body": b"<html>x</html>"})


def test_scannable_text_page_rejects_a_200_with_an_empty_body():
    # Finding 3, second bullet: `retain_body` refuses an empty body, so a page gated on the
    # status alone would be counted among the pages "fetched and hashed" with no extract
    # behind it.
    res = {"http_status": 200, "body": b""}
    assert not m.scannable_text_page(res)
    assert not m.answered_with_body(res)


def test_scannable_text_page_rejects_a_retained_non_200_body():
    res = {"http_status": 403, "body": b"<html>denied</html>"}
    assert m.answered_with_body(res)
    assert not m.scannable_text_page(res)


def test_scannable_text_page_rejects_a_transport_failure():
    assert not m.scannable_text_page({"http_status": 0, "body": b""})


# --- distinguishes_harvest_origin_from_mill_receipts ---------------------------------------

# The real sheet names from Ohio_2021.xlsx, fetched via the legacy Box download route this
# session and inspected directly with `zipfile` (no new dependency: xlsx is a zip container).
REAL_TPO_SHEET_NAMES = [
    "County Production",
    "State Production",
    "Receipts",
    "Wood Movement-IMPORTS",
    "Wood Movement-EXPORTS",
    "Mill Locations",
    "Residue Use State",
    "Regional Production",
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
        lambda: next(calls),
        url="https://example/x",
        attempts=5,
        wait_seconds=3.0,
        sleep=sleeps.append,
        now=lambda: 0.0,
    )
    assert len(result["attempts"]) == 2
    assert result["attempts"][-1]["outcome"] == "reachable"
    assert sleeps == [3.0]  # slept once, between attempt 1 and attempt 2 -- never after success


def test_probe_with_retries_exhausts_the_bound_when_every_attempt_transport_fails():
    result = m.probe_with_retries(
        lambda: (0, 0),
        url="https://example/x",
        attempts=3,
        wait_seconds=1.0,
        sleep=lambda s: None,
        now=lambda: 0.0,
    )
    assert len(result["attempts"]) == 3
    assert all(a["outcome"] == "transport_failure" for a in result["attempts"])


def test_probe_with_retries_records_elapsed_seconds_from_the_injected_clock():
    clock = iter([100.0, 107.5])
    result = m.probe_with_retries(
        lambda: (200, 10),
        url="https://example/x",
        attempts=3,
        wait_seconds=1.0,
        sleep=lambda s: None,
        now=lambda: next(clock),
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
        "Annual other removals volume",
        "Annual removals volume",
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
        "row_count": 0,
        "harvest_removals_groups": [],
        "harvest_removals_attribute_count": 0,
        "harvest_removals_attribute_nbrs": [],
        "non_harvest_removals_groups": [],
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
        {
            "estimate_group": "Annual harvest removals dry weight",
            "attribute_count": 38,
            "lowest_attribute_nbr": "574201",
            "eval_typs": ["EXPREMV"],
        },
        {
            "estimate_group": "Annual harvest removals volume",
            "attribute_count": 17,
            "lowest_attribute_nbr": "574161",
            "eval_typs": ["EXPREMV"],
        },
    ],
    "harvest_removals_attribute_count": 55,
    "harvest_removals_attribute_nbrs": ["574161", "574201"],
    "non_harvest_removals_groups": ["Annual other removals volume", "Annual removals volume"],
    "eval_typs_present": ["EXPCURR", "EXPREMV"],
}
SNUM_INDEX_UNREADABLE = {
    "row_count": 0,
    "harvest_removals_groups": [],
    "harvest_removals_attribute_count": 0,
    "harvest_removals_attribute_nbrs": [],
    "non_harvest_removals_groups": [],
    "eval_typs_present": [],
}
SNUM_INDEX_NO_HARVEST = dict(SNUM_INDEX_WITH_HARVEST) | {
    "harvest_removals_groups": [],
    "harvest_removals_attribute_count": 0,
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
        "doc_params_parsed": True,
        "real_probe_parsed": True,
        "measure_proved": MEASURE_AREA,
        "snum_index": SNUM_INDEX_WITH_HARVEST,
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
    access = _fia_access(
        measure_proved={
            "num_est_desc": "574161 Average annual harvest removals, in cubic feet",
            "est_meta": "Harvest removals estimate.",
            "attribute_nbr": "574161",
        }
    )
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


MEASURE_WITHOUT_A_NUMBER = {
    "num_est_desc": "Area of sampled land and water, in acres",
    "est_meta": "Area estimate for land and water based on all sampled plots.",
    "attribute_nbr": "",
}


def test_compose_fia_access_verified_does_not_claim_a_named_measure_when_none_was_named():
    # Fix round 2, finding 2 site A: the fixed prefix read "Verified for retrieval, with the
    # retrieved measure named: {measured}" while `measured` on this branch says the response
    # named no measure. `real_probe_parsed` only requires non-empty estimates and metadata, so
    # this branch is reachable, and both existing tests over it asserted only truthiness.
    access = _fia_access(measure_proved=None)
    assert access["status"] == "verified"
    assert "with the retrieved measure named" not in access["reason"]
    assert "no numEstDesc/estMeta metadata naming the measure it returned" in access["reason"]


def test_compose_fia_access_verified_without_a_named_measure_refers_back_to_no_measure():
    # The two compounding clauses: "That attribute number is not one of those harvest-removals
    # attributes" and "retrieval of the one measure named above" -- both referents to a measure
    # this branch never named.
    reason = _fia_access(measure_proved=None)["reason"]
    assert "That attribute number" not in reason
    assert "the one measure named above" not in reason
    assert "cannot be checked against those harvest-removals attribute numbers" in reason


def test_compose_fia_access_verified_says_which_measure_when_the_number_is_unreadable():
    # `proved_estimate_measure` returns a record whenever EITHER metadata field is present, so
    # `attribute_nbr` can be "" -- an f-string reading "the request sent snum=" with nothing
    # after it, and a membership test that can never match.
    reason = _fia_access(measure_proved=MEASURE_WITHOUT_A_NUMBER)["reason"]
    assert "Area of sampled land and water" in reason
    assert "no leading attribute number" in reason
    assert "That attribute number" not in reason


def test_compose_fia_access_documented_branch_does_not_name_an_unnamed_measure():
    reason = _fia_access(measure_proved=None, snum_index=SNUM_INDEX_UNREADABLE)["reason"]
    assert "could not be read this run" in reason
    assert "no numEstDesc/estMeta metadata naming the measure it returned" in reason


def test_compose_fia_access_reason_is_never_none():
    for kwargs in (
        {},
        {"doc_params_parsed": False},
        {"real_probe_parsed": False},
        {"snum_index": SNUM_INDEX_UNREADABLE},
        {"snum_index": SNUM_INDEX_NO_HARVEST},
        {"measure_proved": None},
        {"measure_proved": MEASURE_WITHOUT_A_NUMBER},
    ):
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
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138
    )
    assert "NAICS=0" in text
    assert "species=282" in text
    assert "fiadb_api_doc.html" in text


def test_compose_fia_uncovered_delimits_the_unbacked_reading_with_the_marker_convention():
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138
    )
    assert text.count("INFERENCE MARKER, OPENING") == 1
    assert text.count("INFERENCE MARKER, CLOSING") == 1
    assert text.index("INFERENCE MARKER, OPENING") < text.index("INFERENCE MARKER, CLOSING")
    assert "carries no extract hash" in text


def test_compose_fia_uncovered_keeps_the_derived_dc_clause_outside_the_marked_reading():
    # Sub-trap (b): a marking's scope ends where the reader thinks it does. The D.C. clause is
    # interpolated from the fetched evaluation index and must not sit inside the marker.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=1138
    )
    assert "1138-row" in text
    assert text.index("1138-row") > text.index("INFERENCE MARKER, CLOSING")


def test_compose_fia_uncovered_omits_the_dc_clause_when_dc_has_an_evaluation():
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=True, wc_row_count=1138
    )
    assert "District of Columbia" not in text
    assert "NAICS=0" in text


def test_compose_fia_uncovered_does_not_read_an_empty_scan_as_a_zero_hit_finding():
    # Fix round 2, finding 3: `scanned_pages` is empty whenever every FIA fetch returns
    # non-200, and this composer is called unconditionally. "Zero industry-term hits across
    # those pages" over zero pages is a vacuous zero presented as a substantive finding.
    text = m.compose_fia_uncovered(
        industry_scan={
            "pages_scanned": [],
            "industry_classification_terms": {"NAICS": 0},
            "fia_taxonomy_terms": {"species": 0},
        },
        dc_has_evaluation=False,
        wc_row_count=0,
    )
    assert "Zero industry-term hits" not in text
    assert "no industry concept to join on at all" not in text
    assert "fetched and hashed ()" not in text
    assert "is not a scan that found no industry terms" in text


def test_compose_fia_uncovered_empty_scan_does_not_deny_that_anything_was_fetched():
    # Fix round 3, item 1. `retain_body` gates on `answered_with_body` (any status but 0, with
    # bytes); `scannable_text_page` additionally requires a 200. A run whose every /fiadb-api/
    # fetch answers 403-with-a-body therefore registers and hashes five extracts while
    # `scanned_pages` stays empty -- so "No FIA page was fetched and hashed this run" is false
    # on exactly the branch it is written for. The sentence must name the 200-gate the scan
    # actually turns on, and must scope itself to the scan's own corpus: `other_route_*`
    # bodies are fetched and hashed too -- at any status, 200 included -- and never reach the
    # scan, so a sentence about what the run fetched cannot stand in for one about the corpus.
    text = m.compose_fia_uncovered(
        industry_scan={
            "pages_scanned": [],
            "industry_classification_terms": {"NAICS": 0},
            "fia_taxonomy_terms": {"species": 0},
        },
        dc_has_evaluation=False,
        wc_row_count=0,
    )
    assert "fetched and hashed" not in text
    assert "status-200 body" in text


def test_compose_fia_uncovered_names_the_scan_corpus_not_every_hashed_extract():
    # Same fix, the live half: the scan corpus is a proper subset of `extracts[]` on any run
    # where an `other_route_*` fetch answers with a body, so "the N FIA page(s) this run
    # fetched and hashed" misdescribes the set it counts. The count phrase names the corpus.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=True, wc_row_count=1138
    )
    assert "fetched and hashed" not in text
    assert "status-200 body" in text
    assert "fiadb_api_doc.html" in text


def test_compose_fia_uncovered_does_not_draw_the_zero_reading_when_terms_were_found():
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN
        | {"industry_classification_terms": {"NAICS": 0, "SIC": 0, "industry": 4}},
        dc_has_evaluation=True,
        wc_row_count=1138,
    )
    assert "industry=4" in text
    assert "Zero industry-term hits" not in text
    assert "no industry concept to join on at all" not in text
    assert "not itself an industry concept" in text
    assert text.count("INFERENCE MARKER, OPENING") == 1
    assert text.count("INFERENCE MARKER, CLOSING") == 1


def test_compose_fia_uncovered_does_not_assert_the_taxonomy_terms_are_used():
    # The clause "hits for the concepts those same pages do use are {taxonomy}" names an
    # outcome the function never branches on: an all-zero taxonomy count contradicts it.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN
        | {"fia_taxonomy_terms": {"land use": 0, "product": 0, "species": 0}},
        dc_has_evaluation=True,
        wc_row_count=1138,
    )
    assert "do use" not in text
    assert "species=0" in text


def test_compose_fia_uncovered_does_not_place_dc_outside_an_index_that_was_never_read():
    # Same class as the vacuous zero: `dc_has_evaluation` is False both when D.C. is absent
    # from a parsed index and when no index parsed at all.
    text = m.compose_fia_uncovered(
        industry_scan=INDUSTRY_SCAN, dc_has_evaluation=False, wc_row_count=0
    )
    assert "no FIA evaluation unit for the District of Columbia" not in text
    assert "was not read this run" in text


# --- compose_tpo_access -----------------------------------------------------------------------

BOX_NAV_VERIFIED = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
    "nrum_data_folder_id": 121486946349,
    "year_subfolders_found": ["2023", "2024"],
    "probed_year": "2024",
    "sample_file": "Alabama_2024.xlsx",
    "sample_file_sheet_names": [
        "County Production",
        "State Production",
        "Receipts",
        "Mill Locations",
    ],
    "sample_file_first_sheet_name": "County Production",
    "sample_file_first_sheet_headers": REAL_FIRST_SHEET_HEADERS,
}
BOX_NAV_VERIFIED_NO_HEADER_ROW = {
    k: v
    for k, v in BOX_NAV_VERIFIED.items()
    if k not in ("sample_file_first_sheet_name", "sample_file_first_sheet_headers")
}
# The Box share page answered non-200 (a 5xx outage is not a transport failure), so nothing
# behind the share URL was ever read -- `year_subfolders_found` is set only once a status-200
# body arrives, and `nrum_data_folder_id` only once that body parses as a folder listing.
BOX_NAV_SHARE_PAGE_UNREAD = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
}
BOX_NAV_SHARE_PAGE_UNPARSED = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
    "nrum_data_folder_id": None,
    "year_subfolders_found": [],
    "shared_folder_parse_error": "marker not found: sharedFolder",
}
# Fix round 3, item 3: a payload that parsed but carried no `currentFolderID`. This leaves
# `nrum_data_folder_id` None through a parse that *succeeded* -- the state that made
# "that body did not parse" false while `year_subfolders_found` was non-empty.
BOX_NAV_PARSED_WITHOUT_A_FOLDER_ID = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
    "nrum_data_folder_id": None,
    "year_subfolders_found": ["2023", "2024"],
}
BOX_NAV_NO_YEAR_SELECTED = {
    "share_url_discovered": "https://usfs-public.app.box.com/s/abc",
    "nrum_data_folder_id": 121486946349,
    "year_subfolders_found": ["1997", "1999"],
}
BOX_NAV_NO_WORKBOOK_INSPECTED = BOX_NAV_NO_YEAR_SELECTED | {
    "probed_year": "2024",
    "sample_file_inspection_error": "File is not a zip file",
}
BOX_NAV_WORKBOOK_WITHOUT_BOTH_SHEET_KINDS = BOX_NAV_VERIFIED | {
    "sample_file_sheet_names": ["County Production", "State Production"],
}
PROBES_ALL_ANSWERED = [
    {"url": "https://a/1", "outcome": "reachable"},
    {"url": "https://a/2", "outcome": "not_found"},
]
PROBES_WITH_TRANSPORT_FAILURE = PROBES_ALL_ANSWERED + [
    {"url": "https://a/3", "outcome": "transport_failure"},
]


def _marked_spans(text: str) -> list[str]:
    """The text between each `INFERENCE MARKER, OPENING` and its `CLOSING`. Asserting on spans
    rather than on the whole string is what keeps a second marked span from borrowing the
    first one's disclosure."""
    spans = []
    for chunk in text.split("INFERENCE MARKER, OPENING")[1:]:
        assert "INFERENCE MARKER, CLOSING" in chunk, "an opened marker is never closed"
        spans.append(chunk.split("INFERENCE MARKER, CLOSING")[0])
    return spans


def _tpo_access(**overrides):
    kwargs = {
        "route": "nrum -> box -> legacy download",
        "harvest_origin_available": True,
        "box_navigation": BOX_NAV_VERIFIED,
        "probes": PROBES_ALL_ANSWERED,
    }
    return m.compose_tpo_access(**(kwargs | overrides))


def test_compose_tpo_access_verified_marks_the_sheet_name_reading_as_an_inference():
    # Folded-in minor: `harvest_origin_available: true` is a regex match on sheet names from
    # one workbook. The inference that a sheet named "County Production" carries harvest-origin
    # attribution is drawn from a quotation and must be marked. Fix round 2 adds a second
    # marked span (the carried-over route provenance), so each span must carry the
    # no-extract-hash disclosure itself rather than borrowing the other's.
    access = _tpo_access()
    assert access["status"] == "verified"
    spans = _marked_spans(access["reason"])
    assert len(spans) == 2
    # Each span must disclose its own unbacked status: one pair saying so does not cover the
    # other, and a reader meeting the second span first would have no disclosure at all.
    assert all("no extract hash" in span for span in spans)
    assert "the origin/receipt split rests on the sheet names alone" in access["reason"]


def test_compose_tpo_access_verified_names_the_one_workbook_the_reading_rests_on():
    access = _tpo_access()
    assert "Alabama_2024.xlsx" in access["reason"]
    assert "County Production" in access["reason"]
    assert "every state-year workbook" in access["reason"]


def test_compose_tpo_access_not_obtainable_without_a_share_url_claims_no_folder_was_entered():
    # Finding 2, second bullet: the shipped reason asserted "no probed route -- including the
    # Box folder discovered this run -- yielded a machine-readable file", which is false when
    # no folder was discovered at all.
    access = _tpo_access(
        harvest_origin_available=False, box_navigation={"share_url_discovered": None}
    )
    assert access["status"] == "not_obtainable"
    assert "no Box share link" in access["reason"]
    assert "discovered this run" not in access["reason"]


def test_compose_tpo_access_not_obtainable_says_the_folder_was_entered_only_once_it_parsed():
    # Fix round 2, finding 2 site B: the "was entered ... but no file fetched from it" clause
    # was selected by `share_url is not None` alone, which establishes only that a URL was
    # found in the page markup. `nrum_data_folder_id` / `year_subfolders_found` are the
    # signals that the folder page actually answered and parsed.
    access = _tpo_access(harvest_origin_available=False, box_navigation=BOX_NAV_NO_YEAR_SELECTED)
    assert "was entered" in access["reason"]
    assert "no Box share link" not in access["reason"]
    assert "none of which this run selected to probe" in access["reason"]


def test_compose_tpo_access_not_obtainable_claims_no_entry_when_the_share_page_never_answered():
    access = _tpo_access(harvest_origin_available=False, box_navigation=BOX_NAV_SHARE_PAGE_UNREAD)
    reason = access["reason"]
    assert "was entered" not in reason
    assert "no file fetched from it" not in reason
    assert "did not answer this run with a status-200 body" in reason
    assert "https://usfs-public.app.box.com/s/abc" in reason


def test_compose_tpo_access_not_obtainable_names_the_folder_parse_failure():
    reason = _tpo_access(
        harvest_origin_available=False, box_navigation=BOX_NAV_SHARE_PAGE_UNPARSED
    )["reason"]
    assert "did not parse as a Box folder listing" in reason
    assert "marker not found: sharedFolder" in reason
    assert "was entered" not in reason


def test_compose_tpo_access_takes_the_parse_failure_branch_only_when_the_parse_raised():
    # Fix round 3, item 3, state (b). `nrum_data_folder_id is None` is also what a *successful*
    # parse leaves behind when the payload carries no `currentFolderID`, and on that state the
    # old predicate asserted "that body did not parse" with no parse error to name, while
    # `year_subfolders_found` was non-empty. The exact signal is `shared_folder_parse_error`.
    reason = _tpo_access(
        harvest_origin_available=False, box_navigation=BOX_NAV_PARSED_WITHOUT_A_FOLDER_ID
    )["reason"]
    assert "did not parse as a Box folder listing" not in reason
    assert "was entered" in reason
    assert "2023" in reason and "2024" in reason


def test_compose_tpo_access_parse_failure_branch_always_names_the_error():
    # State (a): `shared_folder_parse_error` is set in the same except that produces this
    # branch, so the branch can no longer be reached with no error to name.
    reason = _tpo_access(
        harvest_origin_available=False, box_navigation=BOX_NAV_SHARE_PAGE_UNPARSED
    )["reason"]
    assert "(marker not found: sharedFolder)" in reason


def test_compose_tpo_access_unanswered_share_page_outranks_the_missing_parse_error_key():
    # State (c): a share page that never answered 200-with-a-body sets neither
    # `year_subfolders_found` nor `shared_folder_parse_error`. The absent parse-error key must
    # not read as "the parse succeeded" -- the "did not answer" clause still wins.
    reason = _tpo_access(harvest_origin_available=False, box_navigation=BOX_NAV_SHARE_PAGE_UNREAD)[
        "reason"
    ]
    assert "did not answer this run with a status-200 body" in reason
    assert "did not parse as a Box folder listing" not in reason
    assert "was entered" not in reason


def test_compose_tpo_access_not_obtainable_when_no_workbook_was_inspected():
    reason = _tpo_access(
        harvest_origin_available=False, box_navigation=BOX_NAV_NO_WORKBOOK_INSPECTED
    )["reason"]
    assert "2024 subfolder" in reason
    assert "both fetched and inspected" in reason
    assert "File is not a zip file" in reason


def test_compose_tpo_access_not_obtainable_names_the_sheets_the_inspected_workbook_had():
    reason = _tpo_access(
        harvest_origin_available=False, box_navigation=BOX_NAV_WORKBOOK_WITHOUT_BOTH_SHEET_KINDS
    )["reason"]
    assert "Alabama_2024.xlsx" in reason
    assert "State Production" in reason
    assert "do not include both" in reason


def test_compose_tpo_access_not_obtainable_names_a_transport_failure_as_the_weakest_basis():
    # Finding 3: a transport failure collapsing into `not_obtainable` is what `classify_probe`'s
    # own docstring calls the weakest possible basis for that verdict; the reason must say so.
    access = _tpo_access(harvest_origin_available=False, probes=PROBES_WITH_TRANSPORT_FAILURE)
    assert "transport_failure" in access["reason"]
    assert "https://a/3" in access["reason"]
    assert "weakest basis" in access["reason"]


def test_compose_tpo_access_not_obtainable_omits_the_transport_clause_when_every_route_answered():
    access = _tpo_access(harvest_origin_available=False, probes=PROBES_ALL_ANSWERED)
    assert "transport_failure" not in access["reason"]


def test_compose_tpo_access_verified_derives_the_county_and_volume_columns_from_the_headers():
    # Fix round 2, finding 1: the captured header row is derived evidence bearing on
    # harvest-origin attribution and was going unused inside the marked inference.
    reason = _tpo_access()["reason"]
    assert "COUNTYCD" in reason
    assert "SAWREMVOL" in reason
    assert "county-resolved volume columns" in reason
    assert reason.index("COUNTYCD") < reason.index("INFERENCE MARKER, OPENING")


def test_compose_tpo_access_verified_does_not_call_the_header_reading_a_measurement():
    # Fix round 3, item 4. The evidence belongs outside the marker (round 2 established that
    # and it stands), but what happened was that two column names matched two patterns: that
    # those names *denote* a county and a volume is still a reading of column names. "measured"
    # claims more than the act was.
    reason = _tpo_access()["reason"]
    assert "measured from the header row" not in reason
    assert "read from the header row's own column names" in reason


def test_compose_tpo_access_verified_does_not_claim_no_cell_values_were_read():
    # The one sentence in either artifact that was false today: `inspect_xlsx` reads the first
    # sheet's header row, and box_navigation records 22 cell values from it.
    reason = _tpo_access()["reason"]
    assert "no cell values were read" not in reason
    assert "No data-row cells were read or compared across sheets" in reason


def test_compose_tpo_access_verified_keeps_the_whose_county_caveat_outside_the_marker():
    reason = _tpo_access()["reason"]
    assert "is not settled by a column name" in reason
    assert reason.index("is not settled by a column name") < reason.index(
        "INFERENCE MARKER, OPENING"
    )


def test_compose_tpo_access_verified_says_so_when_no_header_row_was_read():
    reason = _tpo_access(box_navigation=BOX_NAV_VERIFIED_NO_HEADER_ROW)["reason"]
    assert "No header row was read" in reason
    assert "county-resolved volume columns" not in reason


def test_compose_tpo_access_verified_marks_the_carried_over_route_provenance():
    # Fix round 2, finding 4: "(401 without a browser session)" was carried over from the
    # shaping investigation -- no probe in `route_probes` produced a 401 this run.
    reason = _tpo_access()["reason"]
    assert "401" in reason
    provenance = _marked_spans(reason)[1]
    assert "401 without a browser session" in provenance
    assert "No probe in this run requested that URL" in provenance
    assert "share page's own JS bundle" in provenance


# --- compose_pagination_note ------------------------------------------------------------------


def test_compose_pagination_note_reports_a_page_capped_listing():
    note = m.compose_pagination_note(
        {"probed_year": "2021", "files_listed_this_page": 20, "filescount_per_box_metadata": 37}
    )
    assert "page-capped" in note
    assert "20" in note and "37" in note


def test_compose_pagination_note_reports_an_exact_match():
    note = m.compose_pagination_note(
        {"probed_year": "2024", "files_listed_this_page": 13, "filescount_per_box_metadata": 13}
    )
    assert "exactly" in note
    # The caveat that a *different* year could still be page-capped is kept; what must not
    # appear is a claim that this year was.
    assert "page-capped for at least this year" not in note


def test_compose_pagination_note_does_not_claim_an_exact_match_when_listed_exceeds_claimed():
    # Finding 2, third bullet: the shipped else-branch said "matching that folder's filesCount
    # metadata exactly" but fired for `listed > claimed` too.
    note = m.compose_pagination_note(
        {"probed_year": "2024", "files_listed_this_page": 15, "filescount_per_box_metadata": 13}
    )
    assert "exactly" not in note
    assert "matching" not in note
    assert "more rendered than claimed" in note


def test_compose_pagination_note_when_the_comparison_was_not_performed():
    assert "not performed" in m.compose_pagination_note({"probed_year": None})
    assert "not performed" in m.compose_pagination_note(
        {"files_listed_this_page": 13, "filescount_per_box_metadata": None}
    )


# --- compose_cadence_claim --------------------------------------------------------------------


def test_compose_cadence_claim_full_window_contradicts_a_blanket_biennial_claim():
    nav = {
        "year_subfolders_found": [str(y) for y in range(2017, 2025)],
        "window_year_subfolders_found": [str(y) for y in range(2017, 2025)],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "every D1 window year" in claim
    assert "2024" in claim


def test_compose_cadence_claim_partial_window_says_coverage_is_incomplete():
    nav = {
        "year_subfolders_found": ["2017", "2019"],
        "window_year_subfolders_found": ["2017", "2019"],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "incomplete" in claim
    assert "every D1 window year" not in claim


def test_compose_cadence_claim_with_no_window_year_found():
    claim = m.compose_cadence_claim(
        {"year_subfolders_found": [], "window_year_subfolders_found": []},
        window_years=WINDOW_YEARS,
        window_start_year=2017,
    )
    assert claim == "no D1 window year subfolder was found this run"


def test_compose_cadence_claim_appends_a_biennial_suffix_for_pre_window_years_two_apart():
    """Renamed with its predicate. It used to be `..._for_all_odd_pre_window_years`, and the
    name was the tell: all-odd is not biennial, it merely coincides with it on the real folder
    set. The suffix now rides on the spacing, so the name and the claim say the same thing."""
    nav = {
        "year_subfolders_found": ["1997", "1999", "2001", "2017"],
        "window_year_subfolders_found": ["2017"],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "biennial cadence, verified this run" in claim
    assert "only for odd years back to 1997" in claim


def test_compose_cadence_claim_does_not_call_all_odd_quadrennial_years_biennial():
    """The defect the rename exists for. `["1997", "2001", "2005"]` is every-year-odd and
    four-yearly; the previous predicate called it "biennial cadence, verified this run" in a
    sentence that ships in `tpo/summary.json`'s `coverage_span.covered`."""
    nav = {
        "year_subfolders_found": ["1997", "2001", "2005", "2017"],
        "window_year_subfolders_found": ["2017"],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "biennial" not in claim.split("; ")[-1].replace("not biennial", "")
    assert "biennial cadence, verified this run" not in claim
    assert "[1997, 2001, 2005]" in claim
    assert "not a uniform two years" in claim


def test_compose_cadence_claim_reports_even_spaced_pre_window_years_as_even():
    """The parity word is read off the data, not typed. A step of two fixes the parity but not
    which one it is, and the real run happens to be odd -- so an even biennial run must not
    inherit the word "odd" from it."""
    nav = {
        "year_subfolders_found": ["1998", "2000", "2002", "2017"],
        "window_year_subfolders_found": ["2017"],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "only for even years back to 1998" in claim
    assert "odd" not in claim


def test_compose_cadence_claim_calls_a_single_pre_window_folder_no_cadence_at_all():
    """`all()` over the empty pairwise of a one-element list is True, so a bare `all(b - a == 2
    ...)` would call one folder a verified biennial cadence. The `len >= 2` guard is what stops
    that, and this is the test that holds it in place."""
    nav = {"year_subfolders_found": ["2013", "2017"], "window_year_subfolders_found": ["2017"]}
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "biennial cadence, verified this run" not in claim
    assert "one folder fixes no cadence in either direction" in claim
    assert "2013" in claim


def test_compose_cadence_claim_does_not_claim_biennial_when_pre_window_years_are_mixed():
    nav = {
        "year_subfolders_found": ["1998", "1999", "2017"],
        "window_year_subfolders_found": ["2017"],
    }
    claim = m.compose_cadence_claim(nav, window_years=WINDOW_YEARS, window_start_year=2017)
    assert "not biennial across this range" in claim
    assert "biennial cadence, verified this run" not in claim


# --- compose_retention_rule -------------------------------------------------------------------


def test_retention_rule_does_not_claim_retained_bytes_tell_an_empty_200_apart():
    """Whole-branch review, finding 5. The persisted rule read "a 404 page, a 403 page and an
    empty 200 are three different verdicts and only the retained bytes tell them apart", and
    that shipped into both `fia/summary.json` and `tpo/summary.json`. `answered_with_body`
    returns `res["http_status"] != 0 and bool(res["body"])`, so a zero-byte 200 registers no
    extract at all -- there are no retained bytes to tell it apart with. The behaviour is
    defensible; the sentence was not."""
    rule = m.compose_retention_rule([200, 404])["rule"]
    assert "empty 200 are three different verdicts" not in rule
    assert "a 404 page and a 403 page are different verdicts" in rule


def test_retention_rule_names_the_empty_body_exclusion_as_its_own_case():
    """Not merely dropped: an empty 200 registering nothing is a real behaviour a reader of the
    counters needs, and it is a different case from a transport failure."""
    rule = m.compose_retention_rule([200])["rule"]
    assert "Two cases register no extract, and they are not the same case." in rule
    assert "including an empty 200" in rule
    assert "its probe entry's status and its bytes count of zero" in rule
    assert "A transport failure produced no response at all" in rule


def test_retention_rule_scopes_itself_to_the_routes_probed_for_bytes():
    """Whole-branch review, finding 6. The `FIA_DATAMART_CANDIDATES` are probed through
    `c.probe`, which discards bodies by construction, so they can never register an extract --
    while the rule claimed to cover a fetched body "whenever the endpoint answered at all,
    whatever the HTTP status". This run's six datamart attempts were all transport failures, so
    an exception clause covered today's artifact; a re-run that got a 403 or a 200 there would
    have made the persisted sentence false with no test failing."""
    rule = m.compose_retention_rule([200])["rule"]
    assert "Scope: this rule is about the routes probed for bytes." in rule
    assert "probes a route status-only" in rule
    assert "registers no extract whatever it answers" in rule
    assert "whenever the endpoint answered at all, whatever the HTTP status" not in rule


def test_retention_rule_scope_clause_does_not_assert_tpo_has_status_only_routes():
    """A defect in this wave's own fix for finding 6, caught in review before hand-off. The
    first draft opened "Some routes are probed status-only" -- an existence claim, true of
    `run_fia` (the datamart lambda is its one `c.probe` call) and false of `run_tpo`, whose
    every probe goes through `probe_url` and which makes no `c.probe` call at all. Since this
    text ships into BOTH summaries, that traded a sentence false for FIA's datamart for one
    false for TPO. The clause is now existence-neutral, so it is true of a source with such
    routes and of a source without."""
    rule = m.compose_retention_rule([200])["rule"]
    assert "Where this script probes a route status-only" in rule
    assert "which routes, if any, a run probed that way" in rule
    assert "Some routes are probed status-only" not in rule


def test_retention_rule_scope_clause_is_route_class_generic_not_fia_specific():
    """`compose_retention_rule` is shared by `run_fia` and `run_tpo`, and TPO has no datamart
    routes. Naming FIA's would ship a sentence into `tpo/summary.json` about routes that source
    does not have -- false by irrelevance, in the artifact, for a wording fix."""
    rule = m.compose_retention_rule([200])["rule"]
    for fia_only in ("datamart", "Datamart", "DATAMART", "FIA", "Evalidator"):
        assert fia_only not in rule
    assert "recorded in this source's own probe findings" in rule


def test_answered_with_body_docstring_names_both_exclusions():
    """Three sites describe this predicate and only one used to know it: the persisted rule
    named neither exclusion correctly, this docstring named only the transport failure, and
    `scannable_text_page`'s already said `retain_body` refuses an empty body. Pinned as a
    docstring claim, the way findings 1 and 2 of wave 1 are."""
    doc = " ".join(m.answered_with_body.__doc__.split())
    assert "Two exclusions" in doc
    assert "A transport failure (`http_status == 0`) produced no response at all" in doc
    assert "A zero-byte 200 therefore registers no extract at all" in doc
    # And the predicate does what all three now say.
    assert not m.answered_with_body({"http_status": 200, "body": b""})
    assert not m.answered_with_body({"http_status": 0, "body": b""})
    assert m.answered_with_body({"http_status": 403, "body": b"forbidden"})


def test_module_docstring_scopes_the_retention_rule_and_retracts_the_empty_200_claim():
    """The same two corrections at the file-level site, so a reader of the source and a reader
    of the artifact are told the same thing."""
    doc = " ".join(m.__doc__.split())
    assert "a 404 page and a 403 page are different verdicts" in doc
    assert "empty 200 are three different verdicts" not in doc
    assert "The `FIA_DATAMART_CANDIDATES` are probed status-only" in doc
    assert "which discards bodies by construction" in doc


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


# --- composed verdicts round-tripped through the summary schema --------------------------------


def _summary_payload(access: dict) -> dict:
    return {
        "source": "fia",
        "generated_utc": "2026-01-01T00:00:00+00:00",
        "coverage_span": {
            "published_start": "1968",
            "published_end": "2026",
            "window_start": _common.WINDOW_START,
            "window_end": _common.WINDOW_END,
            "covered": "x",
            "uncovered": "y",
        },
        "access": access,
        "extracts": [],
        "findings": {},
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"doc_params_parsed": False},
        {"real_probe_parsed": False},
        {"snum_index": SNUM_INDEX_UNREADABLE},
        {"snum_index": SNUM_INDEX_NO_HARVEST},
        {"measure_proved": None},
        {"measure_proved": MEASURE_WITHOUT_A_NUMBER},
        {"measure_proved": None, "snum_index": SNUM_INDEX_UNREADABLE},
    ],
)
def test_every_composed_fia_access_passes_the_summary_schema(overrides):
    # `_common.validate_summary` raises unless a non-verified status carries a truthy reason.
    # The live run only ever exercises whichever branch the day's fetches produce, so the two
    # new routes to `documented` (unreadable snum catalog, no harvest attribute catalogued)
    # would otherwise first be exercised at write time, in production, as a ValueError.
    _common.validate_summary(_summary_payload(_fia_access(**overrides)))


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {"box_navigation": BOX_NAV_VERIFIED_NO_HEADER_ROW},
        {"harvest_origin_available": False},
        {"harvest_origin_available": False, "box_navigation": {"share_url_discovered": None}},
        {"harvest_origin_available": False, "box_navigation": BOX_NAV_SHARE_PAGE_UNREAD},
        {"harvest_origin_available": False, "box_navigation": BOX_NAV_SHARE_PAGE_UNPARSED},
        {"harvest_origin_available": False, "box_navigation": BOX_NAV_NO_YEAR_SELECTED},
        {"harvest_origin_available": False, "box_navigation": BOX_NAV_NO_WORKBOOK_INSPECTED},
        {
            "harvest_origin_available": False,
            "box_navigation": BOX_NAV_WORKBOOK_WITHOUT_BOTH_SHEET_KINDS,
        },
        {"harvest_origin_available": False, "probes": PROBES_WITH_TRANSPORT_FAILURE},
    ],
)
def test_every_composed_tpo_access_passes_the_summary_schema(overrides):
    payload = _summary_payload(_tpo_access(**overrides)) | {"source": "tpo"}
    _common.validate_summary(payload)


def test_retention_rule_warns_that_a_retained_200_is_not_evidence_of_usable_data():
    # The naive `/fullreport` probe is retained at status 200 and carries an EVALIDator error
    # page. Without this sentence, `non_200_statuses_recorded` invites a reader to treat every
    # other extract's 200 as a clean, usable body.
    rule = m.compose_retention_rule([200, 403])["rule"]
    assert "not that the body is usable data" in rule
    assert "status 200" in rule


def test_docstring_makes_no_claim_about_what_other_audit_scripts_retain():
    """Whole-branch review, finding 2: the other claim that aged in-branch. The ruling-D-B
    paragraph asserted "Every other Stage 0 audit script records a fetched body only when the
    status is 200". True when this file landed (d90f13a); `bds_detail.py` landed later
    (8dde34c), passes `http_status=status`, and ships four extracts at status 204 with
    zero-byte bodies. A claim about other files dates the moment one of them changes, so the
    comparative is gone -- while the rule this script actually follows, and the reason for it,
    stay. Negative pin, so re-adding the sentence beside the corrected text is still caught."""
    doc = " ".join(m.__doc__.split())
    assert "Every other Stage 0 audit script records a fetched body" not in doc
    assert (
        "records a body whenever a route it probes for bytes answers with a non-empty "
        "one, whatever the status"
    ) in doc


# --- the scan corpus and the extract set, on a composed run --------------------------------------


def test_a_composed_fia_run_backs_every_scanned_page_with_a_hashed_extract(tmp_path, monkeypatch):
    """`compose_fia_uncovered` persists a sentence asserting each page in the scan's corpus
    "answered with a status-200 body this run and is hashed as an extract". Nothing enforced
    it. The pairing is held together only by a filename literal duplicated at each of five
    sites -- `retain_body(extracts, SOURCE_FIA, doc, "fiadb_api_doc.html")` and
    `scanned_pages["fiadb_api_doc.html"]`, and so on. Rename one without its twin and
    `pages_scanned` names a file no extract backs, the persisted sentence is false, and before
    this test no test failed: every composer test hands `compose_fia_uncovered` a built-by-hand
    `industry_scan` dict, and none of them calls `retain_body` at all.

    Read off the written summary rather than the in-memory lists, so what is pinned is the
    artifact a reader actually gets.

    Deliberately one-directional. `retain_body` is called on routes the scan gate is never
    offered (`other_route_*`), so hashed-but-never-scanned is correct and expected -- exactly
    what `scannable_text_page`'s docstring says. Only the reverse would make the sentence lie.
    """
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    assert _common.AUDIT_ROOT.is_relative_to(tmp_path), "guard: never write into the real root"
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text="<html><body>an answer</body></html>")
        )
    )

    m.run_fia(client)

    written = json.loads((tmp_path / "fia" / "summary.json").read_text(encoding="utf-8"))
    hashed = {Path(e["path"]).name for e in written["extracts"]}
    scanned = set(written["findings"]["industry_concept_scan"]["pages_scanned"])
    assert scanned, "an empty corpus would make the subset check vacuous"
    assert scanned <= hashed, (
        f"pages_scanned names files no extract backs: {sorted(scanned - hashed)}"
    )
