"""§16.1 for §13.5-13.6's reductions: every sum is exactly rounded, so no value depends on chunking.

Polars splits a derived Series such as `(estimate - truth).abs()` into one chunk per thread, and
`.sum()` / `.mean()` round per chunk -- so the same scores gave `validation_metrics` values that
moved in the last ulp with `POLARS_MAX_THREADS` (56 of 1,490 golden rows at 4 threads, 2026-09-13).
`math.fsum` is exactly rounded, which makes the result a function of the VALUES alone: the chunk
layout, the thread count and the platform all drop out.

Chunking itself cannot be provoked from a unit test -- a six-row Series is never split, and the
pool size is fixed when polars loads -- so these pin the stronger property that implies it. Ten
0.1s are enough: a single-chunk polars mean of them is 0.09999999999999999, and the exactly rounded
one is 0.1. Expectations are computed from plain Python lists with `math.fsum`, never from a frame.
"""

import math

import polars as pl
import pytest

from logging_employment.validate.metrics import bound_metrics, point_metrics

N = 10
TRUTH = [1.0] * N
NATIONAL = 1000.0


def _point(estimate, truth):
    scores = pl.DataFrame(
        {
            "estimator_id": ["a"] * N,
            "cell_id": [f"c{i}" for i in range(N)],
            "state_fips": ["06"] * N,
            "reference_month": ["2019-03"] * N,
            "truth": truth,
            "estimate": estimate,
            "decline_kind": [None] * N,
        },
        schema_overrides={"decline_kind": pl.String},
    )
    national = pl.DataFrame({"reference_month": ["2019-03"], "national_employment": [NATIONAL]})
    out = point_metrics(
        scores, regime="small_cell_biased", seed=1, arm="state_total", national_totals=national
    )
    return out.filter(pl.col("stratum_kind") == "overall")


def _value(frame, name):
    return frame.filter(pl.col("metric_name") == name)["value"].item()


def test_ten_errors_of_one_tenth_have_a_mean_of_exactly_one_tenth():
    """The hand-derived anchor: no oracle, just the number a reader expects."""
    out = _point(estimate=[0.1] * N, truth=[0.0] * N)
    assert _value(out, "bias") == 0.1
    assert _value(out, "mae") == 0.1


@pytest.mark.parametrize(
    ("name", "offset", "expected"),
    # Each offset is one a single-chunk polars reduction mis-rounds FOR THAT METRIC (measured
    # 2026-09-13): no one offset discriminates all five, and a case that passes under the old code
    # pins nothing. 1.3 - 1.0 == 0.30000000000000004 and 1.1 - 1.0 == 0.10000000000000009 exactly.
    [
        ("mae", 0.3, lambda err: math.fsum(abs(e) for e in err) / N),
        ("bias", 0.3, lambda err: math.fsum(err) / N),
        ("rmse", 0.1, lambda err: math.sqrt(math.fsum(e * e for e in err) / N)),
        ("wape", 0.3, lambda err: math.fsum(abs(e) for e in err) / math.fsum(TRUTH)),
        (
            "state_share_absolute_error",
            0.1,
            lambda err: math.fsum(abs(e) / NATIONAL for e in err) / N,
        ),
    ],
)
def test_each_point_metric_is_the_exactly_rounded_reduction(name, offset, expected):
    estimate = [t + offset for t in TRUTH]
    err = [e - t for e, t in zip(estimate, TRUTH, strict=True)]
    assert _value(_point(estimate, TRUTH), name) == expected(err)


def test_the_mean_feasible_width_is_exactly_rounded():
    scores = pl.DataFrame(
        {
            "estimator_id": ["equal_residual"] * N,
            "cell_id": [f"c{i}" for i in range(N)],
            "truth": [0.05] * N,
            "selected_lower": [0.0] * N,
            "selected_upper": [0.1] * N,
            "bound_status": ["bounded"] * N,
        }
    )
    out = bound_metrics(scores, regime="cbp_size_gaps", seed=1, arm="national_size")
    assert _value(out, "mean_feasible_width") == 0.1
