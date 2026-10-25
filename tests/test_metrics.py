import unittest

from api.analytics.metrics import calculate_metrics


class MetricsTests(unittest.TestCase):
    def test_metrics_use_only_matched_rows_and_forecast_minus_actual(self):
        result = calculate_metrics([
            {"forecast_mw": 110, "actual_mw": 100, "matched": True},
            {"forecast_mw": 80, "actual_mw": 100, "matched": True},
            {"forecast_mw": None, "actual_mw": 0, "matched": False},
        ])
        self.assertEqual(result["matched_intervals"], 2)
        self.assertEqual(result["mae_mw"], 15)
        self.assertAlmostEqual(result["rmse_mw"], 250 ** 0.5)
        self.assertEqual(result["wape_percent"], 15)

    def test_wape_undefined_when_actual_sum_is_zero(self):
        result = calculate_metrics([{"forecast_mw": 4, "actual_mw": 0, "matched": True}])
        self.assertEqual(result["mae_mw"], 4)
        self.assertEqual(result["rmse_mw"], 4)
        self.assertIsNone(result["wape_percent"])

    def test_all_unmatched_has_no_metrics(self):
        result = calculate_metrics([{"forecast_mw": None, "actual_mw": 1, "matched": False}])
        self.assertEqual(result, {"matched_intervals": 0, "mae_mw": None, "rmse_mw": None, "wape_percent": None})

    def test_rows_without_an_explicit_true_match_flag_are_excluded(self):
        result = calculate_metrics([
            {"forecast_mw": 10, "actual_mw": 5},
            {"forecast_mw": 9, "actual_mw": 5, "matched": None},
        ])
        self.assertEqual(result, {"matched_intervals": 0, "mae_mw": None, "rmse_mw": None, "wape_percent": None})


if __name__ == "__main__":
    unittest.main()
