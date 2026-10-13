from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from orders.models import Order
from segments.models import CustomerRFM
from segments.rfm import classify, inactivity_flag, quintile_scores
from segments.services import refresh_segments

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.get_current_timezone())


def test_distinct_values_spread_across_all_quintiles():
    assert quintile_scores([10, 20, 30, 40, 50]) == [1, 2, 3, 4, 5]
    assert quintile_scores(list(range(10))) == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


@pytest.mark.parametrize("values", [[7], [7, 7, 7, 7]], ids=["single", "all-equal"])
def test_no_spread_lands_in_the_middle(values: list[int]):
    assert set(quintile_scores(values)) == {3}


def test_ties_share_a_score_and_order_is_preserved():
    scores = quintile_scores([1, 1, 1, 1, 9, 9, 50])

    assert scores[0] == scores[1] == scores[2] == scores[3]
    assert scores[4] == scores[5]
    assert scores[0] < scores[4] < scores[6]


@pytest.mark.parametrize(
    ("days", "flag"),
    [
        (0, "active"),
        (29, "active"),
        (30, "inactive_30"),
        (59, "inactive_30"),
        (60, "inactive_60"),
        (89, "inactive_60"),
        (90, "inactive_90"),
        (400, "inactive_90"),
    ],
)
def test_inactivity_boundaries(days: int, flag: str):
    assert inactivity_flag(days) == flag


@pytest.mark.parametrize(
    ("r", "f", "frequency", "age_days", "segment"),
    [
        (None, None, 0, 5, "new"),
        (None, None, 0, 31, "hibernating"),
        (5, 1, 1, 10, "new"),
        (5, 5, 12, 300, "champions"),
        (4, 4, 6, 300, "champions"),
        (3, 3, 4, 300, "loyal"),
        (1, 5, 9, 300, "at_risk"),
        (2, 3, 4, 300, "at_risk"),
        (4, 1, 1, 300, "loyal"),
        (1, 1, 1, 300, "hibernating"),
    ],
)
def test_segment_rules(r, f, frequency, age_days, segment):
    assert classify(r, f, frequency, age_days) == segment


@pytest.mark.django_db
@freeze_time(NOW)
def test_refresh_uses_exact_day_boundaries_and_ignores_cancelled_and_future_orders(
    make_customer, make_order
):
    customer = make_customer()
    make_order(customer, NOW - timedelta(days=120))
    make_order(customer, NOW - timedelta(days=30))  # last real order: exactly 30 days ago
    make_order(customer, NOW - timedelta(days=2), status=Order.Status.CANCELLED)
    make_order(customer, NOW + timedelta(days=1))

    refresh_segments(timezone.now())

    rfm = CustomerRFM.objects.get(customer=customer)
    assert rfm.recency_days == 30
    assert rfm.frequency == 2
    assert float(rfm.monetary) == 60.0
    assert rfm.inactivity == "inactive_30"


@pytest.mark.django_db
@freeze_time(NOW)
def test_customer_without_orders_is_flagged_by_signup_age(make_customer):
    fresh = make_customer(signed_up_at=NOW - timedelta(days=3))
    stale = make_customer(signed_up_at=NOW - timedelta(days=95))

    refresh_segments(timezone.now())

    assert CustomerRFM.objects.get(customer=fresh).segment == "new"
    stale_rfm = CustomerRFM.objects.get(customer=stale)
    assert (stale_rfm.segment, stale_rfm.inactivity, stale_rfm.r_score) == (
        "hibernating",
        "inactive_90",
        None,
    )


@pytest.mark.django_db
@freeze_time(NOW)
def test_refresh_is_an_upsert(make_customer, make_order):
    customer = make_customer()
    make_order(customer, NOW - timedelta(days=10))
    refresh_segments(timezone.now())

    make_order(customer, NOW - timedelta(days=1))
    refresh_segments(timezone.now())

    assert CustomerRFM.objects.count() == 1
    assert CustomerRFM.objects.get().frequency == 2
