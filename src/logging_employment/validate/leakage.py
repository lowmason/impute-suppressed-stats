"""§13.4's leakage controls, as executable guards.

Three of the five bullets bind today. The other two are recorded as unbindable rather than faked:
"feature normalization and hyperparameter selection are fit only on the training information set"
has no fitted feature pipeline until Stage 5, and "final revisions are excluded from real-time
tests" has no second vintage to exclude (measured 2026-09-07: no period in any staged table carries
a second snapshot).

The third bullet — that no estimator's output depends on a held-out value — has no function here.
It is a property of the whole registry rather than of one frame, so it is carried by
`test_every_estimator_is_invariant_to_the_held_out_value` in
`tests/integration/test_validate_leakage.py`, which perturbs the truth under a fixed mask and
requires identical estimates. A function asserting it would have to run `run_baselines` twice, so
the test is the guard.
"""

from __future__ import annotations

import polars as pl

from ..contracts import HarmonizedData
from ..errors import LeakageError

# Columns that stay PUBLIC when a cell is suppressed, so a value of theirs equal to the withheld
# employment is a coincidence rather than a retention. Excluded by name, and by name only, so that
# any column added later is checked by default.
#
# The list is not a convenience. It was forced by a real firing on the first full harness run:
# `aggregation_level` is the QCEW aggregation-level code and takes exactly two values, '18'
# (national) and '58' (state) — so every masked state cell whose truth is 58 employees tripped a
# string comparison against a constant. `qtrly_establishments` is the same class of case and the
# more important one: QCEW publishes it FOR suppressed cells, which is the entire basis of §10.2
# and of §13.2's propensity, so a state with 58 establishments and 58 employees is public data
# coinciding with the truth, not a leak. `source_row_hash` is built from identity columns only
# (`ingest/qcew.py` uses no value column), so retaining it does not retain the value.
_PUBLIC_UNDER_SUPPRESSION: frozenset[str] = frozenset(
    {
        "snapshot_id",
        "release_vintage",
        "release_status",
        "reference_quarter",
        "reference_month",
        "area_fips",
        "area_type",
        "state_fips",
        "industry_code",
        "naics_vintage",
        "ownership_code",
        "aggregation_level",
        "size_code",
        "qtrly_establishments",
        "disclosure_code",
        "observation_status",
        "is_published_numeric_zero",
        "is_true_zero",
        "source_row_hash",
        "suppression_type",
    }
)


def assert_no_retained_truth(masked: HarmonizedData, truth: pl.DataFrame) -> None:
    """§13.4 bullet 1: no direct copy or derived feature retains the held-out value.

    SCOPE. This is a tripwire over the columns a mask is responsible for clearing, not a proof of
    independence: the columns in `_PUBLIC_UNDER_SUPPRESSION` are published for suppressed cells
    anyway, so an equality there carries no information a real suppression would not also carry.
    The proof that nothing DERIVED depends on the withheld value is the perturbation test in
    `tests/integration/test_validate_leakage.py`, which changes the truth and requires an
    identical masked frame.
    """
    for row in truth.iter_rows(named=True):
        cell = masked.qcew_monthly.filter(
            (pl.col("state_fips") == row["state_fips"])
            & (pl.col("reference_month") == row["reference_month"])
        )
        if cell.height == 0:
            continue
        withheld = str(row["truth"])
        for column, value in cell.row(0, named=True).items():
            if column in _PUBLIC_UNDER_SUPPRESSION:
                continue
            if str(value) == withheld:
                raise LeakageError(
                    f"{column} on {row['state_fips']}/{row['reference_month']} retains the "
                    f"held-out value {withheld}"
                )


def assert_no_future_rows(frame: pl.DataFrame, *, origin: str) -> None:
    """§13.4 bullet 3: a rolling-origin frame contains no period at or after the origin.

    This guard, not the mask, is what Stage 4's exit criterion "a rolling-origin run provably
    contains no future-period rows" is about — a mask hides values, it does not remove rows.
    """
    future = frame.filter(pl.col("reference_month") >= origin)
    if future.height:
        raise LeakageError(
            f"{future.height} future rows at or after origin {origin}: "
            f"{sorted(future['reference_month'].unique().to_list())[:5]}"
        )
