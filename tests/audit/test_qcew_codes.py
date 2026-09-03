"""Branch coverage for the `qcew_codes` sentence helpers.

These four helpers exist to keep a persisted `notes` claim honest across re-runs: each one has
a branch for what today's data shows and a branch for what a future run against revised data
might show instead. Every real run to date has taken exactly one branch of each, so the
adaptive branches -- the reason those helpers were written at all -- have never executed. The
tests below exercise both sides of each helper against fabricated inputs; they are pure
functions over plain lists and dicts, so no network, fixture or artifact is involved.

`qcew_codes` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import _common
import qcew_codes


# --- _observed_detail_sentence -----------------------------------------------------------


def _agglvl(code: str, title: str | None, row_count: int = 1) -> dict:
    return {"code": code, "title": title, "row_count": row_count}


def test_observed_detail_sentence_reports_one_clause_when_titles_agree():
    sentence = qcew_codes._observed_detail_sentence([
        _agglvl("18", "National, NAICS 6-digit -- by ownership sector"),
        _agglvl("58", "State, NAICS 6-digit -- by ownership sector"),
    ])
    assert "all of them strip to one detail clause" in sentence
    assert (
        "'NAICS 6-digit -- by ownership sector' at codes 18 (National), 58 (State)" in sentence
    )
    # The count and the geography names are read out of the input, never typed.
    assert "computed from the 2 agglvl codes" in sentence
    # Frame described, not its ownership cardinality: "both ownerships" was a typed claim that a
    # third own_code would have falsified.
    assert "before the own_code filter" in sentence
    assert "ownerships" not in sentence


def test_observed_detail_sentence_reports_disagreement_when_clauses_differ():
    """The branch no real run has taken: a future agglvl set spanning two NAICS-digit depths
    must say the clause is not uniform, not repeat today's agreement."""
    sentence = qcew_codes._observed_detail_sentence([
        _agglvl("18", "National, NAICS 6-digit -- by ownership sector"),
        _agglvl("14", "National, NAICS 4-digit -- by ownership sector"),
    ])
    assert "they strip to 2 distinct detail clauses" in sentence
    assert "not uniform across the codes present on these rows" in sentence
    assert "all of them strip to one detail clause" not in sentence
    assert "'NAICS 6-digit -- by ownership sector' at codes 18 (National)" in sentence
    assert "'NAICS 4-digit -- by ownership sector' at codes 14 (National)" in sentence


def test_observed_detail_sentence_handles_a_code_with_no_fetched_title():
    """A code observed on the data but absent from the fetched titles file must not crash on
    `title.split`, and must be visible as a missing title rather than silently grouped."""
    sentence = qcew_codes._observed_detail_sentence([
        _agglvl("18", "National, NAICS 6-digit -- by ownership sector"),
        _agglvl("99", None),
    ])
    assert "<no fetched title>" in sentence
    assert "they strip to 2 distinct detail clauses" in sentence


# --- _dc_sentence ------------------------------------------------------------------------


def test_dc_sentence_reports_absence_when_dc_publishes_no_rows():
    sentence = qcew_codes._dc_sentence(
        {"present": False, "row_count": 0, "years": []}, n_quarters=32
    )
    assert "carries zero private-ownership" in sentence
    assert "in any of the 32 quarters" in sentence
    assert "entirely absent from this panel" in sentence
    assert _common.INDUSTRY_CODE in sentence


def test_dc_sentence_reports_presence_when_dc_starts_publishing():
    """The branch no real run has taken. A future panel where DC publishes must describe the
    rows it found, not repeat the absence claim that today's `notes` carries."""
    sentence = qcew_codes._dc_sentence(
        {"present": True, "row_count": 7, "years": ["2023", "2024"]}, n_quarters=32
    )
    assert "is present in the state-like rows: 7 rows, in 2023, 2024." in sentence
    assert "entirely absent" not in sentence
    assert "carries zero" not in sentence


# --- _extraneous_area_sentence -----------------------------------------------------------


def test_extraneous_area_sentence_describes_each_area_outside_state_areas():
    sentence = qcew_codes._extraneous_area_sentence([
        {"area_fips": "72000", "title": "Puerto Rico -- Statewide", "row_count": 12,
         "years": ["2017", "2018"]},
        {"area_fips": "78000", "title": "Virgin Islands -- Statewide", "row_count": 3,
         "years": ["2019"]},
    ])
    assert "72000 ('Puerto Rico -- Statewide', 12 rows, in 2017, 2018) is present" in sentence
    assert "78000 ('Virgin Islands -- Statewide', 3 rows, in 2019) is present" in sentence
    assert "No state-like area code fell outside" not in sentence


def test_extraneous_area_sentence_says_so_when_nothing_falls_outside():
    """The branch no real run has taken -- today's panel always carries PR and VI. A future
    run where it does not must still emit a sentence, not an empty string that would leave a
    dangling double space (or worse, a silently missing clause) in `notes`."""
    sentence = qcew_codes._extraneous_area_sentence([])
    assert sentence == "No state-like area code fell outside c.STATE_AREAS."


# --- _same_industry_detail ---------------------------------------------------------------

_TITLES = {
    "18": "National, NAICS 6-digit -- by ownership sector",
    "58": "State, NAICS 6-digit -- by ownership sector",
    "54": "State, NAICS 4-digit -- by ownership sector",
}


def test_same_industry_detail_true_reports_the_shared_clause():
    same, outcome = qcew_codes._same_industry_detail(["18"], ["58"], _TITLES)
    assert same is True
    assert outcome == (
        "stripping the leading geography clause leaves an identical detail clause at both "
        "levels ('NAICS 6-digit -- by ownership sector')"
    )


def test_same_industry_detail_false_on_differing_clauses_names_both():
    same, outcome = qcew_codes._same_industry_detail(["18"], ["54"], _TITLES)
    assert same is False
    assert "leaves different detail clauses at the two levels" in outcome
    assert "'NAICS 6-digit -- by ownership sector'" in outcome
    assert "'NAICS 4-digit -- by ownership sector'" in outcome


def test_same_industry_detail_false_on_cardinality_does_not_claim_a_clause_comparison():
    """The distinction that a bare identical/different rendering would lose: with two codes at
    one geography level no clause comparison happens at all, so `notes` must not report one."""
    same, outcome = qcew_codes._same_industry_detail(["18"], ["58", "54"], _TITLES)
    assert same is False
    assert "the clause comparison was not reached" in outcome
    assert "1 national and 2 state codes are observed" in outcome
    assert "detail clause" not in outcome


def test_same_industry_detail_false_on_missing_title_names_the_absent_code():
    same, outcome = qcew_codes._same_industry_detail(["18"], ["99"], _TITLES)
    assert same is False
    assert "the clause comparison was not reached" in outcome
    assert "carries no entry for code(s) 99" in outcome
