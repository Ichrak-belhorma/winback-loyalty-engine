from datetime import UTC, datetime

import pytest
from django.test import Client
from django.utils import timezone

from compliance.unsubscribe import is_stop_request
from flows.models import FlowEnrollment
from messaging.models import Message

URL = "/api/webhooks/inbound-sms"


@pytest.fixture
def api() -> Client:
    return Client(HTTP_HOST="localhost")


@pytest.mark.parametrize(
    "text", ["STOP", "stop", " Stop! ", "UNSUBSCRIBE", "Unsub", "stop all", "STOP ALL", "Quit"]
)
def test_stop_keywords_match_case_insensitively(text: str):
    assert is_stop_request(text)


@pytest.mark.parametrize("text", ["stop sending pizza ads", "don't stop", "hello", ""])
def test_ordinary_replies_are_not_opt_outs(text: str):
    assert not is_stop_request(text)


def twilio_post(api: Client, sid: str, sender: str, body: str):
    return api.post(URL, {"MessageSid": sid, "From": sender, "Body": body})


@pytest.mark.django_db
def test_stop_unsubscribes_and_cancels_enrollments_and_deferred_messages(api, make_customer):
    customer = make_customer(phone="+15550009999")
    now = timezone.now()
    for flow in ("winback", "welcome"):
        FlowEnrollment.objects.create(
            customer=customer, flow=flow, key=flow, step="reminder", enrolled_at=now
        )
    Message.objects.create(
        customer=customer,
        channel="sms",
        flow="winback",
        step="reminder",
        body="later",
        status="deferred",
        created_at=now,
        scheduled_for=datetime(2030, 1, 1, tzinfo=UTC),
    )

    body = twilio_post(api, "SM100", "+1 (555) 000-9999", "Stop").json()

    customer.refresh_from_db()
    assert body["unsubscribed"] is True
    assert body["enrollments_cancelled"] == 2
    assert customer.unsubscribed and customer.unsubscribed_at
    assert set(customer.enrollments.values_list("status", "cancel_reason")) == {
        ("cancelled", "unsubscribed")
    }
    assert customer.messages.get().status == "blocked"


@pytest.mark.django_db
def test_redelivered_event_is_not_processed_twice(api, make_customer):
    customer = make_customer(phone="+15550008888")
    twilio_post(api, "SM200", "+15550008888", "hello")

    response = twilio_post(api, "SM200", "+15550008888", "STOP")

    customer.refresh_from_db()
    assert response.json() == {"duplicate": True}
    assert customer.unsubscribed is False


@pytest.mark.django_db
def test_unknown_number_is_acknowledged(api):
    assert twilio_post(api, "SM300", "+15559990000", "STOP").json() == {
        "duplicate": False,
        "matched": False,
    }


@pytest.mark.django_db
def test_missing_event_id_is_rejected(api):
    assert api.post(URL, {"From": "+15550001111", "Body": "STOP"}).status_code == 400
