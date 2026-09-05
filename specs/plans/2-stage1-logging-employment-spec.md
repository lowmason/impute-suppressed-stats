# Stage 1: Foundation, Ingestion, and Harmonization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via
> subagent-driven-development (the default) — or executing-plans when your human partner
> chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage 1 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Stand up the uv-managed hatchling package `logging_employment` and produce immutable,
vintage-aware QCEW, QCEW-size, and CBP Parquet tables with harmonized dimensions, explicit
bridges, and four CLI commands, such that a frozen pull rebuilds byte-identical harmonized
Parquet from `data/raw/` with the network disabled.

**Architecture:** One installable package under `src/logging_employment/` laid out per spec §6.1.
Three layers, each with its own task group: an **acquisition** layer (content-addressed immutable
raw store + one HTTP client + `source_snapshot` records), a **parse** layer (one module per
source, each turning stored bytes into a typed Polars frame against a declared schema), and a
**harmonize** layer (versioned dimensions, bridges, concept guards). Nothing downstream of Stage 1
ever touches a source endpoint — every later stage reads harmonized Parquet. Judgment logic that
decides what a value *means* (the true-zero rule, the disclosure-code allowlist, route selection,
regime fail-closed) is written test-first, before the parser that applies it.

**Tech Stack:** Python 3.14 via uv + hatchling; Polars and PyArrow for tabular work and Parquet;
`httpx` for downloads; Pydantic v2 for configuration; Typer for the CLI; `python-dotenv` for
credentials; pytest with `network` and `slow` markers; ruff and black at line length 100;
interrogate at 100%.

---

## Global Constraints

Every task's requirements implicitly include this section. Values are copied verbatim from the
spec's Rollout note (D1–D5) and from Stage 0's shipped findings.

**D1 window.** Pilot `2017-01` → `2024-12`. Every quarter in the window is final under QCEW's
finalize-with-next-year-Q1 rule. The window spans the 2017→2022 QCEW NAICS transition, which this
stage's crosswalk test must exercise.

**D3 credentials.** Live fetch from `data.bls.gov` and `api.census.gov`. Credentials come from an
untracked repo-root `.env` (keys present: `CENSUS_API_KEY`, `BLS_API_KEY`, `BEA_API_KEY`,
`FRED_API_KEY`, `BLS_CONTACT_EMAIL`) loaded with python-dotenv. `.env` MUST stay gitignored, and
**no key value may appear in any manifest** (§7.2). `bls.gov` admits scripted clients only when the
User-Agent carries a contact address; `BLS_CONTACT_EMAIL` exists for that purpose.

**D4 toolchain.** A single installable package — `src/logging_employment/` laid out per §6.1 —
built with hatchling and managed by uv; `requires-python >= 3.14`; author
`Lowell Mason <mason.lowell@mac.com>`, MIT license; ruff and black at line length 100, pytest
markers `network` and `slow`, interrogate at 100%, python-dotenv in the `dev` dependency group.

> **D4's plan-time wheel check is DONE — do not repeat it as an open decision.**
> D4 requires this plan to verify that jax/jaxlib, numpyro, highspy, polars and pyarrow publish
> 3.14 wheels before locking. Verified 2026-09-05 by resolving and dry-run-installing the full
> set against a real CPython 3.14 interpreter, wheels only:
>
> ```bash
> uv venv --python 3.14 .venv314
> uv pip install --python .venv314 --only-binary :all: --dry-run -r reqs.txt
> ```
>
> with `reqs.txt` = polars, pyarrow, httpx, pydantic, typer, python-dotenv, jax, jaxlib, numpyro,
> highspy, scipy, arviz. **All twelve resolved and installed as wheels; none fell back to an
> sdist.** Resolved versions at check time: polars 1.44.1, pyarrow 25.0.1, jax/jaxlib 0.11.1,
> numpyro 0.21.0, highspy 1.15.1, scipy 1.18.1, arviz 1.3.0, httpx 0.28.1, pydantic 2.13.5,
> typer 0.27.2, python-dotenv 1.2.3. Nothing is recorded as an open decision on this row.
> Note that several of these ship `py3-none-any` or abi3 wheels rather than `cp314` wheels —
> searching filenames for `cp314` is the wrong test and will produce false negatives.

**D5 QCEW acquisition is dual-route.** Implement both the Open Data CSV slice route and the
downloadable bulk-file route behind one ingest interface, selecting by reference year from a
boundary this stage **re-measures**. §5.4's instruction not to hard-code a "latest" year applies to
both routes.

**Estimand invariants that bind every task in this stage.** `INV-003` (no suppression-coded value
becomes a true zero without a source-specific rule proving it), `INV-007` (no silent stacking
across incompatible vintages/universes), `INV-009` (real-world suppression type is `unknown`;
primary-like/complementary-like labels are for synthetic masks only), `INV-010` (enterprise size is
never relabeled establishment size).

**Fail closed (§18.3).** The pipeline MUST fail rather than guess when the supplied source schema
is unrecognized, a disclosure code is unknown, or a requested simultaneous cross-tabulation is
absent. "Fail" means raise a named exception carrying the offending value — never a warning, never
a silent default.

**Anti-transcription rule for this stage.** Stage 0's branch-long defect was *a factual claim typed
as prose instead of derived from data in scope*. Ten instances shipped, most of them inside prose
written to fix a previous instance. When you write a docstring, comment, assertion message, test
name, or CLI help string that states a fact about the data, the test is: **could this run's data
have produced this sentence, and would a re-run against revised data change it?** If the answer is
no, derive it or mark it inline as documented-not-measured, with the reason. This applies to
anything you copy out of this plan, too.

---

## Scope judgment: one plan, fourteen tasks

Stage 1 is large, but it is one vertical slice with a single exit criterion — a frozen pull
rebuilding byte-identical harmonized Parquet offline. Splitting it would produce halves that
cannot satisfy that criterion independently (an acquisition half with nothing to harmonize; a
harmonize half with no immutable store to read). It stays one plan.

---

## What Stage 0 measured — the inputs this plan consumes

Read from `specs/findings/source-audit.md` and the summaries under `data/raw/audit/`. **Do not
re-derive these; do not hard-code them as literals where the plan says to re-measure.**

| Fact | Value | Where it binds |
|---|---|---|
| QCEW slice route | `https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv` | Task 7 |
| QCEW bulk route | `https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip` | Task 8 |
| Bulk member name (2017) | `2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv` | Task 8 |
| Slice earliest year served | 2014 — **measured in one run, not a property of the route.** Re-measure; never hard-code. | Task 7 |
| `bulk_years_required` | `[]` — today's boundary makes the bulk branch unreachable in production, so tests must force it | Task 8 |
| Route column parity | `identical: false`. Bulk→slice renames: `qtrly_estabs_count`→`qtrly_estabs`, `lq_qtrly_estabs_count`→`lq_qtrly_estabs`, `oty_qtrly_estabs_count_chg`→`oty_qtrly_estabs_chg`, `oty_qtrly_estabs_count_pct_chg`→`oty_qtrly_estabs_pct_chg`. Bulk-only: `agglvl_title`, `area_title`, `industry_title`, `own_title`, `size_title` | Task 8 |
| QCEW agglvl codes on 113310 | `18` National, `48` MSA, `58` State, `78` County | Task 2 |
| QCEW own codes on 113310 | `3` Local Government, `5` Private | Task 2 |
| QCEW size codes on 113310 (quarterly file) | `0` "All establishment sizes" only | Task 2 |
| QCEW disclosure codes observed | `''` (17302 rows), `'-'` (935), `'N'` (40875). **BLS ships no titles file for this dimension** (`titles_available.disclosure_code = null`) | Tasks 2, 9 |
| Title files that do exist | agglvl, area, industry, ownership, size — under `https://data.bls.gov/cew/doc/titles/<dimension>/` | Task 2 |
| NAICS vintage by year | 2017–2021 `NAICS 2017`; 2022–2024 `NAICS 2022`. **Rests on an uncited premise** (QCEW does not retabulate prior years onto a new vintage) — carry the marking forward | Task 13 |
| DC (`11000`) | Publishes **zero** private 113310 rows in all 96 months — a genuine `states_dc` coverage gap, not suppression | Tasks 3, 9 |
| Partial-coverage areas | `10000` absent 36 months, `38000` absent 48 months; `interior_month_gaps: 0` | Task 9 |
| Puerto Rico (`72000`) | Present in state-like rows (8 rows, 2017–2018); outside `states_dc`; measured `outside_national_total` | Task 9 |
| Suppression share | 0.2602 over the **4716 cells actually present**, not over a 51×96 = 4896 grid | Task 9 |
| Establishments survive suppression | All 1227 suppressed `states_dc` cells report `qtrly_estabs > 0` (`estabs_survive_suppression_share = 1.0`) | Task 9 |
| QCEW size dimensionality | `simultaneous_state_industry_size = false`. 113310 appears at agglvl `28` only, area pattern `national`. Finest combination: national × 113310 × size codes 1–7. Q2–Q4 probes: 24/24 returned 404 — the by-size file is **first quarter only** | Task 10 |
| QCEW size codes (by-size file) | `1` <5, `2` 5–9, `3` 10–19, `4` 20–49, `5` 50–99, `6` 100–249, `7` 250–499 | Task 10 |
| CBP NAICS predicate | `NAICS2017` for **every** year 2017–2023. A parser deriving the predicate from the reference year's NAICS vintage would ask for a variable CBP does not serve | Task 11 |
| CBP years available | 2017–2023. 2024 → dataset probe 404 | Tasks 11, 12 |
| CBP working query | `get=NAME,NAICS2017_LABEL,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N`, `for=state:*`, `NAICS2017=113310`, `LFO=001` | Task 11 |
| CBP EMPSZES metadata | Official values crosswalk at `variables/EMPSZES.json` **for 2017 only** (44 codes, `carries_values_crosswalk: true`). 2018–2023 return 200 with no crosswalk. The 113310 state slice exposes 7 codes: `001`, `210`, `220`, `230`, `241`, `242`, `251` | Task 11 |
| CBP flags observed | `EMP_F`: `['', 'a']` in 2017, `['']` 2018–2023. `EMP_N`: literal string `'0'` every year. `EMP_N_F` — the actual per-cell noise flag — was never selected as an output column | Task 11 |
| CBP `LFO` | `lfo_by_year` is `null` for all eight years: LFO was only ever *sent* as a filter, never *selected* as an output column. Stage 0 deferred a dedicated `LFO,LFO_LABEL` query **to this stage** | Task 11 |
| CBP disclosure regime | 2017 `noise_infusion_plus_suppression`; 2018–2023 `noise_infusion`; **2024 `unknown`** | Task 12 |
| SUSB | `size_concept.value = "enterprise"`, column `ENTRSIZE`; latest year 2022 | Task 13 |

---

## File Structure

Files this stage creates or modifies. Every path is repo-root-relative.

