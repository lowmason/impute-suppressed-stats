"""The one construction that turns §10.2 establishment exposure into an employees-valued arm.

WHY THERE IS EXACTLY ONE. Before this module each composing baseline built and scaled its own
fallback, which is how §10.3 and §10.6 came to scale by the disclosed intensity while §10.4 scales
by the national CBP March one, with no section asking for either. The values are close on D1 --
disclosed 5.442-6.380, national 5.914-6.139 -- so this was never a numerical problem; it was an
unexplained divergence in a layer Stage 4 is about to score.

THE DIVERGENCE IS KEPT, AND DECLARED. §10.4's national value is exactly its own shrinkage limit as
the CBP cell count goes to zero, a derivation §10.3 and §10.6 have nothing equivalent to appeal
to. So it is not standardised away; each estimator names its choice in `fallback_intensity`, the
run manifest reports it, and a reader can check an arm against the name without reading source.

WHY §10.4's CBP MARCH HELPERS LIVE HERE. `national_march_intensity` is one of the two declared
intensities, so the module that resolves a declaration owns it. `intensity.py` imports it back for
its own arm -- the shrunk per-state value shrinks TOWARD it -- and that direction is what keeps the
two modules acyclic: nothing here imports an estimator module.

THE ARM IS BUILT LAZILY. `compose_with_declared_fallback` computes the gap first and pays for the
arm only when a gap exists. That is not an optimisation. Building it eagerly, as every caller used
to, means a month whose own arm covers the whole missing set still resolves an intensity and still
reads a partition it never uses -- so a partition disagreement that cannot affect the answer would
raise anyway.
"""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from ..errors import ConceptViolationError
from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EmployeeWeights, Estimator, EstimatorContext, compose, usable_own
from .simple import establishment_weights

# The two declared intensities, as a closed set. An estimator's `fallback_intensity` is written
# into `baseline_manifest.json`, so a value outside this tuple would reach a run's output as
# though it were a choice someone made.
DISCLOSED_QCEW = "disclosed_qcew"
NATIONAL_CBP_MARCH = "national_cbp_march"
FALLBACK_INTENSITIES: tuple[str, ...] = (DISCLOSED_QCEW, NATIONAL_CBP_MARCH)

ALL_ESTABLISHMENTS_SIZE_CODE = "001"


def intensity_rows(cbp: pl.DataFrame, reference_year: int) -> pl.DataFrame:
    """The usable CBP rows for one reference year: published, all-establishments, non-empty."""
    return cbp.filter(
        (pl.col("reference_year") == reference_year)
        & (pl.col("size_code") == ALL_ESTABLISHMENTS_SIZE_CODE)
        & pl.col("employment").is_not_null()
        & (pl.col("establishments") > 0)
    )


def national_march_intensity(cbp: pl.DataFrame, *, reference_year: int) -> float | None:
    """The national March employees-per-establishment, and the n -> 0 limit of the shrunk value.

    §10.4's declared fallback intensity, and the target its own per-state shrinkage pulls toward.
    A state with no CBP row weighted at this value is weighted at exactly what this estimator's
    shrinkage returns in the limit; weighting it at a bare establishment count would instead
    assert an intensity of 1.0.
    """
    rows = intensity_rows(cbp, reference_year)
    if rows.height == 0:
        return None
    establishments = float(rows["establishments"].sum())
    if establishments <= 0.0:
        return None
    return float(rows["employment"].sum()) / establishments


def disclosed_intensity(context: EstimatorContext, anchor: Anchor) -> float | None:
    """Published employees per establishment across this month's disclosed cells.

    §10.3's and §10.6's declared fallback intensity: a published ratio of two published sums. It
    is preferred over the residual-implied ratio (R_t / sum A over the missing set) because it
    stays positive and well defined when R_t is 0 -- a degenerate case §12.3 requires to succeed.
    `None` when the disclosed set carries no establishments, which leaves the caller to fall back
    to an empty arm rather than divide by zero.
    """
    disclosed = context.partitions[anchor.reference_month].disclosed
    establishments = float(disclosed["qtrly_establishments"].fill_null(0).sum())
    if establishments <= 0.0:
        return None
    return float(disclosed["employment_value"].fill_null(0).sum()) / establishments


def national_cbp_march_intensity(context: EstimatorContext, anchor: Anchor) -> float | None:
    """§10.4's declared intensity, resolved for the anchor's own reference year."""
    reference_year = int(anchor.reference_month.split("-")[0])
    return national_march_intensity(context.cbp, reference_year=reference_year)


_RESOLVERS: dict[str, Callable[[EstimatorContext, Anchor], float | None]] = {
    DISCLOSED_QCEW: disclosed_intensity,
    NATIONAL_CBP_MARCH: national_cbp_march_intensity,
}


def resolve_intensity(basis: str, context: EstimatorContext, anchor: Anchor) -> float | None:
    """The value of a declared intensity, or `None` when its inputs do not support one."""
    if basis not in _RESOLVERS:
        raise ConceptViolationError(
            f"{basis!r} is not a declared fallback intensity; the declared set is "
            f"{list(FALLBACK_INTENSITIES)}. An estimator's `fallback_intensity` is written into "
            "baseline_manifest.json as the scaling a reader can check its arm against, so a name "
            "outside the set would reach a run's output as though it were a choice"
        )
    return _RESOLVERS[basis](context, anchor)


def establishment_fallback(
    context: EstimatorContext, anchor: Anchor, *, intensity: float
) -> EmployeeWeights:
    """§10.2 exposure scaled into EMPLOYEES. The only fallback arm construction there is.

    The intensity arrives as an argument rather than being chosen here, which is what makes
    "which intensity scaled this arm" a property of the caller that a manifest can report.
    """
    exposure = establishment_weights(context, anchor)
    return EmployeeWeights({cell: value * intensity for cell, value in exposure.items()})


def declared_fallback(
    estimator: Estimator, context: EstimatorContext, anchor: Anchor
) -> EmployeeWeights:
    """The fallback arm THIS estimator declares, empty when its intensity has no value.

    An empty arm is not an error here: `compose` refuses the cells it cannot cover, by name, and
    that refusal carries the month and the cells a reader needs.
    """
    basis = estimator.fallback_intensity
    if basis is None:
        raise ConceptViolationError(
            f"{estimator.estimator_id} asked for a fallback arm but declares no "
            "fallback_intensity; the choice of intensity is a property of the estimator so that a "
            "run's manifest can report it, and there is no default to fall through to"
        )
    intensity = resolve_intensity(basis, context, anchor)
    if intensity is None or intensity <= 0.0:
        return EmployeeWeights({})
    return establishment_fallback(context, anchor, intensity=intensity)


def compose_with_declared_fallback(
    estimator: Estimator,
    own: EmployeeWeights,
    context: EstimatorContext,
    anchor: Anchor,
) -> Weights | Decline:
    """`compose`, with the declared fallback arm built only when a gap actually needs one.

    Every composing estimator goes through here rather than calling `compose` directly, so the
    fallback's construction and its intensity are decided in one place for all seven of them.
    """
    usable = usable_own(own, anchor)
    needs_fallback = any(cell not in usable for cell in anchor.missing_cells)
    fallback = (
        declared_fallback(estimator, context, anchor) if needs_fallback else EmployeeWeights({})
    )
    return compose(own, fallback, anchor, allowed=context.config.baselines.allow_declared_composite)
