"""Judgment-logic tests for `cbp_metadata` (SRC-CBP-001).

Fix round 1 (spec review): `classify_data_body` used to collapse every non-JSON response into
one `"auth_error"` outcome, which would mislabel a Census maintenance page or rate-limit
interstitial as a credential failure. It now reads the HTML `<title>` (`html_title`) and
returns `"invalid_key"` / `"missing_key"` / `"non_json_error"` -- only the first two feed
`zero_pull_cause`'s `"auth_error"` verdict. This file's tests were updated to match, and two
functions were added: `crosswalk_present_in_payload` (whether a fetched metadata document
carries an enumerated `values.item` code list for a given variable, checked across the three
shapes this task's candidate metadata routes can take) and `unavailable_year_reason` (the note
text for a window year outside `years_available`, distinguishing a transport blip from a
confirmed absence).

The `MISSING_KEY_PREFIX` / `INVALID_KEY_PREFIX` fixtures are real byte prefixes captured from
live GET requests to `https://api.census.gov/data/2021/cbp` -- one with no `key` param at all,
one with the `CENSUS_API_KEY` this repo's `.env` carried during this task's development runs,
which those requests showed Census did not accept. Both came back HTTP 200 with `content-type:
text/html` after redirect-following, never 4xx. That is fixture provenance, not a standing
claim about any credential: these bytes pin how `classify_data_body` reads Census's two
key-rejection pages, and they stay valid whatever key a later run uses -- what a given run's
key actually did is `access.status`'s business, recorded in the summary, not theirs.

Fix round 2 (spec review): whether CBP's metadata publishes an EMPSZES code/label crosswalk
turned out to vary by vintage, not to be uniformly absent as fix round 1 assumed from checking
only 2021 by hand. `crosswalk_items_from_payload` was added to extract the actual `{code:
label}` dict (not just a yes/no) from whichever of three candidate shapes carries one; that
function is what both `crosswalk_present_in_payload` (a boolean convenience wrapper around it)
and this test file's crosswalk fixtures below exercise. `REAL_EMPSZES_DOC`, `REAL_GROUPS_DOC`
and `REAL_GROUP_DETAIL_DOC_TRIMMED` are real captured bodies from live GETs to
`/2021/cbp/variables/EMPSZES.json`, `/2021/cbp/groups.json` and
`/2021/cbp/groups/CB2100CBP.json` respectively (the last trimmed to 3 of ~28 variable entries --
noted where used); none of these three 2021 documents carries a `values` key for EMPSZES.
`REAL_2017_EMPSZES_DOC_TRIMMED` is a real captured body from `/2017/cbp/variables/EMPSZES.json`,
trimmed from 44 real code/label pairs to 5 -- and DOES carry one, which is why the two
`crosswalk_present_in_payload`/`crosswalk_items_from_payload` positive-case tests below no
longer need a fabricated fixture (an earlier `SYNTHETIC_DOC_WITH_CROSSWALK` served that purpose
before a real example was found; it has been removed, not merely renamed). Together these
fixtures ground the corrected, year-varying finding: CBP's real 2017 metadata publishes the
official EMPSZES enumeration in the flat variable document, and real 2021 metadata does not
carry it anywhere the three candidate routes were checked. Whether every OTHER available year
matches 2021 or 2017 is not a claim this docstring makes or needs to -- that is measured fresh
each run in `empszes_metadata_crosswalk_probe_by_year`, never asserted from a year checked once
and generalized, which is the mistake fix round 1 made and fix round 2 corrected.
"""

from __future__ import annotations

import json
from pathlib import Path

import _common
import cbp_metadata as m
import httpx

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


# --- html_title ------------------------------------------------------------------------------


def test_html_title_reads_the_missing_key_page():
    assert _common.html_title(MISSING_KEY_PREFIX) == "missing key"


def test_html_title_reads_the_invalid_key_page():
    assert _common.html_title(INVALID_KEY_PREFIX) == "invalid key"


def test_html_title_is_case_insensitive_on_the_tag_itself():
    assert _common.html_title(b"<TITLE>Server Error</TITLE>") == "server error"


def test_html_title_returns_empty_string_when_no_title_tag():
    assert _common.html_title(b"<html><body>no title here</body></html>") == ""


