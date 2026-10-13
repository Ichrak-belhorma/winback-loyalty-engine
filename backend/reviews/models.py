from django.db import models

from customers.models import Customer
from orders.models import Order


class Review(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="reviews")
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField()

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.rating}★ for order {self.order_id}"
