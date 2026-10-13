from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from customers.serializers import SignupSerializer
from customers.services import sign_up


@api_view(["POST"])
def signup(request: Request) -> Response:
    """Create a customer and start the welcome flow (201); an existing email returns 200."""
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    customer, created = sign_up(now=timezone.now(), **serializer.validated_data)
    return Response(
        {"customer_id": customer.pk, "created": created, "referral_code": customer.referral_code},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )
