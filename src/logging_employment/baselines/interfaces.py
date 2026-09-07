"""The `Estimator` protocol, and the declared-composite rule every baseline composes under.

§16.2 names `Estimator` inside `run_pseudo_suppression`'s signature and never defines it. Stage 3
defines it because Stage 4 consumes it.

AN ESTIMATOR PRODUCES WEIGHTS, NOT ESTIMATES. §10 (spec:942) requires every baseline to use "the
same ... reconciliation layer as the full model". The way to make that true rather than merely
stated is to leave estimators no way to produce a number: they return q, and `reconcile.allocate`
turns q into an estimate. §10.1 is q identically 1; §10.2 is q = establishments; §10.3 is a share
variant; §10.4 is shrunk CBP intensity times exposure; §10.6 is exp(prediction).

WHY COMPOSITION IS DECLARED RATHER THAN FORBIDDEN OR SILENT. Six D1 states have zero observed
employment months (AK, DE, HI, ND, NV, VT) and two have no CBP row in any year (HI, RI). Every
month's missing set contains at least one of each, so an all-or-nothing rule would make §10.3 and
§10.4 decline in 96 of 96 months and leave §10.8's rungs 1 and 3 permanently empty -- including the
"preferred transparent baseline" slot Stage 4 must fill with numbers. Silent subsetting is the
other failure: normalizing a partial vector reallocates the uncovered cells' share onto the covered
ones and looks perfectly well-formed. So composition is permitted, and every composed cell carries
`weight_basis = 'establishment_fallback'` in the output table and a count in the manifest. §10.8's
own rank-1 phrasing -- "employee-per-establishment with robust historical adjustment" -- is the
spec's precedent that a composed estimator is legitimate.

BOTH ARMS MUST BE IN THE SAME UNIT, AND THE GUARD ENFORCES IT. `allocate` normalizes the merged
vector as a whole (E = R * q / sum q), so a union of arms in different units is decided entirely by
whichever arm is numerically larger. Measured on 2024-03 with §10.3's shares against raw
establishment counts: nine states holding full observed histories received 0.58 of 1,589 employees
between them -- 0.037% of the residual -- while one fallback state took 1,257. Nothing about that
output looks wrong; it is positive everywhere and sums exactly to R_t, which is precisely why the
check has to be mechanical. Each baseline therefore supplies both arms in EMPLOYEES, and
`_assert_comparable_scales` is the tripwire that catches a regression rather than a statistical
test of anything.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Protocol

import polars as pl

from ..config import Config
from ..errors import ConceptViolationError, WeightDomainError
from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor, Partition

OWN = "own_estimator"
FALLBACK = "establishment_fallback"

# A units tripwire, not a statistical threshold. Arms that genuinely share a unit sit within a
# small factor of each other; the failure this exists to catch was four orders of magnitude.
MAX_SCALE_RATIO = 100.0


@dataclass(frozen=True)
class EmployeeWeights:
    """A weight vector in EMPLOYEES, claimed where it is constructed rather than inferred.

    `allocate` normalizes the union of a composite's two arms, so a union of arms in different
    units is decided entirely by whichever arm is numerically larger -- and the result is positive
    in every cell and sums exactly to R_t, which is why review does not catch it. The claim is
    made once, here, by whoever builds the vector; nothing re-derives it from the values.

    NO POSITIVITY CHECK HERE, DELIBERATELY. `compose` reads a non-positive own weight as a cell
    with no own signal and hands that cell to the fallback, which is behaviour §12.2 requires and
    a test pins. Positivity is enforced by `allocate.check_domain` on the COMPOSED vector -- the
    one that becomes estimates -- so validating it here would turn a legitimate fall-back into a
    raise.
    """

    values: dict[str, float]


@dataclass(frozen=True)
class Decline:
    """A baseline's refusal to run for a month, carrying the reason a reader needs."""

    reason: str


@dataclass(frozen=True)
class EstimatorContext:
    """Everything an estimator may read. Nothing here is a source endpoint."""

    monthly: pl.DataFrame
    cbp: pl.DataFrame
    partitions: dict[str, Partition]
    config: Config


