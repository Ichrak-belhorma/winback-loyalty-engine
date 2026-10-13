from django.db import models

from customers.models import Customer


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed"
        DELIVERED = "delivered"
        CANCELLED = "cancelled"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    external_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    placed_at = models.DateTimeField(db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-placed_at"]

    def __str__(self) -> str:
        return f"Order {self.pk} ${self.total} ({self.status})"
