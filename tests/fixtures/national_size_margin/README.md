# `national_size_margin` fixtures

The frozen input behind `tests/integration/test_national_size_margin_golden.py`. `data/` is
gitignored in its entirety, so the tables the D1 build stages cannot serve as a golden's input
where they sit: a golden is only as frozen as what it reads, and a test comparing a hand-derived
oracle against `data/staged/` is pinned to whatever that machine last rebuilt from live BLS
bytes. These four parquet files are that input, tracked.

Four tables, because `HarmonizedData.load` expects all four. Two carry rows; two carry schema
only.

| File | Rows | Contents |
|---|---|---|
| `qcew_national_size.parquet` | 51 | NAICS 113310 national by-size, `2017-03 … 2024-03`; 37 `observed`, 14 `suppressed` |
| `qcew_monthly.parquet` | 401 | 8 national all-sizes March rows + 393 state March rows |
| `cbp_state_size.parquet` | 0 | schema only |
| `bridge.parquet` | 0 | schema only |

Byte sizes are deliberately not recorded, and neither is a hash of any file: parquet bytes depend
on the polars version that wrote them, so a hash here would go red on a dependency bump while the
rows underneath it were untouched. Row counts, `snapshot_id`s and `release_vintage`s are the
contract; they are properties of the data, not of the writer.

## Provenance

Every row descends from a Stage 0 extract, carried through `build-harmonized` unmodified. The
generation procedure below filters and sorts; it computes nothing.

### `qcew_national_size.parquet`

One `snapshot_id` per reference month, all `113310`:

| `reference_month` | `snapshot_id` | `naics_vintage` | Size classes | Rows |
|---|---|---|---|---|
| `2017-03` | `2017_q1_by_size` | NAICS 2017 | `1`–`6` | 6 |
| `2018-03` | `2018_q1_by_size` | NAICS 2017 | `1`–`6` | 6 |
| `2019-03` | `2019_q1_by_size` | NAICS 2017 | `1`–`6` | 6 |
| `2020-03` | `2020_q1_by_size` | NAICS 2017 | `1`–`6` | 6 |
| `2021-03` | `2021_q1_by_size` | NAICS 2017 | `1`–`6` | 6 |
| `2022-03` | `2022_q1_by_size` | NAICS 2022 | `1`–`7` | 7 |
| `2023-03` | `2023_q1_by_size` | NAICS 2022 | `1`–`7` | 7 |
| `2024-03` | `2024_q1_by_size` | NAICS 2022 | `1`–`7` | 7 |

The seventh class appears from 2022-03 with the NAICS 2022 vintage. The fourteen suppressed rows
are what the golden's `EXPECTED_BOUNDS` solves for.

`size_upper` is non-null on all 51 rows. The open-ended top class — the `ge`-only branch of
`rows.size_support_rows` — is therefore never built from this fixture, and the golden says so
rather than leaving it implied.

### `qcew_monthly.parquet`

`snapshot_id` and `release_vintage` are equal on every row, one pair per reference month:
`2017q1`, `2018q1`, `2019q1`, `2020q1`, `2021q1`, `2022q1`, `2023q1`, `2024q1`. Every row is
`release_status` `final`, `ownership_code` `5` (private), `size_code` `0` (all sizes).

- **8 national rows**, one per March, `aggregation_level` 18.
- **393 state rows**, `aggregation_level` 58, over 50 `area_fips`. 50 × 8 = 400 less the seven
  state-months absent from the published files: `38000` in 2017-03, 2018-03, 2019-03 and 2024-03,
  and `10000` in 2022-03, 2023-03 and 2024-03. Of the 393, 287 are `observed`, 105 `suppressed`
  and 1 `true_zero` — "present as a row" is not "disclosed", and the fixture carries both.

The 50 `area_fips` are exactly the 50 the staged table carries; neither DC nor Puerto Rico appears
in the D1 build, and this fixture inherits that rather than deciding it.

### Why the state rows are here at all

The golden reproduces its fourteen bounds from the national rows alone — a national-only fixture
is half the size and gives identical numbers. The state rows are in it because
`harmonize.universe.assert_definitional_alignment` runs before `build_constraint_system` creates a
row, and that gate **returns early when either level is absent**. Its own docstring says that is
not a pass. Without the state rows the alignment gate inside this golden would be vacuous, and
`test_the_fixture_carries_both_levels_so_the_alignment_gate_is_not_vacuous` — which misaligns the
two levels' `naics_vintage` and requires a raise — could not fail on a national-only frame.

## Regenerating is a §17.6 golden update

§17.6: "Golden updates require a documented reason and reviewer approval." That rule covers this
directory, not only the `EXPECTED_BOUNDS` dict in the test file.

Re-running the procedure below after a BLS revision re-freezes the input the fourteen hand-derived
pairs are held against, which undoes the freeze **silently**: the dict still looks untouched while
the thing it is compared against has moved. Treat a regeneration as an edit to the dict itself.

If the D1 window changes (`project.start_month` / `project.end_month`), the fixture and
`EXPECTED_BOUNDS` must be regenerated **together**, with a fresh hand derivation for any March
that joins. `cells.build_target_cells` derives its month list from the size rows it is handed, so
a widened window otherwise leaves the golden quietly checking the same eight frozen Marches —
still a true statement about the engine, just no longer coterminous with the configured window.

## Regenerating

Run from the repo root with `data/staged/` present, i.e. after `logging-estimates
build-harmonized`. Row counts and column values do not depend on the polars version; parquet bytes
do. The two `.sort(...)` calls make the output a function of the staged *rows* rather than of
whatever order the harmonize step last emitted them in; both keys are total orders on this data —
401 unique `(reference_month, area_type, area_fips)` and 51 unique `(reference_month, size_class)`
— so no tie is broken arbitrarily and re-running reproduces the files byte for byte.

```bash
uv run python - <<'PY'
from pathlib import Path

import polars as pl

STAGED = Path("data/staged")
DST = Path("tests/fixtures/national_size_margin")
INDUSTRY = "113310"

DST.mkdir(parents=True, exist_ok=True)

size = pl.read_parquet(STAGED / "qcew_national_size.parquet").filter(
    pl.col("industry_code") == INDUSTRY
)
months = sorted(set(size["reference_month"].to_list()))
monthly = pl.read_parquet(STAGED / "qcew_monthly.parquet").filter(
    pl.col("reference_month").is_in(months) & pl.col("area_type").is_in(["national", "state"])
)

size.sort(["reference_month", "size_class"]).write_parquet(DST / "qcew_national_size.parquet")
monthly.sort(["reference_month", "area_type", "area_fips"]).write_parquet(
    DST / "qcew_monthly.parquet"
)
for name in ("cbp_state_size", "bridge"):
    pl.read_parquet(STAGED / f"{name}.parquet").clear().write_parquet(DST / f"{name}.parquet")

for path in sorted(DST.glob("*.parquet")):
    print(f"{path.name:30s} {pl.read_parquet(path).height:>4d} rows  {path.stat().st_size:>6d} B")
PY
```

The fixture must be tracked in git for the golden to mean anything, and
`test_the_golden_fixture_is_tracked_in_git_not_rebuilt_from_ignored_data` asserts exactly that by
asking `git ls-files` rather than `Path.exists()`. `git check-ignore` exits 1 on these paths, so
`git add` needs no `-f`.
