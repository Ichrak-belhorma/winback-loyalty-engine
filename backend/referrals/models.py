from django.db import models

from customers.models import Customer


class Referral(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        REWARDED = "rewarded"

    referrer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="referrals_made")
    # A customer can only ever be referred once.
    referee = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="referred_by")
    code = models.CharField(max_length=16)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    referee_discount_percent = models.PositiveSmallIntegerField()
    referrer_reward_percent = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField()
    rewarded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.referrer_id} referred {self.referee_id} [{self.status}]"
