from pathlib import Path

import polars as pl
from tests.conftest import STAGED, requires_staged

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.validate.propensity import sample_targets, target_propensity

pytestmark = requires_staged


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(STAGED).qcew_monthly


def test_propensity_is_defined_on_every_eligible_cell_and_nowhere_else():
    scored = target_propensity(_monthly(), config=load_config(Path("config.yaml")))
    assert scored.filter(pl.col("observation_status") != "observed").height == 0
    assert scored["propensity"].null_count() == 0
    assert scored["propensity"].min() >= 0.0


def test_small_cells_score_higher_than_large_ones():
    """§13.2's propensity must favour primary-like targets: small, sparse, concentrated."""
    scored = target_propensity(_monthly(), config=load_config(Path("config.yaml")))
    small = scored.sort("qtrly_establishments").head(200)["propensity"].mean()
    large = scored.sort("qtrly_establishments", descending=True).head(200)["propensity"].mean()
    assert small > large


def test_sampling_is_deterministic_for_a_seed():
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    a = sample_targets(monthly, n=10, seed=1024, config=cfg)
    b = sample_targets(monthly, n=10, seed=1024, config=cfg)
    c = sample_targets(monthly, n=10, seed=2048, config=cfg)
    assert a == b
    assert a != c


def test_no_predictor_reads_the_targets_own_employment_value():
    """§13.4 bullet 1, at selection time: perturbing a cell must not move its own propensity."""
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    base = target_propensity(monthly, config=cfg)
    poisoned = monthly.with_columns(
        pl.when((pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06"))
        .then(pl.col("employment_value") * 100)
        .otherwise(pl.col("employment_value"))
        .alias("employment_value")
    )
    after = target_propensity(poisoned, config=cfg)
    key = (pl.col("state_fips") == "41") & (pl.col("reference_month") == "2019-06")
    assert base.filter(key)["propensity"].item() == after.filter(key)["propensity"].item()


def test_the_draw_is_propensity_weighted_not_merely_sorted():
    """Not in the plan's test set. `small_cell_biased`'s only selector is `sample_targets`.

    A uniform draw that is sorted by propensity afterwards returns the SAME population as a random
    mask — §13.2 prohibits random masking as the only design, and the regime's name would then
    misreport what it drew. Compare the drawn cells' establishment counts against the eligible
    pool's: a weighted draw is materially smaller, a sorted-uniform one is not.
    """
    monthly, cfg = _monthly(), load_config(Path("config.yaml"))
    scored = target_propensity(monthly, config=cfg)
    pool_median = scored["qtrly_establishments"].median()

    drawn = sample_targets(monthly, n=200, seed=1024, config=cfg)
    keys = [{"state_fips": t.state_fips, "reference_month": t.reference_month} for t in drawn]
    picked = scored.filter(pl.struct("state_fips", "reference_month").is_in(keys))
    assert picked["qtrly_establishments"].median() < pool_median
