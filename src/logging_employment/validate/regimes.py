"""§13.3's holdout regimes.

Three panel facts are declared here rather than discovered at run time, because a generator that
discovers them silently produces the wrong mask. Measured 2026-09-07 on the D1 window: 272 of 400
state-years are fully observed; 6 of 50 states are never observed in any month and can never be a
target; 40 states carry at least one >=12-month observed run. `qcew_monthly` contains no DC rows
while `config.project.geography_universe` is `states_dc` — an open Stage 0 item, cited not fixed.

All three are DATED MEASUREMENTS. Recompute them at run time and assert on structure; a revision
moves every one of them.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass

import polars as pl

from ..config import Config
from ..contracts import HOLDOUT_REGIMES, REGIME_DISPOSITIONS, HarmonizedData
from .mask import MaskTarget, eligible_targets
from .propensity import sample_targets

# The nine Census divisions (U.S. Census Bureau statistical divisions). ONE scheme, named once,
# because §13.6's state-share strata, §13.7's required calibration-by-region, and Stage 5's
# §17.5 region effects must all partition on the SAME thing this regime masks on. Divisions
# rather than the four Census regions: 4 regions give 12-13 states per block against 34-40
# observed states per month, which masks a third of the disclosed set in one replicate.
CENSUS_DIVISIONS: dict[str, tuple[str, ...]] = {
    "new_england": ("09", "23", "25", "33", "44", "50"),
    "middle_atlantic": ("34", "36", "42"),
    "east_north_central": ("17", "18", "26", "39", "55"),
    "west_north_central": ("19", "20", "27", "29", "31", "38", "46"),
    "south_atlantic": ("10", "11", "12", "13", "24", "37", "45", "51", "54"),
    "east_south_central": ("01", "21", "28", "47"),
    "west_south_central": ("05", "22", "40", "48"),
    "mountain": ("04", "08", "16", "30", "32", "35", "49", "56"),
    "pacific": ("02", "06", "15", "41", "53"),
}


@dataclass(frozen=True)
class RegimeSpec:
    """One §13.3 regime: how it selects, at what grain, and whether it can run at all."""

    name: str
    disposition: str
    # "blackout" regimes INTEND to erase a state's history; "single_month" regimes must not.
    grain: str
    select: Callable[[pl.DataFrame, int, Config], list[MaskTarget]] | None


def _small_cell(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    return sample_targets(
        monthly, n=config.validation.replicates_per_regime, seed=seed, config=config
    )


def _concentration(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """High employees-per-establishment. Computed on the CANDIDATE POOL, never as a score input."""
    pool = eligible_targets(monthly).with_columns(
        (
            pl.col("employment_value").cast(pl.Float64)
            / pl.col("qtrly_establishments").cast(pl.Float64)
        ).alias("_epe")
    )
    drawn = pool.sort("_epe", descending=True).head(config.validation.replicates_per_regime * 3)
    drawn = drawn.sample(
        n=min(config.validation.replicates_per_regime, drawn.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _clustered(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Several states inside ONE month — the regime that stresses the residual, not the history."""
    pool = eligible_targets(monthly)
    month = pool.select("reference_month").unique().sample(n=1, seed=seed)["reference_month"].item()
    inside = pool.filter(pl.col("reference_month") == month)
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], month, "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _long_run(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """A >=12-month consecutive blackout. Draws only from states that HAVE such a run."""
    del config
    pool = eligible_targets(monthly).sort("state_fips", "reference_month")
    runs: list[tuple[str, list[str]]] = []
    for (state,), group in pool.group_by("state_fips", maintain_order=True):
        months = group["reference_month"].to_list()
        current: list[str] = []
        for month in months:
            if current and _is_next_month(current[-1], month):
                current.append(month)
            else:
                current = [month]
            if len(current) >= 12:
                runs.append((str(state), list(current[-12:])))
                break
    if not runs:
        return []
    index = seed % len(runs)
    state, months = runs[index]
    return [MaskTarget(state, m, "state_total", "primary_like") for m in months]


def _state_year(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """A whole calendar year for one state, drawn only from FULLY OBSERVED state-years."""
    del config
    pool = eligible_targets(monthly).with_columns(
        pl.col("reference_month").str.slice(0, 4).alias("_year")
    )
    complete = (
        pool.group_by("state_fips", "_year").agg(pl.len().alias("_n")).filter(pl.col("_n") == 12)
    )
    if complete.height == 0:
        return []
    pick = complete.sample(n=1, seed=seed).row(0, named=True)
    chosen = pool.filter(
        (pl.col("state_fips") == pick["state_fips"]) & (pl.col("_year") == pick["_year"])
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]


def _seasonal(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """One calendar month across every eligible state-year — the seasonal blackout."""
    del config
    pool = eligible_targets(monthly).with_columns(
        pl.col("reference_month").str.slice(5, 2).alias("_mm")
    )
    mm = pool.select("_mm").unique().sort("_mm").sample(n=1, seed=seed)["_mm"].item()
    chosen = pool.filter(pl.col("_mm") == mm)
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]


def _regional(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """One Census division's eligible states, in one month."""
    del config
    names = sorted(CENSUS_DIVISIONS)
    division = names[seed % len(names)]
    pool = eligible_targets(monthly).filter(
        pl.col("state_fips").is_in(list(CENSUS_DIVISIONS[division]))
    )
    if pool.height == 0:
        return []
    month = (
        pool.select("reference_month")
        .unique()
        .sort("reference_month")
        .sample(n=1, seed=seed)["reference_month"]
        .item()
    )
    chosen = pool.filter(pl.col("reference_month") == month)
    return [
        MaskTarget(r["state_fips"], month, "state_total", "primary_like")
        for r in chosen.iter_rows(named=True)
    ]


