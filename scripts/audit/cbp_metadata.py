# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-CBP-001: discover CBP's NAICS predicate and official EMPSZES/LFO codes per vintage from
metadata, then execute one keyed 113310 pull per available year.

Deviations from the plan's illustrative code, established empirically against the live API
during this task (not from memory or the reference repo):

1. **The 302-to-HTML-error trap is real and broader than a missing key.** `api.census.gov`
   answers a request with no `key` param by redirecting to `missing_key.html`, and a request
   with a syntactically-plausible but wrong `key` by redirecting to `invalid_key.html` -- both
   confirmed live. `httpx.Client(follow_redirects=True)` (`_common.build_client`) follows both,
   landing on an HTML page served with HTTP 200. Status-based success checks, or a bare
   `resp.json()` call relying on `HTTPStatusError` to catch the bad case, both fail here: the
   status is 200 and the body is real bytes, just not JSON. `classify_data_body` is the single
   point that tells a real tabular answer apart from either error page, keyed on content-type
   before ever attempting to parse the body -- and, for a non-JSON body, on the page's own
   `<title>` (`html_title`), so a Census maintenance page or rate-limit interstitial is never
   folded into the same "the key is bad" bucket as an actual missing/invalid-key redirect.

2. **CBP's metadata publishes no EMPSZES/LFO code-label crosswalk for this dataset -- measured
   by probing every keyless route that could plausibly carry one, not assumed from a single
   endpoint checked once.** The plan's illustrative `value_list` helper reads
   `payload["values"]["item"]` from `/variables/{VAR}.json` -- a shape used by some other Census
   APIs, but this dataset's response has no `values` key. `probe_empszes_metadata_crosswalk`
   checks that endpoint plus two more candidates per year -- `groups.json` (a group index, no
   per-variable detail) and the group detail document named by EMPSZES's own `group` field
   (`groups/{group}.json`, which lists every variable in that group, including EMPSZES's own
   entry, or entries -- confirmed live for 2018, where EMPSZES belongs to two groups at once)
   -- and records `{url, status, carries_values_crosswalk}` for each in
   `empszes_metadata_crosswalk_probe_by_year`. Every candidate probed returned no crosswalk for
   every available year -- the count of candidates checked lives in that finding key each run,
   not as a number typed here. `empszes_by_year` is therefore populated instead from the data
   pull's own rows (`EMPSZES`/`EMPSZES_LABEL` are requested as unfiltered output columns in
   attempts 1-2 below): distinct `(EMPSZES, EMPSZES_LABEL)` pairs actually observed in the
   113310 x state slice (`empszes_pairs_from_rows`). That is an OBSERVATION over the pulled
   slice, not
   SRC-CBP-001's official enumeration -- a size class with zero logging establishments in every
   state a given year produces no row and is silently absent from it. `empszes_by_year[year]`
   says this in the data itself (a `scope`/`note` field alongside `pairs`, not only in this
   docstring), so a downstream reader cannot mistake it for the authoritative list the metadata
   probe already established does not exist. `LFO` is only ever used as a filter (`="001"`) or
   omitted, never selected as an output column, so no attempt here can ever yield a full LFO
   crosswalk from its rows even once a pull succeeds -- `lfo_by_year` stays `null` with that
   limitation recorded in `notes` per year.

3. **A key genuinely present in this repo's `.env` does not authenticate.** Confirmed against
   both this dataset and, as a control ruling out a CBP-specific malformed query, against a
   wholly different dataset (ACS1) with the same key: both return HTTP 200 with an "Invalid
   Key" HTML page. Every keyed request in a run against this credential is therefore expected
   to fail; the script still performs every keyed request for real (it does not special-case
   "this key looks broken, skip the network calls") so a fixed credential needs no code change
   to start succeeding, and so `access.status`/`notes` report what THIS run actually measured
   -- `access.reason` is interpolated from the distinct failure causes actually recorded in
   `working_query_by_year`, not hardcoded to name the credential regardless of what happened.

4. **Every window year gets an explicit entry in every by-year finding, not only the years that
   responded.** A year outside `years_available` (a confirmed non-200 like 2024's 404, or a
   transport-failure `0` that `probe()` never retries) is backfilled with `null` plus a
   `notes` entry naming which of the two it was (`unavailable_year_reason`) -- a missing key
   and `null` are different facts to a downstream reader, and the dispatch that opened this
   task named that distinction directly.
