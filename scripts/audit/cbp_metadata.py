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
   before ever attempting to parse the body.

2. **`/variables/EMPSZES.json` and `/variables/LFO.json` carry no code/label crosswalk for
   this dataset.** The plan's illustrative `value_list` helper reads `payload["values"]["item"]`
   -- a shape used by some other Census APIs, but the real 2021 CBP response (and the full
   `variables.json` bundle, and `groups/CB2100CBP.json`) has no `values` key at all; every
   candidate keyless endpoint checked returns the same variable-description shape (label,
   concept, predicateType, group, attributes), never an enumerated code list. That function
   would have silently returned `[]` for every year, every run, regardless of what CBP
   actually publishes -- the exact "filter that can never fire" defect class this plan's
   dispatches warn about. The only place the crosswalk is genuinely observable is in the data
   pull's own rows: `EMPSZES`/`EMPSZES_LABEL` are requested as unfiltered output columns in
   attempts 1-2 below, so a successful pull's distinct `(EMPSZES, EMPSZES_LABEL)` pairs *are*
   the code list (`empszes_pairs_from_rows`). `LFO` is only ever used as a filter (`="001"`) or
   omitted, never selected as an output column, so no attempt here can ever yield a full LFO
   crosswalk from its rows -- `lfo_by_year` records that limitation in `notes` rather than
   silently staying null with no explanation.

3. **A key genuinely present in this repo's `.env` does not authenticate.** Confirmed against
   both this dataset and, as a control ruling out a CBP-specific malformed query, against a
   wholly different dataset (ACS1) with the same key: both return HTTP 200 with an "Invalid
   Key" HTML page. Every keyed request in a run against this credential is therefore expected
   to fail; the script still performs every keyed request for real (it does not special-case
   "this key looks broken, skip the network calls") so a fixed credential needs no code change
   to start succeeding, and so `access.status`/`notes` report what THIS run actually measured.
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


