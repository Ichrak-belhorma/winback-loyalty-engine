from datetime import timedelta

import pytest

from flows.engine import STEP_ERROR_RETRY_DELAY, enroll, process_due_enrollments
from flows.models import FlowEnrollment
from flows.tests.conftest import T0


@pytest.mark.django_db
def test_unsubscribed_customers_are_never_enrolled(make_customer):
    assert enroll(make_customer(unsubscribed=True), "welcome", T0) is None


@pytest.mark.django_db
def test_only_one_active_enrollment_per_flow_key(make_customer):
    customer = make_customer()

    assert enroll(customer, "winback", T0) is not None
    assert enroll(customer, "winback", T0) is None
    assert enroll(customer, "review", T0, key="review:1", context={"order_id": 1}) is not None
    assert enroll(customer, "review", T0, key="review:2", context={"order_id": 2}) is not None


@pytest.mark.django_db
def test_only_due_enrollments_run(make_customer):
    due = enroll(make_customer(), "welcome", T0)
    enroll(make_customer(), "welcome", T0, start_at=T0 + timedelta(hours=1))

    assert process_due_enrollments(T0).processed == 1
    due.refresh_from_db()
    assert due.step == "first_order_nudge"


@pytest.mark.django_db
def test_failing_step_is_retried_later_not_lost(make_customer, monkeypatch):
    enrollment = enroll(make_customer(), "welcome", T0)

    def boom(*args, **kwargs):
        raise RuntimeError("provider exploded")

    monkeypatch.setattr("flows.definitions.welcome.send_step", boom)

    result = process_due_enrollments(T0)

    enrollment.refresh_from_db()
    assert (result.processed, result.errors) == (0, 1)
    assert enrollment.status == FlowEnrollment.Status.ACTIVE
    assert enrollment.step == "welcome"
    assert enrollment.next_run_at == T0 + STEP_ERROR_RETRY_DELAY
    assert not enrollment.customer.messages.exists()
