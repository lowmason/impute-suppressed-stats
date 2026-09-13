"""§13.2 steps 4 and 6 and §13.5 for the §9.3 parent margin (R-PM-3).

No `data/`. Every test builds a one-month layer with three published states and their private `113`
parents. '01' has two establishments besides its `113310` child, so its parent stays public under a
mask; '02' has none, so its parent equals the child and must be hidden with it; '06' is never masked.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY, run_baselines, state_total_bounds
from logging_employment.config import load_config
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import ConstraintDataError, LeakageError
from logging_employment.validate import harness
from logging_employment.validate.harness import reject_exactly_recoverable
from logging_employment.validate.leakage import assert_no_retained_truth
from logging_employment.validate.mask import MaskTarget, apply_mask
from logging_employment.validate.recover import assert_truth_within_bounds, mask_and_solve
from logging_employment.validate.regimes import REGIME_SPECS

REPO = Path(__file__).resolve().parents[2]
MONTH = "2024-03"


def _layer(make_monthly, make_size, *, value_01: int = 100, parent_01: int = 150) -> HarmonizedData:
    """Three published states and the nation in one month, each state under a private `113` parent."""
    at = {"reference_month": MONTH}
    states = (("01", value_01, 10), ("02", 50, 5), ("06", 250, 15))
    national = {
        "area_type": "national",
        "area_fips": "US000",
        "state_fips": None,
        "aggregation_level": "18",
        "employment_value": sum(value for _, value, _ in states),
        "employment_raw": str(sum(value for _, value, _ in states)),
        "qtrly_establishments": sum(count for _, _, count in states),
    }
    monthly = make_monthly(
        at | national,
        *[
            at
            | {
                "state_fips": state,
                "area_fips": f"{state}000",
                "employment_value": value,
                "employment_raw": str(value),
                "qtrly_establishments": count,
            }
            for state, value, count in states
        ],
    )
    parents = (("01", parent_01, 12), ("02", 50, 5), ("06", 300, 18))
    parent = make_monthly(
        *[
            at
            | {
                "state_fips": state,
                "area_fips": f"{state}000",
                "industry_code": "113",
                "aggregation_level": "55",
                "employment_value": value,
                "employment_raw": str(value),
                "qtrly_establishments": count,
            }
            for state, value, count in parents
        ]
    )
    return HarmonizedData(
        qcew_monthly=monthly,
        qcew_national_size=make_size(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
        qcew_state_parent=parent,
    )


def _target(state: str, label: str = "primary_like") -> MaskTarget:
    return MaskTarget(state, MONTH, "state_total", label)


def test_a_parent_with_other_establishments_stays_published_under_the_mask(make_monthly, make_size):
    """Step 4: '01''s parent is public in reality and stays public, as on 252 of 409 real cases."""
    data = _layer(make_monthly, make_size)
    masked, _ = apply_mask(data, [_target("01")])
    assert masked.qcew_state_parent.equals(data.qcew_state_parent)


def test_a_parent_whose_establishments_are_all_the_masked_cells_is_hidden_with_it(
    make_monthly, make_size
):
    """Step 4: '02''s parent equals the withheld value, so leaving it public would hand it back."""
    data = _layer(make_monthly, make_size)
    masked, truth = apply_mask(data, [_target("02")])
    parent = data.qcew_state_parent.filter(pl.col("state_fips") == "02")
    assert parent["employment_value"].item() == truth["truth"].item()
    hidden = masked.qcew_state_parent.filter(pl.col("state_fips") == "02").row(0, named=True)
    assert hidden["observation_status"] == "suppressed"
    assert hidden["employment_value"] is None
    assert hidden["disclosure_code"] == "N"
    assert hidden["suppression_type"] == "complementary_like"
    others = pl.col("state_fips") != "02"
    assert masked.qcew_state_parent.filter(others).equals(data.qcew_state_parent.filter(others))


