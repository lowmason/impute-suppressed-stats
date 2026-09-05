"""The nine versioned dimensions §8.6 requires."""

from __future__ import annotations

import polars as pl

from ..constants import STATES_DC_FIPS

DIMENSION_VERSION = "v1"

DIMENSIONS: dict[str, tuple[str, ...]] = {
    "geography": tuple(STATES_DC_FIPS),
    "naics": ("113310",),
    "ownership": ("5",),
    "source_universe": ("qcew_covered_private", "cbp_establishments"),
    "statistical_unit": ("establishment",),
    "reference_period": ("calendar_month", "week_including_march_12"),
    "size_concept": ("march_reference", "contemporaneous_modeled"),
    "release_status": ("final", "preliminary"),
    "disclosure_regime": (
        "qcew_disclosure_code_v1",
        "noise_infusion",
        "noise_infusion_plus_suppression",
    ),
}


def dimension_frame(name: str) -> pl.DataFrame:
    """One dimension's members, each stamped with the dimension version."""
    if name not in DIMENSIONS:
        raise KeyError(f"unknown dimension {name!r}; known: {sorted(DIMENSIONS)}")
    members = list(DIMENSIONS[name])
    return pl.DataFrame(
        {
            "dimension": [name] * len(members),
            "member": members,
            "dimension_version": [DIMENSION_VERSION] * len(members),
        },
        schema={"dimension": pl.String, "member": pl.String, "dimension_version": pl.String},
    )
