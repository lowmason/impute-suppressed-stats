"""Judgment-logic tests for `cbp_metadata` (SRC-CBP-001), written before the implementation.

Four pure functions carry all the branching that would otherwise hide inside the per-year
loop: `classify_data_body` (the 302-redirect-to-HTML-error trap), `naics_predicate_matches`
(never silently narrow an ambiguous predicate), `zero_pull_cause` (the fourth cause -- auth
failure -- the brief's zero-row decision tree omits), and `empszes_pairs_from_rows` (deriving
the EMPSZES code/label crosswalk from data-pull rows, since `/variables/EMPSZES.json` carries
no `values.item` for this dataset -- confirmed live, see the module docstring in
`cbp_metadata.py`).

The `MISSING_KEY_PREFIX` / `INVALID_KEY_PREFIX` fixtures below are real byte prefixes captured
from live GET requests to `https://api.census.gov/data/2021/cbp` during this task -- one with
no `key` param at all, one with the actual (invalid) `CENSUS_API_KEY` from this repo's `.env`.
Both came back HTTP 200 with `content-type: text/html` after redirect-following, never 4xx.
Everything else in this file is a synthetic fixture built to exercise shape, not a captured
response -- this run's `CENSUS_API_KEY` does not authenticate, so no real tabular data-pull
body was obtainable to capture.
"""

from __future__ import annotations

import _common
import cbp_metadata as m

# Real prefixes (see module docstring) -- content-type alone is what the classifier keys on,
# so a short prefix is enough; the full pages are ~8.5 KB of unrelated jQuery/CSS boilerplate.
MISSING_KEY_PREFIX = (
    b'<html style="font-size: 14px;">\n\n<head>\n    <title>Missing Key</title>\n'
    b'    <link rel="icon" type="image/x-icon" href="favicon.ico">\n'
)
INVALID_KEY_PREFIX = (
    b'<html style="font-size: 14px;">\n\n<head>\n    <title>Invalid Key</title>\n'
    b'    <link rel="icon" type="image/x-icon" href="favicon.ico">\n'
)
HTML_CONTENT_TYPE = "text/html"
JSON_CONTENT_TYPE = "application/json;charset=utf-8"

# A synthetic but realistically-shaped tabular payload: header row + two data rows, the same
# shape Census's data endpoint returns for `get=...&for=state:*`.
TABULAR_BODY = (
    b'[["NAME","NAICS2017_LABEL","EMPSZES","EMPSZES_LABEL","ESTAB","EMP","EMP_F","EMP_N",'
    b'"state"],'
    b'["Alabama","Logging","251","1 to 4 employees","10","20","","01"],'
    b'["Alaska","Logging","252","5 to 9 employees","5","30","G","02"]]'
)


# --- classify_data_body --------------------------------------------------------------------
#
# Census answers a missing OR invalid key with HTTP 200 after following the redirect to an
# HTML error page -- status alone cannot tell that apart from a real answer. Content-type is
# what discriminates in every fixture below.


def test_classify_missing_key_page_is_auth_error():
    status, payload = m.classify_data_body(HTML_CONTENT_TYPE, MISSING_KEY_PREFIX)
    assert status == "auth_error"
    assert payload is None


def test_classify_invalid_key_page_is_auth_error():
    status, payload = m.classify_data_body(HTML_CONTENT_TYPE, INVALID_KEY_PREFIX)
    assert status == "auth_error"
    assert payload is None


def test_classify_missing_content_type_is_auth_error_not_a_crash():
    """No content-type header at all is exactly as suspicious as an explicit text/html one --
    treated the same way, not trusted by default."""
    status, payload = m.classify_data_body("", b"anything")
    assert status == "auth_error"
    assert payload is None


def test_classify_real_shaped_tabular_json_is_ok():
    status, payload = m.classify_data_body(JSON_CONTENT_TYPE, TABULAR_BODY)
    assert status == "ok"
    assert payload[0][:2] == ["NAME", "NAICS2017_LABEL"]
    assert len(payload) == 3  # header + 2 rows


def test_classify_json_dict_is_bad_shape_not_ok():
    """A dict (e.g. an accidental fetch of dataset.json against the data endpoint) is valid
    JSON but not the list-of-lists tabular shape the data pull must return."""
    status, payload = m.classify_data_body(JSON_CONTENT_TYPE, b'{"not": "tabular"}')
    assert status == "bad_shape"
    assert payload is None


def test_classify_empty_json_list_is_bad_shape():
    """An empty list has no header row -- not a valid answer, however it arose."""
    status, payload = m.classify_data_body(JSON_CONTENT_TYPE, b"[]")
    assert status == "bad_shape"
    assert payload is None


def test_classify_json_list_of_scalars_is_bad_shape():
    status, payload = m.classify_data_body(JSON_CONTENT_TYPE, b"[1, 2, 3]")
    assert status == "bad_shape"
    assert payload is None


def test_classify_malformed_json_with_json_content_type_is_bad_shape_not_a_crash():
    """content-type claims JSON but the body doesn't parse -- must classify, not raise."""
    status, payload = m.classify_data_body(JSON_CONTENT_TYPE, b"{not valid json")
    assert status == "bad_shape"
    assert payload is None


# --- naics_predicate_matches ----------------------------------------------------------------
#
# Real 2021 CBP `variables.json` (fetched live during this task) has exactly one name matching
# `^NAICS[0-9]{4}$` among 28 variables: NAICS2017. The suffixed names below (_LABEL, _F, _TTL)
# are real variable-naming conventions this dataset uses and must NOT match the anchored regex.

