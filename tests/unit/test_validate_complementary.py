from pathlib import Path

import polars as pl
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.mask import MaskTarget
from logging_employment.validate.propensity import complementary_partners
from logging_employment.validate.recover import mask_and_solve

pytestmark = requires_staged


def test_partners_share_the_targets_month_and_are_labelled_complementary():
    monthly = HarmonizedData.load(STAGED).qcew_monthly
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    partners = complementary_partners(monthly, target, n=2, seed=1024)
    assert len(partners) == 2
    assert all(p.reference_month == "2019-06" for p in partners)
    assert all(p.suppression_type == "complementary_like" for p in partners)
    assert all(p.state_fips != "41" for p in partners)


def test_a_complementary_mask_changes_nothing_about_state_total_identification():
    """The scoped negative, pinned. Complementary masking is inert on this arm — by construction.

    If this test ever fails, a national employment margin has appeared in the constraint system and
    SRC-QCEW-006's `decline` has been overturned somewhere. That is a finding, not a flake.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(STAGED)
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    partners = complementary_partners(data.qcew_monthly, target, n=2, seed=1024)
    cell = "state_total|41|2019-06|5|113310|NAICS 2017|ALL"

    alone = mask_and_solve(data, [target], cfg)
    with_partners = mask_and_solve(data, [target, *partners], cfg)
    for system in (alone, with_partners):
        row = system.bounds.filter(pl.col("cell_id") == cell).row(0, named=True)
        assert row["bound_status"] == "unbounded"
