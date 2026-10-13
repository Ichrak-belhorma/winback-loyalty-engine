# Demo script: 90 seconds

For a Loom or a GIF. Mock mode, no keys.

## Before recording

```bash
docker compose down -v && docker compose up --build -d
docker compose exec api python manage.py seed_demo      # about a minute
```

Open http://localhost:3000 in one window, and a terminal with `docker compose logs -f api worker` beside it. Pick a seeded customer with a phone number for the STOP shot:

```bash
docker compose exec api python manage.py shell -c \
  "from customers.models import Customer as C; c=C.objects.exclude(phone='').filter(enrollments__status='active').first(); print(c.first_name, c.phone)"
```

## Shot list

| Time | Show | Say |
|---|---|---|
| 0:00–0:10 | Dashboard, top cards | "This is the retention engine for a same-day delivery store: 2,000 customers, segmented by RFM, with automated welcome, win-back, referral and review flows." |
| 0:10–0:25 | Segment chart, then the reactivation card | "Customers are scored on recency, frequency and spend: champions down to hibernating. Anyone 60 days without an order enters win-back: a reminder, then 10% off, then 20%. This card is the result: the share who ordered within 14 days." |
| 0:25–0:40 | Messages-per-day chart and the flow table | "Every message, from every flow, goes through one compliance gate. Here's volume per flow, and how many were blocked or are waiting." |
| 0:40–0:55 | Blocked card → a blocked row in the recent messages table (badge + reason) | "The gate blocks anyone over three messages a week, holds anything that would land between 9 p.m. and 8 a.m. in the customer's own timezone, and drops anyone who said STOP. Every block is logged with its reason." |
| 0:55–1:10 | Terminal: send STOP for the customer picked earlier, show the JSON response | `curl -X POST localhost:8000/api/webhooks/inbound-sms -d MessageSid=SM-demo --data-urlencode From=<phone> -d Body=stop` "They're unsubscribed at once, every active flow is cancelled, and anything queued for the morning is blocked." |
| 1:10–1:20 | Recent messages table: an "AI" or "Template" copy label | "Copy can be personalized by OpenAI, but the model never chooses a discount. It writes placeholders, and anything that invents a number falls back to the template." |
| 1:20–1:30 | n8n canvas (optional), or back to the dashboard | "Scheduling runs on Celery or n8n, and every flow maps one-to-one to GoHighLevel workflows. The mapping and screenshots are in the repo." |

## Tips

- Record at 1280×720 or wider so both charts sit side by side.
- To show a deferral live, sign up a customer whose timezone is currently at night, then `curl -X POST localhost:8000/api/flows/process-due`. The welcome message shows as `deferred` in the table.
