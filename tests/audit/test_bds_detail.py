"""Judgment-logic tests for `bds_detail` (SRC-OTH-002), pinned before the live NAICS-detail
probes run.

This implementation departs from the brief's illustrative code in three places: two defects and
one deviation. The two defects are enumerated below and were confirmed live against
`https://api.census.gov/data/timeseries/bds` during this task, not from memory. The third
departure -- a dropped fallback branch in the `uncovered` computation -- is a deviation, named
that way because it describes an action this implementation took rather than a flaw found in
the brief; it is disclosed in the task report only, since no live run ever exercised it:

1. **This run met HTTP 204 with a zero-length body for every candidate NAICS predicate that
   matched no published cell -- never a 404 and never a 200 with an empty `[header]`-only JSON
   array.** Confirmed live for every candidate finer than `'11'` this run (`'113'`, `'1133'`,
   `'11331'`, `'113310'`), and for nonsense predicates (`'999999'`, `'abc'`) tried during this
   task's investigation. What this run met, not a documented property of the endpoint in
   general -- see `bds_detail.py`'s module docstring, point 1, for the same scoping.
   204 is a 2xx status, so `resp.raise_for_status()` never raises and the brief's
   `except httpx.HTTPStatusError` never fires; the brief then calls `resp.json()` on the empty
   body, which raises `json.JSONDecodeError` -- uncaught, crashing the script on the very first
   candidate finer than the sector level. `classify_probe_body` checks `status == 204` before
   ever attempting to parse the body, so this is a distinct, named outcome (`"no_content"`)
   rather than a crash or a `bad_shape` guess.
2. **A missing or invalid `CENSUS_API_KEY` answers HTTP 200 with an HTML error page**, the same
   trap `cbp_metadata.py`'s `classify_data_body` was built to catch -- reused here as the same
   content-type + `<title>` approach (`html_title`), not reinvented. `MISSING_KEY_PREFIX` and
   `INVALID_KEY_PREFIX` below are real byte prefixes captured live from this endpoint during
   this task with no `key` param and with a syntactically-plausible wrong key, respectively --
   both HTTP 200, `content-type: text/html`, never a 4xx.

`bds_detail` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import bds_detail as m

MISSING_KEY_PREFIX = (
    b'<html style="font-size: 14px;">\n\n<head>\n    <title>Missing Key</title>\n'
    b'    <link rel="icon" type="image/x-icon" href="favicon.ico">\n'
)
INVALID_KEY_PREFIX = (
    b'<html style="font-size: 14px;">\n\n<head>\n    <title>Invalid Key</title>\n'
    b'    <link rel="icon" type="image/x-icon" href="favicon.ico">\n'
)
JSON_CONTENT_TYPE = "application/json;charset=utf-8"
HTML_CONTENT_TYPE = "text/html"

# A synthetic but realistically-shaped tabular payload: header row + two data rows, the same
# shape this endpoint's `get=YEAR,ESTAB&for=state:*&NAICS=...` returns for a matching predicate
# (confirmed live for NAICS=11: header ["YEAR","ESTAB","NAICS","state"], 2346 rows, 51 states,
# years 1978-2023, every row's NAICS value literally "11").
TABULAR_BODY = (
    b'[["YEAR","ESTAB","NAICS","state"],'
    b'["1978","1345","11","01"],'
    b'["1979","1287","11","01"]]'
)


# --- html_title --------------------------------------------------------------------------------


def test_html_title_reads_the_missing_key_page():
    assert m.html_title(MISSING_KEY_PREFIX) == "missing key"


def test_html_title_reads_the_invalid_key_page():
    assert m.html_title(INVALID_KEY_PREFIX) == "invalid key"


def test_html_title_is_case_insensitive_on_the_tag_itself():
    assert m.html_title(b"<TITLE>Server Error</TITLE>") == "server error"


def test_html_title_returns_empty_string_when_no_title_tag():
    assert m.html_title(b"<html><body>no title here</body></html>") == ""


def test_html_title_returns_empty_string_on_non_html_bytes_not_a_crash():
    assert m.html_title(b"\x00\x01\x02 not html at all") == ""


# --- classify_probe_body ------------------------------------------------------------------------
#
# Branches, enumerated: a transport failure (no response at all); a syntactically valid
# predicate matching no cell (204, empty body); a missing/invalid key rejection page (200,
# HTML, known <title>); an unrelated non-JSON response (200, HTML, unknown <title> -- a
# maintenance page or rate-limit interstitial, which must NOT be folded into the same bucket
# as a key rejection); a JSON body that isn't the tabular header-plus-rows shape; and a real
# tabular answer.


def test_classify_transport_failure_is_its_own_outcome():
    """Status 0 is this script's convention (matching `_common.probe`'s sentinel) for "no
    response at all" -- must be named distinctly, not folded into any body-based outcome."""
    outcome, payload = m.classify_probe_body(0, "", b"")
    assert outcome == "transport_failure"
    assert payload is None


