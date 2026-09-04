# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-FOR-001/002/003: record access verdicts for FIA (`/fullreport` parameters, sampling
error, evaluation vintage) and TPO harvest-origin data. `not_obtainable` is a legitimate
verdict, but only when it is earned by the probes recorded here -- never inherited from a
prior review's inability to find a URL, and never from Appendix A already shipping
`tpo.enabled: false` / `fia.enabled: false`.

This run found both sources reachable. FIA's `/fullreport` returns a real, machine-readable
estimate (with sampling error) once called with the parameters its own doc page marks required
-- the brief's illustrative call omitted all four and got back a 200-status EVALIDator *error*
page, not a report. Which estimate it returns is not incidental and is never left implicit
here: the response names its own measure in `metadata.numEstDesc`/`metadata.estMeta`, and the
access verdict quotes that name, because "the endpoint answers" and "the endpoint answers with
the harvest-origin measure SS2.2 requires" are two different claims. Whether FIA publishes a
harvest-origin measure *at all* is settled separately, by enumerating the estimate attributes
its own `/fullreport/parameters/snum` catalog lists. TPO's harvest-origin data is not at any of
the brief's three candidate URLs, but two hops from the first of them
(`research.fs.usda.gov/programs/nrum` -> its own "data downloads" page -> a public Box folder)
sits a real, county-level, per-state production table, fetchable once you use Box's
undocumented legacy download redirect instead of its modern (session-gated) share URL. See
`main()` for the full probe sequence and `tests/audit/test_forest_sources.py` for what is
pinned about each parsing step.

