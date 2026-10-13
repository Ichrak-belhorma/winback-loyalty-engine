from datetime import datetime

from django.conf import settings
from django.db import transaction

from customers.models import Customer
from customers.services import sign_up
from flows.discounts import discount
from flows.steps import send_personalized
from orders.models import Order
from referrals.models import Referral


class ReferralError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@transaction.atomic
def redeem(code: str, email: str, first_name: str, now: datetime) -> Referral:
    """Attach a friend to a referrer's code. The friend's discount applies to their first order."""
    referrer = Customer.objects.filter(referral_code=code.strip().upper()).first()
    if referrer is None:
        raise ReferralError(404, "Unknown referral code.")
    if referrer.email == email.lower():
        raise ReferralError(400, "You can't redeem your own referral code.")
    friend, _ = sign_up(email=email, first_name=first_name, now=now)
    if Referral.objects.filter(referee=friend).exists():
        raise ReferralError(409, "This customer has already been referred.")
    if friend.orders.exclude(status=Order.Status.CANCELLED).exists():
        raise ReferralError(409, "Referral codes are for new customers only.")
    return Referral.objects.create(
        referrer=referrer,
        referee=friend,
        code=referrer.referral_code,
        referee_discount_percent=settings.DISCOUNTS["referral_referee"],
        referrer_reward_percent=settings.DISCOUNTS["referral_referrer"],
        created_at=now,
    )


def reward_first_order(order: Order, now: datetime) -> Referral | None:
    """On a referred customer's first order, reward the referrer (once)."""
    referral = (
        Referral.objects.select_for_update()
        .filter(referee=order.customer, status=Referral.Status.PENDING)
        .first()
    )
    if referral is None:
        return None
    is_first = (
        not order.customer.orders.exclude(status=Order.Status.CANCELLED)
        .exclude(pk=order.pk)
        .exists()
    )
    if not is_first:
        return None
    referral.status, referral.rewarded_at = Referral.Status.REWARDED, now
    referral.save(update_fields=["status", "rewarded_at"])
    send_personalized(
        referral.referrer,
        "referral",
        "referrer_reward",
        now,
        {"discount": discount("referral_referrer")},
    )
    return referral
