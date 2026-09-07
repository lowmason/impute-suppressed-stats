"""§17.4 row 4 and §17.6: every baseline on a frozen fixture, pinned to golden output.

THIS FILE IS THE UNITS-AND-MAGNITUDE REGRESSION NET. `EmployeeWeights` carries the composite's
unit claim structurally, but a type cannot see a corrupt source column or a CBP vintage that moves
an intensity -- both change the NUMBERS while every arm stays honestly typed. Since
`MAX_SCALE_RATIO` was removed (see `specs/estimator-composition.md` R-COMP-3), the golden below is
the only check that would redden on either. Re-pinning it is therefore a decision about the data,
not a chore: §17.6 requires a documented reason and reviewer approval, and the reason belongs in
the commit that regenerates the file.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.baselines.runner import REGISTRY, run_baselines
from logging_employment.build import deterministic_order
from logging_employment.contracts import HarmonizedData

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "baselines"


@pytest.fixture()
def frozen_harmonized() -> HarmonizedData:
    """The committed twelve-month fixture, loaded from tracked files.

    Loaded from `tests/fixtures/baselines/`, which is IN GIT — not sliced out of `data/staged`,
    which is gitignored. A golden pinned to untracked, rebuildable data is not frozen: it would
    pass on the machine that produced it and fail, or silently re-pin, anywhere else.
    """
    return HarmonizedData.load(FIXTURES)


def test_every_baseline_runs_or_declines_cleanly_on_the_frozen_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    """§17.4 row 4. A DECLINE IS A PASS.

    §10.5 declines on this window by design. A test that treated a decline as a failure would be
    weakened or would start excluding those baselines, and either way the criterion "run every
    baseline" stops meaning anything.
    """
    results, _ = run_baselines(frozen_harmonized, appendix_a_config)
    seen = set(results["estimator_id"].unique().to_list())
    assert seen == {e.estimator_id for e in REGISTRY}
    for estimator_id in seen:
        rows = results.filter(pl.col("estimator_id") == estimator_id)
        statuses = set(rows["reconciliation_status"].unique().to_list())
        assert statuses <= {"anchored_and_reconciled", "declined"}
        if statuses == {"declined"}:
            assert rows["decline_reason"].null_count() == 0


def test_the_baseline_output_matches_its_golden_fixture(
    frozen_harmonized, appendix_a_config
) -> None:
    """§17.6 golden coverage for baseline predictions and reconciliation.

    Also the units-and-magnitude regression net described in this module's docstring: a source
    column or a CBP vintage that moves an intensity redden here or nowhere.

    The in-memory frame is put into the writer's own row order before comparing.
    `run_baselines` returns rows in emission order (month, then estimator) while
    `write_parquet_deterministic` sorts on write, so a direct `.equals` is False even when every
    value agrees. Reusing `deterministic_order` rather than re-sorting by hand keeps the test
    from drifting away from the writer it is checking.
    """
    results, _ = run_baselines(frozen_harmonized, appendix_a_config)
    golden = pl.read_parquet(FIXTURES / "baseline_results_golden.parquet")
    assert deterministic_order(results).equals(golden)


def test_the_anchor_audit_matches_its_golden_fixture(frozen_harmonized, appendix_a_config) -> None:
    """The audit is already emitted one row per month in sorted order, so it needs no re-sort."""
    _, audit = run_baselines(frozen_harmonized, appendix_a_config)
    golden = pl.read_parquet(FIXTURES / "anchor_audit_golden.parquet")
    assert deterministic_order(audit).equals(golden)


def test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data() -> None:
    """The property that makes the two goldens above mean anything.

    `data/` is gitignored. If these fixtures were produced by slicing it at test time, the golden
    would be pinned to whatever that machine last rebuilt, and a fresh clone could not run this
    file at all.
    """
    for name in (
        "qcew_monthly",
        "qcew_national_size",
        "cbp_state_size",
        "bridge",
        "baseline_results_golden",
        "anchor_audit_golden",
    ):
        assert (FIXTURES / f"{name}.parquet").exists()
