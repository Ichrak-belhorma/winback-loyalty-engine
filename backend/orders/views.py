from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from compliance.idempotency import first_delivery
from customers.models import Customer
from orders.models import Order
from orders.serializers import OrderCreatedSerializer
from orders.services import record_order


@api_view(["POST"])
def order_created(request: Request) -> Response:
    serializer = OrderCreatedSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    customer = Customer.objects.filter(email=data["customer_email"].lower()).first()
    if customer is None:
        return Response({"detail": "Unknown customer."}, status=status.HTTP_404_NOT_FOUND)
    if (
        not first_delivery("order_created", data["event_id"])
        or Order.objects.filter(external_id=data["order_id"]).exists()
    ):
        return Response({"duplicate": True})
    now = timezone.now()
    order = record_order(
        customer, data["order_id"], data["total"], data.get("placed_at") or now, now
    )
    return Response({"duplicate": False, "order_id": order.pk}, status=status.HTTP_201_CREATED)
