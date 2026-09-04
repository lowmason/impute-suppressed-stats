# Stage 0: Source Access, Dimensionality, and National-Identity Audit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via
> subagent-driven-development (the default) — or executing-plans when your human partner
> chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/logging-employment-spec-roadmap.md, Stage 0 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Establish from fetched files what each source actually publishes for NAICS 113310
over 2017-01 → 2024-12, by which route, and which `SRC-QCEW-006` branch the national identity
takes, and write it all down in `specs/findings/source-audit.md` so no later stage rests on an
assumed dimension or an unavailable margin.

**Architecture:** Stage 0 is an investigation, not a library. It ships a directory of
standalone PEP 723 scripts under `scripts/audit/`, one per source question, sharing one thin
helper module (`scripts/audit/_common.py`) that owns the HTTP client, byte-for-byte extract
storage with sha256 sidecars, and a fixed JSON summary schema. Each script fetches, stores raw
bytes verbatim, analyses, and writes `data/raw/audit/<source>/summary.json`. A final assembly
step renders every summary into the finding document and re-verifies every hash. Logic that
makes a *judgment* — the `SRC-QCEW-006` branch rule, the state-universe partition, the
size-dimensionality predicate — is written test-first, before the scan it will judge, so a
verdict cannot be reverse-engineered from the data it is supposed to evaluate.

**Tech Stack:** Python ≥ 3.12 via `uv run --no-project` with PEP 723 inline metadata; `httpx`
for fetching; `polars` for tabular analysis; `pytest` for the judgment-logic tests. No project
package, no lockfile, no `pyproject.toml` — Stage 1 introduces all three.

---

## Global Constraints

Every task's requirements implicitly include this section. Values marked "verbatim" are copied
from `specs/logging-employment-spec.md` and its Rollout note; do not paraphrase them.

- **Window (D1, verbatim):** pilot `2017-01` → `2024-12`. QCEW reference years 2017–2024,
  quarters 1–4 — 32 quarters, 96 months.
- **Target industry (verbatim):** `industry_code_used = '113310'`, `industry_title = 'Logging'`.
  The supplied code `'1113310'` is invalid and is recorded, never silently replaced (§3.1).
- **Geography universe (Appendix A, verbatim):** `geography_universe: 'states_dc'` — the 50
  states plus the District of Columbia.
- **Ownership (Appendix A, verbatim):** `ownership: 'private'`. The numeric `own_code` for
  private ownership MUST be derived from the fetched QCEW ownership titles file, never
  hardcoded from memory or from a research review.
- **Source access (D3, verbatim):** live fetch from `data.bls.gov` and `api.census.gov`.
  Credentials come from an untracked repo-root `.env` (keys present: `CENSUS_API_KEY`,
  `BLS_API_KEY`, `BEA_API_KEY`, `FRED_API_KEY`, `BLS_CONTACT_EMAIL`) loaded with python-dotenv.
  `.env` MUST be gitignored before the first commit that adds code, and no key value may appear
  in any manifest (§7.2). Note that `bls.gov` admits scripted clients only when the User-Agent
  carries a contact address; `BLS_CONTACT_EMAIL` exists for that purpose.
  *Stage 0 loads those credentials by shell sourcing* — `set -a && source .env && set +a`, as
  every run command in this plan does — **not** with python-dotenv. D3 names python-dotenv as
  the project's credential mechanism and D4 places it in the Stage 1 package's `dev`
  dependency group; Stage 0 has no package, no `pyproject.toml` and no dependency groups, so
  it has nowhere to put it. Do not `import dotenv` in an audit script: it is absent from every
  PEP 723 dependency block here and from the standard test command, so the import would fail
  at run time.
- **Dual-route mandate (D5, verbatim):** The §5.4 seed endpoint serves only the most recent
  five reference years, so it cannot cover all of D1's window. Stage 1 implements both the Open
  Data CSV slice route and the downloadable bulk-file route behind one ingest interface,
  selecting by reference year from the boundary Stage 0 measures. §5.4's instruction not to
  hard-code a "latest" year applies to both routes. **Stage 0 measures that boundary
  empirically and reports whatever it finds — including a finding that contradicts the
  five-year claim.**
- **Verbatim raw retention.** Every fetched response body is written to disk byte-for-byte. No
  row filter, no column projection, no aggregation-level restriction, and no quarter selection
  is applied on the way to disk. Filtering happens only in analysis, and every filter predicate
  is recorded in the source summary. *(The reference repo `/Users/lowell/Projects/bls-stats`
  is a useful pattern for the HTTP client — descriptive User-Agent, 4xx fast-fail, 5xx
  exponential backoff, streamed 300 MB downloads, 300 s timeout — and its URL templates are
  verified. Do not route Stage 0 through its QCEW engine: `engines/qcew.py:99-105` filters rows
  to selected quarters and splits on `size_code`, `fetch_year(with_size=False)` drops the
  entire by-size file, and `pipeline.py:132` rejects a frame whose row count falls outside a
  ±20% band. Those are correct choices for a vintage ingest pipeline and wrong for an audit,
  which must see every published estimate.)*
- **No numerical disclosure threshold (§2.2 row 1, verbatim):** The implementation MUST NOT
  encode an asserted current "80/3" rule or any other numerical confidentiality threshold. The
  current public rule is not sufficiently disclosed. Use the published disclosure flag and
  public accounting structure. No audit script may branch on an assumed cell-count or
  concentration threshold.
- **Findings assert shape, not value.** No step in this plan states what a fetched file will
  contain. "Expected:" blocks describe the *shape* of the output (keys, column names, row
  cardinality) so a real finding is never mistaken for a test failure, and a test failure is
  never mistaken for a finding.
- **`SRC-QCEW-006` decision thresholds (defaults set by this plan; flag at handoff).**
  1. "Equals" means **exact integer equality**, tolerance 0. QCEW monthly employment and
     quarterly establishment counts are integer counts of jobs and establishments.
  2. A gap that closes only after subtracting non-state areas present in the national universe
     is **`residual_cells`**, not `enforce` — §3.2: "A national control MUST NOT be imposed on
     a state universe that omits components included in the national total."
- **Secrets.** Census API keys travel in `params`, never in a URL string that is recorded.
  `_common.write_summary` and `_common.record_extract` refuse to write any artifact containing
  an environment key value.
- **Commits.** Every task ends with a commit on the current branch. Commit messages use
  Conventional Commits (`chore:`, `feat:`, `docs:`, `test:`).

---

## File Structure

| Path | Responsibility |
|---|---|
| `.gitignore` | *(modify)* Keeps `.env`, `data/`, `runs/`, and tool caches out of git. |
| `scripts/audit/_common.py` | The only shared code: HTTP client, retry, verbatim extract storage with sha256 sidecars, summary JSON schema and validator, secret guard. |
| `scripts/audit/qcew_routes.py` | Task 2 — slice-route year boundary and bulk-route confirmation. |
| `scripts/audit/qcew_codes.py` | Task 3 — code/title inventory on 113310 rows; `SRC-QCEW-007` alignment statement. |
| `scripts/audit/qcew_panel.py` | Task 4 — builds the 113310 private state/national panel; suppression share. |
| `scripts/audit/qcew_identity.py` | Task 5 — geography-universe test, per-quarter comparison table, `SRC-QCEW-006` branch verdict. |
| `scripts/audit/qcew_size.py` | Task 6 — `SRC-QSIZE-002` simultaneous-dimensionality check. |
| `scripts/audit/cbp_metadata.py` | Task 7 — per-vintage NAICS predicate, `EMPSZES`, `LFO`, keyed 113310 extract. |
| `scripts/audit/cbp_regime.py` | Task 8 — disclosure regime by reference year. |
| `scripts/audit/ces_levels.py` | Task 9 — per-state CES publication level. |
| `scripts/audit/bds_detail.py` | Task 10 — BDS finest industry detail. |
| `scripts/audit/susb_layout.py` | Task 11 — SUSB detailed-sizes file layout. |
| `scripts/audit/forest_sources.py` | Task 12 — TPO and FIA access verdicts. |
| `scripts/audit/verify_extracts.py` | Task 13 — re-hashes every extract, validates every summary, emits the committed manifest CSV. This is the exit gate and is re-run whenever the stage is re-checked. |
| `scripts/audit/assemble_finding.py` | Task 13 — renders every summary into `specs/findings/source-audit.md`. |
| `tests/audit/test_common.py` | Task 1 — harness contract: verbatim bytes, hash sidecars, summary validation, secret guard, retry policy. |
| `tests/audit/test_panel_flags.py` | Task 4 — panel flag semantics: `suppressed` is boolean not null, suppressed employment is null not zero, sub-state rows excluded. |
| `tests/audit/test_identity_rule.py` | Task 5 — the `SRC-QCEW-006` branch rule, on toy panels, written before the real scan. |
| `tests/audit/test_size_predicate.py` | Task 6 — the simultaneous-dimensionality predicate, on toy frames. |
| `specs/findings/source-audit.md` | The stage deliverable. |
| `specs/findings/source-audit-extracts.csv` | Committed manifest: one row per fetched extract with its sha256. |
| `data/raw/audit/<source>/` | Gitignored. Raw bytes, `.sha256` sidecars, and `summary.json`. |

**Standard commands** (run from the repository root):

```bash
# Run one audit script
set -a && source .env && set +a && uv run --no-project scripts/audit/<name>.py

# Run the judgment-logic tests
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit -q
```

---

### Task 1: Repository hygiene and the audit harness

**Files:**
- Modify: `.gitignore` (currently one line: `.env`)
- Create: `scripts/audit/_common.py`
- Test: `tests/audit/test_common.py`

**Interfaces:**
- Consumes: an empty repository plus an untracked repo-root `.env` (D3).
- Produces — every later task imports these from `_common`:
  - Constants `AUDIT_ROOT: Path`, `FINDINGS_DIR: Path`, `WINDOW_START: str`, `WINDOW_END: str`,
    `WINDOW_YEARS: tuple[int, ...]`, `INDUSTRY_CODE: str`, `TIMEOUT_SECONDS: float`.
  - `STATES_DC_FIPS: tuple[str, ...]` — the 50 states plus D.C. as two-digit FIPS (Appendix A
    `geography_universe: 'states_dc'`); `STATE_AREAS: set[str]` (each code padded to a `*000`
    area) and `NATIONAL_AREA: str` (`"US000"`) derived from it. Tasks 4 and 6 consume these
    rather than re-declaring them.
  - `ExtractRecord` — frozen dataclass with fields
    `source: str, url: str, path: str, sha256: str, bytes: int, retrieved_utc: str, http_status: int`.
  - `build_client() -> httpx.Client`
  - `request(client: httpx.Client, url: str, *, params: dict | None = None, retries: int = 3, backoff: float = 2.0, sleep: Callable[[float], None] = time.sleep) -> httpx.Response`
  - `probe(client: httpx.Client, url: str, *, params: dict | None = None) -> tuple[int, int]`
  - `record_extract(source: str, url: str, rel_path: str, content: bytes, *, http_status: int = 200) -> ExtractRecord`
  - `download_extract(client: httpx.Client, source: str, url: str, rel_path: str) -> ExtractRecord`
  - `write_summary(source: str, *, coverage_span: dict, access: dict, extracts: list[ExtractRecord], findings: dict) -> Path`
  - `load_summary(source: str) -> dict`
  - `validate_summary(payload: dict) -> None`
  - `sha256_file(path: Path) -> str`
  - The **summary JSON schema**, which every source task must satisfy exactly:

    ```json
    {
      "source": "<registry key, matches the data/raw/audit/ subdirectory name>",
      "generated_utc": "<ISO-8601 UTC, seconds precision>",
      "coverage_span": {
        "published_start": "<earliest reference period the source publishes, or ''>",
        "published_end":   "<latest reference period the source publishes, or ''>",
        "window_start": "2017-01",
        "window_end": "2024-12",
        "covered":   "<the part of D1's window this source covers>",
        "uncovered": "<the part it does not, or '' when it covers the whole window>"
      },
      "access": {
        "route": "<URL template or documented procedure>",
        "status": "verified | documented | not_obtainable",
        "reason": "<required non-null unless status == 'verified'>"
      },
      "extracts": [ { "source": "...", "url": "...", "path": "...", "sha256": "...",
                      "bytes": 0, "retrieved_utc": "...", "http_status": 200 } ],
      "findings": { }
    }
    ```

    `findings` is free-form per source; each task below names the exact keys it must contain.

- [ ] **Step 1: Widen `.gitignore` and prove `.env` is untracked**

Replace the whole file:

```gitignore
# Credentials — D3: .env must never be tracked
.env

# Audit and pipeline data are large and rebuildable; hashes are recorded in
# specs/findings/source-audit-extracts.csv instead.
data/
runs/

# Python
.venv/
__pycache__/
*.pyc

# Tool caches
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 2: Assert the credential is untracked and loadable**

Run:

```bash
git ls-files | grep -c '^\.env$' ; git check-ignore -v .env
set -a && source .env && set +a && test -n "$BLS_CONTACT_EMAIL" && echo "contact email present"
```

Expected: the `grep -c` prints `0`; `git check-ignore` prints a rule line naming `.gitignore`
and `.env`; the last command prints `contact email present`. If `grep -c` prints anything but
`0`, stop — run `git rm --cached .env` and re-check before continuing.

- [ ] **Step 3: Write the failing harness test**

Create `tests/audit/test_common.py`:

```python
import json

import httpx
import pytest

import _common


def test_record_extract_stores_bytes_verbatim_and_hashes(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    body = b'"a","b"\r\n"01000",\xff\n'  # CRLF and a non-UTF8 byte must survive
    rec = _common.record_extract("qcew", "https://example.test/x.csv", "x.csv", body)
    written = (tmp_path / "qcew" / "x.csv").read_bytes()
    assert written == body
    assert rec.bytes == len(body)
    assert _common.sha256_file(tmp_path / "qcew" / "x.csv") == rec.sha256
    sidecar = (tmp_path / "qcew" / "x.csv.sha256").read_text()
    assert sidecar == f"{rec.sha256}  x.csv\n"


def test_write_summary_round_trips_and_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    rec = _common.record_extract("cbp", "https://example.test/y.json", "y.json", b"[]")
    _common.write_summary(
        "cbp",
        coverage_span={
            "published_start": "2017", "published_end": "2022",
            "window_start": "2017-01", "window_end": "2024-12",
            "covered": "2017-2022", "uncovered": "2023-2024",
        },
        access={"route": "https://api.census.gov/data/{year}/cbp", "status": "verified",
                "reason": None},
        extracts=[rec],
        findings={"naics_predicate_by_year": {"2022": "NAICS2017"}},
    )
    loaded = _common.load_summary("cbp")
    _common.validate_summary(loaded)
    assert loaded["extracts"][0]["sha256"] == rec.sha256
    assert loaded["coverage_span"]["uncovered"] == "2023-2024"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("coverage_span"),
        lambda p: p["coverage_span"].pop("uncovered"),
        lambda p: p["access"].__setitem__("status", "probably fine"),
        lambda p: p["access"].update({"status": "documented", "reason": None}),
    ],
)
def test_validate_summary_rejects_broken_payloads(mutate):
    payload = {
        "source": "s", "generated_utc": "2026-09-03T00:00:00+00:00",
        "coverage_span": {"published_start": "", "published_end": "", "window_start": "2017-01",
                          "window_end": "2024-12", "covered": "", "uncovered": ""},
        "access": {"route": "r", "status": "verified", "reason": None},
        "extracts": [], "findings": {},
    }
    mutate(payload)
    with pytest.raises(ValueError):
        _common.validate_summary(payload)


def test_write_summary_refuses_to_leak_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setenv("CENSUS_API_KEY", "sekret-value-0123")
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _common.write_summary(
            "cbp",
            coverage_span={"published_start": "", "published_end": "", "window_start": "2017-01",
                           "window_end": "2024-12", "covered": "", "uncovered": ""},
            access={"route": "https://api.census.gov/data/2022/cbp?key=sekret-value-0123",
                    "status": "verified", "reason": None},
            extracts=[], findings={},
        )


def test_request_fails_fast_on_4xx_and_retries_5xx():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500 if calls["n"] < 3 else 200, text="ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    resp = _common.request(client, "https://example.test/a", sleep=lambda _: None)
    assert resp.status_code == 200 and calls["n"] == 3

    client404 = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError):
        _common.request(client404, "https://example.test/b", sleep=lambda _: None)


def test_probe_returns_status_without_raising():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="no")))
    assert _common.probe(client, "https://example.test/c") == (404, 2)


def test_contact_email_required(monkeypatch):
    monkeypatch.delenv("BLS_CONTACT_EMAIL", raising=False)
    with pytest.raises(RuntimeError, match="BLS_CONTACT_EMAIL"):
        _common.contact_email()
```

- [ ] **Step 4: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit -q
```

Expected: FAIL — collection error `ModuleNotFoundError: No module named '_common'`.

- [ ] **Step 5: Write the harness**

Create `scripts/audit/_common.py`:

```python
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
```

- [ ] **Step 6: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit -q
```

Expected: PASS — 10 passed (the four parametrised validator cases count separately).

- [ ] **Step 7: Commit**

```bash
git add .gitignore scripts/audit/_common.py tests/audit/test_common.py
git commit -m "chore: gitignore data and add the Stage 0 audit harness"
```

---

### Task 2: QCEW acquisition routes and the slice-route year boundary

Closes: the QCEW half of `SRC-QCEW-006`'s "access route" field, D5's dual-route mandate, and
the roadmap exit criterion *"the QCEW year boundary is stated as a reference year, not an
approximation."*

**Files:**
- Create: `scripts/audit/qcew_routes.py`

**Interfaces:**
- Consumes: `_common` (Task 1).
- Produces: `data/raw/audit/qcew_routes/summary.json` with source key `qcew_routes`, and every
  served slice CSV at `data/raw/audit/qcew_routes/slices/{year}q{qtr}.csv`. Tasks 3, 4 and 5
  read those paths out of `load_summary("qcew_routes")["extracts"]`.
  `findings` keys:
  - `slice_probe` — list of `{year, qtr, http_status, bytes, content_type, row_count}`, one per
    probed reference quarter. An `http_status` of `0` means a transport failure survived
    `_common.request`'s retries — re-run this task rather than accepting the row.
  - `earliest_year_served` — int, or `null` when no year returned a parsable CSV.
  - `latest_year_served` — int.
  - `bulk_years_required` — list of ints: the window years the slice route does **not** serve.
    **This list may be empty.**
  - `bulk_years_fetched` — list of ints actually downloaded. When `bulk_years_required` is
    empty this is `[2017]`: D5 mandates both routes, so the bulk route is proved on the
    earliest window year regardless.
  - `bulk_member_names` — mapping year → the ZIP member matched for 113310.
  - `column_parity` — `{"slice_only": [...], "bulk_only": [...], "identical": bool,
    "slice_header_disagreement": {...}, "bulk_header_disagreement": {...}}`. The first three
    keys are the interface Tasks 3 and 4 read. **All three compare column NAMES only, never
    cell values** — so `identical: false` means the routes describe their columns differently,
    not that their data disagrees. Note the two comparisons differ in kind: `slice_only` and
    `bulk_only` are set differences, while `identical` is `slice_header == bulk_header`, an
    *ordered* list equality. Empty `slice_only` and `bulk_only` therefore do NOT imply
    `identical` — the same names in a different order, or a duplicated name, leave both set
    differences empty while `identical` is `false`. The two `*_disagreement`
    maps are empty when every served window quarter (slice) and every fetched year (bulk) share
    one header; a non-empty map is a finding about schema drift, recorded rather than
    normalised away. They are nested inside `column_parity` deliberately: Task 13's exit gate
    rejects any *top-level* `findings` value that is empty, and these are legitimately `{}`.

**Route notes for the implementer.** Two bulk variants exist and the choice is deliberate:
`https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip` (~480 MB) holds
one CSV member per industry, so a 113310-only member drops out of `namelist()`; the smaller
`{year}_qtrly_singlefile.zip` (~305 MB) holds one all-industry CSV and would need a streaming
filter. Use `by_industry`. Both are streamed by `download_extract` under `_common`'s 300 s
timeout, which is the number `bls-stats` uses for the same files.

- [ ] **Step 1: Write the script**

Create `scripts/audit/qcew_routes.py`:

```python
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

import httpx
import polars as pl

import _common as c

SOURCE = "qcew_routes"
SLICE_URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/{industry}.csv"
BULK_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_qtrly_by_industry.zip"


