"""Synthetic demo data: customers drawn from behavioural archetypes so every segment is populated.

Each archetype controls signup age, order count and how long ago the last order was, which
gives realistic recency/frequency spreads (a few frequent recent buyers, a long tail of
lapsed one-timers).
"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from faker import Faker

from customers.models import Customer, generate_referral_code
from orders.models import Order

US_TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
]


@dataclass(frozen=True)
class Archetype:
    name: str
    weight: float
    signup_days: tuple[int, int]
    orders: tuple[int, int]
    last_order_days: tuple[int, int]


ARCHETYPES = [
    Archetype("champion", 0.10, (120, 540), (6, 18), (0, 14)),
    Archetype("loyal", 0.20, (120, 540), (4, 9), (10, 45)),
    Archetype("at_risk", 0.15, (150, 540), (3, 9), (60, 150)),
    Archetype("hibernating", 0.25, (200, 540), (1, 3), (120, 400)),
    Archetype("one_time", 0.15, (60, 400), (1, 1), (30, 200)),
    Archetype("new", 0.15, (0, 30), (0, 2), (0, 30)),
]


@dataclass
class SeedResult:
    customers: int
    orders: int


def _basket_total(rng: random.Random) -> Decimal:
    """Same-day delivery baskets: mostly $20-60 with a long tail."""
    return Decimal(str(round(min(250.0, max(8.0, rng.lognormvariate(3.5, 0.45))), 2)))


def _order_times(
    rng: random.Random, archetype: Archetype, signup: datetime, now: datetime
) -> list[datetime]:
    count = rng.randint(*archetype.orders)
    if count == 0:
        return []
    earliest = max(signup, now - timedelta(days=archetype.last_order_days[1]))
    latest = now - timedelta(days=archetype.last_order_days[0])
    last = earliest + (latest - earliest) * rng.random() if latest > earliest else latest
    last = max(last, signup)
    times = [last]
    span = (last - signup).total_seconds()
    times += [signup + timedelta(seconds=span * rng.random()) for _ in range(count - 1)]
    return sorted(times)


@transaction.atomic
def seed_demo_data(customer_count: int, seed: int, now: datetime) -> SeedResult:
    rng = random.Random(seed)
    fake = Faker("en_US")
    fake.seed_instance(seed)
    weights = [a.weight for a in ARCHETYPES]

    customers: list[Customer] = []
    plans: list[tuple[Archetype, datetime]] = []
    for index in range(customer_count):
        archetype = rng.choices(ARCHETYPES, weights)[0]
        signup = now - timedelta(
            days=rng.uniform(*archetype.signup_days), minutes=rng.randint(0, 1440)
        )
        first, last = fake.first_name(), fake.last_name()
        customers.append(
            Customer(
                email=f"{first}.{last}.{index}@example.com".lower(),
                phone=f"+1555{index:07d}" if rng.random() < 0.85 else "",
                first_name=first,
                last_name=last,
                timezone=rng.choice(US_TIMEZONES),
                referral_code=generate_referral_code(),
                signed_up_at=signup,
            )
        )
        plans.append((archetype, signup))
    Customer.objects.bulk_create(customers, batch_size=500)

    orders: list[Order] = []
    for customer, (archetype, signup) in zip(customers, plans, strict=True):
        for placed in _order_times(rng, archetype, signup, now):
            cancelled = rng.random() < 0.02
            delivered = placed + timedelta(minutes=rng.randint(35, 180))
            orders.append(
                Order(
                    customer=customer,
                    total=_basket_total(rng),
                    status=Order.Status.CANCELLED if cancelled else Order.Status.DELIVERED,
                    placed_at=placed,
                    delivered_at=None if cancelled or delivered > now else delivered,
                )
            )
    Order.objects.bulk_create(orders, batch_size=1000)
    return SeedResult(customers=len(customers), orders=len(orders))
