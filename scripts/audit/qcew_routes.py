# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Measure which reference years the QCEW Open Data slice route serves, and prove the bulk
route covers the rest of the D1 window (D5)."""

from __future__ import annotations

import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import _common as c
import httpx
import polars as pl

SOURCE = "qcew_routes"
SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
BULK_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip"


def read_csv_bytes(content: bytes) -> pl.DataFrame:
    """All columns as Utf8: area_fips has leading zeros and alpha CSA codes like 'C1010'."""
    return pl.read_csv(io.BytesIO(content), infer_schema_length=0)


def column_parity(
    slice_headers: dict[str, list[str]],
    bulk_headers: dict[int, list[str]],
    *,
    reference_bulk_year: int,
) -> dict:
    """The `column_parity` finding, over every header this run actually read.

    Both sides must reduce to one header to be compared at all, and neither reduction is safe
    on its own. `to_fetch` carries more than one year on the normal D5 path (bulk_years_required
    non-empty), not just the single-year fallback this run took, and the slice side spans every
    served window quarter. So each side's agreement is checked before it is reduced, and a
    disagreement is recorded as the bulk- or slice-side schema-drift finding it is rather than
    picked around.

    `identical` is therefore conjoined with BOTH sides' agreement, not left as the bare
    `slice_header == bulk_header`. `identical` claims the slice header and the bulk header are
    the same columns; if either side is not uniform there is no "the" header on that side and
    the claim is not well-formed, so `False` is the honest answer in both directions. Reduced
    to one year and one quarter, the bare comparison could read true on a run where
    `bulk_header_disagreement` or `slice_header_disagreement` beside it was non-empty.

    Conjoined rather than renamed to `identical_to_first_bulk_year`, because this key is read by
    the exit gate and rendered into the shipped finding document: a rename would force the
    artifact to be regenerated in order to say exactly what it already says. The conjunction
    does not -- the shipped run has both disagreement dicts empty, so its `identical` is
    unchanged (verified by recomputing this function over that run's own extracts).

    `slice_only` and `bulk_only` are left as set differences against the two reference headers.
    They describe which columns one route carries and the other does not, which is what Stage 1
    reads them for, with both disagreement dicts beside them.
    """
    distinct_bulk_headers = {tuple(h) for h in bulk_headers.values()}
    bulk_header = bulk_headers[reference_bulk_year]
    distinct_slice_headers = {tuple(h) for h in slice_headers.values()}
    # The first key is the earliest window year/quarter the slice route actually served
    # (extracts accumulate in ascending probe order) — the most defensible single reference,
    # backed by the consistency check above rather than by an assumption.
    slice_header = next(iter(slice_headers.values()), [])
    return {
        "slice_only": sorted(set(slice_header) - set(bulk_header)),
        "bulk_only": sorted(set(bulk_header) - set(slice_header)),
        "identical": (
            slice_header == bulk_header
            and len(distinct_bulk_headers) <= 1
            and len(distinct_slice_headers) <= 1
        ),
        "bulk_header_disagreement": (
            {}
            if len(distinct_bulk_headers) <= 1
            else {str(year): header for year, header in sorted(bulk_headers.items())}
        ),
        "slice_header_disagreement": (
            {}
            if len(distinct_slice_headers) <= 1
            else {Path(p).name: header for p, header in sorted(slice_headers.items())}
        ),
    }


def main() -> None:
    client = c.build_client()
    probe_rows: list[dict] = []
    extracts: list[c.ExtractRecord] = []
    served: set[int] = set()

    # Probe wider than the window: below it to find the true floor, above it to find the
    # publication frontier. Never assume the frontier is "now".
    probe_years = range(2010, datetime.now(UTC).year + 1)
    for year in probe_years:
        for qtr in (1, 2, 3, 4):
            url = SLICE_URL.format(year=year, qtr=qtr, industry=c.INDUSTRY_CODE)
            # 68 requests: one transient failure must not abandon the probes already done.
            # c.request retries 5xx and transport errors; a 4xx is recorded as the finding it is.
            content, ctype = b"", ""
            try:
                resp = c.request(client, url)
                status, content = resp.status_code, resp.content
                ctype = resp.headers.get("content-type", "")
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
            except httpx.TransportError:
                status = 0  # transport failure after retries — re-run this task to resolve
            rows = 0
            if status == 200 and "csv" in ctype:
                try:
                    rows = read_csv_bytes(content).height
                except (pl.exceptions.PolarsError, UnicodeDecodeError, ValueError):
                    # an HTML error page can be served with status 200 and a csv-ish
                    # content-type; keep the body so a parser bug and a real route
                    # boundary are never indistinguishable from an empty disk.
                    rows = 0
            probe_rows.append(
                {
                    "year": year,
                    "qtr": qtr,
                    "http_status": status,
                    "bytes": len(content),
                    "content_type": ctype,
                    "row_count": rows,
                }
            )
            if rows > 0:
                served.add(year)
            if year in c.WINDOW_YEARS and status == 200 and content:
                if rows > 0:
                    extracts.append(
                        c.record_extract(
                            SOURCE,
                            url,
                            f"slices/{year}q{qtr}.csv",
                            content,
                            http_status=status,
                        )
                    )
                else:
                    # not a .csv path: Task 3/4 glob extracts by `.endswith(".csv")` and
                    # would try to parse this body as data.
                    extracts.append(
                        c.record_extract(
                            SOURCE,
                            url,
                            f"slices/unparseable_{year}q{qtr}.body",
                            content,
                            http_status=status,
                        )
                    )

    earliest = min(served) if served else None
    latest = max(served) if served else None
    required = [y for y in c.WINDOW_YEARS if y not in served]
    to_fetch = required or [c.WINDOW_YEARS[0]]

    members: dict[str, str] = {}
    bulk_headers: dict[int, list[str]] = {}
    for year in to_fetch:
        url = BULK_URL.format(year=year)
        rec = c.download_extract(client, SOURCE, url, f"bulk/{year}_qtrly_by_industry.zip")
        extracts.append(rec)
        with zipfile.ZipFile(rec.path) as zf:
            matches = [n for n in zf.namelist() if c.INDUSTRY_CODE in n]
            if not matches:
                raise RuntimeError(f"no 113310 member in {rec.path}; inspect namelist()")
            if len(matches) > 1:
                raise RuntimeError(f"ambiguous 113310 member in {rec.path}: {matches}")
            members[str(year)] = matches[0]
            bulk_headers[year] = read_csv_bytes(zf.read(matches[0])).columns

    slice_paths = [e.path for e in extracts if e.path.endswith(".csv")]
    # Check every served window slice's header, not just the first — a mid-window BLS
    # schema change would otherwise go undetected. These files are already on disk: no
    # network cost.
    slice_headers = {p: read_csv_bytes(Path(p).read_bytes()).columns for p in slice_paths}

    parity = column_parity(slice_headers, bulk_headers, reference_bulk_year=to_fetch[0])

    # `covered` (Task 1 schema) is the part of D1's window this source covers, not the full
    # probed span — clamp to the window; `served` can include years probed outside it.
    covered_years = sorted(served & set(c.WINDOW_YEARS))
    covered = f"{min(covered_years)}-{max(covered_years)}" if covered_years else ""
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(earliest) if earliest else "",
            "published_end": str(latest) if latest else "",
            "window_start": c.WINDOW_START,
            "window_end": c.WINDOW_END,
            "covered": covered,
            "uncovered": ",".join(str(y) for y in required),
        },
        access={
            "route": f"slice: {SLICE_URL} | bulk: {BULK_URL}",
            "status": "verified" if served else "not_obtainable",
            "reason": None if served else "no reference year returned a parsable CSV",
        },
        extracts=extracts,
        findings={
            "slice_probe": probe_rows,
            "earliest_year_served": earliest,
            "latest_year_served": latest,
            "bulk_years_required": required,
            "bulk_years_fetched": to_fetch,
            "bulk_member_names": members,
            "column_parity": parity,
        },
    )
    print(f"slice years served: {earliest}-{latest}; bulk required: {required or 'none'}")


if __name__ == "__main__":
    main()
