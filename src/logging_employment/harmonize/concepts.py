"""Concept guards that halt a run before a statistical unit is silently relabeled."""

from __future__ import annotations

from ..errors import ConceptViolationError


def reject_enterprise_size(size_dimension: str, source_id: str) -> None:
    """Raise if an enterprise-size dimension is offered as establishment size (INV-010).

    Stage 0 measured SUSB's size dimension as `enterprise` (column `ENTRSIZE`). §5.3 permits SUSB
    into a weak prior or a sensitivity model with its concept preserved; what it forbids is the
    relabeling this guard catches.
    """
    if "enterprise" in size_dimension.lower():
        raise ConceptViolationError(
            f"{source_id} carries size dimension {size_dimension!r}; enterprise size is never an "
            "establishment-size measurement (INV-010, SRC-OTH-001)"
        )


def reject_nonemployer_in_core_total(source_id: str) -> None:
    """Raise if a nonemployer source is routed into the core employment total (SRC-OTH-004)."""
    if "nonemp" in source_id.lower():
        raise ConceptViolationError(
            f"{source_id} is a nonemployer source and is excluded from the core employment total; "
            "it may only feed a separately labeled expanded-universe output (§5.3)"
        )
