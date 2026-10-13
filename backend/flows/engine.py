"""Flow engine: enrollments are DB-backed state machines advanced by `process_due_enrollments`."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db import IntegrityError, transaction

from customers.models import Customer
from flows.models import FlowEnrollment
from flows.registry import FLOWS
from flows.steps import Advance, Cancel, Complete, StepResult

logger = logging.getLogger(__name__)

STEP_ERROR_RETRY_DELAY = timedelta(minutes=15)
Status = FlowEnrollment.Status


def enroll(
    customer: Customer,
    flow: str,
    now: datetime,
    *,
    key: str | None = None,
    context: dict[str, Any] | None = None,
    start_at: datetime | None = None,
) -> FlowEnrollment | None:
    """Start `flow` for the customer; None if unsubscribed or already active for this key."""
    if customer.unsubscribed:
        return None
    try:
        with transaction.atomic():
            return FlowEnrollment.objects.create(
                customer=customer,
                flow=flow,
                key=key or flow,
                step=FLOWS[flow].first_step,
                next_run_at=start_at or now,
                context=context or {},
                enrolled_at=now,
            )
    except IntegrityError:
        return None


def cancel_active(customer: Customer, flow: str, reason: str, now: datetime) -> int:
    return FlowEnrollment.objects.filter(customer=customer, flow=flow, status=Status.ACTIVE).update(
        status=Status.CANCELLED, cancel_reason=reason, next_run_at=None, finished_at=now
    )


def _apply(enrollment: FlowEnrollment, result: StepResult, now: datetime) -> None:
    if isinstance(result, Advance):
        enrollment.step, enrollment.next_run_at = result.step, now + result.delay
    elif isinstance(result, Complete):
        enrollment.status, enrollment.next_run_at, enrollment.finished_at = (
            Status.COMPLETED,
            None,
            now,
        )
    elif isinstance(result, Cancel):
        enrollment.status, enrollment.cancel_reason = Status.CANCELLED, result.reason
        enrollment.next_run_at, enrollment.finished_at = None, now
    enrollment.save()


def run_step(enrollment: FlowEnrollment, now: datetime) -> StepResult:
    handler = FLOWS[enrollment.flow].handlers[enrollment.step]
    result = handler(enrollment, now)
    _apply(enrollment, result, now)
    return result


@dataclass
class ProcessResult:
    processed: int = 0
    errors: int = 0


def process_due_enrollments(now: datetime) -> ProcessResult:
    """Run the current step of every active enrollment that is due.

    Each enrollment is locked with SKIP LOCKED, so overlapping runs (beat and n8n, or two
    workers) never execute the same step twice. A step that raises is retried later rather
    than lost.
    """
    result = ProcessResult()
    due_ids = list(
        FlowEnrollment.objects.filter(status=Status.ACTIVE, next_run_at__lte=now)
        .order_by("next_run_at", "id")
        .values_list("id", flat=True)
    )
    for enrollment_id in due_ids:
        with transaction.atomic():
            enrollment = (
                FlowEnrollment.objects.select_for_update(skip_locked=True)
                .select_related("customer")
                .filter(pk=enrollment_id, status=Status.ACTIVE, next_run_at__lte=now)
                .first()
            )
            if enrollment is None:
                continue
            try:
                with transaction.atomic():
                    run_step(enrollment, now)
            except Exception:
                logger.exception("Flow step %s/%s failed", enrollment.flow, enrollment.step)
                FlowEnrollment.objects.filter(pk=enrollment_id).update(
                    next_run_at=now + STEP_ERROR_RETRY_DELAY
                )
                result.errors += 1
                continue
            result.processed += 1
    return result