Raw-retention rule, specific to this script (ruling D-B). The obvious default for a
body-recording site is to keep the bytes only on a status of 200; what every other Stage 0
script does is that script's business and is not asserted here, because a claim about other
files dates the moment one of them changes. This one records a body whenever the endpoint
answered at all, whatever the status, and stamps each extract with the status it
actually carried -- because on an access-verdict probe the non-200 body IS the evidence: a 404
page, a 403 page and an empty 200 are three different verdicts, and only the retained bytes
tell them apart. A transport failure yields no body and so registers no extract; its evidence
is the probe record's `outcome` field instead. `compose_retention_rule` restates this inside
both written summaries, with counts derived from the run, so a reader of the artifacts (not
just of this file, or of a commit message) sees the rule and its scope.
"""

from __future__ import annotations

import html as html_module
import io
import json
import re
import time
import zipfile
from collections.abc import Callable

import httpx

import _common as c

SOURCE_FIA = "fia"
SOURCE_TPO = "tpo"

FIA_DOC = "https://apps.fs.usda.gov/fiadb-api/"
FIA_FULLREPORT = "https://apps.fs.usda.gov/fiadb-api/fullreport"
FIA_WC_PARAMETERS = "https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/wc"
# `snum*` is the required parameter that selects WHICH estimate attribute /fullreport returns,
# and this is its catalog. Probed so the verdict can say whether FIA publishes a harvest-origin
# (removals) attribute at all -- a capability question the successful /fullreport call, which
# returned one area attribute, cannot answer by itself.
FIA_SNUM_PARAMETERS = "https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/snum"
# The brief's own illustrative probe: outputFormat only, none of the doc page's four
# required parameters (wc*, snum*, rselected*, cselected*). Kept and probed so the finding
# that it returns a 200-status *error* page is recorded, not just asserted in this docstring.
FIA_NAIVE_PARAMS = {"outputFormat": "JSON"}
# The doc page's own documented Python-GET usage example (verbatim from the fetched page),
# not invented: it is the one call this run trusts to prove the endpoint returns real data.
FIA_REAL_PARAMS = {
    "rselected": "Land Use - Major",
    "cselected": "Land use",
    "snum": "79",
    "wc": "102020",
    "outputFormat": "NJSON",
}
# Named in the dispatch's lead table as the crux transport failure. Probed here as its own
# FIA route -- kept separate from the /fullreport verdict, per the three-outcome distinction.
FIA_DATAMART_CANDIDATES = (
    "https://apps.fs.usda.gov/fia/datamart/CSV/",
    "https://apps.fs.usda.gov/fia/datamart/datamart.html",
)
FIA_DATAMART_ATTEMPTS = 3
FIA_DATAMART_WAIT_SECONDS = 3.0
# Two more routes from the dispatch's lead table, each a single probe (no retry: both answer
# with a real status, not a transport failure).
FIA_OTHER_ROUTES = (
    "https://apps.fs.usda.gov/Evalidator/evalidator.jsp",
    "https://www.fs.usda.gov/research/programs/fia",
)

TPO_CANDIDATES = (
    "https://research.fs.usda.gov/programs/nrum",
    (
        "https://research.fs.usda.gov/products/dataandtools/"
        "timber-products-output-tpo-interactive-reporting-tool"
    ),
    "https://apps.fs.usda.gov/fiadb-api/tpo",
)
# Discovered by following links from the two research.fs.usda.gov pages above -- neither
# brief candidate links to a raw file; both link to further pages, and the brief's candidate
# list never followed them. Kept as its own tuple (not merged into TPO_CANDIDATES) so
# route_probes can show which URLs came from the brief and which were found by this run.
TPO_DISCOVERED_ROUTES = (
    # Linked from the TPO interactive-tool page: the actual "Interactive Reporting Tool".
    "https://public.tableau.com/views/TPOREPORTINGTOOL/MakeSelection?%3AshowVizHome=no",
    # Linked from the nrum program page: "National Resource Use Monitoring - Data Downloads".
    (
        "https://research.fs.usda.gov/products/dataandtools/"
        "national-resource-use-monitoring-data-downloads"
    ),
)
# "/xml"/"+xml" rather than a bare "xml": both real Office Open XML content types this run
# observed -- xlsx's ".spreadsheetml.sheet" and docx's ".wordprocessingml.document" -- contain
# the literal substring "xml" inside "openXMLformats" itself, so a bare "xml" test would flag
# the docx data-dictionary file as machine-readable data too (verified: it does, in a first
# draft of this constant that this task's own test suite caught).
MACHINE_TYPES = ("json", "csv", "/xml", "+xml", "zip", "excel", "spreadsheet")

# The public Box folder's share URL is NOT hardcoded here -- `discover_box_share_url` reads
# it from the fetched NRUM data-downloads page's own markup each run, the same discipline
# this codebase applies to every other code-to-value mapping (QCEW's own_code, CES's industry
# level selector, ...): a source identifier a fetched page supplies is read from that page,
# not carried in memory. Box's platform-wide legacy download endpoint is a fixed prefix, not
# specific to this share, so it stays a constant.
BOX_LEGACY_DOWNLOAD_BASE = "https://usfs-public.app.box.com/index.php"

WINDOW_YEARS = c.WINDOW_YEARS


# --- pure helpers: probes and classification ------------------------------------------------


def classify_probe(status: int, nbytes: int) -> str:
    """The three access outcomes the dispatch requires kept distinct: `_common.probe`'s
    `(0, 0)` sentinel means no response reached us at all (`transport_failure`) -- the
    weakest possible basis for `not_obtainable`, never conflated with a real `404`
    (`not_found`, the resource is confirmed absent) or a `200` (`reachable`, though not
    necessarily *usable* -- see `FIA_NAIVE_PARAMS`'s 200-status error page). Anything else
    (403, 301, 500, ...) is `other_status`: a real answer that is neither of the above."""
    if status == 0 and nbytes == 0:
        return "transport_failure"
    if status == 404:
        return "not_found"
    if status == 200:
        return "reachable"
    return "other_status"


def is_machine_readable(content_type: str) -> bool:
    ctype = (content_type or "").lower()
    return any(t in ctype for t in MACHINE_TYPES)


def probe_url(client: httpx.Client, url: str, *, params: dict | None = None) -> dict:
    """Like `_common.probe`, but keeps the response body and content-type -- needed for
    `record_extract` and for `route_probes`' `content_type`/`machine_readable` fields, which
    `_common.probe`'s `(status, bytes)` return does not carry. Catches the same
    `httpx.TransportError` family `_common.probe` does, with the same `(0, 0)` sentinel."""
    try:
        resp = client.get(url, params=params)
    except httpx.TransportError:
        return {"url": url, "http_status": 0, "bytes": 0, "content_type": "", "body": b""}
    return {
        "url": url,
        "http_status": resp.status_code,
        "bytes": len(resp.content),
        "content_type": resp.headers.get("content-type", ""),
        "body": resp.content,
    }


def answered_with_body(res: dict) -> bool:
    """Ruling D-B's retention gate: keep the bytes whenever the endpoint answered, whatever the
    status. A transport failure (`http_status == 0`) produced no response at all and so has no
    body to keep; its evidence is the probe record's `outcome` field instead."""
    return res["http_status"] != 0 and bool(res["body"])


def retain_body(extracts: list, source: str, res: dict, rel_path: str) -> None:
    """Append `res`'s body to `extracts` stamped with the status it actually carried -- never
    coerced to 200, which would erase the very distinction the retained non-200 body exists to
    record."""
    if answered_with_body(res):
        extracts.append(c.record_extract(
            source, res["url"], rel_path, res["body"], http_status=res["http_status"]))


def scannable_text_page(res: dict) -> bool:
    """Whether a probe's body joins the term-scan corpus. Deliberately the retention gate AND
    a 200, not the status alone: `industry_concept_scan` names its corpus as the pages that
    "answered with a status-200 body and [are] hashed", so every page it counts must also be a
    registered extract, and `retain_body` refuses an empty body. A status-200 response with no
    body would otherwise be counted in a sentence no extract backs. The implication runs one
    way only, and the composed sentences say so: `retain_body` is called on routes this gate is
    never offered (`other_route_*`), so being fetched and hashed does not put a page in the
    corpus, and such a route answering 200 is hashed without ever being scanned."""
    return answered_with_body(res) and res["http_status"] == 200


def probe_record(res: dict, origin: str) -> dict:
    """One `route_probes` entry. Carries `classify_probe`'s outcome alongside the raw status so
    a reader is never left to classify a bare `http_status: 0` themselves -- the three-outcome
    distinction is the point of recording these at all."""
    return {
        "url": res["url"],
        "http_status": res["http_status"],
        "bytes": res["bytes"],
        "content_type": res["content_type"],
        "machine_readable": is_machine_readable(res["content_type"]),
        "outcome": classify_probe(res["http_status"], res["bytes"]),
        "origin": origin,
    }


def probe_with_retries(
    probe_fn: Callable[[], tuple[int, int]],
    *,
    url: str,
    attempts: int,
    wait_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict:
    """Bounded, spaced retries for a route that resets rather than answers -- "be a good
    citizen against USDA hosts": at most `attempts` requests, `wait_seconds` apart, stopping
    the moment any attempt gets a real response (status != 0). Every attempt's raw
    `(status, bytes)` and its `classify_probe` outcome are recorded, plus the wall-clock span
    actually spent, so a `transport_failure` verdict carries its own retry evidence rather
    than resting on a single try."""
    started = now()
    attempt_records = []
    for attempt_no in range(attempts):
        status, nbytes = probe_fn()
        attempt_records.append({
            "attempt": attempt_no + 1,
            "http_status": status,
            "bytes": nbytes,
            "outcome": classify_probe(status, nbytes),
        })
        if status != 0 or attempt_no == attempts - 1:
            break
        sleep(wait_seconds)
    return {
        "url": url,
        "attempts": attempt_records,
        "elapsed_seconds": round(now() - started, 3),
    }


# --- pure helpers: FIA doc-page and response parsing -----------------------------------------


def parse_fia_doc_parameters(html: str) -> list[dict]:
    """Derive the `/fullreport` parameter list from the doc page's own
    `<table title="Parameter descriptions">` -- not a hardcoded name whitelist. The brief's
    illustrative code matched a fixed regex alternation naming eight parameters, two of which
    (`schemaName`, `whereClause`) do not appear anywhere on the live page (verified: zero
    hits), and it missed thirteen real ones the table documents. Reading the table's actual
    rows, rather than guessing names, cannot repeat either failure mode."""
    match = re.search(r'<table title="Parameter descriptions">(.*?)</table>', html, re.DOTALL)
    if not match:
        return []
    params = []
    for row in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.DOTALL):
        name_match = re.search(r"<th[^>]*>(.*?)</th>", row, re.DOTALL)
        desc_match = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not name_match or not desc_match:
            continue
        raw_name = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()
        desc = re.sub(r"<[^>]+>", " ", desc_match.group(1))
        desc = html_module.unescape(re.sub(r"\s+", " ", desc)).strip()
        params.append({
            "parameter": raw_name.rstrip("*"),
            # A trailing "*" flags a required parameter on this page (lat*/lon*/radius* are
            # the one exception -- required only "FOR CIRCULAR ESTIMATES ONLY", per that row's
            # own description text -- left visible in `description` rather than special-cased
            # here, since this function only reports what the markup structurally encodes).
            "required": raw_name.endswith("*"),
            "description": desc,
        })
    return params


def sampling_error_field(estimates: list[dict]) -> str | None:
    """SRC-FOR-002: does this response carry sampling error "when available"? Checked against
    the real `/fullreport` response's `estimates` rows fetched this run, not asserted from
    documentation -- the doc page's Parameter Descriptions table says nothing about response
    field names at all. `SE` and `SE_PERCENT` are the field names this run actually observed;
    the rest of the candidate list is FIA's own EVALIDator terminology for the same concept,
    kept as a fallback in case a different report type omits `SE`."""
    if not estimates:
        return None
    candidates = ("SE", "SE_PERCENT", "SAMPLING_ERROR", "STD_ERROR", "ESTIMATE_SE")
    keys = estimates[0].keys()
    return next((candidate for candidate in candidates if candidate in keys), None)


def evaluation_vintage_field(metadata: dict) -> str | None:
    """SRC-FOR-003: the field naming the evaluation vintage / survey cycle. `evalGrps` is what
    this run's real response actually returned in `metadata` (echoing the `wc` request
    parameter, itself the evaluation group code -- state FIPS + 4-digit inventory year, per
    the doc page). The brief's candidate list (`EVALID|evalid|EVAL_GRP|INVYR|SURVEY_CYCLE`)
    does not contain this exact key and would have missed it."""
    if not metadata:
        return None
    candidates = ("evalGrps", "EVALID", "EVAL_GRP", "INVYR", "SURVEY_CYCLE")
    return next((candidate for candidate in candidates if candidate in metadata), None)


def parse_wc_evaluation_index(html: str) -> dict:
    """Parse `/fullreport/parameters/wc`: one row per (state, EVALID) -- the evaluation
    vintage catalog `wc*` itself is drawn from. Malformed-markup note, verified against the
    live 344 KB page: every row opens with `<th scope=row ...>` but the table never emits a
    matching `<tr>` opener (grepped directly: 1139 `</tr>` closers, zero `<tr>` openers), so
    rows are recovered by splitting the tbody on `</tr>`, not by matching a `<tr>...</tr>`
    pair -- the latter would silently find nothing."""
    body_match = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    if not body_match:
        return {"states": [], "year_min": None, "year_max": None, "row_count": 0}
    states: set[str] = set()
    years: list[int] = []
    row_count = 0
    for row in body_match.group(1).split("</tr>"):
        cells = re.findall(r"<t[hd][^>]*>([^<]*)</t[hd]>", row)
        if len(cells) != 8:
            continue
        row_count += 1
        states.add(cells[0].strip())
        for year_text in cells[4].split(";"):
            year_text = year_text.strip()
            if year_text.isdigit():
                years.append(int(year_text))
    return {
        "states": sorted(states),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "row_count": row_count,
    }


# The `snum` catalog's own ESTIMATE_GRP_DESCR wording. FIA separates three removals concepts:
# "Annual harvest removals *" (trees removed by harvesting), "Annual other removals *"
# (removals from land-use change and similar), and the combined "Annual removals *". SS2.2
# asks for harvest origin, so only the first is a harvest-origin measure -- a bare `removals`
# predicate would count all three and overstate what the catalog offers.
HARVEST_REMOVALS_GROUP_PATTERN = re.compile(r"(?i)\bharvest removals\b")
REMOVALS_GROUP_PATTERN = re.compile(r"(?i)\bremovals\b")
# The parameter tables on this API render 11 columns per row; a split that yields any other
# count is markup, not a data row.
SNUM_ROW_CELL_COUNT = 11


def parse_snum_estimate_attributes(html: str) -> dict:
    """Enumerate `/fullreport/parameters/snum`: every estimate attribute the API can return,
    and specifically which of them are harvest-removals attributes (ruling D-A).

    Same malformed markup as `/fullreport/parameters/wc` -- rows open with `<th scope=row ...>`
    and the tbody emits no `<tr>` opener -- so rows are recovered by splitting on `</tr>`, not
    by matching a pair. Column order is the page's own: ATTRIBUTE_NBR, ATTRIBUTE_DESCR,
    CONDTREESEED, LAND_BASIS, ESTIMATE_GRP_DESCR, EVAL_TYP, ... . The returned payload is
    deliberately a summary rather than all rows: per matching group a count and the lowest
    attribute number (the handle Stage 7 would use to request one), plus the full list of
    harvest-removals attribute numbers so membership of any *other* attribute number in that
    set is checkable rather than asserted."""
    body_match = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    empty = {
        "row_count": 0, "harvest_removals_groups": [], "harvest_removals_attribute_count": 0,
        "harvest_removals_attribute_nbrs": [], "non_harvest_removals_groups": [],
        "eval_typs_present": [],
    }
    if not body_match:
        return empty
    rows = []
    for row in body_match.group(1).split("</tr>"):
        cells = re.findall(r"<t[hd][^>]*>([^<]*)</t[hd]>", row)
        if len(cells) != SNUM_ROW_CELL_COUNT:
            continue
        rows.append([cell.strip() for cell in cells])
    if not rows:
        return empty

    groups: dict[str, dict] = {}
    harvest_nbrs: list[str] = []
    non_harvest_removals: set[str] = set()
    for nbr, _descr, _cts, _basis, group, eval_typ, *_rest in rows:
        if HARVEST_REMOVALS_GROUP_PATTERN.search(group):
            entry = groups.setdefault(
                group, {"estimate_group": group, "attribute_count": 0,
                        "lowest_attribute_nbr": nbr, "eval_typs": set()})
            entry["attribute_count"] += 1
            entry["eval_typs"].add(eval_typ)
            if _as_int(nbr) < _as_int(entry["lowest_attribute_nbr"]):
                entry["lowest_attribute_nbr"] = nbr
            harvest_nbrs.append(nbr)
        elif REMOVALS_GROUP_PATTERN.search(group):
            non_harvest_removals.add(group)
    return {
        "row_count": len(rows),
        "harvest_removals_groups": [
            {"estimate_group": g["estimate_group"], "attribute_count": g["attribute_count"],
             "lowest_attribute_nbr": g["lowest_attribute_nbr"],
             "eval_typs": sorted(g["eval_typs"])}
            for g in sorted(groups.values(), key=lambda g: g["estimate_group"])
        ],
        "harvest_removals_attribute_count": len(harvest_nbrs),
        "harvest_removals_attribute_nbrs": sorted(harvest_nbrs, key=_as_int),
        "non_harvest_removals_groups": sorted(non_harvest_removals),
        "eval_typs_present": sorted({r[5] for r in rows}),
    }


def _as_int(text: str) -> int:
    """Attribute numbers sort numerically, not lexically (`79` before `574161`). A
    non-numeric cell sorts last rather than raising: the page changing shape is a finding for
    the row count to expose, not a crash inside a sort key."""
    stripped = str(text).strip()
    return int(stripped) if stripped.isdigit() else 10**12


# Word-boundary, not substring: "SIC" occurs inside "BASIC" and "PHYSIOGRAPHIC", both of which
# appear in the real /fullreport response body, and a substring scan would report a nonzero
# industry-classification hit count off them alone.
INDUSTRY_CLASSIFICATION_TERMS = {
    "NAICS": r"(?i)\bNAICS\b",
    "SIC": r"\bSIC\b",
    "industry": r"(?i)\bindustr(?:y|ies)\b",
    "establishment": r"(?i)\bestablishment",
    "employment": r"(?i)\bemploy",
}
# The concepts FIA's own pages do organise by -- scanned alongside the terms above so the
# comparison is a measured contrast rather than a bare absence.
FIA_TAXONOMY_TERMS = {
    "species": r"(?i)\bspecies\b",
    "land use": r"(?i)\bland use\b",
    "product": r"(?i)\bproduct",
}


def count_term_hits(pages: dict[str, str], patterns: dict[str, str]) -> dict[str, int]:
    """Total word-boundary hits per term across the named page texts. The same machinery as
    `tpo_mentions_on_fia_doc_page`, generalised: a zero here is a measured zero over named,
    hashed extracts, which is what lets a "this source has no X concept" sentence be
    interpolated rather than typed. Every requested term gets an entry, including the zeros --
    an omitted key would read as "not checked"."""
    return {
        term: sum(len(re.findall(pattern, text)) for text in pages.values())
        for term, pattern in patterns.items()
    }


def proved_estimate_measure(metadata: dict) -> dict | None:
    """Which measure the successful `/fullreport` call actually returned, read from the
    response's own metadata rather than inferred from the request. `numEstDesc` echoes the
    zero-padded `snum` attribute number and its title; `estMeta` describes what that attribute
    estimates. Returns `None` when the response names neither -- the honest answer when the
    measure cannot be established, not a guess from the parameters sent."""
    num_est_desc = str(metadata.get("numEstDesc") or "").strip()
    est_meta = re.sub(r"<[^>]+>", " ", str(metadata.get("estMeta") or ""))
    est_meta = html_module.unescape(re.sub(r"\s+", " ", est_meta)).strip()
    if not num_est_desc and not est_meta:
        return None
    leading = num_est_desc.split(" ", 1)[0] if num_est_desc else ""
    return {
        "num_est_desc": num_est_desc,
        "est_meta": est_meta,
        "attribute_nbr": leading.lstrip("0") if leading.isdigit() else "",
    }


# --- pure helpers: Box discovery and xlsx inspection -----------------------------------------


def extract_json_object(text: str, marker: str) -> str:
    """Balanced-brace, string-aware extraction of the JSON object assigned right after
    `marker` in a `<script>...marker = {...};...</script>` blob. Box's share pages embed real
    JSON (not a JS literal with bare identifiers), so a scan that tracks string context -- not
    a naive brace count, which a literal `}` inside a string value would defeat -- can extract
    it exactly. Raises `ValueError` if `marker` is absent or the braces never balance: both
    mean the page changed shape, not something to guess past."""
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"marker {marker!r} not found")
    start = idx + len(marker)
    while start < len(text) and text[start] in " \t\r\n":
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"marker {marker!r} not followed by an object")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError(f"unbalanced braces after marker {marker!r}")


