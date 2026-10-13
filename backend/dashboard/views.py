from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from dashboard.stats import messages_over_time, overview
from messaging.models import Message

MAX_DAYS = 180
MAX_RECENT = 100


class RecentMessageSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.first_name")
    customer_email = serializers.CharField(source="customer.email")

    class Meta:
        model = Message
        fields = [
            "id",
            "created_at",
            "sent_at",
            "scheduled_for",
            "customer_id",
            "customer_name",
            "customer_email",
            "flow",
            "step",
            "channel",
            "status",
            "block_reason",
            "personalization",
            "subject",
            "body",
        ]


def _bounded_int(request: Request, name: str, default: int, maximum: int) -> int:
    try:
        value = int(request.query_params.get(name, default))
    except ValueError as exc:
        raise ValidationError({name: "Must be an integer."}) from exc
    if not 1 <= value <= maximum:
        raise ValidationError({name: f"Must be between 1 and {maximum}."})
    return value


@api_view(["GET"])
def stats_overview(request: Request) -> Response:
    return Response(overview(timezone.now()))


@api_view(["GET"])
def stats_messages_over_time(request: Request) -> Response:
    days = _bounded_int(request, "days", 30, MAX_DAYS)
    return Response(messages_over_time(timezone.now(), days))


@api_view(["GET"])
def recent_messages(request: Request) -> Response:
    limit = _bounded_int(request, "limit", 20, MAX_RECENT)
    queryset = Message.objects.select_related("customer").order_by("-created_at", "-id")
    status_filter = request.query_params.get("status")
    if status_filter:
        if status_filter not in Message.Status.values:
            raise ValidationError({"status": f"Must be one of {Message.Status.values}."})
        queryset = queryset.filter(status=status_filter)
    return Response(RecentMessageSerializer(queryset[:limit], many=True).data)