def test_classify_204_is_no_content_not_bad_shape_and_not_a_crash():
    """The central live finding this task exists to catch: a 204 with a JSON content-type and
    an empty body is what this run met whenever a candidate predicate matched no published cell
    (module docstring point 1) -- not an error to retry and not a malformed response, so it
    must not collapse into "bad_shape"."""
    outcome, payload = m.classify_probe_body(204, JSON_CONTENT_TYPE, b"")
    assert outcome == "no_content"
    assert payload is None


def test_classify_204_is_no_content_regardless_of_content_type_header():
    """Confirmed live that 204's content-type header still reads application/json, but the
    classification must not depend on that -- status 204 is checked first."""
    outcome, payload = m.classify_probe_body(204, "", b"")
    assert outcome == "no_content"
    assert payload is None


def test_classify_missing_key_page_is_missing_key():
    outcome, payload = m.classify_probe_body(200, HTML_CONTENT_TYPE, MISSING_KEY_PREFIX)
    assert outcome == "missing_key"
    assert payload is None


def test_classify_invalid_key_page_is_invalid_key():
    outcome, payload = m.classify_probe_body(200, HTML_CONTENT_TYPE, INVALID_KEY_PREFIX)
    assert outcome == "invalid_key"
    assert payload is None


def test_classify_html_with_unrelated_title_is_non_json_error_not_auth():
    """A maintenance page or rate-limit interstitial is non-JSON but is not evidence of a bad
    key -- must not collapse into the same bucket as invalid_key/missing_key."""
    outcome, payload = m.classify_probe_body(
        200, HTML_CONTENT_TYPE, b"<html><head><title>Service Unavailable</title></head></html>")
    assert outcome == "non_json_error"
    assert payload is None


def test_classify_missing_content_type_with_no_title_is_non_json_error_not_a_crash():
    outcome, payload = m.classify_probe_body(200, "", b"anything")
    assert outcome == "non_json_error"
    assert payload is None


def test_classify_real_shaped_tabular_json_is_ok():
    outcome, payload = m.classify_probe_body(200, JSON_CONTENT_TYPE, TABULAR_BODY)
    assert outcome == "ok"
    assert payload[0] == ["YEAR", "ESTAB", "NAICS", "state"]
    assert len(payload) == 3  # header + 2 rows


def test_classify_json_dict_is_bad_shape_not_ok():
    outcome, payload = m.classify_probe_body(200, JSON_CONTENT_TYPE, b'{"not": "tabular"}')
    assert outcome == "bad_shape"
    assert payload is None


def test_classify_empty_json_list_is_bad_shape():
    """An empty list has no header row -- not a valid answer, however it arose. Distinct from
    the 204 empty-body case, which never reaches JSON parsing at all."""
    outcome, payload = m.classify_probe_body(200, JSON_CONTENT_TYPE, b"[]")
    assert outcome == "bad_shape"
    assert payload is None


def test_classify_json_list_of_scalars_is_bad_shape():
    outcome, payload = m.classify_probe_body(200, JSON_CONTENT_TYPE, b"[1, 2, 3]")
    assert outcome == "bad_shape"
    assert payload is None


def test_classify_malformed_json_with_json_content_type_is_bad_shape_not_a_crash():
    outcome, payload = m.classify_probe_body(200, JSON_CONTENT_TYPE, b"{not valid json")
    assert outcome == "bad_shape"
    assert payload is None


