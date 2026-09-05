"""Named fail-closed exceptions (§18.3).

Each carries the offending value, so a caller's log line names what halted the run rather than
only that something did.
"""

from __future__ import annotations


class LoggingEmploymentError(Exception):
    """Base class for every fail-closed condition in this package."""


class UnknownDisclosureCodeError(LoggingEmploymentError):
    """A QCEW disclosure code outside the measured allowlist reached the parser."""


class UnknownDisclosureRegimeError(LoggingEmploymentError):
    """A CBP reference year carries no established disclosure regime."""


class UnknownSizeCodeError(LoggingEmploymentError):
    """A QCEW establishment-size code reached the parser with no published bounds."""


class SchemaMismatchError(LoggingEmploymentError):
    """A fetched file's columns do not match the schema the parser declares."""


class MissingCrossTabulationError(LoggingEmploymentError):
    """A requested simultaneous cross-tabulation is absent from the source file."""


class ConceptViolationError(LoggingEmploymentError):
    """A value would cross a concept boundary the spec forbids crossing."""


class AmbiguousSnapshotError(LoggingEmploymentError):
    """A reference key has more than one stored snapshot and nothing says which one to build."""


class IncompatibleMarginError(LoggingEmploymentError):
    """Two source margins failed the §5.5 compatibility gate and must not be stacked (INV-007)."""


class InfeasibleComponentError(LoggingEmploymentError):
    """A constraint component has no feasible point; §9.6 forbids silently relaxing it."""


class HardConstraintClassError(LoggingEmploymentError):
    """A caller asked for `is_hard=true` on a restriction that is not eligible for it."""


class SolverError(LoggingEmploymentError):
    """The solver returned a status that is neither an optimum nor a recognised refusal."""


class UniverseClosureError(LoggingEmploymentError):
    """The establishment universes of the national row and the state rows do not close.

    §18.3 requires the pipeline to fail rather than guess when source universes cannot be
    reconciled. This is a whole-run halt, not a per-month decline: a nonzero gap means the
    published national row contains something the state table does not, and every month's
    residual is then suspect, not just the failing one's.
    """


class InfeasibleResidualError(LoggingEmploymentError):
    """§12.3's summed bounds exclude the residual, so no feasible scaling exists."""


class WeightDomainError(LoggingEmploymentError):
    """A weight vector's domain is not the missing set, or it carries a null or non-positive weight.

    Normalizing a weight vector defined on a strict subset of the missing set silently reallocates
    the absent cells' share onto the cells that happen to have inputs. That is fabricating an
    allocation, so it is refused rather than normalized.
    """


class NoHarvestFactorError(LoggingEmploymentError):
    """The harvest-proportional baseline has no harvest-origin volume and no latent factor."""
