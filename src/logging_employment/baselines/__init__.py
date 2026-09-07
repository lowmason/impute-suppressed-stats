"""The §10 transparent baselines.

Every estimator here produces weights and nothing else; `reconcile.allocate` turns weights into
estimates. That is what makes §10's "same reconciliation layer as the full model" concrete.
"""

from __future__ import annotations

from .interfaces import Decline, EmployeeWeights, Estimator, EstimatorContext, compose

__all__ = ["Decline", "EmployeeWeights", "Estimator", "EstimatorContext", "compose"]