def discover_box_share_url(html: str) -> str | None:
    """The public Box folder's share URL, read from an `href` in the fetched NRUM
    data-downloads page rather than hardcoded -- the identifier changes with the page, so a
    hardcoded value would silently go stale the moment USDA rotates the share. Returns `None`
    (not a stale guess) when no such link is present."""
    match = re.search(r'href="(https://[a-z0-9.-]+\.app\.box\.com/s/[A-Za-z0-9]+)"', html)
    return match.group(1) if match else None


def box_shared_folder_items(html: str) -> dict:
    """Parse Box's embedded `Box.postStreamData` blob for the
    `/app-api/enduserapp/shared-folder` payload: the current folder's id/name and its
    immediate items (files and subfolders). Box's page renders no such listing anywhere in
    visible HTML text -- only in this embedded JSON -- so this IS the discovery mechanism,
    not a convenience shortcut around one."""
    payload = json.loads(extract_json_object(html, "Box.postStreamData = "))
    folder = payload.get("/app-api/enduserapp/shared-folder")
    if folder is None:
        raise ValueError("Box.postStreamData carries no shared-folder payload")
    return folder


def box_legacy_download_url(shared_name: str, file_id: int | str) -> str:
    """Box's back-compat `rm=box_download_shared_file` redirect -- the only route this run
    found that returns raw file bytes for a Box-hosted public share with a plain GET. Two
    statements here are carried over from the investigation that shaped this script and are
    re-established by no run: how this route was found -- it is undocumented anywhere on Box's
    or USDA's pages and turned up only by reading the share page's own JS bundle -- and that
    the `authenticated_download_url` embedded in that page's JSON was observed to answer 401
    without a browser session, which no probe here requests. What this endpoint and the modern
    share URL (discovered via `discover_box_share_url`) actually answer is a different question,
    left to each run's own probes of them in `route_probes` rather than asserted here."""
    return (
        f"{BOX_LEGACY_DOWNLOAD_BASE}?rm=box_download_shared_file"
        f"&shared_name={shared_name}&file_id=f_{file_id}"
    )


def select_latest_window_year_folder(items: list[dict], window_years: tuple[int, ...]) -> dict | None:
    """The most recent D1-window year with its own subfolder in the NRUM Data share --
    deterministic and reproducible (not "whichever state/year looked convenient"): among
    subfolders named a 4-digit year inside `window_years`, the one with the largest year."""
    candidates = [
        it for it in items
        if it.get("type") == "folder" and str(it.get("name", "")).isdigit()
        and int(it["name"]) in window_years
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda it: int(it["name"]))


def select_first_file(items: list[dict]) -> dict | None:
    """The alphabetically first file in a folder listing -- deterministic and reproducible,
    not a cherry-picked state. Folders are excluded."""
    files = sorted(
        (it for it in items if it.get("type") == "file"),
        key=lambda it: it.get("name") or "",
    )
    return files[0] if files else None


def xlsx_sheet_names(workbook_xml: str) -> list[str]:
    return re.findall(r'<sheet [^>]*name="([^"]*)"', workbook_xml)


def xlsx_shared_strings(shared_strings_xml: str) -> list[str]:
    return [
        html_module.unescape(s)
        for s in re.findall(r"<t[^>]*>(.*?)</t>", shared_strings_xml, re.DOTALL)
    ]


