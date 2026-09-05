"""Fetch writes immutable bytes, one snapshot row each, and never a credential."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import polars as pl
import pytest

from logging_employment.config import load_config
from logging_employment.contracts import SOURCE_SNAPSHOT_SCHEMA, validate_frame
from logging_employment.fetching import (
    fetch_source,
    merge_source_manifest,
    write_source_manifest,
)

REPO = Path(__file__).resolve().parents[2]

ROW = {
    "snapshot_id": "abc",
    "source_id": "qcew",
    "request_url_or_file": "https://x/y.csv",
    "request_parameters_json": "{}",
    "retrieved_at_utc": "2026-09-05T00:00:00+00:00",
    "source_publication_date": "",
    "reference_start": "2017-01",
    "reference_end": "2017-03",
    "release_status": "final",
    "naics_vintage": "NAICS 2017",
    "schema_fingerprint": "f" * 64,
    "content_sha256": "a" * 64,
    "byte_count": 10,
    "http_status": 200,
    "parser_version": "qcew_monthly/1",
    "raw_path": "data/raw/x",
}


def _cfg():
    return load_config(REPO / "config.yaml")


def test_manifest_matches_the_snapshot_schema(tmp_path: Path) -> None:
    path = tmp_path / "source_manifest.parquet"
    digest = write_source_manifest([ROW], path)
    assert len(digest) == 64
    validate_frame(pl.read_parquet(path), SOURCE_SNAPSHOT_SCHEMA, "source_snapshot")


def test_manifest_writing_is_deterministic(tmp_path: Path) -> None:
    rows = [{k: ("x" if v == pl.String else 1) for k, v in SOURCE_SNAPSHOT_SCHEMA.items()}]
    a = write_source_manifest(rows, tmp_path / "a.parquet")
    b = write_source_manifest(rows, tmp_path / "b.parquet")
    assert a == b


def test_manifest_row_order_does_not_depend_on_fetch_order(tmp_path: Path) -> None:
    second = {**ROW, "snapshot_id": "zzz", "source_id": "cbp"}
    a = write_source_manifest([ROW, second], tmp_path / "a.parquet")
    b = write_source_manifest([second, ROW], tmp_path / "b.parquet")
    assert a == b


def test_fetch_refuses_an_unknown_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="susb"):
        fetch_source("susb", _cfg(), env_path=None)


def _serve(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> None:
    monkeypatch.setattr(
        httpx.Client,
        "get",
        lambda self, url, params=None: httpx.Response(
            200, content=payload, request=httpx.Request("GET", url)
        ),
    )
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "who@example.invalid")


def test_a_second_fetch_of_identical_bytes_stores_nothing_new(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve(monkeypatch, (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes())
    kwargs = {
        "env_path": None,
        "raw_root": tmp_path,
        "output_root": tmp_path,
        "years": [2017],
        "quarters": [1],
    }
    first = fetch_source("qcew", _cfg(), **kwargs)
    second = fetch_source("qcew", _cfg(), **kwargs)
    assert first[0]["content_sha256"] == second[0]["content_sha256"]
    assert len(list(tmp_path.rglob("*.csv"))) == 1


def test_fetching_writes_nothing_outside_the_roots_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The manifest path is derived from `cfg.storage.output_uri`, which is the repo's `runs/`.
    # A test that did not override it would write into the working tree.
    _serve(monkeypatch, (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes())
    before = {p for p in REPO.glob("runs/*")}
    fetch_source(
        "qcew",
        _cfg(),
        env_path=None,
        raw_root=tmp_path,
        output_root=tmp_path,
        years=[2017],
        quarters=[1],
    )
    assert (tmp_path / "source_manifest.parquet").exists()
    assert {p for p in REPO.glob("runs/*")} == before


def test_every_snapshot_row_matches_the_declared_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve(monkeypatch, (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes())
    rows = fetch_source(
        "qcew",
        _cfg(),
        env_path=None,
        raw_root=tmp_path,
        output_root=tmp_path,
        years=[2017],
        quarters=[1],
    )
    validate_frame(
        pl.read_parquet(tmp_path / "source_manifest.parquet"), SOURCE_SNAPSHOT_SCHEMA, "s"
    )
    assert rows and all(set(r) == set(SOURCE_SNAPSHOT_SCHEMA) for r in rows)


def test_a_cbp_api_key_never_reaches_a_snapshot_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The CBP request must carry `key`; the recorded row must not. `snapshot_row` scans for the
    # value and raises, so this passes only because the parameters are stripped before recording.
    from logging_employment.fetching import _without_credentials
    from logging_employment.ingest.base import FetchedBytes

    fetched = FetchedBytes(
        url="https://api.census.gov/data/2023/cbp",
        params={"get": "NAME", "key": "SECRET-VALUE", "for": "state:*"},
        content=b"[]",
        http_status=200,
        retrieved_at_utc="2026-09-05T00:00:00+00:00",
    )
    clean = _without_credentials(fetched)
    assert "key" not in clean.params
    assert clean.params == {"get": "NAME", "for": "state:*"}
    # The bytes, status and timestamp are untouched, so the content hash is unaffected.
    assert clean.content == fetched.content
    assert clean.http_status == fetched.http_status
    assert clean.retrieved_at_utc == fetched.retrieved_at_utc


def _serve_cbp(monkeypatch: pytest.MonkeyPatch, key: str) -> None:
    """Serve CBP's variables metadata and data response, and put a key in the environment."""
    variables = (REPO / "tests" / "fixtures" / "cbp" / "variables_2023.json").read_bytes()
    data = (REPO / "tests" / "fixtures" / "cbp" / "data_113310_2023.json").read_bytes()

    def get(self, url, params=None):
        body = variables if url.endswith("variables.json") else data
        return httpx.Response(200, content=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", get)
    monkeypatch.setenv("BLS_CONTACT_EMAIL", "who@example.invalid")
    monkeypatch.setenv("CENSUS_API_KEY", key)


def test_the_cbp_branch_records_no_key_even_though_the_request_carries_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The end-to-end version of the `_without_credentials` unit test above. `snapshot_row` scans
    # the recorded URL and parameters for every known secret and raises, so a branch that forgot
    # to strip the key would fail here -- and only here, since the helper being correct says
    # nothing about the caller using it.
    _serve_cbp(monkeypatch, "SECRET-CENSUS-KEY")
    rows = fetch_source(
        "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023]
    )
    assert rows
    blob = json.dumps(rows)
    assert "SECRET-CENSUS-KEY" not in blob
    assert "key" not in json.loads(rows[0]["request_parameters_json"])


def test_the_cbp_branch_stores_metadata_where_the_offline_build_looks_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The seam between fetch and build: Task 14's rebuild reads the predicate from this file.
    from logging_employment.build import predicate_from_stored_metadata

    _serve_cbp(monkeypatch, "SECRET-CENSUS-KEY")
    fetch_source(
        "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023]
    )
    assert predicate_from_stored_metadata(tmp_path / "cbp", 2023) == "NAICS2017"


def test_a_stored_raw_file_never_contains_the_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _serve_cbp(monkeypatch, "SECRET-CENSUS-KEY")
    fetch_source(
        "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023]
    )
    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert b"SECRET-CENSUS-KEY" not in path.read_bytes(), path


def test_fetching_a_second_source_does_not_erase_the_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # `fetch` runs once per source against one manifest path. Overwriting would leave the
    # provenance artifact describing whichever source ran last.
    _serve(monkeypatch, (REPO / "tests" / "fixtures" / "qcew" / "slice_2017q1.csv").read_bytes())
    fetch_source(
        "qcew",
        _cfg(),
        env_path=None,
        raw_root=tmp_path,
        output_root=tmp_path,
        years=[2017],
        quarters=[1],
    )
    _serve_cbp(monkeypatch, "SECRET-CENSUS-KEY")
    fetch_source(
        "cbp", _cfg(), env_path=None, raw_root=tmp_path, output_root=tmp_path, years=[2023]
    )
    manifest = pl.read_parquet(tmp_path / "source_manifest.parquet")
    assert sorted(manifest["source_id"].unique().to_list()) == ["cbp", "qcew"]


def test_refetching_one_source_refreshes_rather_than_duplicates_it(tmp_path: Path) -> None:
    path = tmp_path / "source_manifest.parquet"
    write_source_manifest([ROW], path)
    merge_source_manifest([{**ROW, "byte_count": 99}], path, "qcew")
    manifest = pl.read_parquet(path)
    assert manifest.height == 1
    assert manifest["byte_count"].to_list() == [99]


def test_merging_leaves_other_sources_untouched(tmp_path: Path) -> None:
    path = tmp_path / "source_manifest.parquet"
    other = {**ROW, "source_id": "cbp", "snapshot_id": "zzz"}
    write_source_manifest([ROW, other], path)
    merge_source_manifest([{**ROW, "byte_count": 99}], path, "qcew")
    manifest = pl.read_parquet(path).sort("source_id")
    assert manifest["source_id"].to_list() == ["cbp", "qcew"]
    assert manifest.filter(pl.col("source_id") == "cbp")["byte_count"].to_list() == [10]
