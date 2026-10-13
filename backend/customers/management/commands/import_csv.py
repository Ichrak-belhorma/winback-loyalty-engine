from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from customers.csv_import import ImportReport, import_customers, import_orders


class Command(BaseCommand):
    help = "Import customers and/or orders from CSV files (upsert by email / order_id)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--customers", type=Path, help="customers CSV")
        parser.add_argument("--orders", type=Path, help="orders CSV (customers must exist)")

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["customers"] and not options["orders"]:
            raise CommandError("Pass --customers and/or --orders.")
        if options["customers"]:
            self._report("customers", import_customers(options["customers"]))
        if options["orders"]:
            self._report("orders", import_orders(options["orders"]))

    def _report(self, label: str, report: ImportReport) -> None:
        self.stdout.write(f"{label}: {report.created} created, {report.updated} updated")
        for error in report.errors:
            self.stdout.write(self.style.WARNING(f"  skipped {error}"))