def xlsx_header_row(sheet_xml: str, shared_strings: list[str]) -> list[str]:
    """First-row (`r="1"`), string-typed (`t="s"`) cell values in column order -- the column
    headers. Non-string row-1 cells are silently skipped: every TPO workbook this run
    inspected has an entirely string-typed header row, so a numeric or blank header cell
    would be a real schema surprise, not something to coerce past."""
    row_match = re.search(r'<row r="1"[^>]*>(.*?)</row>', sheet_xml, re.DOTALL)
    if not row_match:
        return []
    indices = re.findall(r'<c r="[A-Z]+1"[^>]*t="s"[^>]*><v>(\d+)</v></c>', row_match.group(1))
    return [shared_strings[int(i)] for i in indices]


def xlsx_first_sheet_part(workbook_xml: str, rels_xml: str) -> tuple[str, str] | None:
    """The workbook's first sheet as `(name, zip path)`, resolved through the relationship id
    that `<sheet>` carries. Sheet order in `workbook.xml` and the `sheetN.xml` filenames are
    independent -- the relationship part is what binds them -- so reading
    `xl/worksheets/sheet1.xml` and calling it the first sheet is an assumption where this is a
    derivation. Returns `None` when the workbook lists no sheet or the relationship is absent;
    the caller records that gap rather than falling back to a guess."""
    sheet = re.search(r"<sheet\b[^>]*>", workbook_xml)
    if not sheet:
        return None
    name = re.search(r'\bname="([^"]*)"', sheet.group(0))
    rel_id = re.search(r'\br:id="([^"]*)"', sheet.group(0))
    if not name or not rel_id:
        return None
    target = re.search(
        rf'<Relationship\b[^>]*\bId="{re.escape(rel_id.group(1))}"[^>]*\bTarget="([^"]*)"',
        rels_xml,
    )
    if not target:
        return None
    return html_module.unescape(name.group(1)), "xl/" + target.group(1).lstrip("/")


def inspect_xlsx(content: bytes) -> dict:
    """Sheet names and the first sheet's header row, read directly from the xlsx zip
    container with `zipfile` + `re` -- no new dependency (`openpyxl`/`polars` are not in this
    script's PEP 723 block), since only structural facts (sheet names, header cells) are
    needed to evidence SRC-FOR-001, not the full data table."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        workbook_xml = zf.read("xl/workbook.xml").decode("utf-8", "replace")
        sheets = xlsx_sheet_names(workbook_xml)
        rels_xml = (
            zf.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
            if "xl/_rels/workbook.xml.rels" in names else ""
        )
        first = xlsx_first_sheet_part(workbook_xml, rels_xml)
        shared = (
            xlsx_shared_strings(zf.read("xl/sharedStrings.xml").decode("utf-8", "replace"))
            if "xl/sharedStrings.xml" in names else []
        )
        unresolved = ""
        headers: list[str] = []
        if first is None:
            unresolved = "no <sheet> element resolved to a worksheet part via its r:id"
        elif first[1] not in names:
            unresolved = f"first sheet's relationship target {first[1]} is not in the container"
        else:
            headers = xlsx_header_row(zf.read(first[1]).decode("utf-8", "replace"), shared)
    return {
        "sheet_names": sheets,
        "first_sheet_name": first[0] if first else "",
        "first_sheet_headers": headers,
        "first_sheet_unresolved": unresolved,
    }


# Header-row classification. Both patterns are anchored rather than substring tests: a
# `COUNTY`-prefixed name identifies a county, while `RPA_STD_AMOUNT_UOM_CODE` names the unit a
# measure is expressed in, not a measured volume, and would be swept in by a bare "amount" or
# an unanchored "vol".
COUNTY_IDENTIFIER_HEADER_PATTERN = re.compile(r"(?i)^county")
VOLUME_MEASURE_HEADER_PATTERN = re.compile(r"(?i)(?:vol|tons)$")


def classify_header_row(headers: list[str]) -> dict:
    """Which of a sheet's column names identify a county and which name a volume or weight
    measure. This is what lets the TPO verdict say -- from the header row this run actually
    read, not from a sheet name -- that the workbook carries county-resolved volume columns.
    What it cannot say is *whose* county: a column named COUNTY_NAME is as consistent with a
    mill's county as with a harvest county, which is why the origin/receipt reading stays
    inside the inference marker."""
    return {
        "county_identifier_headers": [
            h for h in headers if COUNTY_IDENTIFIER_HEADER_PATTERN.search(h)],
        "volume_measure_headers": [
            h for h in headers if VOLUME_MEASURE_HEADER_PATTERN.search(h)],
    }


HARVEST_ORIGIN_SHEET_PATTERN = re.compile(r"(?i)\bproduction\b")
MILL_RECEIPT_SHEET_PATTERN = re.compile(r"(?i)\breceipts?\b|\bmill\b")


def distinguishes_harvest_origin_from_mill_receipts(sheet_names: list[str]) -> bool:
    """SRC-FOR-001: TPO variables MUST distinguish harvest origin from mill receipts. True iff
    the fetched workbook has at least one sheet reading as harvest-origin production and at
    least one distinct sheet reading as mill receipts -- checked against the actual sheet
    names in the workbook this run fetched, not asserted from the landing page's prose."""
    has_origin = any(HARVEST_ORIGIN_SHEET_PATTERN.search(s) for s in sheet_names)
    has_receipts = any(MILL_RECEIPT_SHEET_PATTERN.search(s) for s in sheet_names)
    return has_origin and has_receipts


# --- pure helpers: verdict and prose composition ----------------------------------------------
#
# Everything below composes a sentence that gets persisted into a summary. They are pure
# functions taking already-measured values precisely so each branch can be tested directly:
# a verdict sentence is a claim about how much a check proves, which is exactly as unverified
# as a claim about data and inherits credibility from the measured material beside it.


def compose_retention_rule(extract_statuses: list[int]) -> dict:
    """Ruling D-B: this script's raw-retention rule, restated inside the artifact that the rule
    shaped, with its counters derived from the run rather than typed."""
    return {
        "rule": (
            "This script writes and registers a fetched body whenever the endpoint answered at "
            "all, whatever the HTTP status, and each extract's own http_status records which "
            "status it carried. On an access-verdict probe the non-200 body IS the evidence: a "
            "404 page, a 403 page and an empty 200 are three different verdicts and only the "
            "retained bytes tell them apart. A transport failure produces no body and so "
            "registers no extract; its evidence is the probe record's outcome field instead. "
            "The counters below therefore say which statuses were retained and nothing more: a "
            "retained status 200 means the endpoint answered, not that the body is usable data "
            "-- an application error page can arrive with status 200, and which retained bodies "
            "are usable is recorded per probe in findings, never inferable from an extract's "
            "http_status. Reader's caution: this rule is this script's, and the absence of a "
            "non-200 extract under another source in this audit is not evidence that no "
            "non-200 response occurred there."
        ),
        "extracts_recorded": len(extract_statuses),
        "extracts_with_non_200_status": sum(1 for s in extract_statuses if s != 200),
        "non_200_statuses_recorded": sorted({s for s in extract_statuses if s != 200}),
    }