def _is_next_month(previous: str, candidate: str) -> bool:
    py, pm = int(previous[:4]), int(previous[5:])
    cy, cm = int(candidate[:4]), int(candidate[5:])
    return (cy, cm) == (py + 1, 1) if pm == 12 else (cy, cm) == (py, pm + 1)


_SELECTORS: dict[str, Callable[[pl.DataFrame, int, Config], list[MaskTarget]]] = {
    "small_cell_biased": _small_cell,
    "concentration_proxy": _concentration,
    "clustered_states_within_month": _clustered,
    "long_consecutive_runs": _long_run,
    "whole_state_year_blocks": _state_year,
    "whole_seasonal_blocks": _seasonal,
    "regional_blocks": _regional,
}

_GRAINS: dict[str, str] = {
    "long_consecutive_runs": "blackout",
    "whole_state_year_blocks": "blackout",
    "whole_seasonal_blocks": "blackout",
    "regional_blocks": "blackout",
}

REGIME_SPECS: dict[str, RegimeSpec] = {
    name: RegimeSpec(
        name=name,
        disposition=REGIME_DISPOSITIONS[name],
        grain=_GRAINS.get(name, "single_month"),
        select=_SELECTORS.get(name),
    )
    for name in HOLDOUT_REGIMES
}


def select_targets(
    regime: str, monthly: pl.DataFrame, *, seed: int, config: Config
) -> list[MaskTarget]:
    """Targets for one regime, or a refusal explaining why the regime cannot produce any."""
    spec = REGIME_SPECS[regime]
    if spec.disposition == "cannot_run_on_d1":
        raise NotImplementedError(
            f"{regime} cannot run on this window: no period in any staged table carries a second "
            "snapshot, so there is no preliminary vintage to compare against a final one. Turn "
            "`validation.include_vintage_comparison` off, or ingest a second vintage in Stage 1."
        )
    if spec.select is None:
        return []
    targets = spec.select(monthly, seed, config)
    if spec.grain == "single_month":
        floor = config.validation.minimum_unmasked_lookback_months
        per_state: dict[str, int] = {}
        for t in targets:
            per_state[t.state_fips] = per_state.get(t.state_fips, 0) + 1
        total_months = monthly["reference_month"].n_unique()
        for state, count in per_state.items():
            if total_months - count < floor:
                raise ValueError(
                    f"{regime} would mask {count} of {total_months} months for state {state}, "
                    f"leaving fewer than {floor} lookback months. A single-month regime must not "
                    "black out a state's own history — that is what the blackout regimes are for."
                )
    return targets


def rolling_origin_frames(
    monthly: pl.DataFrame, *, origins: Sequence[str]
) -> Iterator[tuple[str, pl.DataFrame]]:
    """§13.3's rolling-origin design: one past-only frame per origin.

    TRUNCATION, not masking. A mask nulls a value and leaves the row; the exit criterion asks that
    the run "provably contains no future-period rows", which only removing them can satisfy.

    Reported scope: measured 2026-09-07, no §10 estimator reads a future period, so this regime
    does not separate any Stage 3 baseline. It is built now because Stage 5's model will, and
    because the guard is what makes that claim checkable rather than assumed.
    """
    for origin in origins:
        yield origin, monthly.filter(pl.col("reference_month") < origin)


