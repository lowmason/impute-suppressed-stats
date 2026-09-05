"""SRC-CBP-001..003: predicate and size codes from metadata, flags preserved, fail closed."""

from __future__ import annotations

import json
import re
from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import CBP_STATE_SIZE_SCHEMA, validate_frame
from logging_employment.errors import (
    SchemaMismatchError,
    UnknownDisclosureCodeError,
    UnknownSizeCodeError,
)
from logging_employment.ingest import cbp

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "cbp"
DATA = json.loads((FIX / "data_113310_2023.json").read_text())
DATA_2017 = json.loads((FIX / "data_113310_2017.json").read_text())
EMPSZES_2017 = json.loads((FIX / "empszes_2017.json").read_text())
EMPSZES_2023 = json.loads((FIX / "empszes_2023.json").read_text())
LAYOUT_2017 = (FIX / "state_layout_2017.txt").read_text()
# The response `build_query` actually produces, fetched live. Stage 0's archived extract
# selected neither the NAICS predicate nor LFO as output columns, so it carries none of the
# duplicate columns Census echoes back and cannot exercise this shape.
LIVE = json.loads((FIX / "data_113310_2023_live.json").read_text())


def _parsed(rows: list, year: int, regime: str) -> pl.DataFrame:
    return cbp.parse_cbp_state_size(
        rows,
        snapshot_id="s",
        reference_year=year,
        predicate="NAICS2017",
        # An arbitrary stamp, not a measurement: Stage 0 recorded no CBP naics_vintage_by_year,
        # and this parser passes the value through untouched. See the module docstring.
        naics_vintage="NAICS 2022",
        regime=regime,
    )


# --------------------------------------------------------------------------------------------
# SRC-CBP-001: the predicate and the size codes come from metadata


def test_the_predicate_is_read_from_metadata_not_computed_from_the_vintage() -> None:
    variables = {"variables": {"NAICS2017": {"label": "2017 NAICS code"}, "EMP": {}}}
    assert cbp.discover_naics_predicate(variables) == "NAICS2017"


def test_a_label_variable_is_not_mistaken_for_the_predicate() -> None:
    variables = {"variables": {"NAICS2017": {}, "NAICS2017_LABEL": {}, "EMP": {}}}
    assert cbp.discover_naics_predicate(variables) == "NAICS2017"


def test_ambiguous_metadata_fails_closed_rather_than_picking_one() -> None:
    variables = {"variables": {"NAICS2017": {}, "NAICS2012": {}}}
    with pytest.raises(ValueError, match="exactly one NAICS predicate"):
        cbp.discover_naics_predicate(variables)


def test_no_naics2022_predicate_is_ever_constructed() -> None:
    # Stage 0 measured NAICS2017 for every year 2017-2023, including the NAICS-2022 vintage years.
    source = Path(cbp.__file__).read_text()
    assert "NAICS2022" not in source


def test_2017_size_codes_come_from_the_official_values_crosswalk() -> None:
    codes = cbp.discover_empszes(EMPSZES_2017, data_rows=DATA)
    assert codes["001"] == "All establishments"
    assert len(codes) >= 44


def test_later_years_take_their_labels_from_the_response_column() -> None:
    codes = cbp.discover_empszes(EMPSZES_2023, data_rows=DATA)
    assert set(codes) == {"001", "210", "220", "230", "241", "242", "251"}
    assert codes["210"] == "Establishments with less than 5 employees"


def test_the_query_selects_lfo_label_as_an_output_column() -> None:
    query = cbp.build_query(2023, "NAICS2017", "113310")
    assert "LFO" in query["get"].split(",")
    assert "LFO_LABEL" in query["get"].split(",")
    assert query["NAICS2017"] == "113310"
    assert query["for"] == "state:*"


# --------------------------------------------------------------------------------------------
# Size bounds: parsed from the published label, fail closed on one that does not parse


def test_size_bounds_are_parsed_from_the_official_labels() -> None:
    assert cbp.size_bounds("Establishments with less than 5 employees") == (0, 4)
    assert cbp.size_bounds("Establishments with 20 to 49 employees") == (20, 49)
    assert cbp.size_bounds("All establishments") == (None, None)


