"""Constants carry the measured code sets, and say so."""

from __future__ import annotations

from pathlib import Path

from logging_employment import constants


def test_states_dc_has_fifty_one_members() -> None:
    assert len(constants.STATES_DC_FIPS) == 51
    assert len(set(constants.STATES_DC_FIPS)) == 51


def test_state_areas_are_fips_plus_three_zeroes() -> None:
    assert constants.STATE_AREAS == frozenset(f"{f}000" for f in constants.STATES_DC_FIPS)
    # DC is IN the universe even though it publishes nothing
    assert "11000" in constants.STATE_AREAS
    assert "72000" not in constants.STATE_AREAS  # Puerto Rico is not


def test_disclosure_allowlist_is_the_three_measured_codes() -> None:
    assert constants.QCEW_DISCLOSURE_CODES == frozenset({"", "N", "-"})


def test_the_allowlist_docstring_does_not_claim_a_titles_file_defines_it() -> None:
    # A deliberate prose pin, and the only one in this plan. It is framed negatively -- it fails if
    # someone rewrites the comment to claim BLS documents these codes -- which is the one shape
    # worth pinning. Do not copy this pattern to assert that a sentence exists.
    # BLS publishes no titles file for disclosure_code (Stage 0: titles_available.disclosure_code
    # is null). A comment claiming otherwise would misdescribe the provenance.
    source = Path(constants.__file__).read_text()
    marker = "QCEW_DISCLOSURE_CODES"
    block = source[source.index(marker) : source.index(marker) + 800]
    assert "measured" in block
    assert "no titles file" in block