| Path | Responsibility |
|---|---|
| `pyproject.toml` | D4 toolchain: hatchling build, `requires-python >= 3.14`, deps, ruff/black/pytest/interrogate config |
| `uv.lock` | Locked resolution (generated, committed) |
| `src/logging_employment/__init__.py` | Package version only |
| `src/logging_employment/constants.py` | Window, industry/ownership/agglvl/size codes, `STATES_DC_FIPS`, measured code allowlists |
| `src/logging_employment/classification.py` | §3.1 memo, read anchored from the spec file — never retyped |
| `src/logging_employment/contracts.py` | Polars schemas for all five tables + `bridge`; `observation_status` enum; `schema_fingerprint` |
| `src/logging_employment/config.py` | Pydantic config model, `.env` loading, secret redaction |
| `src/logging_employment/cli.py` | Typer app: `validate-config`, `registry verify`, `fetch`, `build-harmonized` |
| `src/logging_employment/errors.py` | Named fail-closed exceptions |
| `src/logging_employment/store.py` | Content-addressed immutable raw store, `source_snapshot` rows, manifest writer, secret guard |
| `src/logging_employment/registry/models.py` | `SourceRegistryRow` (§7.1's 18 fields) |
| `src/logging_employment/registry/loader.py` | Loads the registry YAML into rows |
| `src/logging_employment/registry/validation.py` | `registry verify` logic |
| `src/logging_employment/registry/sources.yaml` | Seed registry rows for qcew, qcew_size, cbp |
| `src/logging_employment/ingest/base.py` | `HttpFetcher` (contact-email UA), `Retrieval`, retry policy |
| `src/logging_employment/ingest/qcew.py` | Both QCEW routes, boundary probe, column reconciliation, `qcew_monthly` parser |
| `src/logging_employment/ingest/qcew_size.py` | By-size file, dimensionality assertion, `qcew_national_size` parser |
| `src/logging_employment/ingest/cbp.py` | Metadata discovery, LFO query, `cbp_state_size` parser |
| `src/logging_employment/harmonize/disclosure.py` | Disclosure-regime registry keyed by CBP reference year; fail-closed |
| `src/logging_employment/harmonize/dimensions.py` | Versioned dimensions per §8.6 |
| `src/logging_employment/harmonize/bridge.py` | `bridge` table (§8.6's eight fields) |
| `src/logging_employment/harmonize/naics.py` | Mechanical 113310 crosswalk across window vintages |
| `src/logging_employment/harmonize/concepts.py` | Enterprise-size and nonemployer concept guards |
| `src/logging_employment/build.py` | `build-harmonized` orchestration, deterministic Parquet writing |
| `tests/unit/…`, `tests/integration/…` | One test module per source module above |
| `tests/fixtures/` | Frozen bytes copied from `data/raw/audit/` |

**Stage 0's `scripts/audit/` and `tests/audit/` are not touched.** They keep working under
`uv run --no-project`; `tests/conftest.py` already puts `scripts/audit` on `sys.path`. Task 1's
exit includes proving both suites still collect.

---

### Task 1: Package scaffold and toolchain lock

**Files:**
- Create: `pyproject.toml`
- Create: `src/logging_employment/__init__.py`
- Create: `tests/unit/test_package.py`
- Generated: `uv.lock`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an installable package importable as `logging_employment`, exposing
  `logging_employment.__version__: str`. Every later task imports from this package.

- [x] **Step 1: Write the failing test**

Create `tests/unit/test_package.py`:

```python
"""The package installs and exposes a version."""

from __future__ import annotations


def test_package_exposes_a_version_string() -> None:
    import logging_employment

    assert isinstance(logging_employment.__version__, str)
    assert logging_employment.__version__.count(".") >= 1
```

- [x] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_package.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment'` (uv will also
complain there is no project; that is the same failure).

- [x] **Step 3: Write `pyproject.toml`**

```toml
[project]
name = "logging-employment"
version = "0.1.0"
description = "Monthly state Logging (NAICS 113310) employment by establishment size class"
readme = "README.md"
requires-python = ">=3.14"
license = { text = "MIT" }
authors = [{ name = "Lowell Mason", email = "mason.lowell@mac.com" }]
dependencies = [
    "httpx>=0.28",
    "polars>=1.44",
    "pyarrow>=25.0",
    "pydantic>=2.13",
    "pyyaml>=6.0",
    "typer>=0.27",
]

[project.scripts]
logging-estimates = "logging_employment.cli:app"

[dependency-groups]
dev = [
    "black>=25.0",
    "interrogate>=1.7",
    "pytest>=8.0",
    "python-dotenv>=1.2",
    "ruff>=0.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/logging_employment"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.black]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "network: hits a live source endpoint; excluded from the default run",
    "slow: takes more than a few seconds",
]

[tool.interrogate]
fail-under = 100
exclude = ["tests"]
```

- [x] **Step 4: Create the package module**

Create `src/logging_employment/__init__.py`:

```python
"""Monthly state Logging employment by establishment size class."""

from __future__ import annotations

__version__ = "0.1.0"
```

- [x] **Step 5: Lock and install**

Run: `uv lock && uv sync`
Expected: `uv.lock` is created; the sync resolves on CPython 3.14. If uv reports it must download
CPython 3.14, let it.

- [x] **Step 6: Run the test to verify it passes**

Run: `uv run pytest tests/unit/test_package.py -v`
Expected: PASS, 1 passed.

- [x] **Step 7: Prove the CLI entry point is registered**

Run: `uv run logging-estimates --help`
Expected: this FAILS right now with `ModuleNotFoundError` or an AttributeError on `cli` — the
module does not exist until Task 4. That is expected; do not create a stub `cli.py` here. Record
the observed error in your implementer report and move on.

- [x] **Step 8: Prove Stage 0's suite is undisturbed**

Run: `PYTHONPATH=scripts/audit uv run --no-project pytest tests/audit -q`
Expected: the Stage 0 suite collects and passes exactly as before this task (Stage 0 reported 666
tests at plan completion; report the number you observe rather than asserting that one).

- [x] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock src/logging_employment/__init__.py tests/unit/test_package.py
git commit -m "feat(pkg): scaffold the logging_employment package on Python 3.14"
```

---

### Task 2: Constants, the §3.1 classification memo, and measured code allowlists

**Files:**
- Create: `src/logging_employment/constants.py`
- Create: `src/logging_employment/classification.py`
- Create: `src/logging_employment/errors.py`
- Create: `tests/unit/test_constants.py`
- Create: `tests/unit/test_classification.py`

**Interfaces:**
- Consumes: Task 1's package.
- Produces:
  - `constants.WINDOW_START: str`, `WINDOW_END: str`, `INDUSTRY_CODE: str`,
    `PRIVATE_OWN_CODE: str`, `NATIONAL_AREA: str`, `STATES_DC_FIPS: tuple[str, ...]`,
    `STATE_AREAS: frozenset[str]`, `QCEW_STATE_AGGLVL: str`, `QCEW_NATIONAL_AGGLVL: str`,
    `QCEW_ALL_SIZES_CODE: str`, `QCEW_DISCLOSURE_CODES: frozenset[str]`
  - `classification.classification_memo(spec_path: Path) -> dict[str, str]` returning exactly the
    four keys `industry_code_supplied`, `industry_code_used`, `industry_title`,
    `classification_status`
  - `errors.UnknownDisclosureCodeError`, `errors.UnknownDisclosureRegimeError`,
    `errors.SchemaMismatchError`, `errors.MissingCrossTabulationError`, `errors.ConceptViolationError`

- [x] **Step 1: Write the failing tests for the allowlist**

Create `tests/unit/test_constants.py`:

```python
"""Constants carry the measured code sets, and say so."""

from __future__ import annotations

from logging_employment import constants


def test_states_dc_has_fifty_one_members() -> None:
    assert len(constants.STATES_DC_FIPS) == 51
    assert len(set(constants.STATES_DC_FIPS)) == 51


def test_state_areas_are_fips_plus_three_zeroes() -> None:
    assert constants.STATE_AREAS == frozenset(f"{f}000" for f in constants.STATES_DC_FIPS)
    assert "11000" in constants.STATE_AREAS  # DC is IN the universe even though it publishes nothing
    assert "72000" not in constants.STATE_AREAS  # Puerto Rico is not


def test_disclosure_allowlist_is_the_three_measured_codes() -> None:
    assert constants.QCEW_DISCLOSURE_CODES == frozenset({"", "N", "-"})


def test_the_allowlist_docstring_does_not_claim_a_titles_file_defines_it() -> None:
    # A deliberate prose pin, and the only one in this plan. It is framed negatively -- it fails if
    # someone rewrites the comment to claim BLS documents these codes -- which is the one shape
    # worth pinning. Do not copy this pattern to assert that a sentence exists.
    # BLS publishes no titles file for disclosure_code (Stage 0: titles_available.disclosure_code
    # is null). A comment claiming otherwise would misdescribe the provenance.
    source = (constants.__file__ and open(constants.__file__).read()) or ""
    marker = "QCEW_DISCLOSURE_CODES"
    block = source[source.index(marker):source.index(marker) + 800]
    assert "measured" in block
    assert "no titles file" in block
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_constants.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.constants'`.

- [x] **Step 3: Write `constants.py`**

```python
"""Fixed values for the D1 window, the target industry, and the measured QCEW code sets."""

from __future__ import annotations

WINDOW_START = "2017-01"
WINDOW_END = "2024-12"

INDUSTRY_CODE = "113310"
PRIVATE_OWN_CODE = "5"

NATIONAL_AREA = "US000"
STATES_DC_FIPS: tuple[str, ...] = (
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17",
    "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31",
    "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "44", "45", "46",
    "47", "48", "49", "50", "51", "53", "54", "55", "56",
)
STATE_AREAS = frozenset(f"{fips}000" for fips in STATES_DC_FIPS)

QCEW_NATIONAL_AGGLVL = "18"  # "National, NAICS 6-digit -- by ownership sector"
QCEW_STATE_AGGLVL = "58"  # "State, NAICS 6-digit -- by ownership sector"
QCEW_ALL_SIZES_CODE = "0"  # "All establishment sizes"

# The three disclosure codes measured on 113310 rows across the whole D1 window by the Stage 0
# audit (`qcew_codes.findings.codes_present.disclosure_code`): '' 17302 rows, '-' 935, 'N' 40875.
# BLS publishes no titles file for this dimension -- Stage 0 recorded
# `titles_available.disclosure_code = null` -- so this set is measured, not documented, and
# nothing here defines what a code means. A fourth code halting the run (§18.3) is the correct
# response to a set that was only ever observed.
QCEW_DISCLOSURE_CODES = frozenset({"", "N", "-"})
```

- [x] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_constants.py -v`
Expected: PASS, 4 passed.

- [x] **Step 5: Write the failing test for the classification memo**

Create `tests/unit/test_classification.py`:

```python
"""The §3.1 memo is read from the spec, not retyped."""

from __future__ import annotations

from pathlib import Path

import pytest

from logging_employment.classification import classification_memo

SPEC = Path(__file__).resolve().parents[2] / "specs" / "logging-employment-spec.md"


def test_memo_carries_all_four_fields_from_the_spec() -> None:
    memo = classification_memo(SPEC)
    assert set(memo) == {
        "industry_code_supplied",
        "industry_code_used",
        "industry_title",
        "classification_status",
    }
    assert memo["industry_code_used"] == "113310"


def test_memo_reads_the_section_31_fence_and_not_appendix_a(tmp_path: Path) -> None:
    # Appendix A carries three of the four names in YAML `key: value` form. A parser that scanned
    # the whole file could read them from there; an anchored one cannot reach them.
    doctored = tmp_path / "spec.md"
    doctored.write_text(
        "### 3.1 Classification decision\n\n```text\n"
        "industry_code_supplied = 'AAA'\nindustry_code_used = 'BBB'\n"
        "industry_title = 'Anchored'\nclassification_status = 'from_section_31'\n```\n\n"
        "## Appendix A\n\n```yaml\nindustry_code_used: 'WRONG'\nindustry_title: 'Wrong'\n```\n"
    )
    assert classification_memo(doctored)["industry_title"] == "Anchored"


def test_memo_raises_when_section_31_is_missing(tmp_path: Path) -> None:
    empty = tmp_path / "spec.md"
    empty.write_text("## 2. Something else\n\n```text\nindustry_code_used = '113310'\n```\n")
    with pytest.raises(ValueError, match="3.1"):
        classification_memo(empty)
```

- [x] **Step 6: Run to verify it fails**

Run: `uv run pytest tests/unit/test_classification.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.classification'`.

- [x] **Step 7: Write `classification.py`**

The anchored-read approach is Stage 0's, in `scripts/audit/verify_extracts.py::classification_block`
— read that function before writing this one; it documents why anchoring matters here.

```python
"""The §3.1 classification memo, read from the spec's own fenced block.

The four values are never retyped into this package. Retyping them would make this module a second
source of truth that can silently drift from the spec, and §3.1's whole point is that the supplied
code `1113310` and its correction are *recorded* rather than quietly replaced.
"""

from __future__ import annotations

import re
from pathlib import Path

_FIELDS = (
    "industry_code_supplied",
    "industry_code_used",
    "industry_title",
    "classification_status",
)


def _section_31_fence(spec_text: str) -> list[str]:
    """The lines inside the fenced block under the spec's own `### 3.1` heading.

    Anchored rather than first-match: three of the four names recur in Appendix A's example
    configuration as YAML `key: value`, and an unanchored scan of a restructured spec could read
    them from there. The scan starts at the `### 3.1` heading and takes the first fence to open
    before the next heading of equal or higher level.
    """
    lines = spec_text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if re.match(r"###\s+3\.1(\s|$)", line)), None
    )
    if start is None:
        raise ValueError("the spec has no `### 3.1` heading to anchor the classification memo to")
    opened: int | None = None
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if opened is None and re.match(r"#{1,3}\s", line):
            raise ValueError("§3.1 carries no fenced block before the next heading")
        if line.startswith("```"):
            if opened is None:
                opened = i
            else:
                return lines[opened + 1 : i]
    raise ValueError("§3.1's fenced block is never closed")


def classification_memo(spec_path: Path) -> dict[str, str]:
    """Map each §3.1 field name to the value the spec assigns it.

    Raises ValueError when the heading, the fence, or any of the four fields is absent.
    """
    block = _section_31_fence(spec_path.read_text())
    memo: dict[str, str] = {}
    for line in block:
        if "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name in _FIELDS:
            memo[name] = value.strip().strip("'\"")
    missing = [f for f in _FIELDS if f not in memo]
    if missing:
        raise ValueError(f"§3.1's block does not assign {missing}")
    return memo
```

- [x] **Step 8: Run to verify it passes**

Run: `uv run pytest tests/unit/test_classification.py -v`
Expected: PASS, 3 passed.

- [x] **Step 9: Write `errors.py`**

```python
"""Named fail-closed exceptions (§18.3).

Each carries the offending value, so a caller's log line names what halted the run rather than
only that something did.
"""

from __future__ import annotations


class LoggingEmploymentError(Exception):
    """Base class for every fail-closed condition in this package."""


class UnknownDisclosureCodeError(LoggingEmploymentError):
    """A QCEW disclosure code outside the measured allowlist reached the parser."""


class UnknownDisclosureRegimeError(LoggingEmploymentError):
    """A CBP reference year carries no established disclosure regime."""


class SchemaMismatchError(LoggingEmploymentError):
    """A fetched file's columns do not match the schema the parser declares."""


class MissingCrossTabulationError(LoggingEmploymentError):
    """A requested simultaneous cross-tabulation is absent from the source file."""


class ConceptViolationError(LoggingEmploymentError):
    """A value would cross a concept boundary the spec forbids crossing."""
```

- [x] **Step 10: Run the whole suite and commit**

Run: `uv run pytest tests/unit -v`
Expected: PASS, 8 passed.

```bash
git add src/logging_employment/constants.py src/logging_employment/classification.py \
        src/logging_employment/errors.py tests/unit/test_constants.py \
        tests/unit/test_classification.py
git commit -m "feat(core): add constants, the anchored §3.1 memo, and fail-closed errors"
```

---

### Task 3: Table contracts, the `observation_status` enum, and schema fingerprints

**Files:**
- Create: `src/logging_employment/contracts.py`
- Create: `tests/unit/test_contracts.py`

**Interfaces:**
- Consumes: Task 2's `constants`.
- Produces:
  - `contracts.OBSERVATION_STATUSES: tuple[str, ...]` = `("observed", "suppressed", "true_zero", "absent")`
  - `contracts.SOURCE_REGISTRY_SCHEMA`, `SOURCE_SNAPSHOT_SCHEMA`, `QCEW_MONTHLY_SCHEMA`,
    `QCEW_NATIONAL_SIZE_SCHEMA`, `CBP_STATE_SIZE_SCHEMA`, `BRIDGE_SCHEMA` — each a
    `dict[str, polars.DataType]` in the spec's declared field order
  - `contracts.schema_fingerprint(schema: dict[str, pl.DataType]) -> str` — a 64-char sha256
  - `contracts.validate_frame(frame: pl.DataFrame, schema: dict[str, pl.DataType], name: str) -> None`
    raising `SchemaMismatchError`

**Why this task exists before any parser.** `observation_status` is named in four spec contracts
(§7.3, §7.4, §7.7, §15.2) and **enumerated in none of them**. Three parser tasks would otherwise
invent three vocabularies. The four values are fixed here, and the distinction that forces the
fourth one is real: DC publishes no private 113310 row in any of the 96 months, which is neither a
suppressed cell nor a zero.

- [x] **Step 1: Write the failing test**

Create `tests/unit/test_contracts.py`:

```python
"""Table schemas, the observation-status vocabulary, and fingerprint determinism."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment import contracts
from logging_employment.errors import SchemaMismatchError


def test_observation_statuses_separate_absent_from_suppressed_and_zero() -> None:
    assert contracts.OBSERVATION_STATUSES == ("observed", "suppressed", "true_zero", "absent")


def test_qcew_monthly_carries_every_field_the_spec_names() -> None:
    expected = [
        "snapshot_id", "release_vintage", "release_status", "reference_quarter",
        "reference_month", "area_fips", "area_type", "state_fips", "industry_code",
        "naics_vintage", "ownership_code", "aggregation_level", "size_code",
        "qtrly_establishments", "employment_raw", "employment_value", "wages_raw",
        "wages_value", "disclosure_code", "observation_status", "is_published_numeric_zero",
        "is_true_zero", "source_row_hash",
    ]
    assert list(contracts.QCEW_MONTHLY_SCHEMA) == expected


def test_area_fips_is_a_string_so_leading_zeros_survive() -> None:
    assert contracts.QCEW_MONTHLY_SCHEMA["area_fips"] == pl.String
    assert contracts.QCEW_MONTHLY_SCHEMA["state_fips"] == pl.String


def test_fingerprint_is_deterministic_and_order_sensitive() -> None:
    a = {"x": pl.String, "y": pl.Int64}
    b = {"y": pl.Int64, "x": pl.String}
    assert contracts.schema_fingerprint(a) == contracts.schema_fingerprint(a)
    assert len(contracts.schema_fingerprint(a)) == 64
    assert contracts.schema_fingerprint(a) != contracts.schema_fingerprint(b)


def test_validate_frame_names_the_offending_columns() -> None:
    frame = pl.DataFrame({"x": ["a"]})
    with pytest.raises(SchemaMismatchError, match="y"):
        contracts.validate_frame(frame, {"x": pl.String, "y": pl.Int64}, "toy")
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_contracts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.contracts'`.

- [x] **Step 3: Write `contracts.py`**

```python
"""Polars schemas for every table this stage persists, and their fingerprints.

Field order follows the spec's own listing in §7.1-§7.5 and §8.6. Order is load-bearing: the
schema fingerprint is computed over the ordered pairs, so a reordering is a schema change and is
meant to be detected as one.
"""

from __future__ import annotations

import hashlib
import json

import polars as pl

from .errors import SchemaMismatchError

# `observation_status` is named in §7.3, §7.4, §7.7 and §15.2 and enumerated in none of them, so
# these four values are this package's decision rather than the spec's text. `absent` is the one
# that is easy to miss and impossible to fold in: Stage 0 measured that DC (11000) publishes no
# private 113310 row in any of the window's 96 months, which is not a suppressed cell and not a
# zero. Collapsing it into either would state something about DC that no source published.
OBSERVATION_STATUSES: tuple[str, ...] = ("observed", "suppressed", "true_zero", "absent")

SOURCE_REGISTRY_SCHEMA: dict[str, pl.DataType] = {
    "source_id": pl.String,
    "agency": pl.String,
    "dataset": pl.String,
    "landing_url": pl.String,
    "endpoint_pattern": pl.String,
    "access_status": pl.String,
    "frequency": pl.String,
    "reference_period": pl.String,
    "geography": pl.String,
    "industry_detail": pl.String,
    "ownership": pl.String,
    "statistical_unit": pl.String,
    "employment_concept": pl.String,
    "size_dimension": pl.String,
    "disclosure_regime": pl.String,
    "revision_policy": pl.String,
    "model_role": pl.String,
    "limitations": pl.String,
}

SOURCE_SNAPSHOT_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "source_id": pl.String,
    "request_url_or_file": pl.String,
    "request_parameters_json": pl.String,
    "retrieved_at_utc": pl.String,
    "source_publication_date": pl.String,
    "reference_start": pl.String,
    "reference_end": pl.String,
    "release_status": pl.String,
    "naics_vintage": pl.String,
    "schema_fingerprint": pl.String,
    "content_sha256": pl.String,
    "byte_count": pl.Int64,
    "http_status": pl.Int64,
    "parser_version": pl.String,
    "raw_path": pl.String,
}

QCEW_MONTHLY_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "release_vintage": pl.String,
    "release_status": pl.String,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "area_fips": pl.String,
    "area_type": pl.String,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "ownership_code": pl.String,
    "aggregation_level": pl.String,
    "size_code": pl.String,
    "qtrly_establishments": pl.Int64,
    "employment_raw": pl.String,
    "employment_value": pl.Int64,
    "wages_raw": pl.String,
    "wages_value": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
    "is_published_numeric_zero": pl.Boolean,
    "is_true_zero": pl.Boolean,
    "source_row_hash": pl.String,
}

QCEW_NATIONAL_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "reference_quarter": pl.String,
    "reference_month": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "size_class": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "disclosure_code": pl.String,
    "observation_status": pl.String,
}

CBP_STATE_SIZE_SCHEMA: dict[str, pl.DataType] = {
    "snapshot_id": pl.String,
    "reference_year": pl.Int64,
    "state_fips": pl.String,
    "industry_code": pl.String,
    "naics_vintage": pl.String,
    "legal_form_code": pl.String,
    "size_code": pl.String,
    "size_label": pl.String,
    "size_lower": pl.Int64,
    "size_upper": pl.Int64,
    "establishments": pl.Int64,
    "employment": pl.Int64,
    "employment_flag": pl.String,
    "employment_noise_range": pl.String,
    "disclosure_status": pl.String,
    "disclosure_regime": pl.String,
    "reference_period": pl.String,
}

BRIDGE_SCHEMA: dict[str, pl.DataType] = {
    "bridge_id": pl.String,
    "source_concept": pl.String,
    "target_concept": pl.String,
    "valid_start": pl.String,
    "valid_end": pl.String,
    "method": pl.String,
    "uncertainty_treatment": pl.String,
    "verification_status": pl.String,
}


def schema_fingerprint(schema: dict[str, pl.DataType]) -> str:
    """A sha256 over the schema's ordered (name, dtype) pairs."""
    payload = json.dumps([[name, str(dtype)] for name, dtype in schema.items()])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_frame(frame: pl.DataFrame, schema: dict[str, pl.DataType], name: str) -> None:
    """Raise SchemaMismatchError unless the frame's columns and dtypes match the schema exactly."""
    missing = [c for c in schema if c not in frame.columns]
    extra = [c for c in frame.columns if c not in schema]
    if missing or extra:
        raise SchemaMismatchError(f"{name}: missing={missing} extra={extra}")
    wrong = [
        (c, str(schema[c]), str(frame.schema[c])) for c in schema if frame.schema[c] != schema[c]
    ]
    if wrong:
        raise SchemaMismatchError(f"{name}: dtype mismatches {wrong}")
```

- [x] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_contracts.py -v`
Expected: PASS, 5 passed.

- [x] **Step 5: Commit**

```bash
git add src/logging_employment/contracts.py tests/unit/test_contracts.py
git commit -m "feat(contracts): declare table schemas, observation statuses, and fingerprints"
```

---

### Task 4: Configuration model and the `validate-config` command

**Files:**
- Create: `src/logging_employment/config.py`
- Create: `src/logging_employment/cli.py`
- Create: `config.yaml`
- Create: `tests/unit/test_config.py`

**Interfaces:**
- Consumes: Task 2's `constants` and `errors`; Task 3's `contracts`.
- Produces:
  - `config.Config` (Pydantic `BaseModel`) with nested `ProjectConfig`, `StorageConfig`,
    `SourcesConfig`; `Config.sources.cbp.api_key_env: str`
  - `config.load_config(path: Path) -> Config`
  - `config.resolved_dict(cfg: Config) -> dict[str, object]` — the config as written to
    `runs/<run_id>/config.resolved.yaml`, **with no secret value present**
  - `config.credentials() -> dict[str, str]` reading `.env` via python-dotenv
  - `cli.app` — the Typer application registered as `logging-estimates`

- [x] **Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
"""Config parses Appendix A's shape, and the resolved form carries no secret."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from logging_employment.config import Config, load_config, resolved_dict

APPENDIX_A = """
project:
  name: 'logging-state-employment'
  industry_code_supplied: '1113310'
  industry_code_used: '113310'
  industry_title: 'Logging'
  ownership: 'private'
  geography_universe: 'states_dc'
  start_month: '2017-01'
  end_month: '2024-12'
  analysis_mode: 'retrospective_final'
  size_concept: 'march_reference'
storage:
  raw_uri: 'data/raw'
  staged_uri: 'data/staged'
  output_uri: 'runs'
  immutable_raw: true
sources:
  qcew:
    enabled: true
    release_status: 'final'
  qcew_size:
    enabled: true
  cbp:
    enabled: true
    api_key_env: 'CENSUS_API_KEY'
    fail_on_unknown_disclosure_regime: true
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_appendix_a_config_parses(tmp_path: Path) -> None:
    cfg = load_config(_write(tmp_path, APPENDIX_A))
    assert cfg.project.geography_universe == "states_dc"
    assert cfg.project.start_month == "2017-01"
    assert cfg.sources.cbp.api_key_env == "CENSUS_API_KEY"
    assert cfg.sources.cbp.fail_on_unknown_disclosure_regime is True


def test_an_unknown_analysis_mode_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_config(_write(tmp_path, APPENDIX_A.replace("retrospective_final", "guesswork")))


def test_a_window_outside_d1_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="start_month"):
        load_config(_write(tmp_path, APPENDIX_A.replace("'2017-01'", "'2017-1'")))


def test_resolved_config_names_the_env_var_but_never_a_key_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CENSUS_API_KEY", "supersecretvalue")
    resolved = resolved_dict(load_config(_write(tmp_path, APPENDIX_A)))
    assert "supersecretvalue" not in str(resolved)
    assert resolved["sources"]["cbp"]["api_key_env"] == "CENSUS_API_KEY"
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.config'`.

- [x] **Step 3: Write `config.py`**

```python
"""Typed configuration, loaded from YAML, with credentials kept out of the resolved form."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, field_validator

_MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# Named here so the secret guard and the resolved-config writer share one list (D3).
SECRET_ENV_VARS = ("CENSUS_API_KEY", "BLS_API_KEY", "BEA_API_KEY", "FRED_API_KEY")


class _Strict(BaseModel):
    """Base model that rejects unknown keys, so a typo in config.yaml halts rather than defaults."""

    model_config = ConfigDict(extra="forbid")


class ProjectConfig(_Strict):
    """The estimand: industry, ownership, geography universe, window, and mode."""

    name: str
    industry_code_supplied: str
    industry_code_used: str
    industry_title: str
    ownership: Literal["private"]
    geography_universe: Literal["states_dc"]
    start_month: str
    end_month: str
    analysis_mode: Literal["retrospective_final", "realtime_asof"]
    size_concept: Literal["march_reference", "contemporaneous_modeled"]

    @field_validator("start_month", "end_month")
    @classmethod
    def _is_a_month(cls, value: str) -> str:
        if not _MONTH.match(value):
            raise ValueError(f"expected YYYY-MM, got {value!r}")
        return value


class StorageConfig(_Strict):
    """Where raw bytes, staged frames, and run outputs live."""

    raw_uri: str
    staged_uri: str
    output_uri: str
    immutable_raw: bool


class QcewSourceConfig(_Strict):
    """QCEW quarterly acquisition settings."""

    enabled: bool
    release_status: Literal["final", "preliminary"] = "final"


class QcewSizeSourceConfig(_Strict):
    """QCEW by-size acquisition settings."""

    enabled: bool


class CbpSourceConfig(_Strict):
    """CBP acquisition settings, including the fail-closed disclosure switch."""

    enabled: bool
    api_key_env: str
    fail_on_unknown_disclosure_regime: bool


class SourcesConfig(_Strict):
    """The three sources Stage 1 ingests. Later stages add their own keys."""

    qcew: QcewSourceConfig
    qcew_size: QcewSizeSourceConfig
    cbp: CbpSourceConfig


class Config(_Strict):
    """The whole resolved configuration."""

    project: ProjectConfig
    storage: StorageConfig
    sources: SourcesConfig


def load_config(path: Path) -> Config:
    """Parse and validate a config file. Raises pydantic.ValidationError on any violation."""
    return Config.model_validate(yaml.safe_load(path.read_text()))


def resolved_dict(cfg: Config) -> dict[str, object]:
    """The config as it is written to a run directory.

    Only `api_key_env` -- the *name* of an environment variable -- survives; no value is read
    here, so no key can leak into a manifest through this path (§7.2, D3).
    """
    return cfg.model_dump(mode="json")


def credentials(env_path: Path | None = None) -> dict[str, str]:
    """Credentials from the repo-root `.env`, falling back to the process environment.

    Returns only the keys D3 names. The caller passes values to a request; nothing here writes
    them anywhere.
    """
    values: dict[str, str] = {}
    if env_path is not None and env_path.exists():
        values.update({k: v for k, v in dotenv_values(env_path).items() if v is not None})
    for name in (*SECRET_ENV_VARS, "BLS_CONTACT_EMAIL"):
        from_env = os.environ.get(name)
        if from_env:
            values[name] = from_env
    return values
```

- [x] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS, 4 passed.

- [x] **Step 5: Write `config.yaml` at the repo root**

Copy Appendix A's block verbatim for the three keys this stage supports — `project`, `storage`, and
the `qcew`/`qcew_size`/`cbp` entries of `sources`. Leave out the `constraints`, `model`,
`reconciliation`, `validation`, `promotion` and `disclosure` blocks: `Config` forbids extra keys,
and those blocks belong to Stages 2–8. Record in your implementer report that you did so.

