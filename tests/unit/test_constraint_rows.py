"""The row factory: what it accepts, and the three things it must refuse."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.constraints import cells, rows
from logging_employment.contracts import CONSTRAINT_ROW_SCHEMA
from logging_employment.errors import HardConstraintClassError, IncompatibleMarginError


def _kwargs(**overrides):
    base = {
        "constraint_id": "fix|x",
        "constraint_class": "public_accounting_fact",
        "relation": "eq",
        "coefficients": (("cell-a", 1.0),),
        "rhs_lower": 5.0,
        "rhs_upper": 5.0,
        "is_hard": True,
        "evidence_kind": "published_value",
        "period_scope": "2024-03",
        "geography_scope": "01",
        "industry_scope": "113310",
        "ownership_scope": "5",
        "source_snapshot_ids": "2024q1",
        "provenance_text": "published QCEW value",
        "vintage_compatibility_status": "compatible",
    }
    return base | overrides


def test_a_well_formed_hard_row_is_accepted_and_carries_its_evidence_kind() -> None:
    draft = rows.constraint(**_kwargs())
    assert draft.is_hard is True
    assert draft.provenance_text.startswith("evidence_kind=published_value; ")


# --- Guard 1: §7.8, only the first two classes may be hard -------------------------------------


def test_a_hard_row_outside_the_two_eligible_classes_is_refused() -> None:
    for ineligible in ("empirical_measurement", "modeling_assumption", "sensitivity_assumption"):
        with pytest.raises(HardConstraintClassError, match=ineligible):
            rows.constraint(**_kwargs(constraint_class=ineligible))


def test_the_same_class_is_accepted_when_it_is_not_hard() -> None:
    draft = rows.constraint(**_kwargs(constraint_class="empirical_measurement", is_hard=False))
    assert draft.is_hard is False


# --- Guard 2: SRC-QCEW-006's `decline` -- no national employment margin -------------------------


def test_a_row_linking_the_national_row_to_state_cells_is_refused() -> None:
    # Stage 0's verdict is `decline`: "Stage 2 therefore MUST NOT create a national employment
    # margin constraint out of this identity." This guard is what makes that structural.
    kinds = {
        "nat": cells.KIND_NATIONAL_TOTAL,
        "st1": cells.KIND_STATE_TOTAL,
        "st2": cells.KIND_STATE_TOTAL,
    }
    draft = rows.constraint(
        **_kwargs(
            constraint_id="national_identity|2024-03",
            coefficients=(("st1", 1.0), ("st2", 1.0), ("nat", -1.0)),
            rhs_lower=0.0,
            rhs_upper=0.0,
        )
    )
    with pytest.raises(IncompatibleMarginError, match="SRC-QCEW-006"):
        rows.assert_no_national_employment_margin([draft], kinds)


def test_a_row_summing_two_state_cells_is_refused_even_without_the_national_cell() -> None:
    kinds = {"st1": cells.KIND_STATE_TOTAL, "st2": cells.KIND_STATE_TOTAL}
    draft = rows.constraint(
        **_kwargs(coefficients=(("st1", 1.0), ("st2", 1.0)), rhs_lower=9.0, rhs_upper=9.0)
    )
    with pytest.raises(IncompatibleMarginError, match="SRC-QCEW-006"):
        rows.assert_no_national_employment_margin([draft], kinds)


def test_the_size_margin_passes_the_same_guard() -> None:
    kinds = {
        "k1": cells.KIND_NATIONAL_SIZE,
        "k2": cells.KIND_NATIONAL_SIZE,
        "nat": cells.KIND_NATIONAL_TOTAL,
    }
    draft = rows.constraint(
        **_kwargs(
            coefficients=(("k1", 1.0), ("k2", 1.0), ("nat", -1.0)), rhs_lower=0.0, rhs_upper=0.0
        )
    )
    rows.assert_no_national_employment_margin([draft], kinds)  # does not raise


# --- Guard 3: §9.3, no hard constraint from an assumed disclosure threshold ---------------------


def test_a_constraint_warranted_by_an_assumed_threshold_can_never_be_hard() -> None:
    # The Gemini review's §7 item 5 derives a hard bound from an asserted "80/3" disclosure
    # threshold. §9.3 forbids it, and the refusal is by evidence kind rather than by review.
    with pytest.raises(HardConstraintClassError, match="assumed_threshold"):
        rows.constraint(
            **_kwargs(
                evidence_kind="assumed_threshold", relation="le", rhs_lower=None, rhs_upper=26.0
            )
        )


def test_the_same_warrant_is_allowed_as_a_labelled_sensitivity_assumption() -> None:
    draft = rows.constraint(
        **_kwargs(
            constraint_class="sensitivity_assumption",
            evidence_kind="assumed_threshold",
            relation="le",
            rhs_lower=None,
            rhs_upper=26.0,
            is_hard=False,
        )
    )
    assert draft.is_hard is False
    assert "assumed_threshold" in draft.provenance_text


# --- Guard 4: INV-007, a hard row may not span incompatible vintages ----------------------------


def test_a_hard_row_spanning_two_naics_vintages_is_refused() -> None:
    assert rows.vintage_status(["NAICS 2017", "NAICS 2017"]) == "compatible"
    assert rows.vintage_status(["NAICS 2017", "NAICS 2022"]) == "incompatible"
    with pytest.raises(IncompatibleMarginError, match="vintage"):
        rows.constraint(**_kwargs(vintage_compatibility_status="incompatible"))


# --- Shape checks -------------------------------------------------------------------------------


def test_relation_and_rhs_must_agree() -> None:
    with pytest.raises(ValueError, match="eq"):
        rows.constraint(**_kwargs(relation="eq", rhs_lower=1.0, rhs_upper=2.0))
    with pytest.raises(ValueError, match="ge"):
        rows.constraint(**_kwargs(relation="ge", rhs_lower=None, rhs_upper=None))
    with pytest.raises(ValueError, match="integrality"):
        rows.constraint(**_kwargs(relation="integrality", rhs_lower=1.0, rhs_upper=1.0))


def test_to_frames_matches_both_schemas_and_is_sorted() -> None:
    drafts = [
        rows.constraint(**_kwargs(constraint_id="b")),
        rows.constraint(**_kwargs(constraint_id="a", coefficients=(("cell-b", 1.0),))),
    ]
    row_frame, coefficient_frame = rows.to_frames(drafts)
    assert row_frame.schema == pl.Schema(CONSTRAINT_ROW_SCHEMA)
    assert row_frame["constraint_id"].to_list() == ["a", "b"]
    assert coefficient_frame["constraint_id"].to_list() == ["a", "b"]
    assert row_frame["component_id"].null_count() == row_frame.height
