from celery import shared_task
from django.utils import timezone

from compliance.gate import dispatch_deferred


@shared_task
def dispatch_deferred_task() -> int:
    return dispatch_deferred(timezone.now())