- [x] **Step 6: Write `cli.py` with `validate-config` only**

```python
"""The `logging-estimates` command-line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from .config import load_config

app = typer.Typer(add_completion=False, help="Monthly state Logging employment estimates.")


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
```

- [x] **Step 7: Run the command end to end**

Run: `uv run logging-estimates validate-config --config config.yaml`
Expected: `OK: 113310 / private / states_dc / 2017-01..2024-12`

- [x] **Step 8: Commit**

```bash
git add src/logging_employment/config.py src/logging_employment/cli.py config.yaml \
        tests/unit/test_config.py
git commit -m "feat(config): add the typed config model and validate-config"
```

---

### Task 5: Immutable content-addressed raw store, snapshots, and the HTTP client

**Files:**
- Create: `src/logging_employment/store.py`
- Create: `src/logging_employment/ingest/__init__.py`
- Create: `src/logging_employment/ingest/base.py`
- Create: `tests/unit/test_store.py`
- Create: `tests/unit/test_ingest_base.py`

**Interfaces:**
- Consumes: Task 2's `errors`; Task 3's `SOURCE_SNAPSHOT_SCHEMA`; Task 4's `config`.
- Produces:
  - `ingest.base.HttpFetcher(contact_email: str, timeout: float = 30.0)` with
    `.get(url: str, params: dict[str, str] | None = None) -> FetchedBytes`
  - `ingest.base.FetchedBytes` — frozen dataclass with `url: str`, `params: dict[str, str]`,
    `content: bytes`, `http_status: int`, `retrieved_at_utc: str`
  - `store.RawStore(root: Path)` with
    `.put(source_id: str, fetched: FetchedBytes, filename: str) -> StoredObject` and
    `.path_for(source_id: str, content_sha256: str, filename: str) -> Path`
  - `store.StoredObject` — frozen dataclass with `retrieval_id: str` (the full sha256),
    `content_sha256: str`, `byte_count: int`, `raw_path: Path`, `was_already_present: bool`
  - `store.snapshot_row(...) -> dict[str, object]` conforming to `SOURCE_SNAPSHOT_SCHEMA`
  - `store.assert_no_secret(payload: str, secrets: Sequence[str]) -> None` raising `ValueError`

- [x] **Step 1: Write the failing store test**

Create `tests/unit/test_store.py`:

```python
"""The raw store is content-addressed, immutable, and secret-free."""

from __future__ import annotations

from pathlib import Path

import pytest

from logging_employment.ingest.base import FetchedBytes
from logging_employment.store import RawStore, assert_no_secret


def _fetched(content: bytes) -> FetchedBytes:
    return FetchedBytes(
        url="https://example.invalid/x.csv",
        params={},
        content=content,
        http_status=200,
        retrieved_at_utc="2026-09-05T00:00:00+00:00",
    )


def test_identical_bytes_produce_one_retrieval_id(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    first = store.put("qcew", _fetched(b"a,b\n1,2\n"), "slice.csv")
    second = store.put("qcew", _fetched(b"a,b\n1,2\n"), "slice.csv")
    assert first.retrieval_id == second.retrieval_id
    assert first.was_already_present is False
    assert second.was_already_present is True


def test_different_bytes_produce_different_retrieval_ids(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    a = store.put("qcew", _fetched(b"one"), "slice.csv")
    b = store.put("qcew", _fetched(b"two"), "slice.csv")
    assert a.retrieval_id != b.retrieval_id


def test_a_stored_object_is_not_rewritten(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    stored = store.put("qcew", _fetched(b"original"), "slice.csv")
    mtime = stored.raw_path.stat().st_mtime_ns
    store.put("qcew", _fetched(b"original"), "slice.csv")
    assert stored.raw_path.stat().st_mtime_ns == mtime
    assert stored.raw_path.read_bytes() == b"original"


def test_assert_no_secret_raises_on_a_leaked_value() -> None:
    with pytest.raises(ValueError, match="secret"):
        assert_no_secret("url=...&key=abc123", ["abc123"])


def test_assert_no_secret_ignores_empty_secrets() -> None:
    assert_no_secret("anything at all", ["", None])  # type: ignore[list-item]
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.store'`.

- [x] **Step 3: Write `ingest/base.py`**

```python
"""One HTTP client for every source, carrying the contact address BLS requires."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import httpx

from .. import __version__


@dataclass(frozen=True)
class FetchedBytes:
    """A response body with the request that produced it. Bytes are never decoded here."""

    url: str
    params: dict[str, str]
    content: bytes
    http_status: int
    retrieved_at_utc: str


@dataclass
class HttpFetcher:
    """A thin httpx wrapper with the D3 User-Agent and no retry-on-4xx.

    `data.bls.gov` admits scripted clients only when the User-Agent carries a contact address, so
    `contact_email` is required rather than optional.

    A non-200 response is returned rather than raised: Stage 0 measured Census and USDA endpoints
    answering 200 with an error body and 204/404 with a meaningful one, so the status is evidence
    the caller classifies, not a failure this layer decides.
    """

    contact_email: str
    timeout: float = 30.0
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Open one connection pool with the required User-Agent."""
        if not self.contact_email:
            raise ValueError("contact_email is required (D3: BLS_CONTACT_EMAIL)")
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": f"logging-employment/{__version__} ({self.contact_email})"},
        )

    def get(self, url: str, params: dict[str, str] | None = None) -> FetchedBytes:
        """GET a URL and return its bytes verbatim, whatever the status."""
        response = self._client.get(url, params=params or {})
        return FetchedBytes(
            url=url,
            params=dict(params or {}),
            content=response.content,
            http_status=response.status_code,
            retrieved_at_utc=dt.datetime.now(dt.UTC).isoformat(),
        )

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()
```

- [x] **Step 4: Write `store.py`**

```python
"""The immutable, content-addressed raw store and the `source_snapshot` row it produces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .ingest.base import FetchedBytes


@dataclass(frozen=True)
class StoredObject:
    """One immutable object in the raw store."""

    retrieval_id: str
    content_sha256: str
    byte_count: int
    raw_path: Path
    was_already_present: bool


def assert_no_secret(payload: str, secrets: Sequence[str | None]) -> None:
    """Raise ValueError if any non-empty secret value appears in the payload (§7.2, D3)."""
    for secret in secrets:
        if secret and secret in payload:
            raise ValueError("a secret value reached a manifest payload; refusing to write it")


class RawStore:
    """`data/raw/<source_id>/<retrieval_id>/<filename>`, written once and never rewritten.

    `retrieval_id` is the content sha256, so the same bytes always land in the same place and a
    rerun against an unchanged source is a no-op rather than a second copy (§6.2).
    """

    def __init__(self, root: Path) -> None:
        """Anchor the store at `root`, creating it if absent."""
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, source_id: str, content_sha256: str, filename: str) -> Path:
        """Where an object with this hash lives, whether or not it exists yet."""
        return self.root / source_id / content_sha256 / filename

    def put(self, source_id: str, fetched: FetchedBytes, filename: str) -> StoredObject:
        """Store bytes verbatim and return their identity. Existing objects are left untouched."""
        digest = hashlib.sha256(fetched.content).hexdigest()
        path = self.path_for(source_id, digest, filename)
        already = path.exists()
        if not already:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(fetched.content)
        return StoredObject(
            retrieval_id=digest,
            content_sha256=digest,
            byte_count=len(fetched.content),
            raw_path=path,
            was_already_present=already,
        )


def snapshot_row(
    *,
    source_id: str,
    fetched: FetchedBytes,
    stored: StoredObject,
    reference_start: str,
    reference_end: str,
    release_status: str,
    naics_vintage: str,
    schema_fingerprint: str,
    parser_version: str,
    source_publication_date: str,
    secrets: Sequence[str | None],
) -> dict[str, object]:
    """Build one `source_snapshot` row, refusing to emit it if a secret is present."""
    params_json = json.dumps(fetched.params, sort_keys=True)
    assert_no_secret(fetched.url, secrets)
    assert_no_secret(params_json, secrets)
    return {
        "snapshot_id": stored.retrieval_id,
        "source_id": source_id,
        "request_url_or_file": fetched.url,
        "request_parameters_json": params_json,
        "retrieved_at_utc": fetched.retrieved_at_utc,
        "source_publication_date": source_publication_date,
        "reference_start": reference_start,
        "reference_end": reference_end,
        "release_status": release_status,
        "naics_vintage": naics_vintage,
        "schema_fingerprint": schema_fingerprint,
        "content_sha256": stored.content_sha256,
        "byte_count": stored.byte_count,
        "http_status": fetched.http_status,
        "parser_version": parser_version,
        "raw_path": str(stored.raw_path),
    }
```

- [x] **Step 5: Run the store test to verify it passes**

Run: `uv run pytest tests/unit/test_store.py -v`
Expected: PASS, 5 passed.

- [x] **Step 6: Write and run the fetcher test**

Create `tests/unit/test_ingest_base.py`:

```python
"""The fetcher carries the contact address and returns non-200 bodies as evidence."""

from __future__ import annotations

import httpx
import pytest

from logging_employment.ingest.base import HttpFetcher


def test_contact_email_is_required() -> None:
    with pytest.raises(ValueError, match="contact_email"):
        HttpFetcher(contact_email="")


def test_user_agent_carries_the_contact_address(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, content=b"ok")

    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers=fetcher._client.headers,
    )
    fetcher.get("https://example.invalid/x")
    assert "who@example.invalid" in seen["ua"]


def test_a_404_body_is_returned_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"<html>gone</html>")

    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(transport=httpx.MockTransport(handler))
    result = fetcher.get("https://example.invalid/missing")
    assert result.http_status == 404
    assert result.content == b"<html>gone</html>"
```

Run: `uv run pytest tests/unit/test_ingest_base.py -v`
Expected: PASS, 3 passed.

- [x] **Step 7: Commit**

```bash
git add src/logging_employment/store.py src/logging_employment/ingest/ \
        tests/unit/test_store.py tests/unit/test_ingest_base.py
git commit -m "feat(store): add the content-addressed raw store and the shared HTTP client"
```

---

### Task 6: `source_registry` and the `registry verify` command

**Files:**
- Create: `src/logging_employment/registry/__init__.py`
- Create: `src/logging_employment/registry/models.py`
- Create: `src/logging_employment/registry/loader.py`
- Create: `src/logging_employment/registry/validation.py`
- Create: `src/logging_employment/registry/sources.yaml`
- Modify: `src/logging_employment/cli.py`
- Create: `tests/unit/test_registry.py`

**Interfaces:**
- Consumes: Task 3's `SOURCE_REGISTRY_SCHEMA`; Task 2's `errors`.
- Produces:
  - `registry.models.SourceRegistryRow` — Pydantic model with §7.1's eighteen fields and
    `access_status: Literal["verified", "documented", "unverified", "retired"]`
  - `registry.loader.load_registry(path: Path) -> list[SourceRegistryRow]`
  - `registry.loader.registry_frame(rows) -> polars.DataFrame` conforming to
    `SOURCE_REGISTRY_SCHEMA`
  - `registry.validation.verify(rows) -> list[str]` — a list of human-readable problems, empty
    when the registry is sound
  - CLI subcommand group `registry`, with `registry verify`

- [x] **Step 1: Write the failing test**

Create `tests/unit/test_registry.py`:

```python
"""The source registry carries §7.1's fields and refuses free-floating disclosure prose."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
from pydantic import ValidationError

from logging_employment.contracts import SOURCE_REGISTRY_SCHEMA
from logging_employment.registry.loader import load_registry, registry_frame
from logging_employment.registry.models import SourceRegistryRow
from logging_employment.registry.validation import verify

SEED = Path(__file__).resolve().parents[2] / "src" / "logging_employment" / "registry" / "sources.yaml"


def _row(**overrides: str) -> SourceRegistryRow:
    base = dict(
        source_id="qcew",
        agency="BLS",
        dataset="QCEW quarterly industry data",
        landing_url="https://www.bls.gov/cew/",
        endpoint_pattern="https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv",
        access_status="verified",
        frequency="quarterly",
        reference_period="calendar quarter, monthly employment fields",
        geography="national, state, MSA, county",
        industry_detail="NAICS 6-digit",
        ownership="all ownership codes; 5 = Private",
        statistical_unit="establishment",
        employment_concept="covered wage-and-salary jobs",
        size_dimension="none in the quarterly file (size_code 0 only)",
        disclosure_regime="qcew_disclosure_code_v1",
        revision_policy="finalized with the following year's Q1 release",
        model_role="hard constraint source",
        limitations="cells with disclosure_code N carry no employment value",
    )
    base.update(overrides)
    return SourceRegistryRow(**base)


def test_all_eighteen_fields_are_required() -> None:
    assert set(SourceRegistryRow.model_fields) == set(SOURCE_REGISTRY_SCHEMA)


def test_access_status_is_an_enum() -> None:
    with pytest.raises(ValidationError):
        _row(access_status="probably_fine")


def test_registry_frame_matches_the_declared_schema() -> None:
    frame = registry_frame([_row()])
    assert frame.schema == pl.Schema(SOURCE_REGISTRY_SCHEMA)


def test_verify_flags_a_versionless_disclosure_regime() -> None:
    problems = verify([_row(disclosure_regime="values are protected somehow")])
    assert any("disclosure_regime" in p for p in problems)


def test_verify_flags_a_duplicate_source_id() -> None:
    problems = verify([_row(), _row()])
    assert any("duplicate" in p for p in problems)


def test_the_seed_registry_is_sound() -> None:
    rows = load_registry(SEED)
    assert {r.source_id for r in rows} == {"qcew", "qcew_size", "cbp"}
    assert verify(rows) == []
```

- [x] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.registry'`.

- [x] **Step 3: Write `registry/models.py`**

```python
"""The §7.1 `source_registry` row."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SourceRegistryRow(BaseModel):
    """One logical source product, described in the eighteen fields §7.1 requires."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    agency: str
    dataset: str
    landing_url: str | None
    endpoint_pattern: str | None
    access_status: Literal["verified", "documented", "unverified", "retired"]
    frequency: str
    reference_period: str
    geography: str
    industry_detail: str
    ownership: str
    statistical_unit: str
    employment_concept: str
    size_dimension: str | None
    disclosure_regime: str
    revision_policy: str
    model_role: str
    limitations: str
```

- [x] **Step 4: Write `registry/loader.py`**

```python
"""Loading the registry from YAML and rendering it as a typed frame."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl
import yaml

from ..contracts import SOURCE_REGISTRY_SCHEMA
from .models import SourceRegistryRow


def load_registry(path: Path) -> list[SourceRegistryRow]:
    """Parse every row in the registry file, validating each against §7.1."""
    payload = yaml.safe_load(path.read_text())
    return [SourceRegistryRow.model_validate(entry) for entry in payload["sources"]]


def registry_frame(rows: Sequence[SourceRegistryRow]) -> pl.DataFrame:
    """Render registry rows as a frame in the declared column order and dtypes."""
    return pl.DataFrame(
        [row.model_dump() for row in rows], schema=SOURCE_REGISTRY_SCHEMA, orient="row"
    )
```

- [x] **Step 5: Write `registry/validation.py`**

```python
"""Registry checks behind `registry verify`."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from .models import SourceRegistryRow

# §7.1 requires `disclosure_regime` to be "versioned, not free-floating prose only". A version
# suffix is the machine-checkable half of that: a later stage keys its regime registry on this
# string, and prose cannot be keyed on.
_VERSIONED = re.compile(r"_v\d+$")


def verify(rows: Sequence[SourceRegistryRow]) -> list[str]:
    """Return one message per problem found. An empty list means the registry is sound."""
    problems: list[str] = []
    counts = Counter(row.source_id for row in rows)
    problems.extend(
        f"duplicate source_id {source_id!r} appears {n} times"
        for source_id, n in sorted(counts.items())
        if n > 1
    )
    for row in rows:
        if not _VERSIONED.search(row.disclosure_regime):
            problems.append(
                f"{row.source_id}: disclosure_regime {row.disclosure_regime!r} carries no version "
                "suffix (expected a trailing _v<N>)"
            )
        if row.access_status in {"verified", "documented"} and not row.endpoint_pattern:
            problems.append(
                f"{row.source_id}: access_status is {row.access_status!r} but no endpoint_pattern "
                "is recorded"
            )
    return problems
```

- [x] **Step 6: Write `registry/sources.yaml`**

Three rows — `qcew`, `qcew_size`, `cbp`. Fill every one of the eighteen fields from Stage 0's
measured findings, using the endpoint patterns in this plan's Stage 0 inputs table. Set
`access_status: verified` for all three (Stage 0 measured `verified` for each). Give each a
versioned `disclosure_regime` string: `qcew_disclosure_code_v1`, `qcew_size_disclosure_code_v1`,
`cbp_noise_infusion_v1`. For `qcew_size.size_dimension`, record what Stage 0 measured — national
geography × 113310 × size codes 1–7, first quarter only — not a general claim about the file.

- [x] **Step 7: Add the `registry` command group to `cli.py`**

```python
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
```

- [x] **Step 8: Run the tests and the command**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: PASS, 6 passed.

Run: `uv run logging-estimates registry verify --config config.yaml`
Expected: `OK: registry verified`, exit code 0.

- [x] **Step 9: Commit**

```bash
git add src/logging_employment/registry/ src/logging_employment/cli.py tests/unit/test_registry.py
git commit -m "feat(registry): add the source registry and registry verify"
```

---

### Task 7: QCEW slice route and the re-measured year boundary

**Files:**
- Create: `src/logging_employment/ingest/qcew.py`
- Create: `tests/fixtures/qcew/slice_2017q1.csv`
- Create: `tests/unit/test_qcew_routes.py`

**Interfaces:**
- Consumes: Task 5's `HttpFetcher`, `RawStore`, `snapshot_row`; Task 2's `constants`.
- Produces:
  - `ingest.qcew.SLICE_URL: str` and `ingest.qcew.BULK_URL: str` (format templates)
  - `ingest.qcew.slice_url(year: int, qtr: int, industry: str) -> str`
  - `ingest.qcew.probe_slice_boundary(fetcher, industry, candidate_years) -> int` — the earliest
    year the slice route serves, **measured this run**
  - `ingest.qcew.read_slice_csv(raw: bytes) -> polars.DataFrame` — every column read as `String`
  - Task 8 adds `bulk_*` and route selection to this same module

**Fixtures.** `data/raw/` is gitignored, so Stage 0's extracts cannot be test inputs where they
sit. Copy the bytes into the tracked fixture tree, verbatim:

```bash
mkdir -p tests/fixtures/qcew
cp data/raw/audit/qcew_routes/slices/2017q1.csv tests/fixtures/qcew/slice_2017q1.csv
```

- [x] **Step 1: Copy the fixture and record its hash**

Run the two commands above, then:

Run: `shasum -a 256 tests/fixtures/qcew/slice_2017q1.csv`
Expected: a 64-hex digest. Compare it against the row for that path in
`specs/findings/source-audit-extracts.csv` and record both in your implementer report. If they
differ, stop — the copy is not the audited object.

- [x] **Step 2: Write the failing test**

Create `tests/unit/test_qcew_routes.py`:

```python
"""Slice-route URL construction, the boundary probe, and CSV reading."""

from __future__ import annotations

from pathlib import Path

import httpx
import polars as pl

from logging_employment import constants
from logging_employment.ingest import qcew
from logging_employment.ingest.base import HttpFetcher

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


def _fetcher(handler) -> HttpFetcher:
    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(transport=httpx.MockTransport(handler))
    return fetcher


def test_slice_url_interpolates_year_quarter_and_industry() -> None:
    assert qcew.slice_url(2017, 1, "113310") == (
        "https://data.bls.gov/cew/data/api/2017/1/industry/113310.csv"
    )


def test_boundary_probe_returns_the_earliest_year_that_answers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        year = int(str(request.url).split("/api/")[1].split("/")[0])
        if year < 2015:
            return httpx.Response(404, content=b"")
        return httpx.Response(200, content=FIXTURE.read_bytes())

    assert qcew.probe_slice_boundary(_fetcher(handler), "113310", range(2010, 2020)) == 2015


def test_boundary_probe_does_not_hard_code_a_year() -> None:
    # D5 and Stage 0's auditor note both forbid it: earliest_year_served = 2014 was "a status
    # measured in one run, not a property of the route".
    source = Path(qcew.__file__).read_text()
    assert "2014" not in source


def test_every_slice_column_is_read_as_a_string() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    assert set(frame.schema.values()) == {pl.String}
    assert frame["area_fips"].str.len_chars().min() == 5  # leading zeros survive


def test_the_fixture_carries_the_columns_the_parser_needs() -> None:
    frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    for column in (
        "area_fips", "own_code", "industry_code", "agglvl_code", "size_code", "year", "qtr",
        "disclosure_code", "qtrly_estabs", "month1_emplvl", "month2_emplvl", "month3_emplvl",
        "total_qtrly_wages",
    ):
        assert column in frame.columns
```

