from datetime import datetime

from flows.definitions import winback
from segments.services import refresh_segments


def daily_refresh(now: datetime) -> dict[str, object]:
    """Recompute segments, then enroll newly lapsed customers in win-back."""
    segments = refresh_segments(now)
    return {"segments": segments, "winback_enrolled": winback.enroll_candidates(now)}
