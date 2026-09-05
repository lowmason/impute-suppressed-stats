"""The immutable, content-addressed raw store and the `source_snapshot` row it produces."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .ingest.base import FetchedBytes


@dataclass(frozen=True)
class StoredObject:
    """One immutable object in the raw store."""

    retrieval_id: str
    content_sha256: str
    byte_count: int
    raw_path: Path
    was_already_present: bool


def assert_no_secret(payload: str, secrets: Sequence[str | None]) -> None:
    """Raise ValueError if any non-empty secret value appears in the payload (§7.2, D3)."""
    for secret in secrets:
        if secret and secret in payload:
            raise ValueError("a secret value reached a manifest payload; refusing to write it")


class RawStore:
    """`data/raw/<source_id>/<retrieval_id>/<filename>`, written once and never rewritten.

    `retrieval_id` is the content sha256, so the same bytes always land in the same place and a
    rerun against an unchanged source is a no-op rather than a second copy (§6.2).
    """

    def __init__(self, root: Path) -> None:
        """Anchor the store at `root`, creating it if absent."""
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, source_id: str, content_sha256: str, filename: str) -> Path:
        """Where an object with this hash lives, whether or not it exists yet."""
        return self.root / source_id / content_sha256 / filename

    def put(self, source_id: str, fetched: FetchedBytes, filename: str) -> StoredObject:
        """Store bytes verbatim and return their identity. Existing objects are left untouched."""
        digest = hashlib.sha256(fetched.content).hexdigest()
        path = self.path_for(source_id, digest, filename)
        already = path.exists()
        if not already:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(fetched.content)
        return StoredObject(
            retrieval_id=digest,
            content_sha256=digest,
            byte_count=len(fetched.content),
            raw_path=path,
            was_already_present=already,
        )


def snapshot_row(
    *,
    source_id: str,
    fetched: FetchedBytes,
    stored: StoredObject,
    reference_start: str,
    reference_end: str,
    release_status: str,
    naics_vintage: str,
    schema_fingerprint: str,
    parser_version: str,
    source_publication_date: str,
    secrets: Sequence[str | None],
) -> dict[str, object]:
    """Build one `source_snapshot` row, refusing to emit it if a secret is present."""
    params_json = json.dumps(fetched.params, sort_keys=True)
    assert_no_secret(fetched.url, secrets)
    assert_no_secret(params_json, secrets)
    return {
        "snapshot_id": stored.retrieval_id,
        "source_id": source_id,
        "request_url_or_file": fetched.url,
        "request_parameters_json": params_json,
        "retrieved_at_utc": fetched.retrieved_at_utc,
        "source_publication_date": source_publication_date,
        "reference_start": reference_start,
        "reference_end": reference_end,
        "release_status": release_status,
        "naics_vintage": naics_vintage,
        "schema_fingerprint": schema_fingerprint,
        "content_sha256": stored.content_sha256,
        "byte_count": stored.byte_count,
        "http_status": fetched.http_status,
        "parser_version": parser_version,
        "raw_path": str(stored.raw_path),
    }
