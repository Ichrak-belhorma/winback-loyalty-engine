from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from segments.services import refresh_segments


class Command(BaseCommand):
    help = "Recompute RFM scores, named segments and inactivity flags for all customers."

    def handle(self, *args: Any, **options: Any) -> None:
        counts = refresh_segments(timezone.now())
        for segment, count in sorted(counts.items()):
            self.stdout.write(f"{segment:<12} {count}")
