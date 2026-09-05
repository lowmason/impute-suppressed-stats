"""The §12 exact reconciliation layer.

§12.1: "The predictive model ranks feasible allocations. The reconciliation layer maps each draw
into the deterministic feasible set. It is not optional post-hoc cosmetic adjustment." Nothing in
this subpackage is skippable by configuration, and no key exists to disable it.
"""

from __future__ import annotations

from .anchor import Anchor, Partition, national_residual, observed_partition

__all__ = ["Anchor", "Partition", "national_residual", "observed_partition"]
