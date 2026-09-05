"""The raw store is content-addressed, immutable, and secret-free."""

from __future__ import annotations

from pathlib import Path

import pytest

from logging_employment.ingest.base import FetchedBytes
from logging_employment.store import RawStore, assert_no_secret


def _fetched(content: bytes) -> FetchedBytes:
    return FetchedBytes(
        url="https://example.invalid/x.csv",
        params={},
        content=content,
        http_status=200,
        retrieved_at_utc="2026-09-05T00:00:00+00:00",
    )


def test_identical_bytes_produce_one_retrieval_id(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    first = store.put("qcew", _fetched(b"a,b\n1,2\n"), "slice.csv")
    second = store.put("qcew", _fetched(b"a,b\n1,2\n"), "slice.csv")
    assert first.retrieval_id == second.retrieval_id
    assert first.was_already_present is False
    assert second.was_already_present is True


def test_different_bytes_produce_different_retrieval_ids(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    a = store.put("qcew", _fetched(b"one"), "slice.csv")
    b = store.put("qcew", _fetched(b"two"), "slice.csv")
    assert a.retrieval_id != b.retrieval_id


def test_a_stored_object_is_not_rewritten(tmp_path: Path) -> None:
    store = RawStore(tmp_path)
    stored = store.put("qcew", _fetched(b"original"), "slice.csv")
    mtime = stored.raw_path.stat().st_mtime_ns
    store.put("qcew", _fetched(b"original"), "slice.csv")
    assert stored.raw_path.stat().st_mtime_ns == mtime
    assert stored.raw_path.read_bytes() == b"original"


def test_assert_no_secret_raises_on_a_leaked_value() -> None:
    with pytest.raises(ValueError, match="secret"):
        assert_no_secret("url=...&key=abc123", ["abc123"])


def test_assert_no_secret_ignores_empty_secrets() -> None:
    assert_no_secret("anything at all", ["", None])  # type: ignore[list-item]
