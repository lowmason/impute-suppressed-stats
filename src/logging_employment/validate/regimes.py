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
from ..errors import ConceptViolationError
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


# WHY a regime produces no `MaskTarget`, declared per regime rather than inferred from
# `select is None`. That test conflates three unrelated situations — a regime that uses a different
# mechanism entirely, one that is vacuous on the §10 registry, and one that refuses on this window
# — and the harness templated ONE sentence on `{name}` across all of them. Measured 2026-09-08, the
# sentence was true of `rolling_origin` and false of `cbp_size_gaps`, whose named entry points have
# no caller and no test anywhere in the package, and the false version shipped verbatim in
# `runs/f03023ac9f3a/validation_manifest.json`.
REGIME_MECHANISMS: tuple[str, ...] = (
    "qcew_mask",
    "frame_truncation",
    "cbp_gap",
    "no_registry_estimator",
    "no_second_vintage",
)

_MECHANISMS: dict[str, str] = {
    "rolling_origin": "frame_truncation",
    "cbp_size_gaps": "cbp_gap",
    "retrospective_smoothing": "no_registry_estimator",
    "preliminary_to_final_vintage": "no_second_vintage",
}

# Each regime's own sentence, a MEASUREMENT or a DECLARATION and never a deferral (R-S4C-2). The
# two measured ones carry the date and the registry they were measured against, so that adding an
# estimator invalidates them rather than letting them be silently inherited.
_NO_SCORE_REASONS: dict[str, str] = {
    "rolling_origin": (
        "rolling_origin truncates the frame rather than masking a QCEW cell, so it produces no "
        "MaskTarget. Measured 2026-09-08 against the ten-estimator §10 registry: truncation moves "
        "no estimator's pre-origin estimate — rolling_origin_frames removes 1,788 of 4,812 rows "
        "at origin 2022-01, and every estimator returns what it returned unmasked — so this "
        "regime separates ZERO baselines on THIS registry. The scope is the registry: adding a "
        "smoothing or autoregressive estimator invalidates this reason rather than inheriting it. "
        "A scoreboard entry that cannot discriminate would read as evidence, so the regime records "
        "the §13.4 future-row guard instead of a score; the origins it was checked at are recorded "
        "beside this reason."
    ),
    "cbp_size_gaps": (
        "cbp_size_gaps removes CBP state-year rows rather than masking a QCEW cell, so it "
        "produces no MaskTarget and scores no cell on its own: it changes cbp_intensity's weight "
        "basis, not the set of masked cells. Measured 2026-09-08: removal causes ZERO additional "
        "declines (147 declined rows before and after) and moves the cell to the declared fallback "
        "arm, and because national_march_intensity pools over surviving rows the effect reaches "
        "every state in the year rather than only the holed state-year."
    ),
    "retrospective_smoothing": "no smoothing estimator in the §10 registry",
    "preliminary_to_final_vintage": "no second snapshot in any staged table",
}


@dataclass(frozen=True)
class RegimeSpec:
    """One §13.3 regime: how it selects, at what grain, whether it can run, and by what mechanism."""

    name: str
    disposition: str
    # "blackout" regimes INTEND to erase a state's history; "single_month" regimes must not.
    grain: str
    select: Callable[[pl.DataFrame, int, Config], list[MaskTarget]] | None
    mechanism: str
    no_score_reason: str | None

    def __post_init__(self) -> None:
        """Refuse a spec whose mechanism, selector and reason disagree.

        Enforced rather than conventional because this module MUTATES `_SELECTORS` after the
        module body has run past the point a comprehension would read it. A regime that gained a
        selector without gaining `qcew_mask` — or lost one without gaining a reason — would
        otherwise reach the harness as a silent no-op, which is the failure this stage refuses
        everywhere else.
        """
        if self.mechanism not in REGIME_MECHANISMS:
            raise ConceptViolationError(
                f"{self.name}: mechanism {self.mechanism!r} is not declared; the set is "
                f"{list(REGIME_MECHANISMS)}"
            )
        if (self.mechanism == "qcew_mask") != (self.select is not None):
            raise ConceptViolationError(
                f"{self.name}: mechanism {self.mechanism!r} and "
                f"select={'a callable' if self.select else 'None'} disagree. A qcew_mask regime "
                "has a selector and every other mechanism has none."
            )
        if (self.mechanism == "qcew_mask") != (self.no_score_reason is None):
            raise ConceptViolationError(
                f"{self.name}: a qcew_mask regime declares no no_score_reason and every other "
                "mechanism must declare one — a regime that scores nothing must say why "
                "(R-S4C-2), and the reason must be its own rather than a shared template."
            )


