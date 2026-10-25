import unittest
from datetime import timezone

from api.utils.date_ranges import month_bounds


class DateRangeTests(unittest.TestCase):
    def test_january_2026_bounds_are_uk_calendar_month_in_utc(self):
        start, end = month_bounds(2026, 1)
        self.assertEqual(start.isoformat(), "2026-01-01T00:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-02-01T00:00:00+00:00")

    def test_month_bounds_account_for_british_summer_time(self):
        start, end = month_bounds(2026, 7)
        self.assertEqual(start, start.astimezone(timezone.utc))
        self.assertEqual(start.isoformat(), "2026-06-30T23:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-07-31T23:00:00+00:00")

    def test_leap_year_february(self):
        self.assertEqual(month_bounds(2024, 2)[1].isoformat(), "2024-03-01T00:00:00+00:00")

    def test_invalid_month_rejected(self):
        with self.assertRaises(ValueError):
            month_bounds(2026, 13)


if __name__ == "__main__":
    unittest.main()
