import json

import pytest

from messaging.personalization import (
    FallbackPersonalizer,
    InvalidAICopy,
    PersonalizationRequest,
    TemplatePersonalizer,
    validate_ai_copy,
)

OFFER = PersonalizationRequest("winback", "offer", "sms", "Ana", {"discount": "10%"})


class StubAI:
    def __init__(self, raw: str | None = None, error: Exception | None = None) -> None:
        self.raw, self.error = raw, error

    def personalize(self, request: PersonalizationRequest):
        if self.error:
            raise self.error
        return validate_ai_copy(self.raw, request)


def ai_json(body: str, subject: str = "Come back") -> str:
    return json.dumps({"subject": subject, "body": body})


def test_template_injects_configured_discount():
    message = TemplatePersonalizer().personalize(OFFER)

    assert "10% off" in message.body
    assert message.source == "template"


def test_valid_ai_copy_gets_injected_values():
    message = FallbackPersonalizer(
        StubAI(ai_json("Hey {first_name}, enjoy {discount} off today!")), TemplatePersonalizer()
    ).personalize(OFFER)

    assert message.body == "Hey Ana, enjoy 10% off today!"
    assert message.source == "ai"


@pytest.mark.parametrize(
    "raw",
    [
        ai_json("Take 25% off, {first_name}! {discount}"),
        ai_json("Here's $5 off: {discount}"),
        ai_json("Come back, {first_name}!"),
        ai_json("{discount} " + "x" * 400),
        ai_json("Use {coupon} now {discount}"),
        "not json",
    ],
    ids=[
        "invented-percent",
        "invented-dollars",
        "missing-offer",
        "too-long",
        "bad-key",
        "bad-json",
    ],
)
def test_invalid_ai_copy_is_rejected(raw: str):
    with pytest.raises((InvalidAICopy, ValueError)):
        validate_ai_copy(raw, OFFER)


@pytest.mark.parametrize(
    "stub",
    [StubAI(error=TimeoutError("openai timed out")), StubAI(ai_json("Take 50% off!"))],
    ids=["api-timeout", "invalid-copy"],
)
def test_any_ai_failure_falls_back_to_template(stub: StubAI, caplog: pytest.LogCaptureFixture):
    message = FallbackPersonalizer(stub, TemplatePersonalizer()).personalize(OFFER)

    assert message.source == "template"
    assert "10% off" in message.body
    assert "using template" in caplog.text
