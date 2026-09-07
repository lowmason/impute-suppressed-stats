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


def assert_no_retained_truth(masked: HarmonizedData, truth: pl.DataFrame) -> None:
    """§13.4 bullet 1: no direct copy or derived feature retains the held-out value."""
    for row in truth.iter_rows(named=True):
        cell = masked.qcew_monthly.filter(
            (pl.col("state_fips") == row["state_fips"])
            & (pl.col("reference_month") == row["reference_month"])
        )
        if cell.height == 0:
            continue
        withheld = str(row["truth"])
        for column, value in cell.row(0, named=True).items():
            assert str(value) != withheld, (
                f"{column} on {row['state_fips']}/{row['reference_month']} retains the held-out "
                f"value {withheld}"
            )


def assert_no_future_rows(frame: pl.DataFrame, *, origin: str) -> None:
    """§13.4 bullet 3: a rolling-origin frame contains no period at or after the origin.

    This guard, not the mask, is what Stage 4's exit criterion "a rolling-origin run provably
    contains no future-period rows" is about — a mask hides values, it does not remove rows.
    """
    future = frame.filter(pl.col("reference_month") >= origin)
    assert future.height == 0, (
        f"{future.height} future rows at or after origin {origin}: "
        f"{sorted(future['reference_month'].unique().to_list())[:5]}"
    )
