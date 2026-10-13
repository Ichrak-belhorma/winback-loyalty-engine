from django.db import models

from customers.models import Customer


class FlowEnrollment(models.Model):
    """A customer's position in one lifecycle flow, advanced by the flow engine."""

    class Status(models.TextChoices):
        ACTIVE = "active"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="enrollments")
    flow = models.CharField(max_length=32, db_index=True)
    # Distinguishes parallel enrollments in one flow, e.g. "review:order-42"; else the flow name.
    key = models.CharField(max_length=64)
    step = models.CharField(max_length=32)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    context = models.JSONField(default=dict, blank=True)
    cancel_reason = models.CharField(max_length=32, blank=True)
    enrolled_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-enrolled_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "key"],
                condition=models.Q(status="active"),
                name="one_active_enrollment_per_key",
            )
        ]

    def __str__(self) -> str:
        return f"{self.flow}:{self.step} for {self.customer_id} [{self.status}]"
