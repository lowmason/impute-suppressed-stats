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

import pathlib

import pytest

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
    # The lead is shared by both branches, so it must name no outcome of its own.
    assert sentence.startswith("Scope of the fetched-title comparison,")
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
    # The lead is shared with the agreement branch, so it must not presuppose one: the first
    # draft read "Scope of that agreement ... so the clause is not uniform", contradicting
    # itself, and asserting only on the body let that through.
    assert "agreement" not in sentence


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


# --- _geography_universe_note ----------------------------------------------------------------
#
# The composing helper itself, which the four helpers above feed. Until now it was the one
# unprotected branch in this module: each callee had both its branches pinned while the
# composer that chooses between them, and appends the DC-absence paragraph on one of them, had
# none -- and that paragraph is where a previous fix round's own defect landed. It is a pure
# function of five plain arguments, so no network, fixture or artifact is involved here either.


def _note(*, dc_present: bool) -> str:
    return qcew_codes._geography_universe_note(
        32,
        ["01000", "02000"],
        [],
        {"present": dc_present, "row_count": 4, "years": ["2017"]} if dc_present
        else {"present": False, "row_count": 0, "years": []},
        ["71"],
    )


def test_geography_universe_note_does_not_assert_an_unobservable_dc_contribution():
    """Whole-branch review, finding 2. The DC paragraph asserted a residual as a fact -- "DC's
    contribution to the national total is unobservable at the state level -- a national-vs-sum-
    of-states residual distinct from, and additional to, cell-level suppression". That needs an
    unstated premise (that DC has nonzero private 113310 activity at all) which nothing fetched
    here supports, and on the establishment margin `qcew_identity` measures the opposite:
    `estab_gap = estab_gap_after_other = 0` in every quarter, read there as an area adding zero
    establishments adding no employment either. The shipped document carried both readings.
    Negative pin: re-adding the old sentence beside the corrected one is still caught."""
    note = _note(dc_present=False)
    assert "contribution to the national total is unobservable" not in note
    assert "a national-vs-sum-of-states residual distinct from" not in note


def test_geography_universe_note_names_a_channel_and_disclaims_its_magnitude():
    """The corrected wording: a *channel* whose magnitude this script does not measure, and a
    statement of where it would be observed if it is open at all."""
    note = _note(dc_present=False)
    assert "potential national-vs-sum-of-states residual channel" in note
    assert "That is a channel, not a quantity." in note
    assert "no value is claimed for it" in note
    assert "not even that it is nonzero" in note
    # Names where the channel would appear rather than leaving the reader to find it.
    assert "estab_gap and estab_gap_after_other" in note
    assert "clean_months" in note


def test_geography_universe_note_wraps_the_dc_reading_in_an_inference_marker():
    """The reading sits outside the delimited scope of the composition argument's own marking,
    so it carries its own pair -- the convention this branch uses for exactly this. Balance is
    what `test_assemble_finding`'s document-level count assertion rests on."""
    note = _note(dc_present=False)
    assert note.count("INFERENCE MARKER, OPENING") == 1
    assert note.count("INFERENCE MARKER, CLOSING") == 1
    assert note.index("INFERENCE MARKER, OPENING") < note.index("INFERENCE MARKER, CLOSING")
    # The measured sentences stay outside the marked span: what is marked is the reading.
    assert note.index("the state-like predicate above yields") < note.index(
        "INFERENCE MARKER, OPENING")


def test_geography_universe_note_omits_the_dc_paragraph_entirely_when_dc_publishes():
    """The other branch, which no real run has taken. A future run where DC starts publishing
    must not ship a residual-channel reading premised on an absence that did not happen -- and
    must not ship an unbalanced marker either, since the pair lives inside that paragraph."""
    note = _note(dc_present=True)
    assert "residual channel" not in note
    assert "INFERENCE MARKER" not in note
    assert "District of Columbia (11000) is present in the state-like rows" in note


def test_geography_universe_note_keeps_marking_the_hand_authored_composition_argument():
    """Wave 2 added a marker pair; it must not have displaced the existing self-marking of the
    quotation, the membership premise and the conclusion, which is on both branches."""
    for dc_present in (True, False):
        note = _note(dc_present=dc_present)
        assert "hand-authored in all three of its parts" in note
        assert "Unquoted premise, supplied by hand" in note
        assert _common.INDUSTRY_CODE in note


# --- _period_basis -------------------------------------------------------------------------

# The nine columns the live QCEW slice header builds on the same `monthN_emplvl` stem without
# being monthly employment levels: three location quotients and six over-the-year changes.
# Present in every fixture below so each test is a real test of the anchoring, not of a header
# that had nothing to over-collect.
DECOYS = [
    "lq_month1_emplvl", "lq_month2_emplvl", "lq_month3_emplvl",
    "oty_month1_emplvl_chg", "oty_month1_emplvl_pct_chg",
    "oty_month2_emplvl_chg", "oty_month2_emplvl_pct_chg",
    "oty_month3_emplvl_chg", "oty_month3_emplvl_pct_chg",
]
LIVE_HEADER = ["area_fips", "own_code", "industry_code", "year", "qtr", "qtrly_estabs",
               "month1_emplvl", "month2_emplvl", "month3_emplvl", *DECOYS]

QUOTED_REFERENCE_SENTENCE = (
    "QCEW monthly employment counts covered workers who worked during, or received pay for, "
    "the pay period including the 12th day of the month."
)


def _measured_half(basis: str) -> str:
    """Everything before the documented half begins. The split token is the label the artifact
    itself uses, so a rewording that dropped the label would fail here rather than silently
    hand these tests the whole string to search."""
    assert "Documented, not measured:" in basis
    return basis.split("Documented, not measured:")[0]


def test_period_basis_counts_only_the_bare_monthly_employment_columns():
    """The anchoring test. An unanchored 'month'/'emplvl' match over this header collects all
    twelve columns; the derivation must report the three that are monthly employment levels."""
    basis = qcew_codes._period_basis(LIVE_HEADER)
    assert "Monthly employment level columns present: 3 (month1_emplvl, month2_emplvl, " \
           "month3_emplvl)" in basis
    for decoy in DECOYS:
        assert decoy not in basis


def test_period_basis_reports_zero_when_only_decoy_columns_carry_the_stem():
    """The discriminating case: a header with every lq_/oty_ column but no bare monthly
    employment column at all. A predicate that over-collects would report nine here."""
    basis = qcew_codes._period_basis(["area_fips", "year", "qtr", *DECOYS])
    assert "Monthly employment level columns present: 0 (none)" in basis
    # And with no column to read the documented statement onto, it must not claim one does.
    assert "so there is no column here for that statement to be read onto" in basis
    assert "read here as the QCEW monthly employment counts" not in basis


def test_period_basis_reports_what_it_finds_rather_than_a_typed_three():
    """A future QCEW layout with a fourth monthly column must say four. The replaced string
    typed 'three monthly employment columns'; a derivation that still hardcodes three would
    pass the live-header test above and fail here."""
    basis = qcew_codes._period_basis([*LIVE_HEADER, "month4_emplvl"])
    assert "Monthly employment level columns present: 4 (month1_emplvl, month2_emplvl, " \
           "month3_emplvl, month4_emplvl)" in basis
    assert "The 4 column(s) named above are read here" in basis


def test_period_basis_reports_the_period_keying_columns_it_actually_finds():
    assert "of 'year' and 'qtr': year, qtr" in qcew_codes._period_basis(LIVE_HEADER)
    stripped = [col for col in LIVE_HEADER if col != "qtr"]
    assert "of 'year' and 'qtr': year." in qcew_codes._period_basis(stripped)
    assert "of 'year' and 'qtr': (none)." in qcew_codes._period_basis(DECOYS)


def test_period_basis_keeps_the_reference_period_out_of_the_measured_half():
    """The separation this work item exists for. The header establishes column names and
    nothing about a reference period, so no '12th' claim may appear in the measured half --
    and the reading that attaches it to these columns must sit inside the marker pair."""
    for header in (LIVE_HEADER, [*LIVE_HEADER, "month4_emplvl"], DECOYS):
        basis = qcew_codes._period_basis(header)
        assert "12th" not in _measured_half(basis)
        opening = basis.index("INFERENCE MARKER, OPENING")
        closing = basis.index("INFERENCE MARKER, CLOSING")
        attached = "12th day of its own month"
        if attached in basis:
            assert opening < basis.index(attached) < closing
        assert basis.count("INFERENCE MARKER, OPENING") == 1
        assert basis.count("INFERENCE MARKER, CLOSING") == 1
        assert opening < closing
        # The quotation is attribution, not inference, so it stays outside the marked span --
        # the same placement `_geography_universe_note` gives its BLS quotation.
        assert basis.index(QUOTED_REFERENCE_SENTENCE) < opening


def test_period_basis_quotes_the_reference_verbatim_where_the_reference_is_readable():
    """Truth, not presence: the quoted sentence must actually be in the file the artifact cites.
    The reference is a personal skill outside this repo, so a clone without it skips rather
    than failing -- but on a machine that has it, this is what stops the quotation drifting."""
    ref = pathlib.Path(
        "~/.claude/skills/bls-data-context/references/qcew.md").expanduser()
    if not ref.exists():
        pytest.skip(f"{ref} not present; nothing to check the quotation against")
    text = ref.read_text(encoding="utf-8")
    assert QUOTED_REFERENCE_SENTENCE in text
    assert "### Employment concept" in text
    assert "## Source pages reviewed" in text
    basis = qcew_codes._period_basis(LIVE_HEADER)
    assert QUOTED_REFERENCE_SENTENCE in basis
    assert "references/qcew.md" in basis
    assert "'Employment concept'" in basis
