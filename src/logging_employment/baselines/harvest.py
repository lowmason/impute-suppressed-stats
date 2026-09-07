"""§10.5 harvest-proportional allocation, which declines on this window.

§10.5 is two sentences and states no precondition: "Allocate residual using harvest-origin volume
or the estimated latent harvest factor. It is a benchmark, not a preferred standalone estimator."
The obligation to decline rather than improvise comes from the roadmap's Stage 3 exit criteria --
"the harvest-proportional baseline declines to run without a harvest factor rather than fabricating
one" -- so cite the roadmap for the refusal, not the spec.

THERE IS NO HARVEST INPUT. Appendix A ships `tpo.enabled: false` and `fia.enabled: false`, and
`config.yaml` carries no tpo or fia source entry at all. §11.4's latent harvest factor is Stage 7's
deliverable. The tempting substitutes -- timber acreage, a national harvest series spread by state
area, a proxy built from establishment counts -- would each be a different estimator wearing this
one's name, and would be scored by Stage 4 as though §10.5 had run.

This estimator becomes live when Stage 7 supplies `features/harvest_factor.py`. Until then the
decline is the deliverable, and §17.4 row 4's "run every baseline on a small frozen fixture" is
satisfied by a clean decline.
"""

from __future__ import annotations

from ..reconcile.allocate import Weights
from ..reconcile.anchor import Anchor
from .interfaces import Decline, EstimatorContext


class HarvestProportional:
    """§10.5. Declines until Stage 7 supplies a harvest factor."""

    estimator_id = "harvest_proportional"
    # Declines on this window, so it never reaches a composite.
    fallback_intensity = None

    def weights(self, context: EstimatorContext, anchor: Anchor) -> Weights | Decline:
        """Always a decline on this window, carrying the reason a reader can act on."""
        return Decline(
            reason=(
                "no harvest-origin volume and no latent harvest factor are available: Appendix A "
                "ships tpo.enabled=false and fia.enabled=false and the config declares neither "
                "source. Stage 7 supplies the harvest factor; until then §10.5 declines rather "
                "than allocating on a substitute proxy that would be scored as if it were this "
                "baseline"
            )
        )
