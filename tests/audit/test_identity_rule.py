"""Judgment-logic tests for the SRC-QCEW-006 branch rule.

`classify_identity` is a pure function of two comparison tables, and these tests fix its
behaviour on toy panels *before* it is ever pointed at `qcew_panel`. That ordering is the point:
scanning first and reasoning second produces a rationalisation for whichever verdict the data
suggests.

The first nine tests come from the task brief and pin the three-branch contract. The rest pin
the two silent failure modes the brief's illustrative code leaves open, both of which would
corrupt the highest-stakes output in the *safe*-looking direction:

1. `Series.all()` defaults to `ignore_nulls=True`, so a null comparison cell is skipped and
   reads as a pass -- an unevaluable quarter would silently become `enforce`.
2. A reference-side value that was never published must not be summed to `0`, which is
   indistinguishable from a published zero and manufactures (or hides) a gap.

`qcew_identity` is imported bare, like `_common`, per `tests/conftest.py`. Importing it is
inert: the module's only side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import polars as pl
import pytest

from qcew_identity import classify_identity


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
    sentence, so no reason may contain a sentence break."""
    cases = [
        (quarters([(2017, 1, 120, 100, 10, 20, 10)]), months([(2017, 1, 550, 500, 50, 50, 0, 0)])),
        (quarters([(2017, 1, 100, 100, 0, 0, 0)]), months([(2017, 1, 500, 520, 0, -20, -20, 1)])),
        (quarters([(2017, 1, 100, 100, 0, 0, 0)]), months([(2017, 1, 500, 400, 0, 100, 100, 3)])),
        (quarters([(2017, 1, 100, 100, 0, 0, 0)]), months([(2017, 1, 505, 500, 0, 5, 5, 0)])),
        (quarters([(2017, 1, 110, 100, 10, 10, 0)]), months([(2017, 1, 550, 500, 50, 50, 0, 0)])),
        (quarters([(2017, 1, 100, 100, 0, 0, 0)]), months([(2017, 1, 500, 500, 0, 0, 0, 0)])),
    ]
    for q, m in cases:
        reason = classify_identity(q, m)["reason"]
        assert ". " not in reason
        assert not reason.endswith(".")
