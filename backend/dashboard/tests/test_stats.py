from datetime import UTC, datetime, timedelta

import pytest
from django.test import Client
from freezegun import freeze_time

from flows.engine import enroll
from messaging.models import Message
from segments.services import refresh_segments

NOW = datetime(2026, 6, 10, 16, 0, tzinfo=UTC)


@pytest.fixture
def api() -> Client:
    return Client(HTTP_HOST="localhost")


@pytest.mark.django_db
def test_reactivation_counts_orders_inside_the_window_only(api, make_customer, make_order):
    back_in_time, too_late, never = make_customer(), make_customer(), make_customer()
    for customer in (back_in_time, too_late, never):
        enroll(customer, "winback", NOW - timedelta(days=30))
    make_order(back_in_time, NOW - timedelta(days=30) + timedelta(days=14))  # last day counts
    make_order(too_late, NOW - timedelta(days=30) + timedelta(days=15))

    reactivation = api.get("/api/stats/overview").json()["reactivation"]

    assert reactivation["window_days"] == 14
    assert (reactivation["enrolled"], reactivation["reactivated"]) == (3, 1)
    assert reactivation["rate"] == pytest.approx(1 / 3, abs=1e-4)


@pytest.mark.django_db
def test_overview_counts_segments_and_messages_by_flow_and_block_reason(
    api, make_customer, make_order
):
    customer = make_customer()
    make_order(customer, NOW - timedelta(days=100))
    refresh_segments(NOW)
    for status, reason in [("sent", ""), ("blocked", "weekly_cap"), ("blocked", "unsubscribed")]:
        Message.objects.create(
            customer=customer,
            channel="sms",
            flow="winback",
            step="reminder",
            body="x",
            status=status,
            block_reason=reason,
            created_at=NOW,
            sent_at=NOW if status == "sent" else None,
        )

    body = api.get("/api/stats/overview").json()

    assert sum(s["count"] for s in body["segments"]) == 1
    assert body["inactivity"]["inactive_90"] == 1
    winback = next(f for f in body["messages"]["by_flow"] if f["flow"] == "winback")
    assert (winback["sent"], winback["blocked"]) == (1, 2)
    assert body["messages"]["blocked_by_reason"] == {"weekly_cap": 1, "unsubscribed": 1}


@pytest.mark.django_db
@freeze_time(NOW)
def test_messages_over_time_is_zero_filled(api, make_customer):
    customer = make_customer()
    Message.objects.create(
        customer=customer,
        channel="sms",
        flow="review",
        step="request",
        body="x",
        status="sent",
        created_at=NOW,
        sent_at=NOW,
    )

    series = api.get("/api/stats/messages-over-time?days=7").json()

    assert len(series) == 7
    assert sum(point["total"] for point in series) == 1
    assert api.get("/api/stats/messages-over-time?days=999").status_code == 400
