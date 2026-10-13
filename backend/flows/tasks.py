from celery import shared_task
from django.utils import timezone

from flows.engine import process_due_enrollments
from flows.lifecycle import daily_refresh


@shared_task
def process_due_enrollments_task() -> dict[str, int]:
    result = process_due_enrollments(timezone.now())
    return {"processed": result.processed, "errors": result.errors}


@shared_task
def daily_refresh_task() -> dict[str, object]:
    return daily_refresh(timezone.now())
