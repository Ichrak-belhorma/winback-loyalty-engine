from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from compliance.idempotency import first_delivery
from compliance.unsubscribe import is_stop_request, unsubscribe
from customers.models import Customer
from customers.phones import normalize_phone


@api_view(["POST"])
@parser_classes([FormParser, MultiPartParser, JSONParser])
def inbound_sms(request: Request) -> Response:
    """Inbound SMS. Accepts Twilio form fields (MessageSid, From, Body) or JSON
    (event_id, from, body). Redelivered event ids are acknowledged without reprocessing."""
    data = request.data
    event_id = data.get("MessageSid") or data.get("event_id")
    sender = data.get("From") or data.get("from")
    body = data.get("Body") or data.get("body") or ""
    if not event_id or not sender:
        raise ValidationError("event id (MessageSid/event_id) and sender (From/from) required")

    if not first_delivery("inbound_sms", event_id):
        return Response({"duplicate": True})
    customer = Customer.objects.filter(phone=normalize_phone(sender)).first()
    if customer is None:
        return Response({"duplicate": False, "matched": False})
    stop = is_stop_request(body)
    cancelled = unsubscribe(customer, timezone.now()) if stop else 0
    return Response(
        {
            "duplicate": False,
            "matched": True,
            "customer_id": customer.pk,
            "unsubscribed": stop,
            "enrollments_cancelled": cancelled,
        }
    )
