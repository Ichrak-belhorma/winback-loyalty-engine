from django.db import IntegrityError, transaction

from compliance.models import WebhookEvent


def first_delivery(kind: str, event_id: str) -> bool:
    """Record the event; False if this (kind, event_id) was already processed."""
    try:
        with transaction.atomic():
            WebhookEvent.objects.create(kind=kind, event_id=event_id)
    except IntegrityError:
        return False
    return True
