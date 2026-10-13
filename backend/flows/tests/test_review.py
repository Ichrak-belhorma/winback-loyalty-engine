from datetime import timedelta

import pytest
from freezegun import freeze_time

from flows.engine import process_due_enrollments
from flows.tests.conftest import T0


@pytest.fixture
def delivered(make_customer, make_order, post):
    customer = make_customer(first_name="Rae")
    order = make_order(customer, T0 - timedelta(hours=1), external_id="ext-7", status="placed")
    with freeze_time(T0):
        response = post(
            "/api/webhooks/delivery-completed", {"event_id": "d-1", "order_id": "ext-7"}
        )
    assert response.status_code == 200
    return order


def review(post, order_id: int, rating: int):
    with freeze_time(T0 + timedelta(hours=4)):
        return post("/api/reviews", {"order_id": order_id, "rating": rating})


@pytest.mark.django_db
def test_review_request_goes_out_three_hours_after_delivery(delivered):
    process_due_enrollments(T0 + timedelta(hours=2, minutes=59))
    assert not delivered.customer.messages.exists()

    process_due_enrollments(T0 + timedelta(hours=3))

    request = delivered.customer.messages.get()
    assert request.step == "request"
    assert f"/review/{delivered.pk}" in request.body
    delivered.refresh_from_db()
    assert delivered.status == "delivered"


@pytest.mark.django_db
def test_high_rating_gets_public_review_link(delivered, post):
    response = review(post, delivered.pk, 5)

    message = delivered.customer.messages.get()
    assert response.json()["routed_to"] == "public"
    assert message.step == "public_thanks"
    assert "reviews.example.com" in message.body
    assert "needs_followup" not in delivered.customer.tags


@pytest.mark.django_db
@pytest.mark.parametrize("rating", [1, 3])
def test_low_rating_gets_private_fix_it_and_followup_tag(delivered, post, rating: int):
    response = review(post, delivered.pk, rating)

    delivered.customer.refresh_from_db()
    assert response.json()["routed_to"] == "private"
    assert delivered.customer.messages.get().step == "fix_it"
    assert delivered.customer.tags == ["needs_followup"]


@pytest.mark.django_db
def test_request_is_skipped_if_already_reviewed_and_reviews_are_one_per_order(delivered, post):
    review(post, delivered.pk, 4)

    process_due_enrollments(T0 + timedelta(hours=3))

    assert not delivered.customer.messages.filter(step="request").exists()
    assert review(post, delivered.pk, 1).status_code == 409


@pytest.mark.django_db
def test_delivery_webhook_is_idempotent(delivered, post):
    with freeze_time(T0):
        response = post(
            "/api/webhooks/delivery-completed", {"event_id": "d-1", "order_id": "ext-7"}
        )

    assert response.json() == {"duplicate": True}
    assert delivered.customer.enrollments.count() == 1
