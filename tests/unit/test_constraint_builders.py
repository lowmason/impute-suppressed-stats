"""What each builder emits, and the two things it must not."""

from __future__ import annotations

import dataclasses

import polars as pl
import pytest

from logging_employment.constraints import cells, rows
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError, IncompatibleMarginError


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


def test_the_builder_march_gate_is_also_closed_against_a_null_month(
    make_monthly, make_size
) -> None:
    # The same null-open shape as `compat`'s gate, in the builder that Stage 6 inherits.
    cell_frame, size = _built(make_monthly, make_size, _TWO_CLASSES)
    nulled = size.with_columns(pl.lit(None, dtype=pl.String).alias("reference_month"))
    with pytest.raises(ConceptViolationError, match="March"):
        rows.size_support_rows(cell_frame, nulled)


PARENT_ID = "state_parent|41|2024-03|5|113|NAICS 2022|ALL"
CHILD_ID = "state_total|41|2024-03|5|113310|NAICS 2022|ALL"


def _parent_layer(make_monthly, make_size, *, child_status, parent_status, parent_value):
    """One state-month: a `113310` child and its private `113` parent, in the statuses named."""
    child = {
        "state_fips": "41",
        "area_fips": "41000",
        "observation_status": child_status,
        "employment_value": None if child_status == "suppressed" else 90,
        "disclosure_code": "N" if child_status == "suppressed" else "",
    }
    parent = {
        "state_fips": "41",
        "area_fips": "41000",
        "industry_code": "113",
        "aggregation_level": "55",
        "qtrly_establishments": 12,
        "observation_status": parent_status,
        "employment_value": parent_value,
        "disclosure_code": "N" if parent_status == "suppressed" else "",
    }
    data = HarmonizedData(
        qcew_monthly=make_monthly(child),
        qcew_national_size=make_size(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
        qcew_state_parent=make_monthly(parent),
    )
    return cells.build_target_cells(
        data, industry_code="113310", ownership_code="5", size_concept="march_reference"
    )


def test_a_published_parent_over_a_suppressed_child_becomes_one_cell_and_one_row(
    make_monthly, make_size
) -> None:
    """R-PM-2: `child - parent <= 0`, the parent pinned by its own fixing row, never an rhs literal."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status="suppressed",
        parent_status="observed",
        parent_value=150,
    )
    parents = frame.filter(pl.col("cell_id").str.starts_with("state_parent|"))
    assert parents["cell_id"].to_list() == [PARENT_ID]
    (draft,) = rows.parent_margin_rows(frame)
    assert draft.constraint_id == f"parent_margin|{CHILD_ID}"
    assert (draft.relation, draft.rhs_lower, draft.rhs_upper) == ("le", None, 0.0)
    assert draft.coefficients == ((CHILD_ID, 1.0), (PARENT_ID, -1.0))
    assert draft.is_hard and draft.constraint_class == "public_accounting_fact"
    assert draft.provenance_text.startswith("evidence_kind=published_value; ")
    fixing = {d.constraint_id: d for d in rows.observed_value_rows(frame)}
    assert fixing[f"fix|{PARENT_ID}"].rhs_upper == 150.0


@pytest.mark.parametrize(
    ("child_status", "parent_status", "parent_value"),
    [("observed", "observed", 150), ("suppressed", "suppressed", None)],
)
def test_no_parent_cell_without_both_a_published_parent_and_a_suppressed_child(
    make_monthly, make_size, child_status, parent_status, parent_value
) -> None:
    """A parent over a published child restricts nothing; a suppressed parent publishes nothing."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status=child_status,
        parent_status=parent_status,
        parent_value=parent_value,
    )
    assert frame.filter(pl.col("cell_id").str.starts_with("state_parent|")).is_empty()
    assert rows.parent_margin_rows(frame) == []


def test_the_parent_row_couples_one_state_cell_so_the_national_guard_still_admits_it(
    make_monthly, make_size
) -> None:
    """R-PM-2: SRC-QCEW-006's guard is untouched -- a state cell and its parent are not a state sum."""
    frame = _parent_layer(
        make_monthly,
        make_size,
        child_status="suppressed",
        parent_status="observed",
        parent_value=150,
    )
    drafts = rows.parent_margin_rows(frame)
    kinds = {cid: cid.split("|")[0] for cid in frame["cell_id"].to_list()}
    rows.assert_no_national_employment_margin(drafts, kinds)
    other = "state_total|06|2024-03|5|113310|NAICS 2022|ALL"
    widened = dataclasses.replace(drafts[0], coefficients=(*drafts[0].coefficients, (other, 1.0)))
    with pytest.raises(IncompatibleMarginError):
        rows.assert_no_national_employment_margin([widened], {**kinds, other: "state_total"})