def compose_fia_access(
    *,
    route: str,
    doc_params_parsed: bool,
    real_probe_parsed: bool,
    measure_proved: dict | None,
    snum_index: dict,
) -> dict:
    """The FIA access verdict and the sentence that justifies it.

    Two things are kept apart that the first implementation ran together. Retrieval was proved
    for exactly one estimate attribute -- the one `snum` selected -- and the response names it,
    so the reason quotes that name instead of leaving "returns real data" to be read as
    "returns the measure this project needs". Whether a harvest-origin measure exists at all is
    a separate question, answered by the `snum` catalog, and `verified` is withheld unless that
    catalog was read AND lists harvest-removals attributes: a capability nothing this run could
    read is not a capability this run verified.

    Each branch is a complete, independent sentence, and no clause shared across branches
    names an outcome that differs between them. The `documented` branch names which of
    `doc_params_parsed` / `real_probe_parsed` actually held rather than asserting both. The
    `verified` opening claims retrieval only -- never that the measure was named -- because
    `real_probe_parsed` requires non-empty estimates and metadata but not the `numEstDesc` /
    `estMeta` keys that name the returned attribute, so a response that names nothing reaches
    this branch. For the same reason the closing clause refers back to an attribute number
    only when one was read: `proved_estimate_measure` returns a record whenever *either*
    metadata field is present, and its `attribute_nbr` is empty when `numEstDesc` opens with a
    non-numeric token."""
    if not (doc_params_parsed and real_probe_parsed):
        clauses = [
            "the /fiadb-api/ documentation page's parameter table parsed"
            if doc_params_parsed else
            "the /fiadb-api/ documentation page's parameter table did not parse",
            "the real-parameter /fullreport probe returned a report with both estimates and "
            "metadata" if real_probe_parsed else
            "the real-parameter /fullreport probe did not return a report with both estimates "
            "and metadata",
        ]
        return {"route": route, "status": "documented", "reason": (
            "Not verified this run: " + "; ".join(clauses)
            + ". See findings.doc_parameters and findings.probe."
        )}

    numbered = measure_proved is not None and bool(measure_proved["attribute_nbr"])
    if numbered:
        measured = (
            "the response's own metadata names what came back as attribute "
            f'{measure_proved["attribute_nbr"]}, "{measure_proved["num_est_desc"]}" -- '
            f'"{measure_proved["est_meta"]}"'
        )
    elif measure_proved is not None:
        measured = (
            "the response's own metadata names what came back as "
            f'"{measure_proved["num_est_desc"]}" -- "{measure_proved["est_meta"]}", with no '
            "leading attribute number this script could read out of it"
        )
    else:
        measured = (
            "the response carried no numEstDesc/estMeta metadata naming the measure it "
            "returned, so which attribute was retrieved is not established by the response "
            "itself"
        )
    row_count = snum_index["row_count"]
    harvest_count = snum_index["harvest_removals_attribute_count"]

    if row_count == 0:
        return {"route": route, "status": "documented", "reason": (
            f"The /fullreport route answered with real machine-readable data this run "
            f"({measured}), but the /fullreport/parameters/snum attribute catalog could not be "
            "read this run, so whether FIA publishes a harvest-origin (removals) estimate "
            "attribute at all is unestablished here. See findings.probe and "
            "findings.snum_estimate_attributes."
        )}
    if harvest_count == 0:
        return {"route": route, "status": "documented", "reason": (
            f"The /fullreport route answered with real machine-readable data this run "
            f"({measured}), but the /fullreport/parameters/snum catalog fetched this run "
            f"enumerates {row_count} estimate attributes and none of them is a harvest-removals "
            "attribute, so the harvest-origin measure SS2.2 asks for is not obtainable from "
            "this endpoint on the evidence gathered here. See "
            "findings.snum_estimate_attributes."
        )}

    groups = "; ".join(
        f"{g['estimate_group']} ({g['attribute_count']} attribute(s), lowest attribute number "
        f"{g['lowest_attribute_nbr']}, EVAL_TYP {'/'.join(g['eval_typs'])})"
        for g in snum_index["harvest_removals_groups"]
    )
    non_harvest = ", ".join(snum_index["non_harvest_removals_groups"]) or "none"
    proved_is_harvest = (
        numbered
        and measure_proved["attribute_nbr"] in snum_index["harvest_removals_attribute_nbrs"]
    )
    if not numbered:
        gap = (
            "No attribute number could be read out of this run's response, so what came back "
            "cannot be checked against those harvest-removals attribute numbers: what this run "
            "proved end to end is retrieval of one report from this endpoint, while the "
            "harvest-removals capability rests on the fetched catalog listing those attributes "
            "and not on a harvest-removals report having been requested and returned."
        )
    elif proved_is_harvest:
        gap = (
            "That attribute number is itself one of those harvest-removals attributes, so a "
            "harvest-removals report is what this run requested and received."
        )
    else:
        gap = (
            "That attribute number is not one of those harvest-removals attributes: what this "
            "run proved end to end is retrieval of the one measure named above, while the "
            "harvest-removals capability rests on the fetched catalog listing those attributes "
            "and not on a harvest-removals report having been requested and returned."
        )
    return {"route": route, "status": "verified", "reason": (
        f"Verified for retrieval of one report from this endpoint: {measured}. The "
        f"/fullreport/parameters/snum catalog fetched this run enumerates {row_count} estimate "
        f"attributes, of which {harvest_count} sit in harvest-removals estimate groups -- "
        f"{groups} -- which that same catalog keeps distinct from its non-harvest removals "
        f"groups ({non_harvest}). {gap} See findings.snum_estimate_attributes."
    )}


def compose_fia_uncovered(
    *, industry_scan: dict, dc_has_evaluation: bool, wc_row_count: int
) -> str:
    """`coverage_span.uncovered` for FIA. The industry-concept claim is interpolated from a
    term scan over this run's own extracts (the same derivation `tpo_mentions_on_fia_doc_page`
    uses), and whatever reading is drawn from the resulting counts is delimited by the
    `INFERENCE MARKER, OPENING`/`CLOSING` pair `qcew_identity.absent_state_months_note`
    established, so the marking's scope ends where the reader can see it end. The D.C. clause
    is itself measured and therefore sits outside the marker.

    Three outcomes are kept apart that one string used to run together. A scan over zero pages
    -- what a run produces when no page offered to `scannable_text_page` answers with a
    status-200 body -- examined nothing, and a scan that examined nothing must not read as a
    scan that found nothing. That empty corpus is NOT the same as nothing having been fetched
    and hashed: `retain_body` keeps any answered body whatever its status, and the
    `other_route_*` bodies are never offered to the scan at all, so the sentences below name
    the corpus and the 200-gate rather than the extract set. A scan over pages that DID
    turn up industry terms cannot carry the zero-hit reading either. And the count of FIA's own
    taxonomy terms is reported, never asserted to be nonzero, since the function does not
    branch on it. The same distinction governs D.C.: `dc_has_evaluation` is False both when the
    fetched index omits D.C. and when no index was read at all."""
    industry_counts = industry_scan["industry_classification_terms"]
    taxonomy_counts = industry_scan["fia_taxonomy_terms"]
    industry = ", ".join(f"{t}={c}" for t, c in sorted(industry_counts.items()))
    taxonomy = ", ".join(f"{t}={c}" for t, c in sorted(taxonomy_counts.items()))
    industry_total = sum(industry_counts.values())
    pages = industry_scan["pages_scanned"]
    text = "no monthly resolution: SRC-FOR-004 forbids interpolating to months. "
    if not pages:
        text += (
            "No FIA page entered this scan's corpus this run -- none of the pages offered to "
            "it answered with a status-200 body -- so the industry-term scan ran over "
            "no pages and reports nothing about FIA: a scan that examined no pages is not a "
            "scan that found no industry terms, and whether FIA carries an industry concept a "
            "Logging (113310) slice could be selected on is unestablished here."
        )
    else:
        reading = (
            "Zero industry-term hits across those pages is read here as FIA carrying no "
            "industry concept to join on at all, so a Logging (113310) slice cannot be "
            "selected out of FIA the way it is out of QCEW or CBP and Stage 7 would need its "
            "own crosswalk from FIA's species/product/land-use taxonomy instead; the competing "
            "reading -- that an industry concept exists elsewhere in the API and merely goes "
            "unmentioned on the pages this script happens to fetch -- is not excluded by a "
            "zero count over those pages."
            if industry_total == 0 else
            f"{industry_total} industry-term hit(s) across those pages leaves the no-industry-"
            "concept reading this scan was written to test unavailable: a nonzero hit count is "
            "not itself an industry concept a Logging (113310) slice could be selected on, and "
            "which of those hits (if any) name a classification FIA could be joined on is not "
            "established by a count."
        )
        text += (
            f"Also measured, over the {len(pages)} FIA page(s) in this scan's corpus -- each "
            "of which answered with a status-200 body this run and is hashed as an extract "
            f"({', '.join(pages)}): word-boundary hits for the classification codes and "
            f"measures an industry-coded source would carry are {industry}, and hits for the "
            f"species/product/land-use concepts FIA organises its own reporting by are "
            f"{taxonomy}. "
            "INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of "
            "those counts, not a further measurement; it is supplied by hand, carries no "
            f"extract hash and is re-checked by no later run. {reading} "
            "INFERENCE MARKER, CLOSING."
        )
    if wc_row_count == 0:
        text += (
            " The /fullreport/parameters/wc evaluation index was not read this run (zero rows "
            "parsed), so whether FIA has an evaluation unit for the District of Columbia -- "
            "states_dc's 51st member -- is unestablished here rather than answered no."
        )
    elif not dc_has_evaluation:
        text += (
            " Also measured: no FIA evaluation unit for the District of Columbia -- absent from "
            f"the {wc_row_count}-row evaluation index fetched this run (states_dc's 51st member "
            "has no forest inventory)."
        )
    return text


def compose_cadence_claim(
    box_navigation: dict, *, window_years: tuple[int, ...], window_start_year: int
) -> str:
    """`coverage_span.covered` for TPO. Every clause is computed from `box_navigation` -- what
    THIS run's own probes found -- rather than typed from the investigation that shaped this
    script. That investigation happened to land on 2021/Ohio and observed a page-capped listing
    (20 rendered vs a filesCount of 37); a run's deterministic selection can land on a
    different year entirely, so a claim written against the investigation's year would be false
    about the year actually checked."""
    year_folders = sorted(int(y) for y in box_navigation.get("year_subfolders_found", []))
    pre_window = [y for y in year_folders if y < window_start_year]
    window_found = box_navigation.get("window_year_subfolders_found", [])
    fully_annual = (
        sorted(int(y) for y in window_found) == list(window_years) if window_found else False
    )
    if fully_annual:
        claim = (
            "a per-state-year subfolder exists in the NRUM Data Box share for every D1 window "
            f"year (verified this run: {window_found}); this directly contradicts a blanket "
            "'TPO is biennial, not annual' claim for the D1 window specifically, though whether "
            "every individual state resurveys annually (as opposed to the release/folder "
            "cadence being annual) was not checked"
        )
    elif window_found:
        claim = (
            f"per-state-year subfolders found for D1 window years {window_found} out of "
            f"{list(window_years)} (verified this run) -- window coverage by folder is "
            "incomplete, not annual throughout"
        )
    else:
        claim = "no D1 window year subfolder was found this run"
    if pre_window and all(y % 2 == 1 for y in pre_window):
        claim += (
            f"; pre-{window_start_year} subfolders found only for odd years back to "
            f"{min(pre_window)} (biennial cadence, verified this run)"
        )
    elif pre_window:
        claim += (
            f"; pre-{window_start_year} subfolders found for years {pre_window} (not strictly "
            "biennial, verified this run)"
        )
    return claim


