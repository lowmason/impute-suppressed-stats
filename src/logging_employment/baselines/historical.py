"""§10.3's five historical state-share baselines.

The spec lists exactly five (spec:968-972): last observed share, same-month previous-year share,
rolling median share, exponentially weighted historical share, and a robust break-adjusted share.
All five share one history extractor and differ only in how they reduce a series of shares to one
number, which is the whole reason they belong in one module.

CLASSIFICATION-CONSISTENT PERIODS. §10.3 requires them and does not define them. The D1 window
carries a NAICS vintage break at 2022-01 -- NAICS 2017 through 2021-12, NAICS 2022 from 2022-01 --
so a 24-month lookback from 2022-06 would otherwise mix two classifications. The default is to stop
at the break. It is a config key rather than a constant because whether 113310 was actually
retabulated at that break is an UNCITED premise in this repo (see `specs/deferred_items.md`), and a
key can be flipped by whoever finds the citation; a constant would have to be argued with.

THE LOOKBACK IS BOUNDED IN MONTHS, NOT ROWS. `historical_lookback_months` names a span of calendar
time, so taking the last N rows of an observed-only series is a different estimator: a state
observed in only 8 of the last 60 months would reach back five years under a row bound while the
config says two. Both bounds are applied -- months first, then the row cap -- so the config key
means what it says.

WHY THE OWN ARM IS IN EMPLOYEES. A reduced share is dimensionless and runs around 1e-3, while the
establishment fallback runs 1..282. `allocate` normalizes the union of the two, so merging them
raw lets the fallback absorb essentially the whole residual -- measured on 2024-03, the states
holding real histories received 0.037% of R_t between them. The share is therefore multiplied by
the published national total for the month, making the own arm a predicted employment level, and
the fallback arrives already scaled to employees. Neither step invents a number.

COVERAGE. Six states have zero observed employment months in the whole window -- AK, DE, HI, ND,
NV, VT -- so no in-window share exists for them, and every one of the 96 months' missing sets
contains at least one. The own/fallback split is a measurement that a revision moves, so it is
recorded in the run manifest rather than written here. Without composition this entire family
would decline in 96/96 months and §10.8's rung 3 would be permanently empty.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping

import polars as pl

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor, Partition
from .interfaces import Decline, EmployeeWeights, EstimatorContext, compose
from .simple import establishment_fallback_in_employees


def _months_before(month: str, count: int) -> str:
    """The `YYYY-MM` exactly `count` months earlier, for bounding a lookback in calendar time."""
    year, index = (int(part) for part in month.split("-"))
    total = year * 12 + (index - 1) - count
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def observed_share_history(
    monthly: pl.DataFrame,
    partitions: Mapping[str, Partition],
    *,
    state_fips: str,
    before: str,
    lookback_months: int,
    may_cross_vintage: bool,
    vintage: str,
) -> pl.DataFrame:
    """One state's disclosed shares of the national total, most recent last.

    VISIBILITY COMES FROM THE PARTITION, NEVER FROM `observation_status`. This is the same
    mask-parameterised rule the anchor follows, and here it is a leakage control rather than a
    matter of taste: under a Stage 4 pseudo-suppression mask the held-out cell still carries its
    published value in `qcew_monthly`, so a history filtered on the table would hand this
    estimator the very value it is being tested on. Measured on a two-month panel, the table-based
    filter returned a masked cell's own published employment back to it exactly, through the
    share. §13.4 forbids a derived feature retaining a held-out value, and a share of it is one.

    Reading the partition also fixes what the table filter got wrong even unmasked: `disclosed`
    holds `true_zero` as well as `observed`, so a published zero now enters the history as the
    zero share it is. Filtering on `== "observed"` skipped past it to an older positive value.
    """
    national = monthly.filter(pl.col("area_type") == "national").select(
        ["reference_month", pl.col("employment_value").alias("national_value")]
    )
    floor = _months_before(before, lookback_months)
    windows = [
        partition.disclosed for month, partition in partitions.items() if floor <= month < before
    ]
    if not windows:
        return pl.DataFrame(schema={"reference_month": pl.String, "share": pl.Float64})
    rows = (
        pl.concat(windows)
        .filter(pl.col("state_fips") == state_fips)
        .join(national, on="reference_month", how="inner")
        .filter(pl.col("national_value") > 0)
    )
    if not may_cross_vintage:
        rows = rows.filter(pl.col("naics_vintage") == vintage)
    return (
        rows.with_columns((pl.col("employment_value") / pl.col("national_value")).alias("share"))
        .sort("reference_month")
        .tail(lookback_months)
        .select(["reference_month", "share"])
    )


def _vintage_at(monthly: pl.DataFrame, reference_month: str) -> str:
    """The NAICS vintage the target month is published under."""
    rows = monthly.filter(pl.col("reference_month") == reference_month)
    return str(rows["naics_vintage"][0])


def _national_total(monthly: pl.DataFrame, reference_month: str) -> float:
    """The published national employment row for the month, which puts a share into employees."""
    rows = monthly.filter(
        (pl.col("area_type") == "national") & (pl.col("reference_month") == reference_month)
    )
    return float(rows["employment_value"][0])


class _ShareBaseline:
    """Shared plumbing: extract each missing cell's share history, reduce it, then compose."""

    estimator_id = "historical_share"

    def _reduce(self, shares: list[float], anchor: Anchor, history: pl.DataFrame) -> float | None:
        """Collapse one state's share history to a single share, or `None` to take the fallback.

        The only thing the five variants differ in. `history` is passed alongside `shares` because
        the same-month-previous-year variant selects by month rather than by position.
        """
        raise NotImplementedError

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """A predicted employment level per cell with a usable history, composed with the fallback."""
        cfg = context.config.baselines
        vintage = _vintage_at(context.monthly, anchor.reference_month)
        national = _national_total(context.monthly, anchor.reference_month)
        own: dict[str, float] = {}
        for cell in anchor.missing_cells:
            history = observed_share_history(
                context.monthly,
                context.partitions,
                state_fips=cell,
                before=anchor.reference_month,
                lookback_months=cfg.historical_lookback_months,
                may_cross_vintage=cfg.historical_may_cross_naics_vintage,
                vintage=vintage,
            )
            shares = history["share"].to_list()
            if not shares:
                continue
            reduced = self._reduce(shares, anchor, history)
            if reduced is not None and reduced > 0.0:
                # Share -> employees, so both arms of the composite share a unit.
                own[cell] = reduced * national
        return compose(
            EmployeeWeights(own),
            EmployeeWeights(establishment_fallback_in_employees(context, anchor)),
            anchor,
            allowed=cfg.allow_declared_composite,
        )


