# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-OTH-002: discover the finest NAICS detail BDS actually serves for the Logging branch.

Deviations from the plan's illustrative code, established empirically against the live API
during this task (not from memory or the reference repo):

1. **This run met HTTP 204 with a zero-length body, not a 404, for every candidate NAICS
   predicate finer than the 2-digit sector code.** Measured this run for `'113'`, `'1133'`,
   `'11331'`, and `'113310'`, and separately for the nonsense predicates `'999999'` and `'abc'`
   tried during this task's investigation (not persisted as extracts -- ad hoc, no `key`
   response body kept) -- every one of those six requests came back 204 with a
   `content-type: application/json` header and an empty body this run; no 404 was observed for
   any of them. 204 is a 2xx status: `resp.raise_for_status()` never raises, so the brief's
   `except httpx.HTTPStatusError` clause never fires, and the brief's own next line
   (`resp.json()`) raises an uncaught `json.JSONDecodeError` on an empty body -- the script
   would crash on the very first candidate finer than the sector level, not print a status and
   a zero row count as Step 2 of the brief expects. `classify_probe_body` checks
   `status == 204` before ever attempting to parse the body, naming it a distinct outcome
   (`"no_content"`) rather than a crash or a guessed `"bad_shape"` -- what that status means
   about the endpoint in general is not asserted here; only what this run's requests received.

2. **A missing or invalid `CENSUS_API_KEY` answers HTTP 200 with an HTML error page**,
   confirmed live for this endpoint with no `key` param (`<title>Missing Key</title>`) and
   with a syntactically-plausible wrong key (`<title>Invalid Key</title>`) -- the identical
   trap `cbp_metadata.py`'s `classify_data_body` exists to catch on a different Census
   dataset. Reused here as the same content-type + `<title>` approach (`html_title`,
   `classify_probe_body`), not reinvented: a bare status check cannot tell a real answer from
   an auth-rejection page, because both come back HTTP 200.

