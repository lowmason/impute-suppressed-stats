# `ingest/` — one module per source, plus the shared HTTP client

Turns fetched bytes into the three source tables of §7.3 `qcew_monthly`, §7.4 `qcew_national_size`,
§7.5 `cbp_state_size`. Nothing here decides *when* to fetch or *what* to write: `fetching.py`
drives acquisition, `build.py` drives parsing, both one level up. Spec obligations: §8.1
`SRC-QCEW-001..007`, §8.2 `SRC-QSIZE-001..004`, §8.3 `SRC-CBP-001..005`, §18.3 fail-closed, and the
§2.2 rows "Meaning of a QCEW zero", "QCEW size dimensionality", "CBP completeness and accuracy".
Below is only what is invisible from any single file; each module's docstring holds the rest,
including what Stage 0 measured.

## The parsers do not filter what their names imply

The first-contact trap: both QCEW parsers return every row the file gave them.

- `qcew_size.parse_qcew_national_size(frame, ..., industry=INDUSTRY_CODE)` uses `industry` **only**
  for `assert_no_state_industry_size`. Its output is *all industries*. Measured on
  `tests/fixtures/qcew_size/2017_q1_by_size.zip`: 32,011 rows in → **17,745 out across 2,155
  industries**, of which 113310 is **6** (classes 1–6 only, `own_code` 5, `agglvl` 28). The shipped
  table is 140,343 rows for the same reason (spec line 2283). Every consumer filters for itself:
  `constraints/system.py::build_constraint_system`, `constraints/compat.py::run_compatibility_gates`, `constraints/cells.py::build_target_cells`,
  `validate/recover.py::mask_and_solve_size`. Add a consumer and you must add the `industry_code` filter.
- `qcew.parse_qcew_monthly` returns counties, Puerto Rico and every ownership.
  `qcew.apply_universe_filter` (REQ-002 at spec line 2041, §3.2) lives in this module but is called
  from `build.py::build_harmonized` — deliberately, so the parser stays a parser. Measured on
  `tests/fixtures/qcew/slice_2017q1.csv`: 1,810 rows → 5,430 monthly rows (×3, one per
  `monthN_emplvl`) → **150** after the filter. Downstream of the build, a Puerto Rico or county row
  is a bug, not data (spec line 2288).
- `cbp.parse_cbp_state_size` is the exception — its query already carries the industry predicate.

## The bulk QCEW route is fetched but never parsed

`fetching.py::fetch_source` downloads `{year}_qtrly_by_industry.zip` when `route_for_year` says `bulk`, but
`read_bulk_zip` **has no caller anywhere in `src/`** and `build_harmonized` globs `"*.csv"` only
(`build.py::build_harmonized`). Two structural facts before turning that branch on: `snapshot_paths`' manifest
branch (`build.py::snapshot_paths`-131`) never reads its `pattern` argument, and `merge_source_manifest` does
not dedupe while the bulk fetch loop appends one snapshot row per quarter for a single archive.

Nobody has hit it: the measured slice boundary is reference year **2014**
(`specs/findings/source-audit.md:117`, `bulk_years_required = []`), so no D1 year routes to bulk.
`test_qcew_routes.py::test_every_window_year_still_routes_to_the_slice_endpoint` re-reads that
boundary from the findings document at runtime. If a re-audit moved it, production would not take
the bulk route — `probe_slice_boundary` would raise.

## `source_row_hash` identity is a *pair*

`_ROW_IDENTITY_COLUMNS` (`qcew.py`) deliberately excludes `release_vintage` and `snapshot_id`,
so a revision of the same cell hashes identically. The identity of a harmonized row is therefore
`(source_row_hash, release_vintage)`; deduplicating on the hash alone silently drops revisions,
which is INV-007's failure mode. What the docstring cannot know: on the build path both
`snapshot_id` and `release_vintage` are set to the *filename stem* (`build.py::build_harmonized`-178`), e.g.
`2017q1`, and only one vintage is ever ingested — `validate/regimes.py::select_targets` refuses the
vintage-comparison regime for exactly that reason. So today `release_vintage` is a reference key,
not a vintage.

## The declared schema is the exit contract

All three parsers end `.select(list(SCHEMA)).cast(SCHEMA)` against `contracts.py`. A column added to
a parser and not to `contracts.py` is silently dropped; a column added to `contracts.py` and not
the parser raises. Two divergences from the spec's own field lists:

- `QCEW_MONTHLY_SCHEMA` adds `suppression_type` beyond §7.3's list (`contracts.py`-98`): INV-009
  forces every real row to `"unknown"`, and a column that existed only in Stage 4 could not be
  distinguished from a value Stage 4 chose.
