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