- [x] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/unit/test_qcew_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.ingest.qcew'`.

- [x] **Step 4: Write the slice half of `ingest/qcew.py`**

```python
"""QCEW quarterly acquisition over both published routes, and the monthly parser.

D5 makes acquisition dual-route: the Open Data CSV slice endpoint and the downloadable bulk
files, behind one interface, selected by reference year. The boundary between them is measured
each run rather than stored: Stage 0 observed the slice route serving from reference year 2014,
and recorded that as a status measured in one run rather than a property of the route.
"""

from __future__ import annotations

import io
from collections.abc import Iterable

import polars as pl

from .base import FetchedBytes, HttpFetcher

SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
BULK_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip"


def slice_url(year: int, qtr: int, industry: str) -> str:
    """The Open Data slice URL for one industry-quarter."""
    return SLICE_URL.format(year=year, qtr=qtr, industry=industry)


def read_slice_csv(raw: bytes) -> pl.DataFrame:
    """Read a slice CSV with every column typed as String.

    Nothing is coerced at read time. `area_fips` is a zero-padded code, not a number, and a
    suppressed row publishes a literal `0` that must not become an integer before the disclosure
    code has been read (SRC-QCEW-002: parse disclosure metadata before deriving numeric values).
    """
    return pl.read_csv(io.BytesIO(raw), infer_schema_length=0, schema_overrides=None)


def probe_slice_boundary(
    fetcher: HttpFetcher, industry: str, candidate_years: Iterable[int]
) -> int:
    """The earliest candidate year whose Q1 slice returns a non-empty 200.

    Measured, never stored: the value this returns is written to the run manifest so a later
    reader can see which boundary that run used.
    """
    served: list[int] = []
    for year in sorted(candidate_years):
        response = fetcher.get(slice_url(year, 1, industry))
        if response.http_status == 200 and response.content.strip():
            served.append(year)
    if not served:
        raise ValueError(f"the slice route served no candidate year for industry {industry}")
    return served[0]


def fetch_slice(fetcher: HttpFetcher, year: int, qtr: int, industry: str) -> FetchedBytes:
    """Fetch one industry-quarter over the slice route."""
    return fetcher.get(slice_url(year, qtr, industry))
```

- [x] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/unit/test_qcew_routes.py -v`
Expected: PASS, 5 passed.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/ingest/qcew.py tests/fixtures/qcew/slice_2017q1.csv \
        tests/unit/test_qcew_routes.py
git commit -m "feat(qcew): add the slice route and a measured year boundary"
```

---

### Task 8: QCEW bulk route, column reconciliation, and route selection

**Files:**
- Modify: `src/logging_employment/ingest/qcew.py`
- Create: `tests/fixtures/qcew/bulk_2017.zip`
- Modify: `tests/unit/test_qcew_routes.py`

**Interfaces:**
- Consumes: Task 7's module.
- Produces:
  - `ingest.qcew.BULK_TO_SLICE_COLUMNS: dict[str, str]`
  - `ingest.qcew.BULK_ONLY_TITLE_COLUMNS: tuple[str, ...]`
  - `ingest.qcew.read_bulk_zip(raw: bytes, industry: str) -> polars.DataFrame` — already
    reconciled to slice column names
  - `ingest.qcew.route_for_year(year: int, earliest_slice_year: int) -> Literal["slice", "bulk"]`

**Why the bulk branch needs forcing in tests.** Stage 0 measured `bulk_years_required = []` — with
today's boundary at 2014, no window year routes to bulk, so the branch is unreachable in
production. An unexercised branch is exactly the defect Stage 0's own deferred list records
against `scripts/audit/qcew_routes.py`. The test below forces it with a synthetic boundary.

- [x] **Step 1: Copy the bulk fixture** — **NOT DONE AS WRITTEN. See the deviation below.**

```bash
cp data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip tests/fixtures/qcew/bulk_2017.zip
```

Run: `shasum -a 256 tests/fixtures/qcew/bulk_2017.zip` and compare against
`specs/findings/source-audit-extracts.csv` as in Task 7 Step 1.

> **DEVIATION (2026-09-05, approved by the partner).** The command above was not run and the
> hash check above does not apply. The audited archive is **439 MB across 2,232 members** — past
> GitHub's 100 MB per-file push limit, and not something a later commit could un-bloat out of
> git history. `tests/fixtures/qcew/bulk_2017.zip` is instead that archive **reduced to four of
> its members** and re-zipped: SHA-256
> `b7379140427b19ce33dfaeb04b17806069d1e07dff5ee462f2d12e0a9e475db2`, 571,366 bytes. It is
> **derived, not audited** — it appears in no row of `source-audit-extracts.csv`. Each member's
> bytes are byte-identical to the audited archive's, and a test pins the target member's digest.
>
> Three of the four members are near-miss decoys, not padding: with a single-member fixture,
> `read_bulk_zip`'s member filter narrows one name to one name, and deleting the filter outright
> left every test in this task green (verified by mutation). **Do not reduce this fixture to one
> member.** `tests/fixtures/qcew/README.md` records the provenance, the digests, the reasoning,
> and a deterministic regeneration command.

- [x] **Step 2: Write the failing tests**

Append to `tests/unit/test_qcew_routes.py`:

```python
BULK = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "bulk_2017.zip"


def test_route_selection_uses_the_measured_boundary() -> None:
    assert qcew.route_for_year(2017, earliest_slice_year=2014) == "slice"
    # Forced: today's measured boundary makes this unreachable in production, so the bulk branch
    # would otherwise never execute.
    assert qcew.route_for_year(2017, earliest_slice_year=2020) == "bulk"


def test_bulk_columns_are_renamed_to_the_slice_vocabulary() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    assert "qtrly_estabs" in frame.columns
    assert "qtrly_estabs_count" not in frame.columns
    for bulk_name in qcew.BULK_TO_SLICE_COLUMNS:
        assert bulk_name not in frame.columns


def test_both_routes_agree_on_the_columns_the_parser_reads() -> None:
    slice_frame = qcew.read_slice_csv(FIXTURE.read_bytes())
    bulk_frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    needed = {
        "area_fips", "own_code", "industry_code", "agglvl_code", "size_code", "year", "qtr",
        "disclosure_code", "qtrly_estabs", "month1_emplvl", "month2_emplvl", "month3_emplvl",
        "total_qtrly_wages",
    }
    assert needed <= set(slice_frame.columns)
    assert needed <= set(bulk_frame.columns)


def test_bulk_only_title_columns_are_dropped() -> None:
    frame = qcew.read_bulk_zip(BULK.read_bytes(), constants.INDUSTRY_CODE)
    for title_column in qcew.BULK_ONLY_TITLE_COLUMNS:
        assert title_column not in frame.columns
```

- [x] **Step 3: Run to verify they fail**

Run: `uv run pytest tests/unit/test_qcew_routes.py -v`
Expected: FAIL — `AttributeError: module 'logging_employment.ingest.qcew' has no attribute 'route_for_year'`.

- [x] **Step 4: Add the bulk half to `ingest/qcew.py`**

```python
import zipfile
from typing import Literal

# Stage 0 measured `column_parity.identical = false` between the two routes. These four names are
# the disagreements that matter -- the bulk file spells the establishment-count family with a
# `_count` infix. Mapping is one-directional: bulk is renamed into the slice vocabulary, because
# the slice route serves the whole window today and its names are what the parser reads.
BULK_TO_SLICE_COLUMNS: dict[str, str] = {
    "qtrly_estabs_count": "qtrly_estabs",
    "lq_qtrly_estabs_count": "lq_qtrly_estabs",
    "oty_qtrly_estabs_count_chg": "oty_qtrly_estabs_chg",
    "oty_qtrly_estabs_count_pct_chg": "oty_qtrly_estabs_pct_chg",
}

# Five title columns the bulk file carries and the slice file does not. Dropped rather than kept:
# they are labels for codes this package resolves through its own harmonized dimensions (Task 13),
# and keeping them would give two routes two different column sets for the same table.
BULK_ONLY_TITLE_COLUMNS: tuple[str, ...] = (
    "agglvl_title",
    "area_title",
    "industry_title",
    "own_title",
    "size_title",
)


def bulk_url(year: int) -> str:
    """The downloadable bulk-file URL for one reference year."""
    return BULK_URL.format(year=year)


def route_for_year(year: int, earliest_slice_year: int) -> Literal["slice", "bulk"]:
    """Which route serves this reference year, given the boundary measured this run."""
    return "slice" if year >= earliest_slice_year else "bulk"


def read_bulk_zip(raw: bytes, industry: str) -> pl.DataFrame:
    """Read the one industry member out of a bulk zip, in the slice column vocabulary.

    The member name embeds the industry code and its title, e.g.
    `2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv`, so the member is selected
    by an industry-code substring rather than by a reconstructed filename.
    """
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.namelist() if industry in n and n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one member for industry {industry}, found {members}")
        with archive.open(members[0]) as handle:
            frame = pl.read_csv(handle.read(), infer_schema_length=0)
    frame = frame.rename({k: v for k, v in BULK_TO_SLICE_COLUMNS.items() if k in frame.columns})
    return frame.drop([c for c in BULK_ONLY_TITLE_COLUMNS if c in frame.columns])
```

- [x] **Step 5: Run to verify they pass**

Run: `uv run pytest tests/unit/test_qcew_routes.py -v`
Expected: PASS, 9 passed.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/ingest/qcew.py tests/fixtures/qcew/bulk_2017.zip \
        tests/unit/test_qcew_routes.py
git commit -m "feat(qcew): add the bulk route, column reconciliation, and route selection"
```

---

### Task 9: The `qcew_monthly` parser

**Files:**
- Modify: `src/logging_employment/ingest/qcew.py`
- Create: `tests/unit/test_qcew_parser.py`

**Interfaces:**
- Consumes: Task 8's readers; Task 3's `QCEW_MONTHLY_SCHEMA` and `OBSERVATION_STATUSES`;
  Task 2's `constants.QCEW_DISCLOSURE_CODES` and `errors.UnknownDisclosureCodeError`.
- Produces:
  - `ingest.qcew.PARSER_VERSION: str`
  - `ingest.qcew.is_true_zero_expr() -> polars.Expr`
  - `ingest.qcew.parse_qcew_monthly(frame, *, snapshot_id, release_vintage, release_status, naics_vintage) -> polars.DataFrame`
    conforming to `QCEW_MONTHLY_SCHEMA`

**The true-zero rule — read this before writing the test.** §17.1 requires two behaviours that
look symmetrical and are not: a suppression-coded zero parses to null, and a true published zero
is preserved *when its metadata supports that interpretation*. BLS ships **no titles file for
`disclosure_code`** (Stage 0: `titles_available.disclosure_code = null`), so no fetched artifact
defines what `'-'` means, and a rule keyed on that character alone would be prose, not derivation.

What Stage 0 actually measured, on state-level private 113310 rows:

| `disclosure_code` | rows | `qtrly_estabs` | employment fields |
|---|---|---|---|
| `''` | 1154 | positive | published, non-zero |
| `'N'` | 417 | **positive** (22, 39, 2 …) | literal `0`, meaning withheld |
| `'-'` | 9 | **`0`** | literal `0` |

The establishment count is the metadata that supports the interpretation: a cell with zero
establishments has zero employment because there is nothing to employ anyone. So the contract is
**`is_true_zero = (qtrly_estabs == 0) and every value field == 0`**, with `disclosure_code`
recorded but not load-bearing — and a hard failure if a `'-'` row ever arrives carrying
`qtrly_estabs > 0`, because that would break the premise the rule rests on.

- [x] **Step 1: Write the failing tests**

Create `tests/unit/test_qcew_parser.py`:

```python
"""The §17.1 parser contracts: suppression to null, true zeros preserved, months expanded."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment.contracts import QCEW_MONTHLY_SCHEMA, validate_frame
from logging_employment.errors import UnknownDisclosureCodeError
from logging_employment.ingest import qcew

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


def _parsed() -> pl.DataFrame:
    return qcew.parse_qcew_monthly(
        qcew.read_slice_csv(FIXTURE.read_bytes()),
        snapshot_id="snap",
        release_vintage="2017Q1",
        release_status="final",
        naics_vintage="NAICS 2017",
    )


def _row(**overrides: str) -> pl.DataFrame:
    base = {
        "area_fips": "01000", "own_code": "5", "industry_code": "113310", "agglvl_code": "58",
        "size_code": "0", "year": "2017", "qtr": "1", "disclosure_code": "",
        "qtrly_estabs": "10", "month1_emplvl": "100", "month2_emplvl": "110",
        "month3_emplvl": "120", "total_qtrly_wages": "999",
    }
    base.update(overrides)
    return pl.DataFrame({k: [v] for k, v in base.items()})


def test_output_matches_the_declared_schema() -> None:
    validate_frame(_parsed(), QCEW_MONTHLY_SCHEMA, "qcew_monthly")


def test_a_suppression_coded_zero_parses_to_null() -> None:
    out = qcew.parse_qcew_monthly(
        _row(disclosure_code="N", qtrly_estabs="22", month1_emplvl="0", month2_emplvl="0",
             month3_emplvl="0", total_qtrly_wages="0"),
        snapshot_id="s", release_vintage="v", release_status="final", naics_vintage="NAICS 2017",
    )
    assert out["employment_value"].to_list() == [None, None, None]
    assert out["employment_raw"].to_list() == ["0", "0", "0"]
    assert out["observation_status"].unique().to_list() == ["suppressed"]
    # The establishment count survives suppression -- Stage 0 measured this on all 1227 cells.
    assert out["qtrly_establishments"].unique().to_list() == [22]
    assert out["is_true_zero"].unique().to_list() == [False]


def test_a_true_zero_is_preserved_because_the_establishment_count_supports_it() -> None:
    out = qcew.parse_qcew_monthly(
        _row(disclosure_code="-", qtrly_estabs="0", month1_emplvl="0", month2_emplvl="0",
             month3_emplvl="0", total_qtrly_wages="0"),
        snapshot_id="s", release_vintage="v", release_status="final", naics_vintage="NAICS 2017",
    )
    assert out["employment_value"].to_list() == [0, 0, 0]
    assert out["is_true_zero"].unique().to_list() == [True]
    assert out["observation_status"].unique().to_list() == ["true_zero"]


def test_a_dash_row_with_establishments_halts_rather_than_claiming_a_true_zero() -> None:
    with pytest.raises(ValueError, match="qtrly_estabs"):
        qcew.parse_qcew_monthly(
            _row(disclosure_code="-", qtrly_estabs="7", month1_emplvl="0", month2_emplvl="0",
                 month3_emplvl="0", total_qtrly_wages="0"),
            snapshot_id="s", release_vintage="v", release_status="final",
            naics_vintage="NAICS 2017",
        )


def test_an_unknown_disclosure_code_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureCodeError, match="Z"):
        qcew.parse_qcew_monthly(
            _row(disclosure_code="Z"),
            snapshot_id="s", release_vintage="v", release_status="final",
            naics_vintage="NAICS 2017",
        )


def test_three_monthly_columns_expand_to_three_rows() -> None:
    out = qcew.parse_qcew_monthly(
        _row(), snapshot_id="s", release_vintage="v", release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out.height == 3
    assert out["reference_month"].to_list() == ["2017-01", "2017-02", "2017-03"]
    assert out["employment_value"].to_list() == [100, 110, 120]
    assert out["reference_quarter"].unique().to_list() == ["2017Q1"]


def test_quarter_three_maps_to_july_august_september() -> None:
    out = qcew.parse_qcew_monthly(
        _row(qtr="3"), snapshot_id="s", release_vintage="v", release_status="final",
        naics_vintage="NAICS 2017",
    )
    assert out["reference_month"].to_list() == ["2017-07", "2017-08", "2017-09"]


def test_area_fips_round_trips_with_leading_zeros_intact() -> None:
    out = _parsed()
    assert out.filter(pl.col("area_fips") == "01000").height > 0
    assert out["area_fips"].str.len_chars().min() == 5


def test_state_fips_is_the_first_two_characters_for_state_rows() -> None:
    out = _parsed().filter(pl.col("aggregation_level") == "58")
    assert (out["state_fips"] == out["area_fips"].str.slice(0, 2)).all()


def test_source_naics_vintage_survives_ingestion() -> None:
    assert _parsed()["naics_vintage"].unique().to_list() == ["NAICS 2017"]


def test_every_observation_status_is_in_the_declared_vocabulary() -> None:
    from logging_employment.contracts import OBSERVATION_STATUSES

    assert set(_parsed()["observation_status"].unique()) <= set(OBSERVATION_STATUSES)
```

- [x] **Step 2: Run to verify they fail**

Run: `uv run pytest tests/unit/test_qcew_parser.py -v`
Expected: FAIL — `AttributeError: module 'logging_employment.ingest.qcew' has no attribute 'parse_qcew_monthly'`.

- [x] **Step 3: Write the parser**

Append to `ingest/qcew.py`:

```python
import hashlib

from ..constants import QCEW_DISCLOSURE_CODES
from ..contracts import QCEW_MONTHLY_SCHEMA
from ..errors import UnknownDisclosureCodeError

PARSER_VERSION = "qcew_monthly/1"

_VALUE_COLUMNS = ("month1_emplvl", "month2_emplvl", "month3_emplvl", "total_qtrly_wages")


def is_true_zero_expr() -> pl.Expr:
    """True where a published zero is a real zero rather than a withheld value.

    The predicate is the establishment count, not the disclosure character. BLS publishes no
    titles file for `disclosure_code`, so nothing fetched defines what any code means; what Stage 0
    measured is that rows carrying zero establishments carry zero everything, while suppressed
    rows keep a positive establishment count. A cell with no establishments has no employment,
    which is the source-specific rule INV-003 requires before a zero may be read as substantive.
    """
    zero_value_columns = pl.all_horizontal(
        [pl.col(c).cast(pl.Int64, strict=False).fill_null(-1) == 0 for c in _VALUE_COLUMNS]
    )
    return (pl.col("qtrly_estabs").cast(pl.Int64, strict=False) == 0) & zero_value_columns


def _check_disclosure_codes(frame: pl.DataFrame) -> None:
    """Halt on any disclosure code outside the measured allowlist (§18.3)."""
    seen = set(frame["disclosure_code"].fill_null("").unique().to_list())
    unknown = sorted(seen - QCEW_DISCLOSURE_CODES)
    if unknown:
        raise UnknownDisclosureCodeError(
            f"disclosure codes {unknown} are outside the measured allowlist "
            f"{sorted(QCEW_DISCLOSURE_CODES)}"
        )


def _check_dash_rows_carry_no_establishments(frame: pl.DataFrame) -> None:
    """Halt if a '-' row carries establishments, which would break the true-zero premise."""
    offending = frame.filter(
        (pl.col("disclosure_code") == "-")
        & (pl.col("qtrly_estabs").cast(pl.Int64, strict=False) > 0)
    )
    if offending.height:
        raise ValueError(
            f"{offending.height} row(s) carry disclosure_code '-' with qtrly_estabs > 0; the "
            "true-zero rule rests on those two never co-occurring, so this run halts rather than "
            "guessing which reading is right"
        )


def parse_qcew_monthly(
    frame: pl.DataFrame,
    *,
    snapshot_id: str,
    release_vintage: str,
    release_status: str,
    naics_vintage: str,
) -> pl.DataFrame:
    """Turn quarterly QCEW rows into normalized monthly rows (§7.3, SRC-QCEW-002/003/004).

    Disclosure metadata is read first and numeric values are derived second, so a suppressed row's
    literal zero never becomes an integer employment level.
    """
    _check_disclosure_codes(frame)
    _check_dash_rows_carry_no_establishments(frame)

    suppressed = pl.col("disclosure_code") == "N"
    true_zero = is_true_zero_expr()

    prepared = frame.with_columns(
        pl.concat_str([pl.col("year"), pl.lit("Q"), pl.col("qtr")]).alias("reference_quarter"),
        pl.col("qtrly_estabs").cast(pl.Int64, strict=False).alias("qtrly_establishments"),
        pl.col("total_qtrly_wages").alias("wages_raw"),
        pl.when(suppressed)
        .then(None)
        .otherwise(pl.col("total_qtrly_wages").cast(pl.Int64, strict=False))
        .alias("wages_value"),
        true_zero.alias("is_true_zero"),
        pl.when(suppressed)
        .then(pl.lit("suppressed"))
        .when(true_zero)
        .then(pl.lit("true_zero"))
        .otherwise(pl.lit("observed"))
        .alias("observation_status"),
    )

    monthly = prepared.unpivot(
        index=[c for c in prepared.columns if c not in _VALUE_COLUMNS[:3]],
        on=list(_VALUE_COLUMNS[:3]),
        variable_name="month_column",
        value_name="employment_raw",
    ).with_columns(
        pl.col("month_column").str.extract(r"^month(\d)_emplvl$", 1).cast(pl.Int64).alias("mi")
    )

    return (
        monthly.with_columns(
            pl.format(
                "{}-{}",
                pl.col("year"),
                ((pl.col("qtr").cast(pl.Int64) - 1) * 3 + pl.col("mi"))
                .cast(pl.String)
                .str.pad_start(2, "0"),
            ).alias("reference_month"),
            pl.when(suppressed)
            .then(None)
            .otherwise(pl.col("employment_raw").cast(pl.Int64, strict=False))
            .alias("employment_value"),
            (pl.col("employment_raw") == "0").alias("is_published_numeric_zero"),
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(release_vintage).alias("release_vintage"),
            pl.lit(release_status).alias("release_status"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.when(pl.col("agglvl_code") == "18")
            .then(pl.lit("national"))
            .when(pl.col("agglvl_code") == "58")
            .then(pl.lit("state"))
            .otherwise(pl.lit("other"))
            .alias("area_type"),
            pl.when(pl.col("area_fips") == "US000")
            .then(None)
            .otherwise(pl.col("area_fips").str.slice(0, 2))
            .alias("state_fips"),
            pl.col("own_code").alias("ownership_code"),
            pl.col("agglvl_code").alias("aggregation_level"),
            pl.concat_str(
                [pl.col("area_fips"), pl.col("year"), pl.col("qtr"), pl.col("month_column")],
                separator="|",
            )
            .map_elements(
                lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest(), return_dtype=pl.String
            )
            .alias("source_row_hash"),
        )
        .sort(["area_fips", "reference_month"])
        .select(list(QCEW_MONTHLY_SCHEMA))
        .cast(QCEW_MONTHLY_SCHEMA)  # type: ignore[arg-type]
    )
```

- [x] **Step 4: Run to verify they pass**

Run: `uv run pytest tests/unit/test_qcew_parser.py -v`
Expected: PASS, 11 passed. If `unpivot`'s index list or the `cast` mapping needs adjusting for your
Polars version, fix the implementation — **do not relax an assertion** to make a test pass.

> **DEVIATION (2026-09-05): Step 3's `source_row_hash` does not identify a row.** As written it
> hashes `area_fips|year|qtr|month_column`, omitting `own_code`, `agglvl_code`, `size_code` and
> `industry_code`. Measured on `slice_2017q1.csv`: **18 collisions across 5,430 rows**, including
> area `26165` in `2017-03`, where a suppressed Local Government cell (`own_code` 3) and a Private
> cell reporting 93 (`own_code` 5) received the same hash — conflating two universes under one
> identity, which is what `INV-007` forbids. The shipped key is
> `_ROW_IDENTITY_COLUMNS` = QCEW's natural key plus `month_column`. §7.3 names the column but
> never defines its inputs, so this was the plan's choice to make and it was wrong.
>
> The 11 tests here all pass under the *broken* key — none of them asserts uniqueness. Two added
> tests do (`test_source_row_hash_identifies_a_row_uniquely`,
> `test_source_row_hash_separates_ownership_sectors_in_the_same_area_and_month`), so the task ends
> at **13 passed, not 11**. Both fail under the original key and under dropping `own_code` alone.
> **Later tasks joining or deduplicating on `source_row_hash` must use the shipped key**, not
> Step 3's.

- [x] **Step 5: Verify the parser against the whole fixture, not just constructed rows**

Run:

```bash
uv run python -c "
from pathlib import Path
import polars as pl
from logging_employment.ingest import qcew
f = Path('tests/fixtures/qcew/slice_2017q1.csv')
out = qcew.parse_qcew_monthly(qcew.read_slice_csv(f.read_bytes()), snapshot_id='s',
    release_vintage='2017Q1', release_status='final', naics_vintage='NAICS 2017')
print(out.group_by('observation_status').len().sort('observation_status'))
print('rows:', out.height, 'null employment:', out['employment_value'].null_count())
"
```

Expected: three rows per input row; `suppressed` rows have null `employment_value` and the null
count equals 3 × the number of `N` rows in the fixture. Record the observed counts in your
implementer report — they are measurements of this fixture, not values to hard-code.

- [x] **Step 6: Commit**

```bash
git add src/logging_employment/ingest/qcew.py tests/unit/test_qcew_parser.py
git commit -m "feat(qcew): parse quarterly rows into qcew_monthly with a derived true-zero rule"
```

---

### Task 10: QCEW by-size ingestion and the dimensionality assertion

**Files:**
- Create: `src/logging_employment/ingest/qcew_size.py`
- Create: `tests/fixtures/qcew_size/2017_q1_by_size.zip`
- Create: `tests/unit/test_qcew_size.py`

**Interfaces:**
- Consumes: Task 5's fetcher and store; Task 3's `QCEW_NATIONAL_SIZE_SCHEMA`; Task 2's `errors`.
- Produces:
  - `ingest.qcew_size.BY_SIZE_URL: str`
  - `ingest.qcew_size.SIZE_CLASS_BOUNDS: dict[str, tuple[int, int | None]]`
  - `ingest.qcew_size.read_by_size_zip(raw: bytes) -> polars.DataFrame`
  - `ingest.qcew_size.assert_no_state_industry_size(frame, industry) -> None` raising
    `MissingCrossTabulationError`
  - `ingest.qcew_size.parse_qcew_national_size(frame, *, snapshot_id, reference_year, naics_vintage) -> polars.DataFrame`

**What Stage 0 measured, and what it did not.** `simultaneous_state_industry_size = false`, but the
narrower phrasing matters: the by-size file *does* contain non-national areas (agglvl `61`–`64`
have area pattern `mixed`), and 113310 appears at exactly one aggregation level, `28`, whose area
pattern is `national`. So the assertion is not "this file has no state rows" — it is "no
aggregation level carries state, 113310 and size simultaneously". Write the assertion to check
that predicate, and name the function for it. The file is **first quarter only**: all 24 Q2–Q4
probes across the eight window years returned 404.

- [ ] **Step 1: Copy the fixture**

```bash
mkdir -p tests/fixtures/qcew_size
cp data/raw/audit/qcew_size/2017_q1_by_size.zip tests/fixtures/qcew_size/2017_q1_by_size.zip
shasum -a 256 tests/fixtures/qcew_size/2017_q1_by_size.zip
```

Compare the digest against `specs/findings/source-audit-extracts.csv` as in Task 7.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_qcew_size.py`:

```python
"""SRC-QSIZE-001..004: March classification retained, dimensionality verified from contents."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment import constants
from logging_employment.contracts import QCEW_NATIONAL_SIZE_SCHEMA, validate_frame
from logging_employment.errors import MissingCrossTabulationError
from logging_employment.ingest import qcew_size

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew_size" / "2017_q1_by_size.zip"


