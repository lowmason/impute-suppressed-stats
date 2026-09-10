"""The `logging-estimates` command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from .config import load_config

if TYPE_CHECKING:  # annotations only; keeps CLI start-up cheap
    from collections.abc import Mapping

    from .config import Config

app = typer.Typer(add_completion=False, help="Monthly state Logging employment estimates.")


@app.callback()
def main() -> None:
    """Pin the app as a command group.

    Typer collapses a one-command app into a bare top-level command, which would make
    `logging-estimates validate-config` invalid today and valid once a second command lands.
    The callback fixes the invocation syntax regardless of how many commands are registered.
    """


@app.command("validate-config")
def validate_config(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Parse the configuration and report the resolved estimand."""
    cfg = load_config(config)
    typer.echo(
        f"OK: {cfg.project.industry_code_used} / {cfg.project.ownership} / "
        f"{cfg.project.geography_universe} / {cfg.project.start_month}..{cfg.project.end_month}"
    )


registry_app = typer.Typer(help="Source registry commands.")
app.add_typer(registry_app, name="registry")


@registry_app.command("verify")
def registry_verify(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Check the seed registry against §7.1 and report every problem found."""
    from .registry.loader import load_registry
    from .registry.validation import verify

    load_config(config)
    seed = Path(__file__).parent / "registry" / "sources.yaml"
    problems = verify(load_registry(seed))
    for problem in problems:
        typer.echo(f"PROBLEM: {problem}")
    if problems:
        raise typer.Exit(code=1)
    typer.echo("OK: registry verified")


@app.command("fetch")
def fetch(
    source: str = typer.Option(..., "--source", help="qcew, qcew_size, or cbp"),
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Acquire raw bytes for one source into the immutable store and record a snapshot row."""
    if source not in {"qcew", "qcew_size", "cbp"}:
        raise typer.BadParameter(f"unknown source {source!r}")
    from .fetching import fetch_source

    cfg = load_config(config)
    rows = fetch_source(source, cfg, env_path=Path(".env"))
    typer.echo(f"{source}: {len(rows)} snapshot row(s) -> {cfg.storage.raw_uri}")


@app.command("build-harmonized")
def build_harmonized_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Assemble the harmonized Parquet layer from stored raw bytes and print output hashes."""
    from .build import build_harmonized

    cfg = load_config(config)
    hashes = build_harmonized(
        cfg,
        raw_root=Path(cfg.storage.raw_uri),
        out_root=Path(cfg.storage.staged_uri),
        manifest_path=Path(cfg.storage.output_uri) / "source_manifest.parquet",
    )
    for table, digest in sorted(hashes.items()):
        typer.echo(f"{table} {digest}")


def _constraints_dir(cfg: Config) -> Path:
    """§6.2's `data/constraints/`, read from `storage.constraints_uri`."""
    return Path(cfg.storage.constraints_uri)


def _write_manifest(path: Path, payload: Mapping[str, object]) -> None:
    """Write one run manifest, stamped with the code identity that produced it.

    THE point of funnelling all five manifests through one writer. `run_id` covers config and
    input data but deliberately not source (`runs.code_provenance`), so `code_commit` and
    `uv_lock_sha256` are the only things in `runs/<id>/` that can answer "was this directory
    written by the code I am reading?". A per-command `json.dumps` at each site made adding them
    five edits, and made forgetting them on the sixth manifest the default outcome.

    The stamp is merged LAST so no caller can shadow or drop it, and the JSON keeps the
    `indent=2, sort_keys=True` shape every one of these files already had -- `solve-bounds` reads
    `schema_manifest.json` as a precondition gate and an integration test pins its bytes, so the
    formatting is not free to drift.
    """
    import json

    from .runs import code_provenance

    path.write_text(json.dumps({**payload, **code_provenance()}, indent=2, sort_keys=True))


def _input_digests(cfg: Config) -> dict[str, str]:
    """A sha256 per harmonized input, which is what makes the run id a function of the data."""
    import hashlib

    staged = Path(cfg.storage.staged_uri)
    return {
        path.stem: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(staged.glob("*.parquet"))
    }


@app.command("build-constraints")
def build_constraints_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Assemble the constraint system from the harmonized layer and persist it."""

    import highspy
    import yaml

    from .build import write_parquet_deterministic
    from .config import resolved_dict
    from .constraints import graph
    from .constraints.system import build_constraint_system
    from .contracts import (
        CONSTRAINT_COEFFICIENT_SCHEMA,
        CONSTRAINT_ROW_SCHEMA,
        TARGET_CELL_SCHEMA,
        HarmonizedData,
        schema_fingerprint,
    )
    from .runs import run_dir, run_id

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    built = graph.assign_components(build_constraint_system(data, cfg))

    out = _constraints_dir(cfg)
    hashes = {
        "target_cell": write_parquet_deterministic(built.cells, out / "target_cell.parquet"),
        "constraint_row": write_parquet_deterministic(built.rows, out / "constraint_row.parquet"),
        "constraint_coefficient": write_parquet_deterministic(
            built.coefficients, out / "constraint_coefficient.parquet"
        ),
    }

    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    run.mkdir(parents=True, exist_ok=True)
    (run / "config.resolved.yaml").write_text(yaml.safe_dump(resolved_dict(cfg), sort_keys=True))
    _write_manifest(
        run / "schema_manifest.json",
        {
            "constraint_set_hash": built.constraint_set_hash,
            "output_hashes": hashes,
            "schema_fingerprints": {
                "target_cell": schema_fingerprint(TARGET_CELL_SCHEMA),
                "constraint_row": schema_fingerprint(CONSTRAINT_ROW_SCHEMA),
                "constraint_coefficient": schema_fingerprint(CONSTRAINT_COEFFICIENT_SCHEMA),
            },
            "compatibility_report": built.compatibility_report,
            # REQ-029 names the solver among the fail-closed surfaces, and §18.1 wants a run
            # reproducible from its manifest. `config.resolved.yaml` records that the solver is
            # HiGHS; only this records which HiGHS.
            "solver": cfg.constraints.solver,
            "solver_version": highspy.Highs().version(),
        },
    )
    write_parquet_deterministic(
        graph.component_provenance(built), run / "constraint_manifest.parquet"
    )
    typer.echo(f"constraint_set_hash {built.constraint_set_hash}")
    for table, digest in sorted(hashes.items()):
        typer.echo(f"{table} {digest}")


@app.command("solve-bounds")
def solve_bounds_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Solve sharp LP/MILP bounds for every target cell and flag the disclosive ones."""
    import json

    from .build import write_parquet_deterministic
    from .constraints.bounds import solve_bounds
    from .constraints.system import load_system
    from .disclosure.flags import build_flags
    from .runs import run_dir, run_id

    cfg = load_config(config)
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    manifest = run / "schema_manifest.json"
    if not manifest.exists():
        raise typer.BadParameter(
            f"{manifest} is missing: no `build-constraints` run matches the harmonized inputs "
            "currently in the staged directory. Run `build-constraints` first"
        )
    built = load_system(
        _constraints_dir(cfg),
        expected_hash=json.loads(manifest.read_text())["constraint_set_hash"],
    )
    result = solve_bounds(built, cfg.constraints)
    flags = build_flags(result.bounds, built.cells, cfg.disclosure)

    run.mkdir(parents=True, exist_ok=True)
    # The return values are the outputs' sha256s, exactly as `build-constraints` and
    # `run-baselines` collect them; this command was throwing all three away.
    hashes = {
        "deterministic_bounds": write_parquet_deterministic(
            result.bounds, run / "deterministic_bounds.parquet"
        ),
        "component_rank": write_parquet_deterministic(
            result.components, run / "component_rank.parquet"
        ),
        "disclosure_flags": write_parquet_deterministic(flags, run / "disclosure_flags.parquet"),
    }
    counts = result.bounds.group_by("bound_status").len().sort("bound_status")
    narrow = int(flags["narrow_feasible_interval_flag"].sum())
    exact = int(flags["exact_reconstruction_flag"].sum())
    # §16.1: "Every command MUST write a machine-readable manifest." `solve-bounds` wrote none, so
    # the §9 bounds were the one stage whose outputs a reader could only re-hash by hand, and the
    # §9.8 flag counts -- §14's disclosure surface -- survived only in the terminal scrollback.
    # Written AFTER the three tables and only on the success path: a refused run must leave the
    # directory with no artifact of any kind claiming these inputs were bounded.
    _write_manifest(
        run / "bounds_manifest.json",
        {
            # The gate `load_system` was pinned to, restated where the outputs are. This is what
            # ties `runs/<id>/deterministic_bounds.parquet` to the constraint tables in
            # `data/constraints/`, which the run id does not cover.
            "constraint_set_hash": built.constraint_set_hash,
            "output_hashes": hashes,
            "bound_status_counts": {
                row["bound_status"]: row["len"] for row in counts.iter_rows(named=True)
            },
            "narrow_feasible_interval_flags": narrow,
            "exact_reconstruction_flags": exact,
        },
    )
    for row in counts.iter_rows(named=True):
        typer.echo(f"{row['bound_status']} {row['len']}")
    typer.echo(f"flagged {narrow} narrow, {exact} exact")


@app.command("run-baselines")
def run_baselines_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Run every §10 transparent baseline and persist the results under this run's directory."""
    import json

    import polars as pl

    from .baselines.runner import (
        REGISTRY,
        preferred_estimator,
        preferred_estimator_by_month,
        run_baselines,
        state_total_bounds,
    )
    from .build import write_parquet_deterministic
    from .contracts import (
        ANCHOR_AUDIT_SCHEMA,
        BASELINE_RESULT_SCHEMA,
        HarmonizedData,
        schema_fingerprint,
    )
    from .runs import run_dir, run_id

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    manifest_path = run / "schema_manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(
            f"{manifest_path} is missing: no `build-constraints` run matches the harmonized "
            "inputs currently in the staged directory. Run `build-constraints` first"
        )
    # A SECOND PRECONDITION, new with R-S5P-3. INV-002's per-cell half checks every estimate
    # against §9's solved interval, so `solve-bounds` joins `build-constraints` as a gate rather
    # than the check being skipped when its input happens to be absent. A silently-skipped
    # invariant is the failure this requirement exists to remove, and the documented pipeline
    # order already runs `solve-bounds` before `run-baselines`.
    bounds_path = run / "deterministic_bounds.parquet"
    if not bounds_path.exists():
        raise typer.BadParameter(
            f"{bounds_path} is missing: every baseline estimate is checked against its per-cell "
            "deterministic bounds (INV-002), and this run has none. Run `solve-bounds` first"
        )
    results, audit = run_baselines(
        data,
        cfg,
        constraint_set_hash=json.loads(manifest_path.read_text())["constraint_set_hash"],
        bounds=state_total_bounds(pl.read_parquet(bounds_path)),
    )

    out = run / "baseline_results"
    out.mkdir(parents=True, exist_ok=True)
    hashes = {
        "baseline_results": write_parquet_deterministic(results, out / "baseline_results.parquet"),
        "anchor_audit": write_parquet_deterministic(audit, out / "anchor_audit.parquet"),
    }

    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    # Nested by estimator, not pooled. A single pooled count cannot answer "what fraction of
    # THIS estimator's cells took the fallback", which is the number §10.8's ranking turns on and
    # the one Task 19 reads back off this command.
    basis_counts: dict[str, dict[str, int]] = {}
    for row in ran.group_by(["estimator_id", "weight_basis"]).len().iter_rows(named=True):
        basis_counts.setdefault(row["estimator_id"], {})[row["weight_basis"]] = row["len"]
    # Nested by kind, not pooled. §13.5-13.8 define no decline metric, so a scoreboard has to be
    # able to separate §10.5's considered refusal from a month an estimator lost to a data gap:
    # pooled, a broken baseline and a benchmark that never runs look identical.
    declines: dict[str, dict[str, int]] = {}
    for row in (
        results.filter(pl.col("reconciliation_status") == "declined")
        .group_by(["estimator_id", "decline_kind"])
        .len()
        .iter_rows(named=True)
    ):
        declines.setdefault(row["estimator_id"], {})[row["decline_kind"]] = row["len"]
    # R-COMP-6: which intensity scaled each estimator's fallback arm, read off the estimators
    # themselves. §10.3 and §10.6 declare the disclosed ratio and §10.4 the national CBP March
    # one, and R-COMP-7 keeps that difference rather than standardising it — so it is reported
    # here, where a reader can check an arm against the name without reading source.
    fallback_intensity = {
        estimator.estimator_id: estimator.fallback_intensity
        for estimator in REGISTRY
        if estimator.fallback_intensity is not None
    }
    # A SIBLING manifest. `schema_manifest.json` is `solve-bounds`'s precondition gate and an
    # idempotence test pins its bytes, so nothing here may write to it.
    _write_manifest(
        run / "baseline_manifest.json",
        {
            "preferred_estimator": preferred_estimator(results),
            "preferred_estimator_by_month": preferred_estimator_by_month(results),
            "output_hashes": hashes,
            "schema_fingerprints": {
                "baseline_results": schema_fingerprint(BASELINE_RESULT_SCHEMA),
                "anchor_audit": schema_fingerprint(ANCHOR_AUDIT_SCHEMA),
            },
            "weight_basis_counts": basis_counts,
            "fallback_intensity": fallback_intensity,
            "declines": declines,
            "anchor": {
                "basis": "declared_national_total",
                "months_gated": audit.height,
                "months_anchored": int(audit["anchored"].sum()),
                "establishment_gap_max": int(audit["establishment_gap"].abs().max()),
            },
        },
    )
    typer.echo(f"preferred {preferred_estimator(results)}")
    for estimator_id, counts in sorted(basis_counts.items()):
        for basis, count in sorted(counts.items()):
            typer.echo(f"{estimator_id} {basis} {count}")
    for estimator_id, kinds in sorted(declines.items()):
        for kind, count in sorted(kinds.items()):
            typer.echo(f"declined {estimator_id} {kind} {count}")


