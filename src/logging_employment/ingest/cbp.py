"""CBP ingestion: state x six-digit x establishment-size counts as March-centered measurements.

`naics_vintage` is a caller-supplied stamp this module passes through untouched. Stage 0 measured
CBP's NAICS *predicate* for every window year but recorded no per-year NAICS vintage, so nothing
here derives one, and the value a caller passes is documented-not-measured until some later task
measures it.
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from ..contracts import CBP_STATE_SIZE_SCHEMA
from ..errors import SchemaMismatchError, UnknownDisclosureCodeError, UnknownSizeCodeError

CBP_URL = "https://api.census.gov/data/{year}/cbp"
VARIABLES_URL = "https://api.census.gov/data/{year}/cbp/variables.json"
EMPSZES_URL = "https://api.census.gov/data/{year}/cbp/variables/EMPSZES.json"

PARSER_VERSION = "cbp_state_size/1"

# `fetch` stores a year's variables metadata beside its data response, in the same source tree.
# Both are `.json`, and `2023_variables` yields the same reference year as `2023` under a
# four-character stem slice, so the two are told apart by this suffix and nothing else. Named here
# because this module owns CBP's file naming; `fetching` writes it and `build` skips it.
METADATA_SUFFIX = "_variables.json"


def metadata_filename(year: int) -> str:
    """The stored filename for one reference year's CBP variables metadata."""
    return f"{year}{METADATA_SUFFIX}"


def is_metadata_path(path: Path) -> bool:
    """Whether a stored CBP file is variables metadata rather than a data response."""
    return path.name.endswith(METADATA_SUFFIX)


# EMPSZES labels that name a universe rather than an employment range, so a null range is the
# honest answer for them rather than a silent default. Derived by running `size_bounds` over all
# 44 codes the 2017 values crosswalk publishes and reading which ones carry no bounds;
# `test_every_label_in_the_official_crosswalk_resolves` re-derives this set from that fixture.
# `no paid employees` / `paid employees` are deliberately here rather than read as (0, 0) and
# (1, None): CBP covers employer establishments, so those two are universe splits, and giving
# them numeric bounds would let a downstream size-share sum treat them as classes.
NOT_AN_EMPLOYMENT_RANGE: frozenset[str] = frozenset(
    {
        "All establishments",
        "Covered by administrative records",
        "Establishments with no paid employees",
        "Establishments with paid employees",
    }
)

# The EMPFLAG codes the 2017 state record layout defines as withholdings, and the one code in
# that field that is not a withholding. Documented-not-measured: only '' and 'a' were observed in
# this window's 113310 extracts, so the rest of the scheme comes from the Census record layout
# Stage 0 fetched, which `test_the_empflag_table_matches_the_fetched_2017_record_layout`
# re-derives from the shipped copy of that document. Two details the audit summary's "A-M plus S"
# gloss loses and this table keeps: there is no 'D', and 'r' means "Revised Data" -- a revised
# cell is published, so folding every nonempty flag into "suppressed" would discard a real value.
# A response carrying 'D' therefore halts, which is the intended §18.3 behaviour and not an
# omission to patch: the layout this table is derived from does not define that code.
EMPFLAG_WITHHELD_CODES: frozenset[str] = frozenset("ABCEFGHIJKLMS")
EMPFLAG_REVISED_CODE = "r"

_LESS_THAN = re.compile(r"less than (\d+) employees")
_RANGE = re.compile(r"(\d[\d,]*) to (\d[\d,]*) employees")
_OR_PAIR = re.compile(r"(\d+) or (\d+) employees")
_OR_MORE = re.compile(r"(\d[\d,]*) (?:or more|employees or more)")
_EXACT = re.compile(r"with (\d+) employees?$")


def discover_naics_predicate(variables_json: dict) -> str:
    """The NAICS predicate name this vintage actually serves.

    Read from fetched metadata, never computed from the reference year's NAICS vintage: Stage 0
    measured `NAICS2017` for every year 2017-2023, including the years whose data carry the
    NAICS 2022 vintage, so a name derived from the vintage would ask for a variable CBP does not
    serve.
    """
    names = [n for n in variables_json.get("variables", {}) if n.startswith("NAICS")]
    predicates = [n for n in names if not n.endswith("_LABEL")]
    if len(predicates) != 1:
        raise ValueError(f"expected exactly one NAICS predicate in the metadata, found {names}")
    return predicates[0]


