from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings


def customer_zone(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(settings.DEFAULT_CUSTOMER_TIMEZONE)


def in_quiet_hours(now: datetime, tz_name: str) -> bool:
    """True inside the customer-local quiet window (default 21:00-08:00, crossing midnight)."""
    hour = now.astimezone(customer_zone(tz_name)).hour
    start, end = settings.QUIET_HOURS_START, settings.QUIET_HOURS_END
    if start > end:
        return hour >= start or hour < end
    return start <= hour < end


def next_send_window(now: datetime, tz_name: str) -> datetime:
    """The next moment quiet hours end, in the customer's timezone (returned as aware UTC)."""
    zone = customer_zone(tz_name)
    local = now.astimezone(zone)
    candidate = datetime.combine(local.date(), time(settings.QUIET_HOURS_END), tzinfo=zone)
    if candidate <= local:
        candidate = datetime.combine(
            local.date() + timedelta(days=1), time(settings.QUIET_HOURS_END), tzinfo=zone
        )
    return candidate.astimezone(ZoneInfo("UTC"))
