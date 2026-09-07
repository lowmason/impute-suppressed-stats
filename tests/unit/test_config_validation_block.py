import pytest
from pydantic import ValidationError

from logging_employment.config import PromotionConfig, ValidationConfig


def test_a_random_mask_only_design_is_refused_at_construction():
    """§13.2's opening line is a config-time refusal, not a runtime warning."""
    with pytest.raises(ValidationError, match="random_mask_only"):
        ValidationConfig(
            pseudo_suppression_seeds=[1024],
            include_random_mask_sanity_check=True,
            include_primary_like=False,
            include_complementary_like=False,
            include_long_runs=False,
            include_rolling_origin=False,
            include_retrospective_smoothing=False,
            include_vintage_comparison=False,
        )


def test_vintage_comparison_defaults_off_because_d1_carries_one_vintage():
    cfg = ValidationConfig(pseudo_suppression_seeds=[1024], include_primary_like=True)
    assert cfg.include_vintage_comparison is False


def test_promotion_gates_carry_appendix_a_defaults():
    p = PromotionConfig()
    assert p.minimum_wape_improvement == 0.05
    assert p.maximum_major_stratum_wape_degradation == 0.02
    assert p.nominal_coverage_tolerance == 0.05
