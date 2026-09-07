import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY, run_baselines
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.reconcile.anchor import observed_partition
from logging_employment.validate.leakage import (
    assert_no_future_rows,
    assert_no_retained_truth,
)
from logging_employment.validate.mask import MaskTarget, apply_mask


def test_no_column_of_the_masked_frame_retains_a_held_out_value():
    data = HarmonizedData.load(Path("data/staged"))
    masked, truth = apply_mask(data, [MaskTarget("41", "2019-06", "state_total", "primary_like")])
    assert_no_retained_truth(masked, truth)


def test_a_rolling_origin_frame_carrying_a_future_row_is_refused():
    data = HarmonizedData.load(Path("data/staged"))
    with pytest.raises(AssertionError, match="future"):
        assert_no_future_rows(data.qcew_monthly, origin="2020-01")


def test_every_estimator_is_invariant_to_the_held_out_value():
    """§13.4 bullet 1, end to end: change the truth under a fixed mask, get identical estimates.

    SCOPE, because the obvious reading overclaims. Measured: the two masked frames here are
    byte-identical, so this cannot catch "an estimator read `context.monthly`" — under a frame
    mask `context.monthly` IS the masked frame and holds a null, not the truth. What it does
    catch is a regression in `apply_mask` that leaves some column a FUNCTION of the held-out
    value: the frames would then differ, and any estimator reading that column would diverge.
    The structural half of the property is pinned by the partition test below.
    """
    cfg = load_config(Path("config.yaml"))
    data = HarmonizedData.load(Path("data/staged"))
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")

    masked_a, _ = apply_mask(data, [target])
    poisoned = data.qcew_monthly.with_columns(
        pl.when((pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06"))
        .then(pl.col("employment_value") * 7)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    )
    masked_b, _ = apply_mask(dataclasses.replace(data, qcew_monthly=poisoned), [target])

    subset = REGISTRY[:4]
    a, _ = run_baselines(masked_a, cfg, estimators=subset)
    b, _ = run_baselines(masked_b, cfg, estimators=subset)
    key = ["estimator_id", "cell_id"]
    assert a.sort(key).select("estimate").equals(b.sort(key).select("estimate"))


def test_the_partition_the_runner_derives_carries_no_held_out_truth():
    """Evidence §3's latent leak, closed structurally and pinned here.

    `observed_partition`'s docstring invites a Partition-only mask, which leaves the truth sitting
    in `context.partitions[m].missing["employment_value"]` — one column read from any estimator.
    Today's ten estimators happen not to read it, so that leak is latent rather than actual. The
    frame mask makes it unconstructible: the runner derives its partition FROM the masked frame,
    so the missing set carries nulls. This test fails the moment anything reintroduces a
    partition built from unmasked data.
    """
    data = HarmonizedData.load(Path("data/staged"))
    target = MaskTarget("41", "2019-06", "state_total", "primary_like")
    masked, truth = apply_mask(data, [target])

    partitions = observed_partition(masked.qcew_monthly)
    missing = partitions["2019-06"].missing
    held_out = missing.filter(pl.col("state_fips") == "41")
    assert held_out.height == 1, "the masked cell must land in the missing set"
    assert held_out["employment_value"].item() is None
    # And it is genuinely the cell whose truth we hold: same key, value withheld.
    assert truth["truth"].item() is not None
