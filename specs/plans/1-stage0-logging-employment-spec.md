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
  - `quarter_probe` — the per-year, per-quarter result of probing the non-Q1 by-size URLs.
    `coverage_span.uncovered` is written from this rather than asserting "the by-size product
    is Q1-only": the Q1-only shape is a claim about what BLS publishes, so it is measured each
    run and the persisted sentence names the probe count it rests on.
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

import httpx
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


def probe_other_quarters(client: httpx.Client, years: tuple[int, ...]) -> list[dict]:
    """Probe Q2-Q4 of every window year for a by-size file, so the coverage_span's "Q1-only"
    claim is measured this run rather than asserted from memory. The illustrative brief wrote
    that claim as a typed string with no request behind it -- the Global Constraints' rule on
    persisted prose says a factual sentence must be interpolated from data in scope during the
    run, and "no other quarter is published" is exactly the kind of claim a later BLS schedule
    change could falsify. A 404 across the board is what the by-size product's Q1-only design
    would produce; any 200 means it is not Q1-only and the note below must say so instead."""
    rows = []
    for year in years:
        for qtr in (2, 3, 4):
            url = f"https://data.bls.gov/cew/data/files/{year}/csv/{year}_q{qtr}_by_size.zip"
            status, nbytes = c.probe(client, url)
            rows.append({"year": year, "qtr": qtr, "http_status": status, "bytes": nbytes})
    return rows


def main() -> None:
    client = c.build_client()
    extracts, frames = [], []
    for year in c.WINDOW_YEARS:
        url = SIZE_URL.format(year=year)
        rec = c.download_extract(client, SOURCE, url, f"{year}_q1_by_size.zip")
        extracts.append(rec)
        frames.append(read_zip(rec.path).with_columns(pl.lit(year).alias("ref_year")))
    df = pl.concat(frames, how="vertical")

    quarter_probe = probe_other_quarters(client, c.WINDOW_YEARS)
    other_quarters_served = any(row["http_status"] == 200 for row in quarter_probe)

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
            "uncovered": (
                f"Q2-Q4 of every window year: probed ({len(quarter_probe)} requests) and none "
                "returned a by-size file, so the product is Q1-only for every year checked"
                if not other_quarters_served else
                "Q2-Q4 of every window year: NOT purely Q1-only -- at least one non-Q1 by-size "
                "file was found this run; see findings.quarter_probe for which year/quarter"
            ),
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
            "quarter_probe": quarter_probe,
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
   before ever attempting to parse the body -- and, for a non-JSON body, on the page's own
   `<title>` (`html_title`), so a Census maintenance page or rate-limit interstitial is never
   folded into the same "the key is bad" bucket as an actual missing/invalid-key redirect.

2. **Whether CBP's metadata publishes an EMPSZES code-label crosswalk varies by vintage --
   measured every year by probing every keyless route that could plausibly carry one, never
   assumed uniform from a single endpoint checked once.** The plan's illustrative `value_list`
   helper reads `payload["values"]["item"]` from `/variables/{VAR}.json`. **2017's real
   response has exactly that shape -- 44 code/label pairs, `"001": "All establishments"`
   onward.** Every other available year checked this run carried none;
   `empszes_metadata_crosswalk_probe_by_year` records which years, not this docstring.
   A first pass at this task checked only 2021 by hand, found no crosswalk, and generalized
   that to every vintage; the generalization was wrong, and the fix was to make the check
   something the script does every year rather than something a person did once.
   `probe_empszes_metadata_crosswalk` checks `/variables/EMPSZES.json` plus two more
   candidates per year -- `groups.json` (a group index, no per-variable detail) and every
   group detail document named by EMPSZES's own `group` field (`groups/{group}.json`, which
   lists every variable in that group, including EMPSZES's own entry -- confirmed live for
   2018 that this field can name more than one group at once) -- and records `{url, status,
   carries_values_crosswalk}` for each in `empszes_metadata_crosswalk_probe_by_year`, plus the
   actual `{code: label}` dict from whichever candidate carried one
   (`crosswalk_items_from_payload`). Where the official enumeration exists (2017),
   `empszes_by_year[year]` carries it directly, tagged `"source":
   "official_metadata_crosswalk"`. Where it doesn't (2018 onward, confirmed absent this way,
   not merely unfetched), `empszes_by_year[year]` falls back to an OBSERVATION over the keyed
   pull's own rows instead: `EMPSZES`/`EMPSZES_LABEL` are requested as unfiltered output
   columns in attempts 1-2 below, so distinct `(EMPSZES, EMPSZES_LABEL)` pairs actually
   returned (`empszes_pairs_from_rows`) are tagged `"source": "observed_in_113310_state_slice"`
   -- an under-count risk a bare list would hide (a size class with zero logging
   establishments in every state that year produces no row), which is why the source is
   recorded in the data itself, not only in this docstring. `LFO` is only ever used as a
   filter (`="001"`) or omitted, never selected as an output column, so no attempt here can
   ever yield a full LFO crosswalk from its rows even once a pull succeeds -- `lfo_by_year`
   stays `null` with that limitation recorded in `notes` per year.

3. **A key genuinely present in this repo's `.env` does not authenticate.** Confirmed against
   both this dataset and, as a control ruling out a CBP-specific malformed query, against a
   wholly different dataset (ACS1) with the same key: both return HTTP 200 with an "Invalid
   Key" HTML page. Every keyed request in a run against this credential is therefore expected
   to fail; the script still performs every keyed request for real (it does not special-case
   "this key looks broken, skip the network calls") so a fixed credential needs no code change
   to start succeeding, and so `access.status`/`notes` report what THIS run actually measured
   -- `access.reason` is interpolated from the distinct failure causes actually recorded in
   `working_query_by_year`, not hardcoded to name the credential regardless of what happened.

4. **Every window year gets an explicit entry in every by-year finding, not only the years that
   responded.** A year outside `years_available` (a confirmed non-200 like 2024's 404, or a
   transport-failure `0` that `probe()` never retries) is backfilled with `null` plus a
   `notes` entry naming which of the two it was (`unavailable_year_reason`) -- a missing key
   and `null` are different facts to a downstream reader, and the dispatch that opened this
   task named that distinction directly.

5. **A run that stops writing the canonical `data_113310.json` on failure also removes any
   stale one a prior run left behind, at the start of processing each year -- before this
   run has decided whether it has a real answer.** Making the write conditional on success
   fixed what a *future* failing run does; it did nothing about what a *past* one already
   wrote. Without this, a year whose keyed pull fails this run but succeeded (or, before this
   fix, "succeeded") in some earlier run would keep an old file sitting at the exact filename
   the plan's Produces block names, unregistered in this run's `extracts` and therefore vouched
   for by nothing -- worse than absent, because it looks current to anything that opens the
   path directly instead of going through the manifest.
"""

from __future__ import annotations

import json
import os
import re
import shutil

import httpx

import _common as c

SOURCE = "cbp_metadata"
BASE = "https://api.census.gov/data/{year}/cbp"
NAICS_RE = re.compile(r"^NAICS\d{4}$")
_TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Only these two `classify_data_body` outcomes are evidence of a credential problem specifically
# -- see `zero_pull_cause`. Any other non-"ok" outcome (a maintenance page, a rate-limit
# interstitial, a malformed-JSON body) must fall through to "query_bug" instead.
_AUTH_REJECTION_STATUSES = frozenset({"invalid_key", "missing_key"})

# The two values `empszes_by_year[year]["source"]` can carry. Fix round 2: both are real --
# 2017 genuinely has the official enumeration in metadata; 2018 onward fall back to the
# row-derived observation. Task 8 needs to tell them apart, so the source is recorded in the
# data itself, not only in this module's docstring.
EMPSZES_SOURCE_OFFICIAL = "official_metadata_crosswalk"
EMPSZES_SOURCE_OBSERVED = "observed_in_113310_state_slice"


def html_title(body: bytes) -> str:
    """The HTML `<title>` text, lowercased and stripped, or `""` if there isn't one (including
    when `body` isn't HTML at all). Case-insensitive on the tag itself (`<TITLE>` matches too)."""
    match = _TITLE_RE.search(body)
    if not match:
        return ""
    return match.group(1).decode("utf-8", "replace").strip().lower()