def test_every_label_in_the_official_crosswalk_resolves() -> None:
    # Derived, not typed: run the parser over all 44 codes the 2017 crosswalk publishes and
    # require each to yield either a range or a named non-range. A label that silently nulled
    # its bounds would be a §18.3 silent default, which is what this forbids.
    labels = cbp.discover_empszes(EMPSZES_2017, data_rows=DATA).values()
    bounded = [label for label in labels if cbp.size_bounds(label) != (None, None)]
    unbounded = [label for label in labels if cbp.size_bounds(label) == (None, None)]
    assert len(bounded) + len(unbounded) == len(list(labels))
    assert set(unbounded) == set(cbp.NOT_AN_EMPLOYMENT_RANGE)


def test_the_single_and_paired_employee_labels_carry_real_bounds() -> None:
    # The four classes the plan's three regexes silently nulled.
    assert cbp.size_bounds("Establishments with 1 employee") == (1, 1)
    assert cbp.size_bounds("Establishments with 2 employees") == (2, 2)
    assert cbp.size_bounds("Establishments with 3 or 4 employees") == (3, 4)
    assert cbp.size_bounds("Establishments with 5 or 6 employees") == (5, 6)


def test_open_ended_classes_keep_a_null_upper_bound() -> None:
    assert cbp.size_bounds("Establishments with 1,000 employees or more") == (1000, None)
    assert cbp.size_bounds("Establishments with 20 or more employees") == (20, None)


def test_a_label_with_no_parseable_bounds_fails_closed() -> None:
    with pytest.raises(UnknownSizeCodeError, match="Establishments with a medium number"):
        cbp.size_bounds("Establishments with a medium number of employees")


# --------------------------------------------------------------------------------------------
# SRC-CBP-002 / INV-003: EMPFLAG is a withholding, not a published zero


def test_the_empflag_table_matches_the_fetched_2017_record_layout() -> None:
    # Derived from the Census record layout Stage 0 fetched and this suite ships, so a table
    # typed to disagree with the document fails here rather than in production.
    block = LAYOUT_2017.split("EMPFLAG", 2)[2].split("EMP_NF", 1)[0]
    documented = dict(re.findall(r"^\s+([A-Za-z])\s+(\S.*?)\s*$", block, re.MULTILINE))
    withheld = {code for code, text in documented.items() if "Revised" not in text}
    assert set(cbp.EMPFLAG_WITHHELD_CODES) == withheld
    assert cbp.EMPFLAG_REVISED_CODE in documented
    assert cbp.EMPFLAG_REVISED_CODE not in cbp.EMPFLAG_WITHHELD_CODES


def test_an_empflag_row_is_suppressed_rather_than_a_published_zero() -> None:
    # INV-003. The 2017 extract carries rows flagged 'a' whose EMP is the literal '0'; EMPFLAG
    # is the layout's "Data Suppression Flag", so that 0 is a withholding placeholder.
    out = _parsed(DATA_2017, 2017, "noise_infusion_plus_suppression")
    flagged = out.filter(pl.col("employment_flag") != "")
    assert flagged.height > 0
    assert flagged["disclosure_status"].unique().to_list() == ["suppressed"]
    assert flagged["employment"].null_count() == flagged.height


def test_no_published_row_reports_zero_employment_against_live_establishments() -> None:
    # The invariant stated arithmetically, so it holds without appealing to the flag's meaning:
    # CBP covers employer establishments, so a published cell with establishments and no
    # employment is incoherent. True of both fixtures as parsed.
    for rows, year, regime in (
        (DATA_2017, 2017, "noise_infusion_plus_suppression"),
        (DATA, 2023, "noise_infusion"),
    ):
        out = _parsed(rows, year, regime)
        incoherent = out.filter(
            (pl.col("disclosure_status") == "published")
            & (pl.col("establishments") > 0)
            & (pl.col("employment") == 0)
        )
        assert incoherent.height == 0, f"{year}: {incoherent}"


def test_the_suppressed_row_count_agrees_with_what_stage_0_measured() -> None:
    # Stage 0's cbp_regime summary recorded suppressed_share = 4/188 for 2017. A parser that
    # read those rows as published would disagree with the audit that fed this plan.
    out = _parsed(DATA_2017, 2017, "noise_infusion_plus_suppression")
    assert out.filter(pl.col("disclosure_status") == "suppressed").height == 4
    assert out.height == 188


def test_the_2023_extract_carries_no_withheld_row() -> None:
    # EMPFLAG was discontinued from reference year 2018, so the contrast is the point.
    out = _parsed(DATA, 2023, "noise_infusion")
    assert out["disclosure_status"].unique().to_list() == ["published"]
    assert out["employment"].null_count() == 0


