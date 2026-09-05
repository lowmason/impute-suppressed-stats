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

This fixture is that archive reduced to four of its members, re-zipped
(SHA-256 `b7379140427b19ce33dfaeb04b17806069d1e07dff5ee462f2d12e0a9e475db2`, 571,366 bytes):

| Member (under `2017.q1-q4.by_industry/`) | Bytes | Member SHA-256 | Role |
|---|---|---|---|
| `2017.q1-q4 113310 NAICS 113310 Logging.csv` | 2,022,002 | `47bfbef888054477d4fc4fcf4c2a04e70b72610ec4125eeb279c613a14c48caa` | the target |
| `2017.q1-q4 11331 NAICS 11331 Logging.csv` | 2,007,522 | `f800600442a9ddf339e75c737bdb89151c9799d6049762da45c0b9d7b6753576` | parent code, identical title |
| `2017.q1-q4 111331 NAICS 111331 Apple orchards.csv` | 584,446 | `309a05b1fc9fcd7e33fc4f50142b89db44980bf338ea132706d7d6d31ad29d96` | shares the digits `11331` |
| `2017.q1-q4 113110 NAICS 113110 Timber tract operations.csv` | 687,815 | `a71261ca2f30832a9a5c8367eff147f64a484eda731bdacf710159e10d36e172` | sibling forestry code |

Every member's bytes are byte-identical to the audited archive's, and member paths are preserved.
What is **not** preserved is the archive's own bytes, its 2,232-member size, or its member
ordering — anything asserting a property of the container rather than of a member must use the
audited archive.

### Why four members and not one

`read_bulk_zip` selects its member by an unanchored industry-code substring over `namelist()`.
Against a single-member fixture that filter narrows one name to one name, so deleting it
outright leaves the tests green — verified by mutation: with `members = archive.namelist()`
substituted in, a one-member fixture kept all eleven tests passing.

The three extra members are the near-misses that make the filter observable, and they are drawn
from the real archive rather than constructed, because the hazard is a property of BLS's actual
member naming:

- Asking for `113310` must not return `11331`, which publishes under the **same** title,
  `Logging`. Six digits is NAICS's maximum, so no longer code can contain `113310` — the target
  really is unique here — but that is a fact about this data, not a guarantee from the code.
- Asking for `11331` matches **both** `11331 Logging` and `111331 Apple orchards`, and so must
  raise rather than pick one (§18.3). Selecting these members for the fixture tripped exactly
  that: a first attempt filtered on the string `"11331 "` and matched `"111331 "` as well.

### Regenerating

Run from the repo root with the audited archive present under `data/raw/`. Members are selected
by exact name, not by substring, and each source entry's own zip metadata is carried across
rather than restamped, so the output is deterministic: this reproduces the fixture SHA-256 above.

```bash
uv run python - <<'PY'
import hashlib, zipfile
from pathlib import Path

SRC = Path("data/raw/audit/qcew_routes/bulk/2017_qtrly_by_industry.zip")
DST = Path("tests/fixtures/qcew/bulk_2017.zip")
P = "2017.q1-q4.by_industry/2017.q1-q4 "
KEEP = (
    f"{P}113310 NAICS 113310 Logging.csv",
    f"{P}11331 NAICS 11331 Logging.csv",
    f"{P}111331 NAICS 111331 Apple orchards.csv",
    f"{P}113110 NAICS 113110 Timber tract operations.csv",
)

with zipfile.ZipFile(SRC) as src:
    by_name = {i.filename: i for i in src.infolist()}
    chosen = [by_name[n] for n in KEEP]
    payloads = {n: src.read(n) for n in KEEP}

with zipfile.ZipFile(DST, "w") as dst:
    for info in chosen:
        out = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
        out.compress_type = info.compress_type
        out.external_attr = info.external_attr
        out.create_system = info.create_system
        dst.writestr(out, payloads[info.filename])

print(hashlib.sha256(DST.read_bytes()).hexdigest())
PY
```
