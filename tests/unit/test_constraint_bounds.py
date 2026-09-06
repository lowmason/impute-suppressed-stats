"""§9.6: what HiGHS returns for each component shape this stage produces."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.constraints import bounds, cells, graph, rows, system
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import InfeasibleComponentError

REPO = Path(__file__).resolve().parents[2]


def _built(monthly, size):
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cfg = load_config(REPO / "config.yaml")
    return graph.assign_components(system.build_constraint_system(data, cfg)), cfg


def _national(month, employment, establishments):
    return {
        "area_fips": "US000",
        "area_type": "national",
        "state_fips": None,
        "aggregation_level": "18",
        "reference_month": month,
        "employment_value": employment,
        "employment_raw": str(employment),
        "qtrly_establishments": establishments,
    }


_REAL_2024 = (
    {
        "size_class": "1",
        "establishments": 5007,
        "employment": 7630,
        "size_lower": 0,
        "size_upper": 4,
    },
    {
        "size_class": "2",
        "establishments": 1501,
        "employment": 9955,
        "size_lower": 5,
        "size_upper": 9,
    },
    {
        "size_class": "3",
        "establishments": 803,
        "employment": 10480,
        "size_lower": 10,
        "size_upper": 19,
    },
    {
        "size_class": "4",
        "establishments": 357,
        "employment": 10316,
        "size_lower": 20,
        "size_upper": 49,
    },
    {
        "size_class": "5",
        "establishments": 40,
        "employment": 2507,
        "size_lower": 50,
        "size_upper": 99,
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
    {
        "size_class": "7",
        "establishments": 1,
        "employment": None,
        "size_lower": 250,
        "size_upper": 499,
        "disclosure_code": "N",
        "observation_status": "suppressed",
    },
)


def test_the_real_2024_size_component_reproduces_its_published_sharp_bounds(
    make_monthly, make_size
) -> None:
    # Residual 41668 - 40888 = 780, with supports [400, 996] and [250, 499]. Computed analytically
    # while this plan was written and reproduced by HiGHS.
    built, cfg = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024))
    membership = graph.component_membership(built)
    coupled = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]
    solved = bounds.solve_component(built, coupled, membership, cfg.constraints, integer=False)
    by_class = {cell.rsplit("|", 1)[1]: value for cell, value in solved.items()}
    assert by_class["6"][:2] == (400.0, 530.0)
    assert by_class["7"][:2] == (250.0, 380.0)
    assert by_class["6"][2] == "optimal"


def test_a_suppressed_state_cell_is_bounded_below_and_unbounded_above(
    make_monthly, make_size
) -> None:
    # The whole consequence of SRC-QCEW-006's `decline`, in one assertion.
    built, cfg = _built(
        make_monthly(
            {
                "state_fips": "01",
                "observation_status": "suppressed",
                "employment_value": None,
                "disclosure_code": "N",
            },
            _national("2024-03", 200, 60),
        ),
        make_size(
            {
                "size_class": "1",
                "establishments": 60,
                "employment": 200,
                "size_lower": 0,
                "size_upper": 4,
            }
        ),
    )
    membership = graph.component_membership(built)
    lonely = membership.filter(pl.col("cell_id").str.starts_with("state_total|"))["component_id"][0]
    solved = bounds.solve_component(built, lonely, membership, cfg.constraints, integer=False)
    ((lower, upper, status),) = solved.values()
    assert lower == 0.0
    assert upper is None
    assert status == "unbounded"


def test_an_infeasible_component_raises_rather_than_relaxing(make_monthly, make_size) -> None:
    # §9.6 step 4: stop and emit diagnostics on infeasibility; do not silently relax. The residual
    # here is 600 against supports that need at least 650.
    perturbed = tuple(
        row | {"employment": row["employment"] + 180} if row["size_class"] == "1" else row
        for row in _REAL_2024
    )
    built, cfg = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*perturbed))
    membership = graph.component_membership(built)
    coupled = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]
    with pytest.raises(InfeasibleComponentError, match=coupled):
        bounds.solve_component(built, coupled, membership, cfg.constraints, integer=False)


def test_a_soft_row_is_recorded_but_never_narrows_a_bound(make_monthly, make_size) -> None:
    # INV-005: only public accounting facts and valid definitional restrictions enter the
    # deterministic feasible set. Nothing in D1 builds a soft row, so this is the test that keeps
    # the filter honest until Stage 3 adds CBP as an empirical measurement.
    built, cfg = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024))
    membership = graph.component_membership(built)
    coupled = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]
    class_six = next(
        c
        for c in membership.filter(pl.col("component_id") == coupled)["cell_id"]
        if c.endswith("|6")
    )
    soft = rows.constraint(
        constraint_id=f"soft|{class_six}",
        constraint_class="empirical_measurement",
        relation="le",
        coefficients=((class_six, 1.0),),
        rhs_lower=None,
        rhs_upper=450.0,  # would cut the upper bound from 530 to 450 if it entered the model
        is_hard=False,
        evidence_kind="empirical_fit",
        period_scope="2024-03",
        geography_scope="US",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="toy",
        provenance_text="a soft measurement that must not narrow a deterministic bound",
        vintage_compatibility_status="compatible",
    )
    soft_rows, soft_coefficients = rows.to_frames([soft])
    widened = replace(
        built,
        rows=pl.concat([built.rows, soft_rows.with_columns(pl.lit(coupled).alias("component_id"))]),
        coefficients=pl.concat([built.coefficients, soft_coefficients]),
    )
    solved = bounds.solve_component(widened, coupled, membership, cfg.constraints, integer=False)
    assert {c.rsplit("|", 1)[1]: v[:2] for c, v in solved.items()}["6"] == (400.0, 530.0)


def test_column_specs_fold_single_cell_rows_into_bounds_and_leave_the_margin_in_the_matrix(
    make_monthly, make_size
) -> None:
    built, _ = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024))
    membership = graph.component_membership(built)
    coupled = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]
    specs = bounds.column_specs(built, coupled, membership)
    class_six = next(spec for cell, spec in specs.items() if cell.endswith("|6"))
    assert (class_six.lower, class_six.upper) == (400.0, 996.0)
    assert class_six.is_integer is True
    assert len(bounds.matrix_rows(built, coupled)) == 1  # the size margin only


def test_matrix_rows_orders_the_size_margin_by_cell_id_with_the_total_last(
    make_monthly, make_size
) -> None:
    """The coefficient order inside a coupling row, pinned against how it is produced.

    Two mechanisms set it, and neither is read from this call. `size_margin_rows` emits the
    published classes sorted by `size_class` at +1.0 and appends the all-sizes total at -1.0
    (`rows.py`); `to_frames` then re-sorts every coefficient by `(constraint_id, cell_id)`
    (`rows.py`), under which `national_size|...` precedes `national_total|...` because "size"
    sorts before "total". `matrix_rows` reads that frame in frame order, and the list it returns
    becomes `model.addRow`'s index array -- so this order is the model's, not a presentational
    detail.

    Pinned because nothing else in this suite can see it. Reversing the order fed to `addRow`
    leaves every other test in the repo green and the bounds bit-identical, because every hard
    coefficient this stage emits is +/-1. That is a property of this window, not a guarantee, and
    it is exactly what stops holding when a later stage introduces fractional coefficients.
    """
    built, _ = _built(make_monthly(_national("2024-03", 41668, 7713)), make_size(*_REAL_2024))
    membership = graph.component_membership(built)
    coupled = membership.filter(pl.col("cell_id").str.starts_with("national_size|"))[
        "component_id"
    ][0]

    (margin,) = bounds.matrix_rows(built, coupled)
    assert [str(cell).split("|", 1)[0] for cell in margin["cells"]] == [
        cells.KIND_NATIONAL_SIZE
    ] * 7 + [cells.KIND_NATIONAL_TOTAL]
    assert [str(cell).rsplit("|", 1)[1] for cell in margin["cells"]] == [
        *(str(n) for n in range(1, 8)),
        cells.TOTAL_SIZE_CLASS,
    ]
    assert margin["values"] == [*(1.0 for _ in range(7)), -1.0]

    # `column_specs` keys are the HiGHS column indices (`_model` builds `at` from `list(specs)`),
    # so their order is load-bearing in the same way and is fixed by the same cell_id sort.
    assert list(bounds.column_specs(built, coupled, membership)) == list(margin["cells"])
