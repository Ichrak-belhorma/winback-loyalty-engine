from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from compliance.idempotency import first_delivery
from orders.models import Order
from reviews.services import (
    POSITIVE_MIN_RATING,
    DuplicateReview,
    schedule_review_request,
    submit_review,
)


class DeliveryCompletedSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=128)
    order_id = serializers.CharField(max_length=64, help_text="external order id")
    delivered_at = serializers.DateTimeField(required=False)


class ReviewSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, default="", allow_blank=True)


@api_view(["POST"])
def delivery_completed(request: Request) -> Response:
    serializer = DeliveryCompletedSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    order = Order.objects.filter(external_id=data["order_id"]).select_related("customer").first()
    if order is None:
        return Response({"detail": "Unknown order."}, status=status.HTTP_404_NOT_FOUND)
    if not first_delivery("delivery_completed", data["event_id"]):
        return Response({"duplicate": True})
    now = timezone.now()
    enrollment = schedule_review_request(order, data.get("delivered_at") or now, now)
    return Response(
        {
            "duplicate": False,
            "review_request_at": enrollment.next_run_at if enrollment else None,
        }
    )


@api_view(["POST"])
def create_review(request: Request) -> Response:
    serializer = ReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    order = Order.objects.filter(pk=data["order_id"]).select_related("customer").first()
    if order is None:
        return Response({"detail": "Unknown order."}, status=status.HTTP_404_NOT_FOUND)
    try:
        review = submit_review(order, data["rating"], data["comment"], timezone.now())
    except DuplicateReview:
        return Response(
            {"detail": "This order has already been reviewed."}, status=status.HTTP_409_CONFLICT
        )
    return Response(
        {
            "review_id": review.pk,
            "routed_to": "public" if review.rating >= POSITIVE_MIN_RATING else "private",
        },
        status=status.HTTP_201_CREATED,
    )
