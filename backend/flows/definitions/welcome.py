"""Welcome: greet on signup, then nudge at +2 days if there is still no first order."""

from datetime import datetime, timedelta

from flows.discounts import discount
from flows.models import FlowEnrollment
from flows.registry import register
from flows.steps import Advance, Complete, FlowDefinition, StepResult, send_step
from orders.models import Order

FLOW = "welcome"
NUDGE_DELAY = timedelta(days=2)


def welcome(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    send_step(enrollment, "welcome", now)
    return Advance("first_order_nudge", NUDGE_DELAY)


def first_order_nudge(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    ordered = enrollment.customer.orders.exclude(status=Order.Status.CANCELLED)
    if ordered.filter(placed_at__lte=now).exists():
        return Complete()
    send_step(enrollment, "first_order_nudge", now, {"discount": discount("welcome_nudge")})
    return Complete()


register(
    FlowDefinition(
        name=FLOW,
        first_step="welcome",
        handlers={"welcome": welcome, "first_order_nudge": first_order_nudge},
    )
)
