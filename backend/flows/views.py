from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from flows.engine import process_due_enrollments
from flows.lifecycle import daily_refresh


@api_view(["POST"])
def process_due(request: Request) -> Response:
    """Trigger for external schedulers (n8n); same job Celery beat runs every minute."""
    result = process_due_enrollments(timezone.now())
    return Response({"processed": result.processed, "errors": result.errors})


@api_view(["POST"])
def refresh(request: Request) -> Response:
    """Recompute segments and enroll newly lapsed customers (the daily beat job, on demand)."""
    return Response(daily_refresh(timezone.now()))
