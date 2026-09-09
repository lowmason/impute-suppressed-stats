"""M9: the seven Appendix A switches were never a uniform set, so each declares its kind."""

from logging_employment.config import ValidationConfig
from logging_employment.contracts import (
    HOLDOUT_REGIMES,
    REGIME_SWITCHES,
    SWITCH_KINDS,
    VALIDATION_SWITCH_KINDS,
)


def test_every_include_field_is_classified():
    """Derived from the model, so adding a switch without classifying it fails here."""
    switches = {name for name in ValidationConfig.model_fields if name.startswith("include_")}
    assert switches == set(VALIDATION_SWITCH_KINDS)


def test_every_declared_kind_is_from_the_closed_set():
    for switch, kind in VALIDATION_SWITCH_KINDS.items():
        assert kind in SWITCH_KINDS, switch


def test_the_four_regime_switches_name_real_regimes():
    """R-S4C-10: four of the seven name regimes; the mapping must be to declared ones."""
    regime_switches = {
        switch for switch, kind in VALIDATION_SWITCH_KINDS.items() if kind == "regime_switch"
    }
    assert regime_switches == set(REGIME_SWITCHES.values())
    assert set(REGIME_SWITCHES) <= set(HOLDOUT_REGIMES)
    assert REGIME_SWITCHES == {
        "long_consecutive_runs": "include_long_runs",
        "rolling_origin": "include_rolling_origin",
        "retrospective_smoothing": "include_retrospective_smoothing",
        "preliminary_to_final_vintage": "include_vintage_comparison",
    }


def test_the_mask_label_switches_are_not_regime_switches():
    """R-S4C-13: `include_primary_like` / `include_complementary_like` are INV-009 LABELS."""
    assert VALIDATION_SWITCH_KINDS["include_primary_like"] == "mask_label_switch"
    assert VALIDATION_SWITCH_KINDS["include_complementary_like"] == "mask_label_switch"


def test_the_sanity_check_switch_is_a_design_validity_operand():
    """It names a design with no implementation anywhere in the package — but it is not inert."""
    assert VALIDATION_SWITCH_KINDS["include_random_mask_sanity_check"] == "design_validity_operand"


def test_nine_of_thirteen_regimes_have_no_switch():
    """M9's count, as a property. A switch set that grew to cover them would be a design change."""
    assert len(HOLDOUT_REGIMES) - len(REGIME_SWITCHES) == 9
