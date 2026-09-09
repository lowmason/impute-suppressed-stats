"""§13.4's guards must survive `python -O`, which strips a bare `assert` statement."""

import subprocess
import sys
import textwrap

import polars as pl
import pytest

from logging_employment.contracts import HarmonizedData
from logging_employment.errors import LeakageError
from logging_employment.validate.leakage import assert_no_future_rows, assert_no_retained_truth

# The source the `-O` subprocesses run. Module level and NOT indented, so `textwrap.dedent` over a
# concatenation of this and an indented half finds a common prefix of "" and strips nothing.
_RETAINING_FRAME = """
import polars as pl
from logging_employment.contracts import HarmonizedData
from logging_employment.errors import LeakageError
from logging_employment.validate.leakage import assert_no_retained_truth

data = HarmonizedData(
    qcew_monthly=pl.DataFrame(
        {"state_fips": ["41"], "reference_month": ["2019-06"], "employment_value": [58]}
    ),
    qcew_national_size=pl.DataFrame(),
    cbp_state_size=pl.DataFrame(),
    bridge=pl.DataFrame(),
)
truth = pl.DataFrame(
    {"state_fips": ["41"], "reference_month": ["2019-06"], "truth": [58]}
)
"""


def test_a_future_row_is_refused_with_a_typed_error():
    frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
    with pytest.raises(LeakageError, match="future"):
        assert_no_future_rows(frame, origin="2020-01")


def test_the_guard_still_refuses_under_dash_o():
    """M14: a bare `assert` vanishes under -O, so the guard on the live path was strippable.

    Run in a SUBPROCESS because -O is decided at interpreter start: `sys.flags.optimize` cannot be
    changed from inside a running test session, so an in-process test would assert nothing. The
    `__debug__` line is what makes the flag load-bearing — without it this test passes identically
    with `-O` deleted, because after the typed conversion the guard raises on every interpreter.
    """
    program = textwrap.dedent(
        """
        import polars as pl
        from logging_employment.errors import LeakageError
        from logging_employment.validate.leakage import assert_no_future_rows

        if __debug__:
            raise SystemExit("this subprocess is not optimized; -O did not take")
        frame = pl.DataFrame({"reference_month": ["2019-12", "2020-01"]})
        try:
            assert_no_future_rows(frame, origin="2020-01")
        except LeakageError:
            print("REFUSED")
        else:
            print("PASSED")
        """
    )
    done = subprocess.run(
        [sys.executable, "-O", "-c", program], capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "REFUSED"


# V5 IS ABOUT THE OTHER GUARD. Spec V5 (`specs/stage4-harness-completion.md`) requires a test that
# "feeding retained truth to `assert_no_retained_truth` raises under `-O`" — and that is the guard
# with the live `src/` caller (`harness.py`, inside the scoring loop). `assert_no_future_rows` has
# ZERO callers in `src/` until Task 5 of plan 12. The two tests above therefore witness the guard
# that is NOT on the shipped path; these two witness the one that is.


def _masked_frame_that_retains_the_truth() -> tuple[HarmonizedData, pl.DataFrame]:
    """A one-row frame whose `employment_value` still equals the held-out value."""
    data = HarmonizedData(
        qcew_monthly=pl.DataFrame(
            {"state_fips": ["41"], "reference_month": ["2019-06"], "employment_value": [58]}
        ),
        qcew_national_size=pl.DataFrame(),
        cbp_state_size=pl.DataFrame(),
        bridge=pl.DataFrame(),
    )
    truth = pl.DataFrame({"state_fips": ["41"], "reference_month": ["2019-06"], "truth": [58]})
    return data, truth


def test_retained_truth_raises_a_typed_error():
    data, truth = _masked_frame_that_retains_the_truth()
    with pytest.raises(LeakageError, match="employment_value"):
        assert_no_retained_truth(data, truth)


def test_the_retained_truth_guard_still_fires_under_python_O():
    """V5, and the ONLY test here where the `-O` flag is load-bearing.

    `if __debug__: raise SystemExit(...)` is the whole point. Without it this test passes
    identically with `-O` deleted — because after the typed conversion the guard raises
    `LeakageError` on every interpreter, so "it raised" witnesses the typed conversion, not the
    optimisation. The `__debug__` check proves the subprocess really was optimised before the guard
    was called.
    """
    # Dedent ONLY the appended half. `_RETAINING_FRAME` already sits at column 0, so dedenting the
    # CONCATENATION finds a common prefix of "" and strips nothing, leaving this half indented and
    # the subprocess dying on `IndentationError: unexpected indent`. Measured 2026-09-09 — the
    # draft this test came from had it the other way round and could not run.
    script = _RETAINING_FRAME + textwrap.dedent(
        """
        if __debug__:
            raise SystemExit("this subprocess is not optimized; -O did not take")
        try:
            assert_no_retained_truth(data, truth)
        except LeakageError:
            print("raised")
        else:
            raise SystemExit("the guard did not fire under -O")
        """
    )
    result = subprocess.run([sys.executable, "-O", "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "raised"
