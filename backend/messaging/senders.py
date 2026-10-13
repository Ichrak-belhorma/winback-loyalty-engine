import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutboundMessage:
    channel: str
    to: str
    subject: str
    body: str


@dataclass(frozen=True)
class SendResult:
    provider_id: str


class MessageSender(Protocol):
    def send(self, message: OutboundMessage) -> SendResult: ...


class ConsoleSender:
    """Mock sender: prints the message. The gate has already recorded it in the Message table."""

    def send(self, message: OutboundMessage) -> SendResult:
        provider_id = f"console-{uuid.uuid4().hex[:12]}"
        subject = f" | {message.subject}" if message.subject else ""
        logger.info("[%s → %s%s] %s", message.channel, message.to, subject, message.body)
        return SendResult(provider_id=provider_id)


class MailtrapSender:
    """Email via the Mailtrap Email Sending API."""

    URL = "https://send.api.mailtrap.io/api/send"

    def __init__(self, api_token: str, sender_email: str, http: httpx.Client) -> None:
        self._headers = {"Authorization": f"Bearer {api_token}"}
        self._sender = sender_email
        self._http = http

    def send(self, message: OutboundMessage) -> SendResult:
        response = self._http.post(
            self.URL,
            headers=self._headers,
            json={
                "from": {"email": self._sender},
                "to": [{"email": message.to}],
                "subject": message.subject,
                "text": message.body,
            },
        )
        response.raise_for_status()
        return SendResult(provider_id=response.json()["message_ids"][0])


class TwilioSender:
    """SMS via the Twilio Messages API."""

    def __init__(
        self, account_sid: str, auth_token: str, from_number: str, http: httpx.Client
    ) -> None:
        self._url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        self._auth = (account_sid, auth_token)
        self._from = from_number
        self._http = http

    def send(self, message: OutboundMessage) -> SendResult:
        response = self._http.post(
            self._url,
            auth=self._auth,
            data={"To": message.to, "From": self._from, "Body": message.body},
        )
        response.raise_for_status()
        return SendResult(provider_id=response.json()["sid"])


def _require(name: str) -> str:
    value = getattr(settings, name)
    if not value:
        raise ImproperlyConfigured(f"{name} is required when USE_MOCKS=false.")
    return value


def get_sender(channel: str) -> MessageSender:
    """Console sender in mock mode; otherwise Mailtrap for email and Twilio for SMS."""
    if settings.USE_MOCKS:
        return ConsoleSender()
    http = httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS)
    if channel == "email":
        return MailtrapSender(
            _require("MAILTRAP_API_TOKEN"), _require("MAILTRAP_SENDER_EMAIL"), http
        )
    return TwilioSender(
        _require("TWILIO_ACCOUNT_SID"),
        _require("TWILIO_AUTH_TOKEN"),
        _require("TWILIO_FROM_NUMBER"),
        http,
    )