"""

from __future__ import annotations

import json
import os
import re

import httpx

import _common as c

SOURCE = "cbp_metadata"
BASE = "https://api.census.gov/data/{year}/cbp"
NAICS_RE = re.compile(r"^NAICS\d{4}$")
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Only these two `classify_data_body` outcomes are evidence of a credential problem specifically
# -- see `zero_pull_cause`. Any other non-"ok" outcome (a maintenance page, a rate-limit
# interstitial, a malformed-JSON body) must fall through to "query_bug" instead.
_AUTH_REJECTION_STATUSES = frozenset({"invalid_key", "missing_key"})

# The scope tag `empszes_by_year[year]["scope"]` carries when populated -- deliberately not the
# official metadata enumeration; see module docstring point 2.
EMPSZES_OBSERVED_SCOPE = "observed_in_113310_state_slice"


def html_title(body: bytes) -> str:
    """The HTML `<title>` text, lowercased and stripped, or `""` if there isn't one (including
    when `body` isn't HTML at all). Case-insensitive on the tag itself (`<TITLE>` matches too)."""
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return match.group(1).decode("utf-8", "replace").strip().lower()


def classify_data_body(content_type: str, body: bytes) -> tuple[str, list | None]:
    """Classify one response from the keyed CBP data-pull endpoint.

    Census answers a missing OR invalid key with HTTP 200 after following the redirect to an
    HTML error page -- status alone cannot distinguish that from a real answer (see module
    docstring, point 1). Content-type is what discriminates a real answer from any HTML page;
    the page's own `<title>` then discriminates a credential rejection from anything else
    non-JSON (a maintenance page, a rate-limit interstitial, or anything else Census might ever
    serve at 200 that isn't the data). Returns:
      ("ok", header_and_rows)   -- content-type carries "json" and the body parses as a
                                    non-empty list of lists (the tabular header-plus-rows shape
                                    this endpoint returns for a `get=`/`for=` query).
      ("invalid_key", None)     -- non-JSON content-type and the page's `<title>` is
                                    "Invalid Key" (Census's page for a syntactically-plausible
                                    but unregistered key).
      ("missing_key", None)     -- non-JSON content-type and the page's `<title>` is
                                    "Missing Key" (Census's page for no `key` param at all).
      ("non_json_error", None)  -- non-JSON content-type but neither known title matched. Must
                                    NOT be assumed to be a credential problem -- `zero_pull_cause`
                                    relies on this function never folding an unrelated non-JSON
                                    response into the same bucket as an actual key rejection.
      ("bad_shape", None)       -- content-type claims JSON but the body doesn't parse, or
                                    parses to something other than a non-empty list of lists
                                    (e.g. a dict, an empty list, a list of scalars).
    """
    if "json" not in content_type:
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


def naics_predicate_matches(names: list[str]) -> list[str]:
    """Every variable name matching `^NAICS[0-9]{4}$`, sorted. Always a list -- zero matches is
    `[]`, one match is a one-element list, two or more is every match -- so the caller can
    never narrow an ambiguous predicate by indexing into this function's result; it has to
    look at the length and decide, which is exactly what main() does below."""
    return sorted(n for n in names if NAICS_RE.match(n))


def zero_pull_cause(*, state_available: bool, attempt_statuses: list[str]) -> str:
    """Why every attempt in the keyed 113310 pull failed for a year, so a note can name the
    real cause instead of letting one masquerade as another (plan Step 3).

    The plan's illustrative decision tree names three causes -- geography absent, query still
    wrong, size crossing unavailable (the last of which is a *success* path: attempt 3
    breaking the loop, never reaching this function) -- and has no branch for "every attempt
    came back as a key-rejection page". Without one, an invalid or missing `CENSUS_API_KEY`
    reads as "the query is wrong": a credential problem misdiagnosed as a script bug.
    `attempt_statuses` are `classify_data_body` outcomes plus "http_error" for a raised
    `HTTPStatusError`, in attempt order; only reached when none of them was "ok". Only
    `invalid_key`/`missing_key` count as the auth family -- `non_json_error` (a maintenance
    page, a rate-limit interstitial, anything else non-JSON) falls through to `query_bug`
    rather than being assumed to be the same credential problem."""
    if not state_available:
        return "geography_unavailable"
    if attempt_statuses and all(s in _AUTH_REJECTION_STATUSES for s in attempt_statuses):
        return "auth_error"
    return "query_bug"


