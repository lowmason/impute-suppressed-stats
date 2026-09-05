"""The fetcher carries the contact address and returns non-200 bodies as evidence."""

from __future__ import annotations

import httpx
import pytest

from logging_employment.ingest.base import HttpFetcher


def test_contact_email_is_required() -> None:
    with pytest.raises(ValueError, match="contact_email"):
        HttpFetcher(contact_email="")


def test_user_agent_carries_the_contact_address(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, content=b"ok")

    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers=fetcher._client.headers,
    )
    fetcher.get("https://example.invalid/x")
    assert "who@example.invalid" in seen["ua"]


def test_a_404_body_is_returned_not_raised() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"<html>gone</html>")

    fetcher = HttpFetcher(contact_email="who@example.invalid")
    fetcher._client = httpx.Client(transport=httpx.MockTransport(handler))
    result = fetcher.get("https://example.invalid/missing")
    assert result.http_status == 404
    assert result.content == b"<html>gone</html>"