def discover_empszes(empszes_json: dict, data_rows: list[list[str]]) -> dict[str, str]:
    """Map every establishment-size code this vintage publishes to its official label.

    Two metadata routes, both served by CBP for the vintage being read, neither a literal and
    neither borrowed from another Census product (SRC-CBP-001):

    * the variable's own values crosswalk at `variables/EMPSZES.json`, which Stage 0 measured as
      present for reference year 2017 (44 codes) and absent for 2018-2023; and
    * the `EMPSZES_LABEL` column of the data response, which CBP serves alongside `EMPSZES` for
      every year and which is therefore this vintage's own labelling of the codes it published.

    The second is a different metadata route, not a fallback to hard-coded values.
    """
    items = empszes_json.get("values", {}).get("item")
    if items:
        return {str(code): str(label) for code, label in items.items()}
    header, *rows = data_rows
    code_at = header.index("EMPSZES")
    label_at = header.index("EMPSZES_LABEL")
    return {str(row[code_at]): str(row[label_at]) for row in rows}


def build_query(year: int, predicate: str, industry: str) -> dict[str, str]:
    """The state-by-size query for one reference year.

    `LFO` and `LFO_LABEL` are both selected as output columns. Stage 0 sent `LFO=001` only as a
    filter and recorded `lfo_by_year = null` for all eight window years for exactly that reason,
    deferring the dedicated query here.
    """
    return {
        "get": (
            "NAME,EMPSZES,EMPSZES_LABEL,ESTAB,EMP,EMP_F,EMP_N,EMP_N_F,LFO,LFO_LABEL,"
            f"{predicate},{predicate}_LABEL"
        ),
        "for": "state:*",
        predicate: industry,
        "LFO": "001",
    }


def size_bounds(label: str) -> tuple[int | None, int | None]:
    """Employee-count bounds parsed from an official EMPSZES label.

    Bounds come from the label CBP publishes, not from a table typed here, so a vintage that
    changes a class's wording changes the bounds with it rather than silently disagreeing. A
    label that is neither a named universe nor a parseable range raises rather than returning a
    null range, because a silently unbounded size class is the §18.3 silent default.
    """
    if label in NOT_AN_EMPLOYMENT_RANGE:
        return (None, None)
    if (match := _LESS_THAN.search(label)) is not None:
        return (0, int(match.group(1)) - 1)
    if (match := _RANGE.search(label)) is not None:
        return (_int(match.group(1)), _int(match.group(2)))
    if (match := _OR_PAIR.search(label)) is not None:
        return (_int(match.group(1)), _int(match.group(2)))
    if (match := _OR_MORE.search(label)) is not None:
        return (_int(match.group(1)), None)
    if (match := _EXACT.search(label)) is not None:
        return (_int(match.group(1)), _int(match.group(1)))
    raise UnknownSizeCodeError(
        f"no employment bounds parse from the label {label!r}, and it is not one of the "
        f"non-range labels {sorted(NOT_AN_EMPLOYMENT_RANGE)}"
    )


def _int(digits: str) -> int:
    """An employee count from a label's thousands-separated digits."""
    return int(digits.replace(",", ""))


def _check_employment_flags(flags: list[str]) -> None:
    """Halt on an `EMP_F` value outside the documented EMPFLAG scheme (§18.3)."""
    known = EMPFLAG_WITHHELD_CODES | {EMPFLAG_REVISED_CODE, ""}
    unknown = sorted({f for f in flags if f.upper() not in {k.upper() for k in known}})
    if unknown:
        raise UnknownDisclosureCodeError(
            f"employment flags {unknown} are outside the EMPFLAG scheme the 2017 Census state "
            f"record layout documents ({sorted(EMPFLAG_WITHHELD_CODES)} withheld, "
            f"{EMPFLAG_REVISED_CODE!r} revised)"
        )


def _frame_from_rows(data_rows: list[list[str]]) -> pl.DataFrame:
    """Every response column as String, with Census's echoed predicates reconciled.

    A CBP response repeats any variable that is both selected in `get` and used as a predicate:
    the live 2023 `build_query` header carries `LFO` twice and the NAICS predicate twice. Keying
    a frame by column name would silently keep whichever copy came last, so the copies are
    compared instead and the first is kept. They agree on every row of the shipped live fixture;
    a response where they disagree is a shape this parser does not understand, so it halts.
    """
    header, *rows = data_rows
    positions: dict[str, list[int]] = {}
    for index, name in enumerate(header):
        positions.setdefault(name, []).append(index)
    for name, indices in positions.items():
        if len(indices) > 1 and any(len({row[i] for i in indices}) > 1 for row in rows):
            raise SchemaMismatchError(
                f"column {name!r} appears at positions {indices} of the CBP response header with "
                "disagreeing values; the parser cannot tell which copy is the variable"
            )
    return pl.DataFrame(
        {name: [row[indices[0]] for row in rows] for name, indices in positions.items()},
        schema={name: pl.String for name in positions},
    )


