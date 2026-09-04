"""Judgment-logic tests for the SRC-QCEW-006 branch rule.

`classify_identity` is a pure function of two comparison tables, and these tests fix its
behaviour on toy panels *before* it is ever pointed at `qcew_panel`. That ordering is the point:
scanning first and reasoning second produces a rationalisation for whichever verdict the data
suggests.

Three groups, and they were written at different points, which the section comments record:

1. The brief's nine, pinning the three-branch contract.
2. The two silent failure modes the brief's illustrative code leaves open, both of which would
   corrupt the highest-stakes output in the *safe*-looking direction: `Series.all()` defaults to
   `ignore_nulls=True`, so a null comparison cell is skipped and reads as a pass; and a
   reference-side value that was never published must not be summed to `0`, which is
   indistinguishable from a published zero and manufactures (or hides) a gap.
3. Containment -- written after the scan, and labelled as such where it starts.

Groups 1 and 2 predate the scan, and `classify_identity` has not changed since they went green.

`qcew_identity` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is
inert: the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import polars as pl
import pytest

from qcew_identity import (
    INDETERMINATE,
    INSIDE,
    NO_OTHER_AREA,
    OUTSIDE,
    _clean_month_clause,
    classify_identity,
    comparison_tables,
    measure_containment,
)


def quarters(rows):
    return pl.DataFrame(
        rows,
        schema={"year": pl.Int32, "qtr": pl.Int8, "national_estabs": pl.Int64,
                "states_dc_estabs": pl.Int64, "other_estabs": pl.Int64,
                "estab_gap": pl.Int64, "estab_gap_after_other": pl.Int64},
        orient="row",
    )


def months(rows):
    return pl.DataFrame(
        rows,
        schema={"year": pl.Int32, "month": pl.Int8, "national_emp": pl.Int64,
                "states_dc_emp": pl.Int64, "other_emp": pl.Int64, "emp_gap": pl.Int64,
                "emp_gap_after_other": pl.Int64, "n_states_suppressed": pl.Int64},
        orient="row",
    )


def test_clean_identity_with_no_other_areas_enforces():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)])
    assert classify_identity(q, m)["branch"] == "enforce"


def test_identity_closing_only_after_territories_requires_residual_cells():
    q = quarters([(2017, 1, 110, 100, 10, 10, 0)])
    m = months([(2017, 1, 550, 500, 50, 50, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "residual_cells"
    assert out["evidence"]["other_areas_present"] is True


def test_unexplained_establishment_gap_declines():
    q = quarters([(2017, 1, 120, 100, 10, 20, 10)])
    m = months([(2017, 1, 550, 500, 50, 50, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "establishment" in out["reason"]


def test_negative_employment_residual_declines():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 520, 0, -20, -20, 1)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "negative" in out["reason"]


def test_no_unsuppressed_month_declines_as_untestable():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 400, 0, 100, 100, 3)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "untestable" in out["reason"]


def test_gap_in_an_unsuppressed_month_declines():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, 505, 500, 0, 5, 5, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "unsuppressed month" in out["reason"]


def test_suppressed_months_may_carry_a_positive_residual_under_enforce():
    """A positive gap in a suppressed month is the residual Stage 3 allocates, not a defect."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, 510, 460, 0, 50, 50, 2)])
    assert classify_identity(q, m)["branch"] == "enforce"