class LastObservedShare(_ShareBaseline):
    """§10.3 variant 1."""

    estimator_id = "share_last_observed"

    def _reduce(self, shares, anchor, history):
        """The most recent observed share."""
        return shares[-1]


class SameMonthPreviousYearShare(_ShareBaseline):
    """§10.3 variant 2: the same calendar month one year earlier, or nothing.

    Falls back to no own weight rather than to the nearest month: substituting a different month
    would make this variant indistinguishable from `LastObservedShare` exactly when it matters.
    """

    estimator_id = "share_same_month_prior_year"

    def _reduce(self, shares, anchor, history):
        """The share twelve months back, or `None` if that month was not observed."""
        year, month = anchor.reference_month.split("-")
        wanted = f"{int(year) - 1:04d}-{month}"
        matched = history.filter(pl.col("reference_month") == wanted)["share"].to_list()
        return matched[0] if matched else None


class RollingMedianShare(_ShareBaseline):
    """§10.3 variant 3."""

    estimator_id = "share_rolling_median"

    def _reduce(self, shares, anchor, history):
        """The median share over the lookback."""
        return statistics.median(shares)


class ExponentiallyWeightedShare(_ShareBaseline):
    """§10.3 variant 4. The half-life is one year of the lookback, so recency dominates smoothly."""

    estimator_id = "share_exponentially_weighted"
    decay = 0.5 ** (1.0 / 12.0)

    def _reduce(self, shares, anchor, history):
        """A geometrically discounted mean, heaviest on the most recent share."""
        weights = [self.decay ** (len(shares) - 1 - i) for i in range(len(shares))]
        return sum(w * s for w, s in zip(weights, shares, strict=True)) / sum(weights)


class BreakAdjustedShare(_ShareBaseline):
    """§10.3 variant 5: robust to a level break in the share series.

    Uses the median of the most recent segment after the largest single-step change, so one
    reclassification or one plant closure does not drag the estimate toward a regime that ended.
    At four or more shares this is not a plain median over the whole lookback; below four it is
    exactly that, because a segment split needs points on both sides.
    """

    estimator_id = "share_break_adjusted"

    def _reduce(self, shares, anchor, history):
        """The median of the segment following the largest single-step level change."""
        if len(shares) < 4:
            return statistics.median(shares)
        steps = [abs(shares[i + 1] - shares[i]) for i in range(len(shares) - 1)]
        cut = steps.index(max(steps)) + 1
        segment = shares[cut:]
        return statistics.median(segment)
