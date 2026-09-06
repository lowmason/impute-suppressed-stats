import polars as pl
import pytest
from qcew_size import all_sizes_code, has_simultaneous_state_industry_size

STATE_AREAS = {"01000", "06000", "41000"}

# The real fetched titles/size_code.csv (Task 3), 10 rows -- used to pin all_sizes_code's
# success path against the vocabulary it actually runs against, not just an abstract fixture.
REAL_SIZE_TITLES = {
    "0": "All establishment sizes",
    "1": "Fewer than 5 employees per establishment",
    "2": "5 to 9 employees per establishment",
    "3": "10 to 19 employees per establishment",
    "4": "20 to 49 employees per establishment",
    "5": "50 to 99 employees per establishment",
    "6": "100 to 249 employees per establishment",
    "7": "250 to 499 employees per establishment",
    "8": "500 to 999 employees per establishment",
    "9": "1000 or more employees per establishment",
}


def frame(rows):
    return pl.DataFrame(
        rows,
        schema={"area_fips": pl.Utf8, "industry_code": pl.Utf8, "size_code": pl.Utf8},
        orient="row",
    )


def test_national_industry_size_is_not_simultaneous_state_detail():
    df = frame([("US000", "113310", "1"), ("US000", "113310", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0"
    )


def test_state_sector_size_is_not_simultaneous_six_digit_detail():
    df = frame([("41000", "11", "1"), ("41000", "113", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0"
    )


def test_state_six_digit_aggregate_size_code_does_not_count():
    """The aggregate code carries no size breakdown, so it never satisfies the predicate.
    '0' here is this fixture's aggregate code; the script derives the real one from the
    fetched titles file and passes it in."""
    df = frame([("41000", "113310", "0")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0"
    )


def test_one_true_row_flips_the_verdict():
    df = frame([("US000", "113310", "1"), ("41000", "113310", "3")])
    assert has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0"
    )


def test_county_row_is_not_a_state_row():
    df = frame([("41005", "113310", "3")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0"
    )


# --- all_sizes_code -----------------------------------------------------------------------
#
# The one helper the FIX-13 correction (commit 68522a0) added: it derives the aggregate
# size_code from the fetched titles file rather than a hardcoded "0", and is load-bearing
# because it is the single value has_simultaneous_state_industry_size's predicate excludes.
# Added in fix round 1 after the review found this function had zero test coverage --
# everything below had previously been checked by hand, described in prose, not pinned.


def test_all_sizes_code_matches_the_one_real_aggregate_title():
    """Success path against the actual fetched titles/size_code.csv vocabulary (Task 3): code
    '0', title 'All establishment sizes', is the only match."""
    assert all_sizes_code(REAL_SIZE_TITLES) == "0"


def test_all_sizes_code_raises_when_no_title_matches():
    titles = {k: v for k, v in REAL_SIZE_TITLES.items() if k != "0"}
    with pytest.raises(RuntimeError, match="got 0"):
        all_sizes_code(titles)


def test_all_sizes_code_raises_when_more_than_one_title_matches():
    """An ambiguous or renamed vocabulary must fail loudly rather than silently picking one --
    that is the whole reason this helper exists instead of a hardcoded literal."""
    titles = dict(REAL_SIZE_TITLES)
    titles["10"] = "All sizes (alternate wording)"
    with pytest.raises(RuntimeError, match="got 2"):
        all_sizes_code(titles)


def test_all_sizes_code_treats_a_null_title_as_no_match_not_a_crash():
    """`title or ""` in the implementation exists so a None title never reaches `.match(None)`
    (which would raise TypeError, not the intended RuntimeError). Replacing the one matching
    row's title with None must drop the match count to 0, not crash differently."""
    titles = dict(REAL_SIZE_TITLES)
    titles["0"] = None
    with pytest.raises(RuntimeError, match="got 0"):
        all_sizes_code(titles)


def test_all_sizes_code_treats_an_empty_title_as_no_match():
    titles = dict(REAL_SIZE_TITLES)
    titles["0"] = ""
    with pytest.raises(RuntimeError, match="got 0"):
        all_sizes_code(titles)