# --- probe_result --------------------------------------------------------------------------


def test_probe_result_ok_reports_row_count_and_years_from_the_payload():
    header_and_rows = [
        ["YEAR", "ESTAB", "NAICS", "state"],
        ["1979", "1287", "11", "01"],
        ["1978", "1345", "11", "02"],
    ]
    row = m.probe_result("11", 200, "ok", header_and_rows)
    assert row == {
        "naics": "11", "digits": 2, "http_status": 200,
        "row_count": 2, "years_returned": [1978, 1979],
    }


def test_probe_result_no_content_reports_zero_rows_and_no_years():
    row = m.probe_result("113310", 204, "no_content", None)
    assert row["http_status"] == 204
    assert row["row_count"] == 0
    assert row["years_returned"] == []


def test_probe_result_auth_rejection_reports_zero_rows_not_a_crash():
    row = m.probe_result("113", 200, "invalid_key", None)
    assert row["row_count"] == 0
    assert row["years_returned"] == []


def test_probe_result_transport_failure_reports_status_zero_and_zero_rows():
    row = m.probe_result("1133", 0, "transport_failure", None)
    assert row["http_status"] == 0
    assert row["row_count"] == 0


def test_probe_result_digits_is_the_candidate_string_length():
    assert m.probe_result("11331", 204, "no_content", None)["digits"] == 5


def test_probe_result_ok_with_header_only_payload_is_zero_rows_not_a_crash():
    """A valid tabular "ok" response with a header but no data rows is a legitimate (if
    unobserved live) shape -- must report zero rows cleanly, not index-error."""
    row = m.probe_result("11", 200, "ok", [["YEAR", "ESTAB", "NAICS", "state"]])
    assert row["row_count"] == 0
    assert row["years_returned"] == []


def test_probe_result_ok_without_year_column_reports_rows_but_no_years():
    """Defensive branch: this script always requests `get=YEAR,ESTAB`, so a real response
    always carries YEAR, but a caller passing a differently-shaped "ok" payload must still get
    a row_count (rows genuinely exist) without years_returned guessing an index that isn't
    there."""
    row = m.probe_result("11", 200, "ok", [["ESTAB", "NAICS", "state"], ["10", "11", "01"]])
    assert row["row_count"] == 1
    assert row["years_returned"] == []


# --- zero_answer_cause ---------------------------------------------------------------------------
#
# Reached only when even the 2-digit sector code -- which every live run so far has found
# answering -- returned no rows. Must distinguish a uniform credential rejection from a uniform
# network outage from anything else, so a reader is never told "no NAICS code returned rows"
# when the real cause was a broken credential or a dead network.


def test_zero_answer_cause_all_invalid_key_is_auth_error():
    assert m.zero_answer_cause(["invalid_key"] * 5) == "auth_error"


def test_zero_answer_cause_all_missing_key_is_auth_error():
    assert m.zero_answer_cause(["missing_key"] * 5) == "auth_error"


def test_zero_answer_cause_mix_of_invalid_and_missing_key_is_still_auth_error():
    assert m.zero_answer_cause(["invalid_key", "missing_key", "invalid_key"]) == "auth_error"


def test_zero_answer_cause_all_transport_failure_is_network_unreachable():
    assert m.zero_answer_cause(["transport_failure"] * 5) == "network_unreachable"


def test_zero_answer_cause_all_no_content_is_the_generic_boundary_cause():
    """Every candidate, including '11', answering 204 is a real (if drastic) industry-detail
    finding, not a credential or network problem -- must fall through to the generic cause."""
    assert m.zero_answer_cause(["no_content"] * 5) == "no_naics_code_returned_rows"


def test_zero_answer_cause_mixed_statuses_is_the_generic_cause():
    assert m.zero_answer_cause(
        ["invalid_key", "no_content", "transport_failure"]
    ) == "no_naics_code_returned_rows"


def test_zero_answer_cause_all_non_json_error_is_the_generic_cause_not_auth():
    """A maintenance page or rate-limit interstitial repeated across every attempt is still not
    evidence of a credential problem."""
    assert m.zero_answer_cause(["non_json_error"] * 5) == "no_naics_code_returned_rows"


