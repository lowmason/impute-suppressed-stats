# Stage 5 Preconditions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `logging_employment` runnable in a clean environment and make its record true, so Stage 5 (the state-total Bayesian model) can be planned against a system that starts and a roadmap that does not lie.

**Architecture:** Nine independent remediations against a shipped, green codebase. Seven touch code or tests; two are record-only. No new subsystem, no new module boundary — every change lands inside an existing file. Tasks 1–2 come first because they make every later task's test cycle trustworthy: until `python-dotenv` is a runtime dependency and the 42 data-dependent tests skip rather than fail, "the suite is green" is not a statement anyone can check on a fresh clone.

**Tech Stack:** Python >= 3.14, uv + hatchling, polars, pydantic v2, typer, httpx, pytest, ruff, interrogate.

**Requirements input:** `specs/stage5-preconditions.md` (R-S5P-1..9).

**Provenance of the code in this plan:** every code block in Tasks 2–7 was executed in an isolated git worktree at `0106056` before being written here — test run red, implementation applied, test run green, then `ruff format src tests`, `ruff check src tests` and `interrogate src` all clean. The observed outputs are quoted in each task. This repo has a documented history of plan code blocks that parse but do not run; blocks below are transcribed mechanically from the verification run, not retyped.

## Global Constraints

- `requires-python = ">=3.14"`; author `Lowell Mason <mason.lowell@mac.com>`; MIT (Rollout D4).
- **`run_id` MUST NOT change.** `runs.run_id` = sha256 of `{config: resolved_dict(cfg), inputs: {stem: sha256}}`. Adding a pydantic field to `Config` re-ids every run directory and orphans `runs/f03023ac9f3a`, the Stage 4 comparand. Optional keys are *omitted*, never null.
- **Format and lint scope is `src tests`, never `.`** — `uv run ruff format src tests`, `uv run ruff check src tests`. A bare `.` rewrites `except (A, B):` into PEP 758 syntax in `scripts/audit/` files whose PEP 723 headers declare `>=3.12`, where it does not parse.
- **`uv run interrogate src` is `fail-under = 100`.** Every new callable needs a docstring, and the house style says *why this and not the obvious alternative*, citing `§` / `INV-` / `REQ-` / `SRC-` ids.
- **Fail closed with a named error.** Everything raisable subclasses `LoggingEmploymentError` in `errors.py` and carries the offending value.
- Run pytest from the repo root. Committed fixtures live in `tests/fixtures/`; tests never read `data/`.
- Cite deferred items by `D-nnn`, never by title.

---

### Task 1: Make `python-dotenv` a runtime dependency

**Implements:** R-S5P-1

**Files:**
- Modify: `pyproject.toml:9-30`
- Modify: `uv.lock (regenerated)`

**Interfaces:**
- Consumes: nothing.
- Produces: a package whose CLI imports without the dev group. Every later task's `uv run` benefits; none depends on it by symbol.

- [ ] **Step 1: Reproduce the failure**

```bash
uv sync --no-dev && uv run logging-estimates validate-config --config config.yaml
```
Expected: `ModuleNotFoundError: No module named 'dotenv'` — `config.py` imports it at module scope.

- [ ] **Step 2: Move the dependency**

In `pyproject.toml`, add `"python-dotenv>=1.2",` to `[project].dependencies` (alphabetical, between `pydantic>=2.13` and `pyyaml>=6.0`) and delete it from `[dependency-groups].dev`.

```toml
dependencies = [
    "highspy>=1.15.1",
    "httpx>=0.28",
    "numpy>=2.5",
    "polars>=1.44",
    "pyarrow>=25.0",
    "pydantic>=2.13",
    "python-dotenv>=1.2",
    "pyyaml>=6.0",
    "scipy>=1.18.1",
    "typer>=0.27",
]
```

- [ ] **Step 3: Verify the clean-environment install works**

```bash
uv sync --no-dev && uv run logging-estimates validate-config --config config.yaml
```
Expected: the command's normal `OK` output, no traceback.

- [ ] **Step 4: Restore the dev environment and confirm the suite still runs**

```bash
uv sync && uv run pytest tests/unit/test_config.py -q
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "fix(deps): python-dotenv is a runtime dependency, not a dev one"
```


---

### Task 2: Guard the staged-data tests so a clean clone is green

**Implements:** R-S5P-2

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/unit/test_validate_{mask,propensity,recover,complementary}.py`
- Modify: `tests/unit/test_validate_{regimes,declared_regimes,temporal_regimes}.py`
- Modify: `tests/integration/test_validate_{leakage,exact_recovery}.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `tests.conftest.STAGED` (absolute `Path`) and `tests.conftest.requires_staged` (a `pytest.mark.skipif`). Later tasks may import both.

**Measured baseline (do this first, it is the whole point of the task):** with `data/` moved aside, `uv run pytest -q` reports **42 failed, 1286 passed, 28 skipped** across nine modules — 7 unit (34 tests) and 2 integration (8 tests).

**The trap:** three of the nine are MIXED. `test_validate_regimes.py` (2), `test_validate_declared_regimes.py` (2) and `test_validate_temporal_regimes.py` (1) hold five tests that PASS today with no `data/`. A blanket `pytestmark` in all nine still reports "0 failed" while silently converting those five passes into skips. **The acceptance check is arithmetic, not "0 failed":** skipped must rise by exactly 42 and passed must not fall.

- [ ] **Step 1: Record the red baseline**

```bash
mv data data.bak && uv run pytest -q ; mv data.bak data
```
Expected: `42 failed, 1286 passed, 28 skipped`.

- [ ] **Step 2: Add the guard to the root conftest**

Diff of tests/conftest.py (the whole guard; the other nine files are the shapes in `test_code`):

--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -6,6 +6,20 @@ context; see `scripts/audit/_common.py`'s module docstring). The documented test
 `PYTHONPATH=scripts/audit` for that reason. This conftest puts `scripts/audit` on `sys.path`
 too, so a bare `pytest` invocation (no `PYTHONPATH`) finds `_common` as well — it does not
 replace the documented command, only widen how the suite can be run.
+
+It also owns `requires_staged`, the shared staged-data guard. `data/staged/` is gitignored and
+rebuilt from ~564 MB of frozen source bytes, so a bare checkout has none of it, and the nine
+`validate/` modules that read those tables used to FAIL there rather than skip. The guard
+keys on a FILE EXISTING -- `qcew_monthly.parquet`, the same probe `tests/integration/test_d1_*.py`
+already spell out inline -- and not on an env var: an env var records what someone remembered to
+export, while the file records whether `build-harmonized` has actually run, which is the condition
+these tests actually depend on. `STAGED` is absolute, derived from this file, because the modules
+it replaces passed `Path("data/staged")` and so silently required pytest to be invoked from the
+repo root. It lives in the ROOT conftest for the same reason `appendix_a_config` does: both
+`tests/unit/` and `tests/integration/` need it. Modules apply it per-test wherever they also hold
+tests that need no data (`test_validate_regimes.py`, `test_validate_declared_regimes.py`,
+`test_validate_temporal_regimes.py`) -- a blanket `pytestmark` there would skip tests that pass
+in a bare checkout, shrinking coverage while still reporting `0 failed`.
 """
 
 from __future__ import annotations
@@ -23,6 +37,18 @@ if str(_AUDIT_SCRIPTS) not in sys.path:
     # named after a stdlib module must not shadow it suite-wide.
     sys.path.append(str(_AUDIT_SCRIPTS))
 
+STAGED = Path(__file__).resolve().parents[1] / "data" / "staged"
+
+# Import this in a test module (`from tests.conftest import STAGED, requires_staged`) rather than
+# repeating the skipif. It is not yet the suite's ONLY copy: `test_d1_acceptance.py`,
+# `test_d1_baselines.py`, `test_d1_validation.py`, `test_validate_cli.py` and
+# `test_stage4_acceptance.py` still spell out their own `STAGED` + skipif inline, and folding
+# those into this one is a separate change.
+requires_staged = pytest.mark.skipif(
+    not (STAGED / "qcew_monthly.parquet").exists(),
+    reason="data/staged is gitignored; run `build-harmonized` first",
+)
+
 
 @pytest.fixture()
 def appendix_a_config() -> Config:

WHY `from tests.conftest import ...` WORKS (I probed it before relying on it): `addopts =
"--import-mode=importlib"` means pytest does not touch sys.path, but it does register the root
conftest in sys.modules as `tests.conftest` (plus a synthetic `tests` parent) before any test module
is imported. Probed green three ways: from `tests/unit/`, from `tests/integration/` (which has a real
`__init__.py`), and with pytest invoked from `/tmp` against absolute paths. It is not a plain-python
import — `python -c "import tests.conftest"` would fail; only under pytest is it defined. That is
fine for test modules, and it is why the alternative (a registered `requires_staged` MARKER plus a
`pytest_collection_modifyitems` hook) was considered and dropped: it would need a `pyproject.toml`
markers edit and buys nothing measured.

- [ ] **Step 3: Apply it in the nine modules**

THE GUARD IS THE CHANGE, so "test code" here is the exact edit shape applied to the nine modules. Both patterns are verified by running them.

IMPORT PLACEMENT (load-bearing — see `gates`): ruff's isort treats `tests` as THIRD-PARTY (because `[tool.ruff] src = ["src", "tests"]` makes the *contents* of those dirs first-party, not `tests` itself), so the import goes in the third-party block, immediately after `import pytest` / `import polars as pl` and BEFORE the `logging_employment` block. Putting it after the first-party block is 9x I001.

--- PATTERN A: whole module is data-bound -> module-level `pytestmark`
Applied to: test_validate_mask.py, test_validate_propensity.py, test_validate_recover.py,
test_validate_complementary.py, test_validate_leakage.py, test_validate_exact_recovery.py.

  import polars as pl
  import pytest
  from tests.conftest import STAGED, requires_staged

  from logging_employment.config import load_config
  from logging_employment.contracts import HarmonizedData
  ...

  pytestmark = requires_staged


  def test_...():
      data = HarmonizedData.load(STAGED)          # was: HarmonizedData.load(Path("data/staged"))
      monthly = HarmonizedData.load(STAGED).qcew_monthly   # the `.qcew_monthly` variant, same rewrite

`test_validate_mask.py` is the different shape called out in the task — a module-level constant, not
a call. Its whole edit:

  -import dataclasses
  -from pathlib import Path
  +import dataclasses

   import polars as pl
   import pytest
  +from tests.conftest import STAGED, requires_staged
   ...
  -STAGED = Path("data/staged")
  +pytestmark = requires_staged

i.e. the local constant is DELETED and replaced by the import (its `_data()` helper already read
`STAGED`, so no call site changed), and `from pathlib import Path` is dropped because that was its
only use. Same `Path` removal in test_validate_temporal_regimes.py. The other seven keep `Path`
(still used by `load_config(Path("config.yaml"))`).

--- PATTERN B: module ALSO holds tests that pass with no data -> per-test `@requires_staged`
Applied to the three mixed modules. A blanket `pytestmark` here would still report 0 failed while
silently skipping 5 tests that pass today.

  test_validate_regimes.py            10 failing items / 6 functions decorated; 2 tests left undecorated
                                      (test_every_spec_declares_a_grain_and_a_disposition,
                                       test_the_census_divisions_partition_the_state_universe)
  test_validate_declared_regimes.py   3 decorated; 2 left undecorated
                                      (test_the_config_default_agrees_with_the_data,
                                       test_break_windows_are_declared_in_config_not_detected)
  test_validate_temporal_regimes.py   1 decorated; 1 left undecorated
                                      (test_retrospective_smoothing_is_declared_vacuous_not_silently_skipped)

  @requires_staged
  def test_a_never_observed_state_is_never_selected():
      ...

  # on the parametrized one, ABOVE the parametrize decorator:
  @requires_staged
  @pytest.mark.parametrize(
      "regime",
      [...],
  )
  def test_a_feasible_regime_selects_only_eligible_targets(regime):

--- PATTERN B': the subprocess script in test_validate_regimes.py (the one edit no test run here executes)
The staged path is passed as argv, NOT interpolated — an f-string would make every future brace in
that script text a landmine, and this body cannot run without data/.

       script = textwrap.dedent("""
           import hashlib
  +        import sys
           from pathlib import Path
           from logging_employment.config import load_config
           from logging_employment.contracts import HarmonizedData
           from logging_employment.validate.regimes import REGIME_SPECS, select_targets

  -        monthly = HarmonizedData.load(Path("data/staged")).qcew_monthly
  +        monthly = HarmonizedData.load(Path(sys.argv[1])).qcew_monthly
           cfg = load_config(Path("config.yaml"))
           ...
           """)
       digests = {
           subprocess.run(
  -            [sys.executable, "-c", script], capture_output=True, text=True, check=True
  +            [sys.executable, "-c", script, str(STAGED)],
  +            capture_output=True,
  +            text=True,
  +            check=True,
           ).stdout.strip()
           for _ in range(2)
       }

Verified out-of-band (the test itself is skipped here): I ast-parsed the script string out of the
edited file, `compile()`d it, and ran it with a bogus path. Child died at exactly the right place:
  FileNotFoundError: /tmp/not-a-real-staged-dir/qcew_monthly.parquet is missing; run `logging-estimates build-harmonized` first
which proves the `import sys` line, the argv[1] plumbing and the script's syntax/imports.

- [ ] **Step 4: Verify — arithmetic, not "0 failed"**

```bash
mv data data.bak && uv run pytest -q ; mv data.bak data
```
Expected: `0 failed`, `1286 passed` (unchanged), `70 skipped` (28 + 42). If passed dropped below 1286, a blanket `pytestmark` swallowed one of the five mixed-module tests.

Then with `data/` present:
```bash
uv run pytest -q
```
Expected: `1356 passed` — the guard is inert when the data is there.

- [ ] **Step 5: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add tests/
git commit -m "test: skip the staged-data tests when data/staged is absent"
```


---

### Task 3: Accept Appendix A's inactive sources

**Implements:** R-S5P-6

**Files:**
- Modify: `src/logging_employment/config.py`
- Modify: `tests/unit/test_config.py`
- Modify: `config.yaml (header comment)`

**Interfaces:**
- Consumes: nothing.
- Produces: `SourcesConfig` accepting the seven inactive sources with `enabled: false`. No new `Config` field reaches `resolved_dict`, so `run_id` is unchanged.

**Scope, and the corrected arithmetic.** Appendix A's fence gives exactly 11 validation errors. This task fixes the **7** `sources.*` extras only. It leaves **4**: the 3 `Field required` (`baselines`, `disclosure.narrow_interval_absolute_width`, `disclosure.narrow_interval_relative_width`) — which are missing FROM the spec and cannot be fixed without inventing defaults — plus the `model` extra, which is Stage 5's own block and MUST NOT be added here (it would re-id every run directory).

> The spec originally said "8 of 11 ... leaving 3". That was internally inconsistent: `model` is one of the 11 and is out of scope, so it cannot be among those removed. Corrected in `bbd9348`; the verified post-change count is 4.

- [ ] **Step 1: Write the failing test**

Added to /Users/lowell/Projects/impute-suppressed-stats/.claude/worktrees/wf_c524c67f-109-4/tests/unit/test_config.py (new imports: `re`, `typing.Any`, `yaml`, `logging_employment.config.Config`, `logging_employment.runs.run_id`; new module constants `REPO_ROOT`, `SPEC`, `INACTIVE_SOURCES`). Exact verified source:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "specs" / "logging-employment-spec.md"

# Appendix A's seven declared-inactive source entries, in the order the spec lists them.
INACTIVE_SOURCES = ("tpo", "fia", "ces", "susb", "bds", "nonemployer", "bea")


def appendix_a_fence() -> dict[str, Any]:
    """Appendix A's example configuration, parsed out of the spec file itself.

    Read rather than retyped, for `classification.classification_memo`'s reason: a literal is a
    second source of truth that drifts silently, and the whole point of this fixture is to witness
    what the SPEC says, not what a test author copied. Anchored at the `## Appendix A` heading and
    taking the first fence under it, so a fenced block added earlier in the file cannot stand in.
    """
    lines = SPEC.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"##\s+Appendix A\b", line)), None)
    assert start is not None, "the spec has no `## Appendix A` heading"
    opened: int | None = None
    for i in range(start + 1, len(lines)):
        if not lines[i].startswith("```"):
            continue
        if opened is None:
            opened = i
        else:
            return yaml.safe_load("\n".join(lines[opened + 1 : i]))
    raise AssertionError("Appendix A carries no closed fenced block")


def _appendix_a_made_loadable() -> dict[str, Any]:
    """Appendix A's fence minus `model:`, plus the three keys the spec never states.

    Patched HERE and not in `config.py`, which is the whole point of the previous test: a default
    for `narrow_interval_absolute_width` would turn a governance threshold §21 explicitly defers
    to its owner into a silent constant, and a `model:` field would re-identify every run
    directory for a stage that does not exist yet. `baselines: {}` is enough because every
    `BaselinesConfig` field carries a default -- the block is required only because `Config`
    declares no default for it.
    """
    fence = appendix_a_fence()
    fence.pop("model")
    fence["baselines"] = {}
    fence["disclosure"] = {
        **fence["disclosure"],
        "narrow_interval_absolute_width": 10,
        "narrow_interval_relative_width": 0.25,
    }
    return fence


def _error_locations(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Every `(dotted location, error type)` `Config` reports for `payload`, sorted."""
    with pytest.raises(ValidationError) as caught:
        Config.model_validate(payload)
    return sorted((".".join(str(p) for p in e["loc"]), e["type"]) for e in caught.value.errors())


