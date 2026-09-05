# QCEW fixtures

Frozen bytes behind `tests/unit/test_qcew_routes.py`. `data/raw/` is gitignored, so Stage 0's
extracts cannot serve as test inputs where they sit.

## `slice_2017q1.csv` — audited bytes, copied verbatim

A byte-for-byte copy of `data/raw/audit/qcew_routes/slices/2017q1.csv`. Its SHA-256,
`28a6118bb33aab007684ab7091fda207696a876f612f29b3d26b40c93f6fcc6e`, matches that path's row in
`specs/findings/source-audit-extracts.csv`.

```bash
cp data/raw/audit/qcew_routes/slices/2017q1.csv tests/fixtures/qcew/slice_2017q1.csv
```

## `bulk_2017.zip` — **derived, not audited**

**This is not the archive Stage 0 fetched.** The audited archive,
`data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip`
(SHA-256 `15795392040cb4ad772c02e86f9a223dac742c61994570f07fda0d022375227c`, 460,476,363 bytes),
carries 2,232 industry members and is too large to track: it exceeds GitHub's 100 MB per-file
push limit, and git history is not something a later commit can un-bloat.

This fixture is that archive reduced to the single member the tests read, re-zipped:

| | |
|---|---|
| Member name | `2017.q1-q4.by_industry/2017.q1-q4 113310 NAICS 113310 Logging.csv` |
| Member SHA-256 | `47bfbef888054477d4fc4fcf4c2a04e70b72610ec4125eeb279c613a14c48caa` |
| Member bytes | 2,022,002 |
| Fixture SHA-256 | `b32b6380c013da05389cb60781023fa2b2f822bcc760859a148a271f69c22569` |
| Fixture bytes | 232,192 |

The **member bytes are byte-identical** to the audited archive's, and the member's full path is
preserved, so `read_bulk_zip`'s selection-by-industry-substring over `namelist()` is exercised
exactly as it runs in production. What is *not* preserved is the archive's own bytes — anything
asserting a property of the container rather than of the member must use the audited archive.

Regenerate from the repo root, with the audited archive present under `data/raw/`. The source
entry's own zip metadata is carried across rather than restamped, so the output is deterministic:
re-running this yields the fixture SHA-256 above.

```bash
uv run python - <<'PY'
import hashlib, zipfile
from pathlib import Path

SRC = Path("data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip")
DST = Path("tests/fixtures/qcew/bulk_2017.zip")

with zipfile.ZipFile(SRC) as src:
    infos = [i for i in src.infolist() if "113310" in i.filename and i.filename.endswith(".csv")]
    assert len(infos) == 1, infos
    info = infos[0]
    payload = src.read(info.filename)

out = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
out.compress_type = info.compress_type
out.external_attr = info.external_attr
out.create_system = info.create_system
with zipfile.ZipFile(DST, "w") as dst:
    dst.writestr(out, payload)

print(hashlib.sha256(DST.read_bytes()).hexdigest())
PY
```