def _small_cell(monthly: pl.DataFrame, seed: int, config: Config) -> list[MaskTarget]:
    """§13.3's small-cell-biased regime: the propensity draw itself, with no extra filter.

    `sample_targets` is already propensity-WEIGHTED rather than uniform-then-sorted, so this regime
    needs no pool of its own — narrowing the pool here as well would apply the same bias twice.
    """
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
    # SORT BEFORE SAMPLING. `unique()` gives no order guarantee, so a seeded sample over its output
    # picks a different month per process — measured, this regime and `_state_year` were the only
    # two of seven that changed digest across runs, and that broke §16.1's idempotence MUST.
    month = (
        pool.select("reference_month")
        .unique()
        .sort("reference_month")
        .sample(n=1, seed=seed)["reference_month"]
        .item()
    )
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
        pool.group_by("state_fips", "_year")
        .agg(pl.len().alias("_n"))
        .filter(pl.col("_n") == 12)
        # SORT BEFORE SAMPLING: `group_by` returns rows in arbitrary order, so a seeded sample over
        # it is not reproducible across processes. See `_clustered` for the measurement.
        .sort("state_fips", "_year")
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
    """Is `candidate` the calendar month directly after `previous`, across a year boundary?

    String comparison cannot answer this — "2020-12" and "2021-01" are adjacent months but not
    adjacent strings — and `_long_run` needs consecutiveness, not sort order, to find a genuine
    blackout run rather than a gap-spanning one.
    """
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

    THE MEMBERSHIP REFUSAL LIVES HERE AND NOT IN `assert_no_future_rows`, which is where R-S4C-5
    places it. A truncated frame never contains its own origin — every period in it is strictly
    below the origin by construction — so the guard cannot ask this question from the two arguments
    it takes. It COULD be made to: give it the untruncated panel's periods as a third argument and
    the check fits there. That was rejected because every caller would then have to thread the
    pre-truncation universe through to a guard whose whole job is to inspect one frame, and this
    function already holds the panel. The constraint is the guard's signature, not arithmetic.

    THE REFUSAL IS EAGER, which is why `_truncated` is a separate function. A `yield` anywhere in
    this body would defer every line of it until a caller iterated, so the check would not run on
    the bare call — measured 2026-09-08, the inline version returned a generator and raised
    nothing.
    """
    panel = set(monthly["reference_month"].unique().to_list())
    unknown = [origin for origin in origins if origin not in panel]
    if unknown:
        # `min`/`max` over an empty panel raises ValueError, masking the refusal, so the range
        # clause is conditional. No caller in this package reaches it — `rolling_origins` derives
        # origins FROM the panel, so an empty panel yields no origins and no call — but the guard
        # is cheap and the failure mode is a confusing exception type.
        span = f", whose months run {min(panel)}..{max(panel)}" if panel else " (which is empty)"
        raise ConceptViolationError(
            f"origin(s) {unknown} name no period in this panel{span}. An origin outside it "
            "truncates nothing and leaves the §13.4 guard passing over an untruncated frame: "
            "measured, `origins=['banana']` returned all 4,812 rows and `assert_no_future_rows` "
            "reported no future row, because every period sorts below the string."
        )
    return _truncated(monthly, origins)


def _truncated(monthly: pl.DataFrame, origins: Sequence[str]) -> Iterator[tuple[str, pl.DataFrame]]:
    """One past-only frame per origin. Called only by `rolling_origin_frames`, after its refusal."""
    for origin in origins:
        yield origin, monthly.filter(pl.col("reference_month") < origin)


def rolling_origins(monthly: pl.DataFrame, *, config: Config) -> tuple[str, ...]:
    """The origins §13.4's future-row guard runs at: each January with enough history behind it.

    DERIVED FROM THE PANEL, NOT CONFIGURED, and that is a constraint rather than a preference.
    `runs.run_id` hashes `config.resolved_dict`, which is `Config.model_dump(mode="json")` — the
    whole model — so ADDING a `ValidationConfig` key re-identifies every run directory on disk
    exactly as removing one does. `runs/f03023ac9f3a` is Stage 4's acceptance artifact and must
    still resolve from the shipped `config.yaml`. A panel-derived rule needs no new key.

    Januaries rather than the declared break windows, which was the alternative considered:
    `structural_break_windows` and `naics_seam_month` name months this panel's ESTIMATORS are
    stressed at, which is a different question from where a real-time frame should be cut, and
    reusing them would make an edit to either silently move the other. The history floor is
    `minimum_unmasked_lookback_months`, reused rather than re-declared — a January with less than
    that behind it truncates to a frame too short to estimate from, which proves nothing.

    Measured 2026-09-08: seven origins on `data/staged` (2018-01 through 2024-01, with 2017-01
    excluded by the floor) and NONE on the committed `tests/fixtures/baselines` layer, which
    carries 2023 alone. The guard is therefore vacuous on the fixture and binding on D1, and
    `run_pseudo_suppression` then records which, in the manifest, rather than leaving a reader to
    assume. (Forward-looking at the moment this function was written: nothing wired the guard into
    the harness until the task after it, so that sentence was a promise then, not a measurement.)
    """
    months = sorted(monthly["reference_month"].unique().to_list())
    floor = config.validation.minimum_unmasked_lookback_months
    return tuple(
        month for index, month in enumerate(months) if month.endswith("-01") and index >= floor
    )


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

    A STATE-YEAR GAP, not a size gap, whatever the name says. `apply_cbp_gap` keys on
    `(state_fips, reference_year)` and removes the state-year across all seven size codes — 86 rows
    for a 20-key draw on D1. The identifiers `cbp_size_gaps` and `cbp_size_gap_keys` are NOT
    renamed: `cbp_size_gaps` is a member of `contracts.HOLDOUT_REGIMES` and appears in
    `REGIME_DISPOSITIONS`, so renaming would change the manifest's regime keys for no behavioural
    gain. The mismatch is recorded where it is read.

    Returns CBP keys, NOT `MaskTarget`s: no QCEW cell is hidden here, so the regime scores nothing
    on its own. CORRECTED 2026-09-08 — this docstring used to say removal "turns §10.4 from an
    own-arm estimator into a declining one for that state-year". Measured, that produces ZERO
    additional declines (147 declined rows before and after): `CbpIntensity.weights` declines only
    when the ENTIRE `reference_year` is absent, and holing one state moves that cell to the
    declared fallback arm instead. The effect is also not local — `national_march_intensity` is a
    pooled ratio over surviving rows, so dropping one state's row moves every state's shrunk
    intensity in that year. RE-MEASURED 2026-09-09 at `seed=1024` WITH this sort in place: all
    1,080 non-declined `cbp_intensity` estimates across 2017-2023 move, max |delta| **459.5**
    employees, identical across three separate processes. The figure this docstring carried before
    was 421, taken from a draw made BEFORE the sort — and that number was never reproducible:
    three processes at the same seed gave max |delta| of 56.4, 384.1 and 102.4, and one of them
    moved only 921 of the 1,080. Both halves of the old claim were artifacts of the very
    nondeterminism this function is being fixed for. Quote the seed whenever you quote the figure.
    Confining the effect to the holed state-year would require handing the estimator an ungapped
    national value, which `fallback.resolve_intensity` does not permit; that is recorded, not
    fixed.

    SORT BEFORE SAMPLING. `unique()` gives no order guarantee, so a seeded sample over its output
    draws a different key set on EVERY CALL (measured 2026-09-09: six calls in one process, six
    distinct sets) — the same defect diagnosed and fixed twice in this file (`_clustered`,
    `_state_year`) for breaking §16.1's idempotence MUST. It survived here because the pair had no
    test and no caller. Measured 2026-09-08: three processes, three different 20-key sets before
    the sort and one after.
    """
    pool = (
        data.cbp_state_size.select("state_fips", "reference_year")
        .unique()
        .sort("state_fips", "reference_year")
    )
    drawn = pool.sample(
        n=min(config.validation.replicates_per_regime, pool.height),
        with_replacement=False,
        shuffle=True,
        seed=seed,
    )
    return [(r["state_fips"], r["reference_year"]) for r in drawn.iter_rows(named=True)]


