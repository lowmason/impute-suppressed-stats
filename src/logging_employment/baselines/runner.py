"""Run every §10 baseline over the window, and rank what ran by §10.8's hierarchy.

THE GATE RUNS ONCE, FOR THE WINDOW. §18.3 requires the pipeline to fail rather than guess when
source universes cannot be reconciled. A nonzero establishment gap in any month means the published
national row contains a component the state table does not, which makes every month's residual
suspect -- so this halts the run rather than declining one month and shipping the other 95.

EVERY DECLINE IS A ROW, AND EVERY ROW NAMES ITS KIND. A baseline that cannot run for a month writes
a row with a null estimate and a populated `decline_reason`, never no row at all: an absent row is
indistinguishable from a bug, and §17.4 row 4's "run every baseline on a small frozen fixture" is
satisfied by a clean decline only if the decline is visible in the output. The three situations
below -- a data problem, an estimator's considered refusal, and a reconciliation failure -- used to
produce one indistinguishable row shape. `decline_kind` separates them, because §13.5-13.8 score
against truth and define no decline metric: an estimator whose months drop out of the scored set
drops out non-randomly, and a data bug can make a baseline's WAPE look better than a correct
implementation's.

§10.8's HIERARCHY HAS FOUR RUNGS AND §10.1 IS NOT ONE OF THEM. The spec calls equal allocation a
sanity check and leaves it out of the ordering on purpose -- it ignores the establishment counts
that QCEW publishes even for suppressed cells. It still runs and is still scored; it is just never
preferred.

THAT LAST CLAUSE IS NOW ENFORCED RATHER THAN MERELY STATED. `PREFERRABLE` below is the set
`validate/scoreboard.py::preferred_baseline` ranks over, and that function is §13.10's promotion
comparand -- so an estimator outside the hierarchy cannot become the number the full model is
gated against. It stays visible through `best_scoring_baseline`, which reports the best scorer of
any kind and gates nothing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import polars as pl

from ..config import Config
from ..constraints.cells import KIND_STATE_TOTAL, TOTAL_SIZE_CLASS, cell_id
from ..contracts import (
    BASELINE_RESULT_SCHEMA,
    DETERMINISTIC_BOUNDS_SCHEMA,
    HarmonizedData,
    assert_declared_provenance,
    validate_frame,
)
from ..errors import (
    BoundViolationError,
    ConceptViolationError,
    InfeasibleResidualError,
    WeightDomainError,
)
from ..reconcile.allocate import allocate
from ..reconcile.anchor import (
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)
from ..reconcile.integerize import integerize
from ..reconcile.scaling import Bounds
from .harvest import HarvestProportional
from .historical import (
    BreakAdjustedShare,
    ExponentiallyWeightedShare,
    LastObservedShare,
    RollingMedianShare,
    SameMonthPreviousYearShare,
)
from .intensity import CbpIntensity
from .interfaces import Decline, Estimator, EstimatorContext
from .regression import ConstrainedRegression
from .simple import EqualAllocation, EstablishmentProportional

REGISTRY: tuple[Estimator, ...] = (
    EqualAllocation(),
    EstablishmentProportional(),
    LastObservedShare(),
    SameMonthPreviousYearShare(),
    RollingMedianShare(),
    ExponentiallyWeightedShare(),
    BreakAdjustedShare(),
    CbpIntensity(),
    HarvestProportional(),
    ConstrainedRegression(),
)

# §10.8's four rungs, in the spec's order. `share_last_observed` stands for rung 3's "reconciled
# historical shares"; the other four variants are scored but the hierarchy names one representative.
FALLBACK_ORDER: tuple[str, ...] = (
    "cbp_intensity",
    "constrained_regression",
    "share_last_observed",
    "establishment_proportional",
)

# THE HIERARCHY ADMITS MORE ESTIMATORS THAN IT NAMES. `FALLBACK_ORDER` names one representative
# per rung; rung 3 is "reconciled historical shares", which is all five §10.3 variants. Testing
# membership in that four-tuple would rank `share_last_observed` above its own siblings, which
# §10.8 does not do: measured on D1's `whole_state_year_blocks`, `share_rolling_median` pools to
# 0.1342 against `share_last_observed`'s 0.1403. So eligibility is rung MEMBERSHIP, spelled out.
#
# The rungs are also the tie-break, and the tie is real rather than hypothetical: on D1's
# `long_consecutive_runs`, `establishment_proportional` and `share_same_month_prior_year` pool to
# the same 0.4229. §10.8 is a preference order, so the higher rung wins; `group_by` order is not
# guaranteed and would otherwise decide it.
#
# Exactly two estimators sit in no rung, each excluded by its own section's words: §10.1 "Use only
# as a sanity check" and §10.5 "a benchmark, not a preferred standalone estimator". They still run
# and are still scored -- they are just never preferred.
FALLBACK_RUNGS: tuple[tuple[str, ...], ...] = (
    ("cbp_intensity",),
    ("constrained_regression",),
    (
        "share_last_observed",
        "share_same_month_prior_year",
        "share_rolling_median",
        "share_exponentially_weighted",
        "share_break_adjusted",
    ),
    ("establishment_proportional",),
)

PREFERRABLE: frozenset[str] = frozenset(
    estimator_id for rung in FALLBACK_RUNGS for estimator_id in rung
)

# Rung index per estimator, for the tie-break. An estimator in no rung sorts after every rung --
# it is only ever reachable through `best_scoring_baseline`, which does not gate anything.
RUNG_OF: dict[str, int] = {
    estimator_id: index for index, rung in enumerate(FALLBACK_RUNGS) for estimator_id in rung
}


def resolve_estimators(declared: Sequence[str] | None) -> tuple[Estimator, ...]:
    """Estimator ids resolved against `REGISTRY`, in REGISTRY order.

    `None` means the whole registry. Every other input is checked and REFUSED rather than
    silently narrowed, because each failure mode produces a plausible-looking run:

      - an unknown id filtered out would leave a smaller subset, or an empty one whose manifest
        reads `scored=0` -- the empty partition that reads as "scored, nothing wrong" and that
        §13's harness refuses everywhere else;
      - `[]` is a request to score nothing, not a spelling of the default;
      - a repeated id would run one estimator twice and double every denominator built on the
        row count.

    The order is REGISTRY's, never the caller's. `run_id` hashes the ids it is handed, so a
    subset that round-tripped in the order someone typed would give `a,b` and `b,a` two run
    directories holding byte-identical outputs. Canonicalising makes the subset the set it means.
    """
    if declared is None:
        return REGISTRY
    known = {estimator.estimator_id: estimator for estimator in REGISTRY}
    if not declared:
        raise ConceptViolationError(
            "--estimators is empty: that asks the harness to score no estimator at all. "
            f"Omit the option for the full registry, or name some of {sorted(known)}"
        )
    duplicates = sorted({name for name in declared if declared.count(name) > 1})
    if duplicates:
        raise ConceptViolationError(
            f"--estimators repeats {duplicates}: an estimator run twice doubles every "
            "denominator counted off its rows"
        )
    unknown = sorted(set(declared) - set(known))
    if unknown:
        raise ConceptViolationError(
            f"--estimators names {unknown}, which §10's registry does not carry. "
            f"Known estimators: {sorted(known)}"
        )
    chosen = set(declared)
    return tuple(e for e in REGISTRY if e.estimator_id in chosen)


def _cell_ids(partition, anchor) -> dict[str, str]:
    """The shipped seven-field `cell_id` for each missing cell, keyed by state.

    `anchor.missing_cells` carries bare `state_fips`, but Stage 2's identifier is
    `kind|state|month|ownership|industry|naics_vintage|size_class`. Building a shorter string here
    would produce a `baseline_results.cell_id` that never joins `target_cell`,
    `constraint_coefficient`, or `deterministic_bounds` — and nothing would fail loudly, the joins
    would just come back empty. The key fields are read from the cell's own published row rather
    than hardcoded, so a vintage change follows the data.
    """
    ids: dict[str, str] = {}
    for row in partition.missing.iter_rows(named=True):
        ids[str(row["state_fips"])] = cell_id(
            KIND_STATE_TOTAL,
            state_fips=str(row["state_fips"]),
            reference_month=str(row["reference_month"]),
            ownership_code=str(row["ownership_code"]),
            industry_code=str(row["industry_code"]),
            naics_vintage=str(row["naics_vintage"]),
            size_class=TOTAL_SIZE_CLASS,
        )
    return ids


def state_total_bounds(bounds: pl.DataFrame) -> Bounds:
    """§7.10's `deterministic_bounds` table as the per-cell `Bounds` the runner checks against.

    KEYED BY THE SEVEN-FIELD `cell_id`, NOT BY `state_fips`. `scale_into_bounds` keys its `Bounds`
    by whatever `anchor.missing_cells` carries, which on this path is a bare state -- but that
    object is one month's feasible set, while `run_baselines` walks the whole window in a single
    call. State '04' has its own interval in January and another in February, so a state-keyed
    mapping would apply one month's bound to all 96 and no lookup would fail.

    ONLY `state_total` CELLS ARE KEPT. The same table carries §9's national size cells, and
    `test_d1_acceptance` measures cells that carry no row at all, so loading it whole would mix
    two cell kinds into one mapping and put keys in it the runner never looks up.

    DUPLICATES ARE REFUSED RATHER THAN COLLAPSED. `component_id`, `rank` and `nullity` sit beside
    `cell_id` in `DETERMINISTIC_BOUNDS_SCHEMA`, so the schema admits more than one row per cell by
    construction; D1 having exactly one is a measurement, not a guarantee. `dict(zip(...))` would
    silently keep whichever row sorted last and check the estimate against an arbitrary component.

    A NULL `selected_lower` IS REFUSED, while a null `selected_upper` is read as unbounded above.
    The asymmetry is §9.3's: nonnegativity is the one public fact touching every cell, so a cell
    with no lower bound at all means the solver did not answer for it -- whereas a null upper is
    the documented D1 state on 1,227 of 1,241 cells and `Bounds.upper_of` already reads it as
    positive infinity.
    """
    validate_frame(bounds, DETERMINISTIC_BOUNDS_SCHEMA, "deterministic_bounds")
    rows = bounds.filter(pl.col("cell_id").str.starts_with(f"{KIND_STATE_TOTAL}|"))
    duplicated = sorted(
        rows.group_by("cell_id").len().filter(pl.col("len") > 1)["cell_id"].to_list()
    )
    if duplicated:
        raise ConceptViolationError(
            f"deterministic_bounds carries more than one row for {duplicated[:5]} "
            f"({len(duplicated)} cell(s) in total); a per-cell bound must be unique before it can "
            "gate an estimate"
        )
    null_lower = sorted(rows.filter(pl.col("selected_lower").is_null())["cell_id"].to_list())
    if null_lower:
        raise ConceptViolationError(
            f"deterministic_bounds has a null selected_lower for {null_lower[:5]} "
            f"({len(null_lower)} cell(s) in total); §9.3's nonnegativity holds for every cell, so "
            "a missing lower bound is an unsolved cell rather than an unbounded one"
        )
    lower = {
        str(row["cell_id"]): float(row["selected_lower"]) for row in rows.iter_rows(named=True)
    }
    upper: dict[str, float | None] = {
        str(row["cell_id"]): (
            None if row["selected_upper"] is None else float(row["selected_upper"])
        )
        for row in rows.iter_rows(named=True)
    }
    return Bounds(lower=lower, upper=upper)


def assert_within_bounds(
    values: Mapping[str, float],
    bounds: Bounds,
    *,
    cell_ids: Mapping[str, str],
    estimator_id: str,
    reference_month: str,
    tolerance: float,
    quantity: str,
) -> None:
    """INV-002's per-cell half: refuse a released value outside its own solved `[L, U]`.

    COVERAGE IS CHECKED BEFORE THE COMPARISON, and that check is the load-bearing half. `upper_of`
    reads an absent key as `None` and therefore as `+inf`, so a `Bounds` keyed the wrong way --
    by `state_fips`, which is exactly the convention `scale_into_bounds` uses for this same type
    -- would pass every cell and make this whole gate a silent no-op. Indexing `bounds.lower`
    (which has no `_of` accessor, matching `scale_into_bounds`'s own direct index) turns that into
    a named refusal. An uncovered cell is a `ConceptViolationError`, not a `BoundViolationError`:
    nothing was violated, the bound is simply missing, and §18.3's fail-closed rule covers both.

    `tolerance` is the caller's, and production passes `reconciliation.tolerance` rather than
    `constraints.feasibility_tolerance`. `ReconciliationConfig`'s docstring gives the reason: "a
    bound solved to 1e-7 and a residual reconciled to 1e-9 are different obligations", and reusing
    the solver's number here would let a solver tuning change move what counts as a violation.

    `quantity` names which released number is being checked, because both are: §12.6's integers
    are released alongside the floats, and largest-remainder rounding can push a value that sat
    exactly on an upper bound past it. Without the label the message cannot say which one moved.
    """
    uncovered = sorted(cell for cell in values if cell_ids[cell] not in bounds.lower)
    if uncovered:
        raise ConceptViolationError(
            f"{reference_month}: {estimator_id} has no deterministic bound for "
            f"{[cell_ids[cell] for cell in uncovered]}; INV-002 cannot be checked against a "
            "bound that is absent, and an absent bound is not an unbounded one"
        )
    violations = []
    for cell in sorted(values):
        identifier = cell_ids[cell]
        value = float(values[cell])
        low = bounds.lower[identifier]
        high = bounds.upper_of(identifier)
        if value < low - tolerance or value > high + tolerance:
            violations.append(f"{identifier} {quantity}={value} outside [{low}, {high}]")
    if violations:
        raise BoundViolationError(
            f"{reference_month}: {estimator_id} violates INV-002's per-cell bounds at "
            f"{len(violations)} cell(s): {violations}"
        )


def run_baselines(
    data: HarmonizedData,
    config: Config,
    *,
    constraint_set_hash: str | None = None,
    estimators: Sequence[Estimator] = REGISTRY,
    bounds: Bounds | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Every estimator, every month. Returns `(baseline_results, anchor_audit)`.

    `constraint_set_hash` is threaded in rather than recomputed: it identifies the Stage 2 system
    these estimates sit beside, and §18.1's reproducibility check needs the two to agree. The CLI
    reads it from `schema_manifest.json`, which is the same file `solve-bounds` gates on. It stays
    optional so a unit test can build a toy `HarmonizedData` without a Stage 2 run.

    `estimators` defaults to the full `REGISTRY` and exists so §13's harness can restrict a regime
    to the rungs it needs: measured, ten estimators cost ~30 s per call against ~0.4 s for one, and
    the harness pays that per mask replicate.

    `bounds` turns on INV-002's per-cell half, and defaults to `None` -- no bound known, no check
    -- for two different reasons that must not be conflated. For a unit test it is convenience:
    a toy `HarmonizedData` has no Stage 2 run behind it, exactly as with `constraint_set_hash`.
    For `validate/harness.py`'s caller it is a DESIGN QUESTION that is still open, and the
    distinction matters because two different objects could be passed there.

    Passing the RUN DIRECTORY's `deterministic_bounds.parquet` would be wrong: it still carries
    the published value for a cell the pseudo-suppression mask hides, so its intervals were solved
    from a system containing the truth the harness is scoring against, and whether the check
    passed would then be a function of the hidden value -- §13.4's `LeakageError` territory. Note
    that the leak would be in the SIGNAL, not in the numbers: nothing here clips. `bounds` reaches
    exactly one consumer, `assert_within_bounds`, which compares and raises; no estimate is ever
    modified by it.

    Passing MASKED bounds would not leak, and they already exist -- `validate/harness.py` calls
    `recover.mask_and_solve` one line before this function and gets a `MaskedSystem.bounds` solved
    from the masked system. What is unresolved is what an out-of-interval estimate should MEAN on
    a scoring path: raising aborts a whole validation run because one estimator missed one
    interval, which is the opposite of what a scoreboard is for. That ruling is `D-087`, not a
    missing input. The production caller is `cli.py`, where raising is correct because the values
    are being released.
    """
    partitions = observed_partition(data.qcew_monthly)
    audit = closure_audit(data.qcew_monthly, partitions)
    assert_universe_closes(audit)

    context = EstimatorContext(
        monthly=data.qcew_monthly, cbp=data.cbp_state_size, partitions=partitions, config=config
    )
    rows: list[dict[str, object]] = []
    for month in sorted(partitions):
        anchor = national_residual(data.qcew_monthly, partitions[month], reference_month=month)
        if not anchor.missing_cells:
            continue
        ids = _cell_ids(partitions[month], anchor)
        for estimator in estimators:
            try:
                outcome = estimator.weights(context, anchor)
            except WeightDomainError as exc:
                # An estimator whose fallback cannot cover a cell raises rather than returning a
                # `Decline`, and `compose`'s docstring is right that the two are different things:
                # one is a data problem, the other a considered refusal. But the plan's "decline,
                # never fabricate" rule is about the OUTPUT, and it requires a visible row either
                # way — an absent row is indistinguishable from a bug. So the raise is preserved
                # inside `compose`, and here it becomes a `declined` row carrying the exception's
                # own words, which name it as the data problem it is. Without this, one cell with
                # no usable establishment count kills all ten estimators across every month.
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        str(exc),
                        constraint_set_hash,
                        ids,
                        kind="data_gap",
                    )
                )
                continue
            if isinstance(outcome, Decline):
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        outcome.reason,
                        constraint_set_hash,
                        ids,
                        kind=outcome.kind,
                    )
                )
                continue
            try:
                allocated = allocate(anchor, outcome)
            except WeightDomainError as exc:
                # A cell the estimator could not weight is a DECLINE, per the plan's "decline,
                # never fabricate" rule — not a dead run. `qtrly_establishments` is currently >= 1
                # on every suppressed cell, but that is a measurement a revision can move, and one
                # such cell would otherwise abort all ten estimators across all months.
                # `UniverseClosureError` stays a whole-run halt: that one really is global.
                rows.extend(
                    _decline_rows(
                        estimator.estimator_id,
                        anchor,
                        str(exc),
                        constraint_set_hash,
                        ids,
                        kind="reconciliation_failure",
                    )
                )
                continue
            if bounds is not None:
                assert_within_bounds(
                    allocated,
                    bounds,
                    cell_ids=ids,
                    estimator_id=estimator.estimator_id,
                    reference_month=month,
                    tolerance=config.reconciliation.tolerance,
                    quantity="estimate",
                )
            # The margin the integers must honour is the anchor's residual -- the published
            # quantity being allocated -- so it is taken from the anchor rather than re-derived
            # from the allocation. `allocate` already guarantees the values sum to R_t, so the two
            # candidates cannot actually disagree; naming the anchor is simply the honest source.
            integer_total = round(anchor.residual)
            integers = (
                integerize(allocated, total=integer_total)
                if config.reconciliation.integerize_release
                else dict.fromkeys(allocated, None)
            )
            if config.reconciliation.integerize_release and (
                sum(integers.values()) != integer_total
            ):
                # §12.6 step 5, as defence in depth rather than an independent derivation:
                # `integerize` already raises when it cannot place every unit, so this catches a
                # regression in that contract. A bare `assert` would vanish under `python -O`.
                raise InfeasibleResidualError(
                    f"{month}: integerized estimates for {estimator.estimator_id} sum to "
                    f"{sum(integers.values())}, not the required {integer_total}"
                )
            if bounds is not None and config.reconciliation.integerize_release:
                # §12.6's integers are released too, and largest-remainder rounding moves a value
                # by up to one whole employee -- so a float that sat exactly on an upper bound can
                # cross it. Checking only the float would leave the number actually published
                # unchecked, which is the half INV-002 names.
                assert_within_bounds(
                    {cell: float(value) for cell, value in integers.items() if value is not None},
                    bounds,
                    cell_ids=ids,
                    estimator_id=estimator.estimator_id,
                    reference_month=month,
                    tolerance=config.reconciliation.tolerance,
                    quantity="estimate_integer",
                )
            for cell in anchor.missing_cells:
                rows.append(
                    {
                        "estimator_id": estimator.estimator_id,
                        "cell_id": ids[cell],
                        "state_fips": cell,
                        "reference_month": month,
                        "raw_weight": float(outcome.values[cell]),
                        "estimate": float(allocated[cell]),
                        "estimate_integer": integers[cell],
                        "weight_basis": outcome.basis[cell],
                        "anchor_basis": anchor.anchor_basis,
                        "reconciliation_status": "anchored_and_reconciled",
                        "decline_reason": None,
                        "decline_kind": None,
                        "residual": anchor.residual,
                        "missing_set_size": len(anchor.missing_cells),
                        "constraint_set_hash": constraint_set_hash,
                    }
                )
    results = pl.DataFrame(rows, schema=BASELINE_RESULT_SCHEMA)
    assert_declared_provenance(results)
    return results, audit