def test_the_spec_fence_is_short_only_the_keys_the_spec_never_states() -> None:
    """Appendix A's own fence must load but for keys no code can supply.

    Before Appendix A's seven `enabled: false` sources were declared on `SourcesConfig`, this
    fence produced ELEVEN errors: those seven, `model`, and the three below. The seven were the
    only ones code could fix. What is left is a spec gap in both directions and is asserted here
    rather than papered over:

    * `model:` is Stage 5's block and this package has no field for it. Adding one would put a
      key in `resolved_dict` and re-identify every run directory in `runs/`, so the first
      assertion pins that it is still rejected and the second, after popping it, pins that no
      other extra survives.
    * `baselines:` and the two `disclosure:` widths have no values ANYWHERE in the spec --
      `BaselinesConfig` and §21's "Disclosure thresholds" row are this package's originations.
      Defaulting them so the fence loads clean would invent policy the spec declines to state,
      and would delete the evidence that it declines to.
    """
    fence = appendix_a_fence()
    assert ("model", "extra_forbidden") in _error_locations(fence)

    fence.pop("model")
    assert _error_locations(fence) == [
        ("baselines", "missing"),
        ("disclosure.narrow_interval_absolute_width", "missing"),
        ("disclosure.narrow_interval_relative_width", "missing"),
    ]


def test_the_spec_fence_declares_seven_inactive_sources_and_all_seven_load() -> None:
    """The seven the spec lists are the seven the code accepts, and each is disabled as read."""
    sources = appendix_a_fence()["sources"]
    assert sorted(sources) == sorted(("qcew", "qcew_size", "cbp", *INACTIVE_SOURCES))
    assert all(sources[name] == {"enabled": False} for name in INACTIVE_SOURCES)

    cfg = Config.model_validate(_appendix_a_made_loadable())
    assert all(getattr(cfg.sources, name).enabled is False for name in INACTIVE_SOURCES)
    assert cfg.sources.qcew.release_status == "final"


def test_an_inactive_source_may_not_be_enabled(tmp_path: Path) -> None:
    """`enabled: true` on a source with no ingest module is refused at load, not at `fetch`."""
    doctored = APPENDIX_A_AS_THE_CODE_REQUIRES.replace(
        "sources:\n", "sources:\n  tpo:\n    enabled: true\n"
    )
    with pytest.raises(ValidationError, match="Input should be False"):
        load_config(_write(tmp_path, doctored))


def test_a_misspelled_source_name_is_still_rejected(tmp_path: Path) -> None:
    """Declaring the seven as fields must not become `extra="allow"` for source names."""
    doctored = APPENDIX_A_AS_THE_CODE_REQUIRES.replace(
        "sources:\n", "sources:\n  qcew_sise:\n    enabled: false\n"
    )
    with pytest.raises(ValidationError, match="qcew_sise"):
        load_config(_write(tmp_path, doctored))


def test_an_inactive_source_reaches_neither_the_resolved_config_nor_the_run_id(
    tmp_path: Path,
) -> None:
    """Declaring the seven must not move a run id (`runs.py`, and `ValidationConfig`'s warning).

    `runs.run_id` hashes `resolved_dict`, so any key that reaches the dump renames every existing
    `runs/<id>/`. A source that is `enabled: false` contributes no bytes to any stage, so its
    entry is `exclude=True` and the two configs below -- one carrying all seven, one carrying
    none -- must resolve and identify identically.
    """
    without = load_config(_write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES))
    declared = "sources:\n" + "".join(f"  {n}:\n    enabled: false\n" for n in INACTIVE_SOURCES)
    with_seven = load_config(
        _write(tmp_path, APPENDIX_A_AS_THE_CODE_REQUIRES.replace("sources:\n", declared))
    )
    assert with_seven.sources.bea is not None
    assert without.sources.bea is None
    assert sorted(resolved_dict(with_seven)["sources"]) == ["cbp", "qcew", "qcew_size"]
    assert resolved_dict(with_seven) == resolved_dict(without)
    assert run_id(with_seven, {}) == run_id(without, {})


def test_the_shipped_configs_run_id_is_unmoved_by_the_inactive_source_fields() -> None:
    """A literal pin on the id `config.yaml` derives, because the cost of moving it is external.

    `runs/f03023ac9f3a` is Stage 4's acceptance artifact and is derived from this config plus the
    staged inputs. Those inputs are gitignored, so the digest map here is empty and the pinned
    value is not that directory's name -- it is a canary over the same `resolved_dict` input,
    which is the half of the id a config change can move. Measured before this change and
    unchanged by it.
    """
    assert run_id(load_config(REPO_ROOT / "config.yaml"), {}) == "39d1d0859838"
```

Also renamed (mechanical): the module constant `APPENDIX_A` -> `APPENDIX_A_AS_THE_CODE_REQUIRES` (13 sites) with a header comment naming the four ways it differs from the real fence, and `test_appendix_a_config_parses` -> `test_the_code_shaped_config_parses` with a docstring saying why.

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/unit/test_config.py -q -k appendix
```
Expected: FAIL — 11 errors reported where 4 were asserted.

- [ ] **Step 3: Implement**

Exact verified diff of /Users/lowell/Projects/impute-suppressed-stats/.claude/worktrees/wf_c524c67f-109-4/src/logging_employment/config.py:

```diff
@@ -9,7 +9,7 @@ from typing import Literal
 
 import yaml
 from dotenv import dotenv_values
-from pydantic import BaseModel, ConfigDict, field_validator, model_validator
+from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
 
 _MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
 
@@ -85,12 +85,52 @@ class CbpSourceConfig(_Strict):
     fail_on_unknown_disclosure_regime: bool
 
 
+class InactiveSourceConfig(_Strict):
+    """An Appendix A source entry that carries nothing but `enabled: false`.
+
+    `enabled` is `Literal[False]`, not `bool`: this package has no ingest module, no registry row
+    (`registry/sources.yaml` lists three) and no `fetch --source` branch for any of these seven, so
+    `enabled: true` names a source nothing can acquire. Accepting it would defer the failure to a
+    `fetch` that reports an unknown source; refusing it at load is §18.3's fail-closed rule, and
+    `validate-config` is where the operator is already looking.
+    """
+
+    enabled: Literal[False] = False
+
+
 class SourcesConfig(_Strict):
-    """The three sources Stage 1 ingests. Later stages add their own keys."""
+    """The three sources Stage 1 ingests, plus Appendix A's seven declared-inactive entries.
+
+    Appendix A's `sources:` block lists ten. Seven of them -- `tpo`, `fia`, `ces`, `susb`, `bds`,
+    `nonemployer`, `bea` -- carry `enabled: false` and belong to Stages 4-8; before they were
+    declared here, `extra="forbid"` made the spec's own reference configuration unloadable, which
+    is `R-S5P-6`'s defect (`specs/stage5-preconditions.md`) and what this fixes. `R-S5P-6` scopes
+    only these seven: Appendix A's `model:` block and its three MISSING keys are left failing on
+    purpose, and `tests/unit/test_config.py` asserts exactly what still fails.
+
+    They are declared as fields rather than admitted by `extra="allow"`
+    so that a MISSPELLED source name is still a load-time error and so that `enabled: true` on an
+    unimplemented source is refused (`InactiveSourceConfig`); `extra="allow"` would have accepted
+    both silently.
+
+    EVERY ONE OF THE SEVEN IS `exclude=True`, so none of them reaches `resolved_dict` and none can
+    move a run id. That is deliberate and load-bearing, not a serialization detail: `runs.run_id`
+    hashes `resolved_dict`, and a source that is `enabled: false` contributes no bytes to any
+    stage -- nothing outside this module reads these fields. Emitting them would re-identify every
+    run directory on disk (orphaning `runs/f03023ac9f3a`) in exchange for a key that cannot change
+    what a run computes. It is the same omitted-not-null rule `runs.run_id` applies to `overrides`.
+    """
 
     qcew: QcewSourceConfig
     qcew_size: QcewSizeSourceConfig
     cbp: CbpSourceConfig
+    tpo: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    fia: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    ces: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    susb: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    bds: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    nonemployer: InactiveSourceConfig | None = Field(default=None, exclude=True)
+    bea: InactiveSourceConfig | None = Field(default=None, exclude=True)
 
 
 class ConstraintsConfig(_Strict):
```

APPROACH CHOSEN — one shared `InactiveSourceConfig` model, seven `exclude=True` optional fields. Why not the alternatives, all considered:
* `extra="allow"` on `SourcesConfig` — rejected. It would accept a misspelled source name (`qcew_sise:`) silently and would not check `enabled` at all. Measured after the change: `qcew_sise` still raises `extra_forbidden`, and a typo INSIDE an active source (`cbp.api_key_envv`) still raises. Active-source strictness is untouched.
* Seven fields with a NON-excluded default — rejected. `resolved_dict` is `model_dump(mode="json")`, which emits defaults, so `"tpo": null` would enter the payload `runs.run_id` hashes and rename every `runs/<id>/`.
* `resolved_dict(..., exclude_none=True)` — rejected. It changes dump semantics for the whole `Config` tree to fix one block, and would silently drop any future field intentionally set to null.
* A `mode="before"` validator that pops the seven — rejected as less explicit; `exclude=True` keeps the values typed and reachable on the model while keeping them out of every dump.