def compose_pagination_note(box_navigation: dict) -> str:
    """Whether Box's rendered listing for the probed year matched that folder's own
    `filesCount`. Three real outcomes, not two: fewer rendered than claimed is a page cap,
    equal is a match, and MORE rendered than claimed is neither -- the two counts simply
    disagree, and calling that an exact match (as an `else` after `listed < claimed` does)
    states an outcome that did not happen. The shared opening clause names both numbers and no
    outcome, so it is true in every branch it prefixes."""
    listed = box_navigation.get("files_listed_this_page")
    claimed = box_navigation.get("filescount_per_box_metadata")
    year = box_navigation.get("probed_year")
    if listed is None or claimed is None:
        return (
            "the per-year rendered-item-count vs. filesCount comparison was not performed this "
            "run (year folder listing unavailable)"
        )
    if listed == claimed:
        return (
            f"for the probed year ({year}), Box's rendered item list returned {listed} files, "
            f"matching that folder's filesCount metadata ({claimed}) exactly -- no truncation "
            "observed for this specific year, though only the one year named here was checked "
            "and a different year could still be page-capped"
        )
    opening = (
        f"for the probed year ({year}), Box's rendered item list returned {listed} files while "
        f"that folder's own filesCount metadata claims {claimed}"
    )
    if listed < claimed:
        return opening + " -- fewer rendered than claimed, i.e. page-capped for at least this year"
    return opening + (
        " -- more rendered than claimed, so the two counts disagree in the opposite direction "
        "and neither can be taken as this folder's file count without checking which one Box "
        "means"
    )


def compose_tpo_access(
    *, route: str, harvest_origin_available: bool, box_navigation: dict, probes: list[dict]
) -> dict:
    """The TPO access verdict and the sentence that justifies it.

    `not_obtainable` branches on what actually stopped the run, because each state is different
    evidence and a clause naming one of them is false on the others. Finding a share URL in the
    page markup is not entering the folder: the share page can then answer 5xx (an answer, so
    not a transport failure either) or answer with a body that does not parse as a Box listing,
    and on both of those nothing was entered and nothing was fetched. `year_subfolders_found`
    is set only once the share page answered with a status-200 body, and
    `shared_folder_parse_error` is set exactly when the parse raised, so the cascade below
    reads those two rather than the share URL's mere presence. It does not read
    `nrum_data_folder_id`, which is also `None` after a parse that *succeeded* on a payload
    carrying no `currentFolderID` -- a state in which the folder was listed and asserting the
    body "did not parse" would be false. The two keys are ordered, not independent: neither is
    set unless the share page answered, so the unanswered branch is tested first and an absent
    `shared_folder_parse_error` never reads on its own as a successful parse. A probed URL that never answered at all is what
    `classify_probe`'s docstring calls the weakest possible basis for `not_obtainable`, and the
    sentence says so rather than letting a network failure read as a finding about the source.

    The `verified` branch keeps three kinds of statement visibly apart: what the workbook's own
    bytes show (sheet names, and the header row this run read out of the first sheet), what is
    read *from* those sheet names, and what is carried over from the investigation that found
    this route and was not measured by any probe in this run. The second and third each sit in
    their own marked span."""
    transport_failed = [p["url"] for p in probes if p.get("outcome") == "transport_failure"]
    if harvest_origin_available:
        sheets = box_navigation.get("sample_file_sheet_names", [])
        origin = [s for s in sheets if HARVEST_ORIGIN_SHEET_PATTERN.search(s)]
        receipts = [s for s in sheets if MILL_RECEIPT_SHEET_PATTERN.search(s)]
        headers = box_navigation.get("sample_file_first_sheet_headers", [])
        classes = classify_header_row(headers)
        counties = classes["county_identifier_headers"]
        volumes = classes["volume_measure_headers"]
        if not headers:
            header_clause = (
                "No header row was read from that workbook's first sheet this run"
                + (f" ({box_navigation['sample_file_first_sheet_unresolved']})"
                   if box_navigation.get("sample_file_first_sheet_unresolved") else "")
                + ", so nothing here rests on its column names."
            )
        else:
            header_clause = (
                "Its first sheet "
                f"({box_navigation.get('sample_file_first_sheet_name') or 'name unresolved'}) "
                f"carries a {len(headers)}-column header row, {headers}, of which {counties} "
                "match this script's county-identifier pattern and "
                f"{volumes} match its volume/weight-measure pattern."
            )
            if counties and volumes:
                header_clause += (
                    " A county identifier and volume measures therefore share that header row: "
                    "the workbook carries county-resolved volume columns, read from the header "
                    "row's own column names rather than off a sheet name. Which county those "
                    "identifiers name -- the county a harvest came from, or the county a mill "
                    "sits in -- is not settled by a column name."
                )
        return {"route": route, "status": "verified", "reason": (
            "Reachable and machine-readable, but only via an undocumented Box legacy-download "
            "redirect rather than the modern share URL; per-state coverage per year is not "
            "exhaustively verified (see coverage_span). Measured in the one workbook fetched "
            f"this run ({box_navigation.get('sample_file')}, from the "
            f"{box_navigation.get('probed_year')} subfolder): its {len(sheets)} sheet names are "
            f"{sheets}, of which {origin} match this script's harvest-origin sheet-name pattern "
            f"and {receipts} match its mill-receipt pattern. {header_clause} "
            "INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of "
            "those sheet names, not a further measurement; it is supplied by hand, carries no "
            "extract hash and is re-checked by no later run. Sheets named that way are read "
            "here as meaning the workbook holds harvest volumes attributed to the county of "
            "harvest in fields distinct from its mill-receipt fields, which is what "
            "SRC-FOR-001 requires. No data-row cells were read or compared across sheets, so "
            "the origin/receipt split rests on the sheet names alone; and only this one "
            "state-year workbook was inspected, so whether every state-year workbook in the "
            "share shares this sheet structure was not checked either. INFERENCE MARKER, "
            "CLOSING. INFERENCE MARKER, OPENING: how this route was found comes from the "
            "investigation that shaped this script rather than from this run -- the "
            "legacy-download redirect was found by reading the share page's own JS bundle, and "
            "the share page's embedded authenticated_download_url was observed there to answer "
            "401 without a browser session. No probe in this run requested that URL, so both "
            "statements carry no extract hash and are re-checked by no later run. INFERENCE "
            "MARKER, CLOSING."
        )}

    share_url = box_navigation.get("share_url_discovered")
    share_page_answered = "year_subfolders_found" in box_navigation
    parse_error = box_navigation.get("shared_folder_parse_error")
    folder_parsed = "shared_folder_parse_error" not in box_navigation
    year_folders = box_navigation.get("year_subfolders_found", [])
    probed_year = box_navigation.get("probed_year")
    inspection_error = box_navigation.get("sample_file_inspection_error")
    if share_url is None:
        stopped = (
            "no Box share link matching the discovery pattern was present in the fetched NRUM "
            "data-downloads page markup, so the folder route was never entered"
        )
    elif not share_page_answered:
        stopped = (
            f"a Box share URL was read out of that page this run ({share_url}), but it did not "
            "answer this run with a status-200 body, so the folder behind it was never listed "
            "and no workbook was fetched from it"
        )
    elif not folder_parsed:
        stopped = (
            f"the Box share URL read out of that page this run ({share_url}) answered with a "
            "body, but that body did not parse as a Box folder listing"
            + (f" ({parse_error})" if parse_error else "")
            + ", so no year subfolder was reached and no workbook was fetched"
        )
    elif probed_year is None:
        stopped = (
            f"the Box folder behind the share URL read out of that page this run ({share_url}) "
            f"was entered and listed {len(year_folders)} year subfolder(s) ({year_folders}), "
            "none of which this run selected to probe, so no workbook was fetched"
        )
    elif box_navigation.get("sample_file") is None:
        stopped = (
            f"the Box folder behind the share URL read out of that page this run ({share_url}) "
            f"was entered and its {probed_year} subfolder probed, but no workbook from that "
            "subfolder was both fetched and inspected this run"
            + (f" (inspection error: {inspection_error})" if inspection_error else "")
        )
    else:
        stopped = (
            f"the workbook inspected from the {probed_year} subfolder "
            f"({box_navigation['sample_file']}) has sheet names "
            f"{box_navigation.get('sample_file_sheet_names', [])}, which do not include both a "
            "sheet matching this script's harvest-origin pattern and a sheet matching its "
            "mill-receipt pattern, so harvest origin held distinct from mill receipts is not "
            "evidenced by the workbook this run fetched"
        )
    clauses = [stopped]
    if transport_failed:
        clauses.append(
            f"{len(transport_failed)} probed URL(s) returned no response at all "
            f"(transport_failure: {transport_failed}), so for those URLs this verdict rests on "
            "the absence of any answer rather than on an answer showing the data is absent -- "
            "the weakest basis this script records for not_obtainable, and one a re-run could "
            "overturn without anything at the source having changed"
        )
    return {"route": route, "status": "not_obtainable", "reason": (
        "Not obtained this run: " + "; ".join(clauses)
        + ". See findings.route_probes and findings.box_navigation."
    )}


