"""The assembled system: what it contains, and what makes its hash and its run id stable."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment import runs
from logging_employment.config import load_config
from logging_employment.constraints import system
from logging_employment.contracts import (
    CONSTRAINT_COEFFICIENT_SCHEMA,
    CONSTRAINT_ROW_SCHEMA,
    TARGET_CELL_SCHEMA,
    HarmonizedData,
)
from logging_employment.errors import ConceptViolationError, IncompatibleMarginError

REPO = Path(__file__).resolve().parents[2]


def _data(make_monthly, make_size) -> HarmonizedData:
    monthly = make_monthly(
        {"state_fips": "01", "observation_status": "observed", "employment_value": 700},
        {
            "state_fips": "02",
            "observation_status": "suppressed",
            "employment_value": None,
            "disclosure_code": "N",
        },
        {
            "area_fips": "US000",
            "area_type": "national",
            "state_fips": None,
            "aggregation_level": "18",
            "employment_value": 1000,
            "qtrly_establishments": 54,
        },
    )
    size = make_size(
        {
            "size_class": "1",
            "establishments": 50,
            "employment": 100,
            "size_lower": 0,
            "size_upper": 4,
        },
        {
            "size_class": "6",
            "establishments": 4,
            "employment": None,
            "size_lower": 100,
            "size_upper": 249,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
    )
    return HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )


def _cfg():
    return load_config(REPO / "config.yaml")


def test_the_system_matches_all_three_schemas(make_monthly, make_size) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    assert built.cells.schema == pl.Schema(TARGET_CELL_SCHEMA)
    assert built.rows.schema == pl.Schema(CONSTRAINT_ROW_SCHEMA)
    assert built.coefficients.schema == pl.Schema(CONSTRAINT_COEFFICIENT_SCHEMA)


def test_the_system_holds_one_row_family_per_builder(make_monthly, make_size) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    prefixes = [cid.split("|")[0] for cid in built.rows["constraint_id"]]
    assert prefixes.count("fix") == 3  # two observed state/national cells, one observed class
    assert prefixes.count("nonneg") == 2  # the suppressed state cell and the suppressed class
    assert prefixes.count("integer") == 2
    assert prefixes.count("size_margin") == 1
    assert prefixes.count("size_support") == 1


def test_no_row_couples_state_cells_to_each_other_or_to_the_national_row(
    make_monthly, make_size
) -> None:
    # The structural form of SRC-QCEW-006's `decline`, asserted on the assembled system rather
    # than only inside the factory.
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    kinds = {cid: cid.split("|")[0] for cid in built.cells["cell_id"]}
    touched = built.coefficients.join(
        pl.DataFrame({"cell_id": list(kinds), "kind": list(kinds.values())}), on="cell_id"
    )
    per_row = touched.group_by("constraint_id").agg(
        (pl.col("kind") == "state_total").sum().alias("states"),
        (pl.col("kind") == "national_total").any().alias("national"),
    )
    assert (
        per_row.filter(
            (pl.col("states") > 1) | ((pl.col("states") > 0) & pl.col("national"))
        ).height
        == 0
    )


def test_the_hash_is_stable_across_builds_and_moves_when_a_value_moves(
    make_monthly, make_size
) -> None:
    data = _data(make_monthly, make_size)
    first = system.build_constraint_system(data, _cfg())
    second = system.build_constraint_system(data, _cfg())
    assert first.constraint_set_hash == second.constraint_set_hash

    moved = HarmonizedData(
        qcew_monthly=data.qcew_monthly.with_columns(
            pl.when(pl.col("state_fips") == "01")
            .then(701)
            .otherwise(pl.col("employment_value"))
            .alias("employment_value")
        ),
        qcew_national_size=data.qcew_national_size,
        cbp_state_size=data.cbp_state_size,
        bridge=data.bridge,
    )
    assert (
        system.build_constraint_system(moved, _cfg()).constraint_set_hash
        != first.constraint_set_hash
    )


def test_the_hash_ignores_component_id_because_components_are_derived(
    make_monthly, make_size
) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    relabelled = built.rows.with_columns(pl.lit("c000042").alias("component_id"))
    assert (
        system.constraint_set_hash(built.cells, relabelled, built.coefficients)
        == built.constraint_set_hash
    )


def test_the_compatibility_gate_runs_before_any_row_is_built(make_monthly, make_size) -> None:
    data = _data(make_monthly, make_size)
    misaligned = HarmonizedData(
        qcew_monthly=pl.concat(
            [data.qcew_monthly, make_monthly({"industry_code": "111110", "area_type": "state"})]
        ),
        qcew_national_size=data.qcew_national_size,
        cbp_state_size=data.cbp_state_size,
        bridge=data.bridge,
    )
    with pytest.raises(ConceptViolationError):
        system.build_constraint_system(misaligned, _cfg())


def test_the_run_id_is_a_function_of_the_config_and_the_inputs_only() -> None:
    cfg = _cfg()
    digests = {"qcew_monthly": "aaa", "qcew_national_size": "bbb"}
    assert runs.run_id(cfg, digests) == runs.run_id(cfg, digests)
    assert runs.run_id(cfg, digests) != runs.run_id(cfg, {**digests, "qcew_monthly": "ccc"})
    assert len(runs.run_id(cfg, digests)) == 12


def test_the_run_directory_sits_under_the_configured_output_root() -> None:
    cfg = _cfg()
    assert runs.run_dir(cfg, "abc123abc123") == Path(cfg.storage.output_uri) / "abc123abc123"


def test_load_system_names_the_missing_table_rather_than_raising_from_polars(tmp_path) -> None:
    # Review finding: neither `load_system` branch had a test. The CLI test that appeared to cover
    # the hash mismatch never reaches it -- mutating a staged value moves the run id, so the
    # manifest is missing and the command fails earlier, at argument validation.
    with pytest.raises(FileNotFoundError, match="target_cell.parquet"):
        system.load_system(tmp_path)


def test_load_system_refuses_tables_that_do_not_match_the_recorded_hash(
    tmp_path, make_monthly, make_size
) -> None:
    built = system.build_constraint_system(_data(make_monthly, make_size), _cfg())
    for name, frame in (
        ("target_cell", built.cells),
        ("constraint_row", built.rows),
        ("constraint_coefficient", built.coefficients),
    ):
        frame.write_parquet(tmp_path / f"{name}.parquet")

    reloaded = system.load_system(tmp_path, expected_hash=built.constraint_set_hash)
    assert reloaded.constraint_set_hash == built.constraint_set_hash
    assert reloaded.cells.equals(built.cells)

    with pytest.raises(IncompatibleMarginError, match="constraint_set_hash mismatch"):
        system.load_system(tmp_path, expected_hash="0" * 64)