def _structural_break(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Targets inside a DECLARED break window.

    Declared, not detected. A per-cell break detector inside a validation stage is a research
    project, and the national series does not separate COVID from seasonality cleanly enough to
    justify one. The second window overlaps `naics_transition`; score a month under ONE label.
    """
    windows = config.validation.structural_break_windows
    pool = eligible_targets(monthly)
    inside = pool.filter(
        pl.any_horizontal(
            [
                (pl.col("reference_month") >= lo) & (pl.col("reference_month") <= hi)
                for lo, hi in windows
            ]
        )
    )
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def _naics_transition(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """Targets straddling the NAICS 2017 -> 2022 seam.

    The seam is 2021-12/2022-01 BY CONSTRUCTION: `harmonize.naics.vintage_for_year` returns
    "NAICS 2022" at year >= 2022, so `naics_vintage` is a derived column. This regime tests our own
    vintage rule, not a source-published break, and the scoreboard must say so.

    Scoring note: with `historical_may_cross_naics_vintage: false` and a 24-month lookback the
    share family has ZERO own-arm rows in 2022-01..03 — all five §10.3 variants emit
    `establishment_proportional`'s number under five labels. That composition emits no
    `decline_kind`, so it is invisible to §13.8's decline-by-kind report. Read
    `weight_basis_counts`.
    """
    seam = config.validation.naics_seam_month
    half = config.validation.naics_seam_halfwidth_months
    months = sorted(monthly["reference_month"].unique().to_list())
    if seam not in months:
        return []
    centre = months.index(seam)
    window = set(months[max(0, centre - half) : centre + half + 1])
    inside = eligible_targets(monthly).filter(pl.col("reference_month").is_in(list(window)))
    drawn = inside.sample(
        n=min(config.validation.replicates_per_regime, inside.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [
        MaskTarget(r["state_fips"], r["reference_month"], "state_total", "primary_like")
        for r in drawn.iter_rows(named=True)
    ]


def cbp_size_gap_keys(data: HarmonizedData, *, seed: int, config: Config) -> list[tuple[str, int]]:
    """(state_fips, reference_year) pairs whose CBP size rows this regime removes.

    Returns CBP keys, NOT `MaskTarget`s: no QCEW cell is hidden here. The only consumer of
    `cbp_state_size` in the estimation path is `intensity_rows`, so removing a state-year turns
    §10.4 from an own-arm estimator into a declining one for that state-year and leaves every
    other estimator untouched. That difference IS the metric.
    """
    pool = data.cbp_state_size.select("state_fips", "reference_year").unique()
    drawn = pool.sample(
        n=min(config.validation.replicates_per_regime, pool.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [(r["state_fips"], r["reference_year"]) for r in drawn.iter_rows(named=True)]


def apply_cbp_gap(data: HarmonizedData, keys: Sequence[tuple[str, int]]) -> HarmonizedData:
    """Drop the named CBP state-years so §10.4 must fall back or decline."""
    if not keys:
        return data
    selector = pl.struct("state_fips", "reference_year").is_in(
        [{"state_fips": s, "reference_year": y} for s, y in keys]
    )
    return dataclasses.replace(data, cbp_state_size=data.cbp_state_size.filter(~selector))


_SELECTORS["structural_break"] = _structural_break
_SELECTORS["naics_transition"] = _naics_transition

# Rebuilt so the two selectors registered above reach the specs. `REGIME_SPECS` is a plain dict
# built by comprehension, so a late `_SELECTORS` mutation does not propagate on its own; leaving
# it stale would give `select_targets` a `None` selector and an empty target list -- exactly the
# silent no-op this stage refuses everywhere else. `preliminary_to_final_vintage` stays out of
# `_SELECTORS` on purpose, so its disposition raises.
REGIME_SPECS = {
    name: RegimeSpec(
        name=name,
        disposition=REGIME_DISPOSITIONS[name],
        grain=_GRAINS.get(name, "single_month"),
        select=_SELECTORS.get(name),
    )
    for name in HOLDOUT_REGIMES
}