def read_csv_bytes(content: bytes) -> pl.DataFrame:
    """All columns as Utf8: area_fips has leading zeros and alpha CSA codes like 'C1010'."""
    return pl.read_csv(io.BytesIO(content), infer_schema_length=0)


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
            probe_rows.append({
                "year": year, "qtr": qtr, "http_status": status,
                "bytes": len(content), "content_type": ctype, "row_count": rows,
            })
            if rows > 0:
                served.add(year)
            if year in c.WINDOW_YEARS and status == 200 and content:
                if rows > 0:
                    extracts.append(c.record_extract(
                        SOURCE, url, f"slices/{year}q{qtr}.csv", content, http_status=status,
                    ))
                else:
                    # not a .csv path: Task 3/4 glob extracts by `.endswith(".csv")` and
                    # would try to parse this body as data.
                    extracts.append(c.record_extract(
                        SOURCE, url, f"slices/unparseable_{year}q{qtr}.body", content,
                        http_status=status,
                    ))

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

    # `to_fetch` has more than one year on the normal D5 path (bulk_years_required
    # non-empty) — not just the single-year fallback this run took. Reassigning one
    # `bulk_header` per iteration would silently keep only the last year's columns; verify
    # every fetched year agrees before reducing to one. A disagreement is a bulk-side
    # schema-drift finding, not a bug, so it is recorded rather than picked around.
    distinct_bulk_headers = {tuple(h) for h in bulk_headers.values()}
    bulk_header = bulk_headers[to_fetch[0]]

    slice_paths = [e.path for e in extracts if e.path.endswith(".csv")]
    # Check every served window slice's header, not just the first — a mid-window BLS
    # schema change would otherwise go undetected. These files are already on disk: no
    # network cost.
    slice_headers = {p: read_csv_bytes(Path(p).read_bytes()).columns for p in slice_paths}
    distinct_slice_headers = {tuple(h) for h in slice_headers.values()}
    # slice_paths[0] is the earliest window year/quarter the slice route actually served
    # (extracts accumulate in ascending probe order) — the most defensible single
    # reference, now backed by the consistency check above rather than an assumption.
    slice_header = slice_headers[slice_paths[0]] if slice_paths else []

    parity = {
        "slice_only": sorted(set(slice_header) - set(bulk_header)),
        "bulk_only": sorted(set(bulk_header) - set(slice_header)),
        "identical": slice_header == bulk_header,
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

    # `covered` (Task 1 schema) is the part of D1's window this source covers, not the full
    # probed span — clamp to the window; `served` can include years probed outside it.
    covered_years = sorted(served & set(c.WINDOW_YEARS))
    covered = f"{min(covered_years)}-{max(covered_years)}" if covered_years else ""
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(earliest) if earliest else "",
            "published_end": str(latest) if latest else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
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
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/qcew_routes.py
```

Expected: a single stdout line of the form `slice years served: <int>-<int>; bulk required:
<list or 'none'>`. Runtime is dominated by the bulk download — one 480 MB stream, several
minutes on a normal connection. This step reports whatever the servers return; there is no
expected year value.

- [ ] **Step 3: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
s = json.load(open("data/raw/audit/qcew_routes/summary.json"))
f = s["findings"]
assert isinstance(f["earliest_year_served"], int), "no slice year served — investigate"
assert f["slice_probe"], "probe table is empty"
assert f["bulk_years_fetched"], "D5 requires the bulk route to be exercised"
assert f["bulk_member_names"], "no 113310 member found in any bulk ZIP"
for k in ("slice_only", "bulk_only", "identical",
          "slice_header_disagreement", "bulk_header_disagreement"):
    assert k in f["column_parity"], f"column_parity is missing {k!r}"
print("years served:", f["earliest_year_served"], "-", f["latest_year_served"])
print("bulk required:", f["bulk_years_required"], "fetched:", f["bulk_years_fetched"])
print("column parity identical:", f["column_parity"]["identical"])
print("slice extracts:", sum(1 for e in s["extracts"] if e["path"].endswith(".csv")))
PY
```

Expected: `earliest_year_served` and `latest_year_served` print as integers; `bulk_years_fetched`
is non-empty; the slice-extract count is `4 × (number of window years served)`. Any of those
assertions failing is a script bug, not a finding — fix the script. A `bulk_years_required` of
`[]` is a legitimate finding, not a failure.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/qcew_routes.py
git commit -m "feat(audit): measure QCEW slice-route year boundary and prove the bulk route"
```

---

### Task 3: QCEW code inventory on 113310 rows and the SRC-QCEW-007 alignment statement

Closes: the audit half of `REQ-006`; the roadmap's *"code/title lists actually present for
`agglvl_code`, `own_code`, `size_code`, and `disclosure_code` on 113310 rows"*; and
`SRC-QCEW-007`, which §8.1 states as *"It MUST test whether the national Logging total, state
Logging rows, ownership code, and aggregation level are definitionally aligned before creating
a constraint."*

**Files:**
- Create: `scripts/audit/qcew_codes.py`

**Interfaces:**
- Consumes: `_common`; `load_summary("qcew_routes")["extracts"]` for the slice CSV paths.
- Produces: `data/raw/audit/qcew_codes/summary.json` with source key `qcew_codes`, plus the
  five fetched titles files under `data/raw/audit/qcew_codes/titles/`.
  `findings` keys:
  - `titles_available` — mapping dimension → URL or `null`. **There is no published
    `disclosure_code` titles file** (only agglevel, ownership, size, area and industry exist at
    `https://data.bls.gov/cew/doc/titles/`), so its entry is `null` and its codes come from
    observed values only. Record that explicitly rather than hunting for the URL.
  - `codes_present` — mapping dimension → list of `{code, title, row_count}` observed on
    113310 rows across every fetched slice. `title` is `null` where no titles file exists.
  - `private_own_code` — the `own_code` whose title is `Private`, derived from the fetched
    ownership titles file.
  - `national_agglvl` / `state_agglvl` — the `agglvl_code` values carried by the national
    (`area_fips == "US000"`) and state-level 113310 rows, each with its title.
  - `alignment_srcqcew007` — `{national_agglvl, state_agglvl, own_code, industry_code,
    naics_vintage_by_year, period_basis, aligned: bool, notes}`. `aligned` is `true` only when
    the national and state rows carry the same `own_code`, the same `industry_code`, and
    aggregation levels whose titles describe the same industry detail at their two geography
    levels.
  - `size_code_values` — the distinct `size_code` values seen on 113310 slice rows, with row
    counts. (§8.2 context: the slice and singlefile products carry `size_code == "0"` only;
    Task 6 tests the by-size product separately.)

- [ ] **Step 1: Write the script**

Create `scripts/audit/qcew_codes.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Inventory the QCEW code values actually present on 113310 rows, join published titles, and
record the SRC-QCEW-007 national/state alignment statement."""

from __future__ import annotations

import io

import polars as pl

import _common as c

SOURCE = "qcew_codes"
TITLES = {
    "agglvl_code": "https://data.bls.gov/cew/doc/titles/agglevel/agglevel_titles.csv",
    "own_code": "https://data.bls.gov/cew/doc/titles/ownership/ownership_titles.csv",
    "size_code": "https://data.bls.gov/cew/doc/titles/size/size_titles.csv",
    "area_fips": "https://data.bls.gov/cew/doc/titles/area/area_titles.csv",
    "industry_code": "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv",
    # No disclosure_code titles file is published; codes come from observed values only.
    "disclosure_code": None,
}


def load_slices() -> pl.DataFrame:
    paths = [e["path"] for e in c.load_summary("qcew_routes")["extracts"]
             if e["path"].endswith(".csv")]
    if not paths:
        raise RuntimeError("no slice CSVs recorded by qcew_routes; run Task 2 first")
    frames = [pl.read_csv(p, infer_schema_length=0) for p in paths]
    df = pl.concat(frames, how="vertical")
    # Cheap coverage guard: Task 2's bulk route never persists an extracted .csv member (only
    # the .zip), so if a future Task 2 re-run finds the slice route no longer serving the full
    # D1 window, this function would otherwise silently hand back an incomplete panel. Cast
    # both sides to str explicitly rather than trusting today's infer_schema_length=0 dtype, so
    # a future polars behavior change surfaces as a failed guard, not a silently-empty set diff.
    years_present = {str(y) for y in df["year"].unique().to_list()}
    years_wanted = {str(y) for y in c.WINDOW_YEARS}
    missing = sorted(years_wanted - years_present)
    if missing:
        raise RuntimeError(
            f"loaded slice CSVs are missing window years {missing}; Task 2's slice route no "
            "longer serves the full c.WINDOW_YEARS panel -- re-run Task 2, or extend "
            "load_slices() to also load its recorded bulk-route .csv extracts"
        )
    return df


def title_map(content: bytes, code_col: str, title_col: str) -> dict[str, str]:
    df = pl.read_csv(io.BytesIO(content), infer_schema_length=0)
    return dict(zip(df[code_col].to_list(), df[title_col].to_list(), strict=True))


def _agglvl_detail(title: str) -> str:
    """QCEW agglvl titles carry the shape '<Geography>, <detail clause>'. Splitting on the
    first comma isolates the industry-detail / ownership-scope clause so it is comparable
    across geography levels. This docstring deliberately names no code and quotes no title:
    which agglvl codes are observed, and what their fetched titles say, is computed each run
    and recorded in the `national_agglvl` / `state_agglvl` findings and in `notes` -- a typed
    example here would be a second, unchecked copy of that, free to go stale."""
    return title.split(",", 1)[1].strip() if "," in title else title.strip()


def _same_industry_detail(
    nat_agglvl: list[str], st_agglvl: list[str], agglvl_titles: dict[str, str]
) -> tuple[bool, str]:
    """SRC-QCEW-007: true only when exactly one agglvl_code is observed at each geography
    level, and their titles agree once the leading geography clause is stripped -- i.e. both
    describe the same NAICS-digit detail and the same by-ownership breakout. This defends
    against a titles-metadata inconsistency (the fetched agglvl_code titles disagreeing with
    what industry_code and own_code already pinned upstream): it is a real check on the fetched
    file, not a tautology, and returns False if the titles for the two observed codes disagree.
    It is not, however, guaranteed to add discriminating power beyond the cardinality-of-one
    checks above -- wherever the two observed codes are the same industry-detail row at two
    different geographies, their agreement is close to expected. Whether that is so on any
    given run is computed rather than asserted here: a docstring cannot re-check itself, so
    `_observed_detail_sentence` groups the codes actually observed by their stripped clause and
    records what it finds in `notes`.

    Returns the verdict *and* a rendered clause naming the branch that produced it, because
    `notes` has to state the outcome rather than assert one. The three False branches are not
    interchangeable -- a cardinality failure, a title missing from the fetched file, and two
    clauses that genuinely differ are three different findings, and only the third one is about
    the clauses at all -- so a single "identical/different" rendering would let a run report a
    clause comparison it never performed."""
    if len(nat_agglvl) != 1 or len(st_agglvl) != 1:
        return False, (
            "the clause comparison was not reached: it needs exactly one agglvl code at each "
            f"geography level, but {len(nat_agglvl)} national and {len(st_agglvl)} state codes "
            "are observed"
        )
    nat_title = agglvl_titles.get(nat_agglvl[0])
    st_title = agglvl_titles.get(st_agglvl[0])
    missing = [
        code for code, title in ((nat_agglvl[0], nat_title), (st_agglvl[0], st_title))
        if title is None
    ]
    if missing:
        return False, (
            "the clause comparison was not reached: the fetched agglvl titles file carries no "
            f"entry for code(s) {', '.join(missing)}"
        )
    nat_detail, st_detail = _agglvl_detail(nat_title), _agglvl_detail(st_title)
    if nat_detail != st_detail:
        return False, (
            "stripping the leading geography clause leaves different detail clauses at the two "
            f"levels -- national {nat_detail!r} vs state {st_detail!r}"
        )
    return True, (
        "stripping the leading geography clause leaves an identical detail clause at both "
        f"levels ({nat_detail!r})"
    )


def _agglvl_geography(title: str) -> str:
    """The leading clause `_agglvl_detail` strips off: the geography level the code sits at."""
    return title.split(",", 1)[0].strip() if "," in title else ""


def _agglvl_title_list(codes: list[str], agglvl_titles: dict[str, str]) -> str:
    """Render observed agglvl codes with their fetched titles for `notes` -- pulled from the
    titles mapping fetched this run so this can never drift from what was actually fetched,
    for however many codes are observed (not assumed to be exactly one)."""
    return "; ".join(f"code {code} = {agglvl_titles.get(code)!r}" for code in codes)


def _observed_detail_sentence(agglvl_present: list[dict]) -> str:
    """Computed replacement for a prose claim about the fetched agglvl titles file as a whole.

    Groups the agglvl codes actually observed on `c.INDUSTRY_CODE` rows by the detail clause
    their fetched titles strip to, and states what that grouping shows -- so a future run whose
    codes strip to more than one clause says so instead of repeating today's agreement. Its
    input is `codes_present['agglvl_code']`, which is built on the `c.INDUSTRY_CODE`-filtered
    frame *before* the own_code filter is applied; the sentence therefore describes every
    `c.INDUSTRY_CODE` row at whatever ownership codes are present, not the private-only subset
    that nat/state_like carry, and names that frame rather than counting its ownership codes --
    a cardinality would be one more typed claim free to go stale. The geography names are read
    out of the fetched titles too, never typed, so they cannot claim a level the data does not
    contain."""
    by_detail: dict[str, list[str]] = {}
    for row in agglvl_present:
        title = row["title"]
        detail = _agglvl_detail(title) if title is not None else "<no fetched title>"
        geo = _agglvl_geography(title) if title is not None else ""
        by_detail.setdefault(detail, []).append(f"{row['code']} ({geo})" if geo else row["code"])
    rendered = "; ".join(
        f"{detail!r} at codes {', '.join(codes)}" for detail, codes in sorted(by_detail.items())
    )
    # Neutral lead, prefixed to both returns: it must not name an outcome, because the branch
    # below decides which outcome there is. "Scope of that agreement" read as a contradiction
    # on the disagreement branch, and had no antecedent at all when title_evidence_note placed
    # a "comparison was not reached" clause immediately before it.
    lead = (
        f"Scope of the fetched-title comparison, computed from the {len(agglvl_present)} "
        f"agglvl codes observed on {c.INDUSTRY_CODE} rows before the own_code filter: "
    )
    if len(by_detail) == 1:
        return (
            f"{lead}all of them strip to one detail clause -- {rendered}. So the "
            "identical-clause property is established across exactly the geography levels "
            "present here, which is all this run shows; it is not a claim about every title "
            "in the fetched agglvl_code.csv, whose other codes were not examined."
        )
    return (
        f"{lead}they strip to {len(by_detail)} distinct detail clauses -- {rendered} -- so the "
        "clause is not uniform across the codes present on these rows."
    )


def _extraneous_area_sentence(detail: list[dict]) -> str:
    """One sentence per state-like area code absent from c.STATE_AREAS, entirely from computed
    detail and the fetched area_fips titles -- never a typed figure, so a future re-run with a
    different extraneous set describes itself instead of silently repeating today's numbers."""
    if not detail:
        return "No state-like area code fell outside c.STATE_AREAS."
    return " ".join(
        f"{d['area_fips']} ({d['title']!r}, {d['row_count']} rows, in "
        f"{', '.join(d['years'])}) is present in state-like rows but absent from c.STATE_AREAS."
        for d in detail
    )


def _dc_sentence(detail: dict, n_quarters: int) -> str:
    """States what state_like actually shows about area_fips '11000' (DC) -- computed, not
    assumed absent, so a future re-run where DC starts publishing describes that instead of
    silently repeating today's absence claim."""
    if detail["present"]:
        return (
            f"District of Columbia (11000) is present in the state-like rows: "
            f"{detail['row_count']} rows, in {', '.join(detail['years'])}."
        )
    return (
        f"District of Columbia (11000) carries zero private-ownership {c.INDUSTRY_CODE} rows "
        f"in any of the {n_quarters} quarters in which {c.INDUSTRY_CODE} rows appear at all: "
        "it is entirely absent from this panel, not merely cell-suppressed within a published "
        "row."
    )


def _geography_universe_note(
    n_quarters: int,
    state_like_areas: list[str],
    extraneous_detail: list[dict],
    dc_detail: dict,
    nat_agglvl: list[str],
) -> str:
    """SRC-QCEW-007 / Sec 3.2 geography-universe evidence for `notes`. Every figure and every
    area code in it is computed from state_like, nat_agglvl and the fetched area_fips titles.
    The exception is the closing US000-composition argument: a BLS documentation quotation, an
    unquoted premise about which jurisdictions the national universe contains, and the
    conclusion that needs both. This script fetches none of the three and cannot re-derive any
    of them, so all three say so about themselves inline -- the premise and the conclusion as
    explicitly as the quotation, because the conclusion is the part a later task consumes and a
    marking scoped to the quotation alone would leave it looking checked. States only what the
    data and BLS's published documentation show -- never which way SRC-QCEW-006's branch should
    resolve. That verdict is Task 5's, reached test-first against toy panels before the real
    scan (plan Architecture), not reverse-engineered from this finding."""
    dc_gap = ""
    if not dc_detail["present"]:
        dc_gap = (
            " DC's complete row-level absence is a genuine states_dc coverage gap: a "
            "private-ownership Logging panel over this window will have no DC series at all, "
            "which a later task should expect rather than mistake for a bug. Because US000 "
            "includes DC on the hand-authored membership premise recorded above -- not by "
            "anything derived here -- while no DC state row is published, DC's contribution "
            "to the national total is unobservable at the state level -- a "
            "national-vs-sum-of-states residual distinct from, and additional to, cell-level "
            "suppression."
        )
    nat_label = f"agglvl-{'/'.join(nat_agglvl)}" if nat_agglvl else "national-agglvl"
    return (
        "Geography-universe finding for SRC-QCEW-007 / Sec 3.2: across all "
        f"{n_quarters} quarters in which {c.INDUSTRY_CODE} rows appear, the state-like "
        f"predicate above yields exactly {len(state_like_areas)} distinct area codes. "
        f"{_extraneous_area_sentence(extraneous_detail)} "
        f"{_dc_sentence(dc_detail, n_quarters)} "
        "The US000 composition argument that follows is hand-authored in all three of its "
        "parts -- quotation, premise and conclusion. This script fetches none of them, so none "
        "carries an extract hash and no later run re-checks any of them. Quoted, hand-"
        "transcribed from BLS's QCEW Aggregation Level Codes page "
        "(https://www.bls.gov/cew/classifications/aggregation/agg-level-titles.htm, footnote "
        "b): 'National level aggregations exclude Puerto Rico and Virgin Islands from the "
        "totals'. Unquoted premise, supplied by hand and carried by neither that quotation nor "
        "any other source cited here: the jurisdictions QCEW aggregates into a national total "
        "are "
        "the 50 states, DC, Puerto Rico and the Virgin Islands, and nothing else. Conclusion, "
        f"which needs both: read against the national agglvl code computed above ({nat_label}), "
        "the US000 national total is definitionally 50 states + DC, the same composition as "
        "geography_universe: 'states_dc'. The exclusion quotation on its own says only what is "
        "removed, never what remains -- the membership premise is what closes the argument, and "
        f"it is the part a later task should re-source before relying on this.{dc_gap}"
    )


def main() -> None:
    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    maps: dict[str, dict[str, str]] = {}

    for dim, url in TITLES.items():
        if url is None:
            continue
        resp = c.request(client, url)
        extracts.append(c.record_extract(SOURCE, url, f"titles/{dim}.csv", resp.content))
        header = pl.read_csv(io.BytesIO(resp.content), infer_schema_length=0).columns
        code_col = header[0]
        title_col = next(h for h in header if h.endswith("_title"))
        maps[dim] = title_map(resp.content, code_col, title_col)

    loaded = load_slices()
    df = loaded.filter(pl.col("industry_code") == c.INDUSTRY_CODE)
    # Two counts, not one. Both are computed, not typed, so `notes` below states actual quarter
    # counts rather than assuming the D1 window's nominal 32 -- distinct from load_slices()'s
    # year-only guard, so a single missing quarter within an otherwise-complete year still
    # shows up here. They are kept separate because they answer different questions and can
    # diverge: `n_quarters_loaded` counts the concatenated slice frame the industry_code filter
    # is applied *to*, while `n_quarters` counts the quarters that survive it. They coincide
    # only while every loaded quarter publishes at least one c.INDUSTRY_CODE row; using one
    # where the other belongs would silently attribute a post-filter count to the pre-filter
    # frame. Each `notes` sentence below names which of the two it is quoting.
    n_quarters_loaded = loaded.select(["year", "qtr"]).unique().height
    n_quarters = df.select(["year", "qtr"]).unique().height

    codes_present: dict[str, list[dict]] = {}
    for dim in ("agglvl_code", "own_code", "size_code", "disclosure_code"):
        counts = df.group_by(dim).len().sort(dim)
        codes_present[dim] = [
            {"code": code, "title": maps.get(dim, {}).get(code), "row_count": n}
            for code, n in zip(counts[dim].to_list(), counts["len"].to_list(), strict=True)
        ]
        # Defensive, not corrective: group_by(dim).len() cannot itself drop rows -- every row
        # lands in exactly one group, including a null-key group, so e.g. a null-vs-"" split on
        # a blank disclosure_code still produces two groups whose lengths sum back to
        # df.height. This guards the group_by -> list-comprehension pipeline as a whole (every
        # dimension partitions the same 113310 universe) against a future refactor that could
        # lose rows, not against a defect in group_by itself.
        observed = sum(row["row_count"] for row in codes_present[dim])
        if observed != df.height:
            raise RuntimeError(
                f"{dim}: group_by rows sum to {observed}, expected {df.height} 113310 rows "
                "-- a group was lost"
            )

    private = [code for code, title in maps["own_code"].items() if title.strip() == "Private"]
    if len(private) != 1:
        raise RuntimeError(f"expected exactly one 'Private' ownership title, got {private}")
    private_own = private[0]

    priv = df.filter(pl.col("own_code") == private_own)
    nat = priv.filter(pl.col("area_fips") == "US000")
    state_like = priv.filter(
        pl.col("area_fips").str.ends_with("000") & (pl.col("area_fips") != "US000")
    )
    nat_agglvl = sorted(set(nat["agglvl_code"].to_list()))
    st_agglvl = sorted(set(state_like["agglvl_code"].to_list()))

    # Geography-universe figures for `notes`, computed from state_like and the fetched
    # area_fips titles rather than typed, so a future re-run against revised or extended data
    # describes what it actually finds instead of silently repeating today's numbers.
    state_like_areas = sorted(set(state_like["area_fips"].to_list()))
    extraneous_detail = []
    for area in sorted(set(state_like_areas) - c.STATE_AREAS):
        sub = state_like.filter(pl.col("area_fips") == area)
        extraneous_detail.append({
            "area_fips": area,
            "title": maps["area_fips"].get(area),
            "row_count": sub.height,
            "years": sorted(set(sub["year"].to_list())),
        })
    dc_rows = state_like.filter(pl.col("area_fips") == "11000")
    dc_detail = {
        "present": dc_rows.height > 0,
        "row_count": dc_rows.height,
        "years": sorted(set(dc_rows["year"].to_list())),
    }

    # QCEW publishes no per-row NAICS-vintage column, so this is a documentation fact, not a
    # derivable one. Hand-authored (Step 3) from two BLS classification pages plus one unquoted
    # premise -- that QCEW does not retabulate prior reference years onto a new NAICS vintage --
    # which is what turns each page's "introduced with Q1 <year> data" into a claim about what
    # vintage the *earlier* years still carry. Quotations and premise alike are labelled
    # hand-authored in `notes` below; no later run re-checks either. Granting the premise, both
    # switch years fall on QCEW reference-year boundaries, so the mapping is a clean per-year
    # split with no year left "unconfirmed".
    naics_vintage = {
        "2017": "NAICS 2017", "2018": "NAICS 2017", "2019": "NAICS 2017",
        "2020": "NAICS 2017", "2021": "NAICS 2017",
        "2022": "NAICS 2022", "2023": "NAICS 2022", "2024": "NAICS 2022",
    }

    # Neither same_own_code nor same_industry_code is computed as a separate check, for the one
    # reason: each is a single filter applied *before* the national/state-like geography split,
    # so both nat and state_like are sub-frames of an already-filtered frame. nat and state_like
    # both derive from priv = df.filter(own_code == private_own), and priv from
    # df = loaded.filter(industry_code == c.INDUSTRY_CODE), so their own_code values can only
    # ever be {private_own} and their industry_code values only {c.INDUSTRY_CODE} -- or, in
    # either case, the empty set when there are no rows. There is no possible dataset where
    # either differs from the len(nat_agglvl) == 1 / len(st_agglvl) == 1 cardinality checks
    # below, which already fail on the empty case. A dedicated boolean for either would look
    # like an independent verification without being one: it can return only True-when-nonempty,
    # so it can never contradict anything. Both properties still hold and are still required by
    # SRC-QCEW-007 -- they are established by the recorded filter predicates (see
    # filter_predicates_note) rather than by a check that cannot fail. same_detail below is the
    # opposite case and is genuinely computed: it reads the *fetched* agglvl titles, which no
    # filter in this script constrains, so it can and would return False on a titles-metadata
    # inconsistency between the two geography levels.
    same_detail, detail_outcome = _same_industry_detail(
        nat_agglvl, st_agglvl, maps["agglvl_code"]
    )

    aligned = (
        len(nat_agglvl) == 1
        and len(st_agglvl) == 1
        and same_detail
    )

    observed_detail_sentence = _observed_detail_sentence(codes_present["agglvl_code"])

    # The one derivable part of the NAICS-vintage evidence. maps["industry_code"] was fetched
    # and parsed above; reading it here means the note quotes the fetched file instead of a
    # literal typed to match it, and describes an absent code rather than asserting a present
    # one. Deliberately not raised as an error: absence would be a finding for Stage 1 to act
    # on, and it does not invalidate the row inventory this script is producing.
    industry_title = maps["industry_code"].get(c.INDUSTRY_CODE)
    if industry_title is None:
        industry_title_sentence = (
            f"the fetched industry titles file carries no entry for {c.INDUSTRY_CODE} at all, "
            "which is itself a finding to resolve before Stage 1 relies on the code."
        )
    else:
        industry_title_sentence = (
            f"the fetched industry titles file gives {c.INDUSTRY_CODE} = {industry_title!r}, "
            "confirming the code is valid in the vintage that file reflects."
        )

    filter_predicates_note = (
        "Filter predicates recorded verbatim, applied in this order: "
        f"industry_code == '{c.INDUSTRY_CODE}' is applied first, to the full concatenated "
        f"slice frame of {n_quarters_loaded} distinct year-quarters as loaded from Task 2's "
        f"recorded slice CSVs, before any other split; {n_quarters} of those "
        f"{n_quarters_loaded} loaded quarters carry at least one {c.INDUSTRY_CODE} row, and "
        "every per-quarter count quoted elsewhere in these notes names which of the two it "
        f"means. own_code == '{private_own}' (title 'Private', from the fetched ownership "
        "titles file) is applied next, restricting to private ownership; the national/"
        "state-like geography split comes last, so both sides of it are sub-frames of the "
        "already industry- and ownership-filtered frame. National rows are area_fips == "
        "'US000'; state-like rows are area_fips.str.ends_with('000') and area_fips != 'US000'."
    )
    title_evidence_note = (
        "Title evidence for 'same industry detail': fetched agglvl_code titles give national "
        f"{_agglvl_title_list(nat_agglvl, maps['agglvl_code'])} and state "
        f"{_agglvl_title_list(st_agglvl, maps['agglvl_code'])}; {detail_outcome}, so the "
        f"same-industry-detail conjunct of aligned above is {same_detail} (see "
        "_same_industry_detail). This defends against a titles-metadata inconsistency between "
        "the two geography levels' fetched titles; it is not independent discriminating power, "
        "because digit-depth and ownership breakout are already pinned upstream by the queried "
        f"industry_code and the own_code filter. {observed_detail_sentence}"
    )
    naics_vintage_note = (
        "NAICS vintage sourcing (Step 3). One part of this is derived and the rest is "
        f"hand-authored; both are labelled as such. Derived: {industry_title_sentence} Either "
        "way that settles only the current vintage, never the per-year history: QCEW publishes "
        "no per-row NAICS-vintage column and the titles file reflects only the current "
        "vintage, so naics_vintage_by_year above cannot be computed from anything this script "
        "fetches. Everything from here to the end of this note is hand-authored -- the "
        "quotations, the premises drawn on alongside them, and the conclusions that need both, "
        "equally. This script fetches none of it, so none of it carries an extract hash and no "
        "later run re-checks any of it. Quoted verbatim from two BLS classification pages: "
        "https://www.bls.gov/cew/classifications/industry/naics-2017.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) with the release of first "
        "quarter 2017 Quarterly Census of Employment and Wages (QCEW) data.' "
        "https://www.bls.gov/cew/classifications/industry/naics-2022.htm: 'This revision will "
        "be introduced by the Bureau of Labor Statistics (BLS) on September 7, 2022, with the "
        "full data release of first quarter 2022 Quarterly Census of Employment and Wages "
        "(QCEW) data.' Unquoted premise, and the load-bearing one: QCEW does not retabulate "
        "prior reference years onto a new NAICS vintage. The two quotations establish only the "
        "quarter at which each vintage is introduced; without that premise they say nothing "
        "about what vintage 2017-2021 data carry today, and the entire per-year "
        "naics_vintage_by_year mapping rests on it. It is supplied by hand, is carried by "
        "neither quotation and by no other source cited in this note, and is the single claim "
        "here a later task should re-source first. Granting it, the switch is a hard boundary "
        "at reference year 2022, giving the clean per-year split recorded above. Also "
        "hand-checked out-of-band, against the local classification-codes skill's derived "
        "NAICS data rather than against anything fetched here, and reported with its two "
        f"caveats. That skill's concordance CSVs pair {c.INDUSTRY_CODE} to itself with the "
        "title 'Logging' unchanged in both the 2012-to-2017 and the 2017-to-2022 direction, "
        f"and its NAICS structure CSVs carry an empty change_indicator on {c.INDUSTRY_CODE} in "
        "all three of the 2012, 2017 and 2022 vintages, which that skill documents as meaning "
        "unchanged from the prior vintage at that level. Caveat one: the concordance link_type "
        "of 1:1 is not a Census column. Census ships four columns -- source code, source title, "
        "target code, target title -- flags partial flows by cell formatting the parse "
        "discards, and publishes no allocation weights; link_type is derived by that skill "
        "from code multiplicities after deduplication. Caveat two, following from the first: "
        f"1:1 establishes only that {c.INDUSTRY_CODE} neither split nor merged in the "
        "six-digit code pairing, which is not a statement about the industry's definitional "
        "content. It is the unchanged title and the empty structure-file change_indicator, not "
        "the 1:1, that carry the continuity claim, and even they are titles and markers rather "
        "than a comparison of the two vintages' definitional text."
    )

    notes = " ".join([
        filter_predicates_note,
        title_evidence_note,
        _geography_universe_note(
            n_quarters, state_like_areas, extraneous_detail, dc_detail, nat_agglvl
        ),
        naics_vintage_note,
    ])

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(c.WINDOW_YEARS)), "published_end": str(max(c.WINDOW_YEARS)),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": f"{min(c.WINDOW_YEARS)}-{max(c.WINDOW_YEARS)}", "uncovered": "",
        },
        access={"route": "https://data.bls.gov/cew/doc/titles/<dimension>/",
                "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "titles_available": TITLES,
            "codes_present": codes_present,
            "private_own_code": private_own,
            "national_agglvl": [{"code": a, "title": maps["agglvl_code"].get(a)}
                                for a in nat_agglvl],
            "state_agglvl": [{"code": a, "title": maps["agglvl_code"].get(a)}
                             for a in st_agglvl],
            "size_code_values": codes_present["size_code"],
            "alignment_srcqcew007": {
                "national_agglvl": nat_agglvl,
                "state_agglvl": st_agglvl,
                "own_code": private_own,
                "industry_code": c.INDUSTRY_CODE,
                "naics_vintage_by_year": naics_vintage,
                "period_basis": "quarterly file, three monthly employment columns "
                                "(month1/2/3_emplvl), pay period including the 12th",
                "aligned": aligned,
                "notes": notes,
            },
        },
    )
    print(f"private own_code={private_own}; national agglvl={nat_agglvl}; "
          f"state agglvl={st_agglvl}; aligned={aligned}")


if __name__ == "__main__":
    main()
```

> `naics_vintage_by_year` ships as `"unconfirmed"` for every year and must be filled by hand.
> QCEW is documented as switching to NAICS 2022 beginning with 2022 data; confirm the switch
> year against the fetched `industry_titles.csv` and the QCEW classification documentation, then
> replace each year's value with the vintage you confirmed. Leave `"unconfirmed"` and say why in
> `notes` where the check is inconclusive — Stage 1 owns the mechanical crosswalk test, and it
> needs to know which years are actually established.

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/qcew_codes.py
```

Expected: one stdout line of the form `private own_code=<code>; national agglvl=[<code>];
state agglvl=[<code>]; aligned=<bool>`. If the script raises on the `'Private'` title lookup,
the ownership titles file changed shape — inspect
`data/raw/audit/qcew_codes/titles/own_code.csv` and fix the parse, never the constant.

- [ ] **Step 3: Fill `naics_vintage_by_year` by hand**

The script ships every window year as `"unconfirmed"`: QCEW publishes no per-row NAICS-vintage
column, so the vintage is a documentation fact, not a derivable one. Confirm the switch year
against the fetched `data/raw/audit/qcew_codes/titles/industry_titles.csv` and the QCEW
classification documentation, then edit the `naics_vintage` dict comprehension in
`qcew_codes.py` into an explicit per-year literal carrying what you confirmed, and re-run
Step 2 so the summary is regenerated from it.

Where the check is inconclusive for a year, leave that year `"unconfirmed"` **and say why** in
the sibling `notes` field. An `"unconfirmed"` with a stated reason is a legitimate finding; an
`"unconfirmed"` left behind by a skipped step is not, and Step 4 fails it. Stage 1 owns the
mechanical crosswalk test and needs to know which years are actually established.

- [ ] **Step 4: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/qcew_codes/summary.json"))["findings"]
for dim in ("agglvl_code", "own_code", "size_code", "disclosure_code"):
    assert f["codes_present"][dim], f"{dim}: no codes observed on 113310 rows"
    print(dim, "->", [(d["code"], d["title"], d["row_count"]) for d in f["codes_present"][dim]])
assert f["titles_available"]["disclosure_code"] is None
a = f["alignment_srcqcew007"]
assert len(a["national_agglvl"]) == 1 and len(a["state_agglvl"]) == 1, \
    "more than one aggregation level per geography level — resolve before Stage 2"
v = a["naics_vintage_by_year"]
assert set(v) == {str(y) for y in range(2017, 2025)}, "every window year must appear"
assert not (any(x == "unconfirmed" for x in v.values()) and not a["notes"].strip()), \
    "an unconfirmed NAICS vintage needs a notes entry saying why it was inconclusive"
print("NAICS vintage by year:", v)
print("SRC-QCEW-007 aligned:", a["aligned"])
PY
```

Expected: four non-empty code lists print with titles (`disclosure_code` titles print as
`None`); the two aggregation-level assertions hold; `aligned` prints as a boolean. If more than
one aggregation level appears at either geography level, that is a **finding that must be
written up**, not a bug — record the codes and set `aligned: false` with an explanatory `notes`.

- [ ] **Step 5: Commit**

```bash
git add scripts/audit/qcew_codes.py
git commit -m "feat(audit): inventory QCEW codes on 113310 rows and state the SRC-QCEW-007 alignment"
```

---

### Task 4: The 113310 private state/national panel and the suppression share

Closes: the roadmap's *"state × month suppression share for 113310 private ownership"*, which
sizes Stage 4's pseudo-suppression mask design. Also produces the panel Task 5 judges.

**Files:**
- Create: `scripts/audit/qcew_panel.py`

**Interfaces:**
- Consumes: `_common`; `load_summary("qcew_routes")` for slice paths;
  `load_summary("qcew_codes")["findings"]["private_own_code"]`.
- Produces: `data/raw/audit/qcew_panel/panel.parquet` registered through `record_extract` with
  the URL `derived://qcew_routes/slices` so Task 13's verifier re-hashes it like any other
  extract, plus `data/raw/audit/qcew_panel/summary.json` (source key `qcew_panel`).
  Panel schema — one row per `(area_fips, year, month)`:
  `area_fips: str, area_title: str, area_class: str, year: int, qtr: int, month: int,
  emplvl: int | null, qtrly_estabs: int | null, disclosure_code: str, suppressed: bool`.
  `area_class` is one of `national`, `states_dc`, `other_state_level`.
  `emplvl` is **null when `suppressed` is true** — INV-003: a value paired with a suppression
  code is never read as a true zero.
  `findings` keys:
  - `filter_predicates` — the exact predicates applied, recorded because the raw files were
    stored unfiltered.
  - `panel_rows`, `months_covered`, `states_covered`.
  - `other_state_level_areas` — list of `{area_fips, area_title}` for every non-national
    `*000` area present that is **not** in the states+DC universe. Enumerated from the data,
    not assumed.
  - `suppression_share_overall` — float, suppressed state-month cells ÷ all state-month cells.
  - `suppression_share_by_state` — mapping `area_fips` → float.
  - `suppression_share_by_month` — mapping `YYYY-MM` → float.
  - `suppressed_run_lengths` — histogram `{run_length: count}` of consecutive suppressed months
    per state; Stage 4's §13.3 "long runs" regime is sized from this.
  - `estabs_survive_suppression_share` — float: of suppressed state-month rows, the fraction
    whose `qtrly_estabs` is greater than zero. §2.2 row 2 says establishment counts may remain
    available when employment is suppressed; Task 5's universe test depends on it being true,
    so it is measured rather than assumed.

- [ ] **Step 1: Write the failing panel-flag test**

Create `tests/audit/test_panel_flags.py`. This test exists because the natural expression
`pl.col("disclosure_code").str.strip_chars() == "N"` yields **null**, not `False`, wherever the
column is empty — and a null `suppressed` is silently dropped from every `.mean()` denominator,
which would report a suppression share of `1.0` for any state that has any suppression at all.

```python
import polars as pl

from qcew_panel import build_panel


def write_fixture(tmp_path, monkeypatch):
    """Two states over one quarter: one clean row, one suppressed row, one county row."""
    import json

    import _common as c

    monkeypatch.setattr(c, "AUDIT_ROOT", tmp_path)
    header = ("area_fips,own_code,industry_code,agglvl_code,size_code,year,qtr,"
              "disclosure_code,qtrly_estabs,month1_emplvl,month2_emplvl,month3_emplvl")
    rows = [
        'US000,5,113310,18,0,2017,1,,100,1000,1000,1000',
        '01000,5,113310,58,0,2017,1,,40,400,400,400',
        '41000,5,113310,58,0,2017,1,N,50,0,0,0',
        '01001,5,113310,78,0,2017,1,N,3,0,0,0',
    ]
    slice_csv = tmp_path / "qcew_routes" / "slices" / "2017q1.csv"
    slice_csv.parent.mkdir(parents=True, exist_ok=True)
    slice_csv.write_text(header + "\n" + "\n".join(rows) + "\n")
    titles = tmp_path / "qcew_codes" / "titles" / "area_fips.csv"
    titles.parent.mkdir(parents=True, exist_ok=True)
    titles.write_text('area_fips,area_title\nUS000,U.S. TOTAL\n01000,Alabama\n41000,Oregon\n')

    def summary(name, extract_path, findings):
        payload = {
            "source": name, "generated_utc": "x",
            "coverage_span": {k: "" for k in c.COVERAGE_KEYS},
            "access": {"route": "r", "status": "verified", "reason": None},
            "extracts": [{"source": name, "url": "u", "path": str(extract_path),
                          "sha256": "0", "bytes": 1, "retrieved_utc": "x",
                          "http_status": 200}],
            "findings": findings,
        }
        (tmp_path / name / "summary.json").write_text(json.dumps(payload))

    summary("qcew_routes", slice_csv, {})
    summary("qcew_codes", titles, {"private_own_code": "5"})


def test_suppressed_is_boolean_never_null(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    panel = build_panel("5")
    assert panel["suppressed"].null_count() == 0, \
        "a null `suppressed` is dropped from every .mean() denominator"
    assert panel["suppressed"].dtype == pl.Boolean


def test_suppression_share_uses_the_full_denominator(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    states = build_panel("5").filter(pl.col("area_class") == "states_dc")
    assert states.height == 6  # two states x three months
    assert float(states["suppressed"].mean()) == 0.5


def test_suppressed_employment_is_null_not_zero(tmp_path, monkeypatch):
    """INV-003: a value paired with a suppression code is never a true zero."""
    write_fixture(tmp_path, monkeypatch)
    panel = build_panel("5")
    assert panel.filter(pl.col("area_fips") == "41000")["emplvl"].null_count() == 3
    assert panel.filter(pl.col("area_fips") == "01000")["emplvl"].to_list() == [400, 400, 400]


def test_sub_state_rows_are_excluded(tmp_path, monkeypatch):
    write_fixture(tmp_path, monkeypatch)
    assert build_panel("5").filter(pl.col("area_fips") == "01001").height == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_panel_flags.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'qcew_panel'`.

- [ ] **Step 3: Write the script**

Create `scripts/audit/qcew_panel.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Build the 113310 private state/national monthly panel and measure the suppression share.

Reads nothing from the network: every input is an extract another audit script already
recorded (Task 2's slice CSVs, Task 3's fetched titles and derived `private_own_code`), so the
panel is reproducible from the artifacts on disk. The panel itself is registered through
`record_extract` under a `derived://` URL, which is why it re-hashes like any fetched file.

This script measures. It records no verdict on any SRC-QCEW finding: the geography and
suppression counts below state what the retained rows contain, and nothing about what they
imply for a national identity.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from itertools import pairwise
from typing import Any

import polars as pl

import _common as c

SOURCE = "qcew_panel"

# STATES_DC_FIPS / STATE_AREAS / NATIONAL_AREA come from _common (Task 1) — shared, not
# re-declared, because audit scripts do not import one another except through summaries.

# The `*000` suffix is what makes an area_fips national or state-level rather than a county or
# an MSA; named once so the predicate string in `filter_predicates` cannot drift from the
# predicate that was actually applied.
AREA_SUFFIX = "000"
SUPPRESSION_CODE = "N"

# The panel key. `_conform` enforces it, because every share below divides by a count of
# these cells and a duplicate would inflate that denominator silently.
PANEL_KEY = ("area_fips", "year", "month")

# "This cell kept a published establishment count." fill_null before comparing: a null
# qtrly_estabs is otherwise dropped from a .mean() denominator instead of counting as
# "not > 0" (the same hazard as `suppressed`). Written once so the three readings of it
# -- the per-code tally, estabs_survival and the note -- cannot drift apart.
ESTABS_PRESENT = pl.col("qtrly_estabs").fill_null(0) > 0

# The panel contract Task 5 reads. Enforced on the frame before it is serialized (see
# `_conform`), so a renamed column or a narrowed integer fails here rather than downstream.
PANEL_SCHEMA: dict[str, pl.DataType] = {
    "area_fips": pl.String,
    "area_title": pl.String,
    "area_class": pl.String,
    "year": pl.Int32,
    "qtr": pl.Int8,
    "month": pl.Int8,
    "emplvl": pl.Int64,
    "qtrly_estabs": pl.Int64,
    "disclosure_code": pl.String,
    "suppressed": pl.Boolean,
}


def area_titles() -> dict[str, str]:
    path = next(e["path"] for e in c.load_summary("qcew_codes")["extracts"]
                if e["path"].endswith("titles/area_fips.csv"))
    df = pl.read_csv(path, infer_schema_length=0)
    return dict(zip(df[df.columns[0]].to_list(), df[df.columns[1]].to_list(), strict=True))


def slice_paths() -> list[str]:
    """Task 2 recorded 32 quarterly slice CSVs and, alongside them, a bulk ZIP it fetched to
    compare headers. Only the CSVs are panel input; the ZIP is a different file format and a
    different column vocabulary (`qtrly_estabs_count`, not `qtrly_estabs`)."""
    return [e["path"] for e in c.load_summary("qcew_routes")["extracts"]
            if e["path"].endswith(".csv")]


def predicate_exprs(own_code: str) -> list[tuple[str, pl.Expr]]:
    """The filters this script applies, paired with the text recorded for each one.

    Global Constraints require every predicate to be recorded in the summary because the raw
    files were stored unfiltered. Pairing the text with the expression here is what keeps the
    recorded predicate and the applied predicate the same object.
    """
    return [
        (f"industry_code == '{c.INDUSTRY_CODE}'",
         pl.col("industry_code") == c.INDUSTRY_CODE),
        (f"own_code == '{own_code}' (qcew_codes.findings.private_own_code)",
         pl.col("own_code") == own_code),
        (f"area_fips.str.ends_with('{AREA_SUFFIX}')",
         pl.col("area_fips").str.ends_with(AREA_SUFFIX)),
    ]


def apply_predicates(raw: pl.DataFrame, own_code: str) -> tuple[pl.DataFrame, list[str]]:
    """Filter in the listed order, annotating each predicate with what it retained."""
    df, before, recorded = raw, raw.height, []
    for label, expr in predicate_exprs(own_code):
        df = df.filter(expr)
        recorded.append(f"{label}; retained {df.height} of {before} rows")
        before = df.height
    return df, recorded


def _conform(long: pl.DataFrame) -> pl.DataFrame:
    """Project onto PANEL_SCHEMA — column order included — and refuse anything else.

    "Anything else" includes a repeated `PANEL_KEY`. Nothing upstream guarantees one row per
    (area_fips, year, month): the predicates filter on industry, ownership and the area suffix
    only, so uniqueness rests on the source's shape. A duplicated area-quarter would inflate
    the suppression share's denominator — a count of rows — while `absent_months_by_area`,
    which counts distinct months, went on reporting that area as complete, and every derived
    sentence in the summary would still read as self-consistent. That silent failure lands on
    the headline number, so it is refused here rather than reported.
    """
    panel = long.select(*PANEL_SCHEMA)
    if list(panel.schema.items()) != list(PANEL_SCHEMA.items()):
        raise RuntimeError(f"panel schema {dict(panel.schema)} != {PANEL_SCHEMA}")
    repeated = panel.group_by(PANEL_KEY).len().filter(pl.col("len") > 1).sort(PANEL_KEY)
    if repeated.height:
        raise RuntimeError(
            f"panel key {PANEL_KEY} is not unique: {repeated.height} repeated key(s), "
            f"first {repeated.head(3).to_dicts()}"
        )
    return panel


def build_long(own_code: str) -> tuple[pl.DataFrame, list[str]]:
    """The monthly frame before `_conform` projects it onto PANEL_SCHEMA.

    Kept separate because `emplvl_raw` — what the source published in the month columns,
    before INV-003 nulls it out on a suppressed row — exists only here, and
    `disclosure_code_values` has to measure it to report it.
    """
    raw = pl.concat([pl.read_csv(p, infer_schema_length=0) for p in slice_paths()],
                    how="vertical")
    titles = area_titles()
    df, recorded = apply_predicates(raw, own_code)

    long = (
        df.unpivot(
            index=["area_fips", "year", "qtr", "disclosure_code", "qtrly_estabs"],
            on=["month1_emplvl", "month2_emplvl", "month3_emplvl"],
            variable_name="month_col", value_name="emplvl_raw",
        )
        .with_columns(
            year=pl.col("year").cast(pl.Int32),
            qtr=pl.col("qtr").cast(pl.Int8),
            month_in_qtr=pl.col("month_col").str.extract(r"month(\d)_emplvl").cast(pl.Int8),
            qtrly_estabs=pl.col("qtrly_estabs").cast(pl.Int64),
            # fill_null before comparing: `null == "N"` is null in polars, and a null
            # `suppressed` would be dropped from every .mean() denominator below.
            suppressed=pl.col("disclosure_code").fill_null("").str.strip_chars()
            == SUPPRESSION_CODE,
        )
        .with_columns(month=(pl.col("qtr") - 1) * 3 + pl.col("month_in_qtr"))
        .with_columns(
            # INV-003: a value paired with a suppression code is never a true zero.
            emplvl=pl.when(pl.col("suppressed")).then(None)
            .otherwise(pl.col("emplvl_raw").cast(pl.Int64)),
            area_class=pl.when(pl.col("area_fips") == c.NATIONAL_AREA).then(pl.lit("national"))
            .when(pl.col("area_fips").is_in(sorted(c.STATE_AREAS))).then(pl.lit("states_dc"))
            .otherwise(pl.lit("other_state_level")),
            area_title=pl.col("area_fips").replace_strict(titles, default=""),
        )
        .sort("area_fips", "year", "month")
    )
    return long, recorded


def build_panel(own_code: str) -> pl.DataFrame:
    return _conform(build_long(own_code)[0])


def month_index(year: int, month: int) -> int:
    """Months since year 0 — a single ordinal so adjacency survives a year boundary."""
    return year * 12 + month


def run_lengths(months: Sequence[int], flags: Sequence[bool]) -> list[int]:
    """Maximal runs of consecutive suppressed months, over `month_index` values.

    A run ends at an unsuppressed month and equally at an absent one: two suppressed spans
    either side of a month with no published row are two runs, because the panel says nothing
    about the months in between. Stage 4's §13.3 "long runs" regime is sized from this
    histogram, so a merged run would overstate it.
    """
    runs: list[int] = []
    current = 0
    previous: int | None = None
    for month, flag in zip(months, flags, strict=True):
        contiguous = previous is not None and month == previous + 1
        if current and not contiguous:
            runs.append(current)
            current = 0
        if flag:
            current += 1
        elif current:
            runs.append(current)
            current = 0
        previous = month
    if current:
        runs.append(current)
    return runs


def _state_runs(states: pl.DataFrame) -> tuple[dict[int, int], int]:
    """Run-length histogram over states_dc areas, plus the count of interior month gaps."""
    hist: dict[int, int] = {}
    gaps = 0
    ordered = states.sort("year", "month")
    for _key, group in ordered.group_by(["area_fips"], maintain_order=True):
        grp = group.sort("year", "month")
        months = [month_index(y, m) for y, m in zip(grp["year"], grp["month"], strict=True)]
        gaps += sum(1 for a, b in pairwise(months) if b != a + 1)
        for length in run_lengths(months, grp["suppressed"].to_list()):
            hist[length] = hist.get(length, 0) + 1
    return hist, gaps


def disclosure_code_values(long: pl.DataFrame) -> list[dict[str, Any]]:
    """What the published disclosure_code column actually carries on the retained rows.

    Takes the pre-`_conform` frame so `emplvl_raw` is still present: `emplvl_raw_nonzero_rows`
    counts what the source published in the month columns *before* INV-003 nulls it out, and
    `emplvl_published_nonzero_rows` counts what survives into the panel. Without the first of
    those, the note's claim about what a suppressed row publishes would be untestable — and a
    nonzero employment level published under a suppression code would surface here instead of
    disappearing into the null-out.

    §2.2 row 1 forbids encoding any numerical confidentiality threshold, so the suppression
    flag is the published code and nothing else. Enumerating every observed value — with what
    each one carries in the employment and establishment columns — is what makes the
    `== 'N'` predicate auditable instead of asserted.
    """
    return (
        long.group_by(pl.col("disclosure_code").fill_null("").str.strip_chars())
        .agg(
            panel_rows=pl.len(),
            states_dc_rows=(pl.col("area_class") == "states_dc").sum(),
            emplvl_raw_nonzero_rows=(
                pl.col("emplvl_raw").cast(pl.Int64, strict=False).fill_null(0) != 0
            ).sum(),
            emplvl_published_rows=pl.col("emplvl").is_not_null().sum(),
            emplvl_published_nonzero_rows=(pl.col("emplvl") > 0).sum(),
            qtrly_estabs_positive_rows=ESTABS_PRESENT.sum(),
        )
        .sort("disclosure_code")
        .to_dicts()
    )


def estabs_survival(supp_rows: pl.DataFrame) -> float | None:
    """Fraction of suppressed cells whose `qtrly_estabs` is above zero, or None if there are
    none to measure.

    §2.2 row 2 says establishment counts may remain available when employment is suppressed,
    and Task 5's universe test depends on it, so it is measured rather than assumed. `None`
    rather than `0.0` on an empty frame for the same reason `suppression_share_overall` is:
    0.0 is the measurable result "no suppressed cell kept its establishment count", and a
    panel with nothing suppressed must not be reported as having produced it.
    """
    if not supp_rows.height:
        return None
    return float(supp_rows.select(ESTABS_PRESENT).to_series().mean())


def cell_coverage(states: pl.DataFrame, interior_month_gaps: int) -> dict[str, Any]:
    """How many states_dc monthly cells the shares are actually divided by.

    The shares below have a denominator of cells present in the panel, not of a full
    universe x window grid: an area with no published row for a month contributes to neither
    numerator nor denominator. This records the difference so the headline share is readable.

    `interior_month_gaps` is computed by `_state_runs`, in the same traversal that builds the
    run-length histogram, because it is the evidence that no run in that histogram spans an
    absence. It is recorded here, next to the rest of the coverage arithmetic, so a consumer
    reads it as a number rather than parsing it out of the note.
    """
    window_months = len(c.WINDOW_YEARS) * 12
    # Distinct months, not row count: an area's absent-month arithmetic must not depend on
    # `_conform`'s key check having run, even though it makes the two the same.
    present = dict(states.group_by("area_fips")
                   .agg(pl.struct("year", "month").n_unique())
                   .sort("area_fips").iter_rows())
    absent = {area: window_months - present.get(area, 0)
              for area in sorted(c.STATE_AREAS) if present.get(area, 0) < window_months}
    return {
        # The share's actual denominator, so a row count by construction.
        "cells_present": states.height,
        "grid_areas": len(c.STATE_AREAS),
        "grid_months": window_months,
        "grid_cells": len(c.STATE_AREAS) * window_months,
        "absent_months_by_area": absent,
        "areas_with_no_rows": sorted(a for a in c.STATE_AREAS if a not in present),
        "interior_month_gaps": interior_month_gaps,
    }


def notes(
    *,
    panel: pl.DataFrame,
    states: pl.DataFrame,
    supp_rows: pl.DataFrame,
    codes: list[dict[str, Any]],
    coverage: dict[str, Any],
    others: list[dict[str, str]],
    titles_available: dict[str, Any],
) -> str:
    """Every sentence here is interpolated from this run's frames; a re-run against revised
    data restates it rather than repeating it."""
    by_class = dict(panel.group_by("area_class").len().sort("area_class").iter_rows())
    code_counts = ", ".join(
        f"{row['disclosure_code']!r} on {row['panel_rows']} monthly rows "
        f"({row['states_dc_rows']} states_dc, {row['qtrly_estabs_positive_rows']} with "
        f"qtrly_estabs > 0, {row['emplvl_raw_nonzero_rows']} with a nonzero employment level "
        f"in the source month columns, {row['emplvl_published_nonzero_rows']} with one "
        f"published into the panel)"
        for row in codes
    )
    other_desc = ", ".join(
        f"{row['area_fips']} ({row['area_title']})" for row in others
    ) or "none"
    missing = coverage["areas_with_no_rows"]
    partial = {a: n for a, n in coverage["absent_months_by_area"].items() if a not in missing}
    return (
        f"Panel construction. {len(slice_paths())} recorded slice CSVs contribute the raw "
        f"frame; the predicates in filter_predicates are applied to it in the order listed "
        f"there, each one recording what it retained, and the surviving quarterly rows "
        f"unpivot to {panel.height} monthly rows "
        f"({', '.join(f'{n} {cls}' for cls, n in by_class.items())}). "
        f"Suppression flag. `suppressed` is true where the published disclosure_code strips "
        f"to {SUPPRESSION_CODE!r}, and false for every other value, including an empty one: "
        f"the flag is the published code alone, and no cell-count or concentration threshold "
        f"enters it (Global Constraints, §2.2 row 1). qcew_codes.findings.titles_available "
        f"records the published titles file for this column as "
        f"{titles_available.get('disclosure_code')!r}. Values observed on the retained rows, "
        f"with what each carries: {code_counts}. Employment on a suppressed row is written "
        f"null in the panel (INV-003), so of the two counts above, "
        f"emplvl_raw_nonzero_rows is taken before that null-out and "
        f"emplvl_published_nonzero_rows after it; the difference between those two per code "
        f"is measured here, not assumed from what a suppressed row is expected to publish. "
        f"Denominator. suppression_share_overall, _by_state and _by_month divide by the "
        f"{coverage['cells_present']} states_dc monthly cells present in the panel, not by "
        f"the {coverage['grid_cells']} cells of a {coverage['grid_areas']}-area x "
        f"{coverage['grid_months']}-month grid; state_month_cell_coverage decomposes the "
        f"difference. states_dc areas with no retained row in any quarter: {len(missing)} "
        f"({', '.join(missing) or 'none'}). states_dc areas with rows for part of the window "
        f"only: {len(partial)} "
        f"({'; '.join(f'{a}: {n} months absent' for a, n in partial.items()) or 'none'}). "
        f"A per-state share for any of those areas is over the months it publishes. "
        f"Run lengths. suppressed_run_lengths counts maximal runs of consecutive suppressed "
        f"months within one states_dc area, where a run ends at an unsuppressed month and "
        f"equally at an absent one. Counted across the states_dc areas over the "
        f"{coverage['grid_months']}-month window, the number of interior month gaps falling "
        f"inside an area's own span of published rows is "
        f"{coverage['interior_month_gaps']} (state_month_cell_coverage.interior_month_gaps). "
        f"Establishment survival. estabs_survive_suppression_share is measured over the "
        f"{supp_rows.height} suppressed states_dc monthly cells, of which "
        f"{int(supp_rows.select(ESTABS_PRESENT).to_series().sum())} report "
        f"qtrly_estabs > 0. "
        f"Geography. states_covered counts the distinct states_dc area codes present, "
        f"{states['area_fips'].n_unique()} of the {len(c.STATE_AREAS)} in _common.STATE_AREAS; "
        f"other_state_level_areas enumerates every non-national area ending "
        f"'{AREA_SUFFIX}' that is outside that set: {other_desc}. This script draws no "
        f"conclusion from either count about the composition of the "
        f"{c.NATIONAL_AREA} national total."
    )


def main() -> None:
    own_code = c.load_summary("qcew_codes")["findings"]["private_own_code"]
    long, predicates = build_long(own_code)
    panel = _conform(long)

    states = panel.filter(pl.col("area_class") == "states_dc")
    n_cells = states.height
    n_suppressed = int(states["suppressed"].sum())

    by_state = (states.group_by("area_fips")
                .agg(share=pl.col("suppressed").mean()).sort("area_fips"))
    by_month = (states.with_columns(
                    ym=pl.format("{}-{}", pl.col("year"),
                                 pl.col("month").cast(pl.Utf8).str.zfill(2)))
                .group_by("ym").agg(share=pl.col("suppressed").mean()).sort("ym"))

    hist, interior_gaps = _state_runs(states)

    supp_rows = states.filter(pl.col("suppressed"))
    estabs_survive = estabs_survival(supp_rows)

    others = (panel.filter(pl.col("area_class") == "other_state_level")
              .select("area_fips", "area_title").unique().sort("area_fips").to_dicts())
    codes = disclosure_code_values(long)
    coverage = cell_coverage(states, interior_gaps)

    window_months = {(y, m) for y in c.WINDOW_YEARS for m in range(1, 13)}
    covered_months = set(panel.select("year", "month").unique().iter_rows())
    uncovered = ", ".join(f"{y}-{m:02d}" for y, m in sorted(window_months - covered_months))
    # Derived from the months the panel holds, not from its years: QCEW publishes quarter by
    # quarter, so a run whose last quarter is 2025q2 must not report a December end date.
    first_month, last_month = min(covered_months), max(covered_months)

    buf = io.BytesIO()
    panel.write_parquet(buf)
    rec = c.record_extract(SOURCE, "derived://qcew_routes/slices", "panel.parquet",
                           buf.getvalue())

    span_start, span_end = (f"{y}-{m:02d}" for y, m in (first_month, last_month))
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": span_start, "published_end": span_end,
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": f"{span_start}..{span_end}", "uncovered": uncovered,
        },
        access={"route": "derived from qcew_routes slice extracts", "status": "verified",
                "reason": None},
        extracts=[rec],
        findings={
            "filter_predicates": predicates,
            "panel_rows": panel.height,
            "months_covered": states.select("year", "month").unique().height,
            "states_covered": states["area_fips"].n_unique(),
            "other_state_level_areas": others,
            "suppression_share_overall": n_suppressed / n_cells if n_cells else None,
            "suppression_share_by_state": dict(
                zip(by_state["area_fips"].to_list(), by_state["share"].to_list(), strict=True)),
            "suppression_share_by_month": dict(
                zip(by_month["ym"].to_list(), by_month["share"].to_list(), strict=True)),
            "suppressed_run_lengths": {str(k): v for k, v in sorted(hist.items())},
            "estabs_survive_suppression_share": estabs_survive,
            "disclosure_code_values": codes,
            "state_month_cell_coverage": coverage,
            "notes": notes(
                panel=panel, states=states, supp_rows=supp_rows, codes=codes,
                coverage=coverage, others=others,
                titles_available=c.load_summary("qcew_codes")["findings"]["titles_available"],
            ),
        },
    )
    print(f"panel rows={panel.height}; states={states['area_fips'].n_unique()}; "
          f"suppressed share={n_suppressed / n_cells if n_cells else 'n/a'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_panel_flags.py -q
```

Expected: PASS — 4 passed.

- [ ] **Step 5: Run it on the real extracts**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/qcew_panel.py
```

Expected: one stdout line `panel rows=<int>; states=<int>; suppressed share=<float>`.

- [ ] **Step 6: Verify the panel's shape**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/qcew_panel/summary.json"))["findings"]
assert f["months_covered"] == 96, f"expected 96 months in the D1 window, got {f['months_covered']}"
assert 0.0 <= f["suppression_share_overall"] <= 1.0
cov = f["state_month_cell_coverage"]
print("states covered:", f["states_covered"], "of", cov["grid_areas"], "states+DC")
print("states+DC publishing no rows at all:", cov["areas_with_no_rows"])
print("suppression share:", round(f["suppression_share_overall"], 4))
print("non-state *000 areas present:", f["other_state_level_areas"])
print("run-length histogram:", f["suppressed_run_lengths"])
print("estabs survive suppression:", round(f["estabs_survive_suppression_share"], 4))
PY
```

Expected: the assertions hold and the values print. `states_covered` is deliberately **not**
asserted to equal 51. It counts the states+DC areas that actually publish private 113310 rows,
and the District of Columbia publishes none in any window quarter — so 50 is the correct result
on this data, and `areas_with_no_rows` enumerates which areas are absent. Fetch completeness is
carried by `months_covered == 96` and an empty `coverage_span.uncovered`: a window year the slice
route failed to serve shows up there, as missing months, not as a missing state.

- [ ] **Step 7: Commit**

```bash
git add scripts/audit/qcew_panel.py tests/audit/test_panel_flags.py
git commit -m "feat(audit): build the 113310 private panel and measure the suppression share"
```

---

### Task 5: The SRC-QCEW-006 national-identity branch verdict

Closes: `SRC-QCEW-006`'s branch verdict — the roadmap's single highest-stakes Stage 0 output.
§8.1 states the requirement: *"It MUST verify the state/national universe each month. If the
national total includes areas outside the configured state universe, the system must add
explicit residual cells or decline to enforce the national identity."* Stage 3's entire
baseline family (§10.1–10.6, §12.2) allocates a residual against a national total, so a
`decline` verdict changes Stage 3's allocation target and forces its plan to name a substitute
anchor before any baseline is written.

**The rule is written and tested before the scan runs.** Scanning first and reasoning second
produces a rationalisation for whichever verdict the data suggests; the steps below are ordered
to make that impossible.

**Files:**
- Create: `scripts/audit/qcew_identity.py`
- Test: `tests/audit/test_identity_rule.py`

**Interfaces:**
- Consumes: `_common`; `data/raw/audit/qcew_panel/panel.parquet` (Task 4).
- Produces: `classify_identity(quarters: pl.DataFrame, months: pl.DataFrame) -> dict` in
  `qcew_identity.py`, returning `{"branch": str, "reason": str, "evidence": dict}` where
  `branch` is exactly one of `enforce`, `residual_cells`, `decline`.
  `data/raw/audit/qcew_identity/summary.json` (source key `qcew_identity`) with `findings`:
  - `quarter_table` — one row per `(year, qtr)`:
    `national_estabs, states_dc_estabs, other_estabs, estab_gap, estab_gap_after_other`.
  - `month_table` — one row per `(year, month)`:
    `national_emp, states_dc_emp, other_emp, emp_gap, emp_gap_after_other,
    n_states_suppressed`.
  - `branch` — `enforce` | `residual_cells` | `decline`.
  - `verdict_sentence` — the one-sentence verdict required by the stage exit criterion.
  - `geography_universe_explains_gap` — bool.
  - `clean_months` — count of months with zero suppressed state cells.

**Why establishment counts carry the universe test.** §2.2 row 2: establishment counts may
remain available even when employment and wage fields are suppressed, and Task 4 measures
exactly how often that holds. So `qtrly_estabs` answers *"does the state universe exhaust the
national universe?"* with little interference from suppression, and the employment columns are
then free to answer *"how much is suppression hiding?"* That ordering is what the roadmap means
by testing the geography universe **before** suppression is blamed.

- [ ] **Step 1: Write the failing rule test**

Create `tests/audit/test_identity_rule.py`:

```python
import polars as pl
import pytest

from qcew_identity import classify_identity


def quarters(rows):
    return pl.DataFrame(
        rows,
        schema={"year": pl.Int32, "qtr": pl.Int8, "national_estabs": pl.Int64,
                "states_dc_estabs": pl.Int64, "other_estabs": pl.Int64,
                "estab_gap": pl.Int64, "estab_gap_after_other": pl.Int64},
        orient="row",
    )


def months(rows):
    return pl.DataFrame(
        rows,
        schema={"year": pl.Int32, "month": pl.Int8, "national_emp": pl.Int64,
                "states_dc_emp": pl.Int64, "other_emp": pl.Int64, "emp_gap": pl.Int64,
                "emp_gap_after_other": pl.Int64, "n_states_suppressed": pl.Int64},
        orient="row",
    )


def test_clean_identity_with_no_other_areas_enforces():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)])
    assert classify_identity(q, m)["branch"] == "enforce"


