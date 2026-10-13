from datetime import datetime

from django.db import transaction

from customers.models import Customer
from customers.phones import normalize_phone
from flows.engine import enroll


@transaction.atomic
def sign_up(
    *,
    email: str,
    first_name: str,
    now: datetime,
    last_name: str = "",
    phone: str = "",
    timezone: str = "",
) -> tuple[Customer, bool]:
    """Create the customer and start the welcome flow; existing emails are returned as-is."""
    existing = Customer.objects.filter(email=email.lower()).first()
    if existing:
        return existing, False
    customer = Customer.objects.create(
        email=email.lower(),
        first_name=first_name,
        last_name=last_name,
        phone=normalize_phone(phone),
        signed_up_at=now,
        **({"timezone": timezone} if timezone else {}),
    )
    enroll(customer, "welcome", now)
    return customer, True
