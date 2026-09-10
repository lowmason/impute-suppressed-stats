from tests.conftest import STAGED, requires_staged

from logging_employment.contracts import HarmonizedData
from logging_employment.validate.leakage import assert_no_future_rows
from logging_employment.validate.regimes import REGIME_SPECS, rolling_origin_frames


@requires_staged
def test_every_rolling_origin_frame_is_provably_past_only():
    """Stage 4's exit criterion, as an assertion over the truncated frame."""
    monthly = HarmonizedData.load(STAGED).qcew_monthly
    for origin, frame in rolling_origin_frames(monthly, origins=["2020-01", "2022-01"]):
        assert_no_future_rows(frame, origin=origin)
        assert frame.height < monthly.height


def test_retrospective_smoothing_is_declared_vacuous_not_silently_skipped():
    spec = REGIME_SPECS["retrospective_smoothing"]
    assert spec.disposition == "vacuous_on_registry"
    assert spec.select is None
