"""RFM scoring: quintile scores (1-5) for recency, frequency and monetary value.

Scores use the mid-rank percentile, `(count below + half the ties) / n`, so tied values always
share a score and a population where everyone is equal lands in the middle (3) rather than
at an arbitrary end.
"""

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from segments.models import CustomerRFM

Segment = CustomerRFM.Segment
Inactivity = CustomerRFM.Inactivity

NEW_CUSTOMER_DAYS = 30
INACTIVITY_THRESHOLDS: list[tuple[int, str]] = [
    (90, Inactivity.INACTIVE_90),
    (60, Inactivity.INACTIVE_60),
    (30, Inactivity.INACTIVE_30),
]


def quintile_scores(values: Sequence[float]) -> list[int]:
    """Score each value 1-5 by its mid-rank percentile; higher values score higher."""
    n = len(values)
    ordered = sorted(values)
    scores = []
    for value in values:
        below = _count_below(ordered, value)
        ties = _count_below(ordered, value, inclusive=True) - below
        percentile = (below + ties / 2) / n
        scores.append(min(5, 1 + int(percentile * 5)))
    return scores


def _count_below(ordered: Sequence[float], value: float, inclusive: bool = False) -> int:
    return (bisect_right if inclusive else bisect_left)(ordered, value)


def inactivity_flag(days_inactive: int) -> str:
    """30/60/90-day flags; a boundary day belongs to the higher flag (day 30 is inactive_30)."""
    return next(
        (flag for days, flag in INACTIVITY_THRESHOLDS if days_inactive >= days), Inactivity.ACTIVE
    )


@dataclass(frozen=True)
class CustomerStats:
    customer_id: int
    signed_up_at: datetime
    frequency: int
    monetary: float
    first_order_at: datetime | None
    last_order_at: datetime | None


@dataclass(frozen=True)
class RFMResult:
    customer_id: int
    recency_days: int | None
    frequency: int
    monetary: float
    r_score: int | None
    f_score: int | None
    m_score: int | None
    segment: str
    inactivity: str


def classify(r: int | None, f: int | None, frequency: int, days_since_first_activity: int) -> str:
    """Named segment from RFM scores; rules are checked top to bottom."""
    if frequency == 0 or r is None or f is None:
        return (
            Segment.NEW if days_since_first_activity <= NEW_CUSTOMER_DAYS else Segment.HIBERNATING
        )
    if days_since_first_activity <= NEW_CUSTOMER_DAYS:
        return Segment.NEW
    if r >= 4 and f >= 4:
        return Segment.CHAMPIONS
    if r >= 3 and f >= 3:
        return Segment.LOYAL
    if r <= 2 and f >= 3:
        return Segment.AT_RISK
    if r >= 3:
        return Segment.LOYAL
    return Segment.HIBERNATING


def score_customers(stats: Sequence[CustomerStats], now: datetime) -> list[RFMResult]:
    buyers = [s for s in stats if s.frequency > 0 and s.last_order_at]
    recency = {s.customer_id: (now - s.last_order_at).days for s in buyers}
    r_scores = quintile_scores([-recency[s.customer_id] for s in buyers]) if buyers else []
    f_scores = quintile_scores([s.frequency for s in buyers]) if buyers else []
    m_scores = quintile_scores([s.monetary for s in buyers]) if buyers else []
    scored = {
        s.customer_id: (r, f, m)
        for s, r, f, m in zip(buyers, r_scores, f_scores, m_scores, strict=True)
    }

    results = []
    for s in stats:
        r, f, m = scored.get(s.customer_id, (None, None, None))
        first_activity = s.first_order_at or s.signed_up_at
        last_activity = s.last_order_at or s.signed_up_at
        results.append(
            RFMResult(
                customer_id=s.customer_id,
                recency_days=recency.get(s.customer_id),
                frequency=s.frequency,
                monetary=s.monetary,
                r_score=r,
                f_score=f,
                m_score=m,
                segment=classify(r, f, s.frequency, (now - first_activity).days),
                inactivity=inactivity_flag((now - last_activity).days),
            )
        )
    return results