def _frame() -> pl.DataFrame:
    return qcew_size.read_by_size_zip(FIXTURE.read_bytes())


def test_the_assertion_passes_on_the_real_file() -> None:
    # SRC-QSIZE-002: verified from file contents, not inferred from documentation.
    qcew_size.assert_no_state_industry_size(_frame(), constants.INDUSTRY_CODE)


def test_the_assertion_names_the_level_when_a_state_size_row_appears() -> None:
    doctored = pl.DataFrame(
        {
            "area_fips": ["01000"],
            "agglvl_code": ["68"],
            "industry_code": [constants.INDUSTRY_CODE],
            "size_code": ["3"],
            "qtrly_estabs": ["5"],
            "month1_emplvl": ["50"],
            "year": ["2017"],
            "qtr": ["1"],
            "disclosure_code": [""],
        }
    )
    with pytest.raises(MissingCrossTabulationError, match="68"):
        qcew_size.assert_no_state_industry_size(doctored, constants.INDUSTRY_CODE)


def test_parsed_output_matches_the_declared_schema() -> None:
    out = qcew_size.parse_qcew_national_size(
        _frame(), snapshot_id="s", reference_year=2017, naics_vintage="NAICS 2017"
    )
    validate_frame(out, QCEW_NATIONAL_SIZE_SCHEMA, "qcew_national_size")


def test_size_bounds_come_from_the_published_titles() -> None:
    assert qcew_size.SIZE_CLASS_BOUNDS["1"] == (0, 4)
    assert qcew_size.SIZE_CLASS_BOUNDS["7"] == (250, 499)


def test_the_march_reference_is_recorded_on_every_row() -> None:
    # SRC-QSIZE-001: the parser must retain that size class is determined by March employment.
    out = qcew_size.parse_qcew_national_size(
        _frame(), snapshot_id="s", reference_year=2017, naics_vintage="NAICS 2017"
    )
    assert out["reference_month"].unique().to_list() == ["2017-03"]
    assert out["reference_quarter"].unique().to_list() == ["2017Q1"]
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/unit/test_qcew_size.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.ingest.qcew_size'`.

- [ ] **Step 4: Write `ingest/qcew_size.py`**

```python
"""QCEW establishment-size ingestion: a national six-digit benchmark, first quarter only."""

from __future__ import annotations

import io
import zipfile

import polars as pl

from ..contracts import QCEW_NATIONAL_SIZE_SCHEMA
from ..errors import MissingCrossTabulationError

BY_SIZE_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip"

PARSER_VERSION = "qcew_national_size/1"

# Bounds read off the size titles Stage 0 fetched: 1 "Fewer than 5 employees per establishment"
# through 7 "250 to 499 employees per establishment". Codes 8 and 9 exist in the file at other
# aggregation levels but carry no 113310 rows, so they are absent here rather than guessed at.
SIZE_CLASS_BOUNDS: dict[str, tuple[int, int | None]] = {
    "1": (0, 4),
    "2": (5, 9),
    "3": (10, 19),
    "4": (20, 49),
    "5": (50, 99),
    "6": (100, 249),
    "7": (250, 499),
}


def read_by_size_zip(raw: bytes) -> pl.DataFrame:
    """Read the single CSV member of a `<year>_q1_by_size.zip`, every column as String."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {members}")
        with archive.open(members[0]) as handle:
            return pl.read_csv(handle.read(), infer_schema_length=0)


def assert_no_state_industry_size(frame: pl.DataFrame, industry: str) -> None:
    """Halt if any aggregation level carries state geography, this industry, and size at once.

    Named for the predicate it checks, which is narrower than "this file has no state rows": the
    by-size file does carry non-national areas at some aggregation levels. What §2.2 row 3 rests
    on is that none of those levels also carries the six-digit industry with a size breakout, and
    that is what this checks. Halting is the §18.3 response to a requested cross-tabulation that
    is absent -- and, symmetrically, to one that turns out to be present when the spec assumed it
    was not.
    """
    industry_rows = frame.filter(pl.col("industry_code") == industry)
    offending = industry_rows.filter(
        (~pl.col("area_fips").str.starts_with("US")) & (pl.col("size_code") != "0")
    )
    if offending.height:
        levels = sorted(offending["agglvl_code"].unique().to_list())
        raise MissingCrossTabulationError(
            f"state x {industry} x size rows appear at aggregation level(s) {levels}; §2.2 row 3 "
            "assumed no such table exists, so this run halts rather than proceeding on a premise "
            "the file just contradicted"
        )


def parse_qcew_national_size(
    frame: pl.DataFrame, *, snapshot_id: str, reference_year: int, naics_vintage: str
) -> pl.DataFrame:
    """Build `qcew_national_size` from the by-size file (§7.4).

    Every row is stamped with March of the reference year. That is not a convenience: SRC-QSIZE-001
    requires the March classification definition to survive into the table, and the file itself is
    first-quarter-only, so a row that lost its March stamp could not be recovered from the data.
    """
    industry_rows = frame.filter(
        (pl.col("size_code") != "0") & (pl.col("area_fips").str.starts_with("US"))
    )
    return (
        industry_rows.with_columns(
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(reference_year).cast(pl.Int64).alias("reference_year"),
            pl.lit(f"{reference_year}Q1").alias("reference_quarter"),
            pl.lit(f"{reference_year}-03").alias("reference_month"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.col("size_code").alias("size_class"),
            pl.col("size_code")
            .replace_strict({k: v[0] for k, v in SIZE_CLASS_BOUNDS.items()}, default=None)
            .cast(pl.Int64)
            .alias("size_lower"),
            pl.col("size_code")
            .replace_strict({k: v[1] for k, v in SIZE_CLASS_BOUNDS.items()}, default=None)
            .cast(pl.Int64)
            .alias("size_upper"),
            pl.col("qtrly_estabs").cast(pl.Int64, strict=False).alias("establishments"),
            pl.when(pl.col("disclosure_code") == "N")
            .then(None)
            .otherwise(pl.col("month3_emplvl").cast(pl.Int64, strict=False))
            .alias("employment"),
            pl.when(pl.col("disclosure_code") == "N")
            .then(pl.lit("suppressed"))
            .otherwise(pl.lit("observed"))
            .alias("observation_status"),
        )
        .sort(["industry_code", "size_class"])
        .select(list(QCEW_NATIONAL_SIZE_SCHEMA))
        .cast(QCEW_NATIONAL_SIZE_SCHEMA)  # type: ignore[arg-type]
    )
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/unit/test_qcew_size.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 6: Confirm the March employment column choice against the file**

`parse_qcew_national_size` reads `month3_emplvl` as the March level for a Q1 file. Verify that
against the fixture rather than assuming it:

```bash
uv run python -c "
from pathlib import Path
from logging_employment.ingest import qcew_size
f = qcew_size.read_by_size_zip(Path('tests/fixtures/qcew_size/2017_q1_by_size.zip').read_bytes())
print([c for c in f.columns if 'emplvl' in c])
print(f.filter(f['industry_code']=='113310').select(
    ['agglvl_code','area_fips','size_code','month1_emplvl','month2_emplvl','month3_emplvl']).head(8))
"
```

Expected: the three monthly columns are present and 113310 rows appear at one aggregation level
with a national `area_fips`. Record the observed aggregation level in your implementer report.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/ingest/qcew_size.py tests/fixtures/qcew_size/ \
        tests/unit/test_qcew_size.py
git commit -m "feat(qcew-size): ingest the national size benchmark with a contents-based assertion"
```

---

### Task 11: CBP metadata discovery and the `cbp_state_size` parser

**Files:**
- Create: `src/logging_employment/ingest/cbp.py`
- Create: `tests/fixtures/cbp/data_113310_2023.json`
- Create: `tests/fixtures/cbp/empszes_2017.json`
- Create: `tests/fixtures/cbp/empszes_2023.json`
- Create: `tests/unit/test_cbp.py`

**Interfaces:**
- Consumes: Task 5's fetcher and store; Task 3's `CBP_STATE_SIZE_SCHEMA`; Task 12 supplies the
  regime lookup, so this task imports it lazily (see Step 6).
- Produces:
  - `ingest.cbp.CBP_URL: str`, `ingest.cbp.VARIABLES_URL: str`
  - `ingest.cbp.discover_naics_predicate(variables_json: dict) -> str`
  - `ingest.cbp.discover_empszes(empszes_json: dict, data_rows: list[list[str]]) -> dict[str, str]`
  - `ingest.cbp.build_query(year: int, predicate: str, industry: str) -> dict[str, str]`
  - `ingest.cbp.parse_cbp_state_size(rows, *, snapshot_id, reference_year, predicate, naics_vintage, regime) -> polars.DataFrame`

**Three facts from Stage 0 that shape this task.**

1. **The NAICS predicate is `NAICS2017` for every year 2017–2023** — including the years whose data
   carry the 2022 vintage. A parser deriving the predicate name from the reference year's NAICS
   vintage asks for a variable CBP does not serve. Discover it from fetched metadata; never
   compute it.
2. **The official EMPSZES values crosswalk exists for 2017 only.** `variables/EMPSZES.json` carries
   `values.item` in 2017 (44 codes) and returns 200 with no crosswalk for 2018–2023. That does not
   force a literal fallback: the data response itself selects `EMPSZES_LABEL`, which is
   per-vintage metadata served by CBP for the vintage being read. SRC-CBP-001's requirement — codes
   from metadata, never reused from another Census product — is satisfied by reading the response's
   own label column. Say so in the docstring, because a reviewer will otherwise read it as a
   literal fallback.
3. **`LFO` was never selected as an output column.** Stage 0 sent `LFO=001` as a filter and
   recorded `lfo_by_year = null` for all eight years, deferring a dedicated `LFO,LFO_LABEL` query
   **to this stage**. Step 5 discharges that deferral.

- [ ] **Step 1: Copy the fixtures**

