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

2. **Whether CBP's metadata publishes an EMPSZES code-label crosswalk varies by vintage --
   measured every year by probing every keyless route that could plausibly carry one, never
   assumed uniform from a single endpoint checked once.** The plan's illustrative `value_list`
   helper reads `payload["values"]["item"]` from `/variables/{VAR}.json`. **2017's real
   response has exactly that shape -- 44 code/label pairs, `"001": "All establishments"`
   onward.** Every other available year checked this run carried none;
   `empszes_metadata_crosswalk_probe_by_year` records which years, not this docstring.
   A first pass at this task checked only 2021 by hand, found no crosswalk, and generalized
   that to every vintage; the generalization was wrong, and the fix was to make the check
   something the script does every year rather than something a person did once.
   `probe_empszes_metadata_crosswalk` checks `/variables/EMPSZES.json` plus two more
   candidates per year -- `groups.json` (a group index, no per-variable detail) and every
   group detail document named by EMPSZES's own `group` field (`groups/{group}.json`, which
   lists every variable in that group, including EMPSZES's own entry -- confirmed live for
   2018 that this field can name more than one group at once) -- and records `{url, status,
   carries_values_crosswalk}` for each in `empszes_metadata_crosswalk_probe_by_year`, plus the
   actual `{code: label}` dict from whichever candidate carried one
   (`crosswalk_items_from_payload`). Where the official enumeration exists (2017),
   `empszes_by_year[year]` carries it directly, tagged `"source":
   "official_metadata_crosswalk"`. Where it doesn't (2018 onward, confirmed absent this way,
   not merely unfetched), `empszes_by_year[year]` falls back to an OBSERVATION over the keyed
   pull's own rows instead: `EMPSZES`/`EMPSZES_LABEL` are requested as unfiltered output
   columns in attempts 1-2 below, so distinct `(EMPSZES, EMPSZES_LABEL)` pairs actually
   returned (`empszes_pairs_from_rows`) are tagged `"source": "observed_in_113310_state_slice"`
   -- an under-count risk a bare list would hide (a size class with zero logging
   establishments in every state that year produces no row), which is why the source is
   recorded in the data itself, not only in this docstring. `LFO` is only ever used as a
   filter (`="001"`) or omitted, never selected as an output column, so no attempt here can
   ever yield a full LFO crosswalk from its rows even once a pull succeeds -- `lfo_by_year`
   stays `null` with that limitation recorded in `notes` per year.

