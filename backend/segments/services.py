from collections import Counter
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Max, Min, Q, Sum

from customers.models import Customer
from orders.models import Order
from segments.models import CustomerRFM
from segments.rfm import CustomerStats, score_customers

RFM_FIELDS = [
    "recency_days",
    "frequency",
    "monetary",
    "r_score",
    "f_score",
    "m_score",
    "segment",
    "inactivity",
    "computed_at",
]


def load_stats(now: datetime) -> list[CustomerStats]:
    counted = Q(orders__placed_at__lte=now) & ~Q(orders__status=Order.Status.CANCELLED)
    rows = Customer.objects.annotate(
        n=Count("orders", filter=counted),
        spend=Sum("orders__total", filter=counted),
        first=Min("orders__placed_at", filter=counted),
        last=Max("orders__placed_at", filter=counted),
    ).values_list("id", "signed_up_at", "n", "spend", "first", "last")
    return [
        CustomerStats(cid, signup, n, float(spend or 0), first, last)
        for cid, signup, n, spend, first, last in rows
    ]


@transaction.atomic
def refresh_segments(now: datetime) -> dict[str, int]:
    """Recompute every customer's RFM snapshot; returns customer counts per segment."""
    results = score_customers(load_stats(now), now)
    CustomerRFM.objects.bulk_create(
        [
            CustomerRFM(
                customer_id=r.customer_id,
                recency_days=r.recency_days,
                frequency=r.frequency,
                monetary=Decimal(str(round(r.monetary, 2))),
                r_score=r.r_score,
                f_score=r.f_score,
                m_score=r.m_score,
                segment=r.segment,
                inactivity=r.inactivity,
                computed_at=now,
            )
            for r in results
        ],
        update_conflicts=True,
        unique_fields=["customer"],
        update_fields=RFM_FIELDS,
        batch_size=1000,
    )
    return dict(Counter(r.segment for r in results))