def test_html_title_returns_empty_string_on_non_html_bytes_not_a_crash():
    assert _common.html_title(b"\x00\x01\x02 not html at all") == ""


# --- classify_data_body -----------------------------------------------------------------------
#
# Census answers a missing OR invalid key with HTTP 200 after following the redirect to an HTML
# error page -- status alone cannot tell that apart from a real answer. Content-type is what
# discriminates a real answer from any HTML page; the page's own <title> then discriminates a
# credential rejection (invalid_key / missing_key) from anything else non-JSON
# (non_json_error) -- a maintenance page or rate-limit interstitial must not be mislabeled as a
# credential problem just because it also isn't JSON.


def test_classify_missing_key_page_is_missing_key():
    status, payload = m.classify_data_body(HTML_CONTENT_TYPE, MISSING_KEY_PREFIX)
    assert status == "missing_key"
    assert payload is None


def test_classify_invalid_key_page_is_invalid_key():
    status, payload = m.classify_data_body(HTML_CONTENT_TYPE, INVALID_KEY_PREFIX)
    assert status == "invalid_key"
    assert payload is None


def test_classify_html_with_unrelated_title_is_non_json_error_not_auth():
    """A maintenance page or rate-limit interstitial is non-JSON but is not evidence of a bad
    key -- must not collapse into the same bucket as invalid_key/missing_key."""
    status, payload = m.classify_data_body(
        HTML_CONTENT_TYPE, b"<html><head><title>Service Unavailable</title></head></html>"
    )
    assert status == "non_json_error"
    assert payload is None


def test_classify_missing_content_type_with_no_title_is_non_json_error_not_a_crash():
    """No content-type header and no <title> at all -- still classified, not trusted as data,
    and not guessed to be a key problem without title evidence for it."""
    status, payload = m.classify_data_body("", b"anything")
    assert status == "non_json_error"
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


# --- naics_predicate_matches ------------------------------------------------------------------
#
# Real 2021 CBP `variables.json` (fetched live during this task) has exactly one name matching
# `^NAICS[0-9]{4}$` among 28 variables: NAICS2017. The suffixed names below (_LABEL, _F, _TTL)
# are real variable-naming conventions this dataset uses and must NOT match the anchored regex.

