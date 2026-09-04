import polars as pl

from qcew_size import has_simultaneous_state_industry_size

STATE_AREAS = {"01000", "06000", "41000"}


def frame(rows):
    return pl.DataFrame(
        rows,
        schema={"area_fips": pl.Utf8, "industry_code": pl.Utf8, "size_code": pl.Utf8},
        orient="row",
    )


def test_national_industry_size_is_not_simultaneous_state_detail():
    df = frame([("US000", "113310", "1"), ("US000", "113310", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_state_sector_size_is_not_simultaneous_six_digit_detail():
    df = frame([("41000", "11", "1"), ("41000", "113", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_state_six_digit_aggregate_size_code_does_not_count():
    """The aggregate code carries no size breakdown, so it never satisfies the predicate.
    '0' here is this fixture's aggregate code; the script derives the real one from the
    fetched titles file and passes it in."""
    df = frame([("41000", "113310", "0")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_one_true_row_flips_the_verdict():
    df = frame([("US000", "113310", "1"), ("41000", "113310", "3")])
    assert has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_county_row_is_not_a_state_row():
    df = frame([("41005", "113310", "3")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")
