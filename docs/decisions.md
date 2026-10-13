# Decisions and tradeoffs

## One send gate for every message

Compliance rules (opt-out, quiet hours, frequency caps) are only as strong as their weakest caller. Instead of each flow checking them, `send_message()` is the only function that reaches a sender, and it applies the rules in a fixed order: unsubscribed → quiet hours → weekly cap → send. The order matters:

- **Unsubscribed first**, because an opt-out must win over everything, including a message waiting for the morning.
- **Quiet hours before the cap**, because a deferred message hasn't been sent and shouldn't use up the week's allowance. The cap counts only messages actually sent.

Every attempt is stored as a `Message` with its outcome and reason, which gives an audit trail ("why didn't Maya get the offer?") and the dashboard's blocked-by-reason numbers for free. The customer row is locked during the check, so two flows sending at the same moment can't both slip under the cap.

**Tradeoff:** the cap is first come, first served. A win-back reminder can use the last slot of the week and block a review request. Per-flow priority is listed in "What's next".

## Defer at night instead of dropping

A message that falls inside 21:00–08:00 *in the customer's timezone* is stored as `deferred`, with `scheduled_for` set to their next 08:00. A dispatcher re-runs the **whole gate** when it comes due, so a STOP received overnight, or a cap reached in the meantime, still applies. Dropping would lose legitimate messages (a review request after an evening delivery). Sending anyway would break carrier and telemarketing norms and annoy customers.

The daily job runs at 14:00 UTC (10:00 US Eastern) so that win-back batches mostly go out right away instead of piling up behind quiet hours.

## Flows as database state machines

Each enrollment is a row: flow, step, `next_run_at`, status, context. The alternative, chaining Celery tasks with countdowns, hides state in the broker. It's lost on a Redis flush, it can't be queried, and it's hard to cancel. Rows give:

- **Cancellation as an update**: an order cancels win-back with one `UPDATE`, and STOP cancels everything.
- **Visibility**: the dashboard counts active enrollments per flow, and outcomes (`cancel_reason="ordered"`) feed the reactivation rate.
- **Safe scheduling from anywhere**: `process_due_enrollments` locks each due row with `SKIP LOCKED`, so Celery beat every minute, n8n hourly, and a manual `POST /api/flows/process-due` can all run without double sends.
- **One active enrollment per customer and key**: a partial unique constraint. The key is the flow name, or `review:<order>` so reviews can run once per order.

Steps re-check their stop condition (has the customer ordered?) even though the order webhook already cancels win-back. If an order arrives through a CSV import or a missed webhook, the next step still stops.

## The model writes words; config sets the numbers

Personalized copy is useful, but a model that writes "30% off" when the business approved 10% is a real liability. So:

- The model is told to write placeholders (`{discount}`, `{code}`, `{link}`), and the values are filled in from `DISCOUNTS` and settings.
- The output is rejected if it contains any amount it wrote itself (`%`, `$`, "percent", "dollars" next to a digit), if a placeholder the step needs is missing, if it isn't valid JSON, or if it's longer than the channel limit (SMS 300 characters, email 1,000).
- Any rejection, API error or timeout (5 seconds) falls back to the template for that step, and each message records whether it used AI or the template.

Templates exist for every step and are the default in mock mode, so the system is complete without a model.

## RFM scoring

Quintile scores use the **mid-rank percentile**: (number of customers with a lower value + half of those tied) / total. Tied values always share a score, and a population where everyone is equal (or a single customer) scores 3 rather than 1 or 5. Recency is scored on days since the last order (fewer is better), frequency on order count, and monetary on total spend. Cancelled orders don't count.

Segments come from ordered rules (New → Champions → Loyal → At Risk → Hibernating) rather than a full 5×5 grid. Five named segments are what a marketer actually acts on, and the rules sit in one small function with tests.

Customers who never ordered have no scores. They're New for 30 days after signup, then Hibernating.

## Webhooks are idempotent by event id

Stores and SMS providers retry webhooks. `WebhookEvent(kind, event_id)` has a unique constraint, and a redelivered event returns `{"duplicate": true}` without side effects. The order webhook also refuses a second order with the same external id.

## n8n and Celery beat

Celery beat runs every scheduled job out of the box, so the project runs with no n8n setup. The n8n workflows call the same endpoints, for teams who want schedules and intake they can see and edit without a deploy. Because processing is lock-based and enrollment is deduplicated, running both is safe.

## Demo data: synthetic, but through the real engine

`seed_demo` builds customers from behavioural archetypes (frequent recent buyers, lapsed regulars, one-time buyers, new signups) so every segment has realistic numbers. It then replays 45 days in 3-hour ticks *through the actual engine and gate*: real enrollments, real quiet-hour deferrals, real cap blocks. Only the customers' responses are simulated (35% of review requests get a rating; win-back messages lead to a comeback order 3–7% of the time). This keeps the dashboard honest: every number on it comes from the same code paths production would use.

## Known gaps

- **No email unsubscribe link yet** (SMS STOP is complete). Required before real email sending; see `deliverability.md`.
- **Webhooks are not signature-verified** and the stats API is unauthenticated. Fine for a local demo, not for production.
- **The referral discount is reported, not applied.** Redeem returns the friend's discount percentage for the storefront to apply at checkout; this engine doesn't price orders.
- **The weekly cap has no priorities** (see above).