def classify_data_body(content_type: str, body: bytes) -> tuple[str, list | None]:
    """Classify one response from the keyed CBP data-pull endpoint.

    Census answers a missing OR invalid key with HTTP 200 after following the redirect to an
    HTML error page -- status alone cannot distinguish that from a real answer (see module
    docstring, point 1). Content-type is what discriminates a real answer from any HTML page;
    the page's own `<title>` then discriminates a credential rejection from anything else
    non-JSON (a maintenance page, a rate-limit interstitial, or anything else Census might ever
    serve at 200 that isn't the data). Returns:
      ("ok", header_and_rows)   -- content-type carries "json" and the body parses as a
                                    non-empty list of lists (the tabular header-plus-rows shape
                                    this endpoint returns for a `get=`/`for=` query).
      ("invalid_key", None)     -- non-JSON content-type and the page's `<title>` is
                                    "Invalid Key" (Census's page for a syntactically-plausible
                                    but unregistered key).
      ("missing_key", None)     -- non-JSON content-type and the page's `<title>` is
                                    "Missing Key" (Census's page for no `key` param at all).
      ("non_json_error", None)  -- non-JSON content-type but neither known title matched. Must
                                    NOT be assumed to be a credential problem -- `zero_pull_cause`
                                    relies on this function never folding an unrelated non-JSON
                                    response into the same bucket as an actual key rejection.
      ("bad_shape", None)       -- content-type claims JSON but the body doesn't parse, or
                                    parses to something other than a non-empty list of lists
                                    (e.g. a dict, an empty list, a list of scalars).
    """
    if "json" not in content_type:
        title = html_title(body)
        if title == "invalid key":
            return "invalid_key", None
        if title == "missing key":
            return "missing_key", None
        return "non_json_error", None
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
    came back as a key-rejection page". Without one, an invalid or missing `CENSUS_API_KEY`
    reads as "the query is wrong": a credential problem misdiagnosed as a script bug.
    `attempt_statuses` are `classify_data_body` outcomes plus "http_error" for a raised
    `HTTPStatusError`, in attempt order; only reached when none of them was "ok". Only
    `invalid_key`/`missing_key` count as the auth family -- `non_json_error` (a maintenance
    page, a rate-limit interstitial, anything else non-JSON) falls through to `query_bug`
    rather than being assumed to be the same credential problem."""
    if not state_available:
        return "geography_unavailable"
    if attempt_statuses and all(s in _AUTH_REJECTION_STATUSES for s in attempt_statuses):
        return "auth_error"
    return "query_bug"


def empszes_pairs_from_rows(header: list[str], body: list[list]) -> list[dict] | None:
    """Distinct `(EMPSZES, EMPSZES_LABEL)` pairs observed in a successful data-pull response,
    sorted by code. Returns `None` when the response didn't carry both columns (attempt 3
    drops EMPSZES entirely) -- that must read as "not observed", never as an empty list
    standing in for "this vintage has no size classes". This is an OBSERVATION over whatever
    rows the pull returned, not the official metadata enumeration -- see module docstring
    point 2; the caller is responsible for saying so in the persisted record."""
    if "EMPSZES" not in header or "EMPSZES_LABEL" not in header:
        return None
    i_code, i_label = header.index("EMPSZES"), header.index("EMPSZES_LABEL")
    pairs = {(row[i_code], row[i_label]) for row in body}
    return [{"code": code, "label": label} for code, label in sorted(pairs)]


def group_names_from_field(group_field: str | None) -> list[str]:
    """A variable's `group` field, split into every group name it names. Usually one name, but
    confirmed live for 2018's EMPSZES ("CB1800ZBP,CB1800CBP" -- shared between that year's ZIP
    Code Business Patterns and County Business Patterns groups): Census does not always treat
    `group` as a single identifier, and `f"groups/{group}.json"` on the raw field 404s on the
    literal comma. Returns `[]` for `None` or an empty/whitespace-only field."""
    if not group_field:
        return []
    return [g.strip() for g in group_field.split(",") if g.strip()]


def crosswalk_items_from_payload(payload: dict, variable: str) -> dict[str, str] | None:
    """The raw `{code: label}` `values.item` dict for `variable` within `payload`, checked at
    every shape this task's three candidate metadata routes can take: a flat single-variable
    document (`/variables/{variable}.json`, where `payload` itself is the candidate), a
    group-index document with no per-variable detail at all (`/groups.json`, which never
    matches), and a group document listing every variable in that group
    (`/groups/{group}.json`, where `variable`'s own entry sits under `payload["variables"]`).
    Returns `None` if no candidate carries one. Never raises on a malformed or unexpected shape
    -- absence is the answer, not a crash.

    Fix round 2: confirmed live that this is NOT always absent -- 2017's real
    `/variables/EMPSZES.json` carries 44 code/label pairs (`"001": "All establishments"`, ...);
    2018 onward do not. The prior round's claim that no candidate ever carries one was true
    for the single year checked by hand and false as a generalization across vintages; this
    function existing (and `probe_empszes_metadata_crosswalk` calling it every year rather than
    once) is what caught that."""
    candidates = [payload]
    variables = payload.get("variables")
    if isinstance(variables, dict):
        entry = variables.get(variable)
        if isinstance(entry, dict):
            candidates.append(entry)
    for cand in candidates:
        values = cand.get("values")
        if isinstance(values, dict):
            items = values.get("item")
            if isinstance(items, dict):
                return items
    return None


def crosswalk_present_in_payload(payload: dict, variable: str) -> bool:
    """True if `payload` carries an enumerated `values.item` code list for `variable` --
    `crosswalk_items_from_payload(payload, variable) is not None`, as a boolean convenience for
    the probe record; see that function's docstring for the shapes checked."""
    return crosswalk_items_from_payload(payload, variable) is not None


def unavailable_year_reason(probe_status: int) -> str:
    """Why a window year has no CBP data this run, for the note beside its `null` entries.
    Distinguishes a genuine transport blip (`probe()`'s `(0, 0)` sentinel, which `probe` never
    retries -- re-running may find the year published after all) from a real, confirmed status
    Census actually returned (e.g. 2024's 404). Deliberately does not characterize a bare
    non-200 status as "a confirmed absence" in general -- a 5xx would be a server error, not
    evidence the year isn't published; only the literal status is reported here."""
    if probe_status == 0:
        return ("the keyless cbp.json probe returned no response at all this run (a transport "
                "failure, not a confirmed absence) -- re-run this task to resolve it")
    return f"cbp.json returned HTTP {probe_status} for this year, not 200"


def fetch_variable_doc(client: httpx.Client, year: int, variable: str, extracts: list) -> None:
    """Fetch and record `/variables/{variable}.json` verbatim (keyless; a real, useful extract
    -- label, concept, predicateType -- even though it carries no code/label crosswalk for this
    dataset, see module docstring point 2). Callers only invoke this once `variable in names`
    from `variables.json` is already confirmed, so this is pure extract retention, not an
    existence check -- `has_lfo`/`has_empszes` (computed from `variables.json`) are the
    existence checks, independent of this function and of whether this fetch itself succeeds."""
    url = f"{BASE.format(year=year)}/variables/{variable}.json"
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError:
        return None
    extracts.append(c.record_extract(
        SOURCE, url, f"{year}/{variable.lower()}.json", resp.content))
    return None


def fetch_json_or_none(
    client: httpx.Client, source: str, url: str, rel_path: str, extracts: list
) -> tuple[int, dict | None]:
    """GET `url`, record the extract on success, and parse the body as JSON -- returning
    `(status, None)` on an `httpx.HTTPStatusError` instead of raising.

    Fix round 3, Minor 2: `probe_empszes_metadata_crosswalk`'s `groups.json`/group-document
    fetches and the inline `EMPSZES.json` fetch in `main()` used to call `c.request` and
    `.json()` directly, unguarded -- the same shape of request that crashed the live run in
    fix round 1 (2018's comma-separated `group` field producing a 404 on the literal comma).
    Splitting the field fixed that one trigger; it did not fix the pattern. Any of these
    keyless metadata routes returning a 404 or 5xx crashes mid-run, after some of this run's
    extracts have already been appended to the list and before `write_summary` is ever called
    -- exactly the unregistered-files problem Minor 1 and fix round 2's Finding 2 are about,
    from a third angle. This function is what the two request sites route through now, so a
    metadata-route hiccup becomes a documented gap in the probe record instead of a crash."""
    try:
        resp = c.request(client, url)
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code, None
    extracts.append(c.record_extract(source, url, rel_path, resp.content))
    return resp.status_code, resp.json()


def probe_empszes_metadata_crosswalk(
    client: httpx.Client, year: int, empszes_doc: dict, empszes_status: int, extracts: list
) -> tuple[list[dict], dict[str, str] | None]:
    """Probe every keyless metadata route that could plausibly carry an EMPSZES values
    crosswalk for this vintage, and record what each actually returned -- so whether "CBP's
    metadata publishes an EMPSZES value list" is measured every year this run, not assumed
    uniform from a single endpoint checked once during development (module docstring point 2;
    fix round 2 -- 2017 genuinely carries one, 2018 onward do not). `empszes_doc` is
    `/variables/EMPSZES.json`'s already-fetched, already-recorded payload; its own `group`
    field names the candidate group document.

    Returns `(probe_records, official_crosswalk)`. `official_crosswalk` is the raw
    `{code: label}` dict from whichever candidate carried one -- the flat variable document is
    checked first, matching what has actually been observed (2017 carries it there and nowhere
    else checked ever has) -- or `None` if no candidate did this year."""
    ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
    ez_items = crosswalk_items_from_payload(empszes_doc, "EMPSZES")
    probe = [{
        "url": ez_url, "status": empszes_status,
        "carries_values_crosswalk": ez_items is not None,
    }]
    official = ez_items

    groups_url = f"{BASE.format(year=year)}/groups.json"
    groups_status, groups_payload = fetch_json_or_none(
        client, SOURCE, groups_url, f"{year}/groups.json", extracts)
    groups_items = (
        crosswalk_items_from_payload(groups_payload, "EMPSZES")
        if groups_payload is not None else None
    )
    probe.append({
        "url": groups_url, "status": groups_status,
        # None (not False) when the fetch itself failed -- "not measured" must not read as
        # "measured absent" here any more than it does for empszes_by_year itself.
        "carries_values_crosswalk": None if groups_payload is None else groups_items is not None,
    })
    official = official or groups_items

    # `group` can name more than one group, comma-separated -- confirmed live for 2018
    # ("CB1800ZBP,CB1800CBP": EMPSZES is shared between the ZIP Code Business Patterns and
    # County Business Patterns groups that year). Probe every named group's own document, not
    # just the first -- treating the field as a single name 404s on the literal comma.
    for group in group_names_from_field(empszes_doc.get("group")):
        group_url = f"{BASE.format(year=year)}/groups/{group}.json"
        group_status, group_payload = fetch_json_or_none(
            client, SOURCE, group_url, f"{year}/groups_{group}.json", extracts)
        group_items = (
            crosswalk_items_from_payload(group_payload, "EMPSZES")
            if group_payload is not None else None
        )
        probe.append({
            "url": group_url, "status": group_status,
            "carries_values_crosswalk": None if group_payload is None else group_items is not None,
        })
        official = official or group_items
    return probe, official


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("CENSUS_API_KEY is unset; `set -a && source .env && set +a` first")

    client = c.build_client()
    extracts: list[c.ExtractRecord] = []
    years: list[int] = []
    predicates, empszes, lfo, geo_levels = {}, {}, {}, {}
    working, rows, flags, crosswalk_probe = {}, {}, {}, {}
    probe_status: dict[str, int] = {}
    notes: list[str] = []
    any_keyed_success = False

    for year in c.WINDOW_YEARS:
        # Clear this year's ENTIRE directory before this run says anything about it, whether
        # the year turns out available this run or not (fix round 3, Minor 1). Fix round 2
        # only cleared the one canonical filename, and only inside the status==200 branch --
        # so a year available in a past run (full extract set + canonical file on disk) that
        # regresses to non-200 THIS run (a real 404, or probe()'s (0,0) transport sentinel)
        # skipped that unlink entirely, leaving its whole directory on disk unregistered in
        # this run's summary.json -- the same orphan problem Minor 5/Finding 2 fixed, just
        # triggered by a probe failure instead of a pull failure. Wiping unconditionally, every
        # year, before the probe, means this run's disk state can never be a mix of this run's
        # writes and some earlier run's leftovers: whatever survives to write_summary is
        # exactly what this run itself fetched. A transient probe-failure (0) year loses its
        # previously-fetched files too -- the accepted cost of a simple, single invariant
        # rather than a partial-merge-across-runs model this codebase has nowhere else; the
        # existing guidance to re-run this task on a 0 status still applies and refetches it.
        year_dir = c.AUDIT_ROOT / SOURCE / f"{year}"
        if year_dir.exists():
            shutil.rmtree(year_dir)

        status, _ = c.probe(client, f"{BASE.format(year=year)}.json")
        probe_status[str(year)] = status
        if status != 200:
            # probe() has no retry and returns (0, 0) on a TransportError; that "0" is a
            # transient failure, not a finding. Any other non-200 (e.g. 2024's 404) is a real,
            # confirmed status. Both cases -- and the note distinguishing them -- are handled
            # uniformly in the backfill pass after this loop (module docstring point 4), so
            # every window year gets an explicit entry rather than only years_available.
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

        official_crosswalk: dict[str, str] | None = None
        if has_empszes:
            ez_url = f"{BASE.format(year=year)}/variables/EMPSZES.json"
            ez_status, ez_payload = fetch_json_or_none(
                client, SOURCE, ez_url, f"{year}/empszes.json", extracts)
            if ez_payload is not None:
                crosswalk_records, official_crosswalk = probe_empszes_metadata_crosswalk(
                    client, year, ez_payload, ez_status, extracts)
                crosswalk_probe[str(year)] = crosswalk_records
            else:
                crosswalk_probe[str(year)] = None
                notes.append(
                    f"{year}: EMPSZES variable document fetch failed (HTTP {ez_status}) -- "
                    "metadata-crosswalk probe could not run"
                )
        else:
            crosswalk_probe[str(year)] = None
            notes.append(
                f"{year}: EMPSZES is not a variable for this vintage; no metadata-crosswalk "
                "probe was run"
            )

        if official_crosswalk:
            # The official enumeration exists in metadata for this vintage (confirmed live for
            # 2017 -- 44 codes) -- use it, and record that it came from metadata rather than
            # the keyed pull's rows. This also means empszes_by_year can be populated for a
            # year even when the keyed pull itself fails (this run, for every year) -- the
            # crosswalk probe is entirely keyless.
            empszes[str(year)] = {
                "source": EMPSZES_SOURCE_OFFICIAL,
                "pairs": [
                    {"code": code, "label": label}
                    for code, label in sorted(official_crosswalk.items())
                ],
            }
            notes.append(
                f"{year}: EMPSZES official crosswalk found in metadata "
                f"({len(official_crosswalk)} codes) -- see "
                "empszes_metadata_crosswalk_probe_by_year for which route carried it"
            )

        # lfo_by_year is null either way: when LFO isn't a variable at all, and also when it
        # is one, because no attempt below selects LFO/LFO_LABEL as output columns (module
        # docstring point 2) -- there is no code path that ever derives a real LFO crosswalk
        # in this script. Recorded unconditionally here (not only on the branch that goes on
        # to attempt a pull) so an ambiguous/absent NAICS predicate below still leaves a note
        # explaining lfo_by_year rather than silently skipping it for that year.
        lfo[str(year)] = None
        if has_lfo:
            fetch_variable_doc(client, year, "LFO", extracts)
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
            if not official_crosswalk:
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
        winning_content: bytes | None = None
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
            if not official_crosswalk:
                # Fallback only -- the official crosswalk (set above, if the probe found one)
                # always wins. This branch only ever populates empszes_by_year for a vintage
                # where metadata genuinely carries no enumeration (2018 onward, confirmed).
                pairs = empszes_pairs_from_rows(header, body)
                empszes[str(year)] = None if pairs is None else {
                    "source": EMPSZES_SOURCE_OBSERVED,
                    "note": (
                        "NOT the official CBP metadata enumeration -- this vintage's metadata "
                        "carries no EMPSZES values crosswalk (see "
                        "empszes_metadata_crosswalk_probe_by_year). A size class with zero "
                        "logging establishments in every state this year is silently absent "
                        "from `pairs`."
                    ),
                    "pairs": pairs,
                }
            winning_content = dresp.content
            any_keyed_success = True
            break
        else:
            cause = zero_pull_cause(
                state_available="state" in levels, attempt_statuses=attempt_statuses)
            working[str(year)] = {"status": cause}
            rows[str(year)] = None
            flags[str(year)] = None
            if not official_crosswalk:
                empszes[str(year)] = None
            notes.append(
                f"{year}: keyed 113310 pull failed for all {len(attempts)} attempts -- cause: "
                f"{cause} (attempt statuses: {attempt_statuses})"
            )
            if cause == "auth_error":
                distinct = sorted(set(attempt_statuses))
                # empszes_by_year is the one field the keyed-pull failure does NOT necessarily
                # null out -- a year with an official metadata crosswalk (2017) keeps it,
                # because that crosswalk comes from a keyless route this failure never touched.
                # Naming it here unconditionally would repeat exactly the "persisted prose
                # contradicts the artifact" bug fix round 1 already found once in this note.
                empszes_clause = (
                    "empszes_by_year already carries the official metadata crosswalk found "
                    "above, unaffected by this" if official_crosswalk else
                    "empszes_by_year is null for this year too, not measured as zero or empty"
                )
                notes.append(
                    f"{year}: every attempt's response matched Census's key-rejection page "
                    f"({distinct}); rows_113310_by_year and flag_values_by_year are null for "
                    f"this year, not measured as zero or empty; {empszes_clause}; "
                    "working_query_by_year carries {'status': 'auth_error'} rather than the "
                    "successful query shape -- re-run this task once CENSUS_API_KEY "
                    "authenticates."
                )

        # Retain the WINNING attempt's bytes under the canonical filename the plan's Produces
        # block names -- only on a real success, never an HTML error page recorded as if it
        # were data. Reuses the already-fetched bytes; no re-fetch.
        if winning_content is not None:
            extracts.append(c.record_extract(
                SOURCE, BASE.format(year=year), f"{year}/data_113310.json", winning_content))

    # Every window year gets an explicit entry in every by-year finding -- a year outside
    # years_available (confirmed non-200, or probe()'s (0,0) transport sentinel) is backfilled
    # with null plus a note naming which of the two it was, never left as a missing key.
    for year in c.WINDOW_YEARS:
        y = str(year)
        if year in years:
            continue
        predicates.setdefault(y, None)
        empszes.setdefault(y, None)
        lfo.setdefault(y, None)
        working.setdefault(y, None)
        geo_levels.setdefault(y, None)
        rows.setdefault(y, None)
        flags.setdefault(y, None)
        crosswalk_probe.setdefault(y, None)
        notes.append(
            f"{year}: not in years_available -- {unavailable_year_reason(probe_status[y])}; "
            f"every other finding for {year} is null."
        )

    covered = f"{min(years)}-{max(years)}" if years else ""
    uncovered = ",".join(str(y) for y in c.WINDOW_YEARS if y not in years)
    # Both non-"verified" cases below are "not_obtainable", not "documented": nothing about the
    # keyed route was learned from documentation -- every keyed request was actually attempted
    # live, and the *data* it exists to fetch could not be obtained this run, whether because no
    # dataset document ever came back or because the credential never authenticated. "verified"
    # is reserved for what it says: at least one year's keyed pull actually returned real rows.
    access_status = "verified" if any_keyed_success else "not_obtainable"
    # Interpolated from what was actually recorded in working_query_by_year, not hardcoded --
    # the failure could be an auth rejection, but it could also be a geography or query problem
    # (or a mix across years), and the reason must say which was actually observed this run.
    failure_causes = sorted({
        v["status"] for v in working.values() if isinstance(v, dict) and "status" in v
    })
    # Derived from empszes, not typed -- access.status = "not_obtainable" would otherwise read
    # as "nothing usable came out of this run" when a reader only checks this one field, which
    # is false whenever a keyless official metadata crosswalk was found (2017, this run) even
    # though the keyed pull itself failed everywhere.
    official_crosswalk_years = sorted(
        int(y) for y, v in empszes.items()
        if isinstance(v, dict) and v.get("source") == EMPSZES_SOURCE_OFFICIAL
    )
    access_reason = (
        None if access_status == "verified" else
        (
            "CBP metadata routes (dataset document, variables, EMPSZES/LFO variable docs, "
            "groups, geography) returned real JSON for every year in years_available, but "
            "the keyed 113310 data pull did not succeed for any window year this run -- "
            f"causes recorded in working_query_by_year: {failure_causes}; see findings.notes "
            "per year for detail. empszes_by_year is nonetheless populated from a keyless "
            f"official metadata crosswalk (unaffected by the keyed-pull failure) for: "
            f"{official_crosswalk_years or 'no years this run'}"
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
            "empszes_metadata_crosswalk_probe_by_year": crosswalk_probe,
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

> **Deviation (recorded on execution, 2026-09-04): `flag_evidence_by_year`'s `noise_flagged_share`
> field (mandated by the `flag_evidence_by_year` entry in this task's Interfaces block, and by
> the `noise_flagged_share` line in this task's illustrative `flag_evidence` function) is renamed
> to `emp_n_present_and_nonzero_share`.**
>
> **The computation is unchanged by this rename.** The shipped script still counts rows where
> `EMP_N` is present and not the string `"0"`, divided by the row total — only the local variable
> and the output key holding that count were renamed to match. No persisted value moves as a
> result of this rename.
>
> **That computation diverges sharply from the plan's own illustrative
> `sum(n for v, n in EMP_N.items() if v)` (the `noise_flagged_share` line in this task's
> illustrative `flag_evidence` function) — it is not "a different but equivalent-in-practice
> expression," and this run's own data proves it isn't.** `EMP_N` is the
> literal string `"0"` for every row in every window year this task observes (e.g. 2017:
> `{'0': 188}`, 2020: `{'0': 182}`, 2023: `{'0': 188}`). Python treats the non-empty string `"0"`
> as truthy, so the plan's `if v` counts every row: on this data it evaluates to `1.0` for every
> year. The shipped `not in (None, "0")` counts none of those same rows: it evaluates to `0.0`
> for every year, which is what `emp_n_present_and_nonzero_share` actually reads in the persisted
> artifact. These are the two opposite extremes on the observed data, not an equivalence. The
> shipped expression is also the correct one of the two: the plan's illustrative `if v` measures
> only whether `EMP_N` is present, not whether it is nonzero, which is meaningless as a share and
> is itself why that expression would report `1.0` unconditionally regardless of what `EMP_N`
> actually holds — the same string-truthiness bug is why the shipped field reads `0.0` for every
> window year rather than some other value.
>
> **Why:** the plan's name `noise_flagged_share` implies CBP's actual per-cell noise-magnitude
> flag, `EMP_N_F` — a `"FLAG"`-typed attribute, documented in methodology.html as a low/moderate/
> high (G/H/J) indicator. The value this field actually holds is derived from `EMP_N` itself,
> which CBP's own API metadata labels "Noise range for number of employees" and types as `int`,
> not a flag — and `EMP_N_F` is absent from every window year's 113310 x state response header
> this task fetches (confirmed live; Task 7's query never selected it as an output column). A
> reader relying on the plan's name alone would believe this field reports the published
> noise-flag distribution; it does not.
>
> **This was flagged, not silently fixed.** The implementer's first round refused to rename the
> field unilaterally, since both the name and the computation are plan-mandated here, and instead
> shipped an `emp_n_f_caveat` finding disclosing the gap next to the number. A reviewer then
> raised the name itself as misleading in a second round. The human ruled on it at the execution
> gate: rename the field to say what it measures, keep the computation exactly as specified above,
> and keep `emp_n_f_caveat`. This note is the tracked record of that ruling — `specs/` is
> versioned but `.sdd/` and `data/` are both gitignored, so without this line nothing surviving a
> fresh clone would carry the decision or the reason for the mismatch between this section's
> field name and `scripts/audit/cbp_regime.py`'s actual one.

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
  - `excluded_broader_codes` / `near_miss_states` / `notes` — added by the implementation,
    beyond this section's original schema. The illustrative candidate filter below matched the
    industry title against a bare `(?i)logging` substring; the live `sm.industry` file carries
    a second real code that trips it, `15000000` ("Mining, Logging and Construction") — a
    genuinely broader CES supersector, distinct from the target `10000000` ("Mining and
    Logging"), that happens to share the word "logging". Left unfixed, four jurisdictions whose
    only D1-window statewide all-employees series among the logging-named codes sits at
    `15000000` — Delaware, DC, Hawaii, the Virgin Islands — would have been silently promoted
    from `none` to `supersector`. `excluded_broader_codes` lists every logging-named code the
    precise, anchored selector left out; `near_miss_states` names the states/areas whose
    classification would have changed under the looser match; `notes` is the computed prose
    tying both to the six-count denominator (see next bullet) and to why `states_with_113310`
    reads 0 (see the paragraph after next).
  - `states_dc_tally` / `non_state_codes` — added by the implementation. `sm.state` carries 55
    codes, not 51: besides the 50 states + DC, it carries `00` ("All States"), `72` ("Puerto
    Rico"), `78` ("Virgin Islands") and `99` ("All Metropolitan Statistical Areas"), none of
    which is a D1 `states_dc` jurisdiction. The `states_with_*` counts are computed over all 55
    (this section's "record that denominator rather than forcing it to 51", taken literally);
    `states_dc_tally` re-states the same six-way tally restricted to `c.STATES_DC_FIPS` (51
    codes) — the universe D1 Appendix A and Stage 7 actually operate over — and
    `non_state_codes` lists the 4 codes the wider denominator adds, with their fetched titles.

**Derive the selector codes, never assert them.** The all-employees data-type code and the
statewide area code are read from the fetched `sm.data_type` and `sm.area` files by matching
their published titles. Hardcoding either would let a silent mismatch report
`states_with_none: 51`, which reads as a devastating finding about CES coverage when it is
really a typo. The same anchored-title discipline turned out to matter a third time, for the
Mining-and-Logging supersector code itself — see `excluded_broader_codes` above.

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
    """BLS flat files pad both headers and values with spaces — verified on the live
    sm.series file this run fetched: series_id is fixed-width, space-padded on both the header
    and every data row. `truncate_ragged_lines` is defensive: none of the five files this run
    fetched actually has a ragged row (every row in each carries the same field count as its
    header), but a parse that assumed that would stay true is exactly the kind of claim a
    future BLS layout change could falsify silently."""
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
    # That collapse is licensed by D6's claim that 113310 is the only six-digit industry under
    # 1133, verified for this task directly against the classification-codes skill's
    # naics_2017.csv and naics_2022.csv (also true in naics_2012.csv): each carries exactly one
    # level-6 row under 1133 -> 11331 -> 113310. In the sm.industry file this script actually
    # fetches, CES/SAE never reaches this branch at all — the one Logging code it publishes,
    # 10113300, embeds only the 4-digit "1133" (see logging_industry_codes in the summary this
    # run writes) — but the branch stays as a defensive rule for a finer code BLS could add.
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

# Loose net for finding every candidate; sole_code (above) narrows it to exactly one supersector
# code with an anchored title match. Kept separate from that anchor so the codes it excludes are
# still visible to excluded_broader_codes.
LOGGING_NAME_PATTERN = r"(?i)logging"


def qualifying_series(
    series: pl.DataFrame, codes: set[str], all_employees: str, statewide_area: str
) -> pl.DataFrame:
    """Rows of sm.series for the given industry codes, restricted to the statewide
    all-employees series overlapping the D1 window. Used for both the target candidate codes
    and the excluded broader codes, so the near-miss check can never define "qualifying"
    differently than the main query does."""
    return series.filter(
        pl.col("industry_code").is_in(sorted(codes))
        & (pl.col("data_type_code") == all_employees)
        & (pl.col("area_code") == statewide_area)
        & (pl.col("begin_year").cast(pl.Int32) <= max(c.WINDOW_YEARS))
        & (pl.col("end_year").cast(pl.Int32) >= min(c.WINDOW_YEARS))
    )


def excluded_broader_codes(
    logging_named_rows: list[dict], candidate_codes: set[str]
) -> list[dict]:
    """Every logging-named industry code this run's precise selector did not pick as a
    candidate — i.e. every code whose title happens to mention "logging" but which is neither
    embedded-NAICS-113-prefixed nor exactly titled 'Mining and Logging'. An unanchored
    substring match on the industry title (the brief's illustrative filter) would have folded
    these into the same 'supersector' level as the true target; kept visible here instead of
    silently disappearing."""
    return sorted(
        (row for row in logging_named_rows if row["industry_code"] not in candidate_codes),
        key=lambda r: r["industry_code"],
    )


def near_miss_states(
    excluded_series_rows: list[dict], level_by_state: dict[str, str]
) -> list[dict]:
    """States/areas whose only D1-window-overlapping statewide all-employees series among all
    logging-named codes sits at an excluded, broader code — exactly the states a looser,
    unanchored title match would have promoted from 'none' to 'supersector'. `level_by_state`
    is already computed against the precise candidate set, so every state named here already
    shows 'none' there; this function only explains why, from the excluded codes' own series."""
    return sorted(
        (
            {"state_code": row["state_code"], "industry_code": row["industry_code"],
             "series_id": row["series_id"]}
            for row in excluded_series_rows
            if level_by_state.get(row["state_code"]) == "none"
        ),
        key=lambda r: r["state_code"],
    )


def broader_code_note(excluded: list[dict], near_miss: list[dict]) -> str:
    """Computed sentence for `findings.notes`, stating what the precise title match excluded
    and, where relevant, which states that kept out of a coarser classification — so a future
    run against a renamed or retired code describes itself instead of repeating this run's
    'Mining, Logging and Construction' finding. The level a looser match would have assigned
    is derived from `level_of` on each excluded code, never typed as 'supersector' — a future
    excluded code that embeds e.g. NAICS 1131 would resolve to 'other', not 'supersector', and
    this sentence must say so instead of repeating today's wording."""
    if not excluded:
        return (
            "No SAE industry code mentioning 'logging' in its title fell outside the precise "
            "candidate selection this run — the anchored 'Mining and Logging' supersector "
            "match and the embedded-NAICS-113 match together account for every such code."
        )
    codes = "; ".join(f"{r['industry_code']} ({r['industry_name']!r})" for r in excluded)
    if not near_miss:
        return (
            "Excluded from the target industry codes because their titles merely mention "
            f"'logging' without being embedded-NAICS-113-prefixed or exactly titled 'Mining and "
            f"Logging': {codes}. No state's only D1-window-overlapping statewide all-employees "
            "series among the logging-named codes sits at one of these, so no state's level "
            "would change under a looser, unanchored title match."
        )
    states = ", ".join(sorted({r["state_code"] for r in near_miss}))
    levels = sorted({level_of(r["industry_code"]) for r in near_miss})
    level_phrase = levels[0] if len(levels) == 1 else " or ".join(levels)
    return (
        "Excluded from the target industry codes because their titles merely mention "
        f"'logging' without being embedded-NAICS-113-prefixed or exactly titled 'Mining and "
        f"Logging': {codes}. States {states} publish a D1-window-overlapping statewide "
        "all-employees series only at one of these excluded codes — an unanchored substring "
        f"match on 'logging' would have promoted them from 'none' to {level_phrase!r}, which "
        "is not what the fetched sm.industry file actually supports for them."
    )


def _month_grain(year: str, period: str) -> str:
    """"2017", "M01" -> "2017-01" — the same "YYYY-MM" shape as c.WINDOW_START/c.WINDOW_END, so
    the two compare lexicographically as chronologically. SAE periods observed on the live
    sm.series file are all "M01".."M12" (two digits after the "M"); a differently-shaped period
    would produce a string that still sorts sanely against "YYYY-MM" as long as it starts with
    two digits, and would look visibly wrong in `window_coverage_note`'s output otherwise."""
    return f"{year}-{period[1:]}"


def window_coverage_note(series: pl.DataFrame) -> tuple[bool, str]:
    """Whether every D1-window-overlapping qualifying series actually spans the *entire* D1
    window (2017-01 through 2024-12) at MONTH grain — reading begin_period/end_period
    (sm.series columns 11 and 13), not just begin_year/end_year. `qualifying_series` selects on
    year-level overlap only; a series with begin_year=2017, begin_period='M06' would pass that
    filter while not actually covering January 2017. This is what actually backs the persisted
    `coverage_span.covered` claim — a year-grain check here would itself be an unverified claim
    about how much it proves, wearing the same 'verified' framing as the parts that really are."""
    if series.height == 0:
        return False, "no qualifying series exist to check window coverage against"
    rows = series.select("series_id", "begin_year", "begin_period", "end_year",
                         "end_period").to_dicts()
    for row in rows:
        row["start_month"] = _month_grain(row["begin_year"], row["begin_period"])
        row["end_month"] = _month_grain(row["end_year"], row["end_period"])
    latest_start = max(row["start_month"] for row in rows)
    earliest_end = min(row["end_month"] for row in rows)
    fully_covered = latest_start <= c.WINDOW_START and earliest_end >= c.WINDOW_END
    if fully_covered:
        return True, (
            f"every one of the {len(rows)} qualifying series begins at or before "
            f"{c.WINDOW_START} (latest start observed, at month grain via begin_year/"
            f"begin_period: {latest_start}) and ends at or after {c.WINDOW_END} (earliest end "
            f"observed, via end_year/end_period: {earliest_end}), so the full D1 window "
            f"{c.WINDOW_START}-{c.WINDOW_END} is covered wherever a qualifying series exists, "
            "verified at month grain, not merely at the year-level overlap qualifying_series "
            "filters on"
        )
    names = ", ".join(sorted(
        row["series_id"] for row in rows
        if row["start_month"] > c.WINDOW_START or row["end_month"] < c.WINDOW_END
    ))
    return False, (
        f"at least one qualifying series only partially overlaps the D1 window "
        f"{c.WINDOW_START}-{c.WINDOW_END} at month grain (begin_year/begin_period, end_year/"
        f"end_period), even though it passed qualifying_series' year-level overlap filter: "
        f"{names}"
    )


def select_candidates(industry: pl.DataFrame, supersector: str) -> pl.DataFrame:
    """The precise candidate selector this task's finding rests on: every SAE industry code
    whose embedded NAICS begins '113', plus the one code equal to the anchored Mining-and-
    Logging supersector title match. Extracted out of `main()` so the defect this task found
    and fixed — an unanchored substring match on the industry title silently admitting the
    broader '15000000 Mining, Logging and Construction' code alongside the true target,
    '10000000 Mining and Logging' — has a regression test that runs without a live fetch."""
    return industry.with_columns(
        embedded=pl.col("industry_code").map_elements(embedded_naics, return_dtype=pl.Utf8),
        level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8),
    ).filter(
        pl.col("embedded").str.starts_with("113") | (pl.col("industry_code") == supersector)
    )


def states_dc_level_tally(
    level_by_state: dict[str, str], states_dc_fips: tuple[str, ...]
) -> dict[str, int]:
    """The six-way tally restricted to D1's own states_dc universe. Raises loudly if a
    states_dc code is missing from `level_by_state` (i.e. absent from the fetched sm.state
    file this run) instead of silently dropping it out of every bucket: `.get(st) == lvl`
    would return None for a missing code and match no branch, undercounting without a trace
    while `denominator_note` kept asserting the full states_dc count."""
    missing = sorted(set(states_dc_fips) - set(level_by_state))
    if missing:
        raise RuntimeError(
            f"states_dc code(s) {missing} are absent from level_by_state (i.e. from the "
            "fetched sm.state file this run) — refusing to silently under-count them out of "
            "states_dc_tally"
        )
    tally = {lvl: sum(1 for st in states_dc_fips if level_by_state[st] == lvl)
             for lvl in ("113310", "1133", "113", "supersector", "other", "none")}
    assert sum(tally.values()) == len(states_dc_fips), (
        f"states_dc_tally {tally} sums to {sum(tally.values())}, not "
        f"len(states_dc_fips)={len(states_dc_fips)}"
    )
    return tally


def granularity_note(candidate_rows: list[dict]) -> str:
    """Distinguishes, for `findings.notes`, why `states_with_113310` reads 0 — a Stage 7 reader
    could otherwise take the weaker reading ("no state happens to publish there") when the
    stronger one holds ("no such code exists to publish at all"). Computed entirely from
    `candidate_rows` (the same rows written to `logging_industry_codes`), including which
    specific code(s) sit below the supersector — never a typed code literal, so a future run
    where CES/SAE adds or renumbers a code describes what it actually finds."""
    levels_present = {r["level"] for r in candidate_rows}
    if "113310" in levels_present:
        return (
            "The fetched sm.industry file does define an SAE industry code at the 113310 "
            "(NAICS 6-digit) level for Logging, so a states_with_113310 count of 0 would mean "
            "no state's D1-window-overlapping statewide all-employees series happens to be "
            "published there, not that the code is absent."
        )
    below_supersector = sorted(
        (r for r in candidate_rows if r["level"] != "supersector"),
        key=lambda r: r["industry_code"],
    )
    codes = "; ".join(f"{r['industry_code']} ({r['level']})" for r in below_supersector)
    return (
        "The fetched sm.industry file defines no SAE industry code at the NAICS 5- or 6-digit "
        "depth for Logging at all — the Logging-related code(s) it defines below the "
        f"supersector, this run: {codes or '(none)'} (see logging_industry_codes). "
        "states_with_113310 is 0 because CES/SAE itself stops short of 113310 for every state, "
        "not because some state declines to publish at a level that exists."
    )


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
    # Same anchored discipline for the industry title. A bare substring match on "logging"
    # also matches "15000000 Mining, Logging and Construction" — a real, broader CES
    # supersector, verified present in the live sm.industry/sm.series files fetched this run —
    # which is not the Mining-and-Logging supersector D6 and this task mean.
    supersector = sole_code(frames["sm.industry"], "industry_code", "industry_name",
                            r"(?i)^mining and logging$", "sm.industry")

    industry = frames["sm.industry"]
    logging_named = industry.filter(pl.col("industry_name").str.contains(LOGGING_NAME_PATTERN))

    candidates = select_candidates(industry, supersector)
    candidate_codes = set(candidates["industry_code"].to_list())

    excluded = excluded_broader_codes(logging_named.to_dicts(), candidate_codes)
    excluded_codes = {row["industry_code"] for row in excluded}

    series = qualifying_series(
        frames["sm.series"], candidate_codes, all_employees, statewide_area
    ).with_columns(level=pl.col("industry_code").map_elements(level_of, return_dtype=pl.Utf8))

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

    excluded_series_rows = qualifying_series(
        frames["sm.series"], excluded_codes, all_employees, statewide_area
    ).to_dicts() if excluded_codes else []
    near_miss = near_miss_states(excluded_series_rows, level_by_state)

    # D1 Appendix A's own geography universe (50 states + DC, 51 codes) is a strict subset of
    # sm.state's 55 codes (it also carries "00" All States, "72" Puerto Rico, "78" Virgin
    # Islands, "99" All Metropolitan Statistical Areas — none of them a D1 state). Both the
    # code list and the tally below are computed from the fetched sm.state file and
    # c.STATES_DC_FIPS, never typed, so a future change to either denominator shows up here.
    non_state_codes = sorted(set(all_states) - set(c.STATES_DC_FIPS))
    state_names = dict(zip(frames["sm.state"]["state_code"].to_list(),
                           frames["sm.state"]["state_name"].to_list(), strict=True))
    states_dc_tally = states_dc_level_tally(level_by_state, c.STATES_DC_FIPS)

    states_dc_summary = ", ".join(f"{lvl}: {n}" for lvl, n in states_dc_tally.items())
    denominator_note = (
        f"The six states_with_* counts below sum to {len(all_states)}, the number of codes in "
        "the fetched sm.state file, not 51 — sm.state also carries "
        + "; ".join(f"{code} ({state_names.get(code)!r})" for code in non_state_codes)
        + f", none of which is a D1 'states_dc' jurisdiction. Restricted to D1's own "
        f"geography_universe ('states_dc', the {len(c.STATES_DC_FIPS)} codes in "
        f"c.STATES_DC_FIPS, also recorded in the states_dc_tally finding): {states_dc_summary}."
    )

    fully_covered, coverage_note = window_coverage_note(series)
    candidate_rows = candidates.select(
        "industry_code", "industry_name", "embedded", "level"
    ).rename({"embedded": "embedded_naics"}).to_dicts()

    c.write_summary(
        SOURCE,
        coverage_span={
            "published_start": str(series["begin_year"].cast(pl.Int32).min() or ""),
            "published_end": str(series["end_year"].cast(pl.Int32).max() or ""),
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": (
                f"{c.WINDOW_START}-{c.WINDOW_END} for states with a qualifying series — "
                f"verified at month grain, not assumed, from every qualifying series' own "
                f"begin_year/begin_period and end_year/end_period: {coverage_note}"
            ) if fully_covered else (
                f"partial only — {coverage_note}; do not read "
                f"'{c.WINDOW_START}-{c.WINDOW_END} for states with a qualifying series' as "
                "true without checking this run's coverage_note again"
            ),
            "uncovered": f"{tally['none']} sm.state code(s) publish no Logging-related statewide "
                         f"all-employees series overlapping the window, of which "
                         f"{states_dc_tally['none']} are D1 'states_dc' jurisdictions (see "
                         "states_dc_tally and non_state_codes for the rest of the denominator)",
        },
        access={"route": BASE + "<file>", "status": "verified", "reason": None},
        extracts=extracts,
        findings={
            "logging_industry_codes": candidate_rows,
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
            "excluded_broader_codes": excluded,
            "near_miss_states": near_miss,
            "states_dc_tally": states_dc_tally,
            "non_state_codes": [{"code": code, "name": state_names.get(code)}
                                for code in non_state_codes],
            "notes": " ".join([
                denominator_note, broader_code_note(excluded, near_miss),
                granularity_note(candidate_rows),
            ]),
        },
    )
    print("CES publication level tally:", tally)
    print("derived codes — data_type:", all_employees, "| area:", statewide_area,
          "| supersector:", supersector)


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
    one minimal `/fullreport` call. The implementation also stamps each probe record with
    `classify_probe`'s `outcome`, so a reader never has to classify a bare `http_status` (or a
    `0` transport-failure sentinel) themselves.
  - `sampling_error_field` — the response field carrying sampling error or a confidence
    interval, or `null`. `SRC-FOR-002` requires FIA rows to retain it "when available", so a
    `null` here must be paired with a reason.
  - `evaluation_vintage_field` — the field naming the evaluation vintage / survey cycle
    (`SRC-FOR-003`), or `null`.
  - `probe_naive_missing_required_params` — added by the implementation. The illustrative
    `probe` call above (`params={"outputFormat": "JSON"}` only) omits every parameter the doc
    page marks required (`wc*`, `snum*`, `rselected*`, `cselected*`) and returns an HTTP 200
    EVALIDator *error* page ("can only join an iterable"), not a report — a 200 that is not
    usable data. Recorded as its own finding, separate from `probe` (which instead sends the
    doc page's own documented required-parameter example), so the two outcomes are never
    conflated with each other or with a source outage.
  - `evaluation_vintage_index` / `district_of_columbia_has_fia_evaluation` — added by the
    implementation. `evaluation_vintage_index` is the parsed `/fullreport/parameters/wc` table
    (every state's EVALID row: distinct states, min/max `REPORT_YEAR_NM` year, row count) —
    it feeds `coverage_span.published_start/end` and lets `district_of_columbia_has_fia_evaluation`
    (bool) be read back from this run's own fetch rather than assumed: "District of Columbia"
    does not appear among the ~68 state/territory labels FIA evaluates, unlike QCEW's
    `states_dc` universe.
  - `tpo_mentions_on_fia_doc_page` — added by the implementation: a literal case-insensitive
    count of "TPO" in the fetched `/fiadb-api/` doc page body, verifying (not transcribing)
    the dispatch's claim that TPO is not discoverable from FIA's own documentation.
  - `datamart_probes` / `other_routes_probed` — added by the implementation, covering three
    more URLs the dispatch's lead table names (the DataMart CSV path and its HTML sibling,
    `Evalidator/evalidator.jsp`, `research/programs/fia`). `datamart_probes` records three
    bounded, spaced retry attempts per DataMart URL and the elapsed span, kept separate from
    the `/fullreport` verdict per the plan's three-outcome distinction: a transport failure
    (`_common.probe`'s `(0, 0)`) is not a 404, and neither is a `200`. `other_routes_probed`
    uses `probe_url` rather than `_common.probe` so the non-200 body `Evalidator/evalidator.jsp`
    answers with is retained (see `raw_retention_rule`) — that body is the evidence of *how*
    the route is closed, and `_common.probe` discards bodies by construction. Which non-200
    status that route serves is not stable: it answered 403 to one run and 500 to the next, and
    both within seconds on a hand check, so the retained extract's own `http_status` is the
    only reliable statement of what any given run met there.
  - `snum_estimate_attributes` — added by the implementation. The parsed
    `/fullreport/parameters/snum` catalog: how many estimate attributes `/fullreport` can
    return at all, which of them sit in *harvest*-removals estimate groups (kept distinct from
    FIA's "other removals" and combined "removals" groups, since only the first is a
    harvest-origin measure), each such group's attribute count / lowest attribute number /
    `EVAL_TYP`, and the full list of harvest-removals attribute numbers. This is what turns
    FIA's verdict from a reachability claim into an evidenced capability claim: whether the
    endpoint answers and whether it can return the measure §2.2 asks for are different
    questions, and one successful call answers only the first.
  - `measure_proved_by_probe` — added by the implementation: which measure the successful
    `/fullreport` call actually returned, read from the response's own
    `metadata.numEstDesc`/`metadata.estMeta` rather than inferred from the parameters sent, and
    quoted in `access.reason`. `null` when the response names no measure.
  - `industry_concept_scan` — added by the implementation: word-boundary hit counts for
    industry-classification terms (`NAICS`, `SIC`, `industry`, `establishment`, `employment`)
    and for FIA's own organising concepts (`species`, `land use`, `product`) across every FIA
    page this run fetched and hashed, named per page. A page joins that corpus only if it also
    became a registered extract (`scannable_text_page`: the retention gate *and* a 200), so the
    "fetched and hashed" phrase names artifacts a reader can re-grep and a status-200 empty body
    is counted by neither. `coverage_span.uncovered`'s industry-concept sentence is interpolated
    from these counts, and whichever reading those counts support is delimited by the
    `INFERENCE MARKER, OPENING`/`CLOSING` convention rather than stated as a further
    measurement. Three cases are distinct there and none borrows another's sentence: a scan over
    zero pages (every FIA fetch non-200) reports that it examined nothing rather than that it
    found nothing; a nonzero industry count withholds the zero-hit reading; and the taxonomy
    counts are reported, never asserted nonzero. The D.C. clause likewise separates "absent from
    a parsed index" from "no index was read".
  - `raw_retention_rule` — added by the implementation, and present in **both** summaries.
    States this script's non-200 retention rule inside the artifact the rule shaped, with
    counters (`extracts_recorded`, `extracts_with_non_200_status`,
    `non_200_statuses_recorded`) derived from the run. This script writes and registers a
    fetched body whenever the endpoint answered at all, whatever the status, stamped with the
    status it carried — because on an access-verdict probe the non-200 body *is* the evidence
    (a 404 page, a 403 page and an empty 200 are three different verdicts). Every other Stage 0
    audit script gates `record_extract` on `status == 200`; that divergence is deliberate and
    is why the rule is restated in the artifacts rather than only in a commit message.
  `tpo` `findings` keys:
  - `route_probes` — list of `{url, http_status, bytes, content_type, machine_readable}` for
    each candidate route. Each entry also carries an `origin` key added by the implementation
    (`brief` vs. `discovered (...)`), so a reader can see which probed URLs came from this
    section's three original candidates and which were found by following links from them —
    none of the three itself serves machine-readable data; the working route sits two hops
    further — and an `outcome` key from `classify_probe`, so `not_found` (the third brief
    candidate 404s, and its body is retained) is never read as `transport_failure`.
  - `raw_retention_rule` — added by the implementation; see the `fia` entry above.
  - `harvest_origin_available` — bool. §8.4 `SRC-FOR-001` requires harvest origin and mill
    receipts to occupy distinct fields; this records whether the origin measure is reachable.
  - `chosen_route` — the URL that yields machine-readable state-year data, or `null`.
  - `box_navigation` — added by the implementation. Neither `TPO_CANDIDATES` nor the
    `national-resource-use-monitoring-data-downloads` page (found by following a link from
    `programs/nrum`, not in this section's original candidate list) serves raw data directly —
    the latter links to a public Box folder whose share URL is read from that page's own
    markup each run (`share_url_discovered`), never hardcoded. `box_navigation` records the
    discovered folder id, every per-state-year subfolder name found under it
    (`year_subfolders_found`, `window_year_subfolders_found`), which D1-window year this run
    deterministically selected (`probed_year`: the latest window year with a subfolder) and
    its listing (`files_listed_this_page` vs. Box's own `filescount_per_box_metadata`, checked
    for pagination truncation), and the selected sample file's sheet names and header row —
    the direct evidence behind `harvest_origin_available`. Added by the implementation for the
    same reason: `sample_file_first_sheet_name` and `sample_file_first_sheet_unresolved`, since
    the header row is read from the sheet the workbook's own relationship part binds to its
    first `<sheet>` element (`xlsx_first_sheet_part`) rather than from whichever worksheet is
    filed under `sheet1.xml`, and a first sheet that cannot be resolved is recorded as a named
    gap; and `shared_folder_parse_error`, which is what lets `compose_tpo_access` tell "the
    share page never answered" from "it answered and did not parse" instead of reading a share
    URL's presence in the markup as proof the folder was entered. These header names are
    themselves evidence, not decoration: `classify_header_row` picks out the county-identifier
    and volume/weight-measure columns, so `access.reason` can state from the header row —
    outside any inference marker — that the workbook carries county-resolved volume columns.
    Which county those identifiers name stays inside the marker, because a column name does not
    say whose county and no data-row cells were read or compared across sheets.

- [ ] **Step 1: Write the script**

Create `scripts/audit/forest_sources.py`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""SRC-FOR-001/002/003: record access verdicts for FIA (`/fullreport` parameters, sampling
error, evaluation vintage) and TPO harvest-origin data. `not_obtainable` is a legitimate
verdict, but only when it is earned by the probes recorded here -- never inherited from a
prior review's inability to find a URL, and never from Appendix A already shipping
`tpo.enabled: false` / `fia.enabled: false`.

This run found both sources reachable. FIA's `/fullreport` returns a real, machine-readable
estimate (with sampling error) once called with the parameters its own doc page marks required
-- the brief's illustrative call omitted all four and got back a 200-status EVALIDator *error*
page, not a report. Which estimate it returns is not incidental and is never left implicit
here: the response names its own measure in `metadata.numEstDesc`/`metadata.estMeta`, and the
access verdict quotes that name, because "the endpoint answers" and "the endpoint answers with
the harvest-origin measure SS2.2 requires" are two different claims. Whether FIA publishes a
harvest-origin measure *at all* is settled separately, by enumerating the estimate attributes
its own `/fullreport/parameters/snum` catalog lists. TPO's harvest-origin data is not at any of
the brief's three candidate URLs, but two hops from the first of them
(`research.fs.usda.gov/programs/nrum` -> its own "data downloads" page -> a public Box folder)
sits a real, county-level, per-state production table, fetchable once you use Box's
undocumented legacy download redirect instead of its modern (session-gated) share URL. See
`main()` for the full probe sequence and `tests/audit/test_forest_sources.py` for what is
pinned about each parsing step.

Raw-retention rule, specific to this script (ruling D-B). Every other Stage 0 audit script
records a fetched body only when the status is 200. This one records a body whenever the
endpoint answered at all, whatever the status, and stamps each extract with the status it
actually carried -- because on an access-verdict probe the non-200 body IS the evidence: a 404
page, a 403 page and an empty 200 are three different verdicts, and only the retained bytes
tell them apart. A transport failure yields no body and so registers no extract; its evidence
is the probe record's `outcome` field instead. `compose_retention_rule` restates this inside
both written summaries, with counts derived from the run, so a reader of the artifacts (not
just of this file, or of a commit message) sees the rule and its scope.
"""

from __future__ import annotations

import html as html_module
import io
import json
import re
import time
import zipfile
from collections.abc import Callable

import httpx

import _common as c

SOURCE_FIA = "fia"
SOURCE_TPO = "tpo"

FIA_DOC = "https://apps.fs.usda.gov/fiadb-api/"
FIA_FULLREPORT = "https://apps.fs.usda.gov/fiadb-api/fullreport"
FIA_WC_PARAMETERS = "https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/wc"
# `snum*` is the required parameter that selects WHICH estimate attribute /fullreport returns,
# and this is its catalog. Probed so the verdict can say whether FIA publishes a harvest-origin
# (removals) attribute at all -- a capability question the successful /fullreport call, which
# returned one area attribute, cannot answer by itself.
FIA_SNUM_PARAMETERS = "https://apps.fs.usda.gov/fiadb-api/fullreport/parameters/snum"
# The brief's own illustrative probe: outputFormat only, none of the doc page's four
# required parameters (wc*, snum*, rselected*, cselected*). Kept and probed so the finding
# that it returns a 200-status *error* page is recorded, not just asserted in this docstring.
FIA_NAIVE_PARAMS = {"outputFormat": "JSON"}
# The doc page's own documented Python-GET usage example (verbatim from the fetched page),
# not invented: it is the one call this run trusts to prove the endpoint returns real data.
FIA_REAL_PARAMS = {
    "rselected": "Land Use - Major",
    "cselected": "Land use",
    "snum": "79",
    "wc": "102020",
    "outputFormat": "NJSON",
}
# Named in the dispatch's lead table as the crux transport failure. Probed here as its own
# FIA route -- kept separate from the /fullreport verdict, per the three-outcome distinction.
FIA_DATAMART_CANDIDATES = (
    "https://apps.fs.usda.gov/fia/datamart/CSV/",
    "https://apps.fs.usda.gov/fia/datamart/datamart.html",
)
FIA_DATAMART_ATTEMPTS = 3
FIA_DATAMART_WAIT_SECONDS = 3.0
# Two more routes from the dispatch's lead table, each a single probe (no retry: both answer
# with a real status, not a transport failure).
FIA_OTHER_ROUTES = (
    "https://apps.fs.usda.gov/Evalidator/evalidator.jsp",
    "https://www.fs.usda.gov/research/programs/fia",
)

TPO_CANDIDATES = (
    "https://research.fs.usda.gov/programs/nrum",
    (
        "https://research.fs.usda.gov/products/dataandtools/"
        "timber-products-output-tpo-interactive-reporting-tool"
    ),
    "https://apps.fs.usda.gov/fiadb-api/tpo",
)
# Discovered by following links from the two research.fs.usda.gov pages above -- neither
# brief candidate links to a raw file; both link to further pages, and the brief's candidate
# list never followed them. Kept as its own tuple (not merged into TPO_CANDIDATES) so
# route_probes can show which URLs came from the brief and which were found by this run.
TPO_DISCOVERED_ROUTES = (
    # Linked from the TPO interactive-tool page: the actual "Interactive Reporting Tool".
    "https://public.tableau.com/views/TPOREPORTINGTOOL/MakeSelection?%3AshowVizHome=no",
    # Linked from the nrum program page: "National Resource Use Monitoring - Data Downloads".
    (
        "https://research.fs.usda.gov/products/dataandtools/"
        "national-resource-use-monitoring-data-downloads"
    ),
)
# "/xml"/"+xml" rather than a bare "xml": both real Office Open XML content types this run
# observed -- xlsx's ".spreadsheetml.sheet" and docx's ".wordprocessingml.document" -- contain
# the literal substring "xml" inside "openXMLformats" itself, so a bare "xml" test would flag
# the docx data-dictionary file as machine-readable data too (verified: it does, in a first
# draft of this constant that this task's own test suite caught).
MACHINE_TYPES = ("json", "csv", "/xml", "+xml", "zip", "excel", "spreadsheet")

# The public Box folder's share URL is NOT hardcoded here -- `discover_box_share_url` reads
# it from the fetched NRUM data-downloads page's own markup each run, the same discipline
# this codebase applies to every other code-to-value mapping (QCEW's own_code, CES's industry
# level selector, ...): a source identifier a fetched page supplies is read from that page,
# not carried in memory. Box's platform-wide legacy download endpoint is a fixed prefix, not
# specific to this share, so it stays a constant.
BOX_LEGACY_DOWNLOAD_BASE = "https://usfs-public.app.box.com/index.php"

WINDOW_YEARS = c.WINDOW_YEARS


# --- pure helpers: probes and classification ------------------------------------------------


def classify_probe(status: int, nbytes: int) -> str:
    """The three access outcomes the dispatch requires kept distinct: `_common.probe`'s
    `(0, 0)` sentinel means no response reached us at all (`transport_failure`) -- the
    weakest possible basis for `not_obtainable`, never conflated with a real `404`
    (`not_found`, the resource is confirmed absent) or a `200` (`reachable`, though not
    necessarily *usable* -- see `FIA_NAIVE_PARAMS`'s 200-status error page). Anything else
    (403, 301, 500, ...) is `other_status`: a real answer that is neither of the above."""
    if status == 0 and nbytes == 0:
        return "transport_failure"
    if status == 404:
        return "not_found"
    if status == 200:
        return "reachable"
    return "other_status"


def is_machine_readable(content_type: str) -> bool:
    ctype = (content_type or "").lower()
    return any(t in ctype for t in MACHINE_TYPES)


def probe_url(client: httpx.Client, url: str, *, params: dict | None = None) -> dict:
    """Like `_common.probe`, but keeps the response body and content-type -- needed for
    `record_extract` and for `route_probes`' `content_type`/`machine_readable` fields, which
    `_common.probe`'s `(status, bytes)` return does not carry. Catches the same
    `httpx.TransportError` family `_common.probe` does, with the same `(0, 0)` sentinel."""
    try:
        resp = client.get(url, params=params)
    except httpx.TransportError:
        return {"url": url, "http_status": 0, "bytes": 0, "content_type": "", "body": b""}
    return {
        "url": url,
        "http_status": resp.status_code,
        "bytes": len(resp.content),
        "content_type": resp.headers.get("content-type", ""),
        "body": resp.content,
    }


def answered_with_body(res: dict) -> bool:
    """Ruling D-B's retention gate: keep the bytes whenever the endpoint answered, whatever the
    status. A transport failure (`http_status == 0`) produced no response at all and so has no
    body to keep; its evidence is the probe record's `outcome` field instead."""
    return res["http_status"] != 0 and bool(res["body"])


def retain_body(extracts: list, source: str, res: dict, rel_path: str) -> None:
    """Append `res`'s body to `extracts` stamped with the status it actually carried -- never
    coerced to 200, which would erase the very distinction the retained non-200 body exists to
    record."""
    if answered_with_body(res):
        extracts.append(c.record_extract(
            source, res["url"], rel_path, res["body"], http_status=res["http_status"]))


def scannable_text_page(res: dict) -> bool:
    """Whether a probe's body joins the term-scan corpus. Deliberately the retention gate AND
    a 200, not the status alone: `industry_concept_scan` names its corpus as the pages this run
    "fetched and hashed", so every page it counts must also be a registered extract, and
    `retain_body` refuses an empty body. A status-200 response with no body would otherwise be
    counted in a sentence no extract backs."""
    return answered_with_body(res) and res["http_status"] == 200


def probe_record(res: dict, origin: str) -> dict:
    """One `route_probes` entry. Carries `classify_probe`'s outcome alongside the raw status so
    a reader is never left to classify a bare `http_status: 0` themselves -- the three-outcome
    distinction is the point of recording these at all."""
    return {
        "url": res["url"],
        "http_status": res["http_status"],
        "bytes": res["bytes"],
        "content_type": res["content_type"],
        "machine_readable": is_machine_readable(res["content_type"]),
        "outcome": classify_probe(res["http_status"], res["bytes"]),
        "origin": origin,
    }


def probe_with_retries(
    probe_fn: Callable[[], tuple[int, int]],
    *,
    url: str,
    attempts: int,
    wait_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> dict:
    """Bounded, spaced retries for a route that resets rather than answers -- "be a good
    citizen against USDA hosts": at most `attempts` requests, `wait_seconds` apart, stopping
    the moment any attempt gets a real response (status != 0). Every attempt's raw
    `(status, bytes)` and its `classify_probe` outcome are recorded, plus the wall-clock span
    actually spent, so a `transport_failure` verdict carries its own retry evidence rather
    than resting on a single try."""
    started = now()
    attempt_records = []
    for attempt_no in range(attempts):
        status, nbytes = probe_fn()
        attempt_records.append({
            "attempt": attempt_no + 1,
            "http_status": status,
            "bytes": nbytes,
            "outcome": classify_probe(status, nbytes),
        })
        if status != 0 or attempt_no == attempts - 1:
            break
        sleep(wait_seconds)
    return {
        "url": url,
        "attempts": attempt_records,
        "elapsed_seconds": round(now() - started, 3),
    }


# --- pure helpers: FIA doc-page and response parsing -----------------------------------------


def parse_fia_doc_parameters(html: str) -> list[dict]:
    """Derive the `/fullreport` parameter list from the doc page's own
    `<table title="Parameter descriptions">` -- not a hardcoded name whitelist. The brief's
    illustrative code matched a fixed regex alternation naming eight parameters, two of which
    (`schemaName`, `whereClause`) do not appear anywhere on the live page (verified: zero
    hits), and it missed thirteen real ones the table documents. Reading the table's actual
    rows, rather than guessing names, cannot repeat either failure mode."""
    match = re.search(r'<table title="Parameter descriptions">(.*?)</table>', html, re.DOTALL)
    if not match:
        return []
    params = []
    for row in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.DOTALL):
        name_match = re.search(r"<th[^>]*>(.*?)</th>", row, re.DOTALL)
        desc_match = re.search(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if not name_match or not desc_match:
            continue
        raw_name = re.sub(r"<[^>]+>", "", name_match.group(1)).strip()
        desc = re.sub(r"<[^>]+>", " ", desc_match.group(1))
        desc = html_module.unescape(re.sub(r"\s+", " ", desc)).strip()
        params.append({
            "parameter": raw_name.rstrip("*"),
            # A trailing "*" flags a required parameter on this page (lat*/lon*/radius* are
            # the one exception -- required only "FOR CIRCULAR ESTIMATES ONLY", per that row's
            # own description text -- left visible in `description` rather than special-cased
            # here, since this function only reports what the markup structurally encodes).
            "required": raw_name.endswith("*"),
            "description": desc,
        })
    return params


def sampling_error_field(estimates: list[dict]) -> str | None:
    """SRC-FOR-002: does this response carry sampling error "when available"? Checked against
    the real `/fullreport` response's `estimates` rows fetched this run, not asserted from
    documentation -- the doc page's Parameter Descriptions table says nothing about response
    field names at all. `SE` and `SE_PERCENT` are the field names this run actually observed;
    the rest of the candidate list is FIA's own EVALIDator terminology for the same concept,
    kept as a fallback in case a different report type omits `SE`."""
    if not estimates:
        return None
    candidates = ("SE", "SE_PERCENT", "SAMPLING_ERROR", "STD_ERROR", "ESTIMATE_SE")
    keys = estimates[0].keys()
    return next((candidate for candidate in candidates if candidate in keys), None)


def evaluation_vintage_field(metadata: dict) -> str | None:
    """SRC-FOR-003: the field naming the evaluation vintage / survey cycle. `evalGrps` is what
    this run's real response actually returned in `metadata` (echoing the `wc` request
    parameter, itself the evaluation group code -- state FIPS + 4-digit inventory year, per
    the doc page). The brief's candidate list (`EVALID|evalid|EVAL_GRP|INVYR|SURVEY_CYCLE`)
    does not contain this exact key and would have missed it."""
    if not metadata:
        return None
    candidates = ("evalGrps", "EVALID", "EVAL_GRP", "INVYR", "SURVEY_CYCLE")
    return next((candidate for candidate in candidates if candidate in metadata), None)


def parse_wc_evaluation_index(html: str) -> dict:
    """Parse `/fullreport/parameters/wc`: one row per (state, EVALID) -- the evaluation
    vintage catalog `wc*` itself is drawn from. Malformed-markup note, verified against the
    live 344 KB page: every row opens with `<th scope=row ...>` but the table never emits a
    matching `<tr>` opener (grepped directly: 1139 `</tr>` closers, zero `<tr>` openers), so
    rows are recovered by splitting the tbody on `</tr>`, not by matching a `<tr>...</tr>`
    pair -- the latter would silently find nothing."""
    body_match = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    if not body_match:
        return {"states": [], "year_min": None, "year_max": None, "row_count": 0}
    states: set[str] = set()
    years: list[int] = []
    row_count = 0
    for row in body_match.group(1).split("</tr>"):
        cells = re.findall(r"<t[hd][^>]*>([^<]*)</t[hd]>", row)
        if len(cells) != 8:
            continue
        row_count += 1
        states.add(cells[0].strip())
        for year_text in cells[4].split(";"):
            year_text = year_text.strip()
            if year_text.isdigit():
                years.append(int(year_text))
    return {
        "states": sorted(states),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "row_count": row_count,
    }


# The `snum` catalog's own ESTIMATE_GRP_DESCR wording. FIA separates three removals concepts:
# "Annual harvest removals *" (trees removed by harvesting), "Annual other removals *"
# (removals from land-use change and similar), and the combined "Annual removals *". SS2.2
# asks for harvest origin, so only the first is a harvest-origin measure -- a bare `removals`
# predicate would count all three and overstate what the catalog offers.
HARVEST_REMOVALS_GROUP_PATTERN = re.compile(r"(?i)\bharvest removals\b")
REMOVALS_GROUP_PATTERN = re.compile(r"(?i)\bremovals\b")
# The parameter tables on this API render 11 columns per row; a split that yields any other
# count is markup, not a data row.
SNUM_ROW_CELL_COUNT = 11


def parse_snum_estimate_attributes(html: str) -> dict:
    """Enumerate `/fullreport/parameters/snum`: every estimate attribute the API can return,
    and specifically which of them are harvest-removals attributes (ruling D-A).

    Same malformed markup as `/fullreport/parameters/wc` -- rows open with `<th scope=row ...>`
    and the tbody emits no `<tr>` opener -- so rows are recovered by splitting on `</tr>`, not
    by matching a pair. Column order is the page's own: ATTRIBUTE_NBR, ATTRIBUTE_DESCR,
    CONDTREESEED, LAND_BASIS, ESTIMATE_GRP_DESCR, EVAL_TYP, ... . The returned payload is
    deliberately a summary rather than all rows: per matching group a count and the lowest
    attribute number (the handle Stage 7 would use to request one), plus the full list of
    harvest-removals attribute numbers so membership of any *other* attribute number in that
    set is checkable rather than asserted."""
    body_match = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    empty = {
        "row_count": 0, "harvest_removals_groups": [], "harvest_removals_attribute_count": 0,
        "harvest_removals_attribute_nbrs": [], "non_harvest_removals_groups": [],
        "eval_typs_present": [],
    }
    if not body_match:
        return empty
    rows = []
    for row in body_match.group(1).split("</tr>"):
        cells = re.findall(r"<t[hd][^>]*>([^<]*)</t[hd]>", row)
        if len(cells) != SNUM_ROW_CELL_COUNT:
            continue
        rows.append([cell.strip() for cell in cells])
    if not rows:
        return empty

    groups: dict[str, dict] = {}
    harvest_nbrs: list[str] = []
    non_harvest_removals: set[str] = set()
    for nbr, _descr, _cts, _basis, group, eval_typ, *_rest in rows:
        if HARVEST_REMOVALS_GROUP_PATTERN.search(group):
            entry = groups.setdefault(
                group, {"estimate_group": group, "attribute_count": 0,
                        "lowest_attribute_nbr": nbr, "eval_typs": set()})
            entry["attribute_count"] += 1
            entry["eval_typs"].add(eval_typ)
            if _as_int(nbr) < _as_int(entry["lowest_attribute_nbr"]):
                entry["lowest_attribute_nbr"] = nbr
            harvest_nbrs.append(nbr)
        elif REMOVALS_GROUP_PATTERN.search(group):
            non_harvest_removals.add(group)
    return {
        "row_count": len(rows),
        "harvest_removals_groups": [
            {"estimate_group": g["estimate_group"], "attribute_count": g["attribute_count"],
             "lowest_attribute_nbr": g["lowest_attribute_nbr"],
             "eval_typs": sorted(g["eval_typs"])}
            for g in sorted(groups.values(), key=lambda g: g["estimate_group"])
        ],
        "harvest_removals_attribute_count": len(harvest_nbrs),
        "harvest_removals_attribute_nbrs": sorted(harvest_nbrs, key=_as_int),
        "non_harvest_removals_groups": sorted(non_harvest_removals),
        "eval_typs_present": sorted({r[5] for r in rows}),
    }


def _as_int(text: str) -> int:
    """Attribute numbers sort numerically, not lexically (`79` before `574161`). A
    non-numeric cell sorts last rather than raising: the page changing shape is a finding for
    the row count to expose, not a crash inside a sort key."""
    stripped = str(text).strip()
    return int(stripped) if stripped.isdigit() else 10**12


# Word-boundary, not substring: "SIC" occurs inside "BASIC" and "PHYSIOGRAPHIC", both of which
# appear in the real /fullreport response body, and a substring scan would report a nonzero
# industry-classification hit count off them alone.
INDUSTRY_CLASSIFICATION_TERMS = {
    "NAICS": r"(?i)\bNAICS\b",
    "SIC": r"\bSIC\b",
    "industry": r"(?i)\bindustr(?:y|ies)\b",
    "establishment": r"(?i)\bestablishment",
    "employment": r"(?i)\bemploy",
}
# The concepts FIA's own pages do organise by -- scanned alongside the terms above so the
# comparison is a measured contrast rather than a bare absence.
FIA_TAXONOMY_TERMS = {
    "species": r"(?i)\bspecies\b",
    "land use": r"(?i)\bland use\b",
    "product": r"(?i)\bproduct",
}


def count_term_hits(pages: dict[str, str], patterns: dict[str, str]) -> dict[str, int]:
    """Total word-boundary hits per term across the named page texts. The same machinery as
    `tpo_mentions_on_fia_doc_page`, generalised: a zero here is a measured zero over named,
    hashed extracts, which is what lets a "this source has no X concept" sentence be
    interpolated rather than typed. Every requested term gets an entry, including the zeros --
    an omitted key would read as "not checked"."""
    return {
        term: sum(len(re.findall(pattern, text)) for text in pages.values())
        for term, pattern in patterns.items()
    }


def proved_estimate_measure(metadata: dict) -> dict | None:
    """Which measure the successful `/fullreport` call actually returned, read from the
    response's own metadata rather than inferred from the request. `numEstDesc` echoes the
    zero-padded `snum` attribute number and its title; `estMeta` describes what that attribute
    estimates. Returns `None` when the response names neither -- the honest answer when the
    measure cannot be established, not a guess from the parameters sent."""
    num_est_desc = str(metadata.get("numEstDesc") or "").strip()
    est_meta = re.sub(r"<[^>]+>", " ", str(metadata.get("estMeta") or ""))
    est_meta = html_module.unescape(re.sub(r"\s+", " ", est_meta)).strip()
    if not num_est_desc and not est_meta:
        return None
    leading = num_est_desc.split(" ", 1)[0] if num_est_desc else ""
    return {
        "num_est_desc": num_est_desc,
        "est_meta": est_meta,
        "attribute_nbr": leading.lstrip("0") if leading.isdigit() else "",
    }


# --- pure helpers: Box discovery and xlsx inspection -----------------------------------------


def extract_json_object(text: str, marker: str) -> str:
    """Balanced-brace, string-aware extraction of the JSON object assigned right after
    `marker` in a `<script>...marker = {...};...</script>` blob. Box's share pages embed real
    JSON (not a JS literal with bare identifiers), so a scan that tracks string context -- not
    a naive brace count, which a literal `}` inside a string value would defeat -- can extract
    it exactly. Raises `ValueError` if `marker` is absent or the braces never balance: both
    mean the page changed shape, not something to guess past."""
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"marker {marker!r} not found")
    start = idx + len(marker)
    while start < len(text) and text[start] in " \t\r\n":
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"marker {marker!r} not followed by an object")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    raise ValueError(f"unbalanced braces after marker {marker!r}")


def discover_box_share_url(html: str) -> str | None:
    """The public Box folder's share URL, read from an `href` in the fetched NRUM
    data-downloads page rather than hardcoded -- the identifier changes with the page, so a
    hardcoded value would silently go stale the moment USDA rotates the share. Returns `None`
    (not a stale guess) when no such link is present."""
    match = re.search(r'href="(https://[a-z0-9.-]+\.app\.box\.com/s/[A-Za-z0-9]+)"', html)
    return match.group(1) if match else None


def box_shared_folder_items(html: str) -> dict:
    """Parse Box's embedded `Box.postStreamData` blob for the
    `/app-api/enduserapp/shared-folder` payload: the current folder's id/name and its
    immediate items (files and subfolders). Box's page renders no such listing anywhere in
    visible HTML text -- only in this embedded JSON -- so this IS the discovery mechanism,
    not a convenience shortcut around one."""
    payload = json.loads(extract_json_object(html, "Box.postStreamData = "))
    folder = payload.get("/app-api/enduserapp/shared-folder")
    if folder is None:
        raise ValueError("Box.postStreamData carries no shared-folder payload")
    return folder


def box_legacy_download_url(shared_name: str, file_id: int | str) -> str:
    """Box's back-compat `rm=box_download_shared_file` redirect -- the only route this run
    found that returns raw file bytes for a Box-hosted public share with a plain GET. The
    modern share URL (discovered via `discover_box_share_url`) serves a 200 HTML app shell,
    and the `authenticated_download_url` embedded in that shell's JSON 401s without a browser
    session (both verified live this run) -- this legacy endpoint is undocumented anywhere on
    Box's or USDA's pages; it was found by reading the share page's own JS bundle."""
    return (
        f"{BOX_LEGACY_DOWNLOAD_BASE}?rm=box_download_shared_file"
        f"&shared_name={shared_name}&file_id=f_{file_id}"
    )


def select_latest_window_year_folder(items: list[dict], window_years: tuple[int, ...]) -> dict | None:
    """The most recent D1-window year with its own subfolder in the NRUM Data share --
    deterministic and reproducible (not "whichever state/year looked convenient"): among
    subfolders named a 4-digit year inside `window_years`, the one with the largest year."""
    candidates = [
        it for it in items
        if it.get("type") == "folder" and str(it.get("name", "")).isdigit()
        and int(it["name"]) in window_years
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda it: int(it["name"]))


def select_first_file(items: list[dict]) -> dict | None:
    """The alphabetically first file in a folder listing -- deterministic and reproducible,
    not a cherry-picked state. Folders are excluded."""
    files = sorted(
        (it for it in items if it.get("type") == "file"),
        key=lambda it: it.get("name") or "",
    )
    return files[0] if files else None


def xlsx_sheet_names(workbook_xml: str) -> list[str]:
    return re.findall(r'<sheet [^>]*name="([^"]*)"', workbook_xml)


def xlsx_shared_strings(shared_strings_xml: str) -> list[str]:
    return [
        html_module.unescape(s)
        for s in re.findall(r"<t[^>]*>(.*?)</t>", shared_strings_xml, re.DOTALL)
    ]


def xlsx_header_row(sheet_xml: str, shared_strings: list[str]) -> list[str]:
    """First-row (`r="1"`), string-typed (`t="s"`) cell values in column order -- the column
    headers. Non-string row-1 cells are silently skipped: every TPO workbook this run
    inspected has an entirely string-typed header row, so a numeric or blank header cell
    would be a real schema surprise, not something to coerce past."""
    row_match = re.search(r'<row r="1"[^>]*>(.*?)</row>', sheet_xml, re.DOTALL)
    if not row_match:
        return []
    indices = re.findall(r'<c r="[A-Z]+1"[^>]*t="s"[^>]*><v>(\d+)</v></c>', row_match.group(1))
    return [shared_strings[int(i)] for i in indices]


def xlsx_first_sheet_part(workbook_xml: str, rels_xml: str) -> tuple[str, str] | None:
    """The workbook's first sheet as `(name, zip path)`, resolved through the relationship id
    that `<sheet>` carries. Sheet order in `workbook.xml` and the `sheetN.xml` filenames are
    independent -- the relationship part is what binds them -- so reading
    `xl/worksheets/sheet1.xml` and calling it the first sheet is an assumption where this is a
    derivation. Returns `None` when the workbook lists no sheet or the relationship is absent;
    the caller records that gap rather than falling back to a guess."""
    sheet = re.search(r"<sheet\b[^>]*>", workbook_xml)
    if not sheet:
        return None
    name = re.search(r'\bname="([^"]*)"', sheet.group(0))
    rel_id = re.search(r'\br:id="([^"]*)"', sheet.group(0))
    if not name or not rel_id:
        return None
    target = re.search(
        rf'<Relationship\b[^>]*\bId="{re.escape(rel_id.group(1))}"[^>]*\bTarget="([^"]*)"',
        rels_xml,
    )
    if not target:
        return None
    return html_module.unescape(name.group(1)), "xl/" + target.group(1).lstrip("/")


def inspect_xlsx(content: bytes) -> dict:
    """Sheet names and the first sheet's header row, read directly from the xlsx zip
    container with `zipfile` + `re` -- no new dependency (`openpyxl`/`polars` are not in this
    script's PEP 723 block), since only structural facts (sheet names, header cells) are
    needed to evidence SRC-FOR-001, not the full data table."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        names = zf.namelist()
        workbook_xml = zf.read("xl/workbook.xml").decode("utf-8", "replace")
        sheets = xlsx_sheet_names(workbook_xml)
        rels_xml = (
            zf.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
            if "xl/_rels/workbook.xml.rels" in names else ""
        )
        first = xlsx_first_sheet_part(workbook_xml, rels_xml)
        shared = (
            xlsx_shared_strings(zf.read("xl/sharedStrings.xml").decode("utf-8", "replace"))
            if "xl/sharedStrings.xml" in names else []
        )
        unresolved = ""
        headers: list[str] = []
        if first is None:
            unresolved = "no <sheet> element resolved to a worksheet part via its r:id"
        elif first[1] not in names:
            unresolved = f"first sheet's relationship target {first[1]} is not in the container"
        else:
            headers = xlsx_header_row(zf.read(first[1]).decode("utf-8", "replace"), shared)
    return {
        "sheet_names": sheets,
        "first_sheet_name": first[0] if first else "",
        "first_sheet_headers": headers,
        "first_sheet_unresolved": unresolved,
    }


# Header-row classification. Both patterns are anchored rather than substring tests: a
# `COUNTY`-prefixed name identifies a county, while `RPA_STD_AMOUNT_UOM_CODE` names the unit a
# measure is expressed in, not a measured volume, and would be swept in by a bare "amount" or
# an unanchored "vol".
COUNTY_IDENTIFIER_HEADER_PATTERN = re.compile(r"(?i)^county")
VOLUME_MEASURE_HEADER_PATTERN = re.compile(r"(?i)(?:vol|tons)$")


def classify_header_row(headers: list[str]) -> dict:
    """Which of a sheet's column names identify a county and which name a volume or weight
    measure. This is what lets the TPO verdict say -- from the header row this run actually
    read, not from a sheet name -- that the workbook carries county-resolved volume columns.
    What it cannot say is *whose* county: a column named COUNTY_NAME is as consistent with a
    mill's county as with a harvest county, which is why the origin/receipt reading stays
    inside the inference marker."""
    return {
        "county_identifier_headers": [
            h for h in headers if COUNTY_IDENTIFIER_HEADER_PATTERN.search(h)],
        "volume_measure_headers": [
            h for h in headers if VOLUME_MEASURE_HEADER_PATTERN.search(h)],
    }


HARVEST_ORIGIN_SHEET_PATTERN = re.compile(r"(?i)\bproduction\b")
MILL_RECEIPT_SHEET_PATTERN = re.compile(r"(?i)\breceipts?\b|\bmill\b")


def distinguishes_harvest_origin_from_mill_receipts(sheet_names: list[str]) -> bool:
    """SRC-FOR-001: TPO variables MUST distinguish harvest origin from mill receipts. True iff
    the fetched workbook has at least one sheet reading as harvest-origin production and at
    least one distinct sheet reading as mill receipts -- checked against the actual sheet
    names in the workbook this run fetched, not asserted from the landing page's prose."""
    has_origin = any(HARVEST_ORIGIN_SHEET_PATTERN.search(s) for s in sheet_names)
    has_receipts = any(MILL_RECEIPT_SHEET_PATTERN.search(s) for s in sheet_names)
    return has_origin and has_receipts


# --- pure helpers: verdict and prose composition ----------------------------------------------
#
# Everything below composes a sentence that gets persisted into a summary. They are pure
# functions taking already-measured values precisely so each branch can be tested directly:
# a verdict sentence is a claim about how much a check proves, which is exactly as unverified
# as a claim about data and inherits credibility from the measured material beside it.


def compose_retention_rule(extract_statuses: list[int]) -> dict:
    """Ruling D-B: this script's raw-retention rule, restated inside the artifact that the rule
    shaped, with its counters derived from the run rather than typed."""
    return {
        "rule": (
            "This script writes and registers a fetched body whenever the endpoint answered at "
            "all, whatever the HTTP status, and each extract's own http_status records which "
            "status it carried. On an access-verdict probe the non-200 body IS the evidence: a "
            "404 page, a 403 page and an empty 200 are three different verdicts and only the "
            "retained bytes tell them apart. A transport failure produces no body and so "
            "registers no extract; its evidence is the probe record's outcome field instead. "
            "The counters below therefore say which statuses were retained and nothing more: a "
            "retained status 200 means the endpoint answered, not that the body is usable data "
            "-- an application error page can arrive with status 200, and which retained bodies "
            "are usable is recorded per probe in findings, never inferable from an extract's "
            "http_status. Reader's caution: this rule is this script's, and the absence of a "
            "non-200 extract under another source in this audit is not evidence that no "
            "non-200 response occurred there."
        ),
        "extracts_recorded": len(extract_statuses),
        "extracts_with_non_200_status": sum(1 for s in extract_statuses if s != 200),
        "non_200_statuses_recorded": sorted({s for s in extract_statuses if s != 200}),
    }


def compose_fia_access(
    *,
    route: str,
    doc_params_parsed: bool,
    real_probe_parsed: bool,
    measure_proved: dict | None,
    snum_index: dict,
) -> dict:
    """The FIA access verdict and the sentence that justifies it.

    Two things are kept apart that the first implementation ran together. Retrieval was proved
    for exactly one estimate attribute -- the one `snum` selected -- and the response names it,
    so the reason quotes that name instead of leaving "returns real data" to be read as
    "returns the measure this project needs". Whether a harvest-origin measure exists at all is
    a separate question, answered by the `snum` catalog, and `verified` is withheld unless that
    catalog was read AND lists harvest-removals attributes: a capability nothing this run could
    read is not a capability this run verified.

    Each branch is a complete, independent sentence, and no clause shared across branches
    names an outcome that differs between them. The `documented` branch names which of
    `doc_params_parsed` / `real_probe_parsed` actually held rather than asserting both. The
    `verified` opening claims retrieval only -- never that the measure was named -- because
    `real_probe_parsed` requires non-empty estimates and metadata but not the `numEstDesc` /
    `estMeta` keys that name the returned attribute, so a response that names nothing reaches
    this branch. For the same reason the closing clause refers back to an attribute number
    only when one was read: `proved_estimate_measure` returns a record whenever *either*
    metadata field is present, and its `attribute_nbr` is empty when `numEstDesc` opens with a
    non-numeric token."""
    if not (doc_params_parsed and real_probe_parsed):
        clauses = [
            "the /fiadb-api/ documentation page's parameter table parsed"
            if doc_params_parsed else
            "the /fiadb-api/ documentation page's parameter table did not parse",
            "the real-parameter /fullreport probe returned a report with both estimates and "
            "metadata" if real_probe_parsed else
            "the real-parameter /fullreport probe did not return a report with both estimates "
            "and metadata",
        ]
        return {"route": route, "status": "documented", "reason": (
            "Not verified this run: " + "; ".join(clauses)
            + ". See findings.doc_parameters and findings.probe."
        )}

    numbered = measure_proved is not None and bool(measure_proved["attribute_nbr"])
    if numbered:
        measured = (
            "the response's own metadata names what came back as attribute "
            f'{measure_proved["attribute_nbr"]}, "{measure_proved["num_est_desc"]}" -- '
            f'"{measure_proved["est_meta"]}"'
        )
    elif measure_proved is not None:
        measured = (
            "the response's own metadata names what came back as "
            f'"{measure_proved["num_est_desc"]}" -- "{measure_proved["est_meta"]}", with no '
            "leading attribute number this script could read out of it"
        )
    else:
        measured = (
            "the response carried no numEstDesc/estMeta metadata naming the measure it "
            "returned, so which attribute was retrieved is not established by the response "
            "itself"
        )
    row_count = snum_index["row_count"]
    harvest_count = snum_index["harvest_removals_attribute_count"]

    if row_count == 0:
        return {"route": route, "status": "documented", "reason": (
            f"The /fullreport route answered with real machine-readable data this run "
            f"({measured}), but the /fullreport/parameters/snum attribute catalog could not be "
            "read this run, so whether FIA publishes a harvest-origin (removals) estimate "
            "attribute at all is unestablished here. See findings.probe and "
            "findings.snum_estimate_attributes."
        )}
    if harvest_count == 0:
        return {"route": route, "status": "documented", "reason": (
            f"The /fullreport route answered with real machine-readable data this run "
            f"({measured}), but the /fullreport/parameters/snum catalog fetched this run "
            f"enumerates {row_count} estimate attributes and none of them is a harvest-removals "
            "attribute, so the harvest-origin measure SS2.2 asks for is not obtainable from "
            "this endpoint on the evidence gathered here. See "
            "findings.snum_estimate_attributes."
        )}

    groups = "; ".join(
        f"{g['estimate_group']} ({g['attribute_count']} attribute(s), lowest attribute number "
        f"{g['lowest_attribute_nbr']}, EVAL_TYP {'/'.join(g['eval_typs'])})"
        for g in snum_index["harvest_removals_groups"]
    )
    non_harvest = ", ".join(snum_index["non_harvest_removals_groups"]) or "none"
    proved_is_harvest = (
        numbered
        and measure_proved["attribute_nbr"] in snum_index["harvest_removals_attribute_nbrs"]
    )
    if not numbered:
        gap = (
            "No attribute number could be read out of this run's response, so what came back "
            "cannot be checked against those harvest-removals attribute numbers: what this run "
            "proved end to end is retrieval of one report from this endpoint, while the "
            "harvest-removals capability rests on the fetched catalog listing those attributes "
            "and not on a harvest-removals report having been requested and returned."
        )
    elif proved_is_harvest:
        gap = (
            "That attribute number is itself one of those harvest-removals attributes, so a "
            "harvest-removals report is what this run requested and received."
        )
    else:
        gap = (
            "That attribute number is not one of those harvest-removals attributes: what this "
            "run proved end to end is retrieval of the one measure named above, while the "
            "harvest-removals capability rests on the fetched catalog listing those attributes "
            "and not on a harvest-removals report having been requested and returned."
        )
    return {"route": route, "status": "verified", "reason": (
        f"Verified for retrieval of one report from this endpoint: {measured}. The "
        f"/fullreport/parameters/snum catalog fetched this run enumerates {row_count} estimate "
        f"attributes, of which {harvest_count} sit in harvest-removals estimate groups -- "
        f"{groups} -- which that same catalog keeps distinct from its non-harvest removals "
        f"groups ({non_harvest}). {gap} See findings.snum_estimate_attributes."
    )}


def compose_fia_uncovered(
    *, industry_scan: dict, dc_has_evaluation: bool, wc_row_count: int
) -> str:
    """`coverage_span.uncovered` for FIA. The industry-concept claim is interpolated from a
    term scan over this run's own extracts (the same derivation `tpo_mentions_on_fia_doc_page`
    uses), and whatever reading is drawn from the resulting counts is delimited by the
    `INFERENCE MARKER, OPENING`/`CLOSING` pair `qcew_identity.absent_state_months_note`
    established, so the marking's scope ends where the reader can see it end. The D.C. clause
    is itself measured and therefore sits outside the marker.

    Three outcomes are kept apart that one string used to run together. A scan over zero pages
    -- what every FIA fetch returning non-200 produces -- examined nothing, and a scan that
    examined nothing must not read as a scan that found nothing. A scan over pages that DID
    turn up industry terms cannot carry the zero-hit reading either. And the count of FIA's own
    taxonomy terms is reported, never asserted to be nonzero, since the function does not
    branch on it. The same distinction governs D.C.: `dc_has_evaluation` is False both when the
    fetched index omits D.C. and when no index was read at all."""
    industry_counts = industry_scan["industry_classification_terms"]
    taxonomy_counts = industry_scan["fia_taxonomy_terms"]
    industry = ", ".join(f"{t}={c}" for t, c in sorted(industry_counts.items()))
    taxonomy = ", ".join(f"{t}={c}" for t, c in sorted(taxonomy_counts.items()))
    industry_total = sum(industry_counts.values())
    pages = industry_scan["pages_scanned"]
    text = "no monthly resolution: SRC-FOR-004 forbids interpolating to months. "
    if not pages:
        text += (
            "No FIA page was fetched and hashed this run, so the industry-term scan ran over "
            "no pages and reports nothing about FIA: a scan that examined no pages is not a "
            "scan that found no industry terms, and whether FIA carries an industry concept a "
            "Logging (113310) slice could be selected on is unestablished here."
        )
    else:
        reading = (
            "Zero industry-term hits across those pages is read here as FIA carrying no "
            "industry concept to join on at all, so a Logging (113310) slice cannot be "
            "selected out of FIA the way it is out of QCEW or CBP and Stage 7 would need its "
            "own crosswalk from FIA's species/product/land-use taxonomy instead; the competing "
            "reading -- that an industry concept exists elsewhere in the API and merely goes "
            "unmentioned on the pages this script happens to fetch -- is not excluded by a "
            "zero count over those pages."
            if industry_total == 0 else
            f"{industry_total} industry-term hit(s) across those pages leaves the no-industry-"
            "concept reading this scan was written to test unavailable: a nonzero hit count is "
            "not itself an industry concept a Logging (113310) slice could be selected on, and "
            "which of those hits (if any) name a classification FIA could be joined on is not "
            "established by a count."
        )
        text += (
            f"Also measured, over the {len(pages)} FIA page(s) this run fetched and hashed "
            f"({', '.join(pages)}): word-boundary hits for the classification codes and "
            f"measures an industry-coded source would carry are {industry}, and hits for the "
            f"species/product/land-use concepts FIA organises its own reporting by are "
            f"{taxonomy}. "
            "INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of "
            "those counts, not a further measurement; it is supplied by hand, carries no "
            f"extract hash and is re-checked by no later run. {reading} "
            "INFERENCE MARKER, CLOSING."
        )
    if wc_row_count == 0:
        text += (
            " The /fullreport/parameters/wc evaluation index was not read this run (zero rows "
            "parsed), so whether FIA has an evaluation unit for the District of Columbia -- "
            "states_dc's 51st member -- is unestablished here rather than answered no."
        )
    elif not dc_has_evaluation:
        text += (
            " Also measured: no FIA evaluation unit for the District of Columbia -- absent from "
            f"the {wc_row_count}-row evaluation index fetched this run (states_dc's 51st member "
            "has no forest inventory)."
        )
    return text


def compose_cadence_claim(
    box_navigation: dict, *, window_years: tuple[int, ...], window_start_year: int
) -> str:
    """`coverage_span.covered` for TPO. Every clause is computed from `box_navigation` -- what
    THIS run's own probes found -- rather than typed from the investigation that shaped this
    script. That investigation happened to land on 2021/Ohio and observed a page-capped listing
    (20 rendered vs a filesCount of 37); a run's deterministic selection can land on a
    different year entirely, so a claim written against the investigation's year would be false
    about the year actually checked."""
    year_folders = sorted(int(y) for y in box_navigation.get("year_subfolders_found", []))
    pre_window = [y for y in year_folders if y < window_start_year]
    window_found = box_navigation.get("window_year_subfolders_found", [])
    fully_annual = (
        sorted(int(y) for y in window_found) == list(window_years) if window_found else False
    )
    if fully_annual:
        claim = (
            "a per-state-year subfolder exists in the NRUM Data Box share for every D1 window "
            f"year (verified this run: {window_found}); this directly contradicts a blanket "
            "'TPO is biennial, not annual' claim for the D1 window specifically, though whether "
            "every individual state resurveys annually (as opposed to the release/folder "
            "cadence being annual) was not checked"
        )
    elif window_found:
        claim = (
            f"per-state-year subfolders found for D1 window years {window_found} out of "
            f"{list(window_years)} (verified this run) -- window coverage by folder is "
            "incomplete, not annual throughout"
        )
    else:
        claim = "no D1 window year subfolder was found this run"
    if pre_window and all(y % 2 == 1 for y in pre_window):
        claim += (
            f"; pre-{window_start_year} subfolders found only for odd years back to "
            f"{min(pre_window)} (biennial cadence, verified this run)"
        )
    elif pre_window:
        claim += (
            f"; pre-{window_start_year} subfolders found for years {pre_window} (not strictly "
            "biennial, verified this run)"
        )
    return claim


def compose_pagination_note(box_navigation: dict) -> str:
    """Whether Box's rendered listing for the probed year matched that folder's own
    `filesCount`. Three real outcomes, not two: fewer rendered than claimed is a page cap,
    equal is a match, and MORE rendered than claimed is neither -- the two counts simply
    disagree, and calling that an exact match (as an `else` after `listed < claimed` does)
    states an outcome that did not happen. The shared opening clause names both numbers and no
    outcome, so it is true in every branch it prefixes."""
    listed = box_navigation.get("files_listed_this_page")
    claimed = box_navigation.get("filescount_per_box_metadata")
    year = box_navigation.get("probed_year")
    if listed is None or claimed is None:
        return (
            "the per-year rendered-item-count vs. filesCount comparison was not performed this "
            "run (year folder listing unavailable)"
        )
    if listed == claimed:
        return (
            f"for the probed year ({year}), Box's rendered item list returned {listed} files, "
            f"matching that folder's filesCount metadata ({claimed}) exactly -- no truncation "
            "observed for this specific year, though only the one year named here was checked "
            "and a different year could still be page-capped"
        )
    opening = (
        f"for the probed year ({year}), Box's rendered item list returned {listed} files while "
        f"that folder's own filesCount metadata claims {claimed}"
    )
    if listed < claimed:
        return opening + " -- fewer rendered than claimed, i.e. page-capped for at least this year"
    return opening + (
        " -- more rendered than claimed, so the two counts disagree in the opposite direction "
        "and neither can be taken as this folder's file count without checking which one Box "
        "means"
    )


def compose_tpo_access(
    *, route: str, harvest_origin_available: bool, box_navigation: dict, probes: list[dict]
) -> dict:
    """The TPO access verdict and the sentence that justifies it.

    `not_obtainable` branches on what actually stopped the run, because each state is different
    evidence and a clause naming one of them is false on the others. Finding a share URL in the
    page markup is not entering the folder: the share page can then answer 5xx (an answer, so
    not a transport failure either) or answer with a body that does not parse as a Box listing,
    and on both of those nothing was entered and nothing was fetched. `year_subfolders_found`
    is set only once the share page answered with a status-200 body, and
    `nrum_data_folder_id` only once that body parsed, so the cascade below reads those two
    rather than the share URL's mere presence. A probed URL that never answered at all is what
    `classify_probe`'s docstring calls the weakest possible basis for `not_obtainable`, and the
    sentence says so rather than letting a network failure read as a finding about the source.

    The `verified` branch keeps three kinds of statement visibly apart: what the workbook's own
    bytes show (sheet names, and the header row this run read out of the first sheet), what is
    read *from* those sheet names, and what is carried over from the investigation that found
    this route and was not measured by any probe in this run. The second and third each sit in
    their own marked span."""
    transport_failed = [p["url"] for p in probes if p.get("outcome") == "transport_failure"]
    if harvest_origin_available:
        sheets = box_navigation.get("sample_file_sheet_names", [])
        origin = [s for s in sheets if HARVEST_ORIGIN_SHEET_PATTERN.search(s)]
        receipts = [s for s in sheets if MILL_RECEIPT_SHEET_PATTERN.search(s)]
        headers = box_navigation.get("sample_file_first_sheet_headers", [])
        classes = classify_header_row(headers)
        counties = classes["county_identifier_headers"]
        volumes = classes["volume_measure_headers"]
        if not headers:
            header_clause = (
                "No header row was read from that workbook's first sheet this run"
                + (f" ({box_navigation['sample_file_first_sheet_unresolved']})"
                   if box_navigation.get("sample_file_first_sheet_unresolved") else "")
                + ", so nothing here rests on its column names."
            )
        else:
            header_clause = (
                "Its first sheet "
                f"({box_navigation.get('sample_file_first_sheet_name') or 'name unresolved'}) "
                f"carries a {len(headers)}-column header row, {headers}, of which {counties} "
                "match this script's county-identifier pattern and "
                f"{volumes} match its volume/weight-measure pattern."
            )
            if counties and volumes:
                header_clause += (
                    " A county identifier and volume measures therefore share that header row: "
                    "the workbook carries county-resolved volume columns, measured from the "
                    "header row itself rather than read off a sheet name. Which county those "
                    "identifiers name -- the county a harvest came from, or the county a mill "
                    "sits in -- is not settled by a column name."
                )
        return {"route": route, "status": "verified", "reason": (
            "Reachable and machine-readable, but only via an undocumented Box legacy-download "
            "redirect rather than the modern share URL; per-state coverage per year is not "
            "exhaustively verified (see coverage_span). Measured in the one workbook fetched "
            f"this run ({box_navigation.get('sample_file')}, from the "
            f"{box_navigation.get('probed_year')} subfolder): its {len(sheets)} sheet names are "
            f"{sheets}, of which {origin} match this script's harvest-origin sheet-name pattern "
            f"and {receipts} match its mill-receipt pattern. {header_clause} "
            "INFERENCE MARKER, OPENING: what follows to the closing marker is a reading of "
            "those sheet names, not a further measurement; it is supplied by hand, carries no "
            "extract hash and is re-checked by no later run. Sheets named that way are read "
            "here as meaning the workbook holds harvest volumes attributed to the county of "
            "harvest in fields distinct from its mill-receipt fields, which is what "
            "SRC-FOR-001 requires. No data-row cells were read or compared across sheets, so "
            "the origin/receipt split rests on the sheet names alone; and only this one "
            "state-year workbook was inspected, so whether every state-year workbook in the "
            "share shares this sheet structure was not checked either. INFERENCE MARKER, "
            "CLOSING. INFERENCE MARKER, OPENING: how this route was found comes from the "
            "investigation that shaped this script rather than from this run -- the "
            "legacy-download redirect was found by reading the share page's own JS bundle, and "
            "the share page's embedded authenticated_download_url was observed there to answer "
            "401 without a browser session. No probe in this run requested that URL, so both "
            "statements carry no extract hash and are re-checked by no later run. INFERENCE "
            "MARKER, CLOSING."
        )}

    share_url = box_navigation.get("share_url_discovered")
    share_page_answered = "year_subfolders_found" in box_navigation
    folder_parsed = box_navigation.get("nrum_data_folder_id") is not None
    year_folders = box_navigation.get("year_subfolders_found", [])
    probed_year = box_navigation.get("probed_year")
    parse_error = box_navigation.get("shared_folder_parse_error")
    inspection_error = box_navigation.get("sample_file_inspection_error")
    if share_url is None:
        stopped = (
            "no Box share link matching the discovery pattern was present in the fetched NRUM "
            "data-downloads page markup, so the folder route was never entered"
        )
    elif not share_page_answered:
        stopped = (
            f"a Box share URL was read out of that page this run ({share_url}), but it did not "
            "answer this run with a status-200 body, so the folder behind it was never listed "
            "and no workbook was fetched from it"
        )
    elif not folder_parsed:
        stopped = (
            f"the Box share URL read out of that page this run ({share_url}) answered with a "
            "body, but that body did not parse as a Box folder listing"
            + (f" ({parse_error})" if parse_error else "")
            + ", so no year subfolder was reached and no workbook was fetched"
        )
    elif probed_year is None:
        stopped = (
            f"the Box folder behind the share URL read out of that page this run ({share_url}) "
            f"was entered and listed {len(year_folders)} year subfolder(s) ({year_folders}), "
            "none of which this run selected to probe, so no workbook was fetched"
        )
    elif box_navigation.get("sample_file") is None:
        stopped = (
            f"the Box folder behind the share URL read out of that page this run ({share_url}) "
            f"was entered and its {probed_year} subfolder probed, but no workbook from that "
            "subfolder was both fetched and inspected this run"
            + (f" (inspection error: {inspection_error})" if inspection_error else "")
        )
    else:
        stopped = (
            f"the workbook inspected from the {probed_year} subfolder "
            f"({box_navigation['sample_file']}) has sheet names "
            f"{box_navigation.get('sample_file_sheet_names', [])}, which do not include both a "
            "sheet matching this script's harvest-origin pattern and a sheet matching its "
            "mill-receipt pattern, so harvest origin held distinct from mill receipts is not "
            "evidenced by the workbook this run fetched"
        )
    clauses = [stopped]
    if transport_failed:
        clauses.append(
            f"{len(transport_failed)} probed URL(s) returned no response at all "
            f"(transport_failure: {transport_failed}), so for those URLs this verdict rests on "
            "the absence of any answer rather than on an answer showing the data is absent -- "
            "the weakest basis this script records for not_obtainable, and one a re-run could "
            "overturn without anything at the source having changed"
        )
    return {"route": route, "status": "not_obtainable", "reason": (
        "Not obtained this run: " + "; ".join(clauses)
        + ". See findings.route_probes and findings.box_navigation."
    )}


# --- main -------------------------------------------------------------------------------------


def run_fia(client: httpx.Client) -> None:
    extracts: list = []
    # Page texts scanned for classification terms further down. Keyed by the extract filename
    # each was written to, so the scan's own record names hashed artifacts a reader can re-grep,
    # not "some pages".
    scanned_pages: dict[str, str] = {}

    doc = probe_url(client, FIA_DOC)
    doc_params: list[dict] = []
    tpo_mentions_on_doc_page = None
    retain_body(extracts, SOURCE_FIA, doc, "fiadb_api_doc.html")
    if scannable_text_page(doc):
        doc_text = doc["body"].decode("utf-8", "replace")
        scanned_pages["fiadb_api_doc.html"] = doc_text
        doc_params = parse_fia_doc_parameters(doc_text)
        # Checked here, in scope of this run's own fetch, rather than transcribed from the
        # dispatch's claim that the doc page never mentions TPO.
        tpo_mentions_on_doc_page = len(re.findall(r"(?i)\btpo\b", doc_text))

    wc_index = {"states": [], "year_min": None, "year_max": None, "row_count": 0}
    wc_resp = probe_url(client, FIA_WC_PARAMETERS)
    retain_body(extracts, SOURCE_FIA, wc_resp, "wc_evaluation_index.html")
    if scannable_text_page(wc_resp):
        wc_text = wc_resp["body"].decode("utf-8", "replace")
        scanned_pages["wc_evaluation_index.html"] = wc_text
        wc_index = parse_wc_evaluation_index(wc_text)

    # Ruling D-A: enumerate the estimate attributes /fullreport can return, so the verdict can
    # say whether a harvest-origin measure exists rather than only that the endpoint answers.
    # Seeded with the parser's own empty-result shape (not a hand-written literal that could
    # drift from it) so a non-200 snum page still leaves every key present and zeroed.
    snum_index = parse_snum_estimate_attributes("")
    snum_resp = probe_url(client, FIA_SNUM_PARAMETERS)
    retain_body(extracts, SOURCE_FIA, snum_resp, "snum_estimate_attributes.html")
    if scannable_text_page(snum_resp):
        snum_text = snum_resp["body"].decode("utf-8", "replace")
        scanned_pages["snum_estimate_attributes.html"] = snum_text
        snum_index = parse_snum_estimate_attributes(snum_text)

    naive_probe = probe_url(client, FIA_FULLREPORT, params=FIA_NAIVE_PARAMS)
    naive_is_error_page = (
        naive_probe["http_status"] == 200
        and b"Error Type" in naive_probe["body"]
    )
    retain_body(extracts, SOURCE_FIA, naive_probe, "fullreport_naive_probe.html")
    if scannable_text_page(naive_probe):
        scanned_pages["fullreport_naive_probe.html"] = naive_probe["body"].decode(
            "utf-8", "replace")

    real_probe = probe_url(client, FIA_FULLREPORT, params=FIA_REAL_PARAMS)
    estimates: list[dict] = []
    metadata: dict = {}
    real_probe_parsed = False
    retain_body(extracts, SOURCE_FIA, real_probe, "fullreport_real_probe.json")
    if scannable_text_page(real_probe):
        scanned_pages["fullreport_real_probe.json"] = real_probe["body"].decode(
            "utf-8", "replace")
        try:
            parsed = json.loads(real_probe["body"])
            estimates = parsed.get("estimates", [])
            metadata = parsed.get("metadata", {})
            real_probe_parsed = bool(estimates) and bool(metadata)
        except json.JSONDecodeError:
            real_probe_parsed = False

    se_field = sampling_error_field(estimates)
    ev_field = evaluation_vintage_field(metadata)
    measure_proved = proved_estimate_measure(metadata)

    datamart_probes = [
        probe_with_retries(
            lambda u=url: c.probe(client, u), url=url, attempts=FIA_DATAMART_ATTEMPTS,
            wait_seconds=FIA_DATAMART_WAIT_SECONDS)
        for url in FIA_DATAMART_CANDIDATES
    ]
    # `probe_url`, not `_common.probe`: these two routes answer with a real status, and the
    # non-200 one answers with a body that is itself the evidence of *how* it is closed
    # (ruling D-B). Which non-200 status that is has moved between runs -- `Evalidator/
    # evalidator.jsp` served 403 to one run and 500 to the next, and answered both within
    # seconds of each other on a hand check -- which is the case for retaining the bytes
    # rather than trusting a status transcribed into a comment: the run's own extract says
    # which it was. `_common.probe` discards bodies by construction, so it cannot retain that.
    other_route_probes = []
    for i, url in enumerate(FIA_OTHER_ROUTES):
        res = probe_url(client, url)
        retain_body(extracts, SOURCE_FIA, res, f"other_route_{i}.bin")
        other_route_probes.append(probe_record(res, "dispatch lead table"))

    industry_scan = {
        "pages_scanned": sorted(scanned_pages),
        "bytes_scanned": sum(len(t) for t in scanned_pages.values()),
        "industry_classification_terms": count_term_hits(
            scanned_pages, INDUSTRY_CLASSIFICATION_TERMS),
        "fia_taxonomy_terms": count_term_hits(scanned_pages, FIA_TAXONOMY_TERMS),
    }
    # Derived from this run's own fetched evaluation index, not transcribed from the dispatch
    # (which never made this claim) or from memory of the QCEW states_dc finding (a different
    # source, established in an earlier task): does FIA even have a state-level evaluation
    # unit for D.C.? Directly relevant to Appendix A's `geography_universe: 'states_dc'`.
    dc_has_fia_evaluation = "District of Columbia" in wc_index["states"]

    c.write_summary(
        SOURCE_FIA,
        coverage_span={
            # Derived from the fetched /fullreport/parameters/wc evaluation index (this run),
            # not typed: the program-wide span across every state/territory FIA evaluates --
            # not scoped to Logging, for the reason `uncovered` states and
            # findings.industry_concept_scan measures.
            "published_start": str(wc_index["year_min"]) if wc_index["year_min"] else "",
            "published_end": str(wc_index["year_max"]) if wc_index["year_max"] else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": (
                "inventory evaluation cycles overlapping D1's reference years, not calendar "
                "months or a Logging-specific series"
            ),
            "uncovered": compose_fia_uncovered(
                industry_scan=industry_scan,
                dc_has_evaluation=dc_has_fia_evaluation,
                wc_row_count=wc_index["row_count"],
            ),
        },
        access=compose_fia_access(
            route=FIA_FULLREPORT,
            doc_params_parsed=bool(doc_params),
            real_probe_parsed=real_probe_parsed,
            measure_proved=measure_proved,
            snum_index=snum_index,
        ),
        extracts=extracts,
        findings={
            "doc_parameters": doc_params,
            "tpo_mentions_on_fia_doc_page": tpo_mentions_on_doc_page,
            "evaluation_vintage_index": wc_index,
            "snum_estimate_attributes": snum_index,
            "measure_proved_by_probe": measure_proved,
            "industry_concept_scan": industry_scan,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
            "probe_naive_missing_required_params": {
                "url": FIA_FULLREPORT,
                "params_sent": FIA_NAIVE_PARAMS,
                "http_status": naive_probe["http_status"],
                "bytes": naive_probe["bytes"],
                "content_type": naive_probe["content_type"],
                "outcome": classify_probe(naive_probe["http_status"], naive_probe["bytes"]),
                "is_evalidator_error_page": naive_is_error_page,
                "note": (
                    "the brief's illustrative probe -- omits every parameter the doc page "
                    "marks required (wc*, snum*, rselected*, cselected*); returns HTTP 200 "
                    "but an EVALIDator error page, not a report -- a '200 but no usable "
                    "data' outcome, not a source outage"
                ),
            },
            "probe": {
                "url": FIA_FULLREPORT,
                "params_sent": FIA_REAL_PARAMS,
                "http_status": real_probe["http_status"],
                "bytes": real_probe["bytes"],
                "content_type": real_probe["content_type"],
                "outcome": classify_probe(real_probe["http_status"], real_probe["bytes"]),
                "has_sampling_error": se_field is not None,
                "parsed_as_report_with_estimates_and_metadata": real_probe_parsed,
            },
            "sampling_error_field": se_field,
            "evaluation_vintage_field": ev_field,
            "district_of_columbia_has_fia_evaluation": dc_has_fia_evaluation,
            "datamart_probes": datamart_probes,
            "other_routes_probed": other_route_probes,
        },
    )


def run_tpo(client: httpx.Client) -> None:
    extracts = []
    probes = []

    for url in TPO_CANDIDATES:
        res = probe_url(client, url)
        # Retained whatever the status (ruling D-B): one of these three candidates 404s, and
        # its 4 KB body is what distinguishes "this API path is not published" from "published
        # but empty" -- a distinction a discarded body cannot support.
        retain_body(extracts, SOURCE_TPO, res, f"candidate_{TPO_CANDIDATES.index(url)}.bin")
        probes.append(probe_record(res, "brief"))

    nrum_downloads_url = TPO_DISCOVERED_ROUTES[1]
    nrum_downloads_body = b""
    for i, url in enumerate(TPO_DISCOVERED_ROUTES):
        res = probe_url(client, url)
        if url == nrum_downloads_url:
            nrum_downloads_body = res["body"]
        retain_body(extracts, SOURCE_TPO, res, f"discovered_{i}.bin")
        probes.append(probe_record(res, "discovered (linked from a brief candidate page)"))

    # Not hardcoded: read from the NRUM data-downloads page this run actually fetched above.
    box_share_url = discover_box_share_url(nrum_downloads_body.decode("utf-8", "replace"))

    chosen: str | None = None
    harvest_origin_available = False
    box_navigation: dict = {"share_url_discovered": box_share_url}
    box_base = {"url": "", "http_status": 0, "bytes": 0, "content_type": "", "body": b""}
    if box_share_url is not None:
        box_base = probe_url(client, box_share_url)
        retain_body(extracts, SOURCE_TPO, box_base, "box_nrum_data_folder.html")
        probes.append(probe_record(
            box_base, "discovered (linked from the NRUM data-downloads page)"))
    if box_base["http_status"] == 200 and box_base["body"]:
        try:
            root_folder = box_shared_folder_items(box_base["body"].decode("utf-8", "replace"))
        except (ValueError, json.JSONDecodeError) as exc:
            root_folder = {"items": [], "parse_error": str(exc)}
            # Recorded, not just caught: `compose_tpo_access` distinguishes "the share page
            # never answered" from "it answered and did not parse", and the second branch is
            # only readable if the reason it did not parse reaches the artifact.
            box_navigation["shared_folder_parse_error"] = str(exc)
        year_folders = sorted(
            (it.get("name") for it in root_folder.get("items", [])
             if it.get("type") == "folder" and str(it.get("name", "")).isdigit()),
            key=int,
        )
        box_navigation["nrum_data_folder_id"] = root_folder.get("currentFolderID")
        box_navigation["year_subfolders_found"] = year_folders
        box_navigation["window_year_subfolders_found"] = [
            y for y in year_folders if int(y) in WINDOW_YEARS
        ]

        target = select_latest_window_year_folder(root_folder.get("items", []), WINDOW_YEARS)
        if target is not None:
            year_folder_url = f"{box_share_url}/folder/{target['id']}"
            year_resp = probe_url(client, year_folder_url)
            retain_body(
                extracts, SOURCE_TPO, year_resp, f"box_{target['name']}_folder.html")
            probes.append(probe_record(
                year_resp, f"discovered (Box subfolder for {target['name']})"))
            box_navigation["probed_year"] = target["name"]
            if year_resp["http_status"] == 200 and year_resp["body"]:
                try:
                    year_folder = box_shared_folder_items(
                        year_resp["body"].decode("utf-8", "replace"))
                except (ValueError, json.JSONDecodeError):
                    year_folder = {"items": []}
                items = year_folder.get("items", [])
                box_navigation["files_listed_this_page"] = len(
                    [it for it in items if it.get("type") == "file"])
                box_navigation["filescount_per_box_metadata"] = target.get("filesCount")
                chosen_file = select_first_file(items)
                if chosen_file is not None:
                    shared_name = box_share_url.rsplit("/s/", 1)[1]
                    file_url = box_legacy_download_url(shared_name, chosen_file["id"])
                    file_resp = probe_url(client, file_url)
                    retain_body(
                        extracts, SOURCE_TPO, file_resp,
                        f"tpo_sample_{target['name']}_{chosen_file['name']}")
                    probes.append(probe_record(
                        file_resp,
                        f"discovered (Box legacy download of {chosen_file['name']})"))
                    if answered_with_body(file_resp) and is_machine_readable(
                            file_resp["content_type"]):
                        try:
                            inspected = inspect_xlsx(file_resp["body"])
                            harvest_origin_available = (
                                distinguishes_harvest_origin_from_mill_receipts(
                                    inspected["sheet_names"]))
                            box_navigation["sample_file"] = chosen_file["name"]
                            box_navigation["sample_file_sheet_names"] = (
                                inspected["sheet_names"])
                            box_navigation["sample_file_first_sheet_name"] = (
                                inspected["first_sheet_name"])
                            box_navigation["sample_file_first_sheet_headers"] = (
                                inspected["first_sheet_headers"])
                            # Empty on every workbook this run has seen. Persisted anyway so an
                            # absent header row shows up as a named gap in the artifact rather
                            # than as a clause the access reason silently omits.
                            box_navigation["sample_file_first_sheet_unresolved"] = (
                                inspected["first_sheet_unresolved"])
                            if chosen is None:
                                chosen = file_url
                        except (zipfile.BadZipFile, KeyError) as exc:
                            box_navigation["sample_file_inspection_error"] = str(exc)

    # Both sentences below are composed by pure functions from box_navigation -- what THIS run's
    # own probes found -- rather than typed from the investigation that shaped this script.
    # That investigation happened to land on 2021/Ohio and observed a page-capped listing (20
    # rendered vs a filesCount of 37), while a run's deterministic selection
    # (`select_latest_window_year_folder`) can land on a different year entirely, so a hardcoded
    # claim written against the investigation's year would be false about the year actually
    # checked. Composing them out of line is also what makes each branch directly testable.
    year_folders_int = sorted(int(y) for y in box_navigation.get("year_subfolders_found", []))
    cadence_claim = compose_cadence_claim(
        box_navigation, window_years=WINDOW_YEARS, window_start_year=int(c.WINDOW_START[:4]))
    pagination_note = compose_pagination_note(box_navigation)

    c.write_summary(
        SOURCE_TPO,
        coverage_span={
            "published_start": str(year_folders_int[0]) if year_folders_int else "",
            "published_end": str(year_folders_int[-1]) if year_folders_int else "",
            "window_start": c.WINDOW_START, "window_end": c.WINDOW_END,
            "covered": cadence_claim,
            "uncovered": (
                "no monthly resolution: SRC-FOR-004 forbids interpolating to months; "
                "per-state completeness within a year (which of the 51 states_dc have a "
                f"file) was not exhaustively enumerated this run -- {pagination_note} -- so "
                "a full state-by-state count would need paginating Box's listing API for "
                "every window year, out of scope for an access verdict"
            ),
        },
        access=compose_tpo_access(
            route=(
                f"{nrum_downloads_url} -> {box_share_url} -> "
                f"{box_share_url}/folder/<year-subfolder-id> -> "
                f"{BOX_LEGACY_DOWNLOAD_BASE}?rm=box_download_shared_file&...&file_id=f_<id>"
            ),
            harvest_origin_available=harvest_origin_available,
            box_navigation=box_navigation,
            probes=probes,
        ),
        extracts=extracts,
        findings={
            "route_probes": probes,
            "harvest_origin_available": harvest_origin_available,
            "chosen_route": chosen,
            "box_navigation": box_navigation,
            "raw_retention_rule": compose_retention_rule([e.http_status for e in extracts]),
        },
    )


def main() -> None:
    client = c.build_client()
    run_fia(client)
    run_tpo(client)
    fia_summary = c.load_summary(SOURCE_FIA)
    tpo_summary = c.load_summary(SOURCE_TPO)
    snum = fia_summary["findings"]["snum_estimate_attributes"]
    measure = fia_summary["findings"]["measure_proved_by_probe"] or {}
    print(
        "FIA:", fia_summary["access"]["status"],
        "| sampling error field:", fia_summary["findings"]["sampling_error_field"],
        "| evaluation vintage field:", fia_summary["findings"]["evaluation_vintage_field"],
    )
    print(
        "FIA measure proved:", measure.get("num_est_desc"),
        "| snum attributes catalogued:", snum["row_count"],
        "| of them harvest-removals:", snum["harvest_removals_attribute_count"],
    )
    print(
        "TPO:", tpo_summary["access"]["status"],
        "| chosen route:", tpo_summary["findings"]["chosen_route"],
    )


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
