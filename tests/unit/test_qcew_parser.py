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


# The QCEW natural key, in the output's column vocabulary. `reference_month` carries year,
# quarter and month position, so it stands in for all three.
NATURAL_KEY = [
    "area_fips",
    "ownership_code",
    "industry_code",
    "aggregation_level",
    "size_code",
    "reference_month",
]


def test_source_row_hash_is_one_to_one_with_the_natural_key() -> None:
    """The general property: one hash per source row, for every row in the fixture.

    Asserted over the whole frame rather than at a known collision, so it holds against any
    fixture rather than pinning one observed pair.
    """
    out = _parsed()
    assert out.n_unique(subset=NATURAL_KEY) == out.height, "the natural key is not a key"
    assert out["source_row_hash"].n_unique() == out.height


def test_the_collision_the_plans_narrower_key_produced() -> None:
    """Regression pin for the specific pair that exposed the defect.

    The plan hashed `area_fips|year|qtr|month_column`. Area 26165 in 2017-03 publishes both a
    Local Government cell and a Private one, so that key gave two universes one identity --
    INV-007's failure mode. This is a fact about `slice_2017q1.csv`, which is tracked and cannot
    drift; the general property is asserted above.
    """
    pair = _parsed().filter(
        (pl.col("area_fips") == "26165")
        & (pl.col("reference_month") == "2017-03")
        & (pl.col("aggregation_level") == "78")
    )
    assert set(pair["ownership_code"]) == {"3", "5"}
    assert pair["source_row_hash"].n_unique() == pair.height


def test_the_hash_is_stable_across_release_vintages() -> None:
    """A revision re-publishes the same source row, so the hash must not move.

    This is a decision, not an accident: vintage is deliberately excluded so that the same cell
    at two vintages is joinable. The identity of a harmonized row is the pair
    (`source_row_hash`, `release_vintage`), and anything deduplicating must key on both.
    """
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    first = qcew.parse_qcew_monthly(
        frame,
        snapshot_id="pull-a",
        release_vintage="2017Q1",
        release_status="preliminary",
        naics_vintage="NAICS 2017",
    )
    revised = qcew.parse_qcew_monthly(
        frame,
        snapshot_id="pull-b",
        release_vintage="2018Q2",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert first["source_row_hash"].to_list() == revised["source_row_hash"].to_list()
    stacked = pl.concat([first, revised])
    assert stacked.n_unique(subset=["source_row_hash", "release_vintage"]) == stacked.height


def test_release_status_distinguishes_preliminary_from_final() -> None:
    final = qcew.parse_qcew_monthly(
        _row(),
        snapshot_id="s",
        release_vintage="v",
        release_status="final",
        naics_vintage="NAICS 2017",
    )
    prelim = qcew.parse_qcew_monthly(
        _row(),
        snapshot_id="s",
        release_vintage="v",
        release_status="preliminary",
        naics_vintage="NAICS 2017",
    )
    assert final["release_status"].unique().to_list() == ["final"]
    assert prelim["release_status"].unique().to_list() == ["preliminary"]
    # SRC-QCEW-005: a final national control may not be combined with preliminary state values in
    # a hard equation. The column is what lets Stage 2 refuse that combination.
    assert "release_status" in final.columns
