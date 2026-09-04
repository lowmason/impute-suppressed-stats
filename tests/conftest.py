"""Pytest configuration for the audit test suite.

`scripts/audit/_common.py` is imported as `import _common` — a bare sibling import, matching
how every PEP 723 audit script imports it under `uv run --no-project` (no package, no project
context; see `scripts/audit/_common.py`'s module docstring). The documented test command sets
`PYTHONPATH=scripts/audit` for that reason. This conftest puts `scripts/audit` on `sys.path`
too, so a bare `pytest` invocation (no `PYTHONPATH`) finds `_common` as well — it does not
replace the documented command, only widen how the suite can be run.
"""

from __future__ import annotations

import sys
from pathlib import Path

_AUDIT_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts" / "audit"
if str(_AUDIT_SCRIPTS) not in sys.path:
    # append, not insert(0, ...): this directory holds every Stage 0 audit script, and one
    # named after a stdlib module must not shadow it suite-wide.
    sys.path.append(str(_AUDIT_SCRIPTS))
