from django.db import models


class WebhookEvent(models.Model):
    """Inbound webhook event ids already processed, so redeliveries are no-ops."""

    event_id = models.CharField(max_length=128)
    kind = models.CharField(max_length=32)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kind", "event_id"], name="unique_event_per_kind")
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.event_id}"
