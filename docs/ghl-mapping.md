# Mapping to GoHighLevel

Every flow in this engine has a direct equivalent in GoHighLevel (GHL). This table is the translation key: the same lifecycle can run in code (this repo) or be rebuilt in a GHL sub-account. Screenshots of the GHL builds go in [`/ghl`](../ghl).

## Flow by flow

| Our flow | GHL workflow | Trigger | Steps (GHL actions) | Tags | Pipeline stage |
|---|---|---|---|---|---|
| **Welcome** (`welcome`) | *Welcome + first-order nudge* | Contact Created (or Form Submitted for the signup form) | Send SMS/Email (welcome) → Wait 2 days → If/Else "has tag `customer`" → no: Send nudge with offer | `new-signup`; `customer` is added when the first order arrives | Lifecycle: **New** |
| **First-order nudge** (step) | same workflow | (continuation) | Goal Event "Tag added: `customer`" ends the workflow early | — | New → **Active** on first order |
| **Win-back** (`winback`) | *Win-back escalation* | Contact Tag Added `lapsed-60` (set by the segment sync, see below) | Send reminder → Wait 4 days → Send 10% offer → Wait 7 days → Send 20% final offer | `lapsed-60`, `winback-active`; removed on exit | **At Risk** → **Won Back** or **Lapsed** |
| **Stop on order** (rule) | same workflow | — | Goal Event "Order Submitted / Tag added `ordered`", or workflow setting *Stop on response* for replies | `winback-won` | → **Won Back** |
| **Referral** (`referral`) | *Referral reward* | Inbound Webhook (our `/api/referrals/redeem` result), or GHL Affiliate Manager | Wait for friend's first order (Wait for event) → Send referrer reward | `referred-by:<code>`, `referral-rewarded` | — |
| **Review request** (`review`) | *Post-delivery review* | Inbound Webhook `delivery-completed` (or Order Fulfilled from the store integration) | Wait 3 hours → Send Review Request (Reputation Management) | `review-requested` | — |
| **Low-rating routing** (`review/fix_it`) | *Review triage* | Survey or Form Submitted (rating field) | If/Else rating ≥ 4 → send public review link; else → send private fix-it message, Add Tag `needs_followup`, Create Task / Internal Notification for staff | `needs_followup` | Opportunity in a **Service Recovery** pipeline |
| **STOP handling** | built in | Inbound SMS with STOP / UNSUBSCRIBE | GHL sets **DND** for SMS on carrier STOP keywords automatically; plus *Customer Replied* trigger → Remove from all workflows | `unsubscribed` | — |

## Cross-cutting rules

| Our rule | Where it lives here | GHL equivalent |
|---|---|---|
| Single send gate | `compliance/gate.py`: every message passes it | No single gate. Each workflow inherits the sub-account's DND status and its own settings, so the rules below must be configured per workflow. |
| Unsubscribed check | Gate rule 1; `Customer.unsubscribed` | Contact **DND** (per channel or all channels) |
| Quiet hours (21:00–08:00 customer-local, defer) | Gate rule 2; deferred messages are re-checked when due | Workflow setting **Time Window** (allowed sending hours and days, in the contact's timezone where set) |
| Weekly cap (3 per rolling 7 days) | Gate rule 3; counts messages actually sent | Not native. Approximate with a custom field counter incremented by each send action plus an If/Else guard, or a shared "Wait" pattern. This is the clearest case where code is stronger. |
| Idempotent webhooks | `WebhookEvent` (kind, event_id) unique | Inbound Webhook triggers have no built-in dedupe. Guard with If/Else on a custom field storing the last event id. |
| One active enrollment per flow | Partial unique constraint on `FlowEnrollment(customer, key)` while active | Workflow setting **Allow re-entry** off |
| Discounts from config, never invented | Placeholders filled from `DISCOUNTS` | Custom Values (`{{custom_values.winback_offer}}`) in message templates |
| AI copy with template fallback | `FallbackPersonalizer` | GHL's AI content features or a Webhook action to this API; the template text is the action's default |

## Segments

| Our segment / flag | How it's computed | GHL representation |
|---|---|---|
| Champions, Loyal, At Risk, Hibernating, New | RFM quintiles + rules (`segments/rfm.py`), refreshed daily | **Smart Lists** filtered on custom fields `rfm_r`, `rfm_f`, `rfm_m`, `segment` |
| Inactive 30 / 60 / 90 | Days since last order | Tags `lapsed-30`, `lapsed-60`, `lapsed-90` |

A GHL build needs something to compute RFM: a nightly job (the n8n daily refresh, for example) that pushes `segment` and the lapsed tags to contacts through the GHL API. Tag changes then trigger the workflows above. This is the main structural difference: here segmentation and messaging share one database, while in GHL they're connected by tags.

## Pipeline

**Customer Lifecycle** opportunity pipeline:

`New` → `Active` (first order) → `At Risk` (60 days without an order) → `Won Back` (ordered during win-back) / `Lapsed` (win-back completed without an order)

Here, the same stages are derived from data: segment, inactivity flag, and the outcome of the win-back enrollment (`status` / `cancel_reason="ordered"`). The dashboard's reactivation rate is the `At Risk → Won Back` conversion.

## Rebuilding a flow in GHL (narrative)

- **Welcome:** Contact Created → Send SMS (welcome, with a `{{custom_values.store}}` placeholder) → Wait 2 days → If/Else "Tag `customer` exists" → no branch: Send SMS with `{{custom_values.welcome_offer}}`. A Goal Event on tag `customer` ends it early for anyone who orders.
- **Win-back:** Tag Added `lapsed-60` → Add Tag `winback-active` → reminder → Wait 4 days → offer → Wait 7 days → final offer → Remove Tag. A Goal Event on Order Submitted (or tag `ordered` from the store integration) jumps to the end and moves the opportunity to *Won Back*. Re-entry is off, and the 90-day cooldown is a date custom field checked in the trigger filter.
- **Reviews:** Inbound Webhook (delivery completed) → Wait 3 hours → Send Review Request. The rating survey's submission triggers the triage workflow, which splits on rating ≥ 4.