# --- main -------------------------------------------------------------------------------------


def run_fia(client: httpx.Client) -> None:
    extracts: list = []
    # Page texts scanned for classification terms further down. Keyed by the extract filename
    # each was written to, so the scan's own record names hashed artifacts a reader can re-grep,
    # not "some pages".
    scanned_pages: dict[str, str] = {}

    doc = probe_url(client, FIA_DOC)
    doc_params: list[dict] = []
    tpo_mentions_on_doc_page = None
    retain_body(extracts, SOURCE_FIA, doc, "fiadb_api_doc.html")
    if scannable_text_page(doc):
        doc_text = doc["body"].decode("utf-8", "replace")
        scanned_pages["fiadb_api_doc.html"] = doc_text
        doc_params = parse_fia_doc_parameters(doc_text)
        # Checked here, in scope of this run's own fetch, rather than transcribed from the
        # dispatch's claim that the doc page never mentions TPO.
        tpo_mentions_on_doc_page = len(re.findall(r"(?i)\btpo\b", doc_text))

    wc_index = {"states": [], "year_min": None, "year_max": None, "row_count": 0}
    wc_resp = probe_url(client, FIA_WC_PARAMETERS)
    retain_body(extracts, SOURCE_FIA, wc_resp, "wc_evaluation_index.html")
    if scannable_text_page(wc_resp):
        wc_text = wc_resp["body"].decode("utf-8", "replace")
        scanned_pages["wc_evaluation_index.html"] = wc_text
        wc_index = parse_wc_evaluation_index(wc_text)

    # Ruling D-A: enumerate the estimate attributes /fullreport can return, so the verdict can
    # say whether a harvest-origin measure exists rather than only that the endpoint answers.
    # Seeded with the parser's own empty-result shape (not a hand-written literal that could
    # drift from it) so a non-200 snum page still leaves every key present and zeroed.
    snum_index = parse_snum_estimate_attributes("")
    snum_resp = probe_url(client, FIA_SNUM_PARAMETERS)
    retain_body(extracts, SOURCE_FIA, snum_resp, "snum_estimate_attributes.html")
    if scannable_text_page(snum_resp):
        snum_text = snum_resp["body"].decode("utf-8", "replace")
        scanned_pages["snum_estimate_attributes.html"] = snum_text
        snum_index = parse_snum_estimate_attributes(snum_text)

    naive_probe = probe_url(client, FIA_FULLREPORT, params=FIA_NAIVE_PARAMS)
    naive_is_error_page = (
        naive_probe["http_status"] == 200
        and b"Error Type" in naive_probe["body"]
    )
    retain_body(extracts, SOURCE_FIA, naive_probe, "fullreport_naive_probe.html")
    if scannable_text_page(naive_probe):
        scanned_pages["fullreport_naive_probe.html"] = naive_probe["body"].decode(
            "utf-8", "replace")

    real_probe = probe_url(client, FIA_FULLREPORT, params=FIA_REAL_PARAMS)
    estimates: list[dict] = []
    metadata: dict = {}
    real_probe_parsed = False
    retain_body(extracts, SOURCE_FIA, real_probe, "fullreport_real_probe.json")
    if scannable_text_page(real_probe):
        scanned_pages["fullreport_real_probe.json"] = real_probe["body"].decode(
            "utf-8", "replace")
        try:
            parsed = json.loads(real_probe["body"])
            estimates = parsed.get("estimates", [])
            metadata = parsed.get("metadata", {})
            real_probe_parsed = bool(estimates) and bool(metadata)
        except json.JSONDecodeError:
            real_probe_parsed = False

    se_field = sampling_error_field(estimates)
    ev_field = evaluation_vintage_field(metadata)
    measure_proved = proved_estimate_measure(metadata)

    datamart_probes = [
        probe_with_retries(
            lambda u=url: c.probe(client, u), url=url, attempts=FIA_DATAMART_ATTEMPTS,
            wait_seconds=FIA_DATAMART_WAIT_SECONDS)
        for url in FIA_DATAMART_CANDIDATES
    ]
    # `probe_url`, not `_common.probe`: every one of these routes that answers with a body has
    # those bytes retained whatever the status (ruling D-B), and the retained bytes -- not this
    # comment -- say what a run met there. `Evalidator/evalidator.jsp` served 403 to one run
    # and 500 to the next, answering both within seconds on a hand check; those are not the
    # same finding, since a route closed to this client and a fault at the server read
    # differently, so which of them a run met is read back off that run's own extract and its
    # `http_status`. `_common.probe` discards bodies by construction, so it cannot retain them.
    other_route_probes = []
    for i, url in enumerate(FIA_OTHER_ROUTES):
        res = probe_url(client, url)
        retain_body(extracts, SOURCE_FIA, res, f"other_route_{i}.bin")
        other_route_probes.append(probe_record(res, "dispatch lead table"))

    industry_scan = {
        "pages_scanned": sorted(scanned_pages),
        "bytes_scanned": sum(len(t) for t in scanned_pages.values()),
        "industry_classification_terms": count_term_hits(
            scanned_pages, INDUSTRY_CLASSIFICATION_TERMS),
        "fia_taxonomy_terms": count_term_hits(scanned_pages, FIA_TAXONOMY_TERMS),
    }
    # Derived from this run's own fetched evaluation index, not transcribed from the dispatch
    # (which never made this claim) or from memory of the QCEW states_dc finding (a different
    # source, established in an earlier task): does FIA even have a state-level evaluation
    # unit for D.C.? Directly relevant to Appendix A's `geography_universe: 'states_dc'`.
    dc_has_fia_evaluation = "District of Columbia" in wc_index["states"]

    c.write_summary(
        SOURCE_FIA,
        coverage_span={
            # Derived from the fetched /fullreport/parameters/wc evaluation index (this run),
            # not typed: the program-wide span across every state/territory FIA evaluates --
            # not scoped to Logging, for the reason `uncovered` states and
            # findings.industry_concept_scan measures.
            "published_start": str(wc_index["year_min"]) if wc_index["year_min"] else "",
            "published_end": str(wc_index["year_max"]) if wc_index["year_max"] else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": (
                "inventory evaluation cycles overlapping D1's reference years, not calendar "
                "months or a Logging-specific series"
            ),
            "uncovered": compose_fia_uncovered(
                industry_scan=industry_scan,
                dc_has_evaluation=dc_has_fia_evaluation,
                wc_row_count=wc_index["row_count"],
            ),
        },
        access=compose_fia_access(
            route=FIA_FULLREPORT,
            doc_params_parsed=bool(doc_params),
            real_probe_parsed=real_probe_parsed,
            measure_proved=measure_proved,
            snum_index=snum_index,
        ),
        extracts=extracts,
        findings={
            "doc_parameters": doc_params,
            "tpo_mentions_on_fia_doc_page": tpo_mentions_on_doc_page,
            "evaluation_vintage_index": wc_index,
            "snum_estimate_attributes": snum_index,
            "measure_proved_by_probe": measure_proved,
            "industry_concept_scan": industry_scan,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
            "probe_naive_missing_required_params": {
                "url": FIA_FULLREPORT,
                "params_sent": FIA_NAIVE_PARAMS,
                "http_status": naive_probe["http_status"],
                "bytes": naive_probe["bytes"],
                "content_type": naive_probe["content_type"],
                "outcome": classify_probe(naive_probe["http_status"], naive_probe["bytes"]),
                "is_evalidator_error_page": naive_is_error_page,
                "note": (
                    "the brief's illustrative probe -- omits every parameter the doc page "
                    "marks required (wc*, snum*, rselected*, cselected*); returns HTTP 200 "
                    "but an EVALIDator error page, not a report -- a '200 but no usable "
                    "data' outcome, not a source outage"
                ),
            },
            "probe": {
                "url": FIA_FULLREPORT,
                "params_sent": FIA_REAL_PARAMS,
                "http_status": real_probe["http_status"],
                "bytes": real_probe["bytes"],
                "content_type": real_probe["content_type"],
                "outcome": classify_probe(real_probe["http_status"], real_probe["bytes"]),
                "has_sampling_error": se_field is not None,
                "parsed_as_report_with_estimates_and_metadata": real_probe_parsed,
            },
            "sampling_error_field": se_field,
            "evaluation_vintage_field": ev_field,
            "district_of_columbia_has_fia_evaluation": dc_has_fia_evaluation,
            "datamart_probes": datamart_probes,
            "other_routes_probed": other_route_probes,
        },
    )


