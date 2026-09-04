"""Judgment-logic tests for `cbp_regime` (SRC-CBP-003), written before the script exists.

Two defect classes this task's dispatch named directly are what these tests pin down.

First, the null-vs-empty-string coercion: `cbp_metadata.py`'s `flag_values_by_year` computes
`(row[idx[col]] or "")`, which collapses a genuine JSON `null` (no flag present) and a genuine
empty string (a flag whose value is `""`) into the same `""` key -- the exact bug this task's
dispatch says to avoid repeating. `flag_value_key`/`flag_evidence` below are pinned against a
raw body carrying `None`, `""` and `"a"` in the same column, and must keep three distinct keys,
not two.

Second, the "hardcode 'unknown' or hardcode a citation" trap: `unknown` is only a defensible
answer when no year-specific Census documentation was actually fetched this run, and every
non-`unknown` regime needs a citation whose URL this run genuinely fetched (not merely typed).
`validate_regime_entry` is the mechanical version of the brief's Step 4 bash check, enforced at
write time instead of as an after-the-fact assertion a human has to remember to run.

`REGIME_BY_YEAR` (the auditor's hand-authored per-year regime literal, grounded in
https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html's
"Protecting Confidentiality > Noise Infusion" section and, for 2017 only, the year-specific
record layout at .../records-layouts/2017_record_layouts/state_layout_2017.txt -- both fetched
live during this task, see cbp_regime.py's module docstring for what each entry rests on) is
exercised here as data, not re-derived: every entry must independently satisfy
`validate_regime_entry` against `DOC_URLS`' own URL set (a static stand-in for "this run's
successfully fetched URLs" that doesn't require a live fetch to check), and 2024 -- the one
confirmed-absent window year -- must be `unknown`.

`cbp_regime` is imported bare, like `_common` and every other audit script under test, per
`PYTHONPATH=scripts/audit`. Importing it is inert: `main()`'s network calls sit behind
`if __name__ == "__main__"`.
"""

from __future__ import annotations

import pytest

import _common as c
import cbp_regime as m

# --- flag_value_key ---------------------------------------------------------------------------


def test_flag_value_key_maps_json_null_to_the_literal_string_null():
    assert m.flag_value_key(None) == "null"


def test_flag_value_key_leaves_a_genuine_empty_string_as_empty_string():
    """The exact distinction cbp_metadata.py's `(row[idx[col]] or "")` erases: a real `""` flag
    value (if CBP ever published one) must not be indistinguishable from JSON `null` afterward."""
    assert m.flag_value_key("") == ""


def test_flag_value_key_leaves_a_real_flag_letter_untouched():
    assert m.flag_value_key("a") == "a"


# --- flag_evidence -----------------------------------------------------------------------------

HEADER = ["NAME", "NAICS2017_LABEL", "EMPSZES", "EMPSZES_LABEL", "ESTAB", "EMP", "EMP_F",
          "EMP_N", "NAICS2017", "LFO", "state"]


def _row(name: str, emp_f, emp_n: str, state: str) -> list:
    return [name, "Logging", "001", "All establishments", "10", "50", emp_f, emp_n, "113310",
            "001", state]


def test_flag_evidence_keeps_null_and_empty_string_and_a_real_flag_as_three_distinct_keys():
    """Pins the actual defect: a body with None, "" and "a" in EMP_F must produce three distinct
    counted keys, not collapse None and "" together the way cbp_metadata.py's `flag_values_by_year`
    does. This is the regression test for why this task derives from the raw extract instead of
    trusting that finding."""
    body = [
        _row("Alabama", None, "0", "01"),
        _row("Alaska", "", "0", "02"),
        _row("Arizona", "a", "0", "04"),
    ]
    ev = m.flag_evidence(HEADER, body)
    assert ev["EMP_F"] == {"null": 1, "": 1, "a": 1}


def test_flag_evidence_suppressed_share_counts_only_non_null_emp_f():
    body = [_row("Alabama", None, "0", "01"), _row("Alaska", None, "0", "02"),
            _row("Arizona", "a", "0", "04"), _row("Arkansas", None, "0", "05")]
    ev = m.flag_evidence(HEADER, body)
    assert ev["suppressed_share"] == pytest.approx(0.25)


def test_flag_evidence_emp_n_present_and_nonzero_share_excludes_the_string_zero():
    body = [_row("Alabama", None, "0", "01"), _row("Alaska", None, "5", "02")]
    ev = m.flag_evidence(HEADER, body)
    assert ev["emp_n_present_and_nonzero_share"] == pytest.approx(0.5)


