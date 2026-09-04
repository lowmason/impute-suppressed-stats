# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-FOR-001/002/003: record access verdicts for FIA (`/fullreport` parameters, sampling
error, evaluation vintage) and TPO harvest-origin data. `not_obtainable` is a legitimate
verdict, but only when it is earned by the probes recorded here -- never inherited from a
prior review's inability to find a URL, and never from Appendix A already shipping
`tpo.enabled: false` / `fia.enabled: false`.

This run found both sources reachable. FIA's `/fullreport` returns real, machine-readable
estimates (with sampling error) once called with the parameters its own doc page marks
required -- the brief's illustrative call omitted all four and got back a 200-status
EVALIDator *error* page, not a report. TPO's harvest-origin data is not at any of the brief's
three candidate URLs, but two hops from the first of them (`research.fs.usda.gov/programs/nrum`
-> its own "data downloads" page -> a public Box folder) sits a real, county-level, per-state
production table, fetchable once you use Box's undocumented legacy download redirect instead
of its modern (session-gated) share URL. See `main()` for the full probe sequence and
`tests/audit/test_forest_sources.py` for what is pinned about each parsing step.
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
    found that returns raw file bytes for a Box-hosted public share with a plain GET. The
    modern share URL (discovered via `discover_box_share_url`) serves a 200 HTML app shell,
    and the `authenticated_download_url` embedded in that shell's JSON 401s without a browser
    session (both verified live this run) -- this legacy endpoint is undocumented anywhere on
    Box's or USDA's pages; it was found by reading the share page's own JS bundle."""
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


