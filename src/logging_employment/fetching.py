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
from .harmonize.naics import vintage_for_year
from .ingest import cbp, qcew, qcew_size
from .ingest.base import FetchedBytes, HttpFetcher
from .store import RawStore, snapshot_row

KNOWN_SOURCES = ("qcew", "qcew_size", "cbp")


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
                    if fetched.http_status != 200 or not fetched.content.strip():
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
                if fetched.http_status != 200:
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
                if variables.http_status != 200:
                    continue
                # Stored beside the data response, under the name `build` looks for, so the
                # offline rebuild discovers the predicate exactly as this fetch did.
                store.put("cbp", variables, cbp.metadata_filename(year))
                predicate = cbp.discover_naics_predicate(json.loads(variables.content))
                query = cbp.build_query(year, predicate, cfg.project.industry_code_used)
                fetched = fetcher.get(cbp.CBP_URL.format(year=year), params={**query, "key": key})
                if fetched.http_status != 200:
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
    write_source_manifest(
        rows, Path(output_root or cfg.storage.output_uri) / "source_manifest.parquet"
    )
    return rows
