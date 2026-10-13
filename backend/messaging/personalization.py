import json
import logging
import re
import string
from dataclasses import dataclass, field
from typing import Any, Protocol

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field

from messaging.models import Message
from messaging.templates import TEMPLATES

logger = logging.getLogger(__name__)

# Facts the model may only reference as placeholders; their values come from config.
INJECTED_FACTS = ("discount", "code", "link")
# Any money or percentage the model writes itself is rejected.
INVENTED_AMOUNT = re.compile(r"\d\s*%|%\s*\d|[$€£]\s*\d|\d+\s*(?:percent|dollars?)\b", re.I)


@dataclass(frozen=True)
class PersonalizationRequest:
    flow: str
    step: str
    channel: str
    first_name: str
    facts: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PersonalizedMessage:
    subject: str
    body: str
    source: str


class Personalizer(Protocol):
    def personalize(self, request: PersonalizationRequest) -> PersonalizedMessage: ...


def max_body_length(channel: str) -> int:
    return settings.SMS_MAX_CHARS if channel == Message.Channel.SMS else settings.EMAIL_MAX_CHARS


def _values(request: PersonalizationRequest) -> dict[str, str]:
    return {"first_name": request.first_name, "store": settings.STORE_NAME, **request.facts}


def required_placeholders(flow: str, step: str) -> set[str]:
    _, body = TEMPLATES[(flow, step)]
    names = {name for _, name, _, _ in string.Formatter().parse(body) if name}
    return names & set(INJECTED_FACTS)


class TemplatePersonalizer:
    def personalize(self, request: PersonalizationRequest) -> PersonalizedMessage:
        subject, body = TEMPLATES[(request.flow, request.step)]
        values = _values(request)
        return PersonalizedMessage(
            subject=subject.format(**values),
            body=body.format(**values),
            source=Message.Personalization.TEMPLATE,
        )


class AICopy(BaseModel):
    subject: str = Field(min_length=1, max_length=80)
    body: str = Field(min_length=1)


class InvalidAICopy(ValueError):
    pass


def validate_ai_copy(raw: str, request: PersonalizationRequest) -> PersonalizedMessage:
    """Parse and police model output; raises InvalidAICopy so the caller falls back."""
    copy = AICopy.model_validate_json(raw)
    for text in (copy.subject, copy.body):
        if INVENTED_AMOUNT.search(text):
            raise InvalidAICopy(f"model wrote its own amount: {text!r}")
    missing = {
        p for p in required_placeholders(request.flow, request.step) if f"{{{p}}}" not in copy.body
    }
    if missing:
        raise InvalidAICopy(f"missing placeholders {sorted(missing)}")
    values = _values(request)
    try:
        subject, body = copy.subject.format(**values), copy.body.format(**values)
    except (KeyError, IndexError, ValueError) as exc:
        raise InvalidAICopy(f"bad placeholder in copy: {exc}") from exc
    if len(body) > max_body_length(request.channel):
        raise InvalidAICopy(f"body is {len(body)} chars, max {max_body_length(request.channel)}")
    return PersonalizedMessage(subject=subject, body=body, source=Message.Personalization.AI)


SYSTEM_PROMPT = (
    "You write short, warm lifecycle messages for {store}, a same-day grocery delivery service. "
    'Return JSON: {{"subject": str (max 80 chars), "body": str}}. Rules: never write any '
    "price, amount or percentage yourself. Where the offer, code or link belongs, write the "
    "placeholder exactly as given: {{discount}}, {{code}}, {{link}}. Use {{first_name}} for the "
    "name. Keep the body under {max_chars} characters. No emojis in SMS."
)


class OpenAIPersonalizer:
    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        self._client = OpenAI(api_key=api_key, timeout=timeout, max_retries=0)
        self._model = model

    def personalize(self, request: PersonalizationRequest) -> PersonalizedMessage:
        subject, body = TEMPLATES[(request.flow, request.step)]
        brief: dict[str, Any] = {
            "flow": request.flow,
            "step": request.step,
            "channel": request.channel,
            "reference_copy": {"subject": subject, "body": body},
            "required_placeholders": sorted(required_placeholders(request.flow, request.step)),
        }
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(
                        store=settings.STORE_NAME, max_chars=max_body_length(request.channel)
                    ),
                },
                {"role": "user", "content": json.dumps(brief)},
            ],
            response_format={"type": "json_object"},
            max_tokens=300,
            temperature=0.7,
        )
        return validate_ai_copy(response.choices[0].message.content or "", request)


class FallbackPersonalizer:
    """Try the primary personalizer; on any error or invalid copy use the fallback."""

    def __init__(self, primary: Personalizer, fallback: Personalizer) -> None:
        self._primary = primary
        self._fallback = fallback

    def personalize(self, request: PersonalizationRequest) -> PersonalizedMessage:
        try:
            return self._primary.personalize(request)
        except Exception as exc:
            logger.warning(
                "AI personalization failed for %s/%s, using template: %s",
                request.flow,
                request.step,
                exc,
            )
            return self._fallback.personalize(request)


def get_personalizer() -> Personalizer:
    if settings.USE_MOCKS or not settings.OPENAI_API_KEY:
        return TemplatePersonalizer()
    return FallbackPersonalizer(
        OpenAIPersonalizer(
            settings.OPENAI_API_KEY, settings.OPENAI_MODEL, settings.OPENAI_TIMEOUT_SECONDS
        ),
        TemplatePersonalizer(),
    )
