import unittest

from api.analytics.forecast_matching import aggregate_half_hour_actuals, match_forecasts, match_hourly_forecasts
from api.utils.validation import SourceDataError


def actual(start="2026-01-01T00:00:00Z", generation=100):
    return {"startTime": start, "fuelType": "WIND", "generation": generation}


def forecast(published, generation, start="2026-01-01T00:00:00Z"):
    return {"startTime": start, "publishTime": published, "generation": generation}


class ForecastMatchingTests(unittest.TestCase):
    def test_hourly_actual_is_mean_of_the_two_delivery_intervals(self):
        from datetime import datetime, timezone
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = aggregate_half_hour_actuals(
            [actual(generation=100), actual("2026-01-01T00:30:00Z", 120)], [start]
        )
        self.assertEqual(rows, [{"delivery_time": start, "actual_mw": 110, "actual_half_hour_count": 2}])

    def test_hour_is_missing_if_either_half_hour_actual_is_missing(self):
        from datetime import datetime, timezone
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = aggregate_half_hour_actuals([actual(generation=100)], [start])
        self.assertIsNone(rows[0]["actual_mw"])
        self.assertEqual(rows[0]["actual_half_hour_count"], 1)

    def test_hourly_aggregation_collapses_identical_duplicates_and_rejects_conflicts(self):
        from datetime import datetime, timezone
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = actual(generation=100)
        second = actual("2026-01-01T00:30:00Z", 120)
        rows = aggregate_half_hour_actuals([first, first, second], [start])
        self.assertEqual(rows[0]["actual_mw"], 110)
        with self.assertRaisesRegex(SourceDataError, "conflicting"):
            aggregate_half_hour_actuals([first, actual(generation=101), second], [start])

    def test_hourly_aggregation_uses_distinct_utc_hours_across_fall_dst(self):
        from datetime import datetime, timezone
        hours = [datetime(2026, 10, 25, h, tzinfo=timezone.utc) for h in (0, 1)]
        source = []
        for h, hour in enumerate(hours):
            source.extend([
                actual(hour.isoformat().replace('+00:00', 'Z'), 100 + h * 10),
                actual((hour.replace(minute=30)).isoformat().replace('+00:00', 'Z'), 120 + h * 10),
            ])
        rows = aggregate_half_hour_actuals(source, hours)
        self.assertEqual([row["actual_mw"] for row in rows], [110, 120])
        self.assertEqual(len({row["delivery_time"] for row in rows}), 2)

    def test_hourly_expected_utc_hours_reflect_spring_and_fall_dst(self):
        from datetime import timedelta
        from api.utils.date_ranges import month_bounds
        counts = []
        for month in (3, 10):
            start, end = month_bounds(2026, month)
            counts.append(int((end - start) / timedelta(hours=1)))
        self.assertEqual(counts, [743, 745])

    def test_hourly_matching_uses_latest_publication_including_cutoff_and_rejects_later(self):
        from datetime import datetime, timezone
        delivery = datetime(2026, 1, 1, tzinfo=timezone.utc)
        actual_hour = {"delivery_time": delivery, "actual_mw": 100, "actual_half_hour_count": 2}
        rows = match_hourly_forecasts([actual_hour], [
            forecast("2025-12-31T11:00:00Z", 90),
            forecast("2025-12-31T12:00:00Z", 95),
            forecast("2025-12-31T12:00:01Z", 99),
        ])
        self.assertEqual(rows[0]["forecast_mw"], 95)
        self.assertEqual(rows[0]["forecast_published_at"].isoformat(), "2025-12-31T12:00:00+00:00")
        self.assertEqual(rows[0]["signed_error_mw"], -5)

    def test_hourly_matching_keeps_missing_actual_and_zero_percentage_safe(self):
        from datetime import datetime, timezone
        delivery = datetime(2026, 1, 1, tzinfo=timezone.utc)
        rows = match_hourly_forecasts([
            {"delivery_time": delivery, "actual_mw": None, "actual_half_hour_count": 1},
            {"delivery_time": delivery.replace(hour=1), "actual_mw": 0, "actual_half_hour_count": 2},
        ], [
            forecast("2025-12-31T11:30:00Z", 5),
            forecast("2025-12-31T12:00:00Z", 4, "2026-01-01T01:00:00Z"),
        ])
        self.assertFalse(rows[0]["matched"])
        self.assertIsNone(rows[0]["actual_mw"])
        self.assertTrue(rows[1]["matched"])
        self.assertIsNone(rows[1]["percentage_error"])
    def test_chooses_latest_forecast_before_previous_day_noon_uk(self):
        rows = match_forecasts(
            [actual()],
            [forecast("2025-12-31T10:00:00Z", 90), forecast("2025-12-31T11:59:00Z", 95), forecast("2025-12-31T12:01:00Z", 99)],
        )
        self.assertEqual(rows[0]["forecast_mw"], 95)
        self.assertEqual(rows[0]["signed_error_mw"], -5)
        self.assertTrue(rows[0]["matched"])

    def test_cutoff_uses_british_summer_time_for_delivery_day(self):
        delivery = "2026-07-01T23:00:00Z"  # 00:00 on 2 July in London.
        row = match_forecasts(
            [actual(start=delivery)],
            [forecast("2026-07-01T11:00:00Z", 95, start=delivery)],
        )[0]
        self.assertEqual(row["decision_cutoff"].isoformat(), "2026-07-01T11:00:00+00:00")
        self.assertEqual(row["forecast_mw"], 95)

    def test_no_eligible_forecast_keeps_interval_unmatched(self):
        rows = match_forecasts([actual()], [forecast("2025-12-31T12:01:00Z", 99)])
        self.assertIsNone(rows[0]["forecast_mw"])
        self.assertIsNone(rows[0]["absolute_error_mw"])
        self.assertFalse(rows[0]["matched"])

    def test_exact_duplicates_collapse_but_conflicts_are_rejected(self):
        duplicate = forecast("2025-12-31T11:00:00Z", 90)
        self.assertEqual(match_forecasts([actual()], [duplicate, duplicate])[0]["forecast_mw"], 90)
        with self.assertRaisesRegex(SourceDataError, "conflicting"):
            match_forecasts([actual()], [duplicate, forecast("2025-12-31T11:00:00Z", 91)])

    def test_actual_duplicates_are_collapsed_but_conflicts_are_rejected(self):
        row = actual()
        self.assertEqual(len(match_forecasts([row, row], [])), 1)
        with self.assertRaisesRegex(SourceDataError, "FUELHH contains conflicting"):
            match_forecasts([row, actual(generation=101)], [])

    def test_expected_interval_without_actual_is_reported_as_missing(self):
        from datetime import datetime, timezone
        interval = datetime(2026, 1, 1, tzinfo=timezone.utc)
        row = match_forecasts([], [forecast("2025-12-31T11:00:00Z", 90)], [interval])[0]
        self.assertFalse(row["matched"])
        self.assertIsNone(row["actual_mw"])
        self.assertEqual(row["forecast_mw"], 90)

    def test_hourly_forecast_does_not_fill_intermediate_half_hour(self):
        from datetime import datetime, timezone
        deliveries = [
            datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
        ]
        rows = match_forecasts(
            [actual(), actual("2026-01-01T00:30:00Z", 110)],
            [forecast("2025-12-31T11:30:00Z", 95)],
            deliveries,
        )
        self.assertTrue(rows[0]["matched"])
        self.assertEqual(rows[0]["forecast_mw"], 95)
        self.assertFalse(rows[1]["matched"])
        self.assertIsNone(rows[1]["forecast_mw"])
        self.assertIsNone(rows[1]["signed_error_mw"])

    def test_actuals_require_wind_and_aware_timestamps(self):
        with self.assertRaisesRegex(SourceDataError, "unexpected fuelType"):
            match_forecasts([{**actual(), "fuelType": "GAS"}], [])
        with self.assertRaisesRegex(SourceDataError, "UTC offset"):
            match_forecasts([{**actual(), "startTime": "2026-01-01T00:00:00"}], [])

    def test_forecast_timestamp_schema_errors_are_source_data_errors(self):
        with self.assertRaisesRegex(SourceDataError, "publishTime.*UTC offset"):
            match_forecasts([actual()], [forecast("2025-12-31T11:00:00", 99)])


if __name__ == "__main__":
    unittest.main()
