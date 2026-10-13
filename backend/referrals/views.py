from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from referrals.services import ReferralError, redeem


class RedeemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)


@api_view(["POST"])
def redeem_referral(request: Request) -> Response:
    serializer = RedeemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        referral = redeem(now=timezone.now(), **serializer.validated_data)
    except ReferralError as exc:
        return Response({"detail": exc.detail}, status=exc.status)
    return Response(
        {
            "referral_id": referral.pk,
            "customer_id": referral.referee_id,
            "discount_percent": referral.referee_discount_percent,
        },
        status=status.HTTP_201_CREATED,
    )