RUN_ID VERDICT — PLAINLY: `resolved_dict` for the CURRENT `config.yaml` is byte-identical. Measured before the change: sha256 `cd32de5ed6422422c892098822d04316ab685b6031e3b2e595bac186a66e7262`, `run_id(cfg, {})` = `39d1d0859838`, `sources` block `{"cbp": {...}, "qcew": {...}, "qcew_size": {...}}`. Measured after (and again after the `config.yaml` comment edit): identical on all three. `runs/f03023ac9f3a` is not orphaned. Confirmed `exclude=True` cannot leak elsewhere: `grep -rn "model_dump\|model_dump_json" src/` shows the only Config-level dump is `config.py::resolved_dict`; the other hit is `registry/loader.py` dumping `SourceRegistryRow`. Also confirmed the seven fields are read nowhere outside `config.py` (`cfg.sources` is read only at `build.py:179`, `build.py:209`, `fetching.py:129`, `fetching.py:159`, all on qcew/cbp).

- [ ] **Step 4: Verify, including that `run_id` did not move**

```bash
uv run pytest tests/unit/test_config.py tests/unit/test_runs.py -q
```
Expected: PASS.

```bash
uv run python -c "
from pathlib import Path
from logging_employment.config import load_config, resolved_dict
print('model' in resolved_dict(load_config(Path('config.yaml'))))
"
```
Expected: `False` — no new key reaches the resolved config, so `runs/f03023ac9f3a` keeps its id.

- [ ] **Step 5: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add src/logging_employment/config.py tests/unit/test_config.py config.yaml
git commit -m "fix(config): accept Appendix A's inactive sources with enabled: false"
```


---

### Task 4: Enforce INV-002's per-cell bounds on the baseline path

**Implements:** R-S5P-3

**Files:**
- Modify: `src/logging_employment/errors.py`
- Modify: `src/logging_employment/baselines/runner.py`
- Modify: `src/logging_employment/cli.py`
- Create: `tests/unit/test_baselines_bounds.py`
- Modify: `tests/integration/test_constraint_cli.py`

**Interfaces:**
- Consumes: `Bounds` from `reconcile/scaling.py` (frozen dataclass; `lower: dict[str,float]`, `upper: dict[str,float|None]`, `upper_of()` reads `None` as `math.inf`).
- Produces: `errors.BoundViolationError` and `baselines.runner.state_total_bounds(pl.DataFrame) -> Bounds`.

**Behaviour-neutral on D1, and the test must say so.** All 1,227 suppressed state cells are `unbounded` with a null `selected_upper`, so nothing can violate today. The value is the first cell that *can* — a retired anchor, a Stage 6 state x size cell, a size-arm mask. A test that only shows "still green" cannot distinguish a working check from one keyed so it matches nothing; that is the silent-no-op failure mode, and Step 4's tamper test is what rules it out.

**Keying is the subtle part.** `Bounds` here is keyed by the seven-field `cell_id`, NOT by `state_fips`. `scale_into_bounds` keys its `Bounds` by whatever `anchor.missing_cells` carries — a bare state — but that object is one month's feasible set, while `run_baselines` walks all 96 months in one call. State `04` has one interval in January and another in February; a state-keyed mapping would apply one month's bound to all 96 and no lookup would ever fail.

- [ ] **Step 1: Write the failing tests**

NEW FILE: tests/unit/test_baselines_bounds.py (7 tests, no data/ needed)

"""INV-002's per-cell half on the baseline production path (R-S5P-3).

The adding-up half has been enforced since Stage 3. The bounds half was not: nothing in
`baselines/` read `deterministic_bounds`, so an estimate above a solved upper bound shipped as
`anchored_and_reconciled`. On D1 that is harmless -- `selected_upper` is null on 1,227 of 1,241
suppressed state cells, so no bound can bind -- and the two halves of this module are exactly
that pair: the first cell that CAN violate must halt the run, and the D1 shape must be
bit-for-bit unchanged.

No `data/` is touched. The runner is driven on `harmonized_toy`, whose 2023-01 missing set is the
single state '04' against a residual of 50, so the allocated estimate is 50.0 for every estimator
and one finite upper of 10.0 is enough to fire.
"""

from __future__ import annotations

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from logging_employment.baselines.runner import (
    assert_within_bounds,
    run_baselines,
    state_total_bounds,
)
from logging_employment.contracts import DETERMINISTIC_BOUNDS_SCHEMA
from logging_employment.errors import BoundViolationError, ConceptViolationError
from logging_employment.reconcile.scaling import Bounds

TOY_CELL = "state_total|04|2023-01|5|113310|NAICS 2022|ALL"


def _bounds_row(cell_id: str, lower: float | None, upper: float | None) -> dict[str, object]:
    """One `deterministic_bounds` row, every schema column filled.

    Written out rather than taken from a factory because the three columns this test cares about
    -- `cell_id`, `selected_lower`, `selected_upper` -- are the ones a factory would default.
    """
    return {
        "cell_id": cell_id,
        "component_id": "c000000",
        "rank": 1,
        "nullity": 1,
        "lp_lower": lower,
        "lp_upper": upper,
        "milp_lower": None,
        "milp_upper": None,
        "selected_lower": lower,
        "selected_upper": upper,
        "bound_status": "unbounded" if upper is None else "partially_identified",
        "exactly_identified": False,
        "integer_exactly_identified": False,
        "solver_status": "optimal",
        "solver_tolerance": 1e-7,
        "constraint_set_hash": "h",
    }


def _cell_ids(results: pl.DataFrame) -> list[str]:
    """Every `cell_id` the runner produced, read off its own output rather than recomputed.

    Recomputing the seven-field id here would re-derive it from the same `cell_id()` call the
    runner uses, so a keying bug would agree with itself and the bound would be checked against a
    cell nothing ever allocates.
    """
    return sorted(set(results["cell_id"].to_list()))


def _january_cell(results: pl.DataFrame) -> str:
    """The `cell_id` of the one suppressed cell in 2023-01: state '04', residual 50."""
    january = results.filter(
        (pl.col("reference_month") == "2023-01") & (pl.col("state_fips") == "04")
    )
    return str(january["cell_id"].to_list()[0])


def test_an_estimate_above_its_solved_upper_bound_halts_the_run(
    harmonized_toy, appendix_a_config
) -> None:
    """INV-002 admits no per-month refusal, so this raises rather than writing a decline row."""
    unchecked, _ = run_baselines(harmonized_toy, appendix_a_config)
    target = _january_cell(unchecked)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper={cell: (10.0 if cell == target else None) for cell in _cell_ids(unchecked)},
    )
    with pytest.raises(BoundViolationError) as excinfo:
        run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    message = str(excinfo.value)
    assert target in message
    assert "estimate=50.0" in message
    assert "[0.0, 10.0]" in message


def test_the_d1_shape_of_every_upper_null_changes_nothing(
    harmonized_toy, appendix_a_config
) -> None:
    """1,227 of 1,241 suppressed state cells are `unbounded`, so the gate must be a no-op there."""
    unchecked, unchecked_audit = run_baselines(harmonized_toy, appendix_a_config)
    bounds = Bounds(
        lower=dict.fromkeys(_cell_ids(unchecked), 0.0),
        upper=dict.fromkeys(_cell_ids(unchecked), None),
    )
    checked, checked_audit = run_baselines(harmonized_toy, appendix_a_config, bounds=bounds)
    assert_frame_equal(checked, unchecked)
    assert_frame_equal(checked_audit, unchecked_audit)


def test_a_bounds_mapping_keyed_by_state_is_refused_rather_than_ignored(
    harmonized_toy, appendix_a_config
) -> None:
    """`upper_of` reads an absent key as `+inf`, so miskeying would make the gate a silent no-op.

    `scale_into_bounds` keys its `Bounds` by `anchor.missing_cells`, which on this path is a bare
    state -- so this is the mistake the type invites, not a hypothetical one.
    """
    with pytest.raises(ConceptViolationError, match="no deterministic bound"):
        run_baselines(
            harmonized_toy,
            appendix_a_config,
            bounds=Bounds(lower={"04": 0.0, "06": 0.0}, upper={"04": None, "06": None}),
        )


def test_the_integer_release_is_checked_too_not_only_the_float() -> None:
    """§12.6's largest-remainder rounding can move a value across a bound the float honoured."""
    bounds = Bounds(lower={TOY_CELL: 0.0}, upper={TOY_CELL: 10.4})
    cell_ids = {"04": TOY_CELL}
    assert_within_bounds(
        {"04": 10.4},
        bounds,
        cell_ids=cell_ids,
        estimator_id="equal_residual",
        reference_month="2023-01",
        tolerance=1e-9,
        quantity="estimate",
    )
    with pytest.raises(BoundViolationError, match="estimate_integer=11.0"):
        assert_within_bounds(
            {"04": 11.0},
            bounds,
            cell_ids=cell_ids,
            estimator_id="equal_residual",
            reference_month="2023-01",
            tolerance=1e-9,
            quantity="estimate_integer",
        )


def test_the_loader_keeps_state_total_cells_and_reads_a_null_upper_as_unbounded() -> None:
    """A national size row in the same table is not a state-total bound and must not be keyed in."""
    other = "state_total|06|2023-02|5|113310|NAICS 2022|ALL"
    frame = pl.DataFrame(
        [
            _bounds_row(TOY_CELL, 0.0, None),
            _bounds_row(other, 3.0, 12.0),
            _bounds_row("national_size|US|2023-01|5|113310|NAICS 2022|1", 1.0, 2.0),
        ],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    bounds = state_total_bounds(frame)
    assert sorted(bounds.lower) == [TOY_CELL, other]
    assert bounds.upper_of(TOY_CELL) == float("inf")
    assert bounds.upper_of(other) == 12.0
    assert bounds.lower[other] == 3.0


def test_the_loader_refuses_two_rows_for_one_cell() -> None:
    """`component_id`/`rank`/`nullity` mean the schema admits duplicates; D1 having one is a
    measurement. `dict(zip(...))` would keep the last row and check against an arbitrary one."""
    frame = pl.DataFrame(
        [_bounds_row(TOY_CELL, 0.0, None), _bounds_row(TOY_CELL, 0.0, 9.0)],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    with pytest.raises(ConceptViolationError, match="more than one row"):
        state_total_bounds(frame)


def test_the_loader_refuses_a_null_lower_while_accepting_a_null_upper() -> None:
    """§9.3's nonnegativity holds for every cell, so a null lower is unsolved, not unbounded."""
    frame = pl.DataFrame(
        [_bounds_row(TOY_CELL, None, None)],
        schema=DETERMINISTIC_BOUNDS_SCHEMA,
    )
    with pytest.raises(ConceptViolationError, match="null selected_lower"):
        state_total_bounds(frame)


APPENDED to tests/integration/test_baseline_cli.py (2 tests; uses the committed
tests/fixtures/baselines/ layer via `staged_repo`, no data/ needed):

def test_run_baselines_refuses_a_run_with_no_solved_bounds(staged_repo) -> None:
    """R-S5P-3 makes `solve-bounds` a precondition, rather than skipping INV-002 when it is absent.

    A check that turns itself off when its input is missing is the failure this requirement
    exists to remove: the run would ship `anchored_and_reconciled` rows with nothing having
    looked at §9's intervals, and no artifact would record that.
    """
    (staged_repo.run_dir / "deterministic_bounds.parquet").unlink()
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code != 0
    # Short tokens only: Typer boxes the message and hard-wraps the long tmp_path inside it, so
    # asserting on the full artifact path passes locally and fails under a deeper tmp directory.
    assert "solve-bounds" in result.output
    assert "INV-002" in result.output


def test_a_finite_upper_below_the_estimate_halts_the_production_path(staged_repo) -> None:
    """The wiring is not vacuous: the bounds the CLI loads really do gate the estimates.

    Every `selected_upper` this fixture solves is null, exactly as on D1 -- so the passing run
    above cannot distinguish a working check from one whose mapping is keyed wrong and matches
    nothing. Tightening ONE cell's upper below the estimate that cell already received is the
    difference. The estimate is read out of the first run rather than assumed.
    """
    assert (
        runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)]).exit_code
        == 0
    )
    results = pl.read_parquet(
        staged_repo.run_dir / "baseline_results" / "baseline_results.parquet"
    ).filter(pl.col("reconciliation_status") == "anchored_and_reconciled")
    row = results.sort(["cell_id", "estimator_id"]).to_dicts()[0]
    bounds_path = staged_repo.run_dir / "deterministic_bounds.parquet"
    bounds = pl.read_parquet(bounds_path)
    assert bounds.filter(pl.col("cell_id") == row["cell_id"]).height == 1
    bounds.with_columns(
        pl.when(pl.col("cell_id") == row["cell_id"])
        .then(pl.lit(row["estimate"] / 2.0))
        .otherwise(pl.col("selected_upper"))
        .alias("selected_upper")
    ).write_parquet(bounds_path)
    result = runner.invoke(app, ["run-baselines", "--config", str(staged_repo.config_path)])
    assert result.exit_code != 0
    assert isinstance(result.exception, BoundViolationError)
    assert row["cell_id"] in str(result.exception)

(these two also require, at the top of that file:
  import polars as pl
  from logging_employment.errors import BoundViolationError)

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/unit/test_baselines_bounds.py -q
```
Expected: FAIL — `BoundViolationError` does not exist.

- [ ] **Step 3: Implement**

EXACT VERIFIED DIFF (git diff at 0106056, worktree left dirty).