def empszes_pairs_from_rows(header: list[str], body: list[list]) -> list[dict] | None:
    """Distinct `(EMPSZES, EMPSZES_LABEL)` pairs observed in a successful data-pull response,
    sorted by code. Returns `None` when the response didn't carry both columns (attempt 3
    drops EMPSZES entirely) -- that must read as "not observed", never as an empty list
    standing in for "this vintage has no size classes". This is an OBSERVATION over whatever
    rows the pull returned, not the official metadata enumeration -- see module docstring
    point 2; the caller is responsible for saying so in the persisted record."""
    if "EMPSZES" not in header or "EMPSZES_LABEL" not in header:
        return None
    i_code, i_label = header.index("EMPSZES"), header.index("EMPSZES_LABEL")
    pairs = {(row[i_code], row[i_label]) for row in body}
    return [{"code": code, "label": label} for code, label in sorted(pairs)]


def group_names_from_field(group_field: str | None) -> list[str]:
    """A variable's `group` field, split into every group name it names. Usually one name, but
    confirmed live for 2018's EMPSZES ("CB1800ZBP,CB1800CBP" -- shared between that year's ZIP
    Code Business Patterns and County Business Patterns groups): Census does not always treat
    `group` as a single identifier, and `f"groups/{group}.json"` on the raw field 404s on the
    literal comma. Returns `[]` for `None` or an empty/whitespace-only field."""
    if not group_field:
        return []
    return [g.strip() for g in group_field.split(",") if g.strip()]


def crosswalk_present_in_payload(payload: dict, variable: str) -> bool:
    """True if `payload` carries an enumerated `values.item` code list for `variable`, checked
    at every shape this task's three candidate metadata routes can take: a flat single-variable
    document (`/variables/{variable}.json`, where `payload` itself is the candidate), a
    group-index document with no per-variable detail at all (`/groups.json`, which never
    matches), and a group document listing every variable in that group
    (`/groups/{group}.json`, where `variable`'s own entry sits under `payload["variables"]`).
    Never raises on a malformed or unexpected shape -- absence is the answer, not a crash."""
    candidates = [payload]
    variables = payload.get("variables")
    if isinstance(variables, dict):
        entry = variables.get(variable)
        if isinstance(entry, dict):
            candidates.append(entry)
    return any(
        isinstance(cand.get("values"), dict) and isinstance(cand["values"].get("item"), dict)
        for cand in candidates
    )


def unavailable_year_reason(probe_status: int) -> str:
    """Why a window year has no CBP data this run, for the note beside its `null` entries.
    Distinguishes a genuine transport blip (`probe()`'s `(0, 0)` sentinel, which `probe` never
    retries -- re-running may find the year published after all) from a real, confirmed status
    Census actually returned (e.g. 2024's 404). Deliberately does not characterize a bare
    non-200 status as "a confirmed absence" in general -- a 5xx would be a server error, not
    evidence the year isn't published; only the literal status is reported here."""
    if probe_status == 0:
        return ("the keyless cbp.json probe returned no response at all this run (a transport "
                "failure, not a confirmed absence) -- re-run this task to resolve it")
    return f"cbp.json returned HTTP {probe_status} for this year, not 200"


def fetch_variable_doc(client: httpx.Client, year: int, variable: str, extracts: list) -> None:
    """Fetch and record `/variables/{variable}.json` verbatim (keyless; a real, useful extract
    -- label, concept, predicateType -- even though it carries no code/label crosswalk for this
    dataset, see module docstring point 2). Callers only invoke this once `variable in names`
    from `variables.json` is already confirmed, so this is pure extract retention, not an
    existence check -- `has_lfo`/`has_empszes` (computed from `variables.json`) are the
    existence checks, independent of this function and of whether this fetch itself succeeds."""
    url = f"{BASE.format(year=year)}/variables/{variable}.json"
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError:
        return None
    extracts.append(c.record_extract(
        SOURCE, url, f"{year}/{variable.lower()}.json", resp.content))
    return None


