"""Concept guards that halt a run before a statistical unit is silently relabeled.

NEITHER GUARD IS CALLED TODAY, AND THAT IS CORRECT RATHER THAN A GAP. Each refuses an input from a
source this stage does not ingest: `reject_enterprise_size` guards SUSB (INV-010, SRC-OTH-001) and
`reject_nonemployer_in_core_total` guards the nonemployer series (SRC-OTH-004), and neither
`ingest/susb.py` nor `ingest/nonemployer.py` exists. Roadmap Stage 7 owns those ingest halves and
is where the call sites appear; until then both are reserved and are exercised only by their unit
tests. Written down because the alternative reading -- a guard the build path forgot to call -- is
indistinguishable from this one without the note. Same shape, and same reason, as
`errors.NoHarvestFactorError`.
"""

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
