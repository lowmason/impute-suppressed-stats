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


class UnsupportedReferenceYearError(LoggingEmploymentError):
    """A reference year lies outside the NAICS-vintage range this package can process.

    Deliberately not an "unknown vintage": BLS publishes a vintage for every year back to 1990,
    and `harmonize/naics.py` quotes the table. What is missing is downstream support, not the
    classification -- the vendored 113310 crosswalk carries only the 2017 and 2022 vintages,
    `validate/regimes.py` documents a single vintage seam and derives its targets from it, and
    `baselines/historical.py` filters its lookback on vintage equality -- that filter is the
    enforcing one; the seam is prose. Emitting a third vintage
    string would compose it into `cell_id` and five `contracts.py` schemas, so the year is
    refused rather than labelled with a vintage nothing else in the package can consume.
    """


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
    """The harvest-proportional baseline has no harvest-origin volume and no latent factor.

    Reserved for Stage 7 and deliberately unraised today. §10.5 states no precondition, so
    Stage 3's `HarvestProportional` returns a `Decline` rather than raising -- a per-month
    refusal the runner records, not a whole-run halt -- and that is the correct Stage 3
    behaviour. Stage 7 replaces that declining stub with a live baseline and owns the decision
    of when an absent factor is a halt instead; this class is held for that path.
    """


class LeakageError(LoggingEmploymentError):
    """§13.4's leakage controls found the thing they exist to find.

    A typed raise rather than a bare `assert`, because `python -O` strips assert statements and
    both guards run on the live path: `assert_no_retained_truth` from
    `validate/harness.py::run_pseudo_suppression` inside the scoring loop, and
    `assert_no_future_rows` once per rolling origin. Measured 2026-09-08 before this class existed,
    the same call raised under `python` and returned silently under `python -O`. The package states
    this convention in `run_pseudo_suppression`'s own docstring and these two functions were the
    only places in it that violated the convention.
    """
