# API integration specification

How frontend surfaces connect to the shared API (`services/api`): authentication, SIP API calls,
the Trade Digest approval mechanism, and the Comms Assistant request/response flow. This spec
distinguishes what's **built and live today**, what's **specified but not yet built**, and what's
**proposed** — those are three different confidence levels and this doc doesn't blur them.

## Sources
- `services/api/main.py` — the actual FastAPI app, today (one live endpoint).
- `services/api/model_gateway.py` — the actual model-call gateway, today.
- `schemas/api-contract.md` — SIP pipeline/control endpoint shapes, v0.1 draft.
- [ADR-0004](decisions/0004-platform-graduation.md) — hosting, identity, session/auth design.
- `docs/ai-service-architecture.md` — how the three AI modules integrate with the site.
- `docs/modules/comms-assistant.md`, `docs/page-specs.md` §6 — Comms Assistant and Digest specifics.
- `docs/workstreams/bhanu.md` — issue #65 (streaming Comms API), redaction layer status.
- `docs/requirements.md` REQ-U-04 — the one integration with a shipped, tested client today.

## Three surfaces, not one API

This is the first thing to get right, because "the shared API" means different things depending
on which frontend is asking:

| Surface | Auth | Origin | Status |
|---|---|---|---|
| Public FTA Explainer (`GET /api/fta/query`) | None — unauthenticated | CORS-enabled (only endpoint that is) | **Live today** (`services/api/main.py`) |
| Staff SIP control UI | GitHub OAuth + session | Same-origin (API serves the static UI) | Specified (`api-contract.md`), not yet backed by a live DB |
| Staff Comms Assistant UI | GitHub OAuth + session | Same-origin | Architecture decided, endpoint not built (issue #65) |

The **member portal is not on this list.** It runs on Wix Members Area and talks to Member
Jungle, not to `services/api` — see `docs/modules/member-portal-spec.md`. Nothing in this doc
applies to it.

## Authentication flow (staff surfaces only)

Sourced entirely from [ADR-0004](decisions/0004-platform-graduation.md)'s "Identity and
authorization" section — reproduced here as a flow, not re-decided:

1. User clicks "Sign in" → redirected to GitHub OAuth (app owned by the
   `India-New-Zealand-Business-Council` organisation, `[[INZBC to confirm org-level
   registration]]`).
2. GitHub authenticates the user and redirects back with a successful login.
3. **Allowlist check:** the API looks up the GitHub login against the `users` table. No active
   row → `403`, no session issued. **A successful GitHub login is not, by itself, authorisation.**
4. If allowed: `users.role_id` resolves to a role (`SIP Owner` / `Analyst` / `Quality Reviewer` /
   `Secretariat` / `Administrator` / `Board Viewer` / `Auditor`), seeded from
   `docs/sip/launch/launch-config.md`. Role changes are a data edit, not a deploy.
5. **Server-side session created** — opaque session id in a cookie, session state in Postgres.
   Not a JWT: chosen specifically so a session can be revoked immediately rather than waiting out
   a token's expiry.
6. **Cookie:** `HttpOnly`, `Secure`, `SameSite=Lax`, host-only (no domain wildcard).
7. **CSRF:** a double-submit token required on every state-changing (non-GET) request —
   `SameSite=Lax` alone doesn't cover top-level POST navigation.
8. **Expiry:** absolute 12 hours, idle timeout 60 minutes, whichever is sooner.
9. **Offboarding:** set `users.active = false`. The next request on any existing session for that
   user fails — no code change, no redeploy, no key rotation needed.

**Separation of duties is enforced server-side, not just in the UI:** a run's `analyst_id` cannot
equal its `reviewer_id` (`api-contract.md`, `schema.sql`). The SIP UI screens in
`docs/sip-ui-spec.md` disable the illegal path in the interface, but the check that actually
matters lives here.

**Status:** this design is Accepted (ADR-0004) but the database migrations that would make
`users`/`roles`/sessions real are still on Bhanu's Next Up list, not Done — so this flow is
specified, not yet live. Build against contract fixtures until that lands, per the same worklog.

## SIP API calls

Full endpoint list from `schemas/api-contract.md` (v0.1 draft — shapes may still move):

**Pipeline (Roshan — data in):** `POST /api/runs`, `GET /api/runs[/:id]`,
`POST /api/runs/:id/{start,pause,resume,complete}`, `GET /api/runs/:id/source-checks`,
`POST /api/runs/:id/source-checks`, `GET /api/source-library`, `GET /api/candidates?run=:id`,
`POST /api/candidates`, `PATCH /api/candidates/:id`,
`POST /api/candidates/:id/{verify,score,route,merge}`.

**Control (Paras — data out + human gates):** `POST /api/reports/daily`,
`GET /api/reports/:id`, `POST /api/reports/:id/qa`, `POST /api/reports/:id/submit`,
`POST /api/reports/:id/{approve,request-changes}`, `POST /api/reports/:id/decision`,
`GET /api/registers/:name`, `POST /api/registers/:name`, `GET /api/dashboard`.

**Cross-cutting:** `GET /api/audit` (append-only, read), `GET /api/config` (server-side flags,
read).

These endpoints map directly onto the four screens in `docs/sip-ui-spec.md` (brief builder → QA
→ CEO decision → distribution status) — that doc has the screen-by-screen call sequence; this
section is the reference list, not a duplicate walkthrough.

**Fail-closed, every write:** a Critical condition (missing run authority, unapproved version,
missing mandatory source outcome, unverified Critical claim, tracker/DB contradiction, missing
approval, unauthorised distribution) returns an error, never a warning — `api-contract.md`'s own
rule, unchanged here.

**What's actually running today:** none of the above. `services/api/main.py` implements only the
FTA Explainer read path (`GET /api/fta/query`) — its own docstring says the SIP endpoints "land
once the database and the orchestrator's persistence exist." That's the same migrations blocker
noted under Authentication above.

## Trade Digest approval — not an API endpoint today

Worth stating precisely, because the natural assumption (an approval endpoint mirroring the SIP
pattern) is not what's actually specified anywhere:

Per `docs/ai-service-architecture.md` and `docs/page-specs.md` §6, the Digest's human-review gate
is a **Wix CMS status field**, not an API call:

1. The digest pipeline (a separate scheduled service, not `services/api`) evaluates sources,
   summarises, and writes a **draft** directly into a Wix CMS collection via the Wix Data API,
   with `status = draft`.
2. A **named human reviewer** (still unassigned — `docs/discovery.md` OI-5) edits/approves
   **inside the Wix dashboard itself**, flipping the CMS field to `status = published`.
3. The public Digest page and archive render **only** items where `status = published` — this is
   the enforcement point, not a separate approval endpoint.

**So: there is no `/api/digest/*` approval surface to document, because the design deliberately
routes the human gate through Wix's own CMS editing UI instead of a custom one.** If the team
later wants a dedicated approval screen (mirroring the SIP QA/CEO decision pattern in
`sip-ui-spec.md`, e.g. `POST /api/digest/:id/approve`), that would be a **new design decision**,
not something already specified — flagged in Open items below, not built here as if it were.

## Comms Assistant request/response flow

**What's actually built today:** `services/api/model_gateway.py` — a single server-side
`ModelGateway.complete(prompt) -> GatewayResult` path. Provider is OpenAI `gpt-4.1-mini` (the
same account/model `daily-india-nz-news-agent` already uses), fails closed with
`GatewayNotConfiguredError` if no API key is present rather than fabricating a response, one
retry on a transient failure. SIP scoring already calls through this same gateway — the Comms
Assistant is designed to reuse it, not build a second model-call path (`model_gateway.py`'s own
docstring: "SIP scoring, the Comms Assistant and the FTA layer call through here rather than
constructing their own clients").

**What's specified but not built** (`docs/workstreams/bhanu.md` issue #65, "Streaming Comms
Assistant API (SSE)"):

```
Staff user (authenticated, same-origin)
  → submits a drafting request (channel: email | website | social; context/prompt)
  → [REDACTION LAYER — strips member/Board/confidential data before any model call]
  → ModelGateway.complete() (or a streaming equivalent)
  → SSE token stream back to the UI as the draft generates
  → draft rendered in the UI — never sent, never published
  → named human reviewer edits/approves (docs/modules/comms-assistant.md "Definition of done")
  → only on approval: handoff to the actual send/publish channel (mechanism not specified —
    see Open items)
```

**A gap worth flagging prominently, not softening:** the redaction step above is
**non-negotiable** per `docs/modules/comms-assistant.md` ("Prohibited by default: no
member/sponsor/stakeholder personal data... no confidential government/commercial data") and per
the SIP redaction rule this reuses. But `bhanu.md`'s Next Up list records it as **"currently
unowned."** No request should reach the model gateway from the Comms Assistant until this has an
owner and an implementation — that's not a nice-to-have gap, it's the one control that makes the
"drafts only, adversarially tested" promise in `comms-assistant.md` actually true.

**Also not yet true:** the adversarial/security review `comms-assistant.md` requires "before
staff use" hasn't happened (nothing built yet to review) — this flow cannot ship to real staff
use before that review passes, same gate as SIP.

## Cross-cutting rules (every surface)

- **No secrets, no model calls, from the browser** — every model call goes through
  `model_gateway.py` server-side (NFR-01, shipped, tested — `test_model_gateway.py`).
- **Fail-closed on Critical conditions** (NFR-02) — across SIP gates today; the same principle
  should extend to the Comms redaction gate once it's built, per the flag above.
- **Same-origin for authenticated surfaces** — deliberate per ADR-0004: "session cookies never
  cross an origin boundary and CORS is not part of the staff auth path." CORS is enabled *only*
  on the public, unauthenticated FTA endpoint.
- **`production_enabled` stays false** everywhere until a formal launch-approval record exists
  (`docs/sip/README.md`) — this gates SIP distribution today and should gate any future Comms
  send/publish handoff the same way.

## Open items
1. Migrations (issue #44) are the real blocker for every SIP endpoint above going live — build UI
   against contract fixtures until then, per `docs/workstreams/bhanu.md`.
2. Redaction layer for the Comms Assistant: unowned. Needs an owner before any real request flow
   is built, not just before launch.
3. SSE streaming Comms endpoint (#65): not built. `model_gateway.complete()` is synchronous,
   single-response today — streaming is new work, not a small extension.
4. Comms Assistant send/publish handoff mechanism after human approval: not specified anywhere
   (email? Mailchimp? manual copy-paste by staff?) — `docs/ai-service-architecture.md`'s own Open
   Questions asks this exact thing (#4) and it's still open.
5. Whether the Trade Digest should ever get a dedicated approval API (vs. staying a Wix CMS status
   flip) is an open design question, not a decision — don't build one without confirming the team
   wants to move off the CMS-gate design.
6. Named human reviewer for Digest/Comms output (OI-5) is still unassigned — blocks real use of
   either flow regardless of what's technically built.
