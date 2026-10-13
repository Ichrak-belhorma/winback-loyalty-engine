"""Replay recent lifecycle activity over seeded data so the dashboard has history.

Walks the last N days in 3-hour ticks and drives the real engine at each tick: the daily
segment refresh and win-back enrollment, welcome flows for that day's signups, review
requests for that day's deliveries, flow steps, deferred-message dispatch, and the store's
order events. Customer *responses* are simulated: a share of review requests get a rating
and a share of win-back customers come back and order. Every message still passes through
the compliance gate, so quiet hours, caps and deferrals show up as they would live.
"""

import logging
import random
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal

from compliance.gate import dispatch_deferred
from customers.models import Customer
from flows.definitions.winback import CANCEL_ORDERED
from flows.definitions.winback import FLOW as WINBACK
from flows.engine import cancel_active, enroll, process_due_enrollments
from flows.lifecycle import daily_refresh
from flows.models import FlowEnrollment
from messaging.models import Message
from orders.models import Order
from orders.services import record_order
from reviews.models import Review
from reviews.services import schedule_review_request, submit_review

TICK = timedelta(hours=3)
REVIEW_RESPONSE_RATE = 0.35
RATING_WEIGHTS = {5: 45, 4: 25, 3: 12, 2: 8, 1: 10}
# Chance per win-back message that the customer orders within the next few days.
WINBACK_RESPONSE_RATE = {"reminder": 0.03, "offer": 0.05, "final_offer": 0.07}


@contextmanager
def _quiet_logs() -> Iterator[None]:
    names = ["messaging.senders", "compliance.gate", "flows.engine"]
    previous = {name: logging.getLogger(name).level for name in names}
    for name in names:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        yield
    finally:
        for name, level in previous.items():
            logging.getLogger(name).setLevel(level)


def simulate_activity(days: int, now: datetime, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    start = (now - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    comebacks: list[tuple[datetime, Customer]] = []
    pending_ratings: list[tuple[datetime, Order]] = []

    with _quiet_logs():
        tick = start
        while tick < now:
            window_end = min(tick + TICK, now)
            if tick.hour == 15:  # daily job inside US send hours
                daily_refresh(tick)
            for customer in Customer.objects.filter(
                signed_up_at__gte=tick, signed_up_at__lt=window_end
            ):
                enroll(customer, "welcome", customer.signed_up_at)
            for order in Order.objects.filter(
                placed_at__gte=tick, placed_at__lt=window_end
            ).exclude(status=Order.Status.CANCELLED):
                cancel_active(order.customer, WINBACK, CANCEL_ORDERED, order.placed_at)
            for order in Order.objects.filter(
                delivered_at__gte=tick, delivered_at__lt=window_end
            ).select_related("customer"):
                schedule_review_request(order, order.delivered_at, order.delivered_at)

            for when, customer in [c for c in comebacks if c[0] < window_end]:
                comebacks.remove((when, customer))
                total = Decimal(str(round(rng.uniform(18, 70), 2)))
                record_order(customer, f"sim-{customer.pk}-{when:%Y%m%d%H}", total, when, when)
            for when, order in [r for r in pending_ratings if r[0] < window_end]:
                pending_ratings.remove((when, order))
                if not Review.objects.filter(order=order).exists():
                    rating = rng.choices(list(RATING_WEIGHTS), list(RATING_WEIGHTS.values()))[0]
                    submit_review(order, rating, "", when)

            dispatch_deferred(window_end)
            process_due_enrollments(window_end)

            # Includes messages deferred overnight and released during this tick.
            for message in Message.objects.filter(
                status=Message.Status.SENT, sent_at__gte=tick, sent_at__lte=window_end
            ).select_related("customer"):
                if message.flow == WINBACK and rng.random() < WINBACK_RESPONSE_RATE.get(
                    message.step, 0
                ):
                    comebacks.append(
                        (message.sent_at + timedelta(hours=rng.uniform(6, 96)), message.customer)
                    )
                elif message.flow == "review" and message.step == "request":
                    if rng.random() < REVIEW_RESPONSE_RATE:
                        enrollment = FlowEnrollment.objects.filter(
                            customer=message.customer, flow="review"
                        ).latest("enrolled_at")
                        order = Order.objects.get(pk=enrollment.context["order_id"])
                        pending_ratings.append(
                            (message.sent_at + timedelta(hours=rng.uniform(0.5, 8)), order)
                        )
            tick = window_end

    daily_refresh(now)
    return {
        "messages": Message.objects.count(),
        "enrollments": FlowEnrollment.objects.count(),
        "reviews": Review.objects.count(),
    }