REAL_2021_NAMES = [
    "GEO_ID",
    "NAME",
    "NAICS2017",
    "NAICS2017_LABEL",
    "NAICS2017_F",
    "EMPSZES",
    "EMPSZES_LABEL",
    "LFO",
    "LFO_LABEL",
    "ESTAB",
    "EMP",
    "EMP_F",
    "EMP_N",
    "PAYANN",
    "PAYQTR1",
    "PAYQTR1_F",
    "for",
    "in",
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


# --- zero_pull_cause ---------------------------------------------------------------------------
#
# The brief's zero-row decision tree (Step 3) names three causes: geography absent, query still
# wrong, size crossing unavailable. It has no fourth branch for "every attempt came back as a
# key-rejection page" -- an invalid or missing key would otherwise be misread as "the query is
# wrong," which is a script-bug diagnosis for a credential problem. Only `invalid_key` and
# `missing_key` count as the auth family; `non_json_error` (a maintenance page, a rate-limit
# interstitial, anything else non-JSON) must fall through to `query_bug` rather than being
# assumed to be the same credential problem.


def test_zero_pull_cause_geography_unavailable_wins_regardless_of_attempts():
    assert (
        m.zero_pull_cause(state_available=False, attempt_statuses=["invalid_key", "invalid_key"])
        == "geography_unavailable"
    )


def test_zero_pull_cause_all_invalid_key_is_auth_error():
    assert (
        m.zero_pull_cause(
            state_available=True, attempt_statuses=["invalid_key", "invalid_key", "invalid_key"]
        )
        == "auth_error"
    )


def test_zero_pull_cause_all_missing_key_is_auth_error():
    assert (
        m.zero_pull_cause(state_available=True, attempt_statuses=["missing_key", "missing_key"])
        == "auth_error"
    )


def test_zero_pull_cause_mix_of_invalid_and_missing_key_is_still_auth_error():
    """Both are the same credential family -- a run could plausibly see one attempt redirect
    before key validation and another after, though in practice a constant key within one run
    produces one title consistently."""
    assert (
        m.zero_pull_cause(state_available=True, attempt_statuses=["invalid_key", "missing_key"])
        == "auth_error"
    )


def test_zero_pull_cause_non_json_error_is_query_bug_not_auth_error():
    """This is the finding the fix-round review named directly: a maintenance page or
    rate-limit interstitial is non-JSON but must not be assumed to be a credential problem."""
    assert (
        m.zero_pull_cause(
            state_available=True, attempt_statuses=["non_json_error", "non_json_error"]
        )
        == "query_bug"
    )


def test_zero_pull_cause_mixed_statuses_is_query_bug():
    """Not every attempt failed the same way -- a uniform credential failure would fail all
    three identically, so a mix means something about the query itself is wrong."""
    assert (
        m.zero_pull_cause(
            state_available=True, attempt_statuses=["invalid_key", "bad_shape", "http_error"]
        )
        == "query_bug"
    )


def test_zero_pull_cause_all_http_error_is_query_bug():
    assert (
        m.zero_pull_cause(
            state_available=True, attempt_statuses=["http_error", "http_error", "http_error"]
        )
        == "query_bug"
    )


def test_zero_pull_cause_empty_attempt_list_is_query_bug_not_vacuously_auth_error():
    """`all(...)` over an empty list is True in Python -- an empty attempts list must not
    fall through to "auth_error" by that vacuous truth. This is the one case worth pinning
    explicitly: it is the kind of bug that would only ever surface if the attempts loop were
    changed to allow zero attempts, and would otherwise silently misreport the cause."""
    assert m.zero_pull_cause(state_available=True, attempt_statuses=[]) == "query_bug"


# --- empszes_pairs_from_rows --------------------------------------------------------------------
#
# None of the three 2021 metadata documents captured below (`REAL_EMPSZES_DOC`,
# `REAL_GROUPS_DOC`, `REAL_GROUP_DETAIL_DOC_TRIMMED`) carries a `values` key for EMPSZES, which
# the `crosswalk_present_in_payload` tests further down pin. That is measured of 2021, not of
# the dataset: `REAL_2017_EMPSZES_DOC_TRIMMED` about a hundred lines below DOES carry one, and
# which years and routes a run actually finds one on is recorded per run in
# `empszes_metadata_crosswalk_probe_by_year`, never generalized from a year checked once (the
# module docstring's fix round 2, which this comment used to contradict). So for a vintage
# whose metadata carries none, this function's observation over the data-pull rows is the
# fallback -- available when EMPSZES and EMPSZES_LABEL are both requested as unfiltered output
# columns (attempts 1-2 of the keyed pull do this; attempt 3 does not).
#
# Fix round 1: this list is an OBSERVATION over the 113310 x state slice, not the official
# metadata enumeration SRC-CBP-001 asks for -- a size class with zero logging establishments in
# every state a given year produces no row and is silently absent. main() now wraps this
# function's output in a dict that says so explicitly (`{"scope": "observed_in_113310_state_
# slice", ...}`) rather than persisting a bare list that reads as authoritative. This function
# itself is unchanged; it was never the part that overclaimed.


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


# --- crosswalk_present_in_payload ---------------------------------------------------------------
#
# Fix round 1, Spec 1: SRC-CBP-001 asks for the official EMPSZES enumeration "from metadata".
# The row-derived list above is a substitute, acceptable only if the metadata absence is
# established by probing and recorded as evidence rather than asserted from memory. This
# function is that check, run against every keyless route that could plausibly carry it.

# Real, captured live from /2021/cbp/variables/EMPSZES.json -- no "values" key.
REAL_EMPSZES_DOC = {
    "name": "EMPSZES",
    "label": "Employment size of establishments code",
    "concept": "All Sectors: County Business Patterns, including ZIP Code Business Patterns, by "
    "Legal Form of Organization and Employment Size Class for the U.S., States, and "
    "Selected Geographies: 2021",
    "required": "default displayed",
    "predicateType": "string",
    "group": "CB2100CBP",
    "limit": 0,
    "attributes": "EMPSZES_LABEL",
}

# Real, captured live from /2021/cbp/groups.json -- a group index, no per-variable detail, no
# "values" key anywhere.
REAL_GROUPS_DOC = {
    "groups": [
        {
            "name": "CB2100CBP",
            "description": "All Sectors: County Business Patterns, including ZIP Code Business "
            "Patterns, by Legal Form of Organization and Employment Size Class for "
            "the U.S., States, and Selected Geographies: 2021",
            "variables": "http://api.census.gov/data/2021/cbp/groups/CB2100CBP.json",
        }
    ],
}

# Real, captured live from /2021/cbp/groups/CB2100CBP.json, trimmed from ~28 variable entries to
# the 3 relevant here (EMPSZES, EMPSZES_LABEL, ESTAB) -- EMPSZES's own entry has no "values" key.
REAL_GROUP_DETAIL_DOC_TRIMMED = {
    "variables": {
        "EMPSZES_LABEL": {
            "label": "Meaning of Employment size of establishments code",
            "predicateType": "string",
            "group": "CB2100CBP",
            "limit": 0,
            "predicateOnly": True,
        },
        "ESTAB": {
            "label": "Number of establishments",
            "predicateType": "int",
            "group": "CB2100CBP",
            "limit": 0,
            "predicateOnly": True,
        },
        "EMPSZES": {
            "label": "Employment size of establishments code",
            "required": "default displayed",
            "predicateType": "string",
            "group": "CB2100CBP",
            "limit": 0,
            "predicateOnly": True,
        },
    },
}

# Real, captured live from /2017/cbp/variables/EMPSZES.json, trimmed from 44 real code/label
# pairs to 5 -- fix round 2's finding: this route DOES carry a values.item crosswalk for 2017,
# even though 2018-2023 (REAL_EMPSZES_DOC above, and every year actually checked in round 1)
# do not. No fabricated fixture is needed for the positive case any more.
REAL_2017_EMPSZES_DOC_TRIMMED = {
    "name": "EMPSZES",
    "label": "Employment size of establishments",
    "group": "CB1700CBP",
    "values": {
        "item": {
            "001": "All establishments",
            "204": "Establishments with no paid employees",
            "205": "Establishments with paid employees",
            "207": "Establishments with less than 10 employees",
            "209": "Establishments with less than 20 employees",
        }
    },
}


# --- group_names_from_field -------------------------------------------------------------------
#
# Discovered against the live run of this fix round, not anticipated in advance: 2018's real
# EMPSZES doc has `"group": "CB1800ZBP,CB1800CBP"` -- treating that field as one group name and
# building `groups/{group}.json` from it 404s on the literal comma. Real value below.

REAL_2018_GROUP_FIELD = "CB1800ZBP,CB1800CBP"


def test_group_names_from_field_splits_the_real_2018_multi_group_value():
    assert m.group_names_from_field(REAL_2018_GROUP_FIELD) == ["CB1800ZBP", "CB1800CBP"]


def test_group_names_from_field_single_name_is_a_one_element_list():
    assert m.group_names_from_field("CB2100CBP") == ["CB2100CBP"]


def test_group_names_from_field_none_is_empty_list_not_a_crash():
    assert m.group_names_from_field(None) == []


def test_group_names_from_field_empty_string_is_empty_list():
    assert m.group_names_from_field("") == []


def test_group_names_from_field_strips_whitespace_around_commas():
    assert m.group_names_from_field("CB1800ZBP, CB1800CBP") == ["CB1800ZBP", "CB1800CBP"]


def test_crosswalk_absent_from_real_flat_variable_doc():
    assert m.crosswalk_present_in_payload(REAL_EMPSZES_DOC, "EMPSZES") is False


def test_crosswalk_absent_from_real_groups_index():
    assert m.crosswalk_present_in_payload(REAL_GROUPS_DOC, "EMPSZES") is False


def test_crosswalk_absent_from_real_group_detail_doc():
    """The group document lists many variables under payload["variables"] -- this checks
    EMPSZES's own entry within it, not just the top level."""
    assert m.crosswalk_present_in_payload(REAL_GROUP_DETAIL_DOC_TRIMMED, "EMPSZES") is False


def test_crosswalk_present_for_the_real_2017_doc():
    assert m.crosswalk_present_in_payload(REAL_2017_EMPSZES_DOC_TRIMMED, "EMPSZES") is True


def test_crosswalk_present_when_values_item_exists_under_group_variables():
    """Same positive shape, but nested the way a /groups/{group}.json document would carry
    it -- under payload["variables"][variable], not the top level."""
    payload = {"variables": {"EMPSZES": {"values": {"item": {"001": "All establishments"}}}}}
    assert m.crosswalk_present_in_payload(payload, "EMPSZES") is True


def test_crosswalk_check_is_scoped_to_the_named_variable():
    """A different variable in the same group document carrying `values` must not make
    EMPSZES's check return True -- the crosswalk has to belong to the variable being asked
    about, not just exist anywhere in the payload."""
    payload = {
        "variables": {
            "OTHER_VAR": {"values": {"item": {"1": "something"}}},
            "EMPSZES": {"label": "no values key here"},
        }
    }
    assert m.crosswalk_present_in_payload(payload, "EMPSZES") is False


def test_crosswalk_present_in_payload_handles_non_dict_values_key_without_crashing():
    """A malformed or unexpected payload (e.g. `values` present but not a dict) must classify
    as absent, not raise."""
    assert m.crosswalk_present_in_payload({"values": "not a dict"}, "EMPSZES") is False


# --- crosswalk_items_from_payload ---------------------------------------------------------------
#
# Fix round 2: the boolean check above answers "does a crosswalk exist"; this function answers
# "what is it" -- the actual {code: label} dict, needed to populate empszes_by_year with the
# real 2017 enumeration rather than just a yes/no.


def test_crosswalk_items_from_payload_returns_the_real_2017_pairs():
    items = m.crosswalk_items_from_payload(REAL_2017_EMPSZES_DOC_TRIMMED, "EMPSZES")
    assert items == {
        "001": "All establishments",
        "204": "Establishments with no paid employees",
        "205": "Establishments with paid employees",
        "207": "Establishments with less than 10 employees",
        "209": "Establishments with less than 20 employees",
    }


def test_crosswalk_items_from_payload_returns_none_for_real_absent_vintages():
    assert m.crosswalk_items_from_payload(REAL_EMPSZES_DOC, "EMPSZES") is None
    assert m.crosswalk_items_from_payload(REAL_GROUPS_DOC, "EMPSZES") is None
    assert m.crosswalk_items_from_payload(REAL_GROUP_DETAIL_DOC_TRIMMED, "EMPSZES") is None


def test_crosswalk_items_from_payload_reads_the_nested_group_shape():
    payload = {"variables": {"EMPSZES": {"values": {"item": {"001": "All establishments"}}}}}
    assert m.crosswalk_items_from_payload(payload, "EMPSZES") == {"001": "All establishments"}


def test_crosswalk_items_from_payload_scoped_to_the_named_variable():
    payload = {
        "variables": {
            "OTHER_VAR": {"values": {"item": {"1": "something"}}},
            "EMPSZES": {"label": "no values key here"},
        }
    }
    assert m.crosswalk_items_from_payload(payload, "EMPSZES") is None


def test_crosswalk_items_from_payload_handles_non_dict_values_key_without_crashing():
    assert m.crosswalk_items_from_payload({"values": "not a dict"}, "EMPSZES") is None


# --- unavailable_year_reason ---------------------------------------------------------------------
#
# Fix round 1, Spec 2 + Important 4: every window year needs an explicit note, whether its
# `cbp.json` probe returned a transport-failure sentinel (0) or a real, confirmed non-200
# status (e.g. 2024's 404) -- the two are different facts to a Task 8 reader and the note text
# must not claim a distinction the rest of the artifact doesn't honor (the fix-round review
# caught exactly that self-contradiction in the prior version).


def test_unavailable_year_reason_zero_status_names_a_transport_failure():
    reason = m.unavailable_year_reason(0)
    assert "transport failure" in reason
    assert "not a confirmed absence" in reason


def test_unavailable_year_reason_404_names_the_real_status_without_overclaiming():
    reason = m.unavailable_year_reason(404)
    assert "404" in reason
    # Does not assert "confirmed absence" wording for a bare non-200 status in general -- a
    # 5xx would be a server error, not evidence the year isn't published. Only the literal
    # status is reported; the reader interprets a 404 as absence, a 5xx as something else.
    assert "confirmed absence" not in reason


def test_unavailable_year_reason_distinguishes_0_from_a_real_status():
    assert m.unavailable_year_reason(0) != m.unavailable_year_reason(404)


def test_common_module_is_importable_alongside_cbp_metadata():
    """Guards the bare sibling-import convention documented in tests/conftest.py -- if this
    ever breaks, every other test in this file would fail for an unrelated reason and be
    confusing to debug."""
    assert _common.INDUSTRY_CODE == "113310"


def test_classify_data_body_is_case_insensitive_on_the_content_type():
    """Media types are case-insensitive (RFC 9110 8.3.1), and Census could legally answer
    `application/JSON`. The check was `"json" not in content_type`, so that spelling fell to
    the HTML branch, where a real tabular answer -- carrying no `<title>` -- came back
    `non_json_error`: a successful pull read as a source failure. `forest_sources`'s
    `is_machine_readable` already lowercased; this did not."""
    for spelling in ("application/JSON", "APPLICATION/JSON;CHARSET=UTF-8", "Application/Json"):
        status, payload = m.classify_data_body(spelling, TABULAR_BODY)
        assert status == "ok", spelling
        assert payload[0][0] == "NAME"


# --- manifest hygiene: cfe0c1f's two orphan-file failure modes ----------------------------------
#
# cfe0c1f closed both and shipped no test, so nothing held either invariant. They are the same
# invariant from two directions: every file left under `data/raw/audit/` must be registered in
# a summary's `extracts`, and a run must never leave a previous run's file looking current.


def test_fetch_json_or_none_reports_a_404_without_registering_an_extract(tmp_path, monkeypatch):
    """Direction one. A keyless metadata route answering 404 used to crash the run inside
    `c.request`, after this run's earlier extracts were written to disk and before
    `write_summary` could register them -- every one of them an orphan. The status is returned
    as the documented gap instead, and nothing is recorded for a body that never arrived."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    extracts: list = []
    status, payload = m.fetch_json_or_none(
        client, "cbp_metadata", "https://example.invalid/groups.json", "2021/groups.json", extracts
    )
    assert (status, payload) == (404, None)
    assert extracts == []
    assert list(tmp_path.rglob("*")) == [], "a route that did not answer must leave no file"


def test_a_200_with_a_non_json_body_records_nothing_and_does_not_raise(tmp_path, monkeypatch):
    """The third direction, and the one the guard itself was reaching.

    `record_extract` ran BEFORE `resp.json()`, and only `HTTPStatusError` was caught. Census
    serves an HTML error page with status 200, so the file was written to disk and appended to
    `extracts`, and only then did `resp.json()` raise -- leaving exactly the dangling-manifest
    state this function exists to prevent, reached through the function itself. A body that is
    not JSON is not evidence, so nothing is recorded and the caller is told the route produced
    nothing usable.
    """
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"<html><title>error</title></html>")
        )
    )
    extracts: list = []
    status, payload = m.fetch_json_or_none(
        client, "cbp_metadata", "https://example.invalid/x.json", "2021/dataset.json", extracts
    )
    assert (status, payload) == (200, None)
    assert extracts == []
    assert list(tmp_path.rglob("*")) == [], "a body that could not be used must leave no file"


def test_fetch_json_or_none_registers_exactly_one_extract_on_a_real_answer(tmp_path, monkeypatch):
    """The other direction of the same guard: the swallow is scoped to the failure. A route
    that does answer is still parsed and still recorded, or the fix would trade a crash for a
    silently unfetched probe."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    body = {"variables": {"EMPSZES": {"label": "Employment size of establishments"}}}
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
    )
    extracts: list = []
    status, payload = m.fetch_json_or_none(
        client, "cbp_metadata", "https://example.invalid/v.json", "2021/variables.json", extracts
    )
    assert status == 200
    assert payload == body
    assert [Path(e.path).name for e in extracts] == ["variables.json"]
    assert (tmp_path / "cbp_metadata" / "2021" / "variables.json").exists()


