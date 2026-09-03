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

    def flaky_body():
        yield b"chunk-one-"
        yield b"chunk-two-"
        raise httpx.ReadError("connection reset mid-stream")

    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=flaky_body()))
    )
    with pytest.raises(httpx.TransportError):
        _common.download_extract(client, "qcew", "https://example.test/big.zip", "big.zip")
    assert not (tmp_path / "qcew" / "big.zip").exists()
    assert not (tmp_path / "qcew" / "big.zip.part").exists()
    assert not (tmp_path / "qcew" / "big.zip.sha256").exists()


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
