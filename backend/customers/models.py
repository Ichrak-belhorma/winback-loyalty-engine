import secrets

from django.db import models
from django.utils import timezone as dj_timezone

REFERRAL_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_referral_code() -> str:
    return "".join(secrets.choice(REFERRAL_CODE_ALPHABET) for _ in range(8))


class Customer(models.Model):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=32, blank=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=64, default="America/New_York")
    unsubscribed = models.BooleanField(default=False)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    referral_code = models.CharField(max_length=16, unique=True, default=generate_referral_code)
    tags = models.JSONField(default=list, blank=True)
    signed_up_at = models.DateTimeField(default=dj_timezone.now)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>".strip()

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags = [*self.tags, tag]
            self.save(update_fields=["tags"])
