import numpy as np

from logging_employment.validate.intervals import crps, empirical_interval, residual_ensemble


def test_the_ensemble_is_the_point_shifted_by_every_residual():
    ens = residual_ensemble(np.array([-10.0, 0.0, 10.0]), point=100.0)
    assert sorted(ens.tolist()) == [90.0, 100.0, 110.0]


def test_a_wider_level_gives_a_wider_interval():
    ens = residual_ensemble(np.linspace(-50, 50, 201), point=100.0)
    lo50, hi50 = empirical_interval(ens, 0.50)
    lo90, hi90 = empirical_interval(ens, 0.90)
    assert (hi90 - lo90) > (hi50 - lo50)


def test_crps_is_zero_for_a_point_mass_at_the_truth():
    assert crps(np.array([7.0] * 100), truth=7.0) < 1e-9


def test_crps_grows_as_the_ensemble_moves_away():
    ens = np.array([10.0] * 100)
    assert crps(ens, truth=20.0) > crps(ens, truth=12.0)
