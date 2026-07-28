# Forms specification

Covers every form on the public site and portal: fields, the confirmation/notification/webhook
pattern, error handling, and success states. This is a **draft contract**, not a documented
existing one — no form webhook payload is written down anywhere else in the repo yet. Where this
doc proposes a shape, it says so; it does not present a proposal as an agreed contract.

## Sources and ownership
- `docs/modules/website.md` — the form list and the confirmation/notification/webhook pattern.
- `docs/workstreams/bhanu.md` — "Webhook contract for Wix to internal, plus the internal receiver
  service for site forms," marked `SHARED-OK: receiver side from Paras; he keeps the form UI +
  notifications.` **This is why this spec is Paras's to write** — the contract's wire shape is
  still Bhanu's to finalise, but the receiver behaviour, form UI, and notification handling moved
  to this lane.
- [ADR-0002](decisions/0002-internal-platform.md) / [ADR-0004](decisions/0004-platform-graduation.md)
  — the site-forms receiver service was blocked on hosting, now unblocked.
- `apps/site/content/connect.md`, `partners.md`, `trade.md`, `members.md` — the only pages with
  actual sourced field lists today.
- `docs/modules/website.md`'s Definition of done — "forms deliver to the right owner with spam
  protection."

## Forms with sourced field lists today

### Contact / general enquiry (`connect.md`)
| Field | Notes |
|---|---|
| First name | required |
| Last name | required |
| Email | required, validated |
| Subject | dropdown: Membership · Partnership · Media · General (per `connect.md`) |
| Message | required |

Owner notification routes to `sunil@inzbc.org` today (D14, `client-answers.md`) — until a
dedicated `secretariat@inzbc.org` exists (D15, proposed).

### Partnership / sponsorship enquiry (`partners.md`)
"Become a partner" CTA — **distinct from the general contact form**, per `partners.md`: "links to
a partnership enquiry form, distinct from the general contact form on the Connect page." Fields
not yet specified beyond that distinction — draft against the common pattern below;
`[[confirm required fields with the Membership team]]`.

### Trade / market-entry enquiry (`trade.md`, `member-portal-spec.md`)
Referenced from the Trade Resources page and the member portal's "Trade opportunities" screen
(`docs/modules/member-portal-spec.md`) as **market-entry (both directions)** and **introduction
request**, per `docs/modules/website.md`'s form list. `trade.md`'s footer note confirms NZ Privacy
Act 2020 applies to "any enquiry form on this page" but does not enumerate fields.
`[[fields not yet specified — draft against docs/modules/sponsors-trade-services.md's "request
purpose, requesting organisation, sector + market, consent to share" record shape, which is the
closest sourced analogue]]`.

## Forms that are explicitly NOT native site forms

Two items on `website.md`'s form list turn out, per other sourced pages, to not be native forms
at all — worth stating plainly so nobody builds them as one by mistake:

- **Event registration.** `apps/site/content/events.md`: "Registration: via Zoho or Member
  Jungle — do not duplicate registration logic on the site itself." There is no native
  registration form; the site links out. `[[website.md's "event enquiry" form type is a
  different thing — a question about an event, not registering for one — and does need a native
  form; fields not yet sourced]]`.
- **Join / renew.** The live site and every content page describe "Join Now" as an external
  redirect to Member Jungle (`discovery.md`, `apps/site/content/members.md`,
  `member-portal-spec.md`). `website.md`'s form list nonetheless includes "join, renew" as form
  types with the confirmation/webhook pattern. **This is an unresolved contradiction between two
  sourced documents, not a decision this spec makes:** either `website.md`'s list is stale, or a
  lead-capture form is intended to sit in front of the Member Jungle redirect. `[[confirm with
  Bhanu/Sunil before building anything for "join" or "renew" as a native form]]`.

## Forms named in `website.md` with no sourced fields yet

`website.md` also lists: **sponsorship, delegation EOI, speaker, media, newsletter, profile
update, member news.** No content page sources field lists for these. They follow the common
pattern below once each page's content defines its fields — this spec doesn't invent fields for
forms nobody has written content for yet.

## Common submission pattern (every form)

Per `website.md`: **confirmation email to the submitter + owner notification + webhook to the
internal system.** Proposed shape, consistent with `schemas/api-contract.md`'s REST/JSON
convention (not yet agreed with Bhanu — flagged below):

```
POST /api/forms/submissions        (webhook target, internal receiver — Wix calls this)
{
  "form_type": "contact" | "partnership_enquiry" | "market_entry" | "introduction_request" | ...,
  "submitted_at": "<ISO 8601 timestamp>",
  "fields": { ... form-specific fields ... },
  "source_page": "<URL the form was submitted from>",
  "consent": { "privacy_act_acknowledged": true }
}
```

**Behaviour:**
1. Wix form submits to the internal receiver via webhook.
2. Receiver validates the payload, persists it, and triggers two notifications:
   - **Confirmation email to the submitter** — plain acknowledgement, no sensitive data echoed
     back beyond what they just typed.
   - **Owner notification** — routed by `form_type` to the right team (e.g. Membership,
     Secretariat, Media) rather than a single shared inbox. Owner mapping isn't sourced anywhere
     yet — `[[confirm routing table per form_type with each team]]`.
3. Receiver returns success/failure to Wix so the form UI can show the right state (below).

**This is a proposed contract, not documentation of an existing one.** `schemas/api-contract.md`
covers only the SIP pipeline/control surface; no equivalent file exists for forms yet. Bhanu owns
finalising the actual wire shape per his worklog line above — treat the JSON above as a starting
point for that conversation, not a frozen spec.

## Error handling and success states

Not sourced from any existing doc in detail — specified here against the one sourced constraint
(`website.md`'s Definition of done: "forms deliver to the right owner with spam protection") and
standard practice, since nothing else pins this down. Flagged as this spec's own design, open to
correction.

**Client-side (in the Wix form):**
- Inline field-level validation before submit (required fields, email format) — standard Wix
  form behaviour, no custom code needed for this part.
- Spam protection before the submission reaches the receiver at all (honeypot field and/or Wix's
  built-in CAPTCHA/reCAPTCHA) — required by the Definition of done above; specific mechanism
  `[[to confirm — Wix-native vs a custom check in the receiver]]`.

**On submit — success:**
- On-page confirmation message, not just an email (a submitter who doesn't check email
  immediately still needs to know it worked).
- Confirmation email sent (per the common pattern above).
- Form clears / becomes unavailable for immediate resubmission, to avoid accidental duplicates.

**On submit — failure:**
- **If the webhook/receiver is unreachable, the submission must not be silently lost.** This is
  the one hard requirement worth stating even without a sourced answer for the mechanism: either
  Wix's native form-storage acts as a fallback of record (Wix retains submissions in its own
  dashboard regardless of webhook success — confirm this is enabled) so a failed webhook is
  recoverable, or the receiver needs a retry/dead-letter mechanism. `[[decide the fallback
  mechanism before launch — a silently dropped partnership or media enquiry is a real business
  cost, not just a technical gap]]`.
- User sees a clear, non-technical error state with an alternative contact path (e.g. "something
  went wrong — email us directly at sunil@inzbc.org") rather than a dead end.
- Server-side validation failures (should be rare if client-side validation is thorough) return a
  specific reason where possible, not a generic failure.

## Privacy

NZ Privacy Act 2020 applies to every form that collects personal information (per `trade.md`'s
footer note and `CLAUDE.md`'s membership-data rule). Every form needs a visible privacy
acknowledgement or link, consistent with the `consent.privacy_act_acknowledged` field in the
proposed payload above.

## Open items
1. Exact webhook payload contract — this doc proposes a shape; Bhanu finalises it.
2. Owner-notification routing table per `form_type` — not sourced anywhere.
3. Fields for partnership enquiry, market-entry, introduction request, sponsorship, delegation
   EOI, speaker, media, newsletter, profile update, member news forms — not yet specified in any
   content page.
4. The "join/renew as native form vs. pure external redirect" contradiction between `website.md`
   and every content page describing Join — needs a decision, not an assumption.
5. Spam-protection mechanism (Wix-native vs. custom) — not chosen.
6. Failed-webhook fallback mechanism — not chosen; flagged as a real business risk, not a
   technicality, given a lost enquiry has no user-visible symptom unless this is handled.
