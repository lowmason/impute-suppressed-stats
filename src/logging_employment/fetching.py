"""Acquisition: fetch each source's bytes into the immutable store and record provenance."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import polars as pl

from .config import SECRET_ENV_VARS, Config, credentials
from .contracts import (
    CBP_STATE_SIZE_SCHEMA,
    QCEW_MONTHLY_SCHEMA,
    QCEW_NATIONAL_SIZE_SCHEMA,
    SOURCE_SNAPSHOT_SCHEMA,
    schema_fingerprint,
)
from .errors import SourceFetchError
from .harmonize.naics import vintage_for_year
from .ingest import cbp, qcew, qcew_size
from .ingest.base import FetchedBytes, HttpFetcher
from .store import RawStore, snapshot_row

KNOWN_SOURCES = ("qcew", "qcew_size", "cbp")

# (source_id, reference year) pairs whose publisher genuinely serves nothing, each carrying the
# measurement that established it. A pair listed here is allowed to answer non-200 or empty; every
# other key that does halts the run (R-S5P-4).
#
# A module constant and NOT a `Config` field: `config.resolved_dict` is `model_dump(mode="json")`
# and feeds `runs.run_id`, so a new pydantic field -- default or not -- re-ids every existing
# `runs/<id>/` directory, including the Stage 4 comparand `specs/stage5-preconditions.md` §4
# protects. It is also not a per-run operator choice: it is the same class of audited fact as
# `harmonize/disclosure.CBP_REGIME_BY_YEAR`, which is a module constant keyed by reference year
# for the same reason. Deliberately NOT derived from that table, even though 2024 is missing from
# both: "Census publishes no dataset" and "no fetched documentation states a disclosure regime"
# are two findings that happen to coincide on one year, and a year published with an undocumented
# regime must 200 here and halt in `harmonize`, not be excused from being fetched at all.
DECLARED_ABSENCES: dict[tuple[str, int], str] = {
    ("cbp", 2024): (
        "Census serves no 2024 CBP dataset: Stage 0's dataset probe returned a real HTTP 404 "
        "and 2024 is absent from cbp_metadata.years_available (SRC-CBP-003, SRC-CBP-004)"
    ),
}


def _usable(fetched: FetchedBytes, *, source_id: str, year: int, reference: str) -> bool:
    """Whether `fetched` carries bytes worth storing; halt when a failure is undeclared.

    Returns False only for a DECLARED absence, so the one `continue` this leaves in the fetch loop
    is a documented hole in the published record rather than whatever the network did. The
    predicate is two-part for the reason `qcew.probe_slice_boundary` gives -- a source can answer
    200 with an empty body -- and it is applied to all four request sites, including the two that
    checked status alone before R-S5P-4.

    Classifying here rather than in `HttpFetcher` keeps that layer's contract: it returns a
    non-200 so the caller decides, because Stage 0 measured Census and USDA answering 200 with an
    error body and 404 with a meaningful one.
    """
    if fetched.http_status == 200 and fetched.content.strip():
        return True
    if (source_id, year) in DECLARED_ABSENCES:
        return False
    raise SourceFetchError(
        f"{source_id} {reference} returned HTTP {fetched.http_status} with "
        f"{len(fetched.content)} byte(s) from {fetched.url}; refusing to narrow the window "
        f"silently. Declare it in fetching.DECLARED_ABSENCES if the source publishes nothing "
        f"for {year} (R-S5P-4, §18.3)"
    )


def merge_source_manifest(rows: Sequence[dict[str, object]], path: Path, source_id: str) -> str:
    """Fold one source's snapshot rows into the run manifest, replacing that source's rows.

    `fetch` runs once per source, and all three invocations name the same artifact. Writing each
    one straight out would leave the manifest describing whichever source ran last, so a reader
    asking where `qcew_monthly.parquet` came from would find only CBP. Rows for the source being
    fetched are replaced rather than appended, so re-fetching one source refreshes its provenance
    without duplicating it or disturbing the others.
    """
    kept: list[dict[str, object]] = []
    if path.exists():
        existing = pl.read_parquet(path)
        kept = existing.filter(pl.col("source_id") != source_id).to_dicts()
    return write_source_manifest([*kept, *rows], path)


def write_source_manifest(rows: Sequence[dict[str, object]], path: Path) -> str:
    """Write `source_manifest.parquet` reproducibly and return its sha256 (REQ-028, §18.1).

    Sorted before writing, so a manifest does not depend on the order the fetch loop happened to
    visit its sources in -- the same run recorded twice is the same file.
    """
    frame = pl.DataFrame(list(rows), schema=SOURCE_SNAPSHOT_SCHEMA, orient="row").sort(
        ["source_id", "snapshot_id"]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.rechunk().write_parquet(path, compression="uncompressed", statistics=False)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _without_credentials(fetched: FetchedBytes) -> FetchedBytes:
    """The same response with credential-bearing request parameters removed.

    Only the recorded parameters change; the bytes, status and timestamp are untouched, so the
    content hash is unaffected and the stored object is still addressed by what came back.
    """
    return replace(fetched, params={k: v for k, v in fetched.params.items() if k != "key"})


def fetch_source(
    source: str,
    cfg: Config,
    *,
    env_path: Path | None = None,
    raw_root: Path | None = None,
    output_root: Path | None = None,
    years: Sequence[int] | None = None,
    quarters: Sequence[int] | None = None,
) -> list[dict[str, object]]:
    """Fetch one source over the D1 window and return its `source_snapshot` rows.

    Bytes land in the content-addressed store, so a second call over unchanged data re-uses the
    existing object rather than writing a second copy (§6.2). Secret values are passed to requests
    and never to `snapshot_row`, which scans for them and refuses to emit a row that carries one.

    `raw_root` and `output_root` both default to the configured locations. They are separate
    parameters because a caller that redirects the store must redirect the manifest too: leaving
    the manifest on `cfg.storage.output_uri` would write into the repository from a test that
    thought it had been given a temporary directory.
    """
    if source not in KNOWN_SOURCES:
        raise ValueError(f"unknown source {source!r}; known: {KNOWN_SOURCES}")
    creds = credentials(env_path)
    contact = creds.get("BLS_CONTACT_EMAIL") or os.environ.get("BLS_CONTACT_EMAIL", "")
    secrets = [creds.get(name) for name in SECRET_ENV_VARS]
    store = RawStore(Path(raw_root or cfg.storage.raw_uri))
    fetcher = HttpFetcher(contact_email=contact)
    window_years = list(
        years or range(int(cfg.project.start_month[:4]), int(cfg.project.end_month[:4]) + 1)
    )
    rows: list[dict[str, object]] = []
    try:
        if source == "qcew":
            boundary = qcew.probe_slice_boundary(
                fetcher,
                cfg.project.industry_code_used,
                range(min(window_years) - 5, min(window_years) + 1),
            )
            for year in window_years:
                for quarter in list(quarters or (1, 2, 3, 4)):
                    route = qcew.route_for_year(year, boundary)
                    if route == "slice":
                        fetched = qcew.fetch_slice(
                            fetcher, year, quarter, cfg.project.industry_code_used
                        )
                        name = f"{year}q{quarter}.csv"
                    else:
                        fetched = fetcher.get(qcew.bulk_url(year))
                        name = f"{year}_qtrly_by_industry.zip"
                    if not _usable(
                        fetched, source_id="qcew", year=year, reference=f"{year}q{quarter}"
                    ):
                        continue
                    stored = store.put("qcew", fetched, name)
                    rows.append(
                        snapshot_row(
                            source_id="qcew",
                            fetched=fetched,
                            stored=stored,
                            reference_start=f"{year}-{(quarter - 1) * 3 + 1:02d}",
                            reference_end=f"{year}-{quarter * 3:02d}",
                            release_status=cfg.sources.qcew.release_status,
                            naics_vintage=vintage_for_year(year),
                            schema_fingerprint=schema_fingerprint(QCEW_MONTHLY_SCHEMA),
                            parser_version=qcew.PARSER_VERSION,
                            source_publication_date="",
                            secrets=secrets,
                        )
                    )
        elif source == "qcew_size":
            for year in window_years:
                fetched = fetcher.get(qcew_size.BY_SIZE_URL.format(year=year))
                if not _usable(
                    fetched, source_id="qcew_size", year=year, reference=f"{year}q1 by-size"
                ):
                    continue
                stored = store.put("qcew_size", fetched, f"{year}_q1_by_size.zip")
                rows.append(
                    snapshot_row(
                        source_id="qcew_size",
                        fetched=fetched,
                        stored=stored,
                        reference_start=f"{year}-01",
                        reference_end=f"{year}-03",
                        release_status="final",
                        naics_vintage=vintage_for_year(year),
                        schema_fingerprint=schema_fingerprint(QCEW_NATIONAL_SIZE_SCHEMA),
                        parser_version=qcew_size.PARSER_VERSION,
                        source_publication_date="",
                        secrets=secrets,
                    )
                )
        else:
            key = creds.get(cfg.sources.cbp.api_key_env, "")
            for year in window_years:
                variables = fetcher.get(cbp.VARIABLES_URL.format(year=year))
                if not _usable(
                    variables, source_id="cbp", year=year, reference=f"{year} variables metadata"
                ):
                    continue
                # Stored beside the data response, under the name `build` looks for, so the
                # offline rebuild discovers the predicate exactly as this fetch did.
                store.put("cbp", variables, cbp.metadata_filename(year))
                predicate = cbp.discover_naics_predicate(json.loads(variables.content))
                query = cbp.build_query(year, predicate, cfg.project.industry_code_used)
                fetched = fetcher.get(cbp.CBP_URL.format(year=year), params={**query, "key": key})
                if not _usable(fetched, source_id="cbp", year=year, reference=f"{year} data"):
                    continue
                stored = store.put("cbp", fetched, f"{year}.json")
                rows.append(
                    snapshot_row(
                        source_id="cbp",
                        fetched=_without_credentials(fetched),
                        stored=stored,
                        reference_start=f"{year}-03",
                        reference_end=f"{year}-03",
                        release_status="final",
                        naics_vintage=vintage_for_year(year),
                        schema_fingerprint=schema_fingerprint(CBP_STATE_SIZE_SCHEMA),
                        parser_version=cbp.PARSER_VERSION,
                        source_publication_date="",
                        secrets=secrets,
                    )
                )
    finally:
        fetcher.close()
    merge_source_manifest(
        rows, Path(output_root or cfg.storage.output_uri) / "source_manifest.parquet", source
    )
    return rows
