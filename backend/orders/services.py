from datetime import datetime
from decimal import Decimal

from django.db import transaction

from customers.models import Customer
from flows.definitions.winback import CANCEL_ORDERED
from flows.definitions.winback import FLOW as WINBACK
from flows.engine import cancel_active
from orders.models import Order
from referrals.services import reward_first_order


@transaction.atomic
def record_order(
    customer: Customer, external_id: str, total: Decimal, placed_at: datetime, now: datetime
) -> Order:
    """Store a new order and react to it: a returning customer leaves win-back at once, and a
    referred customer's first order rewards their referrer."""
    order = Order.objects.create(
        customer=customer, external_id=external_id, total=total, placed_at=placed_at
    )
    cancel_active(customer, WINBACK, CANCEL_ORDERED, now)
    reward_first_order(order, now)
    return order
