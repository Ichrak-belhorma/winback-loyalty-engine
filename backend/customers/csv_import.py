"""CSV import for real customer/order exports. Rows are upserted; bad rows are reported."""

import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from customers.models import Customer
from customers.phones import normalize_phone
from orders.models import Order


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_time(value: str) -> datetime:
    parsed = parse_datetime(value.strip())
    if parsed is None:
        raise ValueError(f"invalid datetime {value!r}")
    return parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed, UTC)


def import_customers(path: Path) -> ImportReport:
    """Columns: email, first_name, last_name, phone, timezone, signed_up_at."""
    report = ImportReport()
    with path.open(newline="", encoding="utf-8") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            try:
                email = row["email"].strip().lower()
                if not email or "@" not in email:
                    raise ValueError("missing or invalid email")
                defaults = {
                    "first_name": row.get("first_name", "").strip() or email.split("@")[0],
                    "last_name": row.get("last_name", "").strip(),
                    "phone": normalize_phone(row.get("phone", "")),
                    "timezone": row.get("timezone", "").strip() or "America/New_York",
                }
                if row.get("signed_up_at", "").strip():
                    defaults["signed_up_at"] = _parse_time(row["signed_up_at"])
                _, created = Customer.objects.update_or_create(email=email, defaults=defaults)
            except (KeyError, ValueError) as exc:
                report.errors.append(f"line {line}: {exc}")
                continue
            if created:
                report.created += 1
            else:
                report.updated += 1
    return report


def import_orders(path: Path) -> ImportReport:
    """Columns: order_id, customer_email, total, placed_at, delivered_at, status."""
    report = ImportReport()
    customers = {c.email: c for c in Customer.objects.all()}
    with path.open(newline="", encoding="utf-8") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            try:
                customer = customers.get(row["customer_email"].strip().lower())
                if customer is None:
                    raise ValueError(f"unknown customer {row['customer_email']!r}")
                status = row.get("status", "").strip() or Order.Status.DELIVERED
                if status not in Order.Status.values:
                    raise ValueError(f"invalid status {status!r}")
                delivered = row.get("delivered_at", "").strip()
                _, created = Order.objects.update_or_create(
                    external_id=row["order_id"].strip(),
                    defaults={
                        "customer": customer,
                        "total": Decimal(row["total"]),
                        "placed_at": _parse_time(row["placed_at"]),
                        "delivered_at": _parse_time(delivered) if delivered else None,
                        "status": status,
                    },
                )
            except (KeyError, ValueError, InvalidOperation) as exc:
                report.errors.append(f"line {line}: {exc}")
                continue
            if created:
                report.created += 1
            else:
                report.updated += 1
    return report