def classify_data_body(content_type: str, body: bytes) -> tuple[str, list | None]:
    """Classify one response from the keyed CBP data-pull endpoint.

    Census answers a missing OR invalid key with HTTP 200 after following the redirect to an
    HTML error page -- status alone cannot distinguish that from a real answer (see module
    docstring, point 1). Content-type is what discriminates: the error pages serve
    `text/html`; a real answer serves `application/json`. Returns:
      ("ok", header_and_rows)  -- content-type carries "json" and the body parses as a
                                   non-empty list of lists (the tabular header-plus-rows shape
                                   this endpoint returns for a `get=`/`for=` query).
      ("auth_error", None)     -- content-type does not carry "json" (including no
                                   content-type at all). Missing-key and invalid-key pages are
                                   indistinguishable from the body alone without keeping a
                                   copy of Census's HTML, which this function does not need to
                                   do its one job: never mistake either for data.
      ("bad_shape", None)      -- content-type claims JSON but the body doesn't parse, or
                                   parses to something other than a non-empty list of lists
                                   (e.g. a dict, an empty list, a list of scalars).
    """
    if "json" not in content_type:
        return "auth_error", None
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
    came back as an auth-error page". Without one, an invalid or missing `CENSUS_API_KEY`
    reads as "the query is wrong": a credential problem misdiagnosed as a script bug.
    `attempt_statuses` are `classify_data_body` outcomes plus "http_error" for a raised
    `HTTPStatusError`, in attempt order; only reached when none of them was "ok"."""
    if not state_available:
        return "geography_unavailable"
    if attempt_statuses and all(status == "auth_error" for status in attempt_statuses):
        return "auth_error"
    return "query_bug"


def empszes_pairs_from_rows(header: list[str], body: list[list]) -> list[dict] | None:
    """Distinct `(EMPSZES, EMPSZES_LABEL)` pairs observed in a successful data-pull response,
    sorted by code. Returns `None` when the response didn't carry both columns (attempt 3
    drops EMPSZES entirely) -- that must read as "not observed", never as an empty list
    standing in for "this vintage has no size classes"."""
    if "EMPSZES" not in header or "EMPSZES_LABEL" not in header:
        return None
    i_code, i_label = header.index("EMPSZES"), header.index("EMPSZES_LABEL")
    pairs = {(row[i_code], row[i_label]) for row in body}
    return [{"code": code, "label": label} for code, label in sorted(pairs)]


def fetch_variable_doc(
    client: httpx.Client, year: int, variable: str, extracts: list
) -> dict | None:
    """Fetch and record `/variables/{variable}.json` verbatim (keyless; a real, useful extract
    -- label, concept, predicateType -- even though it carries no code/label crosswalk for
    this dataset, see module docstring point 2). Returns the parsed document, or `None` on a
    404 (the variable does not exist for this vintage -- used for `LFO`'s existence check)."""
    url = f"{BASE.format(year=year)}/variables/{variable}.json"
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError:
        return None
    extracts.append(c.record_extract(
        SOURCE, url, f"{year}/{variable.lower()}.json", resp.content))
    return resp.json()


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")

    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    years: list[int] = []
    predicates, empszes, lfo, geo_levels = {}, {}, {}, {}
    working, rows, flags = {}, {}, {}
    probe_status: dict[str, int] = {}
    notes: list[str] = []
    any_keyed_success = False

    for year in c.WINDOW_YEARS:
        status, _ = c.probe(client, f"{BASE.format(year=year)}.json")
        probe_status[str(year)] = status
        if status == 0:
            # probe() has no retry and returns (0, 0) on a TransportError; an http_status of
            # 0 is a transient failure, not a finding -- re-run this task rather than reading
            # the year as absent.
            notes.append(
                f"{year}: the keyless cbp.json probe returned no response at all (transport "
                "failure, not a 4xx) -- re-run this task to resolve whether the year is "
                "actually published; it is NOT counted as absent below."
            )
            continue
        if status != 200:
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
            fetch_variable_doc(client, year, "EMPSZES", extracts)
        if has_lfo:
            fetch_variable_doc(client, year, "LFO", extracts)
        # lfo_by_year is null either way: when LFO isn't a variable at all (per the brief), and
        # also when it is one, because no attempt below selects LFO/LFO_LABEL as output columns
        # (module docstring point 2) -- there is no code path that ever derives a real LFO
        # crosswalk in this script. Recorded unconditionally here (not only on the branch that
        # goes on to attempt a pull) so an ambiguous/absent NAICS predicate below still leaves a
        # note explaining lfo_by_year rather than silently skipping it for that year.
        lfo[str(year)] = None
        if has_lfo:
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
        last_content: bytes | None = None
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
            last_content = dresp.content
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
            empszes[str(year)] = empszes_pairs_from_rows(header, body)
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
                notes.append(
                    f"{year}: CENSUS_API_KEY did not authenticate (every attempt's response "
                    "carried a non-JSON content-type, consistent with Census's HTML "
                    "missing/invalid-key page); rows_113310_by_year, working_query_by_year, "
                    "flag_values_by_year and empszes_by_year are null for this year, not "
                    "measured as zero or empty -- re-run this task once the credential works."
                )

        # Retain the deciding attempt's bytes under the canonical filename the plan's Produces
        # block names, in addition to the per-attempt file above -- same bytes, no re-fetch.
        if last_content is not None:
            extracts.append(c.record_extract(
                SOURCE, BASE.format(year=year), f"{year}/data_113310.json", last_content))

    covered = f"{min(years)}-{max(years)}" if years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y not in years)
    # Both non-"verified" cases below are "not_obtainable", not "documented": nothing about the
    # keyed route was learned from documentation -- every keyed request was actually attempted
    # live, and the *data* it exists to fetch could not be obtained this run, whether because no
    # dataset document ever came back or because the credential never authenticated. "verified"
    # is reserved for what it says: at least one year's keyed pull actually returned real rows.
    access_status = "verified" if any_keyed_success else "not_obtainable"
    access_reason = (
        None if access_status == "verified" else
        (
            "CBP metadata routes (dataset document, variables, EMPSZES/LFO variable docs, "
            "geography) returned real JSON for every year in years_available, but the keyed "
            "113310 data pull did not succeed for any window year this run -- CENSUS_API_KEY "
            "did not authenticate (see findings.notes per year); working_query_by_year, "
            "rows_113310_by_year, flag_values_by_year and empszes_by_year are null "
            "everywhere as a result"
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