```bash
mkdir -p tests/fixtures/cbp
cp data/raw/audit/cbp_metadata/2023/data_113310.json tests/fixtures/cbp/data_113310_2023.json
cp data/raw/audit/cbp_metadata/2017/empszes.json tests/fixtures/cbp/empszes_2017.json
cp data/raw/audit/cbp_metadata/2023/empszes.json tests/fixtures/cbp/empszes_2023.json
```

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_cbp.py`:

```python
"""SRC-CBP-001..003: predicate and size codes from metadata, flags preserved, fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from logging_employment.contracts import CBP_STATE_SIZE_SCHEMA, validate_frame
from logging_employment.ingest import cbp

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "cbp"
DATA = json.loads((FIX / "data_113310_2023.json").read_text())
EMPSZES_2017 = json.loads((FIX / "empszes_2017.json").read_text())
EMPSZES_2023 = json.loads((FIX / "empszes_2023.json").read_text())


def test_the_predicate_is_read_from_metadata_not_computed_from_the_vintage() -> None:
    variables = {"variables": {"NAICS2017": {"label": "2017 NAICS code"}, "EMP": {}}}
    assert cbp.discover_naics_predicate(variables) == "NAICS2017"


def test_no_naics2022_predicate_is_ever_constructed() -> None:
    # Stage 0 measured NAICS2017 for every year 2017-2023, including the NAICS-2022 vintage years.
    source = Path(cbp.__file__).read_text()
    assert "NAICS2022" not in source


def test_2017_size_codes_come_from_the_official_values_crosswalk() -> None:
    codes = cbp.discover_empszes(EMPSZES_2017, data_rows=DATA)
    assert codes["001"] == "All establishments"
    assert len(codes) >= 44


def test_later_years_take_their_labels_from_the_response_column() -> None:
    codes = cbp.discover_empszes(EMPSZES_2023, data_rows=DATA)
    assert set(codes) == {"001", "210", "220", "230", "241", "242", "251"}
    assert codes["210"] == "Establishments with less than 5 employees"


def test_the_query_selects_lfo_label_as_an_output_column() -> None:
    query = cbp.build_query(2023, "NAICS2017", "113310")
    assert "LFO" in query["get"].split(",")
    assert "LFO_LABEL" in query["get"].split(",")
    assert query["NAICS2017"] == "113310"
    assert query["for"] == "state:*"


def test_parsed_output_matches_the_declared_schema() -> None:
    out = cbp.parse_cbp_state_size(
        DATA, snapshot_id="s", reference_year=2023, predicate="NAICS2017",
        naics_vintage="NAICS 2022", regime="noise_infusion",
    )
    validate_frame(out, CBP_STATE_SIZE_SCHEMA, "cbp_state_size")


def test_flags_noise_and_legal_form_survive_parsing() -> None:
    out = cbp.parse_cbp_state_size(
        DATA, snapshot_id="s", reference_year=2023, predicate="NAICS2017",
        naics_vintage="NAICS 2022", regime="noise_infusion",
    )
    assert set(out.columns) >= {"employment_flag", "employment_noise_range", "legal_form_code"}
    assert out["legal_form_code"].unique().to_list() == ["001"]
    assert out["reference_period"].unique().to_list() == ["week_including_march_12"]
    assert out["disclosure_regime"].unique().to_list() == ["noise_infusion"]


def test_state_fips_keeps_its_leading_zero() -> None:
    out = cbp.parse_cbp_state_size(
        DATA, snapshot_id="s", reference_year=2023, predicate="NAICS2017",
        naics_vintage="NAICS 2022", regime="noise_infusion",
    )
    assert "01" in out["state_fips"].to_list()
    assert out["state_fips"].str.len_chars().unique().to_list() == [2]


def test_size_bounds_are_parsed_from_the_official_labels() -> None:
    assert cbp.size_bounds("Establishments with less than 5 employees") == (0, 4)
    assert cbp.size_bounds("Establishments with 20 to 49 employees") == (20, 49)
    assert cbp.size_bounds("All establishments") == (None, None)
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/unit/test_cbp.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.ingest.cbp'`.

- [ ] **Step 4: Write `ingest/cbp.py`**

```python
"""CBP ingestion: state x six-digit x establishment-size counts as March-centered measurements."""

from __future__ import annotations

import re

import polars as pl

from ..contracts import CBP_STATE_SIZE_SCHEMA

CBP_URL = "https://api.census.gov/data/{year}/cbp"
VARIABLES_URL = "https://api.census.gov/data/{year}/cbp/variables.json"
EMPSZES_URL = "https://api.census.gov/data/{year}/cbp/variables/EMPSZES.json"

PARSER_VERSION = "cbp_state_size/1"

_LESS_THAN = re.compile(r"less than (\d+) employees")
_RANGE = re.compile(r"(\d[\d,]*) to (\d[\d,]*) employees")
_OR_MORE = re.compile(r"(\d[\d,]*) (?:or more|employees or more)")


def discover_naics_predicate(variables_json: dict) -> str:
    """The NAICS predicate name this vintage actually serves.

    Read from fetched metadata, never computed from the reference year's NAICS vintage: Stage 0
    measured `NAICS2017` for every year 2017-2023, including the years whose data carry the 2022
    vintage, so a name derived from the vintage would ask for a variable CBP does not serve.
    """
    names = [n for n in variables_json.get("variables", {}) if n.startswith("NAICS")]
    predicates = [n for n in names if not n.endswith("_LABEL")]
    if len(predicates) != 1:
        raise ValueError(f"expected exactly one NAICS predicate in the metadata, found {names}")
    return predicates[0]


def discover_empszes(empszes_json: dict, data_rows: list[list[str]]) -> dict[str, str]:
    """Map every establishment-size code this vintage publishes to its official label.

    Two metadata routes, both served by CBP for the vintage being read, neither a literal and
    neither borrowed from another Census product (SRC-CBP-001):

    * the variable's own values crosswalk at `variables/EMPSZES.json`, which Stage 0 measured as
      present for reference year 2017 (44 codes) and absent for 2018-2023; and
    * the `EMPSZES_LABEL` column of the data response, which CBP serves alongside `EMPSZES` for
      every year and which is therefore this vintage's own labelling of the codes it published.

    The second is a different metadata route, not a fallback to hard-coded values.
    """
    items = empszes_json.get("values", {}).get("item")
    if items:
        return {str(code): str(label) for code, label in items.items()}
    header, *rows = data_rows
    code_at = header.index("EMPSZES")
    label_at = header.index("EMPSZES_LABEL")
    return {str(row[code_at]): str(row[label_at]) for row in rows}


def build_query(year: int, predicate: str, industry: str) -> dict[str, str]:
    """The state-by-size query for one reference year.

    `LFO` and `LFO_LABEL` are both selected as output columns. Stage 0 sent `LFO=001` only as a
    filter and recorded `lfo_by_year = null` for all eight window years for exactly that reason,
    deferring the dedicated query here.
    """
    return {
        "get": (
            "NAME,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N,EMP_N_F,LFO,LFO_LABEL,"
            f"{predicate},{predicate}_LABEL"
        ),
        "for": "state:*",
        predicate: industry,
        "LFO": "001",
    }


def size_bounds(label: str) -> tuple[int | None, int | None]:
    """Employee-count bounds parsed from an official EMPSZES label.

    Bounds come from the label CBP publishes, not from a table typed here, so a vintage that
    changes a class's wording changes the bounds with it rather than silently disagreeing.
    """
    if (match := _LESS_THAN.search(label)) is not None:
        return (0, int(match.group(1)) - 1)
    if (match := _RANGE.search(label)) is not None:
        return (int(match.group(1).replace(",", "")), int(match.group(2).replace(",", "")))
    if (match := _OR_MORE.search(label)) is not None:
        return (int(match.group(1).replace(",", "")), None)
    return (None, None)


def parse_cbp_state_size(
    data_rows: list[list[str]],
    *,
    snapshot_id: str,
    reference_year: int,
    predicate: str,
    naics_vintage: str,
    regime: str,
) -> pl.DataFrame:
    """Build `cbp_state_size` from a CBP API response (§7.5, SRC-CBP-002/004).

    Every field the API returns about disclosure -- `EMP_F`, `EMP_N`, `EMP_N_F` where served -- is
    preserved rather than collapsed into a boolean, and `reference_period` is stamped
    `week_including_march_12` because a CBP employment value is a March-centered measurement, not
    a QCEW identity.
    """
    header, *rows = data_rows
    frame = pl.DataFrame(
        {name: [row[i] for row in rows] for i, name in enumerate(header)},
        schema={name: pl.String for name in header},
    )
    labels = frame["EMPSZES_LABEL"].to_list()
    lower = [size_bounds(label)[0] for label in labels]
    upper = [size_bounds(label)[1] for label in labels]
    return (
        frame.with_columns(
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(reference_year).cast(pl.Int64).alias("reference_year"),
            pl.col("state").alias("state_fips"),
            pl.col(predicate).alias("industry_code"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.col("LFO").alias("legal_form_code"),
            pl.col("EMPSZES").alias("size_code"),
            pl.col("EMPSZES_LABEL").alias("size_label"),
            pl.Series("size_lower", lower, dtype=pl.Int64),
            pl.Series("size_upper", upper, dtype=pl.Int64),
            pl.col("ESTAB").cast(pl.Int64, strict=False).alias("establishments"),
            pl.col("EMP").cast(pl.Int64, strict=False).alias("employment"),
            pl.col("EMP_F").fill_null("").alias("employment_flag"),
            pl.col("EMP_N").fill_null("").alias("employment_noise_range"),
            pl.when(pl.col("EMP").is_null())
            .then(pl.lit("withheld_or_dropped"))
            .otherwise(pl.lit("published"))
            .alias("disclosure_status"),
            pl.lit(regime).alias("disclosure_regime"),
            pl.lit("week_including_march_12").alias("reference_period"),
        )
        .sort(["state_fips", "size_code"])
        .select(list(CBP_STATE_SIZE_SCHEMA))
        .cast(CBP_STATE_SIZE_SCHEMA)  # type: ignore[arg-type]
    )
```

- [ ] **Step 5: Run to verify it passes**

Run: `uv run pytest tests/unit/test_cbp.py -v`
Expected: PASS, 9 passed.

- [ ] **Step 6: Discharge the LFO deferral against the live API**

The deferred item is only closed when a real response carries `LFO_LABEL`. Run, with the
repo-root `.env` loaded:

```bash
uv run --env-file .env python -c "
import os, httpx
from logging_employment.ingest import cbp
q = cbp.build_query(2023, 'NAICS2017', '113310')
q['key'] = os.environ['CENSUS_API_KEY']
r = httpx.get(cbp.CBP_URL.format(year=2023), params=q, timeout=60)
print(r.status_code); print(r.json()[0]); print(r.json()[1])
"
```

Expected: status 200 and a header row containing both `LFO` and `LFO_LABEL`. **If the request
fails because `EMP_N_F` is not served for that year, drop `EMP_N_F` from `build_query` and record
that in your implementer report** — Stage 0 never selected it, so whether it is available is
unmeasured. Do not remove `LFO_LABEL`. Record the observed LFO label in your report; it closes the
deferred item.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/ingest/cbp.py tests/fixtures/cbp/ tests/unit/test_cbp.py
git commit -m "feat(cbp): discover the predicate and size codes from metadata, and select LFO_LABEL"
```

---

### Task 12: The CBP disclosure-regime registry and its fail-closed gate

**Files:**
- Create: `src/logging_employment/harmonize/__init__.py`
- Create: `src/logging_employment/harmonize/disclosure.py`
- Create: `tests/unit/test_disclosure_regime.py`

**Interfaces:**
- Consumes: Task 2's `errors.UnknownDisclosureRegimeError`; Task 4's
  `Config.sources.cbp.fail_on_unknown_disclosure_regime`.
- Produces:
  - `harmonize.disclosure.CBP_REGIME_BY_YEAR: dict[int, str]`
  - `harmonize.disclosure.regime_for_year(year: int, *, fail_on_unknown: bool = True) -> str`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_disclosure_regime.py`:

```python
"""SRC-CBP-003: the regime is stored by reference year and an unknown one halts the run."""

from __future__ import annotations

import pytest

from logging_employment.errors import UnknownDisclosureRegimeError
from logging_employment.harmonize import disclosure


def test_2017_carries_both_mechanisms() -> None:
    assert disclosure.regime_for_year(2017) == "noise_infusion_plus_suppression"


def test_2018_through_2023_are_noise_infusion() -> None:
    assert {disclosure.regime_for_year(y) for y in range(2018, 2024)} == {"noise_infusion"}


def test_2024_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureRegimeError, match="2024"):
        disclosure.regime_for_year(2024)


def test_a_year_outside_the_registry_halts_the_run() -> None:
    with pytest.raises(UnknownDisclosureRegimeError, match="2031"):
        disclosure.regime_for_year(2031)


def test_the_gate_can_be_opened_only_explicitly() -> None:
    assert disclosure.regime_for_year(2024, fail_on_unknown=False) == "unknown"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_disclosure_regime.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.harmonize'`.

- [ ] **Step 3: Write `harmonize/disclosure.py`**

```python
"""The CBP disclosure regime, keyed by reference year, with a fail-closed lookup."""

from __future__ import annotations

from ..errors import UnknownDisclosureRegimeError

# Stage 0's `cbp_regime.regime_by_year`, which rests on Census's own methodology page: noise
# infusion documented continuously since reference year 2007, EMPFLAG discontinued "beginning in
# reference year 2018", and cells with fewer than three establishments dropped rather than flagged
# beginning 2017. 2024 is absent rather than assumed: no 2024 CBP dataset exists to document, and
# the methodology page carries a banner stating its content is no longer current pending a
# Department of Commerce order prohibiting noise infusion -- so the 2018-2023 regime cannot be
# carried forward to a year that postdates it.
CBP_REGIME_BY_YEAR: dict[int, str] = {
    2017: "noise_infusion_plus_suppression",
    2018: "noise_infusion",
    2019: "noise_infusion",
    2020: "noise_infusion",
    2021: "noise_infusion",
    2022: "noise_infusion",
    2023: "noise_infusion",
}


def regime_for_year(year: int, *, fail_on_unknown: bool = True) -> str:
    """The disclosure regime for a CBP reference year.

    Halts on an unrecorded year (§18.3, SRC-CBP-003). `fail_on_unknown=False` returns the literal
    string `"unknown"` instead -- it exists so a caller can *record* the gap in a report, never so
    a pipeline can proceed past it, and the config key that reaches it defaults to failing.
    """
    if year in CBP_REGIME_BY_YEAR:
        return CBP_REGIME_BY_YEAR[year]
    if fail_on_unknown:
        raise UnknownDisclosureRegimeError(
            f"CBP reference year {year} carries no established disclosure regime; refusing to "
            "parse its cells (SRC-CBP-003)"
        )
    return "unknown"
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/unit/test_disclosure_regime.py -v`
Expected: PASS, 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/logging_employment/harmonize/ tests/unit/test_disclosure_regime.py
git commit -m "feat(disclosure): key the CBP regime by reference year and fail closed on 2024"
```

---

### Task 13: Harmonized dimensions, the bridge table, concept guards, and the NAICS crosswalk test

**Files:**
- Create: `src/logging_employment/harmonize/dimensions.py`
- Create: `src/logging_employment/harmonize/bridge.py`
- Create: `src/logging_employment/harmonize/naics.py`
- Create: `src/logging_employment/harmonize/concepts.py`
- Create: `src/logging_employment/harmonize/naics_113310.csv`
- Create: `tests/unit/test_harmonize.py`

**Interfaces:**
- Consumes: Task 3's `BRIDGE_SCHEMA`; Task 2's `constants` and `errors.ConceptViolationError`.
- Produces:
  - `harmonize.dimensions.DIMENSIONS: dict[str, tuple[str, ...]]` — the nine versioned dimensions
    §8.6 requires
  - `harmonize.dimensions.dimension_frame(name: str) -> polars.DataFrame`
  - `harmonize.bridge.bridge_frame(rows: Sequence[dict]) -> polars.DataFrame` conforming to
    `BRIDGE_SCHEMA`
  - `harmonize.naics.vintage_for_year(year: int) -> str`
  - `harmonize.naics.crosswalk_113310() -> polars.DataFrame`
  - `harmonize.naics.assert_113310_survives_the_window() -> None`
  - `harmonize.concepts.reject_enterprise_size(size_dimension: str, source_id: str) -> None`
  - `harmonize.concepts.reject_nonemployer_in_core_total(source_id: str) -> None`

**Vendoring the crosswalk.** The NAICS structure and concordance CSVs live in a personal skill
directory outside this repository, so a test reading them there would not run in a clean clone.
Vendor only the 113310 rows into `src/logging_employment/harmonize/naics_113310.csv`, with a
provenance header naming the files they came from and the date.

**Carry Stage 0's two caveats forward verbatim in the docstring.** `link_type = 1:1` is *derived by
the skill from code multiplicities*, not a Census column — Census ships four columns and publishes
no allocation weights. And 1:1 establishes only that the six-digit code neither split nor merged;
it is the unchanged title and the empty `change_indicator` that carry the continuity claim, and
even those are titles and markers rather than a comparison of definitional text.

- [ ] **Step 1: Vendor the crosswalk rows**

```bash
python3 - <<'PY'
from pathlib import Path
src = Path.home() / ".claude" / "skills" / "classification-codes" / "data"
out = Path("src/logging_employment/harmonize/naics_113310.csv")
out.parent.mkdir(parents=True, exist_ok=True)
lines = [
    "# 113310 rows extracted 2026-09-05 from the classification-codes skill's derived NAICS data:",
    "#   naics_2017.csv, naics_2022.csv (structure files) and naics_2017_to_2022.csv (concordance).",
    "# link_type is derived by that skill from code multiplicities after deduplication; it is NOT a",
    "# Census column. Census ships four columns and publishes no allocation weights.",
    "vintage,code,title,parent_code,change_indicator,link_type_to_next",
]
for vintage, fname in (("2017", "naics_2017.csv"), ("2022", "naics_2022.csv")):
    for row in (src / fname).read_text().splitlines()[1:]:
        parts = row.split(",")
        if parts[0] == "113310":
            lines.append(f"{vintage},113310,{parts[2]},{parts[3]},{parts[6]},")
conc = [r for r in (src / "naics_2017_to_2022.csv").read_text().splitlines() if r.startswith("113310,")]
assert len(conc) == 1, conc
lines[-2] = lines[-2].rsplit(",", 1)[0] + "," + conc[0].split(",")[-1]
out.write_text("\n".join(lines) + "\n")
print(out.read_text())
PY
```

Expected: a five-line CSV body — a comment block, a header, and one row per vintage, the 2017 row
carrying `link_type_to_next = 1:1`. If the skill directory is absent on your machine, stop and say
so in your implementer report rather than typing the values by hand.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_harmonize.py`:

```python
"""Versioned dimensions, bridges, the 113310 crosswalk, and the two concept guards."""

from __future__ import annotations

import polars as pl
import pytest

from logging_employment.contracts import BRIDGE_SCHEMA, validate_frame
from logging_employment.errors import ConceptViolationError
from logging_employment.harmonize import bridge, concepts, dimensions, naics


def test_all_nine_section_86_dimensions_exist() -> None:
    assert set(dimensions.DIMENSIONS) == {
        "geography", "naics", "ownership", "source_universe", "statistical_unit",
        "reference_period", "size_concept", "release_status", "disclosure_regime",
    }


def test_every_dimension_frame_carries_a_version_column() -> None:
    for name in dimensions.DIMENSIONS:
        frame = dimensions.dimension_frame(name)
        assert "dimension_version" in frame.columns
        assert frame.height > 0


def test_bridge_frame_matches_the_declared_schema() -> None:
    frame = bridge.bridge_frame(
        [
            {
                "bridge_id": "cbp_march_to_qcew_month",
                "source_concept": "CBP employment, week including March 12",
                "target_concept": "QCEW monthly employment, pay period including the 12th",
                "valid_start": "2017-01",
                "valid_end": "2024-12",
                "method": "measurement_model",
                "uncertainty_treatment": "estimated in the Stage 6 measurement model",
                "verification_status": "declared_not_estimated",
            }
        ]
    )
    validate_frame(frame, BRIDGE_SCHEMA, "bridge")


def test_the_window_spans_two_naics_vintages() -> None:
    assert naics.vintage_for_year(2017) == "NAICS 2017"
    assert naics.vintage_for_year(2021) == "NAICS 2017"
    assert naics.vintage_for_year(2022) == "NAICS 2022"
    assert naics.vintage_for_year(2024) == "NAICS 2022"


def test_113310_survives_the_window_mechanically() -> None:
    # D1 fixes a window spanning the 2017 -> 2022 transition, so this exercises the boundary.
    naics.assert_113310_survives_the_window()
    frame = naics.crosswalk_113310()
    assert set(frame["vintage"].to_list()) == {"2017", "2022"}
    assert frame["title"].unique().to_list() == ["Logging"]


def test_the_crosswalk_docstring_does_not_call_link_type_a_census_column() -> None:
    source = naics.__doc__ or ""
    assert "not a Census column" in source or "NOT a Census column" in source


def test_enterprise_size_is_rejected_as_an_establishment_size_measurement() -> None:
    with pytest.raises(ConceptViolationError, match="enterprise"):
        concepts.reject_enterprise_size("enterprise", "susb")


def test_establishment_size_passes_the_guard() -> None:
    concepts.reject_enterprise_size("establishment", "cbp")


def test_nonemployer_is_rejected_from_the_core_total() -> None:
    with pytest.raises(ConceptViolationError, match="nonemployer"):
        concepts.reject_nonemployer_in_core_total("nonemployer")
```

- [ ] **Step 3: Run to verify it fails**

Run: `uv run pytest tests/unit/test_harmonize.py -v`
Expected: FAIL — `ImportError: cannot import name 'bridge' from 'logging_employment.harmonize'`.

- [ ] **Step 4: Write `harmonize/naics.py`**

```python
"""NAICS vintage handling and the mechanical 113310 crosswalk across the D1 window.

The crosswalk rows are vendored in `naics_113310.csv` from the classification-codes skill's derived
NAICS data. Two caveats travel with them, recorded by the Stage 0 audit and repeated here because
they bound what this module's passing test proves:

* `link_type = 1:1` is derived from code multiplicities after deduplication; it is **not a Census
  column**. Census ships four columns -- source code, source title, target code, target title --
  flags partial flows through cell formatting that a plain parse discards, and publishes no
  allocation weights.
* 1:1 establishes only that 113310 neither split nor merged in the six-digit code pairing. That is
  not a statement about the industry's definitional content. The unchanged title and the empty
  structure-file `change_indicator` are what carry the continuity claim, and even those are titles
  and markers rather than a comparison of the two vintages' definitional text.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

_CROSSWALK = Path(__file__).parent / "naics_113310.csv"

# The QCEW vintage boundary Stage 0 recorded: NAICS 2017 for reference years 2017-2021, NAICS 2022
# from 2022 on. QCEW publishes no per-row vintage column, so this mapping is documented rather than
# measured, and it rests on one premise no source cited in the audit supports -- that QCEW does not
# retabulate prior reference years onto a new vintage. Stage 0 carried it as uncited and routed a
# citation to a later stage; it is uncited still. Treat a contradiction here as evidence about the
# premise, not as a parser bug.
_VINTAGE_BOUNDARY_YEAR = 2022


def vintage_for_year(year: int) -> str:
    """The NAICS vintage a QCEW reference year's rows carry."""
    return "NAICS 2022" if year >= _VINTAGE_BOUNDARY_YEAR else "NAICS 2017"


def crosswalk_113310() -> pl.DataFrame:
    """The vendored 113310 rows for every vintage the D1 window spans."""
    return pl.read_csv(_CROSSWALK, comment_prefix="#", schema_overrides={"code": pl.String})


def assert_113310_survives_the_window() -> None:
    """Raise unless 113310 is present, titled Logging, and unchanged across both vintages.

    Mechanical rather than string-continuity: §3.1 states outright that apparent code-string
    continuity is not a substitute for a versioned crosswalk test, so this reads the concordance
    and the structure files' change indicators rather than observing that "113310" appears twice.
    """
    frame = crosswalk_113310()
    vintages = set(frame["vintage"].cast(pl.String).to_list())
    if vintages != {"2017", "2022"}:
        raise ValueError(f"expected both window vintages in the crosswalk, found {sorted(vintages)}")
    titles = set(frame["title"].to_list())
    if titles != {"Logging"}:
        raise ValueError(f"113310's title is not stable across vintages: {sorted(titles)}")
    changed = frame.filter(
        pl.col("change_indicator").is_not_null() & (pl.col("change_indicator") != "")
    )
    if changed.height:
        raise ValueError(
            f"113310 carries a non-empty change_indicator in {changed['vintage'].to_list()}; the "
            "structure file marks it as changed from the prior vintage"
        )
    link = frame.filter(pl.col("vintage") == "2017")["link_type_to_next"].to_list()
    if link != ["1:1"]:
        raise ValueError(f"the 2017->2022 concordance does not pair 113310 one-to-one: {link}")
```

- [ ] **Step 5: Write `harmonize/dimensions.py`, `bridge.py`, and `concepts.py`**

```python
# harmonize/dimensions.py
"""The nine versioned dimensions §8.6 requires."""

from __future__ import annotations

import polars as pl

from ..constants import STATES_DC_FIPS

DIMENSION_VERSION = "v1"

