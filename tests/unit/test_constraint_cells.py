"""§7.7 target cells: the key, the two families, and what makes them distinguishable."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl
import pytest

from logging_employment.constraints import cells
from logging_employment.contracts import TARGET_CELL_SCHEMA, HarmonizedData
from logging_employment.errors import ConceptViolationError


def _data(monthly: pl.DataFrame, size: pl.DataFrame) -> HarmonizedData:
    empty = pl.DataFrame()
    return HarmonizedData(
        qcew_monthly=monthly, qcew_national_size=size, cbp_state_size=empty, bridge=empty
    )


def test_the_string_builder_and_the_expression_agree(
    make_monthly: Callable[..., pl.DataFrame],
) -> None:
    frame = make_monthly({})
    built = cells.state_total_cells(frame, size_concept="march_reference")
    assert built["cell_id"][0] == cells.cell_id(
        cells.KIND_STATE_TOTAL,
        state_fips="01",
        reference_month="2024-03",
        ownership_code="5",
        industry_code="113310",
        naics_vintage="NAICS 2022",
        size_class=cells.TOTAL_SIZE_CLASS,
    )


def test_a_state_total_and_a_national_size_cell_never_share_an_id(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # §7.7: "Size cells and total cells MUST have distinct IDs."
    built = cells.build_target_cells(
        _data(
            make_monthly({}, {"area_fips": "US000", "area_type": "national", "state_fips": None}),
            make_size({}),
        ),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert built["cell_id"].n_unique() == built.height == 3
    kinds = {cid.split("|")[0] for cid in built["cell_id"]}
    assert kinds == {"state_total", "national_total", "national_size"}


def test_a_national_cell_carries_US_rather_than_a_null_state_fips(
    make_monthly: Callable[..., pl.DataFrame],
) -> None:
    # A null would be indistinguishable from a missing value in a join; "US" cannot collide with
    # any two-character FIPS.
    built = cells.national_total_cells(
        make_monthly({"area_fips": "US000", "area_type": "national", "state_fips": None}),
        size_concept="march_reference",
        reference_months=["2024-03"],
    )
    assert built["state_fips"].to_list() == ["US"]


def test_a_suppressed_cell_carries_a_null_value_and_a_true_zero_carries_zero(
    make_monthly: Callable[..., pl.DataFrame],
) -> None:
    built = cells.state_total_cells(
        make_monthly(
            {
                "state_fips": "02",
                "observation_status": "suppressed",
                "employment_value": None,
                "disclosure_code": "N",
            },
            {
                "state_fips": "04",
                "observation_status": "true_zero",
                "employment_value": 0,
                "disclosure_code": "-",
            },
        ),
        size_concept="march_reference",
    )
    by_state = dict(zip(built["state_fips"], built["observed_value"], strict=True))
    assert by_state["02"] is None
    assert by_state["04"] == 0


def test_only_the_target_industry_reaches_the_size_family(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # qcew_national_size carries every industry; 99% of its rows are not Logging.
    built = cells.build_target_cells(
        _data(make_monthly({}), make_size({}, {"industry_code": "111110"})),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert set(built["industry_code"]) == {"113310"}


def test_two_release_vintages_for_one_cell_halt_rather_than_stack(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # INV-007: constraints from incompatible release vintages are never stacked silently.
    with pytest.raises(ConceptViolationError, match="release vintage"):
        cells.build_target_cells(
            _data(
                make_monthly({}, {"release_vintage": "2024q1r2", "snapshot_id": "2024q1r2"}),
                make_size({}),
            ),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_a_status_no_builder_covers_halts_rather_than_reaching_the_solver(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    # `absent` is in contracts.OBSERVATION_STATUSES and is written by no parser. A cell carrying it
    # would get no fixing row and no nonnegativity row, and would reach the solver unconstrained.
    with pytest.raises(ConceptViolationError, match="absent"):
        cells.build_target_cells(
            _data(
                make_monthly({}, {"state_fips": "02", "observation_status": "absent"}),
                make_size({}),
            ),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_a_published_cell_with_no_parseable_value_halts(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    with pytest.raises(ConceptViolationError, match="no parseable value"):
        cells.build_target_cells(
            _data(make_monthly({"employment_value": None}), make_size({})),
            industry_code="113310",
            ownership_code="5",
            size_concept="march_reference",
        )


def test_the_built_frame_matches_the_shipped_schema(
    make_monthly: Callable[..., pl.DataFrame], make_size: Callable[..., pl.DataFrame]
) -> None:
    built = cells.build_target_cells(
        _data(make_monthly({}), make_size({})),
        industry_code="113310",
        ownership_code="5",
        size_concept="march_reference",
    )
    assert built.schema == pl.Schema(TARGET_CELL_SCHEMA)
    assert built["cell_id"].to_list() == sorted(built["cell_id"].to_list())
