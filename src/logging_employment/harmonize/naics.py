"""NAICS vintage handling and the mechanical 113310 crosswalk across the D1 window.

The crosswalk rows are vendored in `naics_113310.csv` from the classification-codes skill's derived
NAICS data. Two caveats travel with them, recorded by the Stage 0 audit and repeated here because
they bound what this module's passing test proves:

* `link_type = 1:1` is derived from code multiplicities after deduplication; it is **not a Census
  column**. Census ships four columns -- source code, source title, target code, target title --
  flags partial flows through cell formatting that a plain parse discards, and publishes no
  allocation weights.
* 1:1 establishes only that 113310 neither split nor merged in the six-digit code pairing. That is
  not a statement about the industry's definitional content. The unchanged title and the empty
  structure-file `change_indicator` are what carry the continuity claim, and even those are titles
  and markers rather than a comparison of the two vintages' definitional text.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

_CROSSWALK = Path(__file__).parent / "naics_113310.csv"

# The QCEW vintage boundary Stage 0 recorded: NAICS 2017 for reference years 2017-2021, NAICS 2022
# from 2022 on. QCEW publishes no per-row vintage column, so this mapping is documented rather than
# measured. CITED 2026-09-08 -- Stage 0 carried the supporting premise as uncited and routed a
# citation to a later stage; this is that citation. BLS publishes the reference-year-to-vintage
# mapping directly, and states it in the present tense, which is what makes it load-bearing here:
# 2017-2021 are STILL on NAICS 2017 four years after NAICS 2022 was introduced, so prior reference
# years are not recoded onto a new vintage.
#
#   "Data from 2011-2016 are classified under the NAICS 2012 system. Data from 2017-2021 are
#    classified under the NAICS 2017 system. Data from 2022-forward will be classified under the
#    NAICS 2022 system."
#   -- BLS QCEW Q&A, "What versions of NAICS and SIC does the QCEW program use?",
#      https://www.bls.gov/cew/questions-and-answers.htm (last modified 2026-02-13). The same
#      mapping appears on https://www.bls.gov/cew/classifications/industry/home.htm (last modified
#      2026-01-28), so it does not rest on a single page.
#
# ONE QUALIFICATION, from that same BLS answer, recorded because omitting it would make the
# citation cherry-picked: QCEW HAS retabulated history, once. For 1990-2000, "As a NAICS
# reconstruction project, the data had been reclassified under the NAICS 2002" -- a one-time bridge
# across classification SYSTEMS (SIC to NAICS), announced as its own project. So the unqualified
# claim "QCEW does not retabulate prior reference years" is false as stated. The operative claim
# this module rests on -- no NAICS-vintage-to-NAICS-vintage recode -- is the one BLS supports, and
# BLS says so plainly when it does retabulate, which is why the silence elsewhere carries weight.
#
# SCOPE. The rule below is correct only at or above WINDOW_START (2017-01). BLS's table puts
# 2011-2016 on NAICS 2012 and 2007-2010 on NAICS 2007, where `vintage_for_year` returns
# "NAICS 2017" for every year below 2022. Latent today -- no input reaches those years -- and it
# would become live the moment the window extends backward.
_VINTAGE_BOUNDARY_YEAR = 2022


def vintage_for_year(year: int) -> str:
    """The NAICS vintage a QCEW reference year's rows carry."""
    return "NAICS 2022" if year >= _VINTAGE_BOUNDARY_YEAR else "NAICS 2017"


def crosswalk_113310() -> pl.DataFrame:
    """The vendored 113310 rows for every vintage the D1 window spans.

    Every column reads as String. `vintage` and `parent_code` are digit strings that infer as
    Int64 under a default read, which both silences a leading zero and makes a comparison against
    a string literal raise -- so this matches how every other reader in the package treats a code.
    """
    return pl.read_csv(_CROSSWALK, comment_prefix="#", infer_schema_length=0)


def assert_113310_survives_the_window(frame: pl.DataFrame | None = None) -> None:
    """Raise unless 113310 is present, titled Logging, and unchanged across both vintages.

    Mechanical rather than string-continuity: §3.1 states outright that apparent code-string
    continuity is not a substitute for a versioned crosswalk test, so this reads the concordance
    and the structure files' change indicators rather than observing that "113310" appears twice.

    `frame` defaults to the vendored crosswalk. It is injectable so the tests can show each of
    the four branches failing on a doctored frame; a guarantee nothing has been seen to reject is
    not a guarantee.
    """
    frame = crosswalk_113310() if frame is None else frame
    vintages = set(frame["vintage"].to_list())
    if vintages != {"2017", "2022"}:
        raise ValueError(
            f"expected both window vintages in the crosswalk, found {sorted(vintages)}"
        )
    titles = set(frame["title"].to_list())
    if titles != {"Logging"}:
        raise ValueError(f"113310's title is not stable across vintages: {sorted(titles)}")
    changed = frame.filter(
        pl.col("change_indicator").is_not_null() & (pl.col("change_indicator") != "")
    )
    if changed.height:
        raise ValueError(
            f"113310 carries a non-empty change_indicator in {changed['vintage'].to_list()}; the "
            "structure file marks it as changed from the prior vintage"
        )
    link = frame.filter(pl.col("vintage") == "2017")["link_type_to_next"].to_list()
    if link != ["1:1"]:
        raise ValueError(f"the 2017->2022 concordance does not pair 113310 one-to-one: {link}")