def test_identity_closing_only_after_territories_requires_residual_cells():
    q = quarters([(2017, 1, 110, 100, 10, 10, 0)])
    m = months([(2017, 1, 550, 500, 50, 50, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "residual_cells"
    assert out["evidence"]["other_areas_present"] is True


def test_unexplained_establishment_gap_declines():
    q = quarters([(2017, 1, 120, 100, 10, 20, 10)])
    m = months([(2017, 1, 550, 500, 50, 50, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "establishment" in out["reason"]


def test_negative_employment_residual_declines():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 520, 0, -20, -20, 1)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "negative" in out["reason"]


def test_no_unsuppressed_month_declines_as_untestable():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 400, 0, 100, 100, 3)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "untestable" in out["reason"]


def test_gap_in_an_unsuppressed_month_declines():
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, 505, 500, 0, 5, 5, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == "decline"
    assert "unsuppressed month" in out["reason"]


def test_suppressed_months_may_carry_a_positive_residual_under_enforce():
    """A positive gap in a suppressed month is the residual Stage 3 allocates, not a defect."""
    q = quarters([(2017, 1, 100, 100, 0, 0, 0), (2017, 2, 100, 100, 0, 0, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0), (2017, 2, 510, 460, 0, 50, 50, 2)])
    assert classify_identity(q, m)["branch"] == "enforce"


@pytest.mark.parametrize("branch_input,expected", [(0, "enforce"), (7, "residual_cells")])
def test_branch_is_always_exactly_one_of_three(branch_input, expected):
    q = quarters([(2017, 1, 100 + branch_input, 100, branch_input, branch_input, 0)])
    m = months([(2017, 1, 500, 500, 0, 0, 0, 0)])
    out = classify_identity(q, m)
    assert out["branch"] == expected
    assert out["branch"] in ("enforce", "residual_cells", "decline")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_identity_rule.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'qcew_identity'`.

- [ ] **Step 3: Write the rule and the scan**

Create `scripts/audit/qcew_identity.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""Test the QCEW state/national universe and return the SRC-QCEW-006 branch verdict.

The decision rule (`classify_identity`) is a pure function of two comparison tables and is
tested on toy panels before it ever sees real data -- see tests/audit/test_identity_rule.py.
Thresholds come from the plan's Global Constraints and are recorded, with their provenance and
their hand-authored parts labelled, in the `decision_thresholds` findings key.

Establishment counts carry the geography question and employment counts carry the suppression
question, which is why the rule tests them in that order: `qtrly_estabs` is asked whether the
state universe exhausts the national universe, and only once that is settled are the employment
columns asked how much suppression is hiding.

**Containment is measured, not assumed.** `national - states_dc - other` presupposes that a
non-state area the panel carries is a component *of* the national total. That is exactly what
Sec 8.1 asks to be verified ("if the national total includes areas outside the configured state
universe"), so `measure_containment` settles it from establishment counts before either
comparison table subtracts anything, and records what it found. A non-state area measured to sit
outside the national total is not a residual component of it, and subtracting it would
manufacture a gap where the identity in fact closes.

Two null conventions, and they are deliberately different on the two sides of the comparison:

* The **states+DC** side sums published values and skips what is not published. A suppressed
  state cell therefore contributes nothing, which makes `states_dc_emp` a lower bound on the
  true state sum and makes a positive `emp_gap` the residual Stage 3 would allocate. That is
  the intended reading, not a defect.
* The **reference** side -- the national total and any non-state area inside it -- keeps "not
  published" distinct from "zero". Summing an unpublished reference term to `0` would be
  indistinguishable from a published zero and would manufacture a gap out of a missing value. A
  period whose reference term is unpublished is unevaluable, and the rule says so rather than
  passing it.

The second convention matters because `Series.all()` skips nulls by default: `(col == 0).all()`
over a column with a null returns `True`. Every check below counts its nulls explicitly instead.
"""

from __future__ import annotations

from typing import Any

import polars as pl

import _common as c

SOURCE = "qcew_identity"

# Panel `area_class` labels (Task 4). Audit scripts do not import one another, so these are
# repeated here rather than shared; the panel's schema check is what keeps them honest.
NATIONAL = "national"
STATES_DC = "states_dc"
OTHER = "other_state_level"

QUARTER_KEYS = ["year", "qtr"]
MONTH_KEYS = ["year", "month"]

# The two comparison-table contracts. `classify_identity` reads nothing outside these, so the
# rule can be exercised on toy frames that never touch the panel.
QUARTER_COLUMNS = ("year", "qtr", "national_estabs", "states_dc_estabs", "other_estabs",
                   "estab_gap", "estab_gap_after_other")
MONTH_COLUMNS = ("year", "month", "national_emp", "states_dc_emp", "other_emp", "emp_gap",
                 "emp_gap_after_other", "n_states_suppressed")

# What gets persisted: the rule's columns plus the as-published non-state amount. `other_estabs`
# and `other_emp` are containment-adjusted (see `comparison_tables`), so on an `outside` verdict
# they are 0 in every row even where a non-state area published a count. Persisting the adjusted
# column alone would tell a Stage 3 reader of `quarter_table` that the panel carries no non-state
# establishments at all, which is false; the sibling column carries what was actually published.
QUARTER_PERSISTED_COLUMNS = (*QUARTER_COLUMNS, "other_estabs_published")
MONTH_PERSISTED_COLUMNS = (*MONTH_COLUMNS, "other_emp_published")

SUPPRESSION_CODE_MEANING = "suppressed"

# Where a non-state area sits relative to the national total, as measured from establishments.
INSIDE = "inside_national_total"
OUTSIDE = "outside_national_total"
INDETERMINATE = "indeterminate"
NO_OTHER_AREA = "no_non_state_area_present"

# Hand-authored, and labelled as such where it is persisted. Held as a module constant so the
# marking travels with the text and cannot be separated from it by an edit to `main`.
DECISION_THRESHOLDS_NOTE = (
    "Decision thresholds for SRC-QCEW-006. SCOPE MARKER, OPENING: every sentence in this "
    "findings key, from here to the closing scope marker, is hand-authored. It records where "
    "this script's two thresholds come from; it states nothing this run measured, it is the "
    "only wholly hand-authored key in this summary, and its scope does not extend past its own "
    "closing marker to any neighbouring key. This script fetches nothing, so none of the text "
    "here carries an extract hash and no later run re-checks any of it. Threshold one, "
    "tolerance: 'equals' means exact integer equality, tolerance 0, on the stated ground that "
    "QCEW monthly employment and quarterly establishment counts are integer counts of jobs and "
    "of establishments; classify_identity therefore compares gaps to 0 and never to a band, "
    "and no numerical confidentiality threshold is encoded anywhere in this script. Threshold "
    "two, branch assignment: a gap that closes only after subtracting non-state areas present "
    "in the national universe is classified residual_cells rather than enforce. That rests on "
    "one quotation, reproduced verbatim from specs/logging-employment-spec.md section 3.2: 'A "
    "national control MUST NOT be imposed on a state universe that omits components included "
    "in the national total.' The step from that quotation to the residual_cells branch is an "
    "inference and is hand-authored: the quotation forbids imposing a national control on a "
    "universe missing national components, and the reading applied here is that a states+DC "
    "universe which excludes a non-state area the national total includes is exactly such a "
    "universe, so the area must enter as an explicit residual cell instead of being controlled "
    "away. The quotation does not name the branch, and no measurement in this run carries that "
    "step. The same reading is what makes containment worth measuring rather than assuming: "
    "the quotation is conditioned on components 'included in the national total', so an area "
    "measured to sit outside that total is not what it governs. Both thresholds were set as "
    "defaults by the Stage 0 plan's Global Constraints and confirmed at handoff before "
    "classify_identity was written. SCOPE MARKER, CLOSING: end of the hand-authored text; "
    "every other findings key in this summary is computed from the panel this run read, and "
    "the one inference among them carries its own inline marker."
)


def _require_columns(frame: pl.DataFrame, columns: tuple[str, ...], label: str) -> None:
    """A missing column is a construction bug, not a data condition, so it raises rather than
    resolving to a branch. A null *inside* a present column is the opposite: a real statement
    that a value was not published, handled by the evaluable/testable partitions below."""
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise ValueError(f"{label} table is missing required column(s): {', '.join(missing)}")


def _opt_int(value: Any) -> int | None:
    """Keep an unmeasured extremum null. `int(value or 0)` would render it as 0, which reads in
    the evidence as a closed identity while the branch says otherwise."""
    return None if value is None else int(value)


def _has_nonzero_or_unpublished(series: pl.Series) -> bool:
    """A non-state area counts as present *to the rule* if it contributes a non-zero amount to
    the national total anywhere, or if such a contribution was withheld. Areas measured to sit
    outside the national total reach the rule as zero -- see `measure_containment`."""
    return bool(series.is_null().any() or (series.fill_null(0) != 0).any())


def classify_identity(quarters: pl.DataFrame, months: pl.DataFrame) -> dict:
    """Return {'branch', 'reason', 'evidence'} with branch in enforce/residual_cells/decline.

    `quarters` and `months` must carry QUARTER_COLUMNS and MONTH_COLUMNS. A null in a `*_gap_*`
    column means the period's reference term was not published, so the period is unevaluable
    (quarters) or untestable (months) rather than passing or failing.
    """
    _require_columns(quarters, QUARTER_COLUMNS, "quarters")
    _require_columns(months, MONTH_COLUMNS, "months")

    evaluable = quarters.filter(pl.col("estab_gap_after_other").is_not_null())
    n_unevaluable = quarters.height - evaluable.height
    n_closing = evaluable.filter(pl.col("estab_gap_after_other") == 0).height
    estab_closes = evaluable.height == quarters.height > 0 and n_closing == evaluable.height

    testable = months.filter(pl.col("emp_gap_after_other").is_not_null())
    n_untestable = months.height - testable.height
    n_negative = testable.filter(pl.col("emp_gap_after_other") < 0).height

    clean = testable.filter(pl.col("n_states_suppressed") == 0)
    n_clean_closing = clean.filter(pl.col("emp_gap_after_other") == 0).height
    clean_closes = clean.height > 0 and n_clean_closing == clean.height

    max_estab_gap = _opt_int(evaluable["estab_gap_after_other"].abs().max())
    min_emp_gap = _opt_int(testable["emp_gap_after_other"].min())
    max_clean_gap = _opt_int(clean["emp_gap_after_other"].abs().max())

    evidence = {
        "estab_identity_closes_after_other_areas": estab_closes,
        "other_areas_present": (_has_nonzero_or_unpublished(quarters["other_estabs"])
                                or _has_nonzero_or_unpublished(months["other_emp"])),
        "employment_residual_never_negative": n_negative == 0,
        "clean_months": int(clean.height),
        "clean_months_close": clean_closes,
        "max_estab_gap_after_other": max_estab_gap,
        "min_emp_gap_after_other": min_emp_gap,
        "quarters_total": int(quarters.height),
        "quarters_evaluable": int(evaluable.height),
        "quarters_unevaluable": int(n_unevaluable),
        "quarters_closing": int(n_closing),
        "months_total": int(months.height),
        "testable_months": int(testable.height),
        "untestable_months": int(n_untestable),
        "clean_months_closing": int(n_clean_closing),
        "negative_residual_months": int(n_negative),
        "max_abs_clean_emp_gap": max_clean_gap,
    }

    def decided(branch: str, reason: str) -> dict:
        return {"branch": branch, "reason": reason, "evidence": evidence}

    if evaluable.height != quarters.height or quarters.height == 0:
        return decided("decline", (
            f"only {evaluable.height} of {quarters.height} quarter(s) carry an evaluable "
            f"establishment gap, because a reference establishment count is unpublished in the "
            f"other {n_unevaluable}, so the state universe cannot be shown to exhaust the "
            f"national universe"))
    if not estab_closes:
        return decided("decline", (
            f"the establishment gap after non-state areas is non-zero in "
            f"{evaluable.height - n_closing} of {evaluable.height} evaluable quarter(s), "
            f"reaching {max_estab_gap} in absolute value, so the national universe is not "
            f"explained by the configured state geography"))
    if n_negative:
        return decided("decline", (
            f"{n_negative} of {testable.height} testable month(s) carry a negative employment "
            f"residual after non-state areas, the smallest being {min_emp_gap}, which no amount "
            f"of state suppression can produce and which therefore indicates a definitional "
            f"mismatch rather than a withheld cell"))
    if testable.height == 0:
        return decided("decline", (
            f"none of the {months.height} month(s) carries both a published national and a "
            f"published non-state employment value, so the employment identity is untestable "
            f"on published values"))
    if clean.height == 0:
        return decided("decline", (
            f"every one of the {testable.height} testable month(s) carries at least one "
            f"{SUPPRESSION_CODE_MEANING} state cell, so the employment identity is untestable "
            f"on a complete published state sum"))
    if not clean_closes:
        return decided("decline", (
            f"the employment gap after non-state areas is non-zero in "
            f"{clean.height - n_clean_closing} of the {clean.height} month(s) with no "
            f"{SUPPRESSION_CODE_MEANING} state cell, reaching {max_clean_gap} in absolute "
            f"value, so the national total is not the sum of the state universe in an "
            f"unsuppressed month"))
    if evidence["other_areas_present"]:
        return decided("residual_cells", (
            f"the identity closes across all {evaluable.height} quarter(s) and all "
            f"{clean.height} unsuppressed month(s) only once the non-state areas the panel "
            f"carries are subtracted, so those areas have to enter as explicit residual cells "
            f"rather than be controlled away"))
    return decided("enforce", (
        f"the national total equals the states+DC published sum exactly across all "
        f"{evaluable.height} quarter(s) and all {clean.height} month(s) with no "
        f"{SUPPRESSION_CODE_MEANING} state cell, with no non-state area contributing a value"))


def _published_sum(frame: pl.DataFrame, keys: list[str], value: str, alias: str) -> pl.DataFrame:
    """The states+DC side: sum what was published and skip what was not."""
    return frame.group_by(keys).agg(pl.col(value).sum().cast(pl.Int64).alias(alias))


def _reference_parts(
    frame: pl.DataFrame, keys: list[str], value: str, alias: str
) -> pl.DataFrame:
    """The reference side: carry the sum *and* the count of unpublished cells, so the join
    below can tell 'this area published nothing here' from 'this area is absent here'."""
    return frame.group_by(keys).agg(
        pl.col(value).sum().cast(pl.Int64).alias(f"_{alias}_sum"),
        pl.col(value).null_count().cast(pl.Int64).alias(f"_{alias}_unpublished"),
    )


def _resolve_reference(alias: str, when_absent: int | None) -> pl.Expr:
    """Absent group -> `when_absent`; present but with an unpublished cell -> null."""
    return (
        pl.when(pl.col(f"_{alias}_unpublished").is_null())
        .then(pl.lit(when_absent, pl.Int64))
        .when(pl.col(f"_{alias}_unpublished") > 0)
        .then(pl.lit(None, pl.Int64))
        .otherwise(pl.col(f"_{alias}_sum"))
        .cast(pl.Int64)
        .alias(alias)
    )


def quarterly_estabs(panel: pl.DataFrame) -> pl.DataFrame:
    """One establishment row per (area, year, quarter).

    `qtrly_estabs` is a quarterly figure repeated across the three monthly rows each quarter
    expands into. Rather than trusting that repetition, it is asserted: a quarter whose three
    monthly rows disagreed would make every establishment sum below quietly wrong, so it fails
    here instead.
    """
    keys = ["area_fips", *QUARTER_KEYS]
    collapsed = panel.group_by(keys).agg(
        pl.col("area_class").first(),
        pl.col("qtrly_estabs").first(),
        pl.col("qtrly_estabs").n_unique().alias("_distinct"),
    )
    disagreeing = collapsed.filter(pl.col("_distinct") > 1).height
    if disagreeing:
        raise ValueError(
            f"qtrly_estabs varies within {disagreeing} (area_fips, year, qtr) group(s); the "
            "establishment comparison assumes one quarterly value per area-quarter"
        )
    return collapsed.drop("_distinct")


def _by_class(frame: pl.DataFrame, area_class: str) -> pl.DataFrame:
    return frame.filter(pl.col("area_class") == area_class)


def raw_quarter_table(estabs: pl.DataFrame) -> pl.DataFrame:
    """National, states+DC and non-state establishment counts per quarter, before any
    subtraction. `estab_gap` here is the raw `national - states_dc`; nothing is netted out of it
    until containment has been measured."""
    return (
        estabs.select(QUARTER_KEYS).unique()
        .join(_reference_parts(_by_class(estabs, NATIONAL), QUARTER_KEYS,
                               "qtrly_estabs", "national_estabs"), on=QUARTER_KEYS, how="left")
        .join(_published_sum(_by_class(estabs, STATES_DC), QUARTER_KEYS,
                             "qtrly_estabs", "states_dc_estabs"), on=QUARTER_KEYS, how="left")
        .join(_reference_parts(_by_class(estabs, OTHER), QUARTER_KEYS,
                               "qtrly_estabs", "other_published"), on=QUARTER_KEYS, how="left")
        .with_columns(
            # A missing national row means no national total was published for that quarter,
            # which is unevaluable -- not zero. A missing non-state group means no such area
            # exists that quarter, which genuinely contributes zero.
            _resolve_reference("national_estabs", None),
            _resolve_reference("other_published", 0),
            pl.col("states_dc_estabs").fill_null(0),
        )
        .with_columns(estab_gap=pl.col("national_estabs") - pl.col("states_dc_estabs"))
        .select([*QUARTER_KEYS, "national_estabs", "states_dc_estabs", "other_published",
                 "estab_gap"])
        .sort(QUARTER_KEYS)
    )


def measure_containment(raw: pl.DataFrame) -> dict:
    """Settle whether the panel's non-state areas are components of the national total.

    Sec 8.1 asks the system to verify the state/national universe rather than assume it, and
    this is that step. It is decided on establishment counts, which survive suppression far
    better than employment does, and only on the quarters where a non-state area actually
    publishes a non-zero count -- a quarter contributing nothing cannot discriminate, since
    `estab_gap == other == 0` satisfies both readings at once.
    """
    testable = raw.filter(
        pl.col("estab_gap").is_not_null()
        & pl.col("other_published").is_not_null()
        & (pl.col("other_published") != 0)
    )
    n_inside = testable.filter(pl.col("estab_gap") == pl.col("other_published")).height
    n_outside = testable.filter(pl.col("estab_gap") == 0).height

    if testable.height == 0:
        verdict = NO_OTHER_AREA
    elif n_inside == testable.height:
        verdict = INSIDE
    elif n_outside == testable.height:
        verdict = OUTSIDE
    else:
        verdict = INDETERMINATE

    return {
        "verdict": verdict,
        "quarters_discriminating": int(testable.height),
        "quarters_gap_equals_non_state_amount": int(n_inside),
        "quarters_gap_is_zero": int(n_outside),
        "quarters_non_state_amount_unpublished": int(
            raw.filter(pl.col("other_published").is_null()).height
        ),
        "subtraction_applied": verdict in (INSIDE, INDETERMINATE),
        "basis": (
            f"measured on {testable.height} quarter(s) in which a non-state area publishes a "
            f"non-zero establishment count: national minus states+DC equals that area's own "
            f"count in {n_inside} of them and equals 0 in {n_outside} of them, giving the "
            f"verdict {verdict}, on which the non-state amount is "
            f"{'subtracted from' if verdict in (INSIDE, INDETERMINATE) else 'left out of'} both "
            f"comparison tables' gap columns"
        ),
        "per_quarter": raw.filter(pl.col("other_published").fill_null(-1) != 0).to_dicts(),
    }


def comparison_tables(panel: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """Build the quarter and month comparison tables the rule reads, plus what was measured
    about non-state containment on the way.

    Both tables are indexed by the periods the *panel* covers, not by the national rows, so a
    period with no national row surfaces as an unevaluable period rather than vanishing.

    `other_estabs` and `other_emp` as handed to the rule are the non-state amounts *inside the
    national total*: the published amount where containment measured `inside` (or could not be
    settled, which leaves the gap to fail the rule's first gate rather than be quietly closed),
    and 0 where it measured `outside`. Both tables also carry an `*_published` sibling column
    holding the amount as published, so the zeroing is visible in the tables themselves and not
    only in the `non_state_area_containment` finding.
    """
    estabs = quarterly_estabs(panel)
    raw = raw_quarter_table(estabs)
    containment = measure_containment(raw)
    subtract = containment["subtraction_applied"]

    quarters = (
        raw.with_columns(
            other_estabs=pl.col("other_published") if subtract else pl.lit(0, pl.Int64)
        )
        .with_columns(estab_gap_after_other=pl.col("estab_gap") - pl.col("other_estabs"))
        .rename({"other_published": "other_estabs_published"})
        .select(QUARTER_PERSISTED_COLUMNS)
        .sort(QUARTER_KEYS)
    )

    suppressed_states = (
        _by_class(panel, STATES_DC).filter(pl.col("suppressed"))
        .group_by(MONTH_KEYS).agg(pl.len().cast(pl.Int64).alias("n_states_suppressed"))
    )
    months = (
        panel.select(MONTH_KEYS).unique()
        .join(_reference_parts(_by_class(panel, NATIONAL), MONTH_KEYS, "emplvl", "national_emp"),
              on=MONTH_KEYS, how="left")
        .join(_published_sum(_by_class(panel, STATES_DC), MONTH_KEYS, "emplvl", "states_dc_emp"),
              on=MONTH_KEYS, how="left")
        .join(_reference_parts(_by_class(panel, OTHER), MONTH_KEYS, "emplvl", "other_published"),
              on=MONTH_KEYS, how="left")
        .join(suppressed_states, on=MONTH_KEYS, how="left")
        .with_columns(
            _resolve_reference("national_emp", None),
            _resolve_reference("other_published", 0),
            pl.col("states_dc_emp").fill_null(0),
            pl.col("n_states_suppressed").fill_null(0),
        )
        .with_columns(
            other_emp=pl.col("other_published") if subtract else pl.lit(0, pl.Int64)
        )
        .with_columns(emp_gap=pl.col("national_emp") - pl.col("states_dc_emp"))
        .with_columns(emp_gap_after_other=pl.col("emp_gap") - pl.col("other_emp"))
        .rename({"other_published": "other_emp_published"})
        .select(MONTH_PERSISTED_COLUMNS)
        .sort(MONTH_KEYS)
    )
    return quarters, months, containment


def _period_label(frame: pl.DataFrame) -> str:
    """'2017-01 through 2024-12', from the months the panel actually carries."""
    ordered = frame.sort(MONTH_KEYS)
    first, last = ordered.row(0, named=True), ordered.row(-1, named=True)
    return f"{first['year']}-{first['month']:02d} through {last['year']}-{last['month']:02d}"


def structural_findings(panel: pl.DataFrame, estabs: pl.DataFrame) -> dict:
    """Panel properties the rule's two tables cannot express, all computed from this panel.

    These exist so the verdict can be read against the shape of its input: how many states+DC
    areas each month carries, whether an unpublished employment value is always a
    `suppressed`-flagged one, and how many cells on each side were withheld.
    """
    states = _by_class(panel, STATES_DC)
    per_month = states.group_by(MONTH_KEYS).agg(
        pl.col("area_fips").n_unique().alias("n_areas"),
        pl.col("suppressed").sum().alias("n_suppressed"),
    )
    n_areas, n_months = states["area_fips"].n_unique(), panel.select(MONTH_KEYS).n_unique()

    unpublished_emp = states.filter(pl.col("emplvl").is_null()).height
    flagged = states.filter(pl.col("suppressed")).height
    both = states.filter(pl.col("emplvl").is_null() & pl.col("suppressed")).height

    others = (
        _by_class(panel, OTHER)
        .group_by("area_fips", "area_title")
        .agg(pl.len().cast(pl.Int64).alias("area_months"))
        .sort("area_fips")
        .to_dicts()
    )
    short_span = (
        states.group_by("area_fips", "area_title").agg(pl.len().cast(pl.Int64).alias("months"))
        .filter(pl.col("months") < n_months).sort("area_fips").to_dicts()
    )
    national, other = _by_class(panel, NATIONAL), _by_class(panel, OTHER)
    nat_estabs, other_estabs = _by_class(estabs, NATIONAL), _by_class(estabs, OTHER)

    return {
        "panel_rows": int(panel.height),
        "rows_by_area_class": dict(
            panel.group_by("area_class").len().sort("area_class").iter_rows()
        ),
        "months_covered": int(n_months),
        "quarters_covered": int(panel.select(QUARTER_KEYS).n_unique()),
        "states_dc_areas": int(n_areas),
        "states_dc_areas_per_month": {
            "min": int(per_month["n_areas"].min()), "max": int(per_month["n_areas"].max()),
            "constant": bool(per_month["n_areas"].min() == per_month["n_areas"].max()),
        },
        "states_dc_suppressed_per_month": {
            "min": int(per_month["n_suppressed"].min()),
            "max": int(per_month["n_suppressed"].max()),
        },
        "states_dc_area_months_absent": int(n_areas * n_months - states.height),
        "states_dc_short_span_areas": short_span,
        "states_dc_suppressed_cells": int(flagged),
        "states_dc_unpublished_emp_cells": int(unpublished_emp),
        "states_dc_unpublished_emp_is_exactly_suppressed": bool(
            unpublished_emp == flagged == both
        ),
        "states_dc_unpublished_estab_cells": int(
            _by_class(estabs, STATES_DC).filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "national_months_unpublished_emp": int(national.filter(pl.col("emplvl").is_null()).height),
        "national_quarters_unpublished_estabs": int(
            nat_estabs.filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "national_months_present": int(national.height),
        "national_quarters_present": int(nat_estabs.height),
        "other_state_level_areas": others,
        "other_months_unpublished_emp": int(other.filter(pl.col("emplvl").is_null()).height),
        "other_quarters_unpublished_estabs": int(
            other_estabs.filter(pl.col("qtrly_estabs").is_null()).height
        ),
        "qtrly_estabs_constant_within_area_quarter": True,
    }


def absent_state_months_note(structural: dict, evidence: dict) -> str:
    """Why a states+DC area-month with no published row is read as a true zero. The counts are
    computed; the reading drawn from them is not, and is marked inline as such."""
    areas = ", ".join(
        f"{a['area_title'] or a['area_fips']} ({a['months']} month(s))"
        for a in structural["states_dc_short_span_areas"]
    ) or "none"
    per_month = structural["states_dc_areas_per_month"]
    return (
        f"Absent states+DC area-months, measured: {structural['states_dc_area_months_absent']} "
        f"of the {structural['states_dc_areas']} x {structural['months_covered']} possible "
        f"area-month cells carry no row at all, and each month carries between "
        f"{per_month['min']} and {per_month['max']} of the {structural['states_dc_areas']} "
        f"areas. The area(s) whose span is shorter than the panel's: {areas}. Also measured: "
        f"the establishment gap after non-state areas is exactly zero in "
        f"{evidence['quarters_closing']} of {evidence['quarters_evaluable']} evaluable "
        f"quarter(s). INFERENCE MARKER, OPENING: what follows to the closing marker is a "
        f"reading of those two measurements, not a third measurement, is supplied by hand, "
        f"carries no extract hash and is re-checked by no later run. An area-month with no "
        f"published row is read here as a true zero rather than as a hidden value, on the "
        f"ground that an area adding zero establishments to a quarterly total that closes "
        f"exactly can add no employment in that quarter's months; on that reading the varying "
        f"per-month area count above does not undercut the state sum. INFERENCE MARKER, "
        f"CLOSING."
    )


def verified_panel_scope() -> str:
    """The industry and ownership this verdict covers, both read and checked rather than asserted.

    Naming the scope matters -- a verdict about the national identity is a verdict about one
    industry-and-ownership slice of it -- but writing either into the sentence would state a
    scope fact this run never checked: a re-run against a panel built on different filters would
    print them unchanged. So both are checked against the predicates the panel actually applied.
    Those predicates come from the same `qcew_panel` summary that supplies this script's parquet
    path, which is what ties the check to the file being read rather than to a same-named file
    somewhere else. The ownership code comes from `qcew_codes.findings.private_own_code` and its
    title from the ownership titles file that task fetched, so the title carries an extract hash
    instead of being spelled out here. `c.INDUSTRY_CODE` is a plan-pinned constant and needs no
    such lookup, but it still needs the predicate check: the constant says what this plan targets,
    not what the panel on disk was actually filtered to.

    Refusing is the point. If either predicate is absent the scope cannot be stated truthfully,
    and a verdict sentence that names an unverified scope is worse than no sentence at all.
    """
    predicates = c.load_summary("qcew_panel")["findings"]["filter_predicates"]

    def require_applied(prefix: str, what: str) -> None:
        if not any(p.startswith(prefix) for p in predicates):
            raise ValueError(
                f"no qcew_panel filter predicate applied {prefix!r}, so the {what} scope of "
                f"this verdict cannot be stated"
            )

    require_applied(f"industry_code == '{c.INDUSTRY_CODE}'", "industry")

    codes = c.load_summary("qcew_codes")
    own_code = codes["findings"]["private_own_code"]
    require_applied(f"own_code == '{own_code}'", "ownership")

    titles_path = next(e["path"] for e in codes["extracts"]
                       if e["path"].endswith("titles/own_code.csv"))
    titles = pl.read_csv(titles_path, infer_schema_length=0)
    title = dict(zip(titles[titles.columns[0]].to_list(),
                     titles[titles.columns[1]].to_list(), strict=True))[own_code]
    return f"industry {c.INDUSTRY_CODE} and own_code {own_code} ('{title}')"


def geography_reading(result: dict, quarters: pl.DataFrame) -> str:
    """`geography_universe_explains_gap` is a conjunction, so it is false both when geography
    fails to explain a gap and when there is no gap for geography to explain. Those are opposite
    findings, and Stage 3 reads this key, so the run states which case it is in."""
    evidence = result["evidence"]
    gaps = sorted(int(v) for v in quarters["estab_gap"].drop_nulls().unique())
    return (
        f"Reading of geography_universe_explains_gap, whose value this run is "
        f"{evidence['other_areas_present'] and evidence['estab_identity_closes_after_other_areas']}"
        f": the key is the conjunction of other_areas_present "
        f"({evidence['other_areas_present']}) with estab_identity_closes_after_other_areas "
        f"({evidence['estab_identity_closes_after_other_areas']}), so a false value can mean "
        f"either that geography leaves a gap unexplained or that no gap arose for geography to "
        f"explain. Which of the two this run found, from the raw comparison rather than from "
        f"the conjunction: national minus states+DC establishments takes the value(s) {gaps} "
        f"across the {quarters.height} quarter(s) in the panel, and non-state containment was "
        f"measured separately in non_state_area_containment."
    )


def _clean_month_clause(evidence: dict, months: pl.DataFrame) -> str:
    """The employment clause of the verdict, stating counts rather than an outcome so that no
    wording is shared between two branches that would read as a claim in one of them.

    The suppressed-cell range is taken over the *testable* months, because that is what the
    clause attributes it to. `panel_structure.states_dc_suppressed_per_month` ranges over every
    month in the panel, which is a different population whenever some month is untestable.
    """
    if evidence["testable_months"] == 0:
        return (f"none of the {evidence['months_total']} month(s) carries both a published "
                f"national and a published non-state employment value")
    testable = months.filter(pl.col("emp_gap_after_other").is_not_null())
    if evidence["clean_months"] == 0:
        return (f"each of the {evidence['testable_months']} testable month(s) carries between "
                f"{int(testable['n_states_suppressed'].min())} and "
                f"{int(testable['n_states_suppressed'].max())} {SUPPRESSION_CODE_MEANING} "
                f"states+DC cells and an employment gap after non-state areas of at least "
                f"{evidence['min_emp_gap_after_other']}")
    return (f"in {evidence['clean_months_closing']} of the {evidence['clean_months']} testable "
            f"month(s) carrying no {SUPPRESSION_CODE_MEANING} states+DC cell the employment "
            f"gap after non-state areas is exactly zero, its largest absolute value being "
            f"{evidence['max_abs_clean_emp_gap']}")


def build_verdict_sentence(
    result: dict, structural: dict, containment: dict, months: pl.DataFrame,
    span: str, scope: str
) -> str:
    """One sentence, every figure in it interpolated from this run's tables.

    `quarters_closing` counts quarters where `estab_gap_after_other` is 0, so the sentence says
    "after subtracting" exactly when a subtraction was applied. Stating it unconditionally would
    be false on an `outside` verdict, and omitting it unconditionally would be false on an
    `inside` one.
    """
    evidence = result["evidence"]
    others = structural["other_state_level_areas"]
    names = ", ".join(o["area_title"] or o["area_fips"] for o in others) or "none"
    subtracted = (" after subtracting the non-state amount measured inside it"
                  if containment["subtraction_applied"] else "")
    return (
        f"{result['branch']}: across the {evidence['quarters_total']} quarter(s) and "
        f"{evidence['months_total']} month(s) the panel covers ({span}), the national "
        f"establishment count for {scope} equals the states+DC published "
        f"sum{subtracted} in {evidence['quarters_closing']} of "
        f"{evidence['quarters_evaluable']} evaluable quarter(s), with "
        f"{evidence['quarters_unevaluable']} unevaluable and "
        f"{structural['states_dc_unpublished_estab_cells']} states+DC establishment cell(s) "
        f"unpublished; the panel carries {len(others)} non-state area(s) ({names}) across "
        f"{sum(o['area_months'] for o in others)} area-month(s), measured as "
        f"{containment['verdict']} on {containment['quarters_discriminating']} discriminating "
        f"quarter(s); {_clean_month_clause(evidence, months)}; {result['reason']}."
    )


def assert_one_sentence(sentence: str) -> None:
    """The stage exit criterion reads `verdict_sentence` as exactly one sentence. An area title
    carrying an internal full stop would break that silently, so it breaks loudly here."""
    if sentence.count(".") != 1 or not sentence.endswith("."):
        raise ValueError(f"verdict_sentence must be exactly one sentence, got: {sentence}")


def coverage_span(months: pl.DataFrame) -> dict[str, str]:
    """Derived from the months the panel carries, against the D1 window."""
    ordered = months.sort(MONTH_KEYS)
    labels = [f"{y}-{m:02d}" for y, m in zip(ordered["year"], ordered["month"], strict=True)]
    window = [f"{y}-{m:02d}" for y in c.WINDOW_YEARS for m in range(1, 13)]
    uncovered = [label for label in window if label not in set(labels)]
    return {
        "published_start": labels[0], "published_end": labels[-1],
        "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
        "covered": f"{labels[0]}..{labels[-1]} ({len(labels)} month(s))",
        "uncovered": ",".join(uncovered),
    }


def main() -> None:
    panel_path = next(e["path"] for e in c.load_summary("qcew_panel")["extracts"]
                      if e["path"].endswith("panel.parquet"))
    panel = pl.read_parquet(panel_path)

    quarters, months, containment = comparison_tables(panel)
    result = classify_identity(quarters, months)
    structural = structural_findings(panel, quarterly_estabs(panel))

    sentence = build_verdict_sentence(result, structural, containment, months,
                                      _period_label(months), verified_panel_scope())
    assert_one_sentence(sentence)

    c.write_summary(
        SOURCE,
        coverage_span=coverage_span(months),
        access={"route": f"derived from qcew_panel ({panel_path})", "status": "verified",
                "reason": None},
        extracts=[],
        findings={
            "quarter_table": quarters.to_dicts(),
            "month_table": months.to_dicts(),
            "branch": result["branch"],
            "reason": result["reason"],
            "evidence": result["evidence"],
            "verdict_sentence": sentence,
            "geography_universe_explains_gap": (
                result["evidence"]["other_areas_present"]
                and result["evidence"]["estab_identity_closes_after_other_areas"]
            ),
            "clean_months": result["evidence"]["clean_months"],
            "geography_universe_explains_gap_reading": geography_reading(result, quarters),
            "non_state_area_containment": containment,
            "panel_structure": structural,
            "absent_state_months": absent_state_months_note(structural, result["evidence"]),
            "decision_thresholds": DECISION_THRESHOLDS_NOTE,
        },
    )
    print(sentence)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the rule tests to verify they pass**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_identity_rule.py -q
```

Expected: PASS — 9 passed.

- [ ] **Step 5: Run the scan**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/qcew_identity.py
```

Expected: the one-sentence verdict prints, beginning with `enforce:`, `residual_cells:`, or
`decline:`. Any of the three is a legitimate finding.

- [ ] **Step 6: Verify the verdict is well-formed**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/qcew_identity/summary.json"))["findings"]
assert f["branch"] in ("enforce", "residual_cells", "decline")
assert f["verdict_sentence"].count(".") >= 1 and len(f["verdict_sentence"].split(". ")) == 1, \
    "the verdict must be one sentence"
assert len(f["quarter_table"]) == 32, "the D1 window is 32 quarters"
assert len(f["month_table"]) == 96, "the D1 window is 96 months"
print(f["verdict_sentence"])
PY
```

Expected: all four assertions hold and the verdict sentence prints. If the branch is
`decline`, add a `> Deviation:` note to this task recording it, because Stage 3's plan must
then name a substitute allocation anchor before writing any baseline.

> **Deviation (recorded on execution, 2026-09-03): the branch is `decline`.**
>
> **Stage 3 must name a substitute allocation anchor, or explicitly accept a weaker assumption
> on the existing one, before any baseline is written.** This note is the tracked record of that
> obligation: the audit summary lives under gitignored `data/` and the execution ledger under
> gitignored `.sdd/`, so without this line nothing surviving a fresh clone would carry it.
>
> **The decline is for unverifiability, not for a geography mismatch — the distinction changes
> what Stage 3 has to do.** The state universe exhausts the national one: national minus
> states+DC quarterly establishments is exactly 0 in 32 of 32 quarters, the only distinct gap
> value in the window. Puerto Rico, the single non-state area present, is measured **outside**
> the `US000` total — it publishes 1–2 establishments in 8 quarters (2017q1–2018q4) and the gap
> stays exactly 0 in every one of them, which is the discriminating test. What fails is
> testability: `clean_months` is 0 because every one of the 96 months carries 9–15 suppressed
> states+DC cells, so the employment identity is never checkable against a complete published
> state sum. The monthly gap after non-state areas is +696 to +2711 and never negative —
> consistent with the identity in every month, proving it in none. So Stage 3's choice is
> between a weaker assumption on the *same* anchor and a genuine substitute; Stage 0 does not
> decide which.
>
> **This step's own arithmetic is corrected above.** The illustrative
> `estab_gap_after_other = estab_gap - other_estabs` presupposed that a non-state area is inside
> the national total. Puerto Rico is not, so subtracting it manufactured a −1/−2 gap out of a
> true zero. Containment is now settled from establishment counts *before* either table
> subtracts anything. The branch was `decline` under both forms — only the recorded reason
> changed, from false to true.

- [ ] **Step 7: Commit**

```bash
git add scripts/audit/qcew_identity.py tests/audit/test_identity_rule.py
git commit -m "feat(audit): test the QCEW state/national universe and record the SRC-QCEW-006 branch"
```

---

### Task 6: QCEW establishment-size dimensionality (SRC-QSIZE-002)

Closes: `SRC-QSIZE-002` — *"The parser MUST verify actual simultaneous dimensionality from file
contents, not infer it from adjacent documentation."* The roadmap moved this from an open
verdict to an extract-confirmation because two reviews independently document QCEW size as
national × six-digit **or** state × sector, never both at once.

**This finding is high-stakes, not a checkbox.** Stage 6's `Consumes` block says: *"if an
extract proves a state × 113310 × size table exists, re-route this stage to brainstorming
before planning, because §2.2 row 3's premise would no longer hold."* §2.2 row 3 reads: *"The
system MUST assume no direct public state × six-digit Logging × establishment-size table from
QCEW unless a concrete file extract proves otherwise."* This task is that proof-or-disproof.

**Files:**
- Create: `scripts/audit/qcew_size.py`
- Test: `tests/audit/test_size_predicate.py`

**Interfaces:**
- Consumes: `_common`, including `STATES_DC_FIPS` / `STATE_AREAS` / `NATIONAL_AREA` — shared
  from Task 1, not re-declared locally, because the audit scripts do not import one another
  except through summaries.
- Produces: `has_simultaneous_state_industry_size(df, *, industry, state_areas, all_sizes) -> bool`
  and `all_sizes_code(titles) -> str` — `all_sizes` is the aggregate size_code the predicate
  excludes, and it is **derived from the fetched size_code titles file, never hardcoded**
  (FIX 13 / B1; the same rule that governs `private_own_code`). `main()` therefore loads the
  titles file before computing the verdict, because the verdict depends on it. Also produces
  `data/raw/audit/qcew_size/summary.json` (source key `qcew_size`), plus one
  `{year}_q1_by_size.zip` per window year under `data/raw/audit/qcew_size/`.
  `findings` keys:
  - `simultaneous_state_industry_size` — bool. **The `SRC-QSIZE-002` verdict.**
  - `all_sizes_code` — `{code, title}` for the derived all-sizes aggregate, recorded so the
    value the verdict depends on is auditable rather than implicit.
  - `agglvl_inventory` — per `agglvl_code` present in the by-size product:
    `{agglvl_code, row_count, has_113310, area_pattern, size_codes}` where `area_pattern` is one
    of `national`, `state_level`, `sub_state`, `mixed`.
  - `what_the_file_does_carry` — a one-line prose statement of the finest simultaneous
    (geography, industry, size) combination observed, whichever way the verdict falls.
  - `size_codes_with_titles` — the `size_code` values present, joined to the titles file
    fetched in Task 3.
  - `years_checked` — list of ints.
  - `stage6_reroute_required` — bool, mirroring `simultaneous_state_industry_size`.

- [ ] **Step 1: Write the failing predicate test**

Create `tests/audit/test_size_predicate.py`:

```python
import polars as pl

from qcew_size import has_simultaneous_state_industry_size

STATE_AREAS = {"01000", "06000", "41000"}


def frame(rows):
    return pl.DataFrame(
        rows,
        schema={"area_fips": pl.Utf8, "industry_code": pl.Utf8, "size_code": pl.Utf8},
        orient="row",
    )


def test_national_industry_size_is_not_simultaneous_state_detail():
    df = frame([("US000", "113310", "1"), ("US000", "113310", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_state_sector_size_is_not_simultaneous_six_digit_detail():
    df = frame([("41000", "11", "1"), ("41000", "113", "2")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_state_six_digit_aggregate_size_code_does_not_count():
    """The aggregate code carries no size breakdown, so it never satisfies the predicate.
    '0' here is this fixture's aggregate code; the script derives the real one from the
    fetched titles file and passes it in."""
    df = frame([("41000", "113310", "0")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_one_true_row_flips_the_verdict():
    df = frame([("US000", "113310", "1"), ("41000", "113310", "3")])
    assert has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")


def test_county_row_is_not_a_state_row():
    df = frame([("41005", "113310", "3")])
    assert not has_simultaneous_state_industry_size(
        df, industry="113310", state_areas=STATE_AREAS, all_sizes="0")
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_size_predicate.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'qcew_size'`.

- [ ] **Step 3: Write the script**

Create `scripts/audit/qcew_size.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-QSIZE-002: prove from file contents whether QCEW publishes state x 113310 x
establishment size simultaneously, and record what the by-size product does carry."""

from __future__ import annotations

import io
import re
import zipfile

import polars as pl

import _common as c

SOURCE = "qcew_size"
SIZE_URL = "https://data.bls.gov/cew/data/files/{year}/csv/{year}_q1_by_size.zip"
# STATES_DC_FIPS / STATE_AREAS come from _common (Task 1) — shared, not re-declared, because
# audit scripts do not import one another except through summaries.


ALL_SIZES_TITLE = re.compile(r"^all\b.*\bsizes?\b", re.IGNORECASE)


def all_sizes_code(titles: dict[str, str]) -> str:
    """The size_code standing for the all-sizes aggregate, DERIVED from the fetched
    size_code titles file rather than hardcoded.

    Task 9 states the general rule this follows: a code's meaning comes from the titles file
    the run fetched, never from memory. Hardcoding "0" here would have made this script assert
    a code-to-meaning mapping it never checked -- and the aggregate code is load-bearing,
    because it is the one value the simultaneity predicate must exclude. Raises unless exactly
    one title matches, so an ambiguous or renamed vocabulary fails loudly instead of silently
    counting the aggregate as a real size class."""
    hits = sorted(code for code, title in titles.items() if ALL_SIZES_TITLE.match(title or ""))
    if len(hits) != 1:
        raise RuntimeError(
            f"expected exactly one all-sizes title in the fetched size_code titles, got "
            f"{len(hits)}: {[(h, titles[h]) for h in hits]}"
        )
    return hits[0]


def has_simultaneous_state_industry_size(
    df: pl.DataFrame, *, industry: str, state_areas: set[str], all_sizes: str
) -> bool:
    """True iff a single row carries a state-level area, the target industry, and a real size
    class at once. `all_sizes` is the aggregate code -- it carries no size breakdown, so it
    never counts. Pass the code `all_sizes_code` derived from the fetched titles file; the
    caller supplies it rather than this function assuming a literal."""
    return df.filter(
        pl.col("area_fips").is_in(sorted(state_areas))
        & (pl.col("industry_code") == industry)
        & (pl.col("size_code") != all_sizes)
    ).height > 0


def area_pattern(areas: list[str]) -> str:
    national = {c.NATIONAL_AREA}
    kinds = set()
    for a in areas:
        if a in national:
            kinds.add("national")
        elif a in c.STATE_AREAS:
            kinds.add("state_level")
        else:
            kinds.add("sub_state")
    if len(kinds) == 1:
        return kinds.pop()
    return "mixed"


def read_zip(path: str) -> pl.DataFrame:
    with zipfile.ZipFile(path) as zf:
        member = next(n for n in zf.namelist() if n.endswith(".csv"))
        return pl.read_csv(io.BytesIO(zf.read(member)), infer_schema_length=0)


def main() -> None:
    client = c.build_client()
    extracts, frames = [], []
    for year in c.WINDOW_YEARS:
        url = SIZE_URL.format(year=year)
        rec = c.download_extract(client, SOURCE, url, f"{year}_q1_by_size.zip")
        extracts.append(rec)
        frames.append(read_zip(rec.path).with_columns(pl.lit(year).alias("ref_year")))
    df = pl.concat(frames, how="vertical")

    # The titles file is loaded BEFORE the verdict because the verdict depends on it: the
    # aggregate size_code the predicate excludes is derived from it, not assumed.
    tpath = next(e["path"] for e in c.load_summary("qcew_codes")["extracts"]
                 if e["path"].endswith("titles/size_code.csv"))
    tdf = pl.read_csv(tpath, infer_schema_length=0)
    titles = dict(zip(tdf[tdf.columns[0]].to_list(), tdf[tdf.columns[1]].to_list(),
                      strict=True))
    all_sizes = all_sizes_code(titles)

    verdict = has_simultaneous_state_industry_size(
        df, industry=c.INDUSTRY_CODE, state_areas=c.STATE_AREAS, all_sizes=all_sizes)

    inventory = []
    for (agglvl,), grp in df.group_by(["agglvl_code"], maintain_order=True):
        inventory.append({
            "agglvl_code": agglvl,
            "row_count": grp.height,
            "has_113310": bool((grp["industry_code"] == c.INDUSTRY_CODE).any()),
            "area_pattern": area_pattern(grp["area_fips"].unique().to_list()),
            "size_codes": sorted(grp["size_code"].unique().to_list()),
        })
    inventory.sort(key=lambda r: r["agglvl_code"])

    logging_rows = df.filter(pl.col("industry_code") == c.INDUSTRY_CODE)
    finest = (
        "state x 113310 x establishment size IS published simultaneously"
        if verdict else
        "the finest simultaneous combination observed for 113310 is "
        f"{area_pattern(logging_rows['area_fips'].unique().to_list())} geography x 113310 x "
        f"size codes {sorted(logging_rows['size_code'].unique().to_list())}"
    )

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": f"{min(c.WINDOW_YEARS)}-Q1",
            "published_end": f"{max(c.WINDOW_YEARS)}-Q1",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": "first quarter of each window year only",
            "uncovered": "Q2-Q4 of every window year: the by-size product is Q1-only",
        },
        access={"route": SIZE_URL, "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "simultaneous_state_industry_size": verdict,
            "agglvl_inventory": inventory,
            "what_the_file_does_carry": finest,
            "all_sizes_code": {"code": all_sizes, "title": titles[all_sizes]},
            "size_codes_with_titles": [
                {"code": s, "title": titles.get(s)}
                for s in sorted(logging_rows["size_code"].unique().to_list())
            ],
            "years_checked": list(c.WINDOW_YEARS),
            "stage6_reroute_required": verdict,
        },
    )
    print(f"SRC-QSIZE-002 simultaneous state x 113310 x size: {verdict}")
    print(finest)
    if verdict:
        print("!! Stage 6 must be re-routed to brainstorming: §2.2 row 3's premise no longer holds")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the predicate tests to verify they pass**

Run:

```bash
PYTHONPATH=scripts/audit uv run --no-project --with httpx --with polars --with pytest \
  pytest tests/audit/test_size_predicate.py -q
```

Expected: PASS — 5 passed.

- [ ] **Step 5: Run the scan**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/qcew_size.py
```

Expected: two or three stdout lines — the boolean verdict, the prose statement of what the
file does carry, and the Stage 6 re-route warning only when the verdict is `True`. Both
verdicts are legitimate findings.

- [ ] **Step 6: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/qcew_size/summary.json"))["findings"]
assert isinstance(f["simultaneous_state_industry_size"], bool)
assert f["agglvl_inventory"], "no aggregation levels found in the by-size product"
assert len(f["years_checked"]) == 8
print("verdict:", f["simultaneous_state_industry_size"])
print(f["what_the_file_does_carry"])
for row in f["agglvl_inventory"]:
    if row["has_113310"]:
        print(row)
PY
```

Expected: the assertions hold; at least one inventory row prints with `has_113310: true`. If
**no** aggregation level carries 113310 at all, that is itself a finding — record it and set
`what_the_file_does_carry` to say the by-size product has no Logging detail at any geography.

- [ ] **Step 7: Commit**

```bash
git add scripts/audit/qcew_size.py tests/audit/test_size_predicate.py
git commit -m "feat(audit): prove QCEW by-size dimensionality for 113310 (SRC-QSIZE-002)"
```

---

### Task 7: CBP metadata enumeration and the keyed 113310 extract

Closes: the audit half of `SRC-CBP-001` — *"The pipeline MUST discover the vintage-specific
NAICS predicate and official `EMPSZES` values from metadata"* — which the roadmap records as
the *"keyed CBP execution enumerating `EMPSZES`/`LFO` per vintage"* that every review flagged
unresolved.

**Files:**
- Create: `scripts/audit/cbp_metadata.py`

**Interfaces:**
- Consumes: `_common`; `CENSUS_API_KEY` from the environment.
- Produces: `data/raw/audit/cbp_metadata/summary.json` (source key `cbp_metadata`) plus, per
  available year, `dataset.json`, `variables.json`, `empszes.json`, `lfo.json` and
  `data_113310.json` under `data/raw/audit/cbp_metadata/{year}/`.
  `findings` keys:
  - `years_available` — list of ints among 2017–2024 whose `cbp.json` returns 200.
  - `dataset_probe_status_by_year` — mapping every window year (always all eight) to the raw
    `cbp.json` probe status. `0` means a transport failure survived no retry (`probe` does not
    retry) and must not be read as a confirmed absence; re-run this task to resolve it.
  - `naics_predicate_by_year` — mapping year → the variable name matching `^NAICS[0-9]{4}$`
    (e.g. `NAICS2017`). More than one match is recorded as a list, never silently narrowed.
  - `empszes_by_year` — mapping year → list of `{code, label}`.
  - `lfo_by_year` — mapping year → list of `{code, label}`, or `null` when `LFO` is not a
    variable for that year.
  - `working_query_by_year` — the exact `get`/predicate combination that returned data, with
    `key` elided, plus `size_crossing_available: bool` recording whether the successful query
    still carried `EMPSZES`.
  - `geography_levels_by_year` — the geography level names the year's `geography.json` offers,
    so a failed `for=state:*` can be told apart from an unavailable crossing.
  - `rows_113310_by_year` — mapping year → row count returned for `for=state:*`.
  - `flag_values_by_year` — mapping year → `{"EMP_F": [...], "EMP_N": [...]}` distinct values
    observed. Task 8 consumes this.

**Keyless vs keyed.** `cbp.json`, `variables.json`, and the per-variable value files need no
API key; only the data pull does. The key travels in `params`, never in a recorded URL — see
`_common.assert_no_secrets`.

- [ ] **Step 1: Write the script**

Create `scripts/audit/cbp_metadata.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-CBP-001: discover CBP's NAICS predicate, EMPSZES and LFO code lists per vintage from
metadata, then execute one keyed 113310 pull per available year."""

from __future__ import annotations

import json
import os
import re

import httpx

import _common as c

SOURCE = "cbp_metadata"
BASE = "https://api.census.gov/data/{year}/cbp"
NAICS_RE = re.compile(r"^NAICS\d{4}$")


def value_list(client: httpx.Client, year: int, variable: str,
               extracts: list) -> list[dict] | None:
    url = f"{BASE.format(year=year)}/variables/{variable}.json"
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError:
        return None
    extracts.append(c.record_extract(
        SOURCE, url, f"{year}/{variable.lower()}.json", resp.content))
    payload = resp.json()
    items = (payload.get("values") or {}).get("item") or {}
    return [{"code": k, "label": v} for k, v in sorted(items.items())]


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")

    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    years, predicates, empszes, lfo = [], {}, {}, {}
    working, rows, flags, geo_levels = {}, {}, {}, {}
    probe_status: dict[str, int] = {}

    for year in c.WINDOW_YEARS:
        status, _ = c.probe(client, f"{BASE.format(year=year)}.json")
        probe_status[str(year)] = status
        if status == 0:
            # probe() has no retry and returns (0, 0) on a TransportError; an http_status of
            # 0 is a transient failure, not a finding — re-run this task rather than reading
            # the year as absent.
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
        matches = sorted(n for n in names if NAICS_RE.match(n))
        predicates[str(year)] = matches if len(matches) != 1 else matches[0]

        empszes[str(year)] = value_list(client, year, "EMPSZES", extracts)
        lfo[str(year)] = value_list(client, year, "LFO", extracts) if "LFO" in names else None

        naics = matches[0] if matches else None
        if naics is None:
            rows[str(year)] = 0
            continue
        gresp = c.request(client, f"{BASE.format(year=year)}/geography.json")
        extracts.append(c.record_extract(
            SOURCE, f"{BASE.format(year=year)}/geography.json", f"{year}/geography.json",
            gresp.content))
        geo_levels[str(year)] = sorted(
            {g["name"] for g in gresp.json().get("fips", []) if "name" in g})

        get_cols = ["NAME", f"{naics}_LABEL", "EMPSZES", "EMPSZES_LABEL", "ESTAB", "EMP",
                    "EMP_F", "EMP_N"]
        no_size = [col for col in get_cols if not col.startswith("EMPSZES")]
        # Attempt 3 drops EMPSZES entirely. If it succeeds where 1 and 2 fail, the size
        # crossing is genuinely unavailable for this vintage — a finding. If it also fails,
        # the query itself is wrong — a bug. Step 3 below relies on that distinction.
        attempts = [
            {"get": ",".join(get_cols), "for": "state:*", naics: c.INDUSTRY_CODE,
             "LFO": "001", "key": key},
            {"get": ",".join(get_cols), "for": "state:*", naics: c.INDUSTRY_CODE, "key": key},
            {"get": ",".join(no_size), "for": "state:*", naics: c.INDUSTRY_CODE, "key": key},
        ]
        for params in attempts:
            try:
                dresp = c.request(client, BASE.format(year=year), params=params)
            except httpx.HTTPStatusError:
                continue
            extracts.append(c.record_extract(
                SOURCE, BASE.format(year=year), f"{year}/data_113310.json", dresp.content))
            payload = dresp.json()
            header, body = payload[0], payload[1:]
            working[str(year)] = {k: v for k, v in params.items() if k != "key"}
            working[str(year)]["size_crossing_available"] = "EMPSZES" in set(header)
            rows[str(year)] = len(body)
            idx = {name: i for i, name in enumerate(header)}
            flags[str(year)] = {
                col: sorted({(r[idx[col]] or "") for r in body})
                for col in ("EMP_F", "EMP_N") if col in idx
            }
            break
        else:
            working[str(year)] = None
            rows[str(year)] = 0
            flags[str(year)] = {}

    covered = f"{min(years)}-{max(years)}" if years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y not in years)
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(years)) if years else "",
            "published_end": str(max(years)) if years else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": covered, "uncovered": uncovered,
        },
        access={"route": BASE, "status": "verified" if years else "not_obtainable",
                "reason": None if years else "no window year returned a CBP dataset document"},
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
        },
    )
    print(f"CBP years available: {years}")
    print(f"NAICS predicates: {json.dumps(predicates)}")
    print(f"window years with no CBP: {uncovered or 'none'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/cbp_metadata.py
```

Expected: three stdout lines — the available-year list, the per-year NAICS predicate mapping,
and the window years with no CBP. CBP publishes with a multi-year lag, so a
non-empty `uncovered` is likely and is a first-class finding: Stage 2's hard-control
eligibility, Stage 3's CBP-intensity baseline, and Stage 6's benchmark all need to know which
window years have no CBP anchor.

- [ ] **Step 3: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
s = json.load(open("data/raw/audit/cbp_metadata/summary.json"))
f = s["findings"]
assert f["years_available"], "no CBP year responded — investigate before continuing"
for y in f["years_available"]:
    p = f["naics_predicate_by_year"][str(y)]
    assert isinstance(p, str), f"{y}: {p} — more than one NAICS predicate, resolve by hand"
    assert f["empszes_by_year"][str(y)], f"{y}: EMPSZES value list is empty"
    print(y, p, "EMPSZES:", len(f["empszes_by_year"][str(y)]),
          "LFO:", None if f["lfo_by_year"][str(y)] is None else len(f["lfo_by_year"][str(y)]),
          "rows:", f["rows_113310_by_year"][str(y)])
print("coverage:", s["coverage_span"]["covered"], "| uncovered:", s["coverage_span"]["uncovered"])
import subprocess
out = subprocess.run(["grep", "-r", "-l", "key=", "data/raw/audit/cbp_metadata/"],
                     capture_output=True, text=True).stdout
assert not out.strip(), f"a recorded artifact contains a key parameter: {out}"
PY
```

Expected: one line per available year showing its predicate, `EMPSZES` count, `LFO` count (or
`None`), and 113310 row count; then the coverage line; and no key leak.

**Read a zero row count carefully — the two causes are different findings.** For any year with
`rows_113310_by_year == 0`, check `geography_levels_by_year[year]`: if `state` is absent, the
`for=state:*` predicate is wrong for that vintage and this is a *script bug* to fix. If `state`
is present and even the third attempt (which drops `EMPSZES`) returned nothing, the query is
still wrong. Only when the third attempt succeeds while the first two fail —
`working_query_by_year[year]["size_crossing_available"] == false` — is the honest finding "the
state x six-digit x `EMPSZES` crossing is unavailable for this vintage." Record that in
`notes`; do not let a query bug masquerade as it.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/cbp_metadata.py
git commit -m "feat(audit): enumerate CBP NAICS predicate, EMPSZES and LFO per vintage"
```

---

### Task 8: CBP disclosure regime by reference year

Closes: the audit half of `SRC-CBP-003` — *"It MUST store the disclosure regime by reference
year and fail closed on an unknown regime."* Stage 1 builds the registry that fails closed;
Stage 0 supplies the evidence and, where the evidence is inconclusive, records `unknown` so
Stage 1's fail-closed path is exercised honestly rather than papered over.

**Files:**
- Create: `scripts/audit/cbp_regime.py`

**Interfaces:**
- Consumes: `_common`; `load_summary("cbp_metadata")["findings"]` for
  `flag_values_by_year`, `years_available`, and the recorded `data_113310.json` extracts.
- Produces: `data/raw/audit/cbp_regime/summary.json` (source key `cbp_regime`).
  `findings` keys:
  - `regime_by_year` — mapping year → `{"regime": str, "evidence": str, "citation": str}`.
    `regime` is a short label the auditor writes (for example `noise_infusion`,
    `cell_suppression`, `noise_infusion_plus_suppression`) or the literal `unknown`.
  - `unknown_years` — list of years whose regime is `unknown`. **Stage 1 must fail closed on
    every year in this list.**
  - `flag_evidence_by_year` — mapping year → `{"EMP_F": {...counts}, "EMP_N": {...counts},
    "suppressed_share": float, "noise_flagged_share": float}` computed from the 113310 state
    rows Task 7 pulled.
  - `documentation_fetched` — list of `{url, http_status}` for each methodology page consulted.

**Do not infer a regime from flag counts alone.** The flag distribution is *evidence*; the
regime label needs a citation to Census documentation for that reference year. Where no such
documentation is found, `unknown` is the correct answer and the exit criterion is satisfied by
writing "not obtainable — no published disclosure-methodology statement located for this
reference year" into `evidence`.

- [ ] **Step 1: Write the script**

Create `scripts/audit/cbp_regime.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-CBP-003: record the CBP disclosure regime per reference year, with flag evidence from
the 113310 pulls and a citation per year. `unknown` is a permitted, first-class answer."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import httpx

import _common as c

SOURCE = "cbp_regime"
DOC_URLS = [
    "https://www.census.gov/programs-surveys/cbp/technical-documentation/methodology.html",
    "https://www.census.gov/programs-surveys/cbp/technical-documentation.html",
    "https://www.census.gov/programs-surveys/cbp/technical-documentation/records-layouts.html",
]


def flag_evidence(path: str) -> dict:
    payload = json.loads(Path(path).read_text())
    header, body = payload[0], payload[1:]
    idx = {name: i for i, name in enumerate(header)}
    out: dict = {}
    for col in ("EMP_F", "EMP_N"):
        if col in idx:
            out[col] = dict(Counter((row[idx[col]] or "") for row in body))
    total = len(body) or 1
    out["suppressed_share"] = sum(
        n for v, n in out.get("EMP_F", {}).items() if v) / total
    out["noise_flagged_share"] = sum(
        n for v, n in out.get("EMP_N", {}).items() if v) / total
    return out


def main() -> None:
    client = c.build_client()
    meta = c.load_summary("cbp_metadata")
    years = meta["findings"]["years_available"]

    extracts, docs = [], []
    for url in DOC_URLS:
        try:
            resp = c.request(client, url)
        except httpx.HTTPStatusError as exc:
            docs.append({"url": url, "http_status": exc.response.status_code})
            continue
        docs.append({"url": url, "http_status": resp.status_code})
        extracts.append(c.record_extract(
            SOURCE, url, f"docs/{url.rstrip('/').rsplit('/', 1)[-1]}", resp.content))

    evidence = {}
    for year in years:
        path = next(
            (e["path"] for e in meta["extracts"]
             if e["path"].endswith(f"{year}/data_113310.json")), None)
        evidence[str(year)] = flag_evidence(path) if path else {}

    # Written by the auditor after reading the fetched documentation. `unknown` is permitted
    # and is the correct answer when no per-year methodology statement was located.
    regime_by_year = {
        str(year): {"regime": "unknown", "evidence": "", "citation": ""} for year in years
    }

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(years)) if years else "",
            "published_end": str(max(years)) if years else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": meta["coverage_span"]["covered"],
            "uncovered": meta["coverage_span"]["uncovered"],
        },
        access={"route": "; ".join(DOC_URLS), "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "regime_by_year": regime_by_year,
            "unknown_years": [int(y) for y, v in regime_by_year.items()
                              if v["regime"] == "unknown"],
            "flag_evidence_by_year": evidence,
            "documentation_fetched": docs,
        },
    )
    for year, ev in evidence.items():
        print(year, "suppressed", round(ev.get("suppressed_share", 0), 3),
              "noise-flagged", round(ev.get("noise_flagged_share", 0), 3),
              "EMP_F values", sorted(ev.get("EMP_F", {})))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and read the fetched documentation**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/cbp_regime.py
```

Expected: one line per available CBP year showing the suppressed share, the noise-flagged
share, and the distinct `EMP_F` values observed on 113310 state rows.

- [ ] **Step 3: Fill in the regime labels by hand, from the fetched documentation**

Open every file under `data/raw/audit/cbp_regime/docs/` and, for each year, set `regime`,
`evidence` (one sentence naming what in the document establishes it), and `citation` (the URL
plus the section heading) in the `regime_by_year` literal in `cbp_regime.py`. Leave `unknown`
where no per-year statement exists, and write the reason into `evidence` in the form
`"not obtainable — <why>"`. Re-run the script.

- [ ] **Step 4: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/cbp_regime/summary.json"))["findings"]
for year, entry in sorted(f["regime_by_year"].items()):
    assert entry["evidence"], f"{year}: evidence is blank — every year needs a filled or " \
                              f"'not obtainable — why' evidence line"
    if entry["regime"] != "unknown":
        assert entry["citation"], f"{year}: a non-unknown regime needs a citation"
    print(year, entry["regime"], "|", entry["evidence"][:80])
print("Stage 1 must fail closed on:", f["unknown_years"])
PY
```

Expected: one line per year with a non-blank evidence sentence; the `unknown_years` list prints
(possibly empty).

- [ ] **Step 5: Commit**

```bash
git add scripts/audit/cbp_regime.py
git commit -m "feat(audit): record the CBP disclosure regime per reference year (SRC-CBP-003)"
```

---

### Task 9: Per-state CES publication level

Closes: the audit half of `SRC-OTH-003` and the roadmap's *"per-state CES publication level
(1133, 113, or supersector)"*. D6 makes this consequential: *"CES stays in scope: NAICS
`1133 → 11331 → 113310` verified against the official structure files for both the 2017 and
2022 vintages, so 113310 is the only six-digit industry under 1133 and a state CES series
published at 1133 covers exactly the target industry… A series published only at 113 or at the
Mining-and-Logging supersector is genuinely broader and keeps its proxy-only treatment."* Stage
7's exit criterion requires each CES series to be labelled with the level actually published
for its state.

**Files:**
- Create: `scripts/audit/ces_levels.py`

**Interfaces:**
- Consumes: `_common`.
- Produces: `data/raw/audit/ces/summary.json` (source key `ces`) plus the fetched `sm.*` flat
  files under `data/raw/audit/ces/`.
  `findings` keys:
  - `logging_industry_codes` — list of `{industry_code, industry_name, embedded_naics,
    level}` for every SAE industry code whose embedded NAICS begins `113` or which is the
    Mining-and-Logging supersector. `level` is one of `113310`, `1133`, `113`, `supersector`,
    `other`.
  - `publication_level_by_state` — mapping two-digit state FIPS → the **finest** level with a
    statewide all-employees series overlapping the D1 window, or `none`.
  - `series_by_state` — mapping state FIPS → list of `{series_id, industry_code, level,
    begin_year, end_year}`.
  - `states_with_113310` / `states_with_1133` / `states_with_113_only` /
    `states_with_supersector_only` / `states_with_other` / `states_with_none` — the six counts,
    so Stage 7 can size the ablation.
  - `derived_codes` — `{all_employees_data_type, statewide_area}`, the two selector codes read
    from `sm.data_type` and `sm.area` rather than hardcoded.

**Derive the selector codes, never assert them.** The all-employees data-type code and the
statewide area code are read from the fetched `sm.data_type` and `sm.area` files by matching
their published titles. Hardcoding either would let a silent mismatch report
`states_with_none: 51`, which reads as a devastating finding about CES coverage when it is
really a typo.

**How the level is derived.** An SAE industry code embeds its NAICS code left-justified in
positions 3–8, zero-padded. Stripping trailing zeros from `industry_code[2:8]` recovers the
NAICS digits; the number of digits recovered is the publication level. A code with no NAICS
digits is a supersector. Derive the level this way — do not pattern-match on names.

- [ ] **Step 1: Write the script**

Create `scripts/audit/ces_levels.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0"]
# ///
"""SRC-OTH-003: determine, per state, the finest CES/SAE industry level at which a statewide
all-employees series covering the D1 window is published for Logging."""

from __future__ import annotations

import io

import polars as pl

import _common as c

SOURCE = "ces"
BASE = "https://download.bls.gov/pub/time.series/sm/"
FILES = ("sm.industry", "sm.series", "sm.state", "sm.data_type", "sm.area")


def sole_code(df: pl.DataFrame, code_col: str, text_col: str, pattern: str, what: str) -> str:
    """Derive a code from its published title. Global Constraints forbid hardcoding a code
    that the fetched metadata can supply — the same rule that governs QCEW's own_code."""
    hits = df.filter(pl.col(text_col).str.contains(pattern))
    if hits.height != 1:
        raise RuntimeError(
            f"expected exactly one {what} row matching {pattern!r}, got "
            f"{hits.select(code_col, text_col).to_dicts()}")
    return hits[code_col][0]


def read_tsv(content: bytes) -> pl.DataFrame:
    """BLS flat files pad both headers and values with spaces, and some rows are ragged."""
    df = pl.read_csv(io.BytesIO(content), separator="\t", infer_schema_length=0,
                     truncate_ragged_lines=True)
    # Rename first, then strip values off the RENAMED frame — reusing the pre-rename
    # `df.columns` here looks up padded names that no longer exist.
    df = df.rename({col: col.strip() for col in df.columns})
    return df.with_columns(pl.col(pl.Utf8).str.strip_chars())


def embedded_naics(industry_code: str) -> str:
    return industry_code[2:8].rstrip("0")


def level_of(industry_code: str) -> str:
    naics = embedded_naics(industry_code)
    # Zero-padding makes 11331 and 113310 indistinguishable after rstrip("0") — both come out
    # "11331" — but both denote Logging at its finest published level, so catch them first.
    if naics.startswith("1133") and len(naics) > 4:
        return "113310"
    if naics == "1133":
        return "1133"
    if naics == "113":
        return "113"
    if naics == "":
        return "supersector"
    return "other"


FINEST = {"113310": 0, "1133": 1, "113": 2, "supersector": 3, "other": 4, "none": 5}


def main() -> None:
    client = c.build_client()
    extracts, frames = [], {}
    for name in FILES:
        resp = c.request(client, BASE + name)
        extracts.append(c.record_extract(SOURCE, BASE + name, name, resp.content))
        frames[name] = read_tsv(resp.content)

    # Anchored on the full published title: a looser "^all employees" also matches the
    # 3-month-average-change series.
    all_employees = sole_code(frames["sm.data_type"], "data_type_code", "data_type_text",
                              r"(?i)^all employees, in thousands$", "sm.data_type")
    statewide_area = sole_code(frames["sm.area"], "area_code", "area_name",
                               r"(?i)^statewide$", "sm.area")

    industry = frames["sm.industry"]
    candidates = industry.with_columns(
        embedded=pl.col("industry_code").map_elements(embedded_naics, return_dtype=pl.Utf8),
        level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8),
    ).filter(
        pl.col("embedded").str.starts_with("113")
        | ((pl.col("level") == "supersector")
           & pl.col("industry_name").str.contains("(?i)logging"))
    )

    codes = set(candidates["industry_code"].to_list())
    series = frames["sm.series"].filter(
        pl.col("industry_code").is_in(sorted(codes))
        & (pl.col("data_type_code") == all_employees)
        & (pl.col("area_code") == statewide_area)
        & (pl.col("begin_year").cast(pl.Int32) <= max(c.WINDOW_YEARS))
        & (pl.col("end_year").cast(pl.Int32) >= min(c.WINDOW_YEARS))
    ).with_columns(
        level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8)
    )

    by_state: dict[str, list[dict]] = {}
    for row in series.iter_rows(named=True):
        by_state.setdefault(row["state_code"], []).append({
            "series_id": row["series_id"], "industry_code": row["industry_code"],
            "level": row["level"], "begin_year": int(row["begin_year"]),
            "end_year": int(row["end_year"]),
        })

    all_states = sorted(frames["sm.state"]["state_code"].to_list())
    level_by_state = {
        st: min((s["level"] for s in by_state.get(st, [])), key=lambda x: FINEST[x],
                default="none")
        for st in all_states
    }
    tally = {lvl: sum(1 for v in level_by_state.values() if v == lvl)
             for lvl in ("113310", "1133", "113", "supersector", "other", "none")}

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(series["begin_year"].cast(pl.Int32).min() or ""),
            "published_end": str(series["end_year"].cast(pl.Int32).max() or ""),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": f"{c.WINDOW_START}-{c.WINDOW_END} for states with a qualifying series",
            "uncovered": f"{tally['none']} state(s) publish no Logging-related statewide "
                         f"all-employees series overlapping the window",
        },
        access={"route": BASE + "<file>", "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "logging_industry_codes": candidates.select(
                "industry_code", "industry_name", "embedded", "level"
            ).rename({"embedded": "embedded_naics"}).to_dicts(),
            "publication_level_by_state": level_by_state,
            "series_by_state": by_state,
            "states_with_113310": tally["113310"],
            "states_with_1133": tally["1133"],
            "states_with_113_only": tally["113"],
            "states_with_supersector_only": tally["supersector"],
            "states_with_other": tally["other"],
            "states_with_none": tally["none"],
            "derived_codes": {"all_employees_data_type": all_employees,
                              "statewide_area": statewide_area},
        },
    )
    print("CES publication level tally:", tally)
    print("derived codes — data_type:", all_employees, "| area:", statewide_area)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/ces_levels.py
