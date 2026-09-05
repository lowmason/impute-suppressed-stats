"""What each builder emits, and the two things it must not."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.constraints import cells, rows
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError


def _built(make_monthly, make_size, size_spec):
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
            "qtrly_establishments": sum(int(row["establishments"]) for row in size_spec),
        },
    )
    size = make_size(*size_spec)
    data = HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=size,
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    cell_frame = cells.build_target_cells(
        data, industry_code="113310", ownership_code="5", size_concept="march_reference"
    )
    return cell_frame, size


_TWO_CLASSES = (
    {"size_class": "1", "establishments": 50, "employment": 100, "size_lower": 0, "size_upper": 4},
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


def test_observed_and_true_zero_cells_are_pinned_to_their_published_values(
    make_monthly, make_size
) -> None:
    # INV-001: a disclosed QCEW target cell is preserved exactly.
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.observed_value_rows(cell_frame)
    pinned = {d.coefficients[0][0]: d.rhs_lower for d in drafts}
    assert all(d.relation == "eq" and d.is_hard for d in drafts)
    assert 700.0 in pinned.values() and 1000.0 in pinned.values() and 100.0 in pinned.values()
    assert not any("state_total|02" in cid for cid in pinned)


def test_only_suppressed_cells_receive_nonnegativity_and_integrality(
    make_monthly, make_size
) -> None:
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    nonneg = rows.nonnegativity_rows(cell_frame)
    integral = rows.integrality_rows(cell_frame)
    assert len(nonneg) == len(integral) == 2  # the suppressed state cell and the suppressed class
    assert {d.relation for d in nonneg} == {"ge"}
    assert {d.rhs_lower for d in nonneg} == {0.0}
    assert {d.relation for d in integral} == {"integrality"}
    assert all(d.constraint_class == "definitional_support" and d.is_hard for d in nonneg)


def test_the_size_margin_links_every_class_to_the_national_row_of_the_same_month(
    make_monthly, make_size
) -> None:
    cell_frame, _ = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.size_margin_rows(cell_frame)
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.relation == "eq" and draft.rhs_lower == 0.0 and draft.rhs_upper == 0.0
    weights = dict(draft.coefficients)
    assert sorted(weights.values()) == [-1.0, 1.0, 1.0]
    assert draft.constraint_class == "public_accounting_fact" and draft.is_hard


def test_a_suppressed_class_gets_a_support_row_from_its_published_establishment_count(
    make_monthly, make_size
) -> None:
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    drafts = rows.size_support_rows(cell_frame, size)
    assert len(drafts) == 1
    support = drafts[0]
    assert support.relation == "range"
    assert (support.rhs_lower, support.rhs_upper) == (400.0, 996.0)  # 4 estabs in [100, 249]
    assert support.constraint_class == "definitional_support" and support.is_hard


def test_an_open_ended_top_class_emits_a_lower_bound_only(make_monthly, make_size) -> None:
    # §9.3 forbids arbitrary top-class caps; inventing a number to close class 9's band is
    # exactly that.
    spec = (
        {
            "size_class": "1",
            "establishments": 50,
            "employment": 100,
            "size_lower": 0,
            "size_upper": 4,
        },
        {
            "size_class": "9",
            "establishments": 2,
            "employment": None,
            "size_lower": 1000,
            "size_upper": None,
            "disclosure_code": "N",
            "observation_status": "suppressed",
        },
    )
    cell_frame, size = _built(make_monthly, make_size, spec)
    support = rows.size_support_rows(cell_frame, size)[0]
    assert support.relation == "ge"
    assert support.rhs_lower == 2000.0
    assert support.rhs_upper is None


def test_a_non_march_size_row_cannot_produce_a_support_row(make_monthly, make_size) -> None:
    # INV-011, enforced where the constraint is created rather than trusted from the data. Stage 6
    # inherits this builder.
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    june = size.with_columns(pl.lit("2024-06").alias("reference_month"))
    with pytest.raises(ConceptViolationError, match="March"):
        rows.size_support_rows(cell_frame, june)


def test_a_rounding_interval_becomes_a_range_and_records_its_endpoint_rule() -> None:
    # §9.4. No QCEW field this stage reads is rounded, so this helper is exercised by the property
    # tests rather than by the D1 run; it exists because §9.4 requires the encoding to be
    # field-specific and available.
    draft = rows.rounding_interval_row(
        "round|x",
        "cell-a",
        published_value=1200.0,
        grid_width=100.0,
        endpoint_rule="lower closed, upper open per source documentation",
        period_scope="2024-03",
        geography_scope="01",
        industry_scope="113310",
        ownership_scope="5",
        source_snapshot_ids="s1",
    )
    assert (draft.relation, draft.rhs_lower, draft.rhs_upper) == ("range", 1150.0, 1250.0)
    assert draft.constraint_class == "definitional_support"
    assert "upper open" in draft.provenance_text


def test_an_unfiltered_size_frame_is_refused_rather_than_silently_matched(
    make_monthly, make_size
) -> None:
    # Not in the plan's code block, added after measuring the failure mode on the real table.
    # `size_support_rows` matches a size row to a cell on (reference_month, size_class) and never
    # on industry, so a frame carrying a second industry matches that same cell again: the real
    # 140,343-row table yields 3,857 support rows carrying 14 distinct constraint_ids, each
    # bounding a Logging cell by some other industry's establishment count. Nothing raises. The
    # Global Constraints say every read of that table filters to the project industry first, and
    # this is the guard that makes forgetting it fail loudly instead of quietly.
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    two_industries = pl.concat([size, size.with_columns(pl.lit("111110").alias("industry_code"))])
    with pytest.raises(ConceptViolationError, match="industry"):
        rows.size_support_rows(cell_frame, two_industries)
