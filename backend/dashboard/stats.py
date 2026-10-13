from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.db.models import Count, Exists, OuterRef, Q
from django.db.models.functions import TruncDate

from customers.models import Customer
from flows.models import FlowEnrollment
from messaging.models import Message
from orders.models import Order
from segments.models import CustomerRFM

FLOWS = ["welcome", "winback", "review", "referral"]


def segment_counts() -> list[dict[str, Any]]:
    counts = dict(CustomerRFM.objects.values_list("segment").annotate(n=Count("id")).order_by())
    return [
        {"segment": value, "label": label, "count": counts.get(value, 0)}
        for value, label in CustomerRFM.Segment.choices
    ]


def inactivity_counts() -> dict[str, int]:
    counts = dict(CustomerRFM.objects.values_list("inactivity").annotate(n=Count("id")).order_by())
    return {value: counts.get(value, 0) for value in CustomerRFM.Inactivity.values}


def message_stats() -> dict[str, Any]:
    status_counts = dict(Message.objects.values_list("status").annotate(n=Count("id")).order_by())
    by_flow = {
        row["flow"]: row
        for row in Message.objects.values("flow").annotate(
            sent=Count("id", filter=Q(status=Message.Status.SENT)),
            blocked=Count("id", filter=Q(status=Message.Status.BLOCKED)),
            deferred=Count("id", filter=Q(status=Message.Status.DEFERRED)),
            failed=Count("id", filter=Q(status=Message.Status.FAILED)),
        )
    }
    blocked = dict(
        Message.objects.filter(status=Message.Status.BLOCKED)
        .values_list("block_reason")
        .annotate(n=Count("id"))
        .order_by()
    )
    personalization = dict(
        Message.objects.values_list("personalization").annotate(n=Count("id")).order_by()
    )
    return {
        "total": sum(status_counts.values()),
        "by_status": {s: status_counts.get(s, 0) for s in Message.Status.values},
        "by_flow": [
            {
                "flow": flow,
                **{
                    k: by_flow.get(flow, {}).get(k, 0)
                    for k in ("sent", "blocked", "deferred", "failed")
                },
            }
            for flow in FLOWS
        ],
        "blocked_by_reason": blocked,
        "sent_after_quiet_hours": Message.objects.filter(
            status=Message.Status.SENT, scheduled_for__isnull=False
        ).count(),
        "personalization": {p: personalization.get(p, 0) for p in Message.Personalization.values},
    }


def reactivation(now: datetime) -> dict[str, Any]:
    """Share of win-back enrollees who ordered within the window after enrolling."""
    window = settings.REACTIVATION_WINDOW_DAYS
    ordered_in_window = Order.objects.filter(
        customer=OuterRef("customer"),
        placed_at__gte=OuterRef("enrolled_at"),
        placed_at__lte=OuterRef("enrolled_at") + timedelta(days=window),
    ).exclude(status=Order.Status.CANCELLED)
    enrollments = FlowEnrollment.objects.filter(flow="winback").annotate(
        reactivated=Exists(ordered_in_window)
    )
    enrolled = enrollments.count()
    reactivated = enrollments.filter(reactivated=True).count()
    return {
        "window_days": window,
        "enrolled": enrolled,
        "reactivated": reactivated,
        "rate": round(reactivated / enrolled, 4) if enrolled else None,
        "in_progress": enrollments.filter(status=FlowEnrollment.Status.ACTIVE).count(),
    }


def overview(now: datetime) -> dict[str, Any]:
    customers = Customer.objects.aggregate(
        total=Count("id"), unsubscribed=Count("id", filter=Q(unsubscribed=True))
    )
    active_enrollments = dict(
        FlowEnrollment.objects.filter(status=FlowEnrollment.Status.ACTIVE)
        .values_list("flow")
        .annotate(n=Count("id"))
        .order_by()
    )
    return {
        "customers": customers,
        "segments": segment_counts(),
        "inactivity": inactivity_counts(),
        "messages": message_stats(),
        "reactivation": reactivation(now),
        "active_enrollments": {flow: active_enrollments.get(flow, 0) for flow in FLOWS},
    }


def messages_over_time(now: datetime, days: int) -> list[dict[str, Any]]:
    """Sent messages per UTC day and flow, zero-filled, oldest first."""
    start = (now - timedelta(days=days - 1)).date()
    rows = (
        Message.objects.filter(status=Message.Status.SENT, sent_at__date__gte=start)
        .annotate(day=TruncDate("sent_at"))
        .values_list("day", "flow")
        .annotate(n=Count("id"))
    )
    counts: dict[tuple[date, str], int] = {(day, flow): n for day, flow, n in rows}
    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        point: dict[str, Any] = {"date": day.isoformat()}
        point.update({flow: counts.get((day, flow), 0) for flow in FLOWS})
        point["total"] = sum(point[flow] for flow in FLOWS)
        series.append(point)
    return series
