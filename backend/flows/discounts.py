from django.conf import settings


def discount(name: str) -> str:
    """A configured discount as copy, e.g. "15%". Models never choose these values."""
    return f"{settings.DISCOUNTS[name]}%"