--- a/src/logging_employment/errors.py
+++ b/src/logging_employment/errors.py
@@ -114,3 +114,23 @@ class LeakageError(LoggingEmploymentError):
     this convention in `run_pseudo_suppression`'s own docstring and these two functions were the
     only places in it that violated the convention.
     """
+
+
+class BoundViolationError(LoggingEmploymentError):
+    """A released point estimate falls outside its own `deterministic_bounds` interval (INV-002).
+
+    INV-002 has two halves. The adding-up half -- every estimate sums to the anchor's residual --
+    has been enforced on the baseline path since Stage 3 by `allocate` and
+    `InfeasibleResidualError`. The per-cell half was not: §9's LP/MILP interval is a hard public
+    accounting fact, and nothing in `baselines/` read it, so an estimate above a solved upper
+    bound shipped as `anchored_and_reconciled` with no signal at all.
+
+    A RAISE, NOT A `Decline` ROW, and that is a deliberate break with the runner's other
+    post-allocation failure. `WeightDomainError` out of `allocate` becomes a
+    `reconciliation_failure` row because it is a DATA gap -- one cell with no usable input must
+    not abort ten estimators across 96 months. This is not a data gap: the bound and the estimate
+    are both this pipeline's own output, and INV-002 admits no per-month refusal. Filing it as a
+    decline would let the run ship, with a violated accounting fact recorded as an estimator's
+    considered opinion. §18.3's "fail rather than guess" governs, and R-S5P-3 says so in words:
+    "a violation MUST raise a named error from the `LoggingEmploymentError` hierarchy".
+    """

--- a/src/logging_employment/baselines/runner.py
+++ b/src/logging_employment/baselines/runner.py
@@ -29,14 +29,25 @@ any kind and gates nothing.
 from __future__ import annotations
 
-from collections.abc import Sequence
+from collections.abc import Mapping, Sequence
 
 import polars as pl
 
 from ..config import Config
 from ..constraints.cells import KIND_STATE_TOTAL, TOTAL_SIZE_CLASS, cell_id
-from ..contracts import BASELINE_RESULT_SCHEMA, HarmonizedData, assert_declared_provenance
-from ..errors import ConceptViolationError, InfeasibleResidualError, WeightDomainError
+from ..contracts import (
+    BASELINE_RESULT_SCHEMA,
+    DETERMINISTIC_BOUNDS_SCHEMA,
+    HarmonizedData,
+    assert_declared_provenance,
+    validate_frame,
+)
+from ..errors import (
+    BoundViolationError,
+    ConceptViolationError,
+    InfeasibleResidualError,
+    WeightDomainError,
+)
 from ..reconcile.allocate import allocate
@@ -45,6 +56,7 @@
 from ..reconcile.integerize import integerize
+from ..reconcile.scaling import Bounds
 from .harvest import HarvestProportional
@@ -183,12 +195,118 @@ def _cell_ids(partition, anchor) -> dict[str, str]:
     return ids
 
 
+def state_total_bounds(bounds: pl.DataFrame) -> Bounds:
+    """§7.10's `deterministic_bounds` table as the per-cell `Bounds` the runner checks against.
+
+    KEYED BY THE SEVEN-FIELD `cell_id`, NOT BY `state_fips`. `scale_into_bounds` keys its `Bounds`
+    by whatever `anchor.missing_cells` carries, which on this path is a bare state -- but that
+    object is one month's feasible set, while `run_baselines` walks the whole window in a single
+    call. State '04' has its own interval in January and another in February, so a state-keyed
+    mapping would apply one month's bound to all 96 and no lookup would fail.
+
+    ONLY `state_total` CELLS ARE KEPT. The same table carries §9's national size cells, and
+    `test_d1_acceptance` measures cells that carry no row at all, so loading it whole would mix
+    two cell kinds into one mapping and put keys in it the runner never looks up.
+
+    DUPLICATES ARE REFUSED RATHER THAN COLLAPSED. `component_id`, `rank` and `nullity` sit beside
+    `cell_id` in `DETERMINISTIC_BOUNDS_SCHEMA`, so the schema admits more than one row per cell by
+    construction; D1 having exactly one is a measurement, not a guarantee. `dict(zip(...))` would
+    silently keep whichever row sorted last and check the estimate against an arbitrary component.
+
+    A NULL `selected_lower` IS REFUSED, while a null `selected_upper` is read as unbounded above.
+    The asymmetry is §9.3's: nonnegativity is the one public fact touching every cell, so a cell
+    with no lower bound at all means the solver did not answer for it -- whereas a null upper is
+    the documented D1 state on 1,227 of 1,241 cells and `Bounds.upper_of` already reads it as
+    positive infinity.
+    """
+    validate_frame(bounds, DETERMINISTIC_BOUNDS_SCHEMA, "deterministic_bounds")
+    rows = bounds.filter(pl.col("cell_id").str.starts_with(f"{KIND_STATE_TOTAL}|"))
+    duplicated = sorted(
+        rows.group_by("cell_id").len().filter(pl.col("len") > 1)["cell_id"].to_list()
+    )
+    if duplicated:
+        raise ConceptViolationError(
+            f"deterministic_bounds carries more than one row for {duplicated[:5]} "
+            f"({len(duplicated)} cell(s) in total); a per-cell bound must be unique before it can "
+            "gate an estimate"
+        )
+    null_lower = sorted(rows.filter(pl.col("selected_lower").is_null())["cell_id"].to_list())
+    if null_lower:
+        raise ConceptViolationError(
+            f"deterministic_bounds has a null selected_lower for {null_lower[:5]} "
+            f"({len(null_lower)} cell(s) in total); §9.3's nonnegativity holds for every cell, so "
+            "a missing lower bound is an unsolved cell rather than an unbounded one"
+        )
+    lower = {
+        str(row["cell_id"]): float(row["selected_lower"]) for row in rows.iter_rows(named=True)
+    }
+    upper: dict[str, float | None] = {
+        str(row["cell_id"]): (
+            None if row["selected_upper"] is None else float(row["selected_upper"])
+        )
+        for row in rows.iter_rows(named=True)
+    }
+    return Bounds(lower=lower, upper=upper)
+
+
+def assert_within_bounds(
+    values: Mapping[str, float],
+    bounds: Bounds,
+    *,
+    cell_ids: Mapping[str, str],
+    estimator_id: str,
+    reference_month: str,
+    tolerance: float,
+    quantity: str,
+) -> None:
+    """INV-002's per-cell half: refuse a released value outside its own solved `[L, U]`.
+
+    COVERAGE IS CHECKED BEFORE THE COMPARISON, and that check is the load-bearing half. `upper_of`
+    reads an absent key as `None` and therefore as `+inf`, so a `Bounds` keyed the wrong way --
+    by `state_fips`, which is exactly the convention `scale_into_bounds` uses for this same type
+    -- would pass every cell and make this whole gate a silent no-op. Indexing `bounds.lower`
+    (which has no `_of` accessor, matching `scale_into_bounds`'s own direct index) turns that into
+    a named refusal. An uncovered cell is a `ConceptViolationError`, not a `BoundViolationError`:
+    nothing was violated, the bound is simply missing, and §18.3's fail-closed rule covers both.
+
+    `tolerance` is the caller's, and production passes `reconciliation.tolerance` rather than
+    `constraints.feasibility_tolerance`. `ReconciliationConfig`'s docstring gives the reason: "a
+    bound solved to 1e-7 and a residual reconciled to 1e-9 are different obligations", and reusing
+    the solver's number here would let a solver tuning change move what counts as a violation.
+
+    `quantity` names which released number is being checked, because both are: §12.6's integers
+    are released alongside the floats, and largest-remainder rounding can push a value that sat
+    exactly on an upper bound past it. Without the label the message cannot say which one moved.
+    """
+    uncovered = sorted(cell for cell in values if cell_ids[cell] not in bounds.lower)
+    if uncovered:
+        raise ConceptViolationError(
+            f"{reference_month}: {estimator_id} has no deterministic bound for "
+            f"{[cell_ids[cell] for cell in uncovered]}; INV-002 cannot be checked against a "
+            "bound that is absent, and an absent bound is not an unbounded one"
+        )
+    violations = []
+    for cell in sorted(values):
+        identifier = cell_ids[cell]
+        value = float(values[cell])
+        low = bounds.lower[identifier]
+        high = bounds.upper_of(identifier)
+        if value < low - tolerance or value > high + tolerance:
+            violations.append(f"{identifier} {quantity}={value} outside [{low}, {high}]")
+    if violations:
+        raise BoundViolationError(
+            f"{reference_month}: {estimator_id} violates INV-002's per-cell bounds at "
+            f"{len(violations)} cell(s): {violations}"
+        )
+
+
 def run_baselines(
     data: HarmonizedData,
     config: Config,
     *,
     constraint_set_hash: str | None = None,
     estimators: Sequence[Estimator] = REGISTRY,
+    bounds: Bounds | None = None,
 ) -> tuple[pl.DataFrame, pl.DataFrame]:
@@ -200,6 +318,16 @@   (docstring addition)
+
+    `bounds` turns on INV-002's per-cell half, and defaults to `None` -- no bound known, no check
+    -- for two different reasons that must not be conflated. For a unit test it is convenience:
+    a toy `HarmonizedData` has no Stage 2 run behind it, exactly as with `constraint_set_hash`.
+    For `validate/harness.py`'s caller it is CORRECTNESS: `deterministic_bounds.parquet` still
+    carries the published value for a cell the pseudo-suppression mask hides, so its intervals
+    were solved from a system containing the truth the harness is scoring against. Handing them to
+    a masked run would leak that truth into the estimates through the clip, which is §13.4's
+    `LeakageError` territory. The production caller is `cli.py`; the harness must keep passing
+    nothing until Stage 6 re-solves bounds under the mask.
     """
@@ -268,6 +396,16 @@   (immediately after `allocated = allocate(anchor, outcome)`'s except block)
                 continue
+            if bounds is not None:
+                assert_within_bounds(
+                    allocated,
+                    bounds,
+                    cell_ids=ids,
+                    estimator_id=estimator.estimator_id,
+                    reference_month=month,
+                    tolerance=config.reconciliation.tolerance,
+                    quantity="estimate",
+                )
             # The margin the integers must honour is the anchor's residual -- the published
@@ -288,6 +426,20 @@   (immediately after the InfeasibleResidualError sum check)
                 )
+            if bounds is not None and config.reconciliation.integerize_release:
+                # §12.6's integers are released too, and largest-remainder rounding moves a value
+                # by up to one whole employee -- so a float that sat exactly on an upper bound can
+                # cross it. Checking only the float would leave the number actually published
+                # unchecked, which is the half INV-002 names.
+                assert_within_bounds(
+                    {cell: float(value) for cell, value in integers.items() if value is not None},
+                    bounds,
+                    cell_ids=ids,
+                    estimator_id=estimator.estimator_id,
+                    reference_month=month,
+                    tolerance=config.reconciliation.tolerance,
+                    quantity="estimate_integer",
+                )
             for cell in anchor.missing_cells:

--- a/src/logging_employment/cli.py   (run_baselines_command)
+++ b/src/logging_employment/cli.py
@@ -231,6 +231,7 @@
         run_baselines,
+        state_total_bounds,
     )
@@ -250,8 +251,22 @@
             "inputs currently in the staged directory. Run `build-constraints` first"
         )
+    # A SECOND PRECONDITION, new with R-S5P-3. INV-002's per-cell half checks every estimate
+    # against §9's solved interval, so `solve-bounds` joins `build-constraints` as a gate rather
+    # than the check being skipped when its input happens to be absent. A silently-skipped
+    # invariant is the failure this requirement exists to remove, and the documented pipeline
+    # order already runs `solve-bounds` before `run-baselines`.
+    bounds_path = run / "deterministic_bounds.parquet"
+    if not bounds_path.exists():
+        raise typer.BadParameter(
+            f"{bounds_path} is missing: every baseline estimate is checked against its per-cell "
+            "deterministic bounds (INV-002), and this run has none. Run `solve-bounds` first"
+        )
     results, audit = run_baselines(
-        data, cfg, constraint_set_hash=json.loads(manifest_path.read_text())["constraint_set_hash"]
+        data,
+        cfg,
+        constraint_set_hash=json.loads(manifest_path.read_text())["constraint_set_hash"],
+        bounds=state_total_bounds(pl.read_parquet(bounds_path)),
     )

--- a/tests/integration/conftest.py   (staged_repo now also runs solve-bounds)
+++ b/tests/integration/conftest.py
@@ module docstring
-`tests/fixtures/baselines/`, and a completed `build-constraints` run so `schema_manifest.json`
-exists — `run-baselines` gates on that file the same way `solve-bounds` does.
+`tests/fixtures/baselines/`, and completed `build-constraints` and `solve-bounds` runs, so both
+`schema_manifest.json` and `deterministic_bounds.parquet` exist — `run-baselines` gates on both.
@@ -56,6 +56,11 @@
     result = CliRunner().invoke(app, ["build-constraints", "--config", str(config_path)])
     assert result.exit_code == 0, result.output
+    # `solve-bounds` runs here too, as of R-S5P-3: `run-baselines` now checks every estimate
+    # against `deterministic_bounds.parquet` (INV-002's per-cell half) and gates on the file.
+    # Measured on this fixture: 0.06 s, so the chain stays cheap enough to pay per test.
+    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(config_path)])
+    assert result.exit_code == 0, result.output
     cfg = load_config(config_path)


=== ANSWER TO ITEM 4: where do bounds come from at runtime ===

Signature chain, read: `run_baselines(data, config, *, constraint_set_hash=None,
estimators=REGISTRY)` -> `allocate(anchor, outcome)` -> `integerize(allocated, total=...)`.
Nothing in that chain has ever seen a bound. Two callers exist: `cli.py:253` and
`validate/harness.py:161`.

YES, IT NEEDS A NEW PARAMETER THREADED FROM cli.py. Smallest change that works, verified:

1. `run_baselines` gains ONE keyword-only param, `bounds: Bounds | None = None`. Zero cost to
   both existing callers (both keep working untouched).
