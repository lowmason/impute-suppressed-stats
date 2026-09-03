"""Shared helpers for the Stage 0 source audit.

Stage 0 predates the `logging_employment` package (Stage 1 builds it), so this module is
deliberately standalone: no package import, no config system. Every audit script is a PEP 723
single file run with `uv run --no-project`, and imports this module as a sibling.

Retention rule (plan Global Constraints): `record_extract` and `download_extract` store the
response body byte-for-byte. No row filter, no column projection, and no aggregation-level
restriction is ever applied on the way to disk. Filtering happens only in analysis, and every
filter predicate is recorded in the source summary.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

AUDIT_ROOT = Path("data/raw/audit")
FINDINGS_DIR = Path("specs/findings")
WINDOW_START = "2017-01"
WINDOW_END = "2024-12"
WINDOW_YEARS = tuple(range(2017, 2025))
INDUSTRY_CODE = "113310"
TIMEOUT_SECONDS = 300.0

# Appendix A `geography_universe: 'states_dc'` — the 50 states plus D.C., as two-digit FIPS.
# Shared here, not re-declared per script, so Tasks 4 and 6 cannot drift against each other.
STATES_DC_FIPS = (
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12", "13", "15", "16", "17",
    "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31",
    "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "44", "45", "46",
    "47", "48", "49", "50", "51", "53", "54", "55", "56",
)
assert len(STATES_DC_FIPS) == 51, "states_dc universe must be 50 states + D.C."
STATE_AREAS = {f"{f}000" for f in STATES_DC_FIPS}
NATIONAL_AREA = "US000"

SECRET_ENV_VARS = ("CENSUS_API_KEY", "BLS_API_KEY", "BEA_API_KEY", "FRED_API_KEY")
ACCESS_STATUSES = ("verified", "documented", "not_obtainable")
COVERAGE_KEYS = ("published_start", "published_end", "window_start", "window_end",
                 "covered", "uncovered")


@dataclass(frozen=True)
class ExtractRecord:
    """One fetched file: where it came from, where it landed, and what it hashes to."""

    source: str
    url: str
    path: str
    sha256: str
    bytes: int
    retrieved_utc: str
    http_status: int


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def contact_email() -> str:
    """D3: bls.gov admits scripted clients only when the User-Agent carries a contact."""
    email = os.environ.get("BLS_CONTACT_EMAIL", "").strip()
    if not email:
        raise RuntimeError("BLS_CONTACT_EMAIL is unset; `set -a && source .env && set +a` first")
    return email


def build_client() -> httpx.Client:
    ua = f"logging-employment-audit/0 ({contact_email()})"
    return httpx.Client(
        headers={"User-Agent": ua}, timeout=TIMEOUT_SECONDS, follow_redirects=True
    )


def request(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    retries: int = 3,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """4xx fails fast (it is a finding, not a transient); 5xx and transport errors back off."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code < 500:
                raise
            last = exc
        except httpx.TransportError as exc:
            last = exc
        if attempt < retries:
            sleep(backoff * 2**attempt)
    assert last is not None
    raise last


def probe(client: httpx.Client, url: str, *, params: dict | None = None) -> tuple[int, int]:
    """Status and byte count without raising — a 404 is the answer the boundary walk wants."""
    try:
        resp = client.get(url, params=params)
    except httpx.TransportError:
        return (0, 0)
    return (resp.status_code, len(resp.content))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_no_secrets(text: str) -> None:
    """D3: no key value may appear in any manifest (§7.2)."""
    for name in SECRET_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value and value in text:
            raise RuntimeError(f"{name} value leaked into an audit artifact")


def _write_sidecar(dest: Path, digest: str) -> None:
    (dest.parent / f"{dest.name}.sha256").write_text(f"{digest}  {dest.name}\n")


def record_extract(
    source: str, url: str, rel_path: str, content: bytes, *, http_status: int = 200
) -> ExtractRecord:
    """Write `content` verbatim under data/raw/audit/<source>/<rel_path> with a hash sidecar."""
    assert_no_secrets(url)
    dest = AUDIT_ROOT / source / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    digest = sha256_bytes(content)
    _write_sidecar(dest, digest)
    return ExtractRecord(source, url, str(dest), digest, len(content), _utcnow(), http_status)


def download_extract(
    client: httpx.Client, source: str, url: str, rel_path: str
) -> ExtractRecord:
    """Stream a large file to disk, hashing as it goes (QCEW bulk ZIPs are 300-500 MB)."""
    assert_no_secrets(url)
    dest = AUDIT_ROOT / source / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with client.stream("GET", url) as resp:
        resp.raise_for_status()
        status = resp.status_code
        with dest.open("wb") as fh:
            for chunk in resp.iter_bytes(1 << 20):
                fh.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    hexdigest = digest.hexdigest()
    _write_sidecar(dest, hexdigest)
    return ExtractRecord(source, url, str(dest), hexdigest, size, _utcnow(), status)


def validate_summary(payload: dict[str, Any]) -> None:
    """Raise `ValueError` unless the payload matches the Task 1 summary schema exactly."""
    for key in ("source", "generated_utc", "coverage_span", "access", "extracts", "findings"):
        if key not in payload:
            raise ValueError(f"summary missing top-level key {key!r}")
    missing = [k for k in COVERAGE_KEYS if k not in payload["coverage_span"]]
    if missing:
        raise ValueError(f"coverage_span missing {missing}")
    access = payload["access"]
    if access.get("status") not in ACCESS_STATUSES:
        raise ValueError(f"access.status must be one of {ACCESS_STATUSES}")
    if access["status"] != "verified" and not access.get("reason"):
        raise ValueError("access.reason is required unless access.status == 'verified'")
    for rec in payload["extracts"]:
        for key in ("source", "url", "path", "sha256", "bytes", "retrieved_utc", "http_status"):
            if key not in rec:
                raise ValueError(f"extract record missing {key!r}")


def write_summary(
    source: str,
    *,
    coverage_span: dict[str, str],
    access: dict[str, Any],
    extracts: list[ExtractRecord],
    findings: dict[str, Any],
) -> Path:
    payload = {
        "source": source,
        "generated_utc": _utcnow(),
        "coverage_span": coverage_span,
        "access": access,
        "extracts": [asdict(e) for e in extracts],
        "findings": findings,
    }
    validate_summary(payload)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    assert_no_secrets(text)
    dest = AUDIT_ROOT / source / "summary.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    return dest


def load_summary(source: str) -> dict[str, Any]:
    return json.loads((AUDIT_ROOT / source / "summary.json").read_text())
