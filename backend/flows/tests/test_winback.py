from datetime import timedelta

import pytest

from flows.definitions.winback import enroll_candidates
from flows.engine import enroll, process_due_enrollments
from flows.models import FlowEnrollment
from flows.tests.conftest import T0
from segments.services import refresh_segments


@pytest.fixture
def lapsed(make_customer, make_order):
    def _lapsed(days: int = 75, **fields):
        customer = make_customer(**fields)
        make_order(customer, T0 - timedelta(days=days))
        return customer

    return _lapsed


@pytest.mark.django_db
def test_only_lapsed_buyers_are_enrolled(make_customer, make_order, lapsed):
    sixty, ninety = lapsed(60), lapsed(200)
    recent = lapsed(10)
    lapsed(75, unsubscribed=True)
    make_customer(signed_up_at=T0 - timedelta(days=100))  # never ordered
    already = lapsed(80)
    enroll(already, "winback", T0 - timedelta(days=30))
    refresh_segments(T0)

    assert enroll_candidates(T0) == 2
    enrolled = set(FlowEnrollment.objects.filter(enrolled_at=T0).values_list("customer", flat=True))
    assert enrolled == {sixty.pk, ninety.pk}
    assert recent.pk not in enrolled


@pytest.mark.django_db
def test_escalates_reminder_then_offer_then_final_offer(lapsed):
    customer = lapsed()
    enrollment = enroll(customer, "winback", T0)

    for day in (0, 3, 4, 10, 11):
        process_due_enrollments(T0 + timedelta(days=day))

    messages = list(customer.messages.order_by("created_at").values_list("step", "created_at"))
    assert messages == [
        ("reminder", T0),
        ("offer", T0 + timedelta(days=4)),
        ("final_offer", T0 + timedelta(days=11)),
    ]
    assert "10% off" in customer.messages.get(step="offer").body
    assert "20% off" in customer.messages.get(step="final_offer").body
    enrollment.refresh_from_db()
    assert enrollment.status == "completed"


@pytest.mark.django_db
def test_new_order_cancels_win_back_immediately(lapsed, post):
    customer = lapsed()
    enrollment = enroll(customer, "winback", T0)
    process_due_enrollments(T0)

    response = post(
        "/api/webhooks/order-created",
        {
            "event_id": "evt-1",
            "order_id": "ord-1",
            "customer_email": customer.email,
            "total": "42.00",
        },
    )
    process_due_enrollments(T0 + timedelta(days=30))

    enrollment.refresh_from_db()
    assert response.status_code == 201
    assert (enrollment.status, enrollment.cancel_reason) == ("cancelled", "ordered")
    assert list(customer.messages.values_list("step", flat=True)) == ["reminder"]


@pytest.mark.django_db
def test_step_cancels_if_an_order_slipped_in(lapsed, make_order):
    customer = lapsed()
    enrollment = enroll(customer, "winback", T0)
    process_due_enrollments(T0)
    make_order(customer, T0 + timedelta(days=1))  # e.g. imported, bypassing the webhook

    process_due_enrollments(T0 + timedelta(days=4))

    enrollment.refresh_from_db()
    assert (enrollment.status, enrollment.cancel_reason) == ("cancelled", "ordered")
    assert not customer.messages.filter(step="offer").exists()


@pytest.mark.django_db
def test_order_webhook_is_idempotent(lapsed, post):
    customer = lapsed()
    body = {
        "event_id": "evt-9",
        "order_id": "ord-9",
        "customer_email": customer.email,
        "total": "9",
    }

    assert post("/api/webhooks/order-created", body).status_code == 201
    assert post("/api/webhooks/order-created", body).json() == {"duplicate": True}
    assert customer.orders.count() == 2
