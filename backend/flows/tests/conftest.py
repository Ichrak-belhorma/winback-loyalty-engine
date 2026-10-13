from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from django.test import Client

# Noon in New York: outside quiet hours for the default test customer timezone.
T0 = datetime(2026, 6, 10, 16, 0, tzinfo=UTC)


@pytest.fixture
def api() -> Client:
    return Client(HTTP_HOST="localhost")


@pytest.fixture
def post(api: Client) -> Callable:
    def _post(path: str, data: dict):
        return api.post(path, data, content_type="application/json")

    return _post