- `qcew_national_size` carries **no ownership column** — §7.4's list has none — so a size cell's
  ownership is stamped on downstream at `constraints/cells.py`, from `constants`, not `Config`.

The two QCEW tables do not share a column vocabulary (`size_class` vs `size_code`, `employment` vs
`employment_value`); see `validate/mask.py::apply_size_mask`.

## Fail-closed inventory (§18.3)

| Check | Raises | Where |
|---|---|---|
| disclosure code outside the measured `{"", "N", "-"}` allowlist (duplicated, once per QCEW parser) | `UnknownDisclosureCodeError` | `qcew.py::_check_disclosure_codes`, `qcew_size.py::_check_disclosure_codes` |
| `EMP_F` outside the 2017 EMPFLAG scheme (`'r'` = revised, is **not** withheld; no `'D'` exists) | `UnknownDisclosureCodeError` | `cbp.py::_check_employment_flags` |
| EMPSZES label with no parseable bounds | `UnknownSizeCodeError` | `cbp.py::size_bounds` |
| QCEW size code with no published bounds | `UnknownSizeCodeError` | `qcew_size.py::_check_size_codes` |
| state × industry × size rows present (§2.2 row 3 assumed absent) | `MissingCrossTabulationError` | `qcew_size.py::assert_no_state_industry_size` |
| Census echoing a predicate column twice with disagreeing values | `SchemaMismatchError` | `cbp.py::_frame_from_rows` |
| `disclosure_code == "-"` with `qtrly_estabs > 0` (breaks the true-zero premise) | `ValueError` | `qcew.py::_check_dash_rows_carry_no_establishments` |
| bulk-zip industry substring does not narrow to one member (`11331` hits `111331 Apple orchards`) | `ValueError` | `qcew.py::read_bulk_zip` |
| by-size zip does not hold exactly one CSV; boundary probe served no year | `ValueError` | `qcew_size.py::read_by_size_zip`, `qcew.py::probe_slice_boundary` |

`base.HttpFetcher` returns a non-200 rather than raising (project `CLAUDE.md` has the reason);
`fetching.py` classifies and `continue`s past it, which is why **CBP 2024 is simply absent from
the store rather than an error**. CBP publishes 2017-2023 — Stage 0's recorded 404, spec line 2270,
not a fetch performed for this file.

## Conventions

- Every read is `infer_schema_length=0` — all columns `String`. `area_fips` is a zero-padded code,
  and a suppressed row publishes a literal `0` that must not become an integer before
  `disclosure_code` is read (SRC-QCEW-002).
- No year, size-class table, or predicate name is typed from documentation: each is measured or
  read from fetched metadata, and a test re-derives the constant from the shipped fixture rather
  than trusting the typed table (`test_qcew_size.py::test_size_class_bounds_agree_with_the_titles_the_file_publishes`, `test_cbp.py::test_every_label_in_the_official_crosswalk_resolves`, `test_cbp.py::test_the_empflag_table_matches_the_fetched_2017_record_layout`).
  Two source-scanning tests enforce it: `"2014" not in qcew.py`, `"NAICS2022" not in cbp.py`.
- `qcew_size` reuses `qcew.BULK_TO_SLICE_COLUMNS` / `BULK_ONLY_TITLE_COLUMNS`: the by-size file
  speaks the *bulk* vocabulary (`qtrly_estabs_count`), not the slice one.
- CBP writes a second file per year, `{year}_variables.json` (`cbp.METADATA_SUFFIX`), with **no**
  `source_snapshot` row (`fetching.py::fetch_source`) — invisible to the manifest, and skipped by name in the
  glob path via `cbp.is_metadata_path`.

## Commands

```bash
uv run pytest tests/unit/test_qcew_parser.py tests/unit/test_qcew_routes.py tests/unit/test_cbp.py \
  tests/unit/test_qcew_size.py tests/unit/test_ingest_base.py tests/unit/test_universe.py -q
```

Observed: 86 passed, 1 skipped, under a second. Nothing in this repo excludes the `slow` marker —
the one skip is a `skipif` on a missing file (`tests/unit/test_qcew_routes.py::test_the_member_selector_is_unique_in_the_real_archive_not_just_the_fixture`):
`test_the_member_selector_is_unique_in_the_real_archive_not_just_the_fixture` needs the gitignored
`data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip`, which
`scripts/audit/qcew_routes.py` produces. Fixture provenance — including why `bulk_2017.zip` is
*derived rather than audited* — is in `tests/fixtures/qcew/README.md`.
