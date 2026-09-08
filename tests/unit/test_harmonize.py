"""Versioned dimensions, bridges, the 113310 crosswalk, and the two concept guards."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl
import pytest

from logging_employment.constants import STATES_DC_FIPS
from logging_employment.contracts import BRIDGE_SCHEMA, validate_frame
from logging_employment.errors import ConceptViolationError, UnsupportedReferenceYearError
from logging_employment.harmonize import bridge, concepts, dimensions, disclosure, naics

BRIDGE_ROW = {
    "bridge_id": "cbp_march_to_qcew_month",
    "source_concept": "CBP employment, week including March 12",
    "target_concept": "QCEW monthly employment, pay period including the 12th",
    "valid_start": "2017-01",
    "valid_end": "2024-12",
    "method": "measurement_model",
    "uncertainty_treatment": "estimated in the Stage 6 measurement model",
    "verification_status": "declared_not_estimated",
}


def _flat(text: str) -> str:
    """Collapse runs of whitespace so a wrapped sentence matches an unwrapped one."""
    return re.sub(r"\s+", " ", text)


def test_all_nine_section_86_dimensions_exist() -> None:
    assert set(dimensions.DIMENSIONS) == {
        "geography",
        "naics",
        "ownership",
        "source_universe",
        "statistical_unit",
        "reference_period",
        "size_concept",
        "release_status",
        "disclosure_regime",
    }


def test_every_dimension_frame_carries_a_version_column() -> None:
    for name in dimensions.DIMENSIONS:
        frame = dimensions.dimension_frame(name)
        assert "dimension_version" in frame.columns
        assert frame.height > 0


def test_an_unknown_dimension_is_not_silently_empty() -> None:
    with pytest.raises(KeyError, match="ownership_code"):
        dimensions.dimension_frame("ownership_code")


def test_the_geography_dimension_is_the_states_and_dc_constant() -> None:
    # Derived from `constants`, so widening the geography universe cannot leave this behind.
    members = dimensions.dimension_frame("geography")["member"].to_list()
    assert members == list(STATES_DC_FIPS)


def test_the_regime_dimension_covers_every_regime_the_registry_can_return() -> None:
    # Task 12 owns the year -> regime mapping; this dimension enumerates the members. A regime
    # the registry can emit but the dimension does not list would break INV-007's promise that
    # nothing stacks across incompatible vintages without a declared member to stack on.
    assert set(disclosure.CBP_REGIME_BY_YEAR.values()) <= set(
        dimensions.DIMENSIONS["disclosure_regime"]
    )


def test_bridge_frame_matches_the_declared_schema() -> None:
    validate_frame(bridge.bridge_frame([BRIDGE_ROW]), BRIDGE_SCHEMA, "bridge")


def test_a_bridge_row_missing_a_field_fails_closed() -> None:
    # Polars would render the absent field as null. A bridge whose verification_status is silently
    # null asserts nothing about whether the mapping was estimated or declared (§8.6).
    incomplete = {k: v for k, v in BRIDGE_ROW.items() if k != "verification_status"}
    with pytest.raises(ValueError, match="verification_status"):
        bridge.bridge_frame([incomplete])


def test_the_window_spans_two_naics_vintages() -> None:
    assert naics.vintage_for_year(2017) == "NAICS 2017"
    assert naics.vintage_for_year(2021) == "NAICS 2017"
    assert naics.vintage_for_year(2022) == "NAICS 2022"
    assert naics.vintage_for_year(2024) == "NAICS 2022"


def test_a_reference_year_below_the_naics_2017_era_fails_closed() -> None:
    # BLS puts 2011-2016 on NAICS 2012 and 2007-2010 on NAICS 2007, so the two-branch rule above
    # is correct only at or above 2017; below it the rule returned "NAICS 2017" for a year BLS
    # classifies otherwise. Refusing rather than classifying per BLS's table is the same choice
    # `build.py` already makes for an unestablished CBP disclosure regime, and for the same
    # reason: this repo can LABEL a pre-2017 year from BLS's table but cannot PROCESS one.
    # `assert_113310_survives_the_window` requires exactly {2017, 2022}, `validate/regimes.py`
    # asserts a single vintage seam by construction, and `baselines/historical.py` filters its
    # lookback on vintage equality -- so a third label would silently shrink every baseline
    # window rather than fail, after composing itself into `cell_id`.
    for year in (2016, 2011, 2006):
        with pytest.raises(UnsupportedReferenceYearError, match=str(year)):
            naics.vintage_for_year(year)


def test_the_recorded_bls_table_does_not_drift_from_the_live_rule() -> None:
    # `_BLS_VINTAGE_ERAS` documents BLS's published mapping but never emits one, so nothing else
    # would catch it disagreeing with the rule that does emit. Pinned across the supported range
    # only -- below 2017 the two deliberately differ, which is the whole point of the guard.
    for year in range(2017, 2025):
        assert naics.bls_vintage_for_year(year) == naics.vintage_for_year(year)


def test_the_bls_table_still_names_the_vintages_the_refused_years_carry() -> None:
    # The refusal message quotes this, so a wrong entry would send someone widening the window
    # after the wrong crosswalk. Values are BLS's, quoted at `_BLS_VINTAGE_ERAS`.
    assert naics.bls_vintage_for_year(2016) == "NAICS 2012"
    assert naics.bls_vintage_for_year(2011) == "NAICS 2012"
    assert naics.bls_vintage_for_year(2010) == "NAICS 2007"
    assert naics.bls_vintage_for_year(2006) == "NAICS 2002"
    assert "no NAICS vintage" in naics.bls_vintage_for_year(1989)


def test_113310_survives_the_window_mechanically() -> None:
    # D1 fixes a window spanning the 2017 -> 2022 transition, so this exercises the boundary.
    naics.assert_113310_survives_the_window()
    frame = naics.crosswalk_113310()
    assert set(frame["vintage"].to_list()) == {"2017", "2022"}
    assert frame["title"].unique().to_list() == ["Logging"]


def test_the_crosswalk_reads_every_column_as_a_string() -> None:
    # `vintage` and `parent_code` infer as Int64 under a default read, which makes the vintage
    # comparisons in `assert_113310_survives_the_window` raise on a string literal. Codes are
    # strings everywhere else in this package for the same reason.
    frame = naics.crosswalk_113310()
    assert set(frame.dtypes) == {pl.String}


def test_the_vendored_crosswalk_keeps_its_provenance_header() -> None:
    # The caveats have to travel with the data, not only with the module that reads it.
    text = Path(naics.__file__).parent.joinpath("naics_113310.csv").read_text()
    # Joined, then whitespace-collapsed: the caveat is a sentence, and which column it happens to
    # wrap at is not part of the claim.
    header = _flat(" ".join(l.lstrip("# ") for l in text.splitlines() if l.startswith("#")))
    assert "naics_2017_to_2022.csv" in header
    assert "it is NOT a Census column" in header


def test_the_crosswalk_docstring_does_not_call_link_type_a_census_column() -> None:
    # Collapsed before matching: the plan's own docstring wraps this phrase across a line break,
    # so the unbroken-string form of this assertion fails against the prose it is checking.
    source = _flat(naics.__doc__ or "")
    assert "not a Census column" in source or "NOT a Census column" in source


def test_a_split_or_merged_code_would_fail_the_window_assertion() -> None:
    # The assertion's value is that it fails; without this, nothing shows it can.
    original = naics.crosswalk_113310()
    doctored = original.with_columns(
        pl.when(pl.col("vintage") == "2017")
        .then(pl.lit("1:n"))
        .otherwise(pl.col("link_type_to_next"))
        .alias("link_type_to_next")
    )
    with pytest.raises(ValueError, match="one-to-one"):
        naics.assert_113310_survives_the_window(frame=doctored)


def test_a_retitled_code_would_fail_the_window_assertion() -> None:
    doctored = naics.crosswalk_113310().with_columns(
        pl.when(pl.col("vintage") == "2022")
        .then(pl.lit("Logging and Forestry"))
        .otherwise(pl.col("title"))
        .alias("title")
    )
    with pytest.raises(ValueError, match="title is not stable"):
        naics.assert_113310_survives_the_window(frame=doctored)


def test_a_flagged_change_indicator_would_fail_the_window_assertion() -> None:
    doctored = naics.crosswalk_113310().with_columns(pl.lit("R").alias("change_indicator"))
    with pytest.raises(ValueError, match="change_indicator"):
        naics.assert_113310_survives_the_window(frame=doctored)


def test_enterprise_size_is_rejected_as_an_establishment_size_measurement() -> None:
    with pytest.raises(ConceptViolationError, match="enterprise"):
        concepts.reject_enterprise_size("enterprise", "susb")


def test_establishment_size_passes_the_guard() -> None:
    concepts.reject_enterprise_size("establishment", "cbp")


def test_nonemployer_is_rejected_from_the_core_total() -> None:
    with pytest.raises(ConceptViolationError, match="nonemployer"):
        concepts.reject_nonemployer_in_core_total("nonemployer")