def test_flag_evidence_empty_body_gives_zero_shares_not_a_division_error():
    ev = m.flag_evidence(HEADER, [])
    assert ev["suppressed_share"] == 0.0
    assert ev["emp_n_present_and_nonzero_share"] == 0.0
    assert ev["EMP_F"] == {}
    assert ev["EMP_N"] == {}


def test_flag_evidence_emp_n_f_in_response_false_when_column_absent():
    """The real shape of every year's 113310 pull this task consumes (Task 7 never selected
    EMP_N_F as an output column) -- must read False, not silently absent from the dict."""
    ev = m.flag_evidence(HEADER, [_row("Alabama", None, "0", "01")])
    assert ev["emp_n_f_in_response"] is False


def test_flag_evidence_emp_n_f_in_response_true_when_column_present():
    header_with_flag = [*HEADER, "EMP_N_F"]
    body = [[*_row("Alabama", None, "0", "01"), "G"]]
    ev = m.flag_evidence(header_with_flag, body)
    assert ev["emp_n_f_in_response"] is True


def test_flag_evidence_omits_emp_f_key_entirely_when_column_absent_from_header():
    """A response that dropped EMP_F entirely (attempt 3's shape in cbp_metadata.py) must not
    report an empty/zero count that looks like "measured, zero occurrences" -- the key itself
    must be absent, matching cbp_metadata's own empszes_pairs_from_rows None-vs-[] discipline."""
    header_no_flags = ["NAME", "NAICS2017_LABEL", "ESTAB", "EMP", "NAICS2017", "LFO", "state"]
    body = [["Alabama", "Logging", "10", "50", "113310", "001", "01"]]
    ev = m.flag_evidence(header_no_flags, body)
    assert "EMP_F" not in ev
    assert "EMP_N" not in ev
    assert ev["emp_n_f_in_response"] is False


# --- citation_url ------------------------------------------------------------------------------


def test_citation_url_extracts_the_leading_url():
    citation = ("https://www.census.gov/programs-surveys/cbp/technical-documentation/"
                "methodology.html -- section 'Protecting Confidentiality > Noise Infusion'")
    assert m.citation_url(citation) == (
        "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html")


def test_citation_url_raises_when_no_url_present():
    with pytest.raises(ValueError, match="no URL"):
        m.citation_url("just a section heading, no link")


# --- validate_regime_entry -----------------------------------------------------------------


OK_URLS = {"https://example.gov/methodology.html"}


def test_validate_regime_entry_raises_on_blank_evidence():
    entry = {"regime": "unknown", "evidence": "", "citation": ""}
    with pytest.raises(ValueError, match="evidence must not be blank"):
        m.validate_regime_entry("2024", entry, OK_URLS)


def test_validate_regime_entry_raises_when_non_unknown_regime_has_no_citation():
    entry = {"regime": "noise_infusion", "evidence": "something happened", "citation": ""}
    with pytest.raises(ValueError, match="needs a citation"):
        m.validate_regime_entry("2018", entry, OK_URLS)


def test_validate_regime_entry_raises_when_citation_url_was_not_actually_fetched():
    entry = {"regime": "noise_infusion", "evidence": "something happened",
             "citation": "https://example.gov/not-fetched.html -- some section"}
    with pytest.raises(ValueError, match="not among this run's successfully fetched"):
        m.validate_regime_entry("2018", entry, OK_URLS)


def test_validate_regime_entry_passes_for_a_well_formed_unknown_entry():
    entry = {"regime": "unknown", "evidence": "not obtainable -- no data published", "citation": ""}
    m.validate_regime_entry("2024", entry, OK_URLS)  # must not raise


def test_validate_regime_entry_passes_for_a_well_formed_cited_entry():
    entry = {"regime": "noise_infusion", "evidence": "documented",
             "citation": "https://example.gov/methodology.html -- some section"}
    m.validate_regime_entry("2018", entry, OK_URLS)  # must not raise


# --- REGIME_BY_YEAR itself (the authored literal), exercised as data ---------------------------


def test_regime_by_year_covers_exactly_the_window_years():
    assert set(m.REGIME_BY_YEAR) == {str(y) for y in c.WINDOW_YEARS}


def test_regime_by_year_2024_is_unknown():
    """2024 has no CBP data at all this run (confirmed 404, not a transport blip -- Task 7's
    dataset_probe_status_by_year) and therefore no year-specific documentation could exist to
    check. `unknown` is the only honest answer, and it is what makes Stage 1 fail closed."""
    assert m.REGIME_BY_YEAR["2024"]["regime"] == "unknown"
    assert m.REGIME_BY_YEAR["2024"]["citation"] == ""
    assert m.REGIME_BY_YEAR["2024"]["evidence"]