def test_main_wipes_a_year_directory_before_the_probe_can_skip_it(tmp_path, monkeypatch, capsys):
    """Direction two, and the ordering that carries it. The year-directory wipe runs before
    `c.probe`, so no exit path can skip it: a year whose probe comes back non-200 this run
    still loses whatever an earlier run left behind. Moving the wipe back inside the
    `status == 200` branch -- where fix round 2 had it -- would leave a previous run's
    `data_113310.json` sitting at the exact filename the plan's Produces block names,
    registered by nothing in this run's summary and looking current to anything that opens the
    path instead of the manifest. Every one of the 605 tests before this one passed with the
    wipe in that position."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setattr(_common, "probe", lambda *args, **kwargs: (404, 0))
    # `main` refuses to start without one. Set to a placeholder rather than inherited, so this
    # test behaves the same whether or not the suite was run with `.env` sourced, and never
    # puts a real credential anywhere near `record_extract`'s secret scan.
    monkeypatch.setenv("CENSUS_API_KEY", "placeholder-key-never-sent-anywhere")
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "audit-suite@example.invalid")
    stale = tmp_path / "cbp_metadata" / "2017" / "data_113310.json"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b'[["NAME","EMP"],["Alabama","20"]]')

    m.main()

    assert not stale.exists(), "a previous run's canonical file survived a non-200 probe year"
    assert not stale.parent.exists()
    written = json.loads((tmp_path / "cbp_metadata" / "summary.json").read_text(encoding="utf-8"))
    assert written["extracts"] == []
    assert written["findings"]["years_available"] == []


# --- the module docstring's own claims ----------------------------------------------------------
#
# Prose-only claims, returned by no function, so `m.__doc__` is the only place they live and the
# only place a regression could reintroduce one -- the same reason `test_susb_layout.py` pins its
# module docstring directly.


def _flat(text: str) -> str:
    """Docstring text with its line wrapping collapsed, so these assertions survive a reflow."""
    return " ".join(text.split())


def test_docstring_does_not_state_the_env_key_failure_as_a_standing_fact():
    """Whole-branch review, finding 1: the claim that aged in-branch. Point 3 opened "A key
    genuinely present in this repo's `.env` does not authenticate" and concluded that every
    keyed request "is therefore expected to fail" -- unhedged present tense, true at Task 7
    review time. A later run with a working credential recorded `access.status: "verified"`
    with 179-190 rows for each of 2017-2023, and seven `data_113310.json` extracts at HTTP 200
    are in the tracked manifest. Point 2 of the same docstring was already run-scoped ("checked
    this run"); point 3's present tense was the anomaly. Negative pin, because a regression
    could re-add the sentence beside the corrected one and leave a presence-only check green."""
    doc = _flat(m.__doc__)
    assert "does not authenticate" not in doc
    assert "Every keyed request in a run against this credential is therefore expected" not in doc


def test_docstring_scopes_the_env_key_failure_to_the_runs_that_observed_it():
    """The other half: the invalid-key episode is why `classify_data_body` and
    `zero_pull_cause` exist, so it is re-scoped rather than deleted, and the docstring points
    at the summary for what any given run's credential actually did."""
    doc = _flat(m.__doc__)
    assert "during this task's development runs, the key then in `.env` did not" in doc
    assert "a later run with a working key succeeded" in doc


def test_the_keyless_crosswalk_comment_does_not_claim_every_year_failed():
    """Same claim, second site: the inline comment beside the official-crosswalk branch used to
    qualify "even when the keyed pull itself fails" with "(this run, for every year)". Read
    from the source rather than `__doc__`, since a comment is not reachable at runtime."""
    source = Path(m.__file__).read_text(encoding="utf-8")
    assert "(this run, for every year)" not in source
    assert "Which years a run's keyed pull actually failed for is read off" in source


def test_variable_names_reports_an_unreadable_body_rather_than_raising_keyerror():
    """`payload["variables"]` was indexed directly, so a body that parsed but carried no
    `variables` key raised KeyError mid-loop. None distinguishes "could not read" from a year
    that genuinely lists no variables."""
    assert m.variable_names({"variables": {"EMPSZES": {}, "LFO": {}}}) == ["EMPSZES", "LFO"]
    assert m.variable_names({"variables": {}}) == []
    assert m.variable_names({"dataset": "cbp"}) is None
    assert m.variable_names(None) is None


def test_geography_levels_keeps_an_unreadable_document_apart_from_one_lacking_state():
    """The silent-wrong path: `.get("fips", [])` on a malformed body yields [], which reaches
    `zero_pull_cause` as state_available=False and is persisted as "geography_unavailable" -- a
    fetch failure recorded as a measured fact about CBP. None keeps the two apart."""
    assert m.geography_levels({"fips": [{"name": "state"}, {"name": "us"}]}) == ["state", "us"]
    assert m.geography_levels({"fips": []}) == []
    assert m.geography_levels({"error": "nope"}) is None
    assert m.geography_levels(None) is None
