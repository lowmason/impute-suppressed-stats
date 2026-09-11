"""Judgment-logic tests for `qcew_parent_margins` (R-S5G-5).

Nothing here touches the network or `data/raw/audit/`. The script's only decision is which margin
identifies a suppressed cell and how strongly; the fetching around it is `_common`'s and is tested
there. `qcew_parent_margins` is imported bare, like `_common`, per `tests/conftest.py`; importing
it is inert because its side effects sit behind `if __name__ == "__main__"`.
"""

from __future__ import annotations

import qcew_parent_margins as m

NOTHING = {
    "parent_113_disclosed": False,
    "parent_1133_disclosed": False,
    "parent_11331_disclosed": False,
    "ownership_total_disclosed": False,
    "ownership_siblings_disclosed": False,
}


def test_no_disclosed_margin_is_the_status_quo():
    """Today's measured state: every one of the 1,227 suppressed cells is `[0, +inf)`."""
    assert m.identification(NOTHING) == m.NONE


def test_a_disclosed_single_child_parent_is_exact_not_a_bound():
    """D6: `1133 -> 11331 -> 113310` is single-child in both vintages, so the parent IS the cell."""
    for level in ("parent_1133_disclosed", "parent_11331_disclosed"):
        assert m.identification({**NOTHING, level: True}) == m.EXACT


def test_a_disclosed_113_bounds_rather_than_identifies():
    """`113` aggregates 1131, 1132 and 1133; nonnegativity of the siblings gives an upper bound."""
    assert m.identification({**NOTHING, "parent_113_disclosed": True}) == m.UPPER_BOUND


def test_total_ownership_is_exact_only_when_the_sibling_is_disclosed_too():
    total = {**NOTHING, "ownership_total_disclosed": True}
    assert m.identification(total) == m.UPPER_BOUND
    assert m.identification({**total, "ownership_siblings_disclosed": True}) == m.EXACT


def test_exact_outranks_a_bound_when_both_are_available():
    """The strongest margin wins: a cell with both is a REQ-027 case, not a bounded one."""
    both = {**NOTHING, "parent_113_disclosed": True, "parent_1133_disclosed": True}
    assert m.identification(both) == m.EXACT