```

Expected: two stdout lines — the tally
`CES publication level tally: {'113310': <int>, '1133': <int>, '113': <int>, 'supersector': <int>, 'other': <int>, 'none': <int>}`
and the two derived selector codes. If `sole_code` raises, the titles it printed show what the
file actually contains — widen the pattern to match the published wording, never fall back to a
literal code.
The six counts sum to the number of `sm.state` codes, which includes non-state areas — record
that denominator rather than forcing it to 51.

- [ ] **Step 3: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
f = json.load(open("data/raw/audit/ces/summary.json"))["findings"]
assert f["logging_industry_codes"], "no Logging-related SAE industry code found"
assert f["publication_level_by_state"], "no states enumerated"
for row in f["logging_industry_codes"]:
    print(row["industry_code"], row["embedded_naics"] or "(supersector)", row["level"],
          "|", row["industry_name"])
print("113310:", f["states_with_113310"], "1133:", f["states_with_1133"],
      "113 only:", f["states_with_113_only"],
      "supersector only:", f["states_with_supersector_only"],
      "other:", f["states_with_other"], "none:", f["states_with_none"])
PY
```

Expected: at least one industry-code line prints, then the six counts. If `states_with_113310`
and `states_with_1133` are both `0`, that is a finding with real consequences for Stage 7 —
D6's industry-alignment claim would then apply to no state, and every CES series stays
proxy-only.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/ces_levels.py
git commit -m "feat(audit): determine the per-state CES publication level for Logging"
```

---

### Task 10: BDS finest industry detail

Closes: the audit half of `SRC-OTH-002` — *"BDS industry detail MUST be discovered; six-digit
Logging detail must not be invented."* §5.3's BDS guardrail is *"Do not imply six-digit Logging
detail that is not present."* The only honest way to establish the ceiling is to ask the API
for progressively finer codes and record where it stops answering.

**Files:**
- Create: `scripts/audit/bds_detail.py`

**Interfaces:**
- Consumes: `_common`; `CENSUS_API_KEY`.
- Produces: `data/raw/audit/bds/summary.json` (source key `bds`) plus `variables.json` and one
  response per probed NAICS code.
  `findings` keys:
  - `naics_probe` — list of `{naics, digits, http_status, row_count, years_returned}` for the
    codes `11`, `113`, `1133`, `11331`, `113310`.
  - `finest_naics_available` — the longest probed code that returned rows, or `null`.
  - `six_digit_logging_available` — bool. Must be `false` for §5.3's guardrail to hold as
    written; if it is `true`, record it and flag Stage 7.
  - `years_available` — sorted list of years the API returned.
  - `variables_present` — the subset of `ESTAB`, `FIRM`, `JOB_CREATION`, `JOB_DESTRUCTION`,
    `ESTABS_ENTRY`, `ESTABS_EXIT` that appear in `variables.json`.

- [ ] **Step 1: Write the script**

Create `scripts/audit/bds_detail.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-OTH-002: discover the finest NAICS detail BDS actually serves for the Logging branch."""

from __future__ import annotations

import os

import httpx

import _common as c

SOURCE = "bds"
BASE = "https://api.census.gov/data/timeseries/bds"
CANDIDATES = ("11", "113", "1133", "11331", "113310")
WANTED_VARS = ("ESTAB", "FIRM", "JOB_CREATION", "JOB_DESTRUCTION", "ESTABS_ENTRY",
               "ESTABS_EXIT")


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")
    client = c.build_client()
    extracts = []

    vresp = c.request(client, f"{BASE}/variables.json")
    extracts.append(c.record_extract(SOURCE, f"{BASE}/variables.json", "variables.json",
                                     vresp.content))
    names = set(vresp.json()["variables"].keys())
    present = [v for v in WANTED_VARS if v in names]

    probe, years = [], set()
    for naics in CANDIDATES:
        params = {"get": "YEAR,ESTAB", "for": "state:*", "NAICS": naics, "key": key}
        try:
            resp = c.request(client, BASE, params=params)
        except httpx.HTTPStatusError as exc:
            probe.append({"naics": naics, "digits": len(naics),
                          "http_status": exc.response.status_code, "row_count": 0,
                          "years_returned": []})
            continue
        extracts.append(c.record_extract(SOURCE, BASE, f"naics_{naics}.json", resp.content))
        payload = resp.json()
        header, body = payload[0], payload[1:]
        yidx = header.index("YEAR")
        got = sorted({int(r[yidx]) for r in body})
        years.update(got)
        probe.append({"naics": naics, "digits": len(naics), "http_status": resp.status_code,
                      "row_count": len(body), "years_returned": got})

    answering = [p for p in probe if p["row_count"] > 0]
    finest = max((p["naics"] for p in answering), key=len, default=None)
    six_digit = any(p["naics"] == "113310" and p["row_count"] > 0 for p in probe)

    # `covered` (Task 1 schema) is the part of D1's window this source covers — clamp to the
    # window; `years` can include years the API returns outside it.
    covered_years = sorted(years & set(c.WINDOW_YEARS))
    covered = f"{min(covered_years)}-{max(covered_years)}" if covered_years else ""
    uncovered = ",".join(
        str(y) for y in c.WINDOW_YEARS if years and y not in years) or (
        "" if years else f"{c.WINDOW_START}-{c.WINDOW_END}")
    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(min(years)) if years else "",
            "published_end": str(max(years)) if years else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": covered, "uncovered": uncovered,
        },
        access={"route": BASE, "status": "verified" if answering else "not_obtainable",
                "reason": None if answering else "no probed NAICS code returned rows"},
        extracts=extracts,
        findings={
            "naics_probe": probe,
            "finest_naics_available": finest,
            "six_digit_logging_available": six_digit,
            "years_available": sorted(years),
            "variables_present": present,
        },
    )
    print("BDS finest NAICS:", finest, "| six-digit Logging:", six_digit)
    for p in probe:
        print(" ", p["naics"], "->", p["http_status"], f"{p['row_count']} rows")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/bds_detail.py
```

Expected: a summary line naming the finest NAICS code that returned rows, then one line per
probed code with its status and row count. A `404` or a zero row count at the finer codes is
the expected *kind* of result and is the finding; do not retry until one succeeds.

- [ ] **Step 3: Verify the summary's shape**

Run:

```bash
python3 - <<'PY'
import json
s = json.load(open("data/raw/audit/bds/summary.json"))
f = s["findings"]
assert len(f["naics_probe"]) == 5, "all five candidate codes must be probed"
assert any(p["row_count"] > 0 for p in f["naics_probe"]), "BDS answered nothing at all"
print("finest:", f["finest_naics_available"], "| six-digit:", f["six_digit_logging_available"])
print("years:", f["years_available"][:3], "...", f["years_available"][-3:])
print("uncovered window years:", s["coverage_span"]["uncovered"] or "none")
PY
```

Expected: the assertions hold; the finest code, six-digit boolean, year range, and uncovered
window years print.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/bds_detail.py
git commit -m "feat(audit): discover the finest BDS NAICS detail for Logging (SRC-OTH-002)"
```

---

### Task 11: SUSB detailed-sizes file layout

Closes: the roadmap's *"SUSB detailed-sizes file layout"*, which feeds `SRC-OTH-001` —
*"SUSB data MUST preserve enterprise-size semantics"* — and `INV-010`, *"Firm-size or
enterprise-size data are never relabeled as establishment size."* The Copilot review's open
item is explicit: *"SUSB file layouts should be inspected before claiming any detailed
state-industry-size cross-tab beyond the published enterprise-size description."*

**Files:**
- Create: `scripts/audit/susb_layout.py`

**Interfaces:**
- Consumes: `_common`.
- Produces: `data/raw/audit/susb/summary.json` (source key `susb`) plus the fetched directory
  listing and data files.
  `findings` keys:
  - `latest_year` — the newest year directory found under
    `https://www2.census.gov/programs-surveys/susb/tables/`.
  - `files_found` — the filenames in that year directory.
  - `detailed_sizes_layout` — `{filename, columns, row_count, size_column, size_values,
    industry_code_lengths, geography_levels}` for `us_state_naics_detailedsizes_<year>`.
  - `six_digit_state_layout` — the same shape for `us_state_6digitnaics_<year>`.
  - `size_concept` — `enterprise` | `establishment` | `unclear`, with the column name and
    header text that establishes it. `INV-010` depends on this being read from the file, not
    assumed.
  - `has_113310_at_state` — bool, per file.
  - `detailed_sizes_reaches_six_digit_at_state` — bool. This is the claim the review warns
    against assuming.

- [ ] **Step 1: Write the script**

Create `scripts/audit/susb_layout.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "polars>=1.0", "fastexcel>=0.11"]
# ///
"""Inspect the SUSB state files' actual layout so no detailed state-industry-size cross-tab is
claimed beyond what the header shows, and so the size concept is read rather than assumed."""

from __future__ import annotations

import io
import re

import polars as pl

import _common as c

SOURCE = "susb"
ROOT = "https://www2.census.gov/programs-surveys/susb/tables/"
TARGETS = ("us_state_naics_detailedsizes", "us_state_6digitnaics")


def year_dirs(html: str) -> list[int]:
    return sorted({int(y) for y in re.findall(r'href="(\d{4})/"', html)})


def filenames(html: str) -> list[str]:
    return sorted(set(re.findall(r'href="([^"/]+\.(?:txt|xlsx|zip))"', html)))


def read_table(path: str, content: bytes) -> pl.DataFrame:
    """Prefer the .txt variant: it is plain CSV with one header row. The .xlsx fallback often
    carries title rows above the header, so Step 3 asks you to eyeball its parsed columns."""
    if path.endswith(".txt"):
        return pl.read_csv(io.BytesIO(content), infer_schema_length=0)
    return pl.read_excel(io.BytesIO(content))  # no infer_schema_length kwarg on read_excel


def describe(df: pl.DataFrame) -> dict:
    cols = df.columns
    size_col = next(
        (col for col in cols if re.search(r"(?i)(enterprise|establishment).*size|empl?size", col)),
        None)
    naics_col = next((col for col in cols if re.search(r"(?i)naics", col)), None)
    geo_col = next((col for col in cols if re.search(r"(?i)state|geo", col)), None)
    codes = (df[naics_col].drop_nulls().cast(pl.Utf8).str.replace_all("-", "")
             if naics_col else pl.Series([], dtype=pl.Utf8))
    return {
        "columns": cols,
        "row_count": df.height,
        "size_column": size_col,
        "size_values": sorted(set(df[size_col].drop_nulls().cast(pl.Utf8).to_list()))[:40]
        if size_col else [],
        "industry_code_lengths": sorted({len(v) for v in codes.to_list()}) if naics_col else [],
        "geography_levels": sorted(set(df[geo_col].drop_nulls().cast(pl.Utf8).to_list()))[:10]
        if geo_col else [],
        "has_113310": bool(naics_col and (codes == c.INDUSTRY_CODE).any()),
    }


def main() -> None:
    client = c.build_client()
    extracts = []

    root = c.request(client, ROOT)
    extracts.append(c.record_extract(SOURCE, ROOT, "tables_index.html", root.content))
    years = year_dirs(root.text)
    if not years:
        raise RuntimeError("no year directories parsed from the SUSB tables index")
    latest = years[-1]

    ydir = f"{ROOT}{latest}/"
    ylist = c.request(client, ydir)
    extracts.append(c.record_extract(SOURCE, ydir, f"{latest}_index.html", ylist.content))
    names = filenames(ylist.text)

    layouts: dict[str, dict] = {}
    for stem in TARGETS:
        candidates = [n for n in names if n.startswith(stem)]
        txt = next((n for n in candidates if n.endswith(".txt")), None)
        chosen = txt or next((n for n in candidates if n.endswith(".xlsx")), None)
        if chosen is None:
            layouts[stem] = {"filename": None, "note": "not obtainable — no matching file "
                                                       f"under {ydir}"}
            continue
        url = ydir + chosen
        rec = c.download_extract(client, SOURCE, url, chosen)
        extracts.append(rec)
        df = read_table(chosen, open(rec.path, "rb").read())
        layouts[stem] = {"filename": chosen, **describe(df)}

    detailed = layouts["us_state_naics_detailedsizes"]
    six = layouts["us_state_6digitnaics"]
    size_col = (detailed.get("size_column") or "")
    concept = ("enterprise" if "enterprise" in size_col.lower()
               else "establishment" if "establishment" in size_col.lower()
               else "unclear")

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(years[0]), "published_end": str(latest),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": f"through {latest}",
            "uncovered": ",".join(str(y) for y in c.WINDOW_YEARS if y > latest),
        },
        access={"route": ROOT + "{year}/", "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "latest_year": latest,
            "files_found": names,
            "detailed_sizes_layout": detailed,
            "six_digit_state_layout": six,
            "size_concept": concept,
            "has_113310_at_state": {
                "detailed_sizes": detailed.get("has_113310"),
                "six_digit": six.get("has_113310"),
            },
            "detailed_sizes_reaches_six_digit_at_state": bool(
                detailed.get("has_113310") and 6 in (detailed.get("industry_code_lengths") or [])
            ),
        },
    )
    print("SUSB latest year:", latest, "| size concept:", concept)
    print("detailed-sizes reaches six-digit at state:",
          bool(detailed.get("has_113310") and 6 in (detailed.get("industry_code_lengths") or [])))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/susb_layout.py
```

Expected: two stdout lines — the latest SUSB year with its size concept, and the six-digit
reach boolean.

- [ ] **Step 3: Verify the summary's shape and confirm the size concept by eye**

Run:

```bash
python3 - <<'PY'
import json
s = json.load(open("data/raw/audit/susb/summary.json"))
f = s["findings"]
assert f["latest_year"], "no SUSB year directory found"
assert f["files_found"], "no data files parsed from the year directory"
for key in ("detailed_sizes_layout", "six_digit_state_layout"):
    print(key, "->", f[key].get("filename"))
    print("   size column:", f[key].get("size_column"))
    print("   naics code lengths:", f[key].get("industry_code_lengths"))
    print("   has 113310:", f[key].get("has_113310"))
print("size concept:", f["size_concept"])
print("uncovered window years:", s["coverage_span"]["uncovered"] or "none")
PY
```

Expected: both layouts print with a filename, a size column, the NAICS code lengths present,
and the 113310 boolean. **If `size_concept` prints `unclear`, do not leave it there** — open
the file's header row and the Census record layout, decide `enterprise` or `establishment` from
the published text, and record the header wording that decided it in a `note` key. `INV-010`
turns on this field.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/susb_layout.py
git commit -m "feat(audit): inspect the SUSB state file layouts and confirm the size concept"
```

---

### Task 12: TPO and FIA access verdicts

Closes: the audit halves of `SRC-FOR-001`, `SRC-FOR-002`, and `SRC-FOR-003`, plus the §21 row
*"TPO/FIA coverage — Required only after extraction audit."* Stage 7 consumes both verdicts.
§2.2's forestry row binds: *"TPO and FIA MUST be modeled as correlated measurements of a latent
harvest factor, not as independent additive signals. Harvest-origin measures are preferred to
mill-location receipts."* The audit's job is to establish whether a harvest-origin measure is
obtainable at all, and on what terms.

**`not_obtainable` is a legitimate verdict here.** The ChatGPT review records that it could not
reproduce a reliable raw TPO URL, and Appendix A already ships `tpo.enabled: false` and
`fia.enabled: false`. The exit criterion asks for a filled field *or* `"not obtainable — why"`.

**Files:**
- Create: `scripts/audit/forest_sources.py`

**Interfaces:**
- Consumes: `_common`.
- Produces: `data/raw/audit/fia/summary.json` (source key `fia`) and
  `data/raw/audit/tpo/summary.json` (source key `tpo`).
  `fia` `findings` keys:
  - `doc_parameters` — the `/fullreport` parameter names found in the API documentation page,
    each with the one-line description shown there.
  - `probe` — `{url, params_sent, http_status, bytes, content_type, has_sampling_error}` for
    one minimal `/fullreport` call.
  - `sampling_error_field` — the response field carrying sampling error or a confidence
    interval, or `null`. `SRC-FOR-002` requires FIA rows to retain it "when available", so a
    `null` here must be paired with a reason.
  - `evaluation_vintage_field` — the field naming the evaluation vintage / survey cycle
    (`SRC-FOR-003`), or `null`.
  `tpo` `findings` keys:
  - `route_probes` — list of `{url, http_status, bytes, content_type, machine_readable}` for
    each candidate route.
  - `harvest_origin_available` — bool. §8.4 `SRC-FOR-001` requires harvest origin and mill
    receipts to occupy distinct fields; this records whether the origin measure is reachable.
  - `chosen_route` — the URL that yields machine-readable state-year data, or `null`.

- [ ] **Step 1: Write the script**

Create `scripts/audit/forest_sources.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-FOR-001/002/003: record access verdicts for FIA (/fullreport parameters, sampling error,
evaluation vintage) and for TPO harvest-origin data. `not_obtainable` is a valid verdict."""