3. **A key can be genuinely present in `.env` and still not authenticate -- during this task's
   development runs, the key then in `.env` did not.** Confirmed against both this dataset
   and, as a control ruling out a CBP-specific malformed query, against a wholly different
   dataset (ACS1) with the same key: both returned HTTP 200 with an "Invalid Key" HTML page.
   Those runs are why `classify_data_body` and `zero_pull_cause` exist at all, and they are the
   provenance of this file's key-rejection fixtures. What a credential does is not a fact about
   this file, though, and this docstring does not assert one: a later run with a working key
   succeeded, and `access.status`, `rows_113310_by_year` and `extracts` in the written summary
   record which years that was -- not this text. That split is the design. The script performs
   every keyed request for real (it does not special-case "this key looks broken, skip the
   network calls"), so a fixed credential needs no code change to start succeeding, and
   `access.status`/`notes` report what THAT run actually measured -- `access.reason` is
   interpolated from the distinct failure causes actually recorded in `working_query_by_year`,
   not hardcoded to name the credential regardless of what happened.

4. **Every window year gets an explicit entry in every by-year finding, not only the years that
   responded.** A year outside `years_available` (a confirmed non-200 like 2024's 404, or a
   transport-failure `0` that `probe()` never retries) is backfilled with `null` plus a
   `notes` entry naming which of the two it was (`unavailable_year_reason`) -- a missing key
   and `null` are different facts to a downstream reader, and the dispatch that opened this
   task named that distinction directly.

5. **A run that stops writing the canonical `data_113310.json` on failure also removes any
   stale one a prior run left behind, at the start of processing each year -- before this
   run has decided whether it has a real answer.** Making the write conditional on success
   fixed what a *future* failing run does; it did nothing about what a *past* one already
   wrote. Without this, a year whose keyed pull fails this run but succeeded (or, before this
   fix, "succeeded") in some earlier run would keep an old file sitting at the exact filename
   the plan's Produces block names, unregistered in this run's `extracts` and therefore vouched
   for by nothing -- worse than absent, because it looks current to anything that opens the
   path directly instead of going through the manifest.
"""

from __future__ import annotations

import json
import os
import re
import shutil

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

# The two values `empszes_by_year[year]["source"]` can carry. Fix round 2: both are real --
# 2017 genuinely has the official enumeration in metadata; 2018 onward fall back to the
# row-derived observation. Task 8 needs to tell them apart, so the source is recorded in the
# data itself, not only in this module's docstring.
EMPSZES_SOURCE_OFFICIAL = "official_metadata_crosswalk"
EMPSZES_SOURCE_OBSERVED = "observed_in_113310_state_slice"


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


def crosswalk_items_from_payload(payload: dict, variable: str) -> dict[str, str] | None:
    """The raw `{code: label}` `values.item` dict for `variable` within `payload`, checked at
    every shape this task's three candidate metadata routes can take: a flat single-variable
    document (`/variables/{variable}.json`, where `payload` itself is the candidate), a
    group-index document with no per-variable detail at all (`/groups.json`, which never
    matches), and a group document listing every variable in that group
    (`/groups/{group}.json`, where `variable`'s own entry sits under `payload["variables"]`).
    Returns `None` if no candidate carries one. Never raises on a malformed or unexpected shape
    -- absence is the answer, not a crash.

    Fix round 2: confirmed live that this is NOT always absent -- 2017's real
    `/variables/EMPSZES.json` carries 44 code/label pairs (`"001": "All establishments"`, ...);
    2018 onward do not. The prior round's claim that no candidate ever carries one was true
    for the single year checked by hand and false as a generalization across vintages; this
    function existing (and `probe_empszes_metadata_crosswalk` calling it every year rather than
    once) is what caught that."""
    candidates = [payload]
    variables = payload.get("variables")
    if isinstance(variables, dict):
        entry = variables.get(variable)
        if isinstance(entry, dict):
            candidates.append(entry)
    for cand in candidates:
        values = cand.get("values")
        if isinstance(values, dict):
            items = values.get("item")
            if isinstance(items, dict):
                return items
    return None


def crosswalk_present_in_payload(payload: dict, variable: str) -> bool:
    """True if `payload` carries an enumerated `values.item` code list for `variable` --
    `crosswalk_items_from_payload(payload, variable) is not None`, as a boolean convenience for
    the probe record; see that function's docstring for the shapes checked."""
    return crosswalk_items_from_payload(payload, variable) is not None


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


def fetch_json_or_none(
    client: httpx.Client, source: str, url: str, rel_path: str, extracts: list
) -> tuple[int, dict | None]:
    """GET `url`, record the extract on success, and parse the body as JSON -- returning
    `(status, None)` on an `httpx.HTTPStatusError` instead of raising.

    Fix round 3, Minor 2: `probe_empszes_metadata_crosswalk`'s `groups.json`/group-document
    fetches and the inline `EMPSZES.json` fetch in `main()` used to call `c.request` and
    `.json()` directly, unguarded -- the same shape of request that crashed the live run in
    fix round 1 (2018's comma-separated `group` field producing a 404 on the literal comma).
    Splitting the field fixed that one trigger; it did not fix the pattern. Any of these
    keyless metadata routes returning a 404 or 5xx crashes mid-run, after some of this run's
    extracts have already been appended to the list and before `write_summary` is ever called
    -- exactly the unregistered-files problem Minor 1 and fix round 2's Finding 2 are about,
    from a third angle. This function is what the two request sites route through now, so a
    metadata-route hiccup becomes a documented gap in the probe record instead of a crash."""
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code, None
    extracts.append(c.record_extract(source, url, rel_path, resp.content))
    return resp.status_code, resp.json()


def probe_empszes_metadata_crosswalk(
    client: httpx.Client, year: int, empszes_doc: dict, empszes_status: int, extracts: list
) -> tuple[list[dict], dict[str, str] | None]:
    """Probe every keyless metadata route that could plausibly carry an EMPSZES values
    crosswalk for this vintage, and record what each actually returned -- so whether "CBP's
    metadata publishes an EMPSZES value list" is measured every year this run, not assumed
    uniform from a single endpoint checked once during development (module docstring point 2;
    fix round 2 -- 2017 genuinely carries one, 2018 onward do not). `empszes_doc` is
    `/variables/EMPSZES.json`'s already-fetched, already-recorded payload; its own `group`
    field names the candidate group document.

    Returns `(probe_records, official_crosswalk)`. `official_crosswalk` is the raw
    `{code: label}` dict from whichever candidate carried one -- the flat variable document is
    checked first, matching what has actually been observed (2017 carries it there and nowhere
    else checked ever has) -- or `None` if no candidate did this year."""
    ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
    ez_items = crosswalk_items_from_payload(empszes_doc, "EMPSZES")
    probe = [{
        "url": ez_url, "status": empszes_status,
        "carries_values_crosswalk": ez_items is not None,
    }]
    official = ez_items

    groups_url = f"{BASE.format(year=year)}/groups.json"
    groups_status, groups_payload = fetch_json_or_none(
        client, SOURCE, groups_url, f"{year}/groups.json", extracts)
    groups_items = (
        crosswalk_items_from_payload(groups_payload, "EMPSZES")
        if groups_payload is not None else None
    )
    probe.append({
        "url": groups_url, "status": groups_status,
        # None (not False) when the fetch itself failed -- "not measured" must not read as
        # "measured absent" here any more than it does for empszes_by_year itself.
        "carries_values_crosswalk": None if groups_payload is None else groups_items is not None,
    })
    official = official or groups_items

    # `group` can name more than one group, comma-separated -- confirmed live for 2018
    # ("CB1800ZBP,CB1800CBP": EMPSZES is shared between the ZIP Code Business Patterns and
    # County Business Patterns groups that year). Probe every named group's own document, not
    # just the first -- treating the field as a single name 404s on the literal comma.
    for group in group_names_from_field(empszes_doc.get("group")):
        group_url = f"{BASE.format(year=year)}/groups/{group}.json"
        group_status, group_payload = fetch_json_or_none(
            client, SOURCE, group_url, f"{year}/groups_{group}.json", extracts)
        group_items = (
            crosswalk_items_from_payload(group_payload, "EMPSZES")
            if group_payload is not None else None
        )
        probe.append({
            "url": group_url, "status": group_status,
            "carries_values_crosswalk": None if group_payload is None else group_items is not None,
        })
        official = official or group_items
    return probe, official


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
        # Clear this year's ENTIRE directory before this run says anything about it, whether
        # the year turns out available this run or not (fix round 3, Minor 1). Fix round 2
        # only cleared the one canonical filename, and only inside the status==200 branch --
        # so a year available in a past run (full extract set + canonical file on disk) that
        # regresses to non-200 THIS run (a real 404, or probe()'s (0,0) transport sentinel)
        # skipped that unlink entirely, leaving its whole directory on disk unregistered in
        # this run's summary.json -- the same orphan problem Minor 5/Finding 2 fixed, just
        # triggered by a probe failure instead of a pull failure. Wiping unconditionally, every
        # year, before the probe, means this run's disk state can never be a mix of this run's
        # writes and some earlier run's leftovers: whatever survives to write_summary is
        # exactly what this run itself fetched. A transient probe-failure (0) year loses its
        # previously-fetched files too -- the accepted cost of a simple, single invariant
        # rather than a partial-merge-across-runs model this codebase has nowhere else; the
        # existing guidance to re-run this task on a 0 status still applies and refetches it.
        year_dir = c.AUDIT_ROOT / SOURCE / f"{year}"
        if year_dir.exists():
            shutil.rmtree(year_dir)

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

        official_crosswalk: dict[str, str] | None = None
        if has_empszes:
            ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
            ez_status, ez_payload = fetch_json_or_none(
                client, SOURCE, ez_url, f"{year}/empszes.json", extracts)
            if ez_payload is not None:
                crosswalk_records, official_crosswalk = probe_empszes_metadata_crosswalk(
                    client, year, ez_payload, ez_status, extracts)
                crosswalk_probe[str(year)] = crosswalk_records
            else:
                crosswalk_probe[str(year)] = None
                notes.append(
                    f"{year}: EMPSZES variable document fetch failed (HTTP {ez_status}) -- "
                    "metadata-crosswalk probe could not run"
                )
        else:
            crosswalk_probe[str(year)] = None
            notes.append(
                f"{year}: EMPSZES is not a variable for this vintage; no metadata-crosswalk "
                "probe was run"
            )

        if official_crosswalk:
            # The official enumeration exists in metadata for this vintage (confirmed live for
            # 2017 -- 44 codes) -- use it, and record that it came from metadata rather than
            # the keyed pull's rows. This also means empszes_by_year can be populated for a
            # year even when the keyed pull itself fails -- the crosswalk probe is entirely
            # keyless. Which years a run's keyed pull actually failed for is read off
            # working_query_by_year, never assumed here -- an auth rejection, a geography
            # problem and a query problem are all live causes, and a run can meet a mix.
            empszes[str(year)] = {
                "source": EMPSZES_SOURCE_OFFICIAL,
                "pairs": [
                    {"code": code, "label": label}
                    for code, label in sorted(official_crosswalk.items())
                ],
            }
            notes.append(
                f"{year}: EMPSZES official crosswalk found in metadata "
                f"({len(official_crosswalk)} codes) -- see "
                "empszes_metadata_crosswalk_probe_by_year for which route carried it"
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
            if not official_crosswalk:
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
            if not official_crosswalk:
                # Fallback only -- the official crosswalk (set above, if the probe found one)
                # always wins. This branch only ever populates empszes_by_year for a vintage
                # where metadata genuinely carries no enumeration (2018 onward, confirmed).
                pairs = empszes_pairs_from_rows(header, body)
                empszes[str(year)] = None if pairs is None else {
                    "source": EMPSZES_SOURCE_OBSERVED,
                    "note": (
                        "NOT the official CBP metadata enumeration -- this vintage's metadata "
                        "carries no EMPSZES values crosswalk (see "
                        "empszes_metadata_crosswalk_probe_by_year). A size class with zero "
                        "logging establishments in every state this year is silently absent "
                        "from `pairs`."
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
            if not official_crosswalk:
                empszes[str(year)] = None
            notes.append(
                f"{year}: keyed 113310 pull failed for all {len(attempts)} attempts -- cause: "
                f"{cause} (attempt statuses: {attempt_statuses})"
            )
            if cause == "auth_error":
                distinct = sorted(set(attempt_statuses))
                # empszes_by_year is the one field the keyed-pull failure does NOT necessarily
                # null out -- a year with an official metadata crosswalk (2017) keeps it,
                # because that crosswalk comes from a keyless route this failure never touched.
                # Naming it here unconditionally would repeat exactly the "persisted prose
                # contradicts the artifact" bug fix round 1 already found once in this note.
                empszes_clause = (
                    "empszes_by_year already carries the official metadata crosswalk found "
                    "above, unaffected by this" if official_crosswalk else
                    "empszes_by_year is null for this year too, not measured as zero or empty"
                )
                notes.append(
                    f"{year}: every attempt's response matched Census's key-rejection page "
                    f"({distinct}); rows_113310_by_year and flag_values_by_year are null for "
                    f"this year, not measured as zero or empty; {empszes_clause}; "
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
    # Derived from empszes, not typed -- access.status = "not_obtainable" would otherwise read
    # as "nothing usable came out of this run" when a reader only checks this one field, which
    # is false whenever a keyless official metadata crosswalk was found (2017, this run) even
    # though the keyed pull itself failed everywhere.
    official_crosswalk_years = sorted(
        int(y) for y, v in empszes.items()
        if isinstance(v, dict) and v.get("source") == EMPSZES_SOURCE_OFFICIAL
    )
    access_reason = (
        None if access_status == "verified" else
        (
            "CBP metadata routes (dataset document, variables, EMPSZES/LFO variable docs, "
            "groups, geography) returned real JSON for every year in years_available, but "
            "the keyed 113310 data pull did not succeed for any window year this run -- "
            f"causes recorded in working_query_by_year: {failure_causes}; see findings.notes "
            "per year for detail. empszes_by_year is nonetheless populated from a keyless "
            f"official metadata crosswalk (unaffected by the keyed-pull failure) for: "
            f"{official_crosswalk_years or 'no years this run'}"
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