def test_regime_by_year_every_entry_is_individually_well_formed():
    """Exercises every authored entry against validate_regime_entry, using DOC_URLS' own URL set
    as a stand-in for "successfully fetched this run" -- catches a citation that names a URL not
    in DOC_URLS at all (a typo, or a URL this script never actually fetches) without needing a
    live network call."""
    doc_urls = {spec["url"] for spec in m.DOC_URLS}
    for year, entry in m.REGIME_BY_YEAR.items():
        m.validate_regime_entry(year, entry, doc_urls)


def test_regime_by_year_2017_is_distinguished_from_2018_onward():
    """The one real, dated regime change methodology.html documents inside the D1 window: 2017
    is the last year EMPFLAG (a suppression mechanism) coexists with noise infusion; 2018 is the
    first year it's gone. These must not collapse to the same label."""
    assert m.REGIME_BY_YEAR["2017"]["regime"] != m.REGIME_BY_YEAR["2018"]["regime"]


def test_regime_by_year_non_unknown_years_each_name_their_own_year_in_their_evidence():
    """Trap the dispatch names by name: a shared prefix/string used across differing years is
    fine only if genuinely accurate for every year it's attached to. This checks only that each
    year's own evidence text contains its own year -- a cheap mechanical guard against a
    copy-pasted block that was never rendered per-year at all (e.g. a literal string assigned
    once and reused for every entry).

    It does NOT check pairwise byte-distinctness across years, and must not be read as if it
    did: 2019-2023 deliberately share one template (`_no_year_specific_doc_evidence`) rendered
    once per year, so those five entries are byte-identical to each other apart from the
    substituted year token, and this test passes on exactly that shape. That is the honest state
    of the evidence (see that function's own docstring), not a defect this test is meant to
    catch."""
    for year, entry in m.REGIME_BY_YEAR.items():
        if entry["regime"] == "unknown":
            continue
        assert year in entry["evidence"], (
            f"{year}: evidence text does not name its own year -- suspicious of a copy-pasted "
            "block shared across years without being rendered per-year"
        )


def test_no_year_specific_doc_evidence_marks_the_banner_scope_reading_as_inference():
    """Finding 1 (fix round 1): methodology.html's 'no longer current' banner does not itself
    distinguish a prospective/current-approach scope from a retraction of the dated 2007-2018
    historical statements 2019-2023's entries rest on -- reading it as the former is this
    auditor's own interpretation, not a fetched fact, and it is load-bearing (the opposite
    reading would leave these years with no documentary basis, i.e. `unknown`). It must be
    marked inline with a scope a reader can't miss: exactly one opening and one closing marker,
    with the interpretive clause itself between them and the "weighted accordingly" caveat
    outside them (that caveat follows from the banner's mere existence, not from how its scope
    is read, so it must not be swept inside the marked span)."""
    for year in (2019, 2020, 2021, 2022, 2023):
        evidence = m._no_year_specific_doc_evidence(year)
        assert evidence.count("INFERENCE MARKER, OPENING") == 1
        assert evidence.count("INFERENCE MARKER, CLOSING") == 1
        opening = evidence.index("INFERENCE MARKER, OPENING")
        closing = evidence.index("INFERENCE MARKER, CLOSING")
        assert opening < closing
        marked = evidence[opening:closing]
        assert "prospective" in marked
        assert "retraction" in marked
        assert "weighted accordingly" in evidence[:opening]


# --- DOC_URLS structural guards ------------------------------------------------------------


def test_doc_urls_rel_paths_are_all_distinct():
    """Two DOC_URLS mapping to the same rel_path would make the second record_extract call
    silently overwrite the first's file while both remain listed in `extracts` -- verbatim
    retention means one fetch, one file, one extract record."""
    rel_paths = [spec["rel_path"] for spec in m.DOC_URLS]
    assert len(rel_paths) == len(set(rel_paths))


def test_doc_urls_includes_the_briefs_original_typo_and_the_fixed_url():
    """Real defect found this task: the brief's illustrative DOC_URLS lists
    ".../records-layouts.html" (plural "records"), which 404s live -- the real page is
    ".../record-layouts.html" (singular). Both are kept in DOC_URLS: the brief's original, to
    document the 404 live rather than silently dropping it, and the fix, which is what the
    regime citations actually rest on."""
    urls = {spec["url"] for spec in m.DOC_URLS}
    assert any(u.endswith("/records-layouts.html") for u in urls)
    assert any(u.endswith("/record-layouts.html") for u in urls)


