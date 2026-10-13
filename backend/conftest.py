from collections.abc import Callable
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import count

import pytest
from django.utils import timezone

from customers.models import Customer
from orders.models import Order

_seq = count(1)


@pytest.fixture
def make_customer() -> Callable[..., Customer]:
    def _make(**fields) -> Customer:
        n = next(_seq)
        defaults = {
            "email": f"customer{n}@example.com",
            "first_name": "Sam",
            "phone": f"+1555000{n:04d}",
            "timezone": "America/New_York",
            "signed_up_at": timezone.now() - timedelta(days=200),
        }
        return Customer.objects.create(**{**defaults, **fields})

    return _make


@pytest.fixture
def make_order() -> Callable[..., Order]:
    def _make(customer: Customer, placed_at: datetime, total: str = "30.00", **fields) -> Order:
        return Order.objects.create(
            customer=customer,
            placed_at=placed_at,
            total=Decimal(total),
            status=fields.pop("status", Order.Status.DELIVERED),
            **fields,
        )

    return _make
