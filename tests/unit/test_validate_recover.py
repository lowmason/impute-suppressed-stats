from pathlib import Path

import polars as pl

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.recover import is_exactly_recoverable, mask_and_solve


def test_a_masked_state_total_is_unbounded_and_the_hash_moves():
    """The state-total arm carries no identification — this is a SCOPED NEGATIVE, not a bug.

    Every `state_total` cell is a single-cell component: `assert_no_national_employment_margin`
    implements Stage 0's SRC-QCEW-006 `decline`, so no multi-cell row ever touches one.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    base = mask_and_solve(data, [], cfg)
    masked = mask_and_solve(
        data, [MaskTarget("41", "2019-06", "state_total", "primary_like")], cfg
    )
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"
    row = masked.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
    assert row["bound_status"] == "unbounded"
    assert row["selected_lower"] == 0.0
    assert row["selected_upper"] is None
    assert masked.constraint_set_hash != base.constraint_set_hash
    assert not is_exactly_recoverable(masked.bounds, cell)


def test_exactly_identified_is_not_the_step_six_predicate():
    """A filter on `exactly_identified` would flag every published cell."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    system = mask_and_solve(data, [], cfg)
    assert system.bounds.filter(pl.col("exactly_identified")).height > 1000
    assert system.bounds.filter(pl.col("bound_status") == "exactly_recoverable").height == 0
