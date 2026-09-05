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
