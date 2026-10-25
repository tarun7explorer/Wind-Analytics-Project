import unittest

from fastapi.testclient import TestClient

from api.index import app
from api.routes.analytics import get_report_service
from api.services.elexon_client import ElexonUnavailableError
from api.utils.validation import SourceDataError


class FakeService:
    async def get_report(self, year, month):
        return {
            "year": year,
            "month": month,
            "period_start": "2026-01-01T00:00:00Z",
            "period_end_exclusive": "2026-02-01T00:00:00Z",
            "timezone": "Europe/London",
            "unit": "MW",
            "source_retrieved_at": "2026-10-25T12:00:00Z",
            "source_contract_status": "unverified_live_contract",
            "decision_cutoff_rule": "12:00 Europe/London on the day before each delivery date",
            "expected_intervals": 1,
            "actual_intervals": 1,
            "forecast_intervals": 1,
            "matched_intervals": 1,
            "unmatched_intervals": 0,
            "missing_actual_intervals": 0,
            "missing_forecast_intervals": 0,
            "metrics": {"matched_intervals": 1, "mae_mw": 2.0, "rmse_mw": 2.0, "wape_percent": 2.0},
            "hourly_analysis": {
                "comparison_frequency": "hourly", "actual_method": "mean of both half-hours",
                "expected_periods": 1, "eligible_actual_periods": 1, "actual_incomplete_periods": 0,
                "forecast_periods": 1, "matched_periods": 1, "unmatched_periods": 0,
                "actual_completeness_percent": 100.0, "forecast_coverage_percent": 100.0,
                "exact_half_hour_matched_periods": 1, "exact_half_hour_expected_periods": 1,
                "exact_half_hour_coverage_percent": 100.0,
                "metrics": {"matched_intervals": 1, "mae_mw": 2.0, "rmse_mw": 2.0, "wape_percent": 2.0},
            },
            "records": [{
                "delivery_time": "2026-01-01T00:00:00Z", "forecast_mw": 98.0, "actual_mw": 100.0,
                "signed_error_mw": -2.0, "absolute_error_mw": 2.0, "percentage_error": -2.0,
                "forecast_published_at": "2025-12-31T11:00:00Z", "decision_cutoff": "2025-12-31T12:00:00Z",
                "matched": True,
            }],
            "hourly_records": [{
                "delivery_time": "2026-01-01T00:00:00Z", "forecast_mw": 98.0, "actual_mw": 100.0,
                "actual_half_hour_count": 2, "signed_error_mw": -2.0, "absolute_error_mw": 2.0, "percentage_error": -2.0,
                "forecast_published_at": "2025-12-31T11:00:00Z", "decision_cutoff": "2025-12-31T12:00:00Z",
                "matched": True,
            }],
        }


class UnavailableService:
    async def get_report(self, year, month):
        raise ElexonUnavailableError("Elexon endpoint unreachable")


class MalformedSourceService:
    async def get_report(self, year, month):
        raise SourceDataError("WINDFOR record has invalid 'publishTime'")


class ApiTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_report_service] = FakeService
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_monthly_analytics_defaults_to_january_2026(self):
        response = self.client.get("/api/analytics/monthly")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["year"], 2026)
        self.assertEqual(response.json()["month"], 1)
        self.assertEqual(response.json()["source_contract_status"], "unverified_live_contract")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertNotIn("records", response.json())

    def test_full_report_returns_hourly_comparison_and_preserves_source_rows(self):
        response = self.client.get("/api/analytics/report?year=2026&month=1")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["hourly_analysis"]["comparison_frequency"], "hourly")
        self.assertEqual(payload["hourly_records"][0]["actual_half_hour_count"], 2)
        self.assertEqual(payload["records"][0]["delivery_time"], "2026-01-01T00:00:00Z")

    def test_records_endpoint_paginates_and_validates_month(self):
        response = self.client.get("/api/analytics/records?year=2026&month=1&offset=0&limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertTrue(response.json()["records"][0]["matched"])
        self.assertEqual(self.client.get("/api/analytics/monthly?month=13").status_code, 422)

    def test_upstream_failure_is_reported_without_analytics(self):
        app.dependency_overrides[get_report_service] = UnavailableService
        response = self.client.get("/api/analytics/monthly")
        self.assertEqual(response.status_code, 502)
        self.assertIn("Elexon endpoint unreachable", response.json()["detail"])

    def test_malformed_source_data_is_reported_as_bad_gateway(self):
        app.dependency_overrides[get_report_service] = MalformedSourceService
        response = self.client.get("/api/analytics/monthly")
        self.assertEqual(response.status_code, 502)
        self.assertIn("Invalid Elexon response", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