def test_the_leakage_guard_refuses_a_masked_layer_that_left_such_a_parent_published(
    make_monthly, make_size
):
    """§13.4 bullet 2: the guard re-applies the rule, so a mask that skipped it cannot pass."""
    data = _layer(make_monthly, make_size)
    masked, truth = apply_mask(data, [_target("02")])
    assert_no_retained_truth(masked, truth)
    leaky = dataclasses.replace(masked, qcew_state_parent=data.qcew_state_parent)
    with pytest.raises(LeakageError, match="02/2024-03"):
        assert_no_retained_truth(leaky, truth)


def test_a_masked_cell_is_bounded_by_its_visible_parent_and_not_by_a_hidden_one(
    make_monthly, make_size
):
    """Steps 4-5: '01' comes back `[0, 150]`; '02', its parent hidden with it, stays `unbounded`."""
    system = mask_and_solve(
        _layer(make_monthly, make_size),
        [_target("01"), _target("02", "complementary_like")],
        load_config(REPO / "config.yaml"),
    )
    state = {
        row["cell_id"].split("|")[1]: row
        for row in system.bounds.filter(
            pl.col("cell_id").str.starts_with("state_total|")
        ).iter_rows(named=True)
    }
    assert (state["01"]["selected_lower"], state["01"]["selected_upper"]) == (0.0, 150.0)
    assert state["02"]["bound_status"] == "unbounded"
    assert system.recoverable.is_empty()


def test_a_target_its_visible_parent_pins_is_returned_for_rejection(make_monthly, make_size):
    """Step 6: a parent published at 0 with other establishments pins its child to exactly 0."""
    system = mask_and_solve(
        _layer(make_monthly, make_size, value_01=0, parent_01=0),
        [_target("01")],
        load_config(REPO / "config.yaml"),
    )
    assert system.recoverable.rows() == [("01", MONTH)]


def test_a_truth_above_its_visible_parent_halts_mask_and_solve(make_monthly, make_size):
    """§13.5 through `mask_and_solve`: the check runs on every masked solve, not only when called.

    '01' is withheld at 200 under a published parent of 150, so its masked bound `[0, 150]`
    excludes the truth. The direct tests below pin what `assert_truth_within_bounds` refuses; this
    one pins that `mask_and_solve` calls it.
    """
    data = _layer(make_monthly, make_size, value_01=200, parent_01=150)
    with pytest.raises(ConstraintDataError, match="outside their masked deterministic bounds"):
        mask_and_solve(data, [_target("01")], load_config(REPO / "config.yaml"))


def _located(truth: int, lower: float | None, upper: float | None) -> pl.DataFrame:
    """One withheld cell beside its masked bounds, in the shape `locate_withheld` returns."""
    found = lower is not None
    return pl.DataFrame(
        {
            "state_fips": ["01"],
            "reference_month": [MONTH],
            "truth": [truth],
            "cell_id": ["state_total|01|2024-03|5|113310|NAICS 2022|ALL" if found else None],
            "selected_lower": [lower],
            "selected_upper": [upper],
            "bound_status": ["partially_identified" if found else None],
        },
        schema={
            "state_fips": pl.String,
            "reference_month": pl.String,
            "truth": pl.Int64,
            "cell_id": pl.String,
            "selected_lower": pl.Float64,
            "selected_upper": pl.Float64,
            "bound_status": pl.String,
        },
    )


def test_a_withheld_truth_outside_its_masked_bounds_halts_the_run():
    """§13.5: a known pseudo-hidden truth outside the deterministic bounds is a constraint-data bug."""
    assert_truth_within_bounds(_located(150, 0.0, 150.0), tolerance=1e-7)
    assert_truth_within_bounds(_located(9_999, 0.0, None), tolerance=1e-7)
    with pytest.raises(ConstraintDataError, match="outside their masked deterministic bounds"):
        assert_truth_within_bounds(_located(151, 0.0, 150.0), tolerance=1e-7)


def test_a_withheld_cell_with_no_masked_bound_halts_rather_than_passing_unchecked():
    with pytest.raises(ConstraintDataError, match="no masked bound"):
        assert_truth_within_bounds(_located(10, None, None), tolerance=1e-7)


