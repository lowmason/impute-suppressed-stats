"""§17.6 golden comparison: exact everywhere except the last ulps of a Float64 value.

WHY NOT `.equals`. Both float goldens were written on an arm64 Mac, and a Linux runner cannot
reproduce their last ulps however the code is written: measured 2026-09-13 on ubuntu-latest
(diagnostic run 34764717606), OpenBLAS's `x.T @ y` and `solve`, glibc's `exp`/`log` and `np.dot`
all disagree with Accelerate and Apple's libm in the last bits, which moves
`constrained_regression`'s weights by up to 1.5e-14 relative and every CRPS that `np.dot` feeds.
No integer, count or coverage value moved. An exact comparison therefore tests the machine, not
the change.

WHY THESE TOLERANCES. `REL_TOL = 1e-12` sits two orders above the measured drift and orders below
anything a golden exists to catch -- a corrupt source column or a CBP vintage moves an intensity
by percent, not by ppt. `ABS_TOL = 1e-9` exists for values that ARE round-off:
`anchor_adding_up_max_abs` is 0.0 on one platform and 1e-12 on the other, so relative distance is
1.0 there. Both are in employees or unitless ratios, where 1e-9 means nothing.

WHAT STAYS EXACT, AND WHY IT MATTERS. Every non-Float64 column -- keys, strings, `estimate_integer`,
every count -- plus the schema, the row count, and a float's null-ness, NaN-ness and infinities. A
null is "no estimate" and 0.0 is "estimated zero", so no tolerance joins them. A §12.6 integer that
flips on another platform is a real difference in a released number, and this comparator reddens on
it rather than absorbing it.

Rows are compared POSITIONALLY. The caller puts both frames into one total order first, exactly as
the exact tests did; a misalignment then shows up as a key-column mismatch, which is exact.
"""

from __future__ import annotations

import polars as pl

REL_TOL = 1e-12
ABS_TOL = 1e-9
_SHOWN = 5


def assert_matches_golden(produced: pl.DataFrame, golden: pl.DataFrame) -> None:
    """Raise AssertionError naming every column that differs beyond the §17.6 tolerance."""
    assert produced.schema == golden.schema, (
        f"schema differs: produced {produced.schema} vs golden {golden.schema}"
    )
    assert produced.height == golden.height, (
        f"rows differ: produced {produced.height} vs golden {golden.height}"
    )
    # Side by side, produced as `a_<name>` and golden as `b_<name>`; heights are equal by now.
    side = produced.select(pl.all().name.prefix("a_")).hstack(
        golden.select(pl.all().name.prefix("b_"))
    )
    problems: list[str] = []
    for name, dtype in produced.schema.items():
        mismatch = _float_mismatch(name) if dtype == pl.Float64 else _exact_mismatch(name)
        rows = side.with_row_index("row").filter(mismatch).select("row", f"a_{name}", f"b_{name}")
        if rows.height:
            problems.append(f"{name}: {rows.height} row(s) differ, e.g.\n{rows.head(_SHOWN)}")
    assert not problems, "golden mismatch beyond tolerance:\n" + "\n".join(problems)


def _exact_mismatch(name: str) -> pl.Expr:
    """Differs unless equal or both null (`ne_missing` treats null == null as equal)."""
    return pl.col(f"a_{name}").ne_missing(pl.col(f"b_{name}"))


def _float_mismatch(name: str) -> pl.Expr:
    """Null-ness, NaN-ness and infinities exact; finite pairs within max(ABS_TOL, REL_TOL * scale)."""
    a, b = pl.col(f"a_{name}"), pl.col(f"b_{name}")
    null_differs = a.is_null() != b.is_null()
    nan_differs = a.is_nan() != b.is_nan()
    both_finite = a.is_finite() & b.is_finite()
    # An infinity matches only the same infinity; NaN pairs are settled by `nan_differs`.
    infinite_differs = ~both_finite & ~(a.is_nan() & b.is_nan()) & a.ne(b)
    scale = pl.max_horizontal(a.abs(), b.abs())
    too_far = both_finite & ((a - b).abs() > pl.max_horizontal(pl.lit(ABS_TOL), REL_TOL * scale))
    # `is_null` never yields null; the other terms do on a null input, where `null_differs` decides.
    return null_differs | (nan_differs | infinite_differs | too_far).fill_null(False)
