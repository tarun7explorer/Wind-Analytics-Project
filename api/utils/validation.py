from collections.abc import Mapping
from math import isfinite
from typing import Any

from api.utils.datetime_utils import parse_elexon_datetime


class SourceDataError(ValueError):
    """Raised when an upstream response does not match the expected contract."""


def unwrap_records(payload: Any, dataset: str) -> list[Mapping[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("data")
    if not isinstance(payload, list):
        raise SourceDataError(f"{dataset} response must be a JSON array (or an object with a data array)")
    if any(not isinstance(row, dict) for row in payload):
        raise SourceDataError(f"{dataset} response contains a non-object record")
    return payload


def required_number(record: Mapping[str, Any], field: str, dataset: str) -> float:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise SourceDataError(f"{dataset} record has invalid or missing {field!r}")
    return float(value)


def required_string(record: Mapping[str, Any], field: str, dataset: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise SourceDataError(f"{dataset} record has invalid or missing {field!r}")
    return value


def required_datetime(record: Mapping[str, Any], field: str, dataset: str):
    value = required_string(record, field, dataset)
    try:
        return parse_elexon_datetime(value)
    except ValueError as exc:
        raise SourceDataError(f"{dataset} record has invalid {field!r}: {exc}") from exc
