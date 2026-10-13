import pytest
from django.utils import timezone

from customers.seed import seed_demo_data
from flows.simulation import simulate_activity
from messaging.models import Message


@pytest.mark.django_db
def test_simulated_history_goes_through_the_real_engine_and_gate():
    now = timezone.now()
    seed_demo_data(120, seed=3, now=now)

    totals = simulate_activity(10, now, seed=3)

    assert totals["messages"] > 0
    assert set(Message.objects.values_list("flow", flat=True)) <= {"welcome", "winback", "review"}
    assert not Message.objects.filter(created_at__gt=now).exists()
    assert not Message.objects.filter(status="sent", sent_at__isnull=True).exists()
