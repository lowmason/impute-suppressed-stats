"""The SRC-QCEW-006 universe check and the SRC-QCEW-007 alignment check, in code.

Stage 0 produced the branch verdict -- `decline`, because every one of the window's 96 testable
months carries at least one suppressed states+DC cell, leaving the employment identity untestable
on a complete published state sum. This module does not re-derive that verdict. It measures the
per-month facts Stage 2 needs in order to build constraints at all, and it refuses to describe a
month with an incomplete state sum as one where an identity was evaluated.
"""

from __future__ import annotations

import polars as pl

from ..constants import NATIONAL_AREA, STATE_AREAS
from ..errors import ConceptViolationError


def state_universe_report(frame: pl.DataFrame) -> dict[str, object]:
    """Per-month universe facts: suppressed state cells, non-state areas, national row presence.

    Every per-month mapping is keyed by every month in the frame, including the months with
    nothing to report. A month absent from `suppressed_state_cells_by_month` would read as "no
    suppressed cells" to a caller reaching for it with `.get`, which is the opposite of what its
    absence would mean.
    """
    states = frame.filter(pl.col("area_fips").is_in(list(STATE_AREAS)))
    months = sorted(frame["reference_month"].unique().to_list())
    counted = {
        row["reference_month"]: row["len"]
        for row in states.filter(pl.col("observation_status") == "suppressed")
        .group_by("reference_month")
        .len()
        .iter_rows(named=True)
    }
    suppressed_by_month = {m: counted.get(m, 0) for m in months}
    national_months = set(
        frame.filter(pl.col("area_fips") == NATIONAL_AREA)["reference_month"].unique().to_list()
    )
    # Two independent reasons a month cannot be evaluated, and the report keeps them apart: a
    # state sum that is incomplete because a cell is suppressed, and a missing national row to
    # compare it against.
    evaluable = [m for m in months if suppressed_by_month[m] == 0 and m in national_months]
    outside = sorted(set(frame["area_fips"].unique().to_list()) - STATE_AREAS - {NATIONAL_AREA})
    return {
        "months": months,
        "suppressed_state_cells_by_month": suppressed_by_month,
        "non_state_areas_present": outside,
        "national_row_present_by_month": {m: (m in national_months) for m in months},
        "identity_evaluable_months": evaluable,
        "months_with_a_complete_state_sum": len(evaluable),
    }


def assert_definitional_alignment(frame: pl.DataFrame) -> None:
    """Halt unless national and state rows share industry, ownership and NAICS vintage.

    SRC-QCEW-007 requires this *before* a constraint is created, which is why it lives here rather
    than inside Stage 2's builder: a misaligned pair must never reach the point where it could
    become a hard equation.

    A frame missing either level returns without complaint. That is not a pass: with only one
    level present there is no pair to align, and the caller that needs a national control is the
    one that must notice its absence -- `state_universe_report` reports it per month.
    """
    national = frame.filter(pl.col("area_type") == "national")
    state = frame.filter(pl.col("area_type") == "state")
    if national.is_empty() or state.is_empty():
        return
    for column in ("industry_code", "ownership_code", "naics_vintage"):
        left = set(national[column].unique().to_list())
        right = set(state[column].unique().to_list())
        if left != right:
            raise ConceptViolationError(
                f"national and state rows disagree on {column}: {sorted(left)} vs {sorted(right)}; "
                "refusing to treat them as definitionally aligned (SRC-QCEW-007)"
            )