def probe_empszes_metadata_crosswalk(
    client: httpx.Client, year: int, empszes_doc: dict, empszes_status: int, extracts: list
) -> list[dict]:
    """Probe every keyless metadata route that could plausibly carry an EMPSZES values
    crosswalk for this vintage, and record what each actually returned -- so "CBP's metadata
    publishes no EMPSZES value list" is measured this run, not asserted from a single endpoint
    checked once during development (module docstring point 2). `empszes_doc` is
    `/variables/EMPSZES.json`'s already-fetched, already-recorded payload; its own `group`
    field names the candidate group document."""
    ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
    probe = [{
        "url": ez_url, "status": empszes_status,
        "carries_values_crosswalk": crosswalk_present_in_payload(empszes_doc, "EMPSZES"),
    }]

    groups_url = f"{BASE.format(year=year)}/groups.json"
    gresp = c.request(client, groups_url)
    extracts.append(c.record_extract(SOURCE, groups_url, f"{year}/groups.json", gresp.content))
    probe.append({
        "url": groups_url, "status": gresp.status_code,
        "carries_values_crosswalk": crosswalk_present_in_payload(gresp.json(), "EMPSZES"),
    })

    # `group` can name more than one group, comma-separated -- confirmed live for 2018
    # ("CB1800ZBP,CB1800CBP": EMPSZES is shared between the ZIP Code Business Patterns and
    # County Business Patterns groups that year). Probe every named group's own document, not
    # just the first -- treating the field as a single name 404s on the literal comma.
    for group in group_names_from_field(empszes_doc.get("group")):
        group_url = f"{BASE.format(year=year)}/groups/{group}.json"
        gdresp = c.request(client, group_url)
        extracts.append(c.record_extract(
            SOURCE, group_url, f"{year}/groups_{group}.json", gdresp.content))
        probe.append({
            "url": group_url, "status": gdresp.status_code,
            "carries_values_crosswalk": crosswalk_present_in_payload(gdresp.json(), "EMPSZES"),
        })
    return probe


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")

    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    years: list[int] = []
    predicates, empszes, lfo, geo_levels = {}, {}, {}, {}
    working, rows, flags, crosswalk_probe = {}, {}, {}, {}
    probe_status: dict[str, int] = {}
    notes: list[str] = []
    any_keyed_success = False

    for year in c.WINDOW_YEARS:
        status, _ = c.probe(client, f"{BASE.format(year=year)}.json")
        probe_status[str(year)] = status
        if status != 200:
            # probe() has no retry and returns (0, 0) on a TransportError; that "0" is a
            # transient failure, not a finding. Any other non-200 (e.g. 2024's 404) is a real,
            # confirmed status. Both cases -- and the note distinguishing them -- are handled
            # uniformly in the backfill pass after this loop (module docstring point 4), so
            # every window year gets an explicit entry rather than only years_available.
            continue
        years.append(year)

        meta = c.request(client, f"{BASE.format(year=year)}.json")
        extracts.append(c.record_extract(
            SOURCE, f"{BASE.format(year=year)}.json", f"{year}/dataset.json", meta.content))

        vresp = c.request(client, f"{BASE.format(year=year)}/variables.json")
        extracts.append(c.record_extract(
            SOURCE, f"{BASE.format(year=year)}/variables.json", f"{year}/variables.json",
            vresp.content))
        names = list(vresp.json()["variables"].keys())
        matches = naics_predicate_matches(names)
        predicates[str(year)] = matches[0] if len(matches) == 1 else matches

        has_empszes = "EMPSZES" in names
        has_lfo = "LFO" in names

        if has_empszes:
            ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
            ez_resp = c.request(client, ez_url)
            extracts.append(c.record_extract(
                SOURCE, ez_url, f"{year}/empszes.json", ez_resp.content))
            crosswalk_probe[str(year)] = probe_empszes_metadata_crosswalk(
                client, year, ez_resp.json(), ez_resp.status_code, extracts)
        else:
            crosswalk_probe[str(year)] = None
            notes.append(
                f"{year}: EMPSZES is not a variable for this vintage; no metadata-crosswalk "
                "probe was run"
            )

        # lfo_by_year is null either way: when LFO isn't a variable at all, and also when it
        # is one, because no attempt below selects LFO/LFO_LABEL as output columns (module
        # docstring point 2) -- there is no code path that ever derives a real LFO crosswalk
        # in this script. Recorded unconditionally here (not only on the branch that goes on
        # to attempt a pull) so an ambiguous/absent NAICS predicate below still leaves a note
        # explaining lfo_by_year rather than silently skipping it for that year.
        lfo[str(year)] = None
        if has_lfo:
            fetch_variable_doc(client, year, "LFO", extracts)
            notes.append(
                f"{year}: LFO exists as a variable for this vintage, but no attempt below "
                "selects LFO/LFO_LABEL as output columns (LFO is only ever used as the "
                "filter ='001' or omitted) -- lfo_by_year cannot be derived from this pull's "
                "rows even when a pull succeeds. A genuine LFO crosswalk would need a "
                "dedicated unfiltered LFO,LFO_LABEL query, which this script does not attempt."
            )
        else:
            notes.append(f"{year}: LFO is not a variable for this vintage")

        gresp = c.request(client, f"{BASE.format(year=year)}/geography.json")
        extracts.append(c.record_extract(
            SOURCE, f"{BASE.format(year=year)}/geography.json", f"{year}/geography.json",
            gresp.content))
        levels = sorted({g["name"] for g in gresp.json().get("fips", []) if "name" in g})
        geo_levels[str(year)] = levels

        if len(matches) != 1:
            # Ambiguous (2+) or absent (0) predicate: never silently narrow by picking one --
            # querying needs a single, confirmed predicate variable name. `predicates[year]`
            # already recorded the full match list above; this branch is what keeps the query
            # below from contradicting that record by picking matches[0] anyway.
            reason = "no_naics_predicate_found" if not matches else "ambiguous_naics_predicate"
            working[str(year)] = {"status": reason}
            rows[str(year)] = None
            flags[str(year)] = None
            empszes[str(year)] = None
            notes.append(f"{year}: {reason} ({matches}); keyed 113310 pull skipped")
            continue
        naics = matches[0]

        get_cols = ["NAME", f"{naics}_LABEL", "EMPSZES", "EMPSZES_LABEL", "ESTAB", "EMP",
                    "EMP_F", "EMP_N"]
        no_size = [col for col in get_cols if not col.startswith("EMPSZES")]
        # Attempt 3 drops EMPSZES entirely. If it succeeds where 1 and 2 fail, the size
        # crossing is genuinely unavailable for this vintage -- a finding. If none succeed,
        # `zero_pull_cause` distinguishes an auth failure from a genuine query bug.
        attempts = [
            {"get": ",".join(get_cols), "for": "state:*", naics: c.INDUSTRY_CODE, "LFO": "001"},
            {"get": ",".join(get_cols), "for": "state:*", naics: c.INDUSTRY_CODE},
            {"get": ",".join(no_size), "for": "state:*", naics: c.INDUSTRY_CODE},
        ]
        attempt_statuses: list[str] = []
        winning_content: bytes | None = None
        for attempt_no, attempt in enumerate(attempts, start=1):
            try:
                # `key` is merged into `params` only here, at request time -- it never enters
                # `attempt` (what gets recorded below), so there is nothing to filter out of
                # the record after the fact (module docstring: elide at build time).
                dresp = c.request(client, BASE.format(year=year), params={**attempt, "key": key})
            except httpx.HTTPStatusError:
                attempt_statuses.append("http_error")
                continue
            # Every attempt's raw bytes are retained, under a per-attempt path -- three
            # attempts writing the same `data_113310.json` path would leave later attempts'
            # extract records pointing at a file whose hash no longer matches what they
            # recorded (verbatim retention means recording once per distinct fetch, not
            # silently overwriting).
            extracts.append(c.record_extract(
                SOURCE, BASE.format(year=year), f"{year}/data_113310_attempt{attempt_no}.json",
                dresp.content))
            outcome, payload = classify_data_body(
                dresp.headers.get("content-type", ""), dresp.content)
            attempt_statuses.append(outcome)
            if outcome != "ok":
                continue
            header, body = payload[0], payload[1:]
            working[str(year)] = {**attempt, "size_crossing_available": "EMPSZES" in header}
            rows[str(year)] = len(body)
            idx = {name: i for i, name in enumerate(header)}
            flags[str(year)] = {
                col: sorted({(r[idx[col]] or "") for r in body})
                for col in ("EMP_F", "EMP_N") if col in idx
            }
            pairs = empszes_pairs_from_rows(header, body)
            empszes[str(year)] = None if pairs is None else {
                "scope": EMPSZES_OBSERVED_SCOPE,
                "note": (
                    "NOT the official CBP metadata enumeration -- Census publishes no EMPSZES "
                    "values crosswalk for this dataset (see "
                    "empszes_metadata_crosswalk_probe_by_year). A size class with zero "
                    "logging establishments in every state this year is silently absent from "
                    "`pairs`."
                ),
                "pairs": pairs,
            }
            winning_content = dresp.content
            any_keyed_success = True
            break
        else:
            cause = zero_pull_cause(
                state_available="state" in levels, attempt_statuses=attempt_statuses)
            working[str(year)] = {"status": cause}
            rows[str(year)] = None
            flags[str(year)] = None
            empszes[str(year)] = None
            notes.append(
                f"{year}: keyed 113310 pull failed for all {len(attempts)} attempts -- cause: "
                f"{cause} (attempt statuses: {attempt_statuses})"
            )
            if cause == "auth_error":
                distinct = sorted(set(attempt_statuses))
                notes.append(
                    f"{year}: every attempt's response matched Census's key-rejection page "
                    f"({distinct}); rows_113310_by_year, flag_values_by_year and "
                    "empszes_by_year are null for this year, not measured as zero or empty; "
                    "working_query_by_year carries {'status': 'auth_error'} rather than the "
                    "successful query shape -- re-run this task once CENSUS_API_KEY "
                    "authenticates."
                )

        # Retain the WINNING attempt's bytes under the canonical filename the plan's Produces
        # block names -- only on a real success, never an HTML error page recorded as if it
        # were data. Reuses the already-fetched bytes; no re-fetch.
        if winning_content is not None:
            extracts.append(c.record_extract(
                SOURCE, BASE.format(year=year), f"{year}/data_113310.json", winning_content))

    # Every window year gets an explicit entry in every by-year finding -- a year outside
    # years_available (confirmed non-200, or probe()'s (0,0) transport sentinel) is backfilled
    # with null plus a note naming which of the two it was, never left as a missing key.
    for year in c.WINDOW_YEARS:
        y = str(year)
        if year in years:
            continue
        predicates.setdefault(y, None)
        empszes.setdefault(y, None)
        lfo.setdefault(y, None)
        working.setdefault(y, None)
        geo_levels.setdefault(y, None)
        rows.setdefault(y, None)
        flags.setdefault(y, None)
        crosswalk_probe.setdefault(y, None)
        notes.append(
            f"{year}: not in years_available -- {unavailable_year_reason(probe_status[y])}; "
            f"every other finding for {year} is null."
        )

    covered = f"{min(years)}-{max(years)}" if years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y not in years)
    # Both non-"verified" cases below are "not_obtainable", not "documented": nothing about the
    # keyed route was learned from documentation -- every keyed request was actually attempted
    # live, and the *data* it exists to fetch could not be obtained this run, whether because no
    # dataset document ever came back or because the credential never authenticated. "verified"
    # is reserved for what it says: at least one year's keyed pull actually returned real rows.
    access_status = "verified" if any_keyed_success else "not_obtainable"
    # Interpolated from what was actually recorded in working_query_by_year, not hardcoded --
    # the failure could be an auth rejection, but it could also be a geography or query problem
    # (or a mix across years), and the reason must say which was actually observed this run.
    failure_causes = sorted({
        v["status"] for v in working.values() if isinstance(v, dict) and "status" in v
    })
    access_reason = (
        None if access_status == "verified" else
        (
            "CBP metadata routes (dataset document, variables, EMPSZES/LFO variable docs, "
            "groups, geography) returned real JSON for every year in years_available, but "
            "the keyed 113310 data pull did not succeed for any window year this run -- "
            f"causes recorded in working_query_by_year: {failure_causes}; see findings.notes "
            "per year for detail"
        ) if years else
        "no window year returned a CBP dataset document"
    )
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
            "years_available": years,
            "dataset_probe_status_by_year": probe_status,
            "naics_predicate_by_year": predicates,
            "empszes_by_year": empszes,
            "empszes_metadata_crosswalk_probe_by_year": crosswalk_probe,
            "lfo_by_year": lfo,
            "working_query_by_year": working,
            "geography_levels_by_year": geo_levels,
            "rows_113310_by_year": rows,
            "flag_values_by_year": flags,
            "notes": notes,
        },
    )
    print(f"CBP years available: {years}")
    print(f"NAICS predicates: {json.dumps(predicates)}")
    print(f"window years with no CBP: {uncovered or 'none'}")


if __name__ == "__main__":
    main()
