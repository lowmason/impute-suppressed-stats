import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.mask import MaskTarget, apply_mask, eligible_targets

STAGED = Path("data/staged")


def _data() -> HarmonizedData:
    return HarmonizedData.load(STAGED)


def test_a_masked_row_is_indistinguishable_from_a_real_suppression():
    data = _data()
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    masked, _truth = apply_mask(data, [target])

    real = masked.qcew_monthly.filter(
        (pl.col("observation_status") == "suppressed") & (pl.col("suppression_type") == "unknown")
    ).head(1)
    made = masked.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )
    shared = [
        "employment_value",
        "employment_raw",
        "wages_value",
        "wages_raw",
        "disclosure_code",
        "observation_status",
        "is_published_numeric_zero",
    ]
    assert made.select(shared).row(0) == real.select(shared).row(0)
    # ...but the synthetic label distinguishes it for INV-009.
    assert made["suppression_type"].item() == "primary_like"


def test_no_column_of_a_masked_row_retains_the_withheld_truth():
    data = _data()
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    masked, truth = apply_mask(data, [target])
    withheld = truth["truth"].item()

    row = masked.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    ).row(0, named=True)
    for column, value in row.items():
        assert str(value) != str(withheld), f"{column} retained the held-out truth"


def test_the_staged_layer_is_not_mutated():
    data = _data()
    before = data.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )["employment_value"].item()
    apply_mask(data, [MaskTarget("41", "2019-06", "state_total", "primary_like")])
    after = data.qcew_monthly.filter(
        (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    )["employment_value"].item()
    assert before == after


def test_a_true_zero_cell_is_refused_as_a_target():
    """Measured: masking the one true_zero cell raises WeightDomainError in 8 of 10 estimators.

    On D1 a true zero carries `observation_status == 'true_zero'`, so the observed-only predicate
    is what refuses it — verified, all 27 true-zero rows also have `qtrly_establishments == 0`,
    and no observed row has zero establishments. Match on the status message, not the
    establishment one, or this test asserts a guard that never fires.
    """
    data = _data()
    with pytest.raises(ConceptViolationError, match="observation_status"):
        apply_mask(data, [MaskTarget("38", "2020-01", "state_total", "primary_like")])


def test_an_observed_cell_with_no_establishments_is_refused():
    """The second guard, exercised directly.

    Measured 2026-09-07: zero D1 rows are `observed` with `qtrly_establishments <= 0`, so this
    guard is unreachable through the staged layer today. It is kept because a revision that
    published such a row would otherwise cost a whole month across nine estimators, and it is
    tested on a synthetic frame rather than left as unexecuted code.
    """
    data = _data()
    poisoned = data.qcew_monthly.with_columns(
        pl.when((pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06"))
        .then(0)
        .otherwise(pl.col("qtrly_establishments"))
        .alias("qtrly_establishments")
    )
    with pytest.raises(ConceptViolationError, match="qtrly_establishments"):
        apply_mask(
            dataclasses.replace(data, qcew_monthly=poisoned),
            [MaskTarget("41", "2019-06", "state_total", "primary_like")],
        )


def test_an_already_suppressed_cell_is_refused_as_a_target():
    data = _data()
    suppressed = data.qcew_monthly.filter(pl.col("observation_status") == "suppressed").row(
        0, named=True
    )
    with pytest.raises(ConceptViolationError, match="observation_status"):
        apply_mask(
            data,
            [
                MaskTarget(
                    suppressed["state_fips"],
                    suppressed["reference_month"],
                    "state_total",
                    "primary_like",
                )
            ],
        )


def test_an_undeclared_suppression_type_is_refused():
    data = _data()
    with pytest.raises(ConceptViolationError, match="suppression_type"):
        apply_mask(data, [MaskTarget("41", "2019-06", "state_total", "invented_kind")])


def test_eligible_targets_excludes_true_zero_and_already_suppressed():
    data = _data()
    eligible = eligible_targets(data.qcew_monthly)
    assert eligible.filter(pl.col("qtrly_establishments") <= 0).height == 0
    assert eligible.filter(pl.col("observation_status") != "observed").height == 0
    assert eligible.filter(pl.col("area_type") != "state").height == 0


def test_a_duplicated_target_is_refused():
    """Not in the plan's test set; added because the label join is on (state, month).

    A target set naming the same cell twice makes `labels` carry two rows for one key, and a left
    join then emits TWO rows for that cell in the masked frame. The height check above does not
    catch it — `set(keys)` dedups before comparing — so the frame would silently gain a row and
    the missing set would double-count the cell.
    """
    data = _data()
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    with pytest.raises(ConceptViolationError, match="twice"):
        apply_mask(data, [target, target])