def test_rejected_cells_leave_the_scored_rows_and_are_counted():
    scored = pl.DataFrame(
        {
            "state_fips": ["01", "01", "06"],
            "reference_month": [MONTH] * 3,
            "estimator_id": ["a", "b", "a"],
        }
    )
    kept, rejected = reject_exactly_recoverable(
        scored, pl.DataFrame({"state_fips": ["01"], "reference_month": [MONTH]})
    )
    assert (kept["state_fips"].to_list(), rejected) == (["06"], 1)
    untouched, none = reject_exactly_recoverable(
        scored, pl.DataFrame(schema={"state_fips": pl.String, "reference_month": pl.String})
    )
    assert untouched.equals(scored) and none == 0


def _proportional():
    """The one estimator these layers can feed: it reads nothing but the month's establishments."""
    return [e for e in REGISTRY if e.estimator_id == "establishment_proportional"]


def test_the_exact_recovery_rate_counts_the_targets_step_6_rejects(
    make_monthly, make_size, monkeypatch
):
    """§13.5 measures what §13.2 step 6 then rejects, so it is computed before the rejection.

    '01''s visible parent is published at 0 beside other establishments, pinning '01' to exactly 0;
    '06''s parent leaves it `[0, 300]`. Of the two masked cells one is exactly recoverable, so every
    replicate's rate is 1/2 and '01' leaves the scored rows. Read off the kept rows, the rate was 0
    whenever the rejection worked.

    The leakage tripwire is switched off here, and only here, because on the state arm it refuses
    every target this test needs. A suppressed state cell's lower bound is 0, so exact recovery
    means a zero truth; `mask._hide` writes the literal `"0"` a real `N` row publishes into
    `employment_raw`, and `assert_no_retained_truth` compares by value. Filed as a deferred item.
    """
    targets = [_target("01"), _target("06")]
    only = {"small_cell_biased": REGIME_SPECS["small_cell_biased"]}
    monkeypatch.setattr(harness, "REGIME_SPECS", only)
    monkeypatch.setattr(harness, "select_targets", lambda *args, **kwargs: targets)
    monkeypatch.setattr(harness, "assert_no_retained_truth", lambda *args, **kwargs: None)
    config = load_config(REPO / "config.yaml")
    replicates = len(config.validation.pseudo_suppression_seeds)

    result = harness.run_pseudo_suppression(
        _layer(make_monthly, make_size, value_01=0, parent_01=0), _proportional(), config
    )

    rates = result.metrics.filter(pl.col("metric_name") == "exact_recovery_rate")["value"]
    assert rates.len() == replicates
    assert set(rates.to_list()) == {0.5}
    assert set(result.scores["state_fips"].to_list()) == {"06"}
    entry = result.manifest["regimes"]["small_cell_biased"]
    assert entry["rejected_exactly_recoverable"] == replicates


def test_a_visible_parent_that_binds_rescales_the_estimate_masked_under_it(make_monthly, make_size):
    """D-087's composite path without `data/`: masked bounds, a binding bound, a rescaled estimate.

    '01' and '06' are masked under visible parents of 120 and 300, and the month's residual is
    400 - 50 = 350. Split in proportion to their establishments, 10 and 15, '01' would get 140;
    under its masked bound §12.3 scales it back to 120 and hands the remainder to '06'.
    """
    data = _layer(make_monthly, make_size, parent_01=120)
    targets = [_target("01"), _target("06")]
    config = load_config(REPO / "config.yaml")
    masked, _ = apply_mask(data, targets)
    system = mask_and_solve(data, targets, config)

    def estimates(**kwargs: object) -> dict[str, float]:
        results, _ = run_baselines(masked, config, estimators=_proportional(), **kwargs)
        return dict(results.select("state_fips", "estimate").iter_rows())

    assert estimates() == pytest.approx({"01": 140.0, "06": 210.0})
    bounded = estimates(bounds=state_total_bounds(system.bounds))
    assert bounded == pytest.approx({"01": 120.0, "06": 230.0})