from __future__ import annotations

import re

import httpx

import _common as c

FIA_DOC = "https://apps.fs.usda.gov/fiadb-api/"
FIA_FULLREPORT = "https://apps.fs.usda.gov/fiadb-api/fullreport"
TPO_CANDIDATES = [
    "https://research.fs.usda.gov/programs/nrum",
    "https://research.fs.usda.gov/products/dataandtools/"
    "timber-products-output-tpo-interactive-reporting-tool",
    "https://apps.fs.usda.gov/fiadb-api/tpo",
]
MACHINE_TYPES = ("json", "csv", "xml", "zip", "excel", "spreadsheet")


def probe_url(client: httpx.Client, url: str, params: dict | None = None) -> dict:
    try:
        resp = client.get(url, params=params)
    except httpx.TransportError as exc:
        return {"url": url, "http_status": 0, "bytes": 0, "content_type": "",
                "error": str(exc)}
    ctype = resp.headers.get("content-type", "")
    return {"url": url, "http_status": resp.status_code, "bytes": len(resp.content),
            "content_type": ctype, "body": resp.content}


def main() -> None:
    client = c.build_client()

    # --- FIA -------------------------------------------------------------------
    fia_extracts, params_doc = [], []
    doc = probe_url(client, FIA_DOC)
    if doc["http_status"] == 200:
        fia_extracts.append(c.record_extract("fia", FIA_DOC, "fiadb_api_doc.html",
                                             doc["body"], http_status=200))
        text = doc["body"].decode("utf-8", "replace")
        for name in sorted(set(re.findall(r"\b(wc|snum|sdenom|rselected|cselected|"
                                          r"outputFormat|schemaName|whereClause)\b", text))):
            window = next((m.group(0) for m in
                           re.finditer(rf".{{0,160}}\b{name}\b.{{0,160}}", text)), "")
            params_doc.append({"parameter": name,
                               "context": re.sub(r"\s+", " ", window).strip()[:240]})

    fia_probe = probe_url(client, FIA_FULLREPORT, params={"outputFormat": "JSON"})
    body_text = fia_probe.get("body", b"").decode("utf-8", "replace")[:200_000]
    if fia_probe["http_status"] == 200:
        fia_extracts.append(c.record_extract("fia", FIA_FULLREPORT, "fullreport_probe.txt",
                                             fia_probe["body"], http_status=200))
    se_field = next((f for f in ("SE", "SE_PERCENT", "sampling_error", "SAMPLING_ERROR",
                                 "ESTIMATE_SE") if f in body_text), None)
    ev_field = next((f for f in ("EVALID", "evalid", "EVAL_GRP", "INVYR", "SURVEY_CYCLE")
                     if f in body_text), None)
    fia_ok = fia_probe["http_status"] == 200 and bool(params_doc)

    c.write_summary(
        "fia",
        coverage_span={
            "published_start": "", "published_end": "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": "inventory evaluation cycles, not calendar months",
            "uncovered": "no monthly resolution: SRC-FOR-004 forbids interpolating to months",
        },
        access={"route": FIA_FULLREPORT,
                "status": "verified" if fia_ok else "documented",
                "reason": None if fia_ok else
                "documentation page reachable but a minimal /fullreport probe did not return "
                "a parsable report; parameters recorded from the documentation only"},
        extracts=fia_extracts,
        findings={
            "doc_parameters": params_doc,
            "probe": {k: v for k, v in fia_probe.items() if k != "body"}
            | {"params_sent": {"outputFormat": "JSON"},
               "has_sampling_error": se_field is not None},
            "sampling_error_field": se_field,
            "evaluation_vintage_field": ev_field,
        },
    )

    # --- TPO -------------------------------------------------------------------
    tpo_extracts, probes = [], []
    chosen = None
    for i, url in enumerate(TPO_CANDIDATES):
        res = probe_url(client, url)
        machine = any(t in res["content_type"].lower() for t in MACHINE_TYPES)
        if res["http_status"] == 200:
            tpo_extracts.append(c.record_extract("tpo", url, f"candidate_{i}.bin",
                                                 res["body"], http_status=200))
        probes.append({k: v for k, v in res.items() if k != "body"}
                      | {"machine_readable": machine})
        if machine and chosen is None:
            chosen = url

    c.write_summary(
        "tpo",
        coverage_span={
            "published_start": "", "published_end": "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": "annual/periodic survey cycles, not calendar months",
            "uncovered": "no monthly resolution: SRC-FOR-004 forbids interpolating to months",
        },
        access={"route": chosen or "; ".join(TPO_CANDIDATES),
                "status": "verified" if chosen else "not_obtainable",
                "reason": None if chosen else
                "not obtainable — no probed route returned machine-readable harvest-origin "
                "data; every candidate served an HTML landing or interactive tool page"},
        extracts=tpo_extracts,
        findings={
            "route_probes": probes,
            "harvest_origin_available": chosen is not None,
            "chosen_route": chosen,
        },
    )
    print("FIA:", "verified" if fia_ok else "documented",
          "| sampling error field:", se_field, "| evaluation field:", ev_field)
    print("TPO:", chosen or "not obtainable")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run:

```bash
set -a && source .env && set +a && uv run --no-project scripts/audit/forest_sources.py
```

Expected: two stdout lines — the FIA status with its two field names (either may be `None`),
and the TPO route or `not obtainable`.

- [ ] **Step 3: Verify both summaries and hand-complete any gap**

Run:

```bash
python3 - <<'PY'
import json
for src in ("fia", "tpo"):
    s = json.load(open(f"data/raw/audit/{src}/summary.json"))
    print(src, "->", s["access"]["status"], "|", (s["access"]["reason"] or "")[:110])
fia = json.load(open("data/raw/audit/fia/summary.json"))["findings"]
print("FIA parameters documented:", [p["parameter"] for p in fia["doc_parameters"]])
if fia["sampling_error_field"] is None:
    print("ACTION: SRC-FOR-002 needs either a sampling-error field or a recorded reason")
PY
```

Expected: both statuses print with a reason wherever the status is not `verified`; the FIA
parameter list prints. Where the automated probe leaves `sampling_error_field` or
`evaluation_vintage_field` as `None`, read the fetched documentation and either fill the field
by hand or write `"not obtainable — <why>"` into a `note` key. `SRC-FOR-002` says FIA
observations must retain sampling errors *"when available"*, so establishing availability is
the deliverable, not obtaining the numbers.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/forest_sources.py
git commit -m "feat(audit): record TPO and FIA access verdicts (SRC-FOR-001/002/003)"
```

---

### Task 13: Assemble the finding, verify every exit criterion, and close the stage

Closes: the stage deliverable `specs/findings/source-audit.md` and every roadmap exit
criterion. Also discharges §1.2's final required-plan bullet — *"states which requirements
cannot be implemented without additional source verification"* — and gives a verdict on the
three §21 rows the stage cites.

**Files:**
- Create: `scripts/audit/verify_extracts.py`
- Create: `scripts/audit/assemble_finding.py`
- Create: `specs/findings/source-audit-notes.md` (hand-written; inlined verbatim by the
  assembler so re-running it never clobbers prose)
- Create: `specs/findings/source-audit.md` (generated)
- Create: `specs/findings/source-audit-extracts.csv` (generated, committed)

**Interfaces:**
- Consumes: every `data/raw/audit/*/summary.json`.
- Produces: `verify_extracts.py` as a **script, not a manual step** — it is the exit gate and is
  re-run whenever the stage is re-checked or a later stage re-validates against what shipped.

- [ ] **Step 1: Write the verifier**

Create `scripts/audit/verify_extracts.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]   # _common imports httpx
# ///
"""Stage 0 exit gate: re-hash every recorded extract, validate every summary against the
Task 1 schema, prove .env is untracked, and emit the committed extract manifest."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as c  # noqa: E402

MANIFEST = c.FINDINGS_DIR / "source-audit-extracts.csv"
FIELDS = ("source", "url", "path", "sha256", "bytes", "retrieved_utc", "http_status")


def main() -> int:
    failures: list[str] = []

    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    if ".env" in tracked:
        failures.append("EXIT CRITERION: .env is tracked by git")

    summaries = sorted(c.AUDIT_ROOT.glob("*/summary.json"))
    if not summaries:
        failures.append("no source summaries found under data/raw/audit/")

    rows: list[dict] = []
    for path in summaries:
        payload = json.loads(path.read_text())
        try:
            c.validate_summary(payload)
        except ValueError as exc:
            failures.append(f"{path}: {exc}")
            continue
        for rec in payload["extracts"]:
            target = Path(rec["path"])
            if not target.exists():
                failures.append(f"{rec['source']}: missing extract {target}")
                continue
            actual = c.sha256_file(target)
            if actual != rec["sha256"]:
                failures.append(
                    f"{rec['source']}: sha256 mismatch for {target}\n"
                    f"  recorded {rec['sha256']}\n  on disk  {actual}")
                continue
            sidecar = target.parent / f"{target.name}.sha256"
            if not sidecar.exists():
                failures.append(f"{rec['source']}: missing sidecar {sidecar}")
                continue
            rows.append({k: rec[k] for k in FIELDS})

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["source"], r["path"])))

    print(f"summaries validated: {len(summaries)}; extracts verified: {len(rows)}")
    print(f"manifest written: {MANIFEST}")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the verifier**

