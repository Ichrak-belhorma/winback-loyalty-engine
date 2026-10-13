# Deliverability and compliance

A retention engine is only as good as the share of its messages that land. This note covers what has to be in place before turning real sending on (`USE_MOCKS=false`), and why the engine enforces the limits it does.

## Email authentication

Gmail and Yahoo have required authentication from bulk senders (roughly 5,000+ messages a day to their users) since February 2024. Mailbox providers increasingly filter unauthenticated mail at any volume.

| Record | What it proves | Setup |
|---|---|---|
| **SPF** | The sending server is allowed to send for the domain | TXT on the sending domain, e.g. `v=spf1 include:<provider-spf-domain> ~all` (use the include value your provider gives you). Stay under the 10-DNS-lookup limit. |
| **DKIM** | The message wasn't altered and was signed by the domain | Publish the provider's DKIM public key (CNAME or TXT at `<selector>._domainkey`). Use 2048-bit keys and rotate periodically. |
| **DMARC** | What receivers should do when SPF/DKIM fail, plus reports | TXT at `_dmarc`: start with `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain`, read the reports, then move to `p=quarantine` and finally `p=reject`. |
| **Alignment** | The visible From domain matches the SPF/DKIM domain | Send from a subdomain you control (e.g. `mail.store.com`) with SPF/DKIM set up on that same domain. Without alignment, DMARC fails even when SPF and DKIM pass. |

Use a dedicated subdomain for marketing and lifecycle mail, so its reputation is kept separate from transactional mail (receipts, password resets).

## Sender warm-up

New domains and IPs have no reputation, and a sudden burst looks like spam. Ramp up gradually:

- Start with the **most engaged** customers: Champions and Loyal, who ordered recently and are most likely to open.
- Roughly double the daily volume every few days (for example 200 → 500 → 1,000 → 2,000 …), and hold or slow down if bounces or complaints rise.
- Send the win-back flow, which goes to the *least* engaged contacts, last, once the domain has a track record.
- Keep volume steady day to day. The daily refresh enrolls lapsed customers in batches, which is why sends are spread across the day rather than fired at once.

## List hygiene

- **Hard bounces:** suppress immediately and permanently.
- **Complaints** (feedback loops, "Report spam"): treat as an unsubscribe.
- **Sunset policy:** customers who haven't engaged in about 6 months stop receiving marketing. The Hibernating segment and the `inactive_90` flag exist to drive exactly this decision. Win-back is the last attempt, and the 90-day re-enrollment cooldown stops it from looping.
- **Imports** (`import_csv`) normalize emails and phones. In production, also validate addresses before the first send.

## Why sending is capped

Every message passes one gate (`compliance/gate.py`) that enforces, in order:

1. **Unsubscribed → blocked.** Opt-outs are absolute and apply to every flow.
2. **Quiet hours → deferred** (21:00–08:00 in the customer's own timezone). US telemarketing rules restrict texts and calls outside 8 a.m.–9 p.m. local time, and late-night texts drive opt-outs. Messages are *deferred*, not dropped, and are re-checked when the window opens.
3. **Weekly cap → blocked** (3 messages per customer per rolling 7 days, counting only messages actually sent). Over-mailing is the quickest way to raise complaint rates. Gmail and Yahoo expect spam complaints to stay well under **0.3%** (ideally under 0.1%), and carriers filter SMS senders with high opt-out rates. When flows overlap (a review request during a win-back sequence), the cap keeps the customer's total volume sane.

Blocked and deferred sends are stored with their reason, so the dashboard shows exactly how often each rule fires.

## Unsubscribe compliance

**SMS (implemented):**
- STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT, plus "unsub" and "stop all", in any case and ignoring punctuation, set `unsubscribed=True` instantly. They also cancel every active enrollment and block any already-deferred message.
- Every SMS carries "Reply STOP to opt out."
- In the US, application-to-person SMS from a regular 10-digit number requires **A2P 10DLC** brand and campaign registration (through Twilio), with opt-in described accurately. Unregistered traffic is filtered or blocked.

**Email:**
- US anti-spam law (CAN-SPAM) requires a working unsubscribe mechanism, honoured within 10 business days, plus a valid physical postal address in marketing email.
- Bulk senders to Gmail and Yahoo must support **one-click unsubscribe** (the `List-Unsubscribe` and `List-Unsubscribe-Post` headers, RFC 8058) and honour it within 2 days.
- **Not built yet:** this engine has no email unsubscribe link or `List-Unsubscribe` header. That's required before real email sending, and it's the first item in "What's next" in the README. The gate side already exists: an unsubscribe endpoint only has to set the same flag STOP sets.

## Consent

Only message customers who opted in (checkout or signup consent), and keep a record of when and how. The `signed_up_at` and `unsubscribed_at` timestamps are the start of that audit trail. Transactional messages (order updates) and marketing messages (win-back offers) carry different consent requirements, and the engine only sends lifecycle marketing.
