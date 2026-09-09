# logging_employment

Monthly state Logging (NAICS 113310, private ownership, states + DC, 2017-01..2024-12) employment
by establishment size class, for the cells BLS suppresses for disclosure. Identification precedes
imputation: sharp LP/MILP bounds from public accounting facts (§9), then transparent baselines
(§10), exact reconciliation (§12), then a pseudo-suppression harness (§13). Sources are QCEW,
QCEW-by-size and CBP. The §11 Bayesian model is not built yet.

**The spec is authoritative and this codebase cites it constantly.**
`specs/logging-employment-spec.md` — §3 estimand, §4 invariants (`INV-001`..`INV-016`), §6.2
storage, §7 table field lists, §9 engine, §10 baselines, §12 reconciliation, §13 validation, §14
disclosure, §16 interfaces, §18.3 fail-closed, Appendix A the reference config (≈ `config.yaml`).
Stage status is at the end of that file under `### Stage stamps` — read it rather than assuming a
stage is done; it also records what each stage re-validated about later ones. Plan queue:
`specs/logging-employment-spec-roadmap.md`; open decisions: `specs/deferred_items.md`.

## Commands

```
uv run pytest                    # whole suite; NOT green without data/ (see gotchas)
uv run black .                   # the tree IS black-formatted; never run `ruff format`
uv run ruff check src tests      # clean; a bare `.` also lints scripts/ (see gotchas)
uv run interrogate src           # docstring gate, fail-under = 100

logging-estimates validate-config --config config.yaml   # these two run in a bare checkout,
logging-estimates registry verify --config config.yaml   # no data/ needed
logging-estimates fetch --source qcew --config config.yaml   # or qcew_size / cbp; network +
                                                             # CENSUS_API_KEY from ./.env
# then, in order:
build-harmonized → build-constraints → solve-bounds → run-baselines → reconcile → validate
```

Every command takes `--config config.yaml` and must be idempotent for the same inputs (§16.1);
each gates on the previous one's artifact and refuses with the missing path (`cli.py::solve_bounds_command`, `:250`,
`:349`). `validate --estimators a,b` scores a subset in its own run dir. `--help` is the real
command list — five of §16.1's fifteen do not exist yet (`fit-state-model`, `fit-size-model`,
`disclosure-review`, `publish`, `run-all`).

Markers are declared but never applied by `addopts`: `slow` is on one unit test and four
integration modules and nothing excludes it (pass `-m "not slow"` yourself), and `network` is
declared — its help text even says "excluded from the default run" — but no test carries it.

## Architecture

`fetch` puts raw bytes in a content-addressed immutable store; every later stage reads only the
four harmonized Parquet tables (`contracts.HarmonizedData`), never an endpoint. `build-constraints`
turns those into a cell/row/coefficient system, `solve-bounds` bounds each component,
`run-baselines` produces weights that `reconcile/` turns into estimates, `validate` re-runs it under
synthetic masks. Outputs land in `runs/<run_id>/` beside one JSON manifest per command.

| Module | Owns |
|---|---|
| `cli.py` | the Typer app: subcommands, their preconditions, and the manifests they write |
| `config.py` | pydantic v2 `Config`; every model subclasses `_Strict` (`extra="forbid"`), `.env` credentials, `resolved_dict` |
| `contracts.py` | every persisted table's polars schema (§7), schema fingerprints, closed value sets |
| `build.py` | `build-harmonized` + the deterministic Parquet writer; reads stored bytes, never fetches |
| `fetching.py` | acquisition per source, `source_snapshot` rows, `runs/source_manifest.parquet` |
| `store.py` | `data/raw/<source_id>/<sha256>/<file>`, written once; the secret guard |
| `runs.py` | `runs/<run_id>/` and how the id is derived |
| `errors.py` | the fail-closed exception hierarchy (§18.3) |
| `classification.py`, `constants.py` | §3.1's memo read out of the spec file rather than retyped; the D1 window, `113310`, ownership `5`, states+DC FIPS, measured QCEW code sets |
| `ingest/` | one module per source + the shared `HttpFetcher` → see `ingest/CLAUDE.md` |
| `harmonize/` | NAICS vintages, the nine versioned dimensions, §8.6 bridges, CBP regime-by-year, universe guards |
| `constraints/` | §9 identification engine → see `constraints/CLAUDE.md` |
| `reconcile/` | §12 exact reconciliation → see `reconcile/CLAUDE.md` |
| `baselines/` | §10 transparent baselines → see `baselines/CLAUDE.md` |
| `validate/` | §13 pseudo-suppression harness → see `validate/CLAUDE.md` |
| `registry/` | §7.1 source registry: row model, `registry/sources.yaml`, `registry verify`'s checks |
| `disclosure/` | §9.8 flags only — `exact_reconstruction_flag`, `narrow_feasible_interval_flag`, on suppressed cells only, thresholds from config |

## Conventions that span modules

- **Run ids are derived, not stamped.** `runs.run_id` = sha256 of `{config: resolved_dict(cfg),
  inputs: {stem: sha256}}`, truncated to 12, over `data/staged/*.parquet` (`runs.py::run_id`,
  `cli.py::_input_digests`); optional keys are *omitted*, never null, so they do not re-id existing runs. The
  id therefore covers config + input data but **not source code**.
