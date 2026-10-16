# Wix-to-Internal Site-Forms Webhook Contract (#45)

Defines the webhook delivery contract from the public Wix Vibe site (`inzview`) to the INZBC
platform (`services/api/site_forms.py`) and the staff read surface over received submissions.
Ownership follows [ADR-0007](../docs/decisions/ADR-0007-headless-site-platform-boundary.md):
Paras owns the public site's form UI and confirmation messaging; Bhanu owns the webhook contract
and the internal receiver service.

## 1. Transport and URL Safety

- **Receiver endpoint:** `POST /api/webhooks/wix/site-forms`
- **Staff read endpoints:**
  - `GET /api/site-forms?form_type=<type>&limit=<n>`
  - `GET /api/site-forms/{submission_id}`
- **No query parameters on webhook delivery:** The receiver rejects any request whose URL contains
  a non-empty query string (`400 Bad Request`) before reading the body. Neither secrets
  (`WIX_WEBHOOK_SECRET`), tokens, nor submitter personal data (`contact_email`, `contact_name`,
  `phone`, `message`) may ever appear in the URL path or query string, where proxies and access
  logs would record them in cleartext.

## 2. Authentication and Replay Protection

Webhook deliveries are machine-to-machine requests originating from Wix automation/backend hooks,
not browser requests carrying a staff `inzbc_session` cookie. Every delivery must carry two HTTP
headers:

| Header | Format | Purpose |
| :--- | :--- | :--- |
| `X-Wix-Webhook-Timestamp` | Unix epoch seconds (integer string, e.g. `1760612400`) | Bounds replay window to `±300` seconds of server UTC clock |
| `X-Wix-Webhook-Signature` | `sha256=<64-char lowercase hex digest>` | HMAC-SHA256 over `<timestamp>.<raw_request_body_bytes>` using `WIX_WEBHOOK_SECRET` |

### Signing string construction

```text
signing_input = ascii(X-Wix-Webhook-Timestamp) + "." + raw_request_body_bytes
expected_sig  = "sha256=" + hmac_sha256_hex(WIX_WEBHOOK_SECRET, signing_input)
```

### Refusal behaviour (fail-closed)

1. **`503 Service Unavailable`** if `WIX_WEBHOOK_SECRET` is unset or blank on the receiver.
2. **`400 Bad Request`** if the request URL contains any query parameter.
3. **`401 Unauthorized`** if `X-Wix-Webhook-Timestamp` or `X-Wix-Webhook-Signature` is missing,
   malformed, outside the `300`-second replay window, or fails `hmac.compare_digest`.

## 3. Payload Schema

`Content-Type: application/json`. Unrecognised fields are rejected (`extra="forbid"`).

```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "form_type": "membership_enquiry",
  "submitted_at": "2026-10-16T10:15:00Z",
  "page_slug": "/members",
  "contact_name": "Aarav Patel",
  "contact_email": "aarav.patel@example.co.nz",
  "organisation": "Southern Cross Exports Ltd",
  "phone": "+64 9 555 0199",
  "subject": "Corporate membership enquiry",
  "message": "We export honey and dairy ingredients to Mumbai and would like to join INZBC.",
  "metadata": {
    "membership_tier": "corporate",
    "sector": "Food & Beverage"
  }
}
```

### Field rules

| Field | Type | Required | Constraints |
| :--- | :--- | :--- | :--- |
| `event_id` | UUID | Yes | Unique per Wix webhook event; idempotency key across retries |
| `form_type` | Enum | Yes | `general_enquiry`, `membership_enquiry`, `event_registration`, `trade_enquiry`, `partnership_enquiry` |
| `submitted_at` | ISO-8601 UTC datetime | Yes | Timezone-aware timestamp (`Z` or explicit offset) |
| `page_slug` | string | Yes | Non-empty path starting with `/`, max `120` chars |
| `contact_name` | string | Yes | Trimmed non-empty string, `1..200` chars |
| `contact_email` | string | Yes | Validated email (`local@domain.tld`, no whitespace), max `320` chars |
| `organisation` | string \| null | No | Max `200` chars |
| `phone` | string \| null | No | Max `60` chars |
| `subject` | string \| null | No | Max `300` chars |
| `message` | string \| null | No | Max `5000` chars |
| `metadata` | object (`str -> str`) | No | Up to `20` keys; keys `1..64` chars, values `0..500` chars |

## 4. Idempotency, Retries, and Persistence

- **Canonical payload digest:** The receiver computes `payload_sha256` over the canonicalised
  submission fields (`event_id`, `form_type`, `submitted_at`, `page_slug`, `contact_name`,
  `contact_email`, `organisation`, `phone`, `subject`, `message`, `metadata`).
- **First delivery:** Persists a row in `site_form_submissions` and writes a transactional
  `audit_log` entry (`action = 'site_form.received'`, `record_type = 'site_form_submission'`) in
  the same transaction. Personal contact fields (`contact_name`, `contact_email`, `phone`,
  `message`) are **never** copied into `audit_log`. Returns `201 Created` with
  `{"submission_id": "...", "event_id": "...", "form_type": "...", "received_at": "...", "deduplicated": false}`.
- **Safe retry (same `event_id` + same `payload_sha256`):** Returns `200 OK` with the existing
  record and `"deduplicated": true` without inserting a duplicate row.
- **Conflicting retry (same `event_id` + different `payload_sha256`):** Returns `409 Conflict` so
  a key collision or mutated replay is surfaced rather than overwriting evidence.
- **Retry guidance for Wix dispatcher:** Retry on `502`/`503`/`504` or network timeout with
  exponential backoff (`1s`, `5s`, `30s`, `300s`, up to 5 attempts) reusing the original
  `event_id` and payload body with a fresh `X-Wix-Webhook-Timestamp` and `X-Wix-Webhook-Signature`.
  Do not retry `400`, `401`, `409`, or `422`.
