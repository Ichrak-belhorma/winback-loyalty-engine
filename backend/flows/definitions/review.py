"""Review request: 3 hours after delivery, ask for a rating (once per order)."""

from datetime import datetime, timedelta

from django.conf import settings

from flows.models import FlowEnrollment
from flows.registry import register
from flows.steps import Complete, FlowDefinition, StepResult, send_step
from reviews.models import Review

FLOW = "review"
REQUEST_DELAY = timedelta(hours=3)


def enrollment_key(order_id: int) -> str:
    return f"review:{order_id}"


def request(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    order_id = enrollment.context["order_id"]
    if Review.objects.filter(order_id=order_id).exists():
        return Complete()
    send_step(enrollment, "request", now, {"link": f"{settings.REVIEW_FORM_URL}/{order_id}"})
    return Complete()


register(FlowDefinition(name=FLOW, first_step="request", handlers={"request": request}))
