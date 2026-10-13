"""Building blocks for flow definitions: step results and the personalized-send helper."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from compliance.gate import preferred_channel, send_message
from customers.models import Customer
from flows.models import FlowEnrollment
from messaging.models import Message
from messaging.personalization import PersonalizationRequest, get_personalizer


@dataclass(frozen=True)
class Advance:
    """Move to `step` and run it after `delay`."""

    step: str
    delay: timedelta = timedelta(0)


@dataclass(frozen=True)
class Complete:
    pass


@dataclass(frozen=True)
class Cancel:
    reason: str


StepResult = Advance | Complete | Cancel
StepHandler = Callable[[FlowEnrollment, datetime], StepResult]


@dataclass(frozen=True)
class FlowDefinition:
    name: str
    first_step: str
    handlers: dict[str, StepHandler] = field(default_factory=dict)


def send_personalized(
    customer: Customer,
    flow: str,
    step: str,
    now: datetime,
    facts: dict[str, str] | None = None,
) -> Message:
    """Personalize the copy for a flow step and send it through the compliance gate."""
    copy = get_personalizer().personalize(
        PersonalizationRequest(
            flow=flow,
            step=step,
            channel=preferred_channel(customer),
            first_name=customer.first_name,
            facts=facts or {},
        )
    )
    return send_message(
        customer,
        flow=flow,
        step=step,
        subject=copy.subject,
        body=copy.body,
        personalization=copy.source,
        now=now,
    )


def send_step(
    enrollment: FlowEnrollment, step: str, now: datetime, facts: dict[str, str] | None = None
) -> Message:
    return send_personalized(enrollment.customer, enrollment.flow, step, now, facts)