Run:

```bash
uv run --no-project scripts/audit/verify_extracts.py; echo "exit=$?"
```

Expected: `summaries validated: <n>; extracts verified: <n>`, the manifest path, no `FAIL`
lines, and `exit=0`. Any `FAIL` line names a concrete defect — a mismatched hash means the file
on disk changed after it was recorded; re-fetch and re-run the owning task rather than editing
the recorded hash.

- [ ] **Step 3: Write the hand-authored notes**

Create `specs/findings/source-audit-notes.md`. Fill every bracketed slot from the summaries you
have produced; nothing below may remain a placeholder.

```markdown
## SRC-QCEW-006 branch verdict

<paste the exact `verdict_sentence` from data/raw/audit/qcew_identity/summary.json>

**Consequence.** <One sentence naming what this branch means for Stage 2's constraint system
and Stage 3's allocation target. If the branch is `decline`, state explicitly that Stage 3's
plan must name a substitute anchor before any baseline is written.>

## Requirements that cannot be implemented without further source verification (§1.2)

| Requirement | What is missing | Which stage must resolve it |
|---|---|---|
| <ID> | <the specific unobtained fact> | <stage> |

List every requirement whose Stage 0 field ended as "not obtainable — why". If the list is
empty, write a single line saying so.

## Open §21 decisions this audit touches

| §21 row | Verdict from this audit | Evidence |
|---|---|---|
| Geography universe (50 states + D.C.) | <confirmed / needs explicit residual cells / cannot be reconciled> | <the qcew_identity quarter table> |
| TPO/FIA coverage (required only after extraction audit) | <include / exclude / defer to Stage 7> | <the tpo and fia access statuses> |
| Optional state sources (disabled by default) | <keep disabled / revisit in Stage 7> | <one line; the audit probed no state portal, so "keep disabled" with that reason is a valid verdict> |

## Auditor's notes

<Anything a later stage would be wrong without: surprises, partial coverage, a route that
worked only with a retry, a code list that changed mid-window.>
```