@pytest.mark.parametrize("branch_input,expected", [(0, "enforce"), (7, "residual_cells")])
def test_branch_is_always_exactly_one_of_three(branch_input, expected):
    q = quarters([(2017, 1, 100 + branch_input, 100, branch_input, branch_input, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == expected
    assert out["branch"] in ("enforce", "residual_cells", "decline")


# --- the two silent failure modes ------------------------------------------------------------


def test_unevaluable_quarter_declines_rather_than_passing_the_all_check():
    """`(col == 0).all()` skips nulls and returns True; an unevaluable quarter must not enforce."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, None, 100, 0, None, None)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "establishment" in out["reason"]
    assert out["evidence"]["quarters_unevaluable"] == 1
    assert out["evidence"]["estab_identity_closes_after_other_areas"] is False


def test_month_missing_a_reference_value_is_untestable_not_clean():
    """A month whose national or non-state term was never published is excluded, not counted."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, None, 500, 0, None, None, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "enforce"
    assert out["evidence"]["untestable_months"] == 1
    assert out["evidence"]["testable_months"] == 1
    assert out["evidence"]["clean_months"] == 1


def test_every_month_missing_a_reference_value_declines_as_untestable():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, None, 500, 0, None, None, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "untestable" in out["reason"]
    assert out["evidence"]["testable_months"] == 0


def test_unevaluable_extrema_are_null_not_zero():
    """A `0` extremum reads as a closed identity; an unmeasured one must serialise as null."""
    q = quarters([(2017, 1, None, 100, 0, None, None)])
    m = months([(2017, 1, None, 500, 0, None, None, 0)])
    out = classify_identity(q, m)
    assert out["evidence"]["max_estab_gap_after_other"] is None
    assert out["evidence"]["min_emp_gap_after_other"] is None


def test_negative_check_ignores_an_untestable_month():
    """The non-negativity check runs over testable months only, so a null cannot fake a pass."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, None, 500, 0, None, None, 0)])
    out = classify_identity(q, m)
    assert out["evidence"]["employment_residual_never_negative"] is True
    assert out["branch"] == "enforce"


def test_missing_column_raises_rather_than_returning_a_branch():
    """A construction bug must surface as a traceback, never as a data verdict."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)]).drop("emp_gap_after_other")
    with pytest.raises(ValueError, match="emp_gap_after_other"):
        classify_identity(q, m)


def test_every_reason_is_free_of_sentence_breaks():
    """`reason` is interpolated into `verdict_sentence`, which the exit criterion reads as one
    sentence, so no reason may contain a sentence break.

    One case per branch, in `classify_identity`'s own order. `assert_one_sentence` *raises*, so a
    reason that grew a sentence break would crash the script inside a decline path with nothing
    to catch it -- which is why the unevaluable-quarter and no-testable-month branches are
    covered here too, and why the distinct-reason count below fails if a branch is added without
    a case.
    """
    clean_q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    cases = [
        # unevaluable quarters: a reference establishment count was never published
        (quarters([(2017, 1, None, 100, 0, None, None)]),
         months([(2017, 1, 500, 500, 0, 0, 0, 0)])),
        (quarters([(2017, 1, 120, 100, 10, 20, 10)]), months([(2017, 1, 550, 500, 50, 50, 0, 0)])),
        (clean_q, months([(2017, 1, 500, 520, 0, -20, -20, 1)])),
        # no testable month: every month is missing a reference employment value
        (clean_q, months([(2017, 1, None, 500, 0, None, None, 0)])),
        (clean_q, months([(2017, 1, 500, 400, 0, 100, 100, 3)])),
        (clean_q, months([(2017, 1, 505, 500, 0, 5, 5, 0)])),
        (quarters([(2017, 1, 110, 100, 10, 10, 0)]), months([(2017, 1, 550, 500, 50, 50, 0, 0)])),
        (clean_q, months([(2017, 1, 500, 500, 0, 0, 0, 0)])),
    ]
    reasons = []
    for q, m in cases:
        reason = classify_identity(q, m)["reason"]
        assert ". " not in reason
        assert not reason.endswith(".")
        reasons.append(reason)
    assert len(set(reasons)) == 8, "one case per branch; extend this test when a branch is added"


# --- containment: is a non-state area a component of the national total? ----------------------
#
# These tests were written *after* the scan, unlike everything above, because the scan is what
# showed the question needed asking: the brief's `estab_gap - other_estabs` presupposes that a
# non-state area is inside the national total, and a panel where it is not makes that
# subtraction manufacture a gap out of an identity that closes. `classify_identity` is
# unchanged; the fix is upstream of it, so the tests above still pin the rule as committed.


def raw_quarters(rows):
    return pl.DataFrame(
        rows,
        schema={"year": pl.Int32, "qtr": pl.Int8, "national_estabs": pl.Int64,
                "states_dc_estabs": pl.Int64, "other_published": pl.Int64,
                "estab_gap": pl.Int64},
        orient="row",
    )


def test_non_state_area_inside_the_national_total_is_subtracted():
    raw = raw_quarters([(2017, 1, 110, 100, 10, 10), (2017, 2, 105, 100, 5, 5)])
    out = measure_containment(raw)
    assert out["verdict"] == INSIDE
    assert out["subtraction_applied"] is True
    assert out["quarters_discriminating"] == 2


def test_non_state_area_outside_the_national_total_is_not_subtracted():
    """The national total already equals the state sum, so the area is additional to it."""
    raw = raw_quarters([(2017, 1, 100, 100, 1, 0), (2017, 2, 100, 100, 2, 0)])
    out = measure_containment(raw)
    assert out["verdict"] == OUTSIDE
    assert out["subtraction_applied"] is False
    assert out["quarters_gap_is_zero"] == 2


def test_mixed_containment_is_indeterminate_and_still_subtracts():
    """Unsettled containment must not be resolved by fiat; subtracting leaves a non-zero gap
    for the rule's first gate to decline on."""
    raw = raw_quarters([(2017, 1, 110, 100, 10, 10), (2017, 2, 100, 100, 5, 0)])
    out = measure_containment(raw)
    assert out["verdict"] == INDETERMINATE
    assert out["subtraction_applied"] is True


def test_a_zero_contribution_quarter_cannot_discriminate():
    """`estab_gap == other == 0` satisfies both readings, so it must not be counted as evidence."""
    raw = raw_quarters([(2017, 1, 100, 100, 0, 0), (2017, 2, 100, 100, 0, 0)])
    out = measure_containment(raw)
    assert out["verdict"] == NO_OTHER_AREA
    assert out["quarters_discriminating"] == 0
    assert out["subtraction_applied"] is False


def test_an_unpublished_non_state_count_is_counted_not_treated_as_discriminating():
    raw = raw_quarters([(2017, 1, 100, 100, None, 0), (2017, 2, 110, 100, 10, 10)])
    out = measure_containment(raw)
    assert out["quarters_non_state_amount_unpublished"] == 1
    assert out["quarters_discriminating"] == 1
    assert out["verdict"] == INSIDE


def panel(rows):
    return pl.DataFrame(
        rows,
        schema={"area_fips": pl.String, "area_title": pl.String, "area_class": pl.String,
                "year": pl.Int32, "qtr": pl.Int8, "month": pl.Int8, "emplvl": pl.Int64,
                "qtrly_estabs": pl.Int64, "disclosure_code": pl.String,
                "suppressed": pl.Boolean},
        orient="row",
    )


def outside_containment_panel():
    """One state and one non-state area whose establishments are absent from the national total,
    with the non-state area's employment withheld -- the shape the real panel turns out to have.
    """
    rows = []
    for month in (1, 2, 3):
        rows += [
            ("US000", "US TOTAL", "national", 2017, 1, month, 500, 100, "", False),
            ("01000", "Alabama", "states_dc", 2017, 1, month, 500, 100, "", False),
            ("72000", "Puerto Rico -- Statewide", "other_state_level", 2017, 1, month,
             None, 1, "N", True),
        ]
    return panel(rows)


def test_an_area_outside_the_national_total_does_not_manufacture_a_gap():
    quarters, _, containment = comparison_tables(outside_containment_panel())
    assert containment["verdict"] == OUTSIDE
    assert quarters["other_estabs"].to_list() == [0]
    assert quarters["estab_gap"].to_list() == quarters["estab_gap_after_other"].to_list() == [0]


def test_a_withheld_value_outside_the_national_total_leaves_months_testable():
    """Suppression in an area that is not part of the national total cannot make the national
    identity untestable, because that area is not a term in it."""
    quarters, months, _ = comparison_tables(outside_containment_panel())
    out = classify_identity(quarters, months)
    assert out["evidence"]["testable_months"] == 3
    assert out["evidence"]["untestable_months"] == 0
    assert months["other_emp"].to_list() == [0, 0, 0]


def test_a_withheld_value_inside_the_national_total_makes_months_untestable():
    """The mirror image: when the area *is* a term in the national total, a withheld value is a
    missing term and the month must not be scored as if it were zero."""
    rows = []
    for month in (1, 2, 3):
        rows += [
            ("US000", "US TOTAL", "national", 2017, 1, month, 500, 110, "", False),
            ("01000", "Alabama", "states_dc", 2017, 1, month, 450, 100, "", False),
            ("72000", "Puerto Rico -- Statewide", "other_state_level", 2017, 1, month,
             None, 10, "N", True),
        ]
    quarters, months, containment = comparison_tables(panel(rows))
    assert containment["verdict"] == INSIDE
    assert quarters["estab_gap_after_other"].to_list() == [0]
    out = classify_identity(quarters, months)
    assert out["evidence"]["untestable_months"] == 3
    assert out["branch"] == "decline"
    assert "untestable" in out["reason"]


def test_qtrly_estabs_disagreeing_within_a_quarter_raises():
    """The establishment sums assume one quarterly value per area-quarter, so a disagreement
    fails loudly rather than being silently resolved by picking a row."""
    rows = [("01000", "Alabama", "states_dc", 2017, 1, month, 10, estabs, "", False)
            for month, estabs in ((1, 100), (2, 101), (3, 100))]
    with pytest.raises(ValueError, match="qtrly_estabs varies"):
        comparison_tables(panel(rows))


def test_the_as_published_non_state_amount_survives_the_containment_adjustment():
    """Zeroing `other_estabs`/`other_emp` must not erase what the source actually published, or
    a reader of the persisted tables alone concludes the panel carries no non-state areas."""
    quarters, months, _ = comparison_tables(outside_containment_panel())
    assert quarters["other_estabs"].to_list() == [0]
    assert quarters["other_estabs_published"].to_list() == [1]
    assert months["other_emp"].to_list() == [0, 0, 0]
    # withheld, so null rather than 0 -- "not published" stays distinct from "published zero"
    assert months["other_emp_published"].to_list() == [None, None, None]


def test_the_suppressed_range_is_taken_over_testable_months_only():
    """The clause attributes the range to testable months, so an untestable month's count must
    not widen it."""
    m = months([(2017, 1, 500, 400, 0, 100, 100, 5),
                (2017, 2, None, 400, 0, None, None, 99)])
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    clause = _clean_month_clause(classify_identity(q, m)["evidence"], m)
    assert "between 5 and 5" in clause
    assert "99" not in clause
