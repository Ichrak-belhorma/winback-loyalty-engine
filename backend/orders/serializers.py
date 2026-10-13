from rest_framework import serializers


class OrderCreatedSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=128)
    order_id = serializers.CharField(max_length=64)
    customer_email = serializers.EmailField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    placed_at = serializers.DateTimeField(required=False)
