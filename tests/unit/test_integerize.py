"""§12.6 balanced integerization: the margin survives rounding, and rounding is reproducible."""

from __future__ import annotations

import math

import pytest

from logging_employment.reconcile.integerize import integerize


def test_the_total_survives_rounding() -> None:
    """Independent rounding would give 9, not 10. §12.6 forbids exactly that."""
    out = integerize({"01": 3.4, "02": 3.3, "04": 3.3}, total=10)
    assert sum(out.values()) == 10


def test_units_go_to_the_largest_fractional_remainders() -> None:
    out = integerize({"01": 1.9, "02": 1.6, "04": 1.5}, total=5)
    assert sum(out.values()) == 5
    assert out["01"] == 2


def test_the_tiebreak_is_deterministic_and_repeatable() -> None:
    """§16.1 requires idempotence; a random tie-break would break it.

    Identical fractional parts across every cell force the tie-break to decide alone.
    """
    values = {"04": 1.5, "01": 1.5, "02": 1.5}
    first = integerize(values, total=5)
    for _ in range(20):
        assert integerize(values, total=5) == first
    # Ties break by cell_id ascending, so the lowest ids take the extra units.
    assert first["01"] == 2
    assert first["02"] == 2
    assert first["04"] == 1


def test_integer_lower_and_upper_bounds_are_respected() -> None:
    out = integerize(
        {"01": 5.5, "02": 2.5, "04": 2.0}, total=10, upper={"01": 4, "02": None, "04": None}
    )
    assert sum(out.values()) == 10
    assert out["01"] <= 4


def test_a_zero_total_yields_all_zeros() -> None:
    assert integerize({"01": 0.0, "02": 0.0}, total=0) == {"01": 0, "02": 0}


def test_an_empty_input_returns_empty() -> None:
    assert integerize({}, total=0) == {}


def test_a_total_below_the_summed_lower_bounds_raises() -> None:
    with pytest.raises(ValueError):
        integerize({"01": 1.0, "02": 1.0}, total=1, lower={"01": 1, "02": 1})


def test_a_capped_cell_does_not_starve_an_uncapped_one() -> None:
    """The termination bound must not shrink as units are placed.

    Computing `len(order) * (remaining + 1)` inside the loop condition re-evaluates it against a
    `remaining` that falls with every placement, so the ceiling drops toward the index and the
    loop exits early. Here cells 01 and 02 are capped at 0 and every index spent skipping them
    eats budget: the bound falls 12 -> 9 -> 6 while the index climbs to 6, and one unit is left
    unplaced even though cell 03 is uncapped and can absorb it.
    """
    out = integerize({"01": 0.0, "02": 0.0, "03": 10.0}, total=13, upper={"01": 0, "02": 0})
    assert out == {"01": 0, "02": 0, "03": 13}


def test_every_feasible_bounded_input_places_all_its_units() -> None:
    """A randomised sweep over inputs that are feasible by independent construction.

    Feasibility is decided outside the function -- summed floors at or below the total, and enough
    headroom under the caps to absorb the remainder -- so any exception here is the algorithm's,
    not the fixture's.
    """
    import random

    rng = random.Random(20260905)
    for _ in range(400):
        n = rng.randint(2, 6)
        cells = [f"{i:02d}" for i in range(n)]
        values = {c: rng.uniform(0.0, 12.0) for c in cells}
        floors = {c: math.floor(v) for c, v in values.items()}
        caps: dict[str, int | None] = {}
        for c in cells:
            caps[c] = floors[c] + rng.randint(0, 4) if rng.random() < 0.5 else None
        capacity = sum((caps[c] - floors[c]) if caps[c] is not None else 10_000 for c in cells)
        base = sum(floors.values())
        total = base + rng.randint(0, min(capacity, 8))
        out = integerize(values, total=total, upper=caps)
        assert sum(out.values()) == total
        for c in cells:
            if caps[c] is not None:
                assert out[c] <= caps[c]


def test_a_contradictory_bound_pair_is_refused() -> None:
    """`floors` took the lower bound, then the cap loop overwrote it with the upper bound.

    Nothing compared the two, so `lower=5, upper=3` returned 3 -- below a bound the caller
    declared. D1 has `lower=0, upper=None` throughout, so this is latent here and live in
    Stage 6, which supplies real class bands.
    """
    with pytest.raises(ValueError, match="lower bound"):
        integerize({"a": 4.0}, 3, lower={"a": 5}, upper={"a": 3})


def test_a_cap_for_a_cell_with_no_value_does_not_inject_a_phantom_entry() -> None:
    """The cap loop iterated `upper`, not `values`, so it could create a cell out of nothing.

    A negative cap made `floors.get(cell, 0) > cap` true for a cell that was never passed in.
    That entry lowered `base`, which raised `remaining`, so the surviving real cell also came
    back wrong: `{'a': 2, 'ghost': -1}` for a total of 1.
    """
    assert integerize({"a": 1.0}, 1, upper={"a": None, "ghost": -1}) == {"a": 1}


def test_the_remainder_order_is_taken_above_the_effective_floor() -> None:
    """Largest-remainder is only largest-remainder if the remainder is measured from the floor used.

    `a`'s floor is raised to its lower bound of 2, which already consumes its 0.9 fraction, so it
    has no claim on the spare unit -- but the raw fractional part still sorted it first and it
    took the unit anyway, leaving `b` at 0 despite a 0.8 remainder.
    """
    assert integerize({"a": 0.9, "b": 0.8}, 3, lower={"a": 2}) == {"a": 2, "b": 1}
