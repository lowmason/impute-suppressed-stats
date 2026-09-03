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
