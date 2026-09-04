# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Test the QCEW state/national universe and return the SRC-QCEW-006 branch verdict.

The decision rule (`classify_identity`) is a pure function of two comparison tables and is
tested on toy panels before it ever sees real data -- see tests/audit/test_identity_rule.py.
Thresholds come from the plan's Global Constraints and are recorded, with their provenance and
their hand-authored parts labelled, in the `decision_thresholds` findings key.

Establishment counts carry the geography question and employment counts carry the suppression
question, which is why the rule tests them in that order: `qtrly_estabs` is asked whether the
state universe exhausts the national universe, and only once that is settled are the employment
columns asked how much suppression is hiding.

**Containment is measured, not assumed.** `national - states_dc - other` presupposes that a
non-state area the panel carries is a component *of* the national total. That is exactly what
Sec 8.1 asks to be verified ("if the national total includes areas outside the configured state
universe"), so `measure_containment` settles it from establishment counts before either
comparison table subtracts anything, and records what it found. A non-state area measured to sit
outside the national total is not a residual component of it, and subtracting it would
manufacture a gap where the identity in fact closes.

Two null conventions, and they are deliberately different on the two sides of the comparison:

* The **states+DC** side sums published values and skips what is not published. A suppressed
  state cell therefore contributes nothing, which makes `states_dc_emp` a lower bound on the
  true state sum and makes a positive `emp_gap` the residual Stage 3 would allocate. That is
  the intended reading, not a defect.
* The **reference** side -- the national total and any non-state area inside it -- keeps "not
  published" distinct from "zero". Summing an unpublished reference term to `0` would be
  indistinguishable from a published zero and would manufacture a gap out of a missing value. A
  period whose reference term is unpublished is unevaluable, and the rule says so rather than
  passing it.

The second convention matters because `Series.all()` skips nulls by default: `(col == 0).all()`
over a column with a null returns `True`. Every check below counts its nulls explicitly instead.
"""

from __future__ import annotations

from typing import Any

import polars as pl

import _common as c

SOURCE = "qcew_identity"

# Panel `area_class` labels (Task 4). Audit scripts do not import one another, so these are
# repeated here rather than shared; the panel's schema check is what keeps them honest.
NATIONAL = "national"
STATES_DC = "states_dc"
OTHER = "other_state_level"

QUARTER_KEYS = ["year", "qtr"]
MONTH_KEYS = ["year", "month"]

# The two comparison-table contracts. `classify_identity` reads nothing outside these, so the
# rule can be exercised on toy frames that never touch the panel.
QUARTER_COLUMNS = ("year", "qtr", "national_estabs", "states_dc_estabs", "other_estabs",
                   "estab_gap", "estab_gap_after_other")
MONTH_COLUMNS = ("year", "month", "national_emp", "states_dc_emp", "other_emp", "emp_gap",
                 "emp_gap_after_other", "n_states_suppressed")

# What gets persisted: the rule's columns plus the as-published non-state amount. `other_estabs`
# and `other_emp` are containment-adjusted (see `comparison_tables`), so on an `outside` verdict
# they are 0 in every row even where a non-state area published a count. Persisting the adjusted
# column alone would tell a Stage 3 reader of `quarter_table` that the panel carries no non-state
# establishments at all, which is false; the sibling column carries what was actually published.
QUARTER_PERSISTED_COLUMNS = (*QUARTER_COLUMNS, "other_estabs_published")
MONTH_PERSISTED_COLUMNS = (*MONTH_COLUMNS, "other_emp_published")

SUPPRESSION_CODE_MEANING = "suppressed"

# Where a non-state area sits relative to the national total, as measured from establishments.
INSIDE = "inside_national_total"
OUTSIDE = "outside_national_total"
INDETERMINATE = "indeterminate"
NO_OTHER_AREA = "no_non_state_area_present"

# Hand-authored, and labelled as such where it is persisted. Held as a module constant so the
# marking travels with the text and cannot be separated from it by an edit to `main`.
DECISION_THRESHOLDS_NOTE = (
    "Decision thresholds for SRC-QCEW-006. SCOPE MARKER, OPENING: every sentence in this "
    "findings key, from here to the closing scope marker, is hand-authored. It records where "
    "this script's two thresholds come from; it states nothing this run measured, it is the "
    "only wholly hand-authored key in this summary, and its scope does not extend past its own "
    "closing marker to any neighbouring key. This script fetches nothing, so none of the text "
    "here carries an extract hash and no later run re-checks any of it. Threshold one, "
    "tolerance: 'equals' means exact integer equality, tolerance 0, on the stated ground that "
    "QCEW monthly employment and quarterly establishment counts are integer counts of jobs and "
    "of establishments; classify_identity therefore compares gaps to 0 and never to a band, "
    "and no numerical confidentiality threshold is encoded anywhere in this script. Threshold "
    "two, branch assignment: a gap that closes only after subtracting non-state areas present "
    "in the national universe is classified residual_cells rather than enforce. That rests on "
    "one quotation, reproduced verbatim from specs/logging-employment-spec.md section 3.2: 'A "
    "national control MUST NOT be imposed on a state universe that omits components included "
    "in the national total.' The step from that quotation to the residual_cells branch is an "
    "inference and is hand-authored: the quotation forbids imposing a national control on a "
    "universe missing national components, and the reading applied here is that a states+DC "
    "universe which excludes a non-state area the national total includes is exactly such a "
    "universe, so the area must enter as an explicit residual cell instead of being controlled "
    "away. The quotation does not name the branch, and no measurement in this run carries that "
    "step. The same reading is what makes containment worth measuring rather than assuming: "
    "the quotation is conditioned on components 'included in the national total', so an area "
    "measured to sit outside that total is not what it governs. Both thresholds were set as "
    "defaults by the Stage 0 plan's Global Constraints and confirmed at handoff before "
    "classify_identity was written. SCOPE MARKER, CLOSING: end of the hand-authored text; "
    "every other findings key in this summary is computed from the panel this run read, and "
    "the one inference among them carries its own inline marker."
)


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...], label: str) -> None:
    """A missing column is a construction bug, not a data condition, so it raises rather than
    resolving to a branch. A null *inside* a present column is the opposite: a real statement
    that a value was not published, handled by the evaluable/testable partitions below."""
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ValueError(f"{label} table is missing required column(s): {', '.join(missing)}")


def _opt_int(value: Any) -> int | None:
    """Keep an unmeasured extremum null. `int(value or 0)` would render it as 0, which reads in
    the evidence as a closed identity while the branch says otherwise."""
    return None if value is None else int(value)


def _has_nonzero_or_unpublished(series: pl.Series) -> bool:
    """A non-state area counts as present *to the rule* if it contributes a non-zero amount to
    the national total anywhere, or if such a contribution was withheld. Areas measured to sit
    outside the national total reach the rule as zero -- see `measure_containment`."""
    return bool(series.is_null().any() or (series.fill_null(0) != 0).any())


def classify_identity(quarters: pl.DataFrame, months: pl.DataFrame) -> dict:
    """Return {'branch', 'reason', 'evidence'} with branch in enforce/residual_cells/decline.

    `quarters` and `months` must carry QUARTER_COLUMNS and MONTH_COLUMNS. A null in a `*_gap_*`
    column means the period's reference term was not published, so the period is unevaluable
    (quarters) or untestable (months) rather than passing or failing.
    """
    _require_columns(quarters, QUARTER_COLUMNS, "quarters")
    _require_columns(months, MONTH_COLUMNS, "months")

    evaluable = quarters.filter(pl.col("estab_gap_after_other").is_not_null())
    n_unevaluable = quarters.height - evaluable.height
    n_closing = evaluable.filter(pl.col("estab_gap_after_other") == 0).height
    estab_closes = evaluable.height == quarters.height > 0 and n_closing == evaluable.height

    testable = months.filter(pl.col("emp_gap_after_other").is_not_null())
    n_untestable = months.height - testable.height
    n_negative = testable.filter(pl.col("emp_gap_after_other") < 0).height

    clean = testable.filter(pl.col("n_states_suppressed") == 0)
    n_clean_closing = clean.filter(pl.col("emp_gap_after_other") == 0).height
    clean_closes = clean.height > 0 and n_clean_closing == clean.height

    max_estab_gap = _opt_int(evaluable["estab_gap_after_other"].abs().max())
    min_emp_gap = _opt_int(testable["emp_gap_after_other"].min())
    max_clean_gap = _opt_int(clean["emp_gap_after_other"].abs().max())

    evidence = {
        "estab_identity_closes_after_other_areas": estab_closes,
        "other_areas_present": (_has_nonzero_or_unpublished(quarters["other_estabs"])
                                or _has_nonzero_or_unpublished(months["other_emp"])),
        "employment_residual_never_negative": n_negative == 0,
        "clean_months": int(clean.height),
        "clean_months_close": clean_closes,
        "max_estab_gap_after_other": max_estab_gap,
        "min_emp_gap_after_other": min_emp_gap,
        "quarters_total": int(quarters.height),
        "quarters_evaluable": int(evaluable.height),
        "quarters_unevaluable": int(n_unevaluable),
        "quarters_closing": int(n_closing),
        "months_total": int(months.height),
        "testable_months": int(testable.height),
        "untestable_months": int(n_untestable),
        "clean_months_closing": int(n_clean_closing),
        "negative_residual_months": int(n_negative),
        "max_abs_clean_emp_gap": max_clean_gap,
    }

    def decided(branch: str, reason: str) -> dict:
        return {"branch": branch, "reason": reason, "evidence": evidence}

    if evaluable.height != quarters.height or quarters.height == 0:
        return decided("decline", (
            f"only {evaluable.height} of {quarters.height} quarter(s) carry an evaluable "
            f"establishment gap, because a reference establishment count is unpublished in the "
            f"other {n_unevaluable}, so the state universe cannot be shown to exhaust the "
            f"national universe"))
    if not estab_closes:
        return decided("decline", (
            f"the establishment gap after non-state areas is non-zero in "
            f"{evaluable.height - n_closing} of {evaluable.height} evaluable quarter(s), "
            f"reaching {max_estab_gap} in absolute value, so the national universe is not "
            f"explained by the configured state geography"))
    if n_negative:
        return decided("decline", (
            f"{n_negative} of {testable.height} testable month(s) carry a negative employment "
            f"residual after non-state areas, the smallest being {min_emp_gap}, which no amount "
            f"of state suppression can produce and which therefore indicates a definitional "
            f"mismatch rather than a withheld cell"))
    if testable.height == 0:
        return decided("decline", (
            f"none of the {months.height} month(s) carries both a published national and a "
            f"published non-state employment value, so the employment identity is untestable "
            f"on published values"))
    if clean.height == 0:
        return decided("decline", (
            f"every one of the {testable.height} testable month(s) carries at least one "
            f"{SUPPRESSION_CODE_MEANING} state cell, so the employment identity is untestable "
            f"on a complete published state sum"))
    if not clean_closes:
        return decided("decline", (
            f"the employment gap after non-state areas is non-zero in "
            f"{clean.height - n_clean_closing} of the {clean.height} month(s) with no "
            f"{SUPPRESSION_CODE_MEANING} state cell, reaching {max_clean_gap} in absolute "
            f"value, so the national total is not the sum of the state universe in an "
            f"unsuppressed month"))
    if evidence["other_areas_present"]:
        return decided("residual_cells", (
            f"the identity closes across all {evaluable.height} quarter(s) and all "
            f"{clean.height} unsuppressed month(s) only once the non-state areas the panel "
            f"carries are subtracted, so those areas have to enter as explicit residual cells "
            f"rather than be controlled away"))
    return decided("enforce", (
        f"the national total equals the states+DC published sum exactly across all "
        f"{evaluable.height} quarter(s) and all {clean.height} month(s) with no "
        f"{SUPPRESSION_CODE_MEANING} state cell, with no non-state area contributing a value"))


def _published_sum(frame: pl.DataFrame, keys: list[str], value: str, alias: str) -> pl.DataFrame:
    """The states+DC side: sum what was published and skip what was not."""
    return frame.group_by(keys).agg(pl.col(value).sum().cast(pl.Int64).alias(alias))


def _reference_parts(
    frame: pl.DataFrame, keys: list[str], value: str, alias: str
) -> pl.DataFrame:
    """The reference side: carry the sum *and* the count of unpublished cells, so the join
    below can tell 'this area published nothing here' from 'this area is absent here'."""
    return frame.group_by(keys).agg(
        pl.col(value).sum().cast(pl.Int64).alias(f"_{alias}_sum"),
        pl.col(value).null_count().cast(pl.Int64).alias(f"_{alias}_unpublished"),
    )


def _resolve_reference(alias: str, when_absent: int | None) -> pl.Expr:
    """Absent group -> `when_absent`; present but with an unpublished cell -> null."""
    return (
        pl.when(pl.col(f"_{alias}_unpublished").is_null())
        .then(pl.lit(when_absent, pl.Int64))
        .when(pl.col(f"_{alias}_unpublished") > 0)
        .then(pl.lit(None, pl.Int64))
        .otherwise(pl.col(f"_{alias}_sum"))
        .cast(pl.Int64)
        .alias(alias)
    )


def quarterly_estabs(panel: pl.DataFrame) -> pl.DataFrame:
    """One establishment row per (area, year, quarter).

    `qtrly_estabs` is a quarterly figure repeated across the three monthly rows each quarter
    expands into. Rather than trusting that repetition, it is asserted: a quarter whose three
    monthly rows disagreed would make every establishment sum below quietly wrong, so it fails
    here instead.
    """
    keys = ["area_fips", *QUARTER_KEYS]
    collapsed = panel.group_by(keys).agg(
        pl.col("area_class").first(),
        pl.col("qtrly_estabs").first(),
        pl.col("qtrly_estabs").n_unique().alias("_distinct"),
    )
    disagreeing = collapsed.filter(pl.col("_distinct") > 1).height
    if disagreeing:
        raise ValueError(
            f"qtrly_estabs varies within {disagreeing} (area_fips, year, qtr) group(s); the "
            "establishment comparison assumes one quarterly value per area-quarter"
        )
    return collapsed.drop("_distinct")


def _by_class(frame: pl.DataFrame, area_class: str) -> pl.DataFrame:
    return frame.filter(pl.col("area_class") == area_class)


def raw_quarter_table(estabs: pl.DataFrame) -> pl.DataFrame:
    """National, states+DC and non-state establishment counts per quarter, before any
    subtraction. `estab_gap` here is the raw `national - states_dc`; nothing is netted out of it
    until containment has been measured."""
    return (
        estabs.select(QUARTER_KEYS).unique()
        .join(_reference_parts(_by_class(estabs, NATIONAL), QUARTER_KEYS,
                               "qtrly_estabs", "national_estabs"), on=QUARTER_KEYS, how="left")
        .join(_published_sum(_by_class(estabs, STATES_DC), QUARTER_KEYS,
                             "qtrly_estabs", "states_dc_estabs"), on=QUARTER_KEYS, how="left")
        .join(_reference_parts(_by_class(estabs, OTHER), QUARTER_KEYS,
                               "qtrly_estabs", "other_published"), on=QUARTER_KEYS, how="left")
        .with_columns(
            # A missing national row means no national total was published for that quarter,
            # which is unevaluable -- not zero. A missing non-state group means no such area
            # exists that quarter, which genuinely contributes zero.
            _resolve_reference("national_estabs", None),
            _resolve_reference("other_published", 0),
            pl.col("states_dc_estabs").fill_null(0),
        )
        .with_columns(estab_gap=pl.col("national_estabs") - pl.col("states_dc_estabs"))
        .select([*QUARTER_KEYS, "national_estabs", "states_dc_estabs", "other_published",
                 "estab_gap"])
        .sort(QUARTER_KEYS)
    )


def measure_containment(raw: pl.DataFrame) -> dict:
    """Settle whether the panel's non-state areas are components of the national total.

    Sec 8.1 asks the system to verify the state/national universe rather than assume it, and
    this is that step. It is decided on establishment counts, which survive suppression far
    better than employment does, and only on the quarters where a non-state area actually
    publishes a non-zero count -- a quarter contributing nothing cannot discriminate, since
    `estab_gap == other == 0` satisfies both readings at once.
    """
    testable = raw.filter(
        pl.col("estab_gap").is_not_null()
        & pl.col("other_published").is_not_null()
        & (pl.col("other_published") != 0)
    )
    n_inside = testable.filter(pl.col("estab_gap") == pl.col("other_published")).height
    n_outside = testable.filter(pl.col("estab_gap") == 0).height

    if testable.height == 0:
        verdict = NO_OTHER_AREA
    elif n_inside == testable.height:
        verdict = INSIDE
    elif n_outside == testable.height:
        verdict = OUTSIDE
    else:
        verdict = INDETERMINATE

    return {
        "verdict": verdict,
        "quarters_discriminating": int(testable.height),
        "quarters_gap_equals_non_state_amount": int(n_inside),
        "quarters_gap_is_zero": int(n_outside),
        "quarters_non_state_amount_unpublished": int(
            raw.filter(pl.col("other_published").is_null()).height
        ),
        "subtraction_applied": verdict in (INSIDE, INDETERMINATE),
        "basis": (
            f"measured on {testable.height} quarter(s) in which a non-state area publishes a "
            f"non-zero establishment count: national minus states+DC equals that area's own "
            f"count in {n_inside} of them and equals 0 in {n_outside} of them, giving the "
            f"verdict {verdict}, on which the non-state amount is "
            f"{'subtracted from' if verdict in (INSIDE, INDETERMINATE) else 'left out of'} both "
            f"comparison tables' gap columns"
        ),
        "per_quarter": raw.filter(pl.col("other_published").fill_null(-1) != 0).to_dicts(),
    }


def comparison_tables(panel: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """Build the quarter and month comparison tables the rule reads, plus what was measured
    about non-state containment on the way.

    Both tables are indexed by the periods the *panel* covers, not by the national rows, so a
    period with no national row surfaces as an unevaluable period rather than vanishing.

    `other_estabs` and `other_emp` as handed to the rule are the non-state amounts *inside the
    national total*: the published amount where containment measured `inside` (or could not be
    settled, which leaves the gap to fail the rule's first gate rather than be quietly closed),
    and 0 where it measured `outside`. Both tables also carry an `*_published` sibling column
    holding the amount as published, so the zeroing is visible in the tables themselves and not
    only in the `non_state_area_containment` finding.
    """
    estabs = quarterly_estabs(panel)
    raw = raw_quarter_table(estabs)
    containment = measure_containment(raw)
    subtract = containment["subtraction_applied"]

    quarters = (
        raw.with_columns(
            other_estabs=pl.col("other_published") if subtract else pl.lit(0, pl.Int64)
        )
        .with_columns(estab_gap_after_other=pl.col("estab_gap") - pl.col("other_estabs"))
        .rename({"other_published": "other_estabs_published"})
        .select(QUARTER_PERSISTED_COLUMNS)
        .sort(QUARTER_KEYS)
    )

    suppressed_states = (
        _by_class(panel, STATES_DC).filter(pl.col("suppressed"))
        .group_by(MONTH_KEYS).agg(pl.len().cast(pl.Int64).alias("n_states_suppressed"))
    )
    months = (
        panel.select(MONTH_KEYS).unique()
        .join(_reference_parts(_by_class(panel, NATIONAL), MONTH_KEYS, "emplvl", "national_emp"),
              on=MONTH_KEYS, how="left")
        .join(_published_sum(_by_class(panel, STATES_DC), MONTH_KEYS, "emplvl", "states_dc_emp"),
              on=MONTH_KEYS, how="left")
        .join(_reference_parts(_by_class(panel, OTHER), MONTH_KEYS, "emplvl", "other_published"),
              on=MONTH_KEYS, how="left")
        .join(suppressed_states, on=MONTH_KEYS, how="left")
        .with_columns(
            _resolve_reference("national_emp", None),
            _resolve_reference("other_published", 0),
            pl.col("states_dc_emp").fill_null(0),
            pl.col("n_states_suppressed").fill_null(0),
        )
        .with_columns(
            other_emp=pl.col("other_published") if subtract else pl.lit(0, pl.Int64)
        )
        .with_columns(emp_gap=pl.col("national_emp") - pl.col("states_dc_emp"))
        .with_columns(emp_gap_after_other=pl.col("emp_gap") - pl.col("other_emp"))
        .rename({"other_published": "other_emp_published"})
        .select(MONTH_PERSISTED_COLUMNS)
        .sort(MONTH_KEYS)
    )
    return quarters, months, containment


def _period_label(frame: pl.DataFrame) -> str:
    """'2017-01 through 2024-12', from the months the panel actually carries."""
    ordered = frame.sort(MONTH_KEYS)
    first, last = ordered.row(0, named=True), ordered.row(-1, named=True)
    return f"{first['year']}-{first['month']:02d} through {last['year']}-{last['month']:02d}"


def structural_findings(panel: pl.DataFrame, estabs: pl.DataFrame) -> dict:
    """Panel properties the rule's two tables cannot express, all computed from this panel.

    These exist so the verdict can be read against the shape of its input: how many states+DC
    areas each month carries, whether an unpublished employment value is always a
    `suppressed`-flagged one, and how many cells on each side were withheld.
    """
    states = _by_class(panel, STATES_DC)
    per_month = states.group_by(MONTH_KEYS).agg(
        pl.col("area_fips").n_unique().alias("n_areas"),
        pl.col("suppressed").sum().alias("n_suppressed"),
    )
    n_areas, n_months = states["area_fips"].n_unique(), panel.select(MONTH_KEYS).n_unique()

    unpublished_emp = states.filter(pl.col("emplvl").is_null()).height
    flagged = states.filter(pl.col("suppressed")).height
    both = states.filter(pl.col("emplvl").is_null() & pl.col("suppressed")).height

    others = (
        _by_class(panel, OTHER)
        .group_by("area_fips", "area_title")
        .agg(pl.len().cast(pl.Int64).alias("area_months"))
        .sort("area_fips")
        .to_dicts()
    )
    short_span = (
        states.group_by("area_fips", "area_title").agg(pl.len().cast(pl.Int64).alias("months"))
        .filter(pl.col("months") < n_months).sort("area_fips").to_dicts()
    )
    national, other = _by_class(panel, NATIONAL), _by_class(panel, OTHER)
    nat_estabs, other_estabs = _by_class(estabs, NATIONAL), _by_class(estabs, OTHER)

    return {
        "panel_rows": int(panel.height),
        "rows_by_area_class": dict(
            panel.group_by("area_class").len().sort("area_class").iter_rows()
        ),
        "months_covered": int(n_months),
        "quarters_covered": int(panel.select(QUARTER_KEYS).n_unique()),
        "states_dc_areas": int(n_areas),
        "states_dc_areas_per_month": {
            "min": int(per_month["n_areas"].min()), "max": int(per_month["n_areas"].max()),
            "constant": bool(per_month["n_areas"].min() == per_month["n_areas"].max()),
        },
        "states_dc_suppressed_per_month": {
            "min": int(per_month["n_suppressed"].min()),
            "max": int(per_month["n_suppressed"].max()),
        },
        "states_dc_area_months_absent": int(n_areas * n_months - states.height),
        "states_dc_short_span_areas": short_span,
        "states_dc_suppressed_cells": int(flagged),
        "states_dc_unpublished_emp_cells": int(unpublished_emp),
        "states_dc_unpublished_emp_is_exactly_suppressed": bool(
            unpublished_emp == flagged == both
        ),
        "states_dc_unpublished_estab_cells": int(
            _by_class(estabs, STATES_DC).filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "national_months_unpublished_emp": int(national.filter(pl.col("emplvl").is_null()).height),
        "national_quarters_unpublished_estabs": int(
            nat_estabs.filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "national_months_present": int(national.height),
        "national_quarters_present": int(nat_estabs.height),
        "other_state_level_areas": others,
        "other_months_unpublished_emp": int(other.filter(pl.col("emplvl").is_null()).height),
        "other_quarters_unpublished_estabs": int(
            other_estabs.filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "qtrly_estabs_constant_within_area_quarter": True,
    }


def absent_state_months_note(structural: dict, evidence: dict) -> str:
    """Why a states+DC area-month with no published row is read as a true zero. The counts are
    computed; the reading drawn from them is not, and is marked inline as such."""
    areas = ", ".join(
        f"{a['area_title'] or a['area_fips']} ({a['months']} month(s))"
        for a in structural["states_dc_short_span_areas"]
    ) or "none"
    per_month = structural["states_dc_areas_per_month"]
    return (
        f"Absent states+DC area-months, measured: {structural['states_dc_area_months_absent']} "
        f"of the {structural['states_dc_areas']} x {structural['months_covered']} possible "
        f"area-month cells carry no row at all, and each month carries between "
        f"{per_month['min']} and {per_month['max']} of the {structural['states_dc_areas']} "
        f"areas. The area(s) whose span is shorter than the panel's: {areas}. Also measured: "
        f"the establishment gap after non-state areas is exactly zero in "
        f"{evidence['quarters_closing']} of {evidence['quarters_evaluable']} evaluable "
        f"quarter(s). INFERENCE MARKER, OPENING: what follows to the closing marker is a "
        f"reading of those two measurements, not a third measurement, is supplied by hand, "
        f"carries no extract hash and is re-checked by no later run. An area-month with no "
        f"published row is read here as a true zero rather than as a hidden value, on the "
        f"ground that an area adding zero establishments to a quarterly total that closes "
        f"exactly can add no employment in that quarter's months; on that reading the varying "
        f"per-month area count above does not undercut the state sum. INFERENCE MARKER, "
        f"CLOSING."
    )


def ownership_scope() -> str:
    """The ownership this verdict covers, read rather than asserted.

    Naming the scope matters -- a verdict about the national identity is a verdict about one
    ownership slice of it -- but writing the word into the sentence would state a scope fact this
    run never checked: a re-run against a panel built on a different ownership filter would print
    it unchanged. So the code comes from `qcew_codes.findings.private_own_code`, the title from
    the ownership titles file that task fetched (which carries an extract hash), and the pairing
    is checked against the predicate the panel actually applied before either is used.
    """
    codes = c.load_summary("qcew_codes")
    own_code = codes["findings"]["private_own_code"]
    titles_path = next(e["path"] for e in codes["extracts"]
                       if e["path"].endswith("titles/own_code.csv"))
    titles = pl.read_csv(titles_path, infer_schema_length=0)
    title = dict(zip(titles[titles.columns[0]].to_list(),
                     titles[titles.columns[1]].to_list(), strict=True))[own_code]

    predicates = c.load_summary("qcew_panel")["findings"]["filter_predicates"]
    if not any(p.startswith(f"own_code == '{own_code}'") for p in predicates):
        raise ValueError(
            f"qcew_codes gives private_own_code {own_code!r}, but no qcew_panel filter predicate "
            f"applied it; the ownership scope of this verdict cannot be stated"
        )
    return f"own_code {own_code} ('{title}')"


def geography_reading(result: dict, quarters: pl.DataFrame) -> str:
    """`geography_universe_explains_gap` is a conjunction, so it is false both when geography
    fails to explain a gap and when there is no gap for geography to explain. Those are opposite
    findings, and Stage 3 reads this key, so the run states which case it is in."""
    evidence = result["evidence"]
    gaps = sorted(int(v) for v in quarters["estab_gap"].drop_nulls().unique())
    return (
        f"Reading of geography_universe_explains_gap, whose value this run is "
        f"{evidence['other_areas_present'] and evidence['estab_identity_closes_after_other_areas']}"
        f": the key is the conjunction of other_areas_present "
        f"({evidence['other_areas_present']}) with estab_identity_closes_after_other_areas "
        f"({evidence['estab_identity_closes_after_other_areas']}), so a false value can mean "
        f"either that geography leaves a gap unexplained or that no gap arose for geography to "
        f"explain. Which of the two this run found, from the raw comparison rather than from "
        f"the conjunction: national minus states+DC establishments takes the value(s) {gaps} "
        f"across the {quarters.height} quarter(s) in the panel, and non-state containment was "
        f"measured separately in non_state_area_containment."
    )


def _clean_month_clause(evidence: dict, months: pl.DataFrame) -> str:
    """The employment clause of the verdict, stating counts rather than an outcome so that no
    wording is shared between two branches that would read as a claim in one of them.

    The suppressed-cell range is taken over the *testable* months, because that is what the
    clause attributes it to. `panel_structure.states_dc_suppressed_per_month` ranges over every
    month in the panel, which is a different population whenever some month is untestable.
    """
    if evidence["testable_months"] == 0:
        return (f"none of the {evidence['months_total']} month(s) carries both a published "
                f"national and a published non-state employment value")
    testable = months.filter(pl.col("emp_gap_after_other").is_not_null())
    if evidence["clean_months"] == 0:
        return (f"each of the {evidence['testable_months']} testable month(s) carries between "
                f"{int(testable['n_states_suppressed'].min())} and "
                f"{int(testable['n_states_suppressed'].max())} {SUPPRESSION_CODE_MEANING} "
                f"states+DC cells and an employment gap after non-state areas of at least "
                f"{evidence['min_emp_gap_after_other']}")
    return (f"in {evidence['clean_months_closing']} of the {evidence['clean_months']} testable "
            f"month(s) carrying no {SUPPRESSION_CODE_MEANING} states+DC cell the employment "
            f"gap after non-state areas is exactly zero, its largest absolute value being "
            f"{evidence['max_abs_clean_emp_gap']}")


def build_verdict_sentence(
    result: dict, structural: dict, containment: dict, months: pl.DataFrame,
    span: str, ownership: str
) -> str:
    """One sentence, every figure in it interpolated from this run's tables.

    `quarters_closing` counts quarters where `estab_gap_after_other` is 0, so the sentence says
    "after subtracting" exactly when a subtraction was applied. Stating it unconditionally would
    be false on an `outside` verdict, and omitting it unconditionally would be false on an
    `inside` one.
    """
    evidence = result["evidence"]
    others = structural["other_state_level_areas"]
    names = ", ".join(o["area_title"] or o["area_fips"] for o in others) or "none"
    subtracted = (" after subtracting the non-state amount measured inside it"
                  if containment["subtraction_applied"] else "")
    return (
        f"{result['branch']}: across the {evidence['quarters_total']} quarter(s) and "
        f"{evidence['months_total']} month(s) the panel covers ({span}), the national "
        f"{c.INDUSTRY_CODE} establishment count for {ownership} equals the states+DC published "
        f"sum{subtracted} in {evidence['quarters_closing']} of "
        f"{evidence['quarters_evaluable']} evaluable quarter(s), with "
        f"{evidence['quarters_unevaluable']} unevaluable and "
        f"{structural['states_dc_unpublished_estab_cells']} states+DC establishment cell(s) "
        f"unpublished; the panel carries {len(others)} non-state area(s) ({names}) across "
        f"{sum(o['area_months'] for o in others)} area-month(s), measured as "
        f"{containment['verdict']} on {containment['quarters_discriminating']} discriminating "
        f"quarter(s); {_clean_month_clause(evidence, months)}; {result['reason']}."
    )


def assert_one_sentence(sentence: str) -> None:
    """The stage exit criterion reads `verdict_sentence` as exactly one sentence. An area title
    carrying an internal full stop would break that silently, so it breaks loudly here."""
    if sentence.count(".") != 1 or not sentence.endswith("."):
        raise ValueError(f"verdict_sentence must be exactly one sentence, got: {sentence}")


def coverage_span(months: pl.DataFrame) -> dict[str, str]:
    """Derived from the months the panel carries, against the D1 window."""
    ordered = months.sort(MONTH_KEYS)
    labels = [f"{y}-{m:02d}" for y, m in zip(ordered["year"], ordered["month"], strict=True)]
    window = [f"{y}-{m:02d}" for y in c.WINDOW_YEARS for m in range(1, 13)]
    uncovered = [label for label in window if label not in set(labels)]
    return {
        "published_start": labels[0], "published_end": labels[-1],
        "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
        "covered": f"{labels[0]}..{labels[-1]} ({len(labels)} month(s))",
        "uncovered": ",".join(uncovered),
    }


def main() -> None:
    panel_path = next(e["path"] for e in c.load_summary("qcew_panel")["extracts"]
                      if e["path"].endswith("panel.parquet"))
    panel = pl.read_parquet(panel_path)

    quarters, months, containment = comparison_tables(panel)
    result = classify_identity(quarters, months)
    structural = structural_findings(panel, quarterly_estabs(panel))

    sentence = build_verdict_sentence(result, structural, containment, months,
                                      _period_label(months), ownership_scope())
    assert_one_sentence(sentence)

    c.write_summary(
        SOURCE,
        coverage_span=coverage_span(months),
        access={"route": f"derived from qcew_panel ({panel_path})", "status": "verified",
                "reason": None},
        extracts=[],
        findings={
            "quarter_table": quarters.to_dicts(),
            "month_table": months.to_dicts(),
            "branch": result["branch"],
            "reason": result["reason"],
            "evidence": result["evidence"],
            "verdict_sentence": sentence,
            "geography_universe_explains_gap": (
                result["evidence"]["other_areas_present"]
                and result["evidence"]["estab_identity_closes_after_other_areas"]
            ),
            "clean_months": result["evidence"]["clean_months"],
            "geography_universe_explains_gap_reading": geography_reading(result, quarters),
            "non_state_area_containment": containment,
            "panel_structure": structural,
            "absent_state_months": absent_state_months_note(structural, result["evidence"]),
            "decision_thresholds": DECISION_THRESHOLDS_NOTE,
        },
    )
    print(sentence)


if __name__ == "__main__":
    main()
