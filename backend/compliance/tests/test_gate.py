from datetime import UTC, datetime, timedelta

import pytest

from compliance.gate import dispatch_deferred, send_message
from compliance.quiet_hours import next_send_window
from messaging.models import Message

# 16:00 UTC = 12:00 in New York (EDT): outside quiet hours.
DAYTIME = datetime(2026, 6, 10, 16, 0, tzinfo=UTC)
# 02:00 UTC = 22:00 in New York (EDT) but 19:00 in Los Angeles (PDT).
NY_NIGHT = datetime(2026, 6, 11, 2, 0, tzinfo=UTC)


def send(customer, now, **kwargs) -> Message:
    return send_message(customer, flow="winback", step="reminder", body="Hi!", now=now, **kwargs)


def fill_weekly_cap(customer, now, count: int = 3) -> None:
    for i in range(count):
        send(customer, now - timedelta(days=i + 1))


@pytest.mark.django_db
def test_allowed_sms_is_sent_with_opt_out_footer(make_customer):
    message = send(make_customer(), DAYTIME)

    assert message.status == Message.Status.SENT
    assert message.channel == "sms"
    assert message.provider_id.startswith("console-")
    assert message.body.endswith("Reply STOP to opt out.")


@pytest.mark.django_db
def test_customer_without_phone_gets_email_without_sms_footer(make_customer):
    message = send(make_customer(phone=""), DAYTIME)

    assert (message.channel, message.body) == ("email", "Hi!")


@pytest.mark.django_db
def test_unsubscribed_is_checked_first(make_customer):
    customer = make_customer()
    fill_weekly_cap(customer, NY_NIGHT)
    customer.unsubscribed = True
    customer.save()

    message = send(customer, NY_NIGHT)  # also quiet hours and over the cap

    assert (message.status, message.block_reason) == ("blocked", "unsubscribed")


@pytest.mark.django_db
def test_quiet_hours_are_checked_before_the_cap(make_customer):
    customer = make_customer()
    fill_weekly_cap(customer, NY_NIGHT)

    message = send(customer, NY_NIGHT)

    assert (message.status, message.block_reason) == ("deferred", "quiet_hours")


@pytest.mark.django_db
def test_quiet_hours_use_customer_local_time(make_customer):
    new_york = send(make_customer(timezone="America/New_York"), NY_NIGHT)
    los_angeles = send(make_customer(timezone="America/Los_Angeles"), NY_NIGHT)

    assert new_york.status == "deferred"
    assert new_york.scheduled_for == datetime(2026, 6, 11, 12, 0, tzinfo=UTC)  # 08:00 EDT
    assert los_angeles.status == "sent"


def test_early_morning_defers_to_same_day_and_bad_timezone_falls_back():
    four_am_ny = datetime(2026, 6, 11, 8, 0, tzinfo=UTC)

    assert next_send_window(four_am_ny, "America/New_York") == datetime(
        2026, 6, 11, 12, 0, tzinfo=UTC
    )
    assert next_send_window(four_am_ny, "Mars/Olympus") == next_send_window(
        four_am_ny, "America/New_York"
    )


@pytest.mark.django_db
def test_deferred_message_is_sent_when_window_opens(make_customer):
    message = send(make_customer(), NY_NIGHT)

    assert dispatch_deferred(message.scheduled_for - timedelta(minutes=1)) == 0
    assert dispatch_deferred(message.scheduled_for) == 1
    message.refresh_from_db()
    assert message.status == "sent"
    assert message.sent_at == message.scheduled_for


@pytest.mark.django_db
def test_deferred_message_is_rechecked_against_unsubscribe(make_customer):
    customer = make_customer()
    message = send(customer, NY_NIGHT)
    customer.unsubscribed = True
    customer.save()

    dispatch_deferred(message.scheduled_for)

    message.refresh_from_db()
    assert (message.status, message.block_reason) == ("blocked", "unsubscribed")


@pytest.mark.django_db
def test_weekly_cap_blocks_the_fourth_send_in_seven_days(make_customer):
    customer = make_customer()
    fill_weekly_cap(customer, DAYTIME)

    message = send(customer, DAYTIME)

    assert (message.status, message.block_reason) == ("blocked", "weekly_cap")


@pytest.mark.django_db
def test_weekly_cap_is_a_rolling_window(make_customer):
    customer = make_customer()
    send(customer, DAYTIME - timedelta(days=7, minutes=1))  # just outside the window
    send(customer, DAYTIME - timedelta(days=2))
    send(customer, DAYTIME - timedelta(days=1))

    assert send(customer, DAYTIME).status == "sent"


@pytest.mark.django_db
def test_blocked_and_deferred_sends_do_not_count_toward_the_cap(make_customer):
    customer = make_customer()
    send(customer, NY_NIGHT)  # deferred
    fill_weekly_cap(customer, DAYTIME, count=2)

    assert send(customer, DAYTIME).status == "sent"


@pytest.mark.django_db
def test_provider_error_is_recorded_as_failed(make_customer, monkeypatch):
    class Down:
        def send(self, message):
            raise ConnectionError("twilio unavailable")

    monkeypatch.setattr("compliance.gate.get_sender", lambda channel: Down())

    message = send(make_customer(), DAYTIME)

    assert message.status == "failed"
    assert "twilio unavailable" in message.error
