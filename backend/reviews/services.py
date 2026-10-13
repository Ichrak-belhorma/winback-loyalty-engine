from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, transaction

from flows.definitions.review import FLOW, REQUEST_DELAY, enrollment_key
from flows.engine import enroll
from flows.models import FlowEnrollment
from flows.steps import send_personalized
from orders.models import Order
from reviews.models import Review

POSITIVE_MIN_RATING = 4
FOLLOWUP_TAG = "needs_followup"


def schedule_review_request(
    order: Order, delivered_at: datetime, now: datetime
) -> FlowEnrollment | None:
    order.status, order.delivered_at = Order.Status.DELIVERED, delivered_at
    order.save(update_fields=["status", "delivered_at"])
    return enroll(
        order.customer,
        FLOW,
        now,
        key=enrollment_key(order.pk),
        context={"order_id": order.pk},
        start_at=delivered_at + REQUEST_DELAY,
    )


class DuplicateReview(Exception):
    pass


@transaction.atomic
def submit_review(order: Order, rating: int, comment: str, now: datetime) -> Review:
    """Happy customers get the public review link; unhappy ones a private fix-it message."""
    try:
        with transaction.atomic():
            review = Review.objects.create(
                customer=order.customer,
                order=order,
                rating=rating,
                comment=comment,
                submitted_at=now,
            )
    except IntegrityError as exc:
        raise DuplicateReview from exc

    customer = order.customer
    if rating >= POSITIVE_MIN_RATING:
        send_personalized(
            customer, FLOW, "public_thanks", now, {"link": settings.PUBLIC_REVIEW_URL}
        )
    else:
        send_personalized(customer, FLOW, "fix_it", now)
        customer.add_tag(FOLLOWUP_TAG)
    return review
