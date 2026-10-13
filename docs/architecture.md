# Architecture

## Services

| Service | Role |
|---|---|
| `api` | Django + DRF behind gunicorn: webhooks, signup, referrals, reviews, stats. Migrates on start. |
| `worker` | Celery worker: runs the scheduled jobs. |
| `beat` | Celery beat schedule: process due enrollments (every minute), dispatch deferred messages (every 5 minutes), daily segment refresh and win-back enrollment (14:00 UTC). |
| `postgres` | All state: customers, orders, RFM snapshots, enrollments, messages, reviews, referrals, webhook event ids. |
| `redis` | Celery broker. |
| `frontend` | React dashboard served by nginx on :3000, proxying `/api` to `api`. |
| `n8n` | Optional scheduler and webhook intake calling the same endpoints (safe to run alongside beat). |

## Data model

```mermaid
erDiagram
    Customer ||--o{ Order : places
    Customer ||--|| CustomerRFM : "scored as"
    Customer ||--o{ FlowEnrollment : "enrolled in"
    Customer ||--o{ Message : receives
    Customer ||--o{ Review : writes
    Order ||--o| Review : "reviewed by"
    Customer ||--o{ Referral : "refers (referrer)"
    Customer ||--o| Referral : "referred (referee)"

    Customer {
        string email UK
        string phone "E.164"
        string timezone "IANA"
        bool unsubscribed
        string referral_code UK
        json tags
    }
    CustomerRFM {
        int recency_days
        int frequency
        decimal monetary
        int r_score "1-5"
        int f_score "1-5"
        int m_score "1-5"
        enum segment
        enum inactivity "active|30|60|90"
    }
    FlowEnrollment {
        string flow
        string key "unique while active"
        string step
        enum status "active|completed|cancelled"
        datetime next_run_at
        json context
        string cancel_reason
    }
    Message {
        enum channel "sms|email"
        string flow
        string step
        enum status "sent|deferred|blocked|failed"
        string block_reason
        enum personalization "ai|template"
        datetime scheduled_for
    }
```

## Flow state machines

Each flow is a set of step handlers. A handler returns `Advance(step, delay)`, `Complete()` or `Cancel(reason)`, and the engine applies it to the enrollment.

```mermaid
stateDiagram-v2
    state "Welcome" as W {
        [*] --> welcome: signup
        welcome --> first_order_nudge: +2 days
        first_order_nudge --> [*]: send nudge, or skip if already ordered
    }
    state "Win-back" as B {
        [*] --> reminder: 60+ days inactive (daily job)
        reminder --> offer: +4 days
        offer --> final_offer: +7 days
        final_offer --> [*]
        reminder --> cancelled: order placed
        offer --> cancelled: order placed
        final_offer --> cancelled: order placed
    }
    state "Review" as R {
        [*] --> request: delivered + 3 h
        request --> [*]: skip if already reviewed
    }
```

`process_due_enrollments` selects active enrollments with `next_run_at <= now` and locks each one with `SELECT … FOR UPDATE SKIP LOCKED`. It then runs the step inside its own savepoint. A step that raises is rolled back and retried 15 minutes later, and the enrollment stays active. External events act on enrollments directly: an order cancels win-back, and STOP cancels everything.

## The send gate

```mermaid
sequenceDiagram
    participant F as Flow step / event
    participant P as Personalizer
    participant G as send_message gate
    participant DB as Message log
    participant S as Sender

    F->>P: flow, step, first name, facts {discount, link…}
    P-->>F: subject + body (AI if valid, else template)
    F->>G: send_message(customer, flow, step, copy)
    G->>DB: Message(pending)
    G->>G: lock customer row
    alt unsubscribed
        G->>DB: blocked · unsubscribed
    else inside customer-local quiet hours
        G->>DB: deferred · scheduled_for = next 08:00 local
        Note over G,DB: dispatch_deferred re-runs the whole gate when due
    else ≥ 3 sent in the last 7 days
        G->>DB: blocked · weekly_cap
    else allowed
        G->>S: send (SMS gets "Reply STOP to opt out.")
        S-->>G: provider id or error
        G->>DB: sent / failed
    end
```

The customer row is locked for the duration, so two concurrent flows can't both fit under the weekly cap.

## Segmentation

The daily job, or `POST /api/segments/refresh`:

1. Aggregates each customer's non-cancelled orders up to now: last order, count, spend.
2. Scores R, F and M from 1 to 5 by mid-rank percentile among customers with orders.
3. Assigns a segment with ordered rules: New (first activity within 30 days) → Champions (R≥4, F≥4) → Loyal (R≥3, F≥3) → At Risk (R≤2, F≥3) → Loyal (R≥3) → Hibernating.
4. Sets the inactivity flag from days since the last order (or since signup if they never ordered): 30, 60 or 90.
5. Upserts `CustomerRFM`, then enrolls customers flagged `inactive_60` or `inactive_90` (with at least one order and no win-back in the last 90 days) into win-back.