def test_the_revised_data_flag_is_not_read_as_a_withholding() -> None:
    # 'r' shares the EMPFLAG field but the layout defines it as "Revised Data", not a
    # withholding. Collapsing every nonempty flag into "suppressed" would lose a real value.
    revised = _mutate_flag(DATA, cbp.EMPFLAG_REVISED_CODE)
    out = _parsed(revised, 2023, "noise_infusion")
    assert out["disclosure_status"].unique().to_list() == ["published"]
    assert out["employment"].null_count() == 0


def test_an_unknown_employment_flag_fails_closed() -> None:
    unknown = _mutate_flag(DATA, "Q")
    with pytest.raises(UnknownDisclosureCodeError, match="'Q'"):
        _parsed(unknown, 2023, "noise_infusion")


def _mutate_flag(rows: list, flag: str) -> list:
    header, *body = rows
    at = header.index("EMP_F")
    return [header] + [row[:at] + [flag] + row[at + 1 :] for row in body]


# --------------------------------------------------------------------------------------------
# The declared schema, and the fields §7.5 requires to survive


def test_parsed_output_matches_the_declared_schema() -> None:
    validate_frame(_parsed(DATA, 2023, "noise_infusion"), CBP_STATE_SIZE_SCHEMA, "cbp_state_size")


def test_flags_noise_and_legal_form_survive_parsing() -> None:
    out = _parsed(DATA, 2023, "noise_infusion")
    assert set(out.columns) >= {"employment_flag", "employment_noise_range", "legal_form_code"}
    assert out["legal_form_code"].unique().to_list() == ["001"]
    assert out["reference_period"].unique().to_list() == ["week_including_march_12"]
    assert out["disclosure_regime"].unique().to_list() == ["noise_infusion"]


def test_state_fips_keeps_its_leading_zero() -> None:
    out = _parsed(DATA, 2023, "noise_infusion")
    assert "01" in out["state_fips"].to_list()
    assert out["state_fips"].str.len_chars().unique().to_list() == [2]


# --------------------------------------------------------------------------------------------
# The shape `build_query` actually elicits, as opposed to the shape Stage 0 archived


def test_the_live_response_repeats_the_columns_that_are_also_predicates() -> None:
    # Pins the reason `_frame_from_rows` exists; if Census stops echoing, this test says so.
    header = LIVE[0]
    assert header.count("LFO") == 2
    assert header.count("NAICS2017") == 2


def test_the_echoed_predicate_columns_do_not_shift_the_parsed_values() -> None:
    out = _parsed(LIVE, 2023, "noise_infusion")
    validate_frame(out, CBP_STATE_SIZE_SCHEMA, "cbp_state_size")
    assert out["industry_code"].unique().to_list() == ["113310"]
    assert out["legal_form_code"].unique().to_list() == ["001"]
    assert out["size_label"].str.starts_with("Establishments").sum() == out.height - 46


def test_the_live_and_archived_extracts_agree_on_every_shared_measure() -> None:
    # Same year, same query intent, two response shapes. If keying by name dropped a column,
    # these would diverge.
    keys = ["state_fips", "size_code"]
    measures = ["establishments", "employment", "disclosure_status", "size_lower", "size_upper"]
    live = _parsed(LIVE, 2023, "noise_infusion").select(keys + measures)
    archived = _parsed(DATA, 2023, "noise_infusion").select(keys + measures)
    assert live.equals(archived)


def test_disagreeing_duplicate_columns_fail_closed() -> None:
    header, *rows = [list(r) for r in LIVE]
    doctored = [row[:13] + ["999"] + row[14:] for row in rows]
    with pytest.raises(SchemaMismatchError, match="disagreeing values"):
        _parsed([header] + doctored, 2023, "noise_infusion")


def test_the_live_response_serves_the_lfo_label_the_query_asks_for() -> None:
    # Closes the Stage 0 deferral: `lfo_by_year` was null for all eight window years because the
    # column was only ever sent as a filter, never selected.
    header = LIVE[0]
    labels = {row[header.index("LFO_LABEL")] for row in LIVE[1:]}
    assert labels == {"All establishments"}


def test_the_live_response_carries_the_per_cell_noise_flag() -> None:
    # EMP_N_F, which Stage 0 recorded as absent (`emp_n_f_in_response: false`) because its query
    # never selected it. `build_query` does, and every row carries one -- so `EMP_N`, the literal
    # '0' on every row of every year, is not where CBP's noise information lives.
    header = LIVE[0]
    flags = {row[header.index("EMP_N_F")] for row in LIVE[1:]}
    assert flags == {"G", "H", "J"}
    assert {row[header.index("EMP_N")] for row in LIVE[1:]} == {"0"}