2. `state_total_bounds(pl.DataFrame) -> Bounds` converts the persisted §7.10 table into the
   `reconcile.scaling.Bounds` the check consumes. It must be keyed by the seven-field `cell_id`,
   NOT by `state_fips`: `scale_into_bounds` keys `Bounds` by `anchor.missing_cells` (bare state),
   but that object is ONE month's feasible set while `run_baselines` walks all 96 months in one
   call, so a state key would apply January's bound to December.
3. `cli.py::run_baselines_command` gains a second precondition on
   `runs/<id>/deterministic_bounds.parquet`, matching the `typer.BadParameter`-naming-the-missing-path
   treatment `solve_bounds_command` gives `schema_manifest.json`.

COST OF (3), measured, not estimated:
- `solve-bounds` becomes a HARD precondition of `run-baselines`. That is consistent with the
  documented order (build-constraints -> solve-bounds -> run-baselines) and with CLAUDE.md's
  "each gates on the previous one's artifact and refuses with the missing path".
- Test cost: `tests/integration/conftest.py::staged_repo` must run `solve-bounds` too. Measured
  on the committed fixture: 0.06 s per test, 9 tests -> ~0.5 s. `test_baseline_cli.py` went from
  16.9 s to 22.8 s total including the 2 new tests. No other fixture or module is affected
  (`test_constraint_cli.py` uses its own `workspace` fixture; `tests/unit/test_runs.py`'s
  "run-baselines" hit is prose in a docstring, line 34).
- `validate/harness.py:161` MUST keep passing nothing. `deterministic_bounds.parquet` still
  carries the published value for a masked cell (see `validate/harness.py:230` and
  `validate/CLAUDE.md:131`), so its intervals were solved from a system containing the truth the
  harness scores against; clipping to them would leak it. That is why the default is `None` and
  why the docstring says so.

- [ ] **Step 4: Verify, including the tamper test**

```bash
uv run pytest tests/unit/test_baselines_bounds.py tests/integration/test_baseline_cli.py -v -p no:randomly

(run from /Users/lowell/Projects/impute-suppressed-stats/.claude/worktrees/wf_c524c67f-109-2)
```
Expected: PASS. The tamper test runs the real CLI, halves one `selected_upper` in the run dir's `deterministic_bounds.parquet` below an estimate that cell already received, and asserts the next invocation raises `BoundViolationError` naming that `cell_id`. It needs no `data/` — `tests/integration/conftest.py::staged_repo` builds a tmp repo from committed fixtures.

- [ ] **Step 5: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add src/logging_employment tests/
git commit -m "fix(baselines): raise BoundViolationError when an estimate leaves its bounds"
```


---

### Task 5: Make `fetch` fail closed

**Implements:** R-S5P-4

**Files:**
- Modify: `src/logging_employment/fetching.py`
- Modify: `src/logging_employment/errors.py`
- Modify: `tests/unit/test_fetching.py`

**Interfaces:**
- Consumes: `ingest/base.HttpFetcher`, which deliberately RETURNS non-200 responses so the caller classifies on content, not status. Do not change that contract.
- Produces: a named fetch failure error and a declared-absence mechanism.

**The four `continue` sites are not equivalent — this is the finding that changes the task.**

| Site | Skips | Checks | Consequence |
|---|---|---|---|
| `fetching.py:119` (qcew) | one (year, quarter) | status **and** empty body | silent drop only |
| `:140` (qcew_size) | one year's Q1 by-size zip | **status only** | a 200 with a whitespace/error body is stored as a "zip" and recorded as a valid snapshot row — **latent data corruption**, not just a drop |
| `:162` (cbp variables) | the whole CBP year, before metadata is stored | status only | `build.predicate_from_stored_metadata` later finds nothing for that year |
| `:170` (cbp data) | the year, **after** its variables metadata was written | status only | orphan metadata file with no data snapshot |

`:140` is the one to lead with in review: it is the only site where the current behaviour can put a bad object in the content-addressed store.

**CBP 2024 must keep working.** It is genuinely absent (404, vintage not published). The declaration mechanism is a real design choice — see the verified notes below for the options and their costs. Do **not** add a `Config` pydantic field without accounting for the run-id re-hash.

- [ ] **Step 1: Write the failing test**

Appended to tests/unit/test_fetching.py (imports added at top: `yaml`, `from typer.testing import CliRunner`, `from logging_employment.cli import app`, `from logging_employment.errors import SourceFetchError`).

```python
# --- R-S5P-4: a dropped quarter is a halt, not a narrower window --------------------------------

SLICE = (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes()


def _mock_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    """Route every `httpx.Client` this process opens through `handler`.

    `fetch_source` builds its own `HttpFetcher`, so the `fetcher._client = httpx.Client(
    transport=...)` idiom of `tests/unit/test_qcew_routes.py::_fetcher` has no instance to reach
    in; this is the same `MockTransport`, injected one constructor higher. Patched on `httpx`
    rather than on `HttpFetcher` so `__post_init__`'s contact-address guard and the D3 User-Agent
    still run exactly as in production -- and unlike the `_serve` helper above, which replaces
    `httpx.Client.get` wholesale, the request actually travels through httpx's own request
    building, so a handler can key on the URL the code really asked for.
    """
    real = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real(**kw, transport=httpx.MockTransport(handler))
    )
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "who@example.invalid")


def _qcew_handler(failing: tuple[int, int], status: int = 500, body: bytes = b"upstream failure"):
    """Serve the slice fixture for every year-quarter except one, which answers `status`."""

    def handler(request: httpx.Request) -> httpx.Response:
        year, quarter = (int(p) for p in str(request.url).split("/api/")[1].split("/")[:2])
        if (year, quarter) == failing:
            return httpx.Response(status, content=body)
        return httpx.Response(200, content=SLICE)

    return handler


def test_a_failed_quarter_halts_the_fetch_instead_of_narrowing_the_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-S5P-4. The failing quarter is 2019q3, not the first request, so this distinguishes a halt
    from a fetch that never started: 2018q1..2019q2 are served and stored first, and only the
    manifest -- the artifact every later stage reads -- is withheld."""
    _mock_transport(monkeypatch, _qcew_handler((2019, 3)))
    with pytest.raises(SourceFetchError, match="2019q3"):
        fetch_source(
            "qcew",
            _cfg(),
            env_path=None,
            raw_root=tmp_path,
            output_root=tmp_path,
            years=[2018, 2019],
        )
    assert list(tmp_path.rglob("*.csv")), "the earlier quarters should have been fetched"
    assert not (tmp_path / "source_manifest.parquet").exists()


def test_the_fetch_command_exits_non_zero_and_writes_no_manifest_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The §5 verification line for R-S5P-4, through the CLI rather than the library.

    `fetch` takes no year or quarter option, so this is the production window; the config is
    copied with its two storage roots redirected, per `test_cli_paths.py`'s idiom, because the
    command reads `cfg.storage.*` and would otherwise write into the working tree.
    """
    _mock_transport(monkeypatch, _qcew_handler((2019, 3)))
    raw = yaml.safe_load((REPO / "config.yaml").read_text())
    raw["storage"]["raw_uri"] = str(tmp_path / "raw")
    raw["storage"]["output_uri"] = str(tmp_path / "runs")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(raw))

    result = CliRunner().invoke(app, ["fetch", "--source", "qcew", "--config", str(config_path)])

    # Asserting the exception type, not a word in `result.output`: CliRunner leaves output empty
    # on an uncaught exception (see test_cli_paths.py), so a message assertion would pass against
    # nothing at all.
    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SourceFetchError)
    assert not (tmp_path / "runs" / "source_manifest.parquet").exists()