REAL_2021_NAMES = [
    "GEO_ID", "NAME", "NAICS2017", "NAICS2017_LABEL", "NAICS2017_F", "EMPSZES",
    "EMPSZES_LABEL", "LFO", "LFO_LABEL", "ESTAB", "EMP", "EMP_F", "EMP_N", "PAYANN",
    "PAYQTR1", "PAYQTR1_F", "for", "in",
]


def test_naics_predicate_matches_the_one_real_2021_variable():
    assert m.naics_predicate_matches(REAL_2021_NAMES) == ["NAICS2017"]


def test_naics_predicate_matches_none_found():
    names = [n for n in REAL_2021_NAMES if not n.startswith("NAICS")]
    assert m.naics_predicate_matches(names) == []


def test_naics_predicate_matches_two_vintages_returns_both_sorted():
    """More than one match must never be silently narrowed -- the caller decides what to do
    with an ambiguous predicate; this function just reports every real match."""
    names = REAL_2021_NAMES + ["NAICS2012"]
    assert m.naics_predicate_matches(names) == ["NAICS2012", "NAICS2017"]


def test_naics_predicate_matches_rejects_suffixed_names():
    """`NAICS2017_LABEL`, `NAICS2017_F` etc. must not match the anchored 4-digit pattern --
    this is what makes REAL_2021_NAMES realistic instead of a strawman fixture."""
    assert m.naics_predicate_matches(["NAICS2017_LABEL", "NAICS2017_F", "NAICS2017_TTL"]) == []


def test_naics_predicate_matches_rejects_wrong_digit_count():
    assert m.naics_predicate_matches(["NAICS17", "NAICS201", "NAICS20177"]) == []


# --- zero_pull_cause -----------------------------------------------------------------------
#
# The brief's zero-row decision tree (Step 3) names three causes: geography absent, query
# still wrong, size crossing unavailable. It has no fourth branch for "every attempt came back
# as an auth-error page" -- an invalid or missing key would otherwise be misread as "the query
# is wrong," which is a script-bug diagnosis for a credential problem.


def test_zero_pull_cause_geography_unavailable_wins_regardless_of_attempts():
    assert m.zero_pull_cause(
        state_available=False, attempt_statuses=["auth_error", "auth_error"]
    ) == "geography_unavailable"


def test_zero_pull_cause_all_auth_error_is_auth_error():
    assert m.zero_pull_cause(
        state_available=True, attempt_statuses=["auth_error", "auth_error", "auth_error"]
    ) == "auth_error"


def test_zero_pull_cause_mixed_statuses_is_query_bug():
    """Not every attempt failed the same way -- a uniform credential failure would fail all
    three identically, so a mix means something about the query itself is wrong."""
    assert m.zero_pull_cause(
        state_available=True, attempt_statuses=["auth_error", "bad_shape", "http_error"]
    ) == "query_bug"


def test_zero_pull_cause_all_http_error_is_query_bug():
    assert m.zero_pull_cause(
        state_available=True, attempt_statuses=["http_error", "http_error", "http_error"]
    ) == "query_bug"


def test_zero_pull_cause_empty_attempt_list_is_query_bug_not_vacuously_auth_error():
    """`all(...)` over an empty list is True in Python -- an empty attempts list must not
    fall through to "auth_error" by that vacuous truth. This is the one case worth pinning
    explicitly: it is the kind of bug that would only ever surface if the attempts loop were
    changed to allow zero attempts, and would otherwise silently misreport the cause."""
    assert m.zero_pull_cause(state_available=True, attempt_statuses=[]) == "query_bug"


# --- empszes_pairs_from_rows -----------------------------------------------------------------
#
# `/variables/EMPSZES.json` and the full `/variables.json` dump both carry no `values` key for
# this dataset (confirmed live against 2021) -- the only place the code/label crosswalk shows
# up is in the data-pull rows themselves, when EMPSZES and EMPSZES_LABEL are both requested as
# unfiltered output columns (attempts 1-2 of the keyed pull do this; attempt 3 does not).


def test_empszes_pairs_from_rows_returns_none_when_columns_absent():
    """Attempt 3 drops EMPSZES entirely -- its rows cannot carry the crosswalk, and this must
    read as "not observed", not as an empty list standing in for "no size classes exist"."""
    header = ["NAME", "NAICS2017_LABEL", "ESTAB", "EMP"]
    body = [["Alabama", "Logging", "10", "20"]]
    assert m.empszes_pairs_from_rows(header, body) is None


def test_empszes_pairs_from_rows_dedupes_across_states_and_sorts_by_code():
    header = ["NAME", "EMPSZES", "EMPSZES_LABEL", "EMP"]
    body = [
        ["Alabama", "251", "1 to 4 employees", "20"],
        ["Alaska", "252", "5 to 9 employees", "30"],
        ["Arizona", "251", "1 to 4 employees", "45"],  # same code+label as Alabama's row
    ]
    assert m.empszes_pairs_from_rows(header, body) == [
        {"code": "251", "label": "1 to 4 employees"},
        {"code": "252", "label": "5 to 9 employees"},
    ]


def test_empszes_pairs_from_rows_returns_empty_list_when_columns_present_but_no_rows():
    """Columns present, zero data rows: a real (if surprising) answer -- distinguish it from
    the None case, which means the columns weren't even asked for."""
    header = ["NAME", "EMPSZES", "EMPSZES_LABEL"]
    assert m.empszes_pairs_from_rows(header, []) == []


def test_common_module_is_importable_alongside_cbp_metadata():
    """Guards the bare sibling-import convention documented in tests/conftest.py -- if this
    ever breaks, every other test in this file would fail for an unrelated reason and be
    confusing to debug."""
    assert _common.INDUSTRY_CODE == "113310"