def test_zero_answer_cause_all_bad_shape_is_the_generic_cause():
    assert m.zero_answer_cause(["bad_shape"] * 5) == "no_naics_code_returned_rows"


def test_zero_answer_cause_empty_outcomes_is_the_generic_cause_not_a_crash():
    """Not reached by `main` (outcomes always has one entry per candidate), but a pure function
    must not crash on its own domain's empty case -- `all(...)` over an empty list is
    vacuously True, so the auth/network branches must guard on non-empty explicitly, which
    they do (`outcomes and all(...)`)."""
    assert m.zero_answer_cause([]) == "no_naics_code_returned_rows"


# --- probe_query_scope ---------------------------------------------------------------------------
#
# Point 7 (the dispatch): a verdict about "which NAICS level BDS answers" is a verdict about the
# one `get=`/`for=` predicate this run actually queried under, and that scope must be read out
# of the same params dict the request loop builds, not retyped as a separate literal beside it
# -- otherwise a future change to the query shape (e.g. `for=us:*` instead of `state:*`) would
# silently stop matching what the persisted finding claims.


def test_probe_query_scope_reads_get_and_for_from_the_actual_request_params():
    params = {"get": "YEAR,ESTAB", "for": "state:*", "NAICS": "113310", "key": "shhh"}
    assert m.probe_query_scope(params) == {"get": "YEAR,ESTAB", "for": "state:*"}


def test_probe_query_scope_excludes_naics_and_key():
    """NAICS varies per probe (already recorded per-row in naics_probe) and key is a secret --
    neither belongs in a scope finding meant to describe what's constant across every probe."""
    params = {"get": "YEAR,ESTAB", "for": "state:*", "NAICS": "11", "key": "shhh"}
    scope = m.probe_query_scope(params)
    assert "NAICS" not in scope
    assert "key" not in scope


# --- compose_retention_rule ----------------------------------------------------------------------


def test_compose_retention_rule_counts_the_retained_non_200_bodies():
    # Ruling D-B: this task's 204 bodies are empty -- a status the brief's illustrative code
    # never anticipated -- and http_status alone, not those bodies, distinguishes "not
    # published at this NAICS level" from either 200 outcome. Only "reachable but blocked"
    # vs. a real answer -- both 200 -- actually turns on the retained bytes.
    rule = m.compose_retention_rule([200, 204, 204, 204, 204])
    assert rule["extracts_recorded"] == 5
    assert rule["extracts_with_non_200_status"] == 4
    assert rule["non_200_statuses_recorded"] == [204]


def test_compose_retention_rule_on_an_all_200_run_records_zero_without_omitting_the_rule():
    rule = m.compose_retention_rule([200, 200])
    assert rule["extracts_with_non_200_status"] == 0
    assert rule["non_200_statuses_recorded"] == []
    assert rule["rule"]


def test_compose_retention_rule_warns_the_reader_not_to_generalise_it_to_other_sources():
    rule = m.compose_retention_rule([200, 204])
    assert "is not evidence" in rule["rule"]


def test_compose_retention_rule_discloses_the_status_200_zero_row_ambiguity():
    """Fix round 1 (self-review): the first draft claimed findings.naics_probe always tells a
    status-200 parse failure apart from a status-200 real answer, which is false in the one
    shape row_count can't distinguish -- a header-only real answer vs. a malformed body, both
    status 200 and both row_count 0. The rule text must disclose that gap, not claim it away."""
    rule = m.compose_retention_rule([200, 204])
    assert "header row and zero data rows" in rule["rule"]


def test_compose_retention_rule_attributes_the_204_vs_200_split_to_http_status():
    """Fix round 1 (external review), item 1: the first draft claimed that a 204 with an empty
    body, a 200 auth-rejection page, and a 200 real answer are "three different verdicts and
    only the retained bytes tell them apart." False for the 204 case -- its retained body is
    zero bytes, carrying no discriminating information; http_status alone (200 vs. 204) already
    separates it from either 200 outcome, and the rule's own prior sentence already says so."""
    rule = m.compose_retention_rule([200, 204])
    assert "http_status alone" in rule["rule"]