DIMENSIONS: dict[str, tuple[str, ...]] = {
    "geography": tuple(STATES_DC_FIPS),
    "naics": ("113310",),
    "ownership": ("5",),
    "source_universe": ("qcew_covered_private", "cbp_establishments"),
    "statistical_unit": ("establishment",),
    "reference_period": ("calendar_month", "week_including_march_12"),
    "size_concept": ("march_reference", "contemporaneous_modeled"),
    "release_status": ("final", "preliminary"),
    "disclosure_regime": (
        "qcew_disclosure_code_v1",
        "noise_infusion",
        "noise_infusion_plus_suppression",
    ),
}


def dimension_frame(name: str) -> pl.DataFrame:
    """One dimension's members, each stamped with the dimension version."""
    if name not in DIMENSIONS:
        raise KeyError(f"unknown dimension {name!r}; known: {sorted(DIMENSIONS)}")
    members = list(DIMENSIONS[name])
    return pl.DataFrame(
        {
            "dimension": [name] * len(members),
            "member": members,
            "dimension_version": [DIMENSION_VERSION] * len(members),
        },
        schema={"dimension": pl.String, "member": pl.String, "dimension_version": pl.String},
    )
```

```python
# harmonize/bridge.py
"""The §8.6 bridge table."""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from ..contracts import BRIDGE_SCHEMA


def bridge_frame(rows: Sequence[dict[str, str]]) -> pl.DataFrame:
    """Render bridge rows in the declared column order.

    §8.6's closing line binds every caller: no bridge may be introduced solely to force totals to
    agree. A bridge whose `method` is a reconciliation step rather than a concept mapping does not
    belong in this table.
    """
    return pl.DataFrame(list(rows), schema=BRIDGE_SCHEMA, orient="row")
```

```python
# harmonize/concepts.py
"""Concept guards that halt a run before a statistical unit is silently relabeled."""

from __future__ import annotations

from ..errors import ConceptViolationError


def reject_enterprise_size(size_dimension: str, source_id: str) -> None:
    """Raise if an enterprise-size dimension is offered as establishment size (INV-010).

    Stage 0 measured SUSB's size dimension as `enterprise` (column `ENTRSIZE`). §5.3 permits SUSB
    into a weak prior or a sensitivity model with its concept preserved; what it forbids is the
    relabeling this guard catches.
    """
    if "enterprise" in size_dimension.lower():
        raise ConceptViolationError(
            f"{source_id} carries size dimension {size_dimension!r}; enterprise size is never an "
            "establishment-size measurement (INV-010, SRC-OTH-001)"
        )


def reject_nonemployer_in_core_total(source_id: str) -> None:
    """Raise if a nonemployer source is routed into the core employment total (SRC-OTH-004)."""
    if "nonemp" in source_id.lower():
        raise ConceptViolationError(
            f"{source_id} is a nonemployer source and is excluded from the core employment total; "
            "it may only feed a separately labeled expanded-universe output (§5.3)"
        )
```

- [ ] **Step 6: Run to verify it passes**

Run: `uv run pytest tests/unit/test_harmonize.py -v`
Expected: PASS, 9 passed.

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/harmonize/ tests/unit/test_harmonize.py
git commit -m "feat(harmonize): add versioned dimensions, bridges, concept guards, and the 113310 crosswalk"
```

---

### Task 14: `fetch`, `build-harmonized`, and the offline byte-identical rebuild

**Files:**
- Create: `src/logging_employment/build.py`
- Modify: `src/logging_employment/cli.py`
- Create: `tests/integration/test_build_harmonized.py`
- Create: `tests/integration/__init__.py`

**Interfaces:**
- Consumes: every prior task.
- Produces:
  - `build.write_parquet_deterministic(frame: polars.DataFrame, path: Path) -> str` — writes and
    returns the output's sha256
  - `build.build_harmonized(cfg: Config, *, raw_root: Path, out_root: Path, allow_network: bool = False) -> dict[str, str]`
    mapping table name to output sha256
  - CLI `fetch --source {qcew,qcew_size,cbp} --config …` and `build-harmonized --config …`

**The exit criterion this task discharges.** *A frozen pull covering the full D1 window rebuilds
byte-identical harmonized Parquet from `data/raw/` with the network disabled.* Two properties, and
the test must check both separately: **offline** (no HTTP call is attempted) and **byte-identical**
(two runs produce the same file hashes).

Determinism has three enemies here, all of which the implementation must remove: row order (sort
before writing), Parquet metadata timestamps (write with a fixed compression setting and no
statistics that embed a clock), and any column carrying `retrieved_at_utc` into a harmonized table.
`retrieved_at_utc` belongs in `source_snapshot`, which is a manifest, not a harmonized table.

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/test_build_harmonized.py`:

```python
"""§19 Phase 1 acceptance: an offline rebuild is byte-identical."""

from __future__ import annotations

import shutil
from pathlib import Path

import httpx
import pytest

from logging_employment.build import build_harmonized
from logging_employment.config import load_config

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"


@pytest.fixture()
def frozen_raw(tmp_path: Path) -> Path:
    """A `data/raw`-shaped tree holding the audited fixture bytes."""
    raw = tmp_path / "raw"
    (raw / "qcew" / "frozen").mkdir(parents=True)
    shutil.copy(FIXTURES / "qcew" / "slice_2017q1.csv", raw / "qcew" / "frozen" / "2017q1.csv")
    (raw / "qcew_size" / "frozen").mkdir(parents=True)
    shutil.copy(
        FIXTURES / "qcew_size" / "2017_q1_by_size.zip",
        raw / "qcew_size" / "frozen" / "2017_q1_by_size.zip",
    )
    (raw / "cbp" / "frozen").mkdir(parents=True)
    shutil.copy(FIXTURES / "cbp" / "data_113310_2023.json", raw / "cbp" / "frozen" / "2023.json")
    return raw


def test_rebuild_is_byte_identical(frozen_raw: Path, tmp_path: Path) -> None:
    cfg = load_config(REPO / "config.yaml")
    first = build_harmonized(cfg, raw_root=frozen_raw, out_root=tmp_path / "a")
    second = build_harmonized(cfg, raw_root=frozen_raw, out_root=tmp_path / "b")
    assert first == second
    assert set(first) == {"qcew_monthly", "qcew_national_size", "cbp_state_size", "bridge"}


def test_rebuild_attempts_no_network_call(
    frozen_raw: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args: object, **kwargs: object) -> None:
        raise AssertionError("build-harmonized attempted a network call")

    monkeypatch.setattr(httpx.Client, "send", explode)
    monkeypatch.setattr(httpx, "get", explode)
    cfg = load_config(REPO / "config.yaml")
    build_harmonized(cfg, raw_root=frozen_raw, out_root=tmp_path / "offline")


def test_no_harmonized_table_carries_a_retrieval_timestamp(
    frozen_raw: Path, tmp_path: Path
) -> None:
    import polars as pl

    out = tmp_path / "c"
    build_harmonized(cfg=load_config(REPO / "config.yaml"), raw_root=frozen_raw, out_root=out)
    for path in out.glob("*.parquet"):
        assert "retrieved_at_utc" not in pl.read_parquet_schema(path)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/integration/test_build_harmonized.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.build'`.

- [ ] **Step 3: Write `build.py`**

```python
"""Deterministic assembly of the harmonized layer from frozen raw bytes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl

from .config import Config
from .harmonize import bridge, disclosure
from .harmonize.naics import vintage_for_year
from .ingest import cbp, qcew, qcew_size

BUILDER_VERSION = "build_harmonized/1"

# The bridges this stage declares. Each maps a source concept onto the target concept, and none
# exists to force a total to agree (§8.6).
_BRIDGE_ROWS = [
    {
        "bridge_id": "cbp_march_week_to_qcew_month",
        "source_concept": "CBP employment, week including March 12",
        "target_concept": "QCEW monthly employment, pay period including the 12th",
        "valid_start": "2017-01",
        "valid_end": "2024-12",
        "method": "measurement_model",
        "uncertainty_treatment": "estimated in the Stage 6 measurement model",
        "verification_status": "declared_not_estimated",
    },
    {
        "bridge_id": "qcew_size_march_class",
        "source_concept": "QCEW national size class, first-quarter file",
        "target_concept": "March-reference establishment size class k_y",
        "valid_start": "2017-01",
        "valid_end": "2024-12",
        "method": "definitional",
        "uncertainty_treatment": "none -- both sides are March-referenced by construction",
        "verification_status": "verified_stage0",
    },
]


def write_parquet_deterministic(frame: pl.DataFrame, path: Path) -> str:
    """Write a frame to Parquet reproducibly and return the file's sha256.

    Row order is fixed by sorting on every column before writing: Parquet preserves input order, so
    two runs that assemble the same rows in different orders would produce different bytes and the
    §19 Phase 1 criterion would fail for a reason that has nothing to do with the data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Natural key first, remaining columns as tiebreak: the same determinism as sorting on every
    # column, but the file reads in a sensible order rather than a hash order.
    natural = [c for c in ("area_fips", "state_fips", "reference_month", "size_code") if c in frame.columns]
    ordered = frame.sort(by=natural + [c for c in frame.columns if c not in natural])
    ordered.write_parquet(path, compression="uncompressed", statistics=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_harmonized(
    cfg: Config, *, raw_root: Path, out_root: Path, allow_network: bool = False
) -> dict[str, str]:
    """Assemble every harmonized table from stored bytes and return their output hashes.

    Reads only from `raw_root`. No fetch happens here: acquisition is `fetch`'s job, and keeping
    the two apart is what makes an offline rebuild possible at all (§19 Phase 1).
    """
    if allow_network:
        raise ValueError("build_harmonized never fetches; use `fetch` to acquire bytes first")
    hashes: dict[str, str] = {}

    qcew_frames = [
        qcew.parse_qcew_monthly(
            qcew.read_slice_csv(path.read_bytes()),
            snapshot_id=path.stem,
            release_vintage=path.stem,
            release_status=cfg.sources.qcew.release_status,
            naics_vintage=vintage_for_year(int(path.stem[:4])),
        )
        for path in sorted((raw_root / "qcew").rglob("*.csv"))
    ]
    hashes["qcew_monthly"] = write_parquet_deterministic(
        pl.concat(qcew_frames), out_root / "qcew_monthly.parquet"
    )

    size_frames = [
        qcew_size.parse_qcew_national_size(
            qcew_size.read_by_size_zip(path.read_bytes()),
            snapshot_id=path.stem,
            reference_year=int(path.stem[:4]),
            naics_vintage=vintage_for_year(int(path.stem[:4])),
        )
        for path in sorted((raw_root / "qcew_size").rglob("*.zip"))
    ]
    hashes["qcew_national_size"] = write_parquet_deterministic(
        pl.concat(size_frames), out_root / "qcew_national_size.parquet"
    )

    cbp_frames = []
    for path in sorted((raw_root / "cbp").rglob("*.json")):
        year = int(path.stem[:4])
        cbp_frames.append(
            cbp.parse_cbp_state_size(
                json.loads(path.read_text()),
                snapshot_id=path.stem,
                reference_year=year,
                predicate=predicate_from_stored_metadata(raw_root / "cbp", year),
                naics_vintage=vintage_for_year(year),
                regime=disclosure.regime_for_year(
                    year, fail_on_unknown=cfg.sources.cbp.fail_on_unknown_disclosure_regime
                ),
            )
        )
    hashes["cbp_state_size"] = write_parquet_deterministic(
        pl.concat(cbp_frames), out_root / "cbp_state_size.parquet"
    )

    hashes["bridge"] = write_parquet_deterministic(
        bridge.bridge_frame(_BRIDGE_ROWS), out_root / "bridge.parquet"
    )
    return hashes
```

`predicate_from_stored_metadata` is what keeps `build_harmonized` honest about SRC-CBP-001. It
reads the predicate out of the `variables.json` stored beside that year's data file, so the offline
rebuild discovers the name from metadata exactly as the online fetch did. Add it to `build.py`:

```python
def predicate_from_stored_metadata(cbp_raw_dir: Path, year: int) -> str:
    """The NAICS predicate for one reference year, read from that year's stored metadata.

    A literal here would contradict Task 11's own test: the predicate name is a property of the
    vintage CBP serves, not of the reference year's NAICS vintage, and Stage 0 measured the two
    disagreeing for 2022 and 2023.
    """
    candidates = sorted(cbp_raw_dir.rglob(f"*{year}*variables.json"))
    if not candidates:
        raise FileNotFoundError(
            f"no stored variables.json for CBP {year}; fetch stores it beside the data file so the "
            "offline rebuild can discover the predicate the same way the online fetch did"
        )
    return cbp.discover_naics_predicate(json.loads(candidates[0].read_text()))
```

`fetch` must therefore store `variables.json` alongside each year's data response — Task 16's
`fetch_source` does exactly that in its CBP branch, before it builds the query.

- [ ] **Step 4: Add `fetch` and `build-harmonized` to `cli.py`**

```python
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
        cfg, raw_root=Path(cfg.storage.raw_uri), out_root=Path(cfg.storage.staged_uri)
    )
    for table, digest in sorted(hashes.items()):
        typer.echo(f"{table} {digest}")
```

- [ ] **Step 5: Run the integration test**

Run: `uv run pytest tests/integration/test_build_harmonized.py -v`
Expected: PASS, 3 passed.

- [ ] **Step 6: Run the whole suite, both suites**

Run: `uv run pytest -q`
Expected: every test passes. Report the count.

Run: `PYTHONPATH=scripts/audit uv run --no-project pytest tests/audit -q`
Expected: Stage 0's suite still passes, unchanged.

- [ ] **Step 7: Run the linters**

Run: `uv run ruff check src tests && uv run black --check src tests && uv run interrogate src`
Expected: all three clean. Fix what they flag rather than loosening their configuration.

- [ ] **Step 8: Commit**

```bash
git add src/logging_employment/build.py src/logging_employment/cli.py tests/integration/
git commit -m "feat(build): assemble the harmonized layer deterministically from frozen bytes"
```

---

### Task 15: The universe filter, the suppression-type default, and the SRC-QCEW-006/007 in-code tests

**Files:**
- Modify: `src/logging_employment/ingest/qcew.py`
- Modify: `src/logging_employment/contracts.py`
- Create: `src/logging_employment/harmonize/universe.py`
- Create: `tests/unit/test_universe.py`

**Interfaces:**
- Consumes: Task 9's parser; Task 2's `constants.STATE_AREAS`, `NATIONAL_AREA`, `PRIVATE_OWN_CODE`.
- Produces:
  - `contracts.SUPPRESSION_TYPES: tuple[str, ...]` = `("unknown", "primary_like", "complementary_like")`
    and a `suppression_type` column appended to `QCEW_MONTHLY_SCHEMA`
  - `ingest.qcew.apply_universe_filter(frame: polars.DataFrame) -> polars.DataFrame`
  - `harmonize.universe.state_universe_report(frame: polars.DataFrame) -> dict[str, object]`
  - `harmonize.universe.assert_definitional_alignment(frame: polars.DataFrame) -> None`

**Three roadmap rows this task closes, none of which any earlier task touches.**

* **REQ-002 (universe filter).** The core target is *private* QCEW-covered jobs over the
  `states_dc` geography. No earlier task filters to it — Task 9 parses whatever rows it is given,
  which is correct for a parser and insufficient for the pipeline.
* **INV-009 (default unknown).** The real-world suppression *type* is recorded as `unknown` unless a
  public source identifies it; `primary_like` and `complementary_like` are reserved for Stage 4's
  synthetic masks. Nothing in QCEW identifies the type, so every real row must carry `unknown` —
  and the only way that survives Stage 4 is if the column exists here with that default.
* **SRC-QCEW-006/007 (in-code tests).** Stage 0 produced the *verdicts*; this stage owes the
  *tests*. SRC-QCEW-006 is the state/national universe check each month; SRC-QCEW-007 is the
  definitional-alignment check before any constraint is created.

**What the universe report must and must not claim.** Stage 0's verdict was `decline` — the
employment identity is untestable because every one of the 96 months carries at least one
suppressed states+DC cell. The establishment margin closed exactly in 32 of 32 quarters. So this
report **measures and records**; it does not re-derive the branch verdict, and it must not report
"identity holds" on a month whose state sum is incomplete. Its job is to hand Stage 2 the per-month
facts: how many state cells are suppressed, whether any non-state area appears, and whether the
national row is present at all.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_universe.py`:

```python
"""REQ-002, INV-009, SRC-QCEW-006 and SRC-QCEW-007 in code."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from logging_employment import constants
from logging_employment.contracts import SUPPRESSION_TYPES
from logging_employment.errors import ConceptViolationError
from logging_employment.harmonize import universe
from logging_employment.ingest import qcew

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "qcew" / "slice_2017q1.csv"


def _parsed() -> pl.DataFrame:
    return qcew.parse_qcew_monthly(
        qcew.read_slice_csv(FIXTURE.read_bytes()),
        snapshot_id="s", release_vintage="2017Q1", release_status="final",
        naics_vintage="NAICS 2017",
    )


def test_the_universe_filter_keeps_private_state_and_national_rows_only() -> None:
    filtered = qcew.apply_universe_filter(_parsed())
    assert filtered["ownership_code"].unique().to_list() == [constants.PRIVATE_OWN_CODE]
    kept = set(filtered["area_fips"].unique().to_list())
    assert kept <= constants.STATE_AREAS | {constants.NATIONAL_AREA}
    assert "72000" not in kept  # Puerto Rico is outside states_dc
    assert filtered.filter(pl.col("aggregation_level") == "78").height == 0  # no counties


def test_every_real_row_carries_suppression_type_unknown() -> None:
    # INV-009: primary_like / complementary_like are for Stage 4's synthetic masks only.
    filtered = qcew.apply_universe_filter(_parsed())
    assert filtered["suppression_type"].unique().to_list() == ["unknown"]
    assert SUPPRESSION_TYPES[0] == "unknown"


def test_dc_is_in_the_universe_but_contributes_no_row() -> None:
    # Stage 0 measured 11000 publishing zero private 113310 rows in all 96 months. The universe
    # includes it; the data does not. Those are different statements and both must survive.
    assert "11000" in constants.STATE_AREAS
    assert qcew.apply_universe_filter(_parsed()).filter(pl.col("area_fips") == "11000").height == 0


def test_the_universe_report_counts_suppressed_state_cells_per_month() -> None:
    report = universe.state_universe_report(qcew.apply_universe_filter(_parsed()))
    assert set(report) >= {
        "months", "suppressed_state_cells_by_month", "non_state_areas_present",
        "national_row_present_by_month", "months_with_a_complete_state_sum",
    }
    # Stage 0 measured zero months free of a suppressed state cell; this fixture is one quarter of
    # that window, so the count is reported rather than asserted to a fixed number.
    assert isinstance(report["months_with_a_complete_state_sum"], int)


def test_the_report_sees_non_state_areas_on_an_unfiltered_frame() -> None:
    # Run on the *unfiltered* frame: apply_universe_filter drops non-state areas by construction,
    # so asserting an empty list downstream of it could never fail. Puerto Rico (72000) is present
    # in 2017 state-like rows, which is where this check has content.
    report = universe.state_universe_report(_parsed())
    assert "72000" in report["non_state_areas_present"]


def test_the_report_never_claims_an_identity_on_an_incomplete_state_sum() -> None:
    report = universe.state_universe_report(qcew.apply_universe_filter(_parsed()))
    for month, suppressed in report["suppressed_state_cells_by_month"].items():
        if suppressed > 0:
            assert month not in report["identity_evaluable_months"]


def test_alignment_passes_when_national_and_state_rows_share_industry_and_ownership() -> None:
    universe.assert_definitional_alignment(qcew.apply_universe_filter(_parsed()))


def test_alignment_fails_when_ownership_differs_between_levels() -> None:
    frame = qcew.apply_universe_filter(_parsed())
    doctored = frame.with_columns(
        pl.when(pl.col("area_type") == "national")
        .then(pl.lit("3"))
        .otherwise(pl.col("ownership_code"))
        .alias("ownership_code")
    )
    with pytest.raises(ConceptViolationError, match="ownership"):
        universe.assert_definitional_alignment(doctored)
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_universe.py -v`
Expected: FAIL — `ImportError: cannot import name 'SUPPRESSION_TYPES'`.

- [ ] **Step 3: Add `suppression_type` to the contract**

In `contracts.py`, add above the schemas:

```python
# INV-009: the real-world suppression type is unknown unless a public source identifies one, and
# QCEW identifies none. The two labelled values exist for Stage 4's synthetic masks and must never
# be written onto a real row.
SUPPRESSION_TYPES: tuple[str, ...] = ("unknown", "primary_like", "complementary_like")
```

and append `"suppression_type": pl.String` to `QCEW_MONTHLY_SCHEMA` as its final field. Task 9's
`test_qcew_monthly_carries_every_field_the_spec_names` will fail until you add `"suppression_type"`
to that test's expected list — update the test, and note in your report that the field is this
package's addition, not one §7.3 names.

- [ ] **Step 4: Add the universe filter to `ingest/qcew.py`**

```python
from ..constants import NATIONAL_AREA, PRIVATE_OWN_CODE, STATE_AREAS


def apply_universe_filter(frame: pl.DataFrame) -> pl.DataFrame:
    """Restrict to the estimand's universe: private ownership, states+DC and the national row.

    REQ-002 and §3.2. Puerto Rico is dropped here rather than at read time: Stage 0 measured it
    present in state-like rows and measured it sitting *outside* the national total, so it is a
    real published area that this estimand's geography universe excludes -- not a parse artifact.
    """
    keep = STATE_AREAS | {NATIONAL_AREA}
    return frame.filter(
        (pl.col("ownership_code") == PRIVATE_OWN_CODE) & pl.col("area_fips").is_in(list(keep))
    )
```

and set the default in `parse_qcew_monthly`, alongside the other literal columns:

```python
            pl.lit("unknown").alias("suppression_type"),
```

- [ ] **Step 5: Write `harmonize/universe.py`**

```python
"""The SRC-QCEW-006 universe check and the SRC-QCEW-007 alignment check, in code.