Ruling D-B binds this task: this is an access-verdict probe over five NAICS predicates.
`http_status` alone already separates a 204 ("not published at this NAICS level") from either
200 outcome; it's the response body -- a 200 auth-rejection page's HTML versus a 200 real
tabular answer -- that distinguishes "reachable but blocked" from a real answer, since those two
share the identical status. Every response this run actually receives is persisted regardless of
its status, including the 204's empty body: retaining it, sha256-sidecarred like every other
extract, is what turns "not published" into a recorded observation rather than an unrecorded
absence. Only a transport failure (no response at all, after `_common.request`'s retries)
registers no extract, because there is no body to persist. `compose_retention_rule` states this
script's own retention rule inside the artifact it shapes, per `forest_sources.py`'s established
pattern -- retention rules differ per script, so a reader must not generalise this one to any
other source's summary.
"""

from __future__ import annotations

import json
import os
import re

import httpx

import _common as c

SOURCE = "bds"
BASE = "https://api.census.gov/data/timeseries/bds"
CANDIDATES = ("11", "113", "1133", "11331", "113310")
WANTED_VARS = ("ESTAB", "FIRM", "JOB_CREATION", "JOB_DESTRUCTION", "ESTABS_ENTRY",
               "ESTABS_EXIT")

_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Only these two `classify_probe_body` outcomes are evidence of a credential problem
# specifically -- see `zero_answer_cause`. Any other non-"ok" outcome (204's genuine empty
# match, a maintenance page, a rate-limit interstitial, a malformed body) must fall through to
# the generic cause instead.
_AUTH_REJECTION_OUTCOMES = frozenset({"invalid_key", "missing_key"})


def html_title(body: bytes) -> str:
    """The HTML `<title>` text, lowercased and stripped, or `""` if there isn't one (including
    when `body` isn't HTML at all). Case-insensitive on the tag itself (`<TITLE>` matches too).
    Same approach as `cbp_metadata.py`'s function of the same name -- audit scripts are
    standalone PEP 723 files with no import between them, so this is a deliberate duplicate of
    that approach, not a divergence from it."""
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return match.group(1).decode("utf-8", "replace").strip().lower()


def classify_probe_body(status: int, content_type: str, body: bytes) -> tuple[str, list | None]:
    """Classify one response from the keyed BDS timeseries data-pull endpoint for a single
    candidate NAICS predicate.

    Status is checked before content-type, because this run met a status this task's sibling
    CBP scripts never reported meeting: 204, for every finer-than-sector NAICS candidate this
    run tried (module docstring point 1). Content-type then discriminates a real answer from an
    HTML error page; the page's own `<title>` discriminates a credential rejection from
    anything else non-JSON (module docstring point 2, reusing `cbp_metadata.py`'s approach).
    Returns:
      ("transport_failure", None) -- `status == 0`, this script's convention (matching
                                      `_common.probe`'s sentinel) for no response at all.
      ("no_content", None)       -- `status == 204` with an empty body, which this run met for
                                      every candidate this run found matching no published cell.
                                      Named as a distinct, non-error outcome rather than folded
                                      into `"bad_shape"` -- this IS the industry-detail boundary
                                      finding this run measured, not a malformed response.
      ("ok", header_and_rows)    -- content-type carries "json" and the body parses as a
                                      non-empty list of lists (the tabular header-plus-rows
                                      shape this endpoint returns for a matching predicate).
      ("invalid_key", None)      -- non-JSON content-type and the page's `<title>` is
                                      "Invalid Key".
      ("missing_key", None)      -- non-JSON content-type and the page's `<title>` is
                                      "Missing Key".
      ("non_json_error", None)   -- non-JSON content-type but neither known title matched. Must
                                      NOT be assumed to be a credential problem --
                                      `zero_answer_cause` relies on this function never folding
                                      an unrelated non-JSON response into the same bucket as an
                                      actual key rejection.
      ("bad_shape", None)        -- content-type claims JSON but the body doesn't parse, or
                                      parses to something other than a non-empty list of lists
                                      (e.g. a dict, an empty list, a list of scalars). Distinct
                                      from `"no_content"`: this is a 2xx/other status whose body
                                      claimed JSON and failed to deliver the tabular shape, not
                                      the 204-empty-body case, which never reaches this branch.
    """
    if status == 0:
        return "transport_failure", None
    if status == 204:
        return "no_content", None
    if "json" not in content_type.lower():
        title = html_title(body)
        if title == "invalid key":
            return "invalid_key", None
        if title == "missing key":
            return "missing_key", None
        return "non_json_error", None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "bad_shape", None
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        return "ok", payload
    return "bad_shape", None


def probe_result(naics: str, status: int, outcome: str, payload: list | None) -> dict:
    """Build one `naics_probe` entry (the plan's `{naics, digits, http_status, row_count,
    years_returned}` shape) from a classified response.

    `row_count`/`years_returned` are populated ONLY for the `"ok"` outcome -- every other
    outcome (204's genuine empty match, an auth-rejection page, a malformed body, a transport
    failure) reports zero rows and no years, because none of them carried parseable data rows,
    whatever the reason for the absence. The reason itself lives in `http_status` (and, for a
    caller that also inspects `outcome`, there), never folded into `row_count` as a guess."""
    row_count, years_returned = 0, []
    if outcome == "ok":
        header, rows = payload[0], payload[1:]
        if "YEAR" in header:
            yidx = header.index("YEAR")
            years_returned = sorted({int(r[yidx]) for r in rows})
        row_count = len(rows)
    return {
        "naics": naics, "digits": len(naics), "http_status": status,
        "row_count": row_count, "years_returned": years_returned,
    }


def probe_query_scope(params: dict) -> dict:
    """The `get`/`for` predicate this run's NAICS probes were actually sent with, read out of
    the same `params` dict built for each request rather than retyped as a separate literal
    beside it -- a verdict about which NAICS level BDS answers is a verdict about this one
    predicate, and a future change to the query shape (e.g. `for=us:*` instead of `state:*`)
    must change this finding automatically rather than leaving it to silently drift from what
    was actually sent. Excludes `NAICS` (the one predicate value that varies per probe, already
    recorded per row in `naics_probe`) and `key` (a secret, never persisted)."""
    return {"get": params["get"], "for": params["for"]}


def zero_answer_cause(outcomes: list[str]) -> str:
    """Why every probed NAICS code answered with zero rows this run -- reached only when even
    the 2-digit sector code, which every live run of this task so far has found answering,
    returned nothing. Distinguishes a uniform credential rejection (every probe's response was
    an auth-rejection page) from a uniform network outage (every probe got no response at all)
    from anything else, so a reader is never told "no NAICS code returned rows" when the real
    cause was a broken credential or a dead network rather than an industry-detail boundary.
    Any outcome mix that isn't uniformly one of those two families -- including a run where
    every candidate genuinely answered 204 -- falls through to the generic cause, because that
    IS the industry-detail finding this task exists to report, not an error to explain away."""
    if outcomes and all(o in _AUTH_REJECTION_OUTCOMES for o in outcomes):
        return "auth_error"
    if outcomes and all(o == "transport_failure" for o in outcomes):
        return "network_unreachable"
    return "no_naics_code_returned_rows"


def compose_retention_rule(extract_statuses: list[int]) -> dict:
    """Ruling D-B: this script's raw-retention rule, restated inside the artifact the rule
    shaped, with its counters derived from the run rather than typed. Every response this
    script actually received (any HTTP status, including 204's empty body) is registered as an
    extract; only a transport failure -- which produces no body at all -- registers none.

    The rule's first sentence covers both fetch classes, the five NAICS-detail probes and the
    single `variables.json` request, because the counters below are `len(extract_statuses)` and
    friends over ALL extracts. Scoping the sentence to the probes alone left the shipped
    `extracts_recorded: 6` sitting under a sentence about five things. The alternative --
    deriving the counters over the probe extracts only -- was rejected: it would change a
    measured value in a shipped artifact to fix a wording defect, and it would strand the
    `variables.json` fetch under no stated rule at all, which is the state `susb_layout.py`'s
    own rule text already cites this script as the precedent against."""
    return {
        "rule": (
            "This script performs two kinds of fetch and registers a body from both, so the "
            "counters below count both. From each of the five NAICS-detail probes it writes "
            "and registers a fetched body whenever the endpoint answered at all, whatever the "
            "HTTP status, and each extract's own http_status records which status it carried. "
            "It also fetches this dataset's variables.json once, before any probe, to read "
            "which of the wanted variables the dataset declares; that body is registered on "
            "the same terms and is the sixth extract whenever all five probes answer. On this "
            "access-verdict "
            "probe, http_status alone already separates a 204 with an empty body (matched no "
            "published cell) from either 200 outcome; retaining that empty body anyway, with "
            "its sha256 sidecar like every other extract, is what makes the 204 a recorded "
            "observation rather than an unrecorded absence. The two 200 outcomes -- a 200 "
            "auth-rejection HTML page and a 200 real tabular answer -- share that identical "
            "status, so only the retained bytes tell the two 200 outcomes apart. A transport "
            "failure produces no body and so registers no extract; its evidence is the probe "
            "record's http_status-0 entry instead. The counters below therefore say which "
            "statuses were retained and nothing more: a retained status 200 means the endpoint "
            "answered with a body that claimed to be data, not that the body parsed as the "
            "tabular shape. findings.naics_probe's row_count tells a status-200 parse failure "
            "apart from a status-200 real answer whenever the real answer carries at least one "
            "data row; the one shape this script cannot distinguish by row_count alone is a "
            "status-200 parse failure against a status-200 tabular answer with a header row and "
            "zero data rows -- for that case the retained body itself, not any derived count, "
            "is what a reader would need to open. "
            "Reader's caution: this rule is this script's, and the absence of a non-200 extract "
            "under another source in this audit is not evidence that no non-200 response "
            "occurred there."
        ),
        "extracts_recorded": len(extract_statuses),
        "extracts_with_non_200_status": sum(1 for s in extract_statuses if s != 200),
        "non_200_statuses_recorded": sorted({s for s in extract_statuses if s != 200}),
    }


def fetch_naics_probe(client: httpx.Client, params: dict) -> tuple[int, str, bytes]:
    """GET the BDS timeseries data endpoint for one candidate NAICS predicate, returning
    whatever this run actually received: status, content-type header, and raw bytes.

    A genuine HTTP error status (any 4xx other than 429, or a 5xx that exhausted
    `_common.request`'s retries) is caught and its status/body pair returned rather than
    raised -- that pair is itself part of the evidence Ruling D-B requires this script to keep.
    A transport failure (no response at all, after retries) returns the `(0, "", b"")` sentinel
    instead: one candidate's transient failure must not abandon the other four probes in the
    same run, matching `qcew_routes.py`'s established handling of the same situation."""
    try:
        resp = c.request(client, BASE, params=params)
        return resp.status_code, resp.headers.get("content-type", ""), resp.content
    except httpx.HTTPStatusError as exc:
        return (exc.response.status_code, exc.response.headers.get("content-type", ""),
                exc.response.content)
    except httpx.TransportError:
        return 0, "", b""


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")
    client = c.build_client()
    extracts: list[c.ExtractRecord] = []

    vresp = c.request(client, f"{BASE}/variables.json")
    extracts.append(c.record_extract(
        SOURCE, f"{BASE}/variables.json", "variables.json", vresp.content))
    names = set(vresp.json()["variables"].keys())
    present = [v for v in WANTED_VARS if v in names]

    probe_rows: list[dict] = []
    outcomes: list[str] = []
    years: set[int] = set()
    query_scope: dict | None = None

    for naics in CANDIDATES:
        params = {"get": "YEAR,ESTAB", "for": "state:*", "NAICS": naics, "key": key}
        # Captured from the first iteration's own params dict, not retyped -- every candidate
        # in CANDIDATES sends the same get=/for= predicate, only NAICS varies, so one capture
        # covers the whole probe and stays tied to what was actually sent.
        if query_scope is None:
            query_scope = probe_query_scope(params)
        status, content_type, body = fetch_naics_probe(client, params)
        outcome, payload = classify_probe_body(status, content_type, body)
        outcomes.append(outcome)

        # Ruling D-B: persist whatever this run actually received, whatever its status --
        # http_status alone already separates a 204 from either 200 outcome, but retaining the
        # 204's empty body anyway makes it a recorded observation rather than an unrecorded
        # absence. Only between the two 200 outcomes is the retained body itself the evidence.
        # Only a transport failure (status 0, no body) registers nothing.
        if status != 0:
            extracts.append(c.record_extract(
                SOURCE, BASE, f"naics_{naics}.json", body, http_status=status))

        row = probe_result(naics, status, outcome, payload)
        probe_rows.append(row)
        years.update(row["years_returned"])

    answering = [p for p in probe_rows if p["row_count"] > 0]
    finest = max((p["naics"] for p in answering), key=len, default=None)
    six_digit = any(p["naics"] == "113310" and p["row_count"] > 0 for p in probe_rows)

    # `covered` (Task 1 schema) is the part of D1's window this source covers -- clamped to the
    # window, because BDS's real published range (1978-2023, confirmed live for NAICS=11) runs
    # far wider than D1; `published_start`/`published_end` below carry the unclamped range, and
    # `years_available` (findings) carries every year returned, also unclamped.
    covered_years = sorted(years & set(c.WINDOW_YEARS))
    covered = f"{min(covered_years)}-{max(covered_years)}" if covered_years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y not in years)

    access_status = "verified" if answering else "not_obtainable"
    access_reason = None if answering else zero_answer_cause(outcomes)

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(years)) if years else "",
            "published_end": str(max(years)) if years else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": covered, "uncovered": uncovered,
        },
        access={"route": BASE, "status": access_status, "reason": access_reason},
        extracts=extracts,
        findings={
            "naics_probe": probe_rows,
            "finest_naics_available": finest,
            "six_digit_logging_available": six_digit,
            "years_available": sorted(years),
            "variables_present": present,
            # Point 7: finest_naics_available/six_digit_logging_available are verdicts about
            # this one get=/for= predicate, not about BDS in general -- this key discloses that
            # scope from the actual request params rather than leaving it implicit.
            "probe_query_scope": query_scope,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
        },
    )
    print("BDS finest NAICS:", finest, "| six-digit Logging:", six_digit)
    for p in probe_rows:
        print(" ", p["naics"], "->", p["http_status"], f"{p['row_count']} rows")


if __name__ == "__main__":
    main()
