from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from api.utils.datetime_utils import decision_cutoff_for_delivery
from api.utils.validation import SourceDataError, required_datetime, required_number, required_string


def _normalize_actual(row: dict[str, Any]) -> dict[str, Any]:
    start = required_datetime(row, "startTime", "FUELHH")
    fuel = required_string(row, "fuelType", "FUELHH").upper()
    generation = required_number(row, "generation", "FUELHH")
    if fuel != "WIND":
        raise SourceDataError(f"FUELHH returned unexpected fuelType {fuel!r} after wind filtering")
    return {"delivery_time": start, "actual_mw": generation}


def _normalize_forecast(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "delivery_time": required_datetime(row, "startTime", "WINDFOR"),
        "published_at": required_datetime(row, "publishTime", "WINDFOR"),
        "forecast_mw": required_number(row, "generation", "WINDFOR"),
    }


def _deduplicate_forecasts(forecasts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[datetime, datetime], dict[str, Any]] = {}
    for row in forecasts:
        key = (row["delivery_time"], row["published_at"])
        previous = by_key.get(key)
        if previous is not None and previous["forecast_mw"] != row["forecast_mw"]:
            raise SourceDataError("WINDFOR contains conflicting values for the same delivery and publication time")
        by_key[key] = row  # Exact duplicates collapse to one record.
    return list(by_key.values())


def _deduplicate_actuals(actuals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_delivery: dict[datetime, dict[str, Any]] = {}
    for row in actuals:
        key = row["delivery_time"]
        previous = by_delivery.get(key)
        if previous is not None and previous["actual_mw"] != row["actual_mw"]:
            raise SourceDataError("FUELHH contains conflicting values for the same delivery interval")
        by_delivery[key] = row
    return list(by_delivery.values())


def match_forecasts(
    actual_rows: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
    expected_delivery_times: list[datetime] | None = None,
) -> list[dict[str, Any]]:
    """For each actual interval, choose latest eligible forecast by delivery time.

    The assessment lacks a procurement cutoff, so the documented proxy is noon
    UK local time on the previous calendar day. No later publication is used.
    Exact duplicate source rows collapse; conflicting duplicates fail loudly.
    """
    actuals = _deduplicate_actuals([_normalize_actual(row) for row in actual_rows])
    actual_by_delivery = {item["delivery_time"]: item for item in actuals}
    forecasts = _deduplicate_forecasts([_normalize_forecast(row) for row in forecast_rows])
    by_delivery: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for forecast in forecasts:
        by_delivery[forecast["delivery_time"]].append(forecast)

    deliveries = expected_delivery_times if expected_delivery_times is not None else list(actual_by_delivery)
    records: list[dict[str, Any]] = []
    for delivery in sorted(set(deliveries)):
        actual = actual_by_delivery.get(delivery)
        cutoff = decision_cutoff_for_delivery(delivery)
        eligible = [item for item in by_delivery.get(delivery, []) if item["published_at"] <= cutoff]
        selected = max(eligible, key=lambda item: item["published_at"], default=None)
        forecast_value = selected["forecast_mw"] if selected else None
        actual_value = actual["actual_mw"] if actual is not None else None
        error = forecast_value - actual_value if forecast_value is not None and actual_value is not None else None
        records.append({
            "delivery_time": delivery,
            "forecast_mw": forecast_value,
            "actual_mw": actual_value,
            "signed_error_mw": error,
            "absolute_error_mw": abs(error) if error is not None else None,
            "percentage_error": (error / actual_value * 100) if error is not None and actual_value != 0 else None,
            "forecast_published_at": selected["published_at"] if selected else None,
            "decision_cutoff": cutoff,
            "matched": selected is not None and actual_value is not None,
        })
    return records


def aggregate_half_hour_actuals(
    actual_rows: list[dict[str, Any]],
    expected_hour_starts: list[datetime],
) -> list[dict[str, Any]]:
    """Average each complete UTC delivery-hour pair of FUELHH values.

    Elexon timestamps denote the start of each half-hour delivery interval.
    UTC grouping avoids ambiguous/nonexistent local wall-clock hours at DST.
    """
    actuals = _deduplicate_actuals([_normalize_actual(row) for row in actual_rows])
    by_delivery = {row["delivery_time"]: row["actual_mw"] for row in actuals}
    rows = []
    for hour_start in sorted(set(expected_hour_starts)):
        first = by_delivery.get(hour_start)
        second = by_delivery.get(hour_start + timedelta(minutes=30))
        valid_count = int(first is not None) + int(second is not None)
        actual = (first + second) / 2 if valid_count == 2 else None
        rows.append({
            "delivery_time": hour_start,
            "actual_mw": actual,
            "actual_half_hour_count": valid_count,
        })
    return rows


def match_hourly_forecasts(
    hourly_actuals: list[dict[str, Any]],
    forecast_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach the latest same-hour WINDFOR publication eligible at the cutoff."""
    forecasts = _deduplicate_forecasts([_normalize_forecast(row) for row in forecast_rows])
    by_delivery: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for forecast in forecasts:
        by_delivery[forecast["delivery_time"]].append(forecast)

    rows = []
    for actual in sorted(hourly_actuals, key=lambda row: row["delivery_time"]):
        delivery = actual["delivery_time"]
        cutoff = decision_cutoff_for_delivery(delivery)
        eligible = [item for item in by_delivery.get(delivery, []) if item["published_at"] <= cutoff]
        selected = max(eligible, key=lambda item: item["published_at"], default=None)
        forecast_value = selected["forecast_mw"] if selected else None
        actual_value = actual["actual_mw"]
        matched = actual_value is not None and forecast_value is not None
        error = forecast_value - actual_value if matched else None
        rows.append({
            "delivery_time": delivery,
            "actual_mw": actual_value,
            "actual_half_hour_count": actual["actual_half_hour_count"],
            "forecast_mw": forecast_value,
            "signed_error_mw": error,
            "absolute_error_mw": abs(error) if error is not None else None,
            "percentage_error": error / actual_value * 100 if error is not None and actual_value != 0 else None,
            "forecast_published_at": selected["published_at"] if selected else None,
            "decision_cutoff": cutoff,
            "matched": matched,
        })
    return rows
