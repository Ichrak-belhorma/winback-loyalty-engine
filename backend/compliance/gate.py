"""The single path for every outbound message.

Checks run in a fixed order: unsubscribed → quiet hours (deferred, not dropped) → weekly
cap → send. Every attempt is stored as a `Message` with its outcome, so blocked sends are
auditable. Deferred messages are re-checked against all rules when they come due.
"""

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from compliance.quiet_hours import in_quiet_hours, next_send_window
from customers.models import Customer
from messaging.models import Message
from messaging.senders import OutboundMessage, get_sender

logger = logging.getLogger(__name__)

Status = Message.Status


class BlockReason:
    UNSUBSCRIBED = "unsubscribed"
    QUIET_HOURS = "quiet_hours"
    WEEKLY_CAP = "weekly_cap"


def preferred_channel(customer: Customer) -> str:
    return Message.Channel.SMS if customer.phone else Message.Channel.EMAIL


def send_message(
    customer: Customer,
    *,
    flow: str,
    step: str,
    body: str,
    subject: str = "",
    personalization: str = Message.Personalization.TEMPLATE,
    now: datetime | None = None,
) -> Message:
    now = now or timezone.now()
    channel = preferred_channel(customer)
    if channel == Message.Channel.SMS and "STOP" not in body:
        body = f"{body} {settings.SMS_OPT_OUT_FOOTER}"
    message = Message.objects.create(
        customer=customer,
        channel=channel,
        flow=flow,
        step=step,
        subject=subject,
        body=body,
        personalization=personalization,
        created_at=now,
    )
    return deliver(message, now)


def deliver(message: Message, now: datetime) -> Message:
    """Apply the compliance rules to a pending or deferred message and send it if allowed."""
    with transaction.atomic():
        # Lock the customer so concurrent sends can't both slip under the weekly cap.
        customer = Customer.objects.select_for_update().get(pk=message.customer_id)
        if customer.unsubscribed:
            return _finish(message, Status.BLOCKED, BlockReason.UNSUBSCRIBED)
        if in_quiet_hours(now, customer.timezone):
            message.scheduled_for = next_send_window(now, customer.timezone)
            return _finish(message, Status.DEFERRED, BlockReason.QUIET_HOURS)
        sent_this_week = Message.objects.filter(
            customer=customer, status=Status.SENT, sent_at__gt=now - timedelta(days=7)
        ).count()
        if sent_this_week >= settings.WEEKLY_MESSAGE_CAP:
            return _finish(message, Status.BLOCKED, BlockReason.WEEKLY_CAP)

        to = customer.phone if message.channel == Message.Channel.SMS else customer.email
        try:
            result = get_sender(message.channel).send(
                OutboundMessage(message.channel, to, message.subject, message.body)
            )
        except Exception as exc:
            message.error = f"{type(exc).__name__}: {exc}"
            return _finish(message, Status.FAILED, "")
        message.provider_id, message.sent_at = result.provider_id, now
        return _finish(message, Status.SENT, "")


def _finish(message: Message, status: str, reason: str) -> Message:
    message.status, message.block_reason = status, reason
    message.save()
    if status != Status.SENT:
        logger.info(
            "Message %s (%s/%s) for customer %s: %s %s",
            message.pk,
            message.flow,
            message.step,
            message.customer_id,
            status,
            reason or message.error,
        )
    return message


def dispatch_deferred(now: datetime) -> int:
    """Re-gate deferred messages whose send window has opened; returns how many were due."""
    due = list(
        Message.objects.filter(status=Status.DEFERRED, scheduled_for__lte=now).order_by("id")
    )
    for message in due:
        deliver(message, now)
    return len(due)
