"""Shared helpers for the Stage 0 source audit.

Stage 0 predates the `logging_employment` package (Stage 1 builds it), so this module is
deliberately standalone: no package import, no config system. Every audit script is a PEP 723
single file run with `uv run --no-project`, and imports this module as a sibling.

Retention rule (plan Global Constraints): `record_extract` and `download_extract` store the
response body byte-for-byte. No row filter, no column projection, and no aggregation-level
restriction is ever applied on the way to disk. Filtering happens only in analysis, and every
filter predicate is recorded in the source summary.

Secret-guard scope: the plan's Global Constraints name `record_extract` and `write_summary` for
the no-leaked-key guard, not `download_extract`. `record_extract` scans both `url` and the
fully-buffered `content`; `download_extract` scans only `url` — its body is streamed to disk in
fixed-size chunks and never fully buffered, and a correct substring scan across chunk boundaries
would need a rolling buffer. That's a deliberate boundary for every consumer of this module
to know about, not an oversight.
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
from typing import Any, TypeVar

import httpx

# Resolved from this file's location, not the process CWD — a script launched from inside
# scripts/audit/ (e.g. `cd scripts/audit && uv run foo.py`) must still write to the repo-root
# data/ and specs/ trees, not a nested copy relative to wherever it happened to be launched.
_REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT = _REPO_ROOT / "data" / "raw" / "audit"
FINDINGS_DIR = _REPO_ROOT / "specs" / "findings"
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
# `window_start`/`window_end` are D1's window, identical in every summary. `published_start`
# and `published_end` are NOT uniform, and a reader who takes them as always-measured, or as
# always denominated in years, will be wrong. Across the twelve shipped summaries they carry:
#   - the source's own publication bounds, derived from what the run actually fetched. This is
#     the intended reading, and the one most sources use (`qcew_routes` -- the years the slice
#     route served -- plus `bds`, `ces`, `susb`, `fia`, `tpo`, `cbp_metadata`, `cbp_regime`,
#     `qcew_identity`, `qcew_panel`).
#   - D1's window restated, where the source publishes nothing year-indexed to measure:
#     `qcew_codes`, whose titles files are not year-indexed at all, and `qcew_size`.
#   - a resolution that varies with the source: bare years ("2017"), quarters ("2017-Q1",
#     `qcew_size`), or months ("2017-01", `qcew_panel`). There is no declared format.
# Documented rather than reconciled: each value is prescribed by its own task brief, and
# changing one would mean re-fetching that source. So the exit gate and Stage 1 should read
# `published_*` as "the bound this source's brief asked for, in whatever unit it asked for",
# and use `covered` / `uncovered` -- measured everywhere -- for what a source actually spans.


@dataclass(frozen=True)
class ExtractRecord:
    """One fetched file: where it came from, where it landed, and what it hashes to."""

    source: str
    url: str
    path: str
    sha256: str
    bytes: int
    retrieved_utc: str
    # `int | None`, not `int`: `qcew_panel`'s derived parquet is never fetched over HTTP, so it
    # records no status at all rather than a fabricated one. `validate_summary` requires the
    # key's presence, not its type, and the exit gate renders `None` as an empty manifest
    # field. Every fetched extract still carries the status its response arrived with.
    http_status: int | None


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


_T = TypeVar("_T")


def _is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
    """5xx is transient by definition. 429 (rate limiting) is the one 4xx that is too — the
    archetypal case is a multi-year boundary walk against data.bls.gov. Every other 4xx is a
    finding, not a transient, and fails fast."""
    code = exc.response.status_code
    return code >= 500 or code == 429


def _retry(
    attempt: Callable[[], _T],
    *,
    retries: int,
    backoff: float,
    sleep: Callable[[float], None],
) -> _T:
    """Shared backoff policy: call `attempt`, retrying a retryable status or a transport error
    with exponential backoff. Used by both `request` and `download_extract` so the streamed
    route cannot drift from the non-streamed one."""
    last: Exception | None = None
    for attempt_no in range(retries + 1):
        try:
            return attempt()
        except httpx.HTTPStatusError as exc:
            if not _is_retryable_status(exc):
                raise
            last = exc
        except httpx.TransportError as exc:
            last = exc
        if attempt_no < retries:
            sleep(backoff * 2**attempt_no)
    assert last is not None
    raise last


def request(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    retries: int = 3,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """4xx fails fast (a finding, not a transient) — except 429, which is rate limiting and
    backs off like 5xx and transport errors."""

    def _attempt() -> httpx.Response:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp

    return _retry(_attempt, retries=retries, backoff=backoff, sleep=sleep)


def probe(client: httpx.Client, url: str, *, params: dict | None = None) -> tuple[int, int]:
    """Status and byte count, without raising on any HTTP status — a 404 is the answer the
    boundary walk wants.

    "Without raising" is about statuses, and about one exception family, not about every
    failure. `httpx.TransportError` is caught and reported as the sentinel `(0, 0)` (DNS
    failure, connection refused, timeout: no response at all). Its siblings under
    `httpx.RequestError` are not caught: `DecodingError` and `TooManyRedirects` are not
    `TransportError` subclasses and propagate to the caller. That is deliberate. Widening the
    catch would report a response that did arrive but could not be decoded as `(0, 0)` — as no
    response at all — collapsing two findings a boundary walk exists to tell apart.

    Callers must likewise distinguish the sentinel from a real status: `(0, 0)` means "network
    failed"; any other first element means "endpoint answered", including a 4xx/5xx, which is
    itself the finding the boundary walk is looking for.

    The body is read only to measure it, and is then discarded — nothing is written, and
    nothing but the length is returned. A caller treating a 200 here as evidence must re-fetch
    the URL and record the bytes (`record_extract` / `download_extract`); a `(200, n)` from
    this function vouches for no artifact on disk."""
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


def assert_no_secrets_bytes(data: bytes) -> None:
    """Sole implementation of the secret-value comparison. Checks each secret env value's
    UTF-8-encoded bytes against the raw bytes rather than decoding the buffer, so non-UTF-8
    extract content — expected, since these are third-party source bytes — can never raise
    here for a direct byte caller (e.g. `record_extract`'s `content`). `assert_no_secrets` (the
    text-taking, frozen-signature entry point) delegates here too, after first encoding its
    `str` input; that encode step is what `assert_no_secrets`'s own docstring covers, not this
    one. One comparison implementation either way, so a hardening change made here is never
    forgotten on the other path."""
    for name in SECRET_ENV_VARS:
        value = os.environ.get(name, "").strip()
        if value and value.encode("utf-8") in data:
            raise RuntimeError(f"{name} value leaked into an audit artifact")


def assert_no_secrets(text: str) -> None:
    """D3: no key value may appear in any manifest (§7.2). Delegates to
    `assert_no_secrets_bytes`; `surrogateescape` means a stray lone surrogate in `text` (e.g.
    from upstream data decoded that way) can never raise `UnicodeEncodeError` here."""
    assert_no_secrets_bytes(text.encode("utf-8", "surrogateescape"))


def _write_sidecar(dest: Path, digest: str) -> None:
    (dest.parent / f"{dest.name}.sha256").write_text(f"{digest}  {dest.name}\n")


def record_extract(
    source: str, url: str, rel_path: str, content: bytes, *, http_status: int | None = 200
) -> ExtractRecord:
    """Write `content` verbatim under data/raw/audit/<source>/<rel_path> with a hash sidecar."""
    assert_no_secrets(url)
    assert_no_secrets_bytes(content)
    dest = AUDIT_ROOT / source / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    digest = sha256_bytes(content)
    _write_sidecar(dest, digest)
    return ExtractRecord(source, url, str(dest), digest, len(content), _utcnow(), http_status)


def download_extract(
    client: httpx.Client, source: str, url: str, rel_path: str
) -> ExtractRecord:
    """Stream a large file to disk, hashing as it goes (QCEW bulk ZIPs are 300-500 MB).

    Streams to a `.part` sibling of `dest` and `os.replace`s it into place only once the
    transfer is complete and the sidecar is written — a failed or interrupted stream must
    never leave a truncated file at `dest`; its absence, not a missing sidecar, is the
    signal that the download did not finish. Retries with the same backoff policy as
    `request` (5xx and transport errors back off, 429 counts as transient, any other 4xx
    fails fast). The retry/backoff values match `request`'s defaults but are not parameters
    here: this signature is frozen across its call sites.

    Note: each retry restarts the transfer from byte zero — no `Range`/resume support. That is
    a deliberate scope boundary, not an oversight; partial-content resume is a bigger change
    than the truncated-artifact bug this fixes.
    """
    assert_no_secrets(url)
    dest = AUDIT_ROOT / source / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dest = dest.parent / f"{dest.name}.part"

    def _attempt() -> tuple[int, str, int]:
        digest = hashlib.sha256()
        size = 0
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            status = resp.status_code
            with tmp_dest.open("wb") as fh:
                for chunk in resp.iter_bytes(1 << 20):
                    fh.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        return status, digest.hexdigest(), size

    try:
        # Matches request()'s defaults (retries=3, backoff=2.0); time.sleep is looked up here,
        # at call time, rather than bound as a default parameter, so tests can monkeypatch it.
        status, hexdigest, size = _retry(_attempt, retries=3, backoff=2.0, sleep=time.sleep)
        # Sidecar write and the atomic rename are inside this try too: a failure in either one
        # (permissions, full disk) must still hit the `.part` cleanup below, not orphan it.
        _write_sidecar(dest, hexdigest)
        os.replace(tmp_dest, dest)
    except Exception:
        tmp_dest.unlink(missing_ok=True)
        raise

    return ExtractRecord(source, url, str(dest), hexdigest, size, _utcnow(), status)


def validate_summary(payload: dict[str, Any]) -> None:
    """Raise `ValueError` unless the payload matches the Task 1 summary schema exactly."""
    if not isinstance(payload, dict):
        raise ValueError("summary payload must be a dict")
    for key in ("source", "generated_utc", "coverage_span", "access", "extracts", "findings"):
        if key not in payload:
            raise ValueError(f"summary missing top-level key {key!r}")
    coverage_span = payload["coverage_span"]
    if not isinstance(coverage_span, dict):
        raise ValueError("coverage_span must be a dict")
    missing = [k for k in COVERAGE_KEYS if k not in coverage_span]
    if missing:
        raise ValueError(f"coverage_span missing {missing}")
    if coverage_span["window_start"] != WINDOW_START:
        raise ValueError(f"coverage_span.window_start must be {WINDOW_START!r}")
    if coverage_span["window_end"] != WINDOW_END:
        raise ValueError(f"coverage_span.window_end must be {WINDOW_END!r}")
    access = payload["access"]
    if not isinstance(access, dict):
        raise ValueError("access must be a dict")
    if access.get("status") not in ACCESS_STATUSES:
        raise ValueError(f"access.status must be one of {ACCESS_STATUSES}")
    if access["status"] != "verified" and not access.get("reason"):
        raise ValueError("access.reason is required unless access.status == 'verified'")
    extracts = payload["extracts"]
    if not isinstance(extracts, list):
        raise ValueError("extracts must be a list")
    for rec in extracts:
        if not isinstance(rec, dict):
            raise ValueError("extract record must be a dict")
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
    # ensure_ascii=False: the default would rewrite a non-ASCII secret value's characters as
    # \uXXXX escapes, so assert_no_secrets's substring check below would never see the literal
    # value and would miss the leak.
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert_no_secrets(text)
    dest = AUDIT_ROOT / source / "summary.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    # encoding="utf-8": JSON is UTF-8 by definition (RFC 8259). Without this, both write and
    # read fall back to locale.getpreferredencoding(False) — harmless while ensure_ascii=True
    # guaranteed pure-ASCII output, but G7 (above) turned that off, so text can now carry
    # literal non-ASCII characters and the locale's encoding choice matters.
    dest.write_text(text, encoding="utf-8")
    return dest


def load_summary(source: str) -> dict[str, Any]:
    return json.loads((AUDIT_ROOT / source / "summary.json").read_text(encoding="utf-8"))
