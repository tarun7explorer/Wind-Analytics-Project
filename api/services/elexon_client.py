import os
import calendar
from datetime import datetime
from typing import Any

import httpx


class ElexonUnavailableError(RuntimeError):
    """Elexon could not be reached or did not return a usable response."""


class ElexonConnectionError(ElexonUnavailableError):
    """The request failed before Elexon returned an HTTP response."""


class ElexonHTTPError(ElexonUnavailableError):
    """Elexon returned an HTTP error response."""

    def __init__(self, dataset: str, status_code: int, detail: str):
        self.status_code = status_code
        super().__init__(f"Elexon {dataset} returned HTTP {status_code}: {detail}")


class ElexonMalformedResponseError(ElexonUnavailableError):
    """Elexon returned a successful HTTP response that was not valid JSON."""


class ElexonClient:
    """Async client for Elexon's public BMRS Insights JSON stream API.

    The BMRS OpenAPI contract and the raw FUELHH/WINDFOR response shapes were
    checked against live endpoints on 2026-10-25.
    """

    LIVE_CONTRACT_VERIFIED = True

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 20.0, transport=None):
        self.base_url = (base_url or os.getenv(
            "ELEXON_API_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"
        )).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.trust_env = False
        # The managed Windows environment can inject an unreachable loopback
        # proxy. Use direct TLS by default; deployments that need a proxy can
        # provide ELEXON_HTTP_PROXY explicitly.
        self.proxy_url = os.getenv("ELEXON_HTTP_PROXY") or None

    async def _get_json(self, dataset: str, params: dict[str, str]) -> Any:
        url = f"{self.base_url}/datasets/{dataset}/stream"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
                proxy=self.proxy_url,
                trust_env=self.trust_env,
            ) as client:
                response = await client.get(url, params=params, headers={"Accept": "application/json"})
        except httpx.RequestError as exc:
            raise ElexonConnectionError(
                f"Elexon {dataset} connection failed before an HTTP response: {exc}"
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text.strip().replace("\n", " ")[:300] or "empty response body"
            if status == 400:
                detail = f"request was rejected (invalid query or parameters): {body}"
            elif status in (401, 403):
                detail = f"authentication or authorization was rejected: {body}"
            else:
                detail = body
            raise ElexonHTTPError(dataset, status, detail) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ElexonMalformedResponseError(
                f"Elexon {dataset} returned HTTP {response.status_code} with malformed JSON"
            ) from exc

    async def fetch_actuals(self, year: int, month: int) -> Any:
        # Elexon's OpenAPI schema supports these settlement-date filters and
        # the WIND fuelType. The end date is inclusive.
        date_to = datetime(year, month, calendar.monthrange(year, month)[1]).strftime("%Y-%m-%d")
        return await self._get_json("FUELHH", {
            "settlementDateFrom": f"{year:04d}-{month:02d}-01",
            "settlementDateTo": date_to,
            "fuelType": "WIND",
        })

    async def fetch_forecasts(self, publish_from: datetime, publish_to: datetime) -> Any:
        # Query the raw publication history; do not use the separate latest-only
        # endpoint because historical publication versions are required.
        return await self._get_json("WINDFOR", {
            "publishDateTimeFrom": publish_from.isoformat().replace("+00:00", "Z"),
            "publishDateTimeTo": publish_to.isoformat().replace("+00:00", "Z"),
        })
