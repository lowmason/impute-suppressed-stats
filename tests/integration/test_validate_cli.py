"""The `validate` command: it scores what it was asked to, writes a manifest, and repeats bytes.

COST DEVIATION, stated rather than silent. The plan's version of these tests invokes the full
harness three times at `config.yaml`'s three seeds. These drive the real CLI end to end against a
ONE-SEED copy of the shipped config AND a two-estimator subset, which exercises the same wiring,
the same manifest and the same idempotence at a fraction of the cost. The three-seed, full-registry
acceptance run is Task 19 Step 3's job, and its numbers are recorded in the retired plan's
completion stamp rather than asserted here.

WHY THESE TWO ESTIMATORS, since the subset is what the coverage now rests on. §13.7's CRPS -- not
`run_baselines` -- is the harness's dominant cost, and it runs only for `metrics._INTERVAL_FAMILIES`.
`establishment_proportional` is outside those families and `share_last_observed` is inside them, so
one invocation still crosses both branches of `probabilistic_metrics` and the idempotence test
keeps covering the metric path that dominates the run. Both are §10.8 rungs (4 and 3). Measured
2026-09-07 on the D1 staged layer, one seed: 6.2 s for `establishment_proportional` alone, 49.6 s
for `share_last_observed` alone, 50.2 s for the pair, 226.6 s for all ten -- so the CRPS branch is
essentially the whole bill, and dropping it would buy an 8x that costs the coverage.
"""

import json
from pathlib import Path

import polars as pl
import pytest
import yaml
from typer.testing import CliRunner

from logging_employment.cli import app

REPO = Path(__file__).resolve().parents[2]
STAGED = REPO / "data" / "staged"

# One is interval-ineligible and one is not, so a single pass crosses both metric branches.
SUBSET = "establishment_proportional,share_last_observed"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (STAGED / "qcew_monthly.parquet").exists(),
        reason="data/staged is gitignored; the validate CLI needs the rebuilt tables",
    ),
]


@pytest.fixture(scope="module")
def one_seed_config(tmp_path_factory) -> Path:
    """The shipped config with a single seed, so the run is a third of the full harness.

    `storage.output_uri` is redirected into `tmp_path` the way `conftest.py`'s `staged_repo`
    redirects it, and for a reason this file learned the hard way: the shipped value is the
    RELATIVE string `runs`, which `run_dir` resolves against the process CWD, so a suite run
    from the repo root drove the real CLI into the working checkout's own `runs/` and left a
    run directory there. `staged_uri` is deliberately NOT redirected -- unlike `staged_repo`,
    this test wants the real staged layer whose absence skips the module.

    Redirecting MOVES the run id: `run_id` hashes `resolved_dict(cfg)` and `output_uri` is in
    that payload, so the id is now a function of `tmp_path_factory`'s per-session base directory
    and differs run to run. That is why `_metrics_path` derives it rather than naming it, and
    why no literal id may be written down here.
    """
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["validation"]["pseudo_suppression_seeds"] = [1024]
    root = tmp_path_factory.mktemp("validate-cli")
    raw["storage"]["output_uri"] = str(root / "runs")
    path = root / "config.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    return path


def _metrics_path(config: Path) -> Path:
    """The run directory this config AND this subset hash to, not whichever run sorts last.

    `max(runs/*/validation_metrics.parquet)` would pick up a run written by a DIFFERENT config
    and then assert against numbers this test never produced. The `--estimators` override has to
    be applied here for the same reason: it is part of the run id, so a subset run and a full one
    live in different directories.
    """
    from logging_employment.cli import _estimator_override, _input_digests
    from logging_employment.config import load_config
    from logging_employment.runs import run_dir, run_id

    cfg = load_config(config)
    identifier = run_id(cfg, _input_digests(cfg), overrides=_estimator_override(SUBSET))
    return run_dir(cfg, identifier) / "validation_metrics.parquet"


