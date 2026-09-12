import numpy as np

from logging_employment.validate.intervals import crps, empirical_interval, residual_ensemble


def test_the_ensemble_is_the_point_shifted_by_every_residual():
    ens = residual_ensemble(np.array([-10.0, 0.0, 10.0]), point=100.0)
    assert sorted(ens.tolist()) == [90.0, 100.0, 110.0]


def test_the_ensemble_subtracts_each_residual_because_truth_is_estimate_minus_residual():
    """`D-112`: a residual is `estimate - truth`, so the truth it predicts is `point - residual`.

    The pool is ONE-SIDED on purpose. The symmetric pool above sorts to the same ensemble under
    either sign, so it could not see the shipped `point + residual`.
    """
    ens = residual_ensemble(np.array([5.0, 20.0]), point=125.0)
    assert sorted(ens.tolist()) == [105.0, 120.0]


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


def test_the_closed_form_matches_the_pairwise_matrix():
    """The optimisation is an identity, so pin it against the definition it replaced.

    `crps` uses the sorted-ensemble form of `E|X - X'|`. If the two ever disagree the closed form
    is wrong, not merely slower — and every §13.7 CRPS in the scoreboard is wrong with it.
    """
    rng = np.random.default_rng(7)
    for size in (2, 3, 17, 200):
        ens = rng.normal(500.0, 120.0, size=size)
        for truth in (400.0, 500.0, 900.0):
            pairwise = np.abs(ens - truth).mean() - 0.5 * np.abs(ens[:, None] - ens[None, :]).mean()
            assert abs(crps(ens, truth) - pairwise) < 1e-9, (size, truth)


def test_the_closed_form_handles_a_clipped_ensemble():
    """Clipping at zero breaks shift-invariance, so the identity is checked on clipped input too."""
    ens = np.array([-40.0, -5.0, 0.0, 3.0, 90.0])
    clipped = np.maximum(ens, 0.0)
    pairwise = (
        np.abs(clipped - 10.0).mean() - 0.5 * np.abs(clipped[:, None] - clipped[None, :]).mean()
    )
    assert abs(crps(clipped, 10.0) - pairwise) < 1e-12