def _decline_rows(
    estimator_id: str,
    anchor,
    reason: str,
    constraint_set_hash: str | None,
    ids: dict[str, str],
    *,
    kind: str,
) -> list[dict[str, object]]:
    """One visible row per cell a declining estimator could not weight, carrying the kind.

    `kind` is keyword-only and has no default: the three call sites below are three different
    situations, and the whole point of the column is that a reader can tell them apart without
    parsing `reason`.
    """
    return [
        {
            "estimator_id": estimator_id,
            "cell_id": ids[cell],
            "state_fips": cell,
            "reference_month": anchor.reference_month,
            "raw_weight": None,
            "estimate": None,
            "estimate_integer": None,
            "weight_basis": "none",
            "anchor_basis": anchor.anchor_basis,
            "reconciliation_status": "declined",
            "decline_reason": reason,
            "decline_kind": kind,
            "residual": anchor.residual,
            "missing_set_size": len(anchor.missing_cells),
            "constraint_set_hash": constraint_set_hash,
        }
        for cell in anchor.missing_cells
    ]


def preferred_estimator(results: pl.DataFrame) -> str:
    """§10.8's ordering, applied to whichever estimators actually produced estimates.

    Raises when no rung ran. Unreachable on D1 -- §10.2's inputs are complete on every suppressed
    cell, so rung 4 always produces estimates -- but reachable from a Stage 4 mask that empties
    every month's missing set, which is why it raises rather than returning a sentinel.
    """
    ran = set(
        results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")["estimator_id"]
        .unique()
        .to_list()
    )
    for estimator_id in FALLBACK_ORDER:
        if estimator_id in ran:
            return estimator_id
    raise ValueError("no estimator in §10.8's fallback hierarchy produced any estimate")


def preferred_estimator_by_month(results: pl.DataFrame) -> dict[str, str]:
    """§10.8's ordering resolved WITHIN each month, which is where it actually binds.

    Applying the hierarchy once to the whole window reports the top rung that ran anywhere, which
    on D1 names `cbp_intensity` even though it has no estimate in the twelve months of 2024. A
    consumer reading the scalar would take the preferred estimator's number for a month where it
    produced none. The scalar is kept as a window summary; this is the per-month truth.
    """
    reconciled = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    out: dict[str, str] = {}
    for (month,), group in reconciled.group_by("reference_month", maintain_order=True):
        ran = set(group["estimator_id"].unique().to_list())
        for estimator_id in FALLBACK_ORDER:
            if estimator_id in ran:
                out[str(month)] = estimator_id
                break
    return out
