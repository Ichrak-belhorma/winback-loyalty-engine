from django.db import models

from customers.models import Customer


class CustomerRFM(models.Model):
    """Latest RFM snapshot for a customer, recomputed by the segment refresh job."""

    class Segment(models.TextChoices):
        CHAMPIONS = "champions", "Champions"
        LOYAL = "loyal", "Loyal"
        AT_RISK = "at_risk", "At Risk"
        HIBERNATING = "hibernating", "Hibernating"
        NEW = "new", "New"

    class Inactivity(models.TextChoices):
        ACTIVE = "active"
        INACTIVE_30 = "inactive_30"
        INACTIVE_60 = "inactive_60"
        INACTIVE_90 = "inactive_90"

    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="rfm")
    recency_days = models.PositiveIntegerField(null=True, blank=True)
    frequency = models.PositiveIntegerField(default=0)
    monetary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    r_score = models.PositiveSmallIntegerField(null=True, blank=True)
    f_score = models.PositiveSmallIntegerField(null=True, blank=True)
    m_score = models.PositiveSmallIntegerField(null=True, blank=True)
    segment = models.CharField(max_length=16, choices=Segment.choices, db_index=True)
    inactivity = models.CharField(max_length=16, choices=Inactivity.choices, db_index=True)
    computed_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"{self.customer_id} {self.segment} R{self.r_score}F{self.f_score}M{self.m_score}"