Stage 0 produced the branch verdict -- `decline`, because every one of the window's 96 testable
months carries at least one suppressed states+DC cell, leaving the employment identity untestable
on a complete published state sum. This module does not re-derive that verdict. It measures the
per-month facts Stage 2 needs in order to build constraints at all, and it refuses to describe a
month with an incomplete state sum as one where an identity was evaluated.
"""

from __future__ import annotations

import polars as pl

from ..constants import NATIONAL_AREA, STATE_AREAS
from ..errors import ConceptViolationError


def state_universe_report(frame: pl.DataFrame) -> dict[str, object]:
    """Per-month universe facts: suppressed state cells, non-state areas, national row presence."""
    states = frame.filter(pl.col("area_fips").is_in(list(STATE_AREAS)))
    months = sorted(frame["reference_month"].unique().to_list())
    suppressed_by_month = {
        row["reference_month"]: row["len"]
        for row in states.filter(pl.col("observation_status") == "suppressed")
        .group_by("reference_month")
        .len()
        .iter_rows(named=True)
    }
    suppressed_by_month = {m: suppressed_by_month.get(m, 0) for m in months}
    national_months = set(
        frame.filter(pl.col("area_fips") == NATIONAL_AREA)["reference_month"].unique().to_list()
    )
    evaluable = [
        m for m in months if suppressed_by_month[m] == 0 and m in national_months
    ]
    outside = sorted(
        set(frame["area_fips"].unique().to_list()) - STATE_AREAS - {NATIONAL_AREA}
    )
    return {
        "months": months,
        "suppressed_state_cells_by_month": suppressed_by_month,
        "non_state_areas_present": outside,
        "national_row_present_by_month": {m: (m in national_months) for m in months},
        "identity_evaluable_months": evaluable,
        "months_with_a_complete_state_sum": len(evaluable),
    }


def assert_definitional_alignment(frame: pl.DataFrame) -> None:
    """Halt unless national and state rows share industry, ownership and NAICS vintage.

    SRC-QCEW-007 requires this *before* a constraint is created, which is why it lives here rather
    than inside Stage 2's builder: a misaligned pair must never reach the point where it could
    become a hard equation.
    """
    national = frame.filter(pl.col("area_type") == "national")
    state = frame.filter(pl.col("area_type") == "state")
    if national.is_empty() or state.is_empty():
        return
    for column in ("industry_code", "ownership_code", "naics_vintage"):
        left = set(national[column].unique().to_list())
        right = set(state[column].unique().to_list())
        if left != right:
            raise ConceptViolationError(
                f"national and state rows disagree on {column}: {sorted(left)} vs {sorted(right)}; "
                "refusing to treat them as definitionally aligned (SRC-QCEW-007)"
            )
```

- [ ] **Step 6: Run to verify it passes**

Run: `uv run pytest tests/unit/test_universe.py tests/unit/test_qcew_parser.py -v`
Expected: PASS. If `test_qcew_monthly_carries_every_field_the_spec_names` still fails, you have not
updated its expected list — do that, do not drop the column.

- [ ] **Step 7: Prove SRC-QCEW-005's preliminary/final distinction survives**

Add to `tests/unit/test_qcew_parser.py`:

```python
def test_release_status_distinguishes_preliminary_from_final() -> None:
    final = qcew.parse_qcew_monthly(
        _row(), snapshot_id="s", release_vintage="v", release_status="final",
        naics_vintage="NAICS 2017",
    )
    prelim = qcew.parse_qcew_monthly(
        _row(), snapshot_id="s", release_vintage="v", release_status="preliminary",
        naics_vintage="NAICS 2017",
    )
    assert final["release_status"].unique().to_list() == ["final"]
    assert prelim["release_status"].unique().to_list() == ["preliminary"]
    # SRC-QCEW-005: a final national control may not be combined with preliminary state values in
    # a hard equation. The column is what lets Stage 2 refuse that combination.
    assert "release_status" in final.columns
```

Run: `uv run pytest tests/unit/test_qcew_parser.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/logging_employment/ingest/qcew.py src/logging_employment/contracts.py \
        src/logging_employment/harmonize/universe.py tests/unit/test_universe.py \
        tests/unit/test_qcew_parser.py
git commit -m "feat(universe): filter to the estimand universe and add the QCEW-006/007 checks"
```

---

### Task 16: `fetch`, `source_manifest.parquet`, and the live end-to-end run

**Files:**
- Create: `src/logging_employment/fetching.py`
- Create: `tests/unit/test_fetching.py`
- Modify: `src/logging_employment/build.py`

**Interfaces:**
- Consumes: Task 5's `HttpFetcher`, `RawStore`, `snapshot_row`; Tasks 7/8/10/11's fetchers;
  Task 6's registry.
- Produces:
  - `fetching.fetch_source(source: str, cfg: Config, *, env_path: Path | None = None) -> list[dict]`
  - `fetching.write_source_manifest(rows: Sequence[dict], path: Path) -> str`

**This task completes the CLI.** Task 14's `fetch` command calls `fetching.fetch_source` through a
function-local import, so Task 14's suite passes without this module — only invoking `fetch` needs
it. The live end-to-end run that proves the §19 Phase 1 exit criterion over the real window is
Step 5 below, and it is the last gate in this plan.

**REQ-028.** `source_manifest.parquet` is the provenance artifact §6.2 names in the run directory.
It is the `source_snapshot` rows for one run, written to one file — not a second vocabulary.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_fetching.py`:

```python
"""Fetch writes immutable bytes, one snapshot row each, and never a credential."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import SOURCE_SNAPSHOT_SCHEMA, validate_frame
from logging_employment.fetching import fetch_source, write_source_manifest

REPO = Path(__file__).resolve().parents[2]


def test_manifest_matches_the_snapshot_schema(tmp_path: Path) -> None:
    rows = [
        {
            "snapshot_id": "abc", "source_id": "qcew", "request_url_or_file": "https://x/y.csv",
            "request_parameters_json": "{}", "retrieved_at_utc": "2026-09-05T00:00:00+00:00",
            "source_publication_date": "", "reference_start": "2017-01",
            "reference_end": "2017-03", "release_status": "final", "naics_vintage": "NAICS 2017",
            "schema_fingerprint": "f" * 64, "content_sha256": "a" * 64, "byte_count": 10,
            "http_status": 200, "parser_version": "qcew_monthly/1", "raw_path": "data/raw/x",
        }
    ]
    path = tmp_path / "source_manifest.parquet"
    digest = write_source_manifest(rows, path)
    assert len(digest) == 64
    validate_frame(pl.read_parquet(path), SOURCE_SNAPSHOT_SCHEMA, "source_snapshot")


def test_manifest_writing_is_deterministic(tmp_path: Path) -> None:
    rows = [
        {k: ("x" if v == pl.String else 1) for k, v in SOURCE_SNAPSHOT_SCHEMA.items()}
    ]
    a = write_source_manifest(rows, tmp_path / "a.parquet")
    b = write_source_manifest(rows, tmp_path / "b.parquet")
    assert a == b


def test_fetch_refuses_an_unknown_source(tmp_path: Path) -> None:
    cfg = load_config(REPO / "config.yaml")
    with pytest.raises(ValueError, match="susb"):
        fetch_source("susb", cfg, env_path=None)


def test_a_second_fetch_of_identical_bytes_stores_nothing_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    monkeypatch.setattr(
        httpx.Client, "get",
        lambda self, url, params=None: handler(httpx.Request("GET", url)),
    )
    cfg = load_config(REPO / "config.yaml")
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "who@example.invalid")
    first = fetch_source("qcew", cfg, env_path=None, raw_root=tmp_path, years=[2017], quarters=[1])
    second = fetch_source("qcew", cfg, env_path=None, raw_root=tmp_path, years=[2017], quarters=[1])
    assert first[0]["content_sha256"] == second[0]["content_sha256"]
    assert len(list(tmp_path.rglob("*.csv"))) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/unit/test_fetching.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'logging_employment.fetching'`.

- [ ] **Step 3: Write `fetching.py`**

```python
"""Acquisition: fetch each source's bytes into the immutable store and record provenance."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from pathlib import Path

import polars as pl

from .config import SECRET_ENV_VARS, Config, credentials
from .contracts import (
    CBP_STATE_SIZE_SCHEMA,
    QCEW_MONTHLY_SCHEMA,
    QCEW_NATIONAL_SIZE_SCHEMA,
    SOURCE_SNAPSHOT_SCHEMA,
    schema_fingerprint,
)
from .harmonize.naics import vintage_for_year
from .ingest import cbp, qcew, qcew_size
from .ingest.base import HttpFetcher
from .store import RawStore, snapshot_row

KNOWN_SOURCES = ("qcew", "qcew_size", "cbp")


def write_source_manifest(rows: Sequence[dict[str, object]], path: Path) -> str:
    """Write `source_manifest.parquet` reproducibly and return its sha256 (REQ-028, §18.1)."""
    frame = pl.DataFrame(list(rows), schema=SOURCE_SNAPSHOT_SCHEMA, orient="row").sort(
        ["source_id", "snapshot_id"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path, compression="uncompressed", statistics=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_source(
    source: str,
    cfg: Config,
    *,
    env_path: Path | None = None,
    raw_root: Path | None = None,
    years: Sequence[int] | None = None,
    quarters: Sequence[int] | None = None,
) -> list[dict[str, object]]:
    """Fetch one source over the D1 window and return its `source_snapshot` rows.

    Bytes land in the content-addressed store, so a second call over unchanged data re-uses the
    existing object rather than writing a second copy (§6.2). Secret values are passed to requests
    and never to `snapshot_row`, which scans for them and refuses to emit a row that carries one.
    """
    if source not in KNOWN_SOURCES:
        raise ValueError(f"unknown source {source!r}; known: {KNOWN_SOURCES}")
    creds = credentials(env_path)
    contact = creds.get("BLS_CONTACT_EMAIL") or os.environ.get("BLS_CONTACT_EMAIL", "")
    secrets = [creds.get(name) for name in SECRET_ENV_VARS]
    store = RawStore(Path(raw_root or cfg.storage.raw_uri))
    fetcher = HttpFetcher(contact_email=contact)
    window_years = list(years or range(int(cfg.project.start_month[:4]),
                                       int(cfg.project.end_month[:4]) + 1))
    rows: list[dict[str, object]] = []
    try:
        if source == "qcew":
            boundary = qcew.probe_slice_boundary(fetcher, cfg.project.industry_code_used,
                                                 range(min(window_years) - 5, min(window_years) + 1))
            for year in window_years:
                for quarter in list(quarters or (1, 2, 3, 4)):
                    route = qcew.route_for_year(year, boundary)
                    if route == "slice":
                        fetched = qcew.fetch_slice(
                            fetcher, year, quarter, cfg.project.industry_code_used
                        )
                        name = f"{year}q{quarter}.csv"
                    else:
                        fetched = fetcher.get(qcew.bulk_url(year))
                        name = f"{year}_qtrly_by_industry.zip"
                    if fetched.http_status != 200 or not fetched.content.strip():
                        continue
                    stored = store.put("qcew", fetched, name)
                    rows.append(
                        snapshot_row(
                            source_id="qcew", fetched=fetched, stored=stored,
                            reference_start=f"{year}-{(quarter - 1) * 3 + 1:02d}",
                            reference_end=f"{year}-{quarter * 3:02d}",
                            release_status=cfg.sources.qcew.release_status,
                            naics_vintage=vintage_for_year(year),
                            schema_fingerprint=schema_fingerprint(QCEW_MONTHLY_SCHEMA),
                            parser_version=qcew.PARSER_VERSION,
                            source_publication_date="", secrets=secrets,
                        )
                    )
        elif source == "qcew_size":
            for year in window_years:
                fetched = fetcher.get(qcew_size.BY_SIZE_URL.format(year=year))
                if fetched.http_status != 200:
                    continue
                stored = store.put("qcew_size", fetched, f"{year}_q1_by_size.zip")
                rows.append(
                    snapshot_row(
                        source_id="qcew_size", fetched=fetched, stored=stored,
                        reference_start=f"{year}-01", reference_end=f"{year}-03",
                        release_status="final", naics_vintage=vintage_for_year(year),
                        schema_fingerprint=schema_fingerprint(QCEW_NATIONAL_SIZE_SCHEMA),
                        parser_version=qcew_size.PARSER_VERSION,
                        source_publication_date="", secrets=secrets,
                    )
                )
        else:
            key = creds.get(cfg.sources.cbp.api_key_env, "")
            for year in window_years:
                variables = fetcher.get(cbp.VARIABLES_URL.format(year=year))
                if variables.http_status != 200:
                    continue
                store.put("cbp", variables, f"{year}_variables.json")
                predicate = cbp.discover_naics_predicate(json.loads(variables.content))
                query = cbp.build_query(year, predicate, cfg.project.industry_code_used)
                fetched = fetcher.get(cbp.CBP_URL.format(year=year), params={**query, "key": key})
                if fetched.http_status != 200:
                    continue
                stored = store.put("cbp", fetched, f"{year}.json")
                rows.append(
                    snapshot_row(
                        source_id="cbp", fetched=fetched, stored=stored,
                        reference_start=f"{year}-03", reference_end=f"{year}-03",
                        release_status="final", naics_vintage=vintage_for_year(year),
                        schema_fingerprint=schema_fingerprint(CBP_STATE_SIZE_SCHEMA),
                        parser_version=cbp.PARSER_VERSION,
                        source_publication_date="", secrets=secrets,
                    )
                )
    finally:
        fetcher.close()
    write_source_manifest(rows, Path(cfg.storage.output_uri) / "source_manifest.parquet")
    return rows
```

**The CBP request carries `key` in its parameters, and `snapshot_row` scans for it.** That is the
design, not an oversight: `snapshot_row` raises rather than writing a row whose recorded URL or
parameters contain a credential. So the CBP branch strips `key` before recording, and the guard
stays — it is what catches the next caller who forgets. Add to the imports and use it in the CBP
branch in place of the bare `fetched`:

```python
from dataclasses import replace


def _without_credentials(fetched: FetchedBytes) -> FetchedBytes:
    """The same response with credential-bearing request parameters removed.

    Only the recorded parameters change; the bytes, status and timestamp are untouched, so the
    content hash is unaffected and the stored object is still addressed by what came back.
    """
    return replace(fetched, params={k: v for k, v in fetched.params.items() if k != "key"})
```

then in the CBP branch: `stored = store.put("cbp", fetched, f"{year}.json")` stays as it is, and
the snapshot is built from `_without_credentials(fetched)` rather than `fetched`. Import
`FetchedBytes` from `.ingest.base` alongside `HttpFetcher`.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_fetching.py -v`
Expected: PASS, 4 passed. The CBP `key`-stripping note above will make
`test_a_second_fetch_of_identical_bytes_stores_nothing_new` pass only once the parameters handed to
`snapshot_row` are clean; if you see a "secret value reached a manifest payload" error, that is the
guard working.

- [ ] **Step 5: Prove the exit criterion end to end against a real window pull**

This is the one step that needs the network, and it is what §19 Phase 1 acceptance actually
requires — the fixtures above cover one quarter, not the window.

```bash
uv run --env-file .env logging-estimates fetch --source qcew --config config.yaml
uv run --env-file .env logging-estimates fetch --source qcew_size --config config.yaml
uv run --env-file .env logging-estimates fetch --source cbp --config config.yaml
uv run logging-estimates build-harmonized --config config.yaml | tee /tmp/hashes-1.txt
uv run logging-estimates build-harmonized --config config.yaml | tee /tmp/hashes-2.txt
diff /tmp/hashes-1.txt /tmp/hashes-2.txt && echo "BYTE-IDENTICAL REBUILD: PASS"
```

Expected: `diff` is silent and the marker prints. Record the four table hashes in your implementer
report. Then confirm no credential leaked:

```bash
grep -rlE "$(uv run python -c "
import os
from logging_employment.config import credentials
vals=[v for k,v in credentials().items() if k.endswith('_KEY') and v]
print('|'.join(vals))
")" data/staged runs 2>/dev/null && echo "LEAK" || echo "NO CREDENTIAL IN OUTPUT: PASS"
```

Expected: `NO CREDENTIAL IN OUTPUT: PASS`.


- [ ] **Step 6: Run everything**

Run: `uv run pytest -q` — expect all green; report the count.
Run: `PYTHONPATH=scripts/audit uv run --no-project pytest tests/audit -q` — expect Stage 0 green.
Run: `uv run ruff check src tests && uv run black --check src tests && uv run interrogate src`

- [ ] **Step 7: Commit**

```bash
git add src/logging_employment/fetching.py src/logging_employment/build.py \
        tests/unit/test_fetching.py
git commit -m "feat(fetch): acquire every source into the immutable store and write the manifest"
```

---

## Exit criteria checklist

Run this before declaring the plan complete. Each line is one of the roadmap's Stage 1 `Exit:`
clauses, with the check that discharges it.

- [ ] **Frozen pull rebuilds byte-identical harmonized Parquet offline.** Task 14 Step 5 (fixtures) and Task 16 Step 5 (the real window).
- [ ] **An `N`-coded zero parses to null.** `test_a_suppression_coded_zero_parses_to_null`.
- [ ] **A metadata-supported true zero is preserved.**
      `test_a_true_zero_is_preserved_because_the_establishment_count_supports_it`.
- [ ] **Three monthly columns expand to three rows.** `test_three_monthly_columns_expand_to_three_rows`.
- [ ] **An unknown CBP disclosure regime halts the run.** `test_2024_halts_the_run`.
- [ ] **Source NAICS vintage survives ingestion.** `test_source_naics_vintage_survives_ingestion`.
- [ ] **Enterprise-size input is rejected as an establishment-size measurement.**
      `test_enterprise_size_is_rejected_as_an_establishment_size_measurement`.
- [ ] **Manifest hashes are deterministic.** `test_rebuild_is_byte_identical`.
- [ ] **CBP size codes come from fetched metadata rather than literals.**
      `test_2017_size_codes_come_from_the_official_values_crosswalk` and
      `test_later_years_take_their_labels_from_the_response_column`.
- [ ] **`area_fips` round-trips as a string with leading zeros intact.**
      `test_area_fips_round_trips_with_leading_zeros_intact`.
- [ ] **No credential value appears in any manifest.** Task 16 Step 5's grep, plus
      `test_resolved_config_names_the_env_var_but_never_a_key_value` and
      `test_assert_no_secret_raises_on_a_leaked_value`.
- [ ] **The universe filter keeps private states+DC and national rows only (REQ-002).**
      `test_the_universe_filter_keeps_private_state_and_national_rows_only`.
- [ ] **Every real row carries `suppression_type = unknown` (INV-009).**
      `test_every_real_row_carries_suppression_type_unknown`.
- [ ] **SRC-QCEW-006/007 exist as in-code tests, not just Stage 0 verdicts.**
      `test_the_universe_report_counts_suppressed_state_cells_per_month` and
      `test_alignment_fails_when_ownership_differs_between_levels`.
- [ ] **`source_manifest.parquet` is written and deterministic (REQ-028).**
      `test_manifest_matches_the_snapshot_schema`, `test_manifest_writing_is_deterministic`.
- [ ] **`git ls-files` shows no `.env`.** Run `git ls-files | grep -c '^\.env$'` — expect `0`.

## Plan Completion Protocol

When every task is done and the final review is resolved, run the protocol in the writing-plans
skill: resolve-before-defer gate first (batch any questions for your human partner), then mark up
this file, then update `specs/deferred_items.md` — **including ticking the two items this plan was
assigned**: the `LFO,LFO_LABEL` query (Task 11 Step 6) and CBP's `unknown_years = [2024]`
fail-closed behaviour (Task 12). Then retire the plan to `specs/plans/completed/` and stamp Stage 1
in the spec's Rollout note and the roadmap.