- [ ] **Step 4: Write the assembler**

Create `scripts/audit/assemble_finding.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]   # _common imports httpx
# ///
"""Render every source summary plus the hand-written notes into specs/findings/source-audit.md.

Idempotent: the generated sections are rebuilt from the summaries on every run, and the
hand-written notes file is inlined verbatim, so re-running never clobbers prose.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as c  # noqa: E402

OUT = c.FINDINGS_DIR / "source-audit.md"
NOTES = c.FINDINGS_DIR / "source-audit-notes.md"


def fence(obj) -> str:
    return "```json\n" + json.dumps(obj, indent=2, sort_keys=True) + "\n```"


def main() -> None:
    summaries = {p.parent.name: json.loads(p.read_text())
                 for p in sorted(c.AUDIT_ROOT.glob("*/summary.json"))}
    if not summaries:
        raise SystemExit("no summaries to assemble; run the source tasks first")
    if not NOTES.exists():
        raise SystemExit(f"{NOTES} is required; write it before assembling")

    lines = [
        "# Stage 0 source audit — findings",
        "",
        f"**Generated:** {datetime.now(UTC).date().isoformat()} by "
        "`scripts/audit/assemble_finding.py`.",
        "**Spec:** `specs/logging-employment-spec.md` · "
        "**Roadmap:** `specs/logging-employment-spec-roadmap.md`, Stage 0 · "
        "**Plan:** `specs/plans/1-stage0-logging-employment-spec.md`",
        f"**Window (D1):** {c.WINDOW_START} → {c.WINDOW_END} · "
        f"**Industry:** {c.INDUSTRY_CODE} (Logging) · **Ownership:** private · "
        "**Geography:** states + D.C.",
        "",
        # §3.1 requires the invalid supplied code to be recorded alongside the correction,
        # never silently replaced. These are facts from the source prompt, not fetchable
        # metadata, so they are literals here rather than derived.
        "**Classification (§3.1):** the source prompt supplied `1113310`, which is not a "
        "valid NAICS code. It is recorded, not silently replaced — "
        "`industry_code_supplied = '1113310'`, `industry_code_used = '113310'`, "
        "`industry_title = 'Logging'`, "
        "`classification_status = 'corrected_invalid_supplied_code'`.",
        "",
        "Extract hashes are recorded in `source-audit-extracts.csv` and re-verified by "
        "`scripts/audit/verify_extracts.py`. Raw bytes live under `data/raw/audit/`, which is "
        "gitignored.",
        "",
        "## Access and coverage at a glance",
        "",
        "| Source | Access | Route | Covers of D1 window | Not covered |",
        "|---|---|---|---|---|",
    ]
    for name, s in summaries.items():
        cov = s["coverage_span"]
        route = s["access"]["route"].replace("|", "\\|")
        route = route if len(route) <= 70 else route[:67] + "..."
        lines.append(
            f"| `{name}` | {s['access']['status']} | {route} | "
            f"{cov['covered'] or '—'} | {cov['uncovered'] or 'none'} |")

    lines += ["", NOTES.read_text().rstrip(), "", "## Per-source findings", ""]
    for name, s in summaries.items():
        lines += [f"### `{name}`", ""]
        if s["access"]["status"] != "verified":
            lines += [f"> **{s['access']['status']}** — {s['access']['reason']}", ""]
        lines += [fence(s["findings"]), "",
                  f"_Extracts: {len(s['extracts'])}; generated {s['generated_utc']}._", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT} from {len(summaries)} summaries")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Assemble the finding**

Run:

```bash
uv run --no-project scripts/audit/assemble_finding.py
```

Expected: `wrote specs/findings/source-audit.md from <n> summaries`, where `<n>` is the number
of `data/raw/audit/*/summary.json` files.

- [ ] **Step 6: Check every stage exit criterion**

Run:

```bash
uv run --no-project scripts/audit/verify_extracts.py && python3 - <<'PY'
import json, pathlib, re, sys
fails = []

doc = pathlib.Path("specs/findings/source-audit.md").read_text()
if not doc.strip():
    fails.append("finding file is empty")
# §3.1: the invalid supplied code is recorded, never silently replaced.
if "1113310" not in doc or "corrected_invalid_supplied_code" not in doc:
    fails.append("the §3.1 classification record is missing from the finding document")

# These findings keys are declared elsewhere in this plan as legitimately empty or null —
# an empty value there is a finding, not a missing one, so the exit gate must not reject it.
LEGITIMATELY_EMPTY_FINDINGS = frozenset({
    "bulk_years_required",    # qcew_routes: "[] is a legitimate finding, not a failure"
    "unknown_years",          # cbp_regime: possibly empty
    "sampling_error_field",   # fia: or null, paired with a reason
    "chosen_route",           # tpo: the URL, or null — not_obtainable is legitimate here
})

# Every field is either filled or marked "not obtainable — why".
for path in sorted(pathlib.Path("data/raw/audit").glob("*/summary.json")):
    s = json.loads(path.read_text())
    for key, value in s["findings"].items():
        if key in LEGITIMATELY_EMPTY_FINDINGS:
            continue
        if value in (None, "", [], {}):
            fails.append(f"{path}: findings[{key!r}] is empty — fill it or mark "
                         f"'not obtainable — why'")

# The SRC-QCEW-006 branch verdict.
q = json.loads(pathlib.Path("data/raw/audit/qcew_identity/summary.json").read_text())["findings"]
if q["branch"] not in ("enforce", "residual_cells", "decline"):
    fails.append("branch verdict is not one of enforce/residual_cells/decline")
sentence = q["verdict_sentence"].strip()
# Area titles carry abbreviation periods ("U.S. TOTAL", "D.C."); normalise them away before
# counting sentence enders, or a legitimate verdict is rejected.
normalized = re.sub(r"\b(?:[A-Za-z]\.){2,}", "ABBR", sentence)
# Section references like "§3.2" are not sentence enders either.
normalized = re.sub(r"(?<=\d)\.(?=\d)", "", normalized)
if normalized.count(".") != 1 or not normalized.endswith("."):
    fails.append("the verdict must be exactly one sentence")
if "\n" in sentence:
    fails.append("the verdict must be a single line")
if not re.search(r"\bquarters?\b", sentence):
    fails.append("the verdict must cite the per-quarter comparison")
if "non-state area" not in sentence:
    fails.append("the verdict must state whether the geography universe accounts for any gap")
if q["verdict_sentence"] not in doc:
    fails.append("the verdict sentence is not present in the finding document")

# The QCEW year boundary is a reference year, not an approximation.
r = json.loads(pathlib.Path("data/raw/audit/qcew_routes/summary.json").read_text())["findings"]
if not isinstance(r["earliest_year_served"], int):
    fails.append("earliest_year_served must be an integer reference year")

for f in fails:
    print("FAIL", f)
print("EXIT CRITERIA:", "PASS" if not fails else f"{len(fails)} FAILURES")
sys.exit(1 if fails else 0)
PY
echo "exit=$?"```

Expected: `summaries validated`, `manifest written`, `EXIT CRITERIA: PASS`, and `exit=0`. Every
`FAIL` line names one unmet exit criterion — fix the underlying finding, never the check.

- [ ] **Step 7: Commit the stage deliverable**

```bash
git add scripts/audit/verify_extracts.py scripts/audit/assemble_finding.py \
        specs/findings/source-audit.md specs/findings/source-audit-notes.md \
        specs/findings/source-audit-extracts.csv
git commit -m "docs(findings): record the Stage 0 source audit and its extract manifest"
```

- [ ] **Step 8: Run the Plan Completion Protocol**

1. **Resolve-before-defer gate.** Collect every field this audit closed as
   `"not obtainable — why"`, every `unknown` CBP regime year, and any step skipped during
   execution. Partition them: anything stalled on your human partner's input becomes one
   batched set of questions asked now; anything an answer unblocks is implemented now (the
   protocol restarts after that work lands); everything else is deferred. Do not mark up the
   plan until every ask is resolved.
2. **Markup.** Tick every completed step in this file, add a `> Deviation:` line under any step
   that diverged, and add the status header at the top:
   `**Status: COMPLETE (YYYY-MM-DD)** — executed via <skill>; deferred items in specs/deferred_items.md`
   (or `; nothing deferred`).
3. **Deferred items.** In `specs/deferred_items.md`, first tick any earlier item this plan
   implemented — run that pass even if nothing was deferred here — then append one
   `## 1-stage0-logging-employment-spec — YYYY-MM-DD` section with this plan's deferrals, each
   self-contained (file paths, why deferred, what it would take). Skip the append entirely when
   nothing was deferred. **Confirm at this point that `SRC-OTH-005`'s premise still holds:** the
   BEA `SAEMP25`/`SAEMP27` discontinuation is the recorded reason, and the roadmap's Completion
   section asks for that check.
4. **Stamp the roadmap and the spec.** Tick Stage 0's checkbox in
   `specs/logging-employment-spec-roadmap.md` and replace the Stage 0 stamp line in the spec's
   Rollout note with:
   `> Stage 0: COMPLETE (YYYY-MM-DD) — implemented by plan 1 (specs/plans/completed/1-stage0-logging-employment-spec.md).`
   `> Next: resume the roadmap.`
   Then **re-validate the later stages against what shipped**, which for this stage means at
   minimum:
   - Stage 1's parser contracts against the observed code lists and the QCEW year boundary;
   - Stage 2's available margins against the `SRC-QCEW-006` branch;
   - Stage 3's allocation target — if the branch is `decline`, its plan must name a substitute
     anchor before any baseline is written;
   - Stage 4's mask design against the measured suppression share and run lengths;
   - Stage 6's routing — re-route it to brainstorming if
     `simultaneous_state_industry_size` came back `true`;
   - Stages 2, 3 and 6's `Consumes` blocks against the CBP coverage gap.
5. **Retire.** `git mv specs/plans/1-stage0-logging-employment-spec.md
   specs/plans/completed/` in one `chore(specs): retire plan 1` commit. **Leave
   `specs/logging-employment-spec.md` in place** — Stages 1–9 are live plans against the same
   spec, so the shared-spec exception applies. Re-point any relative links in the retired plan
   for its new depth.

---

## Notes for the executor

**Ordering.** Tasks 1 → 6 are a chain: each reads the previous task's summary. Tasks 7–12 are
independent of one another and of 2–6 once Task 1 exists, so they can run in parallel. Task 13
requires all of them.

**When a fetch fails.** A 4xx is a finding, not a transient — record it and move on. A 5xx or a
transport error is retried by `_common.request`; if it still fails, record the status and set
the source's `access.status` to `not_obtainable` with the reason. Never loosen an assertion to
make a script finish.

**What this stage must not do.** It does not build the package, define a Parquet contract, write
an ingest interface, or encode a disclosure threshold. Every one of those belongs to Stage 1 or
later, and doing them here would put untested code in front of the finding the later stages
actually depend on.