# --- variable_definition_summary ----------------------------------------------------------
#
# Real captured bodies from live GETs to https://api.census.gov/data/2021/cbp/variables/{VAR}.json
# this task -- EMP_F and EMP_N_F are both "attribute of" a base variable with "attribute type":
# "FLAG" and carry no `values` crosswalk; EMP_N_F is the actual per-cell noise-magnitude flag
# (distinct from EMP_N, an int-typed "noise range" value, and from EMP_F, the suppression flag).

REAL_EMP_F_DOC = {
    "name": "EMP_F", "label": "Flag for number of employees",
    "concept": "All Sectors: County Business Patterns, including ZIP Code Business Patterns, by "
               "Legal Form of Organization and Employment Size Class for the U.S., States, and "
               "Selected Geographies: 2021",
    "predicateType": "string", "group": "CB2100CBP", "limit": 0,
    "attribute of": "EMP", "attribute type": "FLAG",
}

REAL_EMP_N_F_DOC = {
    "name": "EMP_N_F", "label": "Flag for Noise range for number of employees ",
    "concept": "All Sectors: County Business Patterns, including ZIP Code Business Patterns, by "
               "Legal Form of Organization and Employment Size Class for the U.S., States, and "
               "Selected Geographies: 2021",
    "predicateType": "string", "group": "CB2100CBP", "limit": 0,
    "attribute of": "EMP_N", "attribute type": "FLAG",
}

REAL_EMP_DOC_WITH_NO_ATTRIBUTE_OF = {
    "name": "EMP", "label": "Number of employees",
    "concept": "All Sectors: County Business Patterns, including ZIP Code Business Patterns, by "
               "Legal Form of Organization and Employment Size Class for the U.S., States, and "
               "Selected Geographies: 2021",
    "predicateType": "int", "group": "CB2100CBP", "limit": 0, "attributes": "EMP_F",
}


def test_variable_definition_summary_reads_a_real_flag_attribute_doc():
    out = m.variable_definition_summary(REAL_EMP_N_F_DOC)
    assert out == {
        "label": "Flag for Noise range for number of employees",
        "attribute_of": "EMP_N",
        "attribute_type": "FLAG",
        "has_values_crosswalk": False,
    }


def test_variable_definition_summary_strips_trailing_whitespace_from_the_real_label():
    """REAL_EMP_N_F_DOC's own label carries a real trailing space in the live API response --
    confirmed by direct fetch this task. Pinned so a future re-fetch that changes the label
    can't silently reintroduce inconsistent whitespace into a persisted evidence string."""
    assert not REAL_EMP_F_DOC["label"].endswith(" ")  # EMP_F's real label has none
    assert REAL_EMP_N_F_DOC["label"].endswith(" ")  # EMP_N_F's real label does
    out = m.variable_definition_summary(REAL_EMP_N_F_DOC)
    assert out["label"] == "Flag for Noise range for number of employees"  # stripped


def test_variable_definition_summary_attribute_of_is_none_for_a_base_variable():
    out = m.variable_definition_summary(REAL_EMP_DOC_WITH_NO_ATTRIBUTE_OF)
    assert out["attribute_of"] is None
    assert out["attribute_type"] is None


def test_variable_definition_summary_has_values_crosswalk_true_when_values_item_present():
    doc_with_crosswalk = {**REAL_EMP_F_DOC, "values": {"item": {"D": "Suppressed"}}}
    out = m.variable_definition_summary(doc_with_crosswalk)
    assert out["has_values_crosswalk"] is True


# --- emp_n_f_caveat ------------------------------------------------------------------------


def test_emp_n_f_caveat_when_never_observed_in_any_response_says_so_and_names_the_label():
    text = m.emp_n_f_caveat(observed_any=False, emp_n_f_label="Flag for Noise range for "
                             "number of employees")
    assert "does not appear in any year's 113310 x state response header" in text
    assert "Flag for Noise range for number of employees" in text
    assert "must not be read as evidence" in text


def test_emp_n_f_caveat_when_observed_says_it_can_be_cross_checked():
    text = m.emp_n_f_caveat(observed_any=True, emp_n_f_label="Flag for Noise range for "
                             "number of employees")
    assert "cross-checked" in text


def test_emp_n_f_caveat_with_no_label_says_the_fetch_failed_not_that_the_label_is_none():
    """`emp_n_f_label=None` means this run's own variables/EMP_N_F.json fetch failed for the
    representative year -- must render as "could not fetch", never as the literal string
    "labelled None", which would assert the label itself is the word None."""
    text = m.emp_n_f_caveat(observed_any=False, emp_n_f_label=None)
    assert "could not fetch" in text
    assert "labelled None" not in text
    assert "labelled 'None'" not in text
