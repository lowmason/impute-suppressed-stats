from pathlib import Path

import httpx
import pytest

import _common


def test_audit_root_and_findings_dir_resolve_from_module_location():
    repo_root = Path(_common.__file__).resolve().parents[2]
    assert _common.AUDIT_ROOT == repo_root / "data" / "raw" / "audit"
    assert _common.FINDINGS_DIR == repo_root / "specs" / "findings"
    assert _common.AUDIT_ROOT.is_absolute()
    assert _common.FINDINGS_DIR.is_absolute()


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


def test_record_extract_refuses_a_key_bearing_url(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setenv("CENSUS_API_KEY", "sekret-value-0123")
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _common.record_extract(
            "cbp", "https://api.census.gov/data/2022/cbp?key=sekret-value-0123", "y.json", b"[]"
        )
    assert not (tmp_path / "cbp").exists()


def test_record_extract_refuses_key_bearing_content(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setenv("CENSUS_API_KEY", "sekret-value-0123")
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _common.record_extract(
            "cbp", "https://example.test/y.json", "y.json", b'{"key": "sekret-value-0123"}'
        )
    assert not (tmp_path / "cbp").exists()


def test_download_extract_streams_bytes_verbatim_with_sidecar(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    body = b"Q" * 1_500_000 + b"\xff\x00\xfe"  # >1 MiB forces multiple 1 MiB chunks
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body))
    )
    rec = _common.download_extract(client, "qcew", "https://example.test/big.zip", "big.zip")
    written = (tmp_path / "qcew" / "big.zip").read_bytes()
    assert written == body
    assert rec.bytes == len(body)
    assert _common.sha256_file(tmp_path / "qcew" / "big.zip") == rec.sha256
    sidecar = (tmp_path / "qcew" / "big.zip.sha256").read_text()
    assert sidecar == f"{rec.sha256}  big.zip\n"
    assert not (tmp_path / "qcew" / "big.zip.part").exists()


def test_download_extract_leaves_no_file_on_interrupted_stream(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setattr(_common.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def flaky_body():
        yield b"chunk-one-"
        yield b"chunk-two-"
        raise httpx.ReadError("connection reset mid-stream")

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=flaky_body())

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.TransportError):
        _common.download_extract(client, "qcew", "https://example.test/big.zip", "big.zip")
    assert not (tmp_path / "qcew" / "big.zip").exists()
    assert not (tmp_path / "qcew" / "big.zip.part").exists()
    assert not (tmp_path / "qcew" / "big.zip.sha256").exists()
    # G4: a transport error is retryable, so this must be retries=3 => 4 total attempts, not a
    # regression that gives up (or stops retrying) after the first failure.
    assert calls["n"] == 4


def test_download_extract_cleans_up_part_file_when_sidecar_write_fails(tmp_path, monkeypatch):
    """G3: `_write_sidecar` and `os.replace` used to run after the try/except that unlinks the
    `.part` file, so a failing sidecar write (permissions, full disk) orphaned it."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    body = b"z" * 5000
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body))
    )

    def boom(dest: Path, digest: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(_common, "_write_sidecar", boom)
    with pytest.raises(OSError):
        _common.download_extract(client, "qcew", "https://example.test/big.zip", "big.zip")
    assert not (tmp_path / "qcew" / "big.zip").exists()
    assert not (tmp_path / "qcew" / "big.zip.part").exists()


def test_download_extract_retries_5xx_and_transport_errors_like_request(tmp_path, monkeypatch):
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setattr(_common.time, "sleep", lambda _: None)
    body = b"z" * 5000
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(500) if calls["n"] < 3 else httpx.Response(200, content=body)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    rec = _common.download_extract(client, "qcew", "https://example.test/big.zip", "big.zip")
    assert calls["n"] == 3
    assert (tmp_path / "qcew" / "big.zip").read_bytes() == body
    assert rec.sha256 == _common.sha256_bytes(body)


def test_download_extract_fails_fast_on_4xx_without_retrying(tmp_path, monkeypatch):
    """G4: `download_extract` must fast-fail a 4xx exactly like `request` does, not retry it —
    coverage gap the retry-parity tests never closed."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setattr(_common.time, "sleep", lambda _: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        _common.download_extract(client, "qcew", "https://example.test/missing.zip", "missing.zip")
    assert calls["n"] == 1
    assert not (tmp_path / "qcew" / "missing.zip").exists()
    assert not (tmp_path / "qcew" / "missing.zip.part").exists()


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
        lambda p: p["coverage_span"].__setitem__("window_start", "2018-01"),
        lambda p: p["coverage_span"].__setitem__("window_end", "2024-11"),
        lambda p: p.__setitem__("coverage_span", None),
        lambda p: p.__setitem__("access", "not-a-dict"),
        lambda p: p.__setitem__(
            "extracts", ["source url path sha256 bytes retrieved_utc http_status"]
        ),
        lambda p: p.__setitem__("extracts", None),
        lambda p: p.__setitem__("extracts", ""),
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


@pytest.mark.parametrize(
    "bad_payload",
    [
        None,
        42,
        ["source", "generated_utc", "coverage_span", "access", "extracts", "findings"],
        "source generated_utc coverage_span access extracts findings",
    ],
)
def test_validate_summary_rejects_non_dict_payload(bad_payload):
    """The list/string cases are adversarial: each one carries all six required top-level
    keys (as elements or as substrings), so the presence loop finds every key and falls
    through to `payload["coverage_span"]` — a non-dict subscript, which must still surface
    as `ValueError`, not `TypeError`."""
    with pytest.raises(ValueError):
        _common.validate_summary(bad_payload)


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