def parse_cbp_state_size(
    data_rows: list[list[str]],
    *,
    snapshot_id: str,
    reference_year: int,
    predicate: str,
    naics_vintage: str,
    regime: str,
) -> pl.DataFrame:
    """Build `cbp_state_size` from a CBP API response (§7.5, SRC-CBP-002/004).

    Every field the API returns about disclosure is preserved rather than collapsed into a
    boolean, and `reference_period` is stamped `week_including_march_12` because a CBP employment
    value is a March-centered measurement, not a QCEW identity.

    `disclosure_status` is derived from `EMP_F`, not from whether `EMP` is null. The 2017 state
    record layout defines EMPFLAG as the "Data Suppression Flag" and says a withheld cell has its
    "Employment or payroll field set to zero", and the 2017 extract bears that out: every flagged
    row publishes `EMP` as the literal `0` against three live establishments. Reading those as
    published zeros would make a suppression-coded value a true zero, which INV-003 forbids, so a
    withheld row's `employment` is null and its raw flag survives in `employment_flag`.

    A null `EMP` is also treated as withheld. No row in either window fixture has one, so that
    branch is documented-not-measured; it is the conservative reading, since a value CBP did not
    publish is certainly not a published one.

    `disclosure_status` cannot report a *dropped* cell. From reference year 2017 CBP omits a cell
    with fewer than three establishments from the release entirely, so a dropped cell is an absent
    row rather than a row carrying a status, and the absence is only visible against an expected
    key list -- which is a harmonize-layer concern, not this parser's.

    `employment_noise_range` carries `EMP_N` verbatim. Stage 0 measured that column as the literal
    string `'0'` on every row of all eight window years: the per-cell noise-magnitude flag is
    `EMP_N_F`, which `build_query` selects and which no Stage 0 response contained. The column is
    therefore preserved, not interpreted.
    """
    frame = _frame_from_rows(data_rows)
    flag = pl.col("EMP_F").fill_null("").str.strip_chars()
    _check_employment_flags(frame.select(flag).to_series().to_list())

    withheld = (
        flag.str.to_uppercase().is_in(sorted(EMPFLAG_WITHHELD_CODES)) | pl.col("EMP").is_null()
    )
    labels = frame["EMPSZES_LABEL"].to_list()
    bounds = [size_bounds(label) for label in labels]
    return (
        frame.with_columns(
            pl.lit(snapshot_id).alias("snapshot_id"),
            pl.lit(reference_year).cast(pl.Int64).alias("reference_year"),
            pl.col("state").alias("state_fips"),
            pl.col(predicate).alias("industry_code"),
            pl.lit(naics_vintage).alias("naics_vintage"),
            pl.col("LFO").alias("legal_form_code"),
            pl.col("EMPSZES").alias("size_code"),
            pl.col("EMPSZES_LABEL").alias("size_label"),
            pl.Series("size_lower", [b[0] for b in bounds], dtype=pl.Int64),
            pl.Series("size_upper", [b[1] for b in bounds], dtype=pl.Int64),
            pl.col("ESTAB").cast(pl.Int64, strict=False).alias("establishments"),
            pl.when(withheld)
            .then(None)
            .otherwise(pl.col("EMP").cast(pl.Int64, strict=False))
            .alias("employment"),
            flag.alias("employment_flag"),
            pl.col("EMP_N").fill_null("").alias("employment_noise_range"),
            pl.when(withheld)
            .then(pl.lit("suppressed"))
            .otherwise(pl.lit("published"))
            .alias("disclosure_status"),
            pl.lit(regime).alias("disclosure_regime"),
            pl.lit("week_including_march_12").alias("reference_period"),
        )
        .sort(["state_fips", "size_code"])
        .select(list(CBP_STATE_SIZE_SCHEMA))
        .cast(CBP_STATE_SIZE_SCHEMA)  # type: ignore[arg-type]
    )
