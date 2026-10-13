from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from customers.models import Customer
from customers.seed import seed_demo_data
from flows.simulation import simulate_activity
from segments.services import refresh_segments


class Command(BaseCommand):
    help = "Load a synthetic demo dataset (~2,000 customers, ~8,000 orders)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--customers", type=int, default=2000)
        parser.add_argument("--seed", type=int, default=42, help="Random seed (reproducible)")
        parser.add_argument(
            "--flush", action="store_true", help="Delete existing customers and their data first"
        )
        parser.add_argument(
            "--simulate-days",
            type=int,
            default=45,
            help="Replay lifecycle activity over the last N days for dashboard history (0: off)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if Customer.objects.exists():
            if not options["flush"]:
                raise CommandError("Customers already exist; re-run with --flush to replace them.")
            Customer.objects.all().delete()
        now = timezone.now()
        result = seed_demo_data(options["customers"], options["seed"], now)
        self.stdout.write(
            self.style.SUCCESS(f"Seeded {result.customers} customers and {result.orders} orders.")
        )
        if options["simulate_days"]:
            self.stdout.write(f"Replaying the last {options['simulate_days']} days of activity…")
            activity = simulate_activity(options["simulate_days"], now, options["seed"])
            self.stdout.write(", ".join(f"{v} {k}" for k, v in activity.items()))
        segments = refresh_segments(now)
        self.stdout.write("Segments: " + ", ".join(f"{k} {v}" for k, v in sorted(segments.items())))
