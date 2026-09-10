from pathlib import Path

import polars as pl
import pytest
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.recover import mask_and_solve_size

pytestmark = requires_staged


def _fully_observed_march(data: HarmonizedData) -> str:
    size = data.qcew_national_size.filter(
        (pl.col("industry_code") == "113310") & (pl.col("reference_month").str.ends_with("-03"))
    )
    counts = size.group_by("reference_month").agg(
        (pl.col("observation_status") == "suppressed").sum().alias("n")
    )
    clean = counts.filter(pl.col("n") == 0)
    if clean.height == 0:
        pytest.skip("no fully observed March margin in this vintage")
    return clean["reference_month"].sort().to_list()[0]


def test_a_single_class_mask_on_a_clean_march_is_exactly_recoverable():
    """§13.2 step 6's rejection, on the ONLY arm where it can fire."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    month = _fully_observed_march(data)
    system, cell_id = mask_and_solve_size(data, month, n_classes=1, seed=1024, config=cfg)
    row = system.bounds.filter(pl.col("cell_id") == cell_id).row(0, named=True)
    assert row["bound_status"] == "exactly_recoverable"
    assert row["selected_lower"] == row["selected_upper"]


def test_a_complementary_pair_defeats_exact_recovery():
    """§13.2 step 3, where it has real content: two masked classes leave nullity > 0."""
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    month = _fully_observed_march(data)
    system, cell_id = mask_and_solve_size(data, month, n_classes=2, seed=1024, config=cfg)
    row = system.bounds.filter(pl.col("cell_id") == cell_id).row(0, named=True)
    assert row["bound_status"] == "partially_identified"
    assert row["selected_lower"] < row["selected_upper"]
