"""Win-back: reminder, then a small discount (+4 days), then a final offer (+7 days).

Customers enter when they go 60+ days without ordering. Any new order cancels the
enrollment immediately (see orders.services); each step also re-checks, as a safety net.
"""

from datetime import datetime, timedelta

from customers.models import Customer
from flows.discounts import discount
from flows.engine import enroll
from flows.models import FlowEnrollment
from flows.registry import register
from flows.steps import Advance, Cancel, Complete, FlowDefinition, StepResult, send_step
from orders.models import Order
from segments.models import CustomerRFM

FLOW = "winback"
OFFER_DELAY = timedelta(days=4)
FINAL_OFFER_DELAY = timedelta(days=7)
REENROLL_COOLDOWN = timedelta(days=90)
ENTRY_FLAGS = (CustomerRFM.Inactivity.INACTIVE_60, CustomerRFM.Inactivity.INACTIVE_90)
CANCEL_ORDERED = "ordered"


def _ordered_since_enrolling(enrollment: FlowEnrollment, now: datetime) -> bool:
    return (
        enrollment.customer.orders.exclude(status=Order.Status.CANCELLED)
        .filter(placed_at__gte=enrollment.enrolled_at, placed_at__lte=now)
        .exists()
    )


def reminder(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    if _ordered_since_enrolling(enrollment, now):
        return Cancel(CANCEL_ORDERED)
    send_step(enrollment, "reminder", now)
    return Advance("offer", OFFER_DELAY)


def offer(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    if _ordered_since_enrolling(enrollment, now):
        return Cancel(CANCEL_ORDERED)
    send_step(enrollment, "offer", now, {"discount": discount("winback_offer")})
    return Advance("final_offer", FINAL_OFFER_DELAY)


def final_offer(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    if _ordered_since_enrolling(enrollment, now):
        return Cancel(CANCEL_ORDERED)
    send_step(enrollment, "final_offer", now, {"discount": discount("winback_final")})
    return Complete()


def enroll_candidates(now: datetime) -> int:
    """Enroll lapsed buyers (60+ days) not already in, or recently through, win-back."""
    recently_enrolled = FlowEnrollment.objects.filter(
        flow=FLOW, enrolled_at__gte=now - REENROLL_COOLDOWN
    ).values("customer_id")
    candidates = Customer.objects.filter(
        unsubscribed=False, rfm__inactivity__in=ENTRY_FLAGS, rfm__frequency__gte=1
    ).exclude(pk__in=recently_enrolled)
    return sum(1 for customer in candidates if enroll(customer, FLOW, now))


register(
    FlowDefinition(
        name=FLOW,
        first_step="reminder",
        handlers={"reminder": reminder, "offer": offer, "final_offer": final_offer},
    )
)