def test_an_empty_body_halts_the_by_size_fetch_even_though_the_status_is_200(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `qcew_size` site checked status alone before R-S5P-4, and government APIs answer 200
    with an error body -- so a whitespace response used to be stored as a zip and recorded as a
    snapshot row."""
    _mock_transport(monkeypatch, lambda request: httpx.Response(200, content=b"   "))
    with pytest.raises(SourceFetchError, match="2017q1 by-size"):
        fetch_source(
            "qcew_size",
            _cfg(),
            env_path=None,
            raw_root=tmp_path,
            output_root=tmp_path,
            years=[2017],
        )
    assert not (tmp_path / "source_manifest.parquet").exists()


def _cbp_handler(absent_years: set[int], *, data_status: int = 200):
    """Serve CBP metadata and data, 404-ing whole years and optionally failing the data leg."""
    variables = (REPO / "tests" / "fixtures" / "cbp" / "variables_2023.json").read_bytes()
    data = (REPO / "tests" / "fixtures" / "cbp" / "data_113310_2023.json").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        year = int(str(request.url).split("/data/")[1].split("/")[0])
        if year in absent_years:
            return httpx.Response(404, content=b"")
        if str(request.url.path).endswith("variables.json"):
            return httpx.Response(200, content=variables)
        return httpx.Response(data_status, content=data if data_status == 200 else b"")

    return handler


def test_the_declared_cbp_2024_absence_still_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The one case that must keep working: Census serves no 2024 CBP dataset, so its 404 is a
    property of the published record and `DECLARED_ABSENCES` says so with its measurement."""
    _mock_transport(monkeypatch, _cbp_handler({2024}))
    monkeypatch.setenv("CENSUS_API_KEY", "SECRET-CENSUS-KEY")
    rows = fetch_source(
        "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023, 2024]
    )
    assert [r["reference_start"] for r in rows] == ["2023-03"]
    assert (tmp_path / "source_manifest.parquet").exists()


def test_an_undeclared_cbp_year_halts_on_the_same_404_that_2024_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical response, identical branch, opposite outcome -- so what saves 2024 is the
    declaration and not the code path. Without this, the test above would pass against the four
    bare `continue` statements R-S5P-4 exists to remove."""
    _mock_transport(monkeypatch, _cbp_handler({2022}))
    monkeypatch.setenv("CENSUS_API_KEY", "SECRET-CENSUS-KEY")
    with pytest.raises(SourceFetchError, match="2022 variables metadata"):
        fetch_source(
            "cbp",
            _cfg(),
            env_path=None,
            raw_root=tmp_path,
            output_root=tmp_path,
            years=[2022, 2023],
        )
    assert not (tmp_path / "source_manifest.parquet").exists()


def test_a_cbp_data_leg_that_fails_after_its_metadata_succeeded_halts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fourth request site, and the only one that fails with bytes already in the store: the
    year's variables metadata is written before the data request is made."""
    _mock_transport(monkeypatch, _cbp_handler(set(), data_status=503))
    monkeypatch.setenv("CENSUS_API_KEY", "SECRET-CENSUS-KEY")
    with pytest.raises(SourceFetchError, match="2023 data"):
        fetch_source(
            "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023]
        )
    assert not (tmp_path / "source_manifest.parquet").exists()
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/unit/test_fetching.py -q
```
Expected: FAIL — the 500 is currently swallowed by `continue`.

- [ ] **Step 3: Implement**

Two files. Exact diff, verbatim from `git diff` in the worktree.

--- src/logging_employment/errors.py (inserted between UnsupportedReferenceYearError and SchemaMismatchError) ---

```python
class SourceFetchError(LoggingEmploymentError):
    """A source request answered a status or a body `fetch` cannot record, undeclared.

    Raised rather than skipped (R-S5P-4, §18.3). `ingest/base.HttpFetcher` deliberately RETURNS a
    non-200 so the caller classifies on content instead of status; this class is that
    classification's refusing branch, and it lives in the caller so the fetcher's contract is
    unchanged. Skipping is the behaviour it replaces, and skipping is unrecoverable downstream: a
    dropped quarter narrows the window, `runs.run_id` hashes the inputs so the shortened run takes
    a NEW id rather than colliding with the full one, and no manifest carries the fact that a
    quarter is missing -- so every later stage proceeds on the shorter window and nothing says so.

    The exceptions are declared in `fetching.DECLARED_ABSENCES`, keyed by (source, reference
    year), so a genuine hole in the published record is a line of code carrying its measurement
    rather than an incidental pass through the same branch a transient 500 takes.
    """
```

--- src/logging_employment/fetching.py ---

```diff
@@ -19,6 +19,7 @@ from .contracts import (
     SOURCE_SNAPSHOT_SCHEMA,
     schema_fingerprint,
 )
+from .errors import SourceFetchError
 from .harmonize.naics import vintage_for_year
 from .ingest import cbp, qcew, qcew_size
 from .ingest.base import FetchedBytes, HttpFetcher
@@ -26,6 +27,51 @@ from .store import RawStore, snapshot_row
 
 KNOWN_SOURCES = ("qcew", "qcew_size", "cbp")
 
+# (source_id, reference year) pairs whose publisher genuinely serves nothing, each carrying the
+# measurement that established it. A pair listed here is allowed to answer non-200 or empty; every
+# other key that does halts the run (R-S5P-4).
+#
+# A module constant and NOT a `Config` field: `config.resolved_dict` is `model_dump(mode="json")`
+# and feeds `runs.run_id`, so a new pydantic field -- default or not -- re-ids every existing
+# `runs/<id>/` directory, including the Stage 4 comparand `specs/stage5-preconditions.md` §4
+# protects. It is also not a per-run operator choice: it is the same class of audited fact as
+# `harmonize/disclosure.CBP_REGIME_BY_YEAR`, which is a module constant keyed by reference year
+# for the same reason. Deliberately NOT derived from that table, even though 2024 is missing from
+# both: "Census publishes no dataset" and "no fetched documentation states a disclosure regime"
+# are two findings that happen to coincide on one year, and a year published with an undocumented
+# regime must 200 here and halt in `harmonize`, not be excused from being fetched at all.
+DECLARED_ABSENCES: dict[tuple[str, int], str] = {
+    ("cbp", 2024): (
+        "Census serves no 2024 CBP dataset: Stage 0's dataset probe returned a real HTTP 404 "
+        "and 2024 is absent from cbp_metadata.years_available (SRC-CBP-003, SRC-CBP-004)"
+    ),
+}
+
+
+def _usable(fetched: FetchedBytes, *, source_id: str, year: int, reference: str) -> bool:
+    """Whether `fetched` carries bytes worth storing; halt when a failure is undeclared.
+
+    Returns False only for a DECLARED absence, so the one `continue` this leaves in the fetch loop
+    is a documented hole in the published record rather than whatever the network did. The
+    predicate is two-part for the reason `qcew.probe_slice_boundary` gives -- a source can answer
+    200 with an empty body -- and it is applied to all four request sites, including the two that
+    checked status alone before R-S5P-4.
+
+    Classifying here rather than in `HttpFetcher` keeps that layer's contract: it returns a
+    non-200 so the caller decides, because Stage 0 measured Census and USDA answering 200 with an
+    error body and 404 with a meaningful one.
+    """
+    if fetched.http_status == 200 and fetched.content.strip():
+        return True
+    if (source_id, year) in DECLARED_ABSENCES:
+        return False
+    raise SourceFetchError(
+        f"{source_id} {reference} returned HTTP {fetched.http_status} with "
+        f"{len(fetched.content)} byte(s) from {fetched.url}; refusing to narrow the window "
+        f"silently. Declare it in fetching.DECLARED_ABSENCES if the source publishes nothing "
+        f"for {year} (R-S5P-4, §18.3)"
+    )
+
 
 def merge_source_manifest(rows: Sequence[dict[str, object]], path: Path, source_id: str) -> str:
@@ -116,7 +162,9 @@ def fetch_source(
                     else:
                         fetched = fetcher.get(qcew.bulk_url(year))
                         name = f"{year}_qtrly_by_industry.zip"
-                    if fetched.http_status != 200 or not fetched.content.strip():
+                    if not _usable(
+                        fetched, source_id="qcew", year=year, reference=f"{year}q{quarter}"
+                    ):
                         continue
                     stored = store.put("qcew", fetched, name)
@@ -137,7 +185,9 @@ def fetch_source(
         elif source == "qcew_size":
             for year in window_years:
                 fetched = fetcher.get(qcew_size.BY_SIZE_URL.format(year=year))
-                if fetched.http_status != 200:
+                if not _usable(
+                    fetched, source_id="qcew_size", year=year, reference=f"{year}q1 by-size"
+                ):
                     continue
                 stored = store.put("qcew_size", fetched, f"{year}_q1_by_size.zip")
@@ -159,7 +209,9 @@ def fetch_source(
             key = creds.get(cfg.sources.cbp.api_key_env, "")
             for year in window_years:
                 variables = fetcher.get(cbp.VARIABLES_URL.format(year=year))
-                if variables.http_status != 200:
+                if not _usable(
+                    variables, source_id="cbp", year=year, reference=f"{year} variables metadata"
+                ):
                     continue
                 # Stored beside the data response, under the name `build` looks for, so the
                 # offline rebuild discovers the predicate exactly as this fetch did.
@@ -167,7 +219,7 @@ def fetch_source(
                 predicate = cbp.discover_naics_predicate(json.loads(variables.content))
                 query = cbp.build_query(year, predicate, cfg.project.industry_code_used)
                 fetched = fetcher.get(cbp.CBP_URL.format(year=year), params={**query, "key": key})
-                if fetched.http_status != 200:
+                if not _usable(fetched, source_id="cbp", year=year, reference=f"{year} data"):
                     continue
                 stored = store.put("cbp", fetched, f"{year}.json")
```

WHY NO OTHER CHANGE IS NEEDED: `merge_source_manifest` is called AFTER the `try/finally`, so an exception from inside the loop propagates past it. `finally: fetcher.close()` still runs; the manifest is never written. Bytes already put in the content-addressed store stay there, which is harmless — `build.snapshot_paths` reads the run manifest, not the store directory, so a fetch that halted contributes nothing downstream. `cli.py::fetch` needs no edit: the uncaught `SourceFetchError` gives exit code 1.

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/unit/test_fetching.py -q
```
Expected: PASS, including that no manifest row is written for the failed quarter.

- [ ] **Step 5: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add src/logging_employment tests/
git commit -m "fix(fetching): fail closed on a non-200 or empty body"
```


---

### Task 6: Stamp code identity into every run manifest

**Implements:** R-S5P-5

**Files:**
- Modify: `src/logging_employment/runs.py`
- Modify: `src/logging_employment/cli.py`
- Modify: `tests/unit/test_runs.py`
- Modify: `tests/integration/test_constraint_cli.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `code_commit` and `uv_lock_sha256` on every `*_manifest.json`, plus a new `bounds_manifest.json` from `solve-bounds`.

**`run_id` MUST NOT change.** It hashes `{config, inputs}`. Putting the commit into it would re-id every run directory on every commit. The point is that staleness becomes **detectable**, not impossible — the stamp sits beside the id, never inside it.

**Note the path correction:** `tests/unit/test_constraint_cli.py` does **not** exist. The real file is `tests/integration/test_constraint_cli.py`, and it runs fine without `data/` — its `workspace` fixture builds a tmp repo from committed `tests/fixtures/constraints/*.parquet` and runs `build-constraints` + `solve-bounds` in about a second.

- [ ] **Step 1: Write the failing tests**

### tests/unit/test_runs.py — header change

-from logging_employment.runs import RUN_ID_LENGTH, run_id
+from pathlib import Path
+
+from logging_employment.runs import RUN_ID_LENGTH, code_provenance, run_id

(`from pathlib import Path` goes after `import json`; ruff format put it there.)

### tests/unit/test_runs.py — appended at end of file

def test_the_code_stamp_records_unknown_rather_than_halting_a_run(tmp_path: Path) -> None:
    """R-S5P-5: the one deliberate exception to §18.3's fail-closed default, pinned as a test.

    `tmp_path` has no `uv.lock` in any ancestor, which is the tarball/sdist install -- reached
    without mocking `subprocess` or `PATH`. Fail-closed guards values that would corrupt an
    estimate; a missing commit id corrupts none, and refusing to run without `git` on PATH turns a
    provenance diagnostic into an outage. BOTH keys go unknown together: `uv.lock` is the anchor
    the git probe is rooted at, so half an answer here would mean a lock digest from one checkout
    beside a commit from whatever repository happened to enclose it.
    """
    assert code_provenance(tmp_path) == {"code_commit": "unknown", "uv_lock_sha256": "unknown"}


def test_a_tree_with_a_lock_and_no_git_history_stamps_half_an_answer(tmp_path: Path) -> None:
    """The sdist case, and the ONLY test that reaches the `git` probe's failure path.

    hatchling ships `uv.lock` (it is tracked) and never ships `.git`, so an sdist install has a
    readable lock digest and an unanswerable commit. Half an answer is the right answer: guessing
    the commit from whatever repository encloses the install directory would be a lie, and halting
    would make the package unusable exactly where it is most often installed. Measured: `git -C`
    on a directory outside any repository exits 128, which is the `returncode != 0` branch.
    """
    (tmp_path / "uv.lock").write_bytes(b"lock bytes")
    assert code_provenance(tmp_path) == {
        "code_commit": "unknown",
        "uv_lock_sha256": hashlib.sha256(b"lock bytes").hexdigest(),
    }


def test_no_code_stamp_reaches_the_payload_the_run_id_hashes(appendix_a_config: Config) -> None:
    """The HARD constraint: stamping code identity must renumber no run directory.

    Two assertions, guarding two different routes in. The first is the id itself, still equal to
    the derivation that predates provenance -- that is the one that fires if `run_id` starts
    folding the stamp into its own payload. The second guards the route the first cannot see:
    a `code_commit` or `uv_lock_sha256` field added to `Config` would reach `resolved_dict`, and
    both the id and its pre-provenance re-derivation would move together, silently and in step.
    So the second reconstructs the payload from `resolved_dict` and names the keys that must not
    appear in it, at the point of entry rather than as a changed digest nobody can attribute.
    """
    assert run_id(appendix_a_config, DIGESTS) == _payload_before_overrides_existed(
        appendix_a_config
    )
    payload = json.dumps(
        {"config": resolved_dict(appendix_a_config), "inputs": DIGESTS}, sort_keys=True
    )
    assert not set(code_provenance()) & set(json.loads(payload)["config"])
    assert "code_commit" not in payload
    assert "uv_lock_sha256" not in payload

### tests/integration/test_constraint_cli.py — inserted before
### test_solve_bounds_without_a_prior_build_names_what_is_missing (no new imports needed;
### json / pl / CliRunner / load_config / _run / _digest are already in the module)

def test_solve_bounds_writes_a_manifest_naming_every_output_it_wrote(workspace: Path) -> None:
    """R-S5P-5: §16.1 requires a machine-readable manifest per command; this one wrote none.

    The digests are checked against the files rather than merely asserted present -- a manifest
    whose `output_hashes` are stale describes some other run, which is worse than no manifest.
    """
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    manifest = json.loads((run / "bounds_manifest.json").read_text())
    assert set(manifest["output_hashes"]) == {
        "deterministic_bounds",
        "component_rank",
        "disclosure_flags",
    }
    for table, digest in manifest["output_hashes"].items():
        assert _digest(run / f"{table}.parquet") == digest
    built = json.loads((run / "schema_manifest.json").read_text())
    assert manifest["constraint_set_hash"] == built["constraint_set_hash"]
    bounds = pl.read_parquet(run / "deterministic_bounds.parquet")
    assert manifest["bound_status_counts"] == dict(
        bounds.group_by("bound_status").len().iter_rows()
    )


def test_a_refused_solve_bounds_leaves_no_manifest_behind(workspace: Path) -> None:
    """The manifest is written on the success path only, or it would assert a run that failed."""
    result = CliRunner().invoke(app, ["solve-bounds", "--config", str(workspace)])
    assert result.exit_code != 0
    output_root = Path(load_config(workspace).storage.output_uri)
    assert not list(output_root.rglob("bounds_manifest.json"))


def test_every_manifest_stamps_the_code_that_wrote_it(workspace: Path) -> None:
    """R-S5P-5: `run_id` hashes config and inputs but NOT source, so a run directory can be stale.

    Deliberately NOT pinned to a value: `code_commit` moves with every commit and carries a
    `-dirty` suffix in any working tree, so a literal would be re-typed forever. What must hold is
    that the keys exist on every manifest and carry something a reader can compare -- and that the
    two commands writing into one directory agree, since they ran from one checkout.
    """
    _run(workspace, "build-constraints")
    _run(workspace, "solve-bounds")
    cfg = load_config(workspace)
    run = next(Path(cfg.storage.output_uri).iterdir())
    stamps = [
        json.loads((run / name).read_text())
        for name in ("schema_manifest.json", "bounds_manifest.json")
    ]
    for manifest in stamps:
        assert manifest["code_commit"]
        assert manifest["uv_lock_sha256"]
    assert stamps[0]["code_commit"] == stamps[1]["code_commit"]
    assert stamps[0]["uv_lock_sha256"] == stamps[1]["uv_lock_sha256"]

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/unit/test_runs.py tests/integration/test_constraint_cli.py -q
```
Expected: FAIL — no `code_commit` key, and no `bounds_manifest.json`.

- [ ] **Step 3: Implement**

### 1. src/logging_employment/runs.py — appended after `run_dir` (no other change to the file;
### `hashlib` and `Path` are already imported at module level)

UNKNOWN_PROVENANCE = "unknown"


def _code_root(start: Path) -> Path | None:
    """The nearest ancestor of `start` holding `uv.lock`, or `None` when no ancestor does.

    `uv.lock` is the anchor because it is the one file that must exist in a checkout of THIS
    project and must not exist in a wheel built from it -- `[tool.hatch.build.targets.wheel]`
    ships `src/logging_employment` and nothing else. Anchoring on `.git` instead would find the
    enclosing repository of a site-packages copy that some unrelated checkout happens to sit
    inside, and stamp a commit that never produced the running code. One anchor for both stamps is
    the point: when this returns `None`, "which code ran" is honestly unanswerable and both keys
    say so together rather than one of them guessing.
    """
    for candidate in (start, *start.parents):
        if (candidate / "uv.lock").is_file():
            return candidate
    return None


def _git_output(root: Path, *args: str) -> str | None:
    """`git -C root <args>` stripped stdout, or `None` when git could not answer.

    `None` for every way the question goes unanswered -- git absent from PATH (`OSError`), the
    command hanging (`SubprocessError`, hence the timeout), or a non-zero exit, which is what
    `root` not being a repository looks like. `check=False` is the classification, not an
    oversight: a probe that reads the return code cannot also let it raise.
    """
    import subprocess

    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except OSError, subprocess.SubprocessError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def code_provenance(start: Path | None = None) -> dict[str, str]:
    """Which source and which locked dependencies produced a run, for stamping into its manifest.

    RECORDS, NEVER RAISES -- the one deliberate exception to §18.3's fail-closed default. That
    default guards values that would corrupt an estimate; a commit id corrupts nothing, it only
    tells a reader whether `runs/<id>/` still corresponds to the code in front of them. Halting a
    pipeline because `git` is missing would turn a diagnostic into an outage and make the package
    unusable from an sdist or a vendored copy, so an unanswerable probe records `"unknown"` --
    which is itself the finding, since a manifest that cannot name its commit is one a reviewer
    must not treat as reproducible.

    Nothing here reaches `run_id`, and that is the whole design. Hashing the commit into the id
    would rename every directory under `runs/` on every commit, so §16.1's "idempotent for the
    same inputs" would become unobservable and Stage 4's acceptance artifact would orphan itself
    on the next commit. Staleness -- CLAUDE.md's "a run directory can be stale w.r.t. your code"
    -- is made DETECTABLE here, not impossible.

    A DIRTY TREE IS NOT ITS COMMIT. `git rev-parse HEAD` answers on a dirty worktree, and a bare
    sha from one is a false "this run matches that commit": exactly the silent failure the stamp
    exists to prevent. The `-dirty` suffix (`git describe --dirty`'s convention) puts that in the
    value a reader compares, rather than in a sibling boolean they can forget to read. Untracked
    files count as dirty because Python imports whatever is on disk, so an uncommitted module is
    part of the code that ran. An unanswerable `git status` after an answerable `rev-parse` also
    marks dirty -- "could not verify clean" must not read as "clean".

    `start` is where the upward walk begins; the default is this module's own directory, so the
    stamp describes the code that is executing rather than the caller's cwd. Tests pass a path
    outside any checkout to reach the unknown branch without mocking `subprocess` or `PATH`.
    """
    root = _code_root(Path(__file__).resolve().parent if start is None else start)
    if root is None:
        return {"code_commit": UNKNOWN_PROVENANCE, "uv_lock_sha256": UNKNOWN_PROVENANCE}
    lock = hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    commit = _git_output(root, "rev-parse", "HEAD")
    if commit is None:
        return {"code_commit": UNKNOWN_PROVENANCE, "uv_lock_sha256": lock}
    status = _git_output(root, "status", "--porcelain")
    return {"code_commit": commit if status == "" else f"{commit}-dirty", "uv_lock_sha256": lock}

### NOTE on `except OSError, subprocess.SubprocessError:` -- I wrote the parenthesised form and
### `uv run ruff format src tests` REWROTE it to this PEP 758 form. It is correct under the
### project's `requires-python = ">=3.14"` and I verified it actually catches (see surprises).

### 2. src/logging_employment/cli.py — new TYPE_CHECKING import

 if TYPE_CHECKING:  # annotations only; keeps CLI start-up cheap
+    from collections.abc import Mapping
+
     from .config import Config

### 3. src/logging_employment/cli.py — the shared helper, inserted between `_constraints_dir`
###    and `_input_digests`

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

### 4. src/logging_employment/cli.py — the four existing writes become `_write_manifest` calls.
###    Mechanical: `(run / "X.json").write_text(json.dumps({...}, indent=2, sort_keys=True))`
###    becomes `_write_manifest(run / "X.json", {...})`, dedented one level, payload unchanged.
###    Sites: schema_manifest.json (build-constraints), baseline_manifest.json (run-baselines),
###    reconcile_manifest.json (reconcile), validation_manifest.json (validate).
###    `import json` then goes unused in build_constraints_command, reconcile_command and
###    validate_command -- `uv run ruff check --fix src tests` removed all three (F401).
###    It STAYS in solve_bounds_command and run_baselines_command, which still `json.loads`
###    the precondition manifest.

### 5. src/logging_employment/cli.py — solve_bounds_command, replacing the three bare writes
###    and the trailing echo

     run.mkdir(parents=True, exist_ok=True)
-    write_parquet_deterministic(result.bounds, run / "deterministic_bounds.parquet")
-    write_parquet_deterministic(result.components, run / "component_rank.parquet")
-    write_parquet_deterministic(flags, run / "disclosure_flags.parquet")
+    # The return values are the outputs' sha256s, exactly as `build-constraints` and
+    # `run-baselines` collect them; this command was throwing all three away.
+    hashes = {
+        "deterministic_bounds": write_parquet_deterministic(
+            result.bounds, run / "deterministic_bounds.parquet"
+        ),
+        "component_rank": write_parquet_deterministic(
+            result.components, run / "component_rank.parquet"
+        ),
+        "disclosure_flags": write_parquet_deterministic(flags, run / "disclosure_flags.parquet"),
+    }
     counts = result.bounds.group_by("bound_status").len().sort("bound_status")
+    narrow = int(flags["narrow_feasible_interval_flag"].sum())
+    exact = int(flags["exact_reconstruction_flag"].sum())
+    # §16.1: "Every command MUST write a machine-readable manifest." `solve-bounds` wrote none, so
+    # the §9 bounds were the one stage whose outputs a reader could only re-hash by hand, and the
+    # §9.8 flag counts -- §14's disclosure surface -- survived only in the terminal scrollback.
+    # Written AFTER the three tables and only on the success path: a refused run must leave the
+    # directory with no artifact of any kind claiming these inputs were bounded.
+    _write_manifest(
+        run / "bounds_manifest.json",
+        {
+            # The gate `load_system` was pinned to, restated where the outputs are. This is what
+            # ties `runs/<id>/deterministic_bounds.parquet` to the constraint tables in
+            # `data/constraints/`, which the run id does not cover.
+            "constraint_set_hash": built.constraint_set_hash,
+            "output_hashes": hashes,
+            "bound_status_counts": {
+                row["bound_status"]: row["len"] for row in counts.iter_rows(named=True)
+            },
+            "narrow_feasible_interval_flags": narrow,
+            "exact_reconstruction_flags": exact,
+        },
+    )
     for row in counts.iter_rows(named=True):
         typer.echo(f"{row['bound_status']} {row['len']}")
-    typer.echo(
-        f"flagged {flags['narrow_feasible_interval_flag'].sum()} narrow, "
-        f"{flags['exact_reconstruction_flag'].sum()} exact"
-    )
+    typer.echo(f"flagged {narrow} narrow, {exact} exact")

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/unit/test_runs.py tests/integration/test_constraint_cli.py -q
# gates:
uv run ruff format src tests ; uv run ruff check src tests ; uv run interrogate src
# whole-suite comparison against the documented dataless baseline:
uv run pytest -q
```
Expected: PASS.

- [ ] **Step 5: Gates and commit**

> **Watch the formatter here.** During verification `uv run ruff format src tests` rewrote
> `except (OSError, subprocess.SubprocessError):` into PEP 758's `except OSError, subprocess.SubprocessError:`
> — in `src/`, not `scripts/`. The project declares `>=3.14` so it parses, but it is the same rewrite
> `CLAUDE.md` documents. Let the formatter win; do not hand-revert it, and do not run `ruff format .`.

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add src/logging_employment tests/
git commit -m "feat(runs): stamp code identity into run manifests; add bounds_manifest.json"
```


---

### Task 7: Relabel §10.7's interval to what is computed

**Implements:** R-S5P-7

**Files:**
- Modify: `src/logging_employment/validate/metrics.py`
- Modify: `src/logging_employment/contracts.py`
- Modify: `tests/fixtures/validation/validation_metrics_golden.parquet`
- Modify: `tests/integration/test_validation_golden.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the corrected `interval_source` value and the updated `INTERVAL_SOURCES` closed set. Stage 5's §13.10 coverage gate reads this field.

**Relabel only.** Do not implement a time-ordered rolling interval — that is a §13.10 design question and is out of scope.

**Blast radius, measured: exactly one committed fixture.** `tests/fixtures/validation/validation_metrics_golden.parquet` — 301 of 1168 rows carry the old string (840 are NULL for non-probabilistic families, 27 are `"none"` for point-only estimators). 12325 -> 12356 bytes.

> A plain `grep -rl tests/` returns **nothing** — the fixture is a binary parquet. Use `grep -rl --binary-files=binary`.

**The golden CAN be regenerated here**, contrary to the usual assumption: `test_validation_golden.py`'s inputs are `tests/fixtures/baselines/`, which is in git, not sliced from `data/staged`. Verified: `uv run pytest tests/integration/test_validation_golden.py -q` -> `5 passed in 16.39s` with no `data/`. Per §17.6, regenerate with a hand-derived oracle row beside the whole-frame `equals`, never from the code under test alone.

- [ ] **Step 1: Write the failing test**

Appended to tests/integration/test_validation_golden.py (plus `import numpy as np` and `INTERVAL_SOURCES` added to the existing `logging_employment.contracts` import block). Exact post-`ruff format` text:

def test_the_interval_source_names_leave_one_out_rather_than_rolling(fixture_run):
    """R-S5P-7: `interval_source` names what is computed, and `rolling_` named something else.

    `probabilistic_metrics` builds each ensemble from `np.delete(residual_pool, position)` — the
    pool is every OTHER scored residual in the same (regime, seed, arm, estimator) group, with no
    time ordering and no window. Nothing rolls. The old value `rolling_residual_ensemble` promised
    §13.10's coverage gate a time-ordered interval that the code never computed, and the gate
    cannot tell the difference: `interval_source` is outside `assert_declared_provenance`'s five
    columns, so `INTERVAL_SOURCES` is checked by nothing at runtime and this test IS the check.

    Scope is the label. A time-ordered rolling interval is explicitly NOT built here
    (`specs/stage5-preconditions.md` §4).
    """
    assert INTERVAL_SOURCES == ("leave_one_out_residual_ensemble", "none")
    golden = pl.read_parquet(GOLDEN)
    for frame, origin in ((golden, "golden"), (fixture_run.metrics, "produced")):
        sources = set(frame["interval_source"].drop_nulls().to_list())
        assert sources <= set(INTERVAL_SOURCES), f"{origin} carries {sorted(sources)}"
        assert "leave_one_out_residual_ensemble" in sources, origin


def test_a_hand_derived_row_reproduces_the_golden_interval(fixture_run):
    """The oracle beside the whole-frame `equals`: one row derived from numpy, not from the code.

    `test_the_metrics_match_the_golden` compares the golden against the function that wrote it, so
    it detects drift and cannot detect a value that was wrong when it was frozen. This re-derives
    §13.7's 90% coverage and mean width for the widest interval-bearing group in the fixture
    (`whole_seasonal_blocks` x `cbp_intensity`, 37 scored cells) from the SCORES — which are data —
    without calling `probabilistic_metrics`. It is also what proves R-S5P-7 moved a label only: it
    passes unchanged on both sides of the rename.
    """
    regime, estimator = "whole_seasonal_blocks", "cbp_intensity"
    group = fixture_run.scores.filter(
        (pl.col("regime") == regime)
        & (pl.col("seed") == 1024)
        & (pl.col("estimator_id") == estimator)
    ).filter(pl.col("estimate").is_not_null())
    pool = (group["estimate"] - group["truth"]).to_numpy()
    assert pool.size == 37
    covered, widths = 0, []
    for position, row in enumerate(group.iter_rows(named=True)):
        ensemble = np.maximum(np.delete(pool, position) + float(row["estimate"]), 0.0)
        lo, hi = np.quantile(ensemble, 0.05), np.quantile(ensemble, 0.95)
        covered += int(lo <= row["truth"] <= hi)
        widths.append(hi - lo)
    golden = pl.read_parquet(GOLDEN).filter(
        (pl.col("regime") == regime)
        & (pl.col("estimator_id") == estimator)
        & (pl.col("metric_family") == "probabilistic")
    )

    def _value(name: str) -> float:
        return golden.filter(pl.col("metric_name") == name)["value"].item()

    assert covered == 33
    assert _value("coverage_0.90") == pytest.approx(covered / pool.size)
    assert _value("mean_interval_width_0.90") == pytest.approx(float(np.mean(widths)))

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/integration/test_validation_golden.py -q
```
Expected: FAIL on the old label.

- [ ] **Step 3: Implement**

Three source diffs (all verified applied, gates green).

--- a/src/logging_employment/contracts.py
+++ b/src/logging_employment/contracts.py
@@ -442,7 +442,19 @@ REGIME_SWITCHES: dict[str, str] = {
 
 MASK_ARMS: tuple[str, ...] = ("state_total", "national_size")
 
-INTERVAL_SOURCES: tuple[str, ...] = ("rolling_residual_ensemble", "none")
+# What produced a probabilistic row's interval, named for what the code computes. Until R-S5P-7
+# this value was named for a ROLLING window that `validate/metrics.py` has never computed: it
+# builds each ensemble from `np.delete(residual_pool, position)` — every OTHER scored residual in
+# the same (regime, seed, arm, estimator) group, leave-one-out by INDEX, no time ordering, no
+# window. (The superseded string is spelled out in the test named below, so a reader who greps for
+# it lands on the reason; it is deliberately not repeated in `src/`.)
+# §13.10's coverage gate reads these intervals and cannot tell a time-ordered interval from this
+# one, so the name is the only thing carrying the distinction. Unlike WEIGHT_BASES and its four
+# siblings above, this tuple is enforced by nothing at runtime — `assert_declared_provenance` does
+# not cover `interval_source` — so `tests/integration/test_validation_golden.py` is its only check.
+# Renaming the value here does not build the rolling version; that is Stage 5's, per
+# `specs/stage5-preconditions.md` §4.
+INTERVAL_SOURCES: tuple[str, ...] = ("leave_one_out_residual_ensemble", "none")

--- a/src/logging_employment/validate/metrics.py
+++ b/src/logging_employment/validate/metrics.py
@@ -177,7 +177,7 @@ def probabilistic_metrics(
         n = len(crps_values)
         common = {
             **base,
-            "interval_source": "rolling_residual_ensemble",
+            "interval_source": "leave_one_out_residual_ensemble",
             "calibration_sample_size": n,
         }

--- a/src/logging_employment/validate/intervals.py
+++ b/src/logging_employment/validate/intervals.py
@@ -1,4 +1,13 @@
-"""§10.7's empirical predictive intervals, from rolling pseudo-suppression residuals.
+"""§10.7's empirical predictive intervals, from pseudo-suppression residuals.
+
+§10.7 asks for them "from ROLLING pseudo-suppression residuals" and this package does not
+compute that: `metrics.probabilistic_metrics` pools every OTHER scored residual in the same
+(regime, seed, arm, estimator) group and drops the target's own by INDEX, which is
+cross-sectional leave-one-out within a replicate — no time ordering, no window. That gap is
+R-S5P-7, and `contracts.INTERVAL_SOURCES` now NAMES it rather than repeating the spec's word;
+the spec's word is quoted here so the divergence stays visible to a reader of this module and
+is not mistaken for a docstring that drifted. Building the time-ordered version is Stage 5's
+(`specs/stage5-preconditions.md` §4), not this module's.
 
 ONE object: the residual-shifted ensemble. Both the quantiles and the CRPS are derived from it, so
 an interval and a score can never disagree about the same predictive distribution.

GOLDEN REGENERATION SCRIPT (lived at /tmp/regen_golden.py; verbatim, run once with
`uv run python /tmp/regen_golden.py` from the repo root; the refusal branch is the point):

"""Audit produced-vs-golden by join, then regenerate the golden only if the diff is the relabel."""

import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path.cwd() / "tests"))
from integration.test_validation_golden import _fixture_config  # noqa: E402

from logging_employment.baselines.runner import REGISTRY  # noqa: E402
from logging_employment.contracts import HarmonizedData  # noqa: E402
from logging_employment.validate.harness import run_pseudo_suppression  # noqa: E402

REPO = Path.cwd()
GOLDEN = REPO / "tests" / "fixtures" / "validation" / "validation_metrics_golden.parquet"
KEY = ["regime", "seed", "mask_arm", "estimator_id", "metric_family", "metric_name"]

produced = run_pseudo_suppression(
    HarmonizedData.load(REPO / "tests" / "fixtures" / "baselines"), REGISTRY, _fixture_config()
).metrics
golden = pl.read_parquet(GOLDEN)

print("columns equal:", produced.columns == golden.columns)
print("heights:", produced.height, "/", golden.height)
print("key unique produced/golden:", produced.select(KEY).n_unique(), golden.select(KEY).n_unique())
print("row order identical (unsorted):", produced.select(KEY).equals(golden.select(KEY)))

joined = produced.join(
    golden, on=KEY, how="full", suffix="__old", validate="1:1", nulls_equal=True
)
print("join height:", joined.height)
moved = []
for col in produced.columns:
    if col in KEY:
        continue
    a, b = joined[col], joined[f"{col}__old"]
    same = (a.eq_missing(b)).all()
    if not same:
        moved.append(col)
        diff = joined.filter(~a.eq_missing(b))
        print(f"  MOVED {col}: {diff.height} rows")
        print(diff.select(*KEY, col, f"{col}__old").head(3))
print("columns that moved:", moved)

if moved == ["interval_source"]:
    old_counts = golden["interval_source"].value_counts().sort("interval_source")
    new_counts = produced["interval_source"].value_counts().sort("interval_source")
    print("old:", old_counts.rows())
    print("new:", new_counts.rows())
    produced.write_parquet(GOLDEN)
    print("REGENERATED", GOLDEN)
else:
    print("REFUSED to regenerate: diff is not the relabel")

Its exact observed output:

columns equal: True
heights: 1168 / 1168
key unique produced/golden: 1168 1168
row order identical (unsorted): True
join height: 1168
  MOVED interval_source: 301 rows
columns that moved: ['interval_source']
old: [(None, 840), ('none', 27), ('rolling_residual_ensemble', 301)]
new: [(None, 840), ('leave_one_out_residual_ensemble', 301), ('none', 27)]
REGENERATED .../tests/fixtures/validation/validation_metrics_golden.parquet

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/integration/test_validation_golden.py -q     # run from the repo root; needs NO data/ (inputs are tests/fixtures/baselines/, in git)
grep -rn "rolling_residual_ensemble" src/
```
Expected: tests PASS; the grep returns nothing.

- [ ] **Step 5: Gates and commit**

```bash
uv run ruff format src tests && uv run ruff check src tests && uv run interrogate src
git add src/logging_employment tests/
git commit -m "fix(validate): interval_source names what is computed, not a rolling scheme"
```


---

### Task 8: Give every open deferred item a size and a closure condition

**Implements:** R-S5P-8

**Files:**
- Modify: `specs/deferred_items.md`
- Create: `tests/unit/test_deferred_register.py`

**Interfaces:**
- Consumes: the `D-nnn` ids added in PR #19.
- Produces: a register where triage is "check the condition, route by size" rather than a re-derivation.

**The schema is not this plan's invention.** It is `~/.claude/skills/writing-plans/references/deferred-backlog.md`:
every item is self-contained (file paths, why deferred, what it would take), plus a **`Size:`** of
`quick-fix` / `plan` / `design`, and a **closure condition** — `Done when:` for work, `Revisit if:` for a
watch item. There is no `Target:` field; a named trigger IS a `Revisit if:`.

**Measured at `bbd9348`:** 41 open items; **33 lack `Size:`** and the same 33 lack both closure conditions.
`D-078` is the model to copy.

- [ ] **Step 1: Write the failing test**

```python
"""The deferred register's own schema, enforced (R-S5P-8).

Prose gets edited by hand and drifts; a test is the only thing that keeps the triage
contract true. The schema is `writing-plans/references/deferred-backlog.md`.
"""

from __future__ import annotations

import re
from pathlib import Path

REGISTER = Path(__file__).resolve().parents[2] / "specs" / "deferred_items.md"
SIZES = {"quick-fix", "plan", "design"}


def _open_items() -> list[tuple[str, str]]:
    """Every unticked item as (D-id, body), split on the checkbox at column 0."""
    parts = re.split(r"(?m)^(?=- \[)", REGISTER.read_text())
    out = []
    for part in parts:
        head = re.match(r"- \[ \] `(D-\d{3})`", part)
        if head:
            out.append((head.group(1), part))
    return out


def test_every_open_item_declares_a_size() -> None:
    missing = [d for d, body in _open_items() if not re.search(r"Size:\s*(\S+)", body)]
    assert not missing, f"{len(missing)} open items with no `Size:` line: {missing}"


def test_every_declared_size_is_in_the_closed_set() -> None:
    bad = {}
    for did, body in _open_items():
        m = re.search(r"Size:\s*([a-z-]+)", body)
        if m and m.group(1) not in SIZES:
            bad[did] = m.group(1)
    assert not bad, f"sizes outside {sorted(SIZES)}: {bad}"


def test_every_open_item_declares_a_closure_condition() -> None:
    missing = [
        d for d, body in _open_items()
        if "Done when:" not in body and "Revisit if:" not in body
    ]
    assert not missing, f"{len(missing)} open items with no closure condition: {missing}"
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/unit/test_deferred_register.py -q
```
Expected: **2 failed** — `test_every_open_item_declares_a_size` and
`test_every_open_item_declares_a_closure_condition`, each naming the same 33 ids.
`test_every_declared_size_is_in_the_closed_set` PASSES.

> Writing this test found a real defect on its first run: `D-085` declared
> `Size: implementation`, which is outside the schema's `{quick-fix, plan, design}`. It was
> corrected to `plan` before this plan was finalised. If that third assertion fails when you run
> it, someone has since added another out-of-set size — fix the item, not the test.

- [ ] **Step 3: List exactly what needs a line**

```bash
uv run python -c "
import re
from pathlib import Path
txt = Path('specs/deferred_items.md').read_text()
for part in re.split(r'(?m)^(?=- \[)', txt):
    h = re.match(r'- \[ \] \`(D-\d{3})\` \*\*(.*?)\*\*', part, re.S)
    if h and ('Size:' not in part or ('Done when:' not in part and 'Revisit if:' not in part)):
        print(h.group(1), ' '.join(h.group(2).split())[:78])
"
```

- [ ] **Step 4: Add the two lines to each, in the file, matching `D-078`'s shape**

Append to each item's body, at its existing indent (six spaces):

```markdown
      Size: design. Revisit if: <the condition that would make this worth reopening>.
```

Rules, so this stays a record change and not a re-triage:
- **Do not invent a condition.** The size and condition come from the item's own recorded reason.
  An item that cannot state one is not deferrable — say so in the completion report rather than
  fabricating a trigger.
- `Done when:` for work with a definite finish; `Revisit if:` for a watch item.
- Do not edit any ticked item, and do not renumber anything.

- [ ] **Step 5: Verify and commit**

```bash
uv run pytest tests/unit/test_deferred_register.py -q
uv run --no-project --python 3.13 python ~/.claude/skills/writing-plans/scripts/deferred_stats.py
```
Expected: tests PASS; the stats line still reports 41 open (this task closes nothing).

```bash
git add specs/deferred_items.md tests/unit/test_deferred_register.py
git commit -m "docs(specs): every open deferred item declares a size and a closure condition"
```

---

### Task 9: Rule on what `rolling_origin` and `cbp_size_gaps` score

**Implements:** R-S5P-9

**Files:**
- Modify: `specs/deferred_items.md` (`D-071`, `D-086`)
- Modify: `specs/logging-employment-spec-roadmap.md` (Stage 4 `Gap closed:`, Stage 5 `Consumes:`)
- Create: `specs/findings/stage-4-log.md` entry (the file exists)

**Interfaces:**
- Consumes: Task 8's schema (this ruling is written as a closure condition or a tick).
- Produces: a recorded answer Stage 5's plan can read. **No code is required by this task.**

**This is a DECISION task.** Its deliverable is a written ruling, not an implementation. It is last
because it is the only task whose answer is not already determined, and it is in the plan because
Stage 5's promotion gate reads this scoreboard — leaving it open means Stage 5 is planned against a
roadmap that says REQ-022 is closed while four of thirteen regimes score nothing.

**Measured at `bbd9348`, from `runs/f03023ac9f3a/`:**

| Regime | Scores? | Owner |
|---|---|---|
| 9 others | yes | — |
| `rolling_origin` | **no** (`n_scored=0`) | `D-071` |
| `cbp_size_gaps` | **no** | `D-071` |
| `retrospective_smoothing` | **no** (`n_scored=0`) | `D-086` |
| `preliminary_to_final_vintage` | **no** | `D-086` |

REQ-022 (`specs/logging-employment-spec.md:2142`) is *"Separate rolling forecasts and retrospective
smoothing."* **Both** of its named regimes score zero, and Stage 4's `Gap closed:` line lists REQ-022.

- [ ] **Step 1: Put the choice to your human partner, with the costs**

This step ends the task's automated portion. Present exactly this, and wait:

> **Option A — give each regime something to score.** `rolling_origin` needs a target selector applied
> to the truncated frame (`assert_no_future_rows` already exists and records `origins_checked`);
> `cbp_size_gaps` needs the CBP gap composed with a QCEW mask, because dropping CBP alone changes only
> `cbp_intensity`'s availability and produces no scored cell on its own. Size: design, then plan.
> Closes `D-071`; leaves `D-086` unless the same pass covers the other two.
>
> **Option B — re-scope REQ-022 honestly.** Strike REQ-022 from Stage 4's `Gap closed:` line, name it in
> Stage 5's `Consumes:` as an open requirement, and record in `D-071`/`D-086` that the four regimes are
> declared-but-unscored by decision. Size: quick-fix. Costs nothing now; means Stage 5's promotion gate
> is applied with nine regimes and says so.

- [ ] **Step 2: Record the ruling**

Whichever is chosen, write it in three places so no reader has to reconstruct it:
1. `D-071` and `D-086` — the ruling as a `Done when:` (Option A) or a tick with the reason (Option B).
2. The roadmap's Stage 4 `Gap closed:` line — REQ-022 stays only if Option A is chosen AND lands.
3. `specs/findings/stage-4-log.md` — a dated entry, since this supersedes a claim the block made.

- [ ] **Step 3: If Option B, apply the roadmap edits**

Strike `REQ-022` from Stage 4's `Gap closed:` line and add to Stage 5's `Consumes:`:

```
REQ-022 is NOT closed by Stage 4: four of §13.3's thirteen regimes score nothing
(`D-071`, `D-086`), so the §13.10 gate is applied over nine.
```

- [ ] **Step 4: Verify**

```bash
uv run pytest tests/unit/test_deferred_register.py -q
grep -n "REQ-022" specs/logging-employment-spec-roadmap.md
```
Expected: the register test passes; REQ-022 appears where the ruling put it and nowhere else.

- [ ] **Step 5: Commit**

```bash
git add specs/
git commit -m "docs(specs): rule on what rolling_origin and cbp_size_gaps score"
```

---

## Self-Review

**Spec coverage.** All nine requirements have a task: R-S5P-1 → Task 1, R-S5P-2 → Task 2,
R-S5P-6 → Task 3, R-S5P-3 → Task 4, R-S5P-4 → Task 5, R-S5P-5 → Task 6, R-S5P-7 → Task 7,
R-S5P-8 → Task 8, R-S5P-9 → Task 9. The spec's §4 ("what this does NOT do") and §6 (spec
amendments) are deliberately unimplemented and no task claims them.

**Ordering.** Tasks 1–2 first because until the CLI imports in a clean environment and the 42
data-dependent tests skip rather than fail, no later task's "the suite is green" is checkable.
Tasks 3–7 are mutually independent and may be done in any order or in parallel. Tasks 8–9 are
record-only and touch no code.

**Two spec claims were corrected before this plan was written** (`bbd9348`), both found by running
the code rather than reading it: R-S5P-2's "six modules" is nine, and R-S5P-6's "8 of 11 leaving 3"
is 7 of 11 leaving 4.

**What this plan does not verify.** Task 1's `uv sync --no-dev` path and Task 8/9's record edits were
not executed in a worktree — Task 1 because it mutates the lock, Tasks 8–9 because they have no code.
Every code block in Tasks 2–7 was executed.
