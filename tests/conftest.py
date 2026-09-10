"""Pytest configuration for the audit test suite.

`scripts/audit/_common.py` is imported as `import _common` — a bare sibling import, matching
how every PEP 723 audit script imports it under `uv run --no-project` (no package, no project
context; see `scripts/audit/_common.py`'s module docstring). The documented test command sets
`PYTHONPATH=scripts/audit` for that reason. This conftest puts `scripts/audit` on `sys.path`
too, so a bare `pytest` invocation (no `PYTHONPATH`) finds `_common` as well — it does not
replace the documented command, only widen how the suite can be run.

It also owns `requires_staged`, the shared staged-data guard. `data/staged/` is gitignored and
rebuilt from ~564 MB of frozen source bytes, so a bare checkout has none of it, and the nine
`validate/` modules that read those tables used to FAIL there rather than skip. The guard
keys on a FILE EXISTING -- `qcew_monthly.parquet`, the same probe `tests/integration/test_d1_*.py`
already spell out inline -- and not on an env var: an env var records what someone remembered to
export, while the file records whether `build-harmonized` has actually run, which is the condition
these tests actually depend on. `STAGED` is absolute, derived from this file, because the modules
it replaces passed `Path("data/staged")` and so silently required pytest to be invoked from the
repo root. It lives in the ROOT conftest for the same reason `appendix_a_config` does: both
`tests/unit/` and `tests/integration/` need it. Modules apply it per-test wherever they also hold
tests that need no data (`test_validate_regimes.py`, `test_validate_declared_regimes.py`,
`test_validate_temporal_regimes.py`) -- a blanket `pytestmark` there would skip tests that pass
in a bare checkout, shrinking coverage while still reporting `0 failed`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from logging_employment.config import Config, load_config

_AUDIT_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "audit"
if str(_AUDIT_SCRIPTS) not in sys.path:
    # append, not insert(0, ...): this directory holds every Stage 0 audit script, and one
    # named after a stdlib module must not shadow it suite-wide.
    sys.path.append(str(_AUDIT_SCRIPTS))

STAGED = Path(__file__).resolve().parents[1] / "data" / "staged"

# Import this in a test module (`from tests.conftest import STAGED, requires_staged`) rather than
# repeating the skipif. It is not yet the suite's ONLY copy: `test_d1_acceptance.py`,
# `test_d1_baselines.py`, `test_d1_validation.py`, `test_validate_cli.py` and
# `test_stage4_acceptance.py` still spell out their own `STAGED` + skipif inline, and folding
# those into this one is a separate change.
requires_staged = pytest.mark.skipif(
    not (STAGED / "qcew_monthly.parquet").exists(),
    reason="data/staged is gitignored; run `build-harmonized` first",
)


@pytest.fixture()
def appendix_a_config() -> Config:
    """The Appendix A configuration, parsed once, for estimators that read config keys.

    Defined in the ROOT conftest, not `tests/unit/`, because §17.6's golden tests under
    `tests/integration/` request it too and pytest does not expose a subdirectory's fixtures to a
    sibling directory.
    """
    return load_config(Path(__file__).resolve().parents[1] / "config.yaml")