@app.command("reconcile")
def reconcile_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
) -> None:
    """Re-reconcile the persisted baseline estimates and report any drift.

    Stage 3 reconciles inside `run-baselines`, so this command verifies rather than produces: it
    re-sums the persisted estimates against each month's recorded residual and reports the largest
    difference. It does NOT re-run the allocation. Stage 5 makes it load-bearing, when posterior
    draws reconcile separately from the estimators that seeded them.
    """
    import hashlib

    import polars as pl

    from .runs import run_dir, run_id

    cfg = load_config(config)
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg)))
    path = run / "baseline_results" / "baseline_results.parquet"
    if not path.exists():
        raise typer.BadParameter(
            f"{path} is missing: no `run-baselines` run matches the harmonized inputs currently "
            "in the staged directory. Run `run-baselines` first"
        )
    results = pl.read_parquet(path)
    ran = results.filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    drift = (
        ran.group_by(["estimator_id", "reference_month"])
        .agg(pl.col("estimate").sum().alias("total"), pl.col("residual").first().alias("residual"))
        .with_columns((pl.col("total") - pl.col("residual")).abs().alias("drift"))
    )
    worst = float(drift["drift"].max()) if drift.height else 0.0
    within_tolerance = worst <= cfg.reconciliation.tolerance
    # §16.1: "Every command MUST write a machine-readable manifest and MUST be idempotent for the
    # same inputs." A verifier that only echoes leaves nothing for §18.1 to reproduce against, so
    # the verdict and the digest of what was checked are persisted beside the results.
    _write_manifest(
        run / "reconcile_manifest.json",
        {
            "checked_pairs": drift.height,
            "max_residual_drift": worst,
            "tolerance": cfg.reconciliation.tolerance,
            "within_tolerance": within_tolerance,
            "baseline_results_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )
    typer.echo(f"checked {drift.height} (estimator, month) pairs")
    typer.echo(f"max residual drift {worst:.3e}")
    if not within_tolerance:
        raise typer.Exit(code=1)


def _estimator_override(estimators: str | None) -> dict[str, list[str]] | None:
    """`--estimators a,b` parsed, checked against §10's registry, and canonicalised for the run id.

    Returns the mapping `run_id` folds into its payload, or `None` when no subset was asked for.
    `None` is what keeps this option cheap: `run_id` omits the key entirely, so an un-overridden
    run hashes exactly as it did before the option existed and not one run directory on disk was
    renumbered by adding it.

    The ids come back in REGISTRY order, so `a,b` and `b,a` name ONE run rather than two
    directories holding byte-identical outputs. Raises `ConceptViolationError` on an unknown,
    repeated, or empty subset; the caller turns that into `typer.BadParameter`.
    """
    from .baselines.runner import resolve_estimators

    if estimators is None:
        return None
    names = [name.strip() for name in estimators.split(",") if name.strip()]
    return {"estimators": [estimator.estimator_id for estimator in resolve_estimators(names)]}


@app.command("validate")
def validate_command(
    config: Path = typer.Option(..., "--config", exists=True, dir_okay=False),
    estimators: str = typer.Option(
        None,
        "--estimators",
        help=(
            "Comma-separated §10 estimator ids to score, e.g. "
            "'establishment_proportional,share_last_observed'. Omit for the full registry. "
            "A subset changes the run id, so it gets its own run directory rather than "
            "overwriting a full pass's metrics."
        ),
    ),
) -> None:
    """Run §13's pseudo-suppression harness and persist its metrics and scoreboard."""

    from .baselines.runner import resolve_estimators
    from .build import write_parquet_deterministic
    from .contracts import (
        VALIDATION_METRIC_SCHEMA,
        VALIDATION_SCORE_SCHEMA,
        VALIDATION_SCOREBOARD_SCHEMA,
        HarmonizedData,
        assert_required_columns_present,
        validate_frame,
    )
    from .errors import ConceptViolationError
    from .runs import run_dir, run_id
    from .validate.harness import run_pseudo_suppression

    # Resolved BEFORE the staged layer is read, so a mistyped id costs a message rather than a
    # table load, and `typer.BadParameter` reports it the way every other bad option is reported.
    try:
        override = _estimator_override(estimators)
    except ConceptViolationError as error:
        raise typer.BadParameter(str(error), param_hint="--estimators") from error
    chosen = resolve_estimators(None if override is None else override["estimators"])

    cfg = load_config(config)
    data = HarmonizedData.load(Path(cfg.storage.staged_uri))
    run = run_dir(cfg, run_id(cfg, _input_digests(cfg), overrides=override))
    run.mkdir(parents=True, exist_ok=True)

    result = run_pseudo_suppression(data, chosen, cfg)

    # ALL THREE TABLES, gated before anything is written. `validation_scores` used to be excluded
    # with a comment calling its columns "a superset of VALIDATION_SCORE_SCHEMA", which was not
    # true in either direction: measured 2026-09-08, 23 produced against 20 declared with 17 in
    # common, so three declared columns were produced by nothing and six produced ones were
    # declared nowhere. The nullity pass is separate because `validate_frame` compares columns and
    # dtypes only, and the defect that motivated it — a NULL `mask_arm` on every `declines` row —
    # sat inside a table the schema gate already passed.
    for frame, schema, table in (
        (result.scores, VALIDATION_SCORE_SCHEMA, "validation_scores"),
        (result.metrics, VALIDATION_METRIC_SCHEMA, "validation_metrics"),
        (result.scoreboard, VALIDATION_SCOREBOARD_SCHEMA, "validation_scoreboard"),
    ):
        validate_frame(frame, schema, table)
        assert_required_columns_present(frame, table)

    hashes = {
        "validation_scores": write_parquet_deterministic(
            result.scores, run / "validation_scores.parquet"
        ),
        "validation_metrics": write_parquet_deterministic(
            result.metrics, run / "validation_metrics.parquet"
        ),
        "validation_scoreboard": write_parquet_deterministic(
            result.scoreboard, run / "validation_scoreboard.parquet"
        ),
    }
    # Recorded at the TOP level, not only per regime. A reader asking "what did this run score"
    # should not have to open thirteen regime entries and intersect them, and `runs/<id>/` carries
    # no `config.resolved.yaml` for a `validate` run to state it instead.
    manifest = {
        **result.manifest,
        "estimators": [estimator.estimator_id for estimator in chosen],
        "output_hashes": hashes,
    }
    _write_manifest(run / "validation_manifest.json", manifest)
    for regime, entry in sorted(result.manifest["regimes"].items()):
        typer.echo(f"{regime} {entry['disposition']} scored={entry['n_scored']}")
