import asyncio
from datetime import datetime, timedelta, timezone

from api.analytics.forecast_matching import aggregate_half_hour_actuals, match_forecasts, match_hourly_forecasts
from api.analytics.metrics import calculate_metrics
from api.services.actuals_service import ActualsService
from api.services.forecast_service import ForecastService
from api.utils.date_ranges import month_bounds
from api.utils.datetime_utils import UK


class MonthlyReportService:
    def __init__(self, actuals: ActualsService, forecasts: ForecastService):
        self.actuals = actuals
        self.forecasts = forecasts

    async def get_report(self, year: int, month: int) -> dict:
        start_utc, end_utc = month_bounds(year, month)
        # Include the day before the month because its publications can be used
        # at the noon day-ahead cutoff for the first delivery day.
        publish_from = (start_utc.astimezone(UK) - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(timezone.utc)
        publish_to = end_utc
        actual_rows, forecast_rows = await asyncio.gather(
            self.actuals.get_month(year, month),
            self.forecasts.get_publications(publish_from, publish_to),
        )
        expected = []
        current = start_utc
        while current < end_utc:
            expected.append(current)
            current += timedelta(minutes=30)
        records = match_forecasts(actual_rows, forecast_rows, expected_delivery_times=expected)
        # Keep rows whose delivery start belongs to the selected UK calendar month.
        records = [r for r in records if start_utc <= r["delivery_time"] < end_utc]
        metrics = calculate_metrics(records)
        matched = metrics["matched_intervals"]
        actual_count = sum(record["actual_mw"] is not None for record in records)
        forecast_count = sum(record["forecast_mw"] is not None for record in records)
        expected_hours = []
        current = start_utc
        while current < end_utc:
            expected_hours.append(current)
            current += timedelta(hours=1)
        hourly_actuals = aggregate_half_hour_actuals(actual_rows, expected_hours)
        hourly_records = match_hourly_forecasts(hourly_actuals, forecast_rows)
        eligible_actual_hours = sum(row["actual_half_hour_count"] == 2 for row in hourly_records)
        hourly_matched = sum(row["matched"] for row in hourly_records)
        hourly_metrics = calculate_metrics(hourly_records)
        hourly_forecast_count = sum(row["forecast_mw"] is not None for row in hourly_records)
        exact_half_hour_coverage = matched / len(records) if records else None
        hourly_forecast_coverage = hourly_matched / eligible_actual_hours if eligible_actual_hours else None
        return {
            "year": year,
            "month": month,
            "period_start": start_utc,
            "period_end_exclusive": end_utc,
            "timezone": "Europe/London",
            "unit": "MW",
            "source_retrieved_at": datetime.now(timezone.utc),
            "source_contract_status": (
                "verified_live_contract" if self.actuals.client.LIVE_CONTRACT_VERIFIED
                else "unverified_live_contract"
            ),
            "decision_cutoff_rule": "12:00 Europe/London on the day before each delivery date",
            "expected_intervals": len(records),
            "actual_intervals": actual_count,
            "forecast_intervals": forecast_count,
            "matched_intervals": matched,
            "unmatched_intervals": len(records) - matched,
            "missing_actual_intervals": len(records) - actual_count,
            "missing_forecast_intervals": len(records) - forecast_count,
            "metrics": metrics,
            "hourly_analysis": {
                "comparison_frequency": "hourly",
                "actual_method": "arithmetic mean of the two consecutive half-hour FUELHH interval-average MW values; both are required",
                "expected_periods": len(hourly_records),
                "eligible_actual_periods": eligible_actual_hours,
                "actual_incomplete_periods": len(hourly_records) - eligible_actual_hours,
                "forecast_periods": hourly_forecast_count,
                "matched_periods": hourly_matched,
                "unmatched_periods": len(hourly_records) - hourly_matched,
                "actual_completeness_percent": (eligible_actual_hours / len(hourly_records) * 100) if hourly_records else None,
                "forecast_coverage_percent": hourly_forecast_coverage * 100 if hourly_forecast_coverage is not None else None,
                "exact_half_hour_matched_periods": matched,
                "exact_half_hour_expected_periods": len(records),
                "exact_half_hour_coverage_percent": exact_half_hour_coverage * 100 if exact_half_hour_coverage is not None else None,
                "metrics": hourly_metrics,
            },
            "records": records,
            "hourly_records": hourly_records,
        }