def test_compose_retention_rule_reserves_the_retained_bytes_claim_for_the_two_200_outcomes():
    """Fix round 1, item 1 continued: "only the retained bytes tell them apart" is only true of
    the 200-auth-rejection vs. 200-real-answer split, where http_status is identical for both
    and inspecting the body is the only way to tell them apart. The rule text must scope that
    claim to those two outcomes, not extend it to the 204 case as well."""
    rule = m.compose_retention_rule([200, 204])
    assert "only the retained bytes tell the two 200 outcomes" in rule["rule"]


def test_compose_retention_rule_no_longer_claims_three_verdicts_need_the_retained_bytes():
    """Fix round 1, item 1 -- negative pin (green-only; the false phrase was already gone by the
    time this test was added, per the advisor's note that a presence-only assertion doesn't pin
    a defect that is an overclaim, only its replacement). The pre-fix text asserted "a 204 ...,
    a 200 auth-rejection HTML page, and a 200 real tabular answer are three different verdicts
    and only the retained bytes tell them apart" -- false for the 204 leg. This asserts that
    exact false phrase is gone, so a regression that re-adds it as an extra sentence (leaving
    the two corrected sentences from the other two tests in place) would still be caught."""
    rule = m.compose_retention_rule([200, 204])
    assert "three different verdicts" not in rule["rule"]


def test_compose_retention_rule_states_why_the_204_body_is_retained():
    """Fix round 1, item 1 follow-up (advisor pass): the deleted "a non-200 body IS the
    evidence" clause was both the false claim and the stated reason a zero-byte 204 body is
    worth retaining at all. The corrected rule must still say why -- the retained-but-empty
    body is what turns the 204 into a recorded observation, not just what http_status already
    tells a reader."""
    rule = m.compose_retention_rule([200, 204])
    assert "recorded observation" in rule["rule"]


def test_compose_retention_rule_covers_the_variables_fetch_its_counters_already_count():
    """Whole-branch review, finding 7. The rule read "a fetched body from the five NAICS-detail
    probes" while `extracts_recorded` is `len(extract_statuses)` over ALL extracts, including
    the separate `variables.json` fetch -- so the shipped artifact said `extracts_recorded: 6`
    under a sentence about five things, and that fetch was retained under no stated rule at
    all. `susb_layout.py`'s own rule text cites "bds_detail.py's own precedent for its single
    non-probed variables.json fetch", i.e. SUSB documented a BDS behaviour BDS did not.

    Fixed by widening the rule's domain, not by narrowing the counters: deriving them over the
    probe extracts only would change a measured value (6 -> 5) in a shipped artifact to fix a
    wording defect."""
    rule = m.compose_retention_rule([200, 200, 204, 204, 204, 204])
    assert rule["extracts_recorded"] == 6
    text = rule["rule"]
    assert "two kinds of fetch and registers a body from both" in text
    assert "variables.json" in text
    assert "the sixth extract whenever all five probes answer" in text
    assert "registers a fetched body from the five NAICS-detail probes whenever" not in text


def test_compose_retention_rule_counters_are_unchanged_by_the_domain_widening():
    """The counters are the measured half and must be byte-identical to what shipped: the fix
    was to the sentence above them. Pinned against this run's real shipped triple."""
    rule = m.compose_retention_rule([200, 200, 204, 204, 204, 204])
    assert rule["extracts_recorded"] == 6
    assert rule["extracts_with_non_200_status"] == 4
    assert rule["non_200_statuses_recorded"] == [204]


def test_classify_probe_body_is_case_insensitive_on_the_content_type():
    """Same fix as `cbp_metadata.classify_data_body`, made in both places: media types are
    case-insensitive (RFC 9110 8.3.1), so `application/JSON` must not fall to the HTML-error
    branch and be classified `non_json_error` by its absent `<title>`."""
    for spelling in ("application/JSON", "APPLICATION/JSON;CHARSET=UTF-8", "Application/Json"):
        outcome, payload = m.classify_probe_body(200, spelling, TABULAR_BODY)
        assert outcome == "ok", spelling
        assert payload is not None
