from datetime import timedelta

import pytest
from freezegun import freeze_time

from customers.models import Customer
from flows.engine import process_due_enrollments
from flows.tests.conftest import T0


def signup(post, email: str = "new@example.com"):
    with freeze_time(T0):
        return post("/api/customers", {"email": email, "first_name": "Nia", "phone": "5550004444"})


@pytest.mark.django_db
def test_signup_sends_welcome_then_nudges_after_two_days(post):
    assert signup(post).status_code == 201
    customer = Customer.objects.get()

    process_due_enrollments(T0)
    process_due_enrollments(T0 + timedelta(days=2) - timedelta(minutes=1))
    assert list(customer.messages.values_list("step", flat=True)) == ["welcome"]

    process_due_enrollments(T0 + timedelta(days=2))
    nudge = customer.messages.get(step="first_order_nudge")
    assert "10% off" in nudge.body
    assert customer.enrollments.get().status == "completed"


@pytest.mark.django_db
def test_nudge_is_skipped_when_customer_already_ordered(post, make_order):
    signup(post)
    customer = Customer.objects.get()
    process_due_enrollments(T0)
    make_order(customer, T0 + timedelta(hours=5))

    process_due_enrollments(T0 + timedelta(days=2))

    assert not customer.messages.filter(step="first_order_nudge").exists()
    assert customer.enrollments.get().status == "completed"


@pytest.mark.django_db
def test_repeat_signup_does_not_re_enroll(post):
    signup(post)
    response = signup(post)

    assert response.status_code == 200
    assert response.json()["created"] is False
    assert Customer.objects.get().enrollments.count() == 1
