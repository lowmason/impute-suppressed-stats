"""The §12 exact reconciliation layer.

§12.1: "The predictive model ranks feasible allocations. The reconciliation layer maps each draw
into the deterministic feasible set. It is not optional post-hoc cosmetic adjustment." Nothing in
this subpackage is skippable by configuration, and no key exists to disable it.
"""

from __future__ import annotations

from .allocate import Weights, allocate, check_domain
from .anchor import (
    Anchor,
    Partition,
    assert_universe_closes,
    closure_audit,
    national_residual,
    observed_partition,
)
from .draws import PosteriorDraws, ReconciliationInputs, reconcile_draws
from .integerize import integerize
from .matrix import reconcile_matrix
from .projection import constraint_violation, kl_project, require_supported_method
from .scaling import Bounds, scale_into_bounds

__all__ = [
    "Anchor",
    "Bounds",
    "Partition",
    "PosteriorDraws",
    "ReconciliationInputs",
    "Weights",
    "allocate",
    "assert_universe_closes",
    "check_domain",
    "closure_audit",
    "constraint_violation",
    "integerize",
    "kl_project",
    "national_residual",
    "observed_partition",
    "reconcile_draws",
    "reconcile_matrix",
    "require_supported_method",
    "scale_into_bounds",
]
