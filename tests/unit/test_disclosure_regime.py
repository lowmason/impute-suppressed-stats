"""SRC-CBP-003: the regime is stored by reference year and an unknown one halts the run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logging_employment.errors import UnknownDisclosureRegimeError
from logging_employment.harmonize import disclosure

# Stage 0's `cbp_regime` summary, shipped here because it lives under the gitignored `data/`
# tree and a test cannot read it from a fresh clone otherwise.
AUDIT = json.loads(
    (
        Path(__file__).resolve().parents[1] / "fixtures" / "cbp" / "cbp_regime_summary.json"
    ).read_text()
)
MEASURED = AUDIT["findings"]["regime_by_year"]


def test_2017_carries_both_mechanisms() -> None:
    assert disclosure.regime_for_year(2017) == "noise_infusion_plus_suppression"


def test_2018_through_2023_are_noise_infusion() -> None:
    assert {disclosure.regime_for_year(y) for y in range(2018, 2024)} == {"noise_infusion"}


def test_2024_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureRegimeError, match="2024"):
        disclosure.regime_for_year(2024)


def test_a_year_outside_the_registry_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureRegimeError, match="2031"):
        disclosure.regime_for_year(2031)


def test_the_gate_can_be_opened_only_explicitly() -> None:
    assert disclosure.regime_for_year(2024, fail_on_unknown=False) == "unknown"


def test_the_registry_is_exactly_what_stage_0_measured() -> None:
    # Derived, not trusted: the registry is a table of facts about Census documentation, and the
    # run that read that documentation is the only thing entitled to state them. A year Stage 0
    # labelled, a label it chose, or a year it left unknown all move this assertion.
    established = {int(y): e["regime"] for y, e in MEASURED.items() if e["regime"] != "unknown"}
    assert disclosure.CBP_REGIME_BY_YEAR == established


def test_the_years_stage_0_could_not_establish_are_absent_rather_than_defaulted() -> None:
    unknown = {int(y) for y, e in MEASURED.items() if e["regime"] == "unknown"}
    assert unknown
    assert unknown.isdisjoint(disclosure.CBP_REGIME_BY_YEAR)
    for year in unknown:
        with pytest.raises(UnknownDisclosureRegimeError, match=str(year)):
            disclosure.regime_for_year(year)


def test_every_established_year_carries_a_citation() -> None:
    # SRC-CBP-003 stores a regime; a regime with no cited source is an assertion, not a finding.
    for year, entry in MEASURED.items():
        if entry["regime"] != "unknown":
            assert entry["citation"].startswith("https://"), year


def test_the_window_years_are_all_covered_or_explicitly_unknown() -> None:
    # D1's pilot window is 2017-01 to 2024-12, so every one of those years must be decided one
    # way or the other -- never simply missing from the registry with no recorded reason.
    for year in range(2017, 2025):
        assert str(year) in MEASURED
        assert (
            disclosure.regime_for_year(year, fail_on_unknown=False) == MEASURED[str(year)]["regime"]
        )
