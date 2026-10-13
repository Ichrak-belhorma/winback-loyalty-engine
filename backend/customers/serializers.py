from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, default="")
    phone = serializers.CharField(max_length=32, required=False, default="")
    timezone = serializers.CharField(max_length=64, required=False, default="")

    def validate_timezone(self, value: str) -> str:
        if value:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise serializers.ValidationError("Unknown IANA timezone.") from exc
        return value
