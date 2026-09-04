"""Judgment-logic coverage for `ces_levels`, pinned before the live sm.* scan runs.

Two things are pinned here. First, the level-derivation rule the brief specifies directly:
`embedded_naics` / `level_of`, including the deliberate 11331/113310 collision the brief's own
docstring calls out. Second, a defect this implementer found by fetching the real sm.industry
file before trusting the brief's candidate filter: `industry_name.str.contains("(?i)logging")`
also matches "15000000 Mining, Logging and Construction" -- a genuinely broader CES supersector
that happens to share the word "logging" with "10000000 Mining and Logging", the one the task
actually means. Left unfixed, four jurisdictions (Delaware, DC, Hawaii, the Virgin Islands) --
whose only D1-window statewide all-employees series among the logging-named codes sits at the
broader 15000000 code -- would have been reported at level "supersector" instead of "none".
`sole_code`'s own docstring already names this exact failure shape for `all_employees` (a looser
"^all employees" pattern also matching the 3-month-average-change series); this is the same bug
in the industry-title match, not caught by the illustrative code's use of a bare substring test.

`ces_levels` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is inert:
the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import polars as pl
import pytest

import ces_levels as m

# --- embedded_naics -------------------------------------------------------------------------


def test_embedded_naics_strips_trailing_zero_padding():
    # The one real code this script's target industry lives at (Task 9 verified this against
    # the live sm.industry file): "10113300" = supersector "10" + NAICS "1133" right-padded.
    assert m.embedded_naics("10113300") == "1133"


def test_embedded_naics_returns_empty_string_for_a_supersector_code():
    assert m.embedded_naics("10000000") == ""


def test_embedded_naics_leaves_no_trailing_zero_to_strip_for_a_six_digit_code():
    assert m.embedded_naics("10212114") == "212114"


# --- level_of --------------------------------------------------------------------------------


def test_level_of_the_real_logging_code_is_1133_not_113310():
    """The finest CES/SAE industry-code granularity this script actually finds for Logging
    (verified against the live sm.industry file, Task 9) is NAICS 4-digit "1133" -- CES/SAE
    defines no separate code at the 5- or 6-digit depth. This is the one case that matters in
    practice; the 113310 branch below exists for a code shape that does not occur today."""
    assert m.level_of("10113300") == "1133"


def test_level_of_collapses_the_11331_113310_collision_to_113310():
    """The brief's own documented case: an embedded field that strips to "11331" (5 chars,
    starts with "1133") is indistinguishable from a true 6-digit 113310 source after
    `rstrip("0")`. Both denote Logging at its finest possible published level -- licensed by
    D6's structure-file-verified claim that 113310 is the only six-digit industry under 1133 in
    both the 2017 and 2022 NAICS vintages (confirmed directly against the classification-codes
    skill's naics_2017.csv / naics_2022.csv for this task) -- so both must classify the same."""
    # "99" + "113310": positions [2:8] = "113310", which strips to "11331" (5 chars).
    assert m.level_of("99113310") == "113310"


def test_level_of_exact_four_digit_naics_is_1133():
    assert m.level_of("99113300") == "1133"


def test_level_of_exact_three_digit_naics_is_113():
    assert m.level_of("99113000") == "113"


def test_level_of_no_embedded_naics_is_supersector():
    assert m.level_of("10000000") == "supersector"


def test_level_of_a_sibling_naics_subsector_is_other_not_1133():
    """NAICS 1131 (Timber Tract Operations) and 1132 (Forest Nurseries) are 1133's siblings
    under 113 (Forestry and Logging). A hypothetical CES code embedding one of them must not
    collapse into the 1133 branch just because it starts with "113"."""
    assert m.level_of("99113100") == "other"


def test_level_of_an_unrelated_naics_is_other():
    # Real code, real title "Coal Mining" -- naics_code "2121" per the national ce.industry
    # file's own naics_code column (Task 9 verification), nothing to do with Logging.
    assert m.level_of("10212100") == "other"


# --- sole_code (against the real fetched vocabulary, Task 9) --------------------------------

REAL_DATA_TYPE_TITLES = pl.DataFrame({
    "data_type_code": ["01", "02", "03", "06", "07", "08", "11", "21", "22", "23", "24", "26",
                       "30"],
    "data_type_text": [
        "All Employees, In Thousands",
        "Average Weekly Hours of All Employees",
        "Average Hourly Earnings of All Employees, In Dollars",
        "Production or Nonsupervisory Employees, In Thousands",
        "Average Weekly Hours of Production Employees",
        "Average Hourly Earnings of Production Employees, In Dollars",
        "Average Weekly Earnings of All Employees, In Dollars",
        "Diffusion Indexes, 1-month span, seasonally adjusted, total nonfarm",
        "Diffusion Indexes, 3-month span, seasonally adjusted, total nonfarm",
        "Diffusion Indexes, 6-month span, seasonally adjusted, total nonfarm",
        "Diffusion Indexes, 12-month span, seasonally adjusted, total nonfarm",
        "All Employees, 3-month average change, In Thousands, seasonally adjusted",
        "Average Weekly Earnings of Production Employees, In Dollars",
    ],
})

REAL_AREA_TITLES = pl.DataFrame({
    "area_code": ["00000", "10180", "10380"],
    "area_name": ["Statewide", "Abilene, TX", "Aguadilla, PR"],
})

REAL_INDUSTRY_TITLES = pl.DataFrame({
    "industry_code": ["10000000", "10113300", "15000000"],
    "industry_name": ["Mining and Logging", "Logging", "Mining, Logging and Construction"],
})


def test_sole_code_all_employees_ignores_the_3_month_average_change_series():
    """A looser "^all employees" pattern (no ", in thousands" suffix, no anchor) would also
    match code "26"; the anchored, full-title pattern this script actually uses picks "01"
    alone."""
    assert m.sole_code(REAL_DATA_TYPE_TITLES, "data_type_code", "data_type_text",
                       r"(?i)^all employees, in thousands$", "sm.data_type") == "01"


def test_sole_code_statewide_area_matches_the_one_real_row():
    assert m.sole_code(REAL_AREA_TITLES, "area_code", "area_name", r"(?i)^statewide$",
                       "sm.area") == "00000"


def test_sole_code_mining_and_logging_supersector_excludes_the_broader_title():
    """The exact defect this task found: an anchored, exact-title match on "Mining and Logging"
    picks only "10000000", never "15000000 Mining, Logging and Construction" -- a real, broader
    CES supersector that also contains "logging" as a substring."""
    assert m.sole_code(REAL_INDUSTRY_TITLES, "industry_code", "industry_name",
                       r"(?i)^mining and logging$", "sm.industry") == "10000000"


def test_sole_code_raises_when_no_title_matches():
    empty = REAL_DATA_TYPE_TITLES.filter(pl.col("data_type_code") != "01")
    with pytest.raises(RuntimeError, match="expected exactly one"):
        m.sole_code(empty, "data_type_code", "data_type_text",
                   r"(?i)^all employees, in thousands$", "sm.data_type")


def test_sole_code_raises_when_more_than_one_title_matches():
    """The failure mode `sole_code` exists to prevent: an ambiguous vocabulary must fail loudly,
    not silently pick one. A loose, unanchored pattern against the real logging-named industry
    titles is exactly the case that would trigger this -- it matches all three rows (both
    supersectors and the target itself), not just the two the brief's illustrative filter
    would have silently folded together."""
    with pytest.raises(RuntimeError, match="expected exactly one") as exc_info:
        m.sole_code(REAL_INDUSTRY_TITLES, "industry_code", "industry_name", r"(?i)logging",
                   "sm.industry")
    for code in ("10000000", "10113300", "15000000"):
        assert code in str(exc_info.value)


# --- qualifying_series -------------------------------------------------------------------------


def _series_frame(rows: list[tuple[str, str, str, str, str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema=["series_id", "state_code", "industry_code", "data_type_code", "area_code",
                "begin_year", "end_year"],
        orient="row",
    )


def test_qualifying_series_keeps_only_matching_industry_type_area_and_window_overlap():
    df = _series_frame([
        ("A", "06", "10113300", "01", "00000", "1990", "2026"),  # matches everything
        ("B", "06", "10113300", "02", "00000", "1990", "2026"),  # wrong data_type
        ("C", "06", "10113300", "01", "10180", "1990", "2026"),  # wrong area (not statewide)
        ("D", "06", "10000000", "01", "00000", "1990", "2026"),  # not in codes
        ("E", "06", "10113300", "01", "00000", "1990", "2016"),  # ends before window starts
        ("F", "06", "10113300", "01", "00000", "2025", "2026"),  # begins after window ends
    ])
    out = m.qualifying_series(df, {"10113300"}, "01", "00000")
    assert out["series_id"].to_list() == ["A"]


def test_qualifying_series_keeps_a_series_that_only_partially_overlaps_the_window():
    """The Interfaces wording is "overlapping the D1 window", not "fully covering" it -- a
    series that starts mid-window or ends mid-window still counts."""
    df = _series_frame([
        ("PARTIAL_START", "06", "10113300", "01", "00000", "2020", "2026"),
        ("PARTIAL_END", "06", "10113300", "01", "00000", "1990", "2019"),
    ])
    out = m.qualifying_series(df, {"10113300"}, "01", "00000")
    assert sorted(out["series_id"].to_list()) == ["PARTIAL_END", "PARTIAL_START"]


# --- excluded_broader_codes --------------------------------------------------------------------


def test_excluded_broader_codes_returns_the_logging_named_code_not_selected():
    named = [
        {"industry_code": "10000000", "industry_name": "Mining and Logging"},
        {"industry_code": "10113300", "industry_name": "Logging"},
        {"industry_code": "15000000", "industry_name": "Mining, Logging and Construction"},
    ]
    out = m.excluded_broader_codes(named, {"10000000", "10113300"})
    assert out == [{"industry_code": "15000000",
                    "industry_name": "Mining, Logging and Construction"}]


def test_excluded_broader_codes_empty_when_every_named_code_is_a_candidate():
    """The branch a future, narrower BLS vocabulary would take -- must return [], not a stale
    non-empty list, once nothing is left out."""
    named = [{"industry_code": "10000000", "industry_name": "Mining and Logging"}]
    assert m.excluded_broader_codes(named, {"10000000", "10113300"}) == []


# --- near_miss_states ------------------------------------------------------------------------


def test_near_miss_states_keeps_only_states_the_main_selection_left_at_none():
    excluded_series = [
        {"state_code": "11", "industry_code": "15000000", "series_id": "X1"},  # DC: none -> kept
        {"state_code": "06", "industry_code": "15000000", "series_id": "X2"},  # CA: 1133 already
    ]
    level_by_state = {"11": "none", "06": "1133"}
    out = m.near_miss_states(excluded_series, level_by_state)
    assert out == [{"state_code": "11", "industry_code": "15000000", "series_id": "X1"}]


def test_near_miss_states_empty_when_no_excluded_series_at_all():
    assert m.near_miss_states([], {"11": "none"}) == []


# --- broader_code_note -------------------------------------------------------------------------


def test_broader_code_note_says_nothing_excluded_when_the_list_is_empty():
    """The branch no real run has taken -- today's fetch always carries 15000000. A future run
    where every logging-named code is a candidate must say so, not carry today's finding."""
    note = m.broader_code_note([], [])
    assert "No SAE industry code" in note
    assert "Mining, Logging and Construction" not in note


def test_broader_code_note_names_the_excluded_code_and_the_near_miss_states():
    excluded = [{"industry_code": "15000000",
                "industry_name": "Mining, Logging and Construction"}]
    near_miss = [{"state_code": "11", "industry_code": "15000000", "series_id": "X1"},
                {"state_code": "10", "industry_code": "15000000", "series_id": "X2"}]
    note = m.broader_code_note(excluded, near_miss)
    assert "15000000 ('Mining, Logging and Construction')" in note
    assert "10, 11" in note
    assert "unanchored substring match" in note


def test_broader_code_note_reports_excluded_with_no_near_miss_states():
    """The branch where a broader code is excluded but no state's classification actually
    depends on it -- must not claim a near-miss that did not happen."""
    excluded = [{"industry_code": "15000000",
                "industry_name": "Mining, Logging and Construction"}]
    note = m.broader_code_note(excluded, [])
    assert "15000000" in note
    assert "No state's only D1-window-overlapping" in note


def test_broader_code_note_derives_the_near_miss_level_not_supersector_literal():
    """A future excluded code that embeds e.g. NAICS 1131 (a sibling of 1133, per
    test_level_of_a_sibling_naics_subsector_is_other_not_1133) resolves to 'other', not
    'supersector' -- the note must say so instead of a typed 'supersector' literal."""
    excluded = [{"industry_code": "99113100", "industry_name": "Some Future Logging Sibling"}]
    near_miss = [{"state_code": "11", "industry_code": "99113100", "series_id": "X1"}]
    note = m.broader_code_note(excluded, near_miss)
    assert "'other'" in note
    assert "'supersector'" not in note


# --- window_coverage_note ---------------------------------------------------------------------


def _series_df(rows: list[tuple[str, str, str]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=["series_id", "begin_year", "end_year"], orient="row")


def test_window_coverage_note_true_when_every_series_spans_the_full_window():
    df = _series_df([("A", "1990", "2026"), ("B", "2017", "2024")])
    covered, note = m.window_coverage_note(df)
    assert covered is True
    assert "latest begin_year observed: 2017" in note
    assert "earliest end_year observed: 2024" in note


def test_window_coverage_note_false_and_names_a_partially_overlapping_series():
    """The branch this task's dispatch flagged as unchecked in the brief's illustrative code:
    a series that only overlaps part of D1 must not be silently counted as full coverage."""
    df = _series_df([("FULL", "1990", "2026"), ("LATE_START", "2020", "2026")])
    covered, note = m.window_coverage_note(df)
    assert covered is False
    assert "LATE_START" in note
    assert "FULL" not in note


def test_window_coverage_note_false_when_series_is_empty():
    df = _series_df([])
    covered, note = m.window_coverage_note(df)
    assert covered is False
    assert "no qualifying series exist" in note


# --- granularity_note --------------------------------------------------------------------------


def test_granularity_note_explains_absence_when_113310_is_not_a_defined_code():
    """Also pins that the excluded code(s) are named from the data passed in, not a typed
    literal: a future run whose only sub-supersector code differs from today's "10113300"
    must show whatever code it actually finds."""
    rows = [
        {"industry_code": "10000000", "level": "supersector"},
        {"industry_code": "10113300", "level": "1133"},
    ]
    note = m.granularity_note(rows)
    assert "defines no SAE industry code at the NAICS 5- or 6-digit depth" in note
    assert "CES/SAE itself stops short of 113310" in note
    assert "10113300 (1133)" in note


def test_granularity_note_explains_zero_differently_when_113310_is_defined():
    """The branch no real run has taken -- CES/SAE defines no such code today. A future
    vintage that does add one must not repeat today's "the code is absent" framing."""
    rows = [
        {"industry_code": "10000000", "level": "supersector"},
        {"industry_code": "10113300", "level": "1133"},
        {"industry_code": "10113310", "level": "113310"},
    ]
    note = m.granularity_note(rows)
    assert "does define an SAE industry code at the 113310" in note
    assert "not that the code is absent" in note
    assert "stops short of 113310" not in note
