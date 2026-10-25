from calendar import monthrange
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    """Return UTC bounds [start, end) covering a calendar month.

    UK calendar-month edges are converted to UTC for API windows. This handles
    British daylight-saving transitions without shifting the selected month.
    """
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if not 1 <= year <= 9998:
        raise ValueError("year must be between 1 and 9998")
    uk = ZoneInfo("Europe/London")
    start = datetime.combine(date(year, month, 1), time.min, tzinfo=uk).astimezone(timezone.utc)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    end = datetime.combine(date(next_year, next_month, 1), time.min, tzinfo=uk).astimezone(timezone.utc)
    return start, end


def month_days(year: int, month: int) -> int:
    return monthrange(year, month)[1]
