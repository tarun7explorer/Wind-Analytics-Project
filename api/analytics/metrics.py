from collections.abc import Iterable, Mapping
from math import sqrt
from typing import Any


def calculate_metrics(records: Iterable[Mapping[str, Any]]) -> dict[str, float | int | None]:
    """Calculate errors over valid matched intervals only.

    Error is forecast minus actual. WAPE is sum(abs(error))/sum(actual)*100.
    It is undefined when there are no matched rows or the actual denominator is 0.
    """
    errors: list[tuple[float, float]] = []
    for row in records:
        forecast = row.get("forecast_mw")
        actual = row.get("actual_mw")
        if row.get("matched") is not True or forecast is None or actual is None:
            continue
        f, a = float(forecast), float(actual)
        errors.append((f - a, a))
    if not errors:
        return {"matched_intervals": 0, "mae_mw": None, "rmse_mw": None, "wape_percent": None}
    absolute_sum = sum(abs(error) for error, _ in errors)
    actual_sum = sum(actual for _, actual in errors)
    return {
        "matched_intervals": len(errors),
        "mae_mw": absolute_sum / len(errors),
        "rmse_mw": sqrt(sum(error * error for error, _ in errors) / len(errors)),
        "wape_percent": (absolute_sum / actual_sum * 100) if actual_sum != 0 else None,
    }
