from pathlib import Path

import pytest
from django.core.management import call_command

from customers.csv_import import import_customers, import_orders
from customers.models import Customer
from orders.models import Order
from segments.models import CustomerRFM

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data"


@pytest.mark.django_db
def test_seed_demo_is_reproducible_and_scores_everyone():
    call_command("seed_demo", customers=150, seed=7, simulate_days=0)
    first = (Customer.objects.count(), Order.objects.count())

    call_command("seed_demo", customers=150, seed=7, flush=True, simulate_days=0)

    assert (Customer.objects.count(), Order.objects.count()) == first
    assert first[0] == 150
    assert first[1] > 300
    assert CustomerRFM.objects.count() == 150


@pytest.mark.django_db
def test_csv_import_upserts_and_reports_bad_rows():
    customers = import_customers(SAMPLES / "customers.csv")
    orders = import_orders(SAMPLES / "orders.csv")
    again = import_orders(SAMPLES / "orders.csv")

    assert (customers.created, len(customers.errors)) == (2, 1)
    assert (orders.created, len(orders.errors)) == (3, 1)
    assert "ghost@example.com" in orders.errors[0]
    assert (again.created, again.updated) == (0, 3)
    assert Order.objects.filter(customer__email="maria.lopez@example.com").count() == 2
