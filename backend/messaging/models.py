from django.db import models

from customers.models import Customer


class Message(models.Model):
    """Every outbound message attempt, including ones the compliance gate blocked."""

    class Channel(models.TextChoices):
        EMAIL = "email"
        SMS = "sms"

    class Status(models.TextChoices):
        PENDING = "pending"
        SENT = "sent"
        DEFERRED = "deferred"
        BLOCKED = "blocked"
        FAILED = "failed"

    class Personalization(models.TextChoices):
        AI = "ai"
        TEMPLATE = "template"

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="messages")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    flow = models.CharField(max_length=32, db_index=True)
    step = models.CharField(max_length=32)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    personalization = models.CharField(
        max_length=10, choices=Personalization.choices, default=Personalization.TEMPLATE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    block_reason = models.CharField(max_length=32, blank=True)
    error = models.TextField(blank=True)
    provider_id = models.CharField(max_length=100, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.flow}/{self.step} to {self.customer_id} [{self.status}]"