def test_write_summary_refuses_to_leak_a_non_ascii_key(tmp_path, monkeypatch):
    """G7: `json.dumps(..., ensure_ascii=True)` (the default) would rewrite a non-ASCII secret
    value's characters as `\\uXXXX` escapes, so the literal value no longer appears as a
    substring of the serialized text and the guard misses it."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    monkeypatch.setenv("CENSUS_API_KEY", "sekret-café-0123")
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _common.write_summary(
            "cbp",
            coverage_span={"published_start": "", "published_end": "", "window_start": "2017-01",
                           "window_end": "2024-12", "covered": "", "uncovered": ""},
            access={"route": "r", "status": "verified", "reason": None},
            extracts=[], findings={"note": "leaked sekret-café-0123 here"},
        )


def test_write_summary_and_load_summary_round_trip_non_ascii_as_utf8(tmp_path, monkeypatch):
    """H1: G7's `ensure_ascii=False` means `text` can now carry literal non-ASCII characters,
    so the encoding `write_summary`'s `dest.write_text(text)` and `load_summary`'s
    `.read_text()` pick up now matters (previously both were safe by accident: the default
    `ensure_ascii=True` guaranteed pure-ASCII output, which every locale encoding agrees on).
    JSON is UTF-8 by definition (RFC 8259). This pins the round-trip contract directly rather
    than by forcing a non-UTF-8 locale, which does not reproduce on every platform (macOS PEP
    538 C-locale coercion makes even `LC_ALL=C` yield utf-8 here) and would pass vacuously."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    note = "café 日本語"  # Latin-1-representable + characters with no cp1252/latin-1 form at all
    dest = _common.write_summary(
        "cbp",
        coverage_span={"published_start": "", "published_end": "", "window_start": "2017-01",
                       "window_end": "2024-12", "covered": "", "uncovered": ""},
        access={"route": "r", "status": "verified", "reason": None},
        extracts=[], findings={"note": note},
    )
    raw = dest.read_bytes()
    decoded = raw.decode("utf-8")  # raises UnicodeDecodeError if the bytes aren't valid UTF-8
    assert note in decoded
    assert note.encode("utf-8") in raw  # literal UTF-8 bytes on disk, not a \uXXXX escape
    assert rb"\u" not in raw  # no field in this payload legitimately escapes
    loaded = _common.load_summary("cbp")
    assert loaded["findings"]["note"] == note


def test_write_summary_and_load_summary_pass_explicit_utf8_encoding(tmp_path, monkeypatch):
    """H1: `dest.write_text(text)` (write_summary) and `.read_text()` (load_summary) must pass
    `encoding="utf-8"` explicitly rather than falling back to `locale.getpreferredencoding`.
    This machine's locale always resolves to UTF-8 (macOS PEP 538 coercion), so no behavioral
    round-trip test can fail here even without the fix -- this spies on the keyword arguments
    `Path.write_text`/`Path.read_text` actually receive instead, the same technique
    `test_assert_no_secrets_delegates_to_the_bytes_implementation` (G2) uses for the analogous
    problem: two calls that behave identically on this machine's input while one silently
    drifts from the documented contract."""
    monkeypatch.setattr(_common, "AUDIT_ROOT", tmp_path)
    orig_write_text = Path.write_text
    orig_read_text = Path.read_text
    write_calls: list[dict] = []
    read_calls: list[dict] = []

    def spy_write_text(self, data, *args, **kwargs):
        write_calls.append(kwargs)
        return orig_write_text(self, data, *args, **kwargs)

    def spy_read_text(self, *args, **kwargs):
        read_calls.append(kwargs)
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", spy_write_text)
    monkeypatch.setattr(Path, "read_text", spy_read_text)

    _common.write_summary(
        "cbp",
        coverage_span={"published_start": "", "published_end": "", "window_start": "2017-01",
                       "window_end": "2024-12", "covered": "", "uncovered": ""},
        access={"route": "r", "status": "verified", "reason": None},
        extracts=[], findings={},
    )
    _common.load_summary("cbp")

    assert len(write_calls) == 1
    assert write_calls[0].get("encoding") == "utf-8"
    assert len(read_calls) == 1
    assert read_calls[0].get("encoding") == "utf-8"


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


def test_request_retries_429_like_5xx():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429 if calls["n"] < 3 else 200, text="ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    resp = _common.request(client, "https://example.test/a", sleep=lambda _: None)
    assert resp.status_code == 200 and calls["n"] == 3


def test_probe_returns_status_without_raising():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="no")))
    assert _common.probe(client, "https://example.test/c") == (404, 2)


def test_contact_email_required(monkeypatch):
    monkeypatch.delenv("BLS_CONTACT_EMAIL", raising=False)
    with pytest.raises(RuntimeError, match="BLS_CONTACT_EMAIL"):
        _common.contact_email()


def test_assert_no_secrets_delegates_to_the_bytes_implementation(monkeypatch):
    """G2: `assert_no_secrets` must not run its own copy of the comparison loop — it must
    call `assert_no_secrets_bytes` so there is exactly one implementation. Proven by spying on
    the module-level name rather than by behavior alone, since a text-only and a bytes-only
    loop can behave identically on ASCII input while still being two maintained copies."""
    calls = []
    monkeypatch.setattr(_common, "assert_no_secrets_bytes", lambda data: calls.append(data))
    _common.assert_no_secrets("hello world")
    assert calls == [b"hello world"]


def test_assert_no_secrets_still_raises_on_a_key_bearing_url(monkeypatch):
    """Unpatched sibling of the spy test above: pins that the delegation preserves the
    documented exception type and message, not just that a call happened."""
    monkeypatch.setenv("CENSUS_API_KEY", "sekret-value-0123")
    with pytest.raises(RuntimeError, match="CENSUS_API_KEY"):
        _common.assert_no_secrets("https://example.test/x?key=sekret-value-0123")