def apply_cbp_gap(data: HarmonizedData, keys: Sequence[tuple[str, int]]) -> HarmonizedData:
    """Drop the named CBP state-years so §10.4 must fall back to the establishment arm.

    NOT "fall back or decline". M4 measured zero additional declines from this gap; the figure and
    its reasoning live in `cbp_size_gap_keys`'s docstring above and are deliberately NOT restated
    here, so the claim has one home to correct. A STATE-YEAR gap keyed on
    `(state_fips, reference_year)` and removed across all seven size codes.
    """
    if not keys:
        return data
    selector = pl.struct("state_fips", "reference_year").is_in(
        [{"state_fips": s, "reference_year": y} for s, y in keys]
    )
    return dataclasses.replace(data, cbp_state_size=data.cbp_state_size.filter(~selector))


_SELECTORS["structural_break"] = _structural_break
_SELECTORS["naics_transition"] = _naics_transition

# Built ONCE, at the foot of the module, after every selector is registered. There used to be a
# second comprehension above `select_targets` and a rebuild here, because `_structural_break` and
# `_naics_transition` are registered late; the first dict was always stale and only the rebuild was
# ever read. `RegimeSpec.__post_init__` now refuses a mechanism/selector mismatch, so the stale
# first pass would raise at import — which is the check working, and the reason there is one dict.
# `preliminary_to_final_vintage` stays out of `_SELECTORS` on purpose, so its disposition raises.
REGIME_SPECS: dict[str, RegimeSpec] = {
    name: RegimeSpec(
        name=name,
        disposition=REGIME_DISPOSITIONS[name],
        grain=_GRAINS.get(name, "single_month"),
        select=_SELECTORS.get(name),
        mechanism=_MECHANISMS.get(name, "qcew_mask"),
        no_score_reason=_NO_SCORE_REASONS.get(name),
    )
    for name in HOLDOUT_REGIMES
}
