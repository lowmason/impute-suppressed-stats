from pathlib import Path

import polars as pl
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.recover import is_exactly_recoverable, mask_and_solve

pytestmark = requires_staged


def test_a_masked_state_total_is_bounded_by_its_published_parent_and_the_hash_moves():
    """Oregon 2019-06: a published `113` parent with other establishments bounds the masked cell.

    Before `D-111` this was a scoped negative -- every state cell a single-cell component and the
    masked cell `[0, +inf)`. The parent's value and its establishment count are read off the staged
    tables, never typed; the precondition that it has other establishments is what keeps it public
    under §13.2 step 4's rule once plan 15 Task 8 lands.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    base = mask_and_solve(data, [], cfg)
    masked = mask_and_solve(data, [MaskTarget("41", "2019-06", "state_total", "primary_like")], cfg)
    at = (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    parent = data.qcew_state_parent.filter(at).row(0, named=True)
    child = data.qcew_monthly.filter(at & (pl.col("area_type") == "state")).row(0, named=True)
    assert parent["observation_status"] == "observed"
    assert parent["qtrly_establishments"] > child["qtrly_establishments"]
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"
    row = masked.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
    assert row["bound_status"] == "partially_identified"
    assert row["selected_lower"] == 0.0
    assert row["selected_upper"] == float(parent["employment_value"])
    assert masked.constraint_set_hash != base.constraint_set_hash
    assert not is_exactly_recoverable(masked.bounds, cell)


def test_exactly_identified_is_not_the_step_six_predicate():
    """A filter on `exactly_identified` would flag every published cell."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    system = mask_and_solve(data, [], cfg)
    assert system.bounds.filter(pl.col("exactly_identified")).height > 1000
    assert system.bounds.filter(pl.col("bound_status") == "exactly_recoverable").height == 0