- **Schemas are ordered `dict[str, pl.DataType]` literals in `contracts.py`, and the order is
  load-bearing** — `schema_fingerprint` hashes the ordered pairs, so reordering fields is
  a schema change. `validate_frame` matches names and dtypes exactly and checks no values;
  `assert_declared_provenance` enforces the closed string sets (`WEIGHT_BASES`,
  `DECLINE_KINDS`, `SUPPRESSION_TYPES`, ...) that a `pl.String` dtype cannot.
- **Every Parquet write is byte-reproducible**: sorted to a total order, rechunked, uncompressed,
  `statistics=False`, returning the file's sha256. `build.write_parquet_deterministic` is
  the shared one — `build.deterministic_order` puts the natural key first and every
  remaining column behind it as tiebreak, and is public so a golden test can order an in-memory
  frame the same way. `fetching.write_source_manifest` repeats the write policy inline but
  sorts on `["source_id", "snapshot_id"]` only.
- **Fail closed with a named error.** Everything in `errors.py` subclasses `LoggingEmploymentError`
  and carries the offending value. Some classes and guards are *deliberately unraised/uncalled* and
  say so (`NoHarvestFactorError`, both guards in `harmonize/concepts.py`): later stages own them.
- **Secrets never reach an artifact** (D3, §7.2): `store.assert_no_secret` refuses a
  snapshot row containing one of `config.SECRET_ENV_VARS`, `fetching._without_credentials` strips
  the `key` param before recording, and `resolved_dict` keeps only the env var's *name*.
- **`cell_id` = `kind|state_fips|reference_month|ownership_code|industry_code|naics_vintage|
  size_class`** (`constraints/cells.py::cell_id`); totals use `state_fips="US"`, `size_class="ALL"`.
  `naics_vintage` sits inside the id, so a vintage change renames every cell.
- **Vintage discipline**: `harmonize/naics.vintage_for_year` gives `NAICS 2022` from 2022, `NAICS
  2017` before it, and *refuses* years < 2017 (`UnsupportedReferenceYearError`) rather than
  mislabelling them. `INV-007` (never stack incompatible vintages) is enforced at four separate
  points: `build.snapshot_paths` (the gotcha below), `constraints/cells.py::_assert_one_vintage_per_cell`,
  `constraints/compat.py` (`:141`, `:154`) and `constraints/rows.py::constraint`.
  None of them is a general guarantee — `constraints/CLAUDE.md` says exactly what each covers.
- **Docstrings are the design record.** Nearly every callable has one, and the house style is to
  say *why this and not the obvious alternative*, citing §/`INV-`/`REQ-`/`SRC-` ids; move those
  notes when refactoring rather than dropping them. Corollary: a note that reads as a measurement
  ("measured 2026-09-05: 1,227 cells") is a dated witness — re-verify before repeating it.
- Committed fixtures live in `tests/fixtures/` and golden tests read them, never `data/`;
  `tests/unit/conftest.py` has frame factories that fill every schema column.

## Gotchas

- **`data/` (~564 MB) and `runs/` are gitignored, and the suite is not green without them.**
  Measured at `8899b5f` with no `data/`: `uv run pytest` → **42 failed, 1238 passed, 26 skipped**.
  Every failure is a `validate/` test calling `HarmonizedData.load(Path("data/staged"))` with no
  skip guard — 34 across seven `tests/unit/test_validate_*.py` modules, 8 across
  `tests/integration/test_validate_{leakage,exact_recovery}.py`. Those paths are **cwd-relative**,
  so run pytest from the repo root. `tests/integration/test_d1_*.py` do it properly, with
  `skipif`. Baseline HEAD before blaming your own change.
- **`black` and `ruff format` disagree; the tree is black's.** At `8899b5f` with ruff 0.16.6,
  `black --check .` passes (172 files) while `ruff format --check .` wants to rewrite 24 —
  running it buries your change in an unrelated diff. Lint is scope-dependent: `ruff check src
  tests` is **clean**, while `ruff check .` reports 24 findings (ISC004, TRY004, UP037, RUF100,
  RET501, UP047) that all live in `scripts/`. `interrogate` is configured `fail-under = 100` and
  currently fails at 98.9%, on four missing docstrings: `config.py::_refuse_a_random_mask_only_design`,
  `validate/recover.py::_empty_truth`, `validate/regimes.py::_small_cell` and `:195`. Line length is 100 in both
  formatters. None of that is yours.
- **Adding a pydantic field to `Config` re-ids every run directory**: `resolved_dict` is
  `model_dump(mode="json")` and feeds `run_id`. For a CLI-only choice use `run_id`'s `overrides`,
  omitting the key when unset (`runs.py` docstring), so existing runs keep their id.
- **A run directory can be stale w.r.t. your code.** `run_id` ignores source, so editing an
  estimator and re-running overwrites the same `runs/<id>/`. The one cross-stage check that does
  fire is `constraint_set_hash` (see `constraints/CLAUDE.md`).
- **CBP responses are not byte-reproducible** — set-identical rows in a different order, so each
  re-fetch stores another object for the same year. `build.snapshot_paths` raises
  `AmbiguousSnapshotError` (`build.py::snapshot_paths`) rather than stacking two snapshots of one key; pass the
  run manifest.
- **Government APIs answer 200 with an error body.** `ingest/base.HttpFetcher` returns
  non-200 responses instead of raising, exactly so the caller classifies on content, not status.
- **`scripts/audit/` is destructive-first.** Standalone PEP 723 files (`uv run --no-project`),
  tested by `tests/audit/`. `cbp_metadata.py` `rmtree`s each year's extract directory *before* it
  probes, and those extracts are gitignored — never run it just to check a change.
