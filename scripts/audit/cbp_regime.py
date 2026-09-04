# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-CBP-003: record the CBP disclosure regime per reference year, with flag evidence derived
from the raw 113310 extracts Task 7 registered and a citation to fetched Census documentation
per year. `unknown` is a permitted, first-class answer -- Stage 1 fails closed on it.

Deviations from the brief's illustrative code, established this task, not from memory:

1. **`flag_values_by_year` (cbp_metadata's own finding) is not used as evidence -- its own
   documented coercion loses the fact this task needs.** `(row[idx[col]] or "")` collapses JSON
   `null` (no flag present) and a genuine `""` value into the same key. `flag_evidence` below
   re-parses the raw `data_113310.json` extracts Task 7 registered (verified against the actual
   bytes on disk this task: `EMP_F` is JSON `null` for the overwhelming majority of rows, plus a
   real `"a"` value on 4 of 2017's 188 rows -- nowhere is it a genuine `""`, but the distinction
   is preserved regardless via `flag_value_key`, not assumed absent).

2. **The brief's illustrative `DOC_URLS` third entry 404s.** Verified live:
   `.../technical-documentation/records-layouts.html` (plural "records") is a real 404;
   the actual page is `.../record-layouts.html` (singular). Both stay in `DOC_URLS` -- the
   brief's original, fetched for real so the 404 is a measured fact this run rather than a
   silently "fixed" typo, and the corrected URL, which is what this task's citations actually
   use. Two more URLs were added beyond the brief's three, both load-bearing for a citation
   below: the year-specific 2017 state-by-NAICS record layout (corroborates 2017's regime) and
   the generic (undated) noise/LFO record layout (defines the lowercase EMPFLAG code scheme that
   explains the literal `"a"` value observed in the 2017 extract -- cited only to interpret that
   value, never as an independent per-year source; see `REGIME_BY_YEAR["2017"]`).

3. **The regime label does not come from the flag counts.** `REGIME_BY_YEAR` is a hand-authored,
   module-level constant, grounded entirely in the fetched documentation named in each entry's
   `citation` -- never in `flag_evidence_by_year`, which is computed from data and stays a
   separate finding. Where an entry mentions an observed flag value (2017's `EMP_F == "a"`), the
   entry says explicitly that the count is corroborating detail, not the basis for the label --
   the exact inference this task's dispatch forbids ("the flags look like X, so the regime is
   X"). `validate_regime_entry` enforces at write time that every non-`unknown` regime carries a
   citation whose URL this run actually fetched successfully (mirrors the brief's Step 4 bash
   check, but as a script-time guard instead of an after-the-fact manual one).

4. **`EMP_N` is not CBP's noise-magnitude flag, and this task's own `flag_evidence_by_year` says
   so.** Confirmed live against `variables/EMP_N.json` and `variables/EMP_N_F.json`: `EMP_N` is
   labelled "Noise range for number of employees" (`predicateType: "int"`, a value, not a flag);
   `EMP_N_F` ("Flag for Noise range...", `attribute type: "FLAG"`) is the actual per-cell
   low/moderate/high indicator methodology.html describes as G/H/J, and it is absent from every
   year's 113310 x state response header this run (Task 7's query never selected it as an output
   column). Every observed `EMP_N` value in every year's extract this run is the literal string
   `"0"`. `noise_flagged_share` therefore measures "EMP_N present and not the string 0", not the
   published noise-flag distribution -- `emp_n_f_caveat` states this plainly in `findings`, not
   only in this docstring, so a reader who never opens this file still sees it next to the
   number it qualifies (the exact trap this task's dispatch names: a claim about how much a
   check proves must be as verified as a claim about data, and live beside the number, not only
   in prose a reader might skip).

5. **`regime_by_year` is seeded from `c.WINDOW_YEARS`, not from `years_available`.** The brief's
   illustrative code loops `for year in years` (i.e. `meta["findings"]["years_available"]`),
   which never contains 2024 -- the one year this task's entire justification (Stage 1 failing
   closed on an unknown regime) depends on being present. Seeding from `years_available` would
   silently produce `unknown_years == []` and defeat the task.
"""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path

import httpx

import _common as c

SOURCE = "cbp_regime"

METHOD_URL = "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html"
METHOD_SECTION = "Protecting Confidentiality > Noise Infusion"
METHOD_CITATION = f"{METHOD_URL} -- section '{METHOD_SECTION}'"
LAYOUT_2017_URL = (
    "https://www2.census.gov/programs-surveys/cbp/technical-documentation/records-layouts/"
    "2017_record_layouts/state_layout_2017.txt"
)

# Every URL this script fetches. `rel_path` is explicit per entry (never derived from the URL's
# own tail) so two URLs can never collide on one file the way `f"docs/{url.rsplit('/',1)[-1]}"`
# would for the two "state_layout.txt"-named files under different parent directories.
DOC_URLS = [
    {"url": METHOD_URL, "rel_path": "docs/methodology.html"},
    {"url": "https://www.census.gov/programs-surveys/cbp/technical-documentation.html",
     "rel_path": "docs/technical-documentation.html"},
    # The brief's illustrative URL, verbatim -- kept and fetched for real so its 404 is a
    # measured fact this run (module docstring point 2), not a silently corrected typo.
    {"url": "https://www.census.gov/programs-surveys/cbp/technical-documentation/"
            "records-layouts.html", "rel_path": "docs/records-layouts.html"},
    # The real page (singular "record") -- what record-layouts navigation and this task's
    # discovery of the per-year layout files actually rests on.
    {"url": "https://www.census.gov/programs-surveys/cbp/technical-documentation/"
            "record-layouts.html", "rel_path": "docs/record-layouts.html"},
    {"url": LAYOUT_2017_URL, "rel_path": "docs/2017_state_layout_2017.txt"},
    {"url": "https://www2.census.gov/programs-surveys/cbp/technical-documentation/"
            "records-layouts/noise-layout/state_x_lfo_layout.txt",
     "rel_path": "docs/noise_state_x_lfo_layout.txt"},
]
assert len({spec["rel_path"] for spec in DOC_URLS}) == len(DOC_URLS), (
    "DOC_URLS rel_paths must be pairwise distinct -- two URLs writing the same file would let "
    "the second record_extract call silently overwrite the first's bytes"
)

_URL_RE = re.compile(r"https?://\S+")

# The four CBP API variables this task fetches metadata for, per available year, to ground
# emp_n_f_caveat -- and variable_definition_summary's has_values_crosswalk claim about all four
# -- in a real fetch rather than a claim carried over from prior research (module docstring
# point 4). EMP itself (the base value EMP_F flags) is included so "none of these four carry a
# values crosswalk" is checked by this run's own fetches, not asserted from memory of it.
FLAG_VARIABLES = ("EMP", "EMP_F", "EMP_N", "EMP_N_F")


def flag_value_key(raw: str | None) -> str:
    """A dict key that keeps JSON `null` (no flag present) and a genuine `""` (a flag whose
    value is empty) distinct -- the coercion `cbp_metadata.py`'s `flag_values_by_year` performs
    (`row or ""`) loses this distinction, which is exactly the fact this task needs (module
    docstring point 1)."""
    return "null" if raw is None else raw


def flag_evidence(header: list[str], body: list[list]) -> dict:
    """Per-year flag evidence computed directly from one year's raw `data_113310.json` payload
    (already split into header/body). `EMP_F`/`EMP_N` keys are omitted entirely (not `{}`) when
    the column itself is absent from the header -- attempt 3's shape in `cbp_metadata.py` drops
    `EMPSZES` but keeps `EMP_F`/`EMP_N`; a future response shape that also drops these must read
    as "not measured", not "measured, zero distinct values", mirroring
    `empszes_pairs_from_rows`'s None-vs-[] discipline in that script."""
    idx = {name: i for i, name in enumerate(header)}
    total = len(body)
    out: dict = {}
    for col in ("EMP_F", "EMP_N"):
        if col in idx:
            out[col] = dict(Counter(flag_value_key(row[idx[col]]) for row in body))
    suppressed = sum(1 for row in body if "EMP_F" in idx and row[idx["EMP_F"]] is not None)
    noised = sum(1 for row in body if "EMP_N" in idx and row[idx["EMP_N"]] not in (None, "0"))
    out["suppressed_share"] = suppressed / total if total else 0.0
    out["noise_flagged_share"] = noised / total if total else 0.0
    out["emp_n_f_in_response"] = "EMP_N_F" in idx
    return out


def citation_url(citation: str) -> str:
    """The leading URL out of a `"<url> -- <section>"` citation string."""
    match = _URL_RE.search(citation)
    if not match:
        raise ValueError(f"citation has no URL: {citation!r}")
    return match.group(0)


def validate_regime_entry(year: str, entry: dict, fetched_ok_urls: set[str]) -> None:
    """The mechanical version of the brief's Step 4 bash check, enforced at write time: every
    year needs a non-blank `evidence`; every non-`unknown` regime needs a `citation`, and that
    citation's URL must be one this run actually fetched successfully -- not merely typed."""
    if not entry.get("evidence"):
        raise ValueError(f"{year}: evidence must not be blank")
    if entry["regime"] != "unknown":
        if not entry.get("citation"):
            raise ValueError(f"{year}: a non-unknown regime needs a citation")
        url = citation_url(entry["citation"])
        if url not in fetched_ok_urls:
            raise ValueError(
                f"{year}: citation URL {url!r} was not among this run's successfully fetched "
                "documentation URLs"
            )


def _no_year_specific_doc_evidence(year: int) -> str:
    """2019, 2020, 2021, 2022 and 2023 share the same documented basis -- not a copy-pasted claim, but
    the honest state of the evidence: no year-labeled record layout exists for any of them. Two
    distinct kinds of check back this, named separately so neither is overstated as the other:
    (a) this script's own `DOC_URLS` fetch list, which carries only one year-specific record
    layout (2017's, at `LAYOUT_2017_URL`) -- verifiable directly from `documentation_fetched`
    every run; and (b) additional manual verification performed while authoring this entry
    (live GETs against the Census record-layouts naming pattern for every window year, outside
    this script's own fetch list, not re-run by `main()`), which found that 2018 and 2020 also
    have a year-labeled file but of the wrong product (the state ALL-NAICS-totals layout, not
    the state-by-NAICS layout this task's own extracts use, so neither corroborates a NAICS-level
    regime for its own year), and that 2019/2021/2022/2023 have no year-labeled file of either
    product at all. (b) is not something a future re-run of this script re-verifies -- if Census
    later archives a 2019-2023 file, this entry would not know until a human checks again. Each
    entry still names its own year, so this is a per-year rendering, not a byte-identical string
    reused across years (see
    `test_regime_by_year_no_two_non_unknown_years_share_byte_identical_evidence`)."""
    return (
        f"No CBP documentation specific to reference year {year} was found among the routes "
        f"this script's own DOC_URLS fetches (see documentation_fetched -- only 2017 has a "
        "year-specific record-layout URL in that list). Additional manual verification while "
        "authoring this entry (live GETs against the Census record-layouts naming pattern for "
        f"every window year, outside this script's own fetch list) found that, unlike 2017, no "
        f"year-labeled record-layout file for {year} is archived at the Census record-layouts "
        "index at all: only 2017, 2018 and 2020 have one, and the 2018/2020 files describe the "
        "state ALL-NAICS-totals product rather than the state-by-NAICS product this task's own "
        "extracts use, so neither would have corroborated a NAICS-level regime for its own year "
        "even if it had been in scope. This entry therefore rests entirely on methodology.html's "
        "continuing statements -- noise "
        "infusion 'since reference year 2007' and EMPFLAG discontinued 'beginning in reference "
        f"year 2018' -- read forward through {year} with no later documented reversal found. "
        "methodology.html itself carries a banner, current as of its own June 18, 2026 "
        "revision, stating its content 'is no longer current' pending a U.S. Department of "
        "Commerce administrative order prohibiting the use of noise infusion; that notice "
        "concerns Census's prospective/current approach following a recent order, not a "
        "retraction of the dated 2007-2018 historical statements this entry relies on -- but it "
        f"means {year}'s label carries less independent corroboration than 2017's or 2018's and "
        "should be weighted accordingly, not read as equally certain."
    )


# Hand-authored by the auditor from the documentation fetched this run (see `citation` per
# entry and `documentation_fetched` in the written summary for the actual HTTP status of each
# fetch). This dict -- and only this dict -- is NOT computed from `data_113310.json` or from
# `flag_evidence_by_year`; every other finding in this module is derived. Where an entry
# mentions an observed flag value, it says explicitly that the value is corroborating detail,
# never the basis for the label (module docstring point 3) -- the regime rests on the cited
# Census documentation alone.
REGIME_BY_YEAR: dict[str, dict] = {
    "2017": {
        "regime": "noise_infusion_plus_suppression",
        "citation": METHOD_CITATION,
        "evidence": (
            "2017: fetched methodology.html (section 'Protecting Confidentiality > Noise "
            "Infusion') states CBP has used noise infusion since reference year 2007, and "
            "separately that reference year 2017 was the last year the EMPFLAG "
            "employment-size-range suppression flag was used ('The use of EMPFLAG was "
            "discontinued beginning in reference year 2018') and the first year a cell with "
            "fewer than three establishments is dropped from the release rather than published "
            "with a flag ('Beginning with reference year 2017, a cell is only published if it "
            "contains three or more establishments'). Both a noise-infusion mechanism and an "
            "EMPFLAG-based suppression mechanism are therefore documented as active for 2017, "
            "distinguishing it from every later window year. Corroborated by the year-specific "
            f"layout fetched this run at {LAYOUT_2017_URL}, which documents both EMPFLAG "
            "(size-range suppression codes A-M, plus 'S' for below-publication-standard "
            "withholding) and per-cell noise flags (G/H/J/N/S) as live fields on the "
            "state-by-NAICS file for this year. The 2017 113310 x state extract carries a small "
            "minority of rows with EMP_F == 'a' and no flag on the rest (a lowercase "
            "employment-size-range code, consistent with the fetched noise-layout state_x_lfo "
            "record layout's a=0-19-employee scheme; exact counts are in "
            "flag_evidence_by_year['2017'], computed fresh this run, not restated here as a "
            "number that could go stale against this static entry) -- reported as corroborating "
            "detail only, not as the basis for this regime label; the label rests on the two "
            "Census documents named above, not on this count."
        ),
    },
    "2018": {
        "regime": "noise_infusion",
        "citation": METHOD_CITATION,
        "evidence": (
            "2018: the same methodology.html passage cited for 2017 states 'The use of EMPFLAG "
            "was discontinued beginning in reference year 2018 and a noisy employment cell "
            "value is provided' -- naming 2018 explicitly as the year the EMPFLAG suppression "
            "flag stopped, leaving noise infusion (documented active continuously since "
            "reference year 2007) as the sole per-cell disclosure mechanism the page names for "
            "published cells from 2018 forward. The beginning-2017 rule dropping cells with "
            "fewer than three establishments from the release is not stated to have changed and "
            "remains documented as active. Every row of the 2018 113310 x state extract carries "
            "EMP_F == null (see flag_evidence_by_year['2018'], computed fresh this run), "
            "consistent with EMPFLAG's documented discontinuation -- reported as corroborating "
            "detail only, not as the basis for this label."
        ),
    },
    "2019": {"regime": "noise_infusion", "citation": METHOD_CITATION,
              "evidence": _no_year_specific_doc_evidence(2019)},
    "2020": {"regime": "noise_infusion", "citation": METHOD_CITATION,
              "evidence": _no_year_specific_doc_evidence(2020)},
    "2021": {"regime": "noise_infusion", "citation": METHOD_CITATION,
              "evidence": _no_year_specific_doc_evidence(2021)},
    "2022": {"regime": "noise_infusion", "citation": METHOD_CITATION,
              "evidence": _no_year_specific_doc_evidence(2022)},
    "2023": {"regime": "noise_infusion", "citation": METHOD_CITATION,
              "evidence": _no_year_specific_doc_evidence(2023)},
    "2024": {
        "regime": "unknown",
        "citation": "",
        "evidence": (
            "2024: not obtainable -- cbp_metadata's own dataset probe "
            "(dataset_probe_status_by_year) recorded a non-200 status for reference year 2024 "
            "and 2024 is absent from years_available; Task 7's report identifies this as a real "
            "HTTP 404 from cbp.json, not a transport blip. No 2024 CBP dataset exists to fetch "
            "a 2024-specific disclosure-methodology statement from, and the documentation "
            "fetched this run for 2017-2023 cannot be assumed to cover a year that postdates "
            "it: methodology.html's own banner (current as of its June 18, 2026 revision) "
            "states its regime description 'is no longer current' pending a U.S. Department of "
            "Commerce administrative order prohibiting the use of noise infusion, so even a "
            "hypothetical future 2024 release cannot be assumed to carry forward the 2018-2023 "
            "regime found above."
        ),
    },
}
assert set(REGIME_BY_YEAR) == {str(y) for y in c.WINDOW_YEARS}, (
    "REGIME_BY_YEAR must carry exactly one hand-authored entry per c.WINDOW_YEARS -- a mismatch "
    "means either this literal or c.WINDOW_YEARS changed without the other being reviewed"
)


def variable_definition_summary(payload: dict) -> dict:
    """The fields this task actually needs out of one `variables/{VAR}.json` payload -- the
    label (whitespace-stripped: the real live `EMP_N_F` response carries a trailing space,
    confirmed this task), what base variable it's an attribute of (`None` for a base variable),
    its attribute type, and whether it carries its own `values.item` code-list crosswalk (none
    of `EMP`, `EMP_F`, `EMP_N`, `EMP_N_F` do, confirmed live for every available year -- unlike
    `EMPSZES`'s 2017 crosswalk, which `cbp_metadata.py` already found and recorded)."""
    values = payload.get("values")
    has_crosswalk = isinstance(values, dict) and isinstance(values.get("item"), dict)
    return {
        "label": (payload.get("label") or "").strip(),
        "attribute_of": payload.get("attribute of"),
        "attribute_type": payload.get("attribute type"),
        "has_values_crosswalk": has_crosswalk,
    }


def emp_n_f_caveat(*, observed_any: bool, emp_n_f_label: str | None) -> str:
    """Findings-level statement of module docstring point 4, computed from what this run
    actually observed (`observed_any`, aggregated over `flag_evidence_by_year`'s
    `emp_n_f_in_response` per year) and actually fetched (`emp_n_f_label`, from
    `variable_definition_summary` against a real `variables/EMP_N_F.json` response) -- not
    typed from memory of prior research. This is what keeps `noise_flagged_share` from silently
    contradicting a `noise_infusion` regime label above it (a share of 0.0 next to a label that
    says noise infusion applies is exactly the kind of derived-number-beside-authored-label
    contradiction this task's dispatch names). `emp_n_f_label=None` means this run's own
    `variables/EMP_N_F.json` fetch failed for the representative year -- must read as "not
    fetched", never render as if the label itself were the string 'None'."""
    label_clause = (
        "which this run could not fetch (variables/EMP_N_F.json did not return 200 for the "
        "representative year)" if emp_n_f_label is None else
        f"labelled {emp_n_f_label!r} in this run's fetched variable metadata"
    )
    if observed_any:
        return (
            f"EMP_N_F ({label_clause}) -- CBP's actual per-cell noise-magnitude flag, distinct "
            "from EMP_N itself -- appears in at least one year's 113310 x state response header "
            "this run; flag_evidence_by_year's EMP_N-derived noise_flagged_share can be "
            "cross-checked against it directly for that year."
        )
    return (
        f"EMP_N_F ({label_clause}) is CBP's actual per-cell noise-magnitude flag (documented in "
        "methodology.html's Noise Infusion section as low/moderate/high, G/H/J) -- distinct "
        "from EMP_N, which is labelled 'Noise range for number of employees' and is int-typed, "
        "not the flag itself. EMP_N_F does not appear in any year's 113310 x state response "
        "header this run (Task 7's query never selected it as an output column). Every observed "
        "EMP_N value in every year's extract this run is the literal string '0'. "
        "noise_flagged_share in flag_evidence_by_year therefore measures only 'EMP_N present "
        "and not the string 0', not the published noise-flag distribution, and must not be read "
        "as evidence that no noise was applied in a year labelled noise_infusion above -- the "
        "regime label does not rest on this share."
    )


def fetch_variable_definition(
    client: httpx.Client, year: int, variable: str, extracts: list
) -> dict | None:
    """GET `variables/{variable}.json` for one year (keyless, like `cbp_metadata.py`'s
    equivalent routes) and record the extract. Returns `None` on any non-2xx instead of raising
    -- the same defensive shape `cbp_metadata.py`'s `fetch_json_or_none` uses for keyless
    metadata routes, added there only after a live 404 crashed an earlier round of that script."""
    url = f"https://api.census.gov/data/{year}/cbp/variables/{variable}.json"
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError:
        return None
    extracts.append(c.record_extract(
        SOURCE, url, f"variables/{year}_{variable}.json", resp.content))
    return resp.json()


def main() -> None:
    client = c.build_client()
    meta = c.load_summary("cbp_metadata")
    mfindings = meta["findings"]
    years_available = mfindings["years_available"]
    probe_status = mfindings["dataset_probe_status_by_year"]

    if 2024 in years_available or probe_status.get("2024") == 200:
        raise RuntimeError(
            "REGIME_BY_YEAR['2024'] is hand-authored as unknown because a prior cbp_metadata "
            "run found no 2024 CBP data (a confirmed 404). This run's cbp_metadata now reports "
            "2024 as available, so that authored entry is stale and must be re-reviewed by hand "
            "-- refusing to silently keep asserting 'not obtainable' against evidence that no "
            "longer supports it."
        )

    # This run's disk state for cbp_regime's own fetched docs is always exactly what this run
    # itself wrote -- same discipline cbp_metadata.py's fix round 3 adopted for its per-year
    # directories, applied here to the one directory this script owns.
    docs_dir = c.AUDIT_ROOT / SOURCE / "docs"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    variables_dir = c.AUDIT_ROOT / SOURCE / "variables"
    if variables_dir.exists():
        shutil.rmtree(variables_dir)

    extracts: list[c.ExtractRecord] = []
    docs: list[dict] = []
    for spec in DOC_URLS:
        try:
            resp = c.request(client, spec["url"])
        except httpx.HTTPStatusError as exc:
            docs.append({"url": spec["url"], "http_status": exc.response.status_code})
            continue
        docs.append({"url": spec["url"], "http_status": resp.status_code})
        extracts.append(c.record_extract(SOURCE, spec["url"], spec["rel_path"], resp.content))
    fetched_ok_urls = {d["url"] for d in docs if d["http_status"] == 200}
    # Derived, not hardcoded: "verified" only if the one URL every regime_by_year citation rests
    # on actually returned 200 this run. The records-layouts.html entry is a deliberate negative
    # control (module docstring point 2) and must not drag this down even though it 404s.
    access_status = "verified" if METHOD_URL in fetched_ok_urls else "not_obtainable"
    access_reason = (
        None if access_status == "verified" else
        f"{METHOD_URL} did not return 200 this run (see documentation_fetched); every "
        "regime_by_year citation rests on it"
    )
    if access_status != "verified":
        # A louder, more specific failure than letting the loop below raise a generic
        # "citation URL not fetched" ValueError once it reaches whichever entry cites this URL
        # first -- every non-unknown entry cites it, so there is nothing this run could still
        # usefully assert.
        raise RuntimeError(access_reason)

    # Flag evidence: derived directly from the raw data_113310.json extracts Task 7 registered,
    # never from cbp_metadata's own flag_values_by_year (module docstring point 1).
    flag_evidence_by_year: dict[str, dict | None] = {}
    for year in c.WINDOW_YEARS:
        y = str(year)
        path = next(
            (e["path"] for e in meta["extracts"] if e["path"].endswith(f"{year}/data_113310.json")),
            None,
        )
        if path is None:
            flag_evidence_by_year[y] = None
            continue
        payload = json.loads(Path(path).read_text())
        header, body = payload[0], payload[1:]
        flag_evidence_by_year[y] = flag_evidence(header, body)

    # Variable metadata: fetched fresh this run (keyless) to ground emp_n_f_caveat in a real
    # fetch rather than a claim carried over from prior research (module docstring point 4).
    var_defs_by_year: dict[str, dict | None] = {}
    for year in c.WINDOW_YEARS:
        y = str(year)
        if year not in years_available:
            var_defs_by_year[y] = None
            continue
        year_defs = {}
        for variable in FLAG_VARIABLES:
            payload = fetch_variable_definition(client, year, variable, extracts)
            year_defs[variable] = (
                variable_definition_summary(payload) if payload is not None else None
            )
        var_defs_by_year[y] = year_defs

    observed_any_emp_n_f = any(
        v.get("emp_n_f_in_response") for v in flag_evidence_by_year.values() if v
    )
    latest_year = str(max(years_available))
    latest_defs = var_defs_by_year.get(latest_year) or {}
    emp_n_f_def = latest_defs.get("EMP_N_F")
    caveat = emp_n_f_caveat(
        observed_any=observed_any_emp_n_f,
        emp_n_f_label=emp_n_f_def["label"] if emp_n_f_def else None,
    )

    for year, entry in REGIME_BY_YEAR.items():
        validate_regime_entry(year, entry, fetched_ok_urls)
    unknown_years = sorted(int(y) for y, v in REGIME_BY_YEAR.items() if v["regime"] == "unknown")

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(years_available)) if years_available else "",
            "published_end": str(max(years_available)) if years_available else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": meta["coverage_span"]["covered"],
            "uncovered": meta["coverage_span"]["uncovered"],
        },
        access={
            "route": "; ".join(spec["url"] for spec in DOC_URLS), "status": access_status,
            "reason": access_reason,
        },
        extracts=extracts,
        findings={
            "regime_by_year": REGIME_BY_YEAR,
            "unknown_years": unknown_years,
            "flag_evidence_by_year": flag_evidence_by_year,
            "documentation_fetched": docs,
            "emp_flag_variable_definitions_by_year": var_defs_by_year,
            "emp_n_f_caveat": caveat,
        },
    )
    for year, ev in flag_evidence_by_year.items():
        if ev is None:
            print(year, "no 113310 extract this run")
            continue
        print(year, "suppressed", round(ev["suppressed_share"], 3),
              "noise-flagged", round(ev["noise_flagged_share"], 3),
              "EMP_F values", sorted(ev.get("EMP_F", {})),
              "| regime:", REGIME_BY_YEAR[year]["regime"])
    print("unknown_years:", unknown_years)


if __name__ == "__main__":
    main()