def inspect_xlsx(content: bytes) -> dict:
    """Sheet names and the first sheet's header row, read directly from the xlsx zip
    container with `zipfile` + `re` -- no new dependency (`openpyxl`/`polars` are not in this
    script's PEP 723 block), since only structural facts (sheet names, header cells) are
    needed to evidence SRC-FOR-001, not the full data table."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        sheets = xlsx_sheet_names(zf.read("xl/workbook.xml").decode("utf-8", "replace"))
        shared = (
            xlsx_shared_strings(zf.read("xl/sharedStrings.xml").decode("utf-8", "replace"))
            if "xl/sharedStrings.xml" in names else []
        )
        headers = (
            xlsx_header_row(
                zf.read("xl/worksheets/sheet1.xml").decode("utf-8", "replace"), shared
            )
            if "xl/worksheets/sheet1.xml" in names else []
        )
    return {"sheet_names": sheets, "first_sheet_headers": headers}


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


# --- main -------------------------------------------------------------------------------------


def run_fia(client: httpx.Client) -> None:
    extracts = []

    doc = probe_url(client, FIA_DOC)
    doc_params: list[dict] = []
    tpo_mentions_on_doc_page = None
    if doc["http_status"] == 200:
        extracts.append(c.record_extract(
            SOURCE_FIA, FIA_DOC, "fiadb_api_doc.html", doc["body"], http_status=200))
        doc_text = doc["body"].decode("utf-8", "replace")
        doc_params = parse_fia_doc_parameters(doc_text)
        # Checked here, in scope of this run's own fetch, rather than transcribed from the
        # dispatch's claim that the doc page never mentions TPO.
        tpo_mentions_on_doc_page = len(re.findall(r"(?i)\btpo\b", doc_text))

    wc_index = {"states": [], "year_min": None, "year_max": None, "row_count": 0}
    wc_resp = probe_url(client, FIA_WC_PARAMETERS)
    if wc_resp["http_status"] == 200:
        extracts.append(c.record_extract(
            SOURCE_FIA, FIA_WC_PARAMETERS, "wc_evaluation_index.html", wc_resp["body"],
            http_status=200))
        wc_index = parse_wc_evaluation_index(wc_resp["body"].decode("utf-8", "replace"))

    naive_probe = probe_url(client, FIA_FULLREPORT, params=FIA_NAIVE_PARAMS)
    naive_is_error_page = (
        naive_probe["http_status"] == 200
        and b"Error Type" in naive_probe["body"]
    )
    if naive_probe["http_status"] == 200 and naive_probe["body"]:
        extracts.append(c.record_extract(
            SOURCE_FIA, FIA_FULLREPORT, "fullreport_naive_probe.html", naive_probe["body"],
            http_status=200))

    real_probe = probe_url(client, FIA_FULLREPORT, params=FIA_REAL_PARAMS)
    estimates: list[dict] = []
    metadata: dict = {}
    real_probe_parsed = False
    if real_probe["http_status"] == 200 and real_probe["body"]:
        extracts.append(c.record_extract(
            SOURCE_FIA, FIA_FULLREPORT, "fullreport_real_probe.json", real_probe["body"],
            http_status=200))
        try:
            parsed = json.loads(real_probe["body"])
            estimates = parsed.get("estimates", [])
            metadata = parsed.get("metadata", {})
            real_probe_parsed = bool(estimates) and bool(metadata)
        except json.JSONDecodeError:
            real_probe_parsed = False

    se_field = sampling_error_field(estimates)
    ev_field = evaluation_vintage_field(metadata)

    datamart_probes = [
        probe_with_retries(
            lambda u=url: c.probe(client, u), url=url, attempts=FIA_DATAMART_ATTEMPTS,
            wait_seconds=FIA_DATAMART_WAIT_SECONDS)
        for url in FIA_DATAMART_CANDIDATES
    ]
    other_route_probes = []
    for url in FIA_OTHER_ROUTES:
        status, nbytes = c.probe(client, url)
        other_route_probes.append({
            "url": url, "http_status": status, "bytes": nbytes,
            "outcome": classify_probe(status, nbytes),
        })

    fia_verified = real_probe_parsed and bool(doc_params)
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
            # not scoped to Logging, since FIA has no NAICS/industry concept at all (it is
            # species/product/land-use based; see findings.fia_has_no_industry_concept).
            "published_start": str(wc_index["year_min"]) if wc_index["year_min"] else "",
            "published_end": str(wc_index["year_max"]) if wc_index["year_max"] else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": (
                "inventory evaluation cycles overlapping D1's reference years, not calendar "
                "months or a Logging-specific series"
            ),
            "uncovered": (
                "no monthly resolution: SRC-FOR-004 forbids interpolating to months; no "
                "NAICS/industry concept -- FIA reports by species group, product, and land "
                "use, not by industry code" + (
                    ""
                    if dc_has_fia_evaluation else
                    "; no FIA evaluation unit for the District of Columbia -- absent from "
                    f"the {wc_index['row_count']}-row evaluation index fetched this run "
                    "(states_dc's 51st member has no forest inventory)"
                )
            ),
        },
        access={
            "route": FIA_FULLREPORT,
            "status": "verified" if fia_verified else "documented",
            "reason": (
                None if fia_verified else
                "documentation page reachable and its parameter table parsed, but the "
                "real-parameter /fullreport probe did not return a parsable report with "
                "estimates and metadata; see findings.probe"
            ),
        },
        extracts=extracts,
        findings={
            "doc_parameters": doc_params,
            "tpo_mentions_on_fia_doc_page": tpo_mentions_on_doc_page,
            "evaluation_vintage_index": wc_index,
            "probe_naive_missing_required_params": {
                "url": FIA_FULLREPORT,
                "params_sent": FIA_NAIVE_PARAMS,
                "http_status": naive_probe["http_status"],
                "bytes": naive_probe["bytes"],
                "content_type": naive_probe["content_type"],
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
        machine = is_machine_readable(res["content_type"])
        if res["http_status"] == 200 and res["body"]:
            extracts.append(c.record_extract(
                SOURCE_TPO, url, f"candidate_{TPO_CANDIDATES.index(url)}.bin", res["body"],
                http_status=200))
        probes.append({
            "url": url, "http_status": res["http_status"], "bytes": res["bytes"],
            "content_type": res["content_type"], "machine_readable": machine,
            "origin": "brief",
        })

    nrum_downloads_url = TPO_DISCOVERED_ROUTES[1]
    nrum_downloads_body = b""
    for i, url in enumerate(TPO_DISCOVERED_ROUTES):
        res = probe_url(client, url)
        machine = is_machine_readable(res["content_type"])
        if url == nrum_downloads_url:
            nrum_downloads_body = res["body"]
        if res["http_status"] == 200 and res["body"]:
            extracts.append(c.record_extract(
                SOURCE_TPO, url, f"discovered_{i}.bin", res["body"], http_status=200))
        probes.append({
            "url": url, "http_status": res["http_status"], "bytes": res["bytes"],
            "content_type": res["content_type"], "machine_readable": machine,
            "origin": "discovered (linked from a brief candidate page)",
        })

    # Not hardcoded: read from the NRUM data-downloads page this run actually fetched above.
    box_share_url = discover_box_share_url(nrum_downloads_body.decode("utf-8", "replace"))

    chosen: str | None = None
    harvest_origin_available = False
    box_navigation: dict = {"share_url_discovered": box_share_url}
    box_base = {"http_status": 0, "bytes": 0, "content_type": "", "body": b""}
    if box_share_url is not None:
        box_base = probe_url(client, box_share_url)
        if box_base["http_status"] == 200 and box_base["body"]:
            extracts.append(c.record_extract(
                SOURCE_TPO, box_share_url, "box_nrum_data_folder.html", box_base["body"],
                http_status=200))
        probes.append({
            "url": box_share_url, "http_status": box_base["http_status"],
            "bytes": box_base["bytes"], "content_type": box_base["content_type"],
            "machine_readable": is_machine_readable(box_base["content_type"]),
            "origin": "discovered (linked from the NRUM data-downloads page)",
        })
    if box_base["http_status"] == 200 and box_base["body"]:
        try:
            root_folder = box_shared_folder_items(box_base["body"].decode("utf-8", "replace"))
        except (ValueError, json.JSONDecodeError) as exc:
            root_folder = {"items": [], "parse_error": str(exc)}
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
            if year_resp["http_status"] == 200 and year_resp["body"]:
                extracts.append(c.record_extract(
                    SOURCE_TPO, year_folder_url, f"box_{target['name']}_folder.html",
                    year_resp["body"], http_status=200))
            probes.append({
                "url": year_folder_url, "http_status": year_resp["http_status"],
                "bytes": year_resp["bytes"], "content_type": year_resp["content_type"],
                "machine_readable": is_machine_readable(year_resp["content_type"]),
                "origin": f"discovered (Box subfolder for {target['name']})",
            })
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
                    if file_resp["http_status"] == 200 and file_resp["body"]:
                        rec = c.record_extract(
                            SOURCE_TPO, file_url,
                            f"tpo_sample_{target['name']}_{chosen_file['name']}",
                            file_resp["body"], http_status=200)
                        extracts.append(rec)
                        machine = is_machine_readable(file_resp["content_type"])
                        probes.append({
                            "url": file_url, "http_status": file_resp["http_status"],
                            "bytes": file_resp["bytes"],
                            "content_type": file_resp["content_type"],
                            "machine_readable": machine,
                            "origin": (
                                f"discovered (Box legacy download of {chosen_file['name']})"
                            ),
                        })
                        if machine:
                            try:
                                inspected = inspect_xlsx(file_resp["body"])
                                harvest_origin_available = (
                                    distinguishes_harvest_origin_from_mill_receipts(
                                        inspected["sheet_names"]))
                                box_navigation["sample_file"] = chosen_file["name"]
                                box_navigation["sample_file_sheet_names"] = (
                                    inspected["sheet_names"])
                                box_navigation["sample_file_first_sheet_headers"] = (
                                    inspected["first_sheet_headers"])
                                if chosen is None:
                                    chosen = file_url
                            except (zipfile.BadZipFile, KeyError) as exc:
                                box_navigation["sample_file_inspection_error"] = str(exc)

    # Every clause below is computed from box_navigation -- what THIS run's own probes found --
    # rather than typed from the investigation that shaped this script. That investigation
    # happened to land on 2021/Ohio and observed a page-capped listing (20 rendered vs a
    # filesCount of 37); this run's deterministic selection (`select_latest_window_year_folder`)
    # instead landed on 2024/Alabama, where the rendered count matched filesCount exactly. A
    # hardcoded claim written against the investigation's year would have been false about the
    # year this run actually checked -- so every number below is read back from box_navigation.
    year_folders_int = sorted(int(y) for y in box_navigation.get("year_subfolders_found", []))
    pre_window_years = [y for y in year_folders_int if y < int(c.WINDOW_START[:4])]
    pre_window_all_odd = bool(pre_window_years) and all(y % 2 == 1 for y in pre_window_years)
    window_years_found = box_navigation.get("window_year_subfolders_found", [])
    window_fully_annual = (
        sorted(int(y) for y in window_years_found) == list(WINDOW_YEARS)
        if window_years_found else False
    )

    if window_fully_annual:
        cadence_claim = (
            "a per-state-year subfolder exists in the NRUM Data Box share for every D1 "
            f"window year (verified this run: {window_years_found}); this directly "
            "contradicts a blanket 'TPO is biennial, not annual' claim for the D1 window "
            "specifically, though whether every individual state resurveys annually (as "
            "opposed to the release/folder cadence being annual) was not checked"
        )
    elif window_years_found:
        cadence_claim = (
            f"per-state-year subfolders found for D1 window years {window_years_found} "
            f"out of {list(WINDOW_YEARS)} (verified this run) -- window coverage by folder "
            "is incomplete, not annual throughout"
        )
    else:
        cadence_claim = "no D1 window year subfolder was found this run"
    if pre_window_all_odd:
        cadence_claim += (
            f"; pre-{c.WINDOW_START[:4]} subfolders found only for odd years back to "
            f"{min(pre_window_years)} (biennial cadence, verified this run)"
        )
    elif pre_window_years:
        cadence_claim += (
            f"; pre-{c.WINDOW_START[:4]} subfolders found for years {pre_window_years} "
            "(not strictly biennial, verified this run)"
        )

    listed = box_navigation.get("files_listed_this_page")
    claimed = box_navigation.get("filescount_per_box_metadata")
    probed_year = box_navigation.get("probed_year")
    if listed is None or claimed is None:
        pagination_note = (
            "the per-year rendered-item-count vs. filesCount comparison was not performed "
            "this run (year folder listing unavailable)"
        )
    elif listed < claimed:
        pagination_note = (
            f"for the probed year ({probed_year}), Box's rendered item list returned "
            f"{listed} files while that folder's own filesCount metadata claims {claimed} "
            "-- confirmed page-capped for at least this year"
        )
    else:
        pagination_note = (
            f"for the probed year ({probed_year}), Box's rendered item list returned "
            f"{listed} files, matching that folder's filesCount metadata ({claimed}) exactly "
            "-- no truncation observed for this specific year, though only one of the eight "
            "window years was checked and a different year could still be page-capped"
        )

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
        access={
            "route": (
                f"{nrum_downloads_url} -> {box_share_url} -> "
                f"{box_share_url}/folder/<year-subfolder-id> -> "
                f"{BOX_LEGACY_DOWNLOAD_BASE}?rm=box_download_shared_file&...&file_id=f_<id>"
            ),
            "status": "verified" if harvest_origin_available else "not_obtainable",
            "reason": (
                (
                    "reachable and machine-readable, but only via an undocumented Box "
                    "legacy-download redirect discovered by reading the share page's JS "
                    "bundle, not the modern share URL (200 HTML app shell) or its embedded "
                    "authenticated_download_url (401 without a browser session); per-state "
                    "coverage per year is not exhaustively verified (see coverage_span)"
                ) if harvest_origin_available else
                "no probed route -- including the Box folder discovered this run -- yielded "
                "a machine-readable file whose sheets distinguish harvest origin from mill "
                "receipts; see findings.route_probes and findings.box_navigation"
            ),
        },
        extracts=extracts,
        findings={
            "route_probes": probes,
            "harvest_origin_available": harvest_origin_available,
            "chosen_route": chosen,
            "box_navigation": box_navigation,
        },
    )


def main() -> None:
    client = c.build_client()
    run_fia(client)
    run_tpo(client)
    fia_summary = c.load_summary(SOURCE_FIA)
    tpo_summary = c.load_summary(SOURCE_TPO)
    print(
        "FIA:", fia_summary["access"]["status"],
        "| sampling error field:", fia_summary["findings"]["sampling_error_field"],
        "| evaluation vintage field:", fia_summary["findings"]["evaluation_vintage_field"],
    )
    print(
        "TPO:", tpo_summary["access"]["status"],
        "| chosen route:", tpo_summary["findings"]["chosen_route"],
    )


if __name__ == "__main__":
    main()
