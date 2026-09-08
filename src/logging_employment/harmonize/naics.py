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

from ..errors import UnsupportedReferenceYearError

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
# SCOPE, and the guard below. The two-branch rule is correct only at or above 2017. BLS's table
# puts 2011-2016 on NAICS 2012 and 2007-2010 on NAICS 2007, so before this guard existed every
# year below 2017 was stamped "NAICS 2017" -- a year BLS classifies otherwise.
#
# A pre-2017 year is REFUSED rather than classified from the table below, because this package can
# name a pre-2017 vintage but cannot consume one. `crosswalk_113310` vendors only the 2017 and
# 2022 rows and `assert_113310_survives_the_window` requires exactly that pair; `validate/regimes`
# asserts the single seam 2021-12/2022-01 BY CONSTRUCTION; `baselines/historical` filters its
# lookback on `naics_vintage` equality, so a third string would quietly shrink every lookback
# rather than fail. `naics_vintage` also composes into `cell_id` (`constraints/cells.py`) and is
# declared by five `contracts.py` schemas. Emitting "NAICS 2012" would therefore be right as a
# BLS fact and wrong as a pipeline value -- the same trade `build.py` already makes when it
# refuses to let an unestablished CBP disclosure regime reach a harmonized table.
#
# ONLY THE LOWER END IS GUARDED. BLS says "2022-forward", so "NAICS 2022" is source-justified for
# every year above the window. NAICS 2027 will end that, but nothing published contradicts the
# rule yet, and guarding forward would refuse a window extension BLS's own table supports.
#
# THE BOUND IS NOT DERIVED FROM `constants.WINDOW_START`, though both read 2017 today. It is the
# first year of BLS's NAICS 2017 era -- a fact about BLS's table, where the window is a fact about
# D1. Deriving it from the window would make widening the window widen the accepted range in the
# same edit, silently restoring the defect this guard exists to stop. Reachability is why that
# matters: `fetching.py` builds its years from `cfg.project.start_month`, which `ProjectConfig`
# validates only as `YYYY-MM`, so the window is a config value and not this constant.
_NAICS_2017_ERA_START = 2017
_VINTAGE_BOUNDARY_YEAR = 2022

# BLS's published table, recorded so a widening does not have to re-source it. Each pair is the
# first reference year of that vintage's era. Used ONLY to tell a refused caller what BLS says --
# never to emit a value. Wiring it to the return is not a one-line change: it also needs crosswalk
# rows for the new vintage, a `validate/regimes` seam that is no longer single, and a decision
# about `cell_id` values that have never existed. A test pins it equal to the live rule across
# 2017-2024 so the documentation cannot drift from the behaviour where both apply.
_BLS_VINTAGE_ERAS: tuple[tuple[int, str], ...] = (
    (1990, "NAICS 2002"),  # 1990-2000 reclassified from SIC by the NAICS reconstruction project
    (2007, "NAICS 2007"),
    (2011, "NAICS 2012"),
    (2017, "NAICS 2017"),
    (2022, "NAICS 2022"),
)


def bls_vintage_for_year(year: int) -> str:
    """What BLS's published table calls `year`, including years this package refuses to process.

    Documentation of the source, not a pipeline value: `vintage_for_year` is what stamps the
    `naics_vintage` column, and it refuses every year this returns a pre-2017 vintage for.
    """
    eras = [vintage for start, vintage in _BLS_VINTAGE_ERAS if year >= start]
    return eras[-1] if eras else "no NAICS vintage (BLS's table starts at 1990)"


def vintage_for_year(year: int) -> str:
    """The NAICS vintage a QCEW reference year's rows carry.

    Raises `UnsupportedReferenceYearError` below 2017 rather than classifying the year from BLS's
    table; the note above records why naming a vintage and being able to consume one differ here.
    """
    if year < _NAICS_2017_ERA_START:
        raise UnsupportedReferenceYearError(
            f"QCEW reference year {year} predates the NAICS 2017 era; BLS classifies it under "
            f"{bls_vintage_for_year(year)}, which this package vendors no crosswalk for and no "
            "downstream stage consumes. Extending the window backward is a deliberate change to "
            "the crosswalk, the vintage seam, and cell_id -- not a change to this bound"
        )
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