@pytest.fixture(scope="module")
def first_run(one_seed_config) -> tuple[Path, bytes]:
    """One CLI invocation, shared. The subset is what makes a second one affordable."""
    path = _metrics_path(one_seed_config)

    # Asserted BEFORE the invocation: a regression caught afterwards has already spent the whole
    # run writing the directory into the checkout, which is the one outcome this guards against.
    # It went unnoticed for so long because the id is DERIVED and never typed, so searches for the
    # literal id, for its file digests and for its row counts all returned nothing.
    #
    # Two assertions, because they catch different failures. Absoluteness is the real invariant --
    # the config named where to write rather than inheriting the process CWD -- and it holds no
    # matter which directory pytest was started from. The second catches a redirect that IS
    # absolute but still lands inside the checkout, and it must resolve first: `is_relative_to` is
    # purely lexical, so the relative `runs/<id>/...` this exists to catch is not "under" `REPO`
    # by that test until the CWD is applied. Both were measured against an unredirected config.
    assert path.is_absolute(), f"storage.output_uri left relative to the CWD: {path}"
    assert not path.resolve().is_relative_to(REPO), f"run artifact inside the checkout: {path}"

    result = CliRunner().invoke(
        app, ["validate", "--config", str(one_seed_config), "--estimators", SUBSET]
    )
    assert result.exit_code == 0, result.output
    assert path.exists(), f"no validation_metrics.parquet at {path}"
    return path, path.read_bytes()


def test_validate_writes_metrics_and_a_manifest(first_run):
    path, _ = first_run
    metrics = pl.read_parquet(path)
    assert metrics.height > 0
    assert metrics["denominator"].null_count() == 0

    manifest = json.loads((path.parent / "validation_manifest.json").read_text())
    assert "regimes" in manifest
    assert manifest["regimes"]["preliminary_to_final_vintage"]["disposition"] == "cannot_run_on_d1"
    # A refused regime records WHY and emits no scores — never an empty partition.
    assert manifest["regimes"]["preliminary_to_final_vintage"]["n_scored"] == 0
    assert manifest["regimes"]["preliminary_to_final_vintage"]["reason"]


def test_validate_scores_only_the_estimators_it_was_given(first_run):
    """The option has to reach `run_pseudo_suppression`, not just the run id.

    Asserted against the SCORES rather than the manifest: the manifest records the ids the CLI
    resolved, so a subset that was hashed into the run id and then dropped on the way to the
    harness would still be reported there. Only the scored rows say which estimators ran.
    """
    path, _ = first_run
    scores = pl.read_parquet(path.parent / "validation_scores.parquet")
    assert set(scores["estimator_id"].unique().to_list()) == set(SUBSET.split(","))

    # REGISTRY order, derived from REGISTRY. Sorting the typed list instead would pass on any
    # ordering the CLI happened to emit, which is the one thing this assertion is here to pin.
    from logging_employment.baselines.runner import REGISTRY

    asked = set(SUBSET.split(","))
    manifest = json.loads((path.parent / "validation_manifest.json").read_text())
    assert manifest["estimators"] == [e.estimator_id for e in REGISTRY if e.estimator_id in asked]

    # The subset must not COST a regime, which the estimator-id set alone cannot show. Every
    # regime the manifest says ran has to carry rows here, and carry them for BOTH estimators --
    # otherwise the module docstring's claim that one pass crosses both branches of
    # `probabilistic_metrics` would hold only for whichever regimes happened to score the
    # interval-eligible one, and the idempotence test's real coverage would be narrower than
    # the docstring says it is.
    ran = {name for name, entry in manifest["regimes"].items() if entry["replicates"]}
    per_regime = scores.group_by("regime").agg(pl.col("estimator_id").n_unique().alias("n"))
    assert set(per_regime["regime"].to_list()) == ran
    assert per_regime["n"].min() == len(asked)


def test_validate_is_idempotent_for_identical_inputs(one_seed_config, first_run):
    """§16.1's MUST, and the only test that could have caught the defect it did.

    Two selectors sampled from an UNORDERED frame (`unique()` / `group_by()` give no order
    guarantee), so a seeded draw picked a different month per PROCESS. Every within-process
    assertion passed — Polars returns the same arbitrary order twice in one interpreter — and only
    comparing the bytes of two separate CLI invocations saw it.
    """
    path, before = first_run
    second = CliRunner().invoke(
        app, ["validate", "--config", str(one_seed_config), "--estimators", SUBSET]
    )
    assert second.exit_code == 0, second.output
    assert path.read_bytes() == before
