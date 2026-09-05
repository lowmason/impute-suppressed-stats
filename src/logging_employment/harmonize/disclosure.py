"""The CBP disclosure regime, keyed by reference year, with a fail-closed lookup."""

from __future__ import annotations

from ..errors import UnknownDisclosureRegimeError

# Stage 0's `cbp_regime.regime_by_year`, which rests on Census's own methodology page: noise
# infusion documented continuously since reference year 2007, EMPFLAG discontinued "beginning in
# reference year 2018", and cells with fewer than three establishments dropped rather than flagged
# beginning 2017.
#
# This table restates a measurement rather than making one, so it is checked rather than trusted:
# `test_the_registry_is_exactly_what_stage_0_measured` re-derives it from the shipped copy of that
# audit summary, and a year Stage 0 labelled differently -- or could not label at all -- fails
# there rather than propagating silently into a parsed table.
#
# 2024 is absent rather than assumed, for two reasons Stage 0 recorded together: no 2024 CBP
# dataset exists to document (the dataset probe returned a real 404, and 2024 is absent from
# `years_available`), and methodology.html carries a banner stating its content "is no longer
# current" pending a U.S. Department of Commerce administrative order prohibiting the use of noise
# infusion. The second is why the 2018-2023 regime cannot simply be carried forward to a later
# year even once one is published.
CBP_REGIME_BY_YEAR: dict[int, str] = {
    2017: "noise_infusion_plus_suppression",
    2018: "noise_infusion",
    2019: "noise_infusion",
    2020: "noise_infusion",
    2021: "noise_infusion",
    2022: "noise_infusion",
    2023: "noise_infusion",
}

UNKNOWN_REGIME = "unknown"


def regime_for_year(year: int, *, fail_on_unknown: bool = True) -> str:
    """The disclosure regime for a CBP reference year.

    Halts on an unrecorded year (§18.3, SRC-CBP-003). `fail_on_unknown=False` returns the literal
    string `"unknown"` instead -- it exists so a caller can *record* the gap in a report, never so
    a pipeline can proceed past it, and the config key that reaches it defaults to failing. The
    string it returns is the same label Stage 0 used for a year it could not establish, so a
    report carrying it says what the audit said.
    """
    if year in CBP_REGIME_BY_YEAR:
        return CBP_REGIME_BY_YEAR[year]
    if fail_on_unknown:
        raise UnknownDisclosureRegimeError(
            f"CBP reference year {year} carries no established disclosure regime; refusing to "
            "parse its cells (SRC-CBP-003)"
        )
    return UNKNOWN_REGIME