def run_tpo(client: httpx.Client) -> None:
    extracts = []
    probes = []

    for url in TPO_CANDIDATES:
        res = probe_url(client, url)
        # Retained whatever the status (ruling D-B): one of these three candidates 404s, and
        # its 4 KB body is what distinguishes "this API path is not published" from "published
        # but empty" -- a distinction a discarded body cannot support.
        retain_body(extracts, SOURCE_TPO, res, f"candidate_{TPO_CANDIDATES.index(url)}.bin")
        probes.append(probe_record(res, "brief"))

    nrum_downloads_url = TPO_DISCOVERED_ROUTES[1]
    nrum_downloads_body = b""
    for i, url in enumerate(TPO_DISCOVERED_ROUTES):
        res = probe_url(client, url)
        if url == nrum_downloads_url:
            nrum_downloads_body = res["body"]
        retain_body(extracts, SOURCE_TPO, res, f"discovered_{i}.bin")
        probes.append(probe_record(res, "discovered (linked from a brief candidate page)"))

    # Not hardcoded: read from the NRUM data-downloads page this run actually fetched above.
    box_share_url = discover_box_share_url(nrum_downloads_body.decode("utf-8", "replace"))

    chosen: str | None = None
    harvest_origin_available = False
    box_navigation: dict = {"share_url_discovered": box_share_url}
    box_base = {"url": "", "http_status": 0, "bytes": 0, "content_type": "", "body": b""}
    if box_share_url is not None:
        box_base = probe_url(client, box_share_url)
        retain_body(extracts, SOURCE_TPO, box_base, "box_nrum_data_folder.html")
        probes.append(probe_record(
            box_base, "discovered (linked from the NRUM data-downloads page)"))
    if box_base["http_status"] == 200 and box_base["body"]:
        try:
            root_folder = box_shared_folder_items(box_base["body"].decode("utf-8", "replace"))
        except (ValueError, json.JSONDecodeError) as exc:
            root_folder = {"items": [], "parse_error": str(exc)}
            # Recorded, not just caught: `compose_tpo_access` distinguishes "the share page
            # never answered" from "it answered and did not parse", and the second branch is
            # only readable if the reason it did not parse reaches the artifact.
            box_navigation["shared_folder_parse_error"] = str(exc)
        year_folders = sorted(
            (it.get("name") for it in root_folder.get("items", [])
             if it.get("type") == "folder" and str(it.get("name", "")).isdigit()),
            key=int,
        )
        box_navigation["nrum_data_folder_id"] = root_folder.get("currentFolderID")
        box_navigation["year_subfolders_found"] = year_folders
        box_navigation["window_year_subfolders_found"] = [
            y for y in year_folders if int(y) in WINDOW_YEARS
        ]

        target = select_latest_window_year_folder(root_folder.get("items", []), WINDOW_YEARS)
        if target is not None:
            year_folder_url = f"{box_share_url}/folder/{target['id']}"
            year_resp = probe_url(client, year_folder_url)
            retain_body(
                extracts, SOURCE_TPO, year_resp, f"box_{target['name']}_folder.html")
            probes.append(probe_record(
                year_resp, f"discovered (Box subfolder for {target['name']})"))
            box_navigation["probed_year"] = target["name"]
            if year_resp["http_status"] == 200 and year_resp["body"]:
                try:
                    year_folder = box_shared_folder_items(
                        year_resp["body"].decode("utf-8", "replace"))
                except (ValueError, json.JSONDecodeError):
                    year_folder = {"items": []}
                items = year_folder.get("items", [])
                box_navigation["files_listed_this_page"] = len(
                    [it for it in items if it.get("type") == "file"])
                box_navigation["filescount_per_box_metadata"] = target.get("filesCount")
                chosen_file = select_first_file(items)
                if chosen_file is not None:
                    shared_name = box_share_url.rsplit("/s/", 1)[1]
                    file_url = box_legacy_download_url(shared_name, chosen_file["id"])
                    file_resp = probe_url(client, file_url)
                    retain_body(
                        extracts, SOURCE_TPO, file_resp,
                        f"tpo_sample_{target['name']}_{chosen_file['name']}")
                    probes.append(probe_record(
                        file_resp,
                        f"discovered (Box legacy download of {chosen_file['name']})"))
                    if answered_with_body(file_resp) and is_machine_readable(
                            file_resp["content_type"]):
                        try:
                            inspected = inspect_xlsx(file_resp["body"])
                            harvest_origin_available = (
                                distinguishes_harvest_origin_from_mill_receipts(
                                    inspected["sheet_names"]))
                            box_navigation["sample_file"] = chosen_file["name"]
                            box_navigation["sample_file_sheet_names"] = (
                                inspected["sheet_names"])
                            box_navigation["sample_file_first_sheet_name"] = (
                                inspected["first_sheet_name"])
                            box_navigation["sample_file_first_sheet_headers"] = (
                                inspected["first_sheet_headers"])
                            # Empty on every workbook this run has seen. Persisted anyway so an
                            # absent header row shows up as a named gap in the artifact rather
                            # than as a clause the access reason silently omits.
                            box_navigation["sample_file_first_sheet_unresolved"] = (
                                inspected["first_sheet_unresolved"])
                            if chosen is None:
                                chosen = file_url
                        except (zipfile.BadZipFile, KeyError) as exc:
                            box_navigation["sample_file_inspection_error"] = str(exc)

    # Both sentences below are composed by pure functions from box_navigation -- what THIS run's
    # own probes found -- rather than typed from the investigation that shaped this script.
    # That investigation happened to land on 2021/Ohio and observed a page-capped listing (20
    # rendered vs a filesCount of 37), while a run's deterministic selection
    # (`select_latest_window_year_folder`) can land on a different year entirely, so a hardcoded
    # claim written against the investigation's year would be false about the year actually
    # checked. Composing them out of line is also what makes each branch directly testable.
    year_folders_int = sorted(int(y) for y in box_navigation.get("year_subfolders_found", []))
    cadence_claim = compose_cadence_claim(
        box_navigation, window_years=WINDOW_YEARS, window_start_year=int(c.WINDOW_START[:4]))
    pagination_note = compose_pagination_note(box_navigation)

    c.write_summary(
        SOURCE_TPO,
        coverage_span={
            "published_start": str(year_folders_int[0]) if year_folders_int else "",
            "published_end": str(year_folders_int[-1]) if year_folders_int else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": cadence_claim,
            "uncovered": (
                "no monthly resolution: SRC-FOR-004 forbids interpolating to months; "
                "per-state completeness within a year (which of the 51 states_dc have a "
                f"file) was not exhaustively enumerated this run -- {pagination_note} -- so "
                "a full state-by-state count would need paginating Box's listing API for "
                "every window year, out of scope for an access verdict"
            ),
        },
        access=compose_tpo_access(
            route=(
                f"{nrum_downloads_url} -> {box_share_url} -> "
                f"{box_share_url}/folder/<year-subfolder-id> -> "
                f"{BOX_LEGACY_DOWNLOAD_BASE}?rm=box_download_shared_file&...&file_id=f_<id>"
            ),
            harvest_origin_available=harvest_origin_available,
            box_navigation=box_navigation,
            probes=probes,
        ),
        extracts=extracts,
        findings={
            "route_probes": probes,
            "harvest_origin_available": harvest_origin_available,
            "chosen_route": chosen,
            "box_navigation": box_navigation,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
        },
    )


def main() -> None:
    client = c.build_client()
    run_fia(client)
    run_tpo(client)
    fia_summary = c.load_summary(SOURCE_FIA)
    tpo_summary = c.load_summary(SOURCE_TPO)
    snum = fia_summary["findings"]["snum_estimate_attributes"]
    measure = fia_summary["findings"]["measure_proved_by_probe"] or {}
    print(
        "FIA:", fia_summary["access"]["status"],
        "| sampling error field:", fia_summary["findings"]["sampling_error_field"],
        "| evaluation vintage field:", fia_summary["findings"]["evaluation_vintage_field"],
    )
    print(
        "FIA measure proved:", measure.get("num_est_desc"),
        "| snum attributes catalogued:", snum["row_count"],
        "| of them harvest-removals:", snum["harvest_removals_attribute_count"],
    )
    print(
        "TPO:", tpo_summary["access"]["status"],
        "| chosen route:", tpo_summary["findings"]["chosen_route"],
    )


if __name__ == "__main__":
    main()
