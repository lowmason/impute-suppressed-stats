import ast
from pathlib import Path

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


PROMOTION_KEYS = frozenset(
    {
        "minimum_wape_improvement",
        "maximum_major_stratum_wape_degradation",
        "nominal_coverage_tolerance",
    }
)


def _named_keys(source: str) -> set[str]:
    """The promotion keys a module NAMES in code, ignoring comments and docstrings.

    An attribute access (`cfg.promotion.nominal_coverage_tolerance`) or a string constant equal to a
    key (what `getattr(cfg.promotion, "...")` and `model_dump()["..."]` spell) counts. A comment is
    not in the AST, and a docstring is excluded by position, so a cross-reference that merely
    MENTIONS a key cannot trip the tripwire. What this cannot see is a reader that never spells a
    key at all -- `cfg.promotion.model_dump().items()` iterated generically.
    """
    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    named: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in PROMOTION_KEYS:
            named.add(node.attr)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in PROMOTION_KEYS
            and id(node) not in docstrings
        ):
            named.add(node.value)
    return named


def test_the_tripwire_detector_sees_reads_and_ignores_mentions():
    """Without this the tripwire below could pass vacuously -- a detector that finds nothing is green."""
    assert _named_keys("x = cfg.promotion.nominal_coverage_tolerance") == {
        "nominal_coverage_tolerance"
    }
    assert _named_keys('v = getattr(p, "minimum_wape_improvement")') == {"minimum_wape_improvement"}
    assert _named_keys('v = p.model_dump()["maximum_major_stratum_wape_degradation"]') == {
        "maximum_major_stratum_wape_degradation"
    }
    mentions = (
        '"""Feeds nominal_coverage_tolerance."""\n'
        "# see minimum_wape_improvement\n"
        "def f():\n"
        '    """Reads maximum_major_stratum_wape_degradation later."""\n'
        "    return 1\n"
    )
    assert _named_keys(mentions) == set()


def test_the_promotion_keys_are_still_unread_and_the_docstring_still_says_so():
    """R-S5G-3: a TRIPWIRE, not a prohibition. It fails when a `src/` reader NAMES one of these keys.

    `PromotionConfig`'s docstring records all three as inert. A docstring cannot notice when it
    stops being true, and the failure mode is specific: the day a promotion path reads one of
    these, the note becomes a false statement in the file a reader consults first. Derived from the
    code's AST (`_named_keys`) rather than asserting a sentence exists, so it tracks code, not prose.
    The declaring module is excluded by RESOLVED PATH, not basename, so a future `config.py` in a
    subpackage is still scanned. When it reddens, the fix is to update the docstring -- not to
    delete this test.
    """
    src = Path(__file__).resolve().parents[2] / "src" / "logging_employment"
    declaring = (src / "config.py").resolve()
    readers = {
        path.relative_to(src).as_posix(): sorted(named)
        for path in sorted(src.rglob("*.py"))
        if path.resolve() != declaring and (named := _named_keys(path.read_text(encoding="utf-8")))
    }
    assert readers == {}, f"now read by {readers}; update PromotionConfig's docstring"