class Estimator(Protocol):
    """A named producer of positive raw weights over one month's missing set."""

    estimator_id: str

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Positive weights for every cell in `anchor.missing_cells`, or a `Decline`."""
        ...


def _assert_comparable_scales(
    own: dict[str, float], fallback: dict[str, float], anchor: Anchor
) -> None:
    """Refuse a composite whose two arms are not plausibly in the same unit.

    Compared over the cells where both arms are defined and positive, using medians so one
    outlying state cannot mask a genuine mismatch. With no overlapping cell there is nothing to
    compare and nothing to get wrong: the merged vector is then all-fallback, and normalization
    makes its scale irrelevant.
    """
    shared = [c for c in own if c in fallback and own[c] > 0.0 and fallback[c] > 0.0]
    if not shared:
        return
    own_scale = statistics.median(own[c] for c in shared)
    fallback_scale = statistics.median(fallback[c] for c in shared)
    ratio = fallback_scale / own_scale
    if not math.isfinite(ratio) or ratio > MAX_SCALE_RATIO or ratio < 1.0 / MAX_SCALE_RATIO:
        raise WeightDomainError(
            f"{anchor.reference_month}: the two arms of the composite differ in scale by a factor "
            f"of {ratio:.4g} (own median {own_scale:.6g}, fallback median {fallback_scale:.6g}); "
            "`allocate` normalizes the union, so the larger arm would absorb nearly the whole "
            "residual. Supply both arms in employees"
        )


def usable_own(own: EmployeeWeights, anchor: Anchor) -> dict[str, float]:
    """The own weights `compose` will actually use: in the missing set, present, and positive.

    Public so a caller can ask whether a fallback arm is needed at all before paying to build one.
    Duplicating this predicate at a call site would let "needs a fallback" and "took the fallback"
    drift apart, which is the split `weight_basis` exists to report.
    """
    return {
        cell: value
        for cell, value in own.values.items()
        if cell in anchor.missing_cells and value is not None and value > 0.0
    }


def compose(
    own: EmployeeWeights,
    fallback: EmployeeWeights,
    anchor: Anchor,
    *,
    allowed: bool,
) -> Weights | Decline:
    """Own weight where it is positive and finite, declared fallback elsewhere.

    Both arms are `EmployeeWeights` and nothing else. A type annotation alone would not carry
    that: nothing in this project runs a static type checker, so the refusal below is what stops
    a plain `dict[str, float]` from impersonating an employees-valued arm at a call site.

    Raises `WeightDomainError` when the fallback itself cannot cover the gap: that is a data
    problem, not an estimator's refusal, and it must not be reported as a decline.
    """
    for name, arm in (("own", own), ("fallback", fallback)):
        if not isinstance(arm, EmployeeWeights):
            raise ConceptViolationError(
                f"{anchor.reference_month}: compose's {name} arm is a {type(arm).__name__}, not "
                "an EmployeeWeights. Both arms are employees-valued and the unit is carried by "
                "the type: measured on D1, substituting a raw establishment count for the scaled "
                "fallback shipped own-cell estimates up to 6.12x too large while every value "
                "stayed positive and every month summed exactly to the residual"
            )
    usable = usable_own(own, anchor)
    gaps = [cell for cell in anchor.missing_cells if cell not in usable]
    if not gaps:
        return Weights(values=usable, basis=dict.fromkeys(usable, OWN))

    if not allowed:
        return Decline(
            reason=(
                "baselines.allow_declared_composite is false and this estimator has no own weight "
                f"for {sorted(gaps)}"
            )
        )

    uncovered = [cell for cell in gaps if fallback.values.get(cell, 0.0) <= 0.0]
    if uncovered:
        raise WeightDomainError(
            f"{anchor.reference_month}: the establishment fallback cannot weight {sorted(uncovered)}"
        )

    _assert_comparable_scales(usable, fallback.values, anchor)
    values = dict(usable) | {cell: fallback.values[cell] for cell in gaps}
    basis = dict.fromkeys(usable, OWN) | dict.fromkeys(gaps, FALLBACK)
    return Weights(values=values, basis=basis)
