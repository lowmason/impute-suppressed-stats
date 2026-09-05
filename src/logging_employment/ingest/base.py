"""One HTTP client for every source, carrying the contact address BLS requires."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import httpx

from .. import __version__


@dataclass(frozen=True)
class FetchedBytes:
    """A response body with the request that produced it. Bytes are never decoded here."""

    url: str
    params: dict[str, str]
    content: bytes
    http_status: int
    retrieved_at_utc: str


@dataclass
class HttpFetcher:
    """A thin httpx wrapper with the D3 User-Agent and no retry-on-4xx.

    `data.bls.gov` admits scripted clients only when the User-Agent carries a contact address, so
    `contact_email` is required rather than optional.

    A non-200 response is returned rather than raised: Stage 0 measured Census and USDA endpoints
    answering 200 with an error body and 204/404 with a meaningful one, so the status is evidence
    the caller classifies, not a failure this layer decides.
    """

    contact_email: str
    timeout: float = 30.0
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Open one connection pool with the required User-Agent."""
        if not self.contact_email:
            raise ValueError("contact_email is required (D3: BLS_CONTACT_EMAIL)")
        self._client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": f"logging-employment/{__version__} ({self.contact_email})"},
        )

    def get(self, url: str, params: dict[str, str] | None = None) -> FetchedBytes:
        """GET a URL and return its bytes verbatim, whatever the status."""
        response = self._client.get(url, params=params or {})
        return FetchedBytes(
            url=url,
            params=dict(params or {}),
            content=response.content,
            http_status=response.status_code,
            retrieved_at_utc=dt.datetime.now(dt.UTC).isoformat(),
        )

    def close(self) -> None:
        """Close the underlying connection pool."""
        self._client.close()
