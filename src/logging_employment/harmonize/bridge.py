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

    A row missing a declared field raises. Polars would render the absent field as null, and a
    bridge carrying a null `verification_status` or `uncertainty_treatment` states nothing about
    whether the mapping was estimated or merely declared -- which is the one thing §8.6 asks a
    bridge row to say.
    """
    for index, row in enumerate(rows):
        missing = [field for field in BRIDGE_SCHEMA if field not in row]
        if missing:
            raise ValueError(f"bridge row {index} is missing the declared field(s) {missing}")
    return pl.DataFrame(list(rows), schema=BRIDGE_SCHEMA, orient="row")
