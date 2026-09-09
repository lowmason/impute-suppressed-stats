"""The rolling-origin generator's refusals, on the committed fixture layer."""

from pathlib import Path

import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConceptViolationError
from logging_employment.validate.regimes import rolling_origin_frames, rolling_origins

FIXTURE = Path("tests/fixtures/baselines")


def _monthly() -> pl.DataFrame:
    return HarmonizedData.load(FIXTURE).qcew_monthly


def test_a_malformed_origin_is_refused_on_the_bare_call():
    """M2: `origins=['banana']` used to truncate nothing and pass the future-row guard.

    Asserted on the BARE call, with no iteration: a refusal that only fires once a caller consumes
    the generator is not a guard, and inlining it into the generator body is exactly that bug.
    """
    # Anchored on the INTERPOLATED value, not the word: the refusal's own hardcoded audit note
    # contains the string `origins=['banana']`, so `match="banana"` would pass even if the message
    # never named the origin the caller passed.
    with pytest.raises(ConceptViolationError, match=r"origin\(s\) \['banana'\]"):
        rolling_origin_frames(_monthly(), origins=["banana"])


def test_a_well_formed_origin_outside_the_panel_is_refused():
    """The case M2 does not name: '2099-01' parses, truncates nothing, and passed."""
    with pytest.raises(ConceptViolationError, match="2099-01"):
        rolling_origin_frames(_monthly(), origins=["2099-01"])


def test_an_in_panel_origin_still_yields_a_past_only_frame():
    monthly = _monthly()
    produced = list(rolling_origin_frames(monthly, origins=["2023-07"]))
    assert len(produced) == 1
    origin, frame = produced[0]
    assert origin == "2023-07"
    assert frame.height < monthly.height
    assert frame.filter(pl.col("reference_month") >= "2023-07").height == 0


def test_the_fixture_panel_yields_no_origin_because_it_is_one_year_long():
    """Measured: `tests/fixtures/baselines` carries 2023-01..2023-12 and nothing before it.

    So the guard is VACUOUS on the fixture and binding on D1, and the manifest records which. A
    January with no history behind it would truncate to an empty frame, which proves nothing.
    """
    cfg = load_config(Path("config.yaml"))
    assert rolling_origins(_monthly(), config=cfg) == ()


def test_origins_are_januaries_with_enough_history_behind_them():
    """Derived from a synthetic panel, so the expectation does not restate the implementation."""
    cfg = load_config(Path("config.yaml"))
    months = [f"{year}-{month:02d}" for year in (2019, 2020, 2021) for month in range(1, 13)]
    monthly = pl.DataFrame({"reference_month": months})
    # 2019-01 sits at index 0, below the 6-month floor; 2020-01 and 2021-01 clear it.
    assert rolling_origins(monthly, config=cfg) == ("2020-01", "2021-01")


def test_every_derived_origin_is_accepted_by_the_generator():
    """The two functions compose: nothing `rolling_origins` returns can trip Task 2's refusal."""
    cfg = load_config(Path("config.yaml"))
    months = [f"{year}-{month:02d}" for year in (2019, 2020) for month in range(1, 13)]
    monthly = pl.DataFrame({"reference_month": months})
    origins = rolling_origins(monthly, config=cfg)
    assert [origin for origin, _ in rolling_origin_frames(monthly, origins=origins)] == list(
        origins
    )
