import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import os

import httpx

from api.services.elexon_client import (
    ElexonClient,
    ElexonConnectionError,
    ElexonHTTPError,
    ElexonMalformedResponseError,
    ElexonUnavailableError,
)


# These tests use an in-memory MockTransport and do not contact Elexon.


class ElexonClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_contract_verification_is_explicit(self):
        self.assertTrue(ElexonClient.LIVE_CONTRACT_VERIFIED)

    async def test_actuals_request_uses_isolated_date_and_wind_filters(self):
        seen = {}

        async def handler(request):
            seen["url"] = request.url
            seen["accept"] = request.headers.get("accept")
            seen["authorization"] = request.headers.get("authorization")
            return httpx.Response(200, json=[])

        client = ElexonClient(transport=httpx.MockTransport(handler))
        self.assertEqual(await client.fetch_actuals(2026, 1), [])
        self.assertTrue(str(seen["url"]).endswith("/datasets/FUELHH/stream?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-31&fuelType=WIND"))
        self.assertEqual(seen["accept"], "application/json")
        self.assertIsNone(seen["authorization"])

    async def test_forecast_request_uses_publication_window(self):
        seen = {}

        async def handler(request):
            seen["url"] = request.url
            return httpx.Response(200, json=[])

        client = ElexonClient(transport=httpx.MockTransport(handler))
        start = datetime(2025, 12, 31, tzinfo=timezone.utc)
        end = datetime(2026, 2, 1, tzinfo=timezone.utc)
        await client.fetch_forecasts(start, end)
        self.assertEqual(request_param(seen["url"], "publishDateTimeFrom"), "2025-12-31T00:00:00Z")
        self.assertEqual(request_param(seen["url"], "publishDateTimeTo"), "2026-02-01T00:00:00Z")

    async def test_non_success_is_an_explicit_source_error(self):
        async def handler(request):
            return httpx.Response(503)

        client = ElexonClient(transport=httpx.MockTransport(handler))
        with self.assertRaises(ElexonUnavailableError):
            await client.fetch_actuals(2026, 1)

    async def test_invalid_query_response_is_distinguished_from_network_failure(self):
        async def handler(request):
            return httpx.Response(400, json={"detail": "invalid date range"})

        client = ElexonClient(transport=httpx.MockTransport(handler))
        with self.assertRaises(ElexonHTTPError) as context:
            await client.fetch_actuals(2026, 1)
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("invalid query or parameters", str(context.exception))
        self.assertIn("invalid date range", str(context.exception))

    async def test_connection_failure_is_reported_without_an_http_status(self):
        async def handler(request):
            raise httpx.ConnectError("connection refused", request=request)

        client = ElexonClient(transport=httpx.MockTransport(handler))
        with self.assertRaises(ElexonConnectionError) as context:
            await client.fetch_actuals(2026, 1)
        self.assertIn("before an HTTP response", str(context.exception))
        self.assertNotIn("HTTP 0", str(context.exception))

    async def test_success_status_with_malformed_json_is_distinguished(self):
        async def handler(request):
            return httpx.Response(200, text="not-json", headers={"Content-Type": "application/json"})

        client = ElexonClient(transport=httpx.MockTransport(handler))
        with self.assertRaises(ElexonMalformedResponseError):
            await client.fetch_actuals(2026, 1)

    async def test_ignores_unreachable_process_proxy_by_default(self):
        async def handler(request):
            return httpx.Response(200, json=[])

        original_client = httpx.AsyncClient
        options = {}

        def capture_options(*args, **kwargs):
            options.update(kwargs)
            return original_client(*args, **kwargs)

        client = ElexonClient(transport=httpx.MockTransport(handler))
        with patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9"}):
            with patch("api.services.elexon_client.httpx.AsyncClient", side_effect=capture_options):
                self.assertEqual(await client.fetch_actuals(2026, 1), [])
        self.assertFalse(options["trust_env"])
        self.assertIsNone(options["proxy"])


def request_param(url, key):
    return dict(url.params).get(key)


if __name__ == "__main__":
    unittest.main()
