import re
from datetime import datetime

from django.db import transaction

from customers.models import Customer
from flows.models import FlowEnrollment
from messaging.models import Message

STOP_KEYWORDS = frozenset(
    {"stop", "stop all", "stopall", "unsubscribe", "unsub", "cancel", "end", "quit"}
)
_PUNCTUATION = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def is_stop_request(text: str) -> bool:
    """Whole-message keyword match, case- and punctuation-insensitive ("Stop!" counts)."""
    normalized = _SPACES.sub(" ", _PUNCTUATION.sub("", text.lower())).strip()
    return normalized in STOP_KEYWORDS


@transaction.atomic
def unsubscribe(customer: Customer, now: datetime) -> int:
    """Opt the customer out everywhere; returns the number of enrollments cancelled."""
    customer.unsubscribed, customer.unsubscribed_at = True, now
    customer.save(update_fields=["unsubscribed", "unsubscribed_at"])
    Message.objects.filter(customer=customer, status=Message.Status.DEFERRED).update(
        status=Message.Status.BLOCKED, block_reason="unsubscribed"
    )
    return FlowEnrollment.objects.filter(
        customer=customer, status=FlowEnrollment.Status.ACTIVE
    ).update(
        status=FlowEnrollment.Status.CANCELLED,
        cancel_reason="unsubscribed",
        next_run_at=None,
        finished_at=now,
    )
