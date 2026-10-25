from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
UK = ZoneInfo("Europe/London")


def parse_elexon_datetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp, requiring an explicit UTC offset."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp has no UTC offset: {value!r}")
    return parsed.astimezone(UTC)


def decision_cutoff_for_delivery(delivery_time: datetime) -> datetime:
    """Cutoff: 12:00 Europe/London on the calendar day before delivery."""
    local_delivery = delivery_time.astimezone(UK)
    previous_day = local_delivery.date() - timedelta(days=1)
    return datetime.combine(previous_day, time(hour=12), tzinfo=UK).astimezone(UTC)


def delivery_date_uk(delivery_time: datetime) -> date:
    return delivery_time.astimezone(UK).date()
