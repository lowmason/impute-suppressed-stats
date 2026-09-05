"""The §17.1 parser contracts: suppression to null, true zeros preserved, months expanded."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import QCEW_MONTHLY_SCHEMA, validate_frame
from logging_employment.errors import UnknownDisclosureCodeError
from logging_employment.ingest import qcew

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


def _parsed() -> pl.DataFrame:
    return qcew.parse_qcew_monthly(
        qcew.read_slice_csv(FIXTURE.read_bytes()),
        snapshot_id="snap",
        release_vintage="2017Q1",
        release_status="final",
        naics_vintage="NAICS 2017",
    )


def _row(**overrides: str) -> pl.DataFrame:
    base = {
        "area_fips": "01000",
        "own_code": "5",
        "industry_code": "113310",
        "agglvl_code": "58",
        "size_code": "0",
        "year": "2017",
        "qtr": "1",
        "disclosure_code": "",
        "qtrly_estabs": "10",
        "month1_emplvl": "100",
        "month2_emplvl": "110",
        "month3_emplvl": "120",
        "total_qtrly_wages": "999",
    }
    base.update(overrides)
    return pl.DataFrame({k: [v] for k, v in base.items()})


def test_output_matches_the_declared_schema() -> None:
    validate_frame(_parsed(), QCEW_MONTHLY_SCHEMA, "qcew_monthly")


def test_a_suppression_coded_zero_parses_to_null() -> None:
    out = qcew.parse_qcew_monthly(
        _row(
            disclosure_code="N",
            qtrly_estabs="22",
            month1_emplvl="0",
            month2_emplvl="0",
            month3_emplvl="0",
            total_qtrly_wages="0",
        ),
        snapshot_id="s",
        release_vintage="v",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out["employment_value"].to_list() == [None, None, None]
    assert out["employment_raw"].to_list() == ["0", "0", "0"]
    assert out["observation_status"].unique().to_list() == ["suppressed"]
    # The establishment count survives suppression -- Stage 0 measured this on all 1227 cells.
    assert out["qtrly_establishments"].unique().to_list() == [22]
    assert out["is_true_zero"].unique().to_list() == [False]


def test_a_true_zero_is_preserved_because_the_establishment_count_supports_it() -> None:
    out = qcew.parse_qcew_monthly(
        _row(
            disclosure_code="-",
            qtrly_estabs="0",
            month1_emplvl="0",
            month2_emplvl="0",
            month3_emplvl="0",
            total_qtrly_wages="0",
        ),
        snapshot_id="s",
        release_vintage="v",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out["employment_value"].to_list() == [0, 0, 0]
    assert out["is_true_zero"].unique().to_list() == [True]
    assert out["observation_status"].unique().to_list() == ["true_zero"]


def test_a_dash_row_with_establishments_halts_rather_than_claiming_a_true_zero() -> None:
    with pytest.raises(ValueError, match="qtrly_estabs"):
        qcew.parse_qcew_monthly(
            _row(
                disclosure_code="-",
                qtrly_estabs="7",
                month1_emplvl="0",
                month2_emplvl="0",
                month3_emplvl="0",
                total_qtrly_wages="0",
            ),
            snapshot_id="s",
            release_vintage="v",
            release_status="final",
            naics_vintage="NAICS 2017",
        )


def test_an_unknown_disclosure_code_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureCodeError, match="Z"):
        qcew.parse_qcew_monthly(
            _row(disclosure_code="Z"),
            snapshot_id="s",
            release_vintage="v",
            release_status="final",
            naics_vintage="NAICS 2017",
        )


def test_three_monthly_columns_expand_to_three_rows() -> None:
    out = qcew.parse_qcew_monthly(
        _row(),
        snapshot_id="s",
        release_vintage="v",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out.height == 3
    assert out["reference_month"].to_list() == ["2017-01", "2017-02", "2017-03"]
    assert out["employment_value"].to_list() == [100, 110, 120]
    assert out["reference_quarter"].unique().to_list() == ["2017Q1"]


def test_quarter_three_maps_to_july_august_september() -> None:
    out = qcew.parse_qcew_monthly(
        _row(qtr="3"),
        snapshot_id="s",
        release_vintage="v",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out["reference_month"].to_list() == ["2017-07", "2017-08", "2017-09"]


def test_area_fips_round_trips_with_leading_zeros_intact() -> None:
    out = _parsed()
    assert out.filter(pl.col("area_fips") == "01000").height > 0
    assert out["area_fips"].str.len_chars().min() == 5


def test_state_fips_is_the_first_two_characters_for_state_rows() -> None:
    out = _parsed().filter(pl.col("aggregation_level") == "58")
    assert (out["state_fips"] == out["area_fips"].str.slice(0, 2)).all()


def test_source_naics_vintage_survives_ingestion() -> None:
    assert _parsed()["naics_vintage"].unique().to_list() == ["NAICS 2017"]


def test_every_observation_status_is_in_the_declared_vocabulary() -> None:
    from logging_employment.contracts import OBSERVATION_STATUSES

    assert set(_parsed()["observation_status"].unique()) <= set(OBSERVATION_STATUSES)


def test_source_row_hash_identifies_a_row_uniquely() -> None:
    """One hash per output row, or the column is not an identity.

    The slice fixture carries several ownership sectors and aggregation levels for the same area
    and month, so a hash omitting any of them collides on real data rather than only in principle.
    """
    out = _parsed()
    assert out["source_row_hash"].n_unique() == out.height


def test_source_row_hash_separates_ownership_sectors_in_the_same_area_and_month() -> None:
    """The collision the fixture actually produced when the key omitted ownership.

    Area 26165 in 2017-03 publishes both a Local Government cell and a Private one. They are
    different observations of different universes; conflating them is what INV-007 forbids.
    """
    pair = _parsed().filter(
        (pl.col("area_fips") == "26165")
        & (pl.col("reference_month") == "2017-03")
        & (pl.col("aggregation_level") == "78")
    )
    assert set(pair["ownership_code"]) == {"3", "5"}
    assert pair["source_row_hash"].n_unique() == pair.height
