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
        d for d, body in _open_items() if "Done when:" not in body and "Revisit if:" not in body
    ]
    assert not missing, f"{len(missing)} open items with no closure condition: {missing}"
